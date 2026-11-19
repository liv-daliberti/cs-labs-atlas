"""Appointments: reviewed faculty periods and dated department listings. R-PAP-01 (contains, same_year: the appointment),
R-PAP-02 (not_faculty_row, datebounds seasons), R-PAP-03 (listings_after_move), R-PAP-13 (transition_side)."""
import calendar, re

from .common import TODAY, WINDOW_START, best_sources, iso_date, source_year
from .names import Name, nosuffix, toks

SEASON = {'spring': ('01-01', '05-31'), 'summer': ('06-01', '08-31'), 'fall': ('08-01', '12-31'), 'autumn': ('08-01', '12-31')}


def datebounds(value):
    """A date's earliest and latest day. A reviewed value may carry a note after the date ('2020 (Fall)', '2022-12 (first
    dated observation; ...)'): the leading date counts, narrowed to the term when the note names a season."""
    value = str(value or '').strip()
    m = re.fullmatch(r'(\d{4}(?:-\d{2}){0,2})\s*\((.*)\)', value)
    if m:
        value = m.group(1); term = SEASON.get(m.group(2).strip().lower()) if len(value) == 4 else None
        if term:
            return f'{value}-{term[0]}', f'{value}-{term[1]}'
    if re.fullmatch(r'\d{4}', value):
        return value + '-01-01', value + '-12-31'
    if re.fullmatch(r'\d{4}-\d{2}', value):
        y, m = map(int, value.split('-')); return value + '-01', value + '-' + str(calendar.monthrange(y, m)[1])
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return value, value
    return None


def contains(start, end, date, asof=None):
    """The site's rule (reconcile-lab-identities-periods.py): every possible publication date fits the period."""
    sb = datebounds(start); eb = datebounds(end or asof); pb = datebounds(date)
    if not sb or not eb or not pb:
        return 'unresolved'
    lo, hi = pb; hi = min(hi, TODAY)
    if lo > hi:
        return 'unresolved'
    if hi < sb[0] or lo > eb[1]:
        return 'outside'
    return 'supported' if lo >= sb[1] and hi <= eb[0] else 'boundary_unresolved'


def same_year(date):
    b = datebounds(date)
    return int(b[0][:4]) if b and b[0][:4] == b[1][:4] else None


def before_window(date):
    """True when the paper's own date (a day, month or year) lies before the atlas window (WINDOW_START, 2016): no paper of that year is a lab paper, whichever route
    brought it in (the sweeps fetch 2016 and later, but a by-id re-pull of a merged id, or a PI work file, can hold an older record)."""
    y = same_year(date)
    return y is not None and y < WINDOW_START


def transition_side(p, lst, date):
    """Which side of a listing's capture date a work falls on, in the PI's first (arrival) or last (departure) listed year.
    'inside' when the year is no transition year, or every possible date of the work is on the school's side of the
    capture (on or before it in a departure year; on or after it in an arrival year); else 'outside'. The window's
    first year (2016) is no arrival and the current year no departure."""
    ys = sorted(l['year'] for l in p.get('listings') or [])
    y = lst['year']
    departing = y == ys[-1] and y < int(TODAY[:4])
    arriving = y == ys[0] and y > 2016
    if not departing and not arriving:
        return 'inside'
    m = re.search(r'/web/(\d{4})(\d{2})(\d{2})', lst.get('url') or '')
    cap = f'{m.group(1)}-{m.group(2)}-{m.group(3)}' if m else None
    pb = datebounds(date)
    if not cap or not pb:
        return 'outside'
    if departing and pb[1] > cap:
        return 'outside'
    if arriving and pb[0] < cap:
        return 'outside'
    return 'inside'


def transition_status(p, lst, date):
    """R-PAP-13's dated-capture rule with the undecided case kept apart (ROADMAP #29): None when the listing's year is no transition
    year; else 'inside' or 'outside' when every possible date of the work is on one side of the capture date, 'undecided' when the work's
    date range straddles the capture (a bare year, or a month containing it), 'no_capture' when the listing has no dated capture or the
    work no usable date. Departure year: the school's side is on or before the capture; arrival year: on or after it."""
    ys = sorted(l['year'] for l in p.get('listings') or [])
    y = lst['year']
    departing = y == ys[-1] and y < int(TODAY[:4])
    arriving = y == ys[0] and y > 2016
    if not departing and not arriving:
        return None
    m = re.search(r'/web/(\d{4})(\d{2})(\d{2})', lst.get('url') or '')
    cap = f'{m.group(1)}-{m.group(2)}-{m.group(3)}' if m else None
    pb = datebounds(date)
    if not cap or not pb:
        return 'no_capture'
    lo, hi = pb
    if departing:
        return 'inside' if hi <= cap else 'outside' if lo > cap else 'undecided'
    return 'inside' if lo >= cap else 'outside' if hi < cap else 'undecided'


def _year(v):
    return int(str(v)[:4]) if str(v or '')[:4].isdigit() else None


def listings_after_move(listings, mine, reviewed_periods):
    """The listing years after an evidenced departure, {year: listing} (2026-10-29): a listing after an evidenced departure
    is a stale page, not an appointment (Princeton ECE kept Mung Chiang, left 2017, and Yuxin Chen, left 2021, on its
    faculty list through 2026); kept aside as listingsAfterMove. A later period (collection or reviewed) that covers the
    year keeps the listing. `mine` are the PI's collection faculty periods (facultyStart/facultyEnd/evidence), and
    `reviewed_periods` the census-overrides periods (start/end). Documented death also ends an appointment;
    later memorial/profile listings do not prove continued employment."""
    def ended(q):
        return any(any(k in (e.get('kind') or '') for k in ('end_moved', 'end_deceased')) for e in q.get('evidence') or [])
    moved = [_year(q['facultyEnd']) for q in mine if _year(q.get('facultyEnd')) and ended(q)]
    # a reviewed period that ends with a move counts too (2026-10-29: Cynthia Rudin, MIT to Duke in 2016; MIT's CSAIL PI
    # listing still named her in 2026)
    moved += [_year(q['end']) for q in reviewed_periods or [] if _year(q.get('end')) and ended(q)]
    spans = [(_year(q.get('facultyStart')), _year(q.get('facultyEnd'))) for q in mine] + [(_year(q.get('start')), _year(q.get('end'))) for q in reviewed_periods or []]

    def covered(y):
        return any(s and s <= y and (e is None or y <= e) for s, e in spans)
    return {y: l for y, l in listings.items() if moved and y > max(moved) and not covered(y)}


NOT_FACULTY = re.compile(r'\b(ph\.?\s?d\.?\s+(student|candidate)|graduate student|doctoral (student|candidate)|master.?s student|'
                         r'post-?docs?|postdoctoral|post-doctoral)\b', re.I)
INCOMING = re.compile(r'\b(incoming|future faculty|will join|joining (?:us )?(?:in )?(?:the )?(?:fall|spring|summer|\d{4})|'
                      r'starting (?:in )?(?:(?:fall|spring|summer|autumn|january|july|september) )?\d{4}|arriving)\b', re.I)


def not_faculty_row(text):
    """A dated listing row that lists the person as a student or postdoc, not as faculty: it proves no appointment
    (the same-year listing rule is about faculty listings; directories such as CMU's SCS list students too). Nor does a
    row announcing a future appointment ('incoming', 'will join', 'starting 2025'): 'Acting' and other held titles count."""
    t = text or ''
    return bool(INCOMING.search(t)) or (bool(NOT_FACULTY.search(t)) and not re.search(r'professor|lecturer|faculty', t, re.I))


def pi_listings(x, yearly, n):
    """A PI's dated listings, {year: listing}: the census row's own sources (a dated capture whose quote names the
    family name and is a faculty row) and the verified yearly department listings (listings/<school>/listings.json) of
    the PI's census rows; the first listing of a year is kept."""
    listings = {}
    # A reviewed bilingual faculty record can have a Chinese canonical name and
    # an English source quote. Require the whole spelled-out alias, never just
    # its surname or initials, before that quote proves its own calendar year.
    aliases = [nosuffix(toks(a)) for a in x.get('aliases') or []]
    aliases = [a for a in aliases if len(a) >= 2 and all(len(t) > 1 for t in a)]
    for s in x.get('sources') or []:
        y = source_year(s); sur = nosuffix(toks(x['name']))[-1] if toks(x['name']) else ''  # R-PAP-08: 'Lionel P. Robert Jr.' is listed as 'Lionel Robert'
        quote = ' '.join(toks(s.get('quote')))
        full_alias = any(' ' + ' '.join(a) + ' ' in ' ' + quote + ' ' for a in aliases)
        named = bool(sur and sur in quote) or full_alias
        if y and 2016 <= y <= 2026 and s.get('sha256') and s.get('quote') and named and not not_faculty_row(s['quote']):
            listings.setdefault(y, dict(url=s['url'], sha256=s['sha256'], quote=s['quote'], kind=s.get('kind') or '', year=y))
    for nm_ in [x['name']] + list(x.get('mergedCensusRows') or []):
        for r in yearly.get(nm_, []):
            if not_faculty_row(r.get('rank_as_listed') or r.get('quote')):
                n['listing_rows_not_faculty'] += 1; continue
            listings.setdefault(int(r['year']), dict(url=r['capture_url'], sha256=r['sha256'], quote=r['quote'], kind='dept_listing:' + (r.get('department') or ''),
                                                     year=int(r['year']), rank=r.get('rank_as_listed'), emeritus=r.get('emeritus'), visiting=r.get('visiting')))
    return listings


def pi_mine(periods, ids, name):
    """The collection faculty periods of the PI: by collection person id, or by name."""
    return [p for p in periods if p.get('personId') in ids or Name([p.get('name') or '']).match(name)]


def pi_periods(mine, o, name=None):
    """The PI's periods as the package writes them: the collection periods (up to two evidence items, complete ones
    first) and the reviewed periods of census-overrides.json (`o`: the PI's override entry; an open reviewed period is
    current as of today)."""
    return [dict(id=p.get('id'), start=p.get('facultyStart'), end=p.get('facultyEnd'), asof=p.get('ongoingAsOf') or p.get('facultyLastConfirmed'),
                 evidence=best_sources(p.get('evidence'))) for p in mine] \
        + [dict(q, **{k: iso_date(q[k]) for k in ('start', 'end') if q.get(k)},
                id=q.get('id') or _override_period_id(name or o.get('name'), q),
                asof=iso_date(q.get('asof')) or (None if q.get('end') else TODAY)) for q in o.get('periods') or []]  # reviewed periods (census-overrides.json)


def _override_period_id(name, q):
    """A reviewed period written without an `id` (the pis.json schema requires one) gets a stable id from its PI, start and end."""
    slug = re.sub(r'[^a-z0-9]+', '_', str(name or 'pi').lower()).strip('_')
    return f"override_period_{slug}_{iso_date(q.get('start')) or 'open'}_{iso_date(q.get('end')) or 'open'}"


def bridge_periods(periods, direct_years, moved=False):
    """R-PAP-28 (2026-11-02, owner: accuracy pass; Klasnja at Michigan). The continuity periods between two of one PI's school
    periods: the gap from the last confirmation of an open period A (its `asof`) to the start of the next period B. Reviewed
    periods built from dated captures say only that the person was there on the capture date ('start is a lower bound, no end is
    claimed'), so the years between two such captures held no paper at all (Klasnja: UMSI profile 2020-08 and directory 2026-01;
    his 2021-2025 papers, 12 a year, all credit Michigan). A gap is bridged when A is open (no end), no period or listing of the
    PI carries departure evidence (`moved`), and in every full calendar year of the gap the PI's identified works name the school
    in their own authorship (`direct_years`: {year: count}). Returns the new periods, each citing both captures."""
    ps = sorted((q for q in periods if q.get('start')), key=lambda q: datebounds(q['start'])[0] if datebounds(q['start']) else '')
    out = []
    if moved:
        return out
    for a, b in zip(ps, ps[1:]):
        ea = a.get('asof') if not a.get('end') else None
        da, db = datebounds(ea), datebounds(b['start'])
        if not ea or not da or not db or any('end_moved' in (e.get('kind') or '') for q in (a, b) for e in q.get('evidence') or []):
            continue
        if da[1] >= db[0]:  # no gap
            continue
        full = range(int(da[0][:4]) + 1, int(db[0][:4]))
        if not full or not all(direct_years.get(y, 0) >= 1 for y in full):
            continue
        out.append(dict(id=f"bridge_{a.get('id') or 'period'}__{b.get('id') or 'period'}", start=ea, end=b['start'], asof=None,
                        evidence=list((a.get('evidence') or [])[:1]) + list((b.get('evidence') or [])[:1]),
                        datePrecision='day', endPrecision=b.get('datePrecision') or 'year', reviewed='R-PAP-28 continuity bridge',
                        note=f"Both periods are open lower bounds at the school (last confirmed {ea}; next period starts {b['start']}), the "
                             f"PI has no departure evidence, and the PI's identified works name the school in every full year between: "
                             f"{full[0]}-{full[-1]}."))
    return out


LISTING_BRIDGE = 'R-PAP-37 listing continuity'
NONPRIMARY_ROW = re.compile(r'\b(adjunct|on leave|consulting|visiting|courtesy|affiliate|emerit|part[- ]time)', re.I)


def listing_bridge_periods(p, direct_years, other_years, covered, moved=False, today=None):
    """R-PAP-37 (2026-11-05, owner task: Michigan student-paper gaps; Gorodetsky's 2021-2026 papers). Continuity periods built from a PI's
    dated listings alone. A listing proves its own calendar year only, so a PI whose school listing is captured in some years (Gorodetsky:
    AERO unit listing 2018-2020; the later captures are filter or hub pages with no names) has no appointment for the years after it, and
    every paper of those years that names the school in its own byline is `outside_appointment`. The R-PAP-28 continuity argument covers
    it: the gap after a listing year is bridged when
      - the PI has listings in two or more calendar years (a single capture shows no span), no period of any kind (periods are reviewed; a PI with one is R-PAP-28's), no departure evidence (`moved`: listings after
        a move, or an end_moved period) and no non-primary listing row (adjunct, courtesy, visiting, emeritus, on leave);
      - in every calendar year of the gap the PI's identified works name the school in their own authorship and credit no other
        institution more often (`direct_years`, `other_years`: {year: count});
      - no listing capture of a department the PI was listed in covers a gap year and omits the PI: a listing drop closes the period
        (R-PAP-03, 2026-11-02). `covered`: {department: {years}} from the school's listing coverage; a department listing the PI
        with no coverage data bridges nothing.
    Two shapes: (a) interior, from listing year A's capture to the next listing year B's capture, every year between qualifying;
    (b) tail, from the last listing's capture through the longest run of qualifying years after it (open when the run reaches today).
    Never a head (before the first listing: the arrival side is R-PAP-13's). The period admits only a paper whose own byline names
    the school (`direct_via`), or a page-1-proved DBLP/lab-page addition. Returns the new periods, each citing the listing."""
    today = today or TODAY
    ls = sorted((l for l in p.get('listings') or [] if l.get('year')), key=lambda l: l['year'])
    if moved or not ls or p.get('periods') or p.get('listingsAfterMove'):
        return []
    if len({l['year'] for l in ls}) < 2:
        return []  # one listing year shows no observed span: a PI seen once (a 2016 capture) may have left before the paper (Mossel 2017, Browning 2018)
    if any(NONPRIMARY_ROW.search(' '.join(str(l.get(k) or '') for k in ('quote', 'kind', 'rank'))) or l.get('emeritus') or l.get('visiting') for l in ls):
        return []
    depts = {(l.get('kind') or '').split(':', 1)[1] for l in ls if (l.get('kind') or '').startswith('dept_listing:')}

    def blocked(y):
        return any(y in (covered or {}).get(d, ()) if d in (covered or {}) else True for d in depts)

    def qualifies(y):
        return direct_years.get(y, 0) >= 1 and direct_years.get(y, 0) >= other_years.get(y, 0) and not blocked(y)

    def cap(l):
        m = re.search(r'/web/(\d{4})(\d{2})(\d{2})', l.get('url') or '')
        return f'{m.group(1)}-{m.group(2)}-{m.group(3)}' if m else f"{l['year']}-12-31"

    def make(a, end, asof, years, shape):
        ev = [dict(url=a['url'], sha256=a['sha256'], quote=a['quote'], kind=a.get('kind') or 'listing')]
        return dict(id=f"listing_bridge_{a['year']}_{shape}", start=cap(a), end=end, asof=asof, evidence=ev, datePrecision='day',
                    **({'endPrecision': 'day'} if end else {}),
                    reviewed=LISTING_BRIDGE, years=[years[0], years[-1]],
                    note=f"The PI's dated listing of {a['year']} is the last evidence of the appointment; the PI has no departure evidence, no listing capture "
                         f"that covers {years[0]}-{years[-1]} omits the PI, and the PI's identified works name the school in their own authorship in every "
                         f"year from {years[0]} to {years[-1]}.")

    out, cy = [], int(today[:4])
    for a, b in zip(ls, ls[1:]):
        gap = list(range(a['year'] + 1, b['year']))
        if gap and all(qualifies(y) for y in gap):
            out.append(make(a, cap(b), None, gap, 'interior'))
            out[-1]['id'] += f"_{b['year']}"
    last = ls[-1]
    run = []
    for y in range(last['year'] + 1, cy + 1):
        if not qualifies(y):
            break
        run.append(y)
    if run:
        out.append(make(last, None if run[-1] == cy else f'{run[-1]}-12-31', today if run[-1] == cy else None, run, 'tail'))
    return out
