"""The Stanford full-text catalog for the CS lab papers (2026-10-27): data/fulltext/stanford/catalog.sqlite, in the schema
of the Princeton collector (scripts/collect_princeton_fulltext_expanded.py runs on it unchanged, through the CMU stage's
collector_wrapper.py, as at CMU, EPFL, MIT and Berkeley). Modelled on berkeley_catalog.py.

storage     data/fulltext/stanford is a symlink to /n/fs/resemble/homogenizing-science/stores/stanford (new downloads go to
            resemble; the homogenizing-science tree's migration keeps the symlink). Every path the collector stores is
            relative to that directory (objects/<sha256>.pdf), as at the other schools.
works       one per Stanford lab paper (hierarchy/stanford/lab_papers.jsonl.gz, keyed by OpenAlex id, else the DBLP record
            or lab-page key the hierarchy gives): id stanford_oa_<W id / key tail>, the hierarchy's title, the paper's DOI
            (else the arXiv DOI 10.48550/arxiv.<id> when its OpenAlex record has an arXiv location, so the collector's
            identity check also compares arXiv ids), year.
nodes/edges each paper (kind paper) and each PI's lab (kind lab: hierarchy/stanford/pis.json lab name, id
            stanford_pi_<normalized PI name> since Stanford's labs carry no unit id); paper -listed_by-> lab for every PI
            the lab paper is listed for.
OpenAlex    hierarchy/stanford has no pi-works.sqlite (its sweep pages hold no locations), so the lab papers' OpenAlex
records     records (id, doi, title, publication_year, ids, locations, primary_location) are fetched here, 100 ids per
            request of api.openalex.org/works?filter=ids.openalex:...  (key from ~/.config/cs-atlas/openalex.env, never
            printed), into fulltext-push/raw/stanford-oa-works.sqlite (works: id, zlib JSON body), which
            ftp_common.oa_bodies reads for a school without pi-works.sqlite.
candidates  come from lab_channels.py through run_steps.sh (the single channel runner, so one arXiv-bulk user at a time):
            oa_arxiv and openalex build exactly berkeley_catalog.py's three kinds from these records (ftp_common
            bulk_rows / oa_location_rows / pmc_rows: arXiv's bulk copy on GCS, never arxiv.org; NLM's PMC open-data copy
            on S3; open pdf_urls and repository pages on hosts the collectors may use), then the other channels.
Evidence: data/fulltext/stanford/discovery/claude-stanford-labpapers/evidence/ (small files: the collector reads one per
attempt). Idempotent: INSERT OR IGNORE everywhere; re-running adds only what is new. Writes commit per batch.
usage: stanford_catalog.py [--dry]
"""
import json, os, sqlite3, sys, time, zlib
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F
from berkeley_catalog import DDL

SCHOOL = 'stanford'
OUT = F.FT / SCHOOL
DISC = OUT / 'discovery' / 'claude-stanford-labpapers'
SELECT = 'id,doi,title,publication_year,ids,locations,primary_location'


def fetch_records(oa_ids):
    """OpenAlex records for the W ids not yet in raw/stanford-oa-works.sqlite, 100 per request (0.25 s apart)."""
    import requests
    store = F.oa_store(SCHOOL)
    assert store.parent == F.HERE / 'raw', store
    db = sqlite3.connect(str(store), timeout=60)
    db.execute('CREATE TABLE IF NOT EXISTS works (id TEXT PRIMARY KEY, body BLOB)')
    db.execute('CREATE TABLE IF NOT EXISTS fetches (at TEXT, asked INT, got INT, status INT)')
    have = {i for (i,) in db.execute('SELECT id FROM works')}
    todo = [i for i in dict.fromkeys(oa_ids) if i.startswith('https://openalex.org/W') and i not in have]
    F.load_env()
    key = os.environ.get('OPENALEX_API_KEY')
    s = requests.Session(); s.headers['User-Agent'] = F.UA
    got = 0
    for k in range(0, len(todo), 100):
        part = todo[k:k + 100]
        params = {'filter': 'ids.openalex:' + '|'.join(F.oa_short(i) for i in part), 'per_page': 100, 'select': SELECT}
        if key:
            params['api_key'] = key
        res, status = None, None
        for attempt in range(5):
            time.sleep(0.25)
            try:
                r = s.get('https://api.openalex.org/works', params=params, timeout=(15, 120))
            except Exception:
                time.sleep(20); continue
            status = r.status_code
            if status == 200:
                res = r.json().get('results') or []; break
            time.sleep(60 if status == 429 else 15)
        rows = [(w['id'], zlib.compress(json.dumps(w).encode())) for w in res or [] if w.get('id')]
        db.executemany('INSERT OR REPLACE INTO works VALUES (?,?)', rows)
        db.execute('INSERT INTO fetches VALUES (?,?,?,?)', (F.now(), len(part), len(rows), status))
        db.commit(); got += len(rows)
        if (k // 100) % 20 == 19:
            print(json.dumps(dict(openalex_asked=k + len(part), of=len(todo), got=got)), flush=True)
    db.close()
    return dict(openalex_records_had=len(have), openalex_asked=len(todo), openalex_got=got)


def main():
    dry = '--dry' in sys.argv
    papers = F.lab_papers(SCHOOL)
    n = Counter(n_papers=len(papers))
    if not dry:
        n.update(fetch_records([r['oa'] for r in papers.values()]))
    bodies = F.oa_bodies(SCHOOL, [r['oa'] for r in papers.values()])
    pis = json.loads((F.SCHOOLS / 'hierarchy' / SCHOOL / 'pis.json').read_text())
    lab_of = {p['pi']: (p.get('lab') or {}) for p in pis}
    n['with_openalex_record'] = sum(1 for r in papers.values() if r['oa'] in bodies)
    works, nodes, edges, ids = [], {}, [], Counter()
    for k, r in papers.items():
        b = bodies.get(r['oa'])
        wid = F.oa_work_id(SCHOOL, r)
        ids[wid] += 1
        a = F.arxiv_of(r, b)
        doi = F.ndoi(r.get('doi')) or (f'10.48550/arxiv.{a}' if a else None)
        node = dict(id=wid, type='paper', name=r['title'], year=r.get('year'), doi=doi, openalex=r['oa'], venue=r.get('venue'),
                    pis=r['pis'], byline_school=r.get('byline_school'), status='stanford_cs_lab_paper_2016_2026')
        works.append((wid, r['title'], doi, r.get('year'), node))
        nodes[wid] = ('paper', r['title'], node)
        for pi in r['pis']:
            lab = lab_of.get(pi) or {}
            lid = lab.get('unitId') or 'stanford_pi_' + F.nt(pi)
            nodes.setdefault(lid, ('lab', lab.get('name') or f'{pi} group', dict(id=lid, type='lab', name=lab.get('name') or f'{pi} group', pi=pi,
                                                                                 basis=lab.get('basis'), url=lab.get('url'))))
            edges.append((f'{wid}->listed_by->{lid}', wid, lid, 'listed_by', dict(source=wid, target=lid, kind='listed_by', pi=pi,
                                                                                    basis='hierarchy/stanford/lab_papers.jsonl.gz')))
        n['with_arxiv_id'] += bool(a)
    n['work_id_collisions'] = sum(1 for v in ids.values() if v > 1)
    print(json.dumps(dict(n)), flush=True)
    if dry:
        return
    for d in (OUT, OUT / 'sources', OUT / 'objects', OUT / 'staged', DISC / 'evidence'):
        d.mkdir(parents=True, exist_ok=True)
    db = F.connect_rw(SCHOOL)
    db.executescript(DDL); db.commit()
    stamp = F.now()[:19].replace('-', '').replace(':', '')
    wrows = []
    for i in range(0, len(works), 100):
        part = works[i:i + 100]
        ev = DISC / 'evidence' / f'works-{stamp}-{i // 100:04d}.json'
        ev.write_text(json.dumps(dict(rule=__doc__, created_at=F.now(), works=[w[4] for w in part]), ensure_ascii=False))
        wrows += [(w[0], w[1], w[2], w[3], json.dumps(w[4], ensure_ascii=False), str(ev), 'queued') for w in part]
    n['works_added'] = F.write_batches(db, 'INSERT OR IGNORE INTO works(id,title,doi,year,graph_json,metadata_source,status) VALUES (?,?,?,?,?,?,?)', wrows)
    n['nodes_added'] = F.write_batches(db, 'INSERT OR IGNORE INTO nodes VALUES (?,?,?,?)',
                                       [(i, kind, name, json.dumps(rec, ensure_ascii=False)) for i, (kind, name, rec) in nodes.items()])
    n['edges_added'] = F.write_batches(db, 'INSERT OR IGNORE INTO edges VALUES (?,?,?,?,?)',
                                       [(e[0], e[1], e[2], e[3], json.dumps(e[4], ensure_ascii=False)) for e in edges])
    graph = dict(source='claude-schools-20261021 Stanford CS lab papers (hierarchy/stanford/lab_papers.jsonl.gz)', built_at=F.now(), works=len(works),
                 storage=f'{F.P.STANFORD_STORE} (symlinked from homogenizing-science/data/fulltext/stanford)')
    if not db.execute("SELECT 1 FROM receipts WHERE key='graph'").fetchone():
        F.write_batches(db, 'INSERT OR REPLACE INTO receipts VALUES (?,?)', [('graph', json.dumps(graph))])
    F.write_batches(db, 'INSERT OR REPLACE INTO receipts VALUES (?,?)', [('lab_papers:' + F.now()[:10], json.dumps(dict(graph, counts=dict(n))))])
    db.close()
    (DISC / 'summary.json').write_text(json.dumps(dict(created_at=F.now(), counts=dict(n), rule=__doc__), indent=1))
    print(json.dumps(dict(n)), flush=True)


if __name__ == '__main__':
    main()
