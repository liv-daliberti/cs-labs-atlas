"""Exact venue-date repairs cannot admit papers or lend authorship/appointments."""
import copy
import hashlib
import json
from collections import Counter
from types import SimpleNamespace

import pytest

import atlas_paths as P
from pihier import retained_dates as D


def setup(tmp_path, monkeypatch):
    store = tmp_path / 'store'
    monkeypatch.setattr(P, 'store', lambda school: store)
    work = dict(id='https://openalex.org/W1', doi='https://doi.org/10.1234/example', title='A conference study',
                publication_year=2024, publication_date='2024-02-01', type='conference-paper',
                authorships=[dict(raw_author_name='Ada Example'), dict(raw_author_name='Ben Researcher')])
    row = dict(pi='Ada Example', oa=work['id'], doi='10.1234/example', title=work['title'], year=2024,
               date=work['publication_date'], type=work['type'], byline=['Ada Example', 'Ben Researcher'],
               identity='pi_orcid', appointment=dict(listing=2024), authorship={'raw_name': 'Ada Example'}, editions=[])
    message = dict(DOI=row['doi'], type='proceedings-article', title=[row['title']],
                   **{'container-title': ['2022 Example Conference Proceedings']},
                   event=dict(start={'date-parts': [[2022, 6, 26]]}, end={'date-parts': [[2022, 6, 29]]}),
                   issued={'date-parts': [[None]]}, created={'date-parts': [[2024, 2, 1]]},
                   author=[dict(given='Ada', family='Example', affiliation=[{'name': 'University of Illinois at Urbana-Champaign'}]),
                           dict(given='Ben', family='Researcher', affiliation=[])])
    review = dict(id='date-example', pi=row['pi'], decision='confirmed_conference_year',
                  match=dict(oa=work['id'], doi=row['doi']), changes={'year': 2022}, reviewed_by='worker',
                  independent_reviewer='independent-reviewer', reviewed_at='2026-11-24', why='Exact publisher venue edition',
                  source=dict(work_sha256=D.digest(work), original_title=work['title'], original_year=2024,
                              original_date=work['publication_date'], ordered_byline=row['byline']), publisher={})
    ctx = SimpleNamespace(school='uiuc', here=tmp_path, rows=[row], hits=[(row['pi'], work)], n=Counter(),
                          pid0={row['pi']: dict(pi=row['pi'], names=[row['pi']], periods=[],
                                               listings=[{'year': 2022}, {'year': 2024}])})

    def save():
        raw = json.dumps({'status': 'ok', 'message-type': 'work', 'message': message}).encode()
        sha = hashlib.sha256(raw).hexdigest()
        target = store / 'metadata/test' / (sha + '.json'); target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        review['publisher'].update(url='https://api.crossref.org/works/10.1234%2Fexample', http_status=200,
                                   captured='2026-11-24T12:00:00+00:00', format='json', sha256=sha,
                                   source_file=str(target.relative_to(store)), container_title=message['container-title'][0],
                                   ordered_byline=[' '.join([a['given'], a['family']]) for a in message['author']])
        P.data_w('paper-claim-review.json', ctx.school, root=tmp_path).write_text(json.dumps(
            dict(version=1, school=ctx.school, decisions=[], conference_dates=[review])))
        return target
    save()
    return ctx, work, row, message, review, save


@pytest.mark.usefixtures('layout')
def test_exact_publisher_venue_year_preserves_identifiers_bylines_and_originals(tmp_path, monkeypatch):
    ctx, work, row, _, _, _ = setup(tmp_path, monkeypatch)
    original = copy.deepcopy((work, row))
    D.apply(ctx)
    result = ctx.rows[0]
    assert result['year'] == 2022 and result['date'] == '2022'
    assert result['appointment'] == {'listing': 2022}
    assert {k: v for k, v in result.items() if k not in {'year', 'date', 'appointment', 'retainedDateReviews'}} == {
        k: v for k, v in row.items() if k not in {'year', 'date', 'appointment'}}
    assert (work, row) == original
    assert ctx.retained_date_review['decisions'][0]['original_complete_source'] == work
    assert ctx.retained_date_review['decisions'][0]['original_eligible_row'] == row


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('fault', ['missing_row', 'source_changed', 'source_hash', 'publisher_bytes', 'publisher_doi',
                                  'publisher_title', 'same_reviewer', 'ambiguous_container', 'event_year', 'explicit_publication', 'wrong_school', 'missing_pi',
                                  'byline', 'outside_appointment', 'editions', 'competing_date', 'unverified', 'path'])
def test_failed_proof_stops_without_changing_any_native_row(tmp_path, monkeypatch, fault):
    ctx, work, row, message, review, save = setup(tmp_path, monkeypatch)
    if fault == 'missing_row': ctx.rows = []
    elif fault == 'source_changed': work['publication_date'] = '2024-03-01'
    elif fault == 'source_hash': review['source']['work_sha256'] = '0' * 64
    elif fault == 'publisher_doi': message['DOI'] = '10.1234/unrelated'
    elif fault == 'publisher_title': message['title'] = ['An unrelated publication']
    elif fault == 'same_reviewer': review['independent_reviewer'] = review['reviewed_by']
    elif fault == 'ambiguous_container': message['container-title'] = ['2022-2024 Example Conference Proceedings']
    elif fault == 'event_year': message['event']['end']['date-parts'] = [[2023, 6, 29]]
    elif fault == 'explicit_publication': message['published'] = {'date-parts': [[2024, 2, 1]]}
    elif fault == 'wrong_school': message['author'][0]['affiliation'] = [{'name': 'Another University'}]
    elif fault == 'missing_pi': message['author'][0]['given'] = 'Different'
    elif fault == 'byline': row['byline'] = ['Ada Example']
    elif fault == 'outside_appointment': ctx.pid0[row['pi']]['listings'] = [{'year': 2024}]
    elif fault == 'editions': row['editions'] = [{'oa': 'another-work'}]
    elif fault == 'competing_date': row['dated_by'] = {'venue_year': 2023}
    elif fault == 'unverified': row['identity'] = 'unverified'
    target = save()
    if fault == 'publisher_bytes': target.write_bytes(b'changed')
    if fault == 'path':
        review['publisher']['source_file'] = '../outside.json'
        P.data_w('paper-claim-review.json', ctx.school, root=tmp_path).write_text(json.dumps(
            dict(version=1, school=ctx.school, decisions=[], conference_dates=[review])))
    before = copy.deepcopy(ctx.rows)
    with pytest.raises(ValueError): D.apply(ctx)
    assert ctx.rows == before


@pytest.mark.usefixtures('layout')
def test_missing_review_never_admits_a_work_or_changes_legacy_rows(tmp_path, monkeypatch):
    ctx, _, row, _, _, _ = setup(tmp_path, monkeypatch)
    P.data_w('paper-claim-review.json', ctx.school, root=tmp_path).write_text(json.dumps(
        dict(version=1, school=ctx.school, decisions=[])))
    before = copy.deepcopy(row)
    D.apply(ctx)
    assert ctx.rows == [before]
    assert not hasattr(ctx, 'retained_date_review')
