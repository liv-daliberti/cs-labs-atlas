"""Historical officer documents do not become current faculty observations on retrieval."""
import collections
import hashlib
import json
import sqlite3
import subprocess
import zlib

import pytest

import cs_related_school as C
from pihier.periods import pi_listings


MEANING = ('The mention of a date before a name means that the person named entered in that year '
           'into the office or appointment specified.')
PDF_TEXT = ('University Officers\nThis issue includes data received up to 12 January 2018.\n' + MEANING
            + '\fPROFESSORS (continued)\nComputing 2004 Avery James Scientist, CL\n'
            + '\fEMERITUS PROFESSORS\nComputing: Riley Retired, CL\n')


def entry():
    return dict(name='Avery Scientist', unit='CS', url='https://school.example/officers.pdf',
                sha256=hashlib.sha256(b'%PDF-fake-officer-fixture').hexdigest(),
                quote='Computing 2004 Avery James Scientist, CL', observed='20261116', ladder=True,
                dated_listing=dict(date='2018-01-12', date_quote='data received up to 12 January 2018.',
                                   page=2, heading='PROFESSORS', entry_name='Avery James Scientist',
                                   appointment_year='2004', appointment_column_quote=MEANING))


def source_db(monkeypatch, row=None, *, corrupt=False, other_url=False):
    row = row or entry()
    db = sqlite3.connect(':memory:')
    db.execute('create table captures (sha256 text, text text)')
    db.execute('create table live (url text, sha256 text, raw_zlib blob)')
    raw = b'%PDF-fake-officer-fixture' + (b'bad' if corrupt else b'')
    db.execute('insert into live values (?,?,?)',
               ('https://other.example/officers.pdf' if other_url else row['url'], row['sha256'], zlib.compress(raw)))
    monkeypatch.setattr(C.subprocess, 'run', lambda *a, **kw: subprocess.CompletedProcess(a[0], 0, PDF_TEXT.encode(), b''))
    return db


def test_dated_listing_reads_source_date_rank_and_name_without_an_interval():
    row = entry()
    assert C.dated_listing(row, PDF_TEXT) == row['dated_listing']
    assert row['observed'] == '20261116'
    assert C.faculty_observed(row) == '20180112'
    assert C.dated_source_fields(row)['retrieved_at'] == '20261116'


def test_active_reader_uses_its_own_rank_section():
    row = entry()
    row['dated_listing']['heading'] = 'READERS'
    text = PDF_TEXT.replace('PROFESSORS (continued)', 'READERS (continued)')
    assert C.dated_listing(row, text)['heading'] == 'READERS'
    row['ladder'] = False
    with pytest.raises(SystemExit, match='active ladder appointment'):
        C.dated_listing(row, text)


@pytest.mark.parametrize('title', ['Sir', 'Dame'])
def test_literal_knighthood_title_preserves_source_and_binds_full_identity(title):
    row = entry()
    row['dated_listing']['entry_name'] = title + ' Avery James Scientist'
    row['quote'] = row['quote'].replace('Avery James Scientist', row['dated_listing']['entry_name'])
    text = PDF_TEXT.replace('Avery James Scientist', row['dated_listing']['entry_name'])
    assert C.dated_listing(row, text) == row['dated_listing']
    # A title does not relax the full-name or actual source-column requirements.
    for bad_name in ['A. James Scientist', 'Riley James Scientist', 'Avery Riley Scientist']:
        bad_row = entry()
        bad_row['name'] = 'Avery J. Scientist'
        bad_row['dated_listing']['entry_name'] = title + ' ' + bad_name
        bad_row['quote'] = row['quote'].replace('Avery James Scientist', bad_name)
        bad_text = text.replace('Avery James Scientist', bad_name)
        with pytest.raises(SystemExit, match='full entry name'):
            C.dated_listing(bad_row, bad_text)
    row['dated_listing']['entry_name'] = 'Avery James Scientist'
    with pytest.raises(SystemExit, match='appointment year'):
        C.dated_listing(row, text)


@pytest.mark.parametrize('change,reason', [
    ({'date': '2027-01-12'}, 'window'),
    ({'date': '2018-02-30'}, 'valid document'),
    ({'date': '2018-01-13'}, 'not stated'),
    ({'date_quote': 'An invented date: 12 January 2018.'}, 'not stated'),
    ({'appointment_column_quote': 'These are graduation years.'}, 'column meaning'),
    ({'page': 3}, 'rank heading'),
    ({'page': 0}, 'page number'),
    ({'page': True}, 'page number'),
    ({'heading': 'EMERITUS PROFESSORS'}, 'rank heading'),
    ({'entry_name': 'Riley Retired'}, 'full entry name'),
    ({'entry_name': 'A. Scientist'}, 'full entry name'),
    ({'appointment_year': '2019'}, 'appointment year'),
    ({'appointment_year': '2018'}, 'appointment year'),
    ({'appointment_year': '2003'}, 'appointment year'),
])
def test_invalid_or_unbound_historical_observations_stay_rejected(change, reason):
    row = entry()
    row['dated_listing'].update(change)
    with pytest.raises(SystemExit, match=reason):
        C.dated_listing(row, PDF_TEXT)


def test_explicit_middle_name_conflict_rejects_an_untitled_officer():
    row = entry()
    row['name'] = 'Avery R. Scientist'
    with pytest.raises(SystemExit, match='full entry name'):
        C.dated_listing(row, PDF_TEXT)


def test_observation_cannot_be_after_retrieval_or_supply_a_period():
    row = entry()
    row['observed'] = '20170101'
    with pytest.raises(SystemExit, match='no later than retrieval'):
        C.dated_listing(row, PDF_TEXT)
    row = entry()
    row['historical_appointment'] = {'start': '2004', 'end': '2018'}
    with pytest.raises(SystemExit, match='not an appointment interval'):
        C.dated_listing(row, PDF_TEXT)


def test_adjacent_role_sections_and_a_quote_from_another_page_are_not_rank_evidence():
    row = entry()
    with pytest.raises(SystemExit, match='mixed'):
        C.dated_listing(row, PDF_TEXT.replace('Computing 2004', 'READERS\nComputing 2004'))
    row['quote'] = 'Computing: Riley Retired, CL'
    with pytest.raises(SystemExit, match='not on its stated page'):
        C.dated_listing(row, PDF_TEXT)


def test_pdf_bytes_and_exact_source_url_bind_the_historical_review(monkeypatch):
    for kwargs in ({'corrupt': True}, {'other_url': True}):
        db = source_db(monkeypatch, **kwargs)
        with pytest.raises(SystemExit, match='hash-verified PDF bytes at its exact source URL'):
            C.hand_evidence('cambridge', c=db, entries=[entry()])


def test_pdf_semantic_text_preserves_rank_when_layout_has_font_letterspacing(monkeypatch):
    db = source_db(monkeypatch)
    def extract(args, **kwargs):
        text = PDF_TEXT if '-raw' in args else PDF_TEXT.replace('PROFESSORS', 'P R O F E S S O R S')
        return subprocess.CompletedProcess(args, 0, text.encode(), b'')
    monkeypatch.setattr(C.subprocess, 'run', extract)
    evidence = C.hand_evidence('cambridge', c=db, entries=[entry()])['avery scientist'][0]
    assert evidence['dated_listing']['date'] == '2018-01-12'


def test_source_dated_year_reaches_native_listings_and_preserves_retrieval(monkeypatch, tmp_path):
    row = entry()
    db = source_db(monkeypatch)
    files = {
        'cs-related-candidates.json': [dict(name=row['name'], source='dblp_affiliation', dblp='https://dblp.org/pid/avery')],
        'dblp-affiliated.json': {'persons': [dict(pid='https://dblp.org/pid/avery', n_window=10,
                                                affiliations=[{'text': 'University of Cambridge'}])]},
        'census-faculty.json': {'faculty': []}, 'cs-related-hand.json': [row],
    }
    for filename, data in files.items():
        (tmp_path / filename).write_text(json.dumps(data))
    monkeypatch.setattr(C.P, 'data', lambda filename, key=None: tmp_path / filename)
    monkeypatch.setattr(C.P, 'data_w', lambda filename, key=None: tmp_path / filename)
    monkeypatch.setattr(C.S, 'get', lambda key: {'cs_related': {}, 'census': {}})
    monkeypatch.setattr(C, 'units_current', lambda key: True)
    monkeypatch.setattr(C, 'unit_pages', lambda key: [])
    monkeypatch.setattr(C.W, 'con', lambda key: db)
    monkeypatch.setattr(C, 'oa_stats', lambda key: {'present': True})
    years = []
    def share(*args):
        years.append(args[3])
        return dict(result='computing', ids=[], school_works=10, dblp_indexed=10, share=1.0)
    monkeypatch.setattr(C, 'share_test', share)
    C.review('cambridge')
    decision = json.loads((tmp_path / 'cs-related-review.json').read_text())['decisions'][0]
    addition = json.loads((tmp_path / 'census-additions.json').read_text())[0]
    assert decision['decision'] == 'accepted'
    assert years == [2018]
    assert decision['faculty_evidence'][0]['observed'] == '20261116'
    assert addition['years_listed'] == [2018]
    assert addition['sources'][0]['observed'] == '20180112'
    assert addition['sources'][0]['retrieved_at'] == '20261116'
    assert addition['pi_basis']['dated_listing'] == row['dated_listing']
    assert addition['pi_basis']['retrieved_at'] == '20261116'
    assert set(pi_listings(addition, {}, collections.Counter())) == {2018}
    assert not (tmp_path / 'census-overrides-school.json').exists()


def test_current_evidence_keeps_legacy_observation_and_unit_recency():
    old = entry()
    current = dict(unit='CURRENT', observed='20250101')
    assert C.units_by_recency([old, current], set()) == ['CS', 'CURRENT']
    assert C.faculty_observed(current) == '20250101'
    assert C.dated_source_fields(current) == {}
