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
                       # Research citations can contain CAPTCHA; require an actual gate/widget context.
                       r'g-recaptcha|h-captcha|hcaptcha\.com|recaptcha/(?:api|enterprise)|'
                       r'captcha[-_](?:container|challenge|form|input)|'
                       r'<(?:title|h[1-3])[^>]*>[^<]{0,120}captcha|'
                       r'(?:complete|solve|enter) (?:the |this |a )?captcha|'
                       r'captcha(?: validation| verification)? (?:required|failed)', re.I)
_last = {}
_blocked = set()


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
    for (h,) in c.execute('select host from blocked'):
        _blocked.add(h)
    # Old collectors did not persist plain access refusals as host blocks.
    # Reuse their receipts so a new URL cannot silently retry the same host.
    for url, in c.execute('select url from live where status in (401,403,429,999)'):
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
    return body(r[0]).decode('utf-8', 'replace') if r and r[0] else ''


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


def robots_row(c, host, refresh=False):
    import requests
    row = c.execute('select status, body from robots where host=?', (host,)).fetchone()
    if row is None or refresh:
        try:
            url = f'https://{host}/robots.txt'
            seen = {url}
            for hop in range(4):
                r = requests.get(url, headers={'User-Agent': UA}, timeout=30, allow_redirects=False)
                location = getattr(r, 'headers', {}).get('Location')
                if r.status_code not in (301, 302, 303, 307, 308) or not location or hop == 3:
                    break
                target = urllib.parse.urljoin(url, location)
                parsed = urllib.parse.urlsplit(target)
                # A few official sites place robots.txt under /content/dam/.
                # Only same-origin HTTPS policy files may be followed; never
                # fetch another host or ordinary site content before permission.
                if (parsed.scheme != 'https' or parsed.netloc != host or
                        not parsed.path.endswith('/robots.txt') or parsed.query or parsed.fragment or target in seen):
                    break
                c.execute('create table if not exists robots_redirects (host text, source_url text primary key, target_url text, status int, fetched_at text)')
                c.execute('insert or replace into robots_redirects values (?,?,?,?,?)',
                          (host, url, target, r.status_code, time.strftime('%Y-%m-%dT%H:%M:%S')))
                url = target
                seen.add(url)
            body = r.text if r.status_code == 200 else ''
            row = (r.status_code, body)
        except Exception as e:  # noqa: BLE001 (network errors of any kind: unreachable)
            row = (-1, repr(e)[:300])
        c.execute('insert or replace into robots values (?,?,?,?)', (host, time.strftime('%Y-%m-%dT%H:%M:%S'), row[0], row[1])); c.commit()
    return row


def robots_decision(status, body, url='/'):
    """(allowed for us, allowed for AI agents by name, crawl delay).
    Missing robots (404/410) has no rules; access refusals and outages never authorize a page request.
    """
    if status not in (200, 404, 410) or (status == 200 and re.search(r'<html', (body or '')[:2000], re.I)):
        return False, False, 2.0
    rp = urllib.robotparser.RobotFileParser(); rp.parse((body or '').splitlines() if status == 200 else [])
    ours = rp.can_fetch(UA, url)
    ai = all(rp.can_fetch(a, url) for a in AI_AGENTS)
    # a Crawl-delay in a group that names one of Claude's agents (UChicago Linguistics: 'ClaudeBot ... Crawl-delay: 10') binds this project too
    delay = max([2.0] + [float(rp.crawl_delay(a) or 0) for a in (UA, '*', *AI_AGENTS)])
    return ours, ai, delay


def robots_ok(c, url):
    host = urllib.parse.urlsplit(url).netloc
    st, body = robots_row(c, host)
    ours, ai, delay = robots_decision(st, body, url)
    return ours and ai, delay


def block(c, host, why):
    _blocked.add(host)
    c.execute('insert or replace into blocked values (?,?,?)', (host, time.strftime('%Y-%m-%dT%H:%M:%S'), why[:300])); c.commit()


def live(c, url, refresh=False):
    """A live page (robots honoured, per-host delay); returns (status, sha256, text blocks), or None when robots
    disallows it or the host is blocked (it served a challenge)."""
    import requests
    host = urllib.parse.urlsplit(url).netloc
    row = c.execute('select status, sha256, raw_zlib, content_type from live where url=?', (url,)).fetchone()
    if row is None or refresh:
        if host in _blocked:
            return None
        ok, delay = robots_ok(c, url)
        if not ok:
            return None
        w = _last.get(host, 0) + max(delay, 1.0) - time.time()
        if w > 0:
            time.sleep(w)
        try:
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
        if st in (401, 403, 429):
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
