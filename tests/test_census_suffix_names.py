"""ROADMAP #42: a generational suffix (Jr./Sr./II/III) is not a family name, and a chair or title string is never a person's
name or alias. Georgia Tech 2026-11-04: 'Charles Isbell, Jr.', 'Charles Cauthen Lever Jr.' and 'Charles Austin Sutlief Jr.' were
one 'jr' family and merged into one person."""
import importlib.util
from pathlib import Path


def census_build():
    spec = importlib.util.spec_from_file_location('by_path_census_build', Path(__file__).resolve().parents[1] / 'tools' / 'census_build.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def row(name, observed, **k):
    return dict(name=name, observed=observed, year=int(observed[:4]), homepage=None, **k)


def test_suffix_is_not_a_family_name():
    cb = census_build()
    rows = [row('Charles Isbell Jr.', '2020-01-01'), row('Charles Cauthen Lever Jr.', '2020-01-01'), row('Charles Austin Sutlief Jr.', '2020-01-01'),
            row('Charles Isbell', '2022-01-01')]
    groups = {tuple(g['names']) for g in cb.merge_people(rows)}
    assert groups == {('Charles Isbell Jr.', 'Charles Isbell'), ('Charles Cauthen Lever Jr.',), ('Charles Austin Sutlief Jr.',)}


def test_two_people_with_a_suffix_stay_apart_and_one_person_keeps_it():
    cb = census_build()
    rows = [row('Thomas C Champion III.', '2020-01-01'), row('Thomas P Barnwell III.', '2020-01-01'), row('Kenneth Wayne Allen Jr.', '2020-01-01')]
    assert len(cb.merge_people(rows)) == 3
    assert cb.display_name([row('Kenneth Wayne Allen Jr.', '2020-01-01')], []) == 'Kenneth Wayne Allen Jr.'  # the suffix is part of the name


def test_display_name_prefers_the_spelling_without_the_suffix():
    cb = census_build()
    rs = [row('Charles Isbell Jr.', '2020-01-01'), row('Charles Isbell', '2021-01-01'), row('Charles Isbell Jr.', '2022-01-01')]
    assert cb.display_name(rs, []) == 'Charles Isbell'


def test_chair_and_title_strings_are_never_names():
    cb = census_build()
    rows = [row('Charles Isbell', '2020-01-01'), row('Dean of Computing/The John P. Imlay Jr. Chair', '2020-01-01'),
            row('Professor of Practice', '2020-01-01'), row('Dean Pomerleau', '2020-01-01'), row('Victoria Dean', '2020-01-01')]
    names = {n for g in cb.merge_people(rows) for n in g['names']}
    assert names == {'Charles Isbell', 'Dean Pomerleau', 'Victoria Dean'}
