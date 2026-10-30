#!/usr/bin/env python3
# Vendored 2026-10-30 from /n/fs/resemble/maxent-grpo/princeton-live-20261015/scripts/build-cs-hierarchy.py (sha256 9a2a4c9bb9ed08420353c8ec80ce4d013a0ce144f935f38239610a359d0c6315); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""CS departments: school -> department -> PI labs -> papers + students, the same way at every school.

Owner decisions 2026-10-21 (AGENTS.md): every faculty PI of a school's computing departments has one own lab (PI +
advisees); centres, initiatives, multi-PI groups and projects are not labs and are not shown here. A lab paper has the
PI on the byline, that authorship lists the school, and it falls in the PI's appointment (a reviewed faculty period,
else a captured department listing from the paper's own year). Students are the PI's stated advisees and the members
of the PI's own unit; a student-paper link is the student's collection authorship of that paper or their name on a
school-affiliated authorship of its byline (kept as a candidate).

Inputs are the per-school packages built by .research-sweeps/claude-schools-20261021/tools/pi_hierarchy.py
(hierarchy/<school>/: pis.json, lab_papers.jsonl.gz, students.json, student_papers.jsonl.gz, report.json) and, when
present, hierarchy/home-departments.json (reviewed home departments of PIs listed by a computing department but homed
elsewhere). Writes atlas/data/cs-hierarchy/<school>.json.gz and atlas/data/cs-hierarchy/index.json.

PI labs with zero lab papers stay in <school>.json.gz but are not shown on either page (owner decision 2026-10-22,
"PI labs with papers only"). Each one's reason is written to atlas/data/cs-hierarchy/hidden-labs.json from the
reviewed ledger hierarchy/zero-paper-labs.json (tools/zero_paper_ledger.py, run after every package rebuild); the
build stops when a zero-paper lab has no ledger row, so a hidden lab always has a recorded reason.

usage: build-cs-hierarchy.py [school ...]      (default: every school with a package)
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import collections, datetime, gzip, json, re, sys
from pathlib import Path

R = P.SITE_ROOT  # vendored: the data root (was parents[1])
D = R / 'atlas/data'; OUT = D / 'cs-hierarchy'
H = P.HIERARCHY  # vendored: was the old sweep link to the same directory
SCHOOLS = {
    'princeton': dict(name='Princeton University', uni='princeton-university', depts={}, full={'Computer Science'}),
    'cmu': dict(name='Carnegie Mellon University', uni='carnegie-mellon-university', full=None, depts={
        'CSD': 'Computer Science Department', 'MLD': 'Machine Learning Department', 'RI': 'Robotics Institute',
        'HCII': 'Human–Computer Interaction Institute', 'LTI': 'Language Technologies Institute',
        'S3D': 'Software and Societal Systems Department', 'CBD': 'Computational Biology Department'}),
    'epfl': dict(name='EPFL', uni='swiss-federal-institute-of-technology-lausanne', full=None,
                 depts={'IC': 'School of Computer and Communication Sciences (IC)'}),
    'mit': dict(name='Massachusetts Institute of Technology', uni='massachusetts-institute-of-technology-mit', full=None,
                depts={'EECS': 'Electrical Engineering and Computer Science'}),
    'berkeley': dict(name='University of California, Berkeley', uni='university-of-california-berkeley', full=None,
                     depts={'EECS': 'Electrical Engineering and Computer Sciences'}),
    # Stanford (owner 2026-10-27): the CS department in full; EE lists only its faculty who publish in CS venues
    # (census/stanford-faculty.json), so EE is a home department that is not covered in full, like other departments.
    'stanford': dict(name='Stanford University', uni='stanford-university', full=None,
                     depts={'CS': 'Computer Science', 'EE': 'Electrical Engineering'}),
}
FULL_CODES = {'stanford': {'CS'}}  # listing codes covered in full where not every listed department is (default: all)
PENDING = 'Home department not yet recorded'
CORE = {'cmu': [(r'Robotics Institute|\bRI\b', 'RI'), (r'Software and Societal|\bS3D\b', 'S3D'), (r'Language Technologies|\bLTI\b', 'LTI'),
                (r'Human.Computer Interaction Institute|\bHCII\b', 'HCII'), (r'Machine Learning Department|\bMLD\b', 'MLD'),
                (r'Computational Biology Department|\bCBD\b', 'CBD'), (r'Computer Science Department|\bCSD\b', 'CSD')],
        'mit': [(r'Electrical Engineering and Computer Science|\bEECS\b', 'EECS')],
        'epfl': [(r'School of Computer and Communication Sciences|\(IC\)', 'IC')],
        'stanford': [(r'^(Department of )?Computer Science$', 'CS')]}


def home_dept(school, cfg, h):
    """A reviewed home department: a computing department by name, else the department as the university writes it."""
    if not h:
        return None
    if h.get('no_academic_department'):
        return f"{h['home_department']} (research staff, no academic department)", 'affiliated'
    for rx, code in CORE.get(school, []):
        if re.search(rx, h['home_department']):
            return cfg['depts'][code], 'full' if code in FULL_CODES.get(school, cfg['depts']) else 'affiliated'
    return h['home_department'], 'affiliated'


def read(p):
    b = Path(p).read_bytes()
    return json.loads(gzip.decompress(b) if str(p).endswith('.gz') else b)


def jsonl(p):
    with gzip.open(p, 'rt') as f:
        return [json.loads(s) for s in f if s.strip()]


def write(p, x):
    p.parent.mkdir(parents=True, exist_ok=True); b = json.dumps(x, ensure_ascii=False, separators=(',', ':')).encode()
    p.write_bytes(gzip.compress(b, mtime=0) if p.suffix == '.gz' else b + b'\n')


STUDENT_ROLES = {'PhD student', 'PhD alumnus', 'Master’s', 'Undergraduate', 'Thesis student', 'Student'}  # the rest: postdocs, staff, visitors


def role_label(roles, relations):
    r = ' '.join(str(x).lower() for x in roles)
    if 'postdoc' in r: return 'Postdoc'
    if 'phd' in r or 'doctoral' in r: return 'PhD alumnus' if 'alumn' in r else 'PhD student'
    if 'master' in r: return 'Master’s'
    if 'undergrad' in r: return 'Undergraduate'
    if any('thesis' in (x.get('type') or '') for x in relations): return 'Thesis student'
    return 'Student' if 'student' in r else 'Lab member'


def department(school, cfg, p, home):
    """(department, coverage): computing departments are covered in full; a PI they list who is homed elsewhere sits in
    their home department, which is not covered in full."""
    if school == 'princeton':
        d = re.sub(r'^Department of ', '', (p['departments'] or ['Computer Science'])[0])
        return d, 'full' if d in cfg['full'] else 'affiliated'
    h = home_dept(school, cfg, home.get(p['pi']))
    if h:
        return h
    codes = [c for c in p['departments'] if c in cfg['depts']]
    if school == 'epfl':
        return (PENDING, 'affiliated') if p.get('rank') == 'affiliated_other_school' else (cfg['depts']['IC'], 'full')
    if school == 'mit' and 'EECS' not in p['departments']:
        return PENDING, 'affiliated'
    if school == 'stanford' and p.get('rank') == 'courtesy':
        return PENDING, 'affiliated'  # a courtesy CS appointment is not a home department; the reviewed one is not recorded
    if codes:
        return cfg['depts'][codes[0]], 'full' if codes[0] in FULL_CODES.get(school, cfg['depts']) else 'affiliated'
    return PENDING, 'affiliated'


LEDGER = H / 'zero-paper-labs.json'
CATEGORIES = {  # tools/zero_paper_ledger.py diagnose(): where the PI's papers dropped out of the lab-paper rule
    'joined_after_window': 'the reviewed appointment starts after every paper so far',
    'no_appointment_coverage': 'papers name the PI and the school, but none falls in a reviewed faculty period or same-year listing',
    'identity_unanchored': 'school-affiliated name hits, none tied to the PI by DBLP, ORCID, a reviewed id, an advisee or a lab page',
    'no_school_affiliation': 'the PI\'s papers exist, but none lists the school',
    'not_in_school_sweep': 'DBLP or the collection knows the PI\'s works, but no 2016-2026 school work carries the name',
    'no_output_found': 'no work at all in 2016-2026 under the PI\'s names',
}


def hidden_labs(order):
    """Every PI lab not shown for having zero lab papers, with its reason from the reviewed ledger."""
    ledger = {(r['school'], r['pi']): r for r in read(LEDGER)['zero_papers']} if LEDGER.exists() else {}
    schools, counts, missing = {}, {}, []
    for s in order:
        x = read(OUT / f'{s}.json.gz'); rows = []
        for i, l in enumerate(x['labs']):
            if l['papers']:
                continue
            r = ledger.get((s, l['pi']['name']))
            if r is None:
                missing.append((s, l['pi']['name'])); continue
            rows.append(dict(id=l['id'], index=i, lab=l['name'], pi=l['pi']['name'], dept=l['dept'], hidden='no_lab_papers',
                             category=r['diagnosis'], verdict=r['verdict'], reason=r.get('reason') or CATEGORIES.get(r['diagnosis'])))
        schools[s] = rows
        counts[s] = dict(shown=len(x['labs']) - len(rows), hidden=len(rows), byCategory=dict(collections.Counter(r['category'] for r in rows)))
    if missing:
        raise SystemExit(f'zero-paper labs without a ledger row (run tools/zero_paper_ledger.py after the package rebuild): {missing}')
    return dict(builtAt=datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z', builtBy='scripts/build-cs-hierarchy.py',
                rule='Owner decision 2026-10-22, "PI labs with papers only": a PI lab with zero lab papers is not shown on the CS atlas '
                     '(index.html) or as a lab on cs-departments.html. Its record stays in <school>.json.gz; this file records why it has none.',
                source='.research-sweeps/claude-schools-20261021/hierarchy/zero-paper-labs.json (tools/zero_paper_ledger.py: diagnosis from '
                       'the PI\'s funnel in pis.json; verdict and reason from the reviewed zero-paper-review.json)',
                categories=CATEGORIES, counts=counts, schools=schools)


def build(school):
    cfg = SCHOOLS[school]; src = H / school
    pis = read(src / 'pis.json'); rep = read(src / 'report.json')
    rows = jsonl(src / 'lab_papers.jsonl.gz'); stu = read(src / 'students.json'); sp = jsonl(src / 'student_papers.jsonl.gz')
    home = {}
    if (H / 'home-departments.json').exists():
        home = {x['name']: x for x in read(H / 'home-departments.json')
                if x.get('school') == school and x.get('status') == 'accepted' and x.get('home_department')}
    gapnote = {}  # the gap research's finding for a lab still missing papers or students (hierarchy/<school>/gap-evidence.json)
    if (H / school / 'gap-evidence.json').exists():
        gapnote = {r['pi']: (r.get('notes') or '')[:400] for r in read(H / school / 'gap-evidence.json') if r.get('status') == 'pi'}
    site_labs = set()
    if (D / f"universities/{cfg['uni']}.json.gz").exists():
        site_labs = {l['id'] for l in read(D / f"universities/{cfg['uni']}.json.gz")['labs']}
    canon = {}
    if (D / f'collection-{school}.json.gz').exists():
        canon = {u['id']: u.get('canonicalId') or u['id'] for u in read(D / f'collection-{school}.json.gz')['units']}
    papers, pidx = [], {}
    students, sidx = [], {}
    labs = []
    by_pi = collections.defaultdict(list)
    for r in rows:
        by_pi[r['pi']].append(r)
    links = collections.defaultdict(list)
    for x in sp:
        links[x['pi']].append(x)
    for p in pis:
        dept, cov = department(school, cfg, p, home)
        lab = p['lab']; unit = lab.get('unitId'); site = canon.get(unit, unit) if unit else None
        mine = []
        for r in sorted(by_pi[p['pi']], key=lambda r: (r.get('date') or '', r.get('title') or '')):
            k = r['work'] or r['oa']
            if k not in pidx:
                pidx[k] = len(papers)
                papers.append(dict(t=r['title'], y=r['year'], d=r.get('date'), v=r.get('venue'), doi=r.get('doi') or None, u=r.get('landing'),
                                   oa=r['oa'], w=r['work'], b=(r.get('byline') or [])[:25], nb=len(r.get('byline') or [])))
            ap = r['appointment']
            mine.append([pidx[k], r['identity'], 'P' if 'periodId' in ap else 'L' + str(ap['listing']['year']), r.get('date')])  # the edition date the appointment was proven with
        sl = []
        for s in stu.get(p['pi'], []):
            if s['person'] not in sidx:
                sidx[s['person']] = len(students)
                students.append(dict(n=s['name'], id=s['person'], r=role_label(s.get('roles') or [], s['relations'])))
            yrs = sorted({y for rel in s['relations'] for y in rel.get('years') or [] if isinstance(y, int)})
            src0 = next((z for rel in s['relations'] for z in rel.get('sources') or [] if z.get('url')), {})
            sl.append([sidx[s['person']], 'member' if all(rel['type'] == 'direct_lab_membership' for rel in s['relations']) else 'advisee',
                       [yrs[0], yrs[-1]] if yrs else None, src0.get('url'), (src0.get('quote') or '')[:240]])
        lk = []
        for x in links[p['pi']]:
            k = x['work'] or x['oa']
            if k in pidx and x['student'] in sidx:
                lk.append([sidx[x['student']], pidx[k], 'v' if x['status'] == 'verified' else 'c', x['basis']])
        labs.append(dict(
            id=unit or f"{school}-pi-lab-{re.sub('[^a-z0-9]+', '-', p['pi'].lower()).strip('-')}", name=lab.get('name') or f"{p['pi']} group",
            url=lab.get('url'), siteLab=site if site in site_labs else None, labBasis=lab.get('basis'),
            pi=dict(name=p['pi'], ids=p['personIds'], rank=p.get('rank'), title=p.get('title'), dblp=p.get('dblp') or [], oa=p.get('oaAuthorIds', [])[:3],
                    basis=p.get('piBasis') if isinstance(p.get('piBasis'), dict) else None, merged=p.get('mergedCensusRows') or []),
            dept=dept, coverage=cov, otherDepts=[x for x in dict.fromkeys(re.sub(r'^Department of ', '', cfg['depts'].get(c, c)) for c in p['departments']) if x != dept]
                                                 if school not in ('epfl', 'mit') else [],
            periods=[dict(start=q['start'], end=q['end'], asof=q['asof'], ev=[dict(url=e.get('url'), quote=(e.get('quote') or '')[:300]) for e in q.get('evidence') or []][:2])
                     for q in p['periods']],
            listings=[dict(y=l['year'], url=l['url'], quote=l['quote'][:300], kind=l.get('kind')) for l in p['listings']],
            papers=mine, students=sl, links=lk,
            gapNote=gapnote.get(p['pi']) if (not mine or not sl) and gapnote.get(p['pi']) else None))
    depts = collections.OrderedDict()
    for i, l in enumerate(labs):
        d = depts.setdefault(l['dept'], dict(name=l['dept'], coverage=l['coverage'], labs=[]))
        d['labs'].append(i)
        if l['coverage'] == 'full':
            d['coverage'] = 'full'
    order = sorted(depts.values(), key=lambda d: (d['coverage'] != 'full', d['name'] == PENDING, -len(d['labs']), d['name']))
    n = dict(departments=len(order), departmentsFull=sum(d['coverage'] == 'full' for d in order), labs=len(labs),
             labsWithPapers=sum(bool(l['papers']) for l in labs), labsWithStudents=sum(bool(l['students']) for l in labs),
             labsComplete=sum(bool(l['papers'] and l['students'] and l['links']) for l in labs),
             papers=len(papers), people=len(students), students=sum(st['r'] in STUDENT_ROLES for st in students),
             members=sum(st['r'] not in STUDENT_ROLES for st in students), studentPaperLinks=sum(len(l['links']) for l in labs))
    data = dict(school=dict(id=school, name=cfg['name'], uni=cfg['uni']), builtAt=datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z',
                packageBuiltAt=rep.get('builtAt'), counts=n, buildCounts=rep.get('counts'), departments=order, labs=labs, papers=papers, students=students)
    write(OUT / f'{school}.json.gz', data)
    return dict(id=school, name=cfg['name'], uni=cfg['uni'], counts=n, departments=[dict(name=d['name'], coverage=d['coverage'], labs=len(d['labs'])) for d in order])


if __name__ == '__main__':
    schools = sys.argv[1:] or [s for s in SCHOOLS if (H / s / 'pis.json').exists()]
    idx_p = OUT / 'index.json'
    idx = {x['id']: x for x in (read(idx_p)['schools'] if idx_p.exists() else [])}
    for s in schools:
        idx[s] = build(s); print(json.dumps(dict(school=s, **idx[s]['counts'])))
    order = [s for s in SCHOOLS if s in idx]
    import csv, io
    out = io.StringIO(); w = csv.writer(out)
    w.writerow(['school', 'department', 'department_coverage', 'lab', 'pi', 'pi_title', 'lab_papers', 'papers_by_faculty_period', 'papers_by_same_year_listing',
                'students', 'student_paper_links', 'verified_student_paper_links', 'listing_years', 'faculty_periods', 'site_lab_id', 'rule'])
    for s in order:
        x = read(OUT / f'{s}.json.gz')
        for l in x['labs']:
            w.writerow([x['school']['name'], l['dept'], l['coverage'], l['name'], l['pi']['name'], l['pi'].get('title') or '', len(l['papers']),
                        sum(p[2] == 'P' for p in l['papers']), sum(p[2] != 'P' for p in l['papers']), len(l['students']), len(l['links']),
                        sum(k[2] == 'v' for k in l['links']), ' '.join(str(y['y']) for y in l['listings']),
                        '; '.join(f"{q['start']}-{q['end'] or 'present'}" for q in l['periods']), l.get('siteLab') or '',
                        'PI on byline + school affiliation on that authorship + faculty period or same-year department listing'])
    (R / 'atlas/downloads/cs-hierarchy-labs.csv').write_text(out.getvalue())
    hidden = hidden_labs(order)
    write(OUT / 'hidden-labs.json', hidden)
    for s in order:
        idx[s]['hiddenLabs'] = hidden['counts'][s]['hidden']
        print(json.dumps(dict(school=s, **hidden['counts'][s]), ensure_ascii=False))
    write(idx_p, dict(builtAt=datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z', pending=[s for s in SCHOOLS if s not in idx],
                      rule='Owner decisions 2026-10-21: school → department → PI labs → papers + students; centres and multi-PI groups are not labs. '
                           'PI labs without lab papers are not shown (2026-10-22); hiddenLabsFile records why.',
                      hiddenLabsFile='data/cs-hierarchy/hidden-labs.json', schools=[idx[s] for s in order]))
