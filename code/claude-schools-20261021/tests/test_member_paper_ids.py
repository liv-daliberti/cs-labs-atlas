"""Disposable registries only: exact-work proof must not become global OA ownership."""
import copy
import json

import pytest

import atlas_ids as A
from pihier import member_paper_reviews as M
from test_atlas_ids import pi, stu, write
from test_member_paper_reviews import certify, context


def fixture(tmp_path, ordinary_twin=False):
    ctx, reviews = context(tmp_path / 'native')
    certify(ctx, reviews)
    members = list(ctx.stu[reviews[0]['pi']].values())
    links = ctx.sp
    if ordinary_twin:
        twin = stu('ext:tsinghua:other-wu', 'Haixu Wu', ['https://other.example/roster'])
        members.append(twin)
        links.append(dict(links[0]['workReview']['original'], student=twin['person']))
    return {'tsinghua': dict(pis=ctx.pis,
                            students={reviews[0]['pi']: members}, papers=ctx.rows, links=links,
                            sweep=[dict(id=ctx.rows[0]['oa'], authorships=[
                                dict(raw_author_name='Wu, Haixu', author=dict(id='https://openalex.org/A5002224926')),
                                dict(raw_author_name='Liu, Yong', author=dict(id='https://openalex.org/A5100724297'))])]),
            'example': dict(pis=[pi('Haixu Wu', oa=['https://openalex.org/A5002224926']),
                                 pi('Yong Liu', oa=['https://openalex.org/A5100724297'])],
                            students={}, papers=[], links=[], sweep=[])}


def run(root, reg, fx, sweep=True):
    write(root, fx)
    db = A.open_registry(reg, seed=False)
    try:
        result = A.run(['tsinghua', 'example'], root, db, use_sweep=sweep, today='2026-11-08')
        anchors = list(db.execute('select anchor,id from anchors order by anchor'))
        redirects = list(db.execute("select id,redirect_to from ids where status='redirect' order by id"))
    finally:
        db.close()
    members = json.loads((root / 'tsinghua' / 'students.json').read_text())
    people = {r['person']: r for rs in members.values() for r in rs}
    pis = {r['pi']: r for r in json.loads((root / 'example' / 'pis.json').read_text())}
    return people, pis, anchors, redirects, result


def test_work_only_rows_never_enter_wanted_prefilter(tmp_path, monkeypatch):
    fx = fixture(tmp_path)
    calls = []
    def lookup(school, wanted, hdir):
        calls.append((school, wanted))
        return {}
    monkeypatch.setattr(A, 'byline_author_ids', lookup)
    people, pis, _, _, _ = run(tmp_path / 'package', tmp_path / 'registry.sqlite', fx)
    assert all(not wanted for _, wanted in calls)
    assert people['ext:tsinghua:haixu-wu']['atlasId'] != pis['Haixu Wu']['atlasId']
    assert people['ext:tsinghua:yong-liu']['atlasId'] != pis['Yong Liu']['atlasId']


def test_consumption_guard_even_when_ordinary_row_populates_same_work_byline(tmp_path):
    fx = fixture(tmp_path, ordinary_twin=True)
    people, pis, anchors, _, _ = run(tmp_path / 'package', tmp_path / 'registry.sqlite', fx)
    # The ordinary route retains its existing behavior; it cannot lend its got-map
    # entry to the certified member with the identical work/byline.
    assert people['ext:tsinghua:other-wu']['atlasId'] == pis['Haixu Wu']['atlasId']
    assert people['ext:tsinghua:haixu-wu']['atlasId'] != pis['Haixu Wu']['atlasId']
    assert people['ext:tsinghua:yong-liu']['atlasId'] != pis['Yong Liu']['atlasId']
    source_urls = {x['url'] for x in fx['tsinghua']['links'][0]['workReview']['review']['proof']['chain'][2:]}
    assert not any(url in anchor for anchor, _ in anchors for url in source_urls)


def test_historical_ids_and_registry_are_exactly_unchanged_by_work_only_proof(tmp_path):
    fx = fixture(tmp_path)
    baseline = copy.deepcopy(fx)
    baseline['tsinghua']['links'] = [x['workReview']['original'] for x in fx['tsinghua']['links']]
    reg = tmp_path / 'registry.sqlite'
    old_people, old_pis, old_anchors, old_redirects, _ = run(tmp_path / 'package', reg, baseline, sweep=False)
    people, pis, anchors, redirects, _ = run(tmp_path / 'package', reg, fx)
    assert {k: r['atlasId'] for k, r in people.items()} == {k: r['atlasId'] for k, r in old_people.items()}
    assert {k: r['atlasId'] for k, r in pis.items()} == {k: r['atlasId'] for k, r in old_pis.items()}
    assert anchors == old_anchors and redirects == old_redirects
    for old, new in zip(baseline['tsinghua']['students'].values(), fx['tsinghua']['students'].values()):
        assert old == new
    # Idempotent rerun validates post-ID semantics and changes no anchors or issued IDs.
    again = run(tmp_path / 'package', reg, fx)
    assert again[2:4] == (anchors, redirects)


def test_plain_candidate_still_uses_existing_bridge_not_blanket_disabled(tmp_path):
    fx = fixture(tmp_path)
    fx['tsinghua']['links'] = [x['workReview']['original'] for x in fx['tsinghua']['links']]
    people, pis, _, _, _ = run(tmp_path / 'package', tmp_path / 'registry.sqlite', fx)
    assert people['ext:tsinghua:haixu-wu']['atlasId'] == pis['Haixu Wu']['atlasId']
    assert people['ext:tsinghua:yong-liu']['atlasId'] == pis['Yong Liu']['atlasId']


def test_prior_global_join_holds_and_rolls_back_all_registry_side_effects(tmp_path):
    fx = fixture(tmp_path)
    old = copy.deepcopy(fx)
    old['tsinghua']['links'] = [x['workReview']['original'] for x in old['tsinghua']['links']]
    reg = tmp_path / 'registry.sqlite'
    root = tmp_path / 'package'
    run(root, reg, old)
    write(root, fx)
    source_before = copy.deepcopy(fx)
    before_files = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    db = A.open_registry(reg, seed=False)
    try:
        before = A.registry_fingerprint(db)
        with pytest.raises(ValueError, match='change an issued member ID'):
            A.run(['tsinghua', 'example'], root, db, today='2026-11-08')
        assert A.registry_fingerprint(db) == before
        assert not db.in_transaction
        assert before_files == {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
        assert fx == source_before
    finally:
        db.close()


def test_scoped_savepoint_preserves_caller_owned_transaction(tmp_path):
    fx = fixture(tmp_path)
    root = tmp_path / 'package'; write(root, fx)
    db = A.open_registry(tmp_path / 'registry.sqlite', seed=False)
    try:
        # An unrelated caller-side table/edit must survive a guarded failure.
        db.execute('create table caller_note (value text)')
        db.execute("insert into caller_note values ('uncommitted caller input')")
        before = A.registry_fingerprint(db)
        with pytest.raises(ValueError, match='caller transaction retained'):
            A.run(['tsinghua', 'example'], root, db, today='2026-11-08')
        assert db.in_transaction and A.registry_fingerprint(db) == before
        # Explicit staging is allowed without committing the caller's transaction.
        result = A.run(['tsinghua', 'example'], root, db, today='2026-11-08', write=False)
        assert result['report']['stats']['exact_work_links_validated'] == 2
        assert db.in_transaction and db.execute('select value from caller_note').fetchone()[0] == 'uncommitted caller input'
        db.rollback()
        assert db.execute('select count(*) from ids').fetchone()[0] == 0
        assert db.execute('select count(*) from caller_note').fetchone()[0] == 0
    finally:
        db.close()


def test_post_id_invariance_failure_rolls_back_before_publication(tmp_path, monkeypatch):
    fx = fixture(tmp_path)
    root = tmp_path / 'package'; write(root, fx)
    before_files = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*.json')}
    real = M.validate_scoped
    def check(school, members, papers, links, *, pis):
        if links and 'studentAtlasId' in links[0]:
            raise ValueError('injected post-ID semantic mismatch')
        return real(school, members, papers, links, pis=pis)
    monkeypatch.setattr(M, 'validate_scoped', check)
    db = A.open_registry(tmp_path / 'registry.sqlite', seed=False)
    try:
        with pytest.raises(ValueError, match='post-ID'):
            A.run(['tsinghua', 'example'], root, db, today='2026-11-08')
        assert db.execute('select count(*) from ids').fetchone()[0] == 0
        assert before_files == {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*.json')}
    finally:
        db.close()


@pytest.mark.parametrize('change', ['role', 'paper_date', 'proof_scope', 'proof_basis', 'missing_proof', 'pi_identity'])
def test_stale_or_malformed_work_proof_rejected_before_any_id_write(tmp_path, change):
    fx = fixture(tmp_path)
    data = fx['tsinghua']
    if change == 'role': next(iter(data['students'].values()))[0]['roles'].append('staff')
    if change == 'paper_date': data['papers'][0]['date'] = '2023'
    if change == 'proof_scope': data['links'][0]['workReview']['identity_scope'] = 'global_person'
    if change == 'proof_basis': data['links'][0]['basis'] = 'advisee_name_on_lab_paper_byline'
    if change == 'missing_proof': data['links'][0].pop('workReview')
    if change == 'pi_identity': data['pis'][0]['identityHold'] = {'why': 'unresolved source ownership'}
    root = tmp_path / 'package'; write(root, fx)
    db = A.open_registry(tmp_path / 'registry.sqlite', seed=False)
    try:
        before = db.total_changes
        with pytest.raises(ValueError, match='exact-work'):
            A.run(['tsinghua', 'example'], root, db, today='2026-11-08')
        assert db.total_changes == before
        assert db.execute('select count(*) from ids').fetchone()[0] == 0
    finally:
        db.close()
