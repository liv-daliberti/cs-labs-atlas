"""Validate and project all 62 independently reviewed final home-allocation records.

From the landed code checkout with the project interpreter and PYTHONPATH=tools:
  python reports/homes-final-1123/apply_all.py [--apply]
The two independently reviewed parts are checked against their exact union.
Only the 16 school home registers are written. Other decisions and all prior
350 reviewed allocations stay exact. --apply requires the durable inputs landed.
"""
import argparse
import collections
import copy
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
    return {k: result[k] for k in ('labs', 'accepted', 'no_decision', 'held_or_empty', 'incomplete_evidence')}


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
    elif kind in ('existing_named_pi_profile', 'existing_named_pi_basis'):
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
    elif kind == 'accepted_census_name':
        assert review['decision'] == proof['decision'] == 'accepted'
        assert digest(review) == proof['review_record_sha256']
        assert proof['source_id'] == review['source_id']
        assert proof['census_name'] == review['census_name']
        assert re.sub(r'\s+', '', proof['census_name']) == re.sub(r'\s+', '', evidence['quote'])
    elif kind == 'existing_accepted_review_alias':
        assert review['decision'] == 'accepted' and digest(review) == proof['review_record_sha256']
        assert proof['alias'] in review['aliases']
        assert proof['alias'].casefold() == evidence['quote'].casefold()
    elif kind == 'existing_accepted_subject_mapping':
        assert review['decision'] == 'accepted' and digest(review) == proof['review_record_sha256']
        assert proof['canonical_name'] == name
        assert proof['source_display_name'] == evidence['quote']
        assert proof['accepted_binding_quote'] in review['reason']
        assert evidence['quote'] in proof['accepted_binding_quote']
    else:
        raise AssertionError(f'{school}/{name}: unreviewed subject proof: {kind}')


def main(apply=False):
    decisions = read(HERE / 'combined-decisions.json')
    receipt = read(HERE / 'combined-review-manifest.json')
    size = sum(len(rows) for rows in decisions.values())
    assert receipt['selected_count'] == receipt['pass_count'] == size == 62
    assert receipt['concrete_decisions_sha256'] == hashlib.sha256((HERE / 'combined-decisions.json').read_bytes()).hexdigest()
    assert receipt['kind'] == 'aggregate_of_existing_independent_receipts'
    assert len(receipt['parts']) == 2
    assert {part['folder'] for part in receipt['parts']} == {'homes50h-1123', 'homes-final-1123'}
    reviewed_decisions = {}
    reviewed_verdicts = {}
    for part in receipt['parts']:
        folder = HERE.parent / part['folder']
        assert hashlib.sha256((folder / 'decisions.json').read_bytes()).hexdigest() == part['decisions_sha256']
        assert hashlib.sha256((folder / 'independent-review.json').read_bytes()).hexdigest() == part['review_receipt_sha256']
        reviewed = read(folder / 'independent-review.json')
        assert reviewed['concrete_decisions_sha256'] == part['decisions_sha256']
        assert reviewed['selected_count'] == reviewed['pass_count']
        part_decisions = read(folder / 'decisions.json')
        part_keys = {(school, name) for school, entries in part_decisions.items() for name in entries}
        part_verdicts = {(v['school'], v['name']): v for v in reviewed['verdicts']}
        assert len(reviewed['verdicts']) == reviewed['selected_count'] == len(part_keys)
        assert set(part_verdicts) == part_keys
        assert not set(reviewed_decisions).intersection(part_keys)
        for school, entries in part_decisions.items():
            for name, entry in entries.items():
                reviewed_decisions[school, name] = entry
        reviewed_verdicts.update(part_verdicts)
    reviews = {(row['school'], row['name']): row for row in receipt['verdicts']}
    assert len(receipt['verdicts']) == size
    assert {(school, name): entry for school, entries in decisions.items() for name, entry in entries.items()} == reviewed_decisions, 'Combined decisions differ from independently reviewed parts'
    assert reviews == reviewed_verdicts, 'Combined verdicts differ from independent receipts'
    schema = read(P.CODE / 'schemas/home-department-decisions.schema.json')
    shared = read(P.data('home-departments.json'))
    baseline = read(HERE / 'combined-prior-home-records.json')
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
            assert verdict['primary_unresolved'] == entry.get('primary_unresolved', [])
            verify_subject(school, name, entry, pis[name], accepted_reviews.get(name))
        path = P.data('home-departments-school.json', school)
        original_bytes = path.read_bytes()
        original = json.loads(original_bytes)
        original_map = {row['name']: row for row in original}
        current = {row['name']: row for row in HOME.load(school)}
        for name in entries:
            assert current.get(name) == baseline[school][name], 'Selected record changed: review it again'
            assert not current.get(name) or current[name].get('status') != 'accepted' or not HOME.valid_evidence(current[name])
        added = [copy.deepcopy(current[name]) if name in current else
                 dict(school=school, name=name, home_department=None, also=[], status='hold',
                      no_academic_department=False, evidence=None) for name in entries]
        apply_reviewed_homes(added, entries, lambda unit: unit)
        # An equivalent legacy spelling is the same home, not a secondary unit.
        for row in added:
            old_home = (baseline[school][row['name']] or {}).get('home_department')
            normalized = re.sub(r'^Department of\s+', '', old_home or '').strip()
            normalized = next((label for label, rx in (S.field(cfg, 'census.home_units') or {}).items() if re.search(rx, normalized, re.I)), normalized)
            if normalized == row['home_department'] and old_home != normalized:
                row['also'] = [u for u in row.get('also', []) if u != old_home]
        for row in added:
            expected = entries[row['name']].get('primary_unresolved') or []
            assert HOME.valid_evidence(row) and row['status'] == 'accepted'
            assert HOME.review(row)['primary_resolved'] == (not bool(expected))
            assert (row.get('primary_unresolved') or []) == expected
        new = {row['name']: row for row in added}
        collisions = set(new) & set(original_map)
        assert all(original_map[name].get('status') != 'accepted' or not HOME.valid_evidence(original_map[name]) for name in collisions)
        assert all(original_map[name] == baseline[school][name] for name in collisions)
        projected = [row for row in original if row['name'] not in new] + added
        assert {row['name']: row for row in projected if row['name'] not in new} == {
            name: row for name, row in original_map.items() if name not in new}
        merged = {row['name']: row for row in HOME.merge_rows(shared, projected, school)}
        assert all(merged[name] == new[name] for name in new)
        plans[school] = dict(path=path, before_bytes=original_bytes, projected=projected,
                             gain=len(new), from_hold=sum(baseline[school][name] is not None and baseline[school][name].get('status') != 'accepted' for name in entries),
                             from_incomplete=sum(baseline[school][name] is not None and baseline[school][name].get('status') == 'accepted' and not HOME.valid_evidence(baseline[school][name]) for name in entries),
                             from_no_decision=sum(baseline[school][name] is None for name in entries),
                             existing_rows=len(original), new=new)
    # Prior 350 allocations remain exact, including schools written by this batch.
    prior_entries = {'ustc': {}}
    for batch in ('homes50-ustc-1121', 'homes50b-ustc-1121'):
        prior_entries['ustc'].update(read(P.CODE / 'reports' / batch / 'decisions.json'))
    prior_entries.update(read(P.CODE / 'reports/homes50c-1121/decisions.json'))
    for school, entries in read(P.CODE / 'reports/homes50d-1123/decisions.json').items():
        prior_entries.setdefault(school, {}).update(entries)
    for school, entries in read(P.CODE / 'reports/homes50e-1123/decisions.json').items():
        prior_entries.setdefault(school, {}).update(entries)
    for school, entries in read(P.CODE / 'reports/homes50f-1123/decisions.json').items():
        prior_entries.setdefault(school, {}).update(entries)
    for school, entries in read(P.CODE / 'reports/homes50g-1123/decisions.json').items():
        prior_entries.setdefault(school, {}).update(entries)
    assert sum(map(len, prior_entries.values())) == 350
    protected = {school: P.data('home-departments-school.json', school).read_bytes()
                 for school in prior_entries if school not in plans}
    prior_rows = {}
    for school, entries in prior_entries.items():
        accepted = HOME.accepted(school)
        prior_rows[school] = {name: accepted[name] for name in entries}
        for name, entry in entries.items():
            assert accepted[name]['home_department'] == entry['home_department']
            assert accepted[name]['reviewed_home_evidence'] == entry['home_department_evidence']
    (HERE / 'combined-projected-home-departments.json').write_text(json.dumps(
        {school: plan['projected'] for school, plan in plans.items()}, ensure_ascii=False, indent=1) + '\n')
    before = counts()
    if apply:
        for school, plan in plans.items():
            registered = read(P.data('home-department-decisions-school.json', school))
            assert all(registered.get(name) == entry for name, entry in decisions[school].items()), 'Land decisions first'
            assert plan['path'].read_bytes() == plan['before_bytes'], 'Register changed: rerun, do not overwrite'
        for school, plan in plans.items():
            path = plan['path']
            temporary = path.with_name(path.name + '.homesfinal.part')
            temporary.write_text(json.dumps(plan['projected'], ensure_ascii=False, indent=1) + '\n')
            assert path.read_bytes() == plan['before_bytes'], 'Register changed during projection'
            temporary.replace(path)
        for school, plan in plans.items():
            merged = HOME.accepted(school)
            assert all(merged[name] == row for name, row in plan['new'].items())
        assert all(P.data('home-departments-school.json', school).read_bytes() == raw
                   for school, raw in protected.items())
        for school, entries in prior_rows.items():
            accepted = HOME.accepted(school)
            assert all(accepted[name] == row for name, row in entries.items())
    after = counts() if apply else None
    joint_count = sum(bool(e.get('primary_unresolved')) for es in decisions.values() for e in es.values())
    result = dict(selected=62, primary_resolved=62 - joint_count, primary_unresolved=joint_count, applied=apply, previous_350_preserved=True, before=before, after=after,
                  schools={school: dict(existing_rows=plan['existing_rows'], projected_rows=len(plan['projected']),
                                        accepted_gain=plan['gain'], from_hold=plan['from_hold'],
                                        from_no_decision=plan['from_no_decision'], from_incomplete=plan['from_incomplete']) for school, plan in plans.items()})
    if apply:
        gain = sum(plan['gain'] for plan in plans.values())
        from_hold = sum(plan['from_hold'] for plan in plans.values())
        from_missing = sum(plan['from_no_decision'] for plan in plans.values())
        from_incomplete = sum(plan['from_incomplete'] for plan in plans.values())
        assert gain == from_hold + from_missing + from_incomplete == 62
        assert before['incomplete_evidence'] - after.get('incomplete_evidence', 0) == from_incomplete
        assert after['accepted'] - before['accepted'] == gain
        assert before.get('no_decision', 0) - after.get('no_decision', 0) == from_missing
        assert before.get('held_or_empty', 0) - after.get('held_or_empty', 0) == from_hold
        (HERE / 'combined-application.json').write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    main(parser.parse_args().apply)
