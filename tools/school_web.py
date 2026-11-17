"""Polite fetching for any school's stage tools, into one sqlite container per school: captures/<key>.sqlite.

Generalized 2026-10-29 from Stanford's st_web.py (claude-stanford-20261027/tools), for protocol stage 1.
- Wayback: the listings pipeline's client (listings/scripts/wb.py): one shared lock throttles every process to one
  web.archive.org request per 6 s; only `id_` captures; never follows a redirect to another page; never retries a 403
  or a challenge. CDX answers and captures are stored zlib-compressed (tables cdx, captures; the listings schema, so
  listings/scripts and period-tools read it unchanged).
- Live pages: robots.txt fetched with requests and a timeout (urllib's RobotFileParser.read() can hang), parsed with
  RobotFileParser.parse; a disallowed URL is never fetched; at least max(2 s, Crawl-delay) between requests to a host;
  a page that reads as a bot challenge is recorded with status 999 and the host is blocked for the rest of the run
  (table live; table robots; table blocked).
- Robots policy (docs/ADDING-A-SCHOOL.md stage 0): a robots.txt that disallows AI agents by name (ClaudeBot,
  anthropic-ai, Claude-Web) is honoured for this project's agents too, whatever User-Agent string is sent:
  robots_ok() checks those names as well as our own UA and '*'.

usage (CLI)   school_web.py <key> cdx <url> [prefix]       list Wayback 200 captures (monthly collapse) of a URL
              school_web.py <key> live <url>               fetch one live page (robots honoured), print its text
              school_web.py <key> robots <host>            print the stored robots decision
"""
import hashlib, json, os, re, sys, time, urllib.parse, urllib.robotparser, zlib
import fcntl
from contextlib import contextmanager, nullcontext
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # python -I leaves the script's directory off sys.path (docs/CONTRIBUTING.md, Imports and sys.path)
import atlas_paths as P  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'listings' / 'scripts'))  # this checkout's code: the data root is the main checkout, whose older wb.py a worktree or snapshot job then imported (Georgia Tech friction 17)
import wb  # noqa: E402
import extract  # noqa: E402

UA = 'HomogenizingScienceResearch/0.2 (academic metadata inventory; robots.txt honoured)'
AI_AGENTS = ('ClaudeBot', 'anthropic-ai', 'Claude-Web', 'Claude-User', 'Claude-SearchBot')
CHALLENGE = re.compile(r'bot detection|traffic check|Please enable JavaScript to view the page content|cf-chl|'
                       r'checking your browser|are you a robot|access denied|<title>Just a moment\.\.\.</title>|'
                       r'challenges\.cloudflare\.com|cf_chl_opt|px-captcha|ddos-guard|'
                       r'<(?:iframe|frame)[^>]+_Incapsula_Resource|Incapsula incident ID|Request unsuccessful\. Incapsula|' 
                       # A script can also serve an empty challenge shell; a readable page may embed the same resource.
                       r'<script[^>]+_Incapsula_Resource[^>]*>\s*</script>\s*(?:</head>\s*)?<body[^>]*>\s*</body>|'
                       # Research citations can contain CAPTCHA; require an actual gate/widget context.
                       r'g-recaptcha|h-captcha|hcaptcha\.com|recaptcha/(?:api|enterprise)|'
                       r'captcha[-_](?:container|challenge|form|input)|'
                       r'<(?:title|h[1-3])[^>]*>[^<]{0,120}captcha|'
                       r'(?:complete|solve|enter) (?:the |this |a )?captcha|'
                       r'captcha(?: validation| verification)? (?:required|failed)', re.I)
_last = {}
_blocked = set()


APACHE_PERMISSION_403 = re.compile(rb"(?is)<title>\s*403 Forbidden\s*</title>.{0,400}?(?:don't|do not) have permission to access (?:this resource|/\S* on this server).{0,300}?<address>\s*Apache")


def apache_path_denial(status, body):
    """A plain Apache directory-permission 403 ('You don't have permission to access /~sam/ on this server'): the server denies that path,
    not automated clients. It is a per-path denial (the page is recorded, never retried), not a host block (cs.toronto.edu, 2026-11-10).
    Any other 403 (a WAF or bot refusal) still closes the host."""
    return status == 403 and bool(APACHE_PERMISSION_403.search(body or b''))


def db_path(key):
    return P.data('school-captures.sqlite', key)


def con(key):
    db_path(key).parent.mkdir(parents=True, exist_ok=True)
    wb.db_path = lambda school, _p=str(db_path(key)): _p  # this school's container (the listings schema)
    c = wb.db(key)
    c.execute('create table if not exists live (url text primary key, fetched_at text, status int, sha256 text, content_type text, raw_zlib blob, text text)')
    c.execute('create table if not exists robots (host text primary key, fetched_at text, status int, body text)')
    c.execute('create table if not exists blocked (host text primary key, at text, why text)')
    c.commit()
    for (h, why) in c.execute('select host, why from blocked'):
        m = re.match(r'HTTP 403 access refusal at (\S+)$', why or '')
        if m:   # re-judge a stored 403 block by the stored body of that page: an Apache permission page is a per-path denial
            r = c.execute('select status, raw_zlib from live where url=?', (m.group(1),)).fetchone()
            try:
                body = zlib.decompress(r[1]) if r and r[1] else b''
            except zlib.error:
                body = (r[1] if r else b'') or b''
            if r and apache_path_denial(r[0], body):
                continue
        _blocked.add(h)
    # Old collectors did not persist plain access refusals as host blocks.
    # Reuse their receipts so a new URL cannot silently retry the same host.
    for url, st, raw in c.execute('select url, status, raw_zlib from live where status in (401,403,429,999)'):
        try:
            body = zlib.decompress(raw) if raw else b''
        except zlib.error:
            body = raw or b''
        if not apache_path_denial(st, body):
            _blocked.add(urllib.parse.urlsplit(url).netloc)
    return c


def cdx_rows(c, url, exact=True, frm='2016', to='2026', collapse='timestamp:6', status_200=True):
    p = {'url': url, 'from': frm, 'to': to, 'output': 'json', 'fl': 'urlkey,timestamp,original,statuscode,digest,mimetype', 'limit': '30000'}
    if status_200:
        p['filter'] = 'statuscode:200'
    if collapse:
        p['collapse'] = collapse
    if not exact:
        p['matchType'] = 'prefix'
    return wb.cdx(p, c) or []


def capture(c, ts, original, page_url, dept):
    """Fetch (or reuse) one id_ capture; returns (capture_url, status, sha256, text blocks)."""
    cap = wb.fetch_capture(ts, original, page_url, dept, c)
    st, raw, ct, bj, sha = c.execute('select http_status, raw_zlib, content_type, blocks_json, sha256 from captures where capture_url=?', (cap,)).fetchone()
    if bj is None:
        b = extract.blocks(body(raw), ct, cap) if raw else []
        c.execute('update captures set blocks_json=?, text=? where capture_url=?', (json.dumps(b), '\n'.join(t for _, t in b), cap)); c.commit()
    else:
        b = json.loads(bj)
    return cap, st, sha, b


body = wb.body  # stored bytes, gunzipped when Wayback served them gzip-encoded


def raw_html(c, cap):
    r = c.execute('select raw_zlib from captures where capture_url=?', (cap,)).fetchone()
    return wb.text(body(r[0])) if r and r[0] else ''


def repair_gzip(c):
    """Re-derive blocks_json and text of every stored capture whose bytes were gzip-encoded (they were extracted from the
    compressed bytes, i.e. read as empty). raw_zlib and sha256 are left as served. Returns the number repaired."""
    n = 0
    for cap, raw, ct in c.execute('select capture_url, raw_zlib, content_type from captures where raw_zlib is not null').fetchall():
        if zlib.decompress(raw)[:2] != b'\x1f\x8b':
            continue
        b = extract.blocks(body(raw), ct, cap)
        c.execute('update captures set blocks_json=?, text=? where capture_url=?', (json.dumps(b), '\n'.join(t for _, t in b), cap)); n += 1
    c.commit()
    return n


def registered_domain(host):
    """Registered domain by label count: the last two labels, three under a two-letter ccTLD with a generic second level (x.ac.uk)."""
    parts = (host or '').lower().rstrip('.').split('.')
    if len(parts) >= 3 and len(parts[-1]) == 2 and parts[-2] in ('ac', 'co', 'edu', 'com', 'org', 'gov', 'net'):
        return '.'.join(parts[-3:])
    return '.'.join(parts[-2:])


@contextmanager
def shared_origin_slot(host, gap):
    """Share the exact collector's flock/stamp for a narrowly approved HTTP origin."""
    stamp = P.RATE_STAMPS / 'hosts' / host
    stamp.parent.mkdir(parents=True, exist_ok=True)
    with stamp.open('a+') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        handle.seek(0)
        try:
            last = float(handle.read().strip() or 0)
        except ValueError as exc:
            raise ValueError('malformed shared host stamp') from exc
        time.sleep(max(0, last + gap - time.time()))
        started = time.time()
        handle.seek(0); handle.truncate(); handle.write(str(started)); handle.flush()
        try:
            yield
        finally:
            time.sleep(max(0, started + gap - time.time()))
            fcntl.flock(handle, fcntl.LOCK_UN)


ROBOTS_RETRY_WAITS = (5, 15, 40)   # seconds before attempts 2..4 at a robots.txt that timed out, failed to connect or answered 5xx/429


def _robots_get(requests, url, waits=None):
    """One robots.txt request with polite retries. A transient failure (timeout, connection error, 429, 5xx) is retried after the waits; if every attempt
    fails the caller records status -1 ('unknown': unreachable) and the next run asks again (robots_row never caches a -1 row). It is never a Disallow:
    robots_decision still refuses to authorize a fetch on it, but the audit must report 'robots_unknown', not 'robots_disallowed' (Nanyang, 2026-11-11:
    two early timeouts stamped 129 listings robots_disallowed on an allow-all robots.txt)."""
    waits = ROBOTS_RETRY_WAITS if waits is None else waits
    last = None
    for i in range(len(waits) + 1):
        try:
            r = requests.get(url, headers={'User-Agent': UA}, timeout=30, allow_redirects=False)
            if r.status_code != 429 and r.status_code < 500:
                return r
            last = r
        except Exception as e:  # noqa: BLE001
            last, err = None, e
        if i < len(waits):
            time.sleep(waits[i])
    if last is not None:
        return last
    raise err


def robots_row(c, host, refresh=False, scheme='https', min_delay=0):
    """The host's robots.txt (stored in `robots`). scheme='http' reads http://host/robots.txt and stores it under the key 'http://host', apart from the HTTPS
    row: an explicitly approved exact-origin policy for a site that only serves http (ZJU, 2026-11-10); HTTPS permission is never inferred from it."""
    import requests
    key = host if scheme == 'https' else f'{scheme}://{host}'
    row = c.execute('select status, body from robots where host=?', (key,)).fetchone()
    if row is not None and row[0] == -1:
        row = None   # an unreachable robots.txt is 'unknown', not a decision: ask again
    if row is None or refresh:
        try:
            url = f'{scheme}://{host}/robots.txt'
            seen = {url}
            for hop in range(6):   # RFC 9309 2.3.1.2: follow at least five redirects
                with shared_origin_slot(host, min_delay) if scheme == 'http' and min_delay else nullcontext():
                    r = _robots_get(requests, url)
                location = getattr(r, 'headers', {}).get('Location')
                if scheme == 'http' and min_delay:  # the charter forbids following redirects
                    break
                if r.status_code not in (301, 302, 303, 307, 308) or not location or hop == 5:
                    break
                target = urllib.parse.urljoin(url, location)
                parsed = urllib.parse.urlsplit(target)
                # A few official sites place robots.txt under /content/dam/, and many send cs.x.edu/robots.txt to
                # www.cs.x.edu/robots.txt. Only HTTPS policy files on the same registered domain may be followed
                # (RFC 9309; a cross-domain redirect is unreadable); never fetch ordinary site content before permission.
                if (parsed.scheme != scheme or registered_domain(parsed.hostname or '') != registered_domain(host) or
                        not parsed.path.endswith('/robots.txt') or parsed.query or parsed.fragment or target in seen):
                    break
                c.execute('create table if not exists robots_redirects (host text, source_url text primary key, target_url text, status int, fetched_at text)')
                c.execute('insert or replace into robots_redirects values (?,?,?,?,?)',
                          (host, url, target, r.status_code, time.strftime('%Y-%m-%dT%H:%M:%S')))
                url = target
                seen.add(url)
            body = r.text if r.status_code == 200 else ''
            row = (r.status_code, body)
            if url != f'{scheme}://{host}/robots.txt':
                c.execute('create table if not exists robots_final (host text primary key, final_url text, status int, body_sha256 text, fetched_at text)')
                c.execute('insert or replace into robots_final values (?,?,?,?,?)',
                          (host, url, r.status_code, hashlib.sha256(body.encode()).hexdigest(), time.strftime('%Y-%m-%dT%H:%M:%S')))
        except Exception as e:  # noqa: BLE001 (network errors of any kind: unreachable)
            row = (-1, repr(e)[:300])
        c.execute('insert or replace into robots values (?,?,?,?)', (key, time.strftime('%Y-%m-%dT%H:%M:%S'), row[0], row[1])); c.commit()
    return row


# Owner ruling 2026-11-12: a robots.txt that answers HTTP 200 with an HTML page holding no robots lines (an SPA catch-all) is 'no rules';
# a service-error / challenge / login page (cloudflare, captcha, anubis, 'Request Error', 'Access Denied', ...) is still not permission.
ROBOTS_LINE_RX = re.compile(r'^\s*(?:user-agent|disallow|allow|sitemap|crawl-delay)\s*:', re.I | re.M)
ROBOTS_HTML_REFUSE_RX = re.compile(r'cf[-_]chl|cf-browser-verification|just a moment|attention required|checking your browser|verify you are (?:a )?human|making sure you.re not a bot|'
                                   r'techaro|anubis[-_.]|g-recaptcha|h-captcha|data-sitekey|bot[- ]?(?:detection|check|protection)|traffic check|type=["\']?password|'
                                   r'<title>[^<]{0,80}(?:log\s?in|sign\s?in|forbidden|unauthori[sz]ed|blocked|error|denied|captcha|challenge|cloudflare|anubis)', re.I)
ROBOTS_HTML_SHORT_RX = re.compile(r'cloudflare|captcha|anubis|request\s+error|access\s+denied|challenge', re.I)   # a short page (a service error / bot-check stub) saying so; a long SPA shell may mention a CDN or a research challenge


def html_robots_is_no_rules(body):
    """True for a 200 robots.txt body that is an HTML page without any robots line and without challenge/error/login markers."""
    b = body or ''
    if '<html' not in b[:2000].lower():
        return False
    return not ROBOTS_LINE_RX.search(b) and not ROBOTS_HTML_REFUSE_RX.search(b[:60000]) and not (len(b) < 12000 and ROBOTS_HTML_SHORT_RX.search(b))



def _robots_no_rules_rulings():
    """The owner-approved exceptions, including any exact path restrictions."""
    try:
        rows = json.loads((Path(__file__).resolve().parents[1] / 'docs' / 'host-rulings.json').read_text()).get('hosts') or []
    except (OSError, ValueError):
        return {}
    return {r['host'].lower(): r for r in rows if (r.get('robots') or {}).get('override') == 'no_rules_by_owner_ruling'}


def robots_ruled_hosts():
    """Unrestricted host rulings for callers that cannot enforce per-URL scope.

    Scoped exceptions deliberately stay out of lpcap's host-wide override set.
    """
    return frozenset(host for host, r in _robots_no_rules_rulings().items() if not r.get('allowed_paths'))


def robots_ruled_no_rules(host, status, body, url=None):
    """Apply an owner robots exception only within its recorded URL scope.

    A real robots.txt and HTTP access refusals or outages remain authoritative.
    """
    ruling = _robots_no_rules_rulings().get((host or '').lower().split(':')[0])
    if ruling is None:
        return False
    paths = ruling.get('allowed_paths')
    if paths:
        parts = urllib.parse.urlsplit(url or '')
        if parts.query or parts.fragment or parts.path.casefold() not in {p.casefold() for p in paths}:
            return False
        # The finite faculty-list ruling covers the observed 200 error stub,
        # never a new HTTP refusal or a challenge response.
        if status != 200 or CHALLENGE.search(body or ''):
            return False
    if status == 405:
        return True
    b = body or ''
    return status == 200 and '<html' in b[:2000].lower() and len(b) < 12000 and not ROBOTS_LINE_RX.search(b)


def robots_decision(status, body, url='/', host=None):
    """(allowed for us, allowed for AI agents by name, crawl delay).
    Missing robots (404/410) has no rules; access refusals and outages never authorize a page request.
    A host with an owner ruling in docs/host-rulings.json (robots_ruled_no_rules) is read as 'no rules'.
    """
    host = host or urllib.parse.urlsplit(url if '//' in url else '//' + url).hostname
    if robots_ruled_no_rules(host, status, body, url=url):
        status, body = 404, ''
    is_html = status == 200 and re.search(r'<html', (body or '')[:2000], re.I)
    if status not in (200, 404, 410) or (is_html and not html_robots_is_no_rules(body)):
        return False, False, 2.0
    rp = urllib.robotparser.RobotFileParser(); rp.parse([] if is_html else (body or '').splitlines() if status == 200 else [])
    ours = rp.can_fetch(UA, url)
    ai = all(rp.can_fetch(a, url) for a in AI_AGENTS)
    # a Crawl-delay in a group that names one of Claude's agents (UChicago Linguistics: 'ClaudeBot ... Crawl-delay: 10') binds this project too
    delay = max([2.0] + [float(rp.crawl_delay(a) or 0) for a in (UA, '*', *AI_AGENTS)])
    return ours, ai, delay


def robots_ok(c, url, same_origin=False, min_delay=0):
    """(allowed, crawl delay). same_origin=True reads robots at the URL's own scheme (an approved http-only origin); the default stays HTTPS."""
    parts = urllib.parse.urlsplit(url)
    host = parts.netloc
    st, body = robots_row(c, host, scheme=parts.scheme, min_delay=min_delay) if same_origin else robots_row(c, host)
    ours, ai, delay = robots_decision(st, body, url)
    return ours and ai, delay


def block(c, host, why):
    _blocked.add(host)
    c.execute('insert or replace into blocked values (?,?,?)', (host, time.strftime('%Y-%m-%dT%H:%M:%S'), why[:300])); c.commit()


def live(c, url, refresh=False, same_origin=False, min_delay=0):
    """A live page (robots honoured, per-host delay); returns (status, sha256, text blocks), or None when robots
    disallows it or the host is blocked (it served a challenge)."""
    import requests
    host = urllib.parse.urlsplit(url).netloc
    row = c.execute('select status, sha256, raw_zlib, content_type from live where url=?', (url,)).fetchone()
    if row is None or refresh:
        if host in _blocked:
            return None
        ok, delay = robots_ok(c, url, same_origin=True, min_delay=min_delay) if same_origin else robots_ok(c, url)
        if not ok:
            return None
        w = _last.get(host, 0) + max(delay, min_delay, 1.0) - time.time()
        if w > 0:
            time.sleep(w)
        try:
            with shared_origin_slot(host, max(delay, min_delay)) if same_origin else nullcontext():
                r = requests.get(url, headers={'User-Agent': UA}, timeout=60, allow_redirects=False)
            body, st, ct = r.content, r.status_code, r.headers.get('Content-Type')
            if 300 <= st < 400:
                # Even a same-host redirect may enter a disallowed path. A reviewer
                # must approve the exact target and check its policy before fetching.
                body = json.dumps({'requested_url': url, 'location': r.headers.get('Location'),
                                   'status': 'redirect_requires_policy_review'}).encode()
                ct = 'application/json'
        except Exception as e:  # noqa: BLE001
            body, st, ct = repr(e).encode(), -1, None
        transport_status = st
        _last[host] = time.time()
        if st in (401, 403, 429) and not apache_path_denial(st, body):
            block(c, host, f'HTTP {st} access refusal at {url}')
        if st in (200, 403, 429, 503) and CHALLENGE.search(body[:20000].decode('utf-8', 'replace')):
            st = 999  # a bot challenge: recorded, never worked around; the host is not used again
            block(c, host, f'challenge at {url}')
        sha = hashlib.sha256(body).hexdigest() if body else None
        # Keep the HTTP status separate from synthetic classifications (e.g. 999).
        c.execute('create table if not exists live_transport (url text primary key, http_status int, classified_status int, sha256 text)')
        c.execute('insert or replace into live_transport values (?,?,?,?)', (url, transport_status, st, sha))
        c.execute('insert or replace into live values (?,?,?,?,?,?,?)', (url, time.strftime('%Y-%m-%dT%H:%M:%S'), st, sha, ct, zlib.compress(body, 6), None)); c.commit()
        row = (st, sha, zlib.compress(body, 6), ct)
    st, sha, raw, ct = row
    b = extract.blocks(zlib.decompress(raw), ct, url) if raw and st == 200 else []
    return st, sha, b


def live_html(c, url):
    r = c.execute('select raw_zlib from live where url=?', (url,)).fetchone()
    return zlib.decompress(r[0]).decode('utf-8', 'replace') if r and r[0] else ''


def flat(blocks):
    """The verification text: block texts joined, whitespace collapsed (quotes must be substrings of it)."""
    return ' '.join(' '.join(t for _, t in blocks).split())


def sha_of_text(s):
    return hashlib.sha256(s.encode()).hexdigest()


if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) < 3 or a[1] not in ('cdx', 'live', 'robots'):
        sys.exit('usage' + __doc__.split('usage', 2)[-1].rstrip())
    c = con(a[0])
    if a[1] == 'cdx':
        for r in cdx_rows(c, a[2], exact=len(a) < 4):
            print(r['timestamp'], r['statuscode'], r['original'], r.get('mimetype'))
    elif a[1] == 'live':
        res = live(c, a[2])
        print(res[0] if res else 'disallowed', res[1] if res else '')
        print(flat(res[2])[:int(os.environ.get('N', 4000))] if res else '')
    elif a[1] == 'robots':
        st, body = robots_row(c, a[2])
        print(st, robots_decision(st, body))
