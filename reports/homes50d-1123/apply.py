"""Validate and project the reviewed fourth batch of 50 academic home allocations.

From code, with the project interpreter and PYTHONPATH=tools:
  python reports/homes50d-1123/apply.py [--apply]
Only the six department registers are written. The durable reviewed inputs
must be landed before --apply. Other decisions and all previous batches stay.
"""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

import atlas_paths as P
import home_department_registry as HOME
import schema_check
import school_config as S
from home_departments_school import apply_reviewed_homes


HERE = Path(__file__).resolve().parent


def read(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def tokens(value):
    return re.findall(r'[^\W_]+', value.casefold())


def counts():
    result = collections.Counter()
    for charter in sorted(P.SCHOOL_CONFIGS.glob('*.toml')):
        school = charter.stem
        rows = read(P.data('pis.json', school))
        if rows is None:
            continue
        homes = {row['name']: row for row in HOME.load(school)}
        for pi in rows:
            result['labs'] += 1
            row = homes.get(pi['pi'])
            category = ('no_decision' if not row else
                        'held_or_empty' if row.get('status') != 'accepted' or not row.get('home_department') else
                        'incomplete_evidence' if not HOME.valid_evidence(row) else 'accepted')
            result[category] += 1
    return dict(result)


def verify_subject(school, name, entry, pi, review):
    evidence = entry['home_department_evidence'][0]
    proof = evidence['identity_basis']
    kind = proof['kind']
    if kind == 'existing_exact_alias':
        assert proof['alias'] in pi['names']
        assert proof['alias'].casefold() == evidence['quote'].casefold()
    elif kind == 'existing_family_first_alias':
        assert proof['alias'] in pi['names']
        words = tokens(proof['alias'])
        assert tokens(evidence['quote']) == words[-1:] + words[:-1]
    elif kind == 'existing_accepted_faculty_card':
        assert review['decision'] == 'accepted' and digest(review) == proof['review_record_sha256']
        row = next(row for row in review['faculty_evidence'] if digest(row) == proof['source_row_sha256'])
        assert row['sha256'] == evidence['sha256'] and row['url'] == evidence['url']
        assert ' '.join(row['quote'].split()) == proof['source_row_quote']
        assert proof['source_display_name'] == evidence['quote']
        assert proof['source_row_quote'] in entry['home_department_evidence'][1]['quote']
    elif kind == 'existing_named_pi_profile':
        assert name == proof['canonical_name'] and digest(pi['piBasis']) == proof['pi_basis_sha256']
        assert pi['piBasis']['url'] == evidence['url']
        assert pi['piBasis']['sha256'] == evidence['sha256']
        assert proof['source_display_name'] == evidence['quote']
    elif kind == 'existing_accepted_faculty_profile':
        assert review['decision'] == 'accepted' and digest(review) == proof['review_record_sha256']
        assert name == proof['canonical_name']
        row = next(row for row in review['faculty_evidence'] if digest(row) == proof['source_row_sha256'])
        assert row['sha256'] == evidence['sha256'] and row['url'] == evidence['url']
        assert row['quote'] == proof['source_row_quote']
        assert proof['source_display_name'] == evidence['quote']
    else:
        raise AssertionError(f'{school}/{name}: unreviewed subject proof: {kind}')


def main(apply=False):
    decisions = read(HERE / 'decisions.json')
    receipt = read(HERE / 'independent-review.json')
    size = sum(len(rows) for rows in decisions.values())
    assert receipt['selected_count'] == receipt['pass_count'] == size == 50
    assert receipt['concrete_decisions_sha256'] == hashlib.sha256((HERE / 'decisions.json').read_bytes()).hexdigest()
    reviews = {(row['school'], row['name']): row for row in receipt['verdicts']}
    assert set(reviews) == {(school, name) for school, rows in decisions.items() for name in rows}
    schema = read(P.CODE / 'schemas/home-department-decisions.schema.json')
    shared = read(P.data('home-departments.json'))
    plans = {}
    for school, entries in decisions.items():
        errors = schema_check.validate(entries, schema)
        assert not errors, errors
        cfg = S.get(school)
        known = ({row['name'] for row in cfg.get('departments') or []}
                 | {row['name'] for row in cfg.get('affiliated_units') or []}
                 | set(S.field(cfg, 'census.home_units') or {}))
        pis = {row['pi']: row for row in read(P.data('pis.json', school))}
        accepted_reviews = {row['name']: row for row in read(P.data('cs-related-review.json', school))['decisions']
                            if row.get('decision') == 'accepted'}
        for name, entry in entries.items():
            verdict = reviews[(school, name)]
            assert verdict['verdict'] == 'pass' and verdict['original_sha256_verified']
            assert verdict['reviewed_evidence'] == entry['home_department_evidence']
            assert verdict['home_department'] == entry['home_department'] in known
            verify_subject(school, name, entry, pis[name], accepted_reviews.get(name))
        path = P.data('home-departments-school.json', school)
        original_bytes = path.read_bytes()
        original = json.loads(original_bytes)
        original_map = {row['name']: row for row in original}
        added = [dict(school=school, name=name, home_department=None, also=[], status='hold',
                      no_academic_department=False, evidence=None) for name in entries]
        apply_reviewed_homes(added, entries, lambda unit: unit)
        assert all(HOME.review(row)['primary_resolved'] for row in added)
        new = {row['name']: row for row in added}
        collisions = set(new) & set(original_map)
        assert all(new[name] == original_map[name] for name in collisions)
        projected = [row for row in original if row['name'] not in new] + added
        assert {row['name']: row for row in projected if row['name'] not in new} == {
            name: row for name, row in original_map.items() if name not in new}
        merged = {row['name']: row for row in HOME.merge_rows(shared, projected, school)}
        assert all(merged[name] == new[name] for name in new)
        plans[school] = dict(path=path, before_bytes=original_bytes, projected=projected,
                             gain=len(new) - len(collisions), existing_rows=len(original), new=new)
    # Prior 150 allocations and their exact registers are protected independently.
    protected = {school: P.data('home-departments-school.json', school).read_bytes()
                 for school in ('ustc', 'cuhk', 'ntu', 'vt')}
    prior_entries = {'ustc': {}}
    for batch in ('homes50-ustc-1121', 'homes50b-ustc-1121'):
        prior_entries['ustc'].update(read(P.CODE / 'reports' / batch / 'decisions.json'))
    prior_entries.update(read(P.CODE / 'reports/homes50c-1121/decisions.json'))
    assert sum(map(len, prior_entries.values())) == 150
    for school, entries in prior_entries.items():
        accepted = HOME.accepted(school)
        for name, entry in entries.items():
            assert accepted[name]['home_department'] == entry['home_department']
            assert accepted[name]['reviewed_home_evidence'] == entry['home_department_evidence']
    (HERE / 'projected-home-departments.json').write_text(json.dumps(
        {school: plan['projected'] for school, plan in plans.items()}, ensure_ascii=False, indent=1) + '\n')
    before = counts()
    if apply:
        for school, plan in plans.items():
            registered = read(P.data('home-department-decisions-school.json', school))
            assert all(registered.get(name) == entry for name, entry in decisions[school].items()), 'Land decisions first'
            assert plan['path'].read_bytes() == plan['before_bytes'], 'Register changed: rerun, do not overwrite'
        for school, plan in plans.items():
            path = plan['path']
            temporary = path.with_name(path.name + '.homes50d.part')
            temporary.write_text(json.dumps(plan['projected'], ensure_ascii=False, indent=1) + '\n')
            assert path.read_bytes() == plan['before_bytes'], 'Register changed during projection'
            temporary.replace(path)
        for school, plan in plans.items():
            merged = HOME.accepted(school)
            assert all(merged[name] == row for name, row in plan['new'].items())
        assert all(P.data('home-departments-school.json', school).read_bytes() == raw
                   for school, raw in protected.items())
    after = counts() if apply else None
    result = dict(selected=50, applied=apply, previous_150_preserved=True, before=before, after=after,
                  schools={school: dict(existing_rows=plan['existing_rows'], projected_rows=len(plan['projected']),
                                        added=plan['gain']) for school, plan in plans.items()})
    if apply:
        gain = sum(plan['gain'] for plan in plans.values())
        assert after['accepted'] - before['accepted'] == before['no_decision'] - after['no_decision'] == gain
        (HERE / 'application.json').write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    main(parser.parse_args().apply)
