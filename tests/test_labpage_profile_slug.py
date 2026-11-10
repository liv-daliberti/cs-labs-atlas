"""R-LAB-01: a directory card's link ('Learn more about <name>') is the PI's profile when its path ends in the PI's name slug."""
import labpage_audit as L


def test_slug_matches_the_ece_card_link():
    assert L.profile_slug_hit('https://ece.gatech.edu/directory/arijit-raychowdhury', ['Arijit Raychowdhury'])
    assert L.profile_slug_hit('https://ic.gatech.edu/people/gregory-abowd-0', ['Gregory Abowd'])


def test_slug_needs_given_and_family_name():
    assert not L.profile_slug_hit('https://ece.gatech.edu/directory/raychowdhury', ['Arijit Raychowdhury'])
    assert not L.profile_slug_hit('https://ece.gatech.edu/directory/arijit-chowdhury', ['Arijit Raychowdhury'])
    assert not L.profile_slug_hit('https://ece.gatech.edu/directory/', ['Arijit Raychowdhury'])


def test_pure_institutional_profile_is_not_a_lab_website():
    assert L.is_profile('https://profiles.wustl.edu/en/persons/fuhai-li', r'wustl\.edu')
    assert not L.is_profile('https://www.cse.wustl.edu/~kunal/', r'wustl\.edu')


def test_a_dotted_first_dot_last_slug_is_a_profile_card():
    # Oxford Computer Science: '/people/Samson.Abramsky' (2026-11-10: 34 PIs had no school_profile check)
    assert L.profile_slug_hit('https://www.cs.ox.ac.uk/people/Samson.Abramsky', ['Samson Abramsky'])
    assert not L.profile_slug_hit('https://www.cs.ox.ac.uk/people/Abramsky', ['Samson Abramsky'])
