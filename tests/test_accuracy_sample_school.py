"""accuracy/sample.py --school: a school outside the six released ones is drawn with the same seed and method into its own
file, and the released draws are unchanged (the 2026-11-02 Michigan stage 9)."""
import importlib.util
import json
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location('accuracy_sample', Path(__file__).resolve().parents[1] / 'accuracy' / 'sample.py')
S = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S)


def test_alumni_fallback_rules():
    rel = {'type': 'researched_advising', 'years': [2019, 2021]}
    assert S.alumni_relation(rel, ['phd_alumnus']) == 2021
    assert S.alumni_relation(rel, ['phd']) is None                  # a current student has no PhD year
    assert S.alumni_relation(rel, ['postdoc_alumnus']) is None
    assert S.alumni_relation({'type': 'researched_membership', 'years': [2020]}, ['phd_alumnus']) is None


def test_thesis_relation_unchanged():
    rel = {'type': 'thesis_adviser', 'years': [2020], 'sources': [{'kind': 'phd_thesis', 'url': 'u', 'quote': 'Degree: PhD, 2020'}]}
    assert S.thesis_relation(rel, 'cmu') == 2020
    assert S.thesis_relation({'type': 'researched_advising', 'years': [2020], 'sources': [{'url': 'u', 'quote': 'PhD alumni'}]}, 'cmu') is None


@pytest.mark.nfs
def test_released_draw_independent_of_other_schools(tmp_path):
    one = S.main(['mit'], tmp_path / 'a.json')['schools']['mit']
    two = S.main(['michigan', 'mit'], tmp_path / 'b.json')['schools']['mit']   # the seed is reset per school
    assert one == two
    assert json.loads((tmp_path / 'a.json').read_text())['schools']['mit']['lab_precision'] == one['lab_precision']
    assert S.OUT.name == 'sample.json' and S.SCHOOLS == ['princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford']


def _persons_file(path, persons):
    import gzip
    with gzip.open(path, 'wt') as f:
        json.dump({'persons': persons}, f)


def test_dblp_persons_reads_the_school_local_file(tmp_path, monkeypatch):
    """An onboarding school's PIs are only in hierarchy/<school>/raw/dblp-dump-persons-school.json.gz: without it the lab-coverage pool of
    a protocol school was empty (UChicago stage 9)."""
    rec = lambda k: {'key': k, 'type': 'article', 'title': 'T ' + k, 'year': 2020, 'dois': [], 'authors': [['A', None]]}
    shared, local = tmp_path / 'shared.json.gz', tmp_path / 'local.json.gz'
    _persons_file(shared, {'p/1': {'pubs': [rec('k1')]}, 'p/2': {'pubs': [rec('k2')]}})
    _persons_file(local, {'p/3': {'pubs': [rec('k3')]}})
    paths = {'dblp-dump-persons.json.gz': shared, 'dblp-dump-persons-school.json.gz': local}
    monkeypatch.setattr(S.P, 'data', lambda name, school=None, **k: paths[name])
    assert set(S.dblp_persons({'p/1', 'p/3'})) == {'p/1'}                       # no school: the shared file only (released draws unchanged)
    assert set(S.dblp_persons({'p/1', 'p/3'}, 'uchicago')) == {'p/1', 'p/3'}
    assert [r['key'] for r in S.dblp_persons({'p/3'}, 'uchicago')['p/3']] == ['k3']
    paths['dblp-dump-persons-school.json.gz'] = tmp_path / 'absent.json.gz'     # a school without its own file is as before
    assert set(S.dblp_persons({'p/1', 'p/3'}, 'uchicago')) == {'p/1'}
