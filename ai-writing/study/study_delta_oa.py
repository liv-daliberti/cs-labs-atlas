"""Abstracts and topics for release papers the earlier build never saw (new papers of the 9 schools, and the three partial schools).

reads   the release membership in the snapshot (release/hierarchy/<school>/lab_papers.jsonl.gz), universe/oa_fields.sqlite (already fetched)
writes  <snapshot>/delta/oa_fields_delta.sqlite   works(id, title, year, type, abstract, primary_topic, topics, keywords, fetched)
        Same columns and shapes as the earlier oa_fields.sqlite so the analysis reads both.
Uses tools/oa_api.Client (key never printed; every request logged to the shared budget ledger; stops at the run cap or the shared floor).
Batches of 50 ids per request: about 140 credits for 7,000 papers.
usage: study_delta_oa.py --id 2026-11-07 [--cap 400] [--floor 3000] [--dry-run]
"""
import argparse
import gzip
import json
import sqlite3
import time

import study_common as C


def missing_ids(snap):
    have = set()
    db = sqlite3.connect(f'file:{snap / "universe" / "oa_fields.sqlite"}?mode=ro', uri=True)
    have.update(r[0] for r in db.execute('select id from works'))
    db.close()
    dp = snap / 'delta' / 'oa_fields_delta.sqlite'
    if dp.exists():
        d = sqlite3.connect(dp)
        have.update(r[0] for r in d.execute('select id from works'))
        d.close()
    need = {}
    for s in C.SCHOOLS:
        for line in gzip.open(snap / 'release' / 'hierarchy' / s / 'lab_papers.jsonl.gz', 'rt'):
            r = json.loads(line)
            if not r.get('year') or not C.FIRST <= r['year'] <= C.LAST:
                continue
            w = C.oa_short(r.get('oa'))
            if w and w.startswith('W') and w not in have:
                need[w] = s
    return need


def inverted_text(inv):
    if not inv:
        return None
    pos = sorted((p, w) for w, ps in inv.items() for p in ps)
    return ' '.join(w for _, w in pos) or None


def topic(t):
    return {'id': (t.get('id') or '').rsplit('/', 1)[-1], 'name': t.get('display_name'), 'score': t.get('score'),
            'subfield': (t.get('subfield') or {}).get('display_name'), 'field': (t.get('field') or {}).get('display_name'),
            'domain': (t.get('domain') or {}).get('display_name')}


def fetch(cl, batch, sel):
    """One request for the batch; on an HTTP error the batch is halved (a single bad id is skipped, not fatal)."""
    import oa_api
    try:
        js, _ = cl.get('works', {'filter': 'openalex:' + '|'.join(batch), 'per-page': 50, 'select': sel}, kind='delta', tries=2)
        return (js or {}).get('results', [])
    except oa_api.Spent:
        raise
    except oa_api.OAError:
        if len(batch) == 1:
            print('skipped', batch[0], flush=True)
            return []
        h = len(batch) // 2
        return fetch(cl, batch[:h], sel) + fetch(cl, batch[h:], sel)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', default='2026-11-07')
    ap.add_argument('--cap', type=int, default=400)
    ap.add_argument('--floor', type=int, default=3000)
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    snap = C.snapshot_dir(a.id)
    need = missing_ids(snap)
    by = {}
    for w, s in need.items():
        by[s] = by.get(s, 0) + 1
    print(json.dumps({'missing': len(need), 'by_school': by}))
    if a.dry_run or not need:
        return
    import oa_api
    cl = oa_api.Client(a.cap, kind='study1107-delta', floor=a.floor)
    out = snap / 'delta' / 'oa_fields_delta.sqlite'
    out.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(out)
    db.execute('create table if not exists works (id text primary key, title text, year int, type text, abstract text, primary_topic text, topics text, keywords text, fetched text)')
    import re
    ids = sorted(w for w in need if re.fullmatch(r'W\d+', w))
    sel = 'id,title,publication_year,type,abstract_inverted_index,primary_topic,topics,keywords'
    got = 0
    for i in range(0, len(ids), 50):
        batch = ids[i:i + 50]
        results = fetch(cl, batch, sel)
        rows = []
        for w in results:
            wid = w['id'].rsplit('/', 1)[-1]
            rows.append((wid, w.get('title'), w.get('publication_year'), w.get('type'), inverted_text(w.get('abstract_inverted_index')),
                         json.dumps(topic(w['primary_topic'])) if w.get('primary_topic') else None,
                         json.dumps([topic(t) for t in w.get('topics') or []]), json.dumps([k.get('display_name') for k in w.get('keywords') or []]),
                         time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())))
        db.executemany('insert or replace into works values (?,?,?,?,?,?,?,?,?)', rows)
        db.commit()
        got += len(rows)
    print(json.dumps({'fetched': got, 'credits_used': cl.used, 'remaining': cl.remaining}))


if __name__ == '__main__':
    main()
