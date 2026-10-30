# Vendored 2026-10-30 from /n/fs/resemble/homogenizing-science/scripts/sweep10_lib.py (sha256 9eae69995244fca1bd455fe5fd83f0fd5d56afe1681b2b69eb7b46e9dbacad83); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Ten-university inventory sweep: polite source capture, inspection and mention records.

Layout (invisible to finalize.py until build_sweep10.py writes the top-level CSVs):
  data/batches/sweep10_<batch>/<university_id>/snapshots/<source_id>.<ext>   original bytes
  data/batches/sweep10_<batch>/<university_id>/sources.jsonl                 one metadata line per capture
  data/batches/sweep10_<batch>/<university_id>/attempts.jsonl                every request, including failures
  data/batches/sweep10_<batch>/<university_id>/extract.py                    offline replay -> mentions.json

CLI (run with the project interpreter from the project root):
  python scripts/sweep10_lib.py fetch   BATCH UID URL [URL ...]
  python scripts/sweep10_lib.py show    BATCH UID SOURCE_ID [--links] [--grep REGEX] [--max N]
  python scripts/sweep10_lib.py list    BATCH UID
  python scripts/sweep10_lib.py existing UID
Captures respect robots.txt and wait at least DELAY seconds between requests to one host.
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import argparse, csv, gzip, hashlib, json, re, subprocess, sys, time, unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib import robotparser

ROOT = P.WORLD_ATLAS  # vendored: the data root (was Path(__file__).resolve().parents[1])
AS_OF = '2026-10-12'
UA = 'Mozilla/5.0 (compatible; HomogenizingScienceResearch/0.1; public academic directory research)'
DELAY = 1.5
BROAD_FIELDS = ['mathematics_and_statistics', 'computer_and_information_sciences', 'physical_sciences',
                'chemical_sciences', 'earth_and_environmental_sciences', 'biological_and_health_sciences',
                'engineering_and_technology', 'agricultural_and_veterinary_sciences', 'social_sciences',
                'interdisciplinary']
UNIT_TYPES = ['laboratory', 'research_group', 'research_center', 'research_institute', 'research_unit', 'chair']
SCOPES = ['in_scope', 'needs_scope_review', 'excluded_humanities', 'excluded_non_research']


def batch_dir(batch):
    return ROOT / 'data/batches' / ('sweep10_' + batch)


def uni_dir(batch, uid):
    return batch_dir(batch) / uid


def clean(v):
    return re.sub(r'\s+', ' ', str(v or '')).strip()


def stable_id(prefix, value):
    return prefix + '_' + hashlib.sha256(value.encode()).hexdigest()[:16]


def norm(v):
    return clean(unicodedata.normalize('NFKC', str(v or ''))).casefold()


def key(v):
    """Comparison key: accents, case, punctuation and a leading 'the' ignored. Latin text reduces to [a-z0-9];
    letters and digits of other scripts (CJK, Hangul, Cyrillic, Greek, Arabic...) are kept, so names written
    only in those scripts still have a key."""
    s = unicodedata.normalize('NFKD', str(v or '').casefold())
    s = re.sub(r'^\s*the\s+', '', s)
    out = []
    for ch in s:
        if ch.isascii():
            if ch.isalnum():
                out.append(ch)
        elif unicodedata.category(ch)[0] in 'LN' and not unicodedata.combining(ch):
            if unicodedata.category(ch) == 'Nd':
                out.append(str(unicodedata.digit(ch)))  # fullwidth and other decimal digits
            elif not ('LATIN' in unicodedata.name(ch, '')):
                out.append(ch)  # non-Latin letters; Latin ones (e.g. ø, ß, æ) keep the old ASCII-only behaviour
    return ''.join(out)


def canonical(url):
    p = urlsplit(url)
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip('/'), p.query, ''))


def urlkey(url):
    return canonical(url).split('://')[-1].removeprefix('www.') if url else ''


def read_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def append_jsonl(path, row):
    with Path(path).open('a', encoding='utf-8') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')


# ---------------------------------------------------------------- capture

_robots = {}
# Cross-process throttle state: tiny files on RAM-backed /dev/shm, so a full /tmp cannot stop captures.
THROTTLE_DIR = Path('/dev/shm/sweep10_throttle') if Path('/dev/shm').is_dir() else Path('/tmp/sweep10_throttle')
_crawl_delay = {}  # host -> seconds requested by robots.txt Crawl-delay (capped at 30)


def _host_wait(host):
    """Minimum spacing between requests to one host, shared by every sweep process on this machine."""
    import fcntl
    lockdir = THROTTLE_DIR
    try:
        lockdir.mkdir(exist_ok=True)
    except OSError:
        time.sleep(4.0 if host.endswith('archive.org') else DELAY)  # no shared lock available: in-process spacing only
        return
    remembered = lockdir / (re.sub(r'[^A-Za-z0-9.-]', '_', host) + '.crawl_delay')
    if host not in _crawl_delay and remembered.exists():
        try:
            _crawl_delay[host] = float(remembered.read_text() or 0)
        except ValueError:
            pass
    delay = max(4.0 if host.endswith('archive.org') else DELAY, _crawl_delay.get(host, 0))
    try:
        with open(lockdir / re.sub(r'[^A-Za-z0-9.-]', '_', host), 'a+') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.seek(0)
            try:
                last = float(f.read().strip() or 0)
            except ValueError:
                last = 0
            gap = time.time() - last
            if gap < delay:
                time.sleep(delay - gap)
            f.seek(0); f.truncate(); f.write(str(time.time())); f.flush()
    except OSError:
        time.sleep(delay)


def get(url, **kw):
    """GET with backoff on rate limiting and transient server errors."""
    import requests
    host = urlsplit(url).netloc
    timeout = kw.pop('timeout', 45)
    err = None
    for wait in [0, 10, 30, 60]:
        if wait:
            time.sleep(wait)
        _host_wait(host)
        try:
            r = requests.get(url, timeout=timeout, headers={'User-Agent': UA, 'Accept-Language': 'en,*;q=0.5'}, **kw)
        except (requests.ConnectionError, requests.Timeout) as e:
            err = e
            if re.search(r'NameResolution|Name or service not known|Failed to resolve|No address associated|nodename nor servname', str(e)):
                break  # a host that does not resolve will not resolve on retry
            continue
        if r.status_code not in (429, 502, 503, 504):
            return r
        err = None
    if err:
        raise err
    return r


def robots_allowed(url):
    import requests
    p = urlsplit(url)
    if p.netloc == 'web.archive.org':
        return True, ''
    base = f'{p.scheme}://{p.netloc}'
    if base not in _robots:
        rp = robotparser.RobotFileParser()
        try:
            r = get(base + '/robots.txt', timeout=20)
            rp.parse(r.text.splitlines() if r.status_code == 200 else [])
        except Exception:
            rp.parse([])
        _robots[base] = rp
        try:
            cd = float(rp.crawl_delay(UA) or rp.crawl_delay('*') or 0)
        except (TypeError, ValueError):
            cd = 0
        _crawl_delay[p.netloc] = min(cd, 30.0)
        try:
            THROTTLE_DIR.mkdir(exist_ok=True)
            (THROTTLE_DIR / (re.sub(r'[^A-Za-z0-9.-]', '_', p.netloc) + '.crawl_delay')).write_text(str(_crawl_delay[p.netloc]))
        except OSError:
            pass
    ok = _robots[base].can_fetch(UA, url)
    return ok, '' if ok else 'robots.txt disallows this path for generic user agents'


def _ext(content_type, url):
    ct = (content_type or '').lower()
    for marker, ext in [('pdf', '.pdf'), ('json', '.json'), ('xml', '.xml'), ('html', '.html'), ('text/plain', '.txt')]:
        if marker in ct:
            return ext
    suffix = Path(urlsplit(url).path).suffix.lower()
    return suffix if suffix in {'.pdf', '.json', '.xml', '.txt', '.csv'} else '.html'


def fetch(batch, uid, url):
    import requests
    d = uni_dir(batch, uid)
    (d / 'snapshots').mkdir(parents=True, exist_ok=True)
    source_id = stable_id('src_sw10', url)
    now = datetime.now(timezone.utc).isoformat()
    attempt = dict(source_id=source_id, requested_url=url, retrieved_at_utc=now, university_id=uid)
    ok, why = robots_allowed(url)
    if not ok:
        attempt.update(status='robots_disallowed', http_status='', error=why)
        append_jsonl(d / 'attempts.jsonl', attempt)
        return attempt
    try:
        r = get(url)
    except Exception as e:
        attempt.update(status='request_failed', http_status='', error=f'{type(e).__name__}: {e}'[:400])
        append_jsonl(d / 'attempts.jsonl', attempt)
        return attempt
    attempt.update(http_status=r.status_code, final_url=r.url)
    if r.status_code != 200 or not r.content:
        attempt.update(status='http_error', error=f'HTTP {r.status_code}')
        append_jsonl(d / 'attempts.jsonl', attempt)
        return attempt
    ext = _ext(r.headers.get('Content-Type', ''), r.url)
    # Content-addressed name: a re-capture of the same URL never overwrites bytes that existing metadata points to.
    path = d / 'snapshots' / (source_id + '_' + hashlib.sha256(r.content).hexdigest()[:12] + ext)
    tmp = path.with_suffix(path.suffix + '.part')
    tmp.write_bytes(r.content)
    tmp.replace(path)
    archive = re.match(r'https?://web\.archive\.org/web/(\d{8,14})', r.url or url)
    meta = dict(source_id=source_id, requested_url=url, final_url=r.url, observed_on=AS_OF, retrieved_at_utc=now,
                http_status=r.status_code, content_type=r.headers.get('Content-Type', ''),
                sha256=hashlib.sha256(r.content).hexdigest(), snapshot_path=str(path.relative_to(ROOT)),
                archive_capture=archive.group(1) if archive else '')
    append_jsonl(d / 'sources.jsonl', meta)
    attempt.update(status='captured', sha256=meta['sha256'], bytes=len(r.content))
    append_jsonl(d / 'attempts.jsonl', attempt)
    return dict(attempt, **meta)


# ---------------------------------------------------------------- replay helpers

def sources(uni_path):
    """Latest metadata per source_id for one university directory, verified against preserved bytes."""
    out = {}
    for m in read_jsonl(Path(uni_path) / 'sources.jsonl'):
        out[m['source_id']] = m
    return out


def raw(meta):
    data = (ROOT / meta['snapshot_path']).read_bytes()
    assert hashlib.sha256(data).hexdigest() == meta['sha256'], 'Changed snapshot: ' + meta['snapshot_path']
    return data


def decoded(meta):
    data = raw(meta)
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        from bs4 import BeautifulSoup
        declared = re.search(r'charset\s*=\s*["\']?([^;\s"\']+)', meta.get('content_type', ''), re.I)
        s = BeautifulSoup(data, 'html.parser', from_encoding=declared.group(1) if declared else None)
        return data.decode(s.original_encoding or 'latin-1', errors='replace')


def soup(meta):
    from bs4 import BeautifulSoup
    return BeautifulSoup(decoded(meta), 'html.parser')


def _strings(v):
    if isinstance(v, dict):
        for x in v.values():
            yield from _strings(x)
    elif isinstance(v, list):
        for x in v:
            yield from _strings(x)
    elif isinstance(v, str):
        yield v


def text(meta):
    """Visible text used for verifying that every recorded name appears in its source."""
    path = ROOT / meta['snapshot_path']
    raw(meta)
    if path.suffix == '.pdf':
        return clean(subprocess.run(['pdftotext', '-layout', str(path), '-'], check=True, capture_output=True, text=True).stdout)
    body = decoded(meta)
    if path.suffix == '.json':
        try:
            from bs4 import BeautifulSoup
            return clean(' '.join(BeautifulSoup(s, 'html.parser').get_text(' ') if '<' in s else s
                                  for s in _strings(json.loads(body))))
        except json.JSONDecodeError:
            return clean(body)
    if path.suffix in {'.html', '.xml'}:
        s = soup(meta)
        for t in s(['script', 'style', 'noscript']):
            t.decompose()
        return clean(s.get_text(' '))
    return clean(body)


def mention(meta, name, *, homepage_url='', department='', unit_type='', broad_field='', principal_investigator='',
            pi_role='', acronym='', scope_status='in_scope', evidence='', note=''):
    """One explicitly named unit observed in one preserved source."""
    href = urljoin(meta.get('final_url') or meta['requested_url'], homepage_url) if homepage_url else ''
    if href.startswith('mailto:') or href.startswith('javascript:'):
        href = ''
    return dict(name=clean(name), acronym=clean(acronym), unit_type=unit_type, broad_field=broad_field,
                department=clean(department), principal_investigator=clean(principal_investigator),
                pi_role=clean(pi_role), homepage_url=href.split('#')[0] if href else '', source_id=meta['source_id'],
                evidence=clean(evidence)[:600], scope_status=scope_status, note=clean(note),
                archive_capture=meta.get('archive_capture', ''))


def write_mentions(uni_path, rows):
    Path(uni_path, 'mentions.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'{len(rows)} mentions written to {Path(uni_path, "mentions.json")}')


# ---------------------------------------------------------------- baseline inventory

def read_csv(path):
    with Path(path).open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def baseline_rows(exclude_batch=''):
    """Current processed inventory plus unmerged batch/review proposals, for duplicate checks."""
    own = f'sweep10_{exclude_batch};' if exclude_batch else None
    rows = [r for r in read_csv(ROOT / 'data/processed/labs.csv') if not (own and own in r.get('source_tags', ''))]
    paths = []
    for d in sorted((ROOT / 'data/batches').glob('*')):
        if d.is_dir() and d.name != 'sweep10_' + exclude_batch:
            f = next((d / n for n in ['all_candidates.csv', 'all_directory_units.csv', 'labs.csv'] if (d / n).exists()), None)
            if f:
                paths.append(f)
    paths += sorted((ROOT / 'data/reviews').glob('*/labs.csv'))
    for f in paths:
        try:
            rows += [r for r in read_csv(f) if r.get('university_id') and r.get('lab_name')]
        except Exception:
            pass
    return rows


# ---------------------------------------------------------------- CLI

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    f = sub.add_parser('fetch'); f.add_argument('batch'); f.add_argument('uid'); f.add_argument('urls', nargs='+')
    s = sub.add_parser('show'); s.add_argument('batch'); s.add_argument('uid'); s.add_argument('source_id')
    s.add_argument('--links', action='store_true'); s.add_argument('--grep', default=''); s.add_argument('--max', type=int, default=20000)
    l = sub.add_parser('list'); l.add_argument('batch'); l.add_argument('uid')
    e = sub.add_parser('existing'); e.add_argument('uid')
    w = sub.add_parser('wayback'); w.add_argument('url')
    a = ap.parse_args()
    if a.cmd == 'wayback':
        # One successful capture per year, 2016 onward; fetch with https://web.archive.org/web/<ts>id_/<url>
        import requests
        r = get('https://web.archive.org/cdx/search/cdx', timeout=60,
                         params=dict(url=a.url, output='json', fl='timestamp,original,statuscode', filter='statuscode:200',
                                     collapse='timestamp:4', **{'from': '2016', 'to': '2026'}))
        rows = r.json()[1:] if r.ok and r.text.strip() else []
        for ts, orig, code in rows:
            print(ts, f'https://web.archive.org/web/{ts}id_/{orig}')
        if not rows:
            print('no 200 captures 2016-2026 for', a.url, f'(HTTP {r.status_code})')
        return
    if a.cmd == 'fetch':
        for url in a.urls:
            r = fetch(a.batch, a.uid, url)
            extra = ''
            if r.get('status') == 'captured':
                t = text(r)
                title = ''
                if r['snapshot_path'].endswith('.html'):
                    ts = soup(r).title
                    title = clean(ts.get_text()) if ts else ''
                extra = f" bytes={r['bytes']} text_chars={len(t)} title={title[:90]!r}"
                if r['snapshot_path'].endswith('.html') and len(t) < 600:
                    extra += ' WARNING: little visible text (client-rendered shell? look for a JSON/API source)'
            print(f"{r['source_id']} {r['status']} http={r.get('http_status','')} {r.get('final_url', url)}{extra} {r.get('error','')}")
    elif a.cmd == 'show':
        meta = sources(uni_dir(a.batch, a.uid))[a.source_id]
        if a.links:
            s_ = soup(meta)
            for i, link in enumerate(s_.select('a[href]')):
                label = clean(link.get_text(' '))
                href = urljoin(meta.get('final_url') or meta['requested_url'], link['href'])
                line = f'{i}\t{label}\t{href}'
                if not a.grep or re.search(a.grep, line, re.I):
                    print(line[:300])
        else:
            t = text(meta)
            if a.grep:
                for m in re.finditer(a.grep, t, re.I):
                    print('...' + t[max(0, m.start() - 150):m.end() + 150] + '...')
            else:
                print(t[:a.max])
    elif a.cmd == 'list':
        for m in sources(uni_dir(a.batch, a.uid)).values():
            print(m['source_id'], m['http_status'], m.get('archive_capture', ''), m['final_url'])
        for r in read_jsonl(uni_dir(a.batch, a.uid) / 'attempts.jsonl'):
            if r['status'] != 'captured':
                print('FAILED', r['status'], r.get('http_status', ''), r['requested_url'], r.get('error', ''))
    elif a.cmd == 'existing':
        rows = [r for r in baseline_rows() if r['university_id'] == a.uid]
        seen = set()
        by_dept = {}
        for r in rows:
            k = key(r['lab_name'])
            if k in seen:
                continue
            seen.add(k)
            by_dept.setdefault(r.get('department') or '(no department)', []).append(r['lab_name'])
        print(f'{len(seen)} distinct existing unit names for {a.uid}')
        for dept, names in sorted(by_dept.items(), key=lambda x: -len(x[1])):
            print(f'\n## {dept} ({len(names)})')
            print('; '.join(sorted(names)))


if __name__ == '__main__':
    main()
