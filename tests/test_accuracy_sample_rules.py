"""The ten rules the 2026-10-29 accuracy sample proposed (R1-R10, work/accuracy/ACCURACY.md), each on the real item that
failed, plus the recorded data issues (Manning's row, the MIT duplicate, Berkeley's reused person id, Shirley Wu)."""
import json
import re
from pathlib import Path

import pytest

import pi_fulltext_affiliation as F
import pi_hierarchy as h

WORK = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def cases():
    return json.loads((Path(__file__).resolve().parent / 'fixtures' / 'accuracy-sample-cases.json').read_text())


def by_oa(cases, w):
    return next(r for r in cases['not_papers'] if r['oa'].endswith(w))


# ---- R1 non-papers (R-PAP-18) ------------------------------------------------------------------------------------

@pytest.mark.parametrize('w, tag', [
    ('W7153821956', 'workshop_proposal'),      # 1  Sarah Fox, CHI 2026 'Workshop on Developing Standards ...'
    ('W2769791602', 'editorial'),              # 3  Boulic, 'Foreword to the Special Section on Motion in Games 2016'
    ('W7221524172', 'oberwolfach_report'),     # 4  Viazovska, Oberwolfach Reports
    ('W7127958959', 'software_record'),        # 5  Payer, Zenodo software (CLower artifact)
    ('W2677610438', 'award_announcement'),     # 6  Berger, 2017 ISCB senior-scientist award
    ('W2605429657', 'highlights_column'),      # 9  Berger, 'Principles of Systems Biology, No. 31'
    ('W4412975911', 'workshop_proposal'),      # 17 Koedinger, L@S 2025 '...: A Collaborative Workshop with ...'
    ('W6929199287', 'dagstuhl_report'),        # 19 Payer, Dagstuhl Seminar 21481
    ('W4408441842', 'tribute'),                # 20 Emer, 'Derek Chiou' (IEEE Micro tribute)
    ('W6948057322', 'dagstuhl_report'),        # 21 Kochenderfer, Dagstuhl Seminar 24361
    ('W4310263535', 'erratum'),                # met in the student sample: Publisher Correction
    ('W7128768787', 'repository_supplement'),  # Figshare 'Supplement 1: ...'
    ('W7139980406', 'software_record'),        # Zenodo software
    ('W4255267968', 'repository_supplement'),  # protocols.io
    ('W3136338351', 'machine_translation'),    # JST machine translation of OpenPose
])
def test_r1_not_papers(cases, w, tag):
    assert h.not_a_paper(by_oa(cases, w)) == tag


@pytest.mark.parametrize('title, typ', [
    ('Puzzles in Memory of Solomon Golomb', 'article'),                      # 'In memory of' inside a paper title
    ('Remembering the “when”: Hebbian memory models for the time of past events', 'article'),
    ('Contraction theory for nonlinear stability analysis and learning-based control: A tutorial overview', 'article'),
    ('Tutorial on the generation of ergodic trajectories with projection-based gradient descent', 'article'),
    ('MedAL: Accurate and Robust Deep Active Learning for Medical Image Analysis', 'conference-paper'),
    ('On the Integrality Gap of the Prize-Collecting Steiner Forest LP', 'conference-paper'),
    ('Art Gallery', 'article'), ('Silence Localization', 'conference-paper'), ('Ray Tracing Harmonic Functions', 'article'),
    ('Kenneth Arrow\'s Last Theorem', 'article'),
    ('Big data approaches for novel mechanistic insights on sleep and circadian rhythms: a workshop summary', 'article'),
    ('Obituaries can popularize science and health', 'article'),
])
def test_r1_keeps_real_papers(title, typ):
    assert h.not_a_paper(dict(title=title, type=typ, venue='Some Journal', doi='10.1/x', byline=['A B', 'C D'],
                              authorship=dict(position='last'))) is None


def test_r1_tribute_forms():
    assert h.person_name_title('Derek Chiou')
    assert not h.person_name_title('Art Gallery')
    row = dict(type='article', venue='Nature', doi='10.1038/530282a', byline=['Patrick Winston'], authorship=dict(position='first'))
    assert h.not_a_paper(dict(row, title='Marvin L. Minsky (1927–2016)')) == 'tribute'
    assert h.not_a_paper(dict(row, title='Pink slime journalism on Facebook: advertisement trends (2019–2024)')) is None


# ---- R2 meeting abstracts (R-PAP-19) ----------------------------------------------------------------------------

@pytest.mark.parametrize('w, tag', [
    ('W3111311984', 'meeting_abstract:venue'),          # 2  Ydstie, AGU Fall Meeting 2019
    ('W2752575772', 'meeting_abstract:doi'),            # 7  Golland, Stroke supplement 'Abstract 136: ...'
    ('W4401572680', 'meeting_abstract:venue'),          # 8  Adalsteinsson, ISMRM
    ('W3002031535', 'meeting_abstract:venue'),          # 10 Oliver, Bulletin of the APS
    ('W2609132648', 'meeting_abstract:venue'),          # 11 Englund, Bulletin of the APS
    ('W4401571924', 'meeting_abstract:venue'),          # 15 Setsompop, ISMRM
    ('W2734831869', 'meeting_abstract:single_author'),  # 16 Verma, IWASI 2017 keynote abstract
])
def test_r2_meeting_abstracts(cases, w, tag):
    assert h.not_a_paper(by_oa(cases, w)) == tag


def test_r2_cs_conference_abstracts_stay():
    # EC, FPGA, SIGCSE one-page abstracts with co-authors are CS conference publications and stay
    r = dict(title='Optimal Auctions via the Multiplicative Weight Method', type='conference-abstract',
             venue='ACM Conference on Economics and Computation (EC)', doi='10.1145/3033274.3085126', byline=['A B', 'C D'],
             authorship=dict(position='last'))
    assert h.not_a_paper(r) is None


# ---- R3 page 1 before the unaffiliated-advisee route (R-PAP-20) -------------------------------------------------

def test_r3_pi0_is_physical_intelligence(cases):
    x = cases['pi0']
    assert x['status'] == 'ok_absent'
    assert h.page1_elsewhere(x['status'], x['page1'], 'berkeley', x['title'])     # 12 Levine, pi-0


def test_r3_keeps_pages_without_affiliations_and_school_pages(cases):
    plain = 'Guiding the search in continuous state-action spaces arXiv:1711.01391v1 [cs.AI] 4 Nov 2017 Beomjoon Kim, Leslie Pack Kaelbling and Tomas Lozano-Perez Abstract We ...'
    assert h.page1_elsewhere('ok_absent', plain, 'mit', 'Guiding the search in continuous state-action spaces') is None
    assert h.page1_elsewhere('ok_absent', 'A paper Jane Doe Berkeley AI Research Abstract x', 'berkeley') is None   # the school, loosely
    assert h.page1_elsewhere('ok_untied', 'A paper Jane Doe Google Abstract x', 'berkeley') is None               # school named: kept
    assert h.page1_elsewhere(None, None, 'berkeley') is None                                                   # unchecked: kept


# ---- R4 chapters without a venue fold by DOI prefix (R-PAP-21) ---------------------------------------------------

def test_r4_rubinstein_chapters_fold_into_the_book(cases):
    rows = [dict(r) for r in cases['rubinstein']]
    assert sum(r['type'] == 'book-chapter' for r in rows) == 16 and any(r['oa'].endswith('W2950014110') for r in rows)   # 13
    kept, folded, _ = h.fold_books(rows, 'stanford')
    assert [r['type'] for r in kept] == ['book'] and folded == 16
    assert h.doi_book_prefix('10.1145/3241304.3241313') == '10.1145/3241304'
    assert h.doi_book_prefix('10.1007/978-3-030-12345-6_5') == '10.1007/978-3-030-12345-6'


# ---- R5 dissertations (R-PAP-22) --------------------------------------------------------------------------------

def test_r5_kundaje_dissertation(cases):
    r = by_oa(cases, 'W7204929729')                                        # 14 Minji Kang's dissertation, Kundaje adviser
    assert r['byline'][0].startswith('Kang') and h.not_a_paper(r) == 'dissertation'
    own = dict(r, byline=['Kundaje, Anshul'], authorship=dict(position='first'))
    assert h.not_a_paper(own) is None                                       # a PI's own thesis would stay


# ---- R6 bare unit names (R-PAP-25) ------------------------------------------------------------------------------

def test_r6_units():
    assert h.norm_unit('Operations Research & Financial Engineering') == h.norm_unit('Department of Operations Research and Financial Engineering')
    assert h.generic_unit('Department of Computer Science') and h.generic_unit('Electrical and Computer Engineering')
    assert not h.generic_unit('Center for Information Technology Policy') and not h.generic_unit('Operations Research & Financial Engineering')
    aff = re.compile(h.AFF['princeton'], re.I)
    assert h.units_in('Center for Information Technology Policy, Princeton University, Princeton, NJ', aff) == ['center for information technology policy']


def test_r6_sircar_and_mittal():
    sircar_units = {h.norm_unit('Operations Research and Financial Engineering')}
    # 24 Sircar, SIAM Review 2017: his own (census) unit, his reviewed author id
    assert h.bare_unit_school(['Operations Research & Financial Engineering'], sircar_units, sircar_units, anchored_ok=True, school_co=False)
    # 22 Mittal, NeurIPS 2019: CITP is a Princeton unit (not his census department); Bhagoji lists Princeton
    school_units = {h.norm_unit('Center for Information Technology Policy'), h.norm_unit('Electrical and Computer Engineering')}
    ece = {h.norm_unit('Electrical and Computer Engineering')}
    assert h.bare_unit_school(['Center for Information Technology Policy'], ece, school_units, anchored_ok=True, school_co=True)
    assert not h.bare_unit_school(['Center for Information Technology Policy'], ece, school_units, anchored_ok=True, school_co=False)
    # a generic name alone is any school's: it needs a school co-author even for an anchored PI
    cs = {h.norm_unit('Computer Science')}
    assert not h.bare_unit_school(['Computer Science'], cs, cs, anchored_ok=True, school_co=False)
    assert h.bare_unit_school(['Department of Computer Science'], cs, cs, anchored_ok=False, school_co=True)
    assert not h.bare_unit_school(['Computer Science'], set(), cs, anchored_ok=True, school_co=True)    # not the PI's unit


# ---- R7 doubled roster tokens (R-STU-05) ------------------------------------------------------------------------

def test_r7_doubled_tokens():
    assert h.dedupe_tokens('Arjun Nitin Nitin Bhagoji') == 'Arjun Nitin Bhagoji'                       # 22 Mittal's roster
    assert h.dedupe_tokens('Li Li') == 'Li Li'                                                           # two-token names stay
    assert h.dedupe_tokens('Jean Jean-Pierre Martin') == 'Jean Jean-Pierre Martin'
    assert h.full_pair(h.dedupe_tokens('Arjun Nitin Nitin Bhagoji')) == h.full_pair(h.byline_name('Bhagoji, Arjun Nitin'))


# ---- R8 page 1 for DBLP-anchored works (R-PAP-24) ---------------------------------------------------------------

def test_r8_fox_footnote_tie(cases):
    x = cases['fox']                                                       # 25 Fox, JCTB 2025: '∗ Stanford University, ...'
    how, quotes = F.tie(re.sub(r'\s+', ' ', x['page1']), [('jacob', 'fox')], re.compile(h.AFF['stanford'], re.I))
    assert how == 'footnote' and quotes[0].startswith('Jacob Fox') and 'Stanford University' in quotes[1]


def test_r8_footnote_is_not_an_equal_contribution_note():
    page = 'A title Jane Doe∗ John Roe Abstract text. ∗ Equal contribution. Stanford University and elsewhere.'
    assert F.tie(page, [('jane', 'doe')], re.compile(h.AFF['stanford'], re.I))[0] is None


# ---- R9 venue-version dating (R-PAP-26) -------------------------------------------------------------------------

def test_r9_engelhardt_ml4h(cases):
    x = cases['engelhardt']                                                # 26 arXiv v1 2021-10, ML4H 2023
    venues = {h.norm_title(d['title'].rstrip('.')): (d['year'], d['key']) for d in x['dblp']}
    date, by = h.venue_version_date(x['work'], venues)
    assert date == '2023' and by['dblp_key'] == 'conf/ml4h/MandyamJYLE23' and by['oa_date'] == '2021-10-06'


def test_r9_sandholm_kilthub_deposit(cases):
    x = cases['sandholm']                                                  # IJCAI 2009 deposited on KiltHub in 2018
    venues = {h.norm_title(d['title'].rstrip('.')): (d['year'], d['key']) for d in x['dblp']}
    w = dict(title=x['row']['title'], type='article', doi=x['row']['doi'], publication_year=2018, publication_date='2018-06-30',
             primary_location=dict(source=dict(type='repository', display_name='Figshare')))
    assert h.venue_version_date(w, venues)[0] == '2009'
    assert h.venue_version_date(dict(w, primary_location=dict(source=dict(type='journal'))), venues)[0] == '2018-06-30'  # a venue record keeps its date


# ---- R10 nicknames (R-LNK-04) -----------------------------------------------------------------------------------

def test_r10_izzy():
    assert h.nick_ok('izzy', 'izabel') and h.nick_ok('izzy', 'isabel')
    assert not h.given_conflict(['Izzy Aguiar'], 'Izabel Aguiar')         # 27 Ugander's student


# ---- recorded data issues -----------------------------------------------------------------------------------------

def test_manning_record_with_another_works_doi(cases):
    r = by_oa(cases, 'W3011573503')
    assert r['doi'] == '10.4230/oasics.slate.2023.2' and r['year'] == 2020 and h.doi_year_conflict(r)
    assert not h.doi_year_conflict(dict(r, type='preprint'))                # a preprint with its later venue DOI is normal
    assert not h.doi_year_conflict(dict(r, doi='10.4230/lipics.types.2016.11', year=2018))


def test_hyphenated_family_name_merges_within_a_lab():
    assert h.same_student('Pablo José. Ortiz-Lampier', 'Pablo Ortiz') and h.same_student('Pablo Ortiz', 'Pablo José Ortiz-Lampier')
    assert not h.same_student('Maria Ortiz-Lampier', 'Pablo Ortiz')


def test_pi_person_id_is_never_a_student():
    labs = {'Borivoje Nikolic': {'berkeley_fac_john-wright': dict(person='berkeley_fac_john-wright', name='John Wright', relations=[{'type': 'researched_advising'}])}}
    assert h.rekey_pi_person_ids(labs, {'berkeley_fac_john-wright'}, 'berkeley') == 1
    r = labs['Borivoje Nikolic']['ext:berkeley:john-wright']
    assert r['person'] == 'ext:berkeley:john-wright' and r['rekeyedFrom'] == ['berkeley_fac_john-wright']


def test_shirley_wu_reviewed_evidence():
    x = [c for c in json.loads((WORK / 'hierarchy/student-corrections.json').read_text())
         if c.get('student') == 'stanford_stu_shirley-yingxin-wu' and c.get('pi') == 'James Zou']
    assert len(x) == 1 and x[0]['action'] == 'replace_sources'
    src = x[0]['sources'][0]
    assert 'Zou, James' in src['quote'] and 'thesis advisor' in src['quote'] and re.fullmatch(r'[0-9a-f]{64}', src['sha256'])


# ---- evidence carried by links, and provenance ------------------------------------------------------------------

def test_relation_source_prefers_complete_sources():
    s = dict(relations=[dict(type='a', sources=[dict(url='u', sha256='', quote='')]),
                        dict(type='b', sources=[dict(url='u2', sha256='a' * 64, quote='Adviser: X')])])
    assert h.relation_source(s) == dict(relation='b', url='u2', sha256='a' * 64, quote='Adviser: X')
    assert h.best_sources([dict(url='u', sha256='b' * 64, statement='Joined MIT in 2007.')])[0]['quote'] == 'Joined MIT in 2007.'


def test_provenance_missing():
    import provenance
    assert provenance.missing(None) == list(provenance.REQUIRED)
    full = dict(code=dict(commit='c', dirty=False), rules=[1], openalex_sweep=dict(sha256='s', last_fetched='t'),
                dblp_dump=dict(date='d', md5='m'), dblp_persons=dict(sha256='s', modified='t'), pi_works=dict(sha256='s', modified='t'),
                reviewed_inputs={'a': 'b'})
    assert provenance.missing(full) == []
    assert provenance.missing(dict(full, code=dict(commit='c', dirty=True))) == ['code.diff_sha256']
