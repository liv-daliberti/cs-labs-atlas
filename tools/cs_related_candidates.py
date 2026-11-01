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
works     papers only: a work whose OpenAlex type is not a paper (pi_hierarchy.NOT_PAPERS: datasets, peer reviews, errata,
          ...) counts for no author (learned 2026-10-30: Michigan's 2022 sweep holds 434,618 ENCODE dataset records, DOI
          prefix 10.17989, each with one University of Michigan author).
school    an authorship counts for the school when an institution's lineage holds the school's lineage id, or (a charter's
          `openalex_related` ids, Michigan Medicine) when it is tagged with a related id and one of its raw affiliation
          strings matches the charter's [affiliation].regex (owner decision 2026-10-30).
-> hierarchy/<school>/cs-related-candidates.json (or --out), hierarchy/cs-venues.json (not with --no-venues)
   --stats: also hierarchy/<school>/oa-author-stats.json.gz, every author id with >= 3 school works (n, DBLP-indexed cs,
   last-author count, years, raw names, ORCIDs, venues, example works), for the computing-share test of
   tools/cs_related_school.py share.
usage: cs_related_candidates.py [--no-venues] [--stats] [--out NAME] [school ...]
       (run it as a Slurm job: cs_related_candidates.slurm; it streams, peak a few GB). A protocol school runs with
       --no-venues --stats --out cs-related-candidates-openalex.json: the shared cs-venues.json is the released schools'
       and is left alone, and tools/cs_related_school.py candidates merges the OpenAlex candidates with its own.
"""
import collections, gzip, json, sqlite3, sys, zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pi_hierarchy import Name, NOT_PAPERS  # noqa: E402
import atlas_paths as P  # noqa: E402  (every path in one place)
from dblp_dump_index import Index  # noqa: E402

import school_config as S  # noqa: E402  (the school charters)
INST = {k: S.inst(k) for k in S.keys()}
SCHOOLS = ['princeton', 'cmu', 'epfl', 'mit', 'berkeley']  # the default run (2026-10-22); name any other school on the command line


def works(school):
    c = sqlite3.connect(f"file:{P.data('openalex-sweep.sqlite', school)}?mode=ro", uri=True)
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


def school_test(key):
    """authorship -> True when it lists the school: lineage, or a related id with a raw string matching the regex."""
    lin = {'https://openalex.org/' + i for i in S.inst_ids(key)}
    rel = {'https://openalex.org/' + i for i in S.sweep_ids(key)} - lin
    rx = S.aff_rx(key)

    def ok(a):
        xs = a.get('institutions') or []
        if any(lin & set(x.get('lineage') or [x.get('id')]) for x in xs):
            return True
        return bool(rel) and any(x.get('id') in rel for x in xs) and any(rx.search(r or '') for r in a.get('raw_affiliation_strings') or [])
    return ok


def venues():
    lab_oa = set()
    for s in SCHOOLS:
        for line in gzip.open(P.data('lab_papers.jsonl.gz', s), 'rt'):
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
                     key=lambda x: -x['lab_papers']), open(P.data_w('cs-venues.json'), 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(dict(cs_venues=len(cs_venues), lab_papers_in_cs_venues=sum(lab[s] for s in cs_venues))), flush=True)


def main(schools, do_venues=True, stats=False, out_name='cs-related-candidates.json'):
    if do_venues:
        venues()
    dblp = Index()
    for s in schools:
        at_school = school_test(s); skipped = collections.Counter()
        pis = json.load(open(P.data('pis.json', s)))
        pi_ids = {a for p in pis for a in (p.get('oaAuthorIds') or []) + (p.get('reviewedOpenAlex') or [])}
        pi_names = [(p['pi'], Name(p.get('names') or [p['pi']])) for p in pis]
        A = collections.defaultdict(lambda: dict(n=0, cs=0, last=0, years=set(), raw=collections.Counter(), venues=collections.Counter(),
                                                 cs_venues=collections.Counter(), works=[]))
        for w in works(s):
            if w.get('type') in NOT_PAPERS:
                skipped[w.get('type')] += 1; continue
            sid, nm = source_of(w)
            in_dblp = dblp.has(doi=w.get('doi'), title=w.get('title'))
            for i, a in enumerate(w.get('authorships') or []):
                if not at_school(a):
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
                if stats:
                    o = (a.get('author') or {}).get('orcid')
                    if o:
                        x.setdefault('orcids', collections.Counter())[o.rsplit('/', 1)[-1]] += 1
                    if not in_dblp and len(x.setdefault('other', [])) < 3:
                        x['other'].append(dict(oa=w['id'], year=w.get('publication_year'), title=(w.get('title') or '')[:150], venue=nm))
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
        json.dump(out, open(P.data_w('cs-related-candidates.json', s).parent / out_name, 'w'), indent=1, ensure_ascii=False)
        if stats:
            st = {aid: dict(n=x['n'], cs=x['cs'], last=x['last'], years=sorted(y for y in x['years'] if y), raw=dict(x['raw'].most_common(5)),
                            orcids=dict(x.get('orcids') or {}), venues=dict(x['venues'].most_common(5)), cs_venues=dict(x['cs_venues'].most_common(5)),
                            dblp_examples=x['works'][:3], other_examples=x.get('other') or [])
                  for aid, x in A.items() if x['n'] >= 3}
            with gzip.open(P.data_w('oa-author-stats.json.gz', s), 'wt') as f:
                json.dump(dict(school=s, rule='papers only (not NOT_PAPERS); school authorships (lineage, or related id + regex); authors with >= 3 school works',
                               skipped=dict(skipped), authors=st), f, ensure_ascii=False)
        print(json.dumps(dict(school=s, authors=len(A), candidates=len(out), name_matches_existing_pi=sum(r['name_matches_pi'] is not None for r in out),
                              new=sum(r['name_matches_pi'] is None for r in out), skipped_not_papers=dict(skipped))), flush=True)


if __name__ == '__main__':
    a = sys.argv[1:]
    out_name = a[a.index('--out') + 1] if '--out' in a else 'cs-related-candidates.json'
    if '--out' in a:
        del a[a.index('--out'):a.index('--out') + 2]
    main([x for x in a if not x.startswith('--')] or SCHOOLS, do_venues='--no-venues' not in a, stats='--stats' in a, out_name=out_name)
