import cs_related_school as CR


def ev(flat, names):
    return CR.faculty_evidence([('EE', 'https://ee.kaist.ac.kr/x', 'sha', '20261124', flat)], names, '', single_person=False)


def test_hangul_name_with_ladder_title_is_evidence():
    flat = '정혜원 직위 부교수 사무실 IT융합빌딩 (N1) 206 윤인수 직위 교수 (KAIST 석좌교수)'
    got = ev(flat, ['Hye Won Chung', '정혜원'])
    assert len(got) == 1 and got[0]['quote'] == '정혜원 직위 부교수' and got[0]['ladder']
    assert ev(flat, ['Insu Yun', '윤인수'])[0]['quote'] == '윤인수 직위 교수'


def test_korean_non_ladder_titles_and_longer_names_are_not_evidence():
    assert ev('김현정 겸임교수 연구분야', ['김현정']) == []
    assert ev('이태식 명예교수', ['이태식']) == []
    assert ev('박정혜원 직위 교수', ['정혜원']) == []
    assert ev('정혜원 직위 연구교수', ['정혜원']) == []
