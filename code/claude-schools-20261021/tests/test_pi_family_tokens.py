import pytest

import labpage_audit as L


def test_mixed_latin_cjk_name_uses_latin_surname():
    assert L.pi_family_tokens('Raymond Chi-Wing WONG 黃智榮') == ['黃智榮', 'WONG']


def test_pure_latin_and_pure_cjk_unchanged():
    assert L.pi_family_tokens('Shaojie Shen') == ['Shen']
    assert L.pi_family_tokens('张三') == ['张三']
    assert L.pi_family_tokens('') == ['']


def test_han_keyed_pi_with_latin_alias_named_on_page():
    p = {'pi': '张卓升', 'names': ['张卓升', 'Zhuosheng Zhang']}
    assert L.pi_full_name_on_page('Prof. Zhuosheng Zhang leads the BCMI lab', p)
    assert L.pi_full_name_on_page('Zhang Zhuosheng, Associate Professor', p)


def test_namesake_family_only_page_fails():
    p = {'pi': '张卓升', 'names': ['张卓升', 'Zhuosheng Zhang']}
    assert not L.pi_full_name_on_page('Wei Zhang is a student of the lab', p)
    assert not L.pi_full_name_on_page('Zhang Wei and Li Zhuo', p)



def test_pinyin_signal_for_han_only_record_and_namesake_fails():
    pytest.importorskip('pypinyin')
    p = {'pi': '章明星', 'names': ['章明星']}
    assert L.pi_full_name_on_page('Mingxing Zhang, associate professor', p)
    assert L.pi_full_name_on_page('Zhang Ming-Xing', p)
    assert not L.pi_full_name_on_page('Zhang Wei is a student', p)
    assert not L.pi_full_name_on_page('Ming Li and Xing Zhao', p)


def test_pinyin_substrings_do_not_count():
    pytest.importorskip('pypinyin')
    p = {'pi': '李勇', 'names': ['李勇']}
    assert not L.pi_full_name_on_page('Li and Yong are common syllables; Young Li lives in Lisbon', p)
    assert L.pi_full_name_on_page('Dr. Yong Li, Tsinghua', p)


def test_person_fetch_han_keyed_call_site():
    import person_fetch as PF
    body = b'<html><body><h1>Prof. Mingxing Zhang</h1></body></html>'
    pytest.importorskip('pypinyin')
    assert PF.names_person(body, '\u7ae0\u660e\u661f', ['\u7ae0\u660e\u661f'])[0]
    assert PF.last_name_on_page(body, '\u7ae0\u660e\u661f', ['\u7ae0\u660e\u661f'])
    ns = b'<html><body><h1>Wei Zhang, a namesake</h1></body></html>'
    assert not PF.names_person(ns, '\u7ae0\u660e\u661f', ['\u7ae0\u660e\u661f'])[0]
    assert not PF.last_name_on_page(ns, '\u7ae0\u660e\u661f', ['\u7ae0\u660e\u661f'])
    alias = b'<html><body>Zhuosheng Zhang leads BCMI</body></html>'
    assert PF.names_person(alias, '\u5f20\u5353\u5347', ['\u5f20\u5353\u5347', 'Zhuosheng Zhang'])[0]


def test_latin_keyed_person_unchanged():
    import person_fetch as PF
    assert PF.names_person(b'<p>Jane Doe works here</p>', 'Jane Doe')[0]
    assert not PF.names_person(b'<p>John Doe works here</p>', 'Jane Doe')[0]
