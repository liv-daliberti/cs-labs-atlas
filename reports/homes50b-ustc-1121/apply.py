"""Validate or apply the second disjoint reviewed 50-row home-only batch.

Run from code with its project interpreter and PYTHONPATH=tools:
  python reports/homes50b-ustc-1121/apply.py [--apply]
The immutable decisions and independent receipt accompany this script.
It preserves every existing non-batch department decision and other PI data.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path

import atlas_paths as P
import home_department_registry as HOME
import lab_home_audit as AUDIT
import schema_check
import school_config as S
from home_departments_school import apply_reviewed_homes


HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def verify_name(pi, evidence, review_rows, persons):
    """Reuse recorded identities; do not turn faculty-role pointers into names."""
    proof = evidence['identity_basis']
    literal = ''.join(evidence['quote'].split())
    kind = proof['kind']
    if kind == 'existing_package_alias':
        assert literal == ''.join(proof['alias'].split())
        assert proof['alias'] in pi['names']
    elif kind == 'accepted_census_name':
        row = review_rows[pi['pi']]
        assert row['decision'] == 'accepted'
        assert 'MEDIUM (owner decision pending)' not in (row.get('reason') or '')
        recorded = row.get('census_name') or row.get('cjk_name')
        assert recorded == proof['census_name'] and literal == ''.join(recorded.split())
        assert row.get('source_id') == proof['source_id']
        digest = hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        assert digest == proof['review_record_sha256']
    elif kind == 'native_dblp_owned_homepage':
        pid = proof['person_id']
        assert pid in pi['dblp'] and literal == ''.join(proof['subject_name'].split())
        key = AUDIT.homepage_key(proof['homepage'])
        assert key and AUDIT.homepage_owners(persons).get(key) == {pid}
        person = next(row for row in persons if row['pid'] == pid)
        assert key in {AUDIT.homepage_key(url) for url in person.get('urls') or []}
    else:
        raise AssertionError(f'Unreviewed identity proof type: {kind}')


def counts():
    result = collections.Counter()
    for charter in sorted(P.SCHOOL_CONFIGS.glob('*.toml')):
        school = charter.stem
        path = P.data('pis.json', school)
        if not path.exists():
            continue
        homes = {row['name']: row for row in HOME.load(school)}
        for pi in read(path):
            result['labs'] += 1
            row = homes.get(pi['pi'])
            if not row:
                result['no_decision'] += 1
            elif row.get('status') != 'accepted' or not row.get('home_department'):
                result['held_or_empty'] += 1
            elif not HOME.valid_evidence(row):
                result['incomplete_evidence'] += 1
            else:
                result['accepted'] += 1
    return dict(result)


def main(apply=False):
    decisions = read(HERE / 'decisions.json')
    receipt = read(HERE / 'independent-review.json')
    assert receipt['pass_count'] == receipt['selected_count'] == len(decisions) == 50
    assert receipt['concrete_decisions_sha256'] == hashlib.sha256((HERE / 'decisions.json').read_bytes()).hexdigest()
    reviews = {row['name']: row for row in receipt['verdicts']}
    assert set(reviews) == set(decisions)
    assert all(row['verdict'] == 'pass' and row['original_sha256_verified'] for row in reviews.values())
    schema = read(P.CODE / 'schemas/home-department-decisions.schema.json')
    errors = schema_check.validate(decisions, schema)
    assert not errors, errors
    cfg = S.get('ustc')
    known = ({d['name'] for d in cfg.get('departments') or []}
             | {d['name'] for d in cfg.get('affiliated_units') or []}
             | set(S.field(cfg, 'census.home_units') or {}))
    pis = {row['pi']: row for row in read(P.data('pis.json', 'ustc'))}
    review_rows = {row['name']: row for row in read(P.data('cs-related-review.json', 'ustc'))['decisions']
                   if row.get('decision') == 'accepted'}
    persons = read(P.data('dblp-affiliated.json', 'ustc'))['persons']
    first_batch = read(P.CODE / 'reports/homes50-ustc-1121/decisions.json')
    assert not set(first_batch) & set(decisions), 'The second batch must be disjoint'
    for name, decision in decisions.items():
        assert name in pis and decision['home_department'] in known
        verify_name(pis[name], decision['home_department_evidence'][0], review_rows, persons)
        proof = decision['home_department_evidence'][0]['identity_basis']
        if proof['kind'] == 'native_dblp_owned_homepage':
            assert decision['home_department_evidence'][2]['quote'] == proof['link_quote']
        assert reviews[name]['reviewed_evidence'] == decision['home_department_evidence']
        assert reviews[name]['home_department'] == decision['home_department']

    path = P.data('home-departments-school.json', 'ustc')
    original_bytes = path.read_bytes()
    original = json.loads(original_bytes)
    old = {row['name']: row for row in original}
    new_rows = [dict(school='ustc', name=name, home_department=None, also=[],
                     no_academic_department=False, status='hold', evidence=None)
                for name in decisions]
    apply_reviewed_homes(new_rows, decisions, lambda unit: unit)
    assert all(HOME.valid_evidence(row) and HOME.review(row)['primary_resolved'] for row in new_rows)
    new = {row['name']: row for row in new_rows}
    collisions = set(old) & set(new)
    assert not collisions or all(old[name] == new[name] for name in collisions), sorted(collisions)
    projected = [row for row in original if row['name'] not in new] + new_rows
    assert {row['name']: row for row in projected if row['name'] not in new} == {
        name: row for name, row in old.items() if name not in new}
    shared = read(P.data('home-departments.json'))
    merged = {row['name']: row for row in HOME.merge_rows(shared, projected, 'ustc')}
    assert all(merged[name] == new[name] for name in decisions)
    preview = HERE / 'projected-home-departments.json'
    preview.write_text(json.dumps(projected, ensure_ascii=False, indent=1) + '\n')
    before = counts()
    if apply:
        registered = read(P.data('home-department-decisions-school.json', 'ustc'))
        assert all(registered.get(name) == row for name, row in decisions.items()), 'Land the reviewed decisions first'
        assert path.read_bytes() == original_bytes, 'The live register changed; rerun instead of overwriting'
        path.write_bytes(preview.read_bytes())
        accepted = HOME.accepted('ustc')
        assert all(accepted[name] == new[name] for name in decisions)
    after = counts() if apply else None
    result = dict(selected=50, applied=apply, idempotent_already_present=len(collisions),
                  previous_local_rows=len(original), projected_local_rows=len(projected),
                  before=before, after=after)
    if apply:
        expected_gain = len(new) - len(collisions)
        assert after['accepted'] - before['accepted'] == expected_gain
        assert before['no_decision'] - after['no_decision'] == expected_gain
        (HERE / 'application.json').write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    main(parser.parse_args().apply)
