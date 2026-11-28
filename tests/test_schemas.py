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


@pytest.mark.parametrize('lab_scoped', [False, True])
def test_fixture_build_outputs_conform(tmp_path, monkeypatch, layout, lab_scoped):
    import provenance
    import test_build_rules as T
    from pihier import build
    T.write_school(tmp_path)
    if lab_scoped:
        evidence = T.put(tmp_path, 'few-students-evidence.json')
        rows = json.loads(evidence.read_text())
        rows[0]['students'][0]['lab_scoped_identity'] = True
        evidence.write_text(json.dumps(rows))
    ctx = T.run_stages(tmp_path)
    if lab_scoped:
        assert any(r.get('identityScope') == 'lab' for r in ctx.stu['Grace Hopper'].values())
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


def test_bound_dblp_latin_name_provenance_conforms(tmp_path, monkeypatch, layout):
    import collections
    import provenance
    import test_build_rules as T
    from pihier import build, identity

    T.write_school(tmp_path)
    ctx = T.run_stages(tmp_path)
    ctx.out = tmp_path / 'out'
    ctx.out.mkdir()
    monkeypatch.setattr(provenance, 'block', lambda school: {})
    build.write(ctx)
    pi = json.loads((ctx.out / 'pis.json').read_text())[0]
    pi.update(names=['方俊'], dblp=['test/fang'])
    dump = dict(persons={'test/fang': dict(names=['Jun Fang 0001'], orcid=[], pubs=[])}, by_name={})
    identity.apply_dump([pi], dump, collections.defaultdict(set), collections.defaultdict(dict), collections.Counter())
    assert pi['latinFromDblp'] == ['Jun Fang']
    assert S.validate([pi], schema('pis')) == []
    pi['latinFromDblp'] = [7]
    assert any('latinFromDblp' in path for path, _ in S.validate([pi], schema('pis')))


def test_data_dictionary_is_generated_from_the_schemas():
    r = subprocess.run([sys.executable, str(CODE / 'tools' / 'data_dictionary.py'), '--check'], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.split_only
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
    # split was the default from the move of 2026-11-01 (7407588) to the school-layout cutover of 2026-11-26; it stays selectable
    assert P.DATA_LAYOUT_DEFAULT == 'school'
    assert P.data('pis.json', 'mit', root='/r', layout='split') == Path('/r/hierarchy/mit/derived/pis.json')
    assert P.data('pis.json', 'mit', root='/r', layout='school') == Path('/r/schools/mit/derived/pis.json')
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
    assert V.paths_for('hierarchy/<school>/pis.json', 'mit', tmp_path) == [tmp_path / 'hierarchy' / 'mit' / 'pis.json']  # route-ok: recorded wording or a path-rewrite fixture, not a data path


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


def test_labpage_additions_preserve_manual_provenance():
    """A manually reviewed row must not be relabeled automatic to pass validation."""
    row = dict(name='A B', pi='P', role='phd', years=None, alumni=False,
               url='https://example.edu/people', sha256='0' * 64,
               quote='A B PhD Student', rule='LP-STU-01', auto=False)
    doc = dict(school='harvard', generated_at='2026-11-15T19:00:00',
               rules={}, students=[row], papers=[])
    sch = schema('labpage-additions')
    assert S.validate(doc, sch) == []
    row['auto'] = True
    assert S.validate(doc, sch) == []
    row['auto'] = 'false'
    assert any('.auto' in str(e) for e in S.validate(doc, sch))
    row['auto'] = False
    del row['quote']
    assert any('quote' in str(e) for e in S.validate(doc, sch))


def test_labpage_schema_preserves_rejection_and_withholding_audit_trail():
    decision = dict(pi='P', name='A B', decision='held', reason='Source role is ambiguous.')
    doc = dict(school='harvard', generated_at='2026-11-15T19:00:00', rules={},
               students=[], papers=[], hand_review_20261115b=[decision])
    sch = schema('labpage-additions')
    assert S.validate(doc, sch) == []
    del decision['reason']
    assert S.validate(doc, sch)
    doc['unexpected_metadata'] = []
    assert any('unexpected_metadata' in str(e) for e in S.validate(doc, sch))


def test_link_diagnosis_accepts_before_window_work():
    """The writer labels a work by its earlier DBLP venue year even when OpenAlex dates it later."""
    work = dict(oa='https://openalex.org/W1', year=2018, title='Earlier venue paper',
                byline_name='Ada Lovelace', type='article', excluded='before_window',
                pi_affiliation='school')
    student = dict(pi='Ada Lovelace', student='Charles Babbage', id='p1', roles=['phd'],
                   years=[2016, 2018], category='with_pi_before_window', works=[work],
                   n_school_works=1, distinct_author_ids=1, pis_seen=[])
    report = dict(summary={'with_pi_before_window': 1}, students={'Ada Lovelace | p1': student})
    assert S.validate(report, schema('link-diagnosis')) == []


def test_student_identity_schema_distinguishes_pairs_from_cross_lab_reviews():
    sch = schema('student-identity-review')
    pair = dict(school='example', pi='First PI', a=['a', 'A B'], b=['b', 'A B'],
                verdict='same_person', reason='Reviewed same-lab aliases.')
    cross = dict(school='example', scope='cross_lab', canonical_name='A B',
                 verdict='same_person', reason='Both rosters link the same primary page.',
                 identity_url='https://student.example/',
                 memberships=[dict(pi='First PI', person='ext:example:a-b'),
                              dict(pi='Second PI', person='ext:example:a-b')],
                 evidence=[dict(url='https://student.example/', sha256='1' * 64, quote='A B')])
    assert S.validate([pair, cross], sch) == []
    del pair['pi']
    assert S.validate([pair], sch)
    del cross['memberships'][0]['person']
    assert S.validate([cross], sch)


def test_cross_lab_schema_requires_a_named_or_typed_identity_basis():
    row = dict(school='example', scope='cross_lab', canonical_name='A B',
               verdict='same_person', reason='Reviewed source-bound identity.',
               memberships=[dict(pi='First PI', person='ext:example:a-b'),
                            dict(pi='Second PI', person='ext:example:a-b')],
               evidence=[dict(url='https://repository.example/item', sha256='1' * 64, quote='A B')])
    sch = schema('student-identity-review')
    assert S.validate([row], sch)
    row['identity_basis'] = 'typed_repository_author'
    assert S.validate([row], sch) == []
    row['verdict'] = 'different_people'
    assert S.validate([row], sch)


def test_link_diagnosis_accepts_reviewed_outcomes():
    """Reviewed student-link exclusions and exact paper-uncertainty holds are explained outcomes (chain_audit.DIAG_REASON)."""
    work = dict(oa='https://openalex.org/W2', year=2024, title='Held paper', byline_name='Ada Lovelace',
                type='article', excluded='reviewed_paper_hold', pi_affiliation='school', paper_hold_decisions=['hold-1'])
    base = dict(pi='Ada Lovelace', roles=['phd'], years=[2023, 2025], n_school_works=1, distinct_author_ids=1, pis_seen=[])
    held = dict(base, student='A', id='p1', category='reviewed_paper_hold', works=[work])
    excl = dict(base, student='B', id='p2', category='reviewed_exclusion', works=[])
    report = dict(summary={'reviewed_paper_hold': 1, 'reviewed_exclusion': 1}, students={'Ada Lovelace | p1': held, 'Ada Lovelace | p2': excl})
    assert S.validate(report, schema('link-diagnosis')) == []
    held['category'] = 'reviewed_nonsense'
    assert S.validate(report, schema('link-diagnosis'))


def test_page1_schema_accepts_reviewed_publisher_marker_with_hashed_evidence():
    page = dict(url='https://publisher.example/paper.pdf', pdf_sha256='a' * 64,
                how='reviewed_publisher_marker', quotes=['Ada Example2 2 Example University'])
    shape = schema('lab_papers')['properties']['authorship']['properties']['page1']
    assert S.validate(page, shape) == []
    assert S.validate(dict(page, how='unreviewed_guess'), shape)
    del page['pdf_sha256']
    assert S.validate(page, shape)


def test_home_hold_can_preserve_missing_evidence_without_accepting_an_assignment():
    row = dict(school='example', name='Pending PI', home_department=None, status='hold',
               evidence=None, note='No professor title on a captured listing.')
    sch = schema('home-departments')
    assert S.validate([row], sch) == []
    assert S.validate([dict(row, status='accepted')], sch)
    assert S.validate([dict(row, home_department='Computer Science')], sch)
    assert S.validate([dict(row, note='')], sch)
    assert S.validate([dict(row, no_academic_department=True)], sch)
    ev = dict(url='https://example.edu/faculty', sha256='a' * 64, quote='Pending PI')
    assert S.validate([dict(row, status='accepted', home_department='Computer Science', evidence=ev)], sch) == []
    assert S.validate([dict(row, evidence=dict(ev, sha256='invalid'))], sch)


def test_source_distinct_student_audit_matches_writer_and_stays_distinct():
    pair = dict(pi='PI', a=['a', 'Same Name'], b=['b', 'Same Name'], keys=['source-a', 'source-b'])
    counts = dict(lab_student_pairs=2, within_lab_pairs=0, within_lab_source_distinct=1,
                  across_lab_people=0, same_paper_pairs=0, students_with_missed_links=0,
                  missed_links=0, students_without_links=0)
    doc = dict(school='example', within_lab=[], within_lab_source_distinct=[pair], across_labs=[],
               same_paper=[], missed_link=[], students_without_links=0, lab_student_pairs=2, counts=counts)
    sch = schema('student-audit')
    assert S.validate([doc], sch) == []
    del pair['keys']
    assert S.validate([doc], sch)
    pair['keys'] = ['source-a', 'source-b']
    counts['within_lab_source_distinct'] = -1
    assert S.validate([doc], sch)


def test_zero_paper_ledger_preserves_nonempty_legacy_provenance():
    row = dict(school='example', pi='PI', diagnosis='no_output_found', verdict='zero_is_right',
               reason='Reviewed local bibliography.', funnel={}, periods=[], listing_years=[], students=0)
    sch = schema('zero-paper-labs')
    for evidence in ('Local DBLP dump: no in-window works.', ['https://example.edu/cv'], None):
        doc = dict(built_by='tools/zero_paper_ledger.py', zero_papers=[dict(row, evidence=evidence)], zero_students=[], counts={})
        assert S.validate(doc, sch) == []
    for evidence in ('', 123, {'invented': 'not a source list'}):
        doc['zero_papers'][0]['evidence'] = evidence
        assert S.validate(doc, sch)
