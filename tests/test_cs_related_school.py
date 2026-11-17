import pytest

import cs_related_school as C


def test_faculty_title_does_not_cross_named_doctor_entry():
    pages = [('DPMMS', 'source', 'sha', '20250101',
              'Imre Leader Dr Kaisey Mandel Dr Stuart Martin Professor of Mathematics '
              'Chao Li Professor of Mathematics')]
    assert C.faculty_evidence(pages, ['Imre Leader']) == []
    assert C.faculty_evidence(pages, ['Chao Li'])[0]['ladder']


def test_faculty_title_does_not_cross_next_professor_prefix():
    pages = [('DPMMS', 'source', 'sha', '20200809',
              'Dr Chao Li Professor Benedikt Loewe Miss Giulia Luoni')]
    assert C.faculty_evidence(pages, ['Chao Li']) == []


def test_explicit_professor_role_still_supplies_evidence():
    pages = [('DPMMS', 'source', 'sha', '20200809',
              'Po-Ling Loh Professor of Statistics')]
    assert C.faculty_evidence(pages, ['Po-Ling Loh'])[0]['quote'] == 'Po-Ling Loh Professor of Statistics'


def test_qualified_role_is_not_mistaken_for_a_next_person_prefix():
    pages = [('AE', 'source', 'sha', '20200809',
              'Karen M Feigh Associate Professor Knight-419 View Full Profile')]
    assert C.faculty_evidence(pages, ['Karen M. Feigh'])[0]['ladder']


def research_review(monkeypatch, tmp_path, *, own=True, appointment=True, source='dblp_affiliation',
                    bad_quote=False, legacy=False, share_result=None, rank='research', kind='own_group', unit='CS',
                    historical=None, period_review='matching', period_text='2010-2021: Professor at University of Cambridge.'):
    import hashlib
    import json
    import sqlite3
    import zlib

    name = 'Avery Scientist'
    url = 'https://school.example/avery'
    title = 'Professor' if rank == 'ladder' else ('Research Professor' if rank == 'research' else 'Teaching Professor')
    html = f'<h1>Avery Scientist</h1><p>{title}</p><p>{period_text}</p><p>I lead the Example Research Group.</p>'.encode()
    sha = hashlib.sha256(html).hexdigest()
    db = sqlite3.connect(':memory:')
    db.execute('create table captures (sha256 text, text text)')
    db.execute('create table live (url text, sha256 text, raw_zlib blob)')
    db.execute('insert into live values (?,?,?)', (url, sha, zlib.compress(html)))
    role = dict(name=name, unit='CS', url=url, sha256=sha, quote=f'Avery Scientist {title}',
                observed='20261115', ladder=rank == 'ladder', appointment_rank=rank)
    if historical is not None:
        role.update(historical_appointment=historical, quote=f'Avery Scientist {title} {period_text}')
    basis = dict(pi=name, kind=kind, stage2_review=True, unit=unit, url=url, sha256=sha,
                 quote='I lead the Example Research Group.', role=title,
                 observed='20261115', appointment_rank=rank)
    if bad_quote:
        basis['quote'] = 'I lead a nonexistent lab.'
    if legacy:
        basis = dict(pi=name, kind='own_group', url=url, sha256=sha, quote=basis['quote'])
    pid = 'https://dblp.org/pid/avery/scientist'
    candidate = dict(name=name, aliases=[], source=source, dblp=pid,
                     openalex=['https://openalex.org/A100'])
    files = {
        'cs-related-candidates.json': [candidate],
        'dblp-affiliated.json': {'persons': [dict(pid=pid, n_window=10,
                                                affiliations=[{'text': 'University of Cambridge'}])]},
        'census-faculty.json': {'faculty': []},
        'cs-related-hand.json': [role] if appointment else [],
        'pi-basis-evidence.json': [basis] if own else [],
    }
    for filename, obj in files.items():
        (tmp_path / filename).write_text(json.dumps(obj))
    monkeypatch.setattr(C.P, 'data', lambda filename, key=None: tmp_path / filename)
    monkeypatch.setattr(C.P, 'data_w', lambda filename, key=None: tmp_path / filename)
    monkeypatch.setattr(C.S, 'get', lambda key: {'cs_related': {}, 'census': {}})
    monkeypatch.setattr(C, 'units_current', lambda key: True)
    monkeypatch.setattr(C, 'unit_pages', lambda key: [])
    monkeypatch.setattr(C.W, 'con', lambda key: db)
    periods = [dict(start=(historical or {}).get('start', '2010'), end=(historical or {}).get('end', '2021'),
                    datePrecision='month' if len((historical or {}).get('start', '2010')) == 7 else 'year', evidence=[dict(url=url, sha256=sha, quote=role['quote'])])]
    if period_review == 'missing':
        periods = []
    elif period_review == 'different_bounds':
        periods[0]['end'] = '2022'
    elif period_review == 'other_source':
        periods[0]['evidence'][0]['sha256'] = '0' * 64
    monkeypatch.setattr(C.CO, 'section', lambda key: {name: {'periods': periods}})
    monkeypatch.setattr(C, 'oa_stats', lambda key: {'present': True} if share_result else {})
    if share_result:
        monkeypatch.setattr(C, 'share_test', lambda *args: dict(
            result=share_result, ids=[], school_works=10, dblp_indexed=1, share=0.1, first_listing_year=args[3]))
    C.review('cambridge')
    return (json.loads((tmp_path / 'cs-related-review.json').read_text())['decisions'][0],
            json.loads((tmp_path / 'census-additions.json').read_text()))


def test_research_pi_needs_both_appointment_and_source_checked_own_group(monkeypatch, tmp_path):
    decision, additions = research_review(monkeypatch, tmp_path)
    assert decision['decision'] == 'accepted'
    assert additions[0]['rank'] == 'research'
    assert additions[0]['pi_basis']['kind'] == 'own_group'
    assert additions[0]['pi_basis']['quote'] == 'I lead the Example Research Group.'
    assert 'Research Professor' in additions[0]['title_as_listed']


def test_research_title_alone_does_not_make_a_pi(monkeypatch, tmp_path):
    decision, additions = research_review(monkeypatch, tmp_path, own=False)
    assert decision['decision'] == 'research_or_other_rank'
    assert additions == []


def test_owned_group_does_not_replace_an_appointment(monkeypatch, tmp_path):
    decision, additions = research_review(monkeypatch, tmp_path, appointment=False)
    assert decision['decision'] == 'pending_source_coverage'
    assert additions == []


def test_own_group_quote_must_be_in_saved_source(monkeypatch, tmp_path):
    import pytest
    with pytest.raises(SystemExit, match='pi-basis-evidence.json: the quote'):
        research_review(monkeypatch, tmp_path, bad_quote=True)


def test_research_pi_still_needs_computing_share(monkeypatch, tmp_path):
    decision, additions = research_review(monkeypatch, tmp_path, source='openalex_rule',
                                         share_result='not_computing')
    assert decision['decision'] == 'faculty_not_computing'
    assert additions == []


def test_research_pi_waits_for_missing_openalex_share(monkeypatch, tmp_path):
    decision, additions = research_review(monkeypatch, tmp_path, source='openalex_rule')
    assert decision['decision'] == 'pending_openalex'
    assert additions == []


def test_legacy_full_census_group_review_does_not_opt_in_to_stage2(monkeypatch, tmp_path):
    decision, additions = research_review(monkeypatch, tmp_path, legacy=True)
    assert decision['decision'] == 'research_or_other_rank'
    assert additions == []


def test_teaching_pi_keeps_its_reviewed_advising_basis(monkeypatch, tmp_path):
    decision, additions = research_review(monkeypatch, tmp_path, rank='teaching', kind='advises_phd')
    assert decision['decision'] == 'accepted'
    assert additions[0]['rank'] == 'teaching'
    assert additions[0]['pi_basis']['kind'] == 'advises_phd'


def test_group_review_from_another_unit_does_not_supply_this_appointment(monkeypatch, tmp_path):
    decision, additions = research_review(monkeypatch, tmp_path, unit='OTHER')
    assert decision['decision'] == 'research_or_other_rank'
    assert additions == []


def test_historical_professorship_preserves_observation_without_inventing_current_listing(monkeypatch, tmp_path):
    decision, additions = research_review(monkeypatch, tmp_path, own=False, rank='ladder',
                                         historical={'start': '2010', 'end': '2021'})
    assert decision['decision'] == 'accepted'
    assert decision['years_listed'] == []
    assert additions[0]['years_listed'] == []
    assert additions[0]['sources'][0]['observed'] == '20261115'
    assert additions[0]['sources'][0]['kind'] == 'historical_appointment:CS'
    assert additions[0]['pi_basis']['historical_appointment'] == {'start': '2010', 'end': '2021'}


def test_historical_appointment_requires_native_builders_reviewed_period(monkeypatch, tmp_path):
    import pytest
    with pytest.raises(SystemExit, match='matching source-bound reviewed census period'):
        research_review(monkeypatch, tmp_path, own=False, rank='ladder',
                        historical={'start': '2010', 'end': '2021'}, period_review='missing')


def test_historical_appointment_rejects_different_reviewed_end(monkeypatch, tmp_path):
    import pytest
    with pytest.raises(SystemExit, match='matching source-bound reviewed census period'):
        research_review(monkeypatch, tmp_path, own=False, rank='ladder',
                        historical={'start': '2010', 'end': '2021'}, period_review='different_bounds')


def test_historical_appointment_rejects_unbound_period_source(monkeypatch, tmp_path):
    import pytest
    with pytest.raises(SystemExit, match='matching source-bound reviewed census period'):
        research_review(monkeypatch, tmp_path, own=False, rank='ladder',
                        historical={'start': '2010', 'end': '2021'}, period_review='other_source')


def test_historical_appointment_cannot_invent_a_start_absent_from_quote(monkeypatch, tmp_path):
    import pytest
    with pytest.raises(SystemExit, match='bounds are absent from its source quote'):
        research_review(monkeypatch, tmp_path, own=False, rank='ladder', historical={'start': '2012', 'end': '2021'})


def test_historical_appointment_rejects_reversed_years(monkeypatch, tmp_path):
    import pytest
    with pytest.raises(SystemExit, match='chronological order'):
        research_review(monkeypatch, tmp_path, own=False, rank='ladder', historical={'start': '2021', 'end': '2010'})


def test_historical_appointment_outside_window_cannot_admit_pi(monkeypatch, tmp_path):
    import pytest
    with pytest.raises(SystemExit, match='overlap 2016'):
        research_review(monkeypatch, tmp_path, own=False, rank='ladder', historical={'start': '2000', 'end': '2010'})


def test_historical_appointment_cannot_treat_a_future_end_as_observed(monkeypatch, tmp_path):
    import pytest
    with pytest.raises(SystemExit, match='cannot end after its source observation'):
        research_review(monkeypatch, tmp_path, own=False, rank='ladder', historical={'start': '2010', 'end': '2030'})


def test_historical_appointment_requires_explicit_year_boundaries(monkeypatch, tmp_path):
    import pytest
    with pytest.raises(SystemExit, match='explicit start/end years'):
        research_review(monkeypatch, tmp_path, own=False, rank='ladder', historical={'start': '2010', 'end': None})


def test_historical_research_appointment_does_not_replace_independent_pi_basis(monkeypatch, tmp_path):
    decision, additions = research_review(monkeypatch, tmp_path, own=False,
                                         historical={'start': '2010', 'end': '2021'})
    assert decision['decision'] == 'research_or_other_rank'
    assert additions == []


def test_historical_research_pi_preserves_rank_and_does_not_create_current_listing(monkeypatch, tmp_path):
    decision, additions = research_review(monkeypatch, tmp_path,
                                         historical={'start': '2010', 'end': '2021'})
    assert decision['decision'] == 'accepted'
    assert additions[0]['rank'] == 'research'
    assert additions[0]['pi_basis']['kind'] == 'own_group'
    assert additions[0]['years_listed'] == decision['years_listed'] == []
    assert additions[0]['sources'][0]['kind'] == 'historical_appointment:CS'


def test_historical_months_bind_literal_dates_and_native_period(monkeypatch, tmp_path):
    decision, additions = research_review(monkeypatch, tmp_path, share_result='computing',
        historical={'start': '2016-01', 'end': '2018-09', 'start_quote': '01/2016', 'end_quote': '09/2018'},
        period_text='01/2016 - 09/2018 Research Associate at University of Cambridge.')
    assert decision['decision'] == 'accepted'
    assert decision['cs_basis']['openalex_share']['first_listing_year'] == 2016
    assert decision['years_listed'] == []
    assert additions[0]['rank'] == 'research'


def test_historical_month_cannot_be_invented_from_a_year(monkeypatch, tmp_path):
    import pytest
    with pytest.raises(SystemExit, match='bounds are absent from its source quote'):
        research_review(monkeypatch, tmp_path,
            historical={'start': '2010-01', 'end': '2021-09', 'start_quote': '2010', 'end_quote': '2021'})


@pytest.mark.parametrize('start_text,end_text', [
    ('June 2021', 'September 2024'),
    ('Jun 2021', 'Sept 2024'),
    ('Jun. 2021', 'Sep. 2024'),
    ('JUNE 2021', 'SEPTEMBER 2024'),
])
def test_named_months_preserve_explicit_historical_boundaries(monkeypatch, tmp_path, start_text, end_text):
    decision, additions = research_review(monkeypatch, tmp_path, own=False, rank='ladder',
        historical={'start': '2021-06', 'end': '2024-09', 'start_quote': start_text, 'end_quote': end_text},
        period_text=f'{start_text} – {end_text}: Assistant Professor at University of Cambridge.')
    assert decision['decision'] == 'accepted'
    assert decision['years_listed'] == additions[0]['years_listed'] == []
    assert additions[0]['pi_basis']['historical_appointment'] == {'start': '2021-06', 'end': '2024-09'}


@pytest.mark.parametrize('literal', ['Juniper 2021', 'Juneish 2021', 'Jun 2020'])
def test_named_months_cannot_rewrite_a_different_or_invalid_source_date(monkeypatch, tmp_path, literal):
    with pytest.raises(SystemExit, match='bounds are absent from its source quote'):
        research_review(monkeypatch, tmp_path, own=False, rank='ladder',
            historical={'start': '2021-06', 'end': '2024-09', 'start_quote': literal, 'end_quote': 'Sept 2024'},
            period_text=f'{literal} – Sept 2024: Assistant Professor at University of Cambridge.')


def test_named_month_literal_cannot_be_cut_out_of_another_word(monkeypatch, tmp_path):
    with pytest.raises(SystemExit, match='bounds are absent from its source quote'):
        research_review(monkeypatch, tmp_path, own=False, rank='ladder',
            historical={'start': '2021-06', 'end': '2024-09', 'start_quote': 'June 2021', 'end_quote': 'Sept 2024'},
            period_text='NotJune 2021 – Sept 2024: Assistant Professor at University of Cambridge.')


@pytest.mark.parametrize('literal', ['2015–23', '2015-23', '2015 — 23'])
def test_abbreviated_end_year_needs_the_complete_source_range(monkeypatch, tmp_path, literal):
    decision, additions = research_review(monkeypatch, tmp_path,
        historical={'start': '2015', 'end': '2023', 'end_quote': literal},
        period_text=f'{literal} Royal Society University Research Fellow, University of Cambridge.')
    assert decision['decision'] == 'accepted'
    assert additions[0]['rank'] == 'research'
    assert additions[0]['years_listed'] == decision['years_listed'] == []
    assert decision['faculty_evidence'][0]['historical_appointment'] == {'start': '2015', 'end': '2023'}
    assert additions[0]['sources'][0]['kind'] == 'historical_appointment:CS'


@pytest.mark.parametrize('start,end,literal', [
    ('2015', '2023', '23'),
    ('2015', '2023', '2020–23'),
    ('2015', '2022', '2015–23'),
    ('1998', '2023', '1998–23'),
])
def test_abbreviated_year_cannot_change_start_end_or_century(monkeypatch, tmp_path, start, end, literal):
    with pytest.raises(SystemExit, match='bounds are absent from its source quote'):
        research_review(monkeypatch, tmp_path,
            historical={'start': start, 'end': end, 'end_quote': literal},
            period_text=f'{start}; {literal} Royal Society University Research Fellow, University of Cambridge.')


def test_abbreviated_range_cannot_be_cut_out_of_another_word(monkeypatch, tmp_path):
    with pytest.raises(SystemExit, match='bounds are absent from its source quote'):
        research_review(monkeypatch, tmp_path,
            historical={'start': '2015', 'end': '2023', 'end_quote': '2015–23'},
            period_text='2015 Royal Society Fellow; Not2015–23 University of Cambridge.')


def test_abbreviated_year_range_does_not_supply_an_independent_pi_basis(monkeypatch, tmp_path):
    decision, additions = research_review(monkeypatch, tmp_path, own=False,
        historical={'start': '2015', 'end': '2023', 'end_quote': '2015–23'},
        period_text='2015–23 Royal Society University Research Fellow, University of Cambridge.')
    assert decision['decision'] == 'research_or_other_rank'
    assert additions == []


def test_historical_research_still_requires_matching_native_period(monkeypatch, tmp_path):
    import pytest
    with pytest.raises(SystemExit, match='matching source-bound reviewed census period'):
        research_review(monkeypatch, tmp_path, historical={'start': '2010', 'end': '2021'},
                        period_review='other_source')


def test_historical_research_does_not_take_other_units_pi_basis(monkeypatch, tmp_path):
    decision, additions = research_review(monkeypatch, tmp_path, unit='OTHER',
                                         historical={'start': '2010', 'end': '2021'})
    assert decision['decision'] == 'research_or_other_rank'
    assert additions == []

def test_current_professor_profile_still_proves_its_observation_year(monkeypatch, tmp_path):
    decision, additions = research_review(monkeypatch, tmp_path, own=False, rank='ladder')
    assert decision['years_listed'] == additions[0]['years_listed'] == [2026]


def test_historical_computing_identity_uses_appointment_start_not_biography_date(monkeypatch, tmp_path):
    decision, additions = research_review(monkeypatch, tmp_path, own=False, rank='ladder', source='openalex_rule',
                                         historical={'start': '2010', 'end': '2021'}, share_result='computing')
    assert decision['decision'] == 'accepted'
    assert decision['cs_basis']['openalex_share']['first_listing_year'] == 2010
    assert additions[0]['years_listed'] == []


def openalex_exclusion_fixture(monkeypatch, tmp_path, *, source_orcid='0000-0001-0000-0001',
                               author_orcids=('0000-0001-0000-0001',), author_name='Avery Scientist', linked=True):
    import gzip
    import json
    pid, author = 'https://dblp.org/pid/avery/scientist', 'https://openalex.org/A100'
    row = dict(name='Avery Scientist', source_id=pid)
    if linked:
        row['openalex_identities'] = [dict(author=author, orcid='0000-0001-0000-0001')]
    docs = {
        'cs-related-source-exclusions.json': {'records': [row]},
        'dblp-affiliated.json': {'persons': [dict(pid=pid, names=['Avery Scientist'], orcid=[source_orcid])]},
    }
    for filename, obj in docs.items():
        (tmp_path / filename).write_text(json.dumps(obj))
    if linked:
        with gzip.open(tmp_path / 'oa-author-stats.json.gz', 'wt') as f:
            json.dump({'authors': {author: dict(raw={author_name: 10}, orcids={o: 10 for o in author_orcids})}}, f)
    monkeypatch.setattr(C.P, 'data', lambda filename, key=None: tmp_path / filename)
    return pid, author


def test_exact_orcid_can_bind_reviewed_nonfaculty_openalex_identity(monkeypatch, tmp_path):
    pid, author = openalex_exclusion_fixture(monkeypatch, tmp_path)
    assert C.source_excluded_openalex_ids('cambridge', {pid}) == {author}


def test_openalex_exclusion_requires_verified_source_pid(monkeypatch, tmp_path):
    import pytest
    openalex_exclusion_fixture(monkeypatch, tmp_path)
    with pytest.raises(AssertionError, match='source-verified DBLP exclusion'):
        C.source_excluded_openalex_ids('cambridge', set())


def test_openalex_exclusion_cannot_borrow_another_dblp_orcid(monkeypatch, tmp_path):
    import pytest
    pid, _ = openalex_exclusion_fixture(monkeypatch, tmp_path, source_orcid='0000-0002-0000-0002')
    with pytest.raises(AssertionError, match='does not match its DBLP PID'):
        C.source_excluded_openalex_ids('cambridge', {pid})


def test_mixed_openalex_author_cannot_be_excluded_as_one_student(monkeypatch, tmp_path):
    import pytest
    pid, _ = openalex_exclusion_fixture(monkeypatch, tmp_path,
                                       author_orcids=('0000-0001-0000-0001', '0000-0002-0000-0002'))
    with pytest.raises(AssertionError, match='never a mixed identity'):
        C.source_excluded_openalex_ids('cambridge', {pid})


def test_openalex_exclusion_rejects_conflicting_author_name(monkeypatch, tmp_path):
    import pytest
    pid, _ = openalex_exclusion_fixture(monkeypatch, tmp_path, author_name='Unrelated Person')
    with pytest.raises(AssertionError, match='name conflicts'):
        C.source_excluded_openalex_ids('cambridge', {pid})


def test_dblp_only_exclusion_does_not_suppress_openalex_namesakes(monkeypatch, tmp_path):
    pid, _ = openalex_exclusion_fixture(monkeypatch, tmp_path, linked=False)
    assert C.source_excluded_openalex_ids('cambridge', {pid}) == set()


def test_candidate_filter_preserves_an_unbound_openalex_namesake(monkeypatch, tmp_path):
    import json
    pid, author = openalex_exclusion_fixture(monkeypatch, tmp_path)
    other = 'https://openalex.org/A200'
    oa = [dict(author=a, name='Avery Scientist', names=['Avery Scientist'], works=10, dblp_works=8,
               cs_share=0.8, years=[2020, 2026]) for a in (author, other)]
    (tmp_path / 'cs-related-candidates-openalex.json').write_text(json.dumps(oa))
    (tmp_path / 'census-faculty.json').write_text(json.dumps({'faculty': []}))
    monkeypatch.setattr(C, 'source_exclusions', lambda key: {pid})
    monkeypatch.setattr(C.P, 'data_w', lambda filename, key=None: tmp_path / filename)
    monkeypatch.setattr(C.S, 'get', lambda key: {})
    C.candidates('cambridge')
    rows = json.loads((tmp_path / 'cs-related-candidates.json').read_text())
    assert len(rows) == 1
    assert rows[0]['openalex'] == [other]


def json_hand(body, quote, *, pointer=None, sha=None, capture_text=None):
    import hashlib
    import sqlite3
    import zlib
    db = sqlite3.connect(':memory:')
    db.execute('create table captures (sha256 text, text text)')
    db.execute('create table live (url text, sha256 text, raw_zlib blob)')
    sha = sha or hashlib.sha256(body).hexdigest()
    url = 'https://school.example/career.json'
    db.execute('insert into live values (?,?,?)', (url, sha, zlib.compress(body)))
    if capture_text:
        db.execute('insert into captures values (?,?)', (sha, capture_text))
    entry = dict(name='Avery Scientist', unit='CS', url=url, sha256=sha,
                 quote=quote, observed='20261116')
    if pointer is not None:
        entry['json_pointer'] = pointer
    return C.hand_evidence('example', db, entries=[entry])


def test_hand_json_uses_literal_decoded_values():
    result = json_hand(b'{"role":"Assistant Professor","bio":"Studies caf\\u00e9 networks"}',
                       'Studies café networks', pointer='/bio')
    assert result['avery scientist'][0]['json_pointer'] == '/bio'
    assert json_hand(b'{"role":"Assistant Professor"}', 'Assistant Professor')


def test_hand_json_does_not_join_fields_or_trust_projected_capture():
    import pytest
    with pytest.raises(SystemExit, match='the quote'):
        json_hand(b'{"name":"Avery Scientist","role":"Assistant Professor"}',
                  'Avery Scientist Assistant Professor',
                  capture_text='Avery Scientist Assistant Professor')


def test_hand_json_pointer_binds_quote_to_one_record():
    import pytest
    body = b'{"roles":[{"school":"Elsewhere","role":"Professor"},{"school":"Harvard","role":"Student"}]}'
    assert json_hand(body, 'Professor', pointer='/roles/0/role')
    for pointer in ('/roles/1/role', '/roles/2', '/roles/01', '/roles/~2', 'roles'):
        with pytest.raises(SystemExit, match='the quote|invalid JSON pointer'):
            json_hand(body, 'Professor', pointer=pointer)
    assert C.json_pointer({'a/b': {'~key': 'value'}}, '/a~1b/~0key') == 'value'


def test_hand_json_rejects_malformed_bytes_and_wrong_hash():
    import pytest
    with pytest.raises(SystemExit, match='invalid saved JSON'):
        json_hand(b'{"role":"Professor",}', 'Professor')
    with pytest.raises(SystemExit, match='source hash mismatch'):
        json_hand(b'{"role":"Professor"}', 'Professor', sha='0' * 64)


def official_profile_review(monkeypatch, tmp_path, identity):
    import hashlib
    import json
    import sqlite3
    import zlib

    name = 'Avery Scientist'
    html = b'<h1>Avery Scientist</h1><p>Assistant Professor</p>'
    sha = hashlib.sha256(html).hexdigest()
    db = sqlite3.connect(':memory:')
    db.execute('create table captures (sha256 text, text text)')
    db.execute('create table live (url text, sha256 text, raw_zlib blob)')
    db.execute('insert into live values (?,?,?)', ('https://school.example/avery', sha, zlib.compress(html)))
    files = {
        'cs-related-candidates.json': [dict(name=name, aliases=[], source='official_profile_ladder')],
        # A busy namesake must not supply computing evidence to the faculty card.
        'dblp-affiliated.json': {'persons': [dict(pid='https://dblp.org/pid/namesake', n_window=900,
                                                affiliations=[{'text': 'University of Cambridge'}])]},
        'dblp-ids.json': {name: identity},
        'census-faculty.json': {'faculty': []},
        'cs-related-hand.json': [dict(name=name, unit='CS', url='https://school.example/avery', sha256=sha,
                                      quote='Avery Scientist Assistant Professor', observed='20261115', ladder=True)],
    }
    for filename, obj in files.items():
        (tmp_path / filename).write_text(json.dumps(obj))
    monkeypatch.setattr(C.P, 'data', lambda filename, key=None: tmp_path / filename)
    monkeypatch.setattr(C.P, 'data_w', lambda filename, key=None: tmp_path / filename)
    monkeypatch.setattr(C.S, 'get', lambda key: {'cs_related': {}, 'census': {}})
    monkeypatch.setattr(C, 'units_current', lambda key: True)
    monkeypatch.setattr(C, 'unit_pages', lambda key: [])
    monkeypatch.setattr(C.W, 'con', lambda key: db)
    monkeypatch.setattr(C, 'oa_stats', lambda key: {})
    C.review('cambridge')
    return (json.loads((tmp_path / 'cs-related-review.json').read_text())['decisions'][0],
            json.loads((tmp_path / 'census-additions.json').read_text()))


def test_official_ladder_profile_uses_evidenced_owned_dblp_person(monkeypatch, tmp_path):
    pid = 'https://dblp.org/pid/owned'
    decision, additions = official_profile_review(monkeypatch, tmp_path, dict(
        pid=pid, basis='homepage_url', n_window=73, url=pid, dump='pinned.xml.gz', sha256='a' * 64,
        quote='<url>https://school.example/avery</url>'))
    assert decision['decision'] == 'accepted'
    assert decision['cs_basis']['dblp'] == [pid]
    assert decision['cs_basis']['dblp_window'] == 73
    assert additions[0]['dblp'] == [pid]


def test_official_profile_does_not_borrow_undecided_namesake_count(monkeypatch, tmp_path):
    decision, additions = official_profile_review(monkeypatch, tmp_path, dict(
        candidates=2, candidates_max_window=900))
    assert decision['decision'] == 'faculty_not_computing'
    assert decision['cs_basis']['dblp'] == []
    assert additions == []


def test_official_profile_rejects_unevidenced_pid(monkeypatch, tmp_path):
    decision, additions = official_profile_review(monkeypatch, tmp_path, dict(
        pid='https://dblp.org/pid/guessed', basis='homepage_url', n_window=900))
    assert decision['decision'] == 'faculty_not_computing'
    assert additions == []


def test_official_profile_keeps_existing_minimum_computing_output(monkeypatch, tmp_path):
    pid = 'https://dblp.org/pid/owned'
    decision, additions = official_profile_review(monkeypatch, tmp_path, dict(
        pid=pid, basis='homepage_url', n_window=C.MIN_DBLP - 1, url=pid, dump='pinned.xml.gz',
        sha256='a' * 64, quote='<url>https://school.example/avery</url>'))
    assert decision['decision'] == 'faculty_not_computing'
    assert decision['cs_basis']['dblp'] == [pid]
    assert additions == []


def test_historical_month_cannot_be_changed_from_the_literal_source_date(monkeypatch, tmp_path):
    import pytest
    with pytest.raises(SystemExit, match='bounds are absent from its source quote'):
        research_review(monkeypatch, tmp_path,
            historical={'start': '2016-02', 'end': '2018-09', 'start_quote': '01/2016', 'end_quote': '09/2018'},
            period_text='01/2016 - 09/2018 Research Associate at University of Cambridge.')


def test_historical_month_rejects_invalid_calendar_month(monkeypatch, tmp_path):
    import pytest
    with pytest.raises(SystemExit, match='invalid start date'):
        research_review(monkeypatch, tmp_path,
            historical={'start': '2016-13', 'end': '2018-09'})


def test_historical_month_cannot_end_after_the_observation_month(monkeypatch, tmp_path):
    import pytest
    with pytest.raises(SystemExit, match='cannot end after its source observation'):
        research_review(monkeypatch, tmp_path,
            historical={'start': '2016-01', 'end': '2026-12'})
