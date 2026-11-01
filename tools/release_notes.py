"""Release notes generated from the build regression (ROADMAP item 14, 2026-10-31): the CHANGES.md every release carries.

Nothing is written by hand. The text is a function of hierarchy/BUILD-REGRESSION.json (what moved between the snapshot
before the rebuild and the packages after it, tools/build_regression.py), the rules in the release manifest against the
previous release's, and the code commits between the two builds. The same inputs give the same text (no clock).

  tools/make_release.py writes it into the release before the manifest is made, so CHANGES.md is a manifest file.
  Regenerate for an existing release to read it (never writes into releases/):
      release_notes.py [<release id>]       prints the notes for that release from its own BUILD-REGRESSION.json
"""
import argparse, json, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402

TOP_PIS = 8


def delta(a, b):
    d = (b or 0) - (a or 0)
    return f'{d:+,}' if d else '0'


def commits(before, after, repo, limit=40):
    """Subjects of the commits between two builds' code commits ([] when either is unknown or git cannot say)."""
    if not before or not after or before == after:
        return []
    try:
        out = subprocess.run(['git', '-C', str(repo), 'log', '--format=%h %s', f'{before}..{after}'], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return []
    lines = out.stdout.splitlines() if out.returncode == 0 else []
    return lines[:limit] + ([f'... and {len(lines) - limit} more'] if len(lines) > limit else [])


def rules_changed(prev, now):
    """(added, removed) rule ids, with the decision note, from two manifests' `rules` lists."""
    p, n = {r['id']: r.get('decided') for r in prev or []}, {r['id']: r.get('decided') for r in now or []}
    return [f'{i} ({n[i]})' for i in n if i not in p], [i for i in p if i not in n]


def render(reg, release=None, prev_release=None, rules=None, prev_rules=None, repo=None):
    """CHANGES.md as text. reg = BUILD-REGRESSION.json; rules / prev_rules = the manifests' rule lists (optional)."""
    b, a = reg['before'], reg['after']
    L = [f'# Changes in release {release}' if release else '# Changes in this release', '',
         f"Generated from the build regression: the packages counted {a['at']} against the snapshot taken {b['at']}"
         f"{' (previous release ' + prev_release + ')' if prev_release else ''}. Nothing here is hand-written.", '']
    flags = reg.get('flags') or []
    L += [f'Regression flags: {len(flags)}' + (' (the release was allowed anyway)' if flags else ''), '']
    for f in flags:
        L.append('- ' + ', '.join(f'{k}: {v}' for k, v in f.items()))
    if flags:
        L.append('')
    L += ['## Counts by school', '', '| school | lab papers | student-paper links | lab-student pairs | PIs | row sets unchanged |', '|---|---|---|---|---|---|']
    for s, r in reg['schools'].items():
        cell = lambda k: f"{r['rows'][k]['before']:,} → {r['rows'][k]['after']:,} ({delta(r['rows'][k]['before'], r['rows'][k]['after'])})"
        same = [k for k, v in r['identical'].items() if v]
        L.append(f"| {s} | {cell('lab_papers')} | {cell('student_papers')} | {cell('lab_student_pairs')} | {cell('pis')} | "
                 f"{'all' if len(same) == len(r['identical']) and same else (', '.join(same) or 'none')} |")
    unchanged = [s for s, r in reg['schools'].items() if r['identical'] and all(r['identical'].values())]
    if unchanged:
        L += ['', 'Unchanged schools (every row set identical): ' + ', '.join(unchanged) + '.']
    for s, r in reg['schools'].items():
        if not (r['report'] or r['pis_changed'] or r.get('ledger')):
            continue
        L += ['', f'## {s}', '']
        if r['report']:
            L.append('Counts that moved: ' + '; '.join(f"{k} {v['before']:,} → {v['after']:,}" for k, v in sorted(r['report'].items())) + '.')
        if r.get('ledger'):
            L += ['', 'Unavailability ledger, papers by reason: ' + '; '.join(f"{k} {v['before']} → {v['after']}" for k, v in sorted(r['ledger'].items())) + '.']
        ch = sorted(r['pis_changed'], key=lambda x: (-abs((x['after'] or 0) - (x['before'] or 0)), x['pi']))
        if ch:
            L += ['', f"{len(ch)} {'PI has' if len(ch) == 1 else 'PIs have'} a different lab-paper count; the largest: " +
                  '; '.join(f"{x['pi']} {x['before']} → {x['after']}" for x in ch[:TOP_PIS]) + '.']
    if rules is not None and prev_rules is not None:
        add, rem = rules_changed(prev_rules, rules)
        if add or rem:
            L += ['', '## Rules', '']
            if add:
                L.append('Added: ' + ', '.join(add) + '.')
            if rem:
                L.append('Removed: ' + ', '.join(rem) + '.')
    cs = commits(b.get('code'), a.get('code'), repo or P.CODE)
    if cs:
        L += ['', f"## Code ({str(b.get('code'))[:10]}..{str(a.get('code'))[:10]})", ''] + [f'- {c}' for c in cs]
    return '\n'.join(L) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('release', nargs='?', default='latest')
    a = ap.parse_args(argv)
    d = Path(P.RELEASES) / a.release
    reg = json.loads((d / 'hierarchy' / 'BUILD-REGRESSION.json').read_text())
    man = json.loads((d / 'MANIFEST.json').read_text())
    sys.stdout.write(render(reg, man.get('release'), None, man.get('rules'), None))
    return 0


if __name__ == '__main__':
    sys.exit(main())
