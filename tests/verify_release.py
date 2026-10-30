#!/usr/bin/env python3
"""Verify a release of this repository: counts, ids, joins, departments, file sizes and privacy.

Self-contained (standard library only); reads nothing outside the repository.
  counts     per school: PIs, students, lab-student pairs, lab-paper rows and student-paper links equal the build report
             (data/schools/<school>/build_report.json) and the school profile (data/schools/profiles.json); unique papers
             equal the profile's count plus papers split off a shared OpenAlex record (field openalex_shared_with)
  ids        no duplicate pi_id, paper_id, student_id, (pi_id, paper_id) lab entry, (pi_id, student_id) advising entry or
             (pi_id, student_id, paper_id) link; atlas: no duplicate university, unit or work id
  joins      every lab entry, advisor, student-paper link and CSV row resolves to rows of pis / papers / students, and a
             student-paper link's paper lists that PI and its student lists that PI as advisor; atlas unit papers, people
             and person papers resolve to units (and works where the work is in the works table)
  atlas ids  every PI, student, paper and link carries its atlas ids (atl:p: person, atl:w: work, atl:l: lab); no two PIs
             of one school share a lab id; a link's atlas ids match its PI, student and paper; every atlas id is in
             data/ids/crossref.tsv.gz; the people at two schools have an appointment row at each
  department every PI has a department (the site's placeholder 'Home department not yet recorded' is reported)
  files      every file is under 50 MB
  privacy    no e-mail address in any data file; the owner's address nowhere in the repository
usage: python3 tests/verify_release.py [repo dir]      exit status 1 when a check fails
"""
import collections, csv, gzip, hashlib, json, re, sys
from pathlib import Path

REPO = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]).resolve()
FAIL, WARN, INFO = [], [], []
PENDING = 'Home department not yet recorded'
IDS_SEEN = set()
EMAIL = re.compile(r'(?<![\w.%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b')
OWNER_SHA256 = '3d295a08f3a63465645d9d4e99fbe34f11aa0622bbf29a754e0b23cb4263aacf'  # sha256 of the owner's address (not stored in clear)


def check(ok, msg):
    (INFO if ok else FAIL).append(('ok   ' if ok else 'FAIL ') + msg)


def rows(rel):
    """A JSONL table: one .jsonl.gz file or a directory of shards with that name."""
    p = REPO / rel
    files = [p] if p.exists() else sorted((REPO / rel[:-len('.jsonl.gz')]).glob('*.jsonl.gz'))
    out = []
    for f in files:
        with gzip.open(f, 'rt', encoding='utf-8') as fh:
            out += [json.loads(l) for l in fh if l.strip()]
    return out


def csv_rows(rel):
    with open(REPO / rel, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def dup(values):
    return [k for k, v in collections.Counter(values).items() if v > 1]


def school(s, prof):
    d = f'data/schools/{s}'
    P, A, S, L = rows(f'{d}/pis.jsonl.gz'), rows(f'{d}/papers.jsonl.gz'), rows(f'{d}/students.jsonl.gz'), rows(f'{d}/student_papers.jsonl.gz')
    rep = json.loads((REPO / d / 'build_report.json').read_text())['counts']
    lab_rows = sum(len(x['labs']) for x in A); pairs = sum(len(x['advisors']) for x in S); split = sum(bool(x.get('openalex_shared_with')) for x in A)
    for name, got, want in [('PIs', len(P), rep['pis']), ('PIs (profile)', len(P), prof['pis']),
                            ('students', len(S), rep['students']), ('students (profile)', len(S), prof['students_unique']),
                            ('lab-student pairs', pairs, rep['lab_student_pairs']),
                            ('lab-paper rows', lab_rows, rep['lab_papers']), ('lab-paper rows (profile)', lab_rows, prof['lab_paper_rows']),
                            ('unique papers - split', len(A) - split, prof['lab_papers_unique']),
                            ('student-paper links', len(L), rep['student_paper_links']), ('student-paper links (profile)', len(L), prof['student_paper_links']),
                            ('labs with papers', sum(p['counts'].get('labPapers', 0) > 0 for p in P), rep['pis_with_lab_papers'])]:
        check(got == want, f'{s}: {name} {got} == {want}')
    if split:
        INFO.append(f'note {s}: {split} papers split off a shared OpenAlex record (distinct DOIs DOI-resolved to one OpenAlex work)')
    pi = {p['pi_id']: p for p in P}; pa = {x['paper_id']: x for x in A}; st = {x['student_id']: x for x in S}
    for name, vals in [('pi_id', [p['pi_id'] for p in P]), ('paper_id', [x['paper_id'] for x in A]), ('student_id', [x['student_id'] for x in S]),
                       ('lab entry', [(l['pi_id'], x['paper_id']) for x in A for l in x['labs']]),
                       ('advising entry', [(a['pi_id'], x['student_id']) for x in S for a in x['advisors']]),
                       ('student-paper link', [(r['pi_id'], r['student_id'], r['paper_id']) for r in L]), ('lab_id', [p['lab']['lab_id'] for p in P])]:
        d_ = dup(vals); check(not d_, f'{s}: no duplicate {name}' + (f' ({len(d_)}: {d_[:3]})' if d_ else ''))
    bad = [l['pi_id'] for x in A for l in x['labs'] if l['pi_id'] not in pi]
    check(not bad, f'{s}: every lab entry names a PI ({len(bad)} bad)')
    bad = [a['pi_id'] for x in S for a in x['advisors'] if a['pi_id'] not in pi]
    check(not bad, f'{s}: every advisor is a PI ({len(bad)} bad)')
    labs_of = {x['paper_id']: {l['pi_id'] for l in x['labs']} for x in A}
    advs_of = {x['student_id']: {a['pi_id'] for a in x['advisors']} for x in S}
    bad = [r for r in L if r['pi_id'] not in pi or r['paper_id'] not in pa or r['student_id'] not in st
           or r['pi_id'] not in labs_of[r['paper_id']] or r['pi_id'] not in advs_of[r['student_id']]]
    check(not bad, f'{s}: every student-paper link resolves (PI, paper with that lab, student with that advisor) ({len(bad)} bad: {bad[:2]})')
    per = collections.Counter(l['pi_id'] for x in A for l in x['labs'])
    bad = [p['pi_id'] for p in P if per[p['pi_id']] != p['counts'].get('labPapers', 0)]
    check(not bad, f"{s}: each PI's counts.labPapers equals its lab entries ({len(bad)} differ: {bad[:3]})")
    nodept = [p['pi_id'] for p in P if not p.get('department')]
    check(not nodept, f'{s}: every PI has a department ({len(nodept)} without)')
    pend = [p['pi_id'] for p in P if p.get('department') == PENDING]
    (WARN if pend else INFO).append(f"{'WARN' if pend else 'ok  '} {s}: PIs with the site placeholder department: {len(pend)} {pend[:5]}")
    c1, c2, c3, c4 = csv_rows(f'{d}/lab_papers.csv'), csv_rows(f'{d}/lab_students.csv'), csv_rows(f'{d}/student_papers.csv'), csv_rows(f'{d}/pis.csv')
    check(len(c1) == lab_rows and all(r['pi_id'] in pi and r['paper_id'] in pa for r in c1), f'{s}: lab_papers.csv {len(c1)} rows resolve')
    check(len(c2) == pairs and all(r['pi_id'] in pi and r['student_id'] in st for r in c2), f'{s}: lab_students.csv {len(c2)} rows resolve')
    check(len(c3) == len(L) and all(r['pi_id'] in pi and r['paper_id'] in pa and r['student_id'] in st for r in c3), f'{s}: student_papers.csv {len(c3)} rows resolve')
    check(len(c4) == len(P), f'{s}: pis.csv {len(c4)} rows')
    # atlas ids (docs/IDS.md in the code)
    if any('atlas_id' in p for p in P):
        bad = [p['pi_id'] for p in P if not str(p.get('atlas_id')).startswith('atl:p:') or not str(p.get('atlas_lab_id')).startswith('atl:l:')]
        check(not bad, f'{s}: every PI has an atlas person id and lab id ({len(bad)} without: {bad[:3]})')
        d_ = dup([p['atlas_lab_id'] for p in P]); check(not d_, f'{s}: no duplicate atlas_lab_id ({d_[:3]})')
        bad = [p['pi_id'] for p in P if s not in {a['school'] for a in p.get('appointments') or []}]
        check(not bad, f'{s}: every PI lists its own appointment ({len(bad)} bad: {bad[:3]})')
        bad = [x['paper_id'] for x in A if not str(x.get('atlas_work_id')).startswith('atl:w:')]
        check(not bad, f'{s}: every paper has an atlas work id ({len(bad)} without: {bad[:3]})')
        bad = [x['student_id'] for x in S if not x.get('atlas_ids') or not all(str(a.get('atlas_id')).startswith('atl:p:') for a in x['advisors'])]
        check(not bad, f'{s}: every student and advisor entry has an atlas person id ({len(bad)} without: {bad[:3]})')
        lab_of = {p['pi_id']: p['atlas_lab_id'] for p in P}
        adv_atlas = {(x['student_id'], a['pi_id']): a['atlas_id'] for x in S for a in x['advisors']}
        bad = [r for r in L if r.get('atlas_lab_id') != lab_of.get(r['pi_id']) or r.get('student_atlas_id') != adv_atlas.get((r['student_id'], r['pi_id']))
               or (r.get('atlas_work_id') not in {pa[r['paper_id']].get('atlas_work_id')} | set(pa[r['paper_id']].get('atlas_work_ids_also') or []))]
        check(not bad, f"{s}: every student-paper link's atlas ids match its lab, student and paper ({len(bad)} bad: {bad[:2]})")
        IDS_SEEN.update(p['atlas_id'] for p in P); IDS_SEEN.update(p['atlas_lab_id'] for p in P)
        IDS_SEEN.update(a['atlas_id'] for x in S for a in x['advisors']); IDS_SEEN.update(x['atlas_work_id'] for x in A)
    return dict(pis=len(P), papers=len(A), lab_rows=lab_rows, students=len(S), pairs=pairs, links=len(L))


def atlas():
    d = 'data/atlas'
    U, N, W = rows(f'{d}/universities.jsonl.gz'), rows(f'{d}/units.jsonl.gz'), rows(f'{d}/works.jsonl.gz')
    UP, PE, PW, G = rows(f'{d}/unit_papers.jsonl.gz'), rows(f'{d}/unit_people.jsonl.gz'), rows(f'{d}/unit_person_papers.jsonl.gz'), rows(f'{d}/pi_identities.jsonl.gz')
    for name, vals in [('university_id', [u['university_id'] for u in U]), ('unit_id', [u['unit_id'] for u in N]), ('work_id', [w['work_id'] for w in W]),
                       ('unit paper', [(r['unit_id'], r['work_id']) for r in UP]), ('unit person', [(r['unit_id'], r['person_id']) for r in PE]),
                       ('pi identity group_id', [g['group_id'] for g in G])]:
        d_ = dup(vals); check(not d_, f'atlas: no duplicate {name}' + (f' ({len(d_)}: {d_[:3]})' if d_ else ''))
    uids = {u['university_id'] for u in U}; units = {u['unit_id'] for u in N}; works = {w['work_id'] for w in W}
    check(all(u['university_id'] in uids for u in N), f'atlas: every unit ({len(N)}) names a university ({len(U)})')
    check(all(r['unit_id'] in units and r['work_id'] in works for r in UP), f'atlas: every unit paper ({len(UP)}) resolves to a unit and a work ({len(W)})')
    nounit = [r['unit_id'] for r in PE if r['unit_id'] not in units]
    (WARN if nounit else INFO).append(f"{'WARN' if nounit else 'ok  '} atlas: unit people ({len(PE)}) whose unit is not in units: {len(set(nounit))} units {sorted(set(nounit))[:3]}")
    people = {(r['unit_id'], r['person_id']) for r in PE}
    check(all((r['unit_id'], r['person_id']) in people for r in PW), f'atlas: every unit person paper ({len(PW)}) resolves to a unit person')
    inw = sum(r['work_id'] in works for r in PW)
    INFO.append(f'note atlas: {inw} of {len(PW)} person papers are also unit works; the rest are researcher-linked works (title/DOI inline)')
    nolab = [g['lab_id'] for g in G if g.get('lab_id') not in units]
    (WARN if nolab else INFO).append(f"{'WARN' if nolab else 'ok  '} atlas: PI identities ({len(G)}) whose lab_id is not a unit: {len(nolab)}")
    return dict(universities=len(U), units=len(N), works=len(W), unit_papers=len(UP), unit_people=len(PE), unit_person_papers=len(PW), pi_identities=len(G))


def files_and_privacy():
    big, owner, emails, total = [], [], collections.Counter(), 0
    for f in sorted(REPO.rglob('*')):
        if '.git' in f.relative_to(REPO).parts or not f.is_file():
            continue
        n = f.stat().st_size; total += n
        if n >= 50 * 1024 * 1024:
            big.append(str(f.relative_to(REPO)))
        b = f.read_bytes()
        if f.suffix == '.gz':
            b = gzip.decompress(b)
        t = b.decode('utf-8', 'replace')
        found = EMAIL.findall(t) if '@' in t else []
        if any(hashlib.sha256(m.lower().encode()).hexdigest() == OWNER_SHA256 for m in found):
            owner.append(str(f.relative_to(REPO)))
        if f.relative_to(REPO).parts[0] == 'data':
            for m in found:
                if not m.lower().endswith('@example.org') and '@lists.' not in m.lower():  # mailing lists are not personal
                    emails[str(f.relative_to(REPO))] += 1
    check(not big, f'every file under 50 MB ({len(big)} over: {big})')
    check(not owner, f"the owner's e-mail address appears nowhere ({owner})")
    check(not emails, f'no e-mail address in data files ({dict(emails)})')
    INFO.append(f'note repository size without .git: {total / 1e6:.1f} MB')


def main():
    prof = {p['school']: p for p in json.loads((REPO / 'data/schools/profiles.json').read_text())}
    schools = sorted(p.name for p in (REPO / 'data/schools').iterdir() if p.is_dir())
    for s in schools:
        if s not in prof:
            FAIL.append(f'FAIL {s}: no profile in data/schools/profiles.json'); continue
        school(s, prof[s])
    if (REPO / 'data/atlas').exists():
        atlas()
    if IDS_SEEN and (REPO / 'data/ids/crossref.tsv.gz').exists():
        xr = list(csv.DictReader(gzip.open(REPO / 'data/ids/crossref.tsv.gz', 'rt', encoding='utf-8'), delimiter='\t'))
        known = {r['atlas_id'] for r in xr}
        miss = sorted(IDS_SEEN - known)
        check(not miss, f'every atlas id in the school data is in data/ids/crossref.tsv.gz ({len(miss)} missing: {miss[:3]})')
        INFO.append(f'note crossref: {len(xr)} rows, {len(known)} atlas ids, schemes {dict(collections.Counter(r["scheme"] for r in xr))}')
        cross = json.loads((REPO / 'data/ids/persons_cross_school.json').read_text())['persons']
        pis_by = {}
        for s in schools:
            for p in rows(f'data/schools/{s}/pis.jsonl.gz'):
                pis_by[p['atlas_lab_id']] = p['atlas_id']
        bad = [c['atlasId'] for c in cross if any(pis_by.get(a['labId']) not in (c['atlasId'], None) for a in c['appointments'])]
        check(not bad, f'people at two schools: every appointment lab belongs to that person ({len(cross)} people, {len(bad)} bad)')
    elif IDS_SEEN:
        FAIL.append('FAIL data/ids/crossref.tsv.gz is missing')
    files_and_privacy()
    for m in INFO + WARN + FAIL:
        print(m)
    print(f'\n{len(FAIL)} failed, {len(WARN)} warnings, {len(INFO)} passed/notes')
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
