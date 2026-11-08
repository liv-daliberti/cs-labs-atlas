"""Explicit observed-year uncertainty holds preserve direct/PDF school evidence and prior history."""
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import zlib

import pytest

import atlas_paths as P
from pihier import papers
import schema_check
import test_build_rules as T
from test_missing_papers_rules import cross


def policy(year=2020):
    return dict(action='hold_company_only_fallback', years=[year], reason='Current on-leave source; dates unknown, fallback needs review.',
                evidence=[dict(url='https://example.edu/owned', sha256='a' * 64,
                               quote='I am an Associate Professor at the university (on leave).', observedAt=f'{year}-11-07T16:37:44')],
                leave_start=None, leave_end=None, departure_inferred=False)


def prepared(tmp_path, monkeypatch, year=2020, hold=True, upto='papers'):
    sweep = cross()
    for w in sweep:
        w['publication_year'] = year; w['publication_date'] = f'{year}-01-01'
    overrides = copy.deepcopy(T.OVERRIDES)
    if hold: overrides[T.SCHOOL]['Ada Lovelace']['cross_affiliation_holds'] = [policy()]
    monkeypatch.setattr(T, 'OVERRIDES', overrides)
    T.write_school(tmp_path, sweep)
    return T.run_stages(tmp_path, upto=upto), sweep


@pytest.mark.usefixtures('layout')
def test_native_uncertain_company_fallback_is_held_without_rejecting_person_or_direct_papers(tmp_path, monkeypatch):
    ctx, _ = prepared(tmp_path, monkeypatch)
    assert 'Selective Caches for Hybrid Memory' not in T.rows_of(ctx, 'Ada Lovelace')
    assert set(T.rows_of(ctx, 'Ada Lovelace')) == {'Same Year Affiliated 0', 'Same Year Affiliated 1'}
    assert ctx.n['cross_affiliation_review_hold'] == 1
    (held,) = ctx.cross_affiliation_hold_review
    assert held['status'] == 'held_source_uncertainty' and held['date'] == '2020-01-01'
    assert held['reviews'][0] == policy()  # Before November observation; leave start remains unknown.
    assert held['admitting_appointment']['periodId'] == 'reviewed:ada-lovelace:1'
    assert ctx.pid0['Ada Lovelace']['periods'][0]['start'] == '2015'


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('year,hold', [(2019, True), (2020, False), (2021, True)])
def test_genuine_prior_or_other_year_history_and_unreviewed_legacy_fallback_are_preserved(tmp_path, monkeypatch, year, hold):
    ctx, _ = prepared(tmp_path, monkeypatch, year=year, hold=hold)
    assert 'Selective Caches for Hybrid Memory' in T.rows_of(ctx, 'Ada Lovelace')
    assert ctx.n['cross_affiliation_review_hold'] == 0


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('basis', ['own_raw', 'own_dual', 'primary_pdf'])
def test_actual_own_school_and_primary_pdf_routes_are_not_suppressed(tmp_path, monkeypatch, basis):
    ctx, sweep = prepared(tmp_path, monkeypatch, upto='hits')
    target = next(h for h in ctx.hits if h[0] == 'Ada Lovelace' and h[1]['title'] == 'Selective Caches for Hybrid Memory')
    w, author = target[1:3]
    if basis == 'own_raw': author['raw_affiliation_strings'].append('Princeton University')
    elif basis == 'own_dual': author['institutions'].append(dict(id=T.INST, lineage=[T.INST], display_name='Princeton University', type='education'))
    else: ctx.tied[w['id']] = dict(how='footnote', quotes=['Ada Lovelace, Princeton University'],
                                  url='https://example.edu/paper.pdf', pdf_sha256='b' * 64)
    before = copy.deepcopy(w); papers.lab_papers(ctx)
    assert 'Selective Caches for Hybrid Memory' in T.rows_of(ctx, 'Ada Lovelace')
    assert ctx.n['cross_affiliation_review_hold'] == 0 and w == before


@pytest.mark.parametrize('change', ['action', 'inferred_year', 'duplicate_year', 'boolean_year', 'missing_hash', 'missing_quote',
                                   'primary_quote', 'date', 'missing_date', 'start', 'end', 'departure', 'missing_reason'])
def test_malformed_or_inferred_hold_policy_fails_closed(change):
    hold = policy()
    if change == 'action': hold['action'] = 'drop_all_papers'
    elif change == 'inferred_year': hold['years'] = [2019, 2020]
    elif change == 'duplicate_year': hold['years'] = [2020, 2020]
    elif change == 'boolean_year': hold['years'] = [True]
    elif change == 'missing_hash': hold['evidence'][0].pop('sha256')
    elif change == 'missing_quote': hold['evidence'][0].pop('quote')
    elif change == 'primary_quote': hold['evidence'][0]['quote'] = 'I am a Professor.'
    elif change == 'date': hold['evidence'][0]['observedAt'] = '2020-99-99'
    elif change == 'missing_date': hold['evidence'][0].pop('observedAt')
    elif change == 'start': hold['leave_start'] = '2020-01-01'
    elif change == 'end': hold['leave_end'] = '2020-12-31'
    elif change == 'departure': hold['departure_inferred'] = True
    else: hold.pop('reason')
    with pytest.raises(ValueError): papers.reviewed_cross_affiliation_holds({'Ada Lovelace': dict(cross_affiliation_holds=[hold])})


def test_exact_meel_reviewed_source_policy_is_consumed_and_schema_valid():
    root = Path(__file__).resolve().parents[1]
    overrides = json.loads((root / 'hierarchy/toronto/reviewed/census-overrides-school.json').read_text())
    assert schema_check.validate({'toronto': overrides}, json.loads((root / 'schemas/census-overrides.schema.json').read_text())) == []
    selected = papers.reviewed_cross_affiliation_holds(overrides)
    assert set(selected) == {'Kuldeep Meel'} and set(selected['Kuldeep Meel']) == {2026}
    hold = selected['Kuldeep Meel'][2026][0]
    assert hold['leave_start'] is hold['leave_end'] is None and hold['departure_inferred'] is False
    assert hold['evidence'][0]['quote'] == overrides['Kuldeep Meel']['nonprimary_appointment_observation']['quote']


@pytest.mark.nfs
def test_meel_original_owned_body_hash_and_literal_leave_observation():
    root = Path(__file__).resolve().parents[1];overrides = json.loads((root / 'hierarchy/toronto/reviewed/census-overrides-school.json').read_text())
    source = overrides['Kuldeep Meel']['cross_affiliation_holds'][0]['evidence'][0]
    path = P.data('school-captures.sqlite', 'toronto')
    if not path.is_file(): pytest.skip('original registered Toronto source cache absent')
    with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
        (status, stored, blob), = db.execute('select status,sha256,raw_zlib from live where url=?', (source['url'],)).fetchall()
    raw = zlib.decompress(blob); assert status == 200 and stored == source['sha256'] == hashlib.sha256(raw).hexdigest()
    from bs4 import BeautifulSoup
    text = ' '.join(BeautifulSoup(raw, 'html.parser').get_text(' ', strip=True).split())
    assert source['quote'] in text and 'Kuldeep S. Meel' in text
