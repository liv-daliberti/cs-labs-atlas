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


def test_fixture_build_outputs_conform(tmp_path, monkeypatch, layout):
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
    # the flat paths the builder used before the layout table (tools/pihier, provenance), still available as layout='flat'
    assert P.data('pis.json', 'mit', root='/r', layout='flat') == Path('/r/hierarchy/mit/pis.json')
    assert P.data('census-faculty.json', 'mit', root='/r', layout='flat') == Path('/r/census/mit-faculty.json')
    assert P.data('dblp_pubs.json.gz', 'princeton', root='/r', layout='flat') == Path('/r/hierarchy/princeton/raw/dblp_pubs.json.gz')
    # the default since the move of 2026-11-01 (7407588) is the split layout
    assert P.DATA_LAYOUT_DEFAULT == 'split'
    assert P.data('pis.json', 'mit', root='/r') == Path('/r/hierarchy/mit/derived/pis.json')
    assert P.data('census-faculty.json', 'mit', root='/r') == Path('/r/hierarchy/mit/derived/census-faculty.json')
    assert P.data('dblp_pubs.json.gz', 'princeton', root='/r') == Path('/r/hierarchy/princeton/raw/dblp_pubs.json.gz')
    with pytest.raises(KeyError):
        P.data('no-such-file.json', 'mit')


def test_data_layout_doc_lists_every_data_file():
    doc = (CODE / 'docs' / 'DATA-LAYOUT.md').read_text()
    missing = [n for n, _, flat, split in P.DATA_FILES if f'| `{n}` |' not in doc or f'`{flat}`' not in doc or f'`{split}`' not in doc]
    assert not missing, missing


def test_validate_root_reads_flat_names_in_either_layout(tmp_path, layout):
    """A --root is a trial build (PI_HIERARCHY_OUT) or a release: both keep the flat names whatever the working layout (ROADMAP #32)."""
    (tmp_path / 'hierarchy' / 'mit').mkdir(parents=True)
    (tmp_path / 'hierarchy' / 'mit' / 'pis.json').write_text('[]')
    assert V.paths_for('hierarchy/<school>/pis.json', 'mit', tmp_path) == [tmp_path / 'hierarchy' / 'mit' / 'pis.json']


def test_labpage_additions_schema_admits_every_basis_the_writer_emits():
    """2026-11-02 (ROADMAP #35-40 validation findings): labpage_audit.py wrote role_basis 'withheld_role_round_failed' (membership-only wiring) and
    'entry_parenthetical' (clean_parenthetical_name), which the schema's enums lacked, so `atlas validate --reviewed` reported 325 violations in
    berkeley and michigan labpage-additions.json. The schema follows the writer: every literal the writer assigns is in the enum."""
    sch = schema('labpage-additions')
    shape = sch['$defs']['student']['properties']
    src = (CODE / 'tools' / 'labpage_audit.py').read_text()
    emitted_role = set(re.findall(r"role_basis='(\w+)'", src)) | set(re.findall(r"r\['role_basis'\] = None, '(\w+)'", src)) | set(re.findall(r"x\['role'\], x\['role_basis'\] = [\w\[\]]+, '(\w+)'", src))
    emitted_years = set(re.findall(r"r\['years_basis'\] = None, '(\w+)'", src)) | set(re.findall(r"x\['years_basis'\] = yrs\[fn\], '(\w+)'", src))
    assert {'withheld_role_round_failed', 'entry_parenthetical', 'reviewer'} <= emitted_role     # the scan still finds the writers
    assert emitted_role <= set(shape['role_basis']['enum']) and emitted_years <= set(shape['years_basis']['enum'])


def test_withheld_rows_validate_against_the_schema():
    import labpage_audit as LA
    row = dict(name='A B', role='phd', years=[2020, 2021], url='https://example.edu/p', sha256='0' * 64, quote='A B', pi='P', alumni=False,
               rule='LP-STU-01', auto=True, pi_first_year=None, role_basis='entry', years_basis='stated_in_entry')
    sch = schema('labpage-additions')
    for years in (False, True):
        out = LA.withhold_roles([row], years=years)
        errs = S.validate({'school': 'x', 'generated_at': 't', 'tool': 't', 'standard': 's', 'status': 'ok', 'rules': {}, 'students': out, 'papers': []}, sch)
        assert not [e for e in errs if 'role_basis' in str(e) or 'years_basis' in str(e)], errs
