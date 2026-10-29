"""Plan of department listing captures used for yearly rows (table plan_csr in hierarchy/cmu/cs-related-captures.sqlite)."""
import json, re, sqlite3
import csrcap

H = "home department faculty list"


def slot(dept, name, kind='main'):
    return dict(dept=dept, slot=name, kind=kind, listing_label=H)


def ensure(con):
    con.execute('''CREATE TABLE IF NOT EXISTS plan_csr (slot TEXT, dept TEXT, year INTEGER, half TEXT, page_url TEXT, capture_url TEXT,
                   wayback_timestamp TEXT, status TEXT, slot_json TEXT, PRIMARY KEY (slot, capture_url))''')


def add(dept, slot_name, capture_url, page_url=None, kind='main'):
    """Register a stored 200 capture (live page or Wayback id_ capture) as a listing for its year."""
    h = csrcap.cached(capture_url)
    if not h:
        return None
    con = csrcap.connect(); ensure(con)
    m = re.match(r'https://web\.archive\.org/web/(\d{14})id_/(.*)$', capture_url)
    if m:
        wts, page = m.group(1), m.group(2)
    else:
        fa = con.execute('select fetched_at from captures where id=?', (h['id'],)).fetchone()[0]
        wts, page = re.sub(r'\D', '', fa)[:14], capture_url
    half = 'H1' if int(wts[4:6]) <= 6 else 'H2'
    con.execute('INSERT OR REPLACE INTO plan_csr VALUES (?,?,?,?,?,?,?,?,?)', (slot_name, dept, int(wts[:4]), half, page_url or page, capture_url, wts, 'ok',
                                                                             json.dumps(slot(dept, slot_name, kind))))
    con.commit(); con.close()
    return wts
