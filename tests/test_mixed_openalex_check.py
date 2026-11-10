import mixed_openalex_check as M

PUBS = [{'title': 'A Long Enough Title About Graph Learning %d' % i, 'dois': ['10.1/x%d' % i]} for i in range(6)]


def test_namesake_id_with_no_dblp_work_is_mixed():
    works = [{'doi': '10.9/other', 'title': 'Wastewater treatment with membranes and more'}]
    assert M.verdict(works, PUBS) == 'mixed'


def test_id_sharing_a_doi_or_title_is_verified():
    assert M.verdict([{'doi': 'https://doi.org/10.1/X2', 'title': 'zzz'}], PUBS) == 'anchored_verified'
    assert M.verdict([{'doi': None, 'title': 'a long enough title about graph learning 3.'}], PUBS) == 'anchored_verified'


def test_too_few_dblp_records_or_no_work_is_undecided():
    assert M.verdict([{'doi': '10.9/o', 'title': 't'}], PUBS[:3]) == 'undecided'
    assert M.verdict([], PUBS) == 'undecided'
