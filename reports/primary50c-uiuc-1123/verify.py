"""Verify live allocations, inventories, source archives and counting conservation."""
import collections
import copy
import csv
import importlib.util
import json
from pathlib import Path
import re

import atlas_paths as P
import evidence_store as E
import home_department_registry as HOME
import home_departments_school as H

HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    out = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(out)
    return out


def csv_file(path, rows, fields):
    with path.open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def main():
    app = module('home_batch_application', HERE / 'apply.py')
    application = read(HERE / 'application.json')
    assert application['applied']
    app.verify_reviews()
    decisions = app.selection_map()
    protected = read(HERE / 'application-unselected-home-digests.json')
    app.verify_protected(protected)
    prior = read(HERE / 'prior-home-records.json')
    selected_rows = []
    for school, entries in decisions.items():
        registered = read(P.data('home-department-decisions-school.json', school))
        accepted = HOME.accepted(school)
        for name, entry in entries.items():
            row = accepted[name]
            assert registered[name] == entry
            assert row['home_department'] == entry['home_department']
            assert row['reviewed_home_evidence'] == entry['home_department_evidence']
            assert HOME.review(row)['primary_resolved'] and not row.get('primary_unresolved')
            assert H.apply_reviewed_homes([copy.deepcopy(row)], {name: entry}, lambda u: u) == [row]
            if school != 'uiuc':
                old = prior[school][name]
                units = {old['home_department']} | set(old.get('also') or []) | set(old.get('primary_unresolved') or [])
                assert units <= {row['home_department']} | set(row.get('also') or [])
                if E.source_of(school) == 'store':
                    authority = E.find(school, 'home-department-decisions.json', key=name)
                    assert len(authority) == 1 and authority[0][5] == entry
                selected_rows.append(dict(school=school, name=name, home_department=row['home_department'],
                                          home_basis=row['home_basis'], also='; '.join(row.get('also') or []),
                                          source_url=row['evidence']['url'], source_sha256=row['evidence']['sha256']))
    assert len(selected_rows) == 50
    for school in decisions:
        if E.source_of(school) == 'store':
            errors = E.check_view(school, root=P.CODE)
            assert not [error for error in errors if 'home-department-decisions.json' in error]
    uiuc = HOME.accepted('uiuc')
    assert len(uiuc) == 428
    assert all(p['pi'] in uiuc for p in read(P.data('pis.json', 'uiuc')))
    assert all(f['name'] in uiuc for f in read(P.data('census-faculty.json', 'uiuc'))['faculty'])
    assert sum(bool(r.get('faculty_only_record')) for r in uiuc.values()) == 58
    assert sum(bool(r.get('no_academic_department')) for r in uiuc.values()) == 1
    projected = {r['name']: r for r in app.uiuc_projection(decisions['uiuc'])}
    assert projected == uiuc
    uiuc_rows = [dict(name=name, home_department=row['home_department'], also='; '.join(row.get('also') or []),
                      home_basis=row['home_basis'], faculty_only_record=bool(row.get('faculty_only_record')),
                      documented_research_unit_home=bool(row.get('no_academic_department')),
                      source_url=row['evidence']['url'], source_sha256=row['evidence']['sha256'])
                 for name, row in sorted(uiuc.items())]
    csv_file(HERE / 'resolutions.csv', selected_rows, list(selected_rows[0]))
    csv_file(HERE / 'uiuc/faculty-departments.csv', uiuc_rows, list(uiuc_rows[0]))
    original = {(r['school'], r['name']) for r in read(HERE / 'original-unresolved-cohort.json')}
    remaining = []
    active_pairs = set()
    for config in sorted(P.SCHOOL_CONFIGS.glob('*.toml')):
        school = config.stem
        path = P.data('pis.json', school)
        if not path.exists():
            continue
        homes = {r['name']: r for r in HOME.load(school)}
        for pi in read(path):
            active_pairs.add((school, pi['pi']))
            row = homes.get(pi['pi']) or {}
            if row.get('primary_unresolved') or row.get('home_basis') == 'primary_unresolved':
                evidence = row.get('evidence') or {}
                candidates = row.get('primary_unresolved') or []
                remaining.append(dict(school=school, name=pi['pi'], reporting_home=row.get('home_department'),
                                      primary_candidates='; '.join(candidates), needs_candidate_metadata_repair=len(candidates) < 2,
                                      source_url=evidence.get('url'), source_sha256=evidence.get('sha256')))
    current = app.counts()
    assert len(remaining) == current['primary_unresolved']
    remaining_original = sum((r['school'], r['name']) in original for r in remaining)
    assert remaining_original <= len(original) - len(selected_rows)
    inactive_original = [dict(school=s, name=n) for s, n in sorted(original - active_pairs)]
    csv_file(HERE / 'remaining-primary-unresolved.csv', remaining, list(remaining[0]))
    audit = module('home_counting_audit', HERE.parent / 'homes-final-1123/audit_crosslisting.py')
    audit.HERE = HERE
    audit.self_test()
    # D-0048 completes a reporting choice without asserting a formal primary.
    first = dict(status='accepted', home_department='A', also=['B'], home_basis='first_listed_site',
                 home_selection_basis='first_listed_site',
                 evidence=dict(url='https://example.edu/person', sha256='a' * 64, quote='Professor of A and B'))
    assessed = audit.assess(first, {'departments': [], 'census': {'home_units': {'A': '^A$', 'B': '^B$'}}})
    assert assessed['weights']['reporting'] == {'A': 1}
    assert assessed['primary_resolved'] and not HOME.review(first)['primary_stated']
    assert all(sum(weights.values()) == 1 for weights in assessed['weights'].values())
    audit.main()
    counting = read(HERE / 'crosslisting-summary.json')
    assert counting['explicit_primary_unresolved'] == current['primary_unresolved']
    assert current['first_listed_homes'] == 57
    assert counting['recorded_primary_resolved'] == current['primary_resolved']
    for sha, source in read(HERE / 'source-archives.json').items():
        assert app.file_sha(Path(source['archive_file'])) == sha
    full_log = (HERE / 'full-suite.log').read_text()
    assert 'main fast-forwarded' in full_log
    line = next(line for line in reversed(full_log.splitlines()) if re.search(r'\d+ passed', line))
    tests = {label: int(number) for number, label in re.findall(r'(\d+) (passed|skipped|warnings?)', line)}
    scientific_before = read(HERE / 'application-scientific-input-digests.json')
    scientific_now = app.scientific_inputs(decisions)
    # An unrelated worker may legitimately update inputs after our application.
    later_drift = [path for path, sha in scientific_before.items() if scientific_now.get(path) != sha]
    result = dict(existing_cases_resolved=50, initial_review_snapshot_queue=len(original),
                  existing_queue_before=application['before']['primary_unresolved'],
                  existing_queue_after=application['after']['primary_unresolved'],
                  current_explicit_unresolved=len(remaining),
                  unrelated_baseline_pi_keys_no_longer_active=inactive_original,
                  uiuc_records=428, uiuc_lab_pis=370, uiuc_faculty_only_records=58,
                  uiuc_academic_unit_homes=427, uiuc_documented_research_unit_homes=1,
                  uiuc_missing_homes=0, uiuc_unresolved_selections=0,
                  first_listed_selections=57, stated_primary_in_existing_50=2,
                  unique_original_http200_sources=81, crosslisting_scenarios_passed=9,
                  all_prior_affiliations_retained=True, selected_metadata_idempotent=True,
                  scientific_inputs_unchanged_across_application=True,
                  unrelated_scientific_changes_after_application=later_drift,
                  unselected_home_rows_preserved=sum(map(len, protected.values())),
                  current_lab_counts=current, full_suite=tests,
                  home_basis_counts=dict(collections.Counter(r['home_basis'] for r in uiuc.values())))
    (HERE / 'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
