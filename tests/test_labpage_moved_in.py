"""Round 1 at Georgia Tech: undated alumni of a PI who arrived inside the window are the previous institution's students."""
import labpage_audit as A


def test_moved_in_alumnus_rule():
    assert A.moved_in_alumnus(2020, None, False, True)          # '(Current: Faculty at Michigan)' on a 2020 arrival's page
    assert A.moved_in_alumnus(2020, None, True, False)           # an undated alumnus
    assert not A.moved_in_alumnus(2020, [2021, None], True, True)  # dated: the year decides
    assert not A.moved_in_alumnus(None, None, True, True)         # a PI whose first listing is the window floor (long at the school): the older-lab rule handles it
    assert not A.moved_in_alumnus(2020, None, False, False)       # a plain undated current member


def test_news_lines_and_kinship_lists_are_not_rosters():
    assert A.news_item('Patrick Kastner and I just received a small seed grant! August 2025: I am honored') and A.news_item('Sept. 2024 - Hamza won an award')
    assert not A.news_item('Ph.D. Students Zihao He (2024 - ), co-advised with Souvik Dhara')
    import importlib.util
    from pathlib import Path
    f = Path(__file__).resolve().parents[1].joinpath('hier' + 'archy', 'labpage-tools-princeton-mit', 'autom.py')   # route-ok: tracked toolkit code
    spec = importlib.util.spec_from_file_location('autom_kin', f)
    src = f.read_text()
    rx = next(l for l in src.splitlines() if l.startswith('HARD_EXCL_HEAD'))
    assert 'siblings?' in rx and 'lineage' in rx and 'progeny' not in rx and spec


def test_bylines_and_current_position_lists():
    assert A.byline_item('Zecheng Zhang,') and A.byline_item(' Ann Lee Smith, ') and not A.byline_item('Zihao He (2024 - ), co-advised with Souvik Dhara')
    assert A.current_position_list('Current Position') and not A.current_position_list('Current Members')


def test_other_institution_and_cv_lines():
    assert A.other_institution_entry('M.S. student, ECE@Rice University, Sept. 2017 - Sept. 2019, Next Move: Ph.D. student, CS@UCSB', '', 'gatech')
    assert not A.other_institution_entry('Ph.D., CS@Georgia Tech, Aug. 2020 - May 2025, Next Move: Research Scientist@NVIDIA', '', 'gatech')
    assert A.talk_item('Invited Talk NeurIPS-ViGIL', 'x') and A.talk_item('Outreach', 'x') and not A.talk_item('Current Students', 'x')
    assert not A.talk_item('Ph.D. Students', 'x')


def test_wired_additions_do_not_count_as_in_the_build():
    """R13: re-running the audit after the accepted students were wired must propose them again, not see them as already in the build."""
    rec = lambda name, shas: dict(name=name, relations=[dict(sources=[dict(sha256=s) for s in shas])])
    students = {'Ann PI': [rec('Wired One', ['a1']), rec('Wired Two', ['a1']), rec('Roster Too', ['a1', 'r9']), rec('Roster Only', ['r9'])], 'Bo PI': [rec('Other Lab', ['a1'])]}
    wired = [dict(pi='Ann PI', name='Wired One', sha256='a1'), dict(pi='Ann PI', name='Wired Two', sha256='a1')]
    out = A.without_wired_additions(students, 'k', wired=wired)
    assert [r['name'] for r in out['Ann PI']] == ['Roster Too', 'Roster Only'] and [r['name'] for r in out['Bo PI']] == ['Other Lab']
    assert A.without_wired_additions(students, 'k', wired=[]) == students   # nothing accepted: the build is compared as it is


def test_wired_manual_rows_stay_in_the_build_the_audit_compares_against():
    """JHU 2026-11-25: preserve_manual_members re-emits accepted manual rows itself; hiding their build record let the automatic
    re-reading of the same person resurface as a conflict. Only automatic wired rows are hidden (R13)."""
    rec = lambda name, shas, **kw: dict(name=name, relations=[dict(sources=[dict(sha256=s) for s in shas])], **kw)
    students = {'Ann PI': [rec('Auto Wired', ['a1']), rec('Manual Wired', ['a1']), rec('Alias Person', ['a1'], aliases=['Manual Alias'])]}
    wired = [dict(pi='Ann PI', name='Auto Wired', sha256='a1'), dict(pi='Ann PI', name='Manual Wired', sha256='a1', auto=False),
             dict(pi='Ann PI', name='Manual Alias', sha256='a1', auto=False), dict(pi='Bo PI', name='Auto Wired', sha256='a1', auto=False)]
    out = A.without_wired_additions(students, 'k', wired=wired)
    assert [r['name'] for r in out['Ann PI']] == ['Manual Wired', 'Alias Person']

def test_wired_paper_rows_are_recognised():
    assert A.wired_paper_row(dict(source='labpage_addition:LP-PAP-01:openalex_authorship'))
    assert not A.wired_paper_row(dict(source='openalex_sweep')) and not A.wired_paper_row({})
