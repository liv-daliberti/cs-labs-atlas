"""Accuracy must sample the rows a per-PI release actually ships, including carry-forward."""
import gzip
import importlib.util
import json
from pathlib import Path

import pytest

import pi_release as PR
import pi_states as PS


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parents[1] / 'accuracy' / filename)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


S = module('projection_sample', 'sample.py')


def put_package(path, members, works, links):
    path.mkdir(parents=True)
    pis = [dict(pi=p, atlasId=f'atl:p:{p}', labId=f'atl:l:x:{p}', dblp=[]) for p in ('A', 'B')]
    (path / 'pis.json').write_text(json.dumps(pis))
    (path / 'students.json').write_text(json.dumps(members))
    (path / 'copies.json').write_text(json.dumps(dict(papers={})))
    for name, rows in [('lab_papers.jsonl.gz', works), ('student_papers.jsonl.gz', links)]:
        with gzip.open(path / name, 'wt') as f:
            for row in rows:
                f.write(json.dumps(row) + '\n')


@pytest.fixture
def projection(tmp_path, monkeypatch):
    new, published = tmp_path / 'new', tmp_path / 'old'
    paper = lambda pi: dict(pi=pi, work=f'w{pi}', oa=f'W{pi}', atlasWorkId=f'atl:w:{pi}', authorship={}, title=f'Paper {pi}', byline=[], identity='reviewed_openalex_author_id')
    student = lambda who: dict(person=who, atlasId=f'atl:p:{who}', name=who, roles=['phd'], relations=[dict(type='thesis_adviser', years=[2020], sources=[dict(kind='phd_thesis', quote='PhD', url='u')])])
    link = lambda pi, who: dict(pi=pi, work=f'w{pi}', oa=f'W{pi}', student=who, name=who, studentAtlasId=f'atl:p:{who}', atlasWorkId=f'atl:w:{pi}')
    put_package(new, {'A': [student('kept'), student('held')], 'B': []}, [paper('A')], [link('A', 'kept'), link('A', 'held')])
    put_package(published / 'hierarchy' / 'x', {'B': [student('restored')]}, [paper('B')], [link('B', 'restored')])
    monkeypatch.setattr(PR, 'package_dir', lambda key, base=None: new if base is None else base / 'hierarchy' / key)
    monkeypatch.setattr(PR, 'load_corrections', lambda *a: None)
    monkeypatch.setattr(S.P, 'SchoolDir', lambda school: new)
    monkeypatch.setattr(S, 'dblp_persons', lambda *a: {})
    res = dict(open_pis=[], school_items={}, pis={pi: {stage: dict(state='done', reasons=[]) for stage in PS.ALL} for pi in ('A', 'B')},
               held_links={'A': [dict(id='held', student='held', diagnosis='unreviewed link')]})
    plan = PR.plan('x', res, published)
    monkeypatch.setattr(PR, 'plan', lambda school: plan)
    cfg = dict(seed=11, uniform=20, stratum=0, cov=0, cands=20, schools=['x'])
    sample = S.main(['x'], tmp_path / 'sample.json', cfg=cfg, only_pis=['A', 'B'], release_plan=plan)
    return sample, plan, new


def test_draw_includes_restored_rows_and_excludes_held_links(projection):
    sample, plan, _ = projection
    school, subset = sample['schools']['x'], sample['subset']['x']
    assert school['n_lab_papers'] == 2
    assert school['n_student_papers'] == 2
    assert {r['key'] for r in school['student_precision']} == {'A|kept|WA', 'B|restored|WB'}
    assert {r['key'] for r in school['student_coverage_order']} == {'A|kept', 'B|restored'}
    assert subset['files'] == PR.package_hashes('x', plan['included'], held=PR.held_set(plan))
    assert subset['projection_version'] == 1
    rows = S.evidence_package('x', sample)
    assert {r['student'] for r in rows['student_papers.jsonl.gz']} == {'kept', 'restored'}
    for item in school['student_precision']:
        row = rows['student_papers.jsonl.gz'][item['i']]
        assert item['key'] == f"{row['pi']}|{row['student']}|{row['oa']}"


def test_evidence_refuses_a_changed_release_projection(projection):
    sample, _, new = projection
    data = json.loads((new / 'students.json').read_text())
    data['A'][0]['name'] = 'changed after draw'
    (new / 'students.json').write_text(json.dumps(data))
    with pytest.raises(ValueError, match='projection changed'):
        S.evidence_package('x', sample)
