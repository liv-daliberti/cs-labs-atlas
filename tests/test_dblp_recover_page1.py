"""R-PAP-36 (2026-11-05, owner: DBLP-listed works confirmed by page 1): the hosts the MIT misses need, and the unconfirmed ledger."""
import dblp_recover as D


def test_R_PAP_36_iacr_eprint_pdf():
    assert D.pdf_url('https://eprint.iacr.org/2021/1234') == 'https://eprint.iacr.org/2021/1234.pdf'
    assert D.pdf_url('http://eprint.iacr.org/2021/1234.pdf') == 'https://eprint.iacr.org/2021/1234.pdf'
    assert 'eprint.iacr.org' in D.OPEN_HOSTS


def test_R_PAP_36_jmlr_pdf():
    assert D.pdf_url('https://www.jmlr.org/papers/v26/23-1234.html') == 'https://jmlr.org/papers/volume26/23-1234/23-1234.pdf'
    assert D.pdf_url('https://jmlr.org/papers/v26/23-1234.html') == 'https://jmlr.org/papers/volume26/23-1234/23-1234.pdf'


def test_R_PAP_36_neurips_and_colt_still_resolve():
    assert D.pdf_url('http://papers.nips.cc/paper_files/paper/2022/hash/abcdef-Abstract-Conference.html') == \
        'https://proceedings.neurips.cc/paper_files/paper/2022/file/abcdef-Paper-Conference.pdf'
    assert D.pdf_url('https://proceedings.mlr.press/v178/freund22a.html') == 'https://proceedings.mlr.press/v178/freund22a/freund22a.pdf'


def test_R_PAP_36_bare_key():
    assert D.bare_key('https://dblp.org/rec/conf/colt/FreundLW22') == D.bare_key('conf/colt/FreundLW22') == 'conf/colt/FreundLW22'
