"""A page that prints one person twice (byte-identical rows in one capture) is one observation; different people are never merged."""
import cjk_name_review as R


def row(name, cap, prof=None, quote='q', year=2023, sha='h', dept='d'):
    return dict(name=name, name_listed=name, capture_url=cap, sha256=sha, profile=prof, quote=quote, year=year, observed=f'{year}0101', dept=dept)


def test_identical_rows_collapse_to_one():
    a = row('何炎祥', 'u1')
    assert R.dedupe([a, dict(a), row('何炎祥', 'u2')]) == [a, row('何炎祥', 'u2')]


def test_duplicate_row_does_not_force_a_split():
    rs = [row('何炎祥', 'u1', 'http://x/1'), row('何炎祥', 'u1', 'http://x/1'), row('何炎祥', 'u2', None, year=2024)]
    groups, _ = R.clusters('何炎祥', rs, {'d': {2023, 2024}})
    assert [(g[0], g[2], len(g[1])) for g in groups] == [('何炎祥', False, 2)]


def test_different_rows_in_one_capture_still_split():
    rs = [row('王伟', 'u1', 'http://x/1', quote='a'), row('王伟', 'u1', 'http://x/2', quote='b')]
    groups, _ = R.clusters('王伟', rs, {'d': {2023}})
    assert len(groups) == 2 and all(g[2] for g in groups)


def test_identity_collision_rows_expand_per_source_id(tmp_path, monkeypatch):
    import excluded_audit as EA
    doc = dict(decisions=[dict(name='Bin Li', decision='pending_identity_collision', reason='r', units_searched=['U'],
                               candidate_sources=[dict(source='dblp_affiliation', dblp='d1', openalex=None), dict(source='openalex_rule', dblp=None, openalex=['W1'])])])
    p = tmp_path / 'r.json'
    p.write_text(__import__('json').dumps(doc))
    monkeypatch.setattr(EA, 'review_path', lambda k: p)
    EA.convert('x')
    out = __import__('json').loads(p.read_text())['decisions']
    assert sorted(d['source_id'] for d in out) == ['W1', 'd1'] and all(d['decision'] == 'excluded_unresolved' and d['reason_code'] == 'identity_collision' for d in out)
