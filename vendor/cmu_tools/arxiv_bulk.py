# Vendored 2026-10-30 from /n/fs/resemble/maxent-grpo/.research-sweeps/claude-cmu-20261017/tools/arxiv_bulk.py (sha256 fa8780a55bad940801701887327ea7edafdb45cf2a0ac580c9e275060a46a261); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""arXiv PDFs from arXiv's official bulk-access copy instead of arxiv.org.

arXiv publishes its full PDF set in a public Google Cloud Storage bucket (gs://arxiv-dataset, the Cornell/Kaggle
"arXiv Dataset", updated continuously; checked 2026-10-18: files from 2026-01 present). Downloading from it does not
touch arxiv.org, whose robots.txt asks for 15 s between requests; the bucket host (storage.googleapis.com) has no
robots.txt rule. For each work without a local copy that has an arXiv id, the bucket's object listing
(storage/v1/b/arxiv-dataset/o?prefix=arxiv/arxiv/pdf/<yymm>/<id>; four in parallel, about 4 listings per second) gives the versions;
the latest one becomes a candidate https://storage.googleapis.com/arxiv-dataset/arxiv/arxiv/pdf/<yymm>/<id>v<n>.pdf
(the collector's identity check — title in the PDF, or the arXiv id against an arXiv DOI — still applies).

cmu        in-scope CMU works (people/scope.json) with a staged arXiv candidate -> straight into
           data/fulltext/cmu/catalog.sqlite (its own catalog)
princeton  Princeton catalog works not downloaded whose candidates or attempts include an arxiv.org URL (read through
           ../claude-princeton-20261015/tools/catalog_snapshot.py) -> package
           data/fulltext/princeton/discovery/claude-arxiv-bulk-<date>/ (cs_open_copies format) for the usual import
Listings are cached in raw/arxiv_bulk_listing.jsonl (resumable).
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import json, re, sqlite3, sys, time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

STAGE = P.SWEEPS / 'claude-cmu-20261017'  # vendored: the data root (was Path(__file__).resolve().parents[1])
CMU = P.STORES / 'cmu'
PRIN = P.STORES / 'princeton'
CACHE = STAGE / 'raw' / 'arxiv_bulk_listing.jsonl'
API = 'https://storage.googleapis.com/storage/v1/b/arxiv-dataset/o'
UA = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'
NEW_ID = re.compile(r'^(\d{4})\.(\d{4,5})$')


def arxiv_id(url):
    m = re.search(r'arxiv\.org/(?:abs|pdf)/([^?#]+?)(?:v\d+)?(?:\.pdf)?/?$', url or '')
    return m.group(1) if m else None


def _list_one(s, i):
    yymm = i.split('.')[0]
    for attempt in range(4):
        try:
            r = s.get(API, params={'prefix': f'arxiv/arxiv/pdf/{yymm}/{i}v', 'fields': 'items(name)'}, timeout=60)
            if r.status_code == 200:
                names = [x['name'] for x in r.json().get('items') or [] if re.search(re.escape(i) + r'v\d+\.pdf$', x['name'])]
                if not names:
                    return None
                return 'https://storage.googleapis.com/arxiv-dataset/' + max(names, key=lambda n: int(re.search(r'v(\d+)\.pdf$', n).group(1)))
            if r.status_code in (429, 500, 502, 503):
                time.sleep(30 * (attempt + 1)); continue
            return None
        except Exception:
            time.sleep(10)
    return None


def listing(ids, workers=4):
    """{arxiv id: latest bulk PDF URL or None}; cached; a few listings in parallel (about 4 per second)."""
    import requests, threading
    from concurrent.futures import ThreadPoolExecutor
    cached = {}
    if CACHE.exists():
        for line in CACHE.open():
            try:  # two processes may append at once; a garbled line is relisted
                r = json.loads(line); cached[r['id']] = r['url']
            except (ValueError, KeyError):
                pass
    todo = [i for i in dict.fromkeys(ids) if i not in cached and NEW_ID.match(i)]
    print(json.dumps(dict(ids=len(set(ids)), cached=len(cached), to_list=len(todo))), flush=True)
    local = threading.local(); lock = threading.Lock(); done = [0]
    def sess():
        if not hasattr(local, 's'):
            local.s = requests.Session(); local.s.headers['User-Agent'] = UA
        return local.s
    with CACHE.open('a') as f:
        def work(i):
            time.sleep(0.8)  # each worker paces itself: ~4 listings per second in all
            url = _list_one(sess(), i)
            with lock:
                cached[i] = url
                f.write(json.dumps(dict(id=i, url=url, at=datetime.now(timezone.utc).isoformat())) + '\n'); f.flush()
                done[0] += 1
                if done[0] % 1000 == 0:
                    print(json.dumps(dict(listed=done[0], of=len(todo))), flush=True)
        with ThreadPoolExecutor(workers) as ex:
            list(ex.map(work, todo))
    return cached


def cmu():
    scope = json.loads((STAGE / 'people' / 'scope.json').read_text())['scope']
    db = sqlite3.connect(str(CMU / 'catalog.sqlite'), timeout=120)
    done = {w for (w,) in db.execute("SELECT id FROM works WHERE status IN ('downloaded','fulltext_xml')")}
    want = {}
    for line in (CMU / 'staged' / 'arxiv-candidates.jsonl').open():
        c = json.loads(line)
        if c['work_id'] not in done and scope.get(c['work_id'], {}).get('in_scope') and arxiv_id(c['url']):
            want.setdefault(c['work_id'], arxiv_id(c['url']))
    urls = listing(list(want.values()))
    ev = CMU / 'discovery' / 'claude-cmu-catalog' / 'evidence' / 'arxiv-bulk.json'
    ev.write_text(json.dumps(dict(rule=__doc__, created_at=datetime.now(timezone.utc).isoformat(), works={w: dict(arxiv=a, url=urls.get(a)) for w, a in want.items()})))
    n = 0
    for w, a in want.items():
        if urls.get(a):
            n += db.execute('INSERT OR IGNORE INTO candidates VALUES (?,?,?,?,?,?)', (w, urls[a], f'https://arxiv.org/abs/{a}', None, 'submittedVersion', str(ev))).rowcount
    db.commit()
    print(json.dumps(dict(cmu_works=len(want), with_bulk_pdf=sum(1 for a in want.values() if urls.get(a)), candidates_added=n)))


def princeton():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'princeton_tools'))
    from catalog_snapshot import snapshot
    snap = snapshot(max_age_s=1800); st = snap['status']
    want = {}
    for src in (snap['candidates'], snap['attempts']):
        for w, us in src.items():
            if st.get(w) in ('downloaded', 'fulltext_xml'):
                continue
            for u in us:
                if arxiv_id(u):
                    want.setdefault(w, arxiv_id(u))
    urls = listing(list(want.values()))
    pkg = PRIN / 'discovery' / ('claude-arxiv-bulk-' + datetime.now(timezone.utc).strftime('%Y%m%d'))
    (pkg / 'evidence').mkdir(parents=True, exist_ok=True)
    ev = pkg / 'evidence' / 'arxiv-bulk.json'
    ev.write_text(json.dumps(dict(rule=__doc__, created_at=datetime.now(timezone.utc).isoformat(), works={w: dict(arxiv=a, url=urls.get(a)) for w, a in want.items()})))
    rows = [dict(work_id=w, url=urls[a], landing_url=f'https://arxiv.org/abs/{a}', license=None, version='submittedVersion', metadata_source=str(ev),
                 source='arxiv_bulk_gcs', detail=a) for w, a in want.items() if urls.get(a)]
    with open(pkg / 'cs-open-copies-candidates.jsonl', 'w') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')
    (pkg / 'work-ids.txt').write_text('\n'.join(r['work_id'] for r in rows) + '\n')
    (pkg / 'summary.json').write_text(json.dumps(dict(created_at=datetime.now(timezone.utc).isoformat(), counts=dict(works=len(want), candidates=len(rows)),
                                                      works_gaining_candidate=len(rows), requires_packages=[], rules=__doc__), indent=1))
    print(json.dumps(dict(princeton_works=len(want), with_bulk_pdf=len(rows), package=str(pkg))))


if __name__ == '__main__':
    {'cmu': cmu, 'princeton': princeton}[sys.argv[1]]()
