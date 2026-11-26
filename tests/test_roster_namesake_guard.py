"""R-STU-33: a shared roster without row-level advisers remains held at every coauthor count."""
import gzip
import json

import atlas_paths as P
import labpage_students_school as L
import school_config as S


def rows(tmp_path, monkeypatch, papers):
    lp = tmp_path / 'lab_papers.jsonl.gz'
    with gzip.open(lp, 'wt') as f:
        for pi, title, year, byline in papers:
            f.write(json.dumps(dict(pi=pi, title=title, year=year, byline=byline)) + '\n')
    monkeypatch.setattr(P, 'data', lambda name, school=None, *a, **k: lp)
    monkeypatch.setattr(S, 'field', lambda cfg, key: [dict(url='x.example/phd', kind='students', listed_as_phd=True)] if key == 'students.rosters' else None)
    monkeypatch.setattr(S, 'get', lambda key: {})
    monkeypatch.setattr(L.W, 'con', lambda key: None)
    monkeypatch.setattr(L.W, 'cdx_rows', lambda c, url, collapse=None: [dict(timestamp='20200101000000', original=url)])
    monkeypatch.setattr(L.W, 'capture', lambda c, ts, orig, url, tag: ('https://web.archive.org/web/20200101000000id_/' + url, 200, 'a' * 64, b''))
    monkeypatch.setattr(L.W, 'flat', lambda b: 'Directory Ada Student Ph.D. Bo Namesake Ph.D. Cy Two Ph.D.')
    forms = [('Prof One', 'Prof One'), ('Prof Two', 'Prof Two')]
    return {(r['student'], r['pi']) for r in L.roster_coauthor_students('k', forms)}


def test_single_paper_pair_with_a_namesake_elsewhere_is_dropped(tmp_path, monkeypatch):
    got = rows(tmp_path, monkeypatch, [
        ('Prof One', 'P1', 2020, ['Ada Student', 'Prof One']),                      # one paper, no other lab carries the name: kept
        ('Prof One', 'P2', 2020, ['Bo Namesake', 'Prof One']),                      # one paper, and ...
        ('Prof Two', 'P3', 2021, ['Bo Namesake', 'Prof Two']),                      # ... the name is on another PI's paper: ambiguous, dropped
        ('Prof One', 'P4', 2020, ['Cy Two', 'Prof One']), ('Prof One', 'P5', 2021, ['Cy Two', 'Prof One']),   # two papers: kept
        ('Prof Two', 'P6', 2021, ['Cy Two', 'Prof Two'])])
    assert got == set()  # R-STU-33: none of these roster entries names an adviser


def test_qualifying_coadvisers_survive_unequal_publication_counts(tmp_path, monkeypatch):
    got = rows(tmp_path, monkeypatch, [
        ('Prof One', 'P1', 2020, ['Ada Student', 'Prof One']),
        ('Prof One', 'P2', 2020, ['Ada Student', 'Prof One']),
        ('Prof One', 'P3', 2021, ['Ada Student', 'Prof One']),
        ('Prof Two', 'P4', 2020, ['Ada Student', 'Prof Two']),
        ('Prof Two', 'P5', 2021, ['Ada Student', 'Prof Two']),
    ])
    assert got == set()  # Unequal or equal coauthor counts cannot establish co-advising
