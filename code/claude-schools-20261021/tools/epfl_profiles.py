"""people.epfl.ch profiles of census people whose rank the sweep's pages leave unknown (live, else the latest Wayback
capture), cached with sha256 in census/raw/profiles.sqlite. robots.txt honoured (requests with a timeout), one request per
3 s per host, Wayback at most one per 10 s; a blocked or missing page is recorded, never worked around.
usage: epfl_profiles.py <name> [<name> ...]   (people.epfl.ch handles are derived from the sweep's rows; else the
       public search page is not used — a person without a handle or SCIPER is reported)
"""
import hashlib, json, re, sqlite3, sys, time, unicodedata, urllib.parse, urllib.robotparser, zlib
from datetime import datetime, timezone
from pathlib import Path

OUT = Path('/n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021/census/raw')
EP = Path('/n/fs/resemble/maxent-grpo/.research-sweeps/claude-epfl-20261019')
UA = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'
LAST, ROBOTS = {}, {}


def db():
    OUT.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(OUT / 'profiles.sqlite'))
    c.execute('CREATE TABLE IF NOT EXISTS pages (url TEXT PRIMARY KEY, final_url TEXT, status INTEGER, fetched_at TEXT, sha256 TEXT, body BLOB)')
    return c


def allowed(s, url):
    u = urllib.parse.urlsplit(url); base = f'{u.scheme}://{u.netloc}'
    if base not in ROBOTS:
        rp = urllib.robotparser.RobotFileParser(); rp.set_url(base + '/robots.txt')
        try:
            r = s.get(base + '/robots.txt', timeout=(10, 20))
            if r.status_code == 200:
                rp.parse(r.text.splitlines())
            elif r.status_code in (401, 403):
                rp.disallow_all = True
            else:
                rp = None
        except Exception:
            rp = None
        ROBOTS[base] = rp
    return ROBOTS[base] is None or ROBOTS[base].can_fetch(UA, url)


def get(s, url, gap):
    host = urllib.parse.urlsplit(url).netloc
    time.sleep(max(0, gap - (time.monotonic() - LAST.get(host, 0)))); LAST[host] = time.monotonic()
    if not allowed(s, url):
        return None, 'robots'
    try:
        r = s.get(url, timeout=(15, 60))
    except Exception as e:
        return None, type(e).__name__
    return (r, 200) if r.status_code == 200 else (None, r.status_code)


def main(names):
    import requests
    s = requests.Session(); s.headers['User-Agent'] = UA
    rows = json.load(open(EP / 'people' / 'dept_ic.json'))['people']
    c = db()
    for name in names:
        rs = [r for r in rows if r['name'] == name]
        handle = next((r.get('handle') for r in rs if r.get('handle')), None)
        sciper = next((r.get('sciper') for r in rs if r.get('sciper')), None)
        if not (handle or sciper):
            print(json.dumps(dict(name=name, skipped='no handle or SCIPER in the sweep'))); continue
        url = f'https://people.epfl.ch/{handle or sciper}?lang=en'
        r, st = get(s, url, 3)
        if r is None:
            wb = 'https://web.archive.org/web/2026id_/' + url
            r, st2 = get(s, wb, 10)
            url, st = (wb, 200) if r is not None else (url, st)
        c.execute('INSERT OR REPLACE INTO pages VALUES (?,?,?,?,?,?)', (url, r.url if r is not None else None, st if isinstance(st, int) else -1,
                                                                      datetime.now(timezone.utc).isoformat(), hashlib.sha256(r.content).hexdigest() if r is not None else None,
                                                                      zlib.compress(r.content) if r is not None else None))
        c.commit()
        print(json.dumps(dict(name=name, url=url, status=st)), flush=True)


if __name__ == '__main__':
    main(sys.argv[1:])
