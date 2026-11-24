"""Census additions for the accepted CS-related decisions that never reached census-additions.json (2026-11-18).

tools/cs_related_school.py review writes census-additions.json together with cs-related-review.json. A school whose review was
composed by hand (VT: 'provisional ... no census addition or package admission yet') has accepted decisions and no additions, so
those people never become census rows and never get a lab (pis.json).

For every decision `accepted` with ladder faculty evidence whose name or alias is not already a census row (census-faculty.json:
any row, PI or not: the census rules decide those) or an addition, this writes one census-format row, the same shape
cs_related_school.py writes: sources are the decision's faculty evidence (kind unit_listing:<unit>), pi_basis is the first
ladder evidence, cs_related carries the DBLP person and window. Existing additions are never rewritten.

usage: census_additions_from_review.py <school> [--apply]      (default: print the rows that would be added)
"""
import argparse, json, re, sys, urllib.parse

import atlas_paths as P  # noqa: E402

SUFFIX = re.compile(r'\s+\d{4}$')  # DBLP homonym number: 'Walid Saad 0001'


def norm(name):
    return re.sub(r'[^a-z ]', '', SUFFIX.sub('', name or '').lower().replace('.', ' ')).split().__str__()


def slug(name):
    return re.sub(r'[^a-z0-9]+', '-', SUFFIX.sub('', name).lower()).strip('-')


def census_names(school):
    f = P.data('census-faculty.json', school)
    rows = json.loads(f.read_text()) if f.exists() else []
    rows = rows.get('faculty', rows) if isinstance(rows, dict) else rows
    adds = P.data('census-additions.json', school)
    rows = list(rows) + (json.loads(adds.read_text()) if adds.exists() else [])
    return {norm(n) for r in rows for n in [r.get('name')] + list(r.get('aliases') or []) if n}


def entry(row, school, today):
    ev = [dict(e, unit=e.get('unit') or urllib.parse.urlparse(e['url']).netloc) for e in row.get('faculty_evidence') or [] if e.get('ladder')]
    if not ev:
        return None
    first, last = ev[0], ev[-1]
    cs = row.get('cs_basis') or {}
    return dict(name=SUFFIX.sub('', row['name']), aliases=row.get('aliases') or [], collection_person_id=f"{school}_fac_" + slug(row['name']),
                dblp=(cs.get('dblp') or [])[:1], rank='ladder', title_as_listed=last['quote'],
                departments=list(dict.fromkeys(e['unit'] for e in ev)), years_listed=row.get('years_listed') or [],
                sources=[dict(url=e['url'], sha256=e['sha256'], quote=e['quote'], kind=f"unit_listing:{e['unit']}", observed=str(e['observed'])) for e in ev],
                is_pi=True, pi_basis=dict(kind='ladder_faculty', url=first['url'], sha256=first['sha256'], quote=first['quote'], observed=str(first['observed']),
                                          role='professor title on the unit faculty listing',
                                          cs_related=dict(dblp=cs.get('dblp') or [], dblp_window=cs.get('dblp_window'),
                                                          openalex=(cs.get('openalex_share') or {}).get('ids') or [], share=(cs.get('openalex_share') or {}).get('share'))),
                lab_units=[], added=f'cs_related_review_{today}_accepted_wired')


def missing(school, today):
    review = json.loads(P.data('cs-related-review.json', school).read_text())['decisions']
    have = census_names(school)
    out = []
    for r in review:
        if r.get('decision') != 'accepted' or any(norm(n) in have for n in [r['name']] + list(r.get('aliases') or [])):
            continue
        e = entry(r, school, today)
        if e:
            out.append(e)
            have |= {norm(n) for n in [r['name']] + e['aliases']}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('school'); ap.add_argument('--apply', action='store_true'); ap.add_argument('--today', default='20261118')
    a = ap.parse_args(argv)
    new = missing(a.school, a.today)
    print(json.dumps(dict(school=a.school, would_add=len(new), names=[e['name'] for e in new])))
    if a.apply and new:
        f = P.data_w('census-additions.json', a.school)
        cur = json.loads(f.read_text()) if f.exists() else []
        f.write_text(json.dumps(cur + new, indent=1, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
