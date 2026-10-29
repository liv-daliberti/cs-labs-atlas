"""Sweep every OpenAlex work 2016-2026 with an authorship affiliated to one school (institution lineage), at most 100 authors.

Each authorship keeps its own institutions and raw affiliation strings, so 'the PI's authorship lists the school' is read
per author position, not per paper. One cursor per publication year; pages are stored zlib-compressed in
hierarchy/<school>/openalex-sweep.sqlite and a rerun resumes from the last stored cursor.

usage: oa_sweep.py <school> [<school> ...]       (OPENALEX_API_KEY from the environment, e.g. ~/.config/cs-atlas/openalex.env;
       OPENALEX_FLOOR credits are left unspent)
       Without OPENALEX_API_KEY the sweep runs on the keyless daily budget (1000 list queries per IP, shared; Stanford
       2026-10-27): set OPENALEX_FLOOR low (e.g. 40) and rerun after the budget resets (00:00 UTC) to resume.
"""
import json, os, sqlite3, sys, time, zlib
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402  (every path in one place)
HERE = P.WORK
INST = {'princeton': 'I20089843', 'cmu': 'I74973139', 'epfl': 'I5124864', 'mit': 'I63966007', 'berkeley': 'I95457486', 'stanford': 'I97018004'}
YEARS = range(2016, 2027)
SELECT = 'id,doi,title,publication_year,publication_date,type,authorships,ids,primary_location'
UA = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'


def db(school):
    p = HERE / 'hierarchy' / school; p.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(p / 'openalex-sweep.sqlite')
    c.execute('create table if not exists pages (year int, page int, cursor text, next_cursor text, n int, count int, fetched_at text, body blob, primary key (year, page))')
    return c


def sweep(school, key, floor):
    c = db(school); inst = INST[school]; s = requests.Session(); s.headers['User-Agent'] = UA
    for y in YEARS:
        last = c.execute('select page, next_cursor, count from pages where year=? order by page desc limit 1', (y,)).fetchone()
        page, cursor = (last[0] + 1, last[1]) if last else (0, '*')
        while cursor:
            for attempt in range(6):
                try:
                    r = s.get('https://api.openalex.org/works', timeout=120, params={**({'api_key': key} if key else {}), 'filter': f'authorships.institutions.lineage:{inst},publication_year:{y},authors_count:<101',
                        'per-page': 200, 'cursor': cursor, 'select': SELECT})
                except requests.RequestException as e:
                    time.sleep(5 * (attempt + 1)); continue
                if r.status_code == 200:
                    try:
                        j = r.json(); break
                    except ValueError:  # a truncated body: retry the same cursor
                        time.sleep(5 * (attempt + 1)); continue
                if r.status_code == 429 and int(r.headers.get('X-RateLimit-Remaining') or 1) <= 0:
                    print(json.dumps({'school': school, 'stopped': 'daily credits spent', 'year': y})); return False
                time.sleep(5 * (attempt + 1))
            else:
                print(json.dumps({'school': school, 'failed': y, 'page': page, 'status': r.status_code})); return False
            nxt = j['meta'].get('next_cursor') if j['results'] else None
            c.execute('insert or replace into pages values (?,?,?,?,?,?,?,?)', (y, page, cursor, nxt, len(j['results']), j['meta']['count'],
                      time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), zlib.compress(json.dumps(j['results']).encode(), 6)))
            c.commit(); page += 1; cursor = nxt
            rem = int(r.headers.get('X-RateLimit-Remaining') or 10**6)
            if rem < floor:
                print(json.dumps({'school': school, 'stopped': 'credit floor', 'remaining': rem, 'year': y})); return False
            time.sleep(0.3)
        n = c.execute('select sum(n), max(count) from pages where year=?', (y,)).fetchone()
        print(json.dumps({'school': school, 'year': y, 'works': n[0], 'count': n[1]}), flush=True)
    return True


def sweep_paged(school, floor, key=None):
    """Keyless mode (no OPENALEX_API_KEY; cursor paging needs a key): one date window per month, page-number paging
    (page * 200 <= 10000 per window; a window over that is split in half until it fits). Stored like the cursor sweep:
    (year, page) with page = month * 1000 + window page, cursor = 'window:<from>..<to>;page=<n>'. Rerun resumes."""
    import calendar, datetime
    c = db(school); inst = INST[school]; s = requests.Session(); s.headers['User-Agent'] = UA
    c.execute('create table if not exists windows (wfrom text, wto text, pages int, count int, done int, primary key (wfrom, wto))')

    def get(params):
        for attempt in range(6):
            try:
                r = s.get('https://api.openalex.org/works', timeout=120, params={**params, **({'api_key': key} if key else {})})
            except requests.RequestException:
                time.sleep(5 * (attempt + 1)); continue
            if r.status_code == 200:
                try:
                    return r, r.json()
                except ValueError:
                    time.sleep(5 * (attempt + 1)); continue
            if r.status_code == 429:
                return r, None
            time.sleep(5 * (attempt + 1))
        return r, None

    def window(y, m, a, b, slot):
        if c.execute('select done from windows where wfrom=? and wto=?', (a, b)).fetchone() == (1,):
            return True
        base = {'filter': f'authorships.institutions.lineage:{inst},from_publication_date:{a},to_publication_date:{b},authors_count:<101',
                'per-page': 200, 'select': SELECT, 'sort': 'publication_date:asc'}
        r, j = get(dict(base, page=1))
        if j is None:
            print(json.dumps({'school': school, 'failed': a, 'status': r.status_code})); return False
        cnt = j['meta']['count']
        if cnt > 10000:
            d0 = datetime.date.fromisoformat(a); d1 = datetime.date.fromisoformat(b); mid = d0 + (d1 - d0) / 2
            return window(y, m, a, mid.isoformat(), slot * 2) and window(y, m, (mid + datetime.timedelta(days=1)).isoformat(), b, slot * 2 + 1)
        npg = (cnt + 199) // 200
        for pg in range(1, npg + 1):
            key = m * 1000 + slot * 60 + pg
            if c.execute('select 1 from pages where year=? and page=?', (y, key)).fetchone():
                continue
            if pg > 1:
                r, j = get(dict(base, page=pg))
                if j is None:
                    print(json.dumps({'school': school, 'failed': a, 'page': pg, 'status': r.status_code})); return False
            c.execute('insert or replace into pages values (?,?,?,?,?,?,?,?)', (y, key, f'window:{a}..{b};page={pg}', None, len(j['results']), cnt,
                      time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), zlib.compress(json.dumps(j['results']).encode(), 6)))
            c.commit()
            rem = int(r.headers.get('X-RateLimit-Remaining') or 10**6)
            if rem < floor:
                print(json.dumps({'school': school, 'stopped': 'credit floor', 'remaining': rem, 'window': a})); return False
            time.sleep(1.0)
        c.execute('insert or replace into windows values (?,?,?,?,1)', (a, b, npg, cnt)); c.commit()
        return True

    for y in YEARS:
        for m in range(1, 13):
            a = f'{y}-{m:02d}-01'; b = f'{y}-{m:02d}-{calendar.monthrange(y, m)[1]}'
            if not window(y, m, a, b, 1):
                return False
        n = c.execute('select sum(n) from pages where year=?', (y,)).fetchone()
        print(json.dumps({'school': school, 'year': y, 'works': n[0]}), flush=True)
    return True


if __name__ == '__main__':
    key = os.environ.get('OPENALEX_API_KEY'); floor = int(os.environ.get('OPENALEX_FLOOR') or 1500)
    for school in sys.argv[1:]:
        # a school whose sweep started in month windows (keyless) stays in month windows: the cursor sweep would read a
        # half-done year's last stored page as the year's end. A key only raises the budget there.
        c_ = db(school)
        paged = c_.execute("select count(*) from sqlite_master where name='windows'").fetchone()[0] and c_.execute('select count(*) from windows').fetchone()[0]
        sweep_paged(school, floor, key) if (paged or not key) else sweep(school, key, floor)
