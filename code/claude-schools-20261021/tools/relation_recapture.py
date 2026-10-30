"""Re-capture the evidence of whitelisted student relations and quote it (2026-10-29).

Why: tools/evidence_check.py wants every student relation (hierarchy/<school>/students.json) to carry a source with url,
a 64-hex sha256 and a non-empty verbatim quote. The CMU, EPFL and MIT site collections stored bare URLs, hashes without
quotes, or DSpace item API records behind an unhashed metadata snapshot (docs/evidence-whitelist.json). This tool fetches
the cited pages again, stores the exact bytes, and quotes the student (and the advisor or the advisor's lab) verbatim.

Inputs (read only)
  hierarchy/<school>/students.json          relations that fail evidence_check.sourced (nothing else is planned)
  hierarchy/<school>/student_papers.jsonl.gz byline links whose relation_source fails sourced (their url is planned too)
  hierarchy/<school>/pis.json               PI name variants (names) and lab names (lab.name; EPFL lab acronyms)
  local capture stores (scoped, no traversal): hierarchy/*captures*.sqlite and hierarchy/<school>/*captures*.sqlite
                                            (zlib content), looked up by cited url / capture url / original sha256
Outputs
  hierarchy/<school>/relation-captures.sqlite  table captures(url, capture_url, fetched_at, status, sha256 of the exact
                                            bytes, content_type, content = gzip of the bytes, error, method, observed,
                                            original_sha256, matches_original, body_ref = id of the row that holds a
                                            shared batch body); one row per attempt, the best 200 row wins (a row with
                                            its own content before a batch row, the newest first)
  hierarchy/<school>/relation-evidence.json {"_doc", "school", "made", "records": [{url, person, name, pi, capture_url,
                                            sha256, quote, names_pi, observed, original_sha256, matches_original,
                                            method}]} sorted by (url, person, pi); one record per (url, person, pi)
  hierarchy/logs/tmp-ids/recapture/extract-summary.json, estimate.json   outcome and before -> after counts

Capture order per cited url: (1) a local copy (same url, or same sha256 as the source carried); (2) a Wayback id_ url
is fetched as cited (its bytes should reproduce the stored sha256: matches_original); (3) API/OAI urls
(api.figshare.com, dspace.mit.edu/server/api, infoscience.epfl.ch/server, www.ri.cmu.edu/wp-json) are fetched live and
the JSON/XML response is the captured body; (4) DSpace item API urls are captured 50 at a time through one discover query
(/server/api/discover/search/objects?query=search.resourceid:(uuid OR ...)): the cited url's row points (body_ref) at
the stored batch response, whose sha256 it carries, and the quote comes from that item's element of the response
(--dspace-single re-captures such items through their own item API url, --dspace-rebatch N through N-item batches:
a 50-uuid capture url is ~1.9 kB, which would push mit/relation-evidence.json over 5 MB);
(5) any other page: the Wayback capture closest to the source's observation
date (its date / observedAt / fetched_at, else mid-year of the relation's last year), found with the Wayback
CDX API (one prefix query per directory of >= 3 cited pages), then the live url; with --live-first (used on
2026-10-29 because the Wayback Machine answered 503 at more than one request per 4 s) the live url comes first and
Wayback only when it fails.
Infoscience OAI ListRecords pages are cited by resumption-token offset; the offsets drifted since the 2026-10-19 harvest
(a record moves a page or so), so `fetch --oai-neighbors` captures the pages one offset step before and after each cited
page, and `extract` looks for a student missing from the cited page on the adjacent pages (+-100, +-200, +-300 records)
it holds: such a record keeps the cited url, names the adjacent page as capture_url, and has matches_original false.

Quotes: copied from the captured text, whitespace-collapsed (HTML: visible text; JSON/XML: the raw text, escapes kept).
A quote names the student and, when names_pi is true, the PI or the PI's lab. When student and PI are not within one
short span of the same record (a roster row, a thesis record, a JSON element, an OAI record) the quote is two verbatim
excerpts of the same page in document order joined by " … " (for example a PI profile's title or the lab page heading
… the student's line; a thesis record's author field … its advisor field). A page that names the student but not the
PI/lab gives names_pi false and pi null. A page that does not name the student gives no record.

Politeness: at most one request per second per host (robots.txt Crawl-delay honoured when larger), one worker thread per
host; robots.txt is obeyed for our User-Agent, and a host whose robots.txt names ClaudeBot, Claude-Web, anthropic-ai or
Claude with a Disallow is not used at all (live or through Wayback); robots-disallowed origins are not fetched through
Wayback either; never dblp.org; 429/503 back off (60 s, 120 s, 240 s, then give up on that url) and double that host's
gap for the rest of the run (at most 20 s); a bot-challenge page
stops the host for the rest of the run. User-Agent: HomogenizingScienceResearch/0.2 (academic metadata inventory).

Re-runs are resumable: a cited url that already has a status-200 row (or a permanent failure: robots, challenge, 404
with no Wayback copy) in relation-captures.sqlite is skipped; only transient failures are retried (--retry-errors
retries every non-200). `extract` and `estimate` never touch the network.

usage: relation_recapture.py fetch   [--school S ...] [--max-minutes M] [--hosts H,...] [--live-first] [--retry-errors]
                                     [--oai-neighbors] [--dspace-single | --dspace-rebatch N] [--redo-live]
       relation_recapture.py extract [--school S ...]
       relation_recapture.py estimate [--school S ...]
       relation_recapture.py all     [--school S ...] [--max-minutes M]
Run with nice -n10 and the env Python (LD_LIBRARY_PATH=<env>/lib <env>/bin/python); stdlib + requests only.
"""
import argparse
import collections
import gzip
import hashlib
import json
import re
import sqlite3
import sys
import threading
import time
import unicodedata
import zlib
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote as urlquote, urlsplit

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402
from evidence_check import BYLINE_BASES, sourced  # noqa: E402

SCHOOLS = ['epfl', 'cmu', 'mit']
UA = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'
TMP = P.HIERARCHY / 'logs' / 'tmp-ids' / 'recapture'
TIMEOUT = (15, 90)
MIN_GAP = 1.05
AI_AGENTS = ('claudebot', 'claude-web', 'anthropic-ai', 'claude')
NEVER_HOSTS = {'dblp.org', 'www.dblp.org', 'dblp.uni-trier.de'}
API_RULES = [('api.figshare.com', '/v2/articles/', 'api'), ('dspace.mit.edu', '/server/api/', 'api'),
             ('infoscience.epfl.ch', '/server/oai', 'oai'), ('infoscience.epfl.ch', '/server/api/', 'api'),
             ('www.ri.cmu.edu', '/wp-json/', 'api'), ('search-api.epfl.ch', '/api/', 'api')]
CHALLENGE = re.compile(r'(cf-chl-|challenge-platform|<title>Just a moment\.\.\.|Attention Required! \| Cloudflare|'
                       r'Please verify you are a human|Access denied \| [\w.]+ used Cloudflare|hcaptcha\.com/1/api|'
                       r'Checking your browser before accessing)', re.I)
PERMANENT = ('robots', 'robots-ai', 'challenge', 'never-host', 'no-capture')


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def log(*a):
    print(datetime.now().strftime('%H:%M:%S'), *a, flush=True)


# ----------------------------------------------------------------------------------------------------------- planning
def load_json(p):
    p = Path(p)
    if str(p).endswith('.jsonl.gz'):
        return [json.loads(l) for l in gzip.open(p, 'rt')]
    return json.loads(p.read_text())


def wb_parts(url):
    m = re.match(r'https?://web\.archive\.org/web/(\d{4,14})(?:id_|if_|im_)?/(.*)$', url)
    return (m.group(1), m.group(2)) if m else (None, None)


def obs_date(src, years):
    """YYYYMMDD the source was observed: Wayback timestamp, else date/observedAt/fetched_at, else mid last year."""
    ts, _ = wb_parts(src.get('url') or '')
    if ts:
        return ts[:8]
    for k in ('date', 'observedAt', 'observedOn', 'fetched_at', 'fetchedAt'):
        v = str(src.get(k) or '')
        if re.match(r'\d{4}-\d{2}-\d{2}', v):
            return v[:10].replace('-', '')
    ys = [int(y) for y in years or [] if str(y).isdigit()]
    return f'{max(ys)}0701' if ys else None


def plan(school):
    """{url: {'targets': {(person, pi): {...}}, 'orig': set(sha), 'dates': [YYYYMMDD], 'relations': n}}"""
    D = P.HIERARCHY / school
    S = load_json(D / 'students.json')
    byid = {}
    for pi, recs in S.items():
        for s in recs:
            byid.setdefault(s['person'], s)
            for m in s.get('merged') or []:
                byid.setdefault(m, s)
    out = {}

    def add(u, s, pi, years, src):
        e = out.setdefault(u, dict(targets={}, orig=set(), dates=[], relations=0))
        e['relations'] += 1
        t = e['targets'].setdefault((s['person'], pi), dict(person=s['person'], name=s['name'], pi=pi,
                                                              aliases=list(s.get('aliases') or [])))
        sha = str(src.get('sha256') or '')
        if re.match(r'^[0-9a-f]{64}$', sha):
            e['orig'].add(sha)
        d = obs_date(src, years)
        if d:
            e['dates'].append(d)
        return t

    for pi, recs in S.items():
        for s in recs:
            for rel in s.get('relations') or []:
                if any(sourced(q) for q in rel.get('sources') or []):
                    continue
                for q in rel.get('sources') or []:
                    if q.get('url'):
                        add(q['url'], s, pi, rel.get('years'), q)
    links = load_json(D / 'student_papers.jsonl.gz')
    for x in links:
        rs = x.get('relation_source') or {}
        if x.get('basis') in BYLINE_BASES and not sourced(rs) and rs.get('url'):
            s = byid.get(x.get('student')) or dict(person=x.get('student'), name=x.get('name'))
            add(rs['url'], s, x['pi'], [], rs)
    return out


# ------------------------------------------------------------------------------------------------------------ storage
def db_path(school):
    return P.HIERARCHY / school / 'relation-captures.sqlite'


_dblock = threading.Lock()


def connect(school):
    con = sqlite3.connect(str(db_path(school)), timeout=120, check_same_thread=False)
    con.execute("""CREATE TABLE IF NOT EXISTS captures (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT NOT NULL,
        capture_url TEXT, fetched_at TEXT NOT NULL, status INTEGER, sha256 TEXT, content_type TEXT, content BLOB,
        error TEXT, method TEXT, observed TEXT, original_sha256 TEXT, matches_original INTEGER)""")
    con.execute('CREATE INDEX IF NOT EXISTS ix_rc_url ON captures(url)')
    if 'body_ref' not in [r[1] for r in con.execute('PRAGMA table_info(captures)')]:
        con.execute('ALTER TABLE captures ADD COLUMN body_ref INTEGER')  # id of the row holding a shared batch body
    con.commit()
    return con


def store(con, url, capture_url, status, body, ctype, method, observed, orig, error=None, fetched_at=None):
    sha = hashlib.sha256(body).hexdigest() if body is not None and status == 200 else None
    match = None if not orig or sha is None else int(sha in orig)
    with _dblock:
        con.execute('INSERT INTO captures(url,capture_url,fetched_at,status,sha256,content_type,content,error,method,'
                    'observed,original_sha256,matches_original) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                    (url, capture_url, fetched_at or now(), status, sha, ctype,
                     gzip.compress(body, 6, mtime=0) if body is not None and status == 200 else None, error, method,
                     observed, ','.join(sorted(orig)) or None, match))
        con.commit()
    return sha


def done_urls(con, retry_errors=False):
    ok, perm = set(), set()
    for u, st, err, ref, cu, meth in con.execute('SELECT url,status,error,body_ref,capture_url,method FROM captures'):
        if REDO_LIVE and meth == 'live':  # --redo-live: a live capture does not count (try Wayback for these urls)
            continue
        # --dspace-single / --dspace-rebatch redo items held only in a long (50-item) batch: its capture url is long
        if st == 200 and not ((DSPACE_SINGLE or DSPACE_REBATCH) and ref is not None and len(cu or '') > 800):
            ok.add(u)
        elif not retry_errors and err and err.split(':')[0] in PERMANENT:
            perm.add(u)
    return ok | perm


# ---------------------------------------------------------------------------------------------------- local lookups
def local_stores(school):
    fs = sorted(P.HIERARCHY.glob('*captures*.sqlite')) + sorted((P.HIERARCHY / school).glob('*captures*.sqlite'))
    return [f for f in fs if f.name != 'relation-captures.sqlite']


class Local:
    """Index of (url | capture_url | final_url) and sha256 -> (store, rowid) for rows with content, cited urls only."""

    def __init__(self, school, urls, shas):
        self.by_url, self.by_sha = {}, {}
        for f in local_stores(school):
            try:
                con = sqlite3.connect(f'file:{f}?mode=ro', uri=True)
                cols = [r[1] for r in con.execute('PRAGMA table_info(captures)')]
                if 'content' not in cols or 'sha256' not in cols:
                    continue
                uc = [c for c in ('url', 'capture_url', 'final_url') if c in cols]
                for row in con.execute(f"SELECT rowid,{','.join(uc)},sha256,status FROM captures "
                                       "WHERE content IS NOT NULL AND (status=200 OR status IS NULL)"):
                    for u in row[1:-2]:
                        if u in urls:
                            self.by_url.setdefault(u, (f, row[0]))
                    if row[-2] in shas:
                        self.by_sha.setdefault(row[-2], (f, row[0]))
                con.close()
            except sqlite3.Error:
                continue

    @staticmethod
    def read(ref):
        f, rid = ref
        con = sqlite3.connect(f'file:{f}?mode=ro', uri=True)
        cols = [r[1] for r in con.execute('PRAGMA table_info(captures)')]
        cu = 'capture_url' if 'capture_url' in cols else ('final_url' if 'final_url' in cols else 'url')
        row = con.execute(f'SELECT url,{cu},fetched_at,sha256,content_type,content FROM captures WHERE rowid=?',
                          (rid,)).fetchone()
        con.close()
        body = zlib.decompress(row[5])
        if hashlib.sha256(body).hexdigest() != row[3]:
            return None
        return dict(url=row[0], capture_url=row[1] or row[0], fetched_at=row[2], content_type=row[4], body=body)


# -------------------------------------------------------------------------------------------------------- fetching
class Net:
    def __init__(self):
        self.sess = requests.Session()
        self.sess.headers.update({'User-Agent': UA, 'Accept-Language': 'en', 'Accept-Encoding': 'gzip, deflate'})
        self.locks = collections.defaultdict(threading.Lock)
        self.next_ok = {}
        self.gap = {}
        self.robots = {}
        self.robots_lock = threading.Lock()
        self.blocked = {}  # host -> reason (challenge, ai-robots)

    def wait(self, host):
        lk = self.locks[host]
        lk.acquire()
        t = self.next_ok.get(host, 0) - time.monotonic()
        if t > 0:
            time.sleep(t)
        return lk

    def get(self, url, host=None):
        host = host or urlsplit(url).netloc.lower()
        if host in NEVER_HOSTS or host.endswith('.dblp.org'):
            return None, b'', None, 'never-host'
        if host in self.blocked:
            return None, b'', None, self.blocked[host]
        for attempt in range(4):
            lk = self.wait(host)
            try:
                r = self.sess.get(url, timeout=TIMEOUT, allow_redirects=True)
                body, st, ct = r.content, r.status_code, r.headers.get('content-type')
                err = None
            except Exception as e:  # network error: recorded, retried on a later run
                body, st, ct, err = b'', None, None, 'neterr:' + repr(e)[:300]
            finally:
                self.next_ok[host] = time.monotonic() + self.gap.get(host, MIN_GAP)
                lk.release()
            if st in (429, 503) or (st is None and 'Read timed out' in (err or '') and host.endswith('archive.org')):
                back = 60 * (2 ** attempt)
                self.gap[host] = min(max(2 * self.gap.get(host, MIN_GAP), 2.0), 20.0)  # slow this host for good
                log(f'  backoff {host} {st or err[:40]} {back}s; gap now {self.gap[host]:.1f}s')
                self.next_ok[host] = time.monotonic() + back
                continue
            if st in (403, 503, 200) and body and CHALLENGE.search(body[:20000].decode('utf-8', 'replace')) \
                    and not host.endswith('archive.org'):
                if st != 200 or len(body) < 20000:
                    self.blocked[host] = 'challenge'
                    return st, b'', ct, 'challenge'
            return st, body, ct, err
        return st, b'', ct, f'ratelimit:{st}'

    # robots ----------------------------------------------------------------------------------------------------
    def robots_rules(self, scheme, host):
        key = host
        with self.robots_lock:
            if key in self.robots:
                return self.robots[key]
        st, body, _, err = self.get(f'{scheme}://{host}/robots.txt', host)
        txt = body.decode('utf-8', 'replace') if st == 200 else ''
        if st in (401, 403):
            txt = 'User-agent: *\nDisallow: /\n'
        groups = parse_robots(txt)
        ai_block = any(any(a in AI_AGENTS or a.startswith('claude') for a in ag) and any(not al and p for al, p, in rules)
                       for ag, rules, _ in groups)
        mine = [g for g in groups if any(a != '*' and a in UA.lower() for a in g[0])] or \
               [g for g in groups if '*' in g[0]]
        rules = [r for g in mine for r in g[1]]
        delay = max([g[2] for g in mine if g[2]] or [0])
        res = dict(ai_block=ai_block, rules=rules, delay=delay)
        if delay:
            self.gap[host] = max(MIN_GAP, min(float(delay), 60.0))
        if ai_block:
            self.blocked[host] = 'robots-ai'
        with self.robots_lock:
            self.robots[key] = res
        return res

    def allowed(self, url):
        sp = urlsplit(url)
        host = sp.netloc.lower()
        r = self.robots_rules(sp.scheme or 'https', host)
        if r['ai_block']:
            return 'robots-ai'
        path = (sp.path or '/') + ('?' + sp.query if sp.query else '')
        best = None
        for allow, pat in r['rules']:
            if rule_match(pat, path) and (best is None or len(pat) > len(best[1]) or (len(pat) == len(best[1]) and allow)):
                best = (allow, pat)
        return None if best is None or best[0] else 'robots'


def parse_robots(txt):
    groups, agents, rules, delay, last_agent = [], [], [], None, False
    for raw in txt.splitlines():
        line = raw.split('#', 1)[0].strip()
        if ':' not in line:
            continue
        k, v = (x.strip() for x in line.split(':', 1))
        k = k.lower()
        if k == 'user-agent':
            if not last_agent and (agents or rules):
                groups.append((agents, rules, delay))
                agents, rules, delay = [], [], None
            agents.append(v.lower())
            last_agent = True
            continue
        last_agent = False
        if k in ('allow', 'disallow'):
            rules.append((k == 'allow', v))
        elif k == 'crawl-delay':
            try:
                delay = float(v)
            except ValueError:
                pass
    if agents or rules:
        groups.append((agents, rules, delay))
    return groups


def rule_match(pat, path):
    if not pat:
        return False
    rx = re.escape(pat).replace(r'\*', '.*')
    if rx.endswith(r'\$'):
        rx = rx[:-2] + '$'
    return re.match(rx, path) is not None


def api_method(url):
    sp = urlsplit(url)
    for h, pre, m in API_RULES:
        if sp.netloc.lower() == h and sp.path.startswith(pre):
            return m
    return None


def norm_url(u):
    u = re.sub(r'^https?://', '', u.strip().lower())
    u = re.sub(r'^www\.', '', u)
    u = re.sub(r'^([^/]+):80(?=/|$)', r'\1', u)
    return u.rstrip('/')


class WaybackIndex:
    """Status-200 Wayback timestamps per cited page, from one CDX prefix query per directory that holds >= 3 cited
    pages (else one exact CDX query per page), so a few hundred lookups become a few dozen."""

    def __init__(self, urls):
        self.group = {}
        dirs = collections.Counter(self.dir_of(u) for u in urls)
        for u in urls:
            d = self.dir_of(u)
            deep = len([x for x in urlsplit(u).path.split('/')[:-1] if x]) >= 2  # never a whole-site prefix
            self.group[u] = (d, 'prefix') if dirs[d] >= 3 and deep and not urlsplit(u).query else (u, 'exact')
        self.cache, self.locks = {}, collections.defaultdict(threading.Lock)

    @staticmethod
    def dir_of(u):
        sp = urlsplit(u)
        return f'{sp.netloc}{sp.path.rsplit("/", 1)[0]}/'

    def lookup(self, net, url, ts):
        key, mode = self.group.get(url, (url, 'exact'))
        with self.locks[key]:
            if key not in self.cache:
                q = (f'https://web.archive.org/cdx/search/cdx?url={urlquote(key, safe="")}&matchType={mode}'
                     f'&output=json&fl=original,timestamp&filter=statuscode:200&limit=100000')
                st, body, _, err = net.get(q)
                idx = collections.defaultdict(list)
                if st == 200:
                    try:
                        for orig, t in json.loads(body or b'[]')[1:]:
                            idx[norm_url(orig)].append(t)
                    except ValueError:
                        pass
                    self.cache[key] = idx
                else:  # lookup refused (the Wayback Machine throttles with 503): not retried in this run
                    self.cache[key] = {}
                    return None
        tss = self.cache[key].get(norm_url(url)) or []
        if not tss:
            return None
        ts = (ts or '20261015').ljust(14, '0')[:14]
        best = min(tss, key=lambda t: abs(int(t.ljust(14, '0')[:14]) - int(ts)))
        return f'https://web.archive.org/web/{best}id_/{url}'


WBI = None
LIVE_FIRST = False
OAI_NEIGHBORS = False  # --oai-neighbors: capture the adjacent ListRecords pages of every cited Infoscience OAI page
REDO_LIVE = False  # --redo-live (with --hosts): look for a Wayback capture of urls held only as a live capture
DSPACE_REBATCH = 0  # --dspace-rebatch N: re-capture items held only in 50-item batches through N-item batches
DSPACE_SINGLE = False  # --dspace-single: capture every DSpace item through its own item API url (short capture_url)


def wayback_closest(net, url, ts):
    """id_ url of the status-200 capture closest to ts (YYYYMMDD...), or None."""
    return WBI.lookup(net, url, ts) if WBI else None


def capture_one(net, con, url, info, local):
    """Capture one cited url (see the module doc for the order). Returns a short outcome tag."""
    orig = info['orig']
    target_ts = sorted(info['dates'])[len(info['dates']) // 2] if info['dates'] else None
    # (1) local copy
    ref = local.by_url.get(url) or next((local.by_sha[s] for s in orig if s in local.by_sha), None)
    if ref:
        got = Local.read(ref)
        if got:
            ts, _ = wb_parts(got['capture_url'] or '')
            observed = (ts[:4] + '-' + ts[4:6] + '-' + ts[6:8]) if ts else str(got['fetched_at'] or '')[:10]
            store(con, url, got['capture_url'], 200, got['body'], got['content_type'], 'local', observed, orig,
                  fetched_at=got['fetched_at'])
            return 'local'
    # (2) cited Wayback id_ url
    ts, inner = wb_parts(url)
    if ts:
        isp = urlsplit(inner)
        ih = isp.netloc.lower()
        if ih:  # the origin's robots.txt is read only for an AI-agent ban (such a host is not used at all)
            net.robots_rules(isp.scheme or 'http', ih)
            if net.blocked.get(ih) == 'robots-ai':
                store(con, url, None, None, None, None, 'wayback', None, orig, error='robots-ai:' + ih)
                return 'robots-ai'
        cu = url if 'id_/' in url else f'https://web.archive.org/web/{ts}id_/{inner}'
        st, body, ct, err = net.get(cu)
        store(con, url, cu, st, body, ct, 'wayback', f'{ts[:4]}-{ts[4:6]}-{ts[6:8]}', orig, error=err)
        return 'wayback' if st == 200 else f'wayback-{st or err}'
    # (3) API / OAI
    m = api_method(url)
    deny = net.allowed(url)
    if deny:
        store(con, url, None, None, None, None, m or 'live', None, orig, error=deny + ':' + urlsplit(url).netloc)
        return deny
    if m:
        st, body, ct, err = net.get(url)
        if st == 200:
            store(con, url, url, st, body, ct, m, now()[:10], orig)
            return m
        store(con, url, url, st, None, ct, m, None, orig, error=err or f'http:{st}')
        # fall through to Wayback for a dead API url
    # (4) Wayback closest, then live (--live-first swaps them, for when the Wayback Machine throttles us)
    if LIVE_FIRST and not m:
        st, body, ct, err = net.get(url)
        if st == 200 and body:
            store(con, url, url, st, body, ct, 'live', now()[:10], orig)
            return 'live'
        store(con, url, url, st, None, ct, 'live', None, orig, error=err or f'http:{st}')
    wb = wayback_closest(net, url, target_ts)
    if wb:
        st, body, ct, err = net.get(wb)
        if st == 200 and body:
            t2 = wb_parts(wb)[0]
            store(con, url, wb, st, body, ct, 'wayback', f'{t2[:4]}-{t2[4:6]}-{t2[6:8]}', orig)
            return 'wayback'
        store(con, url, wb, st, None, ct, 'wayback', None, orig, error=err or f'http:{st}')
    if m:
        return 'no-capture'
    if LIVE_FIRST:
        tag = 'no-capture:live and wayback' if st in (404, 410) else (err or f'http:{st}')
        store(con, url, url, st, None, None, 'live', None, orig, error=tag)
        return tag
    st, body, ct, err = net.get(url)
    if st == 200 and body:
        store(con, url, url, st, body, ct, 'live', now()[:10], orig)
        return 'live'
    tag = err or (f'no-capture:http {st}' if st in (404, 410) else f'http:{st}')
    store(con, url, url, st, None, ct, 'live', None, orig, error=tag)
    return tag


OAI_PAGE = re.compile(r'^(https://infoscience\.epfl\.ch/server/oai/\w+\?verb=ListRecords&resumptionToken=[^/]+///[^/]+/)(\d+)$')
OAI_STEP = (100, -100, 200, -200, 300, -300)


def oai_neighbors(url):
    """The same Infoscience ListRecords sequence one to three pages before/after (offsets drift as items change)."""
    m = OAI_PAGE.match(url)
    if not m:
        return []
    return [m.group(1) + str(int(m.group(2)) + d) for d in OAI_STEP if int(m.group(2)) + d >= 0]


DSPACE_BATCH = 50
DSPACE_ITEM = re.compile(r'^https://dspace\.mit\.edu/server/api/core/items/([0-9a-f\-]{36})$')


def dspace_batch(net, cons, batch):
    """Capture a batch of DSpace item API urls with one discover query; returns the jobs it could not capture."""
    ids = {}
    rest = []
    for job in batch:
        m = DSPACE_ITEM.match(job[1])
        if m:
            ids[m.group(1)] = job
        else:
            rest.append(job)
    if not ids:
        return rest
    cu = ('https://dspace.mit.edu/server/api/discover/search/objects?dsoType=ITEM&size=100&query='
          + urlquote('search.resourceid:(' + ' OR '.join(sorted(ids)) + ')', safe=''))
    if net.allowed(cu):
        return rest + list(ids.values())
    st, body, ct, err = net.get(cu)
    found = set()
    if st == 200:
        try:
            objs = json.loads(body)['_embedded']['searchResult']['_embedded']['objects']
            found = {o['_embedded']['indexableObject']['uuid'] for o in objs}
        except (ValueError, KeyError, TypeError):
            found = set()
    if not found:
        return rest + list(ids.values())
    sha = hashlib.sha256(body).hexdigest()
    today = now()[:10]
    by_school = collections.defaultdict(list)
    for uid, job in ids.items():
        by_school[job[0]].append((uid, job))
    for school, jobs in by_school.items():
        con = cons[school]
        with _dblock:
            cur = con.execute('INSERT INTO captures(url,capture_url,fetched_at,status,sha256,content_type,content,error,'
                              'method,observed) VALUES (?,?,?,?,?,?,?,?,?,?)',
                              ('batch:' + cu, cu, now(), st, sha, ct, gzip.compress(body, 6, mtime=0), None, 'api', today))
            ref = cur.lastrowid
            for uid, (sch, u, e) in jobs:
                if uid not in found:
                    continue
                orig = e['orig']
                con.execute('INSERT INTO captures(url,capture_url,fetched_at,status,sha256,content_type,content,error,'
                            'method,observed,original_sha256,matches_original,body_ref) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                            (u, cu, now(), 200, sha, ct, None, None, 'api', today, ','.join(sorted(orig)) or None,
                             None if not orig else int(sha in orig), ref))
            con.commit()
    return rest + [job for uid, job in ids.items() if uid not in found]


def fetch(schools, max_minutes=None, hosts=None, retry_errors=False):
    net = Net()
    deadline = time.monotonic() + 60 * max_minutes if max_minutes else None
    queues = collections.defaultdict(collections.deque)  # host -> deque of (school, url, info)
    cons, locals_ = {}, {}
    for school in schools:
        pl = plan(school)
        con = cons[school] = connect(school)
        skip = done_urls(con, retry_errors)
        todo = {u: e for u, e in pl.items() if u not in skip}
        shas = set().union(*[e['orig'] for e in todo.values()]) if todo else set()
        locals_[school] = Local(school, set(todo), shas)
        log(f'{school}: {len(pl)} cited urls, {len(pl) - len(todo)} already captured, {len(todo)} to do; '
            f'local hits url={len(locals_[school].by_url)} sha={len(locals_[school].by_sha)}')
        if OAI_NEIGHBORS:
            nb = sorted({n for u in pl if OAI_PAGE.match(u) for n in oai_neighbors(u)[:2]} - skip - set(pl))  # +-1 page
            log(f'{school}: {len(nb)} adjacent Infoscience OAI pages to capture')
            todo = {n: dict(targets={}, orig=set(), dates=[], relations=0) for n in nb}
        for u, e in sorted(todo.items(), key=lambda kv: -kv[1]['relations']):
            h = urlsplit(u).netloc.lower()
            if hosts and h not in hosts:
                continue
            queues[h].append((school, u, e))
    global WBI
    WBI = WaybackIndex([u for q in queues.values() for _, u, _ in q if not wb_parts(u)[0] and not api_method(u)])
    stats = collections.Counter()
    slock = threading.Lock()

    def worker(h):
        q = queues[h]
        while q:
            if deadline and time.monotonic() > deadline:
                return
            school, u, e = q.popleft()
            try:
                tag = capture_one(net, cons[school], u, e, locals_[school])
            except Exception as ex:  # one bad url must not stop the host
                tag = 'exception'
                store(cons[school], u, None, None, None, None, None, None, e['orig'], error='exception:' + repr(ex)[:300])
            with slock:
                stats[(school, h, tag.split(':')[0])] += 1
                n = sum(stats.values())
            if n % 100 == 0:
                log(f'  {n} done; queues left {sum(len(x) for x in queues.values())}')

    def dspace_worker(h):
        """DSpace item API urls in batches of 50 through the discover API (one request instead of 50); an item the
        batch does not return falls back to its own item API url."""
        q = queues[h]
        while q:
            if deadline and time.monotonic() > deadline:
                return
            batch = []
            while q and len(batch) < DSPACE_BATCH:
                batch.append(q.popleft())
            rest = dspace_batch(net, cons, batch)
            for school, u, e in rest:
                tag = capture_one(net, cons[school], u, e, locals_[school])
                with slock:
                    stats[(school, h, 'single-' + tag.split(':')[0])] += 1
            with slock:
                stats[('mit', h, 'batched')] += len(batch) - len(rest)
                n = sum(stats.values())
            log(f'  dspace batch: {len(batch) - len(rest)}/{len(batch)}; {len(q)} left; {n} done')

    ths = [threading.Thread(target=dspace_worker if h == 'dspace.mit.edu' and not DSPACE_SINGLE else worker, args=(h,), daemon=True)
           for h in queues]
    for t in ths:
        t.start()
    for t in ths:
        t.join()
    log('fetch outcomes:')
    for k, v in sorted(stats.items()):
        log('  ', k, v)
    return stats


# -------------------------------------------------------------------------------------------------------- extraction
_SPECIAL = {'ø': 'o', 'Ø': 'O', 'ł': 'l', 'Ł': 'L', 'ß': 'ss', 'æ': 'ae', 'Æ': 'AE', 'đ': 'd', 'Đ': 'D', 'ı': 'i',
            'œ': 'oe', 'Œ': 'OE', 'þ': 'th', '’': "'", '‐': '-', '‑': '-', '–': '-', '\xa0': ' '}


def fold(text, json_escapes=False):
    """Lower-cased, accent-free view of text and a map from each folded char to its index in text (None: same index).
    Without JSON escapes the fold is one char per char (str.translate, fast); with them a char loop decodes \\uXXXX."""
    if not json_escapes:
        if text.isascii():
            return text.lower(), None
        table = {}
        for ch in set(text):
            o = ord(ch)
            if o < 128:
                if 'A' <= ch <= 'Z':
                    table[o] = ch.lower()
                continue
            f = _SPECIAL.get(ch)
            if f is None:
                f = ''.join(c for c in unicodedata.normalize('NFKD', ch) if not unicodedata.combining(c))
            f = f.lower()
            table[o] = f[0] if f else ch
        return text.translate(table), None
    out, idx = [], []
    i, n = 0, len(text)
    while i < n:
        ch, j = text[i], i + 1
        if json_escapes and ch == '\\' and i + 1 < n:
            nx = text[i + 1]
            if nx == 'u' and re.match(r'[0-9a-fA-F]{4}', text[i + 2:i + 6]):
                ch, j = chr(int(text[i + 2:i + 6], 16)), i + 6
            elif nx in '/"\\':
                ch, j = nx, i + 2
            elif nx in 'nrt':
                ch, j = ' ', i + 2
        if ord(ch) < 128:
            s = ch.lower()
        else:
            s = _SPECIAL.get(ch)
            if s is None:
                s = ''.join(c for c in unicodedata.normalize('NFKD', ch) if not unicodedata.combining(c))
            s = s.lower()
        for c in s:
            out.append(c)
            idx.append(i)
        i = j
    return ''.join(out), idx


STOP = {'jr', 'sr', 'ii', 'iii', 'iv', 'dr', 'prof', 'phd', 'mr', 'ms', 'mrs'}
_NICK_GROUPS = ['christopher chris', 'eduard edward ed eddie', 'andrew andy drew', 'alexander alex', 'alexandra alex',
                'jeffrey jeff', 'geoffrey geoff', 'michael mike', 'william bill will', 'robert bob rob bobby',
                'david dave', 'daniel dan danny', 'thomas tom', 'james jim jamie', 'joseph joe', 'steven steve',
                'stephen steve', 'richard rich rick', 'matthew matt', 'anthony tony', 'nicholas nick', 'benjamin ben',
                'samuel sam', 'gregory greg', 'kenneth ken', 'lawrence larry', 'ronald ron', 'donald don',
                'patrick pat', 'raymond ray', 'frederick fred', 'frederic fred', 'jonathan jon', 'timothy tim',
                'peter pete', 'charles charlie chuck', 'zachary zach zack', 'nathaniel nate nathan', 'katherine kate katie',
                'catherine kate cathy', 'elizabeth liz beth', 'jennifer jen jenny', 'rebecca becky', 'susan sue',
                'margaret maggie meg', 'deborah deb debbie', 'victoria vicky', 'barnabas barney', 'manuel manny',
                'abhinav abhi', 'vincent vince', 'philip phil', 'phillip phil', 'leonid leo', 'leonard leo',
                'mitchell mitch', 'douglas doug', 'gerald jerry', 'harold harry', 'henry hank', 'jacob jake',
                'joshua josh', 'kristopher kris', 'theodore ted teddy', 'edmund ed', 'aleksandr alex sasha']
NICK = collections.defaultdict(set)
for _g in _NICK_GROUPS:
    _w = _g.split()
    for _a in _w:
        NICK[_a].update(x for x in _w if x != _a)


def name_tokens(name):
    f, _ = fold(name)
    f = re.sub(r'\([^)]*\)', ' ', f)
    return [t for t in re.findall(r"[a-z]+(?:['\-][a-z]+)*", f) if t not in STOP]


def name_regex(names):
    """One compiled regex over folded text matching any variant of any of names."""
    alts = set()
    variants = []
    for nm in names:
        variants.append(nm)
        nick = re.findall(r'\(([^)]+)\)|"([^"]+)"|“([^”]+)”', nm)
        base = re.sub(r'\([^)]*\)|"[^"]*"|“[^”]*”', ' ', nm).split()
        for n in nick:  # 'Ziheng (Tony) Wang' is also written 'Tony Wang'
            n = next(x for x in n if x)
            if base and len(base) >= 2:
                variants.append(n + ' ' + base[-1])
    for nm in variants:
        toks = name_tokens(nm)
        if len(toks) < 2:
            continue
        F = toks[0]
        fx = re.escape(F).replace(r'\-', r'[\s\-]?')
        if F in NICK:  # 'Christopher Dyer' is also written 'Chris Dyer'
            fx = '(?:' + '|'.join([fx] + [re.escape(x) for x in sorted(NICK[F])]) + ')'
        if '-' in F:
            ini = r'\-?'.join(re.escape(p[0]) + r'\.?' for p in F.split('-'))
        else:
            ini = re.escape(F[0]) + r'\.'
        for L in toks[1:]:
            if len(L) < 2:
                continue
            lx = re.escape(L).replace(r'\-', r'[\s\-]?')
            alts.add(rf"\b{fx}(?:[\s.\-]+[(\"'“]?[a-z'\-]+[)\"'”]?\.?){{0,3}}?[\s.\-]+{lx}\b")
            alts.add(rf'\b{lx}\s*,\s*{fx}\b')
            alts.add(rf'\b{lx}\s+{fx}\b')
            alts.add(rf'\b{ini}\s*(?:[a-z]\.\s*|[a-z]\.?-[a-z]\.\s*){{0,3}}{lx}\b')
        if len(toks) >= 3:  # surname of two tokens written first: "Gamlath Ralalage, Buddhima"
            alts.add(rf'\b{re.escape(toks[-2])}\s+{re.escape(toks[-1])}\s*,\s*{fx}\b')
    if not alts:
        return None
    return re.compile('|'.join(sorted(alts, key=len, reverse=True)))


def lab_terms(pirec, school):
    """(folded phrases, case-sensitive acronyms) naming the PI's lab, excluding generic '<PI> group' names."""
    phrases, acr = set(), set()
    if not pirec:
        return phrases, acr
    last = (name_tokens(pirec['pi']) or [''])[-1]
    lab = (pirec.get('lab') or {}).get('name') or ''
    fl = fold(lab)[0].strip()
    if fl and last not in fl and len(fl) >= 8 and fl not in ('research group', 'lab', 'laboratory'):
        phrases.add(fl)
    if len(last) >= 3:  # 'Weiss Lab', 'Kellis group', 'Chlipala's group', 'Hanlab'
        for suf in (' lab', ' laboratory', ' group', ' research group', "'s group", "'s lab", 'lab'):
            phrases.add(last + suf)
    if school == 'epfl':
        for d in pirec.get('departments') or []:
            if re.match(r'^[A-Z][A-Z0-9\-]{2,11}$', d) and d not in ('IC', 'EDIC', 'SIN', 'SSC', 'STI', 'SB', 'ENAC', 'SV', 'CDH', 'CDM'):
                acr.add(d)
    return phrases, acr


class Text(HTMLParser):
    BLOCK = {'p', 'div', 'li', 'tr', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'dt', 'dd', 'ul', 'ol', 'table',
             'section', 'article', 'header', 'footer', 'nav', 'blockquote', 'pre', 'hr', 'main', 'aside', 'figure',
             'figcaption', 'tbody', 'thead', 'form', 'center', 'address', 'dl', 'body'}
    SKIP = {'script', 'style', 'noscript', 'template', 'svg', 'head'}
    HEAD = {'h1', 'h2', 'h3', 'h4'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines, self.cur, self.skip, self.head, self.title, self.in_title = [], [], 0, 0, '', False
        self.cur_head = False

    def flush(self):
        t = re.sub(r'\s+', ' ', ''.join(self.cur)).strip()
        if t:
            self.lines.append((t, self.cur_head))
        self.cur, self.cur_head = [], False

    def handle_starttag(self, tag, attrs):
        if tag == 'title':
            self.in_title = True
        if tag in self.SKIP and tag != 'head':
            self.skip += 1
        if tag in self.BLOCK:
            self.flush()
        if tag in self.HEAD:
            self.head += 1
        if tag in ('td', 'th'):
            self.cur.append(' ')

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False
        if tag in self.SKIP and tag != 'head' and self.skip:
            self.skip -= 1
        if tag in self.BLOCK:
            self.flush()
        if tag in self.HEAD and self.head:
            self.head -= 1

    def handle_data(self, data):
        if self.in_title:
            self.title += data
            return
        if self.skip:
            return
        if self.head:
            self.cur_head = True
        self.cur.append(data)


def decode(body, ctype):
    ctype = (ctype or '').lower()
    m = re.search(r'charset=([\w\-]+)', ctype)
    for enc in ([m.group(1)] if m else []) + ['utf-8', 'cp1252', 'latin-1']:
        try:
            return body.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return body.decode('utf-8', 'replace')


def kind_of(text, ctype):
    head = text.lstrip()[:200].lower()
    if head.startswith('{') or head.startswith('[') or 'json' in (ctype or ''):
        return 'json'
    if (head.startswith('<?xml') or 'xml' in (ctype or '')) and '<html' not in text[:3000].lower():
        return 'xml'
    return 'html'


def clip(s, a, b, limit):
    """Whitespace-collapsed s[a:b] widened to word boundaries, at most limit chars centred on the span."""
    if b - a > limit:
        return None
    pad = (limit - (b - a)) // 2
    lo, hi = max(0, a - min(pad, 60)), min(len(s), b + min(pad, 60))
    while lo > 0 and lo > a - 80 and not s[lo - 1].isspace() and s[lo - 1] not in ',;{[<>':
        lo -= 1
    while hi < len(s) and hi < b + 80 and not s[hi].isspace() and s[hi] not in ',;}]<>':
        hi += 1
    return re.sub(r'\s+', ' ', s[lo:hi]).strip()


def spans(rx, folded, idx):
    """Original-index spans of rx matches in a folded view."""
    out = []
    if rx is None:
        return out
    for m in rx.finditer(folded):
        a, b = m.start(), m.end()
        out.append((a, b) if idx is None else (idx[a], idx[b - 1] + 1))
    return out


def lab_spans(text, folded, idx, phrases, acr):
    out = []
    for ph in phrases:
        for m in re.finditer(r'\b' + re.escape(ph) + r'\b', folded):
            out.append((m.start(), m.end()) if idx is None else (idx[m.start()], idx[m.end() - 1] + 1))
    for a in acr:
        for m in re.finditer(r'(?<![A-Za-z0-9])' + re.escape(a) + r'(?![A-Za-z0-9])', text):
            out.append((m.start(), m.end()))
    return out


def join_parts(text, first, second, limit=150):
    """Two verbatim excerpts in document order joined by ' … '."""
    (a1, b1), (a2, b2) = sorted([first, second])
    p1, p2 = clip(text, a1, b1, limit), clip(text, a2, b2, limit)
    if not p1 or not p2:
        return None
    return p1 + ' … ' + p2


# --- HTML pages: lines, headings, title
def extract_html(text, targets, pirecs, school):
    par = Text()
    try:
        par.feed(text)
        par.close()
    except Exception:
        pass
    par.flush()
    lines = par.lines
    title = re.sub(r'\s+', ' ', par.title).strip()
    joined, starts, pos = [], [], 0
    for t, _ in lines:
        starts.append(pos)
        joined.append(t)
        pos += len(t) + 1
    full = '\n'.join(joined)
    folded, idx = fold(full)
    tfold, tidx = fold(title)
    import bisect
    out = []
    for t in targets:
        srx = name_regex([t['name']] + t['aliases'])
        ss = spans(srx, folded, idx)
        if not ss:
            out.append((t, None, 'name_not_on_page'))
            continue
        pirec = pirecs.get(t['pi'])
        prx = name_regex([t['pi']] + list((pirec or {}).get('names') or []))
        phrases, acr = lab_terms(pirec, school)
        ps = spans(prx, folded, idx) + lab_spans(full, folded, idx, phrases, acr)
        pline = collections.defaultdict(list)
        for a, b in ps:
            pline[bisect.bisect_right(starts, a) - 1].append((a, b))
        title_pi = spans(prx, tfold, tidx) + lab_spans(title, tfold, tidx, phrases, acr)
        best = None
        for a, b in ss:
            li = bisect.bisect_right(starts, a) - 1
            cand = None
            if pline.get(li):
                pa, pb = min(pline[li], key=lambda s: abs(s[0] - a))
                q = clip(full, min(a, pa), max(b, pb), 300)
                cand = (0, q) if q else (1, join_parts(full, (a, b), (pa, pb)))
            elif pline.get(li + 1) and len(lines[li][0]) + len(lines[li + 1][0]) < 300:
                pa, pb = pline[li + 1][0]
                cand = (1, clip(full, a, pb, 300) or join_parts(full, (a, b), (pa, pb)))
            else:
                hh = next((k for k in range(li - 1, -1, -1) if lines[k][1]), None)
                h1 = next((k for k in range(0, li) if lines[k][1]), None)
                if hh is not None and pline.get(hh):  # the nearest heading above names the PI / lab
                    cand = (2, join_parts(full, pline[hh][0], (a, b)))
                elif title_pi:  # the page title names the PI / lab
                    ta, tb = title_pi[0]
                    q = clip(title, ta, tb, 150)
                    sq = clip(full, a, b, 150)
                    cand = (3, (q + ' … ' + sq) if q and sq else None)
                elif h1 is not None and pline.get(h1):  # the page's first heading names the PI / lab
                    cand = (3, join_parts(full, pline[h1][0], (a, b)))
            if cand and cand[1]:
                if best is None or cand[0] < best[0]:
                    best = cand
            if best and best[0] == 0:
                break
        if best:
            out.append((t, best[1], 'pi'))
        else:
            a, b = ss[0]
            li = bisect.bisect_right(starts, a) - 1
            q = clip(full, a, b, 300) if len(lines[li][0]) > 300 else lines[li][0]
            out.append((t, q, 'student_only'))
    return out


# --- JSON / XML records
def json_records(text):
    """[(start, end)] of the elements of the outermost record array: an array of >= 20 elements, or of >= 2 elements
    averaging >= 2000 chars (a batch of full records), found by a string-aware scan."""
    stack, elems, out = [], {}, []
    i, n, ins = 0, len(text), False
    while i < n:
        c = text[i]
        if ins:
            if c == '\\':
                i += 2
                continue
            if c == '"':
                ins = False
        elif c == '"':
            ins = True
            if stack and stack[-1][0] == '[' and stack[-1][2] is None:
                stack[-1][2] = i
        elif c in '[{':
            if stack and stack[-1][0] == '[' and stack[-1][2] is None:
                stack[-1][2] = i
            stack.append([c, i, None])
            if c == '[':
                elems[i] = []
        elif c in ']}':
            if stack:
                top = stack.pop()
                if top[0] == '[':
                    if top[2] is not None:
                        elems[top[1]].append((top[2], i))
                    el = elems[top[1]]
                    if len(el) >= 20 or (len(el) >= 2 and sum(b - a for a, b in el) / len(el) >= 2000):
                        out.append((len(stack), el))
                    del elems[top[1]]
        elif c == ',' and stack and stack[-1][0] == '[':
            if stack[-1][2] is not None:
                elems[stack[-1][1]].append((stack[-1][2], i))
            stack[-1][2] = None
        elif not c.isspace() and stack and stack[-1][0] == '[' and stack[-1][2] is None:
            stack[-1][2] = i
        i += 1
    out.sort(key=lambda x: x[0])
    return out[0][1] if out else []


def xml_records(text):
    recs = [(m.start(), m.end()) for m in re.finditer(r'<(?:\w+:)?record\b[^>]*>.*?</(?:\w+:)?record>', text, re.S)]
    return recs


def raw_context(text, kind):
    folded, idx = fold(text, json_escapes=(kind == 'json'))
    return folded, idx, (json_records(text) if kind == 'json' else xml_records(text))


def word_index(folded):
    """word -> start offsets in the folded text (built once per large body)."""
    wi = collections.defaultdict(list)
    for m in re.finditer(r'[a-z]+', folded):
        wi[m.group()].append(m.start())
    return wi


def anchor_words(names):
    """Every name_regex alternative contains a surname token: the words to look up in a word index."""
    out = set()
    for nm in names:
        base = re.sub(r'\([^)]*\)|"[^"]*"|“[^”]*”', ' ', nm)
        toks = name_tokens(base)
        out.update(t for t in toks[1:] if len(t) >= 2)
        for part in toks[1:]:
            out.update(x for x in re.findall('[a-z]+', part) if len(x) >= 2)
    return out


def spans_win(rx, words, folded, idx, wi, width=160):
    """spans() restricted to windows around the anchor words (a large body is not rescanned per target)."""
    if rx is None:
        return []
    out = set()
    for p in sorted({p for w in words for p in wi.get(w, ())}):
        for m in rx.finditer(folded, max(0, p - width), min(len(folded), p + width)):
            out.add((m.start(), m.end()))
    return sorted(out) if idx is None else sorted((idx[a], idx[b - 1] + 1) for a, b in out)


def extract_raw(text, kind, targets, pirecs, school, pre=None):
    import bisect
    folded, idx, recs = pre[:3] if pre else raw_context(text, kind)
    big = len(folded) > 300000
    wi = (pre[3] if pre and len(pre) > 3 else None) or (word_index(folded) if big else None)
    rstarts = [r[0] for r in recs]

    def rec_of(p):
        k = bisect.bisect_right(rstarts, p) - 1
        return k if k >= 0 and recs[k][0] <= p < recs[k][1] else None

    out = []
    for t in targets:
        snames = [t['name']] + t['aliases']
        srx = name_regex(snames)
        ss = spans_win(srx, anchor_words(snames), folded, idx, wi) if wi else spans(srx, folded, idx)
        if not ss:
            out.append((t, None, 'name_not_on_page'))
            continue
        pirec = pirecs.get(t['pi'])
        pnames = [t['pi']] + list((pirec or {}).get('names') or [])
        prx = name_regex(pnames)
        phrases, acr = lab_terms(pirec, school)
        if wi:
            ps = spans_win(prx, anchor_words(pnames), folded, idx, wi)
            for ph in phrases:
                w0 = re.findall('[a-z]+', ph)
                ps += spans_win(re.compile(r'\b' + re.escape(ph) + r'\b'), w0[:1], folded, idx, wi, 80) if w0 else []
            ps += lab_spans(text, '', None, (), acr)
        else:
            ps = spans(prx, folded, idx) + lab_spans(text, folded, idx, phrases, acr)
        best = None
        for a, b in ss:
            r = rec_of(a)
            same = [(pa, pb) for pa, pb in ps if rec_of(pa) == r]
            if r is None and recs:  # student outside every collection element: PI must be outside them too
                same = [(pa, pb) for pa, pb in ps if rec_of(pa) is None]
            if not same:
                continue
            pa, pb = min(same, key=lambda s: abs(s[0] - a))
            q = clip(text, min(a, pa), max(b, pb), 300)
            cand = (0, q) if q else (1, join_parts(text, (a, b), (pa, pb)))
            if cand[1] and (best is None or cand[0] < best[0]):
                best = cand
            if best and best[0] == 0:
                break
        if best:
            out.append((t, best[1], 'pi'))
        else:
            a, b = ss[0]
            out.append((t, clip(text, a, b, 200), 'student_only'))
    return out


def best_capture(con, url):
    rows = con.execute('SELECT capture_url,fetched_at,sha256,content_type,content,method,observed,original_sha256,'
                       'matches_original,body_ref FROM captures WHERE url=? AND status=200 '
                       'AND (content IS NOT NULL OR body_ref IS NOT NULL) '
                       'ORDER BY matches_original DESC, (content IS NOT NULL) DESC, id DESC', (url,)).fetchall()
    if not rows:
        return None
    r = list(rows[0][:9])
    if r[4] is None:
        r[4] = con.execute('SELECT content FROM captures WHERE id=?', (rows[0][9],)).fetchone()[0]
    return tuple(r)


def extract(schools):
    summary = {}
    for school in schools:
        pl = plan(school)
        con = connect(school)
        pirecs = {}
        for p in load_json(P.HIERARCHY / school / 'pis.json'):
            pirecs[p['pi']] = p
        records, why = [], collections.Counter()
        why_hosts = collections.defaultdict(collections.Counter)
        rows = {u: best_capture(con, u) for u in pl}
        cache = {}
        for u in sorted(pl, key=lambda x: ((rows[x] or ('',) * 3)[2] or '', x)):  # same body together
            e = pl[u]
            host = urlsplit(wb_parts(u)[1] or u).netloc.lower()
            row = rows[u]
            if not row:
                err = con.execute('SELECT error,status FROM captures WHERE url=? ORDER BY id DESC LIMIT 1', (u,)).fetchone()
                tag = ('not_attempted' if err is None else (err[0] or f'http:{err[1]}').split(':')[0])
                why[tag] += len(e['targets'])
                why_hosts[tag][host] += len(e['targets'])
                continue
            cu, fat, sha, ct, blob, method, observed, osha, match = row
            if sha not in cache:
                cache.clear()
                body = gzip.decompress(blob)
                text = decode(body, ct)
                kind = kind_of(text, ct)
                pre = raw_context(text, kind) if kind != 'html' else None
                if pre and len(pre[0]) > 300000:
                    pre = pre + (word_index(pre[0]),)
                cache[sha] = (text, kind, pre)
            text, kind, pre = cache[sha]
            targets = list(e['targets'].values())
            try:
                res = extract_html(text, targets, pirecs, school) if kind == 'html' else \
                    extract_raw(text, kind, targets, pirecs, school, pre)
            except Exception as ex:
                log('  extract error', u, repr(ex)[:200])
                why['extract_error'] += len(targets)
                continue
            osha = sorted(e['orig'])
            missing = [t for t, q, tag in res if tag == 'name_not_on_page']
            if missing and OAI_PAGE.match(u):  # the ListRecords offsets drifted since the harvest: adjacent pages
                res = [x for x in res if x[2] != 'name_not_on_page']
                for nu in oai_neighbors(u):
                    if not missing:
                        break
                    r2 = best_capture(con, nu)
                    if not r2:
                        continue
                    t2 = decode(gzip.decompress(r2[4]), r2[3])
                    got = extract_raw(t2, 'xml', missing, pirecs, school)
                    for t, q, tag in got:
                        if tag != 'name_not_on_page':
                            records.append(dict(url=u, person=t['person'], name=t['name'],
                                                pi=t['pi'] if tag == 'pi' else None, capture_url=r2[0], sha256=r2[2],
                                                quote=q, names_pi=tag == 'pi', observed=r2[6],
                                                original_sha256=(osha[0] if len(osha) == 1 else (','.join(osha) or None)),
                                                matches_original=False if osha else None, method='oai'))
                            why['oai_adjacent_page_' + tag] += 1
                    found = {g[0]['person'] + '|' + g[0]['pi'] for g in got if g[2] != 'name_not_on_page'}
                    missing = [t for t in missing if t['person'] + '|' + t['pi'] not in found]
                res += [(t, None, 'name_not_on_page') for t in missing]
            for t, q, tag in res:
                why[tag] += 1
                if tag == 'name_not_on_page':
                    why_hosts['name_not_on_page'][host] += 1
                    continue
                if tag == 'student_only':
                    why_hosts['student_only'][host] += 1
                records.append(dict(url=u, person=t['person'], name=t['name'],
                                    pi=t['pi'] if tag == 'pi' else None, capture_url=cu, sha256=sha, quote=q,
                                    names_pi=tag == 'pi', observed=observed,
                                    original_sha256=(osha[0] if len(osha) == 1 else (','.join(osha) or None)),
                                    matches_original=None if not osha else bool(match), method=method))
        uniq = {}
        for r in records:
            uniq[(r['url'], r['person'], r['pi'] or '')] = r
        records = [uniq[k] for k in sorted(uniq)]
        doc = dict(_doc=('Re-captured evidence for student relations whose sources lacked sha256 and/or a verbatim '
                         'quote (docs/evidence-whitelist.json). Made by tools/relation_recapture.py on '
                         f'{now()[:10]}: each cited url was re-captured (local copy, the cited Wayback id_ url, the '
                         'API/OAI response, the Wayback capture closest to the original observation, or the live '
                         'page), its exact bytes hashed (sha256) and stored in relation-captures.sqlite, and a '
                         'verbatim quote naming the student (and, when names_pi, the PI or the PI\'s lab) copied from '
                         'the captured text, whitespace-collapsed; " … " separates two excerpts of the same page in '
                         'document order. matches_original compares the new hash with the sha256 the source carried.'),
                   school=school, made=now(), records=records)
        out = P.HIERARCHY / school / 'relation-evidence.json'
        s = json.dumps(doc, ensure_ascii=False, separators=(',', ':')).replace('},{"url"', '},\n{"url"')
        out.write_text(s + '\n')
        summary[school] = dict(records=len(records), names_pi=sum(r['names_pi'] for r in records), outcomes=dict(why),
                               by_host={k: dict(v.most_common(12)) for k, v in why_hosts.items()},
                               bytes=out.stat().st_size)
        log(school, json.dumps(summary[school])[:600])
    (TMP / 'extract-summary.json').write_text(json.dumps(summary, indent=1) + '\n')
    return summary


# -------------------------------------------------------------------------------------------------------- estimate
def estimate(schools):
    res = {}
    for school in schools:
        D = P.HIERARCHY / school
        S = load_json(D / 'students.json')
        links = load_json(D / 'student_papers.jsonl.gz')
        ev = json.loads((D / 'relation-evidence.json').read_text())['records']
        alias = {}
        for pi, recs in S.items():
            for s in recs:
                alias[s['person']] = s['person']
                for m in s.get('merged') or []:
                    alias.setdefault(m, s['person'])
        good, weak = set(), set()
        for r in ev:
            p = alias.get(r['person'], r['person'])
            if r['names_pi']:
                good.add((r['url'], p, r['pi']))
            else:
                weak.add((r['url'], p))
        c = collections.Counter()
        for pi, recs in S.items():
            for s in recs:
                for rel in s.get('relations') or []:
                    c['relations'] += 1
                    if any(sourced(q) for q in rel.get('sources') or []):
                        continue
                    c['before_failing'] += 1
                    urls = [q.get('url') for q in rel.get('sources') or []]
                    if any((u, s['person'], pi) in good for u in urls):
                        c['fixed_names_pi'] += 1
                    elif any((u, s['person']) in weak for u in urls):
                        c['fixed_student_only'] += 1
                    else:
                        c['still_failing'] += 1
        for x in links:
            if x.get('basis') not in BYLINE_BASES:
                continue
            c['links'] += 1
            rs = x.get('relation_source') or {}
            if sourced(rs):
                continue
            c['links_before_failing'] += 1
            p = alias.get(x.get('student'), x.get('student'))
            if (rs.get('url'), p, x['pi']) in good:
                c['links_fixed_names_pi'] += 1
            elif (rs.get('url'), p) in weak:
                c['links_fixed_student_only'] += 1
            else:
                c['links_still_failing'] += 1
        res[school] = dict(c)
        log(school, dict(c))
    (TMP / 'estimate.json').write_text(json.dumps(res, indent=1) + '\n')
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('stage', choices=['fetch', 'extract', 'estimate', 'all'])
    ap.add_argument('--school', nargs='*', default=SCHOOLS)
    ap.add_argument('--max-minutes', type=float, default=None)
    ap.add_argument('--hosts', default=None, help='comma-separated hosts to fetch (default all)')
    ap.add_argument('--retry-errors', action='store_true')
    ap.add_argument('--live-first', action='store_true', help='pages: live url first, Wayback only when live fails')
    ap.add_argument('--oai-neighbors', action='store_true',
                    help='only capture the adjacent pages of the cited Infoscience OAI ListRecords pages')
    ap.add_argument('--redo-live', action='store_true',
                    help='urls captured only live are retried through Wayback (a live page can be an empty shell)')
    ap.add_argument('--dspace-rebatch', type=int, default=0,
                    help='re-capture DSpace items held only in 50-item batches through batches of N (shorter urls)')
    ap.add_argument('--dspace-single', action='store_true',
                    help='re-capture DSpace items held only as batch responses through their own item API url')
    a = ap.parse_args(argv)
    global LIVE_FIRST, DSPACE_SINGLE, OAI_NEIGHBORS, DSPACE_REBATCH, DSPACE_BATCH, REDO_LIVE
    REDO_LIVE = a.redo_live
    LIVE_FIRST = a.live_first
    OAI_NEIGHBORS = a.oai_neighbors
    if a.dspace_rebatch:
        DSPACE_REBATCH = DSPACE_BATCH = a.dspace_rebatch
    DSPACE_SINGLE = a.dspace_single
    TMP.mkdir(parents=True, exist_ok=True)
    if a.stage in ('fetch', 'all'):
        fetch(a.school, a.max_minutes, set(a.hosts.split(',')) if a.hosts else None, a.retry_errors)
    if a.stage in ('extract', 'all'):
        extract(a.school)
    if a.stage in ('estimate', 'all'):
        estimate(a.school)
    return 0


if __name__ == '__main__':
    sys.exit(main())
