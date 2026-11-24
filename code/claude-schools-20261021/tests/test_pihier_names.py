"""Nondecomposing Latin letters retain their initial in byline matching."""
from pihier.names import Name, toks


def test_eth_given_initial_is_preserved_for_owned_full_name():
    assert toks("Žikelić, Ðorđe") == ["dorde", "zikelic"]
    assert toks("ðorđe Žikelić") == ["dorde", "zikelic"]
    assert Name(["Dorde Zikelic"]).match("Žikelić, Ðorđe")


def test_eth_normalization_does_not_erase_a_conflicting_full_given_name():
    assert not Name(["Orde Zikelic"]).match("Žikelić, Ðorđe")
    assert not Name(["Dorde Zikelic"]).match("Orde Zikelic")
    assert not Name(["Dorde Zikelic"]).match("Marko Zikelic")
