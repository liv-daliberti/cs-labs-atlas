# Vendored 2026-10-30 from /n/fs/resemble/maxent-grpo/.research-sweeps/claude-cmu-20261017/tools/core_search.py (sha256 7585c095f1b99fb79d1f5dd9930d482f5a71255d5457eb94656e3de467fc9de9); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Repository copies through CORE's search API (api.core.ac.uk/v3/search/outputs, the user's academic API key; key read
from the environment only, never written to files or logs) for papers with a DOI and no local copy at both schools.

tools/core_discover.py asked /v3/discover one DOI at a time (about 30 s each) and mostly got CORE's own reader copy,
which refuses automated clients. This pass asks the search endpoint for 25 DOIs at once (doi:"..." OR ...; one request
at a time, 2 s apart, waiting out the rate-limit window when it runs low) and keeps, for every output whose DOI is one
of ours (Princeton CS papers; in-scope CMU and EPFL catalog works), the original repository links CORE records (sourceFulltextUrls, and downloadUrl when it is not core.ac.uk).
Links to doi.org, orcid.org, core.ac.uk and the hosts the collectors cannot use (tools/s2_key_lookup.py BAD_HOSTS;
Princeton's arks / DataSpace, whose /bitstream files robots.txt disallows) are dropped. A link becomes a candidate with
itself as landing page (the collector follows a landing page to its PDF and checks the title in the file).
CMU / EPFL: candidates straight into data/fulltext/<school>/catalog.sqlite; Princeton: package
discovery/claude-core-search-<date><time>/ (a new name each run: an imported package is never rewritten).
cache raw/core_search.jsonl (one record per DOI asked; failed batches retried on a later run)
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import json, os, re, sqlite3, sys, time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

STAGE = P.SWEEPS / 'claude-cmu-20261017'  # vendored: the data root (was Path(__file__).resolve().parents[1])
CACHE = STAGE / 'raw' / 'core_search.jsonl'
FT = P.STORES
sys.path.insert(0, str(Path(__file__).resolve().parent))
from s2_key_lookup import BAD_HOSTS, princeton_targets, catalog_targets

SCOPES = {'cmu': STAGE / 'people' / 'scope.json',
          'epfl': P.SWEEPS / 'claude-epfl-20261019/people/scope.json'}


def school_targets():
    out = {'princeton': princeton_targets()}
    for school, scope in SCOPES.items():
        if scope.exists():
            out[school] = catalog_targets(school, scope)
    return out


def targets():
    return [(school, t['work_id'], t['doi']) for school, (ts, _) in school_targets().items() for t in ts
            if t['doi'] and not t['doi'].lower().startswith('10.48550/') and '_thesis_' not in t['work_id']]

# publisher landing / API / index hosts CORE records as "sources": paywalled, key-gated, or closed to robots
PUBLISHER = ('ieee.org', 'link.springer.com', 'api.elsevier.com', 'scopus.com', 'onlinelibrary.wiley.com', 'api.wiley.com', 'journals.sagepub.com',
             'syndication.highwire.org', 'tandfonline.com', 'doaj.org', 'isiknowledge.com', 'lbdiscover.ust.hk')
DROP = BAD_HOSTS + PUBLISHER + ('orcid.org', 'arks.princeton.edu', 'dataspace.princeton.edu')


def usable(u):
    if not u or not u.startswith('http'):
        return False
    h = (urlsplit(u).hostname or '').lower()
    return not any(h == b or h.endswith('.' + b) for b in DROP)


def main():
    import requests
    s = requests.Session(); s.headers['Authorization'] = 'Bearer ' + os.environ['CORE_API_KEY']
    done = {}
    if CACHE.exists():
        for line in CACHE.open():
            r = json.loads(line); done[r['doi']] = r
    tg = targets()
    todo = list(dict.fromkeys(d.lower() for _, _, d in tg if '"' not in d and '\\' not in d and (d.lower() not in done or done[d.lower()].get('error'))))
    print(json.dumps(dict(dois=len({d.lower() for _, _, d in tg}), todo=len(todo), cached=len(done))), flush=True)
    with CACHE.open('a') as f:
        for i in range(0, len(todo), 25):
            chunk = todo[i:i + 25]
            q = ' OR '.join(f'doi:"{d}"' for d in chunk)
            res = None
            for attempt in range(4):
                time.sleep(2)
                try:
                    r = s.get('https://api.core.ac.uk/v3/search/outputs/', params={'q': q, 'limit': 100}, timeout=(15, 200))
                except Exception:
                    time.sleep(30); continue
                left = r.headers.get('x-ratelimit-remaining')
                if r.status_code == 200:
                    res = r.json().get('results') or []
                    if left is not None and int(left) < 5:
                        time.sleep(60)
                    break
                if r.status_code == 429:
                    time.sleep(120); continue
                time.sleep(20)
            got = defaultdict(list)
            for o in res or []:
                d = (o.get('doi') or '').lower()
                if d in chunk:
                    got[d] += [u for u in (o.get('sourceFulltextUrls') or []) + [o.get('downloadUrl') or ''] if u]
            now = datetime.now(timezone.utc).isoformat()
            for d in chunk:
                rec = dict(doi=d, at=now, links=list(dict.fromkeys(got.get(d, [])))) if res is not None else dict(doi=d, at=now, error=True)
                done[d] = rec; f.write(json.dumps(rec) + '\n')
            f.flush()
            if (i // 25) % 20 == 19:
                print(json.dumps(dict(asked=i + len(chunk), of=len(todo), with_links=sum(1 for d in todo[:i + len(chunk)] if done[d].get('links')))), flush=True)
    package(done)


def package(done):
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d')
    n = Counter()
    plan = school_targets()
    for school in ('cmu', 'epfl'):
        if school not in plan:
            continue
        ts, known = plan[school]
        ev = FT / school / 'discovery' / f'claude-{school}-catalog' / 'evidence' / f'core-search-{stamp}.json'
        ev.parent.mkdir(parents=True, exist_ok=True)
        ev.write_text(json.dumps(dict(rule=__doc__, lookups=[done[t['doi'].lower()] for t in ts if t['doi'] and t['doi'].lower() in done])))
        rows = [(t['work_id'], u) for t in ts if t['doi'] for u in (done.get(t['doi'].lower()) or {}).get('links') or [] if usable(u) and u not in known[t['work_id']]]
        db = sqlite3.connect(str(FT / school / 'catalog.sqlite'), timeout=300)
        for attempt in range(20):
            try:
                n[f'{school}_candidates'] = sum(db.execute('INSERT OR IGNORE INTO candidates VALUES (?,?,?,?,?,?)', (w, u, u, None, None, str(ev))).rowcount for w, u in rows)
                db.commit(); break
            except sqlite3.OperationalError:
                db.rollback(); time.sleep(30)
        n[f'{school}_works'] = len({w for w, _ in rows})
    # Princeton
    ts, known = plan['princeton']
    pkg = FT / 'princeton' / 'discovery' / f"claude-core-search-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
    (pkg / 'evidence').mkdir(parents=True, exist_ok=True)
    pev = pkg / 'evidence' / 'core-search.json'
    pev.write_text(json.dumps(dict(rule=__doc__, lookups=[done[t['doi'].lower()] for t in ts if t['doi'] and t['doi'].lower() in done])))
    out = [dict(work_id=t['work_id'], url=u, landing_url=u, license=None, version=None, metadata_source=str(pev), source='core_search', detail=t['doi'])
           for t in ts if t['doi'] for u in (done.get(t['doi'].lower()) or {}).get('links') or [] if usable(u) and u not in known[t['work_id']]]
    with open(pkg / 'cs-open-copies-candidates.jsonl', 'w') as fh:
        for r in out:
            fh.write(json.dumps(r) + '\n')
    (pkg / 'work-ids.txt').write_text('\n'.join(dict.fromkeys(r['work_id'] for r in out)) + '\n')
    (pkg / 'summary.json').write_text(json.dumps(dict(created_at=datetime.now(timezone.utc).isoformat(), counts=dict(rows=len(out)),
                                                      works_gaining_candidate=len({r['work_id'] for r in out}), requires_packages=[], rules=__doc__), indent=1))
    n['princeton_candidates'], n['princeton_works'], n['princeton_package'] = len(out), len({r['work_id'] for r in out}), pkg.name
    hosts = Counter((urlsplit(u).hostname or '') for r in done.values() for u in r.get('links') or [])
    print(json.dumps(dict(n, asked=len(done), with_links=sum(1 for r in done.values() if r.get('links')), top_hosts=hosts.most_common(15))))


if __name__ == '__main__':
    main()
