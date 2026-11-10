"""Home departments for a composed first-native school (ZJU): no dated department-listing rows exist, so the rows come from the census
(a bare list or {'faculty': [...]}) plus census-additions, and the reviewed census-overrides decisions (R-HOME-01 semantics):

  * a PI whose only unit is a center (charter [census].center_units) is `hold`: a center is never a home until an academic unit is evidenced;
  * a single non-center unit on the official listing -> accepted, home_basis `listed_title`, evidence = the PI's pi_basis (url, sha256, quote);
  * an override `home_department` + `home_department_evidence` (url, sha256, verbatim quote) -> `primary_stated` when the page states the appointment,
    `primary_unresolved` (two or more units, home_department only the reporting unit) when the page names several units and not which is primary.
-> hierarchy/<key>/derived/home-departments-school.json (the stage-3 gate input).  usage: home_departments_composed.py <key>
"""
import json
import sys

import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
import census_overrides as CO  # noqa: E402
from cs_related_school import census_rows  # noqa: E402
from home_departments_school import apply_reviewed_homes  # noqa: E402


def _read(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def build(rows, overrides, units, centers):
    """Base rows from the census; a reviewed decision is applied by the landed R-HOME-01 implementation (home_departments_school.apply_reviewed_homes)."""
    out = []
    for x in rows:
        if not x.get('is_pi'):
            continue
        codes = list(x.get('departments') or [])
        b = x.get('pi_basis') or {}
        row = dict(name=x['name'], home_department=None, also=[units.get(c, c) for c in codes], no_academic_department=False, status='hold',
                   home_basis=None, evidence=dict(url=b.get('url'), sha256=b.get('sha256'), quote=b.get('quote')), note='')
        if len(codes) == 1 and codes[0] not in centers and b.get('url') and b.get('sha256') and b.get('quote'):
            row.update(home_department=units.get(codes[0], codes[0]), also=[], status='accepted', home_basis='listed_title',
                       note=f'the {codes[0]} faculty listing names one unit')
        else:
            row['note'] = ('only a center names this PI: no academic unit is evidenced (center rule, R-HOME-01)' if codes and all(c in centers for c in codes)
                           else 'no unit evidenced')
        out.append(row)
    return apply_reviewed_homes(out, overrides, lambda u: u)


def main(key):
    cfg = S.get(key)
    units = {d['code']: d['name'] for d in cfg.get('departments') or []}
    units.update({u['code']: u['name'] for u in cfg.get('affiliated_units') or []})
    centers = set(S.field(cfg, 'census.center_units') or [])
    rows = census_rows(_read(P.data('census-faculty.json', key), None)) + census_rows(_read(P.data('census-additions.json', key), []))
    out = build(rows, CO.section(key), units, centers)
    for r in out:
        r['school'] = key
    P.data_w('home-departments-school.json', key).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    from collections import Counter
    print(json.dumps(dict(Counter(r['status'] for r in out) + Counter('basis:' + str(r['home_basis']) for r in out))))


if __name__ == '__main__':
    main(sys.argv[1])
