"""Page-1 ties (2026-11-12, stage-7 C items): the read goes past 'Abstract', collective and numbered footnotes tie, curly apostrophes and
accents fold, and a work keeps one tie per PI. Each text is the real head of the paper that was missed; strictness is unchanged (the
affiliation must still name the school for that PI)."""
import re
import pytest

import pi_fulltext_affiliation as F
import pi_hierarchy as h
from pihier.names import tie_for_pi


def aff(school):
    return re.compile(h.AFF[school], re.I)


def test_numbered_company_author_cannot_borrow_a_coauthor_school_email():
    page = ('Recommendation Paper Jiacheng Li1, Julian McAuley2 '
            'j9li@eng.ucsd.edu, jumcaule@amazon.com '
            '1 University of California, San Diego 2 Amazon, United States Abstract Results.')
    assert F.tie(page, [('julian', 'mcauley')], aff('ucsd')) == (None, [])
    assert F.tie(page, [('jiacheng', 'li')], aff('ucsd'))[0] == 'marker'


def test_unresolved_numeric_marker_does_not_borrow_another_author_school():
    page = ('Recommendation Paper Jiacheng Li1, Julian McAuley² '
            'j9li@eng.ucsd.edu 1 University of California, San Diego Abstract Results.')
    assert F.tie(page, [('julian', 'mcauley')], aff('ucsd')) == (None, [])


def test_numeric_inline_school_and_dual_affiliations_remain_supported():
    inline = 'Recommendation Paper Julian McAuley1 Department of Computing University of California, San Diego Abstract Results.'
    assert F.tie(inline, [('julian', 'mcauley')], aff('ucsd'))[0] == 'marker'
    dual = ('Recommendation Paper Julian McAuley1,2 '
            '1 University of California, San Diego 2 Amazon, United States Abstract Results.')
    assert F.tie(dual, [('julian', 'mcauley')], aff('ucsd'))[0] == 'marker'


def test_correspondence_star_with_inline_school_remains_supported():
    page = ('Recommendation Paper Julian McAuley* University of California, San Diego '
            '* Corresponding author Abstract Results.')
    assert F.tie(page, [('julian', 'mcauley')], aff('ucsd'))[0] is not None


def test_stacked_affiliation_labels_do_not_become_author_markers():
    page = ("Grammar-Aligned Decoding Taylor Berg-Kirkpatrick2 Nadia Polikarpova2 Loris D'Antoni1 "
            '1 2 University of Wisconsin-Madison University of California San Diego '
            '{kpark247, ldantoni}@wisc.edu {tberg, npolikarpova}@ucsd.edu Abstract Results.')
    assert F.tie(page, [('loris', 'dantoni')], aff('ucsd')) == (None, [])
    # Flattened stacked columns cannot resolve either institution safely.
    assert F.tie(page, [('nadia', 'polikarpova')], aff('ucsd')) == (None, [])


@pytest.mark.parametrize('stored_metadata', [True, False])
def test_retie_retracts_obsolete_positive_without_altering_primary_bytes(monkeypatch, stored_metadata):
    import json
    import sqlite3
    import zlib
    con = sqlite3.connect(':memory:')
    con.execute('create table works(id text primary key, body blob)')
    con.execute('create table pages(work text primary key, arxiv text, url text, status text, pdf_sha256 text, page1 blob, school_named int, quote text, fetched_at text)')
    work = dict(id='W1', authorships=[dict(raw_author_name='Julian McAuley')])
    body = zlib.compress(json.dumps(work).encode())
    text = zlib.compress(b'Paper Jiacheng Li1, Julian McAuley2 j9li@eng.ucsd.edu 1 University of California, San Diego 2 Amazon, United States Abstract Results.')
    if stored_metadata:
        con.execute('insert into works values (?,?)', ('W1', body))
    else:
        import cs_related_candidates
        monkeypatch.setattr(cs_related_candidates, 'works', lambda school: iter([work]))
    con.execute('insert into pages values (?,?,?,?,?,?,?,?,?)', ('W1', '2204.01839', 'https://example.test/paper.pdf', 'ok', 'original-pdf-sha', text, 1, '{"how":"near","quotes":["Julian McAuley2 j9li@eng.ucsd.edu"]}', 'original-fetch-time'))
    monkeypatch.setattr(F, 'db', lambda school: con)
    monkeypatch.setattr(F, 'read', lambda path: [dict(pi='Julian McAuley', names=['Julian McAuley'])])
    F.retie('ucsd')
    row = con.execute('select status, school_named, quote, pdf_sha256, page1, fetched_at from pages').fetchone()
    assert row == ('ok_untied', 0, None, 'original-pdf-sha', text, 'original-fetch-time')
    assert con.execute('select body from works').fetchone() == ((body,) if stored_metadata else None)


POPA = ('Membrane: A Cryptographic Access Control System for Data Lakes Sam Kumar UCLA Samyukta Yagati UC Berkeley Conor Power UC Berkeley '
        'arXiv:2509.08740v1 [cs.CR] 10 Sep 2025 Abstract Raluca Ada Popa UC Berkeley 2019, for example, an attacker bypassed a firewall')


def test_affiliation_after_the_word_abstract():
    assert F.tie(POPA, [('raluca', 'popa')], aff('berkeley'))[0] == 'near'
    # a school named only later in the sentence, far from the name, is not a tie
    far = 'A Title Raluca Ada Popa Abstract We study caching in data centers and many other things, with a sentence that goes on; UC Berkeley is where we ran it.'
    assert F.tie(far, [('raluca', 'popa')], aff('berkeley'))[0] is None


def test_collective_footnote_all_authors():
    page = ('Strong Formulations Jisun Lee, Hyungki Im, Alper Atamtürk Abstract—We study the problem. '
            'All authors are with the Department of Industrial Engineering and Operations Research, University of California, Berkeley, CA 94720.')
    how, q = F.tie(page, [('alper', 'atamturk')], aff('berkeley'))
    assert how == 'footnote' and 'University of California, Berkeley' in q[1]
    other = page.replace('University of California, Berkeley', 'Seoul National University')
    assert F.tie(other, [('alper', 'atamturk')], aff('berkeley'))[0] is None


def test_collective_footnote_with_a_marker():
    page = ('Back on Track Colton Crosby1∗ , Hao Wang1,2∗ , Mac Schwager1 and Somil Bansal1 Fig. 1: We address deployment. '
            '∗ These authors contributed equally to this work. 1 The authors are associated with the Aeronautics and Astronautics Department, Stanford University. '
            '{cjcrosby, schwager}@stanford.edu 2 The author is associated with the Ming Hsieh Department, University of Southern California.')
    how, q = F.tie(page, [('mac', 'schwager')], aff('stanford'))
    assert how in ('marker', 'footnote') and 'Stanford University' in q[1]
    assert F.tie(page, [('hao', 'wang')], aff('stanford'))[0] in ('marker', 'footnote')   # marker 1 is on his byline too


def test_numbered_unit_footnote_beyond_the_head():
    page = ('HINT Kin Olivares1 * Artur Dubrawski 1 Abstract We present the Hierarchical Mixture Networks. * Equal contribution '
            '1 Machine Learning Department, Carnegie Mellon University, Pittsburgh, USA 2 Nixtla, Pittsburgh, PA, USA.')
    assert F.tie(page, [('artur', 'dubrawski')], aff('cmu'))[0] == 'footnote'


def test_curly_apostrophe_and_marker():
    page = ('LLM-Supported Translation Finnian Westenfelder1,2 , Erik Hemberg1 , Una-May O’Reilly1 , Silviu Chiricescu3 '
            '1 ALFA Group MIT-CSAIL, 2 Draper Scholar, 3 Charles Stark Draper Laboratory Abstract (Kerrisk, 2024).')
    assert F.tie(page, [('una', 'oreilly')], aff('mit'))[0] == 'marker'


def test_equal_contribution_note_is_still_not_a_tie():
    page = 'A title Jane Doe∗ John Roe Abstract text. ∗ Equal contribution. Stanford University and elsewhere.'
    assert F.tie(page, [('jane', 'doe')], aff('stanford'))[0] is None


def test_one_tie_per_pi():
    entry = dict(how='marker', quotes=['Md Tauhidul Islam1,* 1 ', '* correspondence: tauhid@stanford.edu'], url='u', pdf_sha256='s',
                 also=[dict(how='marker', quotes=['James Zou2,3,4 ', '2 Department of Electrical Engineering, Stanford University'])])
    assert tie_for_pi(entry, ['Md Tauhidul Islam'])['quotes'][0].startswith('Md Tauhidul')
    z = tie_for_pi(entry, ['James Zou'])
    assert z['quotes'][0].startswith('James Zou') and z['url'] == 'u'
    assert tie_for_pi(entry, ['Percy Liang']) is None


def test_candidates_consider_every_pi_authorship():
    """A later PI without an affiliation is a page-1 candidate even when an earlier PI on the byline lists an institution (Odysseus, Princeton)."""
    def au(i, inst=(), raw=()):
        return {'author': {'id': i}, 'institutions': list(inst), 'raw_affiliation_strings': list(raw)}
    w = {'authorships': [au('A1', ['Princeton University'], ['Princeton Language and Intelligence']), au('A2'), au('A3')]}
    assert F.unaffiliated_pi_authorship(w, {'A1', 'A2'})['author']['id'] == 'A2'
    assert F.unaffiliated_pi_authorship(w, {'A1'}) is None
    assert F.unaffiliated_pi_authorship({'authorships': [au('A2', raw=['x'])]}, {'A2'}) is None


def test_numbered_unit_footnote_accepts_a_blank_line_after_the_marker():
    # ICML 2024 Chen/Kwok: pdftotext places the affiliation marker on its own line.
    page = ('Efficient Pareto Manifold Learning\nWeiyu Chen 1 James T. Kwok 1\n'
            'Abstract We study multi-task learning.\n1\n\n'
            'Department of Computer Science and Engineering, The Hong\n'
            'Kong University of Science and Technology. Correspondence to Weiyu Chen.')
    how, quotes = F.tie(page, [('james', 'kwok')], aff('hkust'))
    assert how == 'footnote'
    assert 'Hong\nKong University of Science and Technology' in quotes[1]


def test_numbered_blank_line_footnote_does_not_borrow_the_next_authors_school():
    page = ('A research paper James T. Kwok1 Other Author2\nAbstract A method.\n'
            '1\n\nUniversity of Oxford.\n2\n\n'
            'Hong Kong University of Science and Technology.')
    assert F.tie(page, [('james', 'kwok')], aff('hkust'))[0] is None
    assert F.tie(page, [('other', 'author')], aff('hkust'))[0] == 'footnote'
