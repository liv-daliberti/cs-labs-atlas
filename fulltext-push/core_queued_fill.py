"""core_queued_fill (2026-11-17, owner 'yes 1'): a CORE lookup BY DOI for the queued NON-lab works. The core / core_bulk channels
look up lab papers only (lab_channels.plan_for); the catalogs also hold tens of thousands of other queued works (the oa-expand
batches) with a DOI, no candidate and no attempt, that no channel asks CORE about.

Only the DOI leaves the machine (doi:"..." queries, 25 per request, 2 s apart, the registered CORE API key read from
~/.config/cs-atlas/core.env, never printed or logged; the x-ratelimit headers are honoured, 429 and errors back off, 3 failed requests
in a row stop the run). A result counts when its DOI is one of the asked ones; its repository links (sourceFulltextUrls, and
downloadUrl when core.ac.uk is not the host) are kept when the hosts are usable (core_search.usable: no doi.org, arXiv landing,
publisher or core.ac.uk reader links) = an open full-text / download link. Pages of 100 results are followed (offset) while a request is full.

Two halves, like queued_oa_fill (whose plan file format and apply_plan this reuses, so the write is the same audited path):
  lookup   read-only on the catalogs: DOIs of the queued works with no candidate and no attempt -> raw cache <cache>.jsonl (one record per
           DOI: links | error; resumable, a DOI already answered is never asked again; the vendored core_search cache of the lab papers
           is read too). --sample N asks a seeded random N (the pilot). --max-minutes stops cleanly.
  plan     the cache -> PLAN.json.gz ({made_at, schools: {school: {counts, rows}}}); rows are candidate rows (source core_queued).
  apply    queued_oa_fill.apply_plan: fresh backup (<= 12 h, age from the file name), lock wait, INSERT OR IGNORE candidates only,
           integrity_check. Works, attempts, status and downloads are never touched.
usage: core_queued_fill.py lookup <schools> --cache FILE [--sample N --seed S] [--max-minutes M]
       core_queued_fill.py plan <schools> --cache FILE --plan-file PLAN.json.gz [--json COUNTS]
       core_queued_fill.py apply <schools> --plan-file PLAN.json.gz --backup-dir DIR [--lock-wait 2700] [--json OUT]
"""
import argparse
import collections
import json
import os
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F  # noqa: E402
import queued_oa_fill as Q  # noqa: E402

SOURCE = 'core_queued'
URL = 'https://api.core.ac.uk/v3/search/outputs/'
CHUNK, PAGE, MAX_PAGES = 25, 100, 4
MAX_FAILS = 3


def plan_dois(schools, queued=Q.queued):
    """-> {normalized DOI: [(school, work id)]} for the queued works with a DOI, no candidate and no attempt. DOIs that cannot be
    put in a quoted query (a quote or backslash), arXiv DOIs (the arXiv channels own them) and non-DOI strings are left out."""
    out = collections.defaultdict(list)
    for s in schools:
        for i, d in queued(s):
            d = F.ndoi(d)
            if d.startswith('10.') and '"' not in d and '\\' not in d and not d.startswith('10.48550/'):
                out[d].append((s, i))
    return out


def load_cache(path):
    out = {}
    if path and Path(path).exists():
        for line in open(path):
            try:
                r = json.loads(line)
                out[r['doi']] = r
            except (ValueError, KeyError):
                pass
    return out


def links_of(o, usable):
    return [u for u in (o.get('sourceFulltextUrls') or []) + [o.get('downloadUrl') or ''] if u and usable(u)]


def ask(session, dois, sleep=time.sleep, usable=None):
    """-> {doi: [links]} for one chunk of DOIs, or None when the request kept failing (the caller records an error). 2 s before each
    request; the rate-limit window is waited out when it runs low; 429 backs off 120 s, other failures 20-30 s; at most 4 tries per page."""
    if usable is None:
        import core_search
        usable = core_search.usable
    got = {d: [] for d in dois}
    asked = set(dois)
    q = ' OR '.join(f'doi:"{d}"' for d in dois)
    for page in range(MAX_PAGES):
        res = None
        for _attempt in range(4):
            sleep(2)
            try:
                r = session.get(URL, params={'q': q, 'limit': PAGE, 'offset': page * PAGE}, timeout=(15, 200))
            except Exception:
                sleep(30)
                continue
            if r.status_code == 200:
                left = r.headers.get('x-ratelimit-remaining')
                if left is not None and str(left).isdigit() and int(left) < 5:
                    sleep(60)
                res = r.json().get('results') or []
                break
            sleep(120 if r.status_code == 429 else 20)
        if res is None:
            return None
        for o in res:
            d = F.ndoi(o.get('doi'))
            if d in asked:
                got[d] += links_of(o, usable)
        if len(res) < PAGE:
            break
    return {d: list(dict.fromkeys(v)) for d, v in got.items()}


def lookup(schools, cache, sample=None, seed=1, max_minutes=None, session=None, sleep=time.sleep, queued=Q.queued, shared=None, usable=None, log=print):
    """Ask CORE for the planned DOIs not yet answered; append one record per DOI to `cache`. -> counts."""
    want = plan_dois(schools, queued)
    done = {d: r for d, r in load_cache(cache).items() if not r.get('error')}
    for d, r in (shared or {}).items():
        done.setdefault(d, r)
    todo = sorted(d for d in want if d not in done)
    n = dict(queued_dois=len(want), cached=len(want) - len(todo), todo=len(todo))
    if sample is not None and sample < len(todo):
        todo = sorted(random.Random(seed).sample(todo, sample))
    n['asked'] = n['errors'] = n['with_links'] = 0
    if session is None:
        import requests
        F.load_env()
        session = requests.Session()
        session.headers['Authorization'] = 'Bearer ' + os.environ['CORE_API_KEY']
        session.headers['User-Agent'] = F.UA
    end = time.monotonic() + max_minutes * 60 if max_minutes else None
    fails = 0
    Path(cache).parent.mkdir(parents=True, exist_ok=True)
    with open(cache, 'a') as f:
        for i in range(0, len(todo), CHUNK):
            if end and time.monotonic() > end:
                n['stopped'] = 'max-minutes'
                break
            chunk = todo[i:i + CHUNK]
            res = ask(session, chunk, sleep, usable)
            at = F.now()
            for d in chunk:
                rec = dict(doi=d, at=at, links=res[d]) if res is not None else dict(doi=d, at=at, error=True)
                f.write(json.dumps(rec) + '\n')
                n['asked'] += 1
                n['errors'] += res is None
                n['with_links'] += bool(res and res[d])
            f.flush()
            fails = fails + 1 if res is None else 0
            if fails >= MAX_FAILS:
                n['stopped'] = f'{MAX_FAILS} failed requests in a row'
                break
            if (i // CHUNK) % 20 == 0:
                log(json.dumps(dict(at=F.now(), step='core_queued_lookup', **n)), flush=True)
    return n


def build_plan(schools, cache, plan_file=None, queued=Q.queued, shared=None, usable=None):
    """The cache -> {school: {counts, rows}} (and the gzip JSON at plan_file in queued_oa_fill's format)."""
    if usable is None:
        import core_search
        usable = core_search.usable
    want = plan_dois(schools, queued)
    got = dict(shared or {})
    got.update({d: r for d, r in load_cache(cache).items() if not r.get('error')})
    saved = {s: dict(counts=collections.Counter(), rows=[]) for s in schools}
    for d, works in want.items():
        r = got.get(d)
        for s, i in works:
            c = saved[s]['counts']
            c['queued'] += 1
            if r is None:
                c['not_asked'] += 1
                continue
            c['asked'] += 1
            urls = [u for u in r.get('links') or [] if usable(u)]
            if urls:
                c['works_with_link'] += 1
            for u in dict.fromkeys(urls):
                saved[s]['rows'].append(dict(work_id=i, url=u, landing_url=u, version=None, source=SOURCE, detail=json.dumps(dict(matched_by='doi'))))
    for s in schools:
        saved[s]['counts'] = dict(saved[s]['counts'], rows=len(saved[s]['rows']))
    if plan_file:
        import gzip
        tmp = Path(str(plan_file) + '.part')
        with gzip.open(tmp, 'wt') as f:
            json.dump(dict(made_at=F.now(), schools=saved), f)
        os.replace(tmp, plan_file)
    return saved


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('cmd', choices=['lookup', 'plan', 'apply'])
    ap.add_argument('schools')
    ap.add_argument('--cache')
    ap.add_argument('--sample', type=int)
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--max-minutes', type=float)
    ap.add_argument('--plan-file')
    ap.add_argument('--backup-dir')
    ap.add_argument('--lock-wait', type=int, default=2700)
    ap.add_argument('--json')
    a = ap.parse_args(argv)
    schools = a.schools.split(',')
    shared = None
    if a.cmd in ('lookup', 'plan'):
        if not a.cache:
            raise SystemExit('--cache is required')
        try:
            import core_search
            shared = {d: r for d, r in load_cache(core_search.CACHE).items() if not r.get('error')}
        except Exception:
            shared = {}
    if a.cmd == 'lookup':
        n = lookup(schools, a.cache, a.sample, a.seed, a.max_minutes, shared=shared)
        print(json.dumps(dict(at=F.now(), step='core_queued_lookup_done', **n)), flush=True)
        if a.json:
            Path(a.json).write_text(json.dumps(n, indent=1))
        if n.get('stopped', '').endswith('in a row'):
            sys.exit(2)
    elif a.cmd == 'plan':
        saved = build_plan(schools, a.cache, a.plan_file, shared=shared)
        counts = {s: v['counts'] for s, v in saved.items()}
        print(json.dumps(dict(at=F.now(), step='core_queued_plan', counts=counts)), flush=True)
        if a.json:
            Path(a.json).write_text(json.dumps(counts, indent=1))
    else:
        if not (a.plan_file and a.backup_dir):
            raise SystemExit('apply needs --plan-file and --backup-dir')
        Q.apply_plan(a.plan_file, schools, a.backup_dir, lock_wait=a.lock_wait, json_out=a.json)


if __name__ == '__main__':
    main()
