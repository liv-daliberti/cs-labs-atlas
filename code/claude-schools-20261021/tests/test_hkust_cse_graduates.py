"""HKUST CSE Graduate Placements cards as dated student-adviser pairs (tools/hkust_cse_graduates.py, R-STU-26 proposed)."""
import hkust_cse_graduates as G


def card(name, deg_year, sup, job='Researcher<br>Huawei<br>Hong Kong'):
    return (f'<a class="card news-card graduate-card"href="https://x.example/"><div class="content inline-block"><p class="people-name"><!-- -->{name}</p>'
            f'<p class="people-info1"> {job} </p><p class="people-info2">{deg_year}<br>\n Supervised by {sup}</p></div></a>')


PIS = [dict(pi='Huamin QU 屈華民', names=['Huamin Qu'], departments=['CSE']), dict(pi='Bo LI 李波', names=['Bo Li'], departments=['CSE']),
       dict(pi='Wei Wang', names=[], departments=['CSE']), dict(pi='Wei WANG 王威', names=[], departments=['CSE']),
       dict(pi='Nina Ece', names=['Nina Ece'], departments=['ECE'])]


def run(*cards):
    return G.evidence('<html><body>' + ''.join(cards) + '</body></html>', 'https://cse.hkust.edu.hk/pg/ourgraduates/', 'ab' * 32, PIS)


def test_single_supervisor_row_years_and_quote():
    rows, counts, _ = run(card('Leixian SHEN', 'PhD 2026', 'Huamin QU'))
    assert counts['rows'] == 1 and rows[0]['pi'] == 'Huamin QU 屈華民'
    s = rows[0]['students'][0]
    assert s['name'] == 'Leixian SHEN' and s['years'] == [2026, 2026] and s['role'] == 'phd'
    assert s['quote'].endswith('PhD 2026 Supervised by Huamin QU')


def test_co_supervision_names_each_matching_pi_only():
    rows, counts, _ = run(card('Chen CHEN', 'PhD 2018', 'Bo LI and Qiang YANG'))
    assert [r['pi'] for r in rows] == ['Bo LI 李波'] and 'Qiang YANG' in rows[0]['students'][0]['note']


def test_old_masters_and_non_cse_cards_are_not_rows():
    rows, counts, _ = run(card('A OLD', 'PhD 2013', 'Huamin QU'), card('B MASTER', 'MPhil 2020', 'Huamin QU'), card('C ECE', 'PhD 2020', 'Nina ECE'))
    assert rows == [] and counts['outside_window'] == 1 and counts['not_phd'] == 1 and counts['no_pi'] == 1


def test_title_stripped_and_unknown_supervisor_skipped():
    rows, counts, _ = run(card('D X', 'PhD 2019', 'Dr. Huamin QU'), card('E Y', 'PhD 2019', 'Someone ELSE'))
    assert len(rows) == 1 and counts['no_pi'] == 1


def test_a_name_two_pis_share_is_dropped():
    rows, counts, skipped = run(card('F Z', 'PhD 2021', 'Wei WANG'))
    assert rows == [] and counts['ambiguous'] == 1 and skipped[0]['why'] == 'ambiguous'


def test_R_STU_26_card_is_a_dated_pair_and_co_supervision_needs_the_pi_named():
    rows, counts, _ = run(card('G H', 'PhD 2022', 'Qiang YANG and Huamin QU'))
    assert [r['pi'] for r in rows] == ['Huamin QU 屈華民'] and rows[0]['students'][0]['years'] == [2022, 2022]
    rows, counts, _ = run(card('I J', 'PhD 2022', 'Qiang YANG and Zed OTHER'))
    assert rows == [] and counts['no_pi'] == 1
