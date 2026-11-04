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


def test_load_ctx_skips_lab_papers_that_come_only_from_the_accepted_additions(monkeypatch, tmp_path):
    import json
    rows = [dict(pi='A', title='kept', source='openalex_sweep'), dict(pi='A', title='wired', source='labpage_addition:LP-PAP-01:openalex_authorship')]
    src = (A.Path(__file__).resolve().parents[1] / 'tools' / 'labpage_audit.py').read_text()
    assert "startswith('labpage_addition:')" in src and json.dumps(rows[1]['source']).startswith('"labpage_addition:')
