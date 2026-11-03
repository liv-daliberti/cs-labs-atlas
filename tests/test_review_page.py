"""ROADMAP #36: the review page is static and local, draws the rounds' own samples, and exports what the recording tools read."""
import importlib.util
import io
import json
import random
import re
from pathlib import Path

import pytest

import review_page as R

CODE = Path(__file__).resolve().parents[1]
STUDENTS = [dict(name=f'S{i}', pi='P', role='phd', role_basis='entry', years=[2020, None], years_basis='stated_in_entry', alumni=False,
                 quote=f'q{i} <b>', url='https://example.edu/x', capture_url='https://web.archive.org/web/1id_/https://example.edu/x', sha256='0' * 64) for i in range(40)]


def test_labpage_sample_is_the_one_labpage_audit_draws():
    rs = R.labpage_set('u', 'students', 20, 3171, rows=STUDENTS)
    random.seed(3171)
    expect = random.sample(STUDENTS, 20)
    assert [r['heading'].split('  ')[0] for r in rs['rows']] == [x['name'] for x in expect]
    assert rs['rows'][0]['links'][0]['url'].startswith('https://web.archive.org/')


def test_page_is_self_contained_and_escapes_the_quote():
    rs = R.labpage_set('u', 'students', 5, 1, rows=STUDENTS)
    h = R.page(rs)
    assert '&lt;b&gt;' in h
    assert not re.search(r'<script[^>]+src=|<link[^>]+href=|@import|https?://[^"\s]+\.(js|css|woff)', h)
    srcs = re.findall(r'(?:src|href)="([^"]+)"', h)
    assert all(s.startswith('https://web.archive.org/') for s in srcs)       # only the capture links, followed on click
    assert 'rel="noopener noreferrer"' in h and h.count('id="c-') == 5 * 2     # two verdict boxes per student row
    assert json.loads(re.search(r'id="set">(.*?)</script>', h, re.S).group(1).replace('<\\/', '</'))['rows'][0]['id'] == '1'


def verdicts(kind, rows, **kw):
    return dict(format='review-verdicts/1', kind=kind, school='u', sample=kw.get('sample', 'students'), seed=7, verdicts=rows)


def test_export_applies_the_acceptance_bar_scaled_by_sample_size():
    rows = [dict(id=str(i), membership='ok', role_year='ok') for i in range(20)]
    assert R.labpage_spec(verdicts('labpage_students', rows), '3', 'x')['result'] == 'pass'
    rows[0].update(membership='error'); rows[1].update(membership='doubtful')            # 1.5 > 1
    s = R.labpage_spec(verdicts('labpage_students', rows), '3', 'x', date='2026-11-02')
    assert s['result'] == 'fail' and s['membership_score'] == 1.5 and s['students']['membership_errors'] == 1 and s['students']['doubtful_count'] == 1 and s['date'] == '2026-11-02'
    big = [dict(id=str(i), membership='ok', role_year='ok') for i in range(30)]
    big[0].update(membership='error'); big[1].update(membership='doubtful')              # 30 rows: the bar is 1.5
    assert R.labpage_spec(verdicts('labpage_students', big), '4', 'x')['result'] == 'pass'


def test_export_refuses_unjudged_rows():
    with pytest.raises(SystemExit):
        R.labpage_spec(verdicts('labpage_students', [dict(id='1', membership='ok')]), '1', 'x')


def test_papers_round_spec():
    rows = [dict(id='1', paper='error'), dict(id='2', paper='ok')]
    s = R.labpage_spec(verdicts('labpage_papers', rows, sample='papers'), '2', 'x')
    assert s['papers']['errors'] == 1 and s['paper_score'] == 1.0 and s['result'] == 'pass'


def test_accuracy_tsv_is_what_record_py_reads(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('acc_record', CODE / 'accuracy' / 'record.py')
    rec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rec)
    sample = {'schools': {'u': {'lab_precision': [dict(stratum='uniform', i=3, key='P|None|https://openalex.org/W1'), dict(stratum='listing', i=9, key='P|None|https://openalex.org/W2')]}}}
    (tmp_path / 's.json').write_text(json.dumps(sample))
    monkeypatch.setattr(rec, 'files', lambda school: (tmp_path / 's.json', tmp_path / 'v.jsonl'))
    v = verdicts('accuracy_precision', [dict(id='3', verdict='correct', note='ok'), dict(id='9', verdict='incorrect', failure_type='not_a_paper', note='a column')], sample='lab_precision')
    monkeypatch.setattr('sys.stdin', io.StringIO(R.accuracy_tsv(v)))
    rec.main('u', 'lab_precision')
    got = [json.loads(x) for x in (tmp_path / 'v.jsonl').read_text().splitlines()]
    assert [(g['row'], g['verdict'], g['failure_type']) for g in got] == [(3, 'correct', None), (9, 'incorrect', 'not_a_paper')]
    with pytest.raises(SystemExit):
        R.accuracy_tsv(verdicts('accuracy_precision', [dict(id='9', verdict='incorrect')], sample='lab_precision'))


def test_coverage_tsv_follows_truth_and_build():
    v = verdicts('accuracy_lab_coverage', [dict(id='P|k1', true_lab_paper='yes', in_build='no'), dict(id='P|k2', true_lab_paper='no', in_build='no')], sample='lab_coverage')
    a, b = [x.split('\t') for x in R.accuracy_tsv(v).splitlines()]
    assert a[1] == 'incorrect' and a[2] == 'missing_from_build' and json.loads(a[5]) == dict(true_lab_paper=True, in_build=False) and b[1] == 'correct'


def test_accuracy_sets_use_the_draw_row_index(tmp_path):
    lab = [dict(pi='P', title=f't{i}', year=2020, authorship={'raw_name': 'P', 'position': 'first'}, appointment={'listing': {'url': 'https://web.archive.org/x', 'quote': 'Prof P', 'year': 2020, 'kind': 'dept'}}, oa=f'https://openalex.org/W{i}') for i in range(5)]
    f = tmp_path / 'sample-u.json'
    f.write_text(json.dumps({'schools': {'u': {'lab_precision': [dict(stratum='uniform', i=4, key='P|None|W4')]}}}))
    rs = R.accuracy_sets('u', ('lab_precision',), sample_file=f, lab=lab)['lab_precision']
    assert rs['rows'][0]['id'] == '4' and rs['rows'][0]['heading'].startswith('t4') and rs['rows'][0]['quote'] == 'Prof P'
    assert [c['name'] for c in rs['optional']] == ['failure_type']


def test_serve_binds_only_the_loopback_interface():
    import inspect
    assert "('127.0.0.1', port)" in inspect.getsource(R.serve)
