"""Channel wayback_escholarship (2026-11-04, owner): Berkeley papers whose only known copy is on eScholarship (escholarship.org), which blocks
our client at its CDN (403, even for robots.txt). The standing rule for a blocked host is Wayback-only: for each such paper, the Internet
Archive's capture of the item's PDF (https://escholarship.org/content/qt<id>/qt<id>.pdf, id from any known escholarship URL of the work), as the
existing Wayback channels do it: one exact-URL CDX lookup per 8 s (status 200 + application/pdf captures only, latest one), the candidate is
https://web.archive.org/web/<timestamp>id_/<original> (the collector asks web.archive.org at most once per 6 s). No user-agent change, no
other route around the block. Lookups are cached in raw/wayback_lookups.jsonl (kind 'escholarship').
CORE's own hosted copies of eScholarship records (core.ac.uk/download/...) answer a Cloudflare bot challenge (cf-mitigated: challenge,
2026-11-04), so that route is not used.
"""
import json
import re
import time

NAME = 'wayback_escholarship'
ID = re.compile(r'escholarship\.org/(?:uc/item/|content/qt)([0-9a-z]{8})\b')


def item_ids(known):
    return sorted({m.group(1) for u in known for m in [ID.search(u)] if m})


def APPLIES(school, paper):
    return school == 'berkeley' and bool(item_ids(paper.known)) and not any('web.archive.org' in u and 'escholarship' in u for u in paper.known)


def discover(school, papers, ctx):
    import ftp_common as F
    s = ctx.session()
    log_f = F.P.FT_RAW / 'wayback_lookups.jsonl'
    done = {}
    if log_f.exists():
        for line in log_f.open():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get('kind') == 'escholarship' and isinstance(r.get('status'), int) and r['status'] == 200:
                done[r['url']] = r.get('capture')
    last = 0.0
    with log_f.open('a') as f:
        for p in papers:
            rows = []
            for i in item_ids(p.known):
                url = f'escholarship.org/content/qt{i}/qt{i}.pdf'
                if url in done:
                    cap = done[url]
                elif ctx.dry:
                    continue
                else:
                    while True:
                        time.sleep(max(0, 8 - (time.monotonic() - last)))
                        last = time.monotonic()
                        try:
                            r = s.get('https://web.archive.org/cdx/search/cdx', params=dict(url=url, output='json', fl='timestamp,original,mimetype,statuscode',
                                                                                           filter=['statuscode:200', 'mimetype:application/pdf'], limit=20), timeout=(15, 90))
                            status = r.status_code
                            caps = r.json()[1:] if status == 200 and r.text.strip() else []
                        except Exception as e:
                            status, caps = type(e).__name__, []
                        if not isinstance(status, int):
                            print(json.dumps(dict(wayback_unreachable=status, pause_s=900)), flush=True)
                            time.sleep(900)
                            continue
                        if status == 429 or status >= 500:
                            time.sleep(120)
                            continue
                        break
                    best = max(caps, key=lambda x: x[0]) if caps else None
                    cap = dict(timestamp=best[0], original=best[1]) if best else None
                    done[url] = cap
                    f.write(json.dumps(dict(work_id=p.work_id, kind='escholarship', url=url, status=status, capture=cap, at=F.now())) + '\n')
                    f.flush()
                    ctx.n['wayback_escholarship_lookups'] += 1
                if cap:
                    rows.append(dict(work_id=p.work_id, url=f"https://web.archive.org/web/{cap['timestamp']}id_/{cap['original']}", landing_url=None,
                                     version='publishedVersion', source='wayback_escholarship', detail=url))
                    ctx.n['wayback_escholarship_hits'] += 1
                    break
            yield ctx.result(p, 'found' if rows else 'none', rows, query='Wayback CDX (exact URL, 200 pdf) of the eScholarship item PDF: ' + ','.join(item_ids(p.known))[:200])
