import cs_related_school as C

PAGES = [('CEE', 'u', 'sha', '2026', 'Riley Robb Hall C. Lindsay Anderson Chair of the Department of Biological and Environmental Engineering Professor, Biological and Environmental Engineering House Professor Dean, William Keeton House Riley Robb Hall')]


def test_chair_of_department_lead_does_not_hide_the_rank():
    ev = C.faculty_evidence(PAGES, ['C. Lindsay Anderson', 'Catherine Lindsay Anderson'])
    assert ev and ev[0]['ladder'] and 'Professor' in ev[0]['quote']


def test_plain_name_without_rank_still_no_evidence():
    assert not C.faculty_evidence([('X', 'u', 's', '2026', 'Jane Doe Chair of the Department of Physics and the lab director appears later with no title at all ' + 'x ' * 80)], ['Jane Doe'])
