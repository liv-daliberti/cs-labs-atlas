"""List OpenAlex sweep (hierarchy/mit/openalex-sweep.sqlite, read-only) authorships matching gap PIs' name variants.
-> prints per PI: work id, year, title, author id, orcid, raw name, MIT-affiliated?; and writes sweep_hits.json in this dir."""
import json, re, sqlite3, sys, zlib, collections
sys.path.insert(0, '/n/fs/resemble/cs-atlas/work/tools')
from pi_hierarchy import Name, toks, AFF  # noqa
HERE = '/n/fs/resemble/cs-atlas/work/hierarchy/mit/'
gap = json.load(open(HERE + 'gap-input.json'))
extra = {  # researched byline variants to test (not yet applied by the pipeline)
    'Ted Adelson': ['Edward H. Adelson', 'Edward Adelson', 'E. H. Adelson'],
    'Tim Berners-Lee': ['Timothy Berners-Lee', 'Tim Berners Lee', 'T. Berners-Lee'],
    'Tom Leighton': ['F. Thomson Leighton', 'Frank Thomson Leighton', 'Thomson Leighton', 'F. T. Leighton'],
    'Steve Ward': ['Stephen A. Ward', 'Stephen Ward'],
    'Bill Long': ['William J. Long', 'William Long'],
    'F. J. Corbato': ['Fernando J. Corbato', 'Fernando Corbato', 'Fernando J. Corbató'],
    'Gerald Sussman': ['Gerald Jay Sussman', 'Gerald J. Sussman'],
    'Rodney Brooks': ['Rodney A. Brooks'],
    'Alan Willsky': ['Alan S. Willsky'],
    'Christopher Terman': ['Christopher J. Terman', 'Chris J. Terman'],
    'Judy Brewer': ['Judith Brewer'],
    'Jeffrey Jaffe': ['Jeff Jaffe', 'Jeffrey M. Jaffe'],
    'Michael Goemans': ['Michel X. Goemans', 'Michel Goemans'],
    'Zana Bucinca': ['Zana Buçinca'],
    'Mitchell Gordon': ['Mitchell L. Gordon'],
    'Cheng Zhi (Anna) Huang': ['Cheng-Zhi Anna Huang', 'Cheng-Zhi Huang', 'Anna Huang', 'Cheng Zhi Anna Huang'],
}
want = [r for r in gap if r.get('paper_cause')] if len(sys.argv) < 2 else [r for r in gap if r['pi'] in sys.argv[1:]]
nm = {r['pi']: Name(list(r['names']) + extra.get(r['pi'], [])) for r in want}
aff = re.compile(AFF['mit'], re.I); inst = 'https://openalex.org/I63966007'
out = collections.defaultdict(list)
c = sqlite3.connect(f'file:{HERE}openalex-sweep.sqlite?mode=ro', uri=True)
for (body,) in c.execute('select body from pages order by year, page'):
    for w in json.loads(zlib.decompress(body)):
        for a in w.get('authorships') or []:
            raw = a.get('raw_author_name') or (a.get('author') or {}).get('display_name') or ''
            for pi, n in nm.items():
                if pi == 'Arvind':
                    ok = toks(raw) in (['arvind'], ['arvind', 'mithal'])
                else:
                    ok = n.match(raw)
                if ok:
                    mit = any(inst == i.get('id') or inst in (i.get('lineage') or []) for i in a.get('institutions') or []) or any(aff.search(z) for z in a.get('raw_affiliation_strings') or [])
                    out[pi].append(dict(work=w['id'], doi=w.get('doi'), year=w.get('publication_year'), title=(w.get('title') or '')[:110], type=w.get('type'),
                                        author=(a.get('author') or {}).get('id'), orcid=(a.get('author') or {}).get('orcid'), raw=raw, mit=mit,
                                        affs=(a.get('raw_affiliation_strings') or [])[:2]))
json.dump(out, open('/n/fs/resemble/cs-atlas/work/hierarchy/gap-tools-mit/sweep_hits.json', 'w'), indent=0)
for pi in nm:
    rows = out.get(pi, [])
    print('=====', pi, len(rows), 'mit:', sum(r['mit'] for r in rows), 'authors:', collections.Counter(r['author'] for r in rows if r['mit']).most_common(6))
    for r in rows[:40]:
        print('  ', r['year'], 'MIT' if r['mit'] else '---', r['author'], r['orcid'], '|', r['raw'], '|', r['title'][:80], '|', (r['affs'] or [''])[0][:80])
