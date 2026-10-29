"""Candidates for the wider scope: faculty in ANY department who work on CS topics or publish in CS venues.

Owner decision 2026-10-22: "All universities should include all faculty that work on CS-related topics / publish in CS
venues (Even if not in CS)." The census so far covered the computing departments only; this lists the school's other
authors whose output looks like a CS PI's, for review (faculty status, PhD advising or own lab, appointment period).

CS venue  DBLP indexes the work (its DOI, or its title of 30+ normalized characters, is a DBLP record outside CoRR),
          from DBLP's official monthly dump (tools/dblp_dump_index.py). DBLP is the computer-science bibliography, so
          "publishes in CS venues" means "has DBLP-indexed papers". Also written, for reference: the sources where the
          current CS PI lab papers are >= 25% of the five sweeps' school works (hierarchy/cs-venues.json).
author    every OpenAlex author id with an authorship listing the school (institution lineage), 2016-2026, in the school
          sweep (hierarchy/<school>/openalex-sweep.sqlite).
candidate >= 8 school works, >= 5 in CS venues and >= 20% of them in CS venues, last author on >= 30% of them or
          >= 30 school works (students and postdocs are rarely last authors), active in >= 3 distinct years, and not
          already a PI (anchored OpenAlex ids in pis.json, or a name match against the PI's names).
-> hierarchy/<school>/cs-related-candidates.json, hierarchy/cs-venues.json
usage: cs_related_candidates.py [school ...]     (run it as a Slurm job: cs_related_candidates.slurm; it streams, peak a few GB)
"""
import collections, gzip, json, sqlite3, sys, zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pi_hierarchy import Name, HERE  # noqa: E402
from dblp_dump_index import Index  # noqa: E402

import school_config as S  # noqa: E402  (the school charters)
INST = {k: S.inst(k) for k in S.keys()}
SCHOOLS = ['princeton', 'cmu', 'epfl', 'mit', 'berkeley']  # the default run (2026-10-22); name any other school on the command line


def works(school):
    c = sqlite3.connect(f"file:{HERE / 'hierarchy' / school / 'openalex-sweep.sqlite'}?mode=ro", uri=True)
    seen = set()
    for (b,) in c.execute('select body from pages order by year, page'):
        try:
            b = zlib.decompress(b)
        except zlib.error:
            pass
        for w in json.loads(b):
            if w['id'] in seen:
                continue
            seen.add(w['id'])
            yield w


def source_of(w):
    s = (w.get('primary_location') or {}).get('source') or {}
    if not s.get('id') or s.get('type') == 'repository':
        return None, None
    return s['id'], s.get('display_name')


def main(schools):
    lab_oa = set()
    for s in SCHOOLS:
        for line in gzip.open(HERE / 'hierarchy' / s / 'lab_papers.jsonl.gz', 'rt'):
            r = json.loads(line)
            lab_oa.update([r['oa']] + [e['oa'] for e in r.get('editions') or []])
    total, lab, names = collections.Counter(), collections.Counter(), {}
    for s in SCHOOLS:  # streamed: the five sweeps hold ~1M works with full authorships, far too many to keep in memory
        for w in works(s):
            sid, nm = source_of(w)
            if sid:
                total[sid] += 1; names[sid] = nm
                lab[sid] += w['id'] in lab_oa
    cs_venues = {sid for sid in total if lab[sid] >= 5 and lab[sid] / total[sid] >= 0.25}
    json.dump(sorted(({'source': sid, 'name': names[sid], 'lab_papers': lab[sid], 'works': total[sid]} for sid in cs_venues),
                     key=lambda x: -x['lab_papers']), open(HERE / 'hierarchy/cs-venues.json', 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(dict(cs_venues=len(cs_venues), lab_papers_in_cs_venues=sum(lab[s] for s in cs_venues))), flush=True)
    dblp = Index()
    for s in schools:
        inst = 'https://openalex.org/' + INST[s]
        pis = json.load(open(HERE / 'hierarchy' / s / 'pis.json'))
        pi_ids = {a for p in pis for a in (p.get('oaAuthorIds') or []) + (p.get('reviewedOpenAlex') or [])}
        pi_names = [(p['pi'], Name(p.get('names') or [p['pi']])) for p in pis]
        A = collections.defaultdict(lambda: dict(n=0, cs=0, last=0, years=set(), raw=collections.Counter(), venues=collections.Counter(),
                                                 cs_venues=collections.Counter(), works=[]))
        for w in works(s):
            sid, nm = source_of(w)
            in_dblp = dblp.has(doi=w.get('doi'), title=w.get('title'))
            for i, a in enumerate(w.get('authorships') or []):
                if not any(inst in (x.get('lineage') or [x.get('id')]) for x in a.get('institutions') or []):
                    continue
                aid = (a.get('author') or {}).get('id')
                if not aid:
                    continue
                x = A[aid]; x['n'] += 1; x['years'].add(w.get('publication_year'))
                x['last'] += a.get('author_position') == 'last'
                x['raw'][a.get('raw_author_name') or (a.get('author') or {}).get('display_name') or ''] += 1
                if sid:
                    x['venues'][nm] += 1
                if in_dblp:
                    x['cs'] += 1; x['cs_venues'][nm or 'unknown venue'] += 1
                if len(x['works']) < 5 and in_dblp:
                    x['works'].append(dict(oa=w['id'], year=w.get('publication_year'), title=(w.get('title') or '')[:150], venue=nm))
        out = []
        for aid, x in A.items():
            if x['n'] < 8 or x['cs'] < 5 or x['cs'] / x['n'] < 0.20 or len(x['years']) < 3:
                continue
            if x['last'] / x['n'] < 0.30 and x['n'] < 30:
                continue
            name = x['raw'].most_common(1)[0][0]
            if aid in pi_ids:
                continue
            hit = next((pi for pi, nm_ in pi_names if any(nm_.match(r) for r, _ in x['raw'].most_common(3))), None)
            out.append(dict(author=aid, name=name, names=[r for r, _ in x['raw'].most_common(4)], works=x['n'], dblp_works=x['cs'],
                            cs_share=round(x['cs'] / x['n'], 3), last_author_share=round(x['last'] / x['n'], 3),
                            years=[min(y for y in x['years'] if y), max(y for y in x['years'] if y)],
                            top_venues=[v for v, _ in x['venues'].most_common(5)], top_dblp_venues=[v for v, _ in x['cs_venues'].most_common(5)],
                            example_works=x['works'], name_matches_pi=hit))
        out.sort(key=lambda r: (r['name_matches_pi'] is not None, -r['dblp_works']))
        json.dump(out, open(HERE / 'hierarchy' / s / 'cs-related-candidates.json', 'w'), indent=1, ensure_ascii=False)
        print(json.dumps(dict(school=s, authors=len(A), candidates=len(out), name_matches_existing_pi=sum(r['name_matches_pi'] is not None for r in out),
                              new=sum(r['name_matches_pi'] is None for r in out))), flush=True)


if __name__ == '__main__':
    main(sys.argv[1:] or SCHOOLS)
