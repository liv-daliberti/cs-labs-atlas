"""Home departments for the released legacy schools (MIT, Stanford, Berkeley, Princeton, CMU) whose census is a hand-composed list
(no dated listing rows), under R-HOME-01. Rows come from census-faculty.json + census-additions.json; the unit codes are the census
`departments`. Rules, in order:
  1. units = departments minus the reviewed *centers* of hierarchy/<key>/reviewed/home-department-rules.json (a lab, institute or program
     with no tenure line is never a home; it stays visible in `also`).
  2. one unit left -> accepted, home_basis `listed_title`, evidence = the PI's pi_basis (url + sha256 + quote).
  3. two or more units -> accepted with home_basis `primary_unresolved`: every unit is listed (home_department is only the reporting unit:
     the school's computing department when one is among them, else the first listed), evidence = one dated source per unit where the
     census has one. No unit is called primary without a page that says so (that is a reviewed `home_department` decision in
     census-overrides-school.json: home_department + home_department_evidence + primary_stated, applied last by apply_reviewed_homes).
  4. no unit left -> hold (written, never a placeholder).
   (hand decisions: hierarchy/<key>/reviewed/home-department-decisions.json, same shape)
-> hierarchy/<key>/derived/home-departments.json.   usage: home_departments_released.py <key>
"""
import collections, json, re, sys
from pathlib import Path

import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
import census_overrides as CO  # noqa: E402
from cs_related_school import census_rows  # noqa: E402
from home_departments_school import apply_reviewed_homes  # noqa: E402

HEX = re.compile(r'^[0-9a-f]{64}$')


def _read(p, d):
    return json.loads(Path(p).read_text()) if Path(p).exists() else d


def good(e):
    return bool(e and e.get('url') and e.get('quote') and HEX.match(str(e.get('sha256') or '')))


def unit_source(x, unit):
    """The latest census source whose kind or url names the unit and whose quote names the person."""
    u = unit.lower()
    best = None
    for s in x.get('sources') or []:
        if not good(s) or u not in ((s.get('kind') or '') + ' ' + s['url']).lower():
            continue
        if best is None or str(s.get('observed') or '') >= str(best.get('observed') or ''):
            best = s
    return dict(url=best['url'], sha256=best['sha256'], quote=best['quote']) if best else None


BELOW_LINE = re.compile(r'below the line|primary appointment in another', re.I)


def split_units(codes, aliases):
    """'Medicine (Computational Medicine); Biomedical Data Science' -> two units; 'Sloan School of Management (CSAIL PI listing)' -> the unit; a 'Department of ' prefix and reviewed aliases are normalized."""
    out = []
    for c in codes:
        if BELOW_LINE.search(c):
            continue
        for u in re.split(r';| / ', c):
            u = re.sub(r'\s*\((?:CSAIL[^)]*|[^)]*listing)\)\s*$', '', u.strip())
            u = re.sub(r'^Department of\s+', '', u)
            u = aliases.get(u, u)
            if u and u not in out:
                out.append(u)
    return out


def build(rows, centers, computing, overrides, aliases=None, staff_ranks=()):
    out, seen = [], set()
    for x in rows:
        if not x.get('is_pi') or x['name'] in seen:
            continue
        seen.add(x['name'])
        raw = list(dict.fromkeys(x.get('departments') or []))
        codes = split_units(raw, aliases or {})
        units = [c for c in codes if c not in centers]
        cent = [c for c in codes if c in centers]
        b = x.get('pi_basis') or {}
        ev = dict(url=b.get('url'), sha256=b.get('sha256'), quote=b.get('quote'))
        row = dict(name=x['name'], home_department=None, also=cent, no_academic_department=False, status='hold', home_basis=None, evidence=ev, note='')
        if len(units) == 1 and good(ev):
            row.update(home_department=units[0], status='accepted', home_basis='listed_title',
                       note=f'the census lists one academic unit ({units[0]})' + (f'; also {", ".join(cent)} (not a department)' if cent else ''))
        elif len(units) >= 2:
            home = next((u for u in units if u in computing), units[0])
            evs = [e for e in (unit_source(x, u) for u in units) if e]
            if good(ev):
                evs = [ev] + [e for e in evs if e['sha256'] != ev['sha256']]
            if evs:
                row.update(home_department=home, also=[u for u in units if u != home] + cent, status='accepted', home_basis='primary_unresolved',
                           primary_unresolved=units, evidence=evs[0], reviewed_home_evidence=evs,
                           note=f'listed in {" and ".join(units)}; no captured page states which is primary (R-HOME-01): {home} is the reporting unit only')
            else:
                row['note'] = 'several units, no usable evidence'
        elif not units and cent and x.get('rank') in staff_ranks and good(ev):
            row.update(home_department=cent[0], also=cent[1:], status='accepted', home_basis='listed_title',
                       note=f'{x.get("title_as_listed")}: research or affiliate staff appointed in {cent[0]} itself, no academic department (reviewed rule: staff_center_ranks)')
        else:
            row['note'] = ('only a center is evidenced (R-HOME-01 center rule)' if cent else
                           'the census marks the CS-division listing as below the line (primary appointment in another department): the primary unit is not evidenced' if any(BELOW_LINE.search(c) for c in raw) else 'no unit evidenced')
        out.append(row)
    return out


def main(key):
    cfg = S.get(key)
    here = Path(__file__).resolve().parents[1] / 'hierarchy' / key / 'reviewed'   # this checkout's reviewed files win (a branch edit is live before landing)
    rev = here if here.is_dir() and (here / 'home-department-rules.json').exists() else Path(P.HIERARCHY) / key / 'reviewed'
    rules = _read(rev / 'home-department-rules.json', {})
    decisions = dict(CO.section(key))   # hand decisions of this stage (home_department + home_department_evidence + primary_stated | primary_unresolved)
    decisions.update(_read(rev / 'home-department-decisions.json', {}))
    centers = set(rules.get('centers') or [])
    computing = list(S.field(cfg, 'census.computing_departments') or [])
    rows = census_rows(_read(P.data('census-faculty.json', key), None)) + census_rows(_read(P.data('census-additions.json', key), []))
    out = build(rows, centers, computing, decisions, rules.get('aliases') or {}, tuple(rules.get('staff_center_ranks') or ()))
    apply_reviewed_homes(out, decisions, lambda u: u)
    for r in out:
        r['school'] = key
    if '--dry' in sys.argv:
        print(json.dumps(dict(collections.Counter(r['status'] for r in out) + collections.Counter('basis:' + str(r['home_basis']) for r in out))))
        for r in out:
            if r['status'] == 'hold':
                print('HOLD', r['name'], r['also'], r['note'])
        return
    P.data_w('home-departments-school.json', key).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps(dict(collections.Counter(r['status'] for r in out) + collections.Counter('basis:' + str(r['home_basis']) for r in out))))


if __name__ == '__main__':
    main(sys.argv[1])
