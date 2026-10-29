"""Every PI lab with zero lab papers (and every one with zero students): why, and whether zero is right.

The site hides labs without papers (owner 2026-10-22), so each hidden lab needs a reason on record. The diagnosis is
read from the PI's funnel in hierarchy/<school>/pis.json (where the PI's papers dropped out of the lab-paper rule):
  joined_after_window      the reviewed appointment starts after every paper so far (e.g. a 2026-07 arrival)
  no_appointment_coverage  papers name the PI and the school, but none falls in a reviewed period or same-year listing
  identity_unanchored      school-affiliated name hits, none tied to the PI by DBLP/ORCID/reviewed id/advisee/page
  no_school_affiliation    the PI's papers exist, none lists the school (industry or other-employer bylines)
  not_in_school_sweep      DBLP or the collection knows the PI's works, but no 2016-2026 school work carries the name
  no_output_found          no work at all in 2016-2026 under the PI's names
The reviewed verdict comes from hierarchy/zero-paper-review.json {school: {pi: {verdict, reason, evidence?}}}, where
verdict is 'zero_is_right' (with the reason) or 'fix' (what still has to change); a lab with no review is 'unreviewed'.
-> hierarchy/zero-paper-labs.json
usage: zero_paper_ledger.py
"""
import collections, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402  (every path in one place)
HERE = P.WORK
SCHOOLS = ['princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford']


def diagnose(p):
    f = p.get('funnel') or {}
    outside = sum(v for k, v in f.items() if k.startswith('outside_appointment_'))
    starts = [str(q.get('start') or '') for q in p.get('periods') or []]
    if f.get('identity') and not f.get('in_appointment') and starts and all(s[:4] >= '2026' for s in starts):
        return 'joined_after_window'
    if f.get('identity') and not f.get('in_appointment'):
        return 'no_appointment_coverage'
    if f.get('school_affiliated') and not f.get('identity'):
        return 'identity_unanchored'
    if f.get('name_hits') and not f.get('school_affiliated'):
        return 'no_school_affiliation'
    if f.get('dblpTitles') or f.get('dblpDois') or f.get('verifiedWorks'):
        return 'not_in_school_sweep'
    return 'no_output_found' if not outside else 'no_appointment_coverage'


def main():
    rv_path = HERE / 'hierarchy/zero-paper-review.json'
    rv = json.load(open(rv_path)) if rv_path.exists() else {}
    out, counts = dict(built_by='tools/zero_paper_ledger.py', zero_papers=[], zero_students=[]), collections.Counter()
    for s in SCHOOLS:
        for p in json.load(open(HERE / 'hierarchy' / s / 'pis.json')):
            c = p.get('counts') or {}
            f = p.get('funnel') or {}
            if not c.get('labPapers'):
                r = (rv.get(s) or {}).get(p['pi']) or {}
                row = dict(school=s, pi=p['pi'], departments=p.get('departments'), rank=p.get('rank'), title=p.get('title'),
                           diagnosis=diagnose(p), verdict=r.get('verdict', 'unreviewed'), reason=r.get('reason'), evidence=r.get('evidence'),
                           funnel={k: v for k, v in f.items() if not k.startswith('outside_appointment_')},
                           outside_appointment_by_year={k[-4:]: v for k, v in f.items() if k.startswith('outside_appointment_')},
                           periods=[(q.get('start'), q.get('end')) for q in p.get('periods') or []], listing_years=[l['year'] for l in p.get('listings') or []],
                           students=c.get('students', 0))
                out['zero_papers'].append(row); counts[s, 'zero_papers', row['verdict']] += 1
            if not c.get('students'):
                out['zero_students'].append(dict(school=s, pi=p['pi'], departments=p.get('departments'), lab_papers=c.get('labPapers', 0)))
                counts[s, 'zero_students'] += 1
    out['counts'] = {f'{k[0]}:{":".join(k[1:])}': v for k, v in sorted(counts.items())}
    json.dump(out, open(HERE / 'hierarchy/zero-paper-labs.json', 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(out['counts']))
    for r in out['zero_papers']:
        print(f"{r['school']:9} {r['pi'][:28]:28} {r['diagnosis']:24} {r['verdict']}")


if __name__ == '__main__':
    main()
