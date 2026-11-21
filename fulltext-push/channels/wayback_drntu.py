"""Channel wayback_drntu (2026-11-21, D-0033 / Q-0361): NTU papers whose known open copy is on DR-NTU (dr.ntu.edu.sg, reached through
hdl.handle.net/10356/<n>). DR-NTU's WAF answers our client 405, robots.txt included; host-rulings.json rules live access out of bounds. The
standing rule for a host that refuses automated clients is Wayback-only (2026-11-05), and DR-NTU names no AI agent in any robots rule, so
for each such paper: one Internet Archive CDX prefix lookup of the item's files (dr.ntu.edu.sg/bitstream/10356/<n>/, status 200 and
application/pdf captures only), and the latest capture of each distinct file becomes a candidate https://web.archive.org/web/<ts>id_/<original>.
Nothing is ever asked of dr.ntu.edu.sg itself. The lookups take the shared web.archive.org slot (host_throttle.wait_slot, 8 s; a 429 is
recorded for every client and stops the run), and are cached in raw/wayback_lookups.jsonl (kind 'drntu'): a handle is never looked up twice.
The download itself waits for the Wayback rotator's turn (WAYBACK_HOLD), where the collector's identity check applies as for every copy.
Pilot first (D-0033): at most WAYBACK_DRNTU_LIMIT new lookups per run (default 50); the rest only after the pilot's identity check holds.
"""
import json
import os
import re

NAME = 'wayback_drntu'
HANDLE = re.compile(r'(?:hdl\.handle\.net|dr\.ntu\.edu\.sg/(?:handle|bitstream))/10356/(\d+)\b')
CDX = 'https://web.archive.org/cdx/search/cdx'
MAX_FILES = 3


def handles(known):
    return sorted({m.group(1) for u in known for m in [HANDLE.search(u)] if m})


def APPLIES(school, paper):
    return school == 'ntu' and bool(handles(paper.known)) and not any('web.archive.org' in u and 'dr.ntu.edu.sg' in u for u in paper.known)


def cached(log_f):
    done = {}
    if log_f.exists():
        for line in log_f.open():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get('kind') == 'drntu' and r.get('status') == 200:
                done[r['handle']] = r.get('captures') or []
    return done


def best_captures(rows):
    """[[timestamp, original, mimetype, status], ...] -> the latest capture of each distinct file (query string dropped), at most MAX_FILES."""
    latest = {}
    for ts, orig, *_ in rows:
        k = orig.split('?')[0]
        if k not in latest or ts > latest[k][0]:
            latest[k] = (ts, orig)
    return [dict(timestamp=ts, original=o) for ts, o in sorted(latest.values(), key=lambda x: x[1])[:MAX_FILES]]


def discover(school, papers, ctx):
    import ftp_common as F
    import host_throttle as H
    limit = int(os.environ.get('WAYBACK_DRNTU_LIMIT', '50'))
    s = ctx.session()
    log_f = F.P.FT_RAW / 'wayback_lookups.jsonl'
    done = cached(log_f)
    asked = 0
    with log_f.open('a') as f:
        for p in papers:
            caps, unanswered = [], False
            for h in handles(p.known):
                if h not in done:
                    if ctx.dry or asked >= limit or ctx.n.get('stopped'):
                        unanswered = True
                        continue
                    try:
                        H.wait_slot('web.archive.org', 8)
                        r = s.get(CDX, params=dict(url=f'dr.ntu.edu.sg/bitstream/10356/{h}/', matchType='prefix', output='json',
                                                   fl='timestamp,original,mimetype,statuscode', filter=['statuscode:200', 'mimetype:application/pdf'],
                                                   limit=50), timeout=(15, 90))
                        status = r.status_code
                    except Exception as e:   # unreachable or a long shared cooldown: stop, the rest stays unanswered
                        ctx.n['stopped'] = f'web.archive.org: {type(e).__name__}'
                        unanswered = True
                        continue
                    asked += 1
                    if status == 429:
                        H.record_429('web.archive.org')
                        ctx.n['stopped'] = 'web.archive.org HTTP 429'
                        unanswered = True
                        continue
                    if status != 200:
                        ctx.n['wayback_drntu_http_' + str(status)] += 1
                        unanswered = True
                        continue
                    done[h] = best_captures(r.json()[1:] if r.text.strip() else [])
                    f.write(json.dumps(dict(work_id=p.work_id, kind='drntu', handle=h, status=200, captures=done[h], at=F.now())) + '\n')
                    f.flush()
                    ctx.n['wayback_drntu_lookups'] += 1
                caps += done[h]
            rows = [dict(work_id=p.work_id, url=f"https://web.archive.org/web/{c['timestamp']}id_/{c['original']}", landing_url=None,
                         version=None, source='wayback_drntu', detail=c['original']) for c in caps]
            if rows:
                ctx.n['wayback_drntu_hits'] += 1
            elif unanswered:
                continue   # not asked yet (pilot limit, dry run, stop): no Result, so the check stays open rather than a false 'none'
            yield ctx.result(p, 'found' if rows else 'none', rows,
                             query='Wayback CDX (prefix, 200 pdf) of DR-NTU files: ' + ','.join(handles(p.known))[:200])
