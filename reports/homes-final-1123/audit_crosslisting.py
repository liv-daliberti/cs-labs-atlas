"""Audit current lab home records without changing assignments or counting policy.

Run after applying the source-reviewed allocations:
  PYTHONPATH=tools python reports/homes-final-1123/audit_crosslisting.py
The 50-row seeded review sample is bound to the exact inventory and home-record hashes.
"""
import argparse
import collections
import csv
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import random
import re

import atlas_paths as P
import home_department_registry as HOME
import school_config as S

HERE = Path(__file__).resolve().parent
JOINT_WORDS = re.compile(r'\b(?:joint (?:faculty )?appointments?|dual appointment)\b|professor of [^;.]{1,120} and (?:professor )?of ', re.I)
NON_PRIMARY_ROLE = re.compile(r'\b(?:courtesy|affiliat(?:ed|e)|adjunct|visiting|external|former|historical|secondary appointment|internal supervisor)\b', re.I)
ORDER_BASES = {'first_listed_official_profile_position', 'reviewed_first_official_profile_position'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def norm(unit, cfg):
    canonical = S.field(cfg, 'census.home_units') or {}
    if unit in canonical:
        return unit
    codes = {r['code']: r['name'] for r in S.listing_units(cfg)}
    unit = codes.get(unit, unit) or ''
    unit = re.sub(r'^Department of\s+', '', unit).strip()
    return next((name for name, rx in (S.field(cfg, 'census.home_units') or {}).items()
                 if re.search(rx, unit, re.I)), unit)


def assess(row, cfg):
    home = norm(row.get('home_department'), cfg)
    raw_candidates = row.get('primary_unresolved') or []
    candidates = list(dict.fromkeys(norm(u, cfg) for u in raw_candidates if u))
    also = row.get('also') or []
    flags = []
    explicit_joint = bool(raw_candidates or row.get('home_basis') == 'primary_unresolved')
    if explicit_joint:
        flags.append('explicit_primary_unresolved')
        if len(raw_candidates) < 2 or home not in candidates:
            flags.append('malformed_primary_candidates')
        if len(candidates) < len(set(raw_candidates)):
            flags.append('candidate_aliases_collapse')
    candidate_role_conflict = any(NON_PRIMARY_ROLE.search(u) for u in raw_candidates)
    if candidate_role_conflict:
        flags.append('non_primary_role_in_candidates')
    if also:
        flags.append('other_affiliations_recorded')
    if row.get('home_basis') in ORDER_BASES:
        flags.append('primary_chosen_by_position_needs_review')
    if not row.get('home_basis'):
        flags.append('legacy_primary_basis_unrecorded')
    es = row.get('reviewed_home_evidence') or []
    if isinstance(row.get('evidence'), dict):
        es = es + [row['evidence']]
    if JOINT_WORDS.search(' '.join(e.get('quote', '') for e in es)) and not explicit_joint:
        flags.append('joint_wording_needs_role_review')
    valid = row.get('status') == 'accepted' and bool(home) and HOME.valid_evidence(row)
    if not valid:
        flags.append('allocation_incomplete')
    primary = HOME.review(row)['primary_resolved']
    reporting = {home if valid else '[allocation incomplete]': Fraction(1)}
    documented = {home if primary else '[primary not recorded as resolved]': Fraction(1)}
    if not valid:
        fractional = reporting.copy()
    elif explicit_joint and len(candidates) >= 2 and home in candidates and not candidate_role_conflict:
        fractional = {u: Fraction(1, len(candidates)) for u in candidates}
    elif explicit_joint:
        fractional = {'[joint candidates need repair]': Fraction(1)}
    else:
        # A comparison scenario holding legacy reporting units fixed. This does
        # not assert that an unreviewed legacy reporting unit is a proven primary.
        fractional = reporting.copy()
    for weights in (reporting, documented, fractional):
        assert sum(weights.values()) == 1
    return dict(home=home, candidates=candidates, also=also, flags=flags,
                primary_resolved=primary, allocation_complete=valid,
                no_academic_department=bool(row.get('no_academic_department')),
                weights=dict(reporting=reporting, recorded_primary=documented,
                             reporting_with_fractional_joints=fractional))


def self_test():
    cfg = {'departments': [], 'census': {'home_units': {'A': '^A$', 'B': '^B$'}}}
    ev = dict(url='https://example.edu/faculty', sha256='a' * 64, quote='Professor of A')
    base = dict(status='accepted', home_department='A', home_basis='listed_title', evidence=ev)
    single = assess(base, cfg)
    assert single['weights']['reporting_with_fractional_joints'] == {'A': 1}
    secondary = assess({**base, 'also': ['B', 'Research Lab (member)', 'External University']}, cfg)
    assert secondary['weights']['reporting_with_fractional_joints'] == {'A': 1}
    joint = assess({**base, 'home_basis': 'primary_unresolved', 'primary_unresolved': ['A', 'B']}, cfg)
    assert not joint['primary_resolved']
    assert joint['weights']['reporting_with_fractional_joints'] == {'A': Fraction(1, 2), 'B': Fraction(1, 2)}
    bad = assess({**base, 'home_basis': 'primary_unresolved', 'primary_unresolved': []}, cfg)
    assert 'malformed_primary_candidates' in bad['flags']
    assert bad['weights']['reporting_with_fractional_joints'] == {'[joint candidates need repair]': 1}
    legacy = assess({**base, 'home_basis': None}, cfg)
    assert legacy['weights']['recorded_primary'] == {'[primary not recorded as resolved]': 1}
    missing = assess({}, cfg)
    assert not missing['allocation_complete']
    mislabeled_affiliate = assess({**base, 'home_basis': 'primary_unresolved', 'primary_unresolved': ['A', 'B (affiliated)']}, cfg)
    assert 'non_primary_role_in_candidates' in mislabeled_affiliate['flags']
    assert mislabeled_affiliate['weights']['reporting_with_fractional_joints'] == {'[joint candidates need repair]': 1}
    incomplete_joint = assess({**base, 'status': 'hold', 'home_basis': 'primary_unresolved', 'primary_unresolved': ['A', 'B']}, cfg)
    assert incomplete_joint['weights']['reporting_with_fractional_joints'] == {'[allocation incomplete]': 1}
    samples = [single, secondary, joint, bad, legacy, missing, mislabeled_affiliate, incomplete_joint]
    for policy in single['weights']:
        assert sum(sum(r['weights'][policy].values()) for r in samples) == len(samples)
    print('8 scenario checks passed; one lab per policy, affiliates never split, joint weights conserved')


def write_csv(path, rows, fields):
    with path.open('w') as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def main(overlay=None):
    overrides = json.loads(overlay.read_text()) if overlay else {}
    def output(name):
        return HERE / (('preview-' if overlay else '') + name)
    inventory = []
    rows = []
    sources = {}
    tallies = {k: collections.defaultdict(Fraction) for k in
               ['reporting', 'recorded_primary', 'reporting_with_fractional_joints']}
    school_totals = collections.Counter()
    for path in sorted(P.SCHOOL_CONFIGS.glob('*.toml')):
        school = path.stem
        pi_path = P.data('pis.json', school)
        if not pi_path.exists():
            continue
        pis = json.loads(pi_path.read_text())
        assert len({p['pi'] for p in pis}) == len(pis), f'{school}: duplicate inventory PI'
        sources[str(pi_path)] = hashlib.sha256(pi_path.read_bytes()).hexdigest()
        homes = {r['name']: r for r in HOME.load(school)}
        homes.update(overrides.get(school, {}))
        cfg = S.get(school)
        for pi in pis:
            name = pi['pi']
            inventory.append([school, name])
            row = homes.get(name) or {}
            a = assess(row, cfg)
            school_totals[school] += 1
            for policy, weights in a.pop('weights').items():
                for unit, weight in weights.items():
                    tallies[policy][school, unit] += weight
            rows.append(dict(school=school, name=name, **a, record_sha256=digest(row),
                             home_basis=row.get('home_basis'),
                             evidence=row.get('reviewed_home_evidence') or [row.get('evidence') or {}]))
    assert len({(r['school'], r['name']) for r in rows}) == len(rows)
    for policy, units in tallies.items():
        assert sum(units.values()) == len(rows), policy
        for school, count in school_totals.items():
            assert sum(w for (s, _), w in units.items() if s == school) == count
    sealed = dict(inventory_sha256=digest(inventory),
                  allocations_sha256=digest([[r['school'], r['name'], r['record_sha256']] for r in rows]))
    flags = collections.Counter(flag for r in rows for flag in r['flags'])
    # The sample is for human role/primary verification, not an automatic finding
    # that every 'also' item is another academic department.
    strata = collections.defaultdict(list)
    for r in rows:
        f = r['flags']
        stratum = ('explicit_joint' if 'explicit_primary_unresolved' in f else
                   'joint_or_order_signal' if any(k in f for k in ['joint_wording_needs_role_review', 'primary_chosen_by_position_needs_review']) else
                   'other_affiliations' if r['also'] else 'no_other_affiliation_recorded')
        strata[stratum].append(r)
    rng = random.Random('home-crosslisting-2026-11-23-v1')
    selected = []
    for key, target in [('explicit_joint', 15), ('joint_or_order_signal', 10),
                        ('other_affiliations', 15), ('no_other_affiliation_recorded', 10)]:
        pool = sorted(strata[key], key=lambda r: (r['school'], r['name']))
        rng.shuffle(pool)
        selected.extend((key, r) for r in pool[:target])
    used = {(r['school'], r['name']) for _, r in selected}
    if len(selected) < 50:
        pool = [r for r in rows if (r['school'], r['name']) not in used]
        rng.shuffle(pool)
        selected.extend(('fill', r) for r in pool[:50 - len(selected)])
    sample = dict(**sealed, seed='home-crosslisting-2026-11-23-v1', selected_count=len(selected),
                  instructions='Read each cited original source. Classify each unit as academic primary, joint academic, courtesy/affiliate, research/lab, administrative, nested parent, external, or historical. State primary only if source says so or distinguishes tenure. A second faculty listing alone is a candidate, not proof of a joint tenure line. Record exact source/date/quote and pass, correct, or unresolved. Keep this sealed sample historical; redraw after any changed input hash.',
                  rows=[dict(stratum=k, **r, verdict=None, source_role_verdicts=[], reviewer=None) for k, r in selected])
    output('crosslisting-review-sample.json').write_text(json.dumps(sample, ensure_ascii=False, indent=1) + '\n')
    csv_rows = [dict(school=r['school'], name=r['name'], reporting_home=r['home'],
                     primary_resolved=r['primary_resolved'], home_basis=r['home_basis'],
                     no_academic_department=r['no_academic_department'],
                     primary_candidates='; '.join(r['candidates']), other_affiliations='; '.join(map(str, r['also'])),
                     flags='; '.join(r['flags']), record_sha256=r['record_sha256']) for r in rows]
    write_csv(output('crosslisting-inventory.csv'), csv_rows, list(csv_rows[0]))
    queue = [r for r in csv_rows if r['flags']]
    write_csv(output('crosslisting-review-queue.csv'), queue, list(csv_rows[0]))
    units = sorted(set().union(*(set(t) for t in tallies.values())))
    sensitivity = []
    for school, unit in units:
        r = dict(school=school, unit=unit)
        for policy in tallies:
            value = tallies[policy][school, unit]
            r[policy] = str(value)
        r['fractional_joint_delta'] = str(tallies['reporting_with_fractional_joints'][school, unit] - tallies['reporting'][school, unit])
        sensitivity.append(r)
    write_csv(output('crosslisting-sensitivity.csv'), sensitivity, list(sensitivity[0]))
    summary = dict(**sealed, mode='projection_preview' if overlay else 'live', labs=len(rows), allocation_complete=sum(r['allocation_complete'] for r in rows),
                   allocation_incomplete=sum(not r['allocation_complete'] for r in rows),
                   research_unit_homes_no_academic_department=sum(r['no_academic_department'] for r in rows),
                   recorded_primary_resolved=sum(r['primary_resolved'] for r in rows),
                   explicit_primary_unresolved=flags['explicit_primary_unresolved'],
                   other_affiliations_recorded=sum(bool(r['also']) for r in rows), flags=dict(flags),
                   sample_size=len(selected), source_inventory_hashes=sources,
                   original_source_review_scope='The 62 final-batch records were independently checked against original HTTP200 captures; inherited records receive structural/status checks in this run, not fresh original-source certification.',
                   policy='Reporting counts exactly one school-lab once. Recorded-primary view keeps every primary not recorded as resolved in a visible bucket. Fractional scenario splits only structurally valid recorded primary-candidate sets; legacy reporting assignments are held fixed. Untyped also entries are never counted as extra departments. These are comparison outputs, not a change to production scientific estimates.',
                   mass_conservation={k: str(sum(t.values())) for k, t in tallies.items()})
    output('crosslisting-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k != 'source_inventory_hashes'}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--overlay', type=Path, help='Read-only preview of reviewed row overrides; never writes shared data')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    self_test() if args.self_test else main(args.overlay)
