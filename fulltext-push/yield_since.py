"""Copies gained by the lab papers since a moment, by channel (2026-10-29), read-only and rowid-chunked.

For each school: the catalog works of its current lab papers (ftp_common.match_work) whose copy was recorded after
--since (attempts rows with status downloaded / fulltext_xml); each is credited to the channel of the URL that
succeeded: the candidate's evidence path names the lab_channels step (discovery/claude-<school>-labpapers/evidence/
<step>-<stamp>-NNNN.json, or Princeton's discovery/claude-labpapers-<step>-<stamp>/), a file:// URL is local reuse
(origin cross_catalog / disk from the attempt detail), a (work, URL) pair in <out>/staged/requeued-attempts.jsonl
requeued by retry_transient.py is 'retry_transient'; anything else is 'earlier candidates'.
Also: candidates added since --since per step (the evidence path's stamp).
usage: yield_since.py <ISO UTC time> <school> ...
"""
import json, re, sqlite3, sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F

STEP = re.compile(r'(?:claude-labpapers-|/evidence/)([a-z0-9_]+?)-(\d{12,14})')


def run(school, since):
    papers = F.lab_papers(school)
    cs = F.catalog_state(school, with_urls=False)
    lab = {w for r in papers.values() if (w := F.match_work(school, r, cs))}
    out = F.FT / school
    db = sqlite3.connect(f'file:{out / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
    got = {}
    for w, u, t, st, det in F.chunks(db, 'attempts', 'work_id, url, observed_at, status, detail', n=20000):
        if w in lab and st in F.LOCAL and (t or '') >= since:
            got[(w, u)] = det
    ev, added = {}, Counter()
    stamp_since = re.sub(r'\D', '', since)[:12]
    for w, u, ms in F.chunks(db, 'candidates', 'work_id, url, metadata_source', n=20000):
        if (w, u) in got:
            ev[(w, u)] = ms or ''
        m = STEP.search(ms or '')
        if m and m.group(2)[:12] >= stamp_since and w in lab:
            added[m.group(1)] += 1
    db.close()
    requeued = set()
    log = out / 'staged' / 'requeued-attempts.jsonl'
    if log.exists():
        for line in log.open():
            if 'retry_transient' in line:
                r = json.loads(line); requeued.add((r['work_id'], r['url']))
    gained = Counter()
    works = defaultdict(set)
    for (w, u), det in got.items():
        if u.startswith('file://'):
            try:
                lab_ = 'local_reuse:' + json.loads(det)['local_reuse']['origin']
            except Exception:
                lab_ = 'local_reuse'
        elif (w, u) in requeued:
            lab_ = 'retry_transient'
        else:
            m = STEP.search(ev.get((w, u), ''))
            lab_ = m.group(1) if m and m.group(2)[:12] >= stamp_since else 'earlier candidates'
        works[lab_].add(w)
    gained = {k: len(v) for k, v in sorted(works.items(), key=lambda kv: -len(kv[1]))}
    print(json.dumps(dict(school=school, since=since, lab_works_gaining_copy=len({w for w, _ in got}), by_channel=gained, candidates_added_since=dict(added))), flush=True)


if __name__ == '__main__':
    for s in sys.argv[2:]:
        run(s, sys.argv[1])
