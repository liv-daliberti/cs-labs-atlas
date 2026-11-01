"""Which accepted lab-page papers the build kept, and which it set aside (ROADMAP: lab-page wiring, 2026-10-31).

For each school, the papers of hierarchy/<school>/labpage-additions.json that labpage-acceptance.json accepts
(pihier.common.accepted_additions) are looked up in a built package's lab_papers.jsonl.gz by (pi, key). Each one is
`wired`, or set aside with the counter that explains it in report.json (outside the atlas window, outside the PI's
appointment periods, already a lab paper through another source). Read-only; the package root is a scratch build.

usage: wired_additions_report.py <package root> [--schools a b ...] [--json out.json]   (root holds <school>/ packages)
"""
import argparse, collections, gzip, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pihier.common import accepted_additions  # noqa: E402


def report(root, school):
    n = collections.Counter()
    acc = accepted_additions(school, 'papers', None, n)
    pkg = Path(root) / school
    lp = pkg / 'lab_papers.jsonl.gz'
    rows = [json.loads(x) for x in gzip.decompress(lp.read_bytes()).decode().split('\n') if x.strip()] if lp.exists() else []
    have = {(r['pi'], r['oa']) for r in rows if str(r.get('source') or '').startswith('labpage_addition:')}
    rep = json.loads((pkg / 'report.json').read_bytes()) if (pkg / 'report.json').exists() else {}
    c = (rep.get('counts') or {})
    out = dict(school=school, accepted=len(acc), wired=0, set_aside=[])
    for x in acc:
        if (x['pi'], x['key']) in have:
            out['wired'] += 1
            continue
        y = int(x['year'])
        out['set_aside'].append(dict(pi=x['pi'], year=y, title=x.get('title'), key=x['key']))
    out['counters'] = {k: v for k, v in c.items() if k.startswith('labpage_addition_')}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('root'); ap.add_argument('--schools', nargs='*'); ap.add_argument('--json')
    a = ap.parse_args(argv)
    schools = a.schools or [d.name for d in sorted(Path(a.root).iterdir()) if d.is_dir()]
    res = [report(a.root, s) for s in schools]
    for r in res:
        if not r['accepted'] and not r['counters']:
            continue
        print(f"{r['school']:10} accepted papers {r['accepted']}, wired {r['wired']}, set aside {len(r['set_aside'])}  {r['counters']}")
        for x in r['set_aside']:
            print(f"    set aside: {x['pi']} {x['year']} {(x['title'] or '')[:70]}  [{x['key']}]")
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
