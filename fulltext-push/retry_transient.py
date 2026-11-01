"""Requeue transient download failures of lab papers without a copy (2026-10-29).

The collector skips a (work, URL) pair once an attempts row exists for it. The collector wrapper
(claude-cmu-20261017/tools/collector_wrapper.py requeue) already removes, at the start of every pass, attempts that
failed only because a source was paused (source_paused: HTTP 429, 'Repeated access or network failures', 'robots policy
unavailable; retry later', a long crawl delay). This tool does the same - through the same mechanism: delete the attempt
rows, keeping each one in <out>/staged/requeued-attempts.jsonl - for the other transient failures of the missing lab
papers' URLs that are still candidates:
  (never on the publisher hosts in SKIP_HOSTS, which refuse automated clients or serve browser challenges)
  transient  read / connect timeouts, connection reset / aborted / refused, RemoteDisconnected, max retries / name
             resolution errors, HTTP 500 / 502 / 503 / 504, HTTP 429, source_paused, 'robots policy unavailable'
A pair is requeued only when every attempt it has is transient and it has at most 2 of them (a URL that keeps failing is
left alone). Never requeued: robots.txt disallows, 401, 403, 404/410, login / paywall / publisher-host redirects, not a
PDF, identity mismatches - anything else. Deletes run under the catalog's .collector.lock (non-blocking, polled every
10 s), so no pass is running; the next lab pass asks again.
usage: retry_transient.py <school> ... [--dry]
"""
import fcntl, gzip, json, re, sqlite3, sys, time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ftp_common as F

TRANSIENT = re.compile(r'(?:[Tt]imed? ?out|Timeout|Connection reset|Connection aborted|Connection refused|RemoteDisconnected|Max retries exceeded|'
                       r'NameResolutionError|Temporary failure in name resolution|50[0234] Server Error|HTTP 429|429 Client Error|^source_paused|'
                       r'robots policy unavailable|ChunkedEncodingError|IncompleteRead|SSLError|EOF occurred)')
NEVER = re.compile(r'(?:robots\.txt disallows|40[134] Client Error|410 Client Error|outside the evidence-approved|login|paywall|not a PDF|'
                   r'neither a PDF|identity|title differs|mismatch|unambiguous|exceeds)', re.I)


# publisher hosts that refuse automated clients or serve challenges: a timeout there is not retried
SKIP_HOSTS = ('dl.acm.org', 'ieeexplore.ieee.org', 'www.sciencedirect.com', 'onlinelibrary.wiley.com', 'link.springer.com', 'www.tandfonline.com',
              'journals.sagepub.com', 'papers.ssrn.com', 'www.ssrn.com', 'osf.io', 'psyarxiv.com', 'www.researchgate.net')


def missing_works(school):
    p = F.P.FT_LOCAL_REUSE / 'missing.jsonl.gz'
    return {r['work_id'] for l in gzip.open(p, 'rt') if (r := json.loads(l))['school'] == school and r['work_id']}


def run(school, dry):
    out = F.FT / school
    want = missing_works(school)
    db = sqlite3.connect(f'file:{out / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
    cand = set()
    for w, u in F.chunks(db, 'candidates', 'work_id, url', n=20000):
        if w in want:
            cand.add((w, u))
    hist = defaultdict(list)
    cols = [d[0] for d in db.execute('SELECT * FROM attempts LIMIT 0').description]
    for row in F.chunks(db, 'attempts', '*', n=20000):
        r = dict(zip(cols, row))
        if r['work_id'] in want:
            hist[(r['work_id'], r['url'])].append(r)
    st = {}
    for i, s in F.chunks(db, 'works', 'id, status'):
        if i in want:
            st[i] = s
    db.close()
    n, rows = Counter(), []
    for key, atts in hist.items():
        if key not in cand or st.get(key[0]) in F.LOCAL:
            continue
        if re.sub(r'^https?://([^/:]+).*', r'\1', key[1]).lower() in SKIP_HOSTS:
            n['pairs_skipped_publisher_host'] += 1; continue
        kinds = ['transient' if (a['status'] == 'unavailable' and TRANSIENT.search(a['detail'] or '') and not NEVER.search(a['detail'] or '')) else a['status'] for a in atts]
        if all(k == 'transient' for k in kinds):
            if len(atts) <= 2:
                rows += atts; n['pairs_requeued'] += 1
                n['host:' + (re.sub(r'^https?://([^/]+).*', r'\1', key[1]))] += 1
            else:
                n['pairs_left_repeated_transient'] += 1
        elif 'transient' in kinds:
            n['pairs_mixed_left'] += 1
    n['works'] = len({r['work_id'] for r in rows})
    if rows and not dry:
        with (out / '.collector.lock').open('a') as lock:
            while True:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB); break
                except BlockingIOError:
                    time.sleep(10)
            log = out / 'staged' / 'requeued-attempts.jsonl'
            log.parent.mkdir(exist_ok=True)
            with log.open('a') as f:
                for r in rows:
                    f.write(json.dumps(dict(r, requeued_at=datetime.now(timezone.utc).isoformat(), requeued_by='fulltext-push/retry_transient.py')) + '\n')
            w = sqlite3.connect(str(out / 'catalog.sqlite'), timeout=300)
            F.write_batches(w, 'DELETE FROM attempts WHERE id=?', [(r['id'],) for r in rows])
            w.close()
    top = dict(sorted(((k, v) for k, v in n.items() if k.startswith('host:')), key=lambda kv: -kv[1])[:12])
    rec = dict(at=F.now(), school=school, dry=dry, attempts_removed=0 if dry else len(rows), **{k: v for k, v in n.items() if not k.startswith('host:')}, top_hosts=top)
    print(json.dumps(rec), flush=True)
    if not dry:
        with open(F.P.FT_LOGS / 'channels.jsonl', 'a') as f:
            f.write(json.dumps(dict(rec, step='retry_transient')) + '\n')


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    for s in [a for a in sys.argv[1:] if not a.startswith('--')]:
        run(s, dry)
