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
gaps      dated Wayback captures for a PI's listing gap years (see gaps()); closes the gap with a reviewed period
extend    the window years a unit directory misses, from dated unit profile captures (see extend())
usage: periods_school.py fetch|extract|gaps|extend <key>
"""
import collections, json, re, sys, zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
import school_web as W  # noqa: E402
import faculty_periods as FP  # noqa: E402


MOVED = re.compile(r'before (?:coming|joining|moving) to|moved to|left (?:the University of )?Michigan|now (?:at|with) |prior to (?:joining|coming to)|'
                   r'was (?:an? )?(?:assistant |associate )?professor .{0,80}? from (?:19|20)\d\d to', re.I)


DBLP_URL_SKIP = re.compile(r'orcid|wikidata|wikipedia|scholar\.google|twitter|linkedin|dblp|acm\.org|ieee|researchgate|github\.com/[^/]+/?$|'
                           r'mathgenealogy|zbmath|scopus|semanticscholar|openreview|x\.com|bsky|mastodon|mailto:|'
                           r'd-nb\.info|id\.loc\.gov|viaf\.org|isni|bnf\.fr|idref\.fr|nla\.gov\.au|wikimedia|mathscinet|ams\.org/mathscinet|'
                           r'genealogy\.|crossref|youtube|facebook', re.I)  # authority records and profiles are not homepages


def targets(key):
    census = json.loads((P.CENSUS / f'{key}-faculty.json').read_text())['faculty']
    add = json.loads((P.CENSUS / f'{key}-additions.json').read_text()) if (P.CENSUS / f'{key}-additions.json').exists() else []
    rows = json.loads((P.LISTINGS / key / 'rows.json').read_text())
    hp = collections.defaultdict(list)
    for r in rows:
        if r.get('homepage'):
            hp[r['name']].append(r['homepage'])
    out = []
    dpf = P.HIERARCHY / 'dblp-dump-persons.json.gz'
    dp = json.load(__import__('gzip').open(dpf, 'rt'))['persons'] if dpf.exists() else {}
    ov = json.loads((P.HIERARCHY / 'census-overrides.json').read_text()).get(key, {}) if (P.HIERARCHY / 'census-overrides.json').exists() else {}
    for x in census + add:
        if not x.get('is_pi'):
            continue
        urls = [u for nm in [x['name']] + list(x.get('aliases') or []) for u in hp.get(nm, [])] + ([x['profile_url']] if x.get('profile_url') else [])
        urls = [('https:' + u if u.startswith('//') else u) for u in urls if u and not re.search(r'mentor|mailto:|linkedin|twitter|x\.com|facebook', u)]
        urls = list(dict.fromkeys(urls))[:3]
        # the PI's own homepage from their DBLP person record (learned 2026-10-30: most PIs of other units have no
        # homepage in their unit listing); reviewed DBLP ids (census-overrides) first
        dids = ([(ov.get(x['name']) or {}).get('dblp')] if isinstance((ov.get(x['name']) or {}).get('dblp'), str) else list((ov.get(x['name']) or {}).get('dblp') or [])) or list(x.get('dblp') or [])
        for d in dids:
            for u in (dp.get(d) or {}).get('urls') or []:
                if not DBLP_URL_SKIP.search(u) and u not in urls and len(urls) < 4:
                    urls.append(u)
        out.append(dict(name=x['name'], person=x.get('collection_person_id'), urls=urls,
                        first=min(x.get('years_listed') or [2016]), years=sorted(x.get('years_listed') or []), ranks=x.get('ranks_by_year') or {}))
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
    FP.SCHOOL[key] = '(?i:' + (S.field(cfg, 'periods.school_regex') or S.aff(key)) + ')'  # the candidates' patterns are case-sensitive
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
        later = [y for y in t.get('years') or [] if end and y > int(end) + 1 and {'ladder', 'courtesy'} & set(t['ranks'].get(str(y)) or ['ladder'])]
        if later:  # a closed range followed by later professor-rank listings is a rank step ('2014-2020: Assistant Professor'),
            # not a departure; adjunct listings after it are not (Cafarella: MIT from 2020, CSE adjunct 2021-2026: R-PAP-03)
            note = f'closed range ending {end} ignored: listed in {later[0]}-{later[-1]} (learned 2026-10-29, Viswanath Nagarajan)'
            end = None
        else:
            note = None
        evs = [{k: best[k] for k in ('url', 'sha256', 'quote', 'observedAt')}] + [{k: f[k] for k in ('url', 'sha256', 'quote', 'observedAt')} for f in found if f is not best][:2]
        if end:  # the statement that closes the period says the PI moved: the builder's R-PAP-03 sets later listings aside
            fe = next((f for f in found if f.get('end') == end), None)
            if fe and MOVED.search(fe['quote']):
                evs.insert(0, dict({k: fe[k] for k in ('url', 'sha256', 'quote', 'observedAt')}, kind='faculty_end_moved'))
        periods.append(dict(id=f'{key}_faculty_period_{len(periods)}', personId=t['person'], name=t['name'], school=key, unitIds=[],
                            facultyStart=str(starts[0]), facultyEnd=end, labStart=None, labEnd=None, datePrecision='year',
                            endDatePrecision='year' if end else None,
                            evidence=evs,
                            facultyPeriodStatus='supported_start', labPeriodStatus='unresolved', boundaryYearUncertain=True, boundaryMonthUncertain=True,
                            conflictingStartYears=starts if len(starts) > 1 else [], addedBy=f'tools/periods_school.py {key}', endNote=note,
                            qualification="Appointment year from the page's own statement naming the school; the earliest stated faculty year is kept."))
    P.PERIODS.mkdir(exist_ok=True)
    (P.PERIODS / f'{key}-faculty-periods.json').write_text(json.dumps(periods, indent=1, ensure_ascii=False))
    (P.PERIODS / f'{key}-holds.json').write_text(json.dumps(holds, indent=1, ensure_ascii=False))
    print(json.dumps(dict(school=key, periods=len(periods), holds=len(holds), conflicts=sum(1 for p in periods if p['conflictingStartYears']))))


def gaps(key, write=True):
    """Gap years (protocol stage 4, learned 2026-10-30 at Michigan): a PI whose listing years have a hole gets, for
    each missing year, the dated Wayback captures of that year (monthly, at most 4 per URL) of the PI's own homepage, of
    the unit listing that lists the PI, and of a UMSI profile page; a capture whose text names the PI with a ladder
    professor title (cs_related_school.faculty_evidence; a homepage must also name the school) proves that calendar
    year, like a dated listing. Roster years are never bridged without such a capture. When every gap year has one,
    the PI gets a reviewed period in census-overrides.json from the first to the last evidenced year (the
    Berkeley 'bridged' form: start a lower bound, no end claimed, asof the last evidence). Years without a capture stay
    open. -> hierarchy/<key>/gap-year-evidence.json"""
    import cs_related_school as CR
    c = W.con(key); rx = S.aff_rx(key); out = {}
    add = {x['name']: x for x in json.loads((P.CENSUS / f'{key}-additions.json').read_text())} if (P.CENSUS / f'{key}-additions.json').exists() else {}
    cen = {x['name']: x for x in json.loads((P.CENSUS / f'{key}-faculty.json').read_text())['faculty']}
    import stage_gate as SG
    for t in targets(key):
        x0 = cen.get(t['name']) or add.get(t['name']) or {}
        miss = SG.span_gaps(x0)  # years of the professor-rank span with no listing (stage_gate.span_gaps)
        ys = sorted(set(x0.get('years_listed') or []))
        if not miss:
            continue
        x = cen.get(t['name']) or add.get(t['name']) or {}
        names = [t['name']] + list(x.get('aliases') or [])
        urls = list(t['urls'])
        for s_ in x.get('sources') or []:
            u = re.sub(r'^https?://web\.archive\.org/web/\d+(?:id_)?/', '', s_.get('url') or '')
            if u and u not in urls:
                urls.append(u)
        # the units' per-person profile pages (charter [periods].profile_patterns: {first} {last} {all} = name tokens);
        # learned 2026-10-30: UMSI, Robotics and BME profiles prove years their directories miss
        tk = [w for w in re.sub(r'[^a-z ]', ' ', re.sub(r'\s*\([^)]*\)', '', t['name']).lower().replace(' jr', '')).split() if len(w) > 1]
        for pat in S.field(S.get(key), 'periods.profile_patterns') or []:
            if len(tk) >= 2:
                urls.append(pat.format(first=tk[0], last=tk[-1], all='-'.join(tk)))
        urls += [u.rstrip('/') + '/' for u in t['urls'] if not u.endswith('/') and not re.search(r'\.\w{2,4}$', u)]  # CDX keys are exact
        urls = list(dict.fromkeys(urls))
        ev = {}
        for y in miss:
            for u in urls:
                if y in ev:
                    break
                k = re.sub(r'^https?://', '', u)
                rows = W.cdx_rows(c, k, frm=str(y), to=str(y), collapse='timestamp:6')
                for r in rows[:4]:
                    cap, st, sha, b = W.capture(c, r['timestamp'], r['original'], u, 'gap:' + t['name'])
                    if st != 200:
                        continue
                    flat = W.flat(b)
                    is_home = u in t['urls']
                    if is_home and not rx.search(flat):
                        continue
                    hit = CR.faculty_evidence([('gap', cap, sha, r['timestamp'], flat)], names)
                    hit = [h for h in hit if h['ladder']]
                    if hit:
                        ev[y] = dict(url=cap, sha256=sha, quote=hit[0]['quote'], observed=f"{r['timestamp'][:4]}-{r['timestamp'][4:6]}-{r['timestamp'][6:8]}",
                                     kind='homepage_capture' if is_home else 'unit_page_capture', page=u)
                        break
        out[t['name']] = dict(listing_years=ys, gap_years=miss, evidence={str(y): e for y, e in ev.items()}, closed=all(y in ev for y in miss), urls_tried=urls)
        print(json.dumps(dict(pi=t['name'], gaps=miss, closed=sorted(ev))), flush=True)
    (P.HIERARCHY / key / 'gap-year-evidence.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
    if not write:
        return out
    rows = json.loads((P.LISTINGS / key / 'rows.json').read_text())
    f = P.HIERARCHY / 'census-overrides.json'; txt = f.read_text(); ov = json.loads(txt); sec = ov.setdefault(key, {})
    for name, g in out.items():
        if not g['closed']:
            continue
        x = cen.get(name) or add.get(name) or {}
        srcs = sorted([s_ for s_ in x.get('sources') or [] if s_.get('quote')], key=lambda s_: s_.get('observed') or '')
        first, last = (srcs[0], srcs[-1]) if srcs else (None, None)
        iso = lambda d: (f'{d[:4]}-{d[4:6]}-{d[6:8]}' if d and re.fullmatch(r'\d{8}', d) else d)  # contains() reads ISO dates only
        evs = ([dict(url=first['url'], sha256=first['sha256'], quote=first['quote'], observed=iso(first.get('observed')), kind='dept_listing')] if first else []) + \
              [dict(url=e['url'], sha256=e['sha256'], quote=e['quote'], observed=e['observed'], kind=e['kind']) for _, e in sorted(g['evidence'].items())] + \
              ([dict(url=last['url'], sha256=last['sha256'], quote=last['quote'], observed=iso(last.get('observed')), kind='dept_listing')] if last and last is not first else [])
        sec.setdefault(name, {})['periods'] = [dict(id=f"override_period_gaps_{key}_{re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')}", start=str(g['listing_years'][0]),
                                                    end=None, asof=(evs[-1].get('observed') or '')[:10] or None, datePrecision='year', evidence=evs,
                                                    note=f"Bridged from dated evidence for every year {g['listing_years'][0]}-{g['listing_years'][-1]}: listings, and for the gap years "
                                                         f"{g['gap_years']} dated Wayback captures naming the PI with a professor title (hierarchy/{key}/gap-year-evidence.json). "
                                                         "Start is a lower bound (the first listing in the window); no end is claimed.",
                                                    reviewed='periods_school_gaps_20261030')]
        sec[name]['why_periods'] = 'Gap years closed by dated captures (tools/periods_school.py gaps).'
    f.write_text(json.dumps(ov, indent=1, ensure_ascii='\\u' in txt) + ('\n' if txt.endswith('\n') else ''))


def extend(key, write=True):
    """Years a unit's directory misses (protocol stage 4/7, learned 2026-10-30 at Michigan: UMSI's directory is
    paginated in Wayback for 2021-2025, so its faculty were listed in a few years only and their other lab papers fell
    outside the appointment). For each PI of another unit (census additions) whose sources are on a host of the charter's
    [periods].profile_patterns, every window year without a listing is checked against the dated Wayback captures of
    the PI's profile page (one CDX query per URL; the capture nearest mid-year, then the others, at most 3 a year): a
    capture naming the PI with a ladder professor title (cs_related_school.faculty_evidence) proves that calendar year.
    Each contiguous run of proven years (listings and captures) becomes one reviewed period in census-overrides.json
    (start a lower bound, no end claimed, asof the run's last evidence), replacing this tool's earlier periods for the
    PI. -> hierarchy/<key>/profile-year-evidence.json"""
    import cs_related_school as CR
    c = W.con(key); lo, hi = S.get(key).get('window') or [2016, 2026]
    pats = list(S.field(S.get(key), 'periods.profile_patterns') or [])
    add = json.loads((P.CENSUS / f'{key}-additions.json').read_text()) if (P.CENSUS / f'{key}-additions.json').exists() else []
    iso = lambda d: (f'{d[:4]}-{d[4:6]}-{d[6:8]}' if d and re.fullmatch(r'\d{8}', d) else d)
    out = {}
    for x in add:
        if not x.get('is_pi'):
            continue
        hosts = {re.sub(r'^https?://(web\.archive\.org/web/\d+(?:id_)?/)?(https?://)?', '', s_.get('url') or '').split('/')[0].replace('www.', '') for s_ in x.get('sources') or []}
        tk = [w for w in re.sub(r'[^a-z ]', ' ', re.sub(r'\s*\([^)]*\)', '', x['name']).lower().replace(' jr', '')).split() if len(w) > 1]
        urls = list(dict.fromkeys(pt.format(first=tk[0], last=tk[-1], all='-'.join(tk)) for pt in pats
                                  if len(tk) >= 2 and pt.split('/')[0].replace('www.', '') in hosts))
        listed = set(x.get('years_listed') or [])
        miss = [y for y in range(lo, hi + 1) if y not in listed]
        if not urls or not miss:
            continue
        names = [x['name']] + list(x.get('aliases') or [])
        ev = {}
        for u in urls:
            rows = W.cdx_rows(c, u, frm=str(lo), to=str(hi), collapse='timestamp:6')
            by = collections.defaultdict(list)
            for r in rows:
                by[int(r['timestamp'][:4])].append(r)
            for y in miss:
                if y in ev:
                    continue
                for r in sorted(by.get(y, []), key=lambda r: abs(int(r['timestamp'][4:6]) - 6))[:3]:
                    cap, st, sha, b = W.capture(c, r['timestamp'], r['original'], u, 'profile:' + x['name'])
                    if st != 200:
                        continue
                    hit = [h for h in CR.faculty_evidence([('profile', cap, sha, r['timestamp'], W.flat(b))], names) if h['ladder']]
                    if hit:
                        ev[y] = dict(url=cap, sha256=sha, quote=hit[0]['quote'], observed=iso(r['timestamp'][:8]), kind='unit_profile_capture', page=u)
                        break
        yrs = sorted(listed | set(ev))
        runs, cur = [], []
        for y in yrs:
            if cur and y != cur[-1] + 1:
                runs.append(cur); cur = []
            cur.append(y)
        if cur:
            runs.append(cur)
        src = {}
        for s_ in sorted([s_ for s_ in x.get('sources') or [] if s_.get('quote') and s_.get('sha256')], key=lambda s_: s_.get('observed') or ''):
            src.setdefault(int(str(s_.get('observed') or '0')[:4] or 0), s_)
        out[x['name']] = dict(listed=sorted(listed), profile_years=sorted(ev), runs=runs, evidence={str(y): e for y, e in sorted(ev.items())}, urls=urls)
        print(json.dumps(dict(pi=x['name'], listed=sorted(listed), added=sorted(ev), runs=[[r[0], r[-1]] for r in runs])), flush=True)
    (P.HIERARCHY / key / 'profile-year-evidence.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
    if not write:
        return out
    f = P.HIERARCHY / 'census-overrides.json'; txt = f.read_text(); ov = json.loads(txt); sec = ov.setdefault(key, {})
    for name, g in out.items():
        if not g['profile_years']:
            continue
        x = next(a for a in add if a['name'] == name)
        src = {}
        for s_ in sorted([s_ for s_ in x.get('sources') or [] if s_.get('quote') and s_.get('sha256')], key=lambda s_: s_.get('observed') or ''):
            src.setdefault(int(str(s_.get('observed') or '0')[:4]), s_)
        pers = []
        for run in g['runs']:
            evs = []
            for y in run:
                if str(y) in g['evidence']:
                    e = g['evidence'][str(y)]; evs.append({k: e[k] for k in ('url', 'sha256', 'quote', 'observed', 'kind')})
                elif y in src:
                    s_ = src[y]; evs.append(dict(url=s_['url'], sha256=s_['sha256'], quote=s_['quote'], observed=iso(str(s_.get('observed'))[:8]), kind=s_.get('kind') or 'unit_listing'))
            slug = re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')
            pers.append(dict(id=f'override_period_profiles_{key}_{slug}_{run[0]}', start=str(run[0]), end=None, asof=evs[-1]['observed'][:10] if evs else None,
                             datePrecision='year', evidence=evs, reviewed='periods_school_extend_20261030',
                             note=f"Dated evidence for every year {run[0]}-{run[-1]}: unit listings, and dated Wayback captures of the PI's unit profile page naming "
                                  f"the PI with a professor title (hierarchy/{key}/profile-year-evidence.json). Start is a lower bound; no end is claimed."))
        e = sec.setdefault(name, {})
        e['periods'] = [q for q in e.get('periods') or [] if not str(q.get('reviewed', '')).startswith(('periods_school_gaps', 'periods_school_extend'))] + pers
        e['why_periods'] = 'Years proven by dated unit profile captures and listings (tools/periods_school.py extend).'
    f.write_text(json.dumps(ov, indent=1, ensure_ascii='\\u' in txt) + ('\n' if txt.endswith('\n') else ''))


if __name__ == '__main__':
    {'fetch': fetch, 'extract': extract, 'gaps': gaps, 'extend': extend}[sys.argv[1]](sys.argv[2])
