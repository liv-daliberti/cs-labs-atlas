"""Share of each PI's DBLP-listed non-preprint papers (2016-2026, in a year of the PI's appointment) that the lab-paper set holds.

The independent reference is the PI's own DBLP person page (the dump's persons file, as dblp_recover.candidates reads it). A record counts
when it is not a CoRR preprint and its year is a listing year of the PI or inside a faculty period. It is held when the PI's lab papers
contain it by DOI or normalized title. Per PI: listed, held, and the held share; the missing ones are those dblp_recover.candidates returns.
usage: dblp_held_share.py <school> [--out file]   -> {school, listed, held, share, per_pi: {...}}
"""
import collections, gzip, json, sys

import dblp_recover as D
import atlas_paths as P  # noqa: E402
from pi_hierarchy import read, ndoi, norm_title


def run(school):
    pis = read(P.data('pis.json', school))
    pubs = D.dump_pubs(pis, school)
    rows = [json.loads(l) for l in gzip.open(P.data('lab_papers.jsonl.gz', school), 'rt')]
    have = collections.defaultdict(set)
    for r in rows:
        have[r['pi']].add(norm_title(r.get('title'))); have[r['pi']].add(ndoi(r.get('doi')))
    owner = collections.defaultdict(list)
    for p in pis:
        for q in p.get('dblp') or []:
            owner[q].append(p)
    per = collections.defaultdict(lambda: dict(listed=0, held=0, missing=[]))
    for k, rec in pubs.items():
        y = rec.get('year')
        if not y or not (2016 <= int(y) <= 2026) or 'journals/corr' in k:
            continue
        t = norm_title((rec.get('title') or '').rstrip('.'))
        for q in rec.get('authors') or {}:
            for p in owner.get(q, []):
                years = {l['year'] for l in p['listings']}
                if int(y) not in years and not any((x['start'] or '9999')[:4] < str(y) < (x['end'] or '9999')[:4] for x in p['periods']):
                    continue
                d = per[p['pi']]; d['listed'] += 1
                if t in have[p['pi']] or (rec.get('doi') and ndoi(rec['doi']) in have[p['pi']]):
                    d['held'] += 1
                else:
                    d['missing'].append(dict(key=k, title=rec.get('title'), year=int(y), doi=rec.get('doi'), venue=rec.get('venue')))
    L = sum(d['listed'] for d in per.values()); H = sum(d['held'] for d in per.values())
    return dict(school=school, pis_with_listed=len(per), listed=L, held=H, share=round(H / L, 4) if L else None, per_pi=per)


if __name__ == '__main__':
    res = run(sys.argv[1])
    if '--out' in sys.argv:
        json.dump(res, open(sys.argv[sys.argv.index('--out') + 1], 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'per_pi'}))
