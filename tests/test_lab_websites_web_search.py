"""Owner ruling 2026-11-11: a web_search_reviewed check (live fetch, name and school-tie quotes, reviewer) records the official link of a site."""
import lab_websites as W

URL = 'https://cs.stanford.edu/~pliang/'
GOOD = dict(source='web_search_reviewed', url=URL, at='2026-11-11T22:00:00+00:00', sha256='a' * 64, name_quote='Percy Liang Professor', tie_quote='Computer Science Stanford University', reviewer='fresh reviewer')


def test_web_search_check_counts_with_full_provenance():
    assert W.official_check(GOOD, URL)


def test_web_search_check_needs_every_field():
    for k in ('at', 'sha256', 'name_quote', 'tie_quote', 'reviewer'):
        assert not W.official_check({**GOOD, k: ''}, URL)
    assert not W.official_check(GOOD, 'https://other.example/')


def test_reviewed_site_kind_lab_vs_personal():
    d = ['ethz.ch']
    base = dict(name_quote='x', tie_quote='y', note='')
    assert W.reviewed_site_kind({**base, 'url': 'https://msrl.ethz.ch/'}, d) == 'lab_site'   # a dedicated group host
    assert W.reviewed_site_kind({**base, 'url': 'https://people.math.ethz.ch/~patrickc/'}, d) == 'pi_homepage'
    assert W.reviewed_site_kind({**base, 'url': 'https://www.ethz.ch/'}, d) == 'pi_homepage'
    assert W.reviewed_site_kind({**base, 'url': 'https://sam.math.ethz.ch/people/x'}, d) == 'pi_homepage'
    assert W.reviewed_site_kind({**base, 'url': 'https://elliottash.com/', 'note': 'x | group heading: Law and Economics Lab'}, d) == 'lab_site'
    assert W.reviewed_site_kind({**base, 'url': 'https://elliottash.com/', 'note': 'x | group heading: Home'}, d) == 'pi_homepage'
    assert W.reviewed_site_kind({**base, 'url': 'https://example.org/'}, []) == 'pi_homepage'
    assert W.reviewed_site_kind({**base, 'url': 'https://syssec.ethz.ch/people/'}, d) == 'lab_site'   # a group's members page
