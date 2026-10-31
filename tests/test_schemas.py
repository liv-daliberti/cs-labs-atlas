"""Schemas and the data layout (ROADMAP items 9-10): every schema uses only what tools/schema_check.py checks and names a
known file, the builder's own outputs on the fixture school conform to their schemas, the validator catches what it
should, the data dictionary is generated from the schemas, and atlas_paths.DATA_FILES keeps today's paths."""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

import atlas_paths as P
import schema_check as S
import validate as V

CODE = Path(__file__).resolve().parents[1]
SCHEMAS = sorted((CODE / 'schemas').glob('*.schema.json'))


def schema(name):
    return json.loads((CODE / 'schemas' / f'{name}.schema.json').read_text())


@pytest.mark.parametrize('f', SCHEMAS, ids=lambda f: f.name)
def test_schema_is_supported_and_resolves(f):
    s = json.loads(f.read_text())
    assert s.get('x-file') and s.get('x-kind') in ('derived', 'reviewed') and s.get('description')
    S.validate([] if s.get('x-format') else {}, s)                       # unknown keywords raise
    V.paths_for(s['x-file'], 'mit' if '<school>' in s['x-file'] else None, root=CODE)   # every file pattern resolves


def test_fixture_build_outputs_conform(tmp_path, monkeypatch):
    import provenance
    import test_build_rules as T
    from pihier import build
    T.write_school(tmp_path)
    ctx = T.run_stages(tmp_path)
    ctx.out = tmp_path / 'out'; ctx.out.mkdir()
    monkeypatch.setattr(provenance, 'block', lambda school: {})       # no project data: the package files only
    build.write(ctx)
    for name, f in (('pis', 'pis.json'), ('students', 'students.json'), ('lab_papers', 'lab_papers.jsonl.gz'),
                    ('student_papers', 'student_papers.jsonl.gz')):
        assert S.validate_file(ctx.out / f, schema(name)) == [], f


def test_validator_catches_violations():
    sp = schema('student_papers')
    good = dict(pi='A B', student='p1', name='C D', work=None, oa='https://openalex.org/W1', status='candidate',
                basis='collection_person_link', relation_source=dict(relation='academic_advising', url='https://x', sha256='a' * 64, quote='q'))
    assert S.validate(good, sp) == []
    bad = dict(good, basis='guess', relation_source=dict(good['relation_source'], sha256=''))
    msgs = ' '.join(m for _, m in S.validate(bad, sp))
    assert 'guess' in msgs and "''" in msgs


def test_data_dictionary_is_generated_from_the_schemas():
    r = subprocess.run([sys.executable, str(CODE / 'tools' / 'data_dictionary.py'), '--check'], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_data_files_keep_todays_paths_and_split_by_kind():
    names = [n for n, *_ in P.DATA_FILES]
    assert len(names) == len(set(names))
    for name, kind, flat, split in P.DATA_FILES:
        assert kind in ('raw', 'reviewed', 'derived', 'work', 'report')
        assert P.data(name, 'mit', root='/r', layout='flat') == Path('/r') / flat.format(school='mit')
        if name != 'logs':
            assert re.search(rf'/({kind}|logs)(/|$)', split.format(school='mit')), (name, split)
    # the paths the builder used before the layout table (tools/pihier, provenance)
    assert P.data('pis.json', 'mit', root='/r') == Path('/r/hierarchy/mit/pis.json')
    assert P.data('census-faculty.json', 'mit', root='/r') == Path('/r/census/mit-faculty.json')
    assert P.data('dblp_pubs.json.gz', 'princeton', root='/r') == Path('/r/hierarchy/princeton/raw/dblp_pubs.json.gz')
    assert P.data('pis.json', 'mit', root='/r', layout='split') == Path('/r/hierarchy/mit/derived/pis.json')
    with pytest.raises(KeyError):
        P.data('no-such-file.json', 'mit')


def test_data_layout_doc_lists_every_data_file():
    doc = (CODE / 'docs' / 'DATA-LAYOUT.md').read_text()
    missing = [n for n, _, flat, split in P.DATA_FILES if f'| `{n}` |' not in doc or f'`{flat}`' not in doc or f'`{split}`' not in doc]
    assert not missing, missing
