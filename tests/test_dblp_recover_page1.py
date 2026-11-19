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


def test_R_PAP_36_bmva_archive_pdf_is_an_open_proceedings_source():
    url = 'https://bmva-archive.org.uk/bmvc/2024/papers/Paper_563/paper.pdf'
    assert 'bmva-archive.org.uk' in D.OPEN_HOSTS
    assert D.pdf_url(url) == url


def test_R_PAP_36_bare_key():
    assert D.bare_key('https://dblp.org/rec/conf/colt/FreundLW22') == D.bare_key('conf/colt/FreundLW22') == 'conf/colt/FreundLW22'


def test_page1_matches_literal_short_first_name_at_vt():
    import re
    from pi_fulltext_affiliation import tie
    from pi_hierarchy import AFF
    text = 'Jiyune Jeon and Jongseok Kim, Sungkyunkwan University; Sam H. Noh, Virginia Tech; Euiseong Seo, Sungkyunkwan University'
    how, quotes = tie(text, D.page1_name_forms(['Sam H. Noh', 'Sam Hyuk Noh']), re.compile(AFF['vt'], re.I))
    assert how == 'near'
    assert 'Sam H. Noh, Virginia Tech' in quotes[0]


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


def test_R_PAP_36_usenix_and_ceur_hosts():
    assert D.pdf_url('https://www.usenix.org/conference/atc25/presentation/yuan') == 'https://www.usenix.org/system/files/atc25-yuan.pdf'
    assert D.pdf_url('https://ceur-ws.org/Vol-3994/short4.pdf') == 'https://ceur-ws.org/Vol-3994/short4.pdf'
    assert D.CRAWL_DELAY['www.usenix.org'] == 10.0


def test_R_PAP_36_reviewed_blocked_cluster_stops_recovered_rows():
    from pihier import identity
    chen = {'blockedClusters': [{'coauthors': ['Ben Y. Zhao', 'Haitao Zheng'], 'min_coauthors': 2}]}
    assert identity.in_blocked_cluster(chen, dict(authorships=[dict(raw_author_name=b) for b in ['Yuxin Chen', 'Huiying Li', 'Ben Y. Zhao', 'Haitao Zheng']]))


def test_R_PAP_36_retry_chain_does_not_ask_twice(monkeypatch, tmp_path):
    import sqlite3
    c = sqlite3.connect(tmp_path / 'r.sqlite')
    c.execute('create table tries (pi text, dblp_key text, step text, url text, status text, pdf_sha256 text, page1 blob, accepted int, evidence text, at text)')
    c.execute("insert into tries values ('p','k1','none',null,'dblp_unconfirmed',null,null,0,null,'2026-11-06T10:00:00Z')")
    c.execute("insert into tries values ('p','k2','none',null,'dblp_unconfirmed',null,null,0,null,'2026-11-05T10:00:00Z')")
    src = open(D.__file__).read()
    assert "DBLP_RETRY_SINCE" in src and "where at >= ?" in src   # records tried since the chain started are done


def test_bilingual_pi_label_uses_its_explicit_latin_byline_name():
    from pi_fulltext_affiliation import tie
    import school_config as S
    for label, author in [('Sunil ARYA 安雅信', 'Sunil Arya'),
                          ('Gary S. H. CHAN 陳雙幸', 'Gary Chan'),
                          ('James Tin Yau KWOK 郭天佑', 'James Kwok')]:
        text = author + ' Department of Computer Science, Hong Kong University of Science and Technology Abstract A research paper.'
        assert tie(text, D.page1_name_forms([label]), S.aff_rx('hkust'))[0]
    assert not tie('Different Author, Hong Kong University of Science and Technology Abstract A paper.',
                   D.page1_name_forms(['Sunil ARYA 安雅信']), S.aff_rx('hkust'))[0]


def test_primary_conference_pdfs_are_supported_without_author_site_allowlisting():
    for url in ['https://www.ieee-security.org/TC/SP2017/papers/581.pdf',
                'https://www.openproceedings.org/2025/conf/edbt/paper-19.pdf']:
        assert any(host in url for host in D.OPEN_HOSTS)
        assert D.pdf_url(url) == url


def test_R_PAP_36_openalex_other_institution_does_not_close_the_record_before_page_1():
    """2026-11-18 (Harvard gate 9: Brooks, Guess & Sketch): the DOI record's authorship at the PI's name lists only another institution (OpenAlex
    derived it wrongly). The verdict is 'other_institution', which the page-1 steps then check; the school's own listing still wins."""
    import re
    from pi_hierarchy import AFF, INST, Name
    aff = re.compile(AFF['princeton'], re.I); inst = 'https://openalex.org/' + INST['princeton']
    nm = Name(['Ada Lovelace'])

    def work(*insts):
        return dict(id='https://openalex.org/W1', authorships=[dict(raw_author_name='Ada Lovelace', author=dict(id='https://openalex.org/A1', display_name='Ada Lovelace'),
                    institutions=list(insts), raw_affiliation_strings=[i['display_name'] for i in insts])])
    cornell = dict(id='https://openalex.org/I205783295', display_name='Cornell University', type='education', lineage=['https://openalex.org/I205783295'])
    princeton = dict(id=inst, display_name='Princeton University', type='education', lineage=[inst])
    assert D.doi_authorship_verdict(work(cornell), nm, inst, aff, 'princeton') == ('other_institution', None)
    assert D.doi_authorship_verdict(work(princeton), nm, inst, aff, 'princeton')[0] == 'school'
    assert D.doi_authorship_verdict(work(), nm, inst, aff, 'princeton') == (None, None)
    assert D.doi_authorship_verdict(dict(id='W2', authorships=[]), nm, inst, aff, 'princeton') == (None, None)


def test_pmlr_alternate_pdf_locations():
    assert D.pdf_alternates('http://proceedings.mlr.press/v51/basse16a.html')[0] == 'https://proceedings.mlr.press/v51/basse16a.pdf'
    assert D.pdf_alternates('https://proceedings.mlr.press/v235/pu24c.html')[1] == 'https://raw.githubusercontent.com/mlresearch/v235/main/assets/pu24c/pu24c.pdf'
    assert D.pdf_alternates('https://openreview.net/forum?id=abc') == []
