"""A student is never bound to a PI's person record by name (HKUST 2026-11-25: 'Tim Ta Ying Cheng' took the person of PI Tim Kwang-Ting CHENG)."""
from pihier import students as S


def test_pi_persons_are_left_out_of_the_name_table():
    people = [dict(id='hkust_fac_tim-kwang-ting-cheng', name='Tim Kwang-Ting CHENG'), dict(id='hkust_fac_other', name='Pat Cheng')]
    pis = [dict(pi='Kwang-Ting Tim CHENG', personIds=['hkust_fac_tim-kwang-ting-cheng'])]
    assert [q['id'] for q in S.people_by_family(people)['cheng']] == ['hkust_fac_tim-kwang-ting-cheng', 'hkust_fac_other']
    assert [q['id'] for q in S.people_by_family(people, pis)['cheng']] == ['hkust_fac_other']
