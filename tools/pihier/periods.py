"""Appointments: reviewed faculty periods and dated department listings. R-PAP-01 (contains, same_year: the appointment),
R-PAP-02 (not_faculty_row, datebounds seasons), R-PAP-03 (listings_after_move), R-PAP-13 (transition_side)."""
import calendar, re

from .common import TODAY, best_sources, source_year
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


def _year(v):
    return int(str(v)[:4]) if str(v or '')[:4].isdigit() else None


def listings_after_move(listings, mine, reviewed_periods):
    """The listing years after an evidenced departure, {year: listing} (2026-10-29): a listing after an evidenced departure
    is a stale page, not an appointment (Princeton ECE kept Mung Chiang, left 2017, and Yuxin Chen, left 2021, on its
    faculty list through 2026); kept aside as listingsAfterMove. A later period (collection or reviewed) that covers the
    year keeps the listing. `mine` are the PI's collection faculty periods (facultyStart/facultyEnd/evidence), and
    `reviewed_periods` the census-overrides periods (start/end)."""
    moved = [_year(q['facultyEnd']) for q in mine if _year(q.get('facultyEnd')) and any('end_moved' in (e.get('kind') or '') for e in q.get('evidence') or [])]
    # a reviewed period that ends with a move counts too (2026-10-29: Cynthia Rudin, MIT to Duke in 2016; MIT's CSAIL PI
    # listing still named her in 2026)
    moved += [_year(q['end']) for q in reviewed_periods or [] if _year(q.get('end')) and any('end_moved' in (e.get('kind') or '') for e in q.get('evidence') or [])]
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
    for s in x.get('sources') or []:
        y = source_year(s); sur = nosuffix(toks(x['name']))[-1] if toks(x['name']) else ''  # R-PAP-08: 'Lionel P. Robert Jr.' is listed as 'Lionel Robert'
        if y and 2016 <= y <= 2026 and s.get('sha256') and s.get('quote') and sur and sur in ' '.join(toks(s['quote'])) and not not_faculty_row(s['quote']):
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


def pi_periods(mine, o):
    """The PI's periods as the package writes them: the collection periods (up to two evidence items, complete ones
    first) and the reviewed periods of census-overrides.json (`o`: the PI's override entry; an open reviewed period is
    current as of today)."""
    return [dict(id=p.get('id'), start=p.get('facultyStart'), end=p.get('facultyEnd'), asof=p.get('ongoingAsOf') or p.get('facultyLastConfirmed'),
                 evidence=best_sources(p.get('evidence'))) for p in mine] \
        + [dict(q, asof=q.get('asof') or (None if q.get('end') else TODAY)) for q in o.get('periods') or []]  # reviewed periods (census-overrides.json)
