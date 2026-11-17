"""Stage 1 discovery in one command: which candidate listing URLs have Wayback captures in which half-years (ADDING-A-SCHOOL stage 1).

`school_web.py <key> cdx <url>` prints one line per monthly capture, so finding a department's URL eras meant reading hundreds of lines per
URL. This prints one line per URL: the 200-capture count and the half-years of 2016-2026 that have one, and the gap list, so the eras of a
slot can be read off at once and written into the charter's [[departments.listings]].

  discover_listings.py <key> <url> [<url> ...]     exact-URL CDX queries (collapse=timestamp:6), one shared Wayback lock (6 s per request)
  --from 2016 --to 2026                            the window
  --json                                           machine-readable
  --sample 2016,2020,2024 --out <dir>              also fetch, per URL and year, the capture nearest mid-year into <dir> (for writing the page formats BEFORE
                                                   the captures run: Georgia Tech friction 8) and print the format that parses it, its entries and whether it is paged
  --offline --report <file>                     inspect saved evidence without network or cache writes; exit 3 means pending, never no-capture
"""
import argparse, hashlib, json, re, sqlite3, sys, zlib
from pathlib import Path
from urllib.parse import urlencode

import school_web as W  # noqa: E402

HALVES = ('H1', 'H2')


class DiscoveryPending(RuntimeError):
    """Missing or failed evidence, never an empty successful inventory."""


def index_rows(c, url, frm, to, offline=False):
    params = {'url': url, 'from': str(frm), 'to': str(to), 'output': 'json',
              'fl': 'urlkey,timestamp,original,statuscode,digest,mimetype', 'limit': '30000',
              'filter': 'statuscode:200', 'collapse': 'timestamp:6'}
    if not offline:
        rows = W.wb.cdx(params, c)
        if rows is None:
            raise DiscoveryPending('CDX request failed; capture availability remains unknown')
        return rows
    query = 'https://web.archive.org/cdx/search/cdx?' + urlencode(params)
    saved = c.execute('select status, body from cdx where query=?', (query,)).fetchone()
    if not saved or saved[0] != 200:
        raise DiscoveryPending('No successful exact CDX response is cached')
    try:
        records = json.loads(saved[1]) if saved[1].strip() else []
        if not records:
            return []
        if not isinstance(records, list) or not isinstance(records[0], list):
            raise ValueError('invalid CDX table')
        if not {'timestamp', 'original'} <= set(records[0]):
            raise ValueError('missing CDX columns')
        if any(not isinstance(row, list) or len(row) != len(records[0]) for row in records[1:]):
            raise ValueError('incomplete CDX row')
        rows = [dict(zip(records[0], row)) for row in records[1:]]
        if any(not re.fullmatch(r'\d{14}', str(r['timestamp'])) or not isinstance(r['original'], str) for r in rows):
            raise ValueError('invalid capture identity')
        return rows
    except (ValueError, TypeError) as error:
        raise DiscoveryPending('Cached CDX response is not a valid capture table') from error


def cached_capture(c, row):
    cap = f"https://web.archive.org/web/{row['timestamp']}id_/{row['original']}"
    saved = c.execute('select http_status, sha256, raw_zlib from captures where capture_url=?', (cap,)).fetchone()
    if not saved:
        raise DiscoveryPending('Requested sample is not cached')
    status, sha, raw = saved
    if raw and (not sha or hashlib.sha256(zlib.decompress(raw)).hexdigest() != sha):
        raise DiscoveryPending('Cached sample hash does not match its receipt')
    return cap, status, sha, W.wb.text(W.body(raw)) if raw else ''


def half(ts):
    return f'{ts[:4]}{HALVES[0 if int(ts[4:6]) <= 6 else 1]}'


def summarize(rows, frm=2016, to=2026):
    """{'captures': n, 'halves': [...], 'missing': [...], 'first': ts, 'last': ts, 'finals': [original urls seen]} from CDX rows."""
    have = sorted({half(r['timestamp']) for r in rows})
    allh = [f'{y}{h}' for y in range(frm, to + 1) for h in HALVES]
    ts = sorted(r['timestamp'] for r in rows)
    return dict(captures=len(rows), halves=have, missing=[h for h in allh if h not in have] if rows else allh,
                first=ts[0] if ts else None, last=ts[-1] if ts else None,
                originals=sorted({r['original'].split('://')[-1] for r in rows})[:4])


def line(url, s):
    if not s['captures']:
        return f'{url}: no 200 capture'
    by_year = {}
    for h in s['halves']:
        by_year.setdefault(h[:4], []).append(h[4:])
    yrs = ' '.join(f"{y}{''.join(v)}" for y, v in by_year.items())
    return f"{url}: {s['captures']} captures {s['first'][:8]}..{s['last'][:8]}; {yrs}"


def nearest(rows, year):
    """The CDX row whose timestamp is nearest mid-year of `year` (None when the URL has no capture within that year)."""
    ys = [r for r in rows if r['timestamp'].startswith(str(year))]
    return min(ys, key=lambda r: abs(int(r['timestamp'][4:6]) * 31 + int(r['timestamp'][6:8]) - 186)) if ys else None


def sample(c, key, url, rows, years, out, offline=False, receipts=None):
    import listing_formats as LF
    lines = []
    cache_only = offline
    for y in years:
        r = nearest(rows, y)
        if not r:
            if receipts is not None:
                receipts.append(dict(year=y, status='no_capture_in_successful_index'))
            lines.append(f'  {y}: no capture'); continue
        try:
            if cache_only:
                cap, st, sha, h = cached_capture(c, r)
            else:
                cap, st, sha, _ = W.capture(c, r['timestamp'], r['original'], url, key)
                h = W.raw_html(c, cap)
            if st != 200 or not h.strip() or W.CHALLENGE.search(h):
                raise DiscoveryPending(f'Sample has HTTP {st}, an empty body, or a challenge')
        except (DiscoveryPending, RuntimeError) as error:
            # Once the archive refuses or fails, inspect the remaining cache only.
            # Do not keep issuing requests to the same host during a cooldown.
            cache_only = True
            if receipts is None:
                raise DiscoveryPending(str(error)) from error
            receipts.append(dict(year=y, status='pending', timestamp=r['timestamp'], original=r['original'], reason=str(error)))
            lines.append(f'  {y}: pending: {error}')
            continue
        name = out / (re.sub(r'\W+', '_', url) + f"_{r['timestamp'][:8]}.html")
        name.write_text(h)
        fmt, es = LF.parse(h)
        if receipts is not None:
            receipts.append(dict(year=y, status='sampled_unreviewed', timestamp=r['timestamp'], capture_url=cap,
                                 sha256=sha, format=fmt, entries=len(es), paged=LF.is_paged(h), file=str(name)))
        lines.append(f"  {y}: {r['timestamp'][:8]} http {st} {len(h)} bytes -> {name.name}; format {fmt}, {len(es)} entries{', PAGED (' + str(len(LF.page_links(h, r['original']))) + ' more pages)' if LF.is_paged(h) else ''}")
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('key'); ap.add_argument('urls', nargs='+')
    ap.add_argument('--from', dest='frm', type=int, default=2016); ap.add_argument('--to', type=int, default=2026)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--offline', action='store_true', help='Read cached responses only, with no network or cache writes')
    ap.add_argument('--report', type=Path, help='Write per-URL/sample completion states, including pending evidence')
    ap.add_argument('--sample', help='comma-separated years to fetch one capture of per URL'); ap.add_argument('--out', help='directory for the sampled pages')
    a = ap.parse_args(argv)
    if a.sample and not a.out:
        ap.error('--sample needs --out <dir>')
    if a.offline:
        database = W.db_path(a.key)
        if not database.exists():
            c = None
        else:
            c = sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)
    else:
        c = W.con(a.key)
    out = {}
    reports = {}
    cache_only = a.offline
    for u in a.urls:
        report = reports[u] = dict(status='pending', samples=[])
        try:
            if c is None:
                raise DiscoveryPending('School capture database does not exist')
            rows = index_rows(c, u, a.frm, a.to, offline=cache_only)
        except (DiscoveryPending, RuntimeError, ValueError) as error:
            cache_only = True
            report['reason'] = str(error)
            if not a.json:
                print(f'{u}: pending: {error}', flush=True)
            continue
        out[u] = summarize(rows, a.frm, a.to)
        report['index'] = out[u]
        if not a.json:
            print(line(u, out[u]), flush=True)
        if a.sample:
            od = Path(a.out); od.mkdir(parents=True, exist_ok=True)
            for l in sample(c, a.key, u, rows, [int(y) for y in a.sample.split(',')], od,
                            offline=cache_only, receipts=report['samples']):
                if not a.json:
                    print(l, flush=True)
        report['status'] = 'pending' if any(r['status'] == 'pending' for r in report['samples']) else 'discovered_unreviewed'
        if report['status'] == 'pending':
            cache_only = True
    if c is not None:
        c.close()
    if a.report:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(json.dumps(dict(school=a.key, offline=a.offline, urls=reports,
                                           interpretation='Discovery only; no faculty years or listing acceptance are implied.'), indent=2) + '\n')
    if a.json:
        print(json.dumps({u: dict(r.get('index', {}), **{k: v for k, v in r.items() if k != 'index'})
                          for u, r in reports.items()}, indent=1))
    return 3 if any(r['status'] == 'pending' for r in reports.values()) else 0


if __name__ == '__main__':
    sys.exit(main())
