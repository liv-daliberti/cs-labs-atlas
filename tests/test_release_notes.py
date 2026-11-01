"""tools/release_notes.py: CHANGES.md from a build-regression result, deterministic, with rules and no clock."""
import release_notes as RN

REG = dict(
    before=dict(at='2026-10-30T00:00:00Z', source='x', code=None), after=dict(at='2026-10-31T00:00:00Z', source='x', code=None),
    flags=[dict(school='mit', kind='school_rows', count='lab_papers', before=100, after=80)],
    schools={'mit': dict(rows={k: dict(before=10, after=12) for k in ('lab_papers', 'student_papers', 'lab_student_pairs', 'pis')},
                         identical=dict(pis=True, lab_papers=False), report={'students': dict(before=5, after=4)},
                         pis_changed=[dict(pi='Ada', before=3, after=1)], ledger={'no_oa': dict(before=2, after=3)}),
             'cmu': dict(rows={k: dict(before=7, after=7) for k in ('lab_papers', 'student_papers', 'lab_student_pairs', 'pis')},
                         identical=dict(pis=True, lab_papers=True), report={}, pis_changed=[], ledger={})})


def test_render_is_deterministic_and_complete():
    t = RN.render(REG, '2026-10-31.1', '2026-10-29.4', [dict(id='R-A-01', decided='x'), dict(id='R-B-02', decided='2026-10-31')], [dict(id='R-A-01', decided='x'), dict(id='R-C-03', decided='y')])
    assert t == RN.render(REG, '2026-10-31.1', '2026-10-29.4', [dict(id='R-A-01', decided='x'), dict(id='R-B-02', decided='2026-10-31')], [dict(id='R-A-01', decided='x'), dict(id='R-C-03', decided='y')])
    assert t.startswith('# Changes in release 2026-10-31.1') and 'previous release 2026-10-29.4' in t
    assert 'Regression flags: 1 (the release was allowed anyway)' in t and 'school: mit' in t
    assert '| mit | 10 → 12 (+2)' in t and 'Unchanged schools (every row set identical): cmu.' in t
    assert 'students 5 → 4' in t and 'Ada 3 → 1' in t and 'no_oa 2 → 3' in t and '1 PI has a different' in t
    assert 'Added: R-B-02 (2026-10-31).' in t and 'Removed: R-C-03.' in t
