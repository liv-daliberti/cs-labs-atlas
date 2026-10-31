"""tools/labpage_audit.py: paper matching (DOI, arXiv id, title, citation) and the reason assignment for listed students
and papers (docs/LAB-PAGES.md)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import labpage_audit as A  # noqa: E402

LAB = [
    dict(title='Deep Probabilistic Graphical Modeling', doi='10.1000/abc.1', year=2020),
    dict(title='The Dynamic Embedded Topic Model', doi=None, year=2019,
         editions=[dict(doi='10.48550/arxiv.1907.05545', title='The Dynamic Embedded Topic Model')]),
    dict(title='Efficient and Guaranteed-Safe Non-Convex Trajectory Optimization with Constrained Diffusion Model', year=2024),
]


def test_match_by_doi_first():
    idx = A.PaperIndex(LAB)
    how, row = idx.match(dict(title='A different title on the page', links=['https://doi.org/10.1000/ABC.1']))
    assert how == 'doi' and row['year'] == 2020


def test_match_by_arxiv_id_from_link_or_edition():
    idx = A.PaperIndex(LAB)
    how, row = idx.match(dict(title='DETM', links=['https://arxiv.org/pdf/1907.05545v2']))
    assert how == 'arxiv' and row['year'] == 2019


def test_match_by_normalized_title():
    idx = A.PaperIndex(LAB)
    assert idx.match(dict(title='Deep probabilistic graphical modeling.'))[0] == 'title'


def test_match_title_inside_citation_and_prefix():
    idx = A.PaperIndex(LAB)
    q = ('A. Li, Z. Ding, A. B. Dieng. Efficient and Guaranteed-Safe Non-Convex Trajectory Optimization with Constrained '
         'Diffusion Model. arXiv 2024')
    assert idx.match(dict(title='A. Li, Z. Ding', quote=q))[0] == 'title_in_citation'
    assert idx.match(dict(title='Efficient and Guaranteed-Safe Non-Convex Trajectory Optimization'))[0] == 'title_prefix'


def test_no_match_for_short_or_other_titles():
    idx = A.PaperIndex(LAB)
    assert idx.match(dict(title='Topic Model')) == (None, None)
    assert idx.match(dict(title='Something else entirely', links=['https://doi.org/10.1000/other'])) == (None, None)


def test_entry_ids_ignore_arxiv_dois_as_dois():
    dois, axs = A.entry_ids(dict(links=['https://doi.org/10.48550/arXiv.2403.05571', 'https://dl.acm.org/doi/10.1145/3292500.3330701']))
    assert dois == {'10.1145/3292500.3330701'} and axs == {'2403.05571'}


@pytest.mark.parametrize('status,junk,year,start,want', [
    ('accepted', None, 2020, 2015, 'genuinely_missing'),
    ('pi_not_on_byline', None, 2020, 2015, 'pi_not_author'),
    ('outside_appointment', None, 2012, 2015, 'from_previous_school'),
    ('outside_appointment', None, 2024, 2015, 'outside_appointment'),
    ('other_institution', None, 2020, 2015, 'other_institution_affiliation'),
    ('no_school_evidence', None, 2020, 2015, 'no_school_affiliation_evidence'),
    ('unresolved', None, 2020, 2015, 'unresolved_metadata'),
    ('candidate', None, 2020, 2015, 'not_yet_resolved'),
    ('held_by_resolved_id', None, 2020, 2015, 'matched'),
    ('junk', 'thesis', 2020, 2015, 'not_a_paper'),
    ('junk', 'talk', 2020, 2015, 'not_a_paper'),
    ('junk', 'filter_or_heading', 2020, 2015, 'parse_artifact'),
    ('junk', 'fragment', 2020, 2015, 'parse_artifact'),
])
def test_paper_reason(status, junk, year, start, want):
    assert A.paper_reason(status, junk, year, start) == want


def test_every_paper_reason_is_in_the_vocabulary():
    for st in list(A.RECOVER_STATUS) + ['outside_appointment']:
        r = A.paper_reason(st, None, 2020, 2015)
        assert r == 'matched' or r in A.PAPER_REASONS
    for j in A.RECOVER_JUNK:
        assert A.paper_reason('junk', j, 2020, 2015) in A.PAPER_REASONS


@pytest.mark.parametrize('cand,start,alumni_ok,want', [
    (dict(flags=['excluded-heading']), 2015, False, 'not_a_student'),
    (dict(flags=['is-a-PI']), 2015, False, 'not_a_student'),
    (dict(reviewer_drop=True), 2015, False, 'not_a_student'),
    (dict(single_token=True), 2015, False, 'name_unresolved'),
    (dict(years=[2008, 2013]), 2005, False, 'outside_2016_2026'),
    (dict(years=[None, 2017]), 2019, False, 'at_previous_school'),
    (dict(is_cap=True, under_people_heading=False), 2015, False, 'not_in_people_section'),
    (dict(alumni=True), 2001, False, 'undated_alumni_cannot_place'),
    (dict(alumni=True), 2021, True, None),
    (dict(alumni=True, seen_current_2016=True), 2001, False, None),
    (dict(years=[2018, None]), 2015, False, None),
])
def test_student_reason(cand, start, alumni_ok, want):
    assert A.student_reason(cand, start, alumni_ok) == want


@pytest.mark.parametrize('desc,want', [
    ('(Ph.D. in applied math 2014). Now Research Scientist', [None, 2014]),
    ('(Postdoc, 2010-2014). Now group leader', [2010, 2014]),
    ('(visiting postdoc, 2023)', [None, 2023]),
    ('is a 4th-year Ph.D. student', None),
])
def test_paren_years(desc, want):
    assert A.paren_years(desc) == want


def test_lab_site_vs_homepage():
    assert A.is_lab_site('Pillow Lab: home page', 'http://pillowlab.princeton.edu')
    assert A.is_lab_site('Vertaix', 'https://vertaix.princeton.edu/', 'https://vertaix.princeton.edu/people')
    assert not A.is_lab_site('Aarti Gupta', 'https://www.cs.princeton.edu/~aartig/', 'https://www.cs.princeton.edu/~aartig/')


def test_profile_pages_are_not_sites():
    assert A.is_profile('https://www.cs.princeton.edu/people/profile/gkol', r'princeton\.edu')
    assert A.is_profile('https://ece.princeton.edu/people/naveen-verma', r'princeton\.edu')
    assert not A.is_profile('https://www.cs.princeton.edu/~aartig/', r'princeton\.edu')
    assert not A.is_profile('https://nverma.princeton.edu/group-members', r'princeton\.edu')


def test_spread_picks_first_middle_last():
    assert A.spread(['2016', '2018', '2020', '2022', '2024']) == ['2016', '2020', '2024']
    assert A.spread(['2019', '2021']) == ['2019', '2021']


def test_wayback_links_resolve_against_the_original_page():
    row = dict(url='https://ece.princeton.edu/people-list/faculty', capture_url='https://web.archive.org/web/2021id_/https://ece.princeton.edu/people-list/faculty',
               final_url='https://web.archive.org/web/2021id_/https://ece.princeton.edu/people-list/faculty')
    assert A.link_base(row, 'x') == 'https://ece.princeton.edu/people-list/faculty'
    assert A.unwayback('https://web.archive.org/web/20160330172825id_/http://ee.princeton.edu:80/people/faculty') == \
        'http://ee.princeton.edu/people/faculty'


def test_pi_quote_is_verbatim():
    t = 'Welcome to the lab of Professor Aarti Gupta at Princeton University, Computer Science.'
    q = A.pi_quote(t, ['Aarti Gupta'])
    assert q in t and 'Gupta' in q and len(q) <= 160


@pytest.mark.nfs
def test_typo_pair_within_a_lab():
    sys.path.insert(0, str(A.H / A.PM))
    import names
    assert A.typo_pair(names, 'Mikio Aio', 'Mikio Aoi')
    assert not A.typo_pair(names, 'Yi Li', 'Yu Li')
    assert not A.typo_pair(names, 'Adam Charles', 'Adam Chang')


def test_social_hosts_are_not_sites_but_google_sites_are():
    assert not A.social('https://sites.google.com/view/ncclab/')  # Cohen's lab: Google Sites is a lab site
    assert A.social('https://scholar.google.com/citations?user=x')
    assert A.social('https://x.com/someone') and not A.social('https://latex.com/')
    assert A.social('http://isni.org/isni/0000000045035005') and A.social('https://viaf.org/viaf/78465839')
    assert not A.social('https://raphael-group.github.io/') and A.social('https://github.com/raphael-group')


class _Kit:
    """The two Kit methods adapter_plan uses, without stores: every page is stored live."""
    def src_of(self, u):
        return u


def _ctx(family, **kw):
    c = dict(school='x', cfg=dict(family=family), pubs_rows={}, pubs_rows_pages={}, manual={})
    c.update(kw)
    return c


PI = dict(pi='Ada Lovelace', names=['Ada Lovelace'], periods=[dict(start='2018', end=None)], listings=[])


def test_cmu_adapter_splits_live_pages_from_wayback_captures():
    prior = dict(lab_site='https://ada.example.org', people_page='https://ada.example.org/people',
                 people_pages=['https://ada.example.org/people',
                               'https://web.archive.org/web/20190101000000id_/https://ada.example.org/people',
                               'https://ada.example.org/alumni'],
                 pubs_pages=[dict(url='https://ada.example.org/pubs', entries=10)], students=[])
    plan = A.adapter_plan(_Kit(), _ctx('cmu'), PI, prior)
    assert plan['people'] == ['https://ada.example.org/people', 'https://ada.example.org/alumni']
    assert plan['wb_caps'] == {'https://ada.example.org/people': ['https://web.archive.org/web/20190101000000id_/https://ada.example.org/people']}
    assert plan['alumni_pages'] == ['https://ada.example.org/alumni']
    assert [x['pubs_page'] for x in plan['pubs']] == ['https://ada.example.org/pubs']
    assert plan['strict'] and plan['prior_reviewed'] and plan['min_last_year'] == 2018 and plan['wb_from'] == 2018


def test_eb_adapter_reads_pubs_rows_and_reviewer_overrides():
    prior = dict(lab_site='https://lab.example.ch', people_page='https://inst.example.ch/all-members', students=[])
    ctx = _ctx('eb', pubs_rows_pages={'Ada Lovelace': ['https://lab.example.ch/publications']},
               manual={'Ada Lovelace': dict(people=[], drop=['Not A Member'])})
    plan = A.adapter_plan(_Kit(), ctx, PI, prior)
    assert plan['people'] == []  # the reviewer rejected the discovered institute-wide page
    assert plan['drop'] == ['Not A Member']
    assert [x['pubs_page'] for x in plan['pubs']] == ['https://lab.example.ch/publications']
    ctx['manual']['Ada Lovelace']['no_pubs'] = True
    assert A.adapter_plan(_Kit(), ctx, PI, prior)['pubs'] == []


def test_prior_parse_rows_back_an_unparseable_publications_page():
    ctx = _ctx('st', pubs_rows={'Ada Lovelace': [dict(title='T1', url='https://a/pubs'), dict(title='T2', page_url='https://a/pubs2')]})
    assert [r['title'] for r in A.prior_rows_for(ctx, 'Ada Lovelace', 'https://a/pubs2')] == ['T2']


def test_wayback_only_and_never_used_results_are_named():
    assert A.result_of(dict(error='wayback-only-host')) == 'wayback_only_host'
    assert A.result_of(dict(error='off-limits-host')) == 'off_limits'


@pytest.mark.nfs
def test_michigan_charter_never_uses_deep_blue_and_reads_umich_from_wayback():
    import school_config as SC
    assert SC.host_use('michigan', 'deepblue.lib.umich.edu') == 'none'
    assert SC.host_use('michigan', 'news.umich.edu') == 'none' and SC.host_use('michigan', 'record.umich.edu') == 'none'
    assert SC.host_use('michigan', 'cse.engin.umich.edu') == 'wayback-only'
    assert SC.host_use('michigan', 'some-lab.engin.umich.edu') == 'wayback-only'


def test_pi_left_year_from_periods_or_stale_listings():
    assert A.pi_left_year(dict(periods=[dict(start='2008', end='2016-06-30')], listings=[])) == 2016
    assert A.pi_left_year(dict(periods=[dict(start='2008', end=None)], listings=[])) is None
    assert A.pi_left_year(dict(periods=[], listings=[dict(year=2016), dict(year=2017)])) == 2017  # Aaronson: MIT listings end 2017
    assert A.pi_left_year(dict(periods=[], listings=[dict(year=2025), dict(year=2026)])) is None
