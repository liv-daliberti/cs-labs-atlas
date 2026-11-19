"""Release readiness matrix: the freeze as one re-runnable, read-only check (claude-freeze-prep-1119, 2026-11-19).

For every school with at least one included PI under the per-PI rules (tools/pi_release.py, D-0001), one row with real results:
  pis          included / carried / held PIs and `included_sha`
  ids          atlas ids present in the package (make_release refuses a package without them)
  gates        stage-gate 0..10: rc per gate, exactly as `atlas stage-gate <school> <n>` returns it (0 pass or waived, 1 fail), plus open count
  compare      pi_release.compare against the last published release: unexplained removals by kind, rows explained by recorded corrections
  g9           accuracy/summary-<school>.json against the CURRENT included_sha / package hashes (fresh | stale | missing | below_bar)
  validate     tools/validate.py violations of the school's package files
  build        package builtAt, and BUILD-REGRESSION.json / EVIDENCE-CHECK.json freshness against the newest build of the included schools
Nothing is written except --json/--md. Run it nice; it reads packages (no OpenAlex, no network).

  release_readiness.py [school ...] [--published DIR] [--json FILE] [--md FILE] [--jobs N] [--all-charters]
  exit 1 when any included school has a failing check.
"""
import argparse
import concurrent.futures as cf
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import atlas_paths as P  # noqa: E402

GATES = [str(i) for i in range(11)]
PER_PI = ('3', '4', '5', '6', '7')   # a failing gate here holds PIs, not the school (stage_gate.PER_PI_STAGES)
# D-0001 (per-PI release): pi_release.plan reports the school-level items of stages 0-2 and 8 (a candidate with no decision is not in the package, a roster year,
# a host probe, the copies count) and they do not hold a school that has done PIs. Stage 10 is judged by its parts (below).
SCHOOL_LEVEL = ('0', '1', '2', '8')
G10_RELEASE_TIME = ('charter status is', 'the newest release does not count')   # true only AFTER the release is cut: circular before it, never a blocker


def _read(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def _ts(iso):
    try:
        return datetime.fromisoformat(str(iso).rstrip('Z')).replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return None


def charter_schools():
    return sorted(p.stem for p in Path(P.SCHOOL_CONFIGS).glob('*.toml') if p.stem != 'TEMPLATE')


def g9_state(key, pl, gate_result):
    """fresh | stale | missing | below_bar for a school's accuracy summary, from the findings of stage_gate.g9 (the real judge)."""
    import stage_gate as G
    d = _read(G.ACCURACY_DIR / f'summary-{key}.json')
    if not isinstance(d, dict):
        return dict(state='missing', findings=gate_result['items'][:3])
    items = gate_result['items']
    stale = [i for i in items if 'changed' in i or 'redraw' in i or 'files !=' in i]
    low = [i for i in items if i not in stale]
    sub = d.get('subset') or {}
    measures = {k: (d[k].get('p') if isinstance(d.get(k), dict) else None) for k in ('lab_precision_uniform', 'student_precision', 'coverage') if k in d}
    state = 'stale' if stale else ('below_bar' if low else 'fresh')
    return dict(state=state, findings=items[:4], drawn_pis=sub.get('n_pis'), included_now=len(pl['included']),
                sha_match=(sub.get('included_sha') == pl['included_sha']) if sub else None, measures=measures,
                n_verdicts=d.get('n_verdicts'))


def school_row(key, published):
    import pi_release as PR
    import stage_gate as G
    import validate as V
    G.ACCURACY_DIR = Path(P.CODE) / 'accuracy'   # the measurements live in the main checkout (untracked); a worktree's own accuracy/ is only the tracked part
    t0 = time.time()
    pl = PR.plan(key, published=published)
    row = dict(school=key, included=len(pl['included']), carried=len(pl['carried']), held=len(pl['held']), package_pis=pl['package_pis'],
               partial=pl['partial'], included_sha=pl['included_sha'][:12])
    if not pl['included']:
        row['skip'] = 'no included PI'
        return row
    rep = _read(P.data('report.json', key), {}) or {}
    row['built_at'] = rep.get('builtAt')
    row['ids'] = PR._has_ids(key)
    import stale_stages as SS   # the package against its reviewed / recovered / raw inputs (the rebuild window, tools/stale_stages.py)
    outs = [SS.mtime(x) for x in SS.output_paths('build', key)]
    ins = [(SS.mtime(x), x.name) for x in SS.input_paths(SS.STAGES['build'][1], key) if SS.mtime(x) and x.name != 'release-corrections.json']   # corrections are read by the release, not the build
    stale = (not outs or any(t is None for t in outs) or (bool(ins) and max(ins)[0] > min(outs)))
    why = 'an input is newer than the oldest output' if stale else 'fresh'
    row['stale_build'] = dict(stale=bool(stale), why=why, newest_input=(max(ins)[1] if ins else None),
                              newest_input_at=(datetime.fromtimestamp(max(ins)[0], timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ') if ins else None))
    gates = {}
    for st in GATES:
        try:
            r = G.evaluate(key, st)
            gates[st] = dict(rc=0 if r['gate'] != 'fail' else 1, gate=r['gate'], open=r['open'])
            if st == '10':
                its = r['items']
                gates[st]['parts'] = dict(release_time=sum(i.startswith(G10_RELEASE_TIME) for i in its), accuracy=sum(i.startswith('accuracy:') for i in its),
                                          recorded_gate_stale=sum(i.startswith('stale:') for i in its))
                gates[st]['other'] = [i[:200] for i in its if not (i.startswith(G10_RELEASE_TIME) or i.startswith(('accuracy:', 'stale:')))]
            if st == '9':
                row['g9'] = g9_state(key, pl, r)
        except Exception as e:   # a gate that cannot be evaluated is a finding, not a crash
            gates[st] = dict(rc=2, gate='error', open=None, error=repr(e)[:160])
    row['gates'] = gates
    row['copies_json'] = P.data('copies.json', key).exists()
    try:
        c = PR.compare(key, pl['included'], published) if published else None
    except Exception as e:
        c = dict(compared=False, flags=-1, error=repr(e)[:160])
    if c and c.get('compared'):
        row['compare'] = dict(rc=1 if c['flags'] else 0, flags=c['flags'], basis=c['basis'],
                              removed={k: v['n_removed'] for k, v in c['kinds'].items() if v['n_removed']},
                              corrected=sum((c.get('corrected') or {}).values()), corrections_unused=c.get('corrections_unused'),
                              has_record=bool(c.get('corrections_record')))
    else:
        row['compare'] = dict(rc=0 if not c or not c.get('error') else 2, flags=0, note=(c or {}).get('error') or 'school not in the last release')
    a = type('A', (), dict(schools=[key], shared=False, reviewed=False, tree=False, export=False, root=None))()
    res, total = V.run(a)
    row['validate'] = dict(violations=total, missing=sum(v['status'] == 'missing' for v in res.values()),
                           examples=[f"{k}: {e}" for k, v in res.items() if v['status'] == 'violations' for e in v['examples'][:2]][:3])
    row['secs'] = round(time.time() - t0, 1)
    return row


def freshness(rows):
    """BUILD-REGRESSION.json and EVIDENCE-CHECK.json against the newest build among the included schools (make_release's own rule)."""
    built = [_ts(r.get('built_at')) for r in rows if r.get('built_at')]
    newest = max([b for b in built if b], default=None)
    out = dict(newest_build=datetime.fromtimestamp(newest, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ') if newest else None)
    for name, key in (('BUILD-REGRESSION.json', 'regression'), ('EVIDENCE-CHECK.json', 'evidence_check')):
        p = P.data(name)
        d = _read(p)
        if d is None:
            out[key] = dict(state='missing')
            continue
        m = p.stat().st_mtime
        e = dict(state='fresh' if newest and m >= newest else 'stale', written=datetime.fromtimestamp(m, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
        if key == 'regression':
            e['flags'] = len(d.get('flags') or [])
        else:
            e.update(mode=d.get('mode'), ok=d.get('ok'))
            if d.get('mode') != 'strict' or not d.get('ok'):
                e['state'] = 'failed'
        out[key] = e
    return out


def shared_validate():
    import validate as V
    a = type('A', (), dict(schools=[], shared=True, reviewed=False, tree=False, export=False, root=None))()
    res, total = V.run(a)
    return dict(violations=total, files={k: v['status'] for k, v in res.items() if v['status'] == 'violations'})


OWNER_HINT = dict(nus='claude-ns-a-1118 (T659, stale) or Codex; school not in this release', seu='Codex (whu/seu sessions) or claude-ns-a-1118 (T016, stale); not in this release',
                  hit='claude-ns-a-1118 (T012, stale); files committed by claude-freeze-prep-1119', berkeley='claude-release-ready-1118 (store export of release-corrections)',
                  michigan='claude-release-ready-1118 (store export of release-corrections)')


def tree_state():
    """Reviewed inputs and tracked files of the main checkout that git does not hold as committed (a freeze needs them committed or knowingly ignored):
    untracked reviewed JSON, modified tracked files, deleted tracked files. The tool-regenerated student-recall-check copies and derived/ trees are not listed."""
    import subprocess
    out = subprocess.run(['git', '-C', str(P.CODE), 'status', '--porcelain', '--', 'hierarchy', 'accuracy'], capture_output=True, text=True).stdout.splitlines()
    res = dict(untracked_reviewed={}, modified_tracked=[], deleted_tracked=[])
    for line in out:
        code, path = line[:2], line[3:]
        if 'student-recall-check' in path or '/tmp/' in path or '/derived/' in path or path.startswith('accuracy/'):
            continue
        if code == '??' and '/reviewed/' in path:
            res['untracked_reviewed'].setdefault(path.split('/')[1], []).append(path.rsplit('/', 1)[-1])
        elif code.strip() == 'M':
            res['modified_tracked'].append(path)
        elif code.strip() == 'D':
            res['deleted_tracked'].append(path)
    res['owner_hint'] = {k: OWNER_HINT.get(k, 'unknown') for k in res['untracked_reviewed']}
    return res


def problems(r):
    """The failing checks of one row, as short strings (empty = ready)."""
    out = []
    if r.get('skip'):
        return out
    if r.get('stale_build', {}).get('stale'):
        out.append('build stale')
    if not r.get('ids'):
        out.append('ids')
    if not r.get('copies_json', True):
        out.append('copies.json missing')
    g10 = r['gates'].get('10', {})
    if g10.get('parts', {}).get('recorded_gate_stale') or g10.get('other'):
        out.append('gate 10: ' + ', '.join(filter(None, [f"{g10['parts']['recorded_gate_stale']} recorded gates stale" if g10.get('parts', {}).get('recorded_gate_stale') else '', *g10.get('other', [])[:1]])))
    bad = [s for s, g in r['gates'].items() if g['rc'] and s not in PER_PI and s not in SCHOOL_LEVEL and s not in ('9', '10')]
    if bad:
        out.append('gates ' + ','.join(bad))
    if r['compare']['rc']:
        out.append(f"removals {r['compare']['flags']}")
    if r.get('g9', {}).get('state') != 'fresh':
        out.append('g9 ' + r.get('g9', {}).get('state', 'missing'))
    if r['validate']['violations']:
        out.append(f"validate {r['validate']['violations']}")
    return out


def render_md(doc):
    L = [f"# Release readiness {doc['at']}", '',
         f"Compared with release `{doc['published']}`; code `{doc.get('code')}`. Re-run: `bin/atlas run tools/release_readiness.py --json ... --md ...` (read-only, ~{doc.get('secs')} s).", '',
         '| school | incl/held | build | rebuild | ids | gates failing (school-level 0-2,8 and per-PI 3-7 in parens, reported not blocking; 10* = release-time parts only: charter/newest-release/accuracy) | removals | recorded | g9 | validate | built | problems |',
         '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in doc['rows']:
        if r.get('skip'):
            continue
        gf = [s for s, g in r['gates'].items() if g['rc'] and s not in PER_PI and s not in SCHOOL_LEVEL and s != '10']
        gf += ['10*'] if r['gates'].get('10', {}).get('rc') else []
        gp = [s for s, g in r['gates'].items() if g['rc'] and (s in PER_PI or s in SCHOOL_LEVEL)]
        g9 = r.get('g9', {})
        L.append(f"| {r['school']} | {r['included']}/{r['held']} | {'STALE (' + str(r['stale_build']['newest_input']) + ')' if r['stale_build']['stale'] else 'fresh'} | {r.get('rebuild', '-')} | {'yes' if r['ids'] else 'NO'} | {','.join(gf) or '-'}{' (' + ','.join(gp) + ')' if gp else ''} | "
                 f"{r['compare']['flags']} | {r['compare'].get('corrected', 0)} | {g9.get('state', '-')} | {r['validate']['violations']} | {str(r.get('built_at', ''))[5:16]} | {'; '.join(r['problems']) or 'READY'} |")
    skipped = [r['school'] for r in doc['rows'] if r.get('skip')]
    L += ['', f"No included PI (not in the release, D-0018): {', '.join(skipped) or 'none'}", '']
    f = doc['freshness']
    L += ['## Shared files', f"- newest included build: {f['newest_build']}",
          f"- BUILD-REGRESSION.json: {f['regression']}", f"- EVIDENCE-CHECK.json: {f['evidence_check']}",
          f"- shared validate: {doc['shared_validate']}", '']
    t = doc.get('tree') or {}
    L += ['## Main checkout: reviewed inputs not in git (student-recall-check copies and derived/ ignored)']
    for sc, files in sorted((t.get('untracked_reviewed') or {}).items()):
        L.append(f"- untracked {sc}: {', '.join(files)} (likely owner: {(t.get('owner_hint') or {}).get(sc)})")
    L += [f'- modified tracked: {x}' for x in t.get('modified_tracked') or []]
    L += [f'- deleted tracked: {x}' for x in t.get('deleted_tracked') or []]
    L += ['', '## Removals by kind (unexplained, vs the last release)']
    for r in doc['rows']:
        if r.get('compare', {}).get('removed'):
            L.append(f"- {r['school']}: {r['compare']['removed']} (basis: {r['compare'].get('basis')}, record: {'yes' if r['compare'].get('has_record') else 'no'}, restored-but-listed: {r['compare'].get('corrections_unused')})")
    L += ['', '## g9 detail']
    for r in doc['rows']:
        g = r.get('g9')
        if g:
            L.append(f"- {r['school']}: {g['state']} drawn {g.get('drawn_pis')} PIs, now {g.get('included_now')}; measures {g.get('measures')}")
    if doc.get('make_release'):
        L += ['', '## make_release --per-pi --dry-run', f"rc {doc['make_release'].get('rc')}: {doc['make_release'].get('tail')}"]
    return '\n'.join(L) + '\n'


def run(schools, published, jobs=6):
    t0 = time.time()
    rows = []
    with cf.ProcessPoolExecutor(max_workers=jobs) as ex:
        futs = {ex.submit(school_row, s, published): s for s in schools}
        for f in cf.as_completed(futs):
            try:
                rows.append(f.result())
            except Exception as e:
                rows.append(dict(school=futs[f], error=repr(e)[:300], skip=None, included=0, held=0, ids=False,
                                 gates={}, compare=dict(rc=2, flags=-1), validate=dict(violations=-1)))
    rows.sort(key=lambda r: r['school'])
    st = _read(Path(P.CODE).parent / 'scratch' / 'freeze-prep-1119' / 'rebuild-status.json', {})   # the rebuild window's log: {school: "done <job> <time>" | "queued" | ...}
    for r in rows:
        if r['school'] in st:
            r['rebuild'] = st[r['school']]
    for r in rows:
        r['problems'] = problems(r) if not r.get('error') else ['error ' + r['error']]
    import subprocess
    try:
        code = subprocess.run(['git', '-C', str(Path(__file__).resolve().parent.parent), 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
    except OSError:
        code = None
    return dict(at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), published=Path(published).resolve().name if published else None, code=code,
                rows=rows, freshness=freshness(rows), shared_validate=shared_validate(), tree=tree_state(), secs=round(time.time() - t0)), rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('schools', nargs='*')
    ap.add_argument('--published', help='release dir to compare with (default releases/latest)')
    ap.add_argument('--json')
    ap.add_argument('--md')
    ap.add_argument('--jobs', type=int, default=6)
    a = ap.parse_args(argv)
    pub = Path(a.published) if a.published else (Path(P.RELEASES) / 'latest')
    pub = pub if pub.exists() else None
    schools = a.schools or charter_schools()
    doc, rows = run(schools, pub, a.jobs)
    if a.json:
        Path(a.json).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
    md = render_md(doc)
    if a.md:
        Path(a.md).write_text(md)
    else:
        print(md)
    return 1 if any(r.get('problems') for r in rows) else 0


if __name__ == '__main__':
    sys.exit(main())
