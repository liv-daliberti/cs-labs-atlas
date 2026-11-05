"""R-LAB-01: a directory card's link ('Learn more about <name>') is the PI's profile when its path ends in the PI's name slug."""
import labpage_audit as L


def test_slug_matches_the_ece_card_link():
    assert L.profile_slug_hit('https://ece.gatech.edu/directory/arijit-raychowdhury', ['Arijit Raychowdhury'])
    assert L.profile_slug_hit('https://ic.gatech.edu/people/gregory-abowd-0', ['Gregory Abowd'])


def test_slug_needs_given_and_family_name():
    assert not L.profile_slug_hit('https://ece.gatech.edu/directory/raychowdhury', ['Arijit Raychowdhury'])
    assert not L.profile_slug_hit('https://ece.gatech.edu/directory/arijit-chowdhury', ['Arijit Raychowdhury'])
    assert not L.profile_slug_hit('https://ece.gatech.edu/directory/', ['Arijit Raychowdhury'])
