"""Which accepted lab-page papers the build kept, and which it set aside (lab-page wiring, 2026-10-31).

Read from a built package only (so the report is the build's own account, whatever changed in the inputs since):
  kept       lab_papers.jsonl.gz rows whose source is labpage_addition:<rule>:<basis>;
  set aside  report.json -> labpageAdditionsSetAside: the accepted papers the build did not keep, each with its reason
             (outside_window | outside_appointment | already_a_lab_paper), and the counts
             labpage_additions_papers_wired / _not_wired:<why> (a kind that labpage-acceptance.json did not accept).
The appointment check is the builder's own (periods, contains(), faculty_end_moved departures; listingsAfterMove): an accepted
addition outside the PI's appointment is listed here and is not a lab paper.

usage: wired_additions_report.py <package root> [--schools a b ...] [--json out.json]   (root holds <school>/ packages)
"""
import argparse, collections, gzip, json, sys
from pathlib import Path


def report(root, school):
    pkg = Path(root) / school
    lp = pkg / 'lab_papers.jsonl.gz'
    rows = [json.loads(x) for x in gzip.decompress(lp.read_bytes()).decode().split('\n') if x.strip()] if lp.exists() else []
    kept = collections.Counter(r['pi'] for r in rows if str(r.get('source') or '').startswith('labpage_addition:'))
    rep = json.loads((pkg / 'report.json').read_bytes()) if (pkg / 'report.json').exists() else {}
    counts = {k: v for k, v in (rep.get('counts') or {}).items() if k.startswith('labpage_addition')}
    aside = rep.get('labpageAdditionsSetAside') or []
    return dict(school=school, kept=sum(kept.values()), kept_by_pi=dict(kept), set_aside=aside, counts=counts,
                by_reason=dict(collections.Counter(x['reason'] for x in aside)))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('root'); ap.add_argument('--schools', nargs='*'); ap.add_argument('--json')
    a = ap.parse_args(argv)
    schools = a.schools or [d.name for d in sorted(Path(a.root).iterdir()) if d.is_dir()]
    res = [report(a.root, s) for s in schools]
    for r in res:
        if not r['kept'] and not r['set_aside'] and not r['counts']:
            continue
        print(f"{r['school']:10} kept {r['kept']}, set aside {len(r['set_aside'])} {r['by_reason']}  {r['counts']}")
        for x in sorted(r['set_aside'], key=lambda x: (x['reason'] != 'outside_appointment', x['pi'], x['year'])):
            if x['reason'] != 'already_a_lab_paper':
                print(f"    set aside ({x['reason']}): {x['pi']} {x['year']} {(x.get('title') or '')[:70]}  [{x.get('key')}]")
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
