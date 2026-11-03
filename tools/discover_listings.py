"""Stage 1 discovery in one command: which candidate listing URLs have Wayback captures in which half-years (ADDING-A-SCHOOL stage 1).

`school_web.py <key> cdx <url>` prints one line per monthly capture, so finding a department's URL eras meant reading hundreds of lines per
URL. This prints one line per URL: the 200-capture count and the half-years of 2016-2026 that have one, and the gap list, so the eras of a
slot can be read off at once and written into the charter's [[departments.listings]].

  discover_listings.py <key> <url> [<url> ...]     exact-URL CDX queries (collapse=timestamp:6), one shared Wayback lock (6 s per request)
  --from 2016 --to 2026                            the window
  --json                                           machine-readable
  --sample 2016,2020,2024 --out <dir>              also fetch, per URL and year, the capture nearest mid-year into <dir> (for writing the page formats BEFORE
                                                   the captures run: Georgia Tech friction 8) and print the format that parses it, its entries and whether it is paged
"""
import argparse, json, re, sys
from pathlib import Path

import school_web as W  # noqa: E402

HALVES = ('H1', 'H2')


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


def sample(c, key, url, rows, years, out):
    import listing_formats as LF
    lines = []
    for y in years:
        r = nearest(rows, y)
        if not r:
            lines.append(f'  {y}: no capture'); continue
        cap, st, sha, _ = W.capture(c, r['timestamp'], r['original'], url, key)
        h = W.raw_html(c, cap)
        name = out / (re.sub(r'\W+', '_', url) + f"_{r['timestamp'][:8]}.html")
        name.write_text(h)
        fmt, es = LF.parse(h)
        lines.append(f"  {y}: {r['timestamp'][:8]} http {st} {len(h)} bytes -> {name.name}; format {fmt}, {len(es)} entries{', PAGED (' + str(len(LF.page_links(h, r['original']))) + ' more pages)' if LF.is_paged(h) else ''}")
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('key'); ap.add_argument('urls', nargs='+')
    ap.add_argument('--from', dest='frm', type=int, default=2016); ap.add_argument('--to', type=int, default=2026)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--sample', help='comma-separated years to fetch one capture of per URL'); ap.add_argument('--out', help='directory for the sampled pages')
    a = ap.parse_args(argv)
    c = W.con(a.key)
    out = {}
    if a.sample and not a.out:
        ap.error('--sample needs --out <dir>')
    for u in a.urls:
        rows = W.cdx_rows(c, u, frm=str(a.frm), to=str(a.to), collapse='timestamp:6')
        out[u] = summarize(rows, a.frm, a.to)
        if not a.json:
            print(line(u, out[u]), flush=True)
        if a.sample and rows:
            od = Path(a.out); od.mkdir(parents=True, exist_ok=True)
            for l in sample(c, a.key, u, rows, [int(y) for y in a.sample.split(',')], od):
                print(l, flush=True)
    if a.json:
        print(json.dumps(out, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
