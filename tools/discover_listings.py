"""Stage 1 discovery in one command: which candidate listing URLs have Wayback captures in which half-years (ADDING-A-SCHOOL stage 1).

`school_web.py <key> cdx <url>` prints one line per monthly capture, so finding a department's URL eras meant reading hundreds of lines per
URL. This prints one line per URL: the 200-capture count and the half-years of 2016-2026 that have one, and the gap list, so the eras of a
slot can be read off at once and written into the charter's [[departments.listings]].

  discover_listings.py <key> <url> [<url> ...]     exact-URL CDX queries (collapse=timestamp:6), one shared Wayback lock (6 s per request)
  --from 2016 --to 2026                            the window
  --json                                           machine-readable
"""
import argparse, json, sys

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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('key'); ap.add_argument('urls', nargs='+')
    ap.add_argument('--from', dest='frm', type=int, default=2016); ap.add_argument('--to', type=int, default=2026)
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    c = W.con(a.key)
    out = {}
    for u in a.urls:
        out[u] = summarize(W.cdx_rows(c, u, frm=str(a.frm), to=str(a.to), collapse='timestamp:6'), a.frm, a.to)
        if not a.json:
            print(line(u, out[u]), flush=True)
    if a.json:
        print(json.dumps(out, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
