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
truncated  the years a department card cut a title short ('Executive Director, Institute for Data…': the word Professor is lost, the row reads unranked): dated
          profile / homepage captures of exactly those years naming the person with a professor title (see truncated())
deep      the second look at a PI the gaps/extend pass left open (see deep()): profile-URL variants on the PI's home unit hosts across URL eras, the person's own homepages and
          the reviewed `person-urls.json`; what stays unproven is recorded as `unproven_years` + `why_unproven`
usage: periods_school.py fetch [--live-only]|extract|gaps|extend|truncated|deep <key>      (gaps saves per PI and resumes: gaps <key> --max-pis N)
"""
import collections, json, re, sys, zlib

import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
import census_overrides as CO  # noqa: E402
import school_web as W  # noqa: E402
import faculty_periods as FP  # noqa: E402


MOVED = re.compile(r'before (?:coming|joining|moving) to|moved to|left (?:the University of )?Michigan|now (?:at|with) |prior to (?:joining|coming to)|'
                   r'was (?:an? )?(?:assistant |associate )?professor .{0,80}? from (?:19|20)\d\d to|'
                   r'(?:KAIST|카이스트|한국과학기술원)(?:를|에서)?\s*(?:떠나|퇴직|사직)|(?:로|으로)\s*(?:이직|자리를\s*옮)', re.I)


DBLP_URL_SKIP = re.compile(r'orcid|wikidata|wikipedia|scholar\.google|twitter|linkedin|dblp|acm\.org|ieee|researchgate|github\.com/[^/]+/?$|'
                           r'mathgenealogy|zbmath|scopus|semanticscholar|openreview|x\.com|bsky|mastodon|mailto:|'
                           r'd-nb\.info|id\.loc\.gov|viaf\.org|isni|bnf\.fr|idref\.fr|nla\.gov\.au|wikimedia|mathscinet|ams\.org/mathscinet|'
                           r'genealogy\.|crossref|youtube|facebook', re.I)  # authority records and profiles are not homepages


def pi_row(cen, add, name):
    """The row stage_gate.pis_of judges: the census row when it is a PI, else the census addition, else any census row (an affiliated unit's pending row must not hide the addition's years)."""
    c = cen.get(name)
    return c if (c or {}).get('is_pi') else (add.get(name) or c or {})


def census_faculty(key):
    """The census rows: {'faculty': [...]} (census_build) or a bare list (a hand-composed released school)."""
    d = json.loads((P.data('census-faculty.json', key)).read_text())
    return d['faculty'] if isinstance(d, dict) else d


def rows_of(key):
    """listings/<key>/rows.json, or [] for a school without listing rows (MIT, Princeton, CMU, Stanford, Berkeley: hand-composed censuses)."""
    f = P.data('rows.json', key)
    return json.loads(f.read_text()) if f.exists() else []


def targets(key):
    census = census_faculty(key)
    add = json.loads((P.data('census-additions.json', key)).read_text()) if (P.data('census-additions.json', key)).exists() else []
    rows = rows_of(key)
    hp = collections.defaultdict(list)
    for r in rows:
        if r.get('homepage'):
            hp[r['name']].append(r['homepage'])
    out = []
    dpf = P.data('dblp-dump-persons.json.gz')
    dp = json.load(__import__('gzip').open(dpf, 'rt'))['persons'] if dpf.exists() else {}
    dsf = P.data('dblp-dump-persons-school.json.gz', key)   # an onboarding school's own persons (dblp_dump_persons.py <key>)
    if dsf.exists():
        dp = {**dp, **json.load(__import__('gzip').open(dsf, 'rt'))['persons']}
    ov = CO.section(key)
    ef = P.data('extra-lab-pages.json', key)
    extra = json.load(open(ef)) if ef.exists() else {}
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
        for e in extra.get(x['name']) or []:   # reviewed extra lab/homepage/CV pages (extra-lab-pages.json: found by hand or from the profile pages, each with why)
            u = e['url'] if isinstance(e, dict) else e
            if u not in urls:
                urls.append(u)
        out.append(dict(name=x['name'], person=x.get('collection_person_id'), urls=urls,
                        first=min(x.get('years_listed') or [2016]), years=sorted(x.get('years_listed') or []), ranks=x.get('ranks_by_year') or {}))
    return out


NEW_APPOINTMENT = re.compile(r'currently\s+(?:[^.]{0,120}?)\b(?:at|of|in)\s+(?!ETH\b)(?:the\s+)?(?:EPFL|University|Universität|Institut|Max|Harvard|Stanford|MIT|Princeton|Yale|Oxford|Cambridge|Imperial|[A-Z][a-z]+ (?:University|Institute))|appointed .{0,60}as (?:Assistant|Associate|Full) Professor', re.I)
PROMOTION = re.compile(r'currently\s+[^.]{0,160}?(?:at|of)\s+ETH Zurich', re.I)


def _fold(s):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFKD', s or '') if not unicodedata.combining(c)).casefold()


def _name_key(name):
    t = [w for w in re.sub(r'[^a-z\s-]', ' ', _fold(name)).split() if len(w) > 1]
    return (t[0], t[-1]) if len(t) >= 2 else None


def board_periods(key, census_names=None, last_listed=None):
    """Appointment periods from the school's Board entries (hierarchy/<key>/reviewed/official-lists.json, ETH institution only): a Board
    appointment of a professor coming from another institution dates the start (the decision date; the effective date is later, so the year and
    month are marked uncertain); a Board retirement clause dates the end. A PI whose Board start is known and who is still listed in the last
    listing year (or whose retirement is dated) gets one period; a Board promotion ('currently ... at ETH Zurich') proves membership on that date only and
    yields none. {name: period fields}. `census_names` {name: aliases} restricts to census PIs; `last_listed` {name: last listed year}."""
    f = P.data('cs-related-hand.json', key).parent / 'official-lists.json'   # not a registered data file: it sits beside the reviewed cs-related files
    if not f.exists():
        return {}
    entries = [e for e in json.loads(f.read_text()) if e.get('institution') == 'ETH Zurich']   # ETH's Board lists name the institution per entry; EPFL appointees are not ETH periods
    keyed = {}
    for name, aliases in (census_names or {}).items():
        for nm in [name] + list(aliases or []):
            k = _name_key(nm)
            if k:
                keyed.setdefault(k, name)
    starts, ends = {}, {}
    for e in entries:
        k = _name_key(e.get('name'))
        who = keyed.get(k) if census_names is not None else e.get('name')
        if not who or not e.get('date'):
            continue
        iso = f"{e['date'][:4]}-{e['date'][4:6]}-{e['date'][6:8]}" if re.fullmatch(r'\d{8}', e['date']) else None
        if not iso:
            continue
        ev = dict(url=e['url'], sha256=e['sha256'], quote=e['quote'], observedAt=iso, kind='board_' + e['list'].replace('board_', ''))
        if e['list'] == 'board_appointment' and not PROMOTION.search(e['quote']) and NEW_APPOINTMENT.search(e['quote']):
            if who not in starts or iso < starts[who][0]:
                starts[who] = (iso, ev)
        elif e['list'] == 'board_retirement':
            if who not in ends or iso > ends[who][0]:
                ends[who] = (iso, ev)
    out = {}
    for who, (iso, ev) in starts.items():
        end = ends.get(who)
        if end is None and last_listed is not None and (last_listed.get(who) or 0) < 2025:
            continue   # not retired and not listed in the last years: no evidence the appointment continues
        evs = [ev] + ([dict(end[1], kind='faculty_end_retirement')] if end else [])
        out[who] = dict(facultyStart=iso, facultyEnd=end[0] if end else None, evidence=evs)
    return out


def board_proven_years(key, name):
    """Calendar years in which an ETH Board entry (appointment, promotion or retirement decision, institution ETH Zurich) names the PI as an ETH
    professor: a dated official document proves that year the way a same-year listing does. SNSF and Eccellenza entries do not (an awardee is
    not necessarily an ETH professor)."""
    f = P.data('cs-related-hand.json', key).parent / 'official-lists.json'
    if not f.exists():
        return set()
    k = _name_key(name)
    return {int(e['date'][:4]) for e in json.loads(f.read_text())
            if e.get('institution') == 'ETH Zurich' and e.get('date') and k and _name_key(e.get('name')) == k}


def board_merge(key, periods):
    """`periods` (the faculty-periods list) plus the Board periods of census PIs that have none yet. Returns the new list."""
    cen = {x['name']: x for x in census_faculty(key) if x.get('is_pi')}
    add = json.loads(P.data('census-additions.json', key).read_text()) if P.data('census-additions.json', key).exists() else []
    for x in add:
        if x.get('is_pi'):
            cen.setdefault(x['name'], x)
    ov = CO.section(key)
    names = {n: x.get('aliases') or [] for n, x in cen.items() if not (ov.get(n) or {}).get('exclude')}
    last = {n: max(x.get('years_listed') or [0]) for n, x in cen.items()}
    have = {p['name'] for p in periods if not str(p.get('addedBy', '')).endswith('board')}
    kept = [p for p in periods if str(p.get('addedBy', '')).endswith('board') is False]
    out = list(kept)
    for who, b in sorted(board_periods(key, names, last).items()):
        if who in have:
            continue
        x = cen[who]
        out.append(dict(id=f'{key}_faculty_period_board_{len(out)}', personId=x.get('collection_person_id'), name=who, school=key, unitIds=[],
                        facultyStart=b['facultyStart'], facultyEnd=b['facultyEnd'], labStart=None, labEnd=None, datePrecision='day',
                        endDatePrecision='day' if b['facultyEnd'] else None, evidence=b['evidence'], facultyPeriodStatus='supported_start',
                        labPeriodStatus='unresolved', boundaryYearUncertain=False, boundaryMonthUncertain=True, conflictingStartYears=[],
                        addedBy=f'tools/periods_school.py {key} board',
                        qualification="Start from the Board's appointment decision date (the effective date is later); end from the Board's retirement clause."))
    return out


def excluded_names(key):
    """Census PIs the reviewed census overrides exclude: never fetched."""
    return {n for n, v in CO.section(key).items() if isinstance(v, dict) and v.get('exclude')}


def fetch_needed(key, only=None):
    """The names stage 4's fetch still needs: not excluded, no reviewed or Board period, and not settled by contiguous listings (stage_gate.period_basis)."""
    import stage_gate as G
    per = board_merge(key, json.loads(P.data('faculty-periods.json', key).read_text()) if P.data('faculty-periods.json', key).exists() else [])
    ov = CO.section(key)
    have = {p['name'] for p in per} | {k for k, v in ov.items() if isinstance(v, dict) and v.get('periods')}
    skip = excluded_names(key)
    gap_table, rows = department_gap_years(key), rows_of(key)   # D-0080: a PI whose every gap year is a department-wide capture gap is bridged by `gaps`, so it needs no fetch
    need = set()
    for x in G.pis_of(key):
        if x['name'] in skip or G.period_basis(key, x, have, ov) is not None:
            continue
        miss = [y for y in G.span_gaps(x) if y not in G.proven_years(key, x['name'])]
        if miss and not [y for y in miss if y not in interpolated_years(key, x['name'], x.get('aliases') or [], miss, gap_table, rows)]:
            continue
        need.add(x['name'])
    return need & set(only) if only else need


def fetch(key, only=None, everyone=False, live_only=False):
    """Fetch the PIs' pages. Since 2026-11-25 only the PIs stage 4 still needs (fetch_needed): excluded PIs, PIs with a reviewed or Board period and PIs
    settled by contiguous listings are skipped; `--all` restores every census PI, named PIs (`fetch <key> NAME...`) restrict the set.
    live_only (--live-only, or PERIODS_FETCH_ARGS in the stage-4 step; KAIST 2026-11-25): fetch live hosts only and never ask Wayback, so the shared CDX clock
    stays with another job; a page that is not live-fetchable is counted `wayback_deferred` and left for a later plain `fetch`."""
    cfg = S.get(key); c = W.con(key)
    n = collections.Counter()
    wanted = None if everyone else fetch_needed(key, only)
    if everyone and only:
        wanted = set(only)
    for t in targets(key):
        if wanted is not None and t['name'] not in wanted:
            n['skipped_not_needed'] += 1; continue
        for u in t['urls']:
            host = re.sub(r'^https?://', '', u).split('/')[0].lower()
            if c.execute('select 1 from captures where page_url=? and http_status=200 limit 1', (u,)).fetchone() or c.execute('select 1 from live where url=? and status=200 limit 1', (u,)).fetchone():
                n['already_stored'] += 1; continue   # a rerun after new URLs were added fetches only the new ones (UChicago homepage dive)
            live_ok = S.host_use(key, host) == 'live' and host not in W._blocked
            res = W.live(c, u) if live_ok else None
            if res and res[0] == 200:
                n['live_200'] += 1; continue
            if live_only:
                n['wayback_deferred'] += 1; continue
            key_url = re.sub(r'^https?://', '', u)
            try:
                rows = W.cdx_rows(c, key_url, frm='2016', to='2026', collapse='timestamp:6')
                if not rows:
                    n['no_capture'] += 1; continue
                picks = {min(rows, key=lambda r: abs(int(r['timestamp'][:6]) - 202607))['timestamp']}
                picks.add(min(rows, key=lambda r: abs(int(r['timestamp'][:6]) - (t['first'] * 100 + 7)))['timestamp'])
                for r in rows:
                    if r['timestamp'] in picks:
                        cap, st, sha, b = W.capture(c, r['timestamp'], r['original'], u, 'homepage:' + t['name'])
                        n[f'wayback_{st}'] += 1
            except RuntimeError as e:   # the shared Wayback clock is cooling down after a 429: pending, rerun later
                if 'cooling down' not in str(e):
                    raise
                n['wayback_cooling_pending'] += 1
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
    periods = board_merge(key, periods)   # Board appointment/retirement dates for PIs the pages did not settle
    P.data_w('faculty-periods.json', key).write_text(json.dumps(periods, indent=1, ensure_ascii=False))
    P.data_w('holds.json', key).write_text(json.dumps(holds, indent=1, ensure_ascii=False))
    print(json.dumps(dict(school=key, periods=len(periods), holds=len(holds), conflicts=sum(1 for p in periods if p['conflictingStartYears']))))


def department_gap_years(key):
    """D-0080 (owner 2026-11-25): the years a department's whole faculty listing is missing. {dept code: {year: evidence}} for each year between the
    first and last year of the department's professors listing rows that has no row for anyone, with the coverage check: the stored CDX responses of the
    department's listing pages (listings/<key>/raw/captures.sqlite, table cdx) count that year's 200 captures, and the stored captures of that year
    are read for professor names (a JS shell that lists nobody is no listing). A year with a capture that names people is never a gap (a PI missing from it closes the period)."""
    import hashlib, sqlite3
    from urllib.parse import quote, unquote
    cfg = S.get(key)
    rows = rows_of(key)
    path = P.LISTINGS / key / 'raw' / 'captures.sqlite'
    con = sqlite3.connect(f'file:{path}?mode=ro', uri=True) if path.exists() else None
    out = {}
    for d in S.listing_units(cfg):
        code = d['code']
        years = sorted({r['year'] for r in rows if r.get('dept') == code and r.get('kind') == 'main'})
        if len(years) < 2:
            continue
        urls = [l['url'] for l in d.get('listings') or [] if l.get('kind', 'main') == 'main' and l.get('url')]
        for y in range(years[0] + 1, years[-1]):
            if y in years:
                continue
            ev = dict(department=code, year=y, pages=[], named_captures=0)
            if con is not None:
                for q, body in con.execute('select query, body from cdx'):
                    u = unquote(re.search(r'[?&]url=([^&]+)', q).group(1)) if re.search(r'[?&]url=([^&]+)', q) else ''
                    if not any(u.rstrip('/') == x.rstrip('/') or quote(x, safe='') in q for x in urls):
                        continue
                    try:
                        recs = json.loads(body)
                    except ValueError:
                        continue
                    hits = [r for r in recs[1:] if str(r[0]).startswith(str(y)) and r[2] == '200']
                    ev['pages'].append(dict(url=u, query=q, sha256=hashlib.sha256(body.encode()).hexdigest(), captures_200=len(hits), timestamps=[r[0] for r in hits][:6]))
                for ts, txt in con.execute("select wayback_timestamp, text from captures where department=? and wayback_timestamp like ? and http_status=200", (code, f'{y}%')):
                    names = len({r['name'] for r in rows if r.get('dept') == code and r['name'] in (txt or '')})   # distinct professors named in the page text
                    ev.setdefault('stored_captures', []).append(dict(timestamp=ts, names_found=names))
                    ev['named_captures'] += 1 if names >= 3 else 0
            if ev['named_captures'] == 0:
                out.setdefault(code, {})[y] = ev
    return out


def interpolated_years(key, name, aliases, miss, gap_table=None, rows=None, left_by=None):
    """The gap years of a PI that D-0080 bridges: a department-wide gap year of a department in which the PI has professors rows (kind main) both before and after it,
    unless a Board retirement (`left_by` {year}) shows a departure by then. {year: department code}."""
    gap_table = department_gap_years(key) if gap_table is None else gap_table
    rows = rows_of(key) if rows is None else rows
    names = {name, *aliases}
    own = collections.defaultdict(set)
    for r in rows:
        if r['name'] in names and r.get('kind') == 'main':
            own[r['dept']].add(r['year'])
    out = {}
    for y in miss:
        for code, ys in own.items():
            if y in (gap_table.get(code) or {}) and min(ys) < y < max(ys) and not (left_by and min(left_by) <= y):
                out[y] = code
                break
    return out


def gaps(key, write=True, max_pis=None):
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
    ev_file = P.data_w('gap-year-evidence.json', key)
    if ev_file.exists():   # resumable (2026-11-18): a PI whose gap years are unchanged and already searched is never searched again
        out = json.loads(ev_file.read_text())
    add = {x['name']: x for x in json.loads((P.data('census-additions.json', key)).read_text())} if (P.data('census-additions.json', key)).exists() else {}
    cen = {x['name']: x for x in census_faculty(key)}
    import stage_gate as SG
    done_now = 0
    dgaps, drows = department_gap_years(key), rows_of(key)
    gap_file = P.data('cs-related-hand.json', key).parent / 'department-gap-years.json'
    if dgaps and write:   # stored once per department-year (D-0080)
        gap_file.write_text(json.dumps(dgaps, indent=1, ensure_ascii=False))
    board_left = {}
    for e in (json.loads((P.data('cs-related-hand.json', key).parent / 'official-lists.json').read_text()) if (P.data('cs-related-hand.json', key).parent / 'official-lists.json').exists() else []):
        if e.get('list') == 'board_retirement' and e.get('institution') == 'ETH Zurich' and e.get('date'):
            board_left.setdefault(next((t_['name'] for t_ in targets(key) if _name_key(t_['name']) == _name_key(e['name'])), e['name']), set()).add(int(e['date'][:4]))
    for t in targets(key):
        x0 = pi_row(cen, add, t['name'])
        miss = SG.span_gaps(x0)  # years of the professor-rank span with no listing (stage_gate.span_gaps)
        ys = sorted(set(x0.get('years_listed') or []))
        if not miss:
            continue
        prev = out.get(t['name'])
        if prev and prev.get('gap_years') == miss and prev.get('listing_years') == ys:
            continue   # searched before: saved result stands (delete the entry to search again)
        interp = interpolated_years(key, t['name'], x0.get('aliases') or [], miss, dgaps, drows, board_left.get(t['name']))   # D-0080: department-wide capture gaps
        if max_pis is not None and done_now >= max_pis:
            break
        x = pi_row(cen, add, t['name'])
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
        for y, code in interp.items():
            g = dgaps[code][y]
            pg = next((p_ for p_ in g['pages'] if p_['captures_200'] == 0), (g['pages'] or [{}])[0])
            ev[y] = dict(url=pg.get('url') or f'department listing {code}', sha256=pg.get('sha256') or '0' * 64, kind='interpolated_department_gap', page=code,
                         observed=f'{y}-07-01', quote=f"no archived faculty listing of {code} for {y} names anyone ({len(g['pages'])} listing pages checked in the CDX: "
                                                      f"{sum(p_['captures_200'] for p_ in g['pages'])} captures with status 200; stored captures naming people: {g['named_captures']}); "
                                                      f"the PI is listed by {code} before and after (hierarchy/{key}/reviewed/department-gap-years.json)")
        for y in miss:
            if y in ev:
                continue
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
        done_now += 1
        ev_file.write_text(json.dumps(out, indent=1, ensure_ascii=False))   # per-PI save (2026-11-18): a timeout or a Wayback cooldown loses at most the PI in progress
        if write and out[t['name']]['closed']:
            write_gaps(key, {t['name']: out[t['name']]})
    ev_file.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out


def write_gaps(key, out):
    """Bridged periods for the PIs whose every gap year has a dated capture (the write half of gaps(); callable on a saved gap-year-evidence.json)."""
    add = {x['name']: x for x in json.loads((P.data('census-additions.json', key)).read_text())} if (P.data('census-additions.json', key)).exists() else {}
    cen = {x['name']: x for x in census_faculty(key)}
    rows = rows_of(key)
    sec, save = CO.open_section(key)
    for name, g in out.items():
        if not g['closed']:
            continue
        x = pi_row(cen, add, name)
        srcs = sorted([s_ for s_ in x.get('sources') or [] if s_.get('quote')], key=lambda s_: str(s_.get('observed') or ''))
        first, last = (srcs[0], srcs[-1]) if srcs else (None, None)
        iso = lambda d: (f'{d[:4]}-{d[4:6]}-{d[6:8]}' if d and re.fullmatch(r'\d{8}(?:\d{2}){0,3}', d) else d)  # contains() reads ISO dates only
        evs = ([dict(url=first['url'], sha256=first['sha256'], quote=first['quote'], observed=iso(str(first.get('observed') or '')), kind='dept_listing')] if first else []) + \
              [dict(url=e['url'], sha256=e['sha256'], quote=e['quote'], observed=e['observed'], kind=e['kind']) for _, e in sorted(g['evidence'].items())] + \
              ([dict(url=last['url'], sha256=last['sha256'], quote=last['quote'], observed=iso(str(last.get('observed') or '')), kind='dept_listing')] if last and last is not first else [])
        sec.setdefault(name, {})['periods'] = [dict(id=f"override_period_gaps_{key}_{re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')}", start=str(g['listing_years'][0]),
                                                    end=None, asof=iso(str(evs[-1].get('observed') or ''))[:10] or None, datePrecision='year', evidence=evs,
                                                    note=f"Bridged from dated evidence for every year {g['listing_years'][0]}-{g['listing_years'][-1]}: listings, and for the gap years "
                                                         f"{g['gap_years']} dated Wayback captures naming the PI with a professor title (hierarchy/{key}/gap-year-evidence.json). "
                                                         "Start is a lower bound (the first listing in the window); no end is claimed.",
                                                    reviewed='periods_school_gaps_20261030')]
        sec[name]['why_periods'] = 'Gap years closed by dated captures (tools/periods_school.py gaps).'
    save()


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
    add = json.loads((P.data('census-additions.json', key)).read_text()) if (P.data('census-additions.json', key)).exists() else []
    iso = lambda d: (f'{d[:4]}-{d[4:6]}-{d[6:8]}' if d and re.fullmatch(r'\d{8}(?:\d{2}){0,3}', d) else d)
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
    P.data_w('profile-year-evidence.json', key).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    if not write:
        return out
    sec, save = CO.open_section(key)
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
    save()


def truncated_years(rows):
    """{name: [years]}: years in which every row of the person is an unranked (rank 'other') row whose title ends in an ellipsis, i.e. a card that cut the title
    short; such a row proves no rank (Georgia Tech stage 2: 38 people, 8 not covered by an adjacent ladder year)."""
    by = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        by[r['name']][r['year']].append(r)
    out = {}
    for n, ys in by.items():
        yrs = sorted(y for y, rs in ys.items() if all(r['rank'] == 'other' for r in rs) and any('…' in t for r in rs for t in r['titles']))
        if yrs:
            out[n] = yrs
    return out


def truncated(key, write=True):
    """Bridge truncated-title years (Georgia Tech R9). For every person whose card cut the title in some years, fetch the dated captures of those calendar years
    of the person's profile page (charter [periods].profile_patterns) and homepage; a capture naming the person with a ladder title proves that year. A PI whose
    truncated years are all proven gets a reviewed period (first ladder listing year to no end, like gaps()); a non-PI is reported, never added.
    -> hierarchy/<key>/truncated-title-evidence.json"""
    import cs_related_school as CR
    c = W.con(key); rx = S.aff_rx(key); out = {}
    rows = rows_of(key)
    cen = {x['name']: x for x in census_faculty(key)}
    add = {x['name']: x for x in json.loads((P.data('census-additions.json', key)).read_text())} if (P.data('census-additions.json', key)).exists() else {}
    tg = {t['name']: t for t in targets(key)}
    for name, years in sorted(truncated_years(rows).items()):
        x = pi_row(cen, add, name)
        pi = bool(x.get('is_pi'))
        t = tg.get(name) or dict(name=name, urls=[])
        names = [name] + list(x.get('aliases') or [])
        tk = [w for w in re.sub(r'[^a-z ]', ' ', re.sub(r'\s*\([^)]*\)', '', name).lower().replace(' jr', '')).split() if len(w) > 1]
        urls = list(t['urls'])
        for pat in S.field(S.get(key), 'periods.profile_patterns') or []:
            if len(tk) >= 2:
                urls.append(pat.format(first=tk[0], last=tk[-1], all='-'.join(tk)))
        urls = list(dict.fromkeys(urls))
        ev = {}
        for y in years:
            for u in urls:
                if y in ev:
                    break
                for r in W.cdx_rows(c, re.sub(r'^https?://', '', u), frm=str(y), to=str(y), collapse='timestamp:6')[:4]:
                    cap, st, sha, b = W.capture(c, r['timestamp'], r['original'], u, 'trunc:' + name)
                    if st != 200:
                        continue
                    flat = W.flat(b)
                    if u in t['urls'] and not rx.search(flat):
                        continue
                    hit = [h for h in CR.faculty_evidence([('trunc', cap, sha, r['timestamp'], flat)], names) if h['ladder']]
                    if hit:
                        ev[y] = dict(url=cap, sha256=sha, quote=hit[0]['quote'], observed=f"{r['timestamp'][:4]}-{r['timestamp'][4:6]}-{r['timestamp'][6:8]}", kind='profile_capture', page=u)
                        break
        out[name] = dict(pi=pi, truncated_years=years, evidence={str(y): e for y, e in ev.items()}, closed=all(y in ev for y in years), urls_tried=urls)
        print(json.dumps(dict(name=name, pi=pi, years=years, proven=sorted(ev))), flush=True)
    P.data_w('truncated-title-evidence.json', key).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    if not write:
        return out
    sec, save = CO.open_section(key)
    for name, g in out.items():
        if not g['pi'] or not g['closed']:
            continue
        x = pi_row(cen, add, name)
        lad = sorted(int(y) for y, rk in (x.get('ranks_by_year') or {}).items() if 'ladder' in rk)
        if not lad:
            continue
        srcs = sorted([s_ for s_ in x.get('sources') or [] if s_.get('quote')], key=lambda s_: s_.get('observed') or '')
        iso = lambda d: (f'{d[:4]}-{d[4:6]}-{d[6:8]}' if d and re.fullmatch(r'\d{8}(?:\d{2}){0,3}', d) else d)
        evs = ([dict(url=srcs[0]['url'], sha256=srcs[0]['sha256'], quote=srcs[0]['quote'], observed=iso(srcs[0].get('observed')), kind='dept_listing')] if srcs else []) + \
              [dict(url=e['url'], sha256=e['sha256'], quote=e['quote'], observed=e['observed'], kind=e['kind']) for _, e in sorted(g['evidence'].items())]
        per = dict(id=f"override_period_trunc_{key}_{re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')}", start=str(lad[0]), end=None, asof=evs[-1]['observed'][:10], datePrecision='year', evidence=evs,
                   note=f"Ladder listings from {lad[0]}; the years {g['truncated_years']} are listing rows whose title the department card cut short, proven by dated profile captures "
                        f"(hierarchy/{key}/truncated-title-evidence.json). Start is a lower bound; no end is claimed.", reviewed='periods_school_truncated_20261103')
        e = sec.setdefault(name, {})
        e['periods'] = [p_ for p_ in e.get('periods') or [] if not p_.get('id', '').startswith('override_period_trunc_')] + [per]
        e['why_periods'] = (e.get('why_periods') or '') + ' Truncated-title years closed by dated profile captures (tools/periods_school.py truncated).'
    save()


DEEP_PATTERNS = ['{h}/people/{all}', '{h}/directory/{all}', '{h}/directory/person/{all}', '{h}/person/{all}', '{h}/users/{all}', '{h}/faculty/{all}', '{h}/profile/{all}', '{h}/people/faculty/{all}']


def home_hosts(key, home):
    """Hosts of the unit a home department name stands for (departments and affiliated units of the charter, matched by name either way round)."""
    cfg = S.get(key); out = []
    def host(u):
        return re.sub(r'^https?://', '', u or '').split('/')[0]
    for d in (cfg.get('departments') or []) + (cfg.get('affiliated_units') or []):
        nm = d.get('name') or ''
        if home and (home.lower() in nm.lower() or nm.lower() in home.lower()):
            out.append(host(d.get('url')))
            out += [host(l) for l in d.get('listings') or [] if isinstance(l, str)]
    return list(dict.fromkeys(h for h in out if h))


def open_pis(key):
    """PIs the stage-4 gate lists as 'no period' (no period, a listing-year gap, and not yet recorded as unproven)."""
    import stage_gate as SG
    bad, _ = SG.g4(key)
    return [b.split(': no period')[0] for b in bad if ': no period' in b]


def outside_work_years(key, name, x):
    """Window years in which the build identified school works of the PI outside every listing year (pis.json funnel keys `outside_appointment_<year>`)."""
    pis = json.loads((P.data('pis.json', key)).read_text())
    pi = next((p for p in (pis if isinstance(pis, list) else pis.get('pis', [])) if p['pi'] == name), None) or {}
    lo, hi = S.get(key).get('window') or [2016, 2026]
    listed = set(x.get('years_listed') or [])
    return {int(k.rsplit('_', 1)[1]) for k in (pi.get('funnel') or {}) if k.startswith('outside_appointment_')
            and lo <= int(k.rsplit('_', 1)[1]) <= hi and int(k.rsplit('_', 1)[1]) not in listed}


def deep(key, write=True):
    """The second look (Georgia Tech owner decision 2026-11-04) at the PIs gaps()/extend() left open. For each gap year, dated Wayback captures of: the PI's homepages (listing, DBLP,
    reviewed person-urls.json), profile-URL variants (DEEP_PATTERNS) on the hosts of the PI's home unit, across URL eras (one whole-window CDX per URL). A capture naming the PI with a ladder
    title proves that calendar year. A PI whose every gap year is proven gets a reviewed period (like gaps()); otherwise the years that stay unproven go to census-overrides
    `unproven_years` with `why_unproven` (listing years prove nothing for them: R-PAP-01; the R-PAP-28 bridge rule covers their papers at build time).
    -> hierarchy/<key>/deep-gap-evidence.json"""
    import cs_related_school as CR
    import stage_gate as SG
    c = W.con(key); rx = S.aff_rx(key); out = {}
    cen = {x['name']: x for x in census_faculty(key)}
    add = {x['name']: x for x in json.loads((P.data('census-additions.json', key)).read_text())} if (P.data('census-additions.json', key)).exists() else {}
    homes = {r['name']: r.get('home_department') for r in json.loads((P.data('home-departments-school.json', key)).read_text())}
    supplied = json.loads((P.data('person-urls.json', key)).read_text()) if (P.data('person-urls.json', key)).exists() else {}
    tg = {t['name']: t for t in targets(key)}
    only = [a for a in sys.argv[3:] if not a.startswith('--')] or None
    work_years = '--work-years' in sys.argv   # ROADMAP #43: also the years of the PI's identified works outside the listing years (a PI listed in one year only has no span gap)
    for name in (only or open_pis(key)):
        x = pi_row(cen, add, name)
        miss = SG.span_gaps(x)
        if work_years:
            miss = sorted(set(miss) | outside_work_years(key, name, x))
        if not miss:
            continue
        t = tg.get(name) or dict(name=name, urls=[])
        names = [name] + list(x.get('aliases') or [])
        tk = [w for w in re.sub(r'[^a-z ]', ' ', re.sub(r'\s*\([^)]*\)', '', name).lower().replace(' jr', '')).split() if len(w) > 1]
        urls = list(t['urls']) + list(supplied.get(name) or [])
        for h in home_hosts(key, homes.get(name)) + ['www.cc.gatech.edu']:
            for pat in DEEP_PATTERNS:
                if len(tk) >= 2:
                    urls.append(pat.format(h=h, all='-'.join(tk), first=tk[0], last=tk[-1]))
        for pat in S.field(S.get(key), 'periods.profile_patterns') or []:
            if len(tk) >= 2:
                urls.append(pat.format(first=tk[0], last=tk[-1], all='-'.join(tk)))
        urls = list(dict.fromkeys(u for u in urls if u))
        ev = {}
        for u in urls:
            if all(y in ev for y in miss):
                break
            k = re.sub(r'^https?://', '', u)
            rows = W.cdx_rows(c, k, frm=str(min(miss)), to=str(max(miss)), collapse='timestamp:6')
            for y in [y for y in miss if y not in ev]:
                for r in [r for r in rows if r['timestamp'].startswith(str(y))][:4]:
                    cap, st, sha, b = W.capture(c, r['timestamp'], r['original'], u, 'deep:' + name)
                    if st != 200:
                        continue
                    flat = W.flat(b)
                    is_home = u in t['urls'] or u in (supplied.get(name) or [])
                    if is_home and not rx.search(flat):
                        continue
                    hit = [h for h in CR.faculty_evidence([('deep', cap, sha, r['timestamp'], flat)], names) if h['ladder']]
                    if hit:
                        ev[y] = dict(url=cap, sha256=sha, quote=hit[0]['quote'], observed=f"{r['timestamp'][:4]}-{r['timestamp'][4:6]}-{r['timestamp'][6:8]}",
                                     kind='homepage_capture' if is_home else 'unit_page_capture', page=u)
                        break
        out[name] = dict(gap_years=miss, evidence={str(y): e for y, e in ev.items()}, closed=all(y in ev for y in miss), unproven=[y for y in miss if y not in ev], urls_tried=len(urls))
        print(json.dumps(dict(pi=name, gaps=miss, proven=sorted(ev), unproven=out[name]['unproven'], urls=len(urls))), flush=True)
    dp = P.data_w('deep-gap-evidence.json', key)
    if only and dp.exists():   # a run for named PIs adds to the file; it never drops the others' evidence (the stage-4 gate reads it)
        out = {**json.loads(dp.read_text()), **out}
    dp.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    if not write:
        return out
    sec, save = CO.open_section(key)
    for name, g in out.items():
        if only and name not in only:
            continue
        x = pi_row(cen, add, name)
        e = sec.setdefault(name, {})
        if work_years and g['evidence'] and not g['closed']:   # proven years of a work-years pass: one reviewed period per contiguous run of listing and capture years (as extend())
            ys = sorted(set(x.get('years_listed') or []) | {int(y) for y in g['evidence']})
            runs, cur = [], []
            for y in ys:
                if cur and y != cur[-1] + 1:
                    runs.append(cur); cur = []
                cur.append(y)
            runs.append(cur)
            src = {}
            for s_ in sorted([s_ for s_ in x.get('sources') or [] if s_.get('quote') and s_.get('sha256')], key=lambda s_: s_.get('observed') or ''):
                src.setdefault(int(str(s_.get('observed') or '0')[:4] or 0), s_)
            iso_ = lambda d: (f'{d[:4]}-{d[4:6]}-{d[6:8]}' if d and re.fullmatch(r'\d{8}(?:\d{2}){0,3}', d) else d)
            pers = []
            for run in runs:
                evs = []
                for y in run:
                    if str(y) in g['evidence']:
                        v = g['evidence'][str(y)]; evs.append({k_: v[k_] for k_ in ('url', 'sha256', 'quote', 'observed', 'kind')})
                    elif y in src:
                        s_ = src[y]; evs.append(dict(url=s_['url'], sha256=s_['sha256'], quote=s_['quote'], observed=iso_(str(s_.get('observed'))[:8]), kind=s_.get('kind') or 'unit_listing'))
                pers.append(dict(id=f"override_period_workyears_{key}_{re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')}_{run[0]}", start=str(run[0]), end=None, asof=evs[-1]['observed'][:10] if evs else None,
                                 datePrecision='year', evidence=evs, reviewed='periods_school_deep_workyears_20261105',
                                 note=f"Dated evidence for every year {run[0]}-{run[-1]}: listings and dated Wayback captures naming the PI with a ladder title (hierarchy/{key}/deep-gap-evidence.json, work-years pass). Start is a lower bound; no end is claimed."))
            e['periods'] = [q for q in e.get('periods') or [] if not str(q.get('reviewed', '')).startswith('periods_school_deep_workyears')] + pers
            e['why_periods'] = 'Years proven by dated captures and listings for the years of the PI\'s identified works (tools/periods_school.py deep --work-years).'
        if g['closed']:
            srcs = sorted([s_ for s_ in x.get('sources') or [] if s_.get('quote')], key=lambda s_: s_.get('observed') or '')
            iso = lambda d: (f'{d[:4]}-{d[4:6]}-{d[6:8]}' if d and re.fullmatch(r'\d{8}(?:\d{2}){0,3}', d) else d)
            evs = ([dict(url=srcs[0]['url'], sha256=srcs[0]['sha256'], quote=srcs[0]['quote'], observed=iso(srcs[0].get('observed')), kind='dept_listing')] if srcs else []) + \
                  [dict(url=v['url'], sha256=v['sha256'], quote=v['quote'], observed=v['observed'], kind=v['kind']) for _, v in sorted(g['evidence'].items())]
            ys = sorted(set(x.get('years_listed') or []))
            e['periods'] = [dict(id=f"override_period_deep_{key}_{re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')}", start=str(ys[0]), end=None, asof=evs[-1]['observed'][:10], datePrecision='year', evidence=evs,
                                 note=f"Bridged: listings plus dated captures for the gap years {g['gap_years']} (hierarchy/{key}/deep-gap-evidence.json). Start is a lower bound; no end is claimed.",
                                 reviewed='periods_school_deep_20261104')]
            e['why_periods'] = 'Gap years closed by dated captures in the second look (tools/periods_school.py deep).'
        else:
            e['unproven_years'] = sorted(set(e.get('unproven_years') or []) | set(g['unproven']))
            e['why_unproven'] = (f"Second look 2026-11-04: {g['urls_tried']} URLs tried (the PI's homepages, profile-URL variants on the home unit's hosts across URL eras, person-supplied URLs) over the Wayback window; "
                                 f"no dated capture names the PI with a ladder title in {g['unproven']}. These years prove nothing (R-PAP-01); R-PAP-28 bridges the papers at build time.")
    save()


if __name__ == '__main__':
    if sys.argv[1] == 'gaps' and '--max-pis' in sys.argv:   # chunked, resumable: gaps <key> --max-pis N
        gaps(sys.argv[2], max_pis=int(sys.argv[sys.argv.index('--max-pis') + 1]))
    elif sys.argv[1] == 'fetch':   # fetch <key> [--all] [NAME ...]: the PIs stage 4 still needs, every census PI with --all, or the named PIs
        fetch(sys.argv[2], only=[a for a in sys.argv[3:] if not a.startswith('--')] or None, everyone='--all' in sys.argv, live_only='--live-only' in sys.argv)
    else:
        {'extract': extract, 'gaps': gaps, 'extend': extend, 'truncated': truncated, 'deep': deep}[sys.argv[1]](sys.argv[2])
