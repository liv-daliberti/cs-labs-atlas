"""Are students one record each, and tied to their lab's papers? An audit over the built packages (read-only).

within_lab   two student records in one lab that are probably one person: same family name and a compatible first given
             name (same first initial and one given name a prefix of the other, or nickname-equal, or hyphen/space variants
             of one given name), or the same name tokens in another order. pi_hierarchy already merges records whose
             names Name.match; these are what slipped through.
across_labs  one person under several student ids in one school (co-advised, or found by two sources): records in
             different labs whose strict name key (first given name, family name; tools/pi_hierarchy.strict_name_one)
             agrees but whose ids differ.
same_paper   one lab paper linked to two student ids of the same lab whose names match each other (a duplicate shows up
             twice on one byline).
missed_link  a lab paper of the student's own lab, within three years of their recorded advising, whose byline has an
             author with the student's family name and first initial on an authorship that lists the school, but no
             link was made (a name form the matcher rejected). Also students with no link at all although the lab has
             papers in their years.
-> hierarchy/student-audit.json
usage: student_audit.py [school ...]
"""
import collections, gzip, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pi_hierarchy import Name, toks, given, nick_ok, strict_name_one, near_relation, EAST_ASIAN_FAMILY  # noqa: F401,E402

import atlas_paths as P  # noqa: E402  (every path in one place)
HERE = P.WORK; H = P.HIERARCHY
SCHOOLS = [s for s in P.SCHOOL_IDS if (H / s / 'students.json').exists()]


def compatible(a, b):
    """Probably one person: same family name, first given names compatible, or the same tokens reordered."""
    ta, tb = toks(a), toks(b)
    if len(ta) < 2 or len(tb) < 2:
        return False
    if sorted(ta) == sorted(tb):
        return True
    if ta[-1] != tb[-1] and ta[0] != tb[-1]:
        return False
    fa, fb = (ta[0], tb[0]) if ta[-1] == tb[-1] else (ta[-1], tb[0])
    ja, jb = ''.join(ta[:-1]), ''.join(tb[:-1])
    if ta[-1] in EAST_ASIAN_FAMILY and ta[-1] == tb[-1]:
        # (2026-10-29, as the link guard) under an East Asian family name a given name that is a prefix of another is a
        # different common name: 'Yuan Li' and 'Yu-Jhe Li' in Kitani's lab are two people
        return fa == fb or ja == jb or nick_ok(fa, fb)
    return fa[0] == fb[0] and (fa.startswith(fb) or fb.startswith(fa) or nick_ok(fa, fb) or ja == jb or ja.startswith(jb) or jb.startswith(ja))


def audit(s):
    S = json.load(open(H / s / 'students.json'))
    rows = [json.loads(l) for l in gzip.open(H / s / 'lab_papers.jsonl.gz', 'rt')]
    sp = [json.loads(l) for l in gzip.open(H / s / 'student_papers.jsonl.gz', 'rt')]
    by_lab = collections.defaultdict(list)
    for r in rows:
        by_lab[r['pi']].append(r)
    linked = collections.defaultdict(set)
    for x in sp:
        linked[(x['pi'], x['student'])].add(x['oa'])
    out = dict(school=s, within_lab=[], across_labs=[], same_paper=[], missed_link=[], students_without_links=0, lab_student_pairs=0)
    keyed = collections.defaultdict(set)
    for pi, recs in S.items():
        out['lab_student_pairs'] += len(recs)
        for i, a in enumerate(recs):
            keyed[strict_name_one(a['name'])].add((a['person'], pi, a['name']))
            for b in recs[i + 1:]:
                if compatible(a['name'], b['name']):
                    out['within_lab'].append(dict(pi=pi, a=[a['person'], a['name']], b=[b['person'], b['name']]))
        # links: missed name forms, students without links
        for a in recs:
            t = toks(a['name'])
            if len(t) < 2:
                continue
            fam, ini = t[-1], t[0][0]
            got = linked[(pi, a['person'])]
            cands = []
            for r in by_lab.get(pi, []):
                if r['oa'] in got or not near_relation(a, r.get('year')):
                    continue
                for b in r.get('byline_school') or []:
                    tb = toks(b)
                    if len(tb) >= 2 and fam in (tb[-1], tb[0]) and ini in (tb[0][0], tb[-1][0]) and not toks(b) == toks(pi):
                        cands.append(dict(oa=r['oa'], year=r.get('year'), byline_name=b)); break
            if cands:
                out['missed_link'].append(dict(pi=pi, student=a['person'], name=a['name'], papers=cands[:5], n=len(cands)))
            if not got and any(near_relation(a, r.get('year')) for r in by_lab.get(pi, [])):
                out['students_without_links'] += 1
    for k, v in keyed.items():
        ids = {i for i, _, _ in v}
        if k[1] and len(ids) > 1:
            out['across_labs'].append(dict(key=list(k), records=sorted([list(x) for x in v])))
    names = {(pi, a['person']): a['name'] for pi, recs in S.items() for a in recs}
    per = collections.defaultdict(list)
    for x in sp:
        per[(x['pi'], x['oa'])].append(x['student'])
    for (pi, oa), sids in per.items():
        sids = sorted(set(sids))
        for i, a in enumerate(sids):
            for b in sids[i + 1:]:
                na, nb = names.get((pi, a), ''), names.get((pi, b), '')
                if Name([na]).match(nb) or Name([nb]).match(na):
                    out['same_paper'].append(dict(pi=pi, oa=oa, a=[a, na], b=[b, nb]))
    out['counts'] = dict(lab_student_pairs=out['lab_student_pairs'], within_lab_pairs=len(out['within_lab']), across_lab_people=len(out['across_labs']),
                         same_paper_pairs=len(out['same_paper']), students_with_missed_links=len(out['missed_link']),
                         missed_links=sum(m['n'] for m in out['missed_link']), students_without_links=out['students_without_links'])
    return out


def main(schools):
    res = [audit(s) for s in schools]
    json.dump(res, open(H / 'student-audit.json', 'w'), indent=1, ensure_ascii=False)
    for r in res:
        print(json.dumps(dict(school=r['school'], **r['counts'])))


if __name__ == '__main__':
    main(sys.argv[1:] or SCHOOLS)
