"""The ledger's reason codes (docs/UNAVAILABLE.md): one fixture paper per code through unavailable_ledger.decide()."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'fulltext-push'))
import unavailable_ledger as U  # noqa: E402

ALL = ['openalex', 'arxiv', 's2', 'dblp', 'proceedings', 'repository', 'labpages', 'core']


def none(src):
    return dict(source=src, at='2026-10-30T00:00:00+00:00', query='q', result='none', detail={})


def paper(**kw):
    p = dict(status='needs_access_review', doi='10.1109/x.1', attempts=[], untried=[], all_urls=set(), access=None, in_catalog=True,
             applicable=list(ALL), checks={s: none(s) for s in ALL})
    p['checks']['openalex'] = dict(none('openalex'), detail=dict(is_oa=False, oa_status='closed'))
    p.update(kw)
    return p


def att(url, cause):
    return dict(url=url, cause=cause, at='2026-10-29', status='unavailable', detail='')


def code(p):
    return U.decide(p)[0]


def test_found_awaiting_download_untried():
    assert code(paper(untried=['https://repo.example.edu/x.pdf'])) == 'found_awaiting_download'


def test_found_awaiting_download_new_from_a_check():
    p = paper()
    p['checks']['core'] = dict(none('core'), result='found', detail=dict(usable=['https://repo.example.edu/y.pdf']))
    assert U.decide(p)[0] == 'found_awaiting_download' and U.decide(p)[2] == ['https://repo.example.edu/y.pdf']


def test_found_already_attempted_is_not_new():
    p = paper(attempts=[att('https://repo.example.edu/y.pdf', 'not_found')])
    p['checks']['core'] = dict(none('core'), result='found', detail=dict(usable=['https://repo.example.edu/y.pdf']))
    assert code(p) == 'open_copy_unusable'


def test_found_not_in_catalog():
    p = paper(in_catalog=False, status='not_in_catalog')
    p['checks']['arxiv'] = dict(none('arxiv'), result='found', detail=dict(arxiv='2101.00001', usable=['arXiv:2101.00001']))
    assert code(p) == 'found_not_in_catalog'


def test_arxiv_bulk_attempt_counts_as_tried():
    p = paper(attempts=[att('https://storage.googleapis.com/arxiv-dataset/arxiv/arxiv/pdf/2101/2101.00001v1.pdf', 'identity_mismatch')])
    p['checks']['arxiv'] = dict(none('arxiv'), result='found', detail=dict(arxiv='2101.00001', usable=['arXiv:2101.00001']))
    assert code(p) == 'open_copy_unusable'


def test_pending_retry():
    assert code(paper(status='queued', attempts=[att('https://repo.example.edu/a', 'transient')])) == 'pending_retry'
    assert code(paper(access=dict(verdict='requeue_transient', cause='transient'))) == 'pending_retry'


def test_incomplete_check():
    p = paper()
    p['checks']['s2'] = dict(none('s2'), result='error')
    r, missing, _ = U.decide(p)
    assert r == 'incomplete_check' and missing == ['s2']


def test_open_copy_bot_challenge():
    assert code(paper(attempts=[att('https://figshare.com/articles/x/1', 'challenge')])) == 'open_copy_bot_challenge'


def test_open_copy_behind_login():
    assert code(paper(attempts=[att('https://repo.example.edu/a', 'login')])) == 'open_copy_behind_login'


def test_open_copy_robots_disallowed():
    assert code(paper(attempts=[att('https://hal.science/hal-1', 'robots_disallow')])) == 'open_copy_robots_disallowed'


def test_landing_page_without_pdf():
    assert code(paper(attempts=[att('https://pubmed.ncbi.nlm.nih.gov/1/', 'landing_no_pdf')])) == 'landing_page_without_pdf'


def test_open_copy_unusable():
    assert code(paper(attempts=[att('https://lab.example.edu/p.pdf', 'not_found')])) == 'open_copy_unusable'


def test_paywall_only():
    p = paper(attempts=[att('https://ieeexplore.ieee.org/document/1', 'paywall_or_forbidden')])
    p['checks']['openalex'] = dict(none('openalex'), detail=dict(is_oa=True, oa_status='bronze'))
    assert code(p) == 'paywall_only'


def test_publisher_only_closed():
    assert code(paper(attempts=[att('https://ieeexplore.ieee.org/document/1', 'paywall_or_forbidden')])) == 'publisher_only_closed'
    assert code(paper()) == 'publisher_only_closed'


def test_no_doi_no_match():
    assert code(paper(doi=None)) == 'no_doi_no_match'


def test_vocabulary_is_closed_and_documented():
    doc = (Path(__file__).resolve().parents[1] / 'docs' / 'UNAVAILABLE.md').read_text()
    for c in U.REASONS:
        assert f'`{c}`' in doc


def test_summary_is_one_paragraph():
    p = paper(attempts=[att('https://ieeexplore.ieee.org/document/1', 'paywall_or_forbidden')], school='mit', checked_at='2026-10-30T00:00:00',
              publisher='IEEE', venue='IEEE Transactions on Robotics')
    c, m, n = U.decide(p)
    s = U.summarize(p, c, m, n)
    assert s.startswith('At IEEE (closed access, IEEE Transactions on Robotics).') and 'ieeexplore.ieee.org paywall_or_forbidden' in s and '\n' not in s


def test_open_at_publisher_but_robots_disallow():
    p = paper(attempts=[att('https://www.sciencedirect.com/science/article/pii/X', 'robots_disallow')])
    p['checks']['openalex'] = dict(none('openalex'), detail=dict(is_oa=True, oa_status='hybrid'))
    assert code(p) == 'open_copy_robots_disallowed'


def test_quarantined_copy_is_robots_disallowed():
    assert code(paper(quarantined=True, attempts=[att('https://hal.science/hal-1/document', 'other')])) == 'open_copy_robots_disallowed'


def test_identity_unconfirmed_copy():
    assert code(paper(status='identity_unconfirmed')) == 'identity_unconfirmed'
