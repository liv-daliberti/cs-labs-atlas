"""Reciprocal, cited co-advising evidence joins external memberships, never names alone."""
import copy
import json

import pytest

import atlas_ids as A
from test_atlas_ids import paper, pi, stu, write


CASES = [
    ('Jingyi Chen', 'Shing-Chi Cheung', 'Jiasi Shen',
     'Jingyi Chen (PhD student) co-supervised with Prof Jiasi Shen',
     'Jingyi Chen (co-supervised with Shing-Chi Cheung)'),
    ('Dong Chen', 'Shuai Wang', 'Wei Wang',
     'Dong Chen (2022 Fall) Co-advised with Prof. Wei Wang',
     'Dong Chen, Ph.D. Student, co-supervised with Prof. Shuai Wang, 2022 - Present'),
    ('Zhaochen Su', 'Yi R. Fung', 'Junxian He',
     'Zhaochen Su (co-advised w/ Junxian)', 'Zhaochen Su PhD, co-advised w/ Yi R. Fung'),
]


def fixture(case=CASES[0], quotes=True):
    name, first, second, q1, q2 = case
    person = 'ext:example:' + A.slug(name)
    records = [stu(person, name, ['https://example.edu/first']), stu(person, name, ['https://example.edu/second'])]
    if quotes:
        for r, q in zip(records, [q1, q2]):
            r['relations'][0]['sources'][0]['quote'] = q
    return {'example': dict(pis=[pi(first), pi(second)], students={first: [records[0]], second: [records[1]]},
                            papers=[paper(first, 'https://openalex.org/W1', doi='10.1000/science')], links=[], sweep=[])}


def run(root, registry, fx, reverse=False):
    write(root, fx, reverse=reverse)
    db = A.open_registry(registry, seed=False)
    try:
        return A.run(['example'], root, db, use_sweep=True, today='2026-11-08')
    finally:
        db.close()


def student_ids(result):
    return {k: v for k, v in result['person_of'].items() if k[0] == 'stu'}


@pytest.mark.parametrize('case', CASES)
def test_actual_reciprocal_quote_shapes_join_and_keep_source_distinctions(tmp_path, case):
    fx = fixture(case); before = copy.deepcopy(fx['example']['students'])
    result = run(tmp_path / 'trial', tmp_path / 'registry.sqlite', fx)
    assert len(set(student_ids(result).values())) == 1
    assert result['report']['coadvised_student_groups'] == 1
    assert len(result['report']['coadvising_evidence'][0]['sources']) == 2
    after = json.loads((tmp_path / 'trial/example/students.json').read_text())
    for adviser, records in after.items():
        records[0].pop('atlasId')
        assert records == before[adviser]  # roles, years, URL/hash/quote and membership identity remain distinct
    assert result['report']['work_rows'] == 1


def test_same_native_external_id_and_name_on_different_pages_are_not_enough(tmp_path):
    result = run(tmp_path / 'trial', tmp_path / 'registry.sqlite', fixture(quotes=False))
    assert len(set(student_ids(result).values())) == 2


def test_different_native_ids_are_not_joined_from_names_or_coadvising_text(tmp_path):
    fx = fixture(); second = next(reversed(fx['example']['students'].values()))[0]; second['person'] += '-different'
    result = run(tmp_path / 'trial', tmp_path / 'registry.sqlite', fx)
    assert len(set(student_ids(result).values())) == 2


def test_given_name_only_adviser_must_be_unique_across_school_not_just_group(tmp_path):
    fx = fixture(CASES[2]); fx['example']['pis'].append(pi('Junxian Smith'))
    with pytest.raises(A.CoadvisingIDConflict, match='reciprocal'):
        run(tmp_path / 'trial', tmp_path / 'registry.sqlite', fx)


@pytest.mark.parametrize('change', ['one_sided', 'missing_hash', 'unmatched_student', 'negative', 'negated_adviser', 'different_names'])
def test_unresolved_or_contradictory_evidence_holds_before_registry_or_package_writes(tmp_path, change):
    fx = fixture(); _, second = fx['example']['students'].values(); source = second[0]['relations'][0]['sources'][0]
    if change == 'one_sided': source['quote'] = 'Jingyi Chen'
    elif change == 'missing_hash': source.pop('sha256')
    elif change == 'unmatched_student': source['quote'] = 'Other Student co-supervised with Shing-Chi Cheung'
    elif change == 'negative': source['quote'] = 'Jingyi Chen is not co-supervised with Shing-Chi Cheung'
    elif change == 'negated_adviser': source['quote'] = 'Jingyi Chen co-supervised with Someone Else, not Shing-Chi Cheung'
    else: second[0]['name'] = 'Different Student'
    root = tmp_path / 'trial'; write(root, fx); originals = {p.name: p.read_bytes() for p in (root / 'example').iterdir()}
    db = A.open_registry(tmp_path / 'registry.sqlite', seed=False)
    with pytest.raises(A.CoadvisingIDConflict) as exc:
        A.run(['example'], root, db)
    assert exc.value.holds
    assert db.execute('select count(*) from ids').fetchone()[0] == 0
    assert db.execute('select count(*) from anchors').fetchone()[0] == 0
    assert {p.name: p.read_bytes() for p in (root / 'example').iterdir()} == originals
    db.close()


def test_one_existing_issued_id_is_reused_and_order_and_rebuild_are_stable(tmp_path):
    fx = fixture(); only = copy.deepcopy(fx); only['example']['students'].pop(CASES[0][2])
    # A single membership has no duplicate external-ID group; its existing name/source anchor is issued normally.
    original = run(tmp_path / 'single', tmp_path / 'registry.sqlite', only)
    issued = next(iter(student_ids(original).values()))
    joined = run(tmp_path / 'joined', tmp_path / 'registry.sqlite', fx)
    reversed_ = run(tmp_path / 'reverse', tmp_path / 'registry.sqlite', fx, reverse=True)
    assert set(student_ids(joined).values()) == {issued}
    assert student_ids(joined) == student_ids(reversed_)
    assert joined['report']['stats'].get('redirects_new', 0) == 0


def test_two_previously_issued_ids_require_review_and_are_never_silently_redirected(tmp_path):
    reg = tmp_path / 'registry.sqlite'; before = run(tmp_path / 'before', reg, fixture(quotes=False))
    old_ids = set(student_ids(before).values()); assert len(old_ids) == 2
    root = tmp_path / 'after'; write(root, fixture()); db = A.open_registry(reg, seed=False)
    state = db.execute('select * from ids order by id').fetchall()
    with pytest.raises(A.CoadvisingIDConflict, match='issued') as exc:
        A.run(['example'], root, db)
    assert set(exc.value.holds[0]['issued_ids']) == old_ids
    assert db.execute('select * from ids order by id').fetchall() == state
    assert db.execute("select count(*)from ids where status='redirect'").fetchone()[0] == 0
    db.close()


def test_three_adviser_connected_reciprocal_graph_and_cross_school_separation(tmp_path):
    fx = fixture(); school = fx['example']; first, second = [p['pi'] for p in school['pis']]; third = 'Grace Hopper'
    school['pis'].append(pi(third)); person = school['students'][first][0]['person']
    school['students'][second][0]['relations'][0]['sources'][0]['quote'] = 'Jingyi Chen co-supervised with Shing-Chi Cheung and Grace Hopper'
    # An independent third source reciprocates the second adviser, connecting the same native person.
    record = stu(person, 'Jingyi Chen', ['https://example.edu/third'])
    record['relations'][0]['sources'][0]['quote'] = 'Jingyi Chen co-advised with Jiasi Shen'
    school['students'][third] = [record]
    fx['elsewhere'] = copy.deepcopy(school)
    write(tmp_path / 'trial', fx); db = A.open_registry(tmp_path / 'registry.sqlite', seed=False)
    result = A.run(['example', 'elsewhere'], tmp_path / 'trial', db)
    per_school = [{v for k, v in student_ids(result).items() if k[1] == school} for school in fx]
    assert all(len(ids_) == 1 for ids_ in per_school)
    assert per_school[0].isdisjoint(per_school[1])
    db.close()


def test_ambiguous_full_adviser_name_is_not_resolved_to_the_candidate_group(tmp_path):
    fx = fixture(); fx['example']['pis'].append(pi('Another faculty record', names=['Jiasi Shen']))
    with pytest.raises(A.CoadvisingIDConflict, match='reciprocal'):
        run(tmp_path / 'trial', tmp_path / 'registry.sqlite', fx)


def test_another_students_coadvising_clause_does_not_identify_this_student(tmp_path):
    fx = fixture(); source = next(iter(fx['example']['students'].values()))[0]['relations'][0]['sources'][0]
    source['quote'] = 'Jingyi Chen, Other Student co-supervised with Jiasi Shen'
    with pytest.raises(A.CoadvisingIDConflict, match='reciprocal'):
        run(tmp_path / 'trial', tmp_path / 'registry.sqlite', fx)
