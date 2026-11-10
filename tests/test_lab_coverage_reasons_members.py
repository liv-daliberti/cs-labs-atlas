"""A lab whose own page lists members never gets the generic 'No student of this PI in any allowed source' reason (Harvard Yiling Chen, 59 listed members)."""
import lab_coverage_reasons as R


def test_members_listed_counts_current_and_alumni():
    assert R.members_listed({'students': {'listed_current': ['a', 'b'], 'listed_alumni': ['c']}}) == 3


def test_members_listed_is_zero_without_a_students_section():
    assert R.members_listed({}) == 0 and R.members_listed(None) == 0 and R.members_listed({'students': {}}) == 0


def test_a_page_with_members_is_skipped_and_a_stale_generated_reason_removed(tmp_path, monkeypatch):
    import gzip
    import json
    rec = {'pi': 'Yiling Chen', 'lab_page': {'status': 'found'}, 'students': {'listed_current': ['x'] * 59, 'listed_alumni': []}}
    out = tmp_path / 'reasons.json'
    out.write_text(json.dumps({'Yiling Chen': {'students': {'code': 'sources_exhausted', 'why': 'No student of this PI'}}}))
    aud = tmp_path / 'audit.jsonl.gz'
    with gzip.open(aud, 'wt') as f:
        f.write(json.dumps(rec) + '\n')

    class P:
        @staticmethod
        def data(name, key=None, **kw):
            return aud

        @staticmethod
        def data_w(name, key=None, **kw):
            return out
    monkeypatch.setattr(R, 'P', P)
    monkeypatch.setattr(R, 'school_sources', lambda key: [])
    monkeypatch.setattr(R, 'thesis_facts', lambda key: None)
    monkeypatch.setattr(R.LC, 'lab_rows', lambda key: [{'pi': 'Yiling Chen', 'title': 'Professor', 'students': [], 'reasons': {'students': {'code': 'open'}}}])
    R.main('harvard')
    assert 'students' not in json.loads(out.read_text()).get('Yiling Chen', {})
