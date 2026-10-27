"""Lab papers per school by catalog state: local / queued with untried candidates / queued with none / needs_access_review
/ not in catalog (rowid-chunked, read-only). usage: queued_report.py <school> ..."""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F

for school in sys.argv[1:]:
    papers = F.lab_papers(school)
    cs = F.catalog_state(school, with_urls=False)
    import sqlite3
    db = sqlite3.connect(f'file:{F.FT / school / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
    cands, atts = defaultdict(set), defaultdict(set)
    for w, u in F.chunks(db, 'candidates', 'work_id, url', n=20000):
        cands[w].add(u)
    for w, u in F.chunks(db, 'attempts', 'work_id, url', n=20000):
        atts[w].add(u)
    n = Counter()
    for r in papers.values():
        if F.is_local(school, r, cs):
            n['local'] += 1; continue
        w = F.match_work(school, r, cs)
        if not w:
            n['not_in_catalog'] += 1; continue
        st = cs['status'][w]
        untried = cands[w] - atts[w]
        n[f'{st}:untried' if untried else f'{st}:no_untried'] += 1
        if untried:
            n['untried_host:' + (sorted(untried)[0].split('/')[2] if '//' in sorted(untried)[0] else '?')] += 0
    print(json.dumps(dict(school=school, lab_papers=len(papers), **n)), flush=True)
