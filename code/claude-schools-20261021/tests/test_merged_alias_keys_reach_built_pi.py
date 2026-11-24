"""Georgia Tech 2026-11-18: merging three duplicate census spellings renamed three PIs, and reviewed files keyed by the older spelling (students,
advisees, recovered papers) no longer reached them (20 students and 272 student-paper links dropped). A reviewed census-name-aliases pair maps its
merged-away spelling to the built PI; nothing else changes."""
import json

from pihier import students


def test_merged_alias_spelling_maps_to_the_built_pi(tmp_path):
    f = tmp_path / 'census-name-aliases.json'
    f.write_text(json.dumps(dict(school='x', rows=[dict(name_a='Polo Chau', name_b='Duen Horng "Polo" Chau'), dict(name_a='Ann Lee', name_b='Anne Lee')])))
    pis = [dict(pi='Duen Horng "Polo" Chau'), dict(pi='Ann Lee'), dict(pi='Yang Zhang', censusName='Y Z')]
    import atlas_paths as P
    orig = P.data
    try:
        P.data = lambda name, school=None, root=None, **kw: f if name == 'census-name-aliases.json' else orig(name, school, root=root, **kw)
        got = students.renamed_pis(pis, 'x')
    finally:
        P.data = orig
    assert got == {'Polo Chau': 'Duen Horng "Polo" Chau', 'Anne Lee': 'Ann Lee', 'Y Z': 'Yang Zhang'}
    assert students.renamed_pis(pis) == {'Y Z': 'Yang Zhang'}   # no school: the old behaviour
