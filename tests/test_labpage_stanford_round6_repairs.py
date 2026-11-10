"""Stanford round-6 repairs: administrative staff in a contact block, and pages whose footer is dated before 2016."""
import labpage_audit as L


def test_admin_associate_in_contact_block_is_staff():
    assert L.admin_staff_entry('Contact', 'Administrative Associate', 'Jenny Lam Administrative Associate')
    assert L.admin_staff_entry('', 'Executive Assistant to the chair', '')
    assert not L.admin_staff_entry('Students', 'PhD student, advised by X', '')
    assert not L.admin_staff_entry('Contact', 'PhD candidate', 'Administrative Associate help from Jo')


def test_pre_2016_footer_marks_an_old_page():
    assert L.stale_footer_year('Group page. Copyright 2012 Stanford University', 2024) == 2012
    assert L.stale_footer_year('(c) Last updated: 2013', 2024) == 2013
    assert L.stale_footer_year('Copyright 2012 ... Copyright 2024', 2024) is None
    assert L.stale_footer_year('Copyright 2015', 2016) is None   # captured the next year: not yet old
    assert L.stale_footer_year('no footer', 2024) is None
