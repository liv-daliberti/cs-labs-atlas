"""Validate source-reviewed final home allocations and apply only home registers.

Dry-run on the review branch; --apply only after the inputs and code land on main.
The current native PI inventory remains authoritative and is never changed here.
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
import home_departments_released as RELEASED
import home_departments_composed as COMPOSED
import schema_check
import school_config as S

HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1]
SCRATCH = P.SCRATCH / 'homes-finish-1123'


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1) + '\n')


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def selections():
    result = {}
    for part in ('cmu', 'missing', 'joint'):
        values = read(HERE / f'{part}-decisions.json')
        if part == 'cmu':
            values = {'cmu': values}
        for school, entries in values.items():
            target = result.setdefault(school, {})
            assert not set(target) & set(entries), 'Overlapping reviewed cohorts'
            target.update(entries)
    assert sum(map(len, result.values())) == 124
    assert result == read(HERE / 'decisions.json')
    return result


def verify_reviews():
    binding = read(HERE / 'review-binding.json')
    for part, expected in (('cmu', 38), ('missing', 40), ('joint', 46)):
        decisions = HERE / f'{part}-decisions.json'
        sources = HERE / f'{part}-sources.json'
        receipt = read(HERE / f'{part}-independent-review.json')
        assert receipt['result'] == 'pass' and receipt['passed'] == expected and receipt['failed'] == 0
        assert receipt['decisions_sha256'] == file_sha(decisions)
        assert receipt['source_receipts_sha256'] == file_sha(sources)
        assert len(receipt['verdicts']) == expected
        assert all(v['verdict'] == 'pass' for v in receipt['verdicts'])
        values = read(decisions)
        if part == 'cmu':
            values = {'cmu': values}
        assert {(v['school'], v['name']) for v in receipt['verdicts']} == {
            (school, name) for school, entries in values.items() for name in entries}
        assert receipt['reviewer'] != 'codex-homes-finish-1123'
        assert binding[part]['review_sha256'] == file_sha(HERE / f'{part}-independent-review.json')
        assert binding[part]['decisions_sha256'] == file_sha(decisions)
    archives = read(HERE / 'source-archives.json')
    for sha, source in archives.items():
        assert source['http_status'] == 200 and file_sha(Path(source['archive_file'])) == sha
    decisions = selections()
    schema = read(CODE / 'schemas/home-department-decisions.schema.json')
    for school, entries in decisions.items():
        assert not schema_check.validate(entries, schema), school
        for name, entry in entries.items():
            for evidence in entry['home_department_evidence']:
                source = archives[evidence['sha256']]
                # Each URL was verified in its part's independent review. A
                # single body can legitimately have several captured URL forms.
                assert evidence['url'] in source['verified_urls'], (school, name)
    return decisions


def coverage():
    schools = []
    for cfg in sorted(P.SCHOOL_CONFIGS.glob('*.toml')):
        school = cfg.stem
        path = P.data('pis.json', school)
        if not path.exists():
            continue
        homes = {r['name']: r for r in HOME.load(school)}
        pis = read(path)
        assert len(pis) == len({p['pi'] for p in pis}), f'{school}: duplicate native PI keys'
        missing, unresolved, research = [], [], 0
        for pi in pis:
            row = homes.get(pi['pi']) or {}
            if not (row.get('status') == 'accepted' and row.get('home_department') and HOME.valid_evidence(row)):
                missing.append(pi['pi'])
            if row.get('primary_unresolved') or row.get('home_basis') == 'primary_unresolved':
                unresolved.append(pi['pi'])
            research += bool(row.get('no_academic_department'))
        schools.append(dict(school=school, labs=len(pis), accepted=len(pis) - len(missing),
                            missing=missing, unresolved=unresolved, documented_research_unit_homes=research))
    return schools


def protected_snapshot(decisions):
    return {cfg.stem: {r['name']: digest(r) for r in HOME.load(cfg.stem)
                       if r['name'] not in decisions.get(cfg.stem, {})}
            for cfg in sorted(P.SCHOOL_CONFIGS.glob('*.toml'))}


def verify_protected(protected):
    for school, values in protected.items():
        now = {r['name']: digest(r) for r in HOME.load(school)}
        assert all(now.get(name) == sha for name, sha in values.items()), f'{school}: unselected home changed'


def scientific_inputs(schools):
    names = ('pis.json', 'census-faculty.json', 'census-additions.json', 'faculty-periods.json',
             'students.json', 'lab_papers.jsonl.gz', 'student_papers.jsonl.gz')
    return {str(path): file_sha(path) for school in schools for name in names
            if (path := P.data(name, school)).exists()}


def selected_projection(decisions, prior):
    byschool = collections.defaultdict(list)
    for school, entries in decisions.items():
        pis = {p['pi']: p for p in read(P.data('pis.json', school))}
        current = {r['name']: r for r in HOME.load(school)}
        cfg = S.get(school)
        canonical = set(S.field(cfg, 'census.home_units') or {}) | {
            unit['name'] for unit in S.listing_units(cfg)}
        for name, entry in entries.items():
            assert name in pis, f'{school}/{name}: no longer an active native PI key'
            old = current.get(name) or {}
            assert old == prior[school][name], f'{school}/{name}: selected home changed since review'
            identity = {k: pis[name].get(k) for k in ('pi', 'names', 'personIds', 'dblp', 'orcid')}
            assert entry['home_department_evidence'][0]['identity_basis']['pi_identity_sha256'] == digest(identity)
            assert entry['home_department'] in canonical, f'{school}/{name}: unregistered academic unit'
            row = copy.deepcopy(old) if old else dict(school=school, name=name, home_department=None,
                                                      also=[], status='hold', evidence=None)
            H.apply_reviewed_homes([row], {name: entry}, lambda u: u)
            assert HOME.review(row)['primary_resolved'] and not row.get('primary_unresolved')
            previous = {old.get('home_department')} | set(old.get('also') or []) | set(old.get('primary_unresolved') or [])
            previous.discard(None)
            assert previous <= {row['home_department']} | set(row.get('also') or [])
            assert H.apply_reviewed_homes([copy.deepcopy(row)], {name: entry}, lambda u: u) == [row]
            byschool[school].append(row)
    return byschool


def verify_native_rebuild(decisions, projections):
    output = SCRATCH / 'native-projections'
    output.mkdir(exist_ok=True)
    section, writer, released_reader = CO.section, P.data_w, RELEASED._read
    for school, entries in decisions.items():
        existing = section(school)
        target = output / f'{school}.json'
        try:
            CO.section = lambda key: existing | entries if key == school else section(key)
            def reviewed_reader(path, default):
                values = released_reader(path, default)
                if Path(path).name == 'home-department-decisions.json':
                    return {**values, **entries}
                return values
            RELEASED._read = reviewed_reader
            def data_writer(name, key=None):
                assert (name, key) == ('home-departments-school.json', school)
                return target
            P.data_w = data_writer
            with contextlib.redirect_stdout(io.StringIO()):
                if isinstance(read(P.data('census-faculty.json', school)), list):
                    RELEASED.main(school)
                elif not P.data('rows.json', school).exists():
                    COMPOSED.main(school)
                else:
                    H.main(school)
        finally:
            CO.section, P.data_w, RELEASED._read = section, writer, released_reader
        actual = {r['name']: r for r in read(target)}
        for selected in projections[school]:
            name = selected['name']
            assert name in actual and HOME.review(actual[name])['primary_resolved'], (school, name)
            assert actual[name]['home_department'] == selected['home_department'], (school, name, 'normalization/rebuild mismatch')
            assert actual[name]['reviewed_home_evidence'] == entries[name]['home_department_evidence']
            units = {selected['home_department']} | set(selected.get('also') or [])
            assert units <= {actual[name]['home_department']} | set(actual[name].get('also') or []), (school, name, 'rebuild lost affiliation')


def main(apply=False):
    decisions = verify_reviews()
    prior = read(HERE / 'original-cohort.json')
    protected = protected_snapshot(decisions)
    science = scientific_inputs(decisions)
    shared = P.data('home-departments.json')
    shared_sha = file_sha(shared)
    projected = selected_projection(decisions, prior)
    verify_native_rebuild(decisions, projected)
    plans = {}
    for school, selected in projected.items():
        path = P.data('home-departments-school.json', school)
        before = path.read_bytes() if path.exists() else None
        current = json.loads(before) if before else []
        replacements = {r['name']: r for r in selected}
        existing_names = {r['name'] for r in current}
        # Some inherited files contain identical duplicate rows. Preserve
        # bystanders byte-for-value and replace every copy of a selected key;
        # the registry still emits one allocation per exact PI key.
        rows = [replacements.get(r['name'], r) for r in current]
        rows += [row for name, row in replacements.items() if name not in existing_names]
        assert all(row == replacements[row['name']] for row in rows if row['name'] in replacements)
        plans[school] = dict(path=path, before=before, rows=rows)
    before_coverage = coverage()
    if apply:
        assert CODE.resolve() == P.CODE.resolve(), 'Apply from landed main only'
        for school, entries in decisions.items():
            registered = read(P.data('home-department-decisions-school.json', school))
            assert all(registered.get(name) == entry for name, entry in entries.items()), 'Land reviewed inputs first'
        assert all((p['path'].read_bytes() if p['path'].exists() else None) == p['before'] for p in plans.values())
        # All validation completes before the first home register is replaced.
        for plan in plans.values():
            temporary = plan['path'].with_name(plan['path'].name + '.homes-finish.part')
            write(temporary, plan['rows'])
            temporary.replace(plan['path'])
        assert file_sha(shared) == shared_sha
        verify_protected(protected)
        assert science == scientific_inputs(decisions), 'Concurrent scientific input drift; inspect before claiming preservation'
        after = coverage()
        assert not any(s['missing'] or s['unresolved'] for s in after), 'Live lab inventory still has an open home'
    else:
        after = None
    result = dict(applied=apply, selected_records=124, before=before_coverage, after=after,
                  selected_schools=sorted(decisions), prior_affiliations_retained=True,
                  unselected_home_rows_preserved=sum(map(len, protected.values())),
                  scientific_inputs_preserved_across_application=True, shared_register_unchanged=True,
                  native_rebuilds_passed=len(projected))
    write(HERE / ('application.json' if apply else 'dry-run.json'), result)
    if apply:
        write(HERE / 'application-unselected-home-digests.json', protected)
        write(HERE / 'application-scientific-input-digests.json', science)
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    main(parser.parse_args().apply)
