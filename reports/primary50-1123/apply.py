"""Apply the 50 independently reviewed primary-appointment resolutions.

Run from landed code with the project interpreter and PYTHONPATH=tools:
  python reports/primary50-1123/apply.py [--apply]
Only CMU and Zhejiang home registers change. All other home rows, identities,
accepted allocations, research-unit exceptions and scientific data are retained.
"""
import argparse
import collections
import copy
import hashlib
import json
from pathlib import Path
import re

import atlas_paths as P
import home_department_registry as HOME
from home_departments_school import apply_reviewed_homes
import schema_check
import school_config as S

HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def counts():
    result = collections.Counter()
    for cfg_path in sorted(P.SCHOOL_CONFIGS.glob('*.toml')):
        school = cfg_path.stem
        path = P.data('pis.json', school)
        if not path.exists():
            continue
        homes = {row['name']: row for row in HOME.load(school)}
        for pi in read(path):
            result['labs'] += 1
            row = homes.get(pi['pi']) or {}
            result['accepted'] += int(
                row.get('status') == 'accepted' and bool(row.get('home_department')) and HOME.valid_evidence(row))
            result['primary_unresolved'] += int(bool(row.get('primary_unresolved') or row.get('home_basis') == 'primary_unresolved'))
            result['primary_resolved'] += int(HOME.review(row)['primary_resolved'])
            result['research_unit_homes'] += int(bool(row.get('no_academic_department')))
    return {k: result[k] for k in ['labs', 'accepted', 'primary_unresolved', 'primary_resolved', 'research_unit_homes']}


def verify_unselected(protected):
    for school, expected in protected.items():
        current = {row['name']: digest(row) for row in HOME.load(school)}
        assert all(current.get(name) == sha for name, sha in expected.items()), f'{school}: unselected home changed'


def main(apply=False):
    decisions = read(HERE / 'decisions.json')
    receipt = read(HERE / 'independent-review.json')
    assert sum(map(len, decisions.values())) == receipt['selected_count'] == receipt['pass_count'] == 50
    assert receipt['concrete_decisions_sha256'] == hashlib.sha256((HERE / 'decisions.json').read_bytes()).hexdigest()
    verdicts = {(r['school'], r['name']): r for r in receipt['verdicts']}
    assert len(receipt['verdicts']) == len(verdicts) == 50
    assert set(verdicts) == {(s, n) for s, entries in decisions.items() for n in entries}
    baseline = read(HERE / 'prior-home-records.json')
    protected = read(HERE / 'unselected-home-digests.json')
    verify_unselected(protected)
    for sha, source in read(HERE / 'source-receipts.json').items():
        assert source['http_status'] == 200
        assert hashlib.sha256(Path(source['raw_file']).read_bytes()).hexdigest() == sha
    schema = read(P.CODE / 'schemas/home-department-decisions.schema.json')
    shared_path = P.data('home-departments.json')
    shared_bytes = shared_path.read_bytes()
    shared = json.loads(shared_bytes)
    plans = {}
    for school, entries in decisions.items():
        assert not schema_check.validate(entries, schema)
        cfg = S.get(school)
        units = S.field(cfg, 'census.home_units') or {}
        known = set(units) | {u['name'] for u in cfg.get('departments', [])}
        pis = {p['pi']: p for p in read(P.data('pis.json', school))}
        current = {r['name']: r for r in HOME.load(school)}
        path = P.data('home-departments-school.json', school)
        before_bytes = path.read_bytes()
        original = json.loads(before_bytes)
        additions = []
        for name, entry in entries.items():
            old = current[name]
            assert old == baseline[school][name], f'{school}/{name}: selected row changed'
            assert old['status'] == 'accepted' and HOME.valid_evidence(old)
            assert old.get('primary_unresolved') or old.get('home_basis') == 'primary_unresolved'
            verdict = verdicts[school, name]
            assert verdict['verdict'] == 'pass' and verdict['original_sha256_verified']
            assert verdict['home_department'] == entry['home_department'] in known
            assert verdict['reviewed_evidence'] == entry['home_department_evidence']
            assert verdict['primary_unresolved'] == entry['primary_unresolved'] == []
            identity = entry['home_department_evidence'][0]['identity_basis']
            assert identity['kind'] == 'existing_exact_alias'
            assert identity['alias'] in pis[name]['names']
            assert identity['alias'] == entry['home_department_evidence'][0]['quote']
            assert digest(pis[name]) == identity['pi_record_sha256']
            home = entry['home_department']
            value = re.sub(r'^Department of\s+', '', home).strip()
            value = next((label for label, rx in units.items() if re.search(rx, value, re.I)), value)
            assert value == home
            additions.append(copy.deepcopy(old))
        apply_reviewed_homes(additions, entries, lambda u: u)
        for row in additions:
            name = row['name']
            assert HOME.review(row)['primary_resolved'] and not row.get('primary_unresolved')
            old = baseline[school][name]
            named = {old['home_department']} | set(old.get('also') or []) | set(old.get('primary_unresolved') or [])
            assert named <= {row['home_department']} | set(row.get('also') or []), f'{name}: lost prior affiliation'
        new = {r['name']: r for r in additions}
        projected = [r for r in original if r['name'] not in new] + additions
        merged = {r['name']: r for r in HOME.merge_rows(shared, projected, school)}
        assert all(merged[name] == row for name, row in new.items())
        plans[school] = dict(path=path, before_bytes=before_bytes, projected=projected, new=new)
    (HERE / 'projected-home-departments.json').write_text(json.dumps(
        {s: p['projected'] for s, p in plans.items()}, ensure_ascii=False, indent=1) + '\n')
    before = counts()
    if apply:
        for school, entries in decisions.items():
            registered = read(P.data('home-department-decisions-school.json', school))
            assert all(registered.get(n) == e for n, e in entries.items()), 'Land reviewed decisions before applying'
            assert plans[school]['path'].read_bytes() == plans[school]['before_bytes']
        for school, plan in plans.items():
            temp = plan['path'].with_name(plan['path'].name + '.primary50.part')
            temp.write_text(json.dumps(plan['projected'], ensure_ascii=False, indent=1) + '\n')
            assert plan['path'].read_bytes() == plan['before_bytes']
            temp.replace(plan['path'])
        assert shared_path.read_bytes() == shared_bytes
        verify_unselected(protected)
        for school, plan in plans.items():
            accepted = HOME.accepted(school)
            assert all(accepted[name] == row for name, row in plan['new'].items())
    after = counts() if apply else None
    result = dict(selected=50, applied=apply, before=before, after=after,
                  all_unselected_home_rows_preserved=True, all_prior_affiliations_retained=True,
                  schools={s: len(p['new']) for s, p in plans.items()})
    if apply:
        assert after['primary_unresolved'] == before['primary_unresolved'] - 50
        assert after['primary_resolved'] == before['primary_resolved'] + 50
        assert after['accepted'] == before['accepted']
        assert after['research_unit_homes'] == before['research_unit_homes']
        (HERE / 'application.json').write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    main(parser.parse_args().apply)
