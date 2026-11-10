"""Warm the persistent copy-quality cache of full-text stores (2026-11-10): the cold scan the download loop needs at its start, without a loop.

For every work the catalog calls downloaded / fulltext_xml, tools/copy_quality.catalog_status() hashes the stored file and runs pdfinfo + pdftotext
(minutes per GB on NFS); with the result cached in <store>/.copy-quality-cache.jsonl a loop restart reads file metadata only. This job fills that file.
Read-only on the catalog (mode=ro, no write lock, no .loop.lock) and on the stored files; the only write is the cache file (O_APPEND lines).
Idempotent and resumable: lines already cached are skipped, so a stopped job continues where it was. A finished store gets <store>/.copy-quality-warm.json.
usage: warm_copy_cache.py <school> [<school> ...]     env WARM_THREADS (default 4)
"""
import json
import sqlite3
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F  # noqa: E402  (puts tools/ on sys.path)

CQ = F.CQ

LOCAL_STATUS = ('downloaded', 'fulltext_xml')


def warm(school, threads=4, store=None, log=print):
    store = Path(store) if store else F.FT / school
    path = store / 'catalog.sqlite'
    t0 = time.time()
    db = sqlite3.connect(f'file:{path}?mode=ro', uri=True, timeout=120)
    rows = [(i, s) for i, _d, s, _t in F.works_rows(db, 'id, doi, status, title') if s in LOCAL_STATUS]
    db.close()
    local = threading.local()
    done, bad = [0], [0]
    lock = threading.Lock()

    def one(row):
        if not hasattr(local, 'db'):
            local.db = sqlite3.connect(f'file:{path}?mode=ro', uri=True, timeout=120)
        s, _ = CQ.catalog_status(local.db, store, row[0], row[1])
        with lock:
            done[0] += 1
            bad[0] += s not in LOCAL_STATUS
            if done[0] % 500 == 0:
                log(json.dumps(dict(school=school, checked=done[0], of=len(rows), seconds=round(time.time() - t0))), flush=True)

    with ThreadPoolExecutor(threads) as ex:
        list(ex.map(one, rows))
    rec = dict(school=school, works=len(rows), unconfirmed=bad[0], seconds=round(time.time() - t0), at=F.now())
    (store / '.copy-quality-warm.json').write_text(json.dumps(rec) + '\n')
    log(json.dumps(rec), flush=True)
    return rec


if __name__ == '__main__':
    import os
    for s in sys.argv[1:]:
        warm(s, int(os.environ.get('WARM_THREADS', '4')))
