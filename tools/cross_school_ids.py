"""Cross-school identity check (Georgia Tech stage 5 follow-up): a PI who is also a PI at another atlas school must carry the same DBLP id, ORCID or reviewed OpenAlex id in both
schools' identity records (docs/ADDING-A-SCHOOL.md, stage 5; the atlas ids join people by shared anchors, so a person with disjoint anchors in two schools becomes two people).

Same person candidates: the same family name and first given name (spelled out), no conflicting middle initial, across the PI names and aliases of every other school (their
hierarchy/<school>/pis.json) and the onboarding school's census + reviewed overrides. Per pair:
  agree     the records share an anchor (dblp pid, ORCID or OpenAlex author id)
  one_side  only one side has anchors of that kind in common to compare (a missing id on the other side): the id should be added
  conflict  both sides carry anchors and share none (a namesake, or one record has the wrong id)
-> hierarchy/<key>/cross-school-ids.json; prints the counts. usage: cross_school_ids.py <key>
"""
import json
import sys

import atlas_paths as P  # noqa: E402
import census_overrides as CO  # noqa: E402
import school_config as S  # noqa: E402
from oa_identity_candidates import name_match  # noqa: E402


def anchors(rec):
    out = set()
    for d in rec.get('dblp') or []:
        out.add('dblp:' + str(d).rsplit('/pid/', 1)[-1])
    for o in rec.get('orcid') or []:
        out.add('orcid:' + str(o).replace('https://orcid.org/', ''))
    for a in rec.get('openalex') or []:
        out.add('openalex:' + str(a).rsplit('/', 1)[-1])
    return out


def other_school(school):
    p = P.data('pis.json', school)
    if not p.exists():
        return []
    out = []
    for x in json.loads(p.read_text()):
        out.append(dict(school=school, name=x['pi'], names=list(x.get('names') or [x['pi']]), dblp=x.get('dblp') or [], orcid=(x.get('orcid') or []) + (x.get('orcidFromDblp') or []),
                        openalex=(x.get('reviewedOpenAlex') or x.get('oaAuthorIds') or [])))
    return out


def this_school(key):
    ov = CO.section(key)
    cen = json.loads(P.data('census-faculty.json', key).read_text())['faculty']
    add = json.loads(P.data('census-additions.json', key).read_text()) if P.data('census-additions.json', key).exists() else []
    out = []
    for x in cen + add:
        if not x.get('is_pi'):
            continue
        o = ov.get(x['name']) or {}
        oa = o.get('openalex') or x.get('openalex') or []
        out.append(dict(school=key, name=x['name'], names=[x['name']] + list(x.get('aliases') or []) + list(o.get('aliases') or []), dblp=list(x.get('dblp') or []) + ([o['dblp']] if isinstance(o.get('dblp'), str) else list(o.get('dblp') or [])),
                        orcid=list(x.get('orcid') or []) + list(o.get('orcid') or []), openalex=oa if isinstance(oa, list) else [oa]))
    return out


def full_names(names):
    """Name forms whose first given name is spelled out: an initial-first alias ('C. Karen Liu', 'Y. Choi') matches half the faculty of another school."""
    return [n for n in names if len(n.replace(',', ' ').split()[0].strip('.')) > 1 and not n.split()[0].endswith('.')] or names[:1]


def compare(mine, others):
    res = {'agree': [], 'one_side': [], 'conflict': []}
    for m in mine:
        ma = anchors(m)
        for o in others:
            if not any(name_match(a, b) for a in full_names(m['names']) for b in full_names(o['names'])):
                continue
            oa = anchors(o)
            row = dict(name=m['name'], other_school=o['school'], other_name=o['name'], mine=sorted(ma), theirs=sorted(oa))
            if ma & oa:
                res['agree'].append(row)
            elif ma and oa:
                res['conflict'].append(row)
            else:
                res['one_side'].append(row)
    return res


def main(key):
    others = [r for s in S.keys() if s != key for r in other_school(s)]
    res = compare(this_school(key), others)
    P.data_w('cross-school-ids.json', key).write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(json.dumps({k: len(v) for k, v in res.items()}))
    return res


if __name__ == '__main__':
    main(sys.argv[1])
