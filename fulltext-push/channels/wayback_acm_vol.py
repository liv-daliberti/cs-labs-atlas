"""Channel wayback_acm_vol (2026-11-21, owner: the 10k push, "make this a priority"): what wayback_acm asks, one request per ACM volume.

Same question as wayback_acm (lab_channels.step_wayback_acm): for a missing paper with an ACM DOI (10.1145/*), no Wayback candidate and no arXiv
candidate, has the Internet Archive a status-200 application/pdf capture of dl.acm.org/doi/pdf/<doi> or of its ?download=true twin? wayback_acm
asks one exact CDX lookup per URL (up to two per paper, at its own 8 s pace, outside host_throttle). This channel asks one CDX *prefix* lookup per
volume, dl.acm.org/doi/pdf/10.1145/<volume> (the DOI's 7-digit first part), which answers every paper of that volume and both URL forms
at once, for every school: the answer is cached whole (kind 'acm_prefix', its PDF rows), so a volume asked for one school answers the others, and it takes the shared web.archive.org slot (host_throttle.wait_slot; a 429 is recorded for every
client and stops the run). Past hit rates (raw/wayback_lookups.jsonl, 2026-11-21): plain 30%, ?download=true 39% of the plain misses.

Every answer is written to raw/wayback_lookups.jsonl in wayback_acm's own record form (kind 'acm', url, status 200, capture) for both URL
forms, so wayback_acm and the ledger's wayback_acm source (unavailable_ledger.src_wayback) treat those URLs as asked and never repeat them.
A prefix answer that reaches LIMIT rows may be truncated: its papers are then asked one DOI prefix each. Candidates are written as the lookups go
(every 50 hits; the run takes hours); the downloads wait for the Wayback rotator's turn, where the collector's identity check applies.
WAYBACK_ACM_VOL_LIMIT caps the prefix requests of one run (default: no cap).
"""
import json
import os
import re
from collections import defaultdict
from pathlib import Path

NAME = 'wayback_acm_vol'
CDX = 'https://web.archive.org/cdx/search/cdx'
LIMIT = 20000
PDF = re.compile(r'dl\.acm\.org(?::\d+)?/doi/pdf/(10\.1145/[^?#]+)(\?[^#]*)?$', re.I)


def doi_of(paper):
    import ftp_common as F
    return F.ndoi(paper.r.get('doi'))


def APPLIES(school, paper):
    import lab_channels as L
    return doi_of(paper).startswith('10.1145/') and not any('web.archive.org' in u for u in paper.known) and not L.has_arxiv(paper.known)


def plain(d):
    return f'dl.acm.org/doi/pdf/{d}'


def twin(d):
    return f'dl.acm.org/doi/pdf/{d}?download=true'


def volume(d):
    return d.split('/', 1)[0] + '/' + d.split('/', 1)[1].split('.', 1)[0]


def cached(files, vols=None):
    """-> {url without scheme: capture or None}: every status-200 answer of wayback_acm, the ledger and this channel; `vols` (a dict) gets
    {volume: split_rows(its rows)} of every complete prefix answer."""
    done = {}
    for lf in files:
        if lf.exists():
            for line in lf.open():
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get('kind') == 'acm_prefix':
                    if vols is not None and r.get('status') == 200 and not r.get('truncated'):
                        vols[r['volume']] = split_rows(r.get('rows') or [])
                elif r.get('status') == 200 and r.get('url'):
                    done[re.sub(r'^https?://', '', r['url'])] = r.get('capture')
    return done


def cache_files():
    import ftp_common as F
    R = str(F.P.SWEEPS) + '/'
    return [F.P.FT_RAW / 'wayback_lookups.jsonl'] + [Path(R + x) for x in (
        'claude-mit-20261020/raw/wayback_lookups.jsonl', 'claude-cmu-20261017/raw/wayback_lookups.jsonl',
        'claude-epfl-20261019/raw/wayback_lookups.jsonl', 'claude-princeton-20261015/cs-structure/raw/wayback/lookups.jsonl')]


def split_rows(rows):
    """CDX rows [[timestamp, original, mimetype, status], ...] -> {doi (lower): {'plain': capture, 'dl': capture}}, latest capture of each form."""
    out = defaultdict(dict)
    for ts, orig, *_ in rows:
        if 'casa_token' in orig or 'cookieSet' in orig:
            continue
        m = PDF.search(orig)
        if not m:
            continue
        q = (m.group(2) or '').lower()
        form = 'plain' if not q else ('dl' if q == '?download=true' else None)
        if not form:
            continue
        d = m.group(1).lower().rstrip('/')
        if form not in out[d] or ts > out[d][form]['timestamp']:
            out[d][form] = dict(timestamp=ts, original=orig)
    return out


def answer(done, d, vols=None):
    """-> (capture or None, asked): the plain form first, then the twin, as wayback_acm decides; a volume's prefix answer covers both."""
    p, t = plain(d), twin(d)
    if p in done and done[p]:
        return done[p], True
    if p in done and t in done:
        return done[t], True
    if vols and volume(d) in vols:
        f = vols[volume(d)].get(d, {})
        return f.get('plain') or f.get('dl'), True
    return None, False


def discover(school, papers, ctx):
    import ftp_common as F
    import host_throttle as H
    cap_n = int(os.environ.get('WAYBACK_ACM_VOL_LIMIT', '0') or 0)
    log_f = F.P.FT_RAW / 'wayback_lookups.jsonl'
    vols = {}
    done = cached(cache_files(), vols)
    by_doi = defaultdict(list)
    for p in papers:
        by_doi[doi_of(p).lower()].append(p)
    todo = [d for d in by_doi if not answer(done, d, vols)[1]]
    groups = defaultdict(list)
    for d in todo:
        groups[volume(d)].append(d)
    order = sorted(groups, key=lambda v: (-len(groups[v]), v))     # the most papers per request first
    ctx.n['wayback_acm_vol_papers_to_ask'] = len(todo)
    ctx.n['wayback_acm_vol_requests_planned'] = len(order)
    print(json.dumps(dict(school=school, step=NAME, papers=len(papers), to_ask=len(todo), volumes=len(order))), flush=True)
    s = ctx.session()
    asked, pending = 0, []

    def add(d, cap):
        for p in by_doi[d]:
            pending.append(dict(work_id=p.work_id, url=f"https://web.archive.org/web/{cap['timestamp']}id_/{cap['original']}", landing_url=None,
                                version='publishedVersion', source='wayback_acm_dl', detail=plain(d)))

    for d in by_doi:   # answered before (wayback_acm, the ledger, an earlier run) but never written: APPLIES says no Wayback URL is known
        cap, was_asked = answer(done, d, vols)
        if was_asked and cap:
            ctx.n['wayback_acm_vol_cached_hits'] += 1
            add(d, cap)

    def ask(prefix):
        H.wait_slot('web.archive.org', 8)
        r = s.get(CDX, params=dict(url=prefix, matchType='prefix', output='json', fl='timestamp,original,mimetype,statuscode',
                                   filter=['statuscode:200', 'mimetype:application/pdf'], limit=LIMIT), timeout=(15, 120))
        if r.status_code == 429:
            H.record_429('web.archive.org')
        return r.status_code, (r.json()[1:] if r.status_code == 200 and r.text.strip() else [])

    def settle(ds, found, via, f):
        for d in ds:
            got = found.get(d, {})
            for url, form in ((plain(d), 'plain'), (twin(d), 'dl')):
                done[url] = got.get(form)
                f.write(json.dumps(dict(work_id=by_doi[d][0].work_id, kind='acm', url=url, status=200, capture=done[url], via=via, at=F.now())) + '\n')
            cap = answer(done, d, vols)[0]
            if cap:
                ctx.n['wayback_acm_vol_hits'] += 1
                add(d, cap)
        f.flush()

    def flush_rows():
        if pending and not ctx.dry:
            ctx.n['candidates_added'] += ctx.write(list(pending), NAME)
        pending.clear()

    with log_f.open('a') as f:
        for v in order:
            if ctx.dry or ctx.n.get('stopped') or (cap_n and asked >= cap_n):
                break
            queue = [(plain(v), groups[v])]
            while queue and not ctx.n.get('stopped'):
                prefix, ds = queue.pop(0)
                try:
                    status, rows = ask(prefix)
                except Exception as e:   # unreachable, or a shared cooldown longer than host_throttle waits: stop, the rest stays unasked
                    ctx.n['stopped'] = f'web.archive.org: {type(e).__name__}'
                    break
                asked += 1
                ctx.n['wayback_acm_vol_requests'] += 1
                if status == 429:
                    ctx.n['stopped'] = 'web.archive.org HTTP 429'
                    break
                if status != 200:
                    ctx.n[f'wayback_acm_vol_http_{status}'] += 1
                    continue
                truncated = len(rows) >= LIMIT
                if prefix == plain(v):   # the volume's answer, whole: later schools' papers of this volume are answered from it
                    keep = [[ts, o] for ts, o, *_ in rows if PDF.search(o)]
                    f.write(json.dumps(dict(kind='acm_prefix', volume=v, url=prefix, status=200, truncated=truncated, rows=keep, at=F.now())) + '\n')
                    if not truncated:
                        vols[v] = split_rows(keep)
                if truncated and len(ds) > 1:   # possibly truncated: each DOI on its own prefix (both URL forms in one request)
                    ctx.n['wayback_acm_vol_truncated'] += 1
                    queue += [(plain(d), [d]) for d in ds]
                    continue
                settle(ds, split_rows(rows), 'prefix:' + prefix, f)
            if len(pending) >= 50:
                flush_rows()
            if asked % 100 == 0 and asked:
                print(json.dumps(dict(school=school, step=NAME, requests=asked, of=len(order), hits=ctx.n['wayback_acm_vol_hits'])), flush=True)
    flush_rows()
    for d, ps in by_doi.items():
        cap, was_asked = answer(done, d, vols)
        if not was_asked:
            continue   # not asked (dry run, stop, cap): no Result, so the check stays open
        for p in ps:
            url = f"https://web.archive.org/web/{cap['timestamp']}id_/{cap['original']}" if cap else None
            yield ctx.result(p, 'found' if cap else 'none',
                             [dict(work_id=p.work_id, url=url, written_by_step=True)] if cap else [],
                             query=f'Wayback CDX (prefix {volume(d)}, 200 pdf) of {plain(d)} and ?download=true')
