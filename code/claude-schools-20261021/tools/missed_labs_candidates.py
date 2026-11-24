"""Missed-labs candidates from the local OpenAlex snapshot (coordinator brief 2026-11-09, source 2).

Authors with an authorship at the school (institution lineage, charter ids) on a paper of 2016-2025 and at least MINCS
DBLP-indexed papers (the CS test of tools/cs_related_candidates.py: DOI or 30+ character title in DBLP's dump), who are not
in the census (pis.json names/ids, census-faculty.json rows, census-additions), not matched as student / member
(students.json names), ranked by CS paper count and recency. Reads the snapshot read-only; no API credits.
-> <out>/<school>-oa-candidates.json  [{id, names, n, cs, last, first_year, last_year, years, orcid, last_known, depts, venues, examples}]
usage: missed_labs_candidates.py <out_dir> <school> ...
"""
import collections, json, re, sqlite3, sys, unicodedata, zlib
from pathlib import Path

import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
from pi_hierarchy import Name, NOT_PAPERS  # noqa: E402
from dblp_dump_index import Index  # noqa: E402

MINCS = 5
Y0, Y1 = 2016, 2025


def nkey(n):
    n = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode()
    t = re.sub(r'[^a-z ]', '', re.sub(r'\s+', ' ', n.lower().replace('-', ' '))).split()
    return (t[0], t[-1]) if len(t) >= 2 else None


def known(school):
    ids, keys, names = set(), set(), []
    pis = json.load(open(P.data('pis.json', school)))
    for p in pis:
        ids.update(p.get('oaAuthorIds') or []); ids.update(p.get('reviewedOpenAlex') or [])
        names.append(Name(p.get('names') or [p['pi']]))
        for n in [p['pi']] + list(p.get('names') or []):
            if nkey(n): keys.add(nkey(n))
    cen = json.load(open(P.data('census-faculty.json', school)))
    for x in cen.get('faculty', cen) if isinstance(cen, dict) else cen:
        ids.update(x.get('openalex') or [])
        for n in [x['name']] + list(x.get('aliases') or []):
            if nkey(n): keys.add(nkey(n))
    st = json.load(open(P.data('students.json', school)))
    skeys = set()
    for lst in st.values():
        for s in lst:
            for n in [s.get('name')] + list(s.get('aliases') or []):
                if n and nkey(n): skeys.add(nkey(n))
    return ids, keys, skeys


def main(out, schools):
    dblp = Index()
    db = P.OA_SNAPSHOT / 'current' / 'openalex.sqlite'
    c = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    for school in schools:
        ids, keys, skeys = known(school)
        lins = ['I' + i.lstrip('I') for i in S.inst_ids(school)]
        lin = {'https://openalex.org/' + i for i in S.inst_ids(school)}
        A = collections.defaultdict(lambda: dict(n=0, cs=0, last=0, years=set(), raw=collections.Counter(), orcid=None, venues=collections.Counter(), ex=[], aff=collections.Counter()))
        seen = set()
        for inst in lins:
            for (wid, b) in c.execute('select w.id, w.body from works w join work_inst i on i.work_id=w.id where i.inst=? and w.year between ? and ?', (inst, Y0, Y1)):
                if wid in seen:
                    continue
                seen.add(wid)
                w = json.loads(zlib.decompress(b))
                if w.get('type') in NOT_PAPERS:
                    continue
                is_cs = dblp.has(doi=w.get('doi'), title=w.get('title'))
                src = ((w.get('primary_location') or {}).get('source') or {}).get('display_name')
                for a in w.get('authorships') or []:
                    if not any(lin & set(i.get('lineage') or []) for i in a.get('institutions') or []):
                        continue
                    au = a.get('author') or {}
                    if not au.get('id'):
                        continue
                    x = A[au['id']]
                    x['n'] += 1; x['cs'] += bool(is_cs); x['last'] += a.get('author_position') == 'last'; x['years'].add(w.get('publication_year'))
                    x['raw'][au.get('display_name') or ''] += 1; x['orcid'] = x['orcid'] or au.get('orcid')
                    for r in (a.get('raw_affiliation_strings') or [])[:1]:
                        x['aff'][r[:100]] += 1
                    if is_cs:
                        if src: x['venues'][src] += 1
                        if len(x['ex']) < 3: x['ex'].append(dict(id=wid, year=w.get('publication_year'), title=(w.get('title') or '')[:110]))
        out_rows, skipped = [], collections.Counter()
        for aid, x in A.items():
            if x['cs'] < MINCS:
                continue
            nm = x['raw'].most_common(1)[0][0]
            if aid in ids:
                skipped['id_in_census'] += 1; continue
            ks = {nkey(n) for n in x['raw']} - {None}
            if ks & keys:
                skipped['name_in_census'] += 1; continue
            if ks & skeys:
                skipped['name_is_student_or_member'] += 1; continue
            out_rows.append(dict(id=aid, name=nm, names=[n for n, _ in x['raw'].most_common(4)], n=x['n'], cs=x['cs'], last=x['last'], first_year=min(x['years']),
                                 last_year=max(x['years']), years=len(x['years']), orcid=x['orcid'], aff=[a for a, _ in x['aff'].most_common(2)],
                                 venues=[v for v, _ in x['venues'].most_common(3)], examples=x['ex']))
        out_rows.sort(key=lambda r: (-r['cs'], -r['last_year']))
        Path(out, f'{school}-oa-candidates.json').write_text(json.dumps(out_rows, indent=1, ensure_ascii=False))
        print(json.dumps(dict(school=school, works=len(seen), authors=len(A), with_cs=sum(x['cs'] >= MINCS for x in A.values()), candidates=len(out_rows), skipped=dict(skipped))), flush=True)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
