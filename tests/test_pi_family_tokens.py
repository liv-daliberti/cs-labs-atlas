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



def test_pinyin_signal_only_with_pypinyin_present(monkeypatch):
    import sys
    import types
    fake = types.SimpleNamespace(lazy_pinyin=lambda s: ['zhang', 'ming', 'xing'])
    monkeypatch.setitem(sys.modules, 'pypinyin', fake)
    p = {'pi': '章明星', 'names': ['章明星']}
    assert L.pi_full_name_on_page('Ming-Xing Zhang, associate professor', p)
    assert not L.pi_full_name_on_page('Zhang Wei', p)
