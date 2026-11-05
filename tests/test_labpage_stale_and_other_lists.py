"""R-LAB-02/03 (Georgia Tech round 2): stale undated lists, other-institution forms and entries advised by someone else."""
import labpage_audit as L


def test_stale_list_needs_old_alumni_before_the_capture_year():
    x = dict(capture_url='https://web.archive.org/web/20240228210706id_/https://faculty.cc.gatech.edu/~mustaq/')
    assert L.stale_list(x, {x['capture_url']: 2001})
    assert not L.stale_list(x, {x['capture_url']: 2021})
    assert not L.stale_list(x, {})
    assert not L.stale_list(dict(capture_url=None), {None: 2001})


def test_entry_advised_by_someone_else_is_not_this_pis_student():
    assert L.advised_by_other('(MIT ORC PhD, advised by Alexandre Jacquillat)', '', 'Arthur Delarue')
    assert not L.advised_by_other('(PhD, advised by Arthur Delarue and X)', '', 'Arthur Delarue')
    assert not L.advised_by_other('PhD student', '', 'Arthur Delarue')


def test_other_institution_without_the_word_university():
    assert L.other_institution_entry('Taiyuan Zhang (MSCS at Dartmouth)', '', 'gatech')
    assert L.other_institution_entry('Boshen Zhang: Undergraduate researcher, Virginia Tech, August 2021', '', 'gatech')
    assert not L.other_institution_entry('Sinan Wang (Ph.D. of CS at Georgia Tech)', '', 'gatech')


def test_current_students_page_address_marks_entries_current():
    x = dict(head='Post-Doctoral Researchers:', desc='', capture_url='https://web.archive.org/web/20220703140740id_/https://icsrl.ece.gatech.edu/current-students/')
    assert L.current_marker(x)
    assert not L.current_marker(dict(x, capture_url='https://icsrl.ece.gatech.edu/alumni/'))
