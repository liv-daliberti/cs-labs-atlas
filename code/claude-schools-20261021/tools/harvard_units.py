"""Harvard unit faculty directories for the deep dive (T095, owner 2026-11-09): read each computing-relevant unit's OWN faculty directory into a
SCRATCH capture store, so that tools/missed_labs_review.py can accept a lead only where a captured official page names the person followed by a
ladder professor title.

store     <scratch>/missed-labs-profile/harvard.sqlite  (the store tools/missed_labs_fetch.py already uses; main's raw store is never written)
live      a host is read live only when school_web.robots_ok allows (robots.txt incl. rules naming ClaudeBot / anthropic-ai / claude-web); a
          challenge or 401/403/429 marks the host blocked and it is not used again; one request per host per max(1 s, crawl-delay)
wayback   units whose host refuses this client (FAS Akamai, hbs.edu, math.harvard.edu): the latest id_ capture of the exact URL, through the shared
          throttle with WAYBACK_LOW=1; a 429 stops the Wayback side and nothing is retried
paging    `?page=N` (and SEAS's `?page=%2CN`) until a page adds no new text
usage: harvard_units.py [--wayback] [--only CODE ...]     -> <scratch>/harvard-deepdive/units-report.json
"""
import json
import os
import re
import sys
import time
from pathlib import Path

os.environ['WAYBACK_LOW'] = '1'
import school_web as W  # noqa: E402

SCRATCH = Path('/n/fs/resemble/homogenizing-science/scratch')
DB = SCRATCH / 'missed-labs-profile' / 'harvard.sqlite'
REPORT = SCRATCH / 'harvard-deepdive' / 'units-report.json'

# code, label, [urls], pager ('seas' | 'page' | None), via ('live' | 'wayback')
UNITS = [
    ('SEAS', 'SEAS faculty (all areas)', ['https://seas.harvard.edu/faculty'], 'seas', 'live'),
    ('SEAS-CS', 'SEAS Computer Science people', ['https://seas.harvard.edu/computer-science/people'], 'seas', 'live'),
    ('SEAS-AM', 'SEAS Applied Mathematics people', ['https://seas.harvard.edu/applied-mathematics/people'], 'seas', 'live'),
    ('DBMI', 'HMS Biomedical Informatics', ['https://dbmi.hms.harvard.edu/people', 'https://dbmi.hms.harvard.edu/people/faculty'], 'page', 'live'),
    ('BIOSTAT', 'Chan School Biostatistics', ['https://hsph.harvard.edu/department/biostatistics/'], 'page', 'live'),
    ('HKS', 'Kennedy School faculty', ['https://www.hks.harvard.edu/faculty-research'], 'page', 'live'),
    ('KEMPNER', 'Kempner Institute people', ['https://kempnerinstitute.harvard.edu/people/our-people/'], 'page', 'live'),
    ('HLS', 'Harvard Law School faculty', ['https://hls.harvard.edu/faculty/'], 'page', 'live'),
    ('WYSS', 'Wyss core faculty', ['https://wyss.harvard.edu/team/'], 'page', 'live'),
    ('STAT', 'FAS Statistics', ['https://statistics.fas.harvard.edu/people/faculty', 'https://statistics.fas.harvard.edu/people'], None, 'wayback'),
    ('MATH', 'FAS Mathematics', ['https://www.math.harvard.edu/people/', 'https://www.math.harvard.edu/people/faculty/'], None, 'wayback'),
    ('ECON', 'FAS Economics', ['https://economics.harvard.edu/faculty', 'https://economics.harvard.edu/people/faculty'], None, 'wayback'),
    ('PSY', 'FAS Psychology', ['https://psychology.fas.harvard.edu/people/faculty', 'https://psychology.fas.harvard.edu/people'], None, 'wayback'),
    ('HBS', 'Business School faculty (Technology and Operations Management)', ['https://www.hbs.edu/faculty/units/tom/Pages/default.aspx',
                                                                              'https://www.hbs.edu/faculty/Pages/browse.aspx'], None, 'wayback'),
    ('CBS', 'Center for Brain Science', ['https://cbs.fas.harvard.edu/people/', 'https://cbs.fas.harvard.edu/people/faculty/'], None, 'wayback'),
    ('SYSBIO', 'HMS Systems Biology', ['https://sysbio.med.harvard.edu/faculty', 'https://sysbio.med.harvard.edu/people'], None, 'wayback'),
    ('BCB', 'HMS Biomedical Informatics (Wayback copy)', ['https://dbmi.hms.harvard.edu/people'], None, 'wayback'),
]


def pages(c, urls, pager):
    got = []
    for u in urls:
        seen = set()
        n = 0
        while n < 40:
            if pager == 'seas':
                url = u + (f'?page=%2C{n}' if n else '')
            elif pager == 'page':
                url = u + (('&' if '?' in u else '?') + f'page={n}' if n else '')
            else:
                url = u
            r = W.live(c, url)
            if r is not None and 300 <= r[0] < 400:
                row = c.execute('select raw_zlib from live where url=?', (url,)).fetchone()
                import zlib
                loc = json.loads(zlib.decompress(row[0]))['location'] if row and row[0] else None
                got.append({'url': url, 'status': r[0], 'redirect': loc})
                break
            if r is None or r[0] != 200:
                got.append({'url': url, 'status': None if r is None else r[0]})
                break
            text = W.flat(r[2])
            h = hash(text)
            if h in seen:
                break
            seen.add(h)
            got.append({'url': url, 'status': 200, 'sha256': r[1], 'chars': len(text)})
            n += 1
            if not pager:
                break
    return got


def wayback_one(c, url):
    try:
        rows = W.cdx_rows(c, re.sub(r'^https?://', '', url), collapse='timestamp:4', frm='2024')
    except Exception as e:  # noqa: BLE001
        return {'url': url, 'status': 'error:' + repr(e)[:80], 'stop': '429' in repr(e)}
    if not rows:
        return {'url': url, 'status': 'no_capture'}
    r = sorted(rows, key=lambda x: x['timestamp'])[-1]
    cap, st, sha, b = W.capture(c, r['timestamp'], r['original'], url, 'profile')
    return {'url': cap, 'status': st, 'sha256': sha, 'observed': r['timestamp'], 'chars': len(W.flat(b))}


def dbmi_profiles(c, limit=16):
    """The first links of the DBMI people pages are the department's core faculty (Avillach ... Zitnik); their own profile pages carry the HMS titles."""
    links = []
    for (u,) in c.execute("select url from live where url like 'https://dbmi.hms.harvard.edu/people%' and status=200").fetchall():
        for m in re.finditer(r'href="(/people/[a-z0-9-]+)"', W.live_html(c, u)):
            if m.group(1) not in links and not re.fullmatch(r'/people/(?:all|[a-z])', m.group(1)):
                links.append(m.group(1))
    got = []
    for p in links[:limit]:
        r = W.live(c, 'https://dbmi.hms.harvard.edu' + p)
        got.append({'url': 'https://dbmi.hms.harvard.edu' + p, 'status': None if r is None else r[0]})
    return got


def main(argv):
    wayback = '--wayback' in argv
    only = argv[argv.index('--only') + 1:] if '--only' in argv else None
    DB.parent.mkdir(parents=True, exist_ok=True)
    W.db_path = lambda key, _p=str(DB): Path(_p)
    c = W.con('harvard')
    rep = json.loads(REPORT.read_text()) if REPORT.exists() else {}
    stop = False
    if '--dbmi' in argv:
        rep['DBMI-core'] = {'label': 'DBMI core faculty profiles', 'via': 'live', 'pages': dbmi_profiles(c), 'at': time.strftime('%Y-%m-%d')}
        REPORT.write_text(json.dumps(rep, indent=1))
        print(rep['DBMI-core']['pages'])
        return 0
    for code, label, urls, pager, via in UNITS:
        if only and code not in only:
            continue
        if via == 'live':
            rep[code] = {'label': label, 'via': via, 'pages': pages(c, urls, pager), 'at': time.strftime('%Y-%m-%d')}
        elif wayback and not stop:
            res = []
            for u in urls:
                x = wayback_one(c, u)
                res.append(x)
                if x.get('stop'):
                    stop = True
                    break
            rep[code] = {'label': label, 'via': via, 'pages': res, 'at': time.strftime('%Y-%m-%d')}
        else:
            rep.setdefault(code, {'label': label, 'via': via, 'pages': [], 'queued': True})
        REPORT.write_text(json.dumps(rep, indent=1))
        print(code, [(p.get('status'), p.get('chars')) for p in rep[code]['pages']][:12])
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
