"""R-STU-14 (capture-year dating) and R-STU-15 (surname-only advisers) helpers of tools/labpage_students_school.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import labpage_students_school as L  # noqa: E402

URL = 'https://web.archive.org/web/{}id_/https://lab.example.edu/people'


def rec(pi, name, ts, section='Graduate Students', quote=None, role='phd', rc='undated_cannot_place'):
    return dict(pi=pi, audited_at='2026-10-31T00:00:00', students=dict(missing_from_build=[
        dict(name=name, role=role, reason_code=rc, section=section, url=URL.format(ts), sha256='ab' * 32, quote=quote or f'{section} {name}')]))


def test_capture_year():
    assert L.capture_year(URL.format('20190615185603')) == 2019
    assert L.capture_year('https://lab.example.edu/people', 2026) == 2026
    assert L.capture_year('https://lab.example.edu/people') is None


def test_undated_member_counts_in_the_capture_year_and_spans_captures():
    rows = L.undated_capture_rows([rec('Ann Lee', 'Bo Chen', '20190101000000'), rec('Ann Lee', 'Bo Chen', '20230101000000')])
    assert len(rows) == 1 and rows[0]['years'] == [2019, 2023] and rows[0]['years_basis'] == 'capture_date'


def test_undated_rule_keeps_only_student_heading_phd_members_with_a_member_list_quote():
    ok = rec('Ann Lee', 'Bo Chen', '20200101000000')
    alumni = rec('Ann Lee', 'Cy Diaz', '20200101000000', section='Past Members')
    masters = rec('Ann Lee', 'Di Evans', '20200101000000', role='masters')
    other_reason = rec('Ann Lee', 'Ed Fox', '20200101000000', rc='genuinely_missing')
    paper_list = rec('Ann Lee', 'Fay Gu', '20200101000000', quote='PhD Students Anna Li (2020) Publications Approximation with Fay Gu')
    placeholder = rec('Y Z', 'Gil Han', '20200101000000')
    out = L.undated_capture_rows([ok, alumni, masters, other_reason, paper_list, placeholder])
    assert [r['student'] for r in out] == ['Bo Chen']


def test_undated_rule_needs_the_pi_in_the_page_head():
    r = rec('Ann Lee', 'Bo Chen', '20200101000000')
    assert L.undated_capture_rows([r], lambda sha: 'Center team page: Lead Zed Kim, Ann Lee') != []
    assert L.undated_capture_rows([r], lambda sha: 'Center team page: Lead Zed Kim') == []
    assert L.undated_capture_rows([r], lambda sha: None) == []


FLAT = ("ME Graduate Students Program Any PhD MSE First Name Last Name Advisor's Last Name Nassim Abdul Samad nassimab PhD Research Advisor: Stefanopoulou "
        "Julianna Abel jmariee PhD Research Advisor: Brei, Luntz Adrian Adames aadames PhD Research Advisor: Awtar Clover Aguayo caguayo MSE "
        "Mohamadreza Ahmadi mrahmadi PhD Research Advisor: Okwudire")


def test_surname_entries_parse_one_adviser_list_per_phd_entry():
    got = {n: a for n, _, a, _ in L.surname_entries(FLAT)}
    assert got == {'Nassim Abdul Samad': ['Stefanopoulou'], 'Julianna Abel': ['Brei', 'Luntz'], 'Adrian Adames': ['Awtar'], 'Mohamadreza Ahmadi': ['Okwudire']}
    assert all(q.startswith(n) for n, _, _, q in L.surname_entries(FLAT))


def test_surname_resolves_only_when_exactly_one_listed_faculty_member_in_that_department_and_year():
    listed = [('Huei Peng', 'Peng', 'ME', 2017), ('Jun Ni', 'Ni', 'ME', 2017), ('Ann Li', 'Li', 'ME', 2017), ('Bo Li', 'Li', 'ME', 2017),
              ('Gábor Orosz', 'Orosz', 'ME', 2017), ('Cy Peng', 'Peng', 'CSE', 2017)]
    assert L.resolve_surname('Peng', 'ME', 2017, listed) == 'Huei Peng'
    assert L.resolve_surname('Li', 'ME', 2017, listed) is None          # two
    assert L.resolve_surname('Brei', 'ME', 2017, listed) is None        # none
    assert L.resolve_surname('Peng', 'ME', 2018, listed) is None        # no listing that year
    assert L.resolve_surname('Peng', 'ECE', 2017, listed) is None       # never across departments
    assert L.resolve_surname('OROSZ', 'ME', 2017, listed) == 'Gábor Orosz'
    assert L.resolve_surname('Orosz', 'ME', 2017, listed) == 'Gábor Orosz'
