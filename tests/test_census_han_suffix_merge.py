"""HKUST 2026-11-18: 'Dit-Yan YEUNG 楊瓞仁' (the Han suffix read as the family name) and 'Dit-Yan YEUNG' were two persons. Opt-in only."""
import importlib.util
from pathlib import Path


def census_build():
    spec = importlib.util.spec_from_file_location('by_path_census_build2', Path(__file__).resolve().parents[1] / 'tools' / 'census_build.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def row(name, observed):
    return dict(name=name, observed=observed, year=int(observed[:4]), homepage=None)


def test_han_suffix_merge_is_opt_in():
    cb = census_build()
    rows = [row('Dit-Yan YEUNG', '2020-01-01'), row('Dit-Yan YEUNG 楊瓞仁', '2024-01-01'), row('Sai-Kit YEUNG 楊世傑', '2024-01-01')]
    assert len(cb.merge_people(rows)) == 3
    groups = cb.merge_people(rows, han_suffix=True)
    assert sorted(len(g['names']) for g in groups) == [1, 2]
    assert cb.latin_part('楊瓞仁') == '楊瓞仁'
