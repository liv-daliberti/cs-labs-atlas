"""Tsinghua reader fixes (2026-11-12): a lone year under a current list is a start, and the '年级 姓名 类别 导师' Han table reader."""
import pytest
import labpage_audit as L


@pytest.mark.parametrize('desc,head,want', [
    ('Qi Li Joined 2025 Privacy-preserving computation · Blockchain and Zero-knowledge Proof', 'PhD Students 8 members', [2025, None]),   # 刘卓涛's students page
    ('Yuanzhe Pang Joined 2024 Privacy Computing and Hardware Acceleration', 'PhD Students 8 members', [2024, None]),
    ('Chenyang Li Joined 2023 Hardware Acceleration of Privacy Computing', 'Alumni 3 members', [2023, None]),   # under Alumni the page gives no end year
    ('(2025)', 'PhD students', [2025, None]),   # 李元杰's list: 'Jinyao Zhang (2025)'
    ('(with Hewu Li , 2023)', 'PhD students', [2023, None]),   # 'Minghao Tang (with Hewu Li , 2023)'
])
def test_lone_year_under_a_list_is_a_start_and_stays_open(desc, head, want):
    years, basis = L.entry_years(desc, head)
    assert years == want and basis == 'stated_in_entry'
    assert not L.entry_years_end_the_stay(years, basis)


def test_alumni_and_closed_year_entries_are_unchanged():
    assert L.entry_years('(2020)', 'Alumni')[0] == [None, 2020]
    assert L.entry_years('(MS, with Hewu Li , 2023 - 2026)', 'Alumni')[0] == [2023, 2026]
    assert L.entry_years('Summer 2018 intern', 'Students')[0] == [2018, 2018]


TABLE = ('目前在读学生：博士生14人，硕士生6人 导师 年级 姓 名 类别 导师 辅导老师 专业方向 1 2019 吴松云 直博 杨家海 网络空间安全 2 2019 权晓文 工博- 创新领军 杨家海 网络空间安全 '
         '6 2021 贺 鑫 直博 杨家海 网络空间安全 17 2023 张文健 直硕 杨家海 宋光磊 网络空间安全 18 2023 郑 磊 普硕- 强军 杨家海 李城龙 网络空间安全 '
         '19 2023 某某某 普硕 王之梁 网络空间安全 Copyright© 2010,NOM LAB')


def test_han_adviser_table_reads_year_name_type_and_requires_the_pi_as_adviser():
    rows = L.han_adviser_table_cells(TABLE, '杨家海（校内兼职）')
    assert [(r['name'], r['role'], r['years']) for r in rows] == [
        ('吴松云', 'phd', [2019, None]), ('权晓文', 'phd', [2019, None]), ('贺鑫', 'phd', [2021, None]),
        ('张文健', 'masters', [2023, None]), ('郑磊', 'masters', [2023, None])]   # the 王之梁 row is another adviser's; 辅导老师 is not an adviser
    assert rows[0]['quote'] == '2019 吴松云 直博 杨家海' and rows[2]['quote'] == '2021 贺 鑫 直博 杨家海'
    assert L.han_adviser_table_cells(TABLE, '王之梁') == [dict(name='某某某', role='masters', years=[2023, None], head='Current Students', desc='2023 某某某 普硕 王之梁', quote='2023 某某某 普硕 王之梁')]


def test_han_adviser_table_needs_its_header_and_a_han_pi_name():
    assert L.han_adviser_table_cells('2019 吴松云 直博 杨家海 网络空间安全', '杨家海') == []
    assert L.han_adviser_table_cells(TABLE, 'Jiahai Yang') == []
