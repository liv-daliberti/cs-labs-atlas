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


def test_an_entry_placing_the_student_at_another_school():
    d = 'Jake is Ph.D. student in Neuroscience at UT Austin, co-supervised by Alex Huk.'
    m = A.ELSEWHERE_RX.search(d)
    assert m and m.group(1).startswith('UT Austin')
    m = A.ELSEWHERE_RX.search('Ning is a 3rd-year Ph.D. student in PNI at Princeton University.')
    assert m and A.re.search(A.SCHOOL_NAMES['princeton'], m.group(1))


def test_profile_subpages_and_institution_listings():
    assert A.is_profile('https://www.media.mit.edu/people/pattie/overview/', r'mit\.edu')
    lk = A.classify_links([('https://www.media.mit.edu/people/', 'People'), ('https://www.media.mit.edu/people/pattie/publications/', 'Publications')],
                          'https://www.media.mit.edu/people/pattie/overview/', r'mit\.edu')
    assert 'people' not in lk and lk.get('pubs') == ['https://www.media.mit.edu/people/pattie/publications/']


def test_shared_people_pages_are_counted_across_labs():
    disc = {'A': dict(chosen=dict(people_page='https://bliss.eecs.berkeley.edu/students.html')),
            'B': dict(chosen=dict(people_page='http://bliss.eecs.berkeley.edu/students.html/')),
            'C': dict(chosen=dict(people_page='https://lab-c.example.edu/people'))}
    assert A.shared_people_pages({}, disc) == {'bliss.eecs.berkeley.edu/students.html': 2}


def test_generic_school_pages_are_never_sites_on_strength_alone():
    assert A.GENERIC_PAGE_RX.search('/undergraduate/visit/') and A.GENERIC_PAGE_RX.search('/students/')
    assert not A.GENERIC_PAGE_RX.search('/view/ncclab/')


def _role_of():
    sys.path.insert(0, str(A.H / A.PM))
    import autom
    return autom._role


@pytest.mark.parametrize('desc,head,want', [
    ('(PhD student, MIT ORC, 2022 –) Brian Liu (PhD student, MIT ORC, 2021 –)', 'Current Students (PhD and Masters)', ([2022, None], 'stated_in_entry')),
    ('MIT Undergraduate Student, 2020 Deniz Erus MIT Undergraduate Student, 2023', 'MIT Undergraduate Student, SuperUROP 2024-2025', ([2020, 2020], 'stated_in_entry')),
    ('(Postdoc, 2010-2014). Now group leader', 'Postdocs', ([2010, 2014], 'stated_in_entry')),
    ('(Ph.D. in applied math 2014). Now Research Scientist', 'Ph.D. Students', ([None, 2014], 'stated_in_entry')),
    ('Juho Park received his B.S. degree in 2017 and his Ph.D. in 2022', 'Post-doctoral Scholars', (None, 'none')),
    ('Kim', 'Undergraduates > 2019', ([2019, 2019], 'section_year_heading')),
    ('Anushri is a 4th-year Ph.D. student', 'Graduate Students', (None, 'none')),
])
def test_entry_years_are_the_entrys_own(desc, head, want):
    assert A.entry_years(desc, head) == want


@pytest.mark.parametrize('desc,head,want', [
    ('(PhD student, MIT ORC, 2022 –)', 'Current Students (PhD and Masters)', ('phd', 'entry')),
    ('Juho Park received his B.S. degree from Seoul National University', 'Post-doctoral Scholars', ('postdoc', 'section_heading')),
    ('Xiaolong Huang received his Ph.D. in Electrical Engineering', 'Post-doctoral Scholars', ('postdoc', 'section_heading')),
    ('MIT Undergraduate Student, 2020', 'Students', ('undergraduate', 'entry')),
    ('(student, UC Berkeley, PhD 2021)', 'Students and postdocs', ('phd', 'entry')),
    ('Kathryn is our lab manager and is interested in', 'People', (None, 'none')),
])
def test_entry_role_never_comes_from_bio_words(desc, head, want):
    assert A.entry_role(desc, head, _role_of()) == want


def test_listed_titles_lose_a_run_in_byline():
    p = dict(pi='William Freeman', names=['William T. Freeman'])
    t = 'Reasoning about physical interactions with object-centric models Michael Janner, Sergey Levine, William T Freeman, Joshua B Tenenbaum'
    assert A.clean_listed_title(t, p) == ('Reasoning about physical interactions with object-centric models', 'author_tail_cut')
    assert A.clean_listed_title('Freeman, Joshua T', p) == ('Freeman, Joshua T', 'author_only')
    assert A.clean_listed_title('Learning to See by Moving', p) == ('Learning to See by Moving', None)
    assert A.clean_listed_title('Graph Neural Networks for Wireless Networks, Revisited', p)[1] is None


def test_a_degree_from_another_school_in_parentheses():
    m = A.DEGREE_AT_RX.search('(PhD 2016 (DTU), Position: Research Scientist, Mosek)')
    assert m and m.group(1) == 'DTU' and not A.re.search(A.SCHOOL_NAMES['berkeley'], m.group(1))


def test_season_ranges_and_institution_listings():
    assert A.entry_years(', UG researcher, Fall 2019 - Summer 2020 Manu', None) == ([2019, 2020], 'stated_in_entry')
    assert A.INSTITUTION_LISTING.search('/people/alumni') and A.INSTITUTION_LISTING.search('/people/')
    assert not A.INSTITUTION_LISTING.search('/people/anind-dey') and not A.INSTITUTION_LISTING.search('/lab/people')
    assert A._HOST_INST.search('safari.ethz.ch') and A._HOST_INST.search('cse.ucsd.edu')


@pytest.mark.parametrize('row,want', [
    (dict(title='Implementation science for software engineering (keynote)', doi='10.1145/3238147.3264581'), 'talk_or_abstract_title'),
    (dict(title='Machine Learning Informed Decision-Making', doi='10.5465/ambpp.2021.264'), 'meeting_abstract:doi'),
    (dict(title='How Representative Are Web Crawlers', doi='10.5281/zenodo.22683521'), 'repository_record'),
    (dict(title='Extreme Parkour with Legged Robots', doi='10.48550/arxiv.2309.14341'), None),
])
def test_recovered_rows_that_are_not_papers(row, want):
    assert A.addition_not_a_paper(row) == want


def test_two_digit_range_ends():
    assert A.entry_years('(2017-18) — Assistant Professor, University of Illinois', None) == ([2017, 2018], 'stated_in_entry')
    assert A.entry_years('(2020-22) — Assistant Professor', None) == ([2020, 2022], 'stated_in_entry')


@pytest.mark.parametrize('x,want', [
    (dict(head='Graduate Students', desc='Shanka Subhra Mondal'), False),
    (dict(head='Current Graduate Students', desc=''), True),
    (dict(head='Current Members > PhD Students', desc=''), False),  # only the entry's own section heading counts
    (dict(head='PhD Students', desc='is a 3rd-year PhD student'), True),
    (dict(head='Students', desc='Ph.D. in ORFE, Princeton University, expected 2028'), True),
    (dict(head='M.S.E. & M.F. Students', desc=', Benheim Center for Finance'), False),
])
def test_current_marker_is_the_entrys_own(x, want):
    assert A.current_marker(x) == want


def test_a_current_and_former_heading_is_no_current_marker():
    assert not A.current_marker(dict(head='Current and Former Ph.D. Students', desc=', Tech Startup'))
    assert A.current_marker(dict(head='Current and Former Ph.D. Students', desc='Ph.D. in Economics, Princeton University, in progress, expected 2027'))


def _restamp_setup(tmp_path, old, new):
    import hashlib
    import json
    d = tmp_path / 'x'
    d.mkdir()
    ob = json.dumps(old).encode()
    (d / 'labpage-additions.json').write_bytes(json.dumps(new).encode())
    acc = dict(additions_sha256=hashlib.sha256(ob).hexdigest(), students=dict(accepted=True, round=1, counts=dict(proposed=2)),
               papers=dict(accepted=True, round=1, counts=dict(proposed=1)))
    (d / 'labpage-acceptance.json').write_text(json.dumps(acc))
    return d, old


def _adds(students, papers):
    return dict(generated_at='t', students=students, papers=papers)


S = lambda n, role='phd': dict(pi='P', name=n, role=role, years=None)  # noqa: E731
W = lambda k: dict(pi='P', key=k, title='T' + k, year=2020, doi=None)  # noqa: E731


def test_restamp_subset_keeps_acceptance(tmp_path):
    import json
    old = _adds([S('Ann Lee'), S('Bo Wu')], [W('a')])
    new = _adds([S('Ann Lee')], [])
    d, old = _restamp_setup(tmp_path, old, new)
    rep = A.restamp('x', root=d, old=old)
    acc = json.loads((d / 'labpage-acceptance.json').read_text())
    assert rep['kinds']['students']['result'] == 'subset' and rep['kinds']['students']['removed'] == 1
    assert acc['students']['accepted'] and acc['papers']['accepted'] and acc['students']['restamped_from']['removed'] == 1
    assert A.restamp('x', root=d, old=old)['status'] == 'current'


def test_restamp_added_or_changed_row_needs_a_new_round(tmp_path):
    import json
    old = _adds([S('Ann Lee'), S('Bo Wu')], [W('a')])
    new = _adds([S('Ann Lee', role='postdoc'), S('Bo Wu'), S('Cy Xu')], [W('a')])
    d, old = _restamp_setup(tmp_path, old, new)
    rep = A.restamp('x', root=d, old=old)
    acc = json.loads((d / 'labpage-acceptance.json').read_text())
    assert rep['kinds']['students']['result'] == 'needs_new_round' and not acc['students']['accepted']
    assert acc['papers']['accepted'] and rep['kinds']['papers']['result'] == 'subset'


def test_membership_only_withholds_roles_and_stamps(tmp_path):
    import hashlib
    import json
    d = tmp_path / 'y'
    d.mkdir()
    (d / 'labpage-additions.json').write_text(json.dumps(_adds([S('Ann Lee', 'postdoc')], [W('a')])))
    (d / 'labpage-acceptance.json').write_text(json.dumps(dict(papers=dict(accepted=True), students=dict(accepted=False))))
    A.membership_only('y', dict(round=3, seed=1, sampled=20, years_withheld=False), root=d)
    adds = json.loads((d / 'labpage-additions.json').read_text())
    acc = json.loads((d / 'labpage-acceptance.json').read_text())
    assert adds['students'][0]['role'] is None and adds['students'][0]['role_basis'] == 'withheld_role_round_failed'
    assert acc['students']['scope'] == 'membership_only' and acc['students']['accepted']
    assert acc['additions_sha256'] == hashlib.sha256((d / 'labpage-additions.json').read_bytes()).hexdigest()
