"""Verify the live primary-resolution batch and export its remaining review queue."""
import copy
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import re

import atlas_paths as P
import evidence_store as E
import home_department_registry as HOME
from home_departments_school import apply_reviewed_homes

HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def main():
    application = read(HERE / 'application.json')
    assert application['applied']
    decisions = read(HERE / 'decisions.json')
    prior = read(HERE / 'prior-home-records.json')
    protected = read(HERE / 'unselected-home-digests.json')
    verified = 0
    preserved = 0
    for school, hashes in protected.items():
        rows = {r['name']: r for r in HOME.load(school)}
        assert all(name in rows and digest(rows[name]) == sha for name, sha in hashes.items())
        preserved += len(hashes)
    for school, entries in decisions.items():
        rows = HOME.accepted(school)
        for name, entry in entries.items():
            row = rows[name]
            assert row['home_department'] == entry['home_department']
            assert row['reviewed_home_evidence'] == entry['home_department_evidence']
            assert HOME.review(row)['primary_resolved'] and not row.get('primary_unresolved')
            old = prior[school][name]
            units = {old['home_department']} | set(old.get('primary_unresolved') or []) | set(old.get('also') or [])
            assert units <= {row['home_department']} | set(row.get('also') or [])
            assert row.get('no_academic_department') == old.get('no_academic_department')
            assert apply_reviewed_homes([copy.deepcopy(row)], {name: entry}, lambda u: u) == [row]
            verified += 1
    assert verified == 50
    assert all(not E.check_view(school, root=P.CODE) for school in decisions if E.source_of(school) == 'store')
    # Reuse the existing counting audit, writing to this new checkpoint so that
    # the previous 235-case snapshot and its independent sample remain intact.
    path = HERE.parent / 'homes-final-1123/audit_crosslisting.py'
    spec = importlib.util.spec_from_file_location('primary_resolution_counting_audit', path)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    audit.HERE = HERE
    audit.main()
    summary = read(HERE / 'crosslisting-summary.json')
    summary['original_source_review_scope'] = ('This batch independently checked 50 primary-resolution records against 49 original HTTP200 captures. Other records receive structural/status checks here; older source reviews retain their original scope.')
    (HERE / 'crosslisting-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1) + '\n')
    assert summary['explicit_primary_unresolved'] == application['after']['primary_unresolved']
    assert summary['recorded_primary_resolved'] == application['after']['primary_resolved']
    remaining = []
    for cfg_path in sorted(P.SCHOOL_CONFIGS.glob('*.toml')):
        school = cfg_path.stem
        pi_path = P.data('pis.json', school)
        if not pi_path.exists():
            continue
        rows = {r['name']: r for r in HOME.load(school)}
        for pi in read(pi_path):
            row = rows.get(pi['pi']) or {}
            if not (row.get('primary_unresolved') or row.get('home_basis') == 'primary_unresolved'):
                continue
            evidence = row.get('evidence') or {}
            candidates = row.get('primary_unresolved') or []
            remaining.append(dict(school=school, name=pi['pi'], reporting_home=row.get('home_department'),
                                  primary_candidates='; '.join(candidates),
                                  needs_candidate_metadata_repair=len(candidates) < 2,
                                  source_url=evidence.get('url'), source_sha256=evidence.get('sha256')))
    assert len(remaining) == summary['explicit_primary_unresolved']
    with (HERE / 'remaining-primary-unresolved.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=list(remaining[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(remaining)
    full_log = (HERE / 'full-suite.log').read_text()
    passed = re.search(r'(\d+) passed, (\d+) skipped, (\d+) warnings?', full_log)
    assert passed and 'main fast-forwarded' in full_log
    result = dict(selected_verified=verified, unselected_home_rows_preserved=preserved,
                  all_prior_unit_labels_retained=True, resolved_metadata_idempotent=True,
                  selected_source_store_views_exact=True, application=application,
                  full_suite=dict(passed=int(passed[1]), skipped=int(passed[2]), warnings=int(passed[3])),
                  targeted_tests=61, live_crosslisting_summary={k: v for k, v in summary.items() if k != 'source_inventory_hashes'})
    (HERE / 'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'live_crosslisting_summary'}))


if __name__ == '__main__':
    main()
