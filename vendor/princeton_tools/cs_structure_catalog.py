# Vendored 2026-10-30 from /n/fs/resemble/maxent-grpo/.research-sweeps/claude-princeton-20261015/tools/cs_structure_catalog.py (sha256 307ae8951c0b1fe580e6d6c3d4825c448062953ff29e2e86b1dce1e1568346f7); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Put the Princeton CS structure papers into the full-text catalog (package for the collector).

fetch     OpenAlex single-work records (free lookups) for structure papers the catalog lacks: by W id, else
          DOI. -> cs-structure/raw/works_NNN.json.gz
package   discovery/claude-cs-structure-<date>/ (CS_STRUCTURE_PACKAGE; works already in the catalog are not repeated):
            new-works.jsonl            papers not yet in the catalog (node + OpenAlex record)
            new-work-candidates.jsonl  their open-access locations (pdf_url, or repository landing page)
            associations.jsonl         every paper -> unit assignment (old and new papers): kind `pi` for a
                                       faculty assignment, `member` for a student one; evidence = chunked
                                       files with the byline people and the assignment rule
            labs.json                  the new advising listings, so the export registers them
            work-ids.txt               CS-unit papers, for the collector's priority lists
import    under .collector.lock (tools/import_when_free.py cs_structure_catalog)
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import gzip, hashlib, json, os, sys, time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

STAGE = P.SWEEPS / 'claude-princeton-20261015'  # vendored: the data root (was Path(__file__).resolve().parents[1])
ST = STAGE / 'cs-structure'
FULLTEXT = P.STORES / 'princeton'
PACKAGE = FULLTEXT / 'discovery' / os.environ.get('CS_STRUCTURE_PACKAGE', 'claude-cs-structure-20261017')  # 20261016 was the first, imported
UA = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'
sys.path.insert(0, str(Path(__file__).resolve().parent))
SEL = 'id,doi,title,display_name,publication_year,publication_date,ids,type,primary_location,locations,best_oa_location,authorships,open_access'


def catalog_index():
    from catalog_snapshot import snapshot  # chunked reads: a full-table SELECT once starved the collector's commit
    snap = snapshot()
    return set(snap['status']), snap['doi']


def resolve(p, ids, dois):
    if p['key'].startswith('W:') and 'paper_oa_' + p['key'][2:] in ids:
        return 'paper_oa_' + p['key'][2:]
    return dois.get(p['doi']) if p['doi'] else None


def fetch():
    import requests
    papers = json.loads((ST / 'papers.json').read_text())
    ids, dois = catalog_index()
    raw = ST / 'raw'; raw.mkdir(exist_ok=True)
    have = {}
    for f in raw.glob('works_*.json.gz'):
        have.update(json.loads(gzip.decompress(f.read_bytes())))
    todo = [p for p in papers if (p['labs'] or p['students']) and not resolve(p, ids, dois) and p['key'] not in have and (p['key'].startswith('W:') or p['doi'])]
    print(json.dumps(dict(to_fetch=len(todo), cached=len(have))), flush=True)
    s = requests.Session(); s.headers['User-Agent'] = UA
    batch, n = {}, len(list(raw.glob('works_*.json.gz')))
    for i, p in enumerate(todo):
        url = 'https://api.openalex.org/works/' + (p['key'][2:] if p['key'].startswith('W:') else 'doi:' + p['doi'])
        r = s.get(url, params={'select': SEL, 'api_key': os.environ.get('OPENALEX_API_KEY', '')}, timeout=60)
        time.sleep(0.12)
        batch[p['key']] = r.json() if r.status_code == 200 else dict(http_status=r.status_code)
        if len(batch) >= 500 or i == len(todo) - 1:
            (raw / f'works_{n:03d}.json.gz').write_bytes(gzip.compress(json.dumps(batch).encode())); n += 1; batch = {}
    print(json.dumps(dict(fetched=len(todo))))


def package():
    papers = json.loads((ST / 'papers.json').read_text())
    ids, dois = catalog_index()
    rec = {}
    for f in (ST / 'raw').glob('works_*.json.gz'):
        rec.update(json.loads(gzip.decompress(f.read_bytes())))
    PACKAGE.mkdir(parents=True, exist_ok=True); (PACKAGE / 'evidence').mkdir(exist_ok=True)
    units = json.loads((ST / 'advising_units.json').read_text())
    stamp = datetime.now(timezone.utc).isoformat(timespec='seconds')
    works, cands, assoc, n = [], [], [], Counter()
    chunk, chunk_no = [], 0
    def flush():
        nonlocal chunk, chunk_no
        if chunk:
            p = PACKAGE / 'evidence' / f'structure-{chunk_no:04d}.json'
            p.write_text(json.dumps(dict(rule=sys.modules[__name__].__doc__, created_at=stamp, papers=chunk)))
            chunk_no += 1; chunk = []
        return PACKAGE / 'evidence' / f'structure-{chunk_no:04d}.json'
    for p in papers:
        if not (p['labs'] or p['students']):
            continue
        wid = resolve(p, ids, dois)
        ev = PACKAGE / 'evidence' / f'structure-{chunk_no:04d}.json'
        chunk.append(dict(key=p['key'], doi=p['doi'], year=p['year'], title=p['title'], faculty=p['faculty'], students=p['students'], labs=p['labs']))
        if wid is None:
            w = rec.get(p['key'])
            if not w or 'id' not in w:
                n['no_metadata'] += 1
                if len(chunk) >= 200:
                    flush()
                continue
            wid = 'paper_oa_' + w['id'].rsplit('/', 1)[-1]
            if wid not in ids:
                doi = (w.get('doi') or '').lower().replace('https://doi.org/', '')
                node = dict(id=wid, type='paper', name=w.get('title') or w.get('display_name'), year=w.get('publication_year'), date=w.get('publication_date'),
                            doi=doi, openalex=w['id'], workType=w.get('type'), url=('https://doi.org/' + doi) if doi else w['id'], sourceUrls=[w['id']],
                            status='princeton_cs_structure_work')
                works.append(dict(id=wid, node=node, metadata=w, source=str(ev), rule='princeton_cs_structure_2016_2026'))
                ids.add(wid); n['new_works'] += 1
                for loc in w.get('locations') or []:
                    if not loc.get('is_oa'):
                        continue
                    src = loc.get('source') or {}
                    url = loc.get('pdf_url') or (loc.get('landing_page_url') if src.get('type') == 'repository' else None)
                    if url and 'doi.org' not in url:
                        cands.append(dict(work_id=wid, url=url, landing_url=loc.get('landing_page_url'), license=loc.get('license'),
                                          version=loc.get('version'), metadata_source=str(ev))); n['candidates'] += 1
        for u, a in p['labs'].items():
            assoc.append(dict(work_id=wid, lab_id=u, kind='pi' if a['rule'] == 'faculty' else 'member', person=a.get('who', ''),
                              source_url=('https://openalex.org/' + p['key'][2:]) if p['key'].startswith('W:') else ('https://doi.org/' + p['doi'] if p['doi'] else ''),
                              evidence_path=str(ev), match='princeton_cs_structure_' + a['rule'])); n['associations'] += 1
        if len(chunk) >= 200:
            flush()
    flush()
    for name, rows in (('new-works.jsonl', works), ('new-work-candidates.jsonl', cands), ('associations.jsonl', assoc)):
        with open(PACKAGE / name, 'w') as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
    (PACKAGE / 'labs.json').write_text(json.dumps([dict(id=u['id'], name=u['name'], departments=['Computer Science'], url=u['profile_url'], source=u['profile_url'],
                                                        leaders=[u['leader']], unitType='adviser_group_listing') for u in units], indent=1))
    (PACKAGE / 'work-ids.txt').write_text('\n'.join(dict.fromkeys(a['work_id'] for a in assoc)) + '\n')
    (PACKAGE / 'summary.json').write_text(json.dumps(dict(created_at=stamp, counts=dict(n), rule=__doc__), indent=1))
    print(json.dumps(dict(n)))


def import_catalog():
    import fcntl, sqlite3
    with (FULLTEXT / '.collector.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        db = sqlite3.connect(str(FULLTEXT / 'catalog.sqlite'), timeout=300)
        n = Counter()
        for line in (PACKAGE / 'new-works.jsonl').open():
            r = json.loads(line); node = r['node']
            db.execute('INSERT OR IGNORE INTO nodes VALUES (?,?,?,?)', (r['id'], 'paper', node['name'], json.dumps(node)))
            n['works_added'] += db.execute('INSERT OR IGNORE INTO works(id,title,doi,year,graph_json,oa_json,metadata_source,status) VALUES (?,?,?,?,?,?,?,?)',
                                           (r['id'], node['name'], node['doi'] or None, node['year'], json.dumps(node), json.dumps(r['metadata']), r['source'], 'queued')).rowcount
            db.execute('INSERT OR REPLACE INTO collection_scope VALUES (?,?,?)', (r['id'], r['source'], r['rule']))
        for line in (PACKAGE / 'new-work-candidates.jsonl').open():
            c = json.loads(line)
            n['candidates_added'] += db.execute('INSERT OR IGNORE INTO candidates VALUES (?,?,?,?,?,?)',
                                                tuple(c[k] for k in ['work_id', 'url', 'landing_url', 'license', 'version', 'metadata_source'])).rowcount
        for line in (PACKAGE / 'associations.jsonl').open():
            a = json.loads(line)
            if not db.execute('SELECT 1 FROM works WHERE id=?', (a['work_id'],)).fetchone():
                n['association_work_missing'] += 1; continue
            n['links_added'] += db.execute('INSERT OR IGNORE INTO work_lab_sources VALUES (?,?,?,?,?,?,?)',
                                           (a['work_id'], a['lab_id'], a['kind'], a['person'], a['source_url'], a['evidence_path'], a['match'])).rowcount
        raw = (PACKAGE / 'summary.json').read_bytes()
        db.execute('INSERT OR REPLACE INTO receipts VALUES (?,?)', ('discovery:' + str(PACKAGE), json.dumps(dict(
            path=str(PACKAGE), sha256=hashlib.sha256(raw).hexdigest(), imported_at=datetime.now(timezone.utc).isoformat(), counts=dict(n)))))
        db.commit()
        print(json.dumps(dict(n)))


if __name__ == '__main__':
    {'fetch': fetch, 'package': package, 'import': import_catalog}[sys.argv[1]]()
