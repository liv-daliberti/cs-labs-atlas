"""Audit every live PI lab plus every row of the PI inventory, without changing inputs.

Writes CSVs, source hashes, and a JSON summary to --out. A recorded assignment is
not a fresh verification of its original web capture. Missing, ambiguous, and
conflicting decisions remain explicit; name-only fuzzy matches are never used.
"""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import io
import json
import re
from pathlib import Path

import atlas_paths as P
import home_department_registry as HOME
import school_config as S


def sequence(doc):
    return doc if isinstance(doc, list) else (doc or {}).get('faculty', [])


def normalize(unit, cfg, aliases=None):
    unit = (aliases or {}).get(unit, unit) or ''
    codes = {r['code']: r['name'] for r in S.listing_units(cfg)}
    unit = codes.get(unit, unit)
    unit = re.sub(r'^Department of\s+', '', unit).strip()
    for canonical, pattern in (S.field(cfg, 'census.home_units') or {}).items():
        if re.search(pattern, unit, re.I):
            return canonical
    return unit


def assess(row, shared, local, cfg, rules):
    issues = []
    if not row:
        return ['missing_home']
    if row.get('status') != 'accepted' or not row.get('home_department'):
        issues.append('held_home')
    if not HOME.valid_evidence(row):
        issues.append('incomplete_evidence')
    if not row.get('home_basis'):
        issues.append('home_basis_unrecorded')
    if row.get('home_basis') == 'primary_unresolved' or row.get('primary_unresolved'):
        issues.append('primary_unresolved')
    aliases = rules.get('aliases') or {}
    norm = lambda u: normalize(u, cfg, aliases)
    if shared and local and shared.get('status') == local.get('status') == 'accepted' \
            and norm(shared.get('home_department')) != norm(local.get('home_department')):
        if not (local.get('home_basis') == 'primary_stated' and HOME.valid_evidence(local)):
            issues.append('shared_local_conflict')
    centers = {norm(c) for c in list(S.field(cfg, 'census.center_units') or []) + list(rules.get('centers') or [])}
    if norm(row.get('home_department')) in centers and not row.get('no_academic_department'):
        issues.append('center_instead_of_department')
    if 'also listed by' in (row.get('note') or '') and not row.get('home_basis'):
        issues.append('multiple_listings_primary_unreviewed')
    return issues


def proposed_from_listing(pi, cfg):
    """Suggest only a single charter department with a same-unit faculty listing.

    Proposals never become reviewed decisions or alter consumer results.
    """
    codes = pi.get('departments') or []
    deps = {d['code']: d['name'] for d in cfg.get('departments') or []}
    if len(codes) != 1 or codes[0] not in deps or pi.get('rank') in ('courtesy', 'affiliated_other_school'):
        return None
    evs = [s for s in pi.get('listings') or [] if s.get('kind') == 'dept_listing:' + codes[0]]
    evs = [s for s in evs if HOME.valid_evidence({'evidence': s})]
    if not evs:
        return None
    ev = max(evs, key=lambda s: (s.get('year') or 0, s.get('url') or ''))
    return dict(home_department=deps[codes[0]], evidence={k: ev[k] for k in ('url', 'sha256', 'quote')},
                basis='single_department_listing_requires_review')


def audit(inventory, out):
    manifest = {}

    def read(path, default=None):
        path = Path(path)
        if not path.exists():
            return default
        before = path.stat()
        data = path.read_bytes()
        after = path.stat()
        if (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
            raise RuntimeError(f'input changed while reading: {path}')
        manifest[str(path)] = dict(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
        if path.suffix == '.csv':
            return list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))
        return json.loads(data)

    baseline = read(inventory, [])
    records = {(r['school'], r['pi']): dict(inventory=r, built=None, census=None) for r in baseline}
    shared = read(P.data('home-departments.json'), [])
    schools = sorted(set(r['school'] for r in baseline) | {d.name for d in P.HIERARCHY.iterdir()
                     if d.is_dir() and P.data('pis.json', d.name).exists()})
    results = []
    for school in schools:
        cfg = S.get(school)
        charter = Path(S.__file__).resolve().parents[1] / 'schools' / (school + '.toml')
        if charter.exists():
            b = charter.read_bytes()
            manifest[str(charter)] = dict(sha256=hashlib.sha256(b).hexdigest(), bytes=len(b))
        local = read(P.data('home-departments-school.json', school), [])
        sm = {r['name']: r for r in shared if r.get('school') == school}
        lm = {r['name']: r for r in local}
        merged = {r['name']: r for r in HOME.merge_rows(shared, local, school)}
        rules = read(P.HIERARCHY / school / 'reviewed/home-department-rules.json', {})
        pis = read(P.data('pis.json', school), [])
        for pi in pis:
            records.setdefault((school, pi['pi']), dict(inventory=None, built=None, census=None))['built'] = pi
        overrides = read(P.data('census-overrides-school.json', school), {})
        for filename in ('census-faculty.json', 'census-additions.json'):
            for c in sequence(read(P.data(filename, school), [])):
                if c.get('is_pi') and not (overrides.get(c['name']) or {}).get('exclude'):
                    records.setdefault((school, c['name']), dict(inventory=None, built=None, census=None))['census'] = c
        for (s, name), item in sorted(records.items()):
            if s != school:
                continue
            r = merged.get(name)
            issues = assess(r, sm.get(name), lm.get(name), cfg, rules)
            pi = item['built'] or {}
            proposal = proposed_from_listing(pi, cfg) if not r else None
            evidence = (r or {}).get('evidence') or {}
            results.append(dict(school=school, pi=name, live_built_lab=bool(item['built']),
                                current_census_pi=bool(item['census']), in_inventory=bool(item['inventory']),
                                inventory_status=(item['inventory'] or {}).get('inventory_status'),
                                home_department=normalize((r or {}).get('home_department'), cfg, rules.get('aliases')) or None,
                                home_department_as_recorded=(r or {}).get('home_department'),
                                home_status=(r or {}).get('status', 'missing'), home_basis=(r or {}).get('home_basis'),
                                primary_resolved=HOME.review(r)['primary_resolved'] and not issues,
                                also=(r or {}).get('also') or [], primary_unresolved=(r or {}).get('primary_unresolved') or [],
                                issues=issues, local_home=(lm.get(name) or {}).get('home_department'),
                                shared_home=(sm.get(name) or {}).get('home_department'),
                                shared_register_missing=name not in sm, evidence_url=evidence.get('url'),
                                evidence_sha256=evidence.get('sha256'), evidence_quote=evidence.get('quote'),
                                proposal=proposal, lab_name=(pi.get('lab') or {}).get('name'),
                                next_action=('Review captured listing proposal' if proposal else
                                             'Resolve appointment or source conflict using official faculty evidence' if issues else
                                             'Recorded assignment available; original capture has not been re-reviewed in this audit')))

    def csv_write(filename, rows):
        with (out / filename).open('w', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=list(results[0]))
            w.writeheader()
            for r in rows:
                w.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in r.items()})

    out.mkdir(parents=True, exist_ok=True)
    csv_write('all-labs-home-departments.csv', results)
    csv_write('home-department-followups.csv', [r for r in results if r['issues']])
    csv_write('uchicago-home-departments.csv', [r for r in results if r['school'] == 'uchicago'])
    counts = lambda rows: dict(records=len(rows), built_labs=sum(r['live_built_lab'] for r in rows),
                              recorded_accepted=sum(r['home_status'] == 'accepted' and bool(r['home_department']) for r in rows),
                              clear_recorded_home=sum(r['primary_resolved'] for r in rows),
                              needs_review=sum(bool(r['issues']) for r in rows),
                              issues=dict(collections.Counter(i for r in rows for i in r['issues'])))
    summary = dict(generated_at=dt.datetime.now(dt.timezone.utc).isoformat(), inventory=str(inventory),
                   definition='Recorded evidence and register consistency audit; not a fresh verification of every original source.',
                   totals=counts(results), live_built=counts([r for r in results if r['live_built_lab']]),
                   schools={s: counts([r for r in results if r['school'] == s]) for s in schools})
    (out / 'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n')
    (out / 'input-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, default=P.SCRATCH / 'pi-inventory-review-1117/all-pis-labs.csv')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    audit(args.inventory, args.out)


if __name__ == '__main__':
    main()
