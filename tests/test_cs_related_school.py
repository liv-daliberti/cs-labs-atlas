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
                    historical=None, period_review='matching'):
    import hashlib
    import json
    import sqlite3
    import zlib

    name = 'Avery Scientist'
    url = 'https://school.example/avery'
    title = 'Professor' if rank == 'ladder' else ('Research Professor' if rank == 'research' else 'Teaching Professor')
    period_text = '2010-2021: Professor at University of Cambridge.'
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
    periods = [dict(start='2010', end='2021', datePrecision='year', evidence=[dict(url=url, sha256=sha, quote=role['quote'])])]
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


def test_historical_ladder_review_cannot_replace_research_pi_group_evidence(monkeypatch, tmp_path):
    import pytest
    with pytest.raises(SystemExit, match='cannot supply a research/teaching PI basis'):
        research_review(monkeypatch, tmp_path, own=False, historical={'start': '2010', 'end': '2021'})


def test_current_professor_profile_still_proves_its_observation_year(monkeypatch, tmp_path):
    decision, additions = research_review(monkeypatch, tmp_path, own=False, rank='ladder')
    assert decision['years_listed'] == additions[0]['years_listed'] == [2026]


def test_historical_computing_identity_uses_appointment_start_not_biography_date(monkeypatch, tmp_path):
    decision, additions = research_review(monkeypatch, tmp_path, own=False, rank='ladder', source='openalex_rule',
                                         historical={'start': '2010', 'end': '2021'}, share_result='computing')
    assert decision['decision'] == 'accepted'
    assert decision['cs_basis']['openalex_share']['first_listing_year'] == 2010
    assert additions[0]['years_listed'] == []
