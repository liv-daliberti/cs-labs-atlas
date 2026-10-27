"""Evidence helpers for the Berkeley CS-related review: every quote is checked to be an exact substring of the stored capture."""
import json, re
from lib import *

class Missing(Exception):
    pass

def page(url):
    h = mpcap.cached(url)
    if not h:
        raise Missing(f'no stored capture: {url}')
    return h

def E(url, needle):
    h = page(url)
    if needle not in h['text']:
        raise Missing(f'quote not in {url}: {needle!r}')
    return dict(url=url, sha256=h['sha256'], quote=needle)

def observed(url):
    m = mpcap.WAYBACK_RX.match(url)
    if m:
        t = m.group(1); return f'{t[:4]}-{t[4:6]}-{t[6:8]}'
    con = mpcap.connect()
    fa = con.execute('select fetched_at from captures where (url=? or capture_url=?) and status=200 order by id desc', (url, url)).fetchone()[0]
    con.close(); return fa[:10]

def L(url, needle, kind):
    r = E(url, needle); r['observed'] = observed(url); r['kind'] = kind; return r

def DISS(needle):
    """An EECS dissertations-by-year entry containing needle."""
    con = mpcap.connect()
    rows = con.execute("select url from captures where status=200 and url like '%Pubs/Dissertations/Years/%'").fetchall(); con.close()
    for (u,) in rows:
        if needle in page(u)['text']:
            return E(u, needle)
    raise Missing(f'dissertation entry not found: {needle!r}')

def MATH(needle):
    con = mpcap.connect()
    rows = con.execute("select url from captures where status=200 and url like 'https://math.berkeley.edu/people/past-department-members/past-phd-students%' order by id").fetchall(); con.close()
    for (u,) in rows:
        if needle in page(u)['text']:
            return E(u, needle)
    raise Missing(f'math thesis entry not found: {needle!r}')

def OA(author, inst):
    """The OpenAlex author record's affiliation entry for institution inst (exact JSON substring)."""
    u = 'https://api.openalex.org/authors/' + author.split('/')[-1]
    t = page(u)['text']
    key = '"display_name":' + json.dumps(inst)
    i = t.find(key)
    if i < 0:
        raise Missing(f'{inst} not in {u}')
    j = t.find('"years":', i)
    k = t.find(']', j)
    return E(u, t[i:k + 1])

def OA_orcid(author):
    d = json.loads(page('https://api.openalex.org/authors/' + author.split('/')[-1])['text'])
    o = d.get('orcid')
    return o.replace('https://orcid.org/', '') if o else None

def EECS(names, one_per_year=True):
    rows = eecs_rows(names)
    if not one_per_year:
        return rows
    out, seen = [], set()
    for r in rows:
        y = r['observed'][:4]
        if y not in seen:
            seen.add(y); out.append(r)
    return out
