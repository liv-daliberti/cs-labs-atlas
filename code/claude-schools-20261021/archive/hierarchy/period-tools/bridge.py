"""Bridged appointment periods from dated listing rows (appointment-period review, 2026-10-26).

For a PI listed as faculty in dated department listings before and after a year with no capture of any of their
department listings, the reviewed period runs from the first dated faculty listing in the window (a lower bound on the
start, stated in the note) to the last dated faculty listing (asof, no end claimed). Rows used: listings/<school>/
listings.json rows (no future-start note, not emeritus/visiting, not lecturer-only) plus the PI's dated census
sources in hierarchy/<school>/pis.json. Each capture is copied into hierarchy/period-captures.sqlite (sha256 re-checked)
and each quote verified there by pcap.ev; a quote that the store's text view cannot show is kept from the listing
store with its own verification note.
usage: bridge.py <school> <pi> [<pi> ...]   -> appends/replaces entries in proposals/<school>-bridged.json
"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import pcap

HERE = Path(__file__).resolve().parents[2]
MAXGAP = int(sys.argv[sys.argv.index('--max-gap') + 1]) if '--max-gap' in sys.argv else 99
args = [a for i, a in enumerate(sys.argv[1:], 1) if a != '--max-gap' and sys.argv[i - 1] != '--max-gap']
school, names = args[0], args[1:]
L = json.load(open(HERE / f'listings/{school}/listings.json'))
P = {p['pi']: p for p in json.load(open(HERE / f'hierarchy/{school}/pis.json'))}
out_f = HERE / f'hierarchy/period-tools/proposals/{school}-bridged.json'
CENSUS = {}
for _f in (HERE / f'census/{school}-additions.json', HERE / f'census/{school}-faculty-hierarchy.json', HERE / f'census/{school}-faculty.json'):
    if _f.exists():
        _c = json.load(open(_f)); _c = _c.get('faculty', _c) if isinstance(_c, dict) else _c
        for _x in _c:
            CENSUS.setdefault(_x['name'], []).extend(_x.get('sources') or [])
out = {e['pi']: e for e in (json.load(open(out_f)) if out_f.exists() else [])}
LECT = lambda r: re.search(r'Lecturer', r.get('rank_as_listed') or '', re.I) and not re.search(r'Professor', r.get('rank_as_listed') or '', re.I)


def evidence(r):
    kind = 'dept_listing:' + r['department'] + (' (profile page)' if r.get('listing') == 'department profile page' else '')
    try:
        if 'web.archive.org' in r['capture_url'] and not pcap.cached(r['capture_url']):
            pcap.copy_listing(school, r['capture_url'])
        return pcap.ev(r['capture_url'], r['quote'], kind, r['observed_on'])
    except (ValueError, KeyError) as e:
        return dict(url=r['capture_url'], sha256=r['sha256'], quote=r['quote'], observed=r['observed_on'], kind=kind,
                    note=f'quote verified by the listings pipeline against listings/{school}/captures.sqlite ({str(e)[:60]})')


for pi in names:
    rows = [r for r in L if r['pi'] == pi and not r.get('future_start_note') and not r.get('emeritus') and not r.get('visiting') and not LECT(r)]
    for l in P[pi]['listings']:
        if l.get('emeritus') or l.get('visiting') or not l.get('url') or re.search(r'emerit|Graduate School|visiting|retired', l.get('quote') or '', re.I):
            continue
        if re.search(r'Lecturer', l.get('quote') or '', re.I) and not re.search(r'Professor', l.get('quote') or '', re.I):
            continue
        obs = (re.search(r'/web/(\d{8})', l['url']) or [None, None])[1]
        if not obs:  # a live census source: its observed date is in the census row
            src = next((s_ for s_ in CENSUS.get(pi, []) if s_.get('url') == l['url'] and s_.get('sha256') == l['sha256']), None)
            obs = str((src or {}).get('observed') or '').replace('-', '')[:8] or None
            obs = obs if obs and len(obs) == 8 else None
        rows.append(dict(capture_url=l['url'], sha256=l['sha256'], quote=l['quote'], department=(l.get('kind') or '').split(':')[-1] or 'census source',
                         observed_on=f'{obs[:4]}-{obs[4:6]}-{obs[6:]}' if obs else None, year=l['year'], census=True))
    rows = [r for r in rows if r.get('observed_on')]
    for r in rows:
        if r.get('census') and not r['observed_on']:
            continue
    rows.sort(key=lambda r: r['observed_on'])
    if not rows:
        print('no rows', pi); continue
    years = sorted({int(r['observed_on'][:4]) for r in rows})
    gaps = [y for y in range(years[0], years[-1] + 1) if y not in years]
    runs, cur = [], 0
    for y in range(years[0], years[-1] + 1):
        cur = cur + 1 if y in gaps else 0
        runs.append(cur)
    if max(runs) > MAXGAP:
        print('skip (gap run longer than', MAXGAP, 'years):', pi, gaps); continue
    pick = [rows[0]] + [max((r for r in rows if int(r['observed_on'][:4]) < g), key=lambda r: r['observed_on']) for g in gaps] \
        + [min((r for r in rows if int(r['observed_on'][:4]) > g), key=lambda r: r['observed_on']) for g in gaps] + [rows[-1]]
    seen, ev = set(), []
    for r in sorted(pick, key=lambda r: r['observed_on']):
        if (r['capture_url'], r['quote']) in seen:
            continue
        seen.add((r['capture_url'], r['quote']))
        ev.append(evidence(r))
    note = (f"Bridged from dated faculty listings: listed as faculty in {', '.join(map(str, years))}; no department listing or "
            f"profile capture exists for {', '.join(map(str, gaps)) or 'no year'} and no evidence of a break. Start is a LOWER BOUND "
            f"(the first dated faculty listing in the 2016-2026 window); the period stops at the last dated faculty listing (asof), "
            f"no end is claimed.")
    out[pi] = dict(pi=pi, existing_period_id=None, verdict='period', period=dict(start=rows[0]['observed_on'], end=None, asof=rows[-1]['observed_on'],
                   datePrecision='day', evidence=ev, note=note), departure=None)
    print(pi, rows[0]['observed_on'], '..', rows[-1]['observed_on'], 'gaps', gaps, 'ev', len(ev))
json.dump(list(out.values()), open(out_f, 'w'), indent=1, ensure_ascii=False)
