import labpage_audit as L


def test_mixed_latin_cjk_name_uses_latin_surname():
    assert L.pi_family_tokens('Raymond Chi-Wing WONG 黃智榮') == ['黃智榮', 'WONG']


def test_pure_latin_and_pure_cjk_unchanged():
    assert L.pi_family_tokens('Shaojie Shen') == ['Shen']
    assert L.pi_family_tokens('张三') == ['张三']
    assert L.pi_family_tokens('') == ['']
