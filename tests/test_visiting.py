"""R-STU-17 (2026-11-04, owner): the `visiting` student role (tools/visiting.py, labpage_audit entry_role, student-decisions, conversion)."""
import pytest

import labpage_audit as L
import student_decisions as SD
import visiting as V
import visiting_roles as VR

NO_ROLE = lambda s: (None, None)


def role_of(s):
    """A stand-in for autom._role: the few words the cases below need."""
    import re
    for r, rx in (('postdoc', r'post-?doc'), ('undergraduate', r'undergrad'), ('masters', r"master"), ('phd', r'ph\.?\s?d|graduate'), ('other', r'scientist|visit|staff|professor')):
        if re.search(rx, s or '', re.I):
            return r, None
    return None, None


@pytest.mark.parametrize('text', ['visiting student from CUHK', '(visiting, CUHK)', 'Visiting Ph.D. from Tsinghua', 'Visiting Undergraduate from Tsinghua',
                                  'visiting student researcher (ETH Zurich)', '(visiting senior thesis student, University of Oxford)', 'visiting Applied Math PhD student, Yale',
                                  'Visitors (students)', 'Visiting Students', 'Other student visitors', 'former visiting graduate student (TU Darmstadt)'])
def test_R_STU_17_visiting_student_wording(text):
    assert V.says_visiting(text)


@pytest.mark.parametrize('text', ['visiting professor', 'Visiting Scholar, Stanford', 'visiting scientist, PhD', '(visiting postdoc', 'visiting researcher from ETH',
                                  'Visitors', 'Visiting Students, Scholars and Scientists', 'Visiting faculty and graduate students', 'a visit to the lab'])
def test_R_STU_17_professors_scholars_and_bare_visitors_are_not_visiting_students(text):
    assert not V.says_visiting(text)


def test_R_STU_17_entry_role_is_visiting_in_the_entry_or_under_a_visiting_heading():
    f = lambda d, h=None: L.entry_role(d, h, role_of)
    assert f(' — CS, BS 2026, visiting student from CUHK → PhD program at UChicago', "Alumni — undergraduate & master's") == ('visiting', 'entry')
    assert f('(visiting, CUHK)', 'PhD students') == ('visiting', 'entry')
    assert f('', 'Visiting Students') == ('visiting', 'section_heading')
    assert f('(PhD student at ETH)', 'Alumni > Visiting Students') == ('visiting', 'section_heading')
    # not visiting: a postdoc / staff / scientist title under the heading, a mixed heading, an earlier stay, faculty
    assert f('Visiting Scientist, MIT', 'Visiting Students')[0] != 'visiting'
    assert f('', 'Undergraduate and Visiting Students')[0] != 'visiting'
    assert f('PhD student, previously a visiting student at ETH', 'PhD students')[0] == 'phd'
    assert f('visiting professor of physics', 'People')[0] != 'visiting'


def test_R_STU_17_the_role_vocabulary_admits_visiting():
    import json
    from pathlib import Path
    assert 'visiting' in L.ROLE_OK
    sch = json.loads((Path(__file__).resolve().parents[1] / 'schemas' / 'labpage-additions.schema.json').read_text())
    assert 'visiting' in sch['$defs']['student']['properties']['role']['enum']


def test_R_STU_17_parenthetical_visiting_is_the_role_not_the_name():
    assert L.clean_parenthetical_name('Ann Lee (visiting, CUHK)') == ('Ann Lee', 'visiting')
    assert L.clean_parenthetical_name('Bo Xu (visiting PhD, ETH)') == ('Bo Xu', 'visiting')
    assert L.clean_parenthetical_name('Cy Wu (postdoc)') == ('Cy Wu', 'postdoc')


def test_R_STU_17_a_visiting_student_is_not_a_student_elsewhere():
    """The `at <other institution>` drop (ELSEWHERE_RX) no longer reads 'visiting student at X' as a student of X, and the entry check is skipped
    for a row whose role is visiting; a plain 'PhD student at X' is still elsewhere."""
    assert not L.ELSEWHERE_RX.search('visiting student at ETH Zurich')
    assert L.ELSEWHERE_RX.search('PhD student at ETH Zurich')


def test_R_STU_17_student_decisions_visiting_passes_and_is_not_excluded():
    dec = {'Yuxin Chen': {'Diantong Li': dict(decision='visiting'), 'Chinmaya Mahesh': dict(decision='not')}}
    assert SD.visiting(dec, 'Yuxin Chen', 'Diantong  Li') and not SD.excluded(dec, 'Yuxin Chen', 'Diantong Li')
    assert SD.excluded(dec, 'Yuxin Chen', 'Chinmaya Mahesh') and not SD.visiting(dec, 'Yuxin Chen', 'Chinmaya Mahesh')


def test_R_STU_17_conversion_reads_the_rows_own_evidence_not_a_neighbours():
    row = lambda name, quote, role='phd', **k: dict(name=name, quote=quote, role=role, **k)
    # the visiting phrase must follow the name directly; a later entry's label is not this person's
    assert VR.signal(row('Ann Lee', 'Ann Lee (visiting PhD, ETH) Bo Xu PhD student'))[0] == 'entry'
    assert VR.signal(row('Bo Xu', 'Ann Lee (visiting PhD, ETH) Bo Xu PhD student')) is None
    # a heading names the section: only a pure visiting heading, and not for a row whose own role is another degree
    assert VR.signal(row('Cy Wu', 'Visiting Students Cy Wu', role='other', section='Visiting Students'))[0] == 'section'
    assert VR.signal(row('Cy Wu', 'Cy Wu', role='undergraduate', section='Undergraduate and Visiting Students')) is None
    assert VR.signal(row('Di Fu', 'Visiting Undergraduate Research Assistant Di Fu', role='phd', section='Visiting Undergraduate Research Assistant')) is None
    assert VR.signal(row('Peter Hase', 'Visiting PhD student Navita Goyal Visiting research scientist Peter Hase', role='phd', section='Visiting PhD student')) is None
    # a reviewer's note counts only when it opens with the phrase
    assert VR.signal(row('Ed Gu', 'Ed Gu', role='other', note='visiting undergrad (Cornell), now RI MSR at CMU'))[0] == 'note'
    assert VR.signal(row('Fay Ho', 'Fay Ho', role='masters', note="lab page writes 'Fay H. Ho'; not the 2024 visiting undergrad Zirui Li")) is None


def test_R_STU_17_release_export_labels_and_relation():
    """The release export shows a visiting student as 'Visiting student' (the vendored site builder says 'Lab member'), and a PhD of the same lab keeps its own label."""
    import export_release as E
    assert E.role_label(['visiting'], [dict(type='researched_membership', role='visiting')]) == 'Visiting student'
    assert E.role_label(['visiting'], [dict(type='thesis_adviser')]) == 'Visiting student'
    assert E.role_label(['phd', 'visiting'], []) == 'PhD student' and E.role_label(['member'], []) == 'Lab member'


def test_R_STU_17_conversion_needs_the_evidence_shown_not_just_hinted():
    # after-name wording shows it; a label before a name is not read as that name's role unless the row's own section is a visiting heading
    assert VR.shown('Ann Lee (visiting PhD, ETH) Bo Xu PhD student', 'Ann Lee', False).startswith('Ann Lee (visiting')
    assert VR.shown('Visiting Masters Student (ETH Zurich) Yuanyuan Gao Masters Student', 'Yuanyuan Gao', False) is None
    assert VR.shown('Visiting Students Abdel Zaro (Berkeley) - PhD at GT Gargi Sadalgekar (Princeton)', 'Gargi Sadalgekar', True).startswith('Visiting Students')
    # another role heading, a scientist title, or a mixed heading between the heading and the name stops it
    assert VR.shown('Visiting Students Abdel Zaro Alumni Gargi Sadalgekar', 'Gargi Sadalgekar', True) is None
    assert VR.shown('Visiting PhD student Navita Goyal Visiting research scientist Peter Hase', 'Peter Hase', True) is None
    assert VR.shown('Undergraduate and Visiting Students Cy Wu', 'Cy Wu', True) is None
