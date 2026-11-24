"""Read-only onboarding and paper-publication reconciliation.

atlas doctor [school ...] [--gates recorded|live|off] [--site-dir DIR] [--out-dir DIR]

Uses the existing gate and rebuild dependency rules. Never runs collection,
restamps acceptance, changes a package, or admits a local file for hosting.
Website figures describe the selected checkout, not a verified live deployment.
"""
import argparse
import collections
import datetime
import gzip
import json
import re
from pathlib import Path

import atlas_paths as P
import school_config as S
import stale_stages as ST


def read_json(path, errors):
    try:
        return json.loads(Path(path).read_bytes())
    except (OSError, ValueError) as exc:
        errors.append(f'{path}: {exc}')
        return None


def read_rows(path, errors):
    try:
        with gzip.open(path, 'rt') as handle:
            return [json.loads(line) for line in handle if line.strip()]
    except (OSError, ValueError, EOFError) as exc:
        errors.append(f'{path}: {exc}')
        return None


def identities(row):
    """Exact IDs only; titles never match papers or copies."""
    keys = set()
    for field in ('work', 'w', 'key', 'id', 'atlasWorkId', 'atlasId', 'oa'):
        value = row.get(field)
        if value:
            keys.add(str(value))
            if re.fullmatch(r'(?:https?://openalex.org/)?W\d+', str(value)):
                keys.add(str(value).rsplit('/', 1)[-1])
    doi = re.sub(r'^https?://(?:dx\.)?doi\.org/', '', str(row.get('doi') or ''), flags=re.I).strip().lower()
    if doi:
        keys.add('doi:' + doi)
    if row.get('arxiv'):
        keys.add('arxiv:' + row['arxiv'])
    return keys


def identity_map(rows):
    """Withhold aliases shared by distinct rows; never select an arbitrary match."""
    candidates = collections.defaultdict(set)
    for pos, row in enumerate(rows):
        for key in identities(row):
            candidates[key].add(pos)
    return {k: next(iter(v)) for k, v in candidates.items() if len(v) == 1}


def match(row, mapping):
    hits = {mapping[key] for key in identities(row) if key in mapping}
    return next(iter(hits)) if len(hits) == 1 else None


def reader_record(index, paper):
    """Same lookup order as PaperReader.find, including compact record zero."""
    doi = re.sub(r'^https?://(?:dx\.)?doi\.org/', '', str(paper.get('doi') or ''), flags=re.I).lower()
    keys = [paper.get('w') or paper.get('oa'), paper.get('atlasId'), paper.get('oa'), 'doi:' + doi]
    for key in keys:
        if key not in index.get('works', {}):
            continue
        record = index['works'][key]
        if index.get('schema') == 2:
            if type(record) is not int or not 0 <= record < len(index.get('records', [])):
                continue
            record = index['records'][record]
        if isinstance(record, dict) and (record.get('path') or (
                record.get('link') and re.match(r'^https?://', record.get('sourceUrl') or '', re.I))):
            return record
    return None


def reconcile(rows, copies, site_papers, reader):
    """Disjoint counts over distinct package works, and actionable local-copy gaps."""
    unique = {}
    for row in rows:
        key = row.get('work') or row.get('oa') or next(iter(sorted(identities(row))), None)
        if key:
            unique.setdefault(key, row)
    copy_rows = [dict(value, key=key) for key, value in copies.get('papers', {}).items()]
    copy_map, site_map = identity_map(copy_rows), identity_map(site_papers)
    counts = collections.Counter(package_papers=len(unique), site_papers=len(site_papers), local_copies=0,
                                 local_hosted=0, local_linked=0, local_missing_reader=0,
                                 local_paper_missing_from_site=0, local_linked_without_indicator=0)
    gaps = []
    for key, row in unique.items():
        pos = match(row, copy_map)
        if pos is None or copy_rows[pos].get('status') not in ('downloaded', 'fulltext_xml'):
            continue
        counts['local_copies'] += 1
        site_pos = match(row, site_map)
        reason = None
        if site_pos is None:
            reason = 'local_paper_missing_from_site'
        else:
            record = reader_record(reader, site_papers[site_pos])
            if record is None:
                reason = 'local_missing_reader'
            elif record.get('path'):
                counts['local_hosted'] += 1
            else:
                counts['local_linked'] += 1
                if record.get('storedCopy') is not True and record.get('linkBasis') != 'confirmed_copy':
                    reason = 'local_linked_without_indicator'
        if reason:
            counts[reason] += 1
            gaps.append(dict(key=key, title=row.get('title'), doi=row.get('doi'), oa=row.get('oa'), reason=reason))
    return dict(counts), gaps


def gate_reports(key, mode):
    if mode == 'off':
        return []
    import stage_gate as G
    reports = []
    for stage in range(11):
        errors = []
        path = P.HIERARCHY / key / 'reports' / f'stage-{stage}-gate.json'
        try:
            if mode == 'live':
                result, at = G.evaluate(key, str(stage)), None
            elif path.exists():
                doc = read_json(path, errors) or {}
                result, at = doc.get('result') or {}, doc.get('at')
            else:
                result, at = {}, None
            reports.append(dict(stage=stage, gate=result.get('gate', 'unmeasured'), at=at,
                                items=result.get('unwaived_items', result.get('items', [])), errors=errors))
        except (OSError, ValueError, KeyError) as exc:
            reports.append(dict(stage=stage, gate='unmeasured', items=[], errors=[str(exc)]))
    return reports


def pi_state_view(key, mode):
    """Per-PI admission (process v4): the recorded hierarchy/<key>/reports/pi-states.json, or computed live with --gates live; None when off or never written."""
    if mode == 'off':
        return None
    import pi_states as PS
    try:
        res = PS.compute(key) if mode == 'live' else PS.recorded(key)
    except Exception as exc:   # a gate that cannot run is reported, never a pass
        return dict(error=f'{type(exc).__name__}: {exc}')
    if not res:
        return None
    return dict(at=res.get('at'), line=PS.summary_line(res), pis_total=res['pis_total'], downloadable=res['downloadable'], open_pis=res['open_pis'][:20],
                n_open=len(res['open_pis']), counts=res['counts'], school_items=sum(len(v) for v in res['school_items'].values()),
                release_ready=res['release_ready'])


def evidence_view(key):
    """For a store-sourced school (charter [evidence] source = "store"): does the reviewed JSON view equal the evidence store's export? None for other schools."""
    import evidence_store as E
    if E.source_of(key) != 'store':
        return None
    try:
        return dict(source='store', problems=E.check_view(key, P.CODE))
    except (OSError, ValueError, KeyError, E.SourceOfTruth) as exc:
        return dict(source='store', problems=[f'{key}: evidence view not measured: {exc}'])


def school_report(key, site, reader, gates):
    errors = []
    package = P.data('lab_papers.jsonl.gz', key)
    counter = P.data('copies.json', key)
    rows, copies = read_rows(package, errors), read_json(counter, errors)
    website = site / 'atlas/data/cs-hierarchy' / f'{key}.json.gz'
    index = read_json(website.parent / 'index.json', errors)
    # An unlisted school is known absence. Missing assets of a listed school,
    # or a missing index, are unknown, never a claim of zero site coverage.
    doc = None
    if index is not None and key not in {s['id'] for s in index.get('schools', [])}:
        doc = {'papers': []}
    elif index is not None:
        try:
            doc = json.loads(gzip.decompress(website.read_bytes()))
        except (OSError, ValueError, EOFError) as exc:
            errors.append(f'{website}: {exc}')
    counts, gaps = (None, []) if rows is None or copies is None or doc is None or reader is None else reconcile(
        rows, copies, doc.get('papers', []), reader)
    stale = {}
    for stage in ST.ORDER:
        try:
            changed, why = ST.check(stage, key)
            stale[stage] = dict(stale=changed, reason=why)
        except (OSError, ValueError, KeyError) as exc:
            stale[stage] = dict(stale=None, reason=str(exc))
    reports = gate_reports(key, gates)
    evidence = evidence_view(key)
    pi_view = pi_state_view(key, gates)
    # stages 3-7 are per PI (process v4): a failing gate there is shown in pi_states, it is not the school's first blocker
    first = next((g for g in reports if g['stage'] < 10 and g['stage'] not in (3, 4, 5, 6, 7) and g['gate'] not in ('pass', 'waived')), None)
    actions = []
    if stale.get('build', {}).get('stale'):
        actions.append(f'Build from committed reviewed inputs: bin/atlas pipeline build-audit SCHOOLS={key} --from-worktree')
    if first:
        actions.append(f'Inspect stage {first["stage"]}: bin/atlas stage-gate {key} {first["stage"]} --json'
                       + (' (recorded evidence only; evaluate live before deciding)' if gates == 'recorded' else ''))
    if pi_view and pi_view.get('n_open'):
        actions.append(f"{pi_view['n_open']} of {pi_view['pis_total']} PIs are open ({pi_view['downloadable']} downloadable now): bin/atlas stage-gate {key} admission")
    if evidence and evidence['problems']:
        actions.append(f'The {key} JSON view differs from its evidence store ({len(evidence["problems"])} problems): bin/atlas evidence-store check {key}; '
                       f'if the store is right, bin/atlas evidence-store sync {key} and commit; never edit the reviewed JSON by hand')
    if stale.get('copies', {}).get('stale'):
        actions.append(f'Recount after the build: bin/atlas pipeline copies SCHOOLS={key} --from-worktree')
    if counts and (counts['local_missing_reader'] or counts['local_paper_missing_from_site']):
        actions.append('Refresh the frozen reader export and school projection together through docs/PUBLISHING.md; '
                       'an interim hierarchy update retains the old reader allowlist.')
    if counts and counts['local_linked_without_indicator']:
        actions.append('Preserve stored_copy as storedCopy in the site importer and display local-copy provenance separately from read location.')
    return dict(school=key, package=str(package), copies=str(counter), website=str(website),
                copies_counted_at=(copies or {}).get('summary', {}).get('counted_at'), counts=counts, gaps=gaps,
                gates_basis=gates, gates=reports, pi_states=pi_view, evidence_view=evidence, stale=stale, next_actions=actions, errors=errors)


def markdown(report):
    lines = ['# Onboarding and publication reconciliation', '',
             'Website numbers describe the selected checkout, not a verified live deployment. '
             'Local copies are measured from copies.json; a stale counter needs recounting. '
             'These reports never authorize hosting or change attribution.', '',
             '| School | Package works | Local copies | Hosted | Linked | Paper absent from site | Reader missing |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for school in report['schools']:
        c = school['counts'] or {}
        lines.append('| ' + ' | '.join(str(x) for x in [school['school'], *[
            c.get(k, 'unknown') for k in ('package_papers', 'local_copies', 'local_hosted', 'local_linked',
                                        'local_paper_missing_from_site', 'local_missing_reader')]]) + ' |')
    for school in report['schools']:
        lines += ['', '## ' + school['school'], '']
        if school.get('pi_states') and school['pi_states'].get('line'):
            lines.append('- Per-PI admission (census/3/4/5/6/7 = done/excluded/open): ' + school['pi_states']['line'])
        lines += ['- ' + action for action in school['next_actions']]
        lines += ['- Unmeasured: ' + error for error in school['errors']]
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('schools', nargs='*')
    parser.add_argument('--gates', choices=['recorded', 'live', 'off'], default='recorded')
    parser.add_argument('--site-dir', type=Path, default=P.SITE)
    parser.add_argument('--out-dir', type=Path)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    schools = args.schools or sorted(p.stem for p in P.SCHOOL_CONFIGS.glob('*.toml') if p.stem != 'TEMPLATE')
    for key in schools:
        try:
            S.get(key)
        except KeyError:
            parser.error(f'unknown school: {key}')
    errors = []
    reader = read_json(args.site_dir / 'atlas/data/local-papers.json', errors)
    deployment = read_json(args.site_dir / 'deployment/release.json', errors)
    report = dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(), site_checkout=str(args.site_dir),
                  site_release=(deployment or {}).get('release'), reader_release=(reader or {}).get('release'),
                  errors=errors, schools=[school_report(k, args.site_dir, reader, args.gates) for k in schools])
    if args.out_dir:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        (args.out_dir / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        (args.out_dir / 'REPORT.md').write_text(markdown(report))
    print(json.dumps(report) if args.json else markdown(report))
    return 1 if errors or any(s['errors'] for s in report['schools']) else 0


if __name__ == '__main__':
    raise SystemExit(main())
