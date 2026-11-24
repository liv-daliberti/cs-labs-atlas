"""Yearly Wayback captures of CMU SCS faculty listings the sweep lacks, one capture per year 2016-2026 (CDX
collapse=timestamp:4, status 200), raw bytes (id_), kept in census/captures-cmu.sqlite with sha256. Wayback is paced
at one request per 5 s; nothing behind a bot wall is fetched.
usage: fetch_listings.py
"""
import hashlib, json, sqlite3, time, zlib
from datetime import datetime, timezone
from pathlib import Path
import requests

HERE = Path(__file__).resolve().parents[1]
UA = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'
TARGETS = {  # listing url (CDX exact) -> (department, listing kind)
    'ml.cmu.edu/people/core-faculty.html': ('MLD', 'core_faculty'),
    'ml.cmu.edu/people/affiliated-faculty.html': ('MLD', 'affiliated_faculty'),
    'ml.cmu.edu/people/adjunct-faculty.html': ('MLD', 'adjunct_faculty'),
    'csd.cs.cmu.edu/directory/faculty': ('CSD', 'faculty_directory'),
    'csd.cmu.edu/people/faculty': ('CSD', 'faculty'),
    'www.cs.cmu.edu/directory/all': ('SCS', 'directory_all'),
}


def main():
    db = sqlite3.connect(str(HERE / 'captures-cmu.sqlite'))
    db.execute('CREATE TABLE IF NOT EXISTS pages (url TEXT PRIMARY KEY, original TEXT, timestamp TEXT, dept TEXT, kind TEXT, status INTEGER, sha256 TEXT, body BLOB, fetched_at TEXT)')
    s = requests.Session(); s.headers['User-Agent'] = UA
    last = 0.0
    def get(url):
        nonlocal last
        time.sleep(max(0, 5 - (time.monotonic() - last))); last = time.monotonic()
        return s.get(url, timeout=(20, 120))
    for target, (dept, kind) in TARGETS.items():
        r = get(f'https://web.archive.org/cdx/search/cdx?url={target}&output=json&fl=timestamp,original,statuscode&filter=statuscode:200&collapse=timestamp:4&from=2016&to=2026')
        rows = r.json()[1:] if r.status_code == 200 and r.text.strip() else []
        for ts, orig, st in rows:
            url = f'https://web.archive.org/web/{ts}id_/{orig}'
            if db.execute('SELECT 1 FROM pages WHERE url=?', (url,)).fetchone():
                continue
            try:
                p = get(url)
            except requests.RequestException as e:
                print(json.dumps(dict(url=url, error=type(e).__name__)), flush=True); continue
            body = p.content if p.status_code == 200 else b''
            db.execute('INSERT OR REPLACE INTO pages VALUES (?,?,?,?,?,?,?,?,?)', (url, orig, ts, dept, kind, p.status_code, hashlib.sha256(body).hexdigest() if body else None,
                                                                                   zlib.compress(body) if body else None, datetime.now(timezone.utc).isoformat()))
            db.commit()
            print(json.dumps(dict(url=url, status=p.status_code, bytes=len(body))), flush=True)
    print(json.dumps(dict(pages=db.execute('SELECT count(*) FROM pages WHERE status=200').fetchone()[0])), flush=True)


if __name__ == '__main__':
    main()
