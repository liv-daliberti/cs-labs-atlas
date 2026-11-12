"""An open-ended 'PhD, 2024.9-' entry is a start year, still current (SJTU 马超 list, 2026-11-11)."""
import re
import pytest
import labpage_audit as L


@pytest.fixture(autouse=True)
def cjk_region_context():
    L._ENTRY_CTX['bare_year_entry'] = True   # the Chinese-region schools' reading of a bare 'Ph.D. 2023' under a people heading
    yield
    L._ENTRY_CTX['bare_year_entry'] = False


def test_open_ended_month_ranges_are_a_start_and_stay_current():
    for d in ('PhD, 2024.9-', 'PhD, 2024.9–', 'PhD, 2024.9至今', 'PhD student 2024/09 - present', 'PhD 2024.09 to present'):
        years, basis = L.entry_years(d, None)
        assert years == [2024, None] and basis == 'stated_in_entry', d
        assert not L.entry_years_end_the_stay(years, basis)


def test_closed_and_degree_year_entries_are_unchanged():
    assert L.entry_years('(Postdoc, 2010-2014)', None)[0] == [2010, 2014]
    assert L.entry_years('PhD 2021', None)[0] == [None, 2021]


def test_bare_degree_year_in_a_current_list_is_an_entry_year():
    for d in ('(Ph.D./M.S. 2023)', 'Ph.D. 2023', '(Ph.D. 2023)'):
        assert L.entry_years(d, 'Current Students')[0] == [2023, None], d
        assert not L.entry_years_end_the_stay(*L.entry_years(d, 'Current Students'))
    # outside a current list, or in a mixed / alumni heading, a degree year still ends the stay
    assert L.entry_years('Ph.D. 2023', 'Alumni')[0] == [None, 2023]
    assert L.entry_years('Ph.D. 2023', 'Current and Former Students')[0] == [None, 2023]
    assert L.entry_years('Ph.D. 2023', None)[0] == [None, 2023]
    assert L.entry_years('Ph.D. 2019-2023', 'Current Students')[0] == [2019, 2023]


def test_slash_date_open_start_and_prior_degree_after_from_is_not_the_role():
    for d in ('Ph.D student, 2022/9/1 to present; B.S. from X', 'Ph.D student, 2022/9/1 - present. B.S. from X', 'Ph.D student 2022/9/1–'):
        assert L.entry_years(d, None) == ([2022, None], 'stated_in_entry'), d
    ro = lambda t: ('phd' if re.search(r'ph\.?\s?d', t, re.I) else 'undergraduate' if re.search(r'\bb\.?s\.?\b', t, re.I) else None, 'x')
    assert L.entry_role('Ph.D student, 2022/9/1 to present; B.S. from Tsinghua University', 'Members', ro)[0] == 'phd'
    assert L.entry_role('Ph.D student, 2022/9/1 to present', 'Members', ro)[0] == 'phd'


def test_incoming_joint_institute_unclosed_bracket_and_bare_year_under_group_heading():
    assert L.incoming_entry('incoming Ph.D. (Fall 2027)', '') and L.incoming_entry('(2027)', '') and L.incoming_entry('admitted for 2027', '')
    assert not L.incoming_entry('Ph.D. student, 2024-', '')
    assert L.joint_other_institute_entry('Co-supervised by Prof. Li, Shanghai AI Laboratory', '', 'sjtu')
    assert L.joint_other_institute_entry('joint PhD with Shanghai Innovation Institute', '', 'sjtu')
    assert not L.joint_other_institute_entry('Ph.D. student, 2023-', '', 'sjtu')
    assert L.clean_parenthetical_name('Haolan Zhang（Ph.D') == ('Haolan Zhang', 'phd')
    assert L.clean_parenthetical_name('Ann Lee (PhD') == ('Ann Lee', 'phd')
    assert L.entry_years('(Ph.D./M.S. 2023)', 'Research Group Graduate Students')[0] == [2023, None]
    assert L.entry_years('M.S. 2026', 'Research Group Graduate Students')[0] == [2026, None]
    assert L.entry_years('Ph.D. 2023', 'Graduated Students')[0] == [None, 2023]


def test_sjtu_round6_parse_items_from_the_stored_pages():
    ro = lambda t: ('phd' if re.search(r'ph\.?\s?d', t, re.I) else 'masters' if re.search(r'master', t, re.I) else 'undergraduate' if re.search(r'\bb\.?s\.?\b|undergrad', t, re.I) else 'member', 'x')
    # year after award brackets is the entry year (马叶涵's page)
    assert L.entry_years('(2024 Zhongyuan Scholarship, 2025 Huawei Scholarship) 2022', 'Graduate Students')[0] == [2022, None]
    assert L.entry_years('(2026 National Scholarship) 2024 Yiming Zhang', 'Graduate Students > 2025')[0] == [2024, None]
    # dates in the bracket after a co-advised bracket (郑臻哲's page); the B.S. held on arrival is not the role
    d = '(Co-Advised with Prof. Guihai Chen) (2020-, B.S. CS@ Shanghai Jiao Tong University)'
    assert L.entry_years(d, 'Ph.D. students')[0] == [2020, None]
    assert L.entry_role(d, 'Ph.D. students', ro)[0] == 'phd'
    # a Chinese name token before the role (Jia Xiang on 陈国兴's page)
    assert L.entry_role('(向嘉 Master Student, 2021-2024, Alibaba Cloud)', 'Alumni', ro)[0] == 'masters'
    # visit ranges (ZJU 沈春华's visitors)
    assert L.entry_years('2019 ↝ 2020 Visit', None)[0] == [2019, 2020]
    assert L.entry_years('(2019-20 Visit)', None)[0] == [2019, 2020]
    assert L.entry_years('2019-20 Visit', None)[0] == [2019, 2020]


def test_ntu_round6_and_sjtu_remaining_items():
    ro = lambda t: ('phd' if re.search(r'ph\.?\s?d|doctoral', t, re.I) else 'postdoc' if re.search(r'post', t, re.I) else None, 'x')
    # label glued to the name is the stated role
    assert L.clean_parenthetical_name('Zhai Chao Post-doctorate') == ('Zhai Chao', 'postdoc')
    # a mixed postdoc / PhD heading states no role
    assert L.entry_role('', 'Current Post-doctorates and PhD students', ro) == (None, 'none')
    assert L.entry_role('', 'PhD students', ro)[0] == 'phd'
    # award / honour headings are not rosters
    assert L.nonmember_candidate('Zhaoxi Chen', 'NTU PhD Medal of Honour')
    assert L.nonmember_candidate('Zhaoxi Chen', 'CCDS Outstanding PhD Thesis Award')
    assert not L.nonmember_candidate('Zhaoxi Chen', 'PhD Students')
    # 'Master Student' after a Chinese given name when the reader does not know it
    assert L.entry_role('(向嘉 Master Student, 2021-2024, Alibaba Cloud)', 'Alumni', lambda t: (None, None))[0] == 'masters'


def test_bio_sentence_never_sets_the_role_and_a_mixed_heading_list_withholds_it():
    ro = lambda t: ('undergraduate' if re.search(r'\bb\.?s\.?\b', t, re.I) else 'phd' if re.search(r'ph\.?\s?d', t, re.I) else None, 'x')
    assert L.entry_role('received her B.S. in Electronic Information Science from UESTC', 'Ph.D. Student > 2023 Intake', ro)[0] == 'phd'
    txt = 'PhD Students Du Mingzhe Zhao Shiqian Le Duc Dong Research Associates/ Research Assistants / Visiting Students Do Duc Anh Zhao Shiqian Xu Huimin Alumni Zhang Siyue'
    assert L.nearer_nonphd_heading(txt, 'Do Duc Anh', 'PhD Students')
    assert L.nearer_nonphd_heading(txt, 'Zhao Shiqian', 'PhD Students')   # listed again right after the non-PhD heading
    assert not L.nearer_nonphd_heading(txt, 'Du Mingzhe', 'PhD Students')


def test_to_start_future_month_is_incoming():
    assert L.incoming_entry('(PhD, to start in September 2027)', '')
    assert L.incoming_entry('PhD student to start September 2027', '')
    assert L.incoming_entry('will join in Fall 2027', '')
    assert not L.incoming_entry('(PhD, started September 2022)', '')
    assert not L.incoming_entry('Ph.D. student, 2024-', '')


def test_tsinghua_round1_headings_card_labels_and_bylines():
    ro = lambda t: (None, None)
    assert L.entry_role('', 'Master Students', ro) == ('masters', 'section_heading')
    assert L.entry_role('', 'Ph.D Students', ro) == ('phd', 'section_heading')
    assert L.entry_role('Master · Y2 eBPF observability', 'Lab Members > Current Students (13 active)', ro) == ('masters', 'entry')
    assert L.entry_role('Ph.D. · Y5 w/ Prof. X', 'Current Students', ro)[0] == 'phd'
    # a heading that is a person's name is not a role ('Meng' read as M.Eng)
    assert L.entry_role('(2020)', 'Alumni > Zili Meng', lambda t: ('masters', 'x') if 'Meng' in t else (None, None))[0] is None
    # an author list followed by a title is a publication line, not a roster
    q = 'Weiyu Xie , Mingxing Zhang , Xia Liao , Kang Chen , Jinlei Jiang , Yongwei Wu The 29th ACM International Conf'
    assert L.publication_item('Ph.D Computer Science & Technology, 2017', '', q)
    assert not L.publication_item('Current Students', '', 'Current Students Ann Lee Ph.D')


def test_han_member_cards():
    t = ('Advisory Committee ... 博士生 （博士生信息持续更新中） 蔡冠宇 23级博士研究生 蔡冠宇，上海交通大学2023级直博生。 '
         '硕士生 张钰浩 24级硕士研究生 张钰浩，现就读于上海交通大学。 '
         '研究助理 陈天行 25级博士研究生 陈天行，深圳大学2021级本科生，香港大学计算机系2025级直博生。')
    cards = L.han_member_cards(t)
    by = {c['name']: c for c in cards}
    assert by['蔡冠宇']['role'] == 'phd' and by['蔡冠宇']['year'] == 2023 and by['蔡冠宇']['member'] and not by['蔡冠宇']['alumni']
    assert by['张钰浩']['role'] == 'masters' and by['张钰浩']['year'] == 2024
    assert not by['陈天行']['member']   # a research assistant of another university


def test_tsinghua_round2_and_hkust_reaudit_items():
    assert L.nonmember_candidate('Guo Cheng', 'Ph.D Computer Science & Technology, 2017')
    assert not L.nonmember_candidate('Ann Lee', 'Ph.D. Students')
    assert L.entry_years('2025 Summer -', None)[0] == [2025, None]
    assert L.entry_years('2025 Fall - ', None)[0] == [2025, None]
    assert L.entry_years('PhD, 2021 - 2026', None)[0] == [2021, 2026]
    assert L.clean_parenthetical_name('(Co-supervision) Jiawen Zhang')[0] == 'Jiawen Zhang'
    assert L.entry_role('Visiting intern, PhD student from Tsinghua University, Spring 2016', 'Members', lambda t: (None, None))[0] == 'visiting'
    assert L.entry_role('(Visiting professor, X University)', 'Members', lambda t: (None, None))[0] != 'visiting'


def test_han_card_item_has_every_key_an_extract_row_has():
    class N:
        @staticmethod
        def match(name, held):
            return None, None
    c = L.han_member_cards('博士生 蔡冠宇 23级博士研究生 蔡冠宇，上海交通大学。')[0]
    item = L.han_card_item(c, {'url': 'https://x/people.html', 'sha256': 'ab' * 32}, N, [])
    assert all(k in item for k in L.HAN_ITEM_KEYS) and item['url'] == 'https://x/people.html' and item['han_card']['member']


def test_undergraduate_interns_heading_sets_the_role():
    assert L.role_fallback('Undergraduate Interns') == 'undergraduate'
    assert L.entry_role('', 'Undergraduate Interns', lambda t: (None, None)) == ('undergraduate', 'section_heading')


def test_unlabelled_alumni_year_is_an_end_year():
    assert L.entry_years('(2020)', 'Alumni')[0] == [None, 2020]
    assert L.entry_years('(2020)', 'Alumni > Zili Meng')[0] == [None, 2020]
    assert L.entry_years('(2020)', 'Current Students')[0] == [2020, None]   # 2026-11-12: a lone year under a current list is a start, not a one-year stay (Tsinghua 李元杰)


def test_month_year_open_start_and_season_year_stay():
    assert L.entry_years('Master Student, September 2022~ Tsinghua Shenzhen', None)[0] == [2022, None]
    assert L.entry_years('Postdoctor, March 2023~', None)[0] == [2023, None]
    assert L.entry_years('(Tsinghua University), summer 2018', None)[0] == [2018, 2018]
    assert L.entry_years('Summer 2018 intern', None)[0] == [2018, 2018]
    assert L.entry_years('(2025 Summer -)', None)[0] == [2025, None]


def test_since_fyp_and_alumni_destination():
    assert L.entry_years('Since 2022 Fall', None)[0] == [2022, None]
    assert L.entry_years('Since Fall 2022 abc@sjtu.edu.cn', None)[0] == [2022, None]
    assert L.entry_years('Name', 'Final Year Projects > FYP 2019')[0] == [2019, 2019]
    # a Han roster word registers as a people heading and as a current marker
    assert L.STRICT_HEAD.search('在读研究生') and L.STRICT_HEAD.search('已毕业')
    assert L.current_marker({'head': '在读研究生'}) and not L.current_marker({'head': '已毕业'})


def test_discovery_name_signal_for_a_han_keyed_pi():
    import pi_name_signal as N
    assert N.page_names_pi('Shuibing He, Zhejiang University, personal homepage', '何水兵', None)
    assert not N.page_names_pi('He lab at another university', '何水兵', None)   # a family-name-only page never counts


def test_role_from_a_preceding_page_heading():
    assert L.role_from_preceding_heading('Administrative Staff Ph.D Student roster updated: 2026-10-20 Qi Zhao') == 'phd'
    assert L.role_from_preceding_heading("Master Student roster Ke Fan") == 'masters'
    assert L.role_from_preceding_heading('博士生 蔡') == 'phd'
    assert L.role_from_preceding_heading('Ph.D Student roster ... Alumni Ann Lee') is None   # an alumni heading after it
    assert L.role_from_preceding_heading('no heading here') is None


def test_bare_role_sub_heading_and_han_people_links():
    f = L.role_from_preceding_heading
    assert f('Ph.D Student roster Qi Zhao Since 2021 Fall abc AT sjtu.edu.cn Master Haoran Wang 王浩然 Since 2023') == 'masters'
    assert f('Ph.D Student roster x Master Thesis defended') == 'phd'   # 'Master' inside a sentence is not a heading
    assert L.PEOPLE_LINK.match('在读研究生') and L.PEOPLE_LINK.match('团队成员')
    assert not L.PEOPLE_LINK.match('成果发表')


def test_a_lab_on_a_school_subdomain_is_not_a_directory_profile():
    d = r'tsinghua\.edu\.cn'
    assert not L.is_profile('https://nics.ee.tsinghua.edu.cn/people/Xueqing/', d)
    assert not L.is_profile('https://hcsi.cs.tsinghua.edu.cn/people/Wang/', d)
    assert L.is_profile('https://www.ee.tsinghua.edu.cn/people/zhang/', d)
    assert L.is_profile('https://ee.tsinghua.edu.cn/people/li/', d)


def test_zju_roster_items():
    assert L.ENTRY_AS_HEAD_RX.match('Weiya Xu Ph.D., NUS') and not L.ENTRY_AS_HEAD_RX.match('Ph.D. Students')
    assert L.entry_role('', 'Alumni > Weiya Xu Ph.D., NUS', lambda t: ('phd', 'x')) == (None, 'none')   # the previous entry's degree is a destination, not this person's role
    assert L.entry_role('', 'Ph.D. Students', lambda t: ('phd', 'x'))[0] == 'phd'


def test_kai_bu_alumni_and_fyp_lists():
    d = ', BS 2024. FYP advisee (Master Student, HKUST )'
    assert L.entry_years(d, 'Undergraduate. 2023-2024 FYP advisee')[0] == [None, 2024]    # a finished cohort heading: the degree year is the graduation year
    assert L.entry_years(d, 'Alumni')[0] == [None, 2024]
    assert L.entry_years(', BS 2026. FYP advisee', 'Undergraduate FYP advisee')[0] == [2026, 2026]
    assert L.entry_role(', CS 2026. FYP advisee (Master Student, CUHK-Shenzhen )', 'Alumni', lambda t: (None, None))[0] == 'undergraduate'


def test_a_bare_visitor_entry_is_role_visiting():
    ro = lambda t: (None, None)
    assert L.entry_role('Visitor', 'Researchers > ZJU100 Young Professor', ro)[0] == 'visiting'
    assert L.entry_role('Visitor, University of X', 'Members', ro)[0] == 'visiting'
    assert L.entry_role('Visiting professor of physics', 'People', ro)[0] != 'visiting'


def test_outside_the_chinese_region_a_bare_degree_year_is_an_end_year_and_months_ranges_keep_their_end():
    L._ENTRY_CTX['bare_year_entry'] = False
    assert L.entry_years('PhD 2022', 'Former students')[0] == [None, 2022]
    assert L.entry_years('(PhD 2022)', 'Alumni')[0] == [None, 2022]
    assert L.entry_years('MPCS, 2020 -> PhD NYU', 'Students')[0] != [2020, None]
    assert L.entry_years('Oct 2016 - May 2020', None)[0] == [2016, 2020]
    assert L.entry_years('Oct 2016 -', None)[0] == [2016, None]
    ro = lambda t: ('postdoc', 'x') if 'ostdoc' in t else (None, None)
    assert L.entry_role('', 'Current Postdocs', ro)[0] == 'postdoc'
    assert L.entry_role('', 'Mechanical Engineering Postdoc', ro)[0] == 'postdoc'
