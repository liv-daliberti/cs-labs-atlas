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


def test_site_kind_one_rule_for_discovery_rows():
    d, dh = ['ethz.ch'], {'ee.ethz.ch', 'inf.ethz.ch'}
    assert W.site_kind('http://www.iis.ee.ethz.ch/', '', d, dh) == 'lab_site'          # a group host below a department host
    assert W.site_kind('http://www.ee.ethz.ch/', '', d, dh) == 'pi_homepage'           # the department itself
    assert W.site_kind('http://www.inf.ethz.ch/personal/markusp/', '', d, dh) == 'pi_homepage'
    assert W.site_kind('https://people.inf.ethz.ch/trg/', '', d, dh) == 'pi_homepage'
    assert W.site_kind('https://elliottash.com/', 'Law and Economics Lab', d, dh) == 'lab_site'
    assert W.site_kind('https://example.org/', '', [], set()) == 'pi_homepage'
    assert W.site_kind('https://bsse.ethz.ch/cbg', '', d, {'bsse.ethz.ch'}) == 'lab_site'
    assert W.site_kind('https://bsse.ethz.ch/people/', '', d, {'bsse.ethz.ch'}) == 'pi_homepage'
