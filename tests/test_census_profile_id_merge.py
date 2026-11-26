import census_build as C

PAT = r'cs\.kaist\.ac\.kr/people/view\?idx=(\d+)'


def row(name, year, idx, observed):
    return dict(name=name, name_listed=name, year=year, observed=observed, dept='CS', rank='ladder', titles=['Professor'], dept_title=['Professor'],
                profile=f'https://cs.kaist.ac.kr/people/view?idx={idx}&kind=faculty', homepage=None)


def test_same_profile_id_joins_latin_and_hangul_spellings():
    rows = [row('Sungeui Yoon', 2016, 20, '20160405000000'), row('Sung-Eui Yoon', 2020, 20, '20200810000000'), row('윤성의', 2025, 20, '20250921000000'),
            row('Dongman Lee', 2020, 77, '20200810000000')]
    groups = C.merge_people(rows, profile_id_rx=PAT)
    by = {tuple(sorted(g['names'])): g for g in groups}
    assert len(groups) == 2
    yoon = next(g for g in groups if '윤성의' in g['names'])
    assert sorted(yoon['names']) == sorted(['Sungeui Yoon', 'Sung-Eui Yoon', '윤성의'])
    assert sorted({r['year'] for r in yoon['rows']}) == [2016, 2020, 2025]
    assert C.display_name(yoon['rows'], yoon['names'], True) == 'Sung-Eui Yoon'
    assert C.display_name(yoon['rows'], yoon['names']) == '윤성의'
    assert by


def test_no_pattern_keeps_name_rules_and_different_ids_never_merge():
    rows = [row('윤성의', 2025, 20, '20250921000000'), row('이동만', 2025, 77, '20250921000000'), row('Dongman Lee', 2020, 78, '20200810000000')]
    groups = C.merge_people(rows, profile_id_rx=PAT)
    assert len(groups) == 3
    assert len(C.merge_people(rows[:1] + [row('Sung-Eui Yoon', 2020, 20, '20200810000000')])) == 2


def test_stated_latin_needs_the_hangul_name_and_a_parenthesis():
    import profile_romanization_school as R
    flat = '위다레흐트 세버스티언는(Sebastian Wiederrecht)는 KAIST에서 전산이론을 연구하는 조교수로'
    assert R.stated_latin(flat, '위다레흐트 세버스티언') == ('Sebastian Wiederrecht', '위다레흐트 세버스티언는(Sebastian Wiederrecht)')
    assert R.stated_latin('김현우 부교수 Amazon Lab (Area Chair)', '김현우') == (None, None)
