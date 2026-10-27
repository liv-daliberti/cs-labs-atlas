"""One-off repair (2026-10-22): berkeley_catalog.py's first three runs reused evidence file names, so a later run
rewrote works-NNNN.json / openalex-locations-NNNN.json / pmc-open-data-NNNN.json / arxiv-bulk-NNNN.json with other rows.
Each unstamped evidence file under discovery/claude-berkeley-labpapers/evidence/ is rewritten (atomically) to list
exactly the catalog rows that cite it: candidates (work, url, landing, version) or works (their graph node).
Read-only chunked catalog reads; the files are replaced via a temporary name, so a collector reading one never sees a
partial file."""
import json, re, sqlite3, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F

EV = F.FT / 'berkeley' / 'discovery' / 'claude-berkeley-labpapers' / 'evidence'
UNSTAMPED = re.compile(r'^(works|openalex-locations|pmc-open-data|arxiv-bulk)-\d{4}\.json$')
db = sqlite3.connect(f"file:{F.FT / 'berkeley' / 'catalog.sqlite'}?mode=ro", uri=True, timeout=120)
cands, works = defaultdict(list), defaultdict(list)
for w, u, land, ver, src in F.chunks(db, 'candidates', 'work_id, url, landing_url, version, metadata_source', n=20000):
    if src and UNSTAMPED.match(Path(src).name) and Path(src).parent == EV:
        cands[src].append(dict(work_id=w, url=u, landing_url=land, version=ver))
for w, g, src in F.chunks(db, 'works', 'id, graph_json, metadata_source', n=5000):
    if src and UNSTAMPED.match(Path(src).name) and Path(src).parent == EV:
        works[src].append(json.loads(g))
db.close()
kind = {'openalex-locations': 'openalex_location', 'pmc-open-data': 'pmc_open_data', 'arxiv-bulk': 'openalex_arxiv_bulk'}
import berkeley_catalog as B
n = 0
for f in sorted(EV.glob('*.json')):
    if not UNSTAMPED.match(f.name):
        continue
    src = str(f)
    stem = f.name.rsplit('-', 1)[0]
    body = dict(rule=B.__doc__, repaired_at=F.now(), repair_note=__doc__)
    if stem == 'works':
        body['works'] = works.get(src, [])
    else:
        body['rows'] = [dict(r, source=kind[stem]) for r in cands.get(src, [])]
    tmp = f.with_suffix('.tmp'); tmp.write_text(json.dumps(body, ensure_ascii=False)); tmp.replace(f); n += 1
print(json.dumps(dict(files_rewritten=n, candidate_files=len(cands), candidate_rows=sum(map(len, cands.values())),
                      work_files=len(works), work_rows=sum(map(len, works.values())))))
