"""The candidate universe of the CS-related scope review, per school: cs-related-candidates.json, the thesis harvest's
non-PI advisers, and the missing-PI review's out-of-scope rejections; each resolved against pis.json (names and OpenAlex
ids) and against the school's author index (OpenAlex authors whose raw names match, with their CS-venue counts).
-> <out>/<school>-universe.json
usage: universe.py <out_dir> <school> [<school> ...]
"""
import collections, gzip, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE / 'tools'))
from pi_hierarchy import Name, toks  # noqa: E402


def natural(n):
    n = re.sub(r'\s+', ' ', n).strip()
    if n.count(',') == 1:
        a, b = [x.strip() for x in n.split(',')]
        return f'{b} {a}'
    return n


def main(out, schools):
    th = json.load(open(HERE / 'hierarchy/thesis-harvest-report.json'))['non_pi_advisers']
    for s in schools:
        A = json.load(gzip.open(Path(out) / f'{s}-authors.json.gz', 'rt'))
        by_last = collections.defaultdict(list)
        for aid, r in A.items():
            for raw in r['raw']:
                t = toks(raw)
                if len(t) >= 2:
                    by_last[t[-1]].append(aid); by_last[t[0]].append(aid)
        pis = json.load(open(HERE / 'hierarchy' / s / 'pis.json'))
        pi_ids = {a: p['pi'] for p in pis for a in (p.get('oaAuthorIds') or []) + (p.get('reviewedOpenAlex') or [])}
        pi_nm = [(p['pi'], Name(p.get('names') or [p['pi']])) for p in pis]
        cf = HERE / f'census/{s}-faculty-hierarchy.json'
        cen = json.load(open(cf if cf.exists() else HERE / f'census/{s}-faculty.json'))
        cen = cen.get('faculty', cen) if isinstance(cen, dict) else cen
        if (HERE / f'census/{s}-additions.json').exists():
            cen = list(cen) + json.load(open(HERE / f'census/{s}-additions.json'))
        cen_nm = [(c['name'], Name([c['name']] + list(c.get('aliases') or [])), c.get('rank'), c.get('is_pi'), c.get('departments')) for c in cen]
        U = collections.OrderedDict()

        def add(name, src, **kw):
            nm = natural(name)
            key = ' '.join(toks(nm))
            r = U.setdefault(key, dict(name=nm, sources=[], aliases=[], seed_openalex=[]))
            r['sources'].append(src)
            if name not in r['aliases'] and name != nm:
                r['aliases'].append(name)
            for k, v in kw.items():
                if k == 'seed_openalex':
                    r['seed_openalex'] += [x for x in v if x not in r['seed_openalex']]
                else:
                    r[k] = v
        for c in json.load(open(HERE / 'hierarchy' / s / 'cs-related-candidates.json')):
            add(c['name'], 'cs-related-candidates', seed_openalex=[c['author']], cand=dict(works=c['works'], cs=c['cs_venue_works'], share=c['cs_share'], last=c['last_author_share'], years=c['years'], top=c['top_venues'][:3]))
        for c in th.get(s, []):
            add(c['adviser'], 'thesis-non-pi-adviser', theses=c['theses'] if isinstance(c['theses'], int) else c['theses'], thesis_years=c['years'], census=(c.get('census') or {}).get('rank'))
        mp = json.load(open(HERE / 'hierarchy' / s / 'missing-pi-review.json'))
        for d in mp['decisions']:
            if d.get('decision') == 'does_not_qualify' and d.get('reason') in ('homed_outside_scope', 'not_faculty_of_a_computing_department'):
                add(d['name'], 'missing-pi-review:' + d['reason'])
        # merge keys that are the same person by Name match (e.g. 'Gopala K. Anumanchipalli' / 'Gopala Krishna Anumanchipalli')
        keys = list(U)
        for i, k in enumerate(keys):
            if k not in U:
                continue
            nm = Name([U[k]['name']])
            for k2 in keys[i + 1:]:
                if k2 in U and nm.match(U[k2]['name']) and toks(U[k2]['name'])[-1] == toks(U[k]['name'])[-1]:
                    r2 = U.pop(k2); r = U[k]
                    r['sources'] += r2['sources']; r['aliases'] += [r2['name']] + r2['aliases']
                    r['seed_openalex'] += [x for x in r2['seed_openalex'] if x not in r['seed_openalex']]
                    for kk, v in r2.items():
                        r.setdefault(kk, v)
        for k, r in U.items():
            nm = Name([r['name']] + r['aliases'])
            r['existing_pi'] = next((pi for pi, n_ in pi_nm if any(n_.match(x) for x in [r['name']] + r['aliases'])), None) \
                or next((pi_ids[a] for a in r['seed_openalex'] if a in pi_ids), None)
            r['in_cs_census'] = next((dict(name=cn, rank=rk, is_pi=ip, departments=dp) for cn, n_, rk, ip, dp in cen_nm
                                      if any(n_.match(x) for x in [r['name']] + r['aliases']) and toks(cn)[-1] in ' '.join(toks(r['name'])).split()), None)
            t = toks(r['name'])
            cands = set(by_last.get(t[-1], [])) | set(r['seed_openalex']) if t else set(r['seed_openalex'])
            oa = []
            for aid in cands:
                a = A.get(aid)
                if not a:
                    continue
                if aid in r['seed_openalex'] or any(nm.match(raw) for raw in a['raw']):
                    oa.append(dict(id=aid, n=a['n'], cs=a['cs'], last=a['last'], years=[min(map(int, a['years'])), max(map(int, a['years']))],
                                   raw=list(a['raw'])[:3], orcid=a['orcid'], venues=list(a['venues'])[:3]))
            oa.sort(key=lambda x: -x['n'])
            r['openalex_matches'] = oa
            r['cs_total'] = sum(x['cs'] for x in oa)
        json.dump(list(U.values()), open(Path(out) / f'{s}-universe.json', 'w'), indent=1, ensure_ascii=False)
        print(s, len(U), 'existing PI:', sum(bool(r['existing_pi']) for r in U.values()))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
