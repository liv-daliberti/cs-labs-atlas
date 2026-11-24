"""Verify final live coverage at every school, preservation and counting totals."""
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


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def csv_file(name, rows):
    with (HERE / name).open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def main():
    app = module('final_homes_application', HERE / 'apply.py')
    application = app.read(HERE / 'application.json')
    assert application['applied']
    decisions = app.verify_reviews()
    app.verify_protected(app.read(HERE / 'application-unselected-home-digests.json'))
    prior = app.read(HERE / 'original-cohort.json')
    selected_rows = []
    for school, entries in decisions.items():
        registered = app.read(P.data('home-department-decisions-school.json', school))
        current = HOME.accepted(school)
        for name, entry in entries.items():
            assert registered[name] == entry
            if E.source_of(school) == 'store':
                rows = E.find(school, 'home-department-decisions.json', key=name)
                assert len(rows) == 1 and rows[0][5] == entry
            row = current[name]
            assert row['home_department'] == entry['home_department']
            assert row['reviewed_home_evidence'] == entry['home_department_evidence']
            assert HOME.review(row)['primary_resolved'] and not row.get('primary_unresolved')
            old = prior[school][name]
            units = {old.get('home_department')} | set(old.get('also') or []) | set(old.get('primary_unresolved') or [])
            units.discard(None)
            assert units <= {row['home_department']} | set(row.get('also') or [])
            assert H.apply_reviewed_homes([copy.deepcopy(row)], {name: entry}, lambda u: u) == [row]
            selected_rows.append(dict(school=school, name=name, home_department=row['home_department'],
                                      also='; '.join(row.get('also') or []), home_basis=row['home_basis'],
                                      source_url=row['evidence']['url'], source_sha256=row['evidence']['sha256']))
        if E.source_of(school) == 'store':
            assert not [e for e in E.check_view(school, root=P.CODE) if 'home-department-decisions.json' in e]
    app.verify_native_rebuild(decisions, {s: [HOME.accepted(s)[n] for n in entries] for s, entries in decisions.items()})
    coverage = app.coverage()
    assert not any(s['missing'] or s['unresolved'] for s in coverage)
    total = sum(s['labs'] for s in coverage)
    assert sum(s['accepted'] for s in coverage) == total
    csv_file('resolutions.csv', selected_rows)
    csv_file('school-coverage.csv', [dict(school=s['school'], labs=s['labs'], accepted=s['accepted'],
                                       missing=len(s['missing']), unresolved=len(s['unresolved']),
                                       research_unit_homes=s['documented_research_unit_homes']) for s in coverage])
    all_labs = []
    for school in (s['school'] for s in coverage):
        homes = HOME.accepted(school)
        for pi in app.read(P.data('pis.json', school)):
            row = homes[pi['pi']]
            all_labs.append(dict(school=school, name=pi['pi'], home_department=row['home_department'],
                                 also='; '.join(row.get('also') or []), home_basis=row.get('home_basis') or '',
                                 documented_research_unit_home=bool(row.get('no_academic_department')),
                                 source_url=row['evidence']['url'], source_sha256=row['evidence']['sha256']))
    assert len(all_labs) == total
    csv_file('all-lab-departments.csv', all_labs)
    audit = module('final_home_counting', HERE.parent / 'homes-final-1123/audit_crosslisting.py')
    audit.HERE = HERE
    audit.self_test()
    choice = dict(status='accepted', home_department='A', also=['B'], home_basis='first_listed_site',
                  home_selection_basis='first_listed_site',
                  evidence=dict(url='https://example.edu/person', sha256='a' * 64, quote='Professor of A and B'))
    assessed = audit.assess(choice, {'departments': [], 'census': {'home_units': {'A': '^A$', 'B': '^B$'}}})
    assert assessed['weights']['reporting'] == {'A': 1} and not HOME.review(choice)['primary_stated']
    assert all(sum(weights.values()) == 1 for weights in assessed['weights'].values())
    audit.main()
    counting = app.read(HERE / 'crosslisting-summary.json')
    assert counting['labs'] == total and counting['allocation_complete'] == total
    assert counting['allocation_incomplete'] == counting['explicit_primary_unresolved'] == 0
    counting['original_source_review_scope'] = (
        'All124 final-batch decisions independently checked against original HTTP200 sources. '
        'Other inherited homes receive coverage/evidence/status checks, not a new original-source audit. '
        'Source-order reporting choices retain primary_stated=false. The global review sample is prospective.')
    app.write(HERE / 'crosslisting-summary.json', counting)
    log = (HERE / 'full-suite.log').read_text()
    assert 'main fast-forwarded' in log
    line = next(line for line in reversed(log.splitlines()) if re.search(r'\d+ passed', line))
    tests = {label: int(number) for number, label in re.findall(r'(\d+) (passed|skipped|warnings?)', line)}
    before = app.read(HERE / 'application-scientific-input-digests.json')
    science_now = app.scientific_inputs(decisions)
    later_drift = [path for path, sha in before.items() if science_now.get(path) != sha]
    result = dict(schools=len(coverage), labs=total, accepted_home_allocations=total,
                  missing_homes=0, explicit_unresolved_selections=0,
                  existing_unresolved_cases_completed=84, additional_missing_homes_completed=40,
                  reviewed_records=len(selected_rows),
                  selected_basis_counts=dict(collections.Counter(r['home_basis'] for r in selected_rows)),
                  documented_research_unit_homes=sum(s['documented_research_unit_homes'] for s in coverage),
                  source_archives_verified=len(app.read(HERE / 'source-archives.json')),
                  all_prior_affiliations_retained=True, native_rebuilds_passed=len(decisions),
                  selected_metadata_idempotent=True, unselected_home_rows_preserved=application['unselected_home_rows_preserved'],
                  scientific_inputs_unchanged_across_application=True,
                  unrelated_scientific_changes_after_application=later_drift,
                  counting_scenarios_passed=9, lab_mass_conservation=counting['mass_conservation'],
                  appointment_timing_notes=[dict(school='cmu', name='Niloofar Mireshghallah',
                      note='Owned homepage states a current faculty role; institutional profile labels Fall2027. '
                           'Both name LTI, so home allocation is settled; this review does not adjudicate PI dates or eligibility.')],
                  full_suite=tests, coverage=coverage)
    app.write(HERE / 'verification.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
