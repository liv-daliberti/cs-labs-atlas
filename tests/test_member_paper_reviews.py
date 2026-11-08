"""Exact-work certification: sealed real cases in curated, raw-body-free contexts.

The old 530-row package supplies regression examples, NEVER final approval
preimages. Real school review input must bind the final ordinary native output.
"""
import base64
import collections
import copy
import hashlib
import gzip
import json
import zlib
from pathlib import Path
from types import SimpleNamespace

import pytest

import atlas_paths as P
from pihier import member_paper_reviews as M
from schema_check import validate

FIXTURE = Path(__file__).parent / 'fixtures' / 'member-paper-reviews.json'


def context(tmp_path, real_source=None):
    fx = json.loads(FIXTURE.read_text())
    paper = fx['paper']
    pi = paper['pi']
    # A curated scientific view, not copied API bytes. The NFS replay below also
    # exercises the complete original projected source under its sealed digest.
    source = real_source or dict(id=paper['oa'], doi=paper['doi'], publication_year=2024,
                                 authorships=[dict(raw_author_name=a['native']) for a in fx['cases'][0]['proof']['authors']])
    ctx = SimpleNamespace(school='tsinghua', here=tmp_path, n=collections.Counter(), rows=[paper],
                          stu={pi: {c['member']['person']: c['member'] for c in fx['cases']}},
                          sp=[c['candidate'] for c in fx['cases']], hits=[(pi, source)])
    reviews = []
    for c in fx['cases']:
        reviews.append(dict(id=c['id'], pi=pi, member=c['member']['person'], reviewed_by='regression-fixture-only',
                            reviewed_at='2026-11-08', projection=M.PROJECTION,
                            match=dict(oa=paper['oa'], work=paper['work'], doi=paper['doi'], arxiv_version='2310.06625v1'),
                            preimages=M.preimages(c['candidate'], c['member'], paper, source), proof=c['proof']))
    return ctx, reviews


def put(ctx, reviews):
    path = P.data('member-paper-review.json', ctx.school, root=ctx.here)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(version=1, school=ctx.school, reviews=reviews), ensure_ascii=False))
    return path


def certify(ctx, reviews):
    put(ctx, reviews)
    M.apply(ctx)
    return ctx


def test_R_LNK_08_two_real_source_cases_change_only_two_link_statuses(tmp_path):
    ctx, reviews = context(tmp_path)
    before = copy.deepcopy(ctx)
    # Unreviewed members and other papers with the same byline do not inherit proof.
    other = dict(ctx.sp[0], oa='https://openalex.org/W99')
    ctx.sp.append(other)
    certify(ctx, reviews)
    assert [r['status'] for r in ctx.sp] == ['verified', 'verified', 'candidate']
    assert ctx.rows == before.rows and ctx.stu == before.stu and ctx.hits == before.hits
    assert (ctx.rows[0]['year'], ctx.rows[0]['date']) == (2024, '2024')
    for old, row in zip(before.sp, ctx.sp):
        assert {k: v for k, v in row.items() if k not in ('status', 'basis', 'workReview')} == {
            k: v for k, v in old.items() if k not in ('status', 'basis')}
        assert row['workReview']['original'] == old
        assert row['workReview']['review']['proof']['pdf']['date'] == '2023-10-10'
        assert row['workReview']['identity_scope'] == 'exact_work'
    M.validate_scoped(ctx.school, {p: list(v.values()) for p, v in ctx.stu.items()}, ctx.rows, ctx.sp)
    assert ctx.n['member_paper_review_verified'] == 2
    assert not validate(ctx.sp[0], json.loads((FIXTURE.parents[2] / 'schemas/student_papers.schema.json').read_text()))


def test_absent_optional_input_is_exact_noop(tmp_path):
    ctx, _ = context(tmp_path)
    before = copy.deepcopy(vars(ctx))
    M.apply(ctx)
    assert vars(ctx) == before


@pytest.mark.parametrize('part', ['candidate', 'member', 'paper', 'editions', 'source'])
def test_complete_semantic_preimages_hold_changed_fields(tmp_path, part):
    ctx, reviews = context(tmp_path)
    target = {'candidate': ctx.sp[0], 'member': next(iter(ctx.stu[ctx.sp[0]['pi']].values())),
              'paper': ctx.rows[0], 'editions': ctx.rows[0], 'source': ctx.hits[0][1]}[part]
    target['future_scientific_field'] = dict(exact='new value', nested={'sha256': '9' * 64})
    if part == 'editions':
        target['editions'].append(dict(oa='https://openalex.org/W88', date='2022', byline=['Another Author']))
    before = copy.deepcopy(ctx.sp)
    certify(ctx, reviews[:1])
    assert ctx.sp == before
    assert ctx.member_paper_review['decisions'][0]['reason'] == 'stale_semantic_preimage'


@pytest.mark.parametrize('part,field,value,reason', [
    ('proof', 'author_index', 1, 'wrong_author_slot'),
    ('citation', 'href', 'https://arxiv.org/abs/0000.00000', 'wrong_citation_identifier'),
    ('citation', 'kind', 'reading_list', 'schema'),
    ('pdf', 'url', 'https://arxiv.org/pdf/2310.06625v2', 'wrong_pdf_edition'),
    ('pdf', 'title', 'A distinct same-year paper', 'competing_title_or_edition'),
    ('pdf', 'complete_body', False, 'schema'),
    ('pdf', 'parse_returncode', 1, 'schema'),
    ('pdf', 'affiliations', [], 'schema'),
    ('period', 'start', '2023', 'timing_not_proven_at_stated_precision'),
    ('period', 'end', '2024', 'timing_not_proven_at_stated_precision'),
])
def test_wrong_partial_or_temporally_uncertain_proofs_never_verify(tmp_path, part, field, value, reason):
    ctx, reviews = context(tmp_path)
    d = reviews[0]
    target = d['proof'] if part == 'proof' else d['proof'][part]
    target[field] = value
    if part == 'period':
        # A sourced boundary year is still insufficient to certify all possible dates.
        target['quote'] = f"Ph.D. in Software Engineering, {target['start']}-{target['end']}"
    before = copy.deepcopy(ctx.sp)
    if reason == 'schema':
        with pytest.raises(ValueError, match='invalid member paper review'):
            certify(ctx, reviews[:1])
    else:
        certify(ctx, reviews[:1])
        assert ctx.member_paper_review['decisions'][0]['reason'] == reason
    assert ctx.sp == before


@pytest.mark.parametrize('change,reason', [
    ('truncated_citation', 'incomplete_or_ambiguous_printed_byline'),
    ('wrong_slot_spelling', 'incomplete_or_ambiguous_printed_byline'),
    ('wrong_affiliation', 'target_affiliation_unconfirmed'),
    ('disconnected_chain', 'disconnected_owned_chain'),
    ('wrong_adviser', 'disconnected_owned_chain'),
    ('unbound_spelling', 'unbound_spelling_map'),
    ('other_member', 'other_member_assertion'),
])
def test_owned_source_chain_and_complete_author_mapping(tmp_path, change, reason):
    ctx, reviews = context(tmp_path)
    p = reviews[0]['proof']
    if change == 'truncated_citation': p['citation']['authors'].pop()
    if change == 'wrong_slot_spelling': p['authors'][3]['printed'] = 'Haixu Other'
    if change == 'wrong_affiliation': p['pdf']['affiliations'][3]['affiliations'] = ['Ant Group, Hangzhou, China']
    if change == 'disconnected_chain': p['chain'][1]['href'] = 'https://different.example/person'
    if change == 'wrong_adviser': p['adviser_name'] = 'Another Adviser'
    if change == 'unbound_spelling': p['authors'][3]['evidence_sha256'] = '0' * 64
    if change == 'other_member': p['authors'][0]['member'] = reviews[1]['member']
    certify(ctx, reviews[:1])
    assert all(r['status'] == 'candidate' for r in ctx.sp)
    assert ctx.member_paper_review['decisions'][0]['reason'] == reason


@pytest.mark.parametrize('part', ['member', 'paper', 'candidate', 'source', 'doi', 'other_pi'])
def test_exact_native_target_required_no_rescue_or_name_alias_join(tmp_path, part):
    ctx, reviews = context(tmp_path)
    if part == 'member': ctx.stu[reviews[0]['pi']].pop(reviews[0]['member'])
    if part == 'paper': ctx.rows.clear()
    if part == 'candidate': ctx.sp.clear()
    if part == 'source': ctx.hits.append((ctx.hits[0][0], dict(ctx.hits[0][1], changed=True)))
    if part == 'doi': reviews[0]['match']['doi'] = '10.48550/arxiv.2310.06626'
    if part == 'other_pi': reviews[0]['pi'] = 'Name-Only Other PI'
    before = copy.deepcopy((ctx.stu, ctx.rows, ctx.sp))
    certify(ctx, reviews[:1])
    assert (ctx.stu, ctx.rows, ctx.sp) == before
    assert ctx.member_paper_review['decisions'][0]['status'] == 'held'


def test_duplicate_candidates_and_competing_reviews_hold_all(tmp_path):
    ctx, reviews = context(tmp_path)
    duplicate = copy.deepcopy(reviews[0]); duplicate['id'] = 'second-review'
    duplicate['proof']['citation']['href'] = 'https://arxiv.org/abs/1111.11111'
    certify(ctx, [reviews[0], duplicate])
    assert all(r['status'] == 'candidate' for r in ctx.sp)
    assert {r['reason'] for r in ctx.member_paper_review['decisions']} == {'competing_reviews'}
    ctx, reviews = context(tmp_path)
    ctx.sp.append(copy.deepcopy(ctx.sp[0]))
    certify(ctx, reviews[:1])
    assert all(r['status'] == 'candidate' for r in ctx.sp)


def test_post_id_invariance_and_stale_proof_fail_before_registry(tmp_path):
    ctx, reviews = context(tmp_path)
    certify(ctx, reviews)
    members = {p: list(v.values()) for p, v in ctx.stu.items()}
    for r in members[reviews[0]['pi']]: r.update(atlasId='atl:p:000000000000', alsoPi=[])
    ctx.rows[0]['atlasWorkId'] = 'atl:w:000000000000'
    for r in ctx.sp: r.update(studentAtlasId='atl:p:000000000000', atlasWorkId='atl:w:000000000000', labId='atl:l:example:pi')
    M.validate_scoped(ctx.school, members, ctx.rows, ctx.sp)
    exported = M.export_fields(ctx.sp[0])
    assert exported['identity_scope'] == 'exact_work' and exported['work_review']['original']['status'] == 'candidate'
    assert M.export_fields(dict(basis='collection_person_link')) == {}
    ctx.sp[0]['relation_source']['quote'] += ' altered'
    with pytest.raises(ValueError, match='stale exact-work'):
        M.validate_scoped(ctx.school, members, ctx.rows, ctx.sp)


def test_finite_owned_resolution_is_required_not_a_generic_url_alias(tmp_path):
    ctx, reviews = context(tmp_path)
    reviews[0]['proof']['link_resolutions'] = []
    certify(ctx, reviews[:1])
    assert ctx.sp[0]['status'] == 'candidate'
    assert ctx.member_paper_review['decisions'][0]['reason'] == 'disconnected_owned_chain'
    ctx, reviews = context(tmp_path)
    reviews[0]['proof']['link_resolutions'][0]['source_sha256'] = '1' * 64
    certify(ctx, reviews[:1])
    assert ctx.sp[0]['status'] == 'candidate'
    assert ctx.member_paper_review['decisions'][0]['reason'] == 'disconnected_owned_chain'


def test_evidence_checker_rejects_unknown_or_stale_work_only_proof(tmp_path):
    import evidence_check as E
    from test_atlas_ids import pi, write
    ctx, reviews = context(tmp_path)
    certify(ctx, reviews)
    fx = {'tsinghua': dict(pis=[pi(reviews[0]['pi'])], students={p: list(v.values()) for p, v in ctx.stu.items()},
                          papers=ctx.rows, links=ctx.sp, sweep=[])}
    root = tmp_path / 'package'; write(root, fx)
    result = E.check('tsinghua', root)
    assert result['link_work_review']['n'] == 0 and result['link_work_review']['of'] == 2
    ctx.sp[0]['workReview']['identity_scope'] = 'global_person'
    write(root, fx)
    result = E.check('tsinghua', root)
    assert result['link_work_review']['n'] > 0


@pytest.mark.parametrize('scoped', [False, True])
def test_release_json_and_conditional_csv_preserve_scope_and_proof(tmp_path, monkeypatch, scoped):
    import csv
    import export_release as E
    from test_atlas_ids import pi, write
    ctx, reviews = context(tmp_path / 'native')
    # English native PI spelling keeps this regression independent of the
    # pre-existing export slug policy for non-Latin names.
    old_pi = reviews[0]['pi']; name = 'Mingsheng Long'
    ctx.stu[name] = ctx.stu.pop(old_pi)
    ctx.rows[0]['pi'] = name
    for link, d in zip(ctx.sp, reviews):
        link['pi'] = name; d['pi'] = name; d['proof']['pi'] = name
        d['preimages'] = M.preimages(link, ctx.stu[name][d['member']], ctx.rows[0], ctx.hits[0][1])
    ctx.hits[0] = (name, ctx.hits[0][1])
    if scoped: certify(ctx, reviews)
    root = tmp_path / 'package'
    write(root, {'tsinghua': dict(pis=[pi(name, lab={})], students={name: list(ctx.stu[name].values())},
                                papers=ctx.rows, links=ctx.sp, sweep=[])})
    (root / 'tsinghua/report.json').write_text(json.dumps(dict(builtAt='fixture')))
    monkeypatch.setattr(E, 'H', root)
    monkeypatch.setitem(E.SITE.SCHOOLS, 'tsinghua', {})
    monkeypatch.setattr(E.SITE, 'department', lambda *a: ('Computer Science', 'full'))
    monkeypatch.setattr(E, 'site_lab_map', lambda *a: (set(), {}))
    out = tmp_path / 'export'
    E.export_school(out, 'tsinghua', [], [], {})
    exported = [json.loads(line) for line in gzip.open(out / 'data/schools/tsinghua/student_papers.jsonl.gz', 'rt')]
    table = list(csv.DictReader((out / 'data/schools/tsinghua/student_papers.csv').open()))
    assert len(exported) == len(table) == 2
    if scoped:
        assert all(r['identity_scope'] == 'exact_work' and r['work_review']['original']['status'] == 'candidate' for r in exported)
        assert all(r['identity_scope'] == 'exact_work' and len(r['review_input_sha256']) == 64 for r in table)
    else:
        assert all('identity_scope' not in r and 'work_review' not in r for r in exported)
        assert all('identity_scope' not in r for r in table)


@pytest.mark.nfs
def test_sealed_original_source_projects_to_exact_digest_and_certifies_curated_two(tmp_path):
    path = P.SCRATCH / 'tsinghua-member-paper-identities-1108' / 'two-exact-person-paper-certificates.json'
    if not path.exists(): pytest.skip('sealed private source packet is not installed')
    before = path.read_bytes()
    fx = json.loads(FIXTURE.read_text())
    assert hashlib.sha256(before).hexdigest() == fx['packet_sha256']
    packet = json.loads(before)
    original = packet['complete_original_source_work']
    blob = base64.b64decode(original['raw_original_zlib_base64'])
    assert hashlib.sha256(blob).hexdigest() == original['source_compressed_sha256']
    raw = zlib.decompress(blob)
    assert hashlib.sha256(raw).hexdigest() == original['source_uncompressed_sha256']
    from sweep_from_snapshot import project
    from pihier.common import school_scope_work
    source = school_scope_work(project(json.loads(raw)), 'tsinghua')
    assert M.digest(source) == fx['actual_projected_source_sha256']
    ctx, reviews = context(tmp_path, source)
    certify(ctx, reviews)
    assert [r['status'] for r in ctx.sp] == ['verified', 'verified']
    assert path.read_bytes() == before
    original_links = P.SCRATCH / 'tsinghua-first-chain-1108' / 'package-retry1' / 'tsinghua' / 'student_papers.jsonl.gz'
    assert hashlib.sha256(original_links.read_bytes()).hexdigest() == packet['original_530_candidate_links_sha256']
