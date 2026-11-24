"""R-STU-18: only evidence-confirmed UChicago roster pairs (verdict true) become student relations."""
import collections
import json

import atlas_paths as P
import roster_pair_evidence as R
from pihier.students import RESEARCHED_FILES, researched

PAGE = 'Group Ann Lee (PhD 2021, co-advised with Bo Chen) Cy Dunn (PhD 2022) Ed Fox (PhD 2020)'
VERDICTS = dict(pairs=[
    dict(student='Ann Lee', pi='Pat Barber', roster_years=[2019, 2021], verdict='true', basis='listing', note='co-advised', sources=[dict(url='u1', quote='x')]),
    dict(student='Ann Lee', pi='Bo Chen', roster_years=[2019, 2021], verdict='true', basis='listing', note='', sources=[dict(url='u1', quote='x')]),
    dict(student='Cy Dunn', pi='Pat Barber', roster_years=[2022, 2022], verdict='unsettled', basis='none', note='', sources=[dict(url='u1', quote='x')]),
    dict(student='Ed Fox', pi='Pat Barber', roster_years=[2020, 2020], verdict='not', basis='other-adviser', note='', sources=[dict(url='u1', quote='x')]),
])


def fake_captures(url):
    return [('https://cap/' + url, 'ab' * 32, PAGE)]


def test_R_STU_18_only_true_pairs_are_written_and_a_co_advised_student_sits_under_both_pis():
    out, miss = R.build(VERDICTS, fake_captures)
    rows = {o['pi']: [s['name'] for s in o['students']] for o in out}
    assert rows == {'Bo Chen': ['Ann Lee'], 'Pat Barber': ['Ann Lee']} and miss == []   # unsettled (Cy Dunn) and not (Ed Fox) never appear
    s = out[0]['students'][0]
    assert s['role'] == 'phd' and s['years'] == [2019, 2021] and s['sha256'] == 'ab' * 32 and s['quote'] in PAGE


def test_R_STU_18_a_page_that_does_not_name_the_student_gives_no_row():
    out, miss = R.build(VERDICTS, lambda u: [('c', 'cd' * 32, 'nothing here')])
    assert out == [] and len(miss) == 2


def test_R_STU_18_the_wired_rows_are_exactly_the_true_verdicts():
    d = json.load(open(R.VERDICTS))
    true = collections.Counter((p['pi'], p['student']) for p in d['pairs'] if p['verdict'] == 'true')
    ev = json.load(open(R.OUT))
    wired = collections.Counter((o['pi'], s['name']) for o in ev for s in o['students'])
    assert wired == true and sum(true.values()) == d['counts']['true'] == 44 and d['counts_original_75']['true'] == 41
    for student, pis in (('Haoyang Liu', {'Rina Foygel Barber', 'Chao Gao'}), ('Yu Gui', {'Rina Foygel Barber', 'Cong Ma'})):  # Zhu/Barber and Wang/Hoskins are not among the 75 roster pairs, so no verdict exists: not wired
        assert {pi for pi, n in wired if n == student} == pis
    # co-adviser halves (not among the 75): both advisers wired, flagged, and only where the co-adviser is an atlas PI (Kolar, MacAyeal, Weinberger are not)
    for student, pis in (('Wanrong Zhu', {'Rina Foygel Barber', 'Wei-Biao Wu'}), ('Yuguan Wang', {'Yuehaw Khoo', 'Jeremy Hoskins'}), ('Raphael Rossellini', {'Rina Foygel Barber', 'Rebecca Willett'})):
        assert {pi for pi, n in wired if n == student} == pis
    extra = [p for p in d['pairs'] if p['index'] >= 75]
    assert len(extra) == 3 and all(p['verdict'] == 'true' and p['basis'] == 'co-adviser named on the same page' and p['in_original_75'] is False for p in extra)
    assert not {pi for pi, _ in wired} & {'Mladen Kolar', 'Douglas MacAyeal', 'Shmuel Weinberger'}
    # years: narrowed to the page's graduation date, never extended past the roster years
    yrs = {(o['pi'], s['name']): s['years'] for o in ev for s in o['students']}
    assert yrs[('Daniel Sanz-Alonso', 'Hwanwoo Kim')] == [2021, 2024] and yrs[('Daniel Sanz-Alonso', 'Ruiyi Yang')] == [2020, 2022]
    roster = {(p['pi'], p['student']): p['roster_years'] for p in d['pairs']}
    assert all(yrs[k][0] >= min(roster[k]) and yrs[k][1] <= max(roster[k]) for k in yrs)
    assert all(s['sha256'] and s['quote'] and s['url'] for o in ev for s in o['students'])


def test_R_STU_18_the_student_build_wires_each_pair_as_a_researched_advising_relation(tmp_path):
    assert 'roster-evidence.json' in RESEARCHED_FILES
    f = P.data('roster-evidence.json', 'uchicago', root=tmp_path)
    f.parent.mkdir(parents=True)
    out, _ = R.build(VERDICTS, fake_captures)
    f.write_text(json.dumps(out))
    ctx = type('C', (), dict(here=tmp_path, school='uchicago', pis=[{'pi': 'Pat Barber'}, {'pi': 'Bo Chen'}], ge={}, n=collections.Counter()))()
    stu = collections.defaultdict(dict)
    researched(ctx, stu, {})
    assert [r['name'] for r in stu['Pat Barber'].values()] == ['Ann Lee'] == [r['name'] for r in stu['Bo Chen'].values()]
    rel = next(iter(stu['Pat Barber'].values()))['relations'][0]
    assert rel['type'] == 'researched_advising' and rel['years'] == [2019, 2021] and rel['sources'][0]['sha256'] == 'ab' * 32
