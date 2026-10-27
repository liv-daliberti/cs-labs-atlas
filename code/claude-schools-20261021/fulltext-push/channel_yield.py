"""Which channel produced each lab paper's local copy since the push began (2026-10-22T04:00Z): the successful attempt's
URL, its candidate row's evidence file (metadata_source), and the evidence path's channel. A lab paper counts once
(its own catalog work, else a catalog work with the same DOI or normalized title). Read-only, rowid-chunked.
-> logs/yield-<school>.json; usage: channel_yield.py <school> ..."""
import json, re, sqlite3, sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F

START = '2026-10-22T04:00'


def channel(src):
    s = src or ''
    m = re.search(r'claude-\w+-labpapers/evidence/([a-z_]+?)-\d', s)
    if m:
        return m.group(1)
    m = re.search(r'claude-berkeley-labpapers/evidence/(openalex-locations|pmc-open-data|arxiv-bulk)', s)
    if m:
        return {'openalex-locations': 'openalex', 'pmc-open-data': 'openalex_pmc', 'arxiv-bulk': 'oa_arxiv'}[m.group(1)]
    m = re.search(r'claude-labpapers-([a-z_]+)-\d', s)
    if m:
        return m.group(1)
    if 'infoscience-rest' in s:
        return 'infoscience (REST; push and earlier runs)'
    if 'claude-berkeley-catalog' in s:
        return 'berkeley DBLP catalog (sibling sweep)'
    return 'candidates that predate the push'


def main():
    for school in sys.argv[1:]:
        papers = F.lab_papers(school)
        db = sqlite3.connect(f'file:{F.FT / school / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
        info, doi_ids, title_ids = {}, defaultdict(list), defaultdict(list)
        for i, d, t, st in F.chunks(db, 'works', 'id, doi, title, status'):
            info[i] = st
            if d:
                doi_ids[F.ndoi(d)].append(i)
            if len(F.nt(t)) >= 20:
                title_ids[F.nt(t)].append(i)
        won, before = {}, set()
        for w, u, at, st in F.chunks(db, 'attempts', 'work_id, url, observed_at, status', n=20000):
            if st in F.LOCAL:
                if (at or '') >= START:
                    won.setdefault(w, u)
                else:
                    before.add(w)
        src = {}
        for w, u, ms in F.chunks(db, 'candidates', 'work_id, url, metadata_source', n=20000):
            if won.get(w) == u:
                src[w] = ms
        db.close()
        n = Counter()
        for r in papers.values():
            group = [x for x in ([r.get('work'), F.oa_work_id(school, r)] + doi_ids.get(F.ndoi(r.get('doi')), []) + title_ids.get(F.nt(r.get('title')), [])) if x and x in info]
            if any(x in before for x in group):
                continue  # already local before the push
            hit = next((x for x in group if x in won and info[x] in F.LOCAL), None)
            if hit:
                n[channel(src.get(hit))] += 1
        out = dict(school=school, since=START, new_local_lab_papers=sum(n.values()), by_channel=dict(n.most_common()))
        (F.HERE / 'logs' / f'yield-{school}.json').write_text(json.dumps(out, indent=1))
        print(json.dumps(out), flush=True)


if __name__ == '__main__':
    main()
