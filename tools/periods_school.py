"""Faculty appointment periods with verbatim evidence for a protocol school's PIs (protocol stage 4), generalized from
tools/faculty_periods.py (which reads a pre-protocol school's stage structure and site collection).

pages     per census PI: the homepage the department listing links (listings/<key>/rows.json `homepage`) and the
          census profile_url. A page on a host the charter marks wayback-only or none, or any page whose live host
          disallows us by robots.txt or challenges, is read from Wayback: the 200 capture nearest 1 July 2026, and the
          one nearest 1 July of the PI's first listed year (two id_ captures at most), into captures/<key>.sqlite.
          Other hosts are fetched live (robots honoured, school_web.live).
extract   tools/faculty_periods.candidates(): sentences that state an appointment at the school with a year ('joined
          the University of Michigan in 2015', 'Professor at Michigan since 2012', CV lines '2015 - present Assistant
          Professor ... University of Michigan'), with the school pattern from the charter ([periods].school_regex,
          else [affiliation].regex). The quote is the page's own words around the match (whitespace collapsed).
accept    the earliest stated faculty start year; a closed range or 'until'/'left' sets facultyEnd; several start years
          are kept as conflictingStartYears. Everything else is a hold.
-> periods/<key>-faculty-periods.json (the site's facultyPeriods format; personId = the census collection_person_id),
   periods/<key>-holds.json
usage: periods_school.py fetch|extract <key>
"""
import collections, json, re, sys, time, zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
import school_web as W  # noqa: E402
import faculty_periods as FP  # noqa: E402


def targets(key):
    census = json.loads((P.CENSUS / f'{key}-faculty.json').read_text())['faculty']
    add = json.loads((P.CENSUS / f'{key}-additions.json').read_text()) if (P.CENSUS / f'{key}-additions.json').exists() else []
    rows = json.loads((P.LISTINGS / key / 'rows.json').read_text())
    hp = collections.defaultdict(list)
    for r in rows:
        if r.get('homepage'):
            hp[r['name']].append(r['homepage'])
    out = []
    for x in census + add:
        if not x.get('is_pi'):
            continue
        urls = [u for nm in [x['name']] + list(x.get('aliases') or []) for u in hp.get(nm, [])] + ([x['profile_url']] if x.get('profile_url') else [])
        urls = [('https:' + u if u.startswith('//') else u) for u in urls if u and not re.search(r'mentor|mailto:|linkedin|twitter|x\.com|facebook', u)]
        out.append(dict(name=x['name'], person=x.get('collection_person_id'), urls=list(dict.fromkeys(urls))[:3],
                        first=min(x.get('years_listed') or [2016])))
    return out


def fetch(key):
    cfg = S.get(key); c = W.con(key)
    n = collections.Counter()
    for t in targets(key):
        for u in t['urls']:
            host = re.sub(r'^https?://', '', u).split('/')[0].lower()
            live_ok = S.host_use(key, host) == 'live' and host not in W._blocked
            res = W.live(c, u) if live_ok else None
            if res and res[0] == 200:
                n['live_200'] += 1; continue
            key_url = re.sub(r'^https?://', '', u)
            rows = W.cdx_rows(c, key_url, frm='2016', to='2026', collapse='timestamp:6')
            if not rows:
                n['no_capture'] += 1; continue
            picks = {min(rows, key=lambda r: abs(int(r['timestamp'][:6]) - 202607))['timestamp']}
            picks.add(min(rows, key=lambda r: abs(int(r['timestamp'][:6]) - (t['first'] * 100 + 7)))['timestamp'])
            for r in rows:
                if r['timestamp'] in picks:
                    cap, st, sha, b = W.capture(c, r['timestamp'], r['original'], u, 'homepage:' + t['name'])
                    n[f'wayback_{st}'] += 1
        print(json.dumps(dict(pi=t['name'], **n)), flush=True)
    print(json.dumps(dict(n)))


def extract(key):
    cfg = S.get(key); c = W.con(key)
    FP.SCHOOL[key] = S.field(cfg, 'periods.school_regex') or S.aff(key)
    lo, hi = cfg.get('window') or [2016, 2026]
    periods, holds = [], []
    for t in targets(key):
        pages = []
        for u in t['urls']:
            row = c.execute('select status, sha256, raw_zlib, content_type, fetched_at from live where url=?', (u,)).fetchone()
            if row and row[0] == 200:
                pages.append((u, row[1], W.flat(W.extract.blocks(zlib.decompress(row[2]), row[3], u)), row[4][:10]))
            for cap, sha, txt, ts in c.execute("select capture_url, sha256, text, wayback_timestamp from captures where page_url=? and http_status=200", (u,)):
                pages.append((cap, sha, ' '.join((txt or '').split()), f'{ts[:4]}-{ts[4:6]}-{ts[6:8]}'))
        fam = t['name'].split()[-1].lower()
        found = []
        for u, sha, text, at in pages:
            if fam not in text.lower():
                continue
            found += [dict(url=u, sha256=sha, quote=q, start=s_, end=e_, pattern=pn, observedAt=at) for s_, e_, q, pn in FP.candidates(text, key)]
        found = list({(f['url'], f['quote']): f for f in found}.values())
        if not found:
            holds.append(dict(name=t['name'], person=t['person'], reason='no appointment statement found' if pages else 'no page captured', pages=t['urls'])); continue
        starts = sorted({int(f['start']) for f in found})
        best = min(found, key=lambda f: int(f['start']))
        ends = sorted({int(f['end']) for f in found if f.get('end')})
        end = str(ends[-1]) if ends and ends[-1] < hi else None
        periods.append(dict(id=f'{key}_faculty_period_{len(periods)}', personId=t['person'], name=t['name'], school=key, unitIds=[],
                            facultyStart=str(starts[0]), facultyEnd=end, labStart=None, labEnd=None, datePrecision='year',
                            endDatePrecision='year' if end else None,
                            evidence=[{k: best[k] for k in ('url', 'sha256', 'quote', 'observedAt')}] +
                                     [{k: f[k] for k in ('url', 'sha256', 'quote', 'observedAt')} for f in found if f is not best][:2],
                            facultyPeriodStatus='supported_start', labPeriodStatus='unresolved', boundaryYearUncertain=True, boundaryMonthUncertain=True,
                            conflictingStartYears=starts if len(starts) > 1 else [], addedBy=f'tools/periods_school.py {key}',
                            qualification="Appointment year from the page's own statement naming the school; the earliest stated faculty year is kept."))
    P.PERIODS.mkdir(exist_ok=True)
    (P.PERIODS / f'{key}-faculty-periods.json').write_text(json.dumps(periods, indent=1, ensure_ascii=False))
    (P.PERIODS / f'{key}-holds.json').write_text(json.dumps(holds, indent=1, ensure_ascii=False))
    print(json.dumps(dict(school=key, periods=len(periods), holds=len(holds), conflicts=sum(1 for p in periods if p['conflictingStartYears']))))


if __name__ == '__main__':
    {'fetch': fetch, 'extract': extract}[sys.argv[1]](sys.argv[2])
