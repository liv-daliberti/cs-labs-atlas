"""Transient failures of the priority papers are asked again (2026-11-03, owner: "getting local every paper we can").

The collector asks a (work, URL) pair once: an attempts row ends it, and only a source pause is cleared at the next pass
(collector_wrapper.requeue). The download loops never passed --retry-transient-after-hours (it would also hold dspace.mit.edu for
24 hours after any 429), so a timeout, a dropped connection or an HTTP 500 from a repository ended the URL for good: 218 of the
2,000 queued link-only papers in release 2026-11-03.2 had nothing but such failures (the ledger's pending_retry).
requeue_transient() removes those attempt rows (each kept in <store>/staged/requeued-attempts.jsonl, as every requeue) for the
given work ids, when
  - every row of the pair is a transient failure (retry_transient.TRANSIENT, never retry_transient.NEVER: robots.txt, 401/403/404,
    login, not a PDF, identity), the newest at least OLDER_HOURS old, and the host is not one of retry_transient.SKIP_HOSTS
    (publishers that refuse automated clients);
  - the pair was requeued fewer than MAX_RETRIES times (staged/transient-retries.json), so a URL that keeps failing is left alone.
robots.txt, pacing, paused hosts and the title check are the collector's, unchanged. lab_first_loop calls it before each priority phase.
"""
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

import ftp_common as F
from retry_transient import NEVER, SKIP_HOSTS, TRANSIENT

OLDER_HOURS = 6.0
MAX_RETRIES = 2
COUNTS = 'transient-retries.json'


def _transient(a):
    d = a['detail'] or ''
    return a['status'] == 'unavailable' and bool(TRANSIENT.search(d)) and not NEVER.search(d) and not d.startswith('source_paused')


def requeue_transient(school, work_ids, older_than_hours=OLDER_HOURS, max_retries=MAX_RETRIES, dry=False, now=None, store=None):
    """-> number of attempt rows removed (or, dry, that would be)."""
    out = Path(store) if store else F.FT / school
    ids = list(dict.fromkeys(work_ids))
    if not ids:
        return 0
    now = now or datetime.now(timezone.utc)
    cutoff = (now - timedelta(hours=older_than_hours)).isoformat()
    db = sqlite3.connect(f'file:{out / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
    db.row_factory = sqlite3.Row
    pairs = {}
    for i in range(0, len(ids), 400):
        part = ids[i:i + 400]
        q = ','.join('?' * len(part))
        for a in db.execute(f"SELECT a.* FROM attempts a JOIN works w ON w.id=a.work_id WHERE a.work_id IN ({q}) "
                            f"AND w.status NOT IN ('downloaded','fulltext_xml','quarantined_robots_ai')", part):
            pairs.setdefault((a['work_id'], a['url']), []).append(dict(a))
    db.close()
    cp = out / 'staged' / COUNTS
    try:
        counts = json.loads(cp.read_text())
    except (OSError, ValueError):
        counts = {}
    rows = []
    for (w, u), atts in pairs.items():
        if (urlsplit(u).hostname or '').lower() in SKIP_HOSTS or not all(_transient(a) for a in atts):
            continue
        if max(a['observed_at'] for a in atts) > cutoff or counts.get(f'{w}\t{u}', 0) >= max_retries:
            continue
        rows += atts
    if dry or not rows:
        return len(rows)
    log = out / 'staged' / 'requeued-attempts.jsonl'
    log.parent.mkdir(exist_ok=True)
    stamp = now.isoformat()
    with log.open('a') as f:
        for r in rows:
            f.write(json.dumps(dict(r, requeued_at=stamp, requeued_by='fulltext-push/priority_retry.py')) + '\n')
    counts = {}
    try:
        counts = json.loads(cp.read_text())
    except (OSError, ValueError):
        pass
    for k in {f"{r['work_id']}\t{r['url']}" for r in rows}:
        counts[k] = counts.get(k, 0) + 1
    cp.write_text(json.dumps(counts))
    w = sqlite3.connect(str(out / 'catalog.sqlite'), timeout=300)
    F.write_batches(w, 'DELETE FROM attempts WHERE id=?', [(r['id'],) for r in rows])
    w.close()
    return len(rows)
