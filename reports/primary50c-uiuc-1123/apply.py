"""Validate and materialize the reviewed 50 selections and complete UIUC homes.

Run from the landed code root with PYTHONPATH=tools. Without --apply, writes only
this batch's scratch projections. Reviewed inputs must be landed before --apply.
"""
import argparse
import collections
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path

import atlas_paths as P
import census_overrides as CO
import home_department_registry as HOME
import home_departments_school as H
import schema_check

HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
SCRATCH = P.SCRATCH / 'primary50c-uiuc-1123'


def read(path):
    return json.loads(path.read_text())


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def counts():
    result = collections.Counter()
    for config in sorted(P.SCHOOL_CONFIGS.glob('*.toml')):
        school = config.stem
        path = P.data('pis.json', school)
        if not path.exists():
            continue
        homes = {row['name']: row for row in HOME.load(school)}
        for pi in read(path):
            row = homes.get(pi['pi']) or {}
            result['labs'] += 1
            result['accepted'] += int(row.get('status') == 'accepted' and bool(row.get('home_department')) and HOME.valid_evidence(row))
            result['primary_unresolved'] += int(bool(row.get('primary_unresolved') or row.get('home_basis') == 'primary_unresolved'))
            result['primary_resolved'] += int(HOME.review(row)['primary_resolved'])
            result['research_unit_homes'] += int(bool(row.get('no_academic_department')))
            result['first_listed_homes'] += int(row.get('home_basis') in ('first_listed_site', 'first_listed_publication'))
    return dict(result)


def selection_map():
    decisions = read(HERE / 'decisions.json')
    assert sum(map(len, decisions.values())) == 50
    decisions['uiuc'] = read(HERE / 'uiuc/final-decisions.json')
    assert len(decisions['uiuc']) == 428
    return decisions


def protected_snapshot(decisions):
    return {config.stem: {r['name']: digest(r) for r in HOME.load(config.stem)
                          if r['name'] not in decisions.get(config.stem, {})}
            for config in sorted(P.SCHOOL_CONFIGS.glob('*.toml'))}


def verify_protected(protected):
    for school, values in protected.items():
        actual = {r['name']: digest(r) for r in HOME.load(school)}
        assert all(actual.get(name) == sha for name, sha in values.items()), f'{school}: unselected home changed'


def scientific_inputs(schools):
    # The application changes home registers only. Hash the actual current inputs
    # across this application, allowing unrelated earlier work by other workers.
    files = ('pis.json', 'census-faculty.json', 'census-additions.json', 'faculty-periods.json',
             'students.json', 'lab_papers.jsonl.gz', 'student_papers.jsonl.gz')
    return {str(path): file_sha(path) for school in schools for name in files
            if (path := P.data(name, school)).exists()}


def verify_reviews():
    primary = read(HERE / 'independent-review.json')
    bound = primary.get('decisions_sha256') or primary.get('concrete_decisions_sha256')
    assert bound == file_sha(HERE / 'decisions.json')
    assert primary.get('result', primary.get('status')) == 'pass'
    verdicts = primary['verdicts']
    assert len(verdicts) == 50
    assert {(r['school'], r['name']) for r in verdicts} == {
        (school, name) for school, entries in read(HERE / 'decisions.json').items() for name in entries}
    assert all(r.get('verdict') == 'pass' for r in verdicts)
    base = read(HERE / 'uiuc/independent-review.json')
    assert base['result'] == 'pass' and base['sampled_pass'] == 50 and base['sampled_fail'] == 0
    assert base['decisions_sha256'] == file_sha(HERE / 'uiuc/decisions.json')
    joint = read(HERE / 'uiuc/first-listed-independent-review.json')
    assert joint['result'] == 'pass' and joint['passed'] == 10 and joint['failed'] == 0
    binding = read(HERE / 'uiuc/first-listed-binding.json')
    assert binding['base_decisions_sha256'] == file_sha(HERE / 'uiuc/decisions.json')
    assert binding['addendum_sha256'] == file_sha(HERE / 'uiuc/first-listed-addendum.json')
    assert binding['final_decisions_sha256'] == file_sha(HERE / 'uiuc/final-decisions.json')
    assert joint['binding'] == binding
    aliases = read(HERE / 'uiuc/unit-alias-independent-review.json')
    assert aliases['result'] == 'pass' and aliases['binding'] == binding
    assert aliases['all_428_semantic_affiliation_sets_preserved']
    # The composite review covers the unchanged base and every changed row.
    assert read(HERE / 'uiuc/final-decisions.json') == {
        **read(HERE / 'uiuc/decisions.json'), **read(HERE / 'uiuc/first-listed-addendum.json')}
    assert len(joint['verdicts']) == 10 and all(r['verdict'] == 'pass' for r in joint['verdicts'])


def uiuc_projection(decisions):
    output = SCRATCH / 'uiuc-projected-home-departments.json'
    section, writer = CO.section, P.data_w
    current = section('uiuc')

    def data_writer(name, key=None):
        assert (name, key) == ('home-departments-school.json', 'uiuc')
        return output

    try:
        CO.section = lambda key: current | decisions if key == 'uiuc' else section(key)
        P.data_w = data_writer
        with contextlib.redirect_stdout(io.StringIO()):
            H.main('uiuc')
    finally:
        CO.section, P.data_w = section, writer
    rows = read(output)
    aliases = read(HERE / 'uiuc/unit-alias-independent-review.json')
    assert file_sha(output) == aliases['final_projection_sha256']
    assert len(rows) == len({r['name'] for r in rows}) == 428
    assert {r['name'] for r in rows} == set(decisions)
    assert sum(bool(r.get('faculty_only_record')) for r in rows) == 58
    assert all(r['status'] == 'accepted' and HOME.valid_evidence(r) for r in rows)
    assert all(HOME.review(r)['primary_resolved'] for r in rows)
    assert all(not any('candidate discovery' in u.lower() for u in r.get('also', [])) for r in rows)
    assert H.apply_reviewed_homes(copy.deepcopy(rows), decisions, lambda u: u) == rows
    return rows


def main(apply=False):
    verify_reviews()
    decisions = selection_map()
    schema = read(CODE / 'schemas/home-department-decisions.schema.json')
    assert all(not schema_check.validate(entries, schema) for entries in decisions.values())
    archives = read(HERE / 'source-archives.json')
    for sha, source in archives.items():
        assert source['http_status'] == 200 and file_sha(Path(source['archive_file'])) == sha
    for file in ('source-receipts.json', 'uiuc/source-receipts.json', 'uiuc/first-listed-source-receipts.json'):
        for sha, source in read(HERE / file).items():
            assert source['http_status'] == 200 and file_sha(Path(archives[sha]['archive_file'])) == sha
    prior = read(HERE / 'prior-home-records.json')
    protected = protected_snapshot(decisions)
    science = scientific_inputs(decisions)
    shared = P.data('home-departments.json')
    shared_sha = file_sha(shared)
    plans = {}
    for school, entries in decisions.items():
        path = P.data('home-departments-school.json', school)
        before = path.read_bytes() if path.exists() else None
        original = json.loads(before) if before is not None else []
        if school == 'uiuc':
            assert not HOME.load(school), 'UIUC gained another live review; reconcile before applying'
            projected = uiuc_projection(entries)
        else:
            current = {r['name']: r for r in HOME.load(school)}
            selected = []
            pis = {r['pi']: r for r in read(P.data('pis.json', school))}
            for name, entry in entries.items():
                old = current[name]
                assert old == prior[school][name], f'{school}/{name}: selected home changed since review'
                assert old.get('primary_unresolved') or old.get('home_basis') == 'primary_unresolved'
                identity = entry['home_department_evidence'][0]['identity_basis']
                current_identity = {k: pis[name].get(k) for k in ['pi', 'names', 'personIds', 'dblp', 'orcid']}
                assert digest(current_identity) == identity['pi_identity_sha256']
                selected.append(copy.deepcopy(old))
            H.apply_reviewed_homes(selected, entries, lambda u: u)
            for row in selected:
                old = prior[school][row['name']]
                assert HOME.review(row)['primary_resolved'] and not row.get('primary_unresolved')
                units = {old['home_department']} | set(old.get('also') or []) | set(old.get('primary_unresolved') or [])
                assert units <= {row['home_department']} | set(row.get('also') or [])
            projected = [r for r in original if r['name'] not in entries] + selected
        byname = {r['name']: r for r in projected}
        assert all(byname[name]['home_department'] == entry['home_department'] for name, entry in entries.items())
        assert all(byname[name]['reviewed_home_evidence'] == entry['home_department_evidence'] for name, entry in entries.items())
        plans[school] = dict(path=path, before=before, rows=projected)
    before_counts = counts()
    if apply:
        assert CODE.resolve() == P.CODE.resolve(), 'Apply only from landed main code'
        for school, entries in decisions.items():
            registered = read(P.data('home-department-decisions-school.json', school))
            assert all(registered.get(name) == entry for name, entry in entries.items()), 'Land reviewed inputs first'
        assert all((p['path'].read_bytes() if p['path'].exists() else None) == p['before'] for p in plans.values())
        for plan in plans.values():
            temporary = plan['path'].with_name(plan['path'].name + '.primary50c.part')
            temporary.write_text(json.dumps(plan['rows'], ensure_ascii=False, indent=1) + '\n')
            temporary.replace(plan['path'])
        assert file_sha(shared) == shared_sha
        verify_protected(protected)
        assert scientific_inputs(decisions) == science, 'Scientific inputs changed during application; inspect concurrent drift'
        for school, entries in decisions.items():
            accepted = HOME.accepted(school)
            assert all(accepted[name]['home_department'] == entry['home_department'] for name, entry in entries.items())
    result = dict(applied=apply, selected_existing=50, uiuc_records=428,
                  before=before_counts, after=counts() if apply else None,
                  all_unselected_home_rows_preserved=True, all_scientific_inputs_preserved=True,
                  all_prior_selected_affiliations_preserved=True, shared_register_unchanged=True,
                  schools={s: len(d) for s, d in decisions.items()})
    if apply:
        assert result['after']['primary_unresolved'] == result['before']['primary_unresolved'] - 50
        assert result['after']['accepted'] == result['before']['accepted'] + 370
        assert result['after']['research_unit_homes'] == result['before']['research_unit_homes'] + 1
        (HERE / 'application.json').write_text(json.dumps(result, indent=1) + '\n')
        (HERE / 'application-unselected-home-digests.json').write_text(json.dumps(protected, ensure_ascii=False, indent=1) + '\n')
        (HERE / 'application-scientific-input-digests.json').write_text(json.dumps(science, indent=1) + '\n')
    else:
        (SCRATCH / 'projected-home-departments.json').write_text(json.dumps(
            {s: p['rows'] for s, p in plans.items()}, ensure_ascii=False, indent=1) + '\n')
        (HERE / 'dry-run.json').write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    main(parser.parse_args().apply)
