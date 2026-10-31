"""Per-author index of one school's OpenAlex sweep (2016-2026), for the CS-related scope review (owner decision 2026-10-22).

For every OpenAlex author id with an authorship whose own institutions (lineage) list the school: school works, works in
CS venues (hierarchy/cs-venues.json; repositories never count), works by year, last-author count, raw names, ORCIDs, top
venues, and the CS-venue works themselves (id, year, venue, title). Streams the sweep; keeps aggregates only.
-> <out>/<school>-authors.json.gz
usage: author_index.py <out_dir> <school> [<school> ...]
"""
import collections, gzip, json, sqlite3, sys, zlib
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
INST = {'princeton': 'I20089843', 'cmu': 'I74973139', 'epfl': 'I5124864', 'mit': 'I63966007', 'berkeley': 'I95457486'}


def works(school):
    c = sqlite3.connect(f"file:{HERE / 'hierarchy' / school / 'openalex-sweep.sqlite'}?mode=ro", uri=True)
    seen = set()
    for (b,) in c.execute('select body from pages order by year, page'):
        try:
            b = zlib.decompress(b)
        except zlib.error:
            pass
        for w in json.loads(b):
            if w['id'] not in seen:
                seen.add(w['id']); yield w


def main(out, schools):
    csv = {v['source']: v['name'] for v in json.load(open(HERE / 'hierarchy/cs-venues.json'))}
    for s in schools:
        inst = 'https://openalex.org/' + INST[s]
        A = collections.defaultdict(lambda: dict(n=0, cs=0, last=0, years=collections.Counter(), cs_years=collections.Counter(),
                                                 raw=collections.Counter(), orcid=set(), venues=collections.Counter(), cs_works=[]))
        for w in works(s):
            src = (w.get('primary_location') or {}).get('source') or {}
            sid = src.get('id') if src.get('type') != 'repository' else None
            for a in w.get('authorships') or []:
                if not any(inst in (x.get('lineage') or [x.get('id')]) for x in a.get('institutions') or []):
                    continue
                aid = (a.get('author') or {}).get('id')
                if not aid:
                    continue
                x = A[aid]; y = w.get('publication_year'); x['n'] += 1; x['years'][y] += 1
                x['last'] += a.get('author_position') == 'last'
                x['raw'][a.get('raw_author_name') or (a.get('author') or {}).get('display_name') or ''] += 1
                if (a.get('author') or {}).get('orcid'):
                    x['orcid'].add(a['author']['orcid'].rsplit('/', 1)[-1])
                if sid:
                    x['venues'][src.get('display_name')] += 1
                    if sid in csv:
                        x['cs'] += 1; x['cs_years'][y] += 1
                        if len(x['cs_works']) < 60:
                            x['cs_works'].append([w['id'], y, csv[sid], (w.get('title') or '')[:160]])
        rows = {aid: dict(n=x['n'], cs=x['cs'], last=x['last'], years=dict(x['years']), cs_years=dict(x['cs_years']),
                          raw=dict(x['raw'].most_common(6)), orcid=sorted(x['orcid']), venues=dict(x['venues'].most_common(6)),
                          cs_works=x['cs_works']) for aid, x in A.items()}
        with gzip.open(Path(out) / f'{s}-authors.json.gz', 'wt') as f:
            json.dump(rows, f, ensure_ascii=False)
        print(json.dumps(dict(school=s, authors=len(rows), with_cs=sum(r['cs'] > 0 for r in rows.values()))), flush=True)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
