"""The Berkeley full-text catalog for the CS lab papers: data/fulltext/berkeley/catalog.sqlite, in the schema of the
Princeton collector (scripts/collect_princeton_fulltext_expanded.py runs on it unchanged, through the CMU stage's
collector_wrapper.py, as at CMU, EPFL and MIT).

works       one per Berkeley lab paper (hierarchy/berkeley/lab_papers.jsonl.gz, keyed by OpenAlex id): id
            berkeley_oa_<W id>, the OpenAlex title, the paper's DOI (else the arXiv DOI 10.48550/arxiv.<id> when the
            paper has an arXiv version, so the collector's identity check also compares arXiv ids), year.
nodes/edges each paper (kind paper) and each PI's lab (kind lab, hierarchy/berkeley/pis.json unit id and name);
            paper -listed_by-> lab for every PI the lab paper is listed for.
candidates  from the paper's OpenAlex record (hierarchy/berkeley/pi-works.sqlite; ftp_common.oa_location_rows):
              arXiv     the arXiv id of an arXiv location or DOI -> arXiv's bulk copy
                        storage.googleapis.com/arxiv-dataset/arxiv/arxiv/pdf/<yymm>/<id>v<n>.pdf (listing through
                        ../../claude-cmu-20261017/tools/arxiv_bulk.py, cached), never arxiv.org
              PMC       PubMed Central locations -> NLM's PMC open-data copy on S3 (PDF, then JATS XML)
              open PDF  an open location's pdf_url, or a repository's pdf_url / landing page, on a host the
                        collectors may use (not doi.org, arxiv.org, dl.acm.org, openreview.net, aaai.org, IEEE,
                        Elsevier, Wiley, ...: s2_key_lookup.ok_pdf + core_search.usable)
            The collector checks the catalog title (or the arXiv id against an arXiv DOI) in every downloaded file.
Evidence: data/fulltext/berkeley/discovery/claude-berkeley-labpapers/evidence/ (small files: the collector reads one per
attempt). Idempotent: INSERT OR IGNORE everywhere; re-running adds only what is new. Writes commit per batch.
usage: berkeley_catalog.py [--dry]
"""
import json, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F

SCHOOL = 'berkeley'
OUT = F.FT / SCHOOL
DISC = OUT / 'discovery' / 'claude-berkeley-labpapers'
DDL = '''
CREATE TABLE IF NOT EXISTS works (
  id TEXT PRIMARY KEY, title TEXT, doi TEXT, year INTEGER,
  graph_json TEXT NOT NULL, oa_json TEXT, metadata_source TEXT,
  status TEXT NOT NULL DEFAULT 'queued', file_path TEXT,
  sha256 TEXT, byte_count INTEGER, pages INTEGER,
  download_url TEXT, downloaded_at TEXT, identity_check TEXT);
CREATE TABLE IF NOT EXISTS nodes (id TEXT PRIMARY KEY, kind TEXT, name TEXT, record_json TEXT);
CREATE TABLE IF NOT EXISTS edges (id TEXT PRIMARY KEY, source TEXT, target TEXT, kind TEXT, record_json TEXT);
CREATE INDEX IF NOT EXISTS edges_source ON edges(source);
CREATE INDEX IF NOT EXISTS edges_target ON edges(target);
CREATE TABLE IF NOT EXISTS candidates (
  work_id TEXT, url TEXT, landing_url TEXT, license TEXT, version TEXT,
  metadata_source TEXT, PRIMARY KEY(work_id,url));
CREATE TABLE IF NOT EXISTS attempts (
  id INTEGER PRIMARY KEY, work_id TEXT, url TEXT, observed_at TEXT,
  status TEXT, detail TEXT);
CREATE TABLE IF NOT EXISTS receipts (key TEXT PRIMARY KEY, value TEXT);
CREATE INDEX IF NOT EXISTS attempts_work_url ON attempts(work_id,url);
CREATE TABLE IF NOT EXISTS assets (work_id TEXT,kind TEXT,url TEXT,path TEXT,sha256 TEXT,bytes INTEGER,version TEXT,license TEXT,metadata_source TEXT,downloaded_at TEXT,identity_check TEXT,PRIMARY KEY(work_id,kind,url));
'''


def main():
    dry = '--dry' in sys.argv
    papers = F.lab_papers(SCHOOL)
    bodies = F.oa_bodies(SCHOOL, [r['oa'] for r in papers.values()])
    lacking = [r['oa'] for r in papers.values() if r['oa'] not in bodies]
    if lacking and not dry:
        bodies.update(F.fetch_oa_bodies(lacking))
    pis = json.loads((F.P.data('pis.json', SCHOOL)).read_text())
    lab_of = {p['pi']: (p.get('lab') or {}) for p in pis}
    n = Counter(n_papers=len(papers), with_openalex_record=sum(1 for r in papers.values() if r['oa'] in bodies))
    works, nodes, edges, cands, arx, pmc = [], {}, [], [], {}, {}
    for k, r in papers.items():
        b = bodies.get(r['oa'])
        wid = F.oa_work_id(SCHOOL, r)
        a = F.arxiv_of(r, b)
        doi = F.ndoi(r.get('doi')) or (f'10.48550/arxiv.{a}' if a else None)
        node = dict(id=wid, type='paper', name=r['title'], year=r.get('year'), doi=doi, openalex=r['oa'], venue=r.get('venue'),
                    pis=r['pis'], byline_school=r.get('byline_school'), status='berkeley_cs_lab_paper_2016_2026')
        works.append((wid, r['title'], doi, r.get('year'), node))
        nodes[wid] = ('paper', r['title'], node)
        for pi in r['pis']:
            lab = lab_of.get(pi) or {}
            lid = lab.get('unitId') or 'berkeley_pi_' + F.nt(pi)
            nodes.setdefault(lid, ('lab', lab.get('name') or f'{pi} group', dict(id=lid, type='lab', name=lab.get('name') or f'{pi} group', pi=pi,
                                                                                 basis=lab.get('basis'))))
            edges.append((f'{wid}->listed_by->{lid}', wid, lid, 'listed_by', dict(source=wid, target=lid, kind='listed_by', pi=pi,
                                                                                    basis='hierarchy/berkeley/lab_papers.jsonl.gz')))  # route-ok: a label
        if a:
            arx[wid] = a
        rows, p = F.oa_location_rows(wid, b)
        cands += rows
        if p:
            pmc[wid] = p
    n['with_arxiv_id'] = len(arx); n['with_pmc'] = len(pmc); n['works_with_open_location'] = len({c['work_id'] for c in cands})
    print(json.dumps(dict(n)), flush=True)
    if dry:
        return
    for d in (OUT, OUT / 'sources', OUT / 'objects', OUT / 'staged', DISC / 'evidence'):
        d.mkdir(parents=True, exist_ok=True)
    db = F.connect_rw(SCHOOL)
    db.executescript(DDL); db.commit()
    # works: evidence per 100 works (small; a new name per run, so earlier rows keep their own evidence), then INSERT OR IGNORE per batch
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
    graph = dict(source='claude-schools-20261021 Berkeley CS lab papers (hierarchy/berkeley/lab_papers.jsonl.gz)', built_at=F.now(), works=len(works))
    if not db.execute("SELECT 1 FROM receipts WHERE key='graph'").fetchone():
        F.write_batches(db, 'INSERT OR REPLACE INTO receipts VALUES (?,?)', [('graph', json.dumps(graph))])
    F.write_batches(db, 'INSERT OR REPLACE INTO receipts VALUES (?,?)', [('lab_papers:' + F.now()[:10], json.dumps(dict(graph, counts=dict(n))))])
    db.close()
    n['candidates_openalex'] = F.write_candidates(SCHOOL, cands, DISC / 'evidence' / f'openalex-locations-{stamp}.json', __doc__)
    import requests
    s = requests.Session(); s.headers['User-Agent'] = F.UA
    memo, prow = {}, []
    for w, p in pmc.items():
        prow += F.pmc_rows(w, p, memo, s)
    n['candidates_pmc'] = F.write_candidates(SCHOOL, prow, DISC / 'evidence' / f'pmc-open-data-{stamp}.json', __doc__)
    brow, n['arxiv_not_in_bulk'] = F.bulk_rows(arx, 'openalex_arxiv_bulk')
    n['candidates_arxiv_bulk'] = F.write_candidates(SCHOOL, brow, DISC / 'evidence' / f'arxiv-bulk-{stamp}.json', __doc__)
    (DISC / 'summary.json').write_text(json.dumps(dict(created_at=F.now(), counts=dict(n), rule=__doc__), indent=1))
    print(json.dumps(dict(n)), flush=True)


if __name__ == '__main__':
    main()
