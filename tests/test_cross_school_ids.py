"""Cross-school identity check: the same person at two schools must share an anchor."""
import cross_school_ids as X


def R(school, name, **k):
    return dict(school=school, name=name, names=k.pop('names', [name]), dblp=k.pop('dblp', []), orcid=k.pop('orcid', []), openalex=k.pop('openalex', []))


def test_agree_one_side_and_conflict():
    mine = [R('g', 'Ann Lee', dblp=['https://dblp.org/pid/1/2'], orcid=['0000-0001']), R('g', 'Bo Kim', openalex=['https://openalex.org/A1']), R('g', 'Cy Wu', dblp=['https://dblp.org/pid/9/9'])]
    theirs = [R('s', 'Ann Lee', dblp=['https://dblp.org/pid/1/2']), R('s', 'Bo Kim'), R('s', 'Cy Wu', orcid=['0000-0009'])]
    res = X.compare(mine, theirs)
    assert [r['name'] for r in res['agree']] == ['Ann Lee'] and [r['name'] for r in res['one_side']] == ['Bo Kim'] and [r['name'] for r in res['conflict']] == ['Cy Wu']


def test_an_initial_first_alias_does_not_make_a_namesake_pair():
    mine = [R('g', 'Karen Liu', names=['Karen Liu', 'C. Karen Liu'], orcid=['1'])]
    theirs = [R('c', 'Changliu Liu', orcid=['2']), R('s', 'Karen Liu', orcid=['1'])]
    res = X.compare(mine, theirs)
    assert [r['other_school'] for r in res['agree']] == ['s'] and not res['conflict']
