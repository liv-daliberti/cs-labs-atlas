import re

import own_page_rank_school as R

L = re.compile(r'(?<![助副理后])研究员|教授', re.I)
S_ = re.compile('武汉大学')


def test_quote_names_school_and_title():
    t = '首页 何德彪，武汉大学计算机学院教授、博士生导师、院长；主要从事密码学'
    q = R.rank_quote(t, S_, L)
    assert '武汉大学' in q and '教授' in q


def test_associate_is_ladder_but_adjunct_and_emeritus_are_not():
    assert R.rank_quote('张三，武汉大学计算机学院副教授', S_, L)
    assert R.rank_quote('张三，武汉大学计算机学院兼职教授', S_, L) is None
    assert R.rank_quote('张三，武汉大学计算机学院荣休教授', S_, L) is None
