"""Reviewed unknown claims cannot anchor papers; reviewed editions preserve every eligible byline."""
import copy
import gzip
import hashlib
import json
from collections import Counter
from types import SimpleNamespace

import pytest

import atlas_paths as P
import test_build_rules as T
from pihier import identity, links, reviewed_claims as R

OA = 'https://openalex.org/'


def decision(oa='W1', action='hold', **extra):
    return dict(id=oa + ':' + action, pi='Ada Lovelace', decision=action, match={'oa': OA + oa},
                why='Source review requires this claim to stay unresolved.', reviewed_by='reviewer', reviewed_at='2026-11-08',
                evidence=[dict(url='https://example.edu/source', sha256='a' * 64, quote='Original source clause')], **extra)


def write_review(root, decisions):
    path = P.data_w('paper-claim-review.json', T.SCHOOL, root=root)
    path.write_text(json.dumps(dict(version=1, school=T.SCHOOL, decisions=decisions)))
    return path


def paper(wid, pi='Ada Lovelace', **extra):
    row = dict(pi=pi, oa=OA + wid, work=None, doi='10.9/' + wid, title=wid, year=2020,
               appointment={'periodId': 'p'}, identity='dblp_person_page_doi',
               byline=[pi], byline_school=[pi], editions=[])
    row.update(extra)
    return row


def context(root, rows):
    return SimpleNamespace(here=root, school=T.SCHOOL, pis=[dict(pi='Ada Lovelace'), dict(pi='Grace Hopper')],
                           n=Counter(), rows=copy.deepcopy(rows))


@pytest.mark.usefixtures('layout')
def test_unknown_claim_is_held_without_discarding_another_pi_or_calling_it_not_a_paper(tmp_path):
    write_review(tmp_path, [decision()])
    ctx = context(tmp_path, [paper('W1'), paper('W1', pi='Grace Hopper'), paper('W2')])
    R.apply(ctx)
    assert [(r['pi'], r['oa']) for r in ctx.rows] == [('Grace Hopper', OA + 'W1'), ('Ada Lovelace', OA + 'W2')]
    assert ctx.n['paper_review_rows_held'] == 1 and not ctx.n['paper_review_rows_rejected']
    assert not ctx.n['not_paper_dropped']
    assert ctx.paper_claim_review['decisions'][0]['outcome'] == 'held'
    assert ctx.n['lab_papers'] == 2 and ctx.n['identity:dblp_person_page_doi'] == 2


@pytest.mark.usefixtures('layout')
def test_native_unknown_work_cannot_lend_a_dynamic_author_anchor(tmp_path, monkeypatch):
    monkeypatch.setattr(identity, 'DUMP_PERSONS', None)
    seed = T.work('W501', 'A Bibliography Anchoring Research Paper', 2020, [T.au('Ada Lovelace', 'A15')], doi='10.9/seed')
    dependent = T.work('W502', 'An Otherwise Unsupported Research Paper', 2020, [T.au('Ada Lovelace', 'A15')])
    T.write_school(tmp_path, sweep=[seed, dependent])
    overrides = copy.deepcopy(T.OVERRIDES)
    pid = 'https://dblp.org/pid/example/AdaLovelace'
    overrides[T.SCHOOL]['Ada Lovelace'].update(openalex=[], mixed_openalex=[], dblp=[pid])
    T.put(tmp_path, 'census-overrides.json', None).write_text(json.dumps(overrides))
    T.put(tmp_path, 'dblp-dump-persons-school.json.gz').write_bytes(gzip.compress(json.dumps(dict(
        persons={pid: dict(names=['Ada Lovelace'], pubs=[dict(key='conf/example/Ada20', title=seed['title'],
                                                          year=2020, dois=[seed['doi']], authors=['Ada Lovelace'])])}, by_name={})).encode()))
    before = T.run_stages(tmp_path, upto='papers')
    assert {r['oa'] for r in before.rows if r['pi'] == 'Ada Lovelace'} == {seed['id'], dependent['id']}
    write_review(tmp_path, [decision('W501')])
    after = T.run_stages(tmp_path, upto='papers')
    R.apply(after)
    assert not T.rows_of(after, 'Ada Lovelace')
    assert not after.anchored['Ada Lovelace'].get(OA + 'A15')
    assert after.paper_claim_review['decisions'][0]['outcome'] == 'held_before_identity'
    assert after.n['paper_review_hits_withheld_before_identity'] == 1


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('selector', [{'oa': OA + 'W1'}, {'doi': '10.9/W1'}, {'work': 'collection_work_1'}])
def test_exclusions_find_each_identifier_kind_on_folded_editions(tmp_path, selector):
    held = decision()
    held['match'] = selector
    write_review(tmp_path, [held])
    ctx = context(tmp_path, [])
    folded = paper('W9', editions=[paper('W1', work='collection_work_1')])
    assert R.excluded(ctx, 'Ada Lovelace', folded)
    assert not R.excluded(ctx, 'Grace Hopper', folded)
    assert not R.excluded(ctx, 'Ada Lovelace', paper('W7', work='other_work'))


@pytest.mark.usefixtures('layout')
def test_exclusions_keep_pi_scope_and_complete_edition_selectors_when_reused(tmp_path):
    held = decision()
    held['match'] = dict(oa=OA + 'W1', doi='https://doi.org/10.9/W1')
    write_review(tmp_path, [held, decision('W2', 'merge', into={'oa': OA + 'W3'}),
                            dict(decision('W4'), pi='Grace Hopper')])
    ctx = context(tmp_path, [])
    folded = paper('W9', editions=[paper('W1')])
    assert R.excluded(ctx, 'Ada Lovelace', folded)
    assert R.excluded(ctx, 'Ada Lovelace', folded)
    assert ctx.n['paper_review_hits_withheld_before_identity'] == 1
    assert not R.excluded(ctx, 'Grace Hopper', folded)
    assert not R.excluded(ctx, 'Unreviewed PI', folded)
    assert not R.excluded(ctx, 'Ada Lovelace', paper('W2'))
    # Identifiers on different editions cannot jointly satisfy one selector.
    split = paper('W1', doi='10.9/different', editions=[paper('W8', doi='10.9/W1')])
    assert not R.excluded(ctx, 'Ada Lovelace', split)
    assert not R.excluded(ctx, 'Ada Lovelace', paper('W4'))
    assert R.excluded(ctx, 'Grace Hopper', paper('W4'))


@pytest.mark.usefixtures('layout')
def test_exclusion_index_preserves_conflicting_hold_reject_detection(tmp_path):
    rejected = decision('W2', 'reject')
    rejected['match'] = dict(doi='10.9/W1')
    write_review(tmp_path, [decision(), rejected])
    ctx = context(tmp_path, [])
    with pytest.raises(ValueError, match='conflicting hold/reject'):
        R.excluded(ctx, 'Ada Lovelace', paper('W1'))


@pytest.mark.usefixtures('layout')
def test_explicit_different_title_editions_keep_source_student_byline(tmp_path):
    T.write_school(tmp_path)
    ctx = T.run_stages(tmp_path, upto='students')
    source = paper('W501', title='The Preprint Title', byline=['Ada Lovelace', 'Alan Turing'],
                   byline_school=['Ada Lovelace', 'Alan Turing'])
    published = paper('W502', title='A Different Publisher Title')
    ctx.rows = [source, published]
    write_review(tmp_path, [decision('W501', 'merge', into={'doi': 'https://doi.org/10.9/W502'})])
    R.apply(ctx)
    assert len(ctx.rows) == 1 and ctx.rows[0]['oa'] == OA + 'W502'
    assert [e['oa'] for e in ctx.rows[0]['editions']] == [OA + 'W501']
    assert ctx.rows[0]['_bylines'] == [(['Ada Lovelace'], ['Ada Lovelace']),
                                       (['Ada Lovelace', 'Alan Turing'], ['Ada Lovelace', 'Alan Turing'])]
    links.link_students(ctx)
    assert any(r['student'] == 'p_alan' and r['oa'] == OA + 'W502' for r in ctx.sp)
    assert all(r['status'] != 'verified' for r in ctx.sp)


@pytest.mark.usefixtures('layout')
def test_missing_or_other_pi_merge_target_holds_source_without_admitting_a_target(tmp_path):
    write_review(tmp_path, [decision('W1', 'merge', into={'oa': OA + 'W2'})])
    ctx = context(tmp_path, [paper('W1'), paper('W2', pi='Grace Hopper')])
    R.apply(ctx)
    assert ctx.rows == [paper('W2', pi='Grace Hopper')]
    assert ctx.paper_claim_review['decisions'][0]['outcome'] == 'held_missing_merge_target'


@pytest.mark.usefixtures('layout')
def test_edition_merge_chains_resolve_to_existing_root_and_retain_all_bylines(tmp_path):
    write_review(tmp_path, [decision('W1', 'merge', into={'oa': OA + 'W2'}),
                            decision('W2', 'merge', into={'oa': OA + 'W3'})])
    ctx = context(tmp_path, [paper('W1', byline=['One']), paper('W2', byline=['Two']), paper('W3', byline=['Three'])])
    R.apply(ctx)
    assert len(ctx.rows) == 1 and ctx.rows[0]['oa'] == OA + 'W3'
    assert {tuple(b) for b, _ in ctx.rows[0]['_bylines']} == {('One',), ('Two',), ('Three',)}
    assert {e['oa'] for e in ctx.rows[0]['editions']} == {OA + 'W1', OA + 'W2'}


@pytest.mark.usefixtures('layout')
def test_cycle_and_ambiguous_merge_targets_fail_before_modifying_rows(tmp_path):
    write_review(tmp_path, [decision('W1', 'merge', into={'oa': OA + 'W2'}),
                            decision('W2', 'merge', into={'oa': OA + 'W1'})])
    rows = [paper('W1'), paper('W2')]; ctx = context(tmp_path, rows)
    with pytest.raises(ValueError, match='cycle'):
        R.apply(ctx)
    assert ctx.rows == rows
    write_review(tmp_path, [decision('W1', 'merge', into={'doi': '10.9/shared'})])
    ctx = context(tmp_path, [paper('W1'), paper('W2', doi='10.9/shared'), paper('W3', doi='10.9/shared')])
    with pytest.raises(ValueError, match='ambiguous'):
        R.apply(ctx)


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('change', [dict(decision='accept'), dict(evidence=[]), dict(match={}), dict(into={'oa': OA + 'W2'}),
                                  dict(reviewed_at='yesterday'), dict(evidence=[dict(url='u', sha256='bad', quote='q')])])
def test_invalid_review_cannot_silently_bypass_normal_gates(tmp_path, change):
    d = decision(); d.update(change); write_review(tmp_path, [d]); ctx = context(tmp_path, [paper('W1')])
    with pytest.raises(ValueError):
        R.prepare(ctx)


@pytest.mark.usefixtures('layout')
def test_loaded_review_hash_is_frozen_and_in_school_provenance(tmp_path, monkeypatch):
    import provenance
    path = write_review(tmp_path, [decision()]); ctx = context(tmp_path, [paper('W1')]); R.prepare(ctx)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert ctx.paper_claim_review['sha256'] == digest
    monkeypatch.setattr(provenance, 'P', SimpleNamespace(data=lambda name, school=None: P.data(name, school, root=tmp_path), SITE_DATA=tmp_path))
    assert provenance.school_inputs(T.SCHOOL)[str(path)]['sha256'] == digest
    path.write_text('{}')
    with pytest.raises(ValueError, match='changed during'):
        R.apply(ctx)


@pytest.mark.usefixtures('layout')
def test_no_review_keeps_existing_output_and_unmatched_review_stays_reported(tmp_path):
    ctx = context(tmp_path, [paper('W1')]); R.apply(ctx)
    assert ctx.rows == [paper('W1')] and ctx.paper_claim_review is None and not ctx.n
    write_review(tmp_path, [decision('W999')]); ctx = context(tmp_path, [paper('W1')]); R.apply(ctx)
    assert ctx.rows == [paper('W1')]
    assert ctx.paper_claim_review['decisions'][0]['outcome'] == 'no_current_claim'


@pytest.mark.usefixtures('layout')
def test_full_native_build_writes_review_receipt_and_links_only_to_kept_lead(tmp_path, monkeypatch):
    import schema_check
    from pathlib import Path
    from pihier import build, common

    monkeypatch.setattr(identity, 'DUMP_PERSONS', None)
    works = [T.work('W501', 'An Earlier Preprint Name', 2020, [T.au('Ada Lovelace', 'A1'), T.au('Alan Turing', 'A9')]),
             T.work('W502', 'A Different Published Title', 2020, [T.au('Ada Lovelace', 'A1')]),
             T.work('W503', 'An Unresolved Claim', 2020, [T.au('Ada Lovelace', 'A1')])]
    T.write_school(tmp_path, sweep=works)
    write_review(tmp_path, [decision('W501', 'merge', into={'oa': OA + 'W502'}), decision('W503')])
    monkeypatch.setattr(build, 'HERE', tmp_path)
    monkeypatch.setattr(build, 'Ctx', lambda school, out: common.Ctx(school, here=tmp_path, site=tmp_path, out=out))
    monkeypatch.setattr(build.provenance, 'block', lambda school: {})
    monkeypatch.setenv('PI_HIERARCHY_OUT', str(tmp_path / 'trial'))
    build.build(T.SCHOOL)
    out = tmp_path / 'trial' / T.SCHOOL
    report = json.loads((out / 'report.json').read_text())
    assert report['counts']['lab_papers'] == 1
    assert report['counts']['paper_review_editions_merged'] == 1
    assert {d['outcome'] for d in report['paperClaimReview']['decisions']} == {'merged', 'held_before_identity'}
    with gzip.open(out / 'student_papers.jsonl.gz', 'rt') as f:
        linked = [json.loads(x) for x in f]
    assert any(r['student'] == 'p_alan' for r in linked)
    assert all(r['oa'] == OA + 'W502' for r in linked)
    schema = json.loads((Path(__file__).resolve().parents[1] / 'schemas/report.schema.json').read_text())
    assert schema_check.validate(report['paperClaimReview'], schema['properties']['paperClaimReview']) == []


def flags_hold(**extra):
    d = decision(action='hold_derived_school_flags', scope='derived_school_flags_only')
    d['match']['doi'] = '10.9/W1'
    d['evidence'][0]['source_kind'] = 'partial_fulltext_jats'
    d.update(extra)
    return d


@pytest.mark.usefixtures('layout')
def test_flags_hold_preserves_claim_and_raw_evidence_but_suppresses_all_derived_flags(tmp_path):
    write_review(tmp_path, [flags_hold()])
    row = paper('W1', byline=['Ada Lovelace', 'Foreign Author'], byline_school=['Ada Lovelace', 'Foreign Author'],
                authorship={'raw_affiliations': ['Combined global institution string'], 'author_id': 'A1'},
                byline_affiliation_review={'status': 'applied', 'source': 'competing positive'},
                _bylines=[(['Ada Lovelace', 'Foreign Author'], ['Foreign Author'])])
    ctx = context(tmp_path, [row, paper('W1', pi='Grace Hopper'), paper('W2')])
    assert not R.excluded(ctx, 'Ada Lovelace', row)
    R.apply(ctx)
    held = ctx.rows[0]
    assert held['byline_school'] == [] and held['_bylines'] == [(row['byline'], [])]
    for key in ('oa', 'doi', 'pi', 'identity', 'appointment', 'authorship', 'byline'):
        assert held[key] == row[key]
    ev = held['byline_affiliation_review']
    assert ev['status'] == 'held' and ev['scope'] == 'derived_school_flags_only'
    assert ev['prior_derivation'] == row['byline_affiliation_review']
    assert ev['evidence'][0]['source_kind'] == 'partial_fulltext_jats'
    assert ctx.rows[1:] == [paper('W1', pi='Grace Hopper'), paper('W2')]
    assert ctx.n['paper_review_derived_school_flags_held'] == 1
    assert not ctx.n['paper_review_rows_held'] and not ctx.n['paper_review_hits_withheld_before_identity']


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('row', [paper('W1', doi='10.9/wrong'), paper('W9', doi='10.9/W1'),
    paper('W1', doi='10.9/wrong', editions=[paper('W9', doi='10.9/W1')])])
def test_flags_hold_requires_both_identifiers_on_one_record(tmp_path, row):
    write_review(tmp_path, [flags_hold()]); ctx = context(tmp_path, [row])
    R.apply(ctx)
    assert ctx.rows == [row]


@pytest.mark.usefixtures('layout')
def test_flags_hold_survives_an_explicit_merge_without_positive_edition_fallback(tmp_path):
    write_review(tmp_path, [flags_hold(), decision('W2', 'merge', into={'oa': OA + 'W1'})])
    ctx = context(tmp_path, [paper('W1'), paper('W2', byline_school=['Foreign Author'])])
    R.apply(ctx)
    assert len(ctx.rows) == 1 and ctx.rows[0]['byline_school'] == []
    assert all(names == [] for _, names in ctx.rows[0]['_bylines'])
    assert len(ctx.rows[0]['editions']) == 1


@pytest.mark.usefixtures('layout')
def test_flags_hold_never_admits_a_missing_or_ordinary_rejected_paper(tmp_path):
    reject = decision('W1', 'reject'); reject['match'] = {'doi': '10.9/W1'}
    write_review(tmp_path, [flags_hold(), reject])
    ctx = context(tmp_path, [paper('W1')]); R.apply(ctx)
    assert not ctx.rows and ctx.n['paper_review_rows_rejected'] == 1
    assert ctx.paper_claim_review['decisions'][0]['outcome'] == 'no_current_claim'
    ctx = context(tmp_path, []); R.apply(ctx)
    assert not ctx.rows


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('change', [dict(match={'oa': OA + 'W1'}), dict(match={'doi': '10.9/W1'}),
    dict(scope='paper_admission'), dict(evidence=[dict(url='https://example.edu/a', sha256='a'*64, quote='q')])])
def test_flags_hold_requires_explicit_scope_exact_pair_and_typed_source(tmp_path, change):
    write_review(tmp_path, [flags_hold(**change)])
    with pytest.raises(ValueError, match='school flag hold'):
        R.prepare(context(tmp_path, [paper('W1')]))
