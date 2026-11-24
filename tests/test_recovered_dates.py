"""Exact publication dates cannot bypass a partial-year appointment boundary."""
import hashlib
import json

import pytest

from pihier import recovered_dates
from test_build_rules import SCHOOL, OVERRIDES, put, rows_of, run_stages, write_additions, write_school

pytestmark = pytest.mark.usefixtures('layout')


def install(root, change=None, existing=False):
    if not existing:
        write_school(root)
    write_additions(root, paper_years=(2021,))
    path = put(root, 'labpage-additions.json')
    data = json.loads(path.read_text())
    row = data['papers'][0]
    row['date'] = '2021-05-23'
    work = dict(DOI=row['doi'], title=[row['title']], **{'published-online': {'date-parts': [[2021, 5, 23]]}})
    source = dict(url='https://api.crossref.org/works/' + row['doi'], http_status=200,
                  captured='2026-11-24T20:34:42+00:00', reviewed_by=['independent-reviewer'], date_field='published-online')
    row['evidence']['publication_date_source'] = source
    if change:
        change(row, work, source)
    raw = json.dumps(dict(status='ok', **{'message-type': 'work'}, message=work)).encode()
    source['sha256'] = hashlib.sha256(raw).hexdigest()
    source['source_file'] = source['sha256'] + '.json'
    capture = path.parent / 'publication-date-sources' / source['source_file']
    capture.parent.mkdir(exist_ok=True)
    capture.write_bytes(raw)
    path.write_text(json.dumps(data))
    acceptance = put(root, 'labpage-acceptance.json')
    accepted = json.loads(acceptance.read_text())
    accepted['additions_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    acceptance.write_text(json.dumps(accepted))
    return row, capture


def test_verified_date_resolves_partial_year_without_expanding_period(tmp_path, monkeypatch):
    from copy import deepcopy
    import test_build_rules as fixture
    overrides = deepcopy(OVERRIDES)
    overrides[SCHOOL]['Ada Lovelace']['periods'] = [dict(id='reviewed:ada:date', start='2015', end='2021-06', evidence=[
        dict(url='https://example.edu/cv', sha256='a' * 64, quote='Ada Lovelace moved in June 2021.', kind='faculty_end_moved')])]
    monkeypatch.setattr(fixture, 'OVERRIDES', overrides)
    write_school(tmp_path)
    write_additions(tmp_path)
    assert 'A Paper Only The Lab Page Lists' not in rows_of(run_stages(tmp_path), 'Ada Lovelace')
    install(tmp_path, existing=True)
    row = rows_of(run_stages(tmp_path), 'Ada Lovelace')['A Paper Only The Lab Page Lists']
    assert row['date'] == '2021-05-23'
    assert row['appointment']['periodId'] == 'reviewed:ada:date'


@pytest.mark.parametrize('failure', ['doi', 'title', 'year', 'date', 'field', 'status', 'bytes', 'missing'])
def test_invalid_exact_date_proof_holds_the_paper(tmp_path, failure):
    def change(row, work, source):
        if failure == 'doi': work['DOI'] = '10.9/some-other-paper'
        if failure == 'title': work['title'] = ['Another work']
        if failure == 'year': row['year'] = 2020
        if failure == 'date': row['date'] = '2021-05-24'
        if failure == 'field': source['date_field'] = 'created'
        if failure == 'status': source['http_status'] = 403
    _, capture = install(tmp_path, change)
    if failure == 'bytes': capture.write_bytes(capture.read_bytes() + b' ')
    if failure == 'missing': capture.unlink()
    ctx = run_stages(tmp_path)
    assert 'A Paper Only The Lab Page Lists' not in rows_of(ctx, 'Ada Lovelace')
    assert ctx.n['labpage_addition_recovered_invalid_publication_date_proof'] == 1
    assert ctx.labpage_set_aside[0]['reason'] == 'invalid_publication_date_proof'


def test_undeclared_precision_stays_whole_year():
    row = dict(year=2021, date='2021-05-23', evidence={})
    assert recovered_dates.publication_date(None, row, 'labpage_addition') == '2021'
