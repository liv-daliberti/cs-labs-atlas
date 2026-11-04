"""Polite crawl of a repository's dissertation item pages for the ADVISER field (2026-11-04, owner), as an adviser-bearing student source.

Why: stage 6 prefers dissertations with an advisor field, but the two onboarding repositories give it only on the item page (Georgia Tech's
OAI-PMH is disallowed; UChicago's oai_dc carries no contributors). Configuration per school in the charter, section [etd_crawl]:
    host         the one host crawled (one flock per host, strictly sequential)
    delay        seconds between requests (raised to the host's Crawl-delay)
    enumerate    "sitemap"  sitemap (index) URL + url_rx: the item URLs the robots-listed sitemap names
                 "oai"      the school's OAI harvest (raw/oai_repo/<school>.sqlite) rows whose type matches oai_type_rx; the record
                            pages are the queue (only dissertations are fetched)
    parser       "dspace7" (Georgia Tech SMARTech item pages: Author(s) / Advisor(s) / Resource Subtype) | "invenio" (UChicago Knowledge)
robots.txt (this client, ClaudeBot, anthropic-ai) is checked for every URL before it is fetched; a 403/429-after-retries, a login page 25 times
running or a non-HTML body stops the crawl (state kept). Resumable: raw/etd_crawl/<school>.sqlite (queue, pages), one file per school.
Only the fields we need are stored per page: title, author, degree/type, year, department, advisors, URL, sha256 of the page, and a short
verbatim quote of the metadata block. Nothing else of the page is kept.
usage: etd_crawl.py enumerate <school> | add <school> <urls-or-sitemap file> [--rx R] [--front] | crawl <school> [--max N] | evidence <school> [--out FILE] | stats <school>
`evidence` matches each dissertation's advisor to the school's PIs (full name, pihier.names.Name) and writes thesis-evidence rows:
{pi, students: [{name, role, years, url, sha256, quote, note}]} (the format tools/pihier/students.py RESEARCHED_FILES reads).
"""
import fcntl
import hashlib
import json
import re
import sqlite3
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F  # noqa: E402
import oai_repo as O  # noqa: E402

WINDOW = (2016, 2026)
LOGIN_STOP = 25
TRANSIENT_STOP = 12
DISS_RX = re.compile(r'dissertation|doctoral|ph\.?\s?d|doctor of', re.I)


def base_school(school):
    return school.split('@')[0]


def cfg(school):
    """The charter's [etd_crawl] section; 'gatech@wayback' reads [etd_crawl_wayback] of gatech (its own queue and table, so one crawl per host)."""
    import school_config as SC
    base, _, suffix = school.partition('@')
    return dict(SC.field(SC.get(base), 'etd_crawl' + (f'_{suffix}' if suffix else ''), {}) or {})


def db_path(school):
    return F.P.FT_RAW / 'etd_crawl' / f'{school}.sqlite'


def connect(school):
    p = db_path(school)
    p.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(p), timeout=120)
    c.executescript("""
    CREATE TABLE IF NOT EXISTS queue (url TEXT PRIMARY KEY, seq INTEGER, hint TEXT, status TEXT DEFAULT 'pending', at TEXT);
    CREATE TABLE IF NOT EXISTS pages (url TEXT PRIMARY KEY, sha256 TEXT, fetched_at TEXT, dissertation INTEGER, title TEXT, author TEXT,
        degree TEXT, year INTEGER, department TEXT, advisors TEXT, quote TEXT);
    CREATE TABLE IF NOT EXISTS state (k TEXT PRIMARY KEY, v TEXT);
    """)
    return c


# ------------------------------------------------------------------------------------------------------------------ parsers

def _soup(html_bytes):
    from bs4 import BeautifulSoup
    return BeautifulSoup(html_bytes, 'lxml')


def _text(node):
    return re.sub(r'\s+', ' ', node.get_text(' ')).strip()


def _meta(soup, name):
    return [m.get('content', '').strip() for m in soup.find_all('meta', attrs={'name': name}) if m.get('content')]


def parse_dspace7(body, hint=None):
    """Georgia Tech SMARTech (DSpace 7 server-side render): Author(s) / Advisor(s) / Date / Resource Subtype blocks. A page the renderer
    answered with its login view has no item and gives None (counted as 'login')."""
    s = _soup(body)
    title = (s.title.get_text() if s.title else '').strip()
    if title.endswith(':: Login') or not _meta(s, 'citation_title'):
        return None
    fields = {}
    for h in s.find_all('h2', class_='simple-view-element-header'):
        body_el = h.find_next_sibling('div')
        if not body_el:
            continue
        names = [_text(a) for a in body_el.select('a, span.dont-break-out') if _text(a)]
        fields[_text(h)] = names or ([_text(body_el)] if _text(body_el) else [])
    advisors = [n for n in fields.get('Advisor(s)', []) if n]
    authors = _meta(s, 'citation_author') or fields.get('Author(s)', [])
    sub = ' '.join(fields.get('Resource Subtype', []))
    date = ' '.join(fields.get('Date', [])) or (_meta(s, 'citation_publication_date') or [''])[0]
    units = [n for n in fields.get('Associated Organization(s)', []) if n]
    ym = re.search(r'\b(19|20)\d\d\b', date)
    quote = f"Author(s) {'; '.join(authors)} | Advisor(s) {'; '.join(advisors)} | Date {date} | Resource Subtype {sub}"
    return dict(title=_meta(s, 'citation_title')[0], author=authors[0] if authors else '', degree=sub, year=int(ym.group(0)) if ym else None,
                department='; '.join(units[:3]), advisors=advisors, dissertation=bool(DISS_RX.search(sub)), quote=quote[:400])


def parse_invenio(body, hint=None):
    """UChicago Knowledge (InvenioRDM record page): Creators, 'Advisor:' contributors, 'Published <Month> <Year>', Department(s)."""
    s = _soup(body)
    if not _meta(s, 'citation_title'):
        return None
    advisors, committee = [], []
    for h in s.find_all('h3', class_='creatibutors-header'):
        ul = h.find_next_sibling('ul')
        names = [_text(n) for n in (ul.select('.creatibutor-name') if ul else [])]
        label = _text(h).lower()
        if label.startswith('advisor') or label.startswith('adviser') or 'chair' in label:
            advisors += names
        else:
            committee += names
    txt = _text(s)
    ym = re.search(r'Published\s+(?:[A-Z][a-z]+\s+)?((?:19|20)\d\d)', txt)
    dep = ''
    for dt in s.find_all('dt'):
        if _text(dt).startswith('Department'):
            dd = dt.find_next_sibling('dd')
            dep = _text(dd) if dd else ''
    authors = _meta(s, 'citation_author')
    rt = re.search(r'Version v\d+\s+(\w[\w ]*?)\s+(?:Open|Restricted|Embargoed|Closed)\b', txt)
    typ = rt.group(1) if rt else ''
    quote = f"Creators {'; '.join(authors)} | Advisor: {'; '.join(advisors)} | Published {ym.group(1) if ym else ''} | {typ} | Department(s) {dep}"
    return dict(title=_meta(s, 'citation_title')[0], author=authors[0] if authors else '', degree=typ, year=int(ym.group(1)) if ym else None,
                department=dep, advisors=advisors, dissertation=bool(DISS_RX.search(typ)), quote=quote[:400])


def parse_smartech(body, hint=None):
    """The old SMARTech (DSpace 6, smartech.gatech.edu/handle/1853/<n>) as Wayback captured it. A '?show=full' capture has the table dc.contributor.advisor /
    dc.type / dc.description.degree / dc.contributor.department. A plain capture has no table, but its DC.* meta tags come in the record's field order:
    the advisor is the DC.contributor that precedes DC.creator (the later DC.contributor values are the department and the committee); it is only
    taken for a Dissertation or Thesis, and the quote says it came from the meta tags."""
    s = _soup(body)
    rows = {}
    for tr in s.select('table.detailtable tr, table.itemDisplayTable tr'):
        td = [_text(x) for x in tr.find_all('td')]
        if len(td) >= 2 and td[0].count('.') >= 1:
            rows.setdefault(td[0], []).append(td[1])
    handle = (hint or {}).get('handle', '')
    if rows.get('dc.title'):
        advisors = rows.get('dc.contributor.advisor', [])
        typ = ' '.join(rows.get('dc.type', []))
        deg = ' '.join(rows.get('dc.description.degree', []) + rows.get('thesis.degree.level', []))
        date = (rows.get('dc.date.issued') or rows.get('dc.date.submitted') or rows.get('dc.date.created') or [''])[0]
        dep = '; '.join(rows.get('dc.contributor.department', []))
        author = (rows.get('dc.contributor.author') or [''])[0]
        title = rows['dc.title'][0]
        quote = (f"dc.contributor.advisor {'; '.join(advisors)} | dc.contributor.author {author} | dc.date.issued {date} | dc.type {typ} | "
                 f"dc.description.degree {deg} | dc.contributor.department {dep}")
    else:
        metas = [(m.get('name'), (m.get('content') or '').strip()) for m in s.find_all('meta') if (m.get('name') or '').startswith('DC.')]
        if not any(n == 'DC.title' for n, _ in metas):
            return None
        names = [n for n, _ in metas]
        typ = next((v for n, v in metas if n == 'DC.type'), '')
        creator = names.index('DC.creator') if 'DC.creator' in names else -1
        before = [v for n, v in metas[:creator] if n == 'DC.contributor'] if creator > 0 else []
        advisors = before[:1] if re.search(r'dissertation|thesis', typ, re.I) else []
        deg = next((v for n, v in metas if n == 'DC.description' and re.fullmatch(r'(?:Ph\.?\s?D\.?|M\.?S\.?|M\.?\s?Eng\.?|M\.?Arch\.?|[A-Z][A-Za-z.]{1,8})', v)), '')
        date = next((v for n, v in metas if n == 'DC.date'), '')
        after = [v for n, v in metas[creator:] if n == 'DC.contributor'] if creator >= 0 else []
        dep = after[0] if after else ''
        author = next((v for n, v in metas if n == 'DC.creator'), '')
        title = next(v for n, v in metas if n == 'DC.title')
        quote = f"DC.contributor {'; '.join(advisors)} (before DC.creator) | DC.creator {author} | DC.date {date} | DC.type {typ} | DC.description {deg} | DC.contributor {dep}"
    ym = re.search(r'\b(19|20)\d\d\b', date)
    typ_full = f"{typ} {deg}".strip()
    return dict(title=title, author=author, degree=typ_full, year=int(ym.group(0)) if ym else None, department=dep, advisors=advisors,
                dissertation=bool(re.search(r'dissertation|doctoral|ph\.?\s?d', typ_full, re.I)), quote=quote[:500], handle=handle)


PARSERS = dict(dspace7=parse_dspace7, invenio=parse_invenio, smartech=parse_smartech)


# ------------------------------------------------------------------------------------------------------------------ enumerate

def sitemap_urls(client, url, rx, tries=4):
    """Item URLs of a sitemap or sitemap index (nested sitemaps followed), in listed order, filtered by regex. A response that ends before its
    closing tag (a 7 MB sitemap cut off on 2026-11-04) is asked again, up to `tries` times, never parsed as complete."""
    sizes = []
    for attempt in range(tries):
        text = client.get(url).content.decode('utf8', 'replace')
        if re.search(r'</(urlset|sitemapindex)>\s*$', text):
            break
        sizes.append(len(text))
        print(json.dumps(dict(sitemap_truncated=url, bytes=len(text), attempt=attempt)), flush=True)
        if len(sizes) >= 2 and sizes[-1] == sizes[-2]:
            # the same cut twice: the server ends the file there (Georgia Tech sitemap1.xml, 955,812 bytes, 2026-11-04). The complete <loc>
            # entries before the cut are used; the entries after it are not listed anywhere we may read, and the crawl says so.
            text = text[:text.rfind('</url>') + 6] if '</url>' in text else text
            print(json.dumps(dict(sitemap_cut_server_side=url, bytes=len(text))), flush=True)
            break
        client.sleep(60 * (attempt + 1))
    else:
        raise O.Blocked(f'sitemap {url} stays truncated')
    locs = [u.strip() for u in re.findall(r'<loc>\s*([^<]+?)\s*</loc>', text)]
    if '<sitemapindex' in text[:2000]:
        return [u for sm in locs for u in sitemap_urls(client, sm, rx, tries)]
    return [u for u in locs if re.search(rx, u)]


def cdx_rows(client, conf):
    """Wayback CDX listing of the captured item pages (status 200, one row per URL key): (handle, kind, timestamp, original URL), the '?show=full' capture
    preferred over the plain one, the newest of each. Fetched through the page URL web.archive.org/web/<ts>id_/<original> (the capture as stored)."""
    r = client.get('https://web.archive.org/cdx/search/cdx', [('url', conf['cdx_url']), ('filter', 'statuscode:200'), ('filter', 'original:' + conf['cdx_original_rx']),
                                                              ('collapse', 'urlkey'), ('output', 'json'), ('fl', 'original,timestamp')])
    best = {}
    for orig, ts in r.json()[1:]:
        m = re.search(r'handle/1853/(\d+)(\?show=full)?$', orig)
        if not m:
            continue
        kind = 'full' if m.group(2) else 'plain'
        cur = best.setdefault(m.group(1), {})
        if kind not in cur or ts > cur[kind][0]:
            cur[kind] = (ts, orig)
    rows = []
    for h, v in best.items():
        kind = 'full' if 'full' in v else 'plain'
        ts, orig = v[kind]
        rows.append((h, kind, ts, orig))
    rows.sort(key=lambda x: (x[1] != 'full', -int(x[0])))   # explicit advisor first; high handles first (deposited 2016 onwards)
    return rows


def enumerate_queue(school, conf, client=None, out=print):
    c = connect(school)
    if conf.get('enumerate') == 'cdx':
        rows = [(f'https://web.archive.org/web/{ts}id_/{orig}', json.dumps(dict(handle=f'1853/{h}', kind=kind, ts=ts, original=orig)))
                for h, kind, ts, orig in cdx_rows(client, conf)]
    elif conf.get('enumerate') == 'oai':
        src = sqlite3.connect(f'file:{O.db_path(school)}?mode=ro', uri=True)
        rows = []
        for links, rtype, year in src.execute('SELECT links, rtype, year FROM records WHERE deleted=0'):
            if re.search(conf.get('oai_type_rx', 'doctoralThesis'), rtype or ''):
                u = next((x for x in json.loads(links) if '/records/' in x), None)
                if u:
                    rows.append((u, json.dumps(dict(rtype=rtype, year=year))))
    else:
        urls = sitemap_urls(client, conf['sitemap'], conf['url_rx'])
        rows = [(u, None) for u in urls]
    n0 = c.execute('SELECT COUNT(*) FROM queue').fetchone()[0]
    seq = n0
    for u, hint in rows:
        if not c.execute('SELECT 1 FROM queue WHERE url=?', (u,)).fetchone():
            c.execute('INSERT INTO queue (url, seq, hint) VALUES (?,?,?)', (u, seq, hint))
            seq += 1
    c.commit()
    out(json.dumps(dict(school=school, enumerated=len(rows), new=seq - n0)))
    return seq - n0


# ------------------------------------------------------------------------------------------------------------------ crawl

def url_allowed(rp_by_agent, url):
    return all(rp.can_fetch(url, a) for a, rp in rp_by_agent.items())


def load_robots(host, client):
    from protego import Protego
    r = client.s.get(f'https://{host}/robots.txt', timeout=(15, 30))
    text = r.text if r.status_code == 200 else ('' if r.status_code == 404 else 'User-agent: *\nDisallow: /\n')
    rp = Protego.parse(text)
    agents = (F.UA,) + O.AI_AGENTS
    return {a: rp for a in agents}, max([rp.crawl_delay(a) or 0 for a in agents])


def crawl(school, max_pages=None, out=print, client=None):
    conf = cfg(school)
    if not conf:
        out(json.dumps(dict(school=school, skipped='no [etd_crawl] section')))
        return None
    host = conf['host']
    lockf = F.P.FT_RAW / 'etd_crawl' / f'{host}.lock'
    lockf.parent.mkdir(parents=True, exist_ok=True)
    with open(lockf, 'w') as lk:
        try:
            fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            out(json.dumps(dict(school=school, stop=f'another crawl of {host} is running')))
            return None
        client = client or O.Client(max(float(conf.get('delay') or 10), float(conf.get('min_delay', 10))), low_priority=True)
        rp, cd = load_robots(host, client)
        client.delay = max(client.delay, float(cd or 0))
        out(json.dumps(dict(school=school, host=host, delay=client.delay, robots=dict(zip(['self', 'ClaudeBot', 'anthropic-ai'],
                                                                                           [rp[a].can_fetch(f'https://{host}/', a) for a in rp])))))
        c = connect(school)
        if not c.execute('SELECT 1 FROM queue LIMIT 1').fetchone():
            enumerate_queue(school, conf, client, out)
        parser = PARSERS[conf['parser']]
        done = logins = transients = 0
        try:
            while True:
                row = c.execute("SELECT url, hint FROM queue WHERE status='pending' ORDER BY seq LIMIT 1").fetchone()
                if not row or (max_pages and done >= max_pages):
                    break
                url, hint = row
                hint = json.loads(hint) if hint else {}
                if urlsplit(url).netloc != host or not url_allowed(rp, url):
                    c.execute("UPDATE queue SET status='robots', at=? WHERE url=?", (F.now(), url))
                    c.commit()
                    continue
                try:
                    r = client.get(url, tolerate=(404, 410))
                except O.Transient as e:  # the server is ill, not refusing: wait and ask again; the URL stays pending
                    transients += 1
                    out(json.dumps(dict(school=school, transient=str(e), wait=1800, in_a_row=transients, at=F.now())))
                    if transients >= TRANSIENT_STOP:
                        raise O.Blocked(f'{TRANSIENT_STOP} failed rounds in a row (each after the client\'s own back-offs)') from e
                    client.sleep(1800)
                    continue
                transients = 0
                st = 'done'
                if r.status_code in (404, 410):
                    st = 'gone'
                elif b'Temporarily Offline' in r.content[:6000] or (not r.content.strip() and r.status_code == 200):
                    # an Internet Archive outage page or an empty answer: the service is ill, not refusing; wait and ask again (the URL stays pending)
                    transients += 1
                    out(json.dumps(dict(school=school, transient='offline or empty page', wait=1800, in_a_row=transients, at=F.now())))
                    if transients >= TRANSIENT_STOP:
                        raise O.Blocked(f'{TRANSIENT_STOP} offline rounds in a row')
                    client.sleep(1800)
                    continue
                elif b'<html' not in r.content[:4000].lower() and b'<!doctype' not in r.content[:200].lower():
                    st = 'nonhtml'   # a PDF, JSON or other body for this one URL: skipped, never a reason to stop
                else:
                    p = parser(r.content, hint)
                    if p is None:
                        st = 'login' if conf.get('stop_on_unparsed', True) else 'unparsed'
                        logins += 1
                        if conf.get('stop_on_unparsed', True) and logins >= LOGIN_STOP:
                            raise O.Blocked(f'{LOGIN_STOP} login views in a row: the host does not serve item pages to this client')
                    else:
                        logins = 0
                        if hint.get('rtype') and re.search(r'doctoral', hint['rtype'], re.I):
                            p['dissertation'] = True
                            p['degree'] = f"{p['degree']} (OAI type {hint['rtype'].rsplit('/', 1)[-1]})"
                        c.execute('INSERT OR REPLACE INTO pages VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                                  (url, hashlib.sha256(r.content).hexdigest(), F.now(), int(p['dissertation']), p['title'], p['author'], p['degree'],
                                   p['year'] or hint.get('year'), p['department'], json.dumps(p['advisors']), p['quote']))
                c.execute('UPDATE queue SET status=?, at=? WHERE url=?', (st, F.now(), url))
                c.commit()
                done += 1
                if done % 100 == 0:
                    out(json.dumps(stats(school)))
        except O.Blocked as e:
            out(json.dumps(dict(school=school, blocked=str(e), stats=stats(school))))
            return None
        out(json.dumps(dict(school=school, stats=stats(school))))
        return stats(school)


def add_urls(school, urls, front=False):
    """Queue more URLs (the one paced crawler fetches them; never a second client). front: ahead of everything pending. -> number added."""
    conf = cfg(school)
    c = connect(school)
    lo, hi = c.execute('SELECT COALESCE(MIN(seq), 0), COALESCE(MAX(seq), -1) FROM queue').fetchone()
    n = 0
    for u in urls:
        if urlsplit(u).netloc != conf['host'] or c.execute('SELECT 1 FROM queue WHERE url=?', (u,)).fetchone():
            continue
        seq = lo - 1 - n if front else hi + 1 + n
        c.execute('INSERT INTO queue (url, seq) VALUES (?,?)', (u, seq))
        n += 1
    c.commit()
    return n


def stats(school):
    c = connect(school)
    q = dict(c.execute('SELECT status, COUNT(*) FROM queue GROUP BY status'))
    return dict(school=school, queue=q, pages=c.execute('SELECT COUNT(*) FROM pages').fetchone()[0],
                dissertations=c.execute('SELECT COUNT(*) FROM pages WHERE dissertation=1').fetchone()[0],
                with_advisor=c.execute("SELECT COUNT(*) FROM pages WHERE dissertation=1 AND advisors!='[]'").fetchone()[0])


# ------------------------------------------------------------------------------------------------------------------ evidence

def natural(name):
    """'Last, First M.' -> 'First M. Last'."""
    n = re.sub(r'\s+', ' ', name or '').strip()
    if ',' in n:
        last, _, first = n.partition(',')
        return f'{first.strip()} {last.strip()}'.strip()
    return n


MASTERS_UNIT_RX = re.compile(r'MAPSS|MACSS|MA Program|Master|Public Policy Theses|Chicago Studies|Committee on International Relations|Divinity|Humanities', re.I)


def role_of(degree, department=''):
    """phd for a dissertation record; masters when the record's own unit names a master's programme (UChicago's OAI types every thesis
    'doctoralThesis', its MA communities are named 'MA Program in the Social Sciences', 'MACSS', 'MA Theses')."""
    d = (degree or '').lower()
    if MASTERS_UNIT_RX.search(department or ''):
        return 'masters'
    if re.search(r'dissertation|doctoral|ph\.?\s?d|doctor of', d):
        return 'phd'
    return 'other'


def replay_url(url):
    """The Wayback fetch URL (.../<ts>id_/<orig>) -> the replay URL a reader opens (.../<ts>/<orig>)."""
    return re.sub(r'(/web/\d{14})id_/', r'\1/', url)


def build_evidence(school, pis, window=WINDOW, pi_window=None):
    """-> (rows in thesis-evidence.json shape, counts). pis: [{pi, names}] (hierarchy/<school>/derived/pis.json)."""
    if str(F.P.TOOLS) not in sys.path:
        sys.path.insert(0, str(F.P.TOOLS))
    from pihier.names import Name
    idx = {p['pi']: Name(list(dict.fromkeys([p['pi']] + list(p.get('names') or [])))) for p in pis}
    out, counts = {}, dict(dissertations=0, no_advisor=0, outside_window=0, no_pi=0, rows=0, ambiguous=0, duplicate_of_earlier_source=0)
    seen = set()  # (normalized title, author family): the live item pages come first, a Wayback copy of the same dissertation is not a second row
    sources = [school] + ([school + '@wayback'] if db_path(school + '@wayback').exists() else [])
    for src in sources:
        c = connect(src)
        found = set()
        for url, sha, title, author, degree, year, dep, advisors, quote in c.execute(
                'SELECT url, sha256, title, author, degree, year, department, advisors, quote FROM pages WHERE dissertation=1 ORDER BY url'):
            key = (F.nt(title)[:80], F.nt(natural(author).split()[-1] if natural(author) else ''))
            if key in seen:
                counts['duplicate_of_earlier_source'] += 1
                continue
            found.add(key)
            counts['dissertations'] += 1
            advs = json.loads(advisors)
            if not advs:
                counts['no_advisor'] += 1
                continue
            if not year or not (window[0] <= year <= window[1]):
                counts['outside_window'] += 1
                continue
            hit = False
            win_drop = False
            for a in advs:
                nat = natural(a)
                pi_hits = [p for p, nm in idx.items() if nm.match(nat)]
                if len(pi_hits) > 1:
                    counts['ambiguous'] += 1
                    continue
                for p in pi_hits:
                    hit = True
                    if pi_window and p in pi_window and not (pi_window[p][0] <= year <= pi_window[p][1]):
                        counts['outside_pi_appointment'] = counts.get('outside_pi_appointment', 0) + 1   # defense year outside the PI's listed years at the school
                        continue
                    out.setdefault(p, []).append(dict(
                        name=natural(author), role=role_of(degree, dep), years=[year, year], url=replay_url(url), sha256=sha, quote=quote,
                        note=f"{school} repository item page{' (Wayback capture of the old SMARTech page)' if '@' in src else ''} ({degree}; {dep}): '{title}'; advisor '{a}' = {p}"))
                    counts['rows'] += 1
            if not hit:
                counts['no_pi'] += 1
        seen |= found
    rows = [dict(pi=p, students=sorted(v, key=lambda s: (s['years'][0], s['name'])),
                 notes=f'Dissertation item pages crawled {time.strftime("%Y-%m-%d")} (etd_crawl.py): advisor field matched to the PI by full name.')
            for p, v in sorted(out.items())]
    return rows, counts


def main(argv):
    cmd, school = argv[0], argv[1]
    if cmd == 'enumerate':
        conf = cfg(school)
        client = O.Client(max(float(conf.get('delay') or 10), 10.0))
        enumerate_queue(school, conf, client)
    elif cmd == 'crawl':
        mx = int(argv[argv.index('--max') + 1]) if '--max' in argv else None
        crawl(school, mx)
    elif cmd == 'add':  # add <school> <file of URLs, or a saved sitemap> [--rx REGEX] [--front]
        conf = cfg(school)
        text = Path(argv[2]).read_text()
        rx = argv[argv.index('--rx') + 1] if '--rx' in argv else conf.get('url_rx', '.')
        urls = re.findall(r'<loc>\s*([^<]+?)\s*</loc>', text) if '<loc>' in text else text.split()
        print(json.dumps(dict(school=school, added=add_urls(school, [u for u in urls if re.search(rx, u)], '--front' in argv))))
    elif cmd == 'stats':
        print(json.dumps(stats(school)))
    elif cmd == 'evidence':
        pis = json.loads(F.P.data('pis.json', school).read_text())
        if str(F.P.TOOLS) not in sys.path:
            sys.path.insert(0, str(F.P.TOOLS))
        import periods_school as PS
        pw = {t['name']: (t['first'], max(t['years'] or [2026])) for t in PS.targets(school)}   # listed years at the school
        rows, counts = build_evidence(school, pis, pi_window=pw)
        outp = Path(argv[argv.index('--out') + 1]) if '--out' in argv else None
        if outp:
            outp.write_text(json.dumps(rows, indent=1, ensure_ascii=False))
        print(json.dumps(counts))


if __name__ == '__main__':
    main(sys.argv[1:])
