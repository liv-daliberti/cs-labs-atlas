"""Per-lab coverage of a protocol school: every lab needs students, a PI identity and papers, or a recorded evidence-backed reason (owner rule
2026-11-03, docs/DECISIONS.md).

For each PI of hierarchy/<key>/pis.json: the number of students and where they come from (students.json relations), the number of lab papers,
and, when either is 0, a reason code with its evidence. Reasons come from two places:
  derived    from the census row, quoted: `no_phd_advising_role` (teaching-track or lecturer title), `research_only_appointment` (research title),
             `emeritus_throughout` (every listed year emeritus), `new_hire_2025_or_later` (first listed year 2025+), `appointment_ended_early`
             (last listed year before 2019 and no student or paper after), `no_identity` (reviewed no_identity override)
  reviewed   hierarchy/<key>/reviewed/lab-coverage-reasons.json {pi: {students|papers: {code, why, sources_checked?}}}, for the codes a hand
             search establishes (`sources_exhausted` lists every source checked; `all_students_before_2016`)
A lab at 0 students or 0 papers with neither is `open`. -> hierarchy/<key>/reports/LAB-COVERAGE.md and .json in this checkout.
usage: lab_coverage.py <key>
"""
import collections, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # python -I leaves the script's directory off sys.path
import atlas_paths as P  # noqa: E402
import census_overrides as CO  # noqa: E402

CODE = Path(__file__).resolve().parents[1]


def read(p, default=None):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else default


def student_sources(rels):
    """'adviser list', 'lab page', 'roster+co-author', 'thesis/other' counts of one lab's student relations."""
    c = collections.Counter()
    for s in rels:
        kinds = set()
        for r in s.get('relations') or []:
            for src in r.get('sources') or []:
                q, u = src.get('quote') or '', src.get('url') or ''
                if 'PhD roster' in (r.get('section') or '') or r.get('years_basis') == 'roster_years':
                    kinds.add('roster+co-author')
                elif 'ttic.edu/students' in u or 'ttic.edu/student-alumni' in u or re.search(r'Advisors?\s*[:-]', q):
                    kinds.add('adviser list')
                else:
                    kinds.add('lab page')
        c[sorted(kinds)[0] if kinds else 'other'] += 1
    return dict(c)


def derived_reason(kind, p, cen, ov):
    """(code, why, evidence quote) from the census row, or None."""
    title = (cen.get('title_as_listed') or p.get('title') or '').strip()
    ys = sorted(cen.get('years_listed') or [])
    rby = cen.get('ranks_by_year') or {}
    allr = [set(v if isinstance(v, list) else [v]) for v in rby.values()]
    if (ov.get('no_identity') and ov.get('why_no_identity')) and kind == 'papers':
        return 'no_identity', ov['why_no_identity'], title
    if re.search(r'emerit', title, re.I) and allr and all('emeritus' in r or 'adjunct' in r for r in allr) and ys and ys[0] <= 2016:
        return 'emeritus_throughout', f"every listed year {ys[0]}-{ys[-1]} reads emeritus; no advising or new papers expected", title
    if kind == 'students' and cen.get('rank') in ('teaching', 'lecturer') and not any('ladder' in r for r in allr):
        return 'no_phd_advising_role', 'teaching-track or lecturer title in every listed year', title
    if kind == 'students' and cen.get('rank') == 'research' and not any('ladder' in r for r in allr):
        return 'research_only_appointment', 'research-faculty title in every listed year', title
    if ys and ys[0] >= 2025:
        return 'new_hire_2025_or_later', f'first listed {ys[0]} ({title}); no students or UChicago papers yet', title
    if ys and ys[-1] <= 2018:
        return 'appointment_ended_early', f'last listed {ys[-1]}; the appointment at the school ends before the papers can accrue (R-PAP-01)', title
    return None


def lab_rows(key):
    """One dict per lab (see the module docstring): pi, department, title, students, student_sources, papers, reasons {students|papers: {code, why, ...}}."""
    pis = read(P.data('pis.json', key), [])
    stu = read(P.data('students.json', key), {})
    cen = {x['name']: x for x in read(P.data('census-faculty.json', key), {}).get('faculty', [])}
    cen.update({x['name']: x for x in read(P.data('census-additions.json', key), [])})
    ov = CO.section(key)
    manual = read(P.data('lab-coverage-reasons.json', key), {}) or {}
    rows = []
    for p in pis:
        nm = p['pi']; c = cen.get(nm) or {}
        ns, npap = p['counts']['students'], p['counts']['labPapers']
        row = dict(pi=nm, department=(p.get('departments') or [None])[0], title=(p.get('title') or '')[:80], students=ns,
                   student_sources=student_sources(stu.get(nm) or []), papers=npap, reasons={})
        for kind, n in (('students', ns), ('papers', npap)):
            if n:
                continue
            m = (manual.get(nm) or {}).get(kind)
            d = derived_reason(kind, p, c, ov.get(nm) or {})
            if m:
                row['reasons'][kind] = dict(code=m['code'], why=m['why'], sources_checked=m.get('sources_checked'), by='review')
            elif d:
                row['reasons'][kind] = dict(code=d[0], why=d[1], quote=d[2], by='census')
            else:
                row['reasons'][kind] = dict(code='open', why='no recorded reason yet')
        rows.append(row)
    return rows


def main(key):
    rows = lab_rows(key)
    out = CODE / 'hierarchy' / key / 'reports'
    out.mkdir(parents=True, exist_ok=True)
    summ = dict(labs=len(rows), with_students=sum(1 for r in rows if r['students']), with_papers=sum(1 for r in rows if r['papers']),
                students_reasoned=collections.Counter(r['reasons']['students']['code'] for r in rows if 'students' in r['reasons']),
                papers_reasoned=collections.Counter(r['reasons']['papers']['code'] for r in rows if 'papers' in r['reasons']),
                papers_per_lab_median=sorted(r['papers'] for r in rows)[len(rows) // 2] if rows else 0)
    (out / 'LAB-COVERAGE.json').write_text(json.dumps(dict(school=key, summary=summ, labs=rows), indent=1, ensure_ascii=False, default=dict) + '\n')
    L = [f'# {key}: lab coverage (students, papers, reasons)', '',
         f"Labs {summ['labs']}; with students {summ['with_students']}; with papers {summ['with_papers']}; median papers per lab {summ['papers_per_lab_median']}.", '',
         f"Reasons for 0 students: {dict(summ['students_reasoned'])}. Reasons for 0 papers: {dict(summ['papers_reasoned'])}.", '',
         '| PI | dept | students | sources | papers | reason (students) | reason (papers) |', '|---|---|---|---|---|---|---|']
    for r in sorted(rows, key=lambda r: (r['students'] > 0 and r['papers'] > 0, r['pi'])):
        rs = r['reasons']
        L.append(f"| {r['pi']} | {r['department']} | {r['students']} | {', '.join(f'{k} {v}' for k, v in r['student_sources'].items()) or '-'} | {r['papers']} | "
                 f"{rs.get('students', {}).get('code', '')} | {rs.get('papers', {}).get('code', '')} |")
    (out / 'LAB-COVERAGE.md').write_text('\n'.join(L) + '\n')
    print(json.dumps({k: (dict(v) if isinstance(v, collections.Counter) else v) for k, v in summ.items()}))


if __name__ == '__main__':
    main(sys.argv[1])
