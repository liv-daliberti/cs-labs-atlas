"""One profile per school from its built package: who the computing PIs are, where they sit, what they publish, who
their students are, and how complete each layer is. Read-only over the packages (no network).

inputs   hierarchy/<school>/{pis.json, lab_papers.jsonl.gz, students.json, student_papers.jsonl.gz, report.json,
         copies.json}, census/<school>-additions.json (CS-related-scope additions), hierarchy/home-departments.json,
         hierarchy/missing-papers-audit.json (DBLP reference), hierarchy/zero-paper-labs.json
measures PIs (core computing departments vs CS-related additions), home departments, arrivals and departures in the
         window (reviewed period starts/ends), unique lab papers per year, top venues, students by role, student-paper
         links, labs with the full chain, coverage against the PIs' DBLP pages, local full-text share, and the
         zero-paper / zero-student labs with their recorded reasons
-> hierarchy/school-profiles.json, hierarchy/SCHOOL-PROFILES.md
usage: school_profiles.py
"""
import collections, gzip, importlib.util, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402  (every path in one place)
HERE = P.WORK
H = HERE / 'hierarchy'
import school_config as S  # noqa: E402  (the school charters)
SCHOOLS = list(P.SCHOOL_IDS)
NAMES = S.short_names()
YEARS = list(range(2016, 2027))


def load(p, default=None):
    return json.load(open(p)) if p.exists() else default


SITE_BUILDER = P.vendor('site_builder') / 'build-cs-hierarchy.py'  # vendored from the site build's scripts/ (tools/vendor_sync.py)
_spec = importlib.util.spec_from_file_location('build_cs_hierarchy', SITE_BUILDER)
SITE = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(SITE)


# The entry the site builder's SCHOOLS table will need for Stanford (not added to the site yet, 2026-10-27): the census
# keys departments by these codes; a PI homed elsewhere is placed by hierarchy/home-departments.json.
SITE_FALLBACK = {'stanford': dict(name='Stanford University', uni='stanford-university', full=None,
                                  depts={'CS': 'Computer Science', 'EE': 'Electrical Engineering'})}


def dept(s, p, homes):
    """The PI's department exactly as the site places it (the site builder's own department())."""
    return SITE.department(s, SITE.SCHOOLS.get(s) or SITE_FALLBACK[s], p, homes[s])[0]


def profile(s, homes, audit, zero):
    pis = json.load(open(H / s / 'pis.json'))
    rep = json.load(open(H / s / 'report.json'))['counts']
    adds = {a['name'] for a in load(P.data('census-additions.json', s), []) if 'cs_related' in str(a.get('added'))}
    home = {p['pi']: dept(s, p, homes) for p in pis}
    papers, by_year, venues, per_pi = {}, collections.Counter(), collections.Counter(), collections.Counter()
    for line in gzip.open(H / s / 'lab_papers.jsonl.gz', 'rt'):
        r = json.loads(line)
        per_pi[r['pi']] += 1
        if r['oa'] not in papers:
            papers[r['oa']] = r
            by_year[r.get('year')] += 1
            if r.get('venue'):
                venues[r['venue']] += 1
    S = json.load(open(H / s / 'students.json'))
    people, roles = {}, collections.Counter()
    for pi, rows in S.items():
        for x in rows:
            if x['person'] not in people:
                people[x['person']] = x
                roles[(x.get('roles') or ['unknown'])[0]] += 1
    links = sum(1 for _ in gzip.open(H / s / 'student_papers.jsonl.gz', 'rt'))
    starts = collections.Counter(); ends = collections.Counter()
    for p in pis:
        for q in p.get('periods') or []:
            y0, y1 = str(q.get('start') or '')[:4], str(q.get('end') or '')[:4]
            if y0.isdigit() and 2016 <= int(y0) <= 2026:
                starts[int(y0)] += 1
            if y1.isdigit() and 2016 <= int(y1) <= 2026:
                ends[int(y1)] += 1
    depts = collections.Counter(home.values())
    a = next((x for x in audit if x['school'] == s), {})
    cop = (load(H / s / 'copies.json', {}) or {}).get('summary', {})
    return dict(
        school=s, name=NAMES[s],
        pis=len(pis), pis_core=sum(p['pi'] not in adds for p in pis), pis_cs_related_additions=sum(p['pi'] in adds for p in pis),
        departments=len(depts), top_departments=depts.most_common(12),
        pi_arrivals_by_year={y: starts[y] for y in YEARS}, pi_departures_by_year={y: ends[y] for y in YEARS},
        lab_papers_unique=len(papers), lab_paper_rows=sum(per_pi.values()), lab_papers_by_year={y: by_year[y] for y in YEARS},
        median_papers_per_pi=sorted(per_pi.get(p['pi'], 0) for p in pis)[len(pis) // 2],
        top_venues=venues.most_common(15),
        students_unique=len(people), students_by_first_role=dict(roles.most_common()),
        student_paper_links=links, pis_with_students=rep.get('pis_with_students'), pis_with_lab_papers=rep.get('pis_with_lab_papers'),
        pis_complete_chain=rep.get('pis_complete_chain'),
        dblp_reference=dict(pis_with_dblp=a.get('pis_with_dblp'), published=a.get('published')),
        local_fulltext=dict(lab_papers=cop.get('lab_papers'), local=cop.get('local'), share=cop.get('local_share'), queued=cop.get('queued'),
                            needs_access_review=cop.get('needs_access_review')),
        zero_paper_labs=[dict(pi=r['pi'], verdict=r['verdict'], reason=r['reason']) for r in zero['zero_papers'] if r['school'] == s],
        zero_student_labs=[r['pi'] for r in zero['zero_students'] if r['school'] == s])


def md(P):
    out = [f'# {len(P)} schools: computing PI labs, 2016–2026', '',
           'Built by `tools/school_profiles.py` from the packages in `hierarchy/<school>/`. A PI lab is one faculty PI plus '
           'their advisees; a lab paper has the PI on the byline with the school on that authorship, inside a reviewed '
           'appointment period or a same-year dated faculty listing. Scope (owner, 2026-10-22): every faculty member in '
           'any department who works on CS-related topics or publishes in CS venues.', '',
           '| | ' + ' | '.join(p['name'] for p in P) + ' |', '|---|' + '---|' * len(P)]
    rows = [('PI labs', 'pis'), ('… core computing departments', 'pis_core'), ('… CS-related, other departments', 'pis_cs_related_additions'),
            ('Home departments', 'departments'), ('Unique lab papers', 'lab_papers_unique'), ('Median lab papers per PI', 'median_papers_per_pi'),
            ('Students (unique people)', 'students_unique'), ('Student–paper links', 'student_paper_links'),
            ('Labs with students', 'pis_with_students'), ('Labs with papers', 'pis_with_lab_papers'), ('Labs with papers, students and links', 'pis_complete_chain')]
    for label, k in rows:
        out.append(f'| {label} | ' + ' | '.join(f'{p[k]:,}' if isinstance(p[k], int) else str(p[k]) for p in P) + ' |')
    out.append('| DBLP-published papers we hold | ' + ' | '.join(
        f"{p['dblp_reference']['published']['coverage']:.0%}" if p['dblp_reference'].get('published') else '—' for p in P) + ' |')
    out.append('| Lab papers held locally (full text) | ' + ' | '.join(
        f"{p['local_fulltext']['share']:.0%}" if p['local_fulltext'].get('share') is not None else '—' for p in P) + ' |')
    for p in P:
        out += ['', f"## {p['name']}", '',
                'Home departments: ' + ', '.join(f'{d} ({n})' for d, n in p['top_departments']) + '.', '',
                'Unique lab papers by year: ' + ', '.join(f'{y}: {n:,}' for y, n in p['lab_papers_by_year'].items()) + '.', '',
                'PI arrivals (reviewed period starts) by year: ' + ', '.join(f'{y}: {n}' for y, n in p['pi_arrivals_by_year'].items() if n) + '. '
                'Departures (period ends): ' + ', '.join(f'{y}: {n}' for y, n in p['pi_departures_by_year'].items() if n) + '.', '',
                'Top venues: ' + '; '.join(f'{v} ({n})' for v, n in p['top_venues'][:10]) + '.', '',
                'Students by role: ' + ', '.join(f'{r} {n:,}' for r, n in p['students_by_first_role'].items()) + '.', '']
        if p['zero_paper_labs']:
            out.append('Labs with no lab papers (hidden on the site):')
            out += [f"- {z['pi']}: {z['verdict'].replace('_', ' ')}. {z['reason'] or ''}" for z in p['zero_paper_labs']]
        if p['zero_student_labs']:
            out.append('Labs with no students yet: ' + ', '.join(p['zero_student_labs']) + '.')
    return '\n'.join(out) + '\n'


def main():
    homes = collections.defaultdict(dict)  # the site builder's view: accepted reviewed home departments by school
    for r in json.load(open(H / 'home-departments.json')):
        if r.get('status') == 'accepted' and r.get('home_department'):
            homes[r['school']][r['name']] = r
    audit = load(H / 'missing-papers-audit.json', [])
    zero = json.load(open(H / 'zero-paper-labs.json'))
    P = [profile(s, homes, audit, zero) for s in SCHOOLS]
    json.dump(P, open(H / 'school-profiles.json', 'w'), indent=1, ensure_ascii=False)
    open(H / 'SCHOOL-PROFILES.md', 'w').write(md(P))
    for p in P:
        print(json.dumps({k: p[k] for k in ['school', 'pis', 'pis_cs_related_additions', 'lab_papers_unique', 'students_unique', 'student_paper_links', 'pis_complete_chain']}))


if __name__ == '__main__':
    main()
