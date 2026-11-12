"""Headings that look like member sections but are programme-committee or best-paper lists (Tsinghua 2026-11-11)."""
import labpage_audit as LA  # noqa: E402


def test_tpc_and_best_paper_heads_are_not_member_lists():
    for head in ('TPC member > Kuiper: Enterprise Cloud Plug-and-Play Network Management Platform', 'TPC Members', 'SPC member', 'PC member 2024',
                 'NLPCC 2020 (Best Student Paper)', 'Best Paper Award'):
        assert LA.NOT_MEMBER_HEAD.search(head), head


def test_real_member_heads_stay_members():
    for head in ('Ph.D. Students', 'Current Members', 'Alumni', 'Postdocs', 'Group Members', 'Master Students'):
        assert not LA.NOT_MEMBER_HEAD.search(head), head


def test_visitors_at_another_institution_and_collaborated_students_are_not_member_lists():
    """CMU round 10 (Pfeffer's 'My Visitors @ TUM'; Kilinc-Karzan's students she collaborated with)."""
    assert LA.nonmember_candidate('Philipp Singer', 'My Visitors @ TUM', 'cmu')
    assert not LA.nonmember_candidate('Ann Lee', 'Visitors @ Carnegie Mellon University', 'cmu')
    assert not LA.nonmember_candidate('Ann Lee', 'Visitors', 'cmu')
    assert LA.nonmember_candidate('Adams Wei Yu', 'I collaborate with the following PhD students', 'cmu')
    assert not LA.nonmember_candidate('Ann Lee', 'PhD students I advise', 'cmu')


def test_page_with_only_old_years_is_stale():
    """CMU round 10 (Brookes's students page: no footer, newest dated item 2008)."""
    old = 'Publications. Concurrency, 1984. Models, 1990. Semantics, 2008. Current students: Carsten Varming'
    assert LA.stale_footer_year(old, None) == 2008
    assert LA.stale_footer_year(old + ' Seminar 2019', None) is None
    assert LA.stale_footer_year('Students 2012', None) is None   # a single year is not enough


def test_degree_held_is_not_the_role():
    """CMU round 10: Esquivel (BS read as undergraduate), Jason Lee ('student pursuing M.S.' read as phd), Tingting Liu (an intern's PhD at HKU)."""
    role_of = lambda s: (('intern' if 'ntern' in s else 'undergraduate' if 'BS' in s else 'member'), 0)
    assert LA.entry_role('PhD Pre-Candidate BS Civil & Environmental Engineering: University of Massachusetts Amherst', 'Graduate Students', role_of)[0] == 'phd'
    assert LA.entry_role('is an IMB student pursuing M.S. in Electrical and Computer Engineering. His interests', 'Graduate Students', role_of)[0] == 'masters'
    assert LA.entry_role('PhD. in Educational Technology Student, University of Hong Kong and Assistant Professor, Hubei University',
                         'Former Summer Interns > 2019', role_of) == ('intern', 'section_heading')
    assert LA.entry_role('PhD. in Computer Science Student, Carnegie Mellon University', 'Graduate Students', lambda s: ('phd', 0))[0] == 'phd'


def test_student_level_prize_heading_lists_students_and_award_heading_still_does_not():
    """Georgia Tech Bo Zhu: '2021 Neukom Graduate Research Prize Winner' names its recipients' level; NTU's thesis award heading stays out."""
    assert not LA.nonmember_candidate('Yaorui Zhang', '2021 Neukom Undergraduate Research Prize Winner > 2021 Neukom Graduate Research Prize Winner')
    assert LA.nonmember_candidate('Zhaoxi Chen', 'CCDS Outstanding PhD Thesis Award')
    assert LA.AWARD_SENTENCE_RX.search('Guanghui Wang , Krishna Acharya , and Juba Ziani received the fellowship')


PAGE = ('Graduated Students and Alumni PhD Students: 10. Dr. Ronald SO (Computer Science and Engineering, Spring 2020; He is a research fellow.) '
        '11. Dr. Yongxiang (Jason) HUANG (Computer Science and Engineering, Winter 2021; He is currently working full-time as an R&D Engineer at Tencent, Shenzhen.) '
        '12. Dr. Siqi (Portia) BAO (Computer Science and Engineering, Summer 2017; She is at Baidu.) '
        'Selected publications: Siqi Bao, Pei Wang, Albert Chung. A paper title. In CVPR 2019. Best Paper Award: Siqi Bao.')


def test_numbered_roster_cell_is_its_own_quote():
    """HKUST Chung: the quote of a numbered graduates-list entry is that entry, not a paper-author or award line."""
    x = dict(name='Siqi BAO', desc='(Computer Science and Engineering, Summer 2017; She is at Baidu.)', quote='Siqi Bao, Pei Wang, Albert Chung. A paper title. In CVPR 2019.')
    LA.localize_quote(x, PAGE)
    assert x['quote'] == '12. Dr. Siqi (Portia) BAO (Computer Science and Engineering, Summer 2017; She is at Baidu.)'
    y = dict(name='Yongxiang HUANG', desc='', quote='Best Paper Award: Siqi Bao.')
    LA.localize_quote(y, PAGE)
    assert y['quote'].startswith('11. Dr. Yongxiang (Jason) HUANG (Computer Science and Engineering, Winter 2021') and y['quote'].endswith('Shenzhen.)')
    assert LA.numbered_entry_quote('Colin Tsang', PAGE) is None


def test_committee_referee_and_letter_writer_lists_are_not_member_lists():
    for head in ('Dissertation Committee Members', 'Foreign Advisor', 'Letter Writers', 'External Examiners > Postdoc, Johns Hopkins University, USA', 'Referees'):
        assert LA.nonmember_candidate('Hailun Zhang', head), head
    for head in ('PhD Students', 'Alumni', 'Postdoc, Johns Hopkins University, USA'):
        assert not LA.nonmember_candidate('Hailun Zhang', head), head


CHEN = ("Yuan Qiao  Master's from Peking Univ ( Nat'l Scholarship) Hongyi Li  Bachelor's from Tsinghua Univ Students for whom I serve as the co-chair/ dissertation committee/ "
        "foreign advisor/ letter writer and others: At HKUST : Chang Dong (2022)  Assistant Professor, Durham University, UK Wentao Lu (2022)  Postdoc, Johns Hopkins University, USA "
        "Hailun Zhang (2019)  Assistant Professor, CUHK Shenzhen Yunjie Wang (2017)  Assistant Professor, Renmin University")
KILINC = ("Students I have been very fortunate to advise the following PhD students: Alex L. Wang , CMU CS 2022 Nam Ho-Nguyen , CMU Tepper OR 2019 In addition, I have had wonderful "
          "opportunities to collaborate with the PhD students (some current and some former): Lingqing Shen , CMU Tepper ACO Adams Wei Yu , CMU ML 2019 "
          "Postdoctoral Researchers I have been very fortunate to advise the following postdoctoral researchers: Soroosh Shafieezadeh-Abadeh , 2021-2023")


def test_colon_lead_collaborator_and_committee_lists_on_the_real_pages():
    """The real text of imchen.people.ust.hk (sha16 355f1b2c...) and Kilinc-Karzan's page: the lead sentence, not a heading, marks the list."""
    for n in ('Hailun Zhang', 'Yunjie Wang', 'Wentao Lu'):
        assert LA.collaborator_list_before(CHEN, n), n
    assert not LA.collaborator_list_before(CHEN, 'Hongyi Li')
    assert LA.collaborator_list_before(KILINC, 'Adams Wei Yu') and LA.collaborator_list_before(KILINC, 'Lingqing Shen')
    assert not LA.collaborator_list_before(KILINC, 'Alex L. Wang') and not LA.collaborator_list_before(KILINC, 'Soroosh Shafieezadeh-Abadeh')


def test_numbered_cell_with_middle_names_on_the_real_chung_capture():
    """The real text of cse.ust.hk/~achung (sha16 cca1bc482a7c9b70): 'Dr. Ronald Wai King SO (...)' is the cell of the row 'Ronald So'; the earlier 'Mr. Wai King SO (An honors-track ...' is another entry."""
    page = ("(... as Postdoctoral Scholar in 2014) 8. Dr. Ronald Wai King SO (Computer Science and Engineering, January 2017; He is currently working full-time as a Resident Physicist at the Princess Margaret Hospital, Hong Kong.) "
            "15. Dr. Colin Siu Chung TSANG (Computer Science and Engineering, Summer 2023; He is currently with The Chinese University of Hong Kong) M.Phil. Students: "
            "Mr. Wai King SO (An honors-track student in the Computer Engineering Program, Joined our MPhil program at UST in 2007, and joined out PhD program in 2009)")
    assert LA.numbered_entry_quote('Ronald So', page).startswith('8. Dr. Ronald Wai King SO (Computer Science and Engineering, January 2017')
    assert LA.numbered_entry_quote('Colin Tsang', page).endswith('The Chinese University of Hong Kong)')
    assert LA.numbered_entry_quote('Wai King So', page) is None   # the honors-track entry has no department/term bracket: not merged


def test_stanford_recall_entry_formats():
    """Stanford recall 2026-11-12: each on the stored entry text (Ying/Lu, Winstein, Shah, Duchi, Bouland, Re's 'PhDs', Gevaert's :443, Pohl's Nerrise)."""
    import sys
    sys.path.insert(0, str(LA.HT / 'labpage-tools-princeton-mit'))
    import autom
    ro = autom._role
    assert LA.entry_years('(2023, co-advised with Jose Blanchet)', 'Graduated PhD students')[0] == [None, 2023]
    assert LA.entry_years('(2020, with Philip Levis)', 'Current > Doctoral')[0] == [None, 2020]
    assert LA.entry_role('(BMI, Postdoctoral Scholar 2021)', 'Recent Lab Alumni', ro)[0] == 'postdoc'
    assert LA.entry_years('(BMI, Postdoctoral Scholar 2021)', 'Recent Lab Alumni')[0] == [None, 2021]
    assert LA.entry_role('Statistics (PhD 2019)', 'Alumni', ro)[0] == 'phd'
    assert LA.entry_role('MS student -> postgrad researcher in CS (2023-5) and Physics (2025-present)', 'Alumni', ro)[0] == 'other'
    assert LA.entry_role('MS student, 2023', 'Alumni', ro)[0] == 'masters'
    assert LA.STRICT_HEAD.search('PhDs') and LA.STUDENT_HEAD.search('PhDs')
    assert LA.url_key('https://med.stanford.edu:443/gevaertlab/people.html') == LA.url_key('http://med.stanford.edu/gevaertlab/people.html')
    assert LA.plausible_under_student_heading('Favour Nerrise') and not LA.plausible_under_student_heading('Machine Learning')


def test_industry_visiting_scholar_is_not_a_student_member():
    assert LA.prose_nonmember('Masao Sambongi', ', Olympus Corporation, Visiting Scholar, 2015-2017', 'Masao Sambongi, Olympus Corporation, Visiting Scholar, 2015-2017')
    assert not LA.prose_nonmember('Ann Lee', ', Visiting Student from CUHK, 2016', 'Ann Lee, Visiting Student from CUHK, 2016')


def test_generic_graduate_students_heading_states_no_degree():
    """Stanford Cioffi: 'Graduate Students' with only emails: the role stays unknown; an explicit PhD heading still says phd."""
    import sys
    sys.path.insert(0, str(LA.HT / 'labpage-tools-princeton-mit'))
    import autom
    assert LA.entry_role('Muhammad Umer umer@stanford.edu', 'Graduate Students', autom._role) == (None, 'none')
    assert LA.entry_role('Muhammad Umer umer@stanford.edu', 'PhD Students', autom._role)[0] == 'phd'
