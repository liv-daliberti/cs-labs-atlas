"""tools/sweep_check.py: a synthetic sweep with a 20x year and a duplicated page must fail; exceptions need a reason."""
import json, sqlite3, sys, zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import sweep_check as SC  # noqa: E402

INST = 'I1'


def work(i, year, typ='article', doi=True):
    return {'id': f'https://openalex.org/W{i}', 'doi': f'https://doi.org/10.1/{i}' if doi else None, 'publication_year': year, 'type': typ,
            'authorships': [{'institutions': [{'id': 'https://openalex.org/' + INST, 'lineage': ['https://openalex.org/' + INST]}]}]}


def sweep(path, per_year, dup_page=False, blow=None, blow_type='article'):
    c = sqlite3.connect(path)
    c.execute('create table pages (year int, page int, cursor text, next_cursor text, n int, count int, fetched_at text, body blob, primary key (year, page))')
    i = 0
    for y in range(2016, 2027):
        n = per_year * (20 if y == blow else 1)
        ws = []
        for _ in range(n):
            i += 1
            ws.append(work(i, y, blow_type if (y == blow and len(ws) >= per_year) else 'article'))
        c.execute('insert into pages values (?,?,?,?,?,?,?,?)', (y, 0, '*', None, len(ws), len(ws) + (len(ws[:50]) if dup_page and y == 2018 else 0), '', zlib.compress(json.dumps(ws).encode())))
        if dup_page and y == 2018:  # the first 50 works stored again under a second page
            c.execute('insert into pages values (?,?,?,?,?,?,?,?)', (y, 1, 'x', None, 50, len(ws) + 50, '', zlib.compress(json.dumps(ws[:50]).encode())))
    c.commit(); c.close()


def trip_set(r):
    return {(t['test'], t.get('year')) for t in r['trips']}


def test_clean_sweep_passes(tmp_path):
    p = tmp_path / 's.sqlite'; sweep(p, 100)
    r = SC.check_openalex(p, {INST}, [INST], 2026)
    assert r['trips'] == [] and r['dup_id_rate'] == 0 and r['inst_share'] == 1.0


def test_20x_year_and_duplicated_page_fail(tmp_path):
    p = tmp_path / 's.sqlite'; sweep(p, 100, dup_page=True, blow=2022)
    r = SC.check_openalex(p, {INST}, [INST], 2026)
    t = trip_set(r)
    assert ('year_outlier', 2022) in t
    assert ('duplicate_ids', None) in t
    assert r['dup_id_rate'] > 0


def test_exception_needs_reason_and_verified_cause(tmp_path):
    p = tmp_path / 's.sqlite'; sweep(p, 100, blow=2022, blow_type='dataset')
    r = SC.check_openalex(p, {INST}, [INST], 2026)
    trip = next(t for t in r['trips'] if t['test'] == 'year_outlier')
    assert trip['papers_outlier'] is False  # the excess is datasets
    failed, excused = SC.apply_exceptions(r['trips'], [{'test': 'year_outlier', 'year': 2022}])  # no reason: not an exception
    assert failed and not excused
    failed, excused = SC.apply_exceptions(r['trips'], [{'test': 'year_outlier', 'year': 2022, 'reason': 'datasets', 'verify': 'papers_normal'}])
    assert not failed and excused
    p2 = tmp_path / 's2.sqlite'; sweep(p2, 100, blow=2022)  # the excess is papers: the same exception does not hold
    r2 = SC.check_openalex(p2, {INST}, [INST], 2026)
    failed, _ = SC.apply_exceptions(r2['trips'], [{'test': 'year_outlier', 'year': 2022, 'reason': 'datasets', 'verify': 'papers_normal'}])
    assert failed


def test_wrong_institution_fails(tmp_path):
    p = tmp_path / 's.sqlite'; sweep(p, 100)
    r = SC.check_openalex(p, {'I2'}, ['I2'], 2026)
    assert ('institutions', None) in trip_set(r)


def test_partial_current_year_is_not_low_outlier():
    assert SC.outliers({y: 1000 for y in range(2016, 2026)} | {2026: 200}, 2026) == {}
    assert 2020 in SC.outliers({y: 1000 for y in range(2016, 2027)} | {2020: 200}, 2026)


def test_not_papers_matches_builder():
    import pi_hierarchy
    assert SC.NOT_PAPERS == pi_hierarchy.NOT_PAPERS
