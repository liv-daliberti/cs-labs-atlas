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
