"""Person-specific ID guards and reviewed shared primary pages; no role or paper admission changes."""
import copy
import collections
import json
import sys
import types

import pytest

import atlas_ids as A
from test_atlas_ids import write
from test_atlas_ids_coadvising import fixture, run, student_ids


def sources(fx):
    return [r[0]['relations'][0]['sources'][0] for r in fx['example']['students'].values()]


def proof(fx):
    name = next(iter(fx['example']['students'].values()))[0]['name']
    url = 'https://student.example/'
    ev = [dict(kind='primary_person_page', url=url, sha256='1' * 64, quote=name)]
    members = []
    for pi, records in fx['example']['students'].items():
        r = records[0]; q = r['relations'][0]['sources'][0]
        members.append(dict(pi=pi, person=r['person']))
        ev.append(dict(kind='roster_person_link', pi=pi, person=r['person'], url=q['url'], sha256=q['sha256'],
                       quote=f'<a href="{url}">{name}</a>'))
    return dict(scope='cross_lab', school='example', verdict='same_person', canonical_name=name,
                identity_url=url, memberships=members, evidence=ev)


def reviewed(root, registry, fx, reviews):
    write(root, fx)
    A.P.hfile_w(root, 'student-identity-review.json').write_text(json.dumps(reviews))
    db = A.open_registry(registry, seed=False)
    try:
        return A.run(['example'], root, db, use_sweep=True, today='2026-11-08')
    finally:
        db.close()


@pytest.mark.parametrize('quote', [
    'Current Students and Postdocs: Many of my students are co-advised. Jingyi Chen',
    'Current graduate students Other Student (co-advised with Jiasi Shen) Jingyi Chen',
    'Other Student co-supervised with Shing-Chi Cheung; Jingyi Chen',
    'Other Student is not co-advised with Jiasi Shen. Jingyi Chen',
])
def test_roster_boilerplate_or_another_student_cannot_activate_a_hold(tmp_path, quote):
    fx = fixture(quotes=False)
    for q in sources(fx): q['quote'] = quote
    result = run(tmp_path / 'trial', tmp_path / 'registry.sqlite', fx)
    assert len(set(student_ids(result).values())) == 2  # no name-only join either
    assert result['report']['shared_external_identity_groups'] == 0


@pytest.mark.parametrize('quote', [
    'Roster: Jingyi Chen is not co-advised with Jiasi Shen',
    'Jingyi Chen was never co-supervised by Jiasi Shen',
    'Jingyi Chen, PhD student, co-advised with Someone Else, not Jiasi Shen',
    'Not Jingyi Chen co-advised with Jiasi Shen',
    'Jingyi Chen has not been co-advised with Jiasi Shen',
])
def test_actual_negative_student_clause_still_holds_with_precise_original_span(tmp_path, quote):
    fx = fixture(quotes=False); sources(fx)[0]['quote'] = quote
    with pytest.raises(A.CoadvisingIDConflict, match='negative') as exc:
        run(tmp_path / 'trial', tmp_path / 'registry.sqlite', fx)
    clause = exc.value.holds[0]['student_specific_clauses'][0]
    assert quote[clause['span']['start']:clause['span']['end']] == clause['span']['text']
    assert 'Jingyi Chen' in clause['span']['text']


def test_one_sided_person_specific_claim_still_holds(tmp_path):
    fx = fixture(); sources(fx)[1]['quote'] = 'Many of my students are co-advised. Jingyi Chen'
    with pytest.raises(A.CoadvisingIDConflict, match='reciprocal'):
        run(tmp_path / 'trial', tmp_path / 'registry.sqlite', fx)


def test_actual_haoyi_shared_source_anchor_is_already_supported_identity(tmp_path):
    case = ('Haoyi Zeng', 'Nada Amin', 'Stephen Chong',
            'Haoyi Zeng (PhD Student, Fall 2025 & Spring 2026, co-advised with Steve Chong)',
            'Haoyi Zeng (PhD Student, Fall 2025 & Spring 2026, co-advised with Steve Chong)')
    fx = fixture(case); sources(fx)[1]['url'] = sources(fx)[0]['url']; before = copy.deepcopy(fx['example']['students'])
    result = run(tmp_path / 'trial', tmp_path / 'registry.sqlite', fx)
    assert len(set(student_ids(result).values())) == 1
    assert result['report']['coadvising_evidence'][0]['basis'] == 'shared_identity_anchor'
    after = json.loads((tmp_path / 'trial/example/students.json').read_text())
    for pi, rows in after.items():
        rows[0].pop('atlasId'); assert rows == before[pi]


def test_shared_anchor_does_not_silently_redirect_two_previously_issued_people(tmp_path):
    fx = fixture(quotes=False); reg = tmp_path / 'registry.sqlite'; before = run(tmp_path / 'old', reg, fx)
    assert len(set(student_ids(before).values())) == 2
    for q in sources(fx): q['quote'] = 'Jingyi Chen co-advised with Jiasi Shen'
    for records in fx['example']['students'].values():
        records[0]['relations'][0]['sources'].append(dict(url='https://example.edu/shared', sha256='3' * 64, quote='Jingyi Chen'))
    with pytest.raises(A.CoadvisingIDConflict, match='issued'):
        run(tmp_path / 'new', reg, fx)
    db = A.open_registry(reg, seed=False)
    assert db.execute("select count(*)from ids where status='redirect'").fetchone()[0] == 0; db.close()


def test_shared_anchor_does_not_override_actual_negative_clause(tmp_path):
    fx = fixture(quotes=False); sources(fx)[1]['url'] = sources(fx)[0]['url']
    sources(fx)[0]['quote'] = 'Jingyi Chen is not co-advised with Jiasi Shen'
    with pytest.raises(A.CoadvisingIDConflict, match='negative'):
        run(tmp_path / 'trial', tmp_path / 'registry.sqlite', fx)


def test_two_original_rosters_and_named_primary_page_resolve_one_sided_identity_only(tmp_path):
    fx = fixture(); sources(fx)[1]['quote'] = 'Many of my students are co-advised. Jingyi Chen'
    before = copy.deepcopy(fx['example']['students']); p = proof(fx)
    result = reviewed(tmp_path / 'trial', tmp_path / 'registry.sqlite', fx, [p])
    assert len(set(student_ids(result).values())) == 1
    assert result['report']['reviewed_cross_lab_identity_groups'] == 1
    assert result['report']['work_rows'] == 1
    after = json.loads((tmp_path / 'trial/example/students.json').read_text())
    for pi, rows in after.items():
        rows[0].pop('atlasId'); assert rows == before[pi]
    assert result['report']['reviewed_cross_lab_identity_evidence'][0]['evidence'] == p['evidence']


@pytest.mark.parametrize('change', ['missing_primary_hash', 'wrong_primary_name', 'wrong_href', 'wrong_link_name',
                                   'wrong_roster_hash', 'wrong_roster_url', 'missing_roster', 'different_person',
                                   'different_name', 'duplicate_membership', 'duplicate_proof', 'not_same_person', 'generic_link'])
def test_review_proof_must_bind_exact_named_memberships_original_sources_and_primary_page(tmp_path, change):
    fx = fixture(); p = proof(fx); reviews = [p]
    if change == 'missing_primary_hash': p['evidence'][0].pop('sha256')
    elif change == 'wrong_primary_name': p['evidence'][0]['quote'] = 'Other Student'
    elif change == 'wrong_href': p['evidence'][1]['quote'] = '<a href="https://other.example/">Jingyi Chen</a>'
    elif change == 'wrong_link_name': p['evidence'][1]['quote'] = '<a href="https://student.example/">Other Student</a>'
    elif change == 'wrong_roster_hash': p['evidence'][1]['sha256'] = '9' * 64
    elif change == 'wrong_roster_url': p['evidence'][1]['url'] = 'https://other.example/'
    elif change == 'missing_roster': p['evidence'].pop()
    elif change == 'different_person': p['memberships'][1]['person'] += '-different'
    elif change == 'different_name': next(reversed(fx['example']['students'].values()))[0]['name'] = 'Different Student'
    elif change == 'duplicate_membership': p['memberships'].append(p['memberships'][0])
    elif change == 'duplicate_proof': reviews.append(copy.deepcopy(p))
    elif change == 'not_same_person': p['verdict'] = 'different_people'
    else: p['evidence'][1]['quote'] = 'Current students Jingyi Chen'
    with pytest.raises(ValueError, match='identity review'):
        reviewed(tmp_path / 'trial', tmp_path / 'registry.sqlite', fx, reviews)
    db = A.open_registry(tmp_path / 'registry.sqlite', seed=False)
    assert db.execute('select count(*)from ids').fetchone()[0] == 0
    assert db.execute('select count(*)from anchors').fetchone()[0] == 0; db.close()


def test_reviewed_shared_page_does_not_merge_two_issued_ids(tmp_path):
    fx = fixture(quotes=False); reg = tmp_path / 'registry.sqlite'; result = run(tmp_path / 'old', reg, fx)
    ids = set(student_ids(result).values()); assert len(ids) == 2
    with pytest.raises(A.CoadvisingIDConflict, match='issued') as exc:
        reviewed(tmp_path / 'trial', reg, fx, [proof(fx)])
    assert set(exc.value.holds[0]['issued_ids']) == ids


def test_one_issued_id_is_reused_and_reviewed_root_url_spelling_is_stable(tmp_path):
    fx = fixture(quotes=False); only = copy.deepcopy(fx); only['example']['students'].pop(next(reversed(only['example']['students'])))
    reg = tmp_path / 'registry.sqlite'; result = run(tmp_path / 'old', reg, only); issued = next(iter(student_ids(result).values()))
    p = proof(fx); p['evidence'][2]['quote'] = '<a href="https://student.example">Jingyi Chen</a>'
    joined = reviewed(tmp_path / 'new', reg, fx, [p]); again = reviewed(tmp_path / 'again', reg, fx, [p])
    assert set(student_ids(joined).values()) == {issued}
    assert student_ids(joined) == student_ids(again)
    assert joined['report']['stats'].get('redirects_new', 0) == 0


def test_old_within_lab_review_shape_does_not_create_a_cross_lab_join(tmp_path):
    fx = fixture(quotes=False)
    result = reviewed(tmp_path / 'trial', tmp_path / 'registry.sqlite', fx,
                      [dict(school='example', pi='Shing-Chi Cheung', verdict='same_person', a=['a', 'Jingyi Chen'], b=['b', 'Jingyi Chen'])])
    assert len(set(student_ids(result).values())) == 2


def test_reviewed_id_survives_external_to_shared_native_person_refresh(tmp_path):
    fx = fixture(quotes=False)
    reg = tmp_path / 'registry.sqlite'
    before = reviewed(tmp_path / 'external', reg, fx, [proof(fx)])
    issued = set(student_ids(before).values())
    for records in fx['example']['students'].values():
        records[0]['person'] = 'example_native_student'
    refreshed = reviewed(tmp_path / 'native', reg, fx, [proof(fx)])
    assert set(student_ids(refreshed).values()) == issued
    assert refreshed['report']['reviewed_cross_lab_identity_groups'] == 1
    assert refreshed['report']['stats'].get('redirects_new', 0) == 0


def test_native_person_refresh_still_requires_exact_roster_link(tmp_path):
    fx = fixture(quotes=False)
    for records in fx['example']['students'].values():
        records[0]['person'] = 'example_native_student'
    review = proof(fx)
    review['evidence'][1]['sha256'] = 'f' * 64
    with pytest.raises(ValueError, match='exact membership roster link'):
        reviewed(tmp_path / 'native', tmp_path / 'registry.sqlite', fx, [review])


def test_review_metadata_does_not_waive_multiple_issued_guard(tmp_path):
    fx = fixture(quotes=False); reg = tmp_path / 'registry.sqlite'; before = run(tmp_path / 'before', reg, fx)
    old = sorted(set(student_ids(before).values())); p = proof(fx)
    p['issued_id_review'] = dict(survivor=old[0], alias=old[1], decision='prepare_explicit_redirect_in_isolated_registry_only')
    with pytest.raises(A.CoadvisingIDConflict, match='issued'):
        reviewed(tmp_path / 'held', reg, fx, [p])


def test_explicit_assign_redirect_then_standard_run_preserves_ids_facts_and_replays(tmp_path):
    fx = fixture(quotes=False); reg = tmp_path / 'registry.sqlite'; before = run(tmp_path / 'before', reg, fx)
    old = sorted(set(student_ids(before).values())); survivor, alias = old; p = proof(fx)
    # Before explicit reviewed registry preparation the ordinary safety guard still holds.
    with pytest.raises(A.CoadvisingIDConflict, match='issued'):
        reviewed(tmp_path / 'held', reg, fx, [p])
    db = A.open_registry(reg, seed=False)
    before_ids = {r[0]: r for r in db.execute('select * from ids')}
    anchors = [(A.RANK['name'], r[0]) for r in db.execute('select anchor from anchors where id in(?,?)', old)]
    stats = __import__('collections').Counter()
    assert A.assign(db, 'person', 'atl:p:', {'explicit_review': sorted(anchors)}, '2026-11-08', stats) == {'explicit_review': survivor}
    assert stats['redirects_new'] == 1
    after_ids = {r[0]: r for r in db.execute('select * from ids')}
    assert [i for i in before_ids if before_ids[i] != after_ids[i]] == [alias]
    assert before_ids[alias][:4] == after_ids[alias][:4]  # issued id/minted anchor/date never change
    assert A.resolve(db, survivor) == A.resolve(db, alias) == survivor
    again = __import__('collections').Counter()
    A.assign(db, 'person', 'atl:p:', {'explicit_review': sorted(anchors)}, '2026-11-08', again)
    assert again['redirects_new'] == 0
    assert {r[0]: r for r in db.execute('select * from ids')} == after_ids
    db.commit(); db.close()
    prepared = reviewed(tmp_path / 'prepared', reg, fx, [p])
    replay = reviewed(tmp_path / 'replay', reg, fx, [p])
    assert set(student_ids(prepared).values()) == {survivor}
    assert student_ids(prepared) == student_ids(replay)
    assert prepared['report']['stats'].get('split_minted', 0) == 0
    assert prepared['report']['stats'].get('redirects_new', 0) == 0
    after = json.loads((tmp_path / 'prepared/example/students.json').read_text())
    for pi, rows in after.items():
        rows[0].pop('atlasId'); assert rows == fx['example']['students'][pi]


def test_native_within_lab_review_stage_ignores_cross_lab_proofs_without_changing_students(tmp_path):
    from pihier import students as S
    p = proof(fixture()); A.P.data_w('student-identity-review.json', root=tmp_path).write_text(json.dumps([p]))
    ctx = types.SimpleNamespace(here=tmp_path, school='example', n=collections.Counter(), typo_pairs=[])
    students = {'One PI': {'one': dict(person='one', name='Jingyi Chen', relations=[], roles=['member'])}}
    before = copy.deepcopy(students)
    assert S.identity_review(ctx, students) == 0
    S.queue_surname_typos(ctx, students)
    assert students == before and not ctx.typo_pairs


@pytest.mark.parametrize('legacy_review', [False, True])
def test_candidate_queue_keeps_cross_lab_proof_scope_separate_from_legacy_pairs(tmp_path, monkeypatch, legacy_review):
    import student_name_candidates as Q
    p = proof(fixture()); pair = dict(school='example', pi='One PI', a=['a', 'Jingyi Chen'], b=['b', 'Jingyi Cheng'])
    review = tmp_path / 'review.json'; review.write_text(json.dumps([p] + ([dict(pair, verdict='different_people')] if legacy_review else [])))
    package = tmp_path / 'example'; package.mkdir(); (package / 'report.json').write_text(json.dumps({'studentSurnameTypoCandidates': [pair]}))
    out = tmp_path / 'queue.json'; monkeypatch.setattr(Q.P, 'SCHOOL_IDS', ['example'])
    monkeypatch.setattr(sys, 'argv', ['student_name_candidates.py', '--root', str(tmp_path), '--review', str(review), '--out', str(out)])
    Q.main()
    assert json.loads(out.read_text()) == ([] if legacy_review else [pair])


@pytest.mark.parametrize('layout', ['flat', 'split'])
def test_real_hierarchy_reads_existing_shared_review_in_both_layouts(tmp_path, monkeypatch, layout):
    import gzip
    monkeypatch.setenv('CS_ATLAS_DATA_LAYOUT', layout)
    monkeypatch.setattr(A.P, 'HIERARCHY', A.P.data('pis.json', 'example', root=tmp_path, layout='flat').parent.parent)
    fx = fixture()
    sources(fx)[1]['quote'] = 'Current students: Jingyi Chen'
    data = fx['example']
    for name, value in [('pis.json', data['pis']), ('students.json', data['students'])]:
        A.P.data_w(name, 'example').write_text(json.dumps(value))
    for name, rows in [('lab_papers.jsonl.gz', data['papers']), ('student_papers.jsonl.gz', data['links'])]:
        with gzip.open(A.P.data_w(name, 'example'), 'wt') as output:
            for row in rows:
                output.write(json.dumps(row) + '\n')
    review = A.P.data_w('student-identity-review.json')
    review.write_text(json.dumps([proof(fx)]))
    # A stale nested file must never shadow the actual hierarchy-container input.
    nested = A.P.data_w('student-identity-review.json', root=A.P.HIERARCHY)
    assert nested != review
    nested.write_text('{invalid stale nested input')
    before = copy.deepcopy(data['students'])
    db = A.open_registry(tmp_path / 'registry.sqlite', seed=False)
    try:
        result = A.run(['example'], A.P.HIERARCHY, db, use_sweep=False, today='2026-11-08')
    finally:
        db.close()
    assert len(set(student_ids(result).values())) == 1
    assert result['report']['reviewed_cross_lab_identity_groups'] == 1
    after = json.loads(A.P.data('students.json', 'example').read_text())
    for pi, rows in after.items():
        rows[0].pop('atlasId')
        assert rows == before[pi]
