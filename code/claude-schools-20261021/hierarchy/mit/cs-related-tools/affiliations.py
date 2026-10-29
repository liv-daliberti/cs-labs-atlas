"""Raw affiliation strings each candidate carries on their MIT works in the school's OpenAlex sweep
(hierarchy/mit/openalex-sweep.sqlite, streamed): the most frequent strings name the unit (Lincoln Laboratory, CSAIL,
a hospital, a department) and help classify people the faculty listings do not show. Also the ORCID on the author record (authorship author.orcid).
usage: affiliations.py <out.json>
"""
import collections, json, sqlite3, sys, zlib
H = '/n/fs/resemble/cs-atlas/work'
cands = {c['author']: c['name'] for c in json.load(open(f'{H}/hierarchy/mit/cs-related-candidates.json'))}
orc = collections.defaultdict(collections.Counter); aff = collections.defaultdict(collections.Counter); yrs = collections.defaultdict(collections.Counter)
con = sqlite3.connect(f'file:{H}/hierarchy/mit/openalex-sweep.sqlite?mode=ro', uri=True)
seen = set()
for (b,) in con.execute('select body from pages order by year, page'):
    try:
        b = zlib.decompress(b)
    except zlib.error:
        pass
    for w in json.loads(b):
        if w['id'] in seen:
            continue
        seen.add(w['id'])
        for a in w.get('authorships') or []:
            aid = (a.get('author') or {}).get('id')
            if aid in cands:
                for s in a.get('raw_affiliation_strings') or []:
                    aff[aid][s[:160]] += 1
                yrs[aid][w.get('publication_year')] += 1
                if (a.get('author') or {}).get('orcid'):
                    orc[aid][a['author']['orcid'].split('/')[-1]] += 1
json.dump({a: dict(name=cands[a], top=aff[a].most_common(6), orcid=orc[a].most_common(3), years=dict(sorted(yrs[a].items()))) for a in cands}, open(sys.argv[1], 'w'), ensure_ascii=False, indent=0)
print('works', len(seen))
