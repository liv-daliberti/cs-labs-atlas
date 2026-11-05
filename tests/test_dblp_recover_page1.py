"""R-PAP-36 (2026-11-05, owner: DBLP-listed works confirmed by page 1): the hosts the MIT misses need, and the unconfirmed ledger."""
import dblp_recover as D


def test_R_PAP_36_iacr_eprint_is_not_asked():
    # eprint.iacr.org serves a bot challenge and an AI policy against its PDFs: no fetch
    assert D.pdf_url('https://eprint.iacr.org/2021/1157') is None and 'eprint.iacr.org' not in D.OPEN_HOSTS


def test_R_PAP_36_jmlr_pdf():
    assert D.pdf_url('https://www.jmlr.org/papers/v26/23-1234.html') == 'https://jmlr.org/papers/volume26/23-1234/23-1234.pdf'
    assert D.pdf_url('https://jmlr.org/papers/v26/23-1234.html') == 'https://jmlr.org/papers/volume26/23-1234/23-1234.pdf'


def test_R_PAP_36_neurips_and_colt_still_resolve():
    assert D.pdf_url('http://papers.nips.cc/paper_files/paper/2022/hash/abcdef-Abstract-Conference.html') == \
        'https://proceedings.neurips.cc/paper_files/paper/2022/file/abcdef-Paper-Conference.pdf'
    assert D.pdf_url('https://proceedings.mlr.press/v178/freund22a.html') == 'https://proceedings.mlr.press/v178/freund22a/freund22a.pdf'


def test_R_PAP_36_bare_key():
    assert D.bare_key('https://dblp.org/rec/conf/colt/FreundLW22') == D.bare_key('conf/colt/FreundLW22') == 'conf/colt/FreundLW22'


def test_R_PAP_36_requests_take_host_throttle_slots(monkeypatch):
    calls = []

    class HT:
        WAIT_MAX = 900

        @staticmethod
        def cooldown_left(host):
            return 0

        @staticmethod
        def reserve(host, delay):
            calls.append((host, delay)); return 0

        @staticmethod
        def record_429(host):
            calls.append(('429', host))

    class R:
        status_code = 429
    monkeypatch.setattr(D, '_HT', [HT])
    monkeypatch.setitem(D._robots, 'proceedings.mlr.press', '')
    monkeypatch.setattr(D.requests, 'get', lambda *a, **k: R)
    assert D.polite_get('https://proceedings.mlr.press/v1/x.pdf') is R
    assert calls == [('proceedings.mlr.press', 3.0), ('429', 'proceedings.mlr.press')]


def test_R_PAP_36_arxiv_v1_that_predates_the_record():
    from pihier import papers
    ev = dict(basis='page1_arxiv', url='https://storage.googleapis.com/arxiv-dataset/arxiv/arxiv/pdf/1211/1211.1001v1.pdf')
    assert papers.arxiv_predates_record(ev, 2016)            # Mossel's Majority is Stablest: v1 2012, journal 2016
    assert not papers.arxiv_predates_record(ev, 2015)
    assert not papers.arxiv_predates_record(dict(basis='page1_open', url='https://jmlr.org/x.pdf'), 2016)
    assert not papers.arxiv_predates_record(dict(basis='page1_arxiv', url='https://storage.googleapis.com/arxiv-dataset/arxiv/arxiv/pdf/2206/2206.01.pdf'), 2022)
