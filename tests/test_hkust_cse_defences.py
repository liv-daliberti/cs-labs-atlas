"""HKUST CSE qualifying / proposal / thesis event pages as dated student-supervisor pairs (tools/hkust_cse_defences.py, R-STU-29)."""
import hkust_cse_defences as D

PIS = [dict(pi='Huamin QU 屈華民', names=['Huamin Qu'], departments=['CSE'], periods=[dict(start='2006', end=None)]),
       dict(pi='Kai CHEN 陳凱', names=['Kai Chen'], departments=['CSE'], periods=[dict(start='2019-01', end=None)]),
       dict(pi='Fangzhen LIN 林方真', names=['Fangzhen Lin'], departments=['CSE'], periods=[]),
       dict(pi='Wei Wang', names=[], departments=['CSE'], periods=[dict(start='2010', end=None)]),
       dict(pi='Wei WANG 王威', names=[], departments=['CSE'], periods=[dict(start='2010', end=None)])]


def page(kind='PhD Thesis Defence', cand='Mr. Leixian SHEN', sups=('Prof. Huamin Qu (Supervisor)',), extra=''):
    com = ''.join(f'<br>{s}' for s in sups)
    return (f'<html><body><h1>{kind}</h1><p>Title: "A title"</p><p>By</p><p>{cand}</p><p>Abstract</p><p>Some abstract text.</p>'
            f'<p>Committee Members:\t{com}<br>Dr. Qifeng Chen (Chairperson)<br>Prof. Qiong Luo</p>{extra}<p>**** ALL are Welcome ****</p></body></html>')


def ev(raw, date='2021-08-12', n=1):
    return dict(url=f'https://cse.hkust.edu.hk/pg/defenses/Summer21/x{n}-{date}.html', sha256='ab' * 32, date=date, raw=raw)


def run(*events, today='2026-11-13'):
    return D.build(list(events), PIS, None, today=today)


def test_index_row_and_event_page_parse():
    idx = ('<table><tr><td>12 August 2021</td><td>Mr. Leixian SHEN</td><td>T</td><td>PhD\n Thesis Defence</td><td><a href="/pg/defenses/Summer21/lshen-12-08-2021.html">x</a></td></tr>'
           '<tr><td>1 June 2021</td><td>M</td><td>T</td><td>MPhil Thesis Defence</td><td><a href="a.html">x</a></td></tr></table>')
    r = D.parse_index(idx, 'https://cse.hkust.edu.hk/pg/defenses/Summer21/')
    assert [(e['date'], e['degree'], e['kind']) for e in r] == [('2021-08-12', 'PhD', 'Thesis Defence'), ('2021-06-01', 'MPhil', 'Thesis Defence')]
    assert r[0]['url'] == 'https://cse.hkust.edu.hk/pg/defenses/Summer21/lshen-12-08-2021.html'
    pe = D.parse_event(page())
    assert pe['candidate'] == 'Leixian SHEN' and pe['kind'] == 'Thesis Defence' and pe['supervisors'][0][0] == 'Huamin Qu'


def test_R_STU_29_supervisor_line_makes_a_dated_phd_pair_with_verbatim_quote():
    rows, held, cnt, _ = run(ev(page()))
    assert held == [] and rows[0]['pi'] == 'Huamin QU 屈華民'
    s = rows[0]['students'][0]
    assert s['name'] == 'Leixian SHEN' and s['role'] == 'phd' and s['years'] == [2021, 2021]
    flat = D.flat_text(page())
    assert all(part in flat for part in s['quote'].split(' [...] '))


def test_chairperson_and_members_are_not_supervisors():
    rows, held, cnt, un = run(ev(page(sups=())))
    assert rows == [] and cnt['no_supervisor'] == 1


def test_events_of_one_student_merge_into_one_year_span():
    rows, _, cnt, _ = run(ev(page('PhD Qualifying Examination'), '2019-05-01', 1), ev(page('PhD Thesis Proposal Defence'), '2021-02-01', 2), ev(page(), '2023-06-01', 3))
    s = rows[0]['students'][0]
    assert len(rows[0]['students']) == 1 and s['years'] == [2019, 2023] and len(s['other_sources']) == 2 and 'Thesis Defence' in s['note']
    assert s['url'].endswith('2023-06-01.html')


def test_mphil_future_and_old_events_are_not_rows():
    rows, held, cnt, _ = run(ev(page('MPhil Thesis Defence')), ev(page(), '2026-12-04', 2), ev(page(), '2014-05-01', 3))
    assert rows == [] and held == [] and cnt['not_phd_event'] == 1 and cnt['future_held'] == 1 and cnt['outside_window'] == 1


def test_initial_only_candidate_is_not_a_spelled_name():
    rows, _, cnt, _ = run(ev(page(cand='Mr. J. SMITH')))
    assert rows == [] and cnt['name_not_spelled'] == 1


def test_two_supervisors_give_a_row_only_for_the_named_pis_and_unknown_is_listed():
    rows, _, cnt, un = run(ev(page(sups=('Prof. Kai Chen (Supervisor)', 'Prof. Qiang Yang (Supervisor)'))))
    assert [r['pi'] for r in rows] == ['Kai CHEN 陳凱'] and 'Qiang Yang' in un and 'more than one supervisor' in rows[0]['students'][0]['note']


def test_a_name_two_pis_share_is_dropped():
    rows, _, cnt, un = run(ev(page(sups=('Prof. Wei Wang (Supervisor)',))))
    assert rows == [] and cnt['ambiguous'] == 1 and un['Wei Wang']['why'] == 'ambiguous'


def test_pi_without_a_period_record_or_before_its_start_is_held():
    rows, held, _, _ = run(ev(page(sups=('Prof. Fangzhen Lin (Supervisor)',))))
    assert rows == [] and held[0]['students'][0]['held_why'] == 'no_period_record'
    rows, held, _, _ = run(ev(page(sups=('Prof. Kai Chen (Supervisor)',)), '2017-03-01'))
    assert rows == [] and held[0]['students'][0]['held_why'] == 'event_year_before_period_start_2019'


def _lst(*years):
    return [dict(year=y, kind='dept_listing:CSE', url=f'https://web.archive.org/web/{y}/l', sha256='cd' * 32) for y in years]


def test_listing_window_is_same_year_only_and_cites_the_listing():
    pis = [dict(pi='Tong ZHANG', names=['Tong Zhang'], departments=['CSE'], periods=[], listings=_lst(2019, 2021)),
           dict(pi='Pan HUI', names=['Pan Hui'], departments=['CSE'], periods=[], listings=_lst(2016, 2026))]
    w = D.listing_window(pis[0])
    assert w['years'] == [2019, 2021] and D.listing_window(dict(listings=[])) is None
    assert D.in_window(w, 2019) and not D.in_window(w, 2020) and not D.in_window(w, 2022)    # no interval between listings, none after the last
    sup = ('Prof. Tong Zhang (Supervisor)',)
    evs = [ev(page('PhD Qualifying Examination', sups=sup), '2021-05-01', 1), ev(page(sups=sup), '2023-06-01', 2)]
    rows, held, _, _ = D.build(evs, pis, None, today='2026-11-13')                    # default: no record, held
    assert rows == [] and held[0]['students'][0]['held_why'] == 'no_period_record'
    rows, held, _, _ = D.build(evs, pis, None, today='2026-11-13', by_listing=True)   # the 2021 event has a 2021 listing, 2023 has none
    s = rows[0]['students'][0]
    assert held == [] and s['years'] == [2021, 2021] and s['other_sources'] == []
    assert s['period_basis']['facultyBasis'] == 'department_listing_same_year' and s['period_basis']['listings'][0]['year'] == 2021
    rows, held, _, _ = D.build([evs[1]], pis, None, today='2026-11-13', by_listing=True)
    assert rows == [] and held[0]['students'][0]['held_why'] == 'no_dated_listing_in_event_year_2023'
