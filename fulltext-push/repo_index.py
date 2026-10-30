"""Institutional open-access repositories already indexed by earlier stages, matched to the lab papers still missing
(2026-10-26).

oar   (princeton) Princeton's Open Access Repository, every item page's citation_* tags as crawled by
      ../../claude-princeton-20261015/tools/oar_index.py (cs-structure/raw/oar/items_NNN.json.gz; nothing is fetched
      here): an item whose DOI equals the paper's, or whose normalized title equals it (>= 30 characters) with a year
      within 2 -> the item's citation_pdf_url (oar.princeton.edu/bitstream/...). Imported by lab_channels.py (step oar).
"""
import glob, gzip, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F

OAR = str(F.P.archive_sweep('claude-princeton-20261015') / 'cs-structure/raw/oar/items_*.json.gz')


def step_oar(school, miss, known, n):
    assert school == 'princeton'
    by_doi, by_t = {}, {}
    for f in sorted(glob.glob(OAR)):
        for it in json.loads(gzip.open(f).read()):
            if it.get('status') != 200 or not it.get('pdf'):
                continue
            for d in it.get('dois') or []:
                by_doi.setdefault(F.ndoi(d), it)
            k = F.nt(it.get('title'))
            if len(k) >= 30:
                by_t.setdefault(k, it)
    n['oar_items'] = len(by_t)
    rows = []
    for r, w in miss:
        d = F.ndoi(r.get('doi'))
        it, how = (by_doi[d], 'doi') if d and d in by_doi else (by_t.get(F.nt(r['title'])), 'title')
        if not it:
            continue
        if how == 'title':
            y = (it.get('date') or '')[:4]
            if r.get('year') and y.isdigit() and abs(int(y) - int(r['year'])) > 2:
                continue
        n['oar_matched_' + how] += 1
        for u in it['pdf'][:1]:
            rows.append(dict(work_id=w, url=u, landing_url=it['handle'], version='acceptedVersion', source='princeton_oar',
                             detail=json.dumps(dict(match=how, handle=it['handle'], title=r['title']))))
    return rows
