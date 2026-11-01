"""The corpus for the AI-written-text study: every CS lab paper of the five schools with its title and abstract.

papers   hierarchy/<school>/lab_papers.jsonl.gz (one row per paper; a paper of two labs keeps both labs) with each lab's
         department from atlas/data/cs-hierarchy/<school>.json.gz
abstract OpenAlex abstract_inverted_index, fetched 50 works per list query (OPENALEX_API_KEY), cached in
         ai-writing/abstracts.sqlite; rebuilt into plain text in word order
-> ai-writing/papers.jsonl.gz  {key, school, oa, doi, title, abstract, year, date, venue, type, labs:[{pi, lab, dept}]}
usage: build_corpus.py fetch | build
"""
import collections, gzip, json, os, sqlite3, sys, time, zlib
from pathlib import Path
import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'tools'))
import atlas_paths as P  # noqa: E402  (every path in one place)
SITE = P.SITE_DATA / 'cs-hierarchy'
SCHOOLS = ('princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford')


def rows():
    for s in SCHOOLS:
        with gzip.open(P.data('lab_papers.jsonl.gz', s), 'rt') as f:
            for line in f:
                r = json.loads(line); r['school'] = s; yield r


def db():
    c = sqlite3.connect(HERE / 'abstracts.sqlite')
    c.execute('create table if not exists abstracts (oa text primary key, inverted blob)')
    return c


def fetch():
    key = os.environ['OPENALEX_API_KEY']; c = db(); s = requests.Session()
    have = {r[0] for r in c.execute('select oa from abstracts')}
    ids = sorted({r['oa'] for r in rows() if (r.get('oa') or '').startswith('https://openalex.org/W')} - have)  # DBLP-recovered rows have no OpenAlex id
    for i in range(0, len(ids), 50):
        batch = '|'.join(x.rsplit('/', 1)[-1] for x in ids[i:i + 50])
        for attempt in range(5):
            try:
                r = s.get('https://api.openalex.org/works', timeout=120, params={'api_key': key, 'filter': f'openalex:{batch}', 'per-page': 50,
                                                                                 'select': 'id,abstract_inverted_index'})
                if r.status_code == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(5 * (attempt + 1))
        else:
            print(json.dumps(dict(failed_at=i))); return
        for w in r.json()['results']:
            c.execute('insert or replace into abstracts values (?,?)', (w['id'], zlib.compress(json.dumps(w.get('abstract_inverted_index')).encode())))
        for x in ids[i:i + 50]:  # works OpenAlex returned nothing for stay recorded as empty
            c.execute('insert or ignore into abstracts values (?,?)', (x, zlib.compress(b'null')))
        c.commit(); time.sleep(0.2)
    print(json.dumps(dict(fetched=len(ids), total=c.execute('select count(*) from abstracts').fetchone()[0])))


def text(inv):
    if not inv:
        return None
    pos = sorted((p, w) for w, ps in inv.items() for p in ps)
    return ' '.join(w for _, w in pos)


def build():
    c = db(); ab = {oa: text(json.loads(zlib.decompress(b))) for oa, b in c.execute('select oa, inverted from abstracts')}
    dept = {}
    for s in SCHOOLS:
        x = json.loads(gzip.decompress((SITE / f'{s}.json.gz').read_bytes())) if (SITE / f'{s}.json.gz').exists() else {'labs': []}
        for l in x['labs']:
            dept[(s, l['pi']['name'])] = (l['name'], l['dept'])
        for q in json.load(open(P.data('pis.json', s))):  # PIs added since the site's last build: their own lab, first department
            dept.setdefault((s, q['pi']), (q['pi'], (q.get('departments') or [None])[0]))
    out = collections.OrderedDict()
    for r in rows():
        k = (r['school'], r['work'] or r['oa'])
        lab, d = dept.get((r['school'], r['pi']), (None, None))
        if k not in out:
            out[k] = dict(key=f'{r["school"]}:{r["work"] or r["oa"]}', school=r['school'], oa=r['oa'], doi=r.get('doi'), title=r.get('title'),
                          abstract=ab.get(r['oa']), year=r.get('year'), date=r.get('date'), venue=r.get('venue'), type=r.get('type'), labs=[])
        out[k]['labs'].append(dict(pi=r['pi'], lab=lab, dept=d))
    with gzip.open(HERE / 'papers.jsonl.gz', 'wt') as f:
        for v in out.values():
            f.write(json.dumps(v, ensure_ascii=False) + '\n')
    n = collections.Counter((v['school'], bool(v['abstract'] and len(v['abstract'].split()) >= 50)) for v in out.values())
    print(json.dumps(dict(papers=len(out), by_school_with_abstract={s: f"{n[(s, True)]}/{n[(s, True)] + n[(s, False)]}" for s in SCHOOLS})))


if __name__ == '__main__':
    {'fetch': fetch, 'build': build}[sys.argv[1]]()
