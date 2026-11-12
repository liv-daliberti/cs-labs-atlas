"""tools/labpage_audit.py: paper matching (DOI, arXiv id, title, citation) and the reason assignment for listed students
and papers (docs/LAB-PAGES.md)."""
import sys

import pytest

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


def test_entry_years_table_row_and_defended():
    assert A.entry_years('| Stanford Univ. Medical Center | 2004 | Ming Lin', None)[0] == [None, 2004]
    assert A.entry_years(', Goldman Sachs. Defended on the 6th of January, 2012. [ Thesis ]', None)[0] == [None, 2012]


def test_parenthetical_name_is_stripped_and_gives_role():
    assert A.clean_parenthetical_name('Linfeng Li (postdoc) (co-advisor)') == ('Linfeng Li', 'postdoc')
    assert A.clean_parenthetical_name('Wei Liu (ROB)') == ('Wei Liu', None)
    assert A.clean_parenthetical_name('Prince (artist)') == ('Prince (artist)', None)  # one-word names stay


def test_committee_words_are_not_names():
    assert A.NAME_NOISE.search("Oral's Chair Ruixue Guo")
    assert A.NAME_NOISE.search('Reader Isabella Douglas')
    assert not A.NAME_NOISE.search('Ruixue Guo')


def test_coadviser_phrase_before_a_name():
    assert A.COADVISER_BEFORE.search('PhD Student, Robotics co-advised w/ ')
    assert A.COADVISER_BEFORE.search('Omar Shaikh PhD, Co-advise with ')
    assert A.COADVISER_BEFORE.search('Rubens Lacouture (with ')
    assert not A.COADVISER_BEFORE.search('PhD Students Yulun ')


def test_reference_block_and_other_institution_marker():
    ref = ('Goncalves Filho, A. L., Longo, M. G., Conklin, J., Cauley, S. F., Polak, D., Liu, W., Setsompop, K., Schaefer, P. W., '
           'Huang, S. Y., Rapalino, O. 2021 Abstract')
    assert len(A.CITE_INITIALS.findall('Smith, J. K., Doe, A. B., Roe, C. D., and more')) >= 3
    assert A.OTHER_INST_AT.search('Haoyi Lin, Undergrad student @NUSRI, 2023').group(1) == 'NUSRI'
    assert ref


def test_date_is_not_a_year_range_and_link_marker_is_a_citation():
    assert A.entry_years('Page generated 2020-05-24 15:57:44 PDT, by jemdoc', None)[0] is None
    assert A.entry_years('(Postdoc, 2017-18)', None)[0] == [2017, 2018]
    assert A.CITATION_CONTEXT.search('Lexing Ying. A parallel method. SIAM Journal on Scientific Computing 36 (2014). [Link]')


def test_collaborator_prose_and_pre_window_capture():
    assert A.COLLAB_PROSE.search('I have had wonderful opportunities to collaborate with the PhD students (some current and some former): Lingqing')
    assert not A.COLLAB_PROSE.search('I advise the following PhD students: Alex Wang')
    assert A.WINDOW[0] == 2016


def test_admin_staff_and_affiliates_are_not_members():
    assert A.ADMIN_DESC.search('Position Secretary Office ME C2 389')
    assert A.ADMIN_DESC.search('Chris Downey Administrative Assistant')
    assert not A.ADMIN_DESC.search('Position Scientist Office ME C2')
    assert A.AFFILIATE_DESC.search('Research Affiliate, Berkman Klein Center')
    assert not A.AFFILIATE_DESC.search('Research Scientist, ICSI')


def test_courtesy_titles_bio_sentences_and_other_institution_roles():
    assert A.PROF_TITLE_DESC.search('(consulting professor).')
    assert A.PROF_TITLE_DESC.search('Professor, University of Toronto')
    assert not A.PROF_TITLE_DESC.search('PhD student, Computer Science')
    pre = 'I obtained my B.S. and M.S. degrees in EE from Bilkent University, where I worked with '
    m = list(A.BIO_TRIGGER.finditer(pre))
    assert A.BIO_TAIL.match('Orhan Arikan and ') is not None
    om = A.OTHER_INST_ROLE.search('Sarah Gonzalez MS Student MIT AeroAstro Aditi Gupta')
    assert om and om.group(1) == 'MIT'
    assert not A.OTHER_INST_ROLE.search('Xiangyu Peng MS Student UM Robotics Institute')


def test_cotaught_and_visiting_scientist_heading():
    assert A.COADVISER_BEFORE.search('Fall 2016: 10-601B Introduction to Machine Learning (Masters) , co-taught with ')
    assert A.FACULTY_HEAD.search('Visiting Scientists at NTT Research')
    assert A.FACULTY_HEAD.search('Collaborators')
    assert not A.FACULTY_HEAD.search('PhD Students')


def test_fellowship_names_are_noise():
    assert A.NAME_NOISE.search('William J. Happel Fellowship')
    assert A.NAME_NOISE.search('NSF Graduate Research Fellowship')
    assert not A.NAME_NOISE.search('William Happel')


@pytest.mark.parametrize('name,heading', [
    ('NUMA Architecture', 'Student Reports'),
    ('Schmidt Distinguished Talk', 'Washington People > Google Scholar Profile (citation data)'),
    ('Martin Saveski', 'Prospective Students/Postdocs/Interns > Meta'),
    ('Ravit Barak', 'postdoc positions'),
])
def test_report_and_recruiting_sections_cannot_supply_members(name, heading):
    assert A.nonmember_candidate(name, heading) is not None


@pytest.mark.parametrize('name,heading', [
    ('Peiqi Gao', 'Current PhD Students'),
    ('Jinyuan Li', 'PhD Students'),
    ('Chen Yang', 'PhD students'),
    ('Jin Zhang', 'Graduate Students > Heng Dong PhD Candidate'),
])
def test_current_member_rosters_survive_nonperson_filter(name, heading):
    assert A.nonmember_candidate(name, heading) is None


def test_archive_host_policy_uses_original_cdx_target():
    assert A.archive_original_url('https://web.archive.org/cdx/search/cdx?url=https%3A%2F%2Fblocked.edu%2Fpeople%2F*') == 'https://blocked.edu/people/'
    assert A.archive_original_url('https://web.archive.org/web/20200101000000id_/https://blocked.edu/people/a') == 'https://blocked.edu/people/a'
    assert A.archive_original_url('https://school.edu/people/a') is None


def test_live_first_archive_miss_is_pending_not_a_request():
    class Cache:
        @staticmethod
        def cached(school, url):
            return None

    pending = set()
    url = 'https://web.archive.org/cdx/search/cdx?url=https://school.edu/lab'
    out = A.cached_archive_only(Cache(), 'u', url, pending)
    assert A.result_of(out) == 'wayback_deferred' and pending == {url}


def test_live_first_archive_hit_reuses_captured_bytes():
    class Cache:
        @staticmethod
        def cached(school, url):
            return {'status': 200, 'content': b'captured', 'sha256': 'known'}

    pending = set()
    assert A.cached_archive_only(Cache(), 'u', 'archive-url', pending)['content'] == b'captured'
    assert not pending


def test_live_first_transport_also_blocks_redirects_to_archive():
    from types import SimpleNamespace
    sent, pending = [], set()
    send = lambda request, **kw: sent.append(request.url)
    with pytest.raises(RuntimeError, match='archive network disabled'):
        A.live_only_send(send, pending, SimpleNamespace(url='https://web.archive.org/web/2020id_/https://u.edu/'))
    assert not sent and pending
    A.live_only_send(send, pending, SimpleNamespace(url='https://u.edu/'))
    assert sent == ['https://u.edu/']


def test_live_first_holds_redirect_before_unchecked_destination():
    from types import SimpleNamespace
    sent = []
    def send(request, **options):
        sent.append(request.url)
        assert options['allow_redirects'] is False
        return SimpleNamespace(status_code=302, headers={'Location': 'https://new-host.edu/private'})
    held = []
    response = A.live_only_send(send, set(), SimpleNamespace(url='https://u.edu/profile'), allow_redirects=True,
                               record_redirect=lambda *args: held.append(args))
    assert response.status_code == 302
    assert response.headers['Location'] == 'https://new-host.edu/private'
    assert sent == ['https://u.edu/profile']
    assert held == [('https://u.edu/profile', 302, 'https://new-host.edu/private')]


@pytest.mark.parametrize('status,body,allowed', [(302, b'', False), (429, b'', False), (None, b'', False),
                                               (200, b'<html>challenge</html>', False), (404, b'', True)])
def test_robots_redirect_failure_or_html_is_not_permission(tmp_path, status, body, allowed):
    import sqlite3
    import zlib
    from types import SimpleNamespace
    path = tmp_path/'cache.sqlite'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE captures (id INTEGER, url TEXT, capture_url TEXT, error TEXT, status INTEGER, content BLOB)')
        db.execute('INSERT INTO captures VALUES (1,?,NULL,?,?,?)', ('https://u.edu/robots.txt', 'timeout' if status is None else None,
                                                                 status, zlib.compress(body)))
    kit = SimpleNamespace(store=path, school='u', lpcap=SimpleNamespace(DBS={'u': str(path)}))
    assert A.Kit._ai_allowed(kit, 'https://u.edu/profile') is allowed


def test_live_refusal_is_shared_and_blocks_later_requests(tmp_path):
    from types import SimpleNamespace
    path = tmp_path / 'denials.json'
    sent = []
    def send(request, **kw):
        sent.append(request.url)
        return SimpleNamespace(status_code=403)
    options = {'denied': lambda host: A.live_denials(path).get(host),
               'record_denial': lambda host, status: A.remember_live_denial(host, status, path)}
    request = SimpleNamespace(url='https://u.edu/faculty/a')
    A.live_only_send(send, set(), request, **options)
    assert A.live_denials(path)['u.edu']['status'] == 403
    with pytest.raises(RuntimeError, match='previously refused'):
        A.live_only_send(send, set(), SimpleNamespace(url='https://u.edu/faculty/b'), **options)
    assert sent == ['https://u.edu/faculty/a']


def test_school_web_import_ignores_legacy_page_container(tmp_path):
    import sqlite3
    from types import SimpleNamespace
    path = tmp_path / 'legacy.sqlite'
    with sqlite3.connect(path) as con:
        con.execute('CREATE TABLE pages (url TEXT)')
    # No lpcap attribute: an unsupported source must return before opening a writer.
    assert A.Kit.import_school_web(SimpleNamespace(school='old'), str(path), ['https://u.edu/']) == 0


def test_live_first_named_agent_host_exclusion_is_not_path_specific():
    assert A.names_project_agents('User-agent: ClaudeBot\nDisallow: /api\n')
    assert A.names_project_agents('user-agent: anthropic-ai # model bot\nAllow: /\n')
    assert not A.names_project_agents('User-agent: *\nDisallow: /admin\n')


def test_named_agent_exclusion_survives_http_https_archive_variant(tmp_path, monkeypatch):
    import sqlite3
    import zlib
    from types import SimpleNamespace
    path = tmp_path / 'captures.sqlite'
    with sqlite3.connect(path) as con:
        con.execute('CREATE TABLE captures (id INTEGER, url TEXT, capture_url TEXT, status INTEGER, content BLOB, error TEXT)')
        con.execute('INSERT INTO captures VALUES (1,?,NULL,200,?,NULL)',
                    ('https://u.edu/robots.txt', zlib.compress(b'User-agent: ClaudeBot\nDisallow: /api\n')))
    monkeypatch.setenv('CS_ATLAS_LABPAGE_LIVE_ONLY', '1')
    kit = SimpleNamespace(store=path, school='u', lpcap=SimpleNamespace(DBS={'u': str(path)}))
    assert not A.Kit._ai_allowed(kit, 'http://u.edu/lab/')


def test_page_evidence_uses_an_existing_archive_when_live_bytes_are_absent():
    from types import SimpleNamespace
    url = 'https://u.edu/ada/'
    capture = 'https://web.archive.org/web/20250101000000id_/' + url
    row = {'url': url, 'capture_url': capture, 'sha256': 'a' * 64,
           'content': b'<title>Ada Example</title>'}
    kit = SimpleNamespace(
        stored=lambda source: (row, {'html': 'Ada Example research group'}) if source == capture else (None, None),
        src_of=lambda source: capture,
        lpcap=SimpleNamespace(decode=lambda b: b.decode(), collapse=lambda s: ' '.join(s.split())))
    evidence, title = A.page_evidence(kit, url, ['Ada Example'])
    assert evidence['sha256'] == 'a' * 64 and evidence['capture_url'] == capture
    assert title == 'Ada Example'
    kit.host_use = lambda host: 'none'
    assert A.page_evidence(kit, url, ['Ada Example']) == (None, '')


def test_live_redirect_cannot_reach_a_wayback_only_host():
    from types import SimpleNamespace
    sent = []
    policy = lambda host: 'wayback-only' if host == 'restricted.edu' else 'live'
    with pytest.raises(RuntimeError, match='previously refused'):
        A.live_only_send(lambda request, **kw: sent.append(request.url), set(),
                         SimpleNamespace(url='https://restricted.edu/redirected-page'),
                         denied=lambda host: A.transport_policy_denied(policy, host))
    assert sent == []
    assert A.transport_policy_denied(lambda h: 'none', 'blocked.edu')
    assert not A.transport_policy_denied(lambda h: 'live', 'allowed.edu')


MEMBER_CARDS_HTML = '''<div class="member-category">Ph.D. Students</div><ul>
<li class="member-item"><span class="member-avatar">ZJ</span><div class="member-body"><div class="member-head"><span class="member-name">Zhenglong Jin</span>
<span class="member-role-tag phd">Ph.D.</span></div><div class="member-advisor">(w/ Prof. Ying Liu)</div><div class="member-footer"><span class="member-period">2023 – now</span></div></div></li>
<li class="member-item"><span class="member-avatar">SL</span><div class="member-body"><div class="member-head"><span class="member-name">Shiming Liu</span>
<span class="member-role-tag phd">Ph.D.</span></div><div class="member-advisor"></div><div class="member-footer"><span class="member-period">2021 – 2025</span></div></div></li></ul>
<div class="member-category">Master Students</div><ul>
<li class="member-item"><span class="member-avatar">JS</span><div class="member-body"><div class="member-head"><span class="member-name">Junzhe Sun</span>
<span class="member-role-tag master">Master</span></div><div class="member-advisor"></div><div class="member-footer"><span class="member-period">2024 – now</span></div></div></li></ul>'''


def test_member_item_cards_read_each_cards_own_tag_adviser_and_period():
    cs = A.member_item_cards(MEMBER_CARDS_HTML)
    assert [(c['name'], c['tag'], c['advisor'], c['years'], c['head']) for c in cs] == [
        ('Zhenglong Jin', 'Ph.D.', '(w/ Prof. Ying Liu)', [2023, None], 'Ph.D. Students'),
        ('Shiming Liu', 'Ph.D.', '', [2021, 2025], 'Ph.D. Students'),
        ('Junzhe Sun', 'Master', '', [2024, None], 'Master Students')]


def test_apply_member_card_sets_role_years_and_an_own_quote():
    c = dict(A.member_item_cards(MEMBER_CARDS_HTML)[0], ptxt='ZJ Zhenglong Jin Ph.D. (w/ Prof. Ying Liu) 2023 – now SL Shiming Liu')
    x = dict(name='Zhenglong Jin', desc='Ph.D. (w/ Prof. Ying Liu) 2023 – now SL', head='Ph.D. Students', quote='Zhenglong Jin Ph.D', years=None, role=None)
    A.apply_member_card(x, c, lambda t: (None, None))
    assert x['years'] == [2023, None] and x['quote'] == 'Zhenglong Jin Ph.D. (w/ Prof. Ying Liu) 2023 – now'


@pytest.mark.parametrize('desc,head,role', [
    ('(MPhil student, HKUST (GZ) RBM, co-supervised with Prof. Mingming Fan, Fall 2022 - Summer 2024, PhD @ ETH)', 'Past members', 'masters'),
    ('(Exchange student, undergraduate from X, Fall 2018)', 'Past members', 'visiting'),
    ('(Exchange, undergrad from Y, Summer 2016)', 'Past members', 'visiting'),
    ('(RA, 2025-2026), now a PhD student in our group', 'Postgraduate Researchers', 'other'),
    ('(Research intern, graduate student from HKUST, Summer 2024)', 'Past members', 'other'),
    ('(Research intern, undergraduate student from HKUST, Summer 2024)', 'Past members', 'undergraduate'),
    ('(UGVIS, 2024)', 'Undergraduate Researchers', 'visiting'),
    ('(RA 2026, PhD@University of Cambridge)', 'Honorable Alumni', 'other'),
    ('(UG Intern, 2019-2021)', 'Alumni', 'undergraduate'),
    ('(PGVIS, 2025)', 'Postgraduate Researchers', 'visiting'),
    ('(Computer Science and Engineering, 2022)', 'M.Phil. (Master of Philosophy) Students: > )', 'masters'),
    ('(PhD student, Fall 2021 - Fall 2025)', 'Past members', None),
    ('(Visiting intern, graduate student from Harvard, Summer 2024)', 'Past members', None)])
def test_label_role_first_label_decides(desc, head, role):
    assert A.label_role(desc, head) == role


def test_started_in_year_is_an_open_start_and_nested_brackets_keep_the_range():
    assert A.entry_years('(PhD, started in 2025, primary advisor Prof. X )', 'Current graduate students :') == ([2025, None], 'stated_in_entry')
    assert A.entry_years('(MPhil student, HKUST (GZ) RBM, co-supervised with Prof. Mingming Fan, Fall 2022 - Summer 2024, PhD @ ETH)', 'Past members')[0] == [2022, 2024]


def test_citation_tail_and_quote_localisation():
    assert A.citation_fragment_item('), San Francisco') and A.citation_fragment_item(') . DOI website . · Pei Wang')
    assert not A.citation_fragment_item('Pei Wang (PhD student)')
    x = dict(name='Chaobo Jia', desc='(UGVIS, 2024)', quote='Ivan (Yin Fung) Lok (UROP, 2025) Li Zhang (UROP, 2025) Chaobo Jia', qkind='heading..name')
    A.localize_quote(x, 'Yuhua Zhao (UROP, 2024) Chaobo Jia (UGVIS, 2024) Sirui Xie (UGVIS, 2023)')
    assert x['quote'] == 'Chaobo Jia (UGVIS, 2024)'


def test_a_quoted_paper_title_in_the_entry_is_a_bibliography_line():
    assert A.citation_fragment_item('Wei Fu, Jiaxuan Gao, Xujie Shen, “ AReaL: A Large-Scale Asynchronous RL System ”, 2025')
    assert not A.citation_fragment_item('Wei Fu (PhD student, 2025)', '(PhD student, 2025)')


def test_alumni_card_with_current_position_takes_the_stays_own_postdoc_role():
    d = 'Current position: Chief scientist, Differential Robotics November 2024 - August 2025 The Hong Kong University of Science and Technology Postdoctoral fellow in Electronic and Computer Engineering Ph.D., Zhejiang University'
    assert A.label_role(d, 'Alumni') == 'postdoc'
    assert A.label_role('Current position: Postdoctoral fellow, HKUST Thesis title: X September 2021 - August 2025 HKUST Ph.D. in Robotics', 'Alumni') is None


def test_registered_people_page_is_honoured_by_discovery():
    from types import SimpleNamespace
    checks, pages = [], []
    kit = SimpleNamespace(get=lambda u: dict(status=200, content=b'x', capture_url=None, sha256='h'))
    ctx = dict(registered={'P': dict(url='https://lab.github.io/', people_page='https://lab.github.io/student/')})
    chosen = dict(lab_site='https://lab.github.io/', people_page=None)
    add = lambda *a, **k: checks.append(a)
    assert A.apply_registered_people_page(kit, ctx, 'P', 'https://lab.github.io/', chosen, pages, add)
    assert chosen['people_page'] == 'https://lab.github.io/student/' and pages == [('people', 'https://lab.github.io/student/')]
    # another host, an already-chosen page and a failed fetch change nothing
    c2 = dict(people_page=None)
    assert not A.apply_registered_people_page(kit, ctx, 'P', 'https://other.org/', c2, [], add) and c2['people_page'] is None
    bad = SimpleNamespace(get=lambda u: dict(status=404, content=b'', capture_url=None, sha256=None))
    assert not A.apply_registered_people_page(bad, ctx, 'P', 'https://lab.github.io/', c2, [], add) and c2['people_page'] is None


def test_a_bare_role_heading_right_before_a_name_is_that_names_role():
    seg = 'Student roster updated: 2026-10-20 Ph.D Student Master Haoran Wang'
    assert A.role_from_preceding_heading(seg[-30:]) == 'masters'


def test_primary_adviser_elsewhere_and_co_supervision():
    assert A.primary_adviser_other('(PhD, started in 2025, primary advisor Prof. Guoming Tang )', 'Jiyang Liu (PhD', 'Qiong LUO')
    assert not A.primary_adviser_other('(PhD, started in 2024, co-advised by Prof. Xiaojuan Ma )', 'Gongyao Jiang (PhD', 'Qiong LUO')
    assert not A.primary_adviser_other('(PhD, advisor Prof. Qiong Luo)', 'X (PhD', 'Qiong LUO')
    assert not A.advised_by_other('(PhD, started in 2024, co-advised by Prof. Xiaojuan Ma )', 'Gongyao Jiang (PhD', 'Qiong LUO')
    assert A.advised_by_other('(PhD, advised by Alexandre Jacquillat)', '', 'Someone Else')


def test_author_lists_followed_by_a_title_are_not_rosters():
    pt = 'Honorable Alumni 2025 Wei Fu, Jiaxuan Gao, Xujie Shen, Chen Zhu, Zhiyu Mei, “ AReaL: Large-Scale Asynchronous Reinforcement Learning ” arXiv 2025'
    assert A.author_list_item('Wei Fu, Jiaxuan Gao, Xujie Shen, Chen Zhu, Zhiyu Mei,', pt)
    pt2 = 'Current students Ada Lovelace, Alan Turing, Grace Hopper, Edsger Dijkstra Alumni Bob Jones (PhD 2020)'
    assert not A.author_list_item('Ada Lovelace, Alan Turing, Grace Hopper, Edsger Dijkstra', pt2)


def test_a_roster_entry_with_a_bracketed_descriptor_is_not_an_author_list():
    assert not A.author_list_item('Youhe Jiang (RA 2026, PhD', 'Youhe Jiang (RA 2026, PhD@University of Cambridge) \u201c A Long Quoted Title Of A Paper \u201d')
    assert A.author_list_item('Simon C. H. Yu, Wilbur C. K. Wong, and', 'Simon C. H. Yu, Wilbur C. K. Wong, and Albert Chung, \u201c A Long Title About Something \u201d Proceedings')


def test_han_glued_cells_read_name_plus_role_word_before_the_alumni_heading():
    t = '顾扬博士生 华勤博士生 贾博涵博士生 许圣林硕士生 高剑奇博士后 全部毕业生 总计114个 汪毅 博士 华东计算所 李某某博士生'
    cs = A.han_glued_cells(t)
    assert [(c['name'], c['role']) for c in cs] == [('顾扬', 'phd'), ('华勤', 'phd'), ('贾博涵', 'phd'), ('许圣林', 'masters'), ('高剑奇', 'postdoc')]
    assert not A.han_glued_cells('顾扬博士生 华勤博士生')   # fewer than three cells: not a roster


def test_cmu_round9_entry_rules():
    assert A.strip_program_label('Seungjoo Lee Societal Computing') == 'Seungjoo Lee'
    assert A.strip_program_label('Riku Arakawa Human-Computer Interaction') == 'Riku Arakawa'
    assert A.strip_program_label('Machine Learning') == 'Machine Learning'
    assert A.entry_years('(PhD Student at Yale, with Zhong Shao); following position: since 2019 Researcher at Facebook', 'Former Group Members') == (None, 'none')
    assert A.leading_other_institution('(PhD Student at Yale, with Zhong Shao); following position: since 2019 Researcher at Facebook', 'cmu') == 'Yale'
    assert A.leading_other_institution('(Purdue) Summer 2021', 'cmu')
    assert A.leading_other_institution('(2021-2022. Former master’s student. CVD, MBZUAI.)', 'cmu') == 'CVD, MBZUAI'
    assert not A.leading_other_institution('(2017-2022. Former PhD Student. CPCB, CBD, CMU.)', 'cmu')
    assert not A.leading_other_institution('(PhD Student at Carnegie Mellon University)', 'cmu')
    assert A.YEAR_ONLY_ENTRY_RX.match('(2021)') and not A.YEAR_ONLY_ENTRY_RX.match('(PhD, 2021)')


def test_tsinghua_defect_rules():
    assert A.role_if_none('(Master) Chao Xu', 'Students') == 'masters'
    assert A.role_if_none('(PhD) x', 'Students') == 'phd'
    assert A.role_if_none('Postdoctor, March 2023~ Department of Electronic Engineering', 'Members') == 'postdoc'
    assert A.role_if_none('', 'Members > Postdoctors') == 'postdoc'
    assert A.role_if_none('(working closely on the project)', 'Students') is None
    assert A.pub_item_head('Ju Ren, Ph.D. > Book/Book Chapter') and not A.pub_item_head('Ph.D. Students')
    assert A.entry_years('(2022, w/ Ke Xu)', 'Past PhD Students:') == ([None, 2022], 'stated_in_entry')


def test_name_first_cards_and_cohort_years():
    t = ('Yuxuan Yang 2024 Master’s Student Bowen Zeng 2024 Master’s Student Zonghao Chen 2025 Master’s Student Jianfeng Zhang 2025 Master’s Student Co-supervised '
         'Zimo Liu 2026 Master’s Student Jun Zhang 2020 Direct-entry PhD graduate Co-supervised Yujia Ding 2021 Master’s graduate')
    cs = {c['name']: c for c in A.name_first_cards(t)}
    assert cs['Zonghao Chen']['years'] == [2025, None] and cs['Zimo Liu']['years'] == [2026, None] and not cs['Zimo Liu']['advisor']
    assert cs['Jianfeng Zhang']['advisor'] == 'Co-supervised' and cs['Zonghao Chen']['quote'] == 'Zonghao Chen 2025 Master’s Student'
    assert cs['Jun Zhang']['years'] == [None, 2020] and cs['Jun Zhang']['alumni'] and cs['Yujia Ding']['alumni']
    assert not A.name_first_cards('Yuxuan Yang 2024 Master’s Student Bowen Zeng 2024 Master’s Student')
    assert A.entry_years('2023 Direct-entry PhD Student Co-supervised', 'Phd Students') == ([2023, None], 'stated_in_entry')
    assert A.entry_years('(B.S from UESTC, Ph.D started 2023)', 'Ph.D. Students')[0] == [2023, None]
    assert A.label_role('(Zhejiang University)', 'Under Graduate Students') == 'undergraduate'
