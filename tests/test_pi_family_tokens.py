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
    p = {'pi': '章明星', 'names': ['章明星']}
    assert L.pi_full_name_on_page('Mingxing Zhang, associate professor', p)
    assert L.pi_full_name_on_page('Zhang Ming-Xing', p)
    assert not L.pi_full_name_on_page('Zhang Wei is a student', p)
    assert not L.pi_full_name_on_page('Ming Li and Xing Zhao', p)


def test_vendored_pypinyin_loads_from_a_clean_interpreter():
    import subprocess
    import sys
    code = ("import importlib.util as u; s = u.spec_from_file_location('ps', 'tools/pinyin_signal.py'); m = u.module_from_spec(s); s.loader.exec_module(m); "
            "print(m.syllables('章明星'))")
    r = subprocess.run([sys.executable, '-I', '-c', code], capture_output=True, text=True, cwd=str(__import__('pathlib').Path(__file__).resolve().parents[1]))
    assert r.stdout.strip() == "['zhang', 'ming', 'xing']", r.stderr
