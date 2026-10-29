"""The build-time evidence check (2026-10-29, owner): every claim in the built packages carries its evidence.

Checked per school, in hierarchy/<school>/ (or --dir <root>/<school>/):
  pi_period              a PI appointment period (pis.json periods) with no evidence item that has url, sha256 and quote
  faculty_listing        a dated department listing (pis.json listings) without url, sha256 and quote
  student_relation       a student relation (students.json relations) with no source that has url, sha256 and quote
  student_relation_student_only  (2026-10-29) a student relation whose only sourced evidence is a re-captured page that names
                         the student but not the PI or the PI's lab (source names_pi false; tools/relation_recapture.py,
                         R-STU-08): the hash and quote are real, the adviser rests on the collection's advising context
  student_no_relation    a student record with no relation at all
  paper_school_basis     a lab paper without its school basis (authorship.school_via)
  paper_appointment      a lab paper whose appointment is neither a periodId of one of the PI's periods with evidence, nor
                         a listing with url, sha256 and quote
  link_byline            a student-paper link whose basis is a byline match (within_lab_byline_match,
                         byline_name_with_school_affiliation, advisee_name_on_lab_paper_byline, full_name_on_lab_paper_byline)
                         without the work id and the exact byline string matched
  link_relation_source   such a link without the student's own roster source (relation_source: url, sha256, quote)
  link_relation_source_student_only  (2026-10-29) such a link whose roster source is a re-captured student-only quote

A sha256 must be 64 hex digits; a quote must be non-empty text. Whitelisted categories (docs/evidence-whitelist.json:
{category: {school: {"max": n, "why": "..."}}}) pass up to their count; anything over it, or not listed, fails.
-> hierarchy/EVIDENCE-CHECK.json (counts, samples) and hierarchy/EVIDENCE-CHECK.md
usage: evidence_check.py [--report] [--dir <root>] [school ...]      exit 0 clean (or --report), 1 violations over the whitelist
"""
import argparse, collections, gzip, json, re, sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402  (every path in one place)

BYLINE_BASES = {'within_lab_byline_match', 'byline_name_with_school_affiliation', 'advisee_name_on_lab_paper_byline', 'full_name_on_lab_paper_byline'}
CATEGORIES = ['pi_period', 'faculty_listing', 'student_relation', 'student_relation_student_only', 'student_no_relation', 'paper_school_basis', 'paper_appointment',
              'link_byline', 'link_relation_source', 'link_relation_source_student_only']
WHITELIST = P.WORK / 'docs' / 'evidence-whitelist.json'
SHA = re.compile(r'^[0-9a-f]{64}$')


def sourced(e):
    return isinstance(e, dict) and bool(e.get('url')) and bool(SHA.match(str(e.get('sha256') or ''))) and bool(str(e.get('quote') or '').strip())


def load(p):
    p = Path(p)
    if str(p).endswith('.jsonl.gz'):
        return [json.loads(l) for l in gzip.open(p, 'rt')]
    return json.loads(p.read_text())


def check(school, root):
    D = Path(root) / school
    pis = load(D / 'pis.json'); students = load(D / 'students.json')
    papers = load(D / 'lab_papers.jsonl.gz'); links = load(D / 'student_papers.jsonl.gz')
    bad = collections.defaultdict(list); total = collections.Counter()

    def flag(cat, key):
        bad[cat].append(key)

    period_ok = {}
    for p in pis:
        for q in p.get('periods') or []:
            total['pi_period'] += 1
            ok = any(sourced(e) for e in q.get('evidence') or [])
            period_ok[(p['pi'], q.get('id'))] = ok
            if not ok:
                flag('pi_period', f"{p['pi']} | {q.get('id')} | {q.get('start')}-{q.get('end')}")
        for l in p.get('listings') or []:
            total['faculty_listing'] += 1
            if not sourced(l):
                flag('faculty_listing', f"{p['pi']} | {l.get('year')} | {l.get('url')}")
    for pi, recs in students.items():
        for s in recs:
            rels = s.get('relations') or []
            total['student_no_relation'] += 1
            if not rels:
                flag('student_no_relation', f"{pi} | {s.get('person')} | {s.get('name')}")
            for rel in rels:
                total['student_relation'] += 1
                total['student_relation_student_only'] += 1
                if not any(sourced(q) for q in rel.get('sources') or []):
                    flag('student_relation', f"{pi} | {s.get('person')} | {s.get('name')} | {rel.get('type')}")
                elif not any(sourced(q) and q.get('names_pi') is not False for q in rel.get('sources') or []):
                    flag('student_relation_student_only', f"{pi} | {s.get('person')} | {s.get('name')} | {rel.get('type')}")
    for r in papers:
        key = f"{r['pi']} | {r.get('oa')}"
        total['paper_school_basis'] += 1; total['paper_appointment'] += 1
        if not (r.get('authorship') or {}).get('school_via'):
            flag('paper_school_basis', key)
        ap = r.get('appointment') or {}
        if ap.get('periodId') is not None:
            if not period_ok.get((r['pi'], ap['periodId'])):
                flag('paper_appointment', key + ' | period ' + str(ap['periodId']))
        elif not sourced(ap.get('listing')):
            flag('paper_appointment', key + ' | listing')
    for x in links:
        if x.get('basis') not in BYLINE_BASES:
            continue
        key = f"{x['pi']} | {x.get('student')} | {x.get('oa')} | {x['basis']}"
        total['link_byline'] += 1; total['link_relation_source'] += 1; total['link_relation_source_student_only'] += 1
        if not ((x.get('oa') or x.get('work')) and str(x.get('byline') or '').strip()):
            flag('link_byline', key)
        if not sourced(x.get('relation_source')):
            flag('link_relation_source', key)
        elif (x.get('relation_source') or {}).get('names_pi') is False:
            flag('link_relation_source_student_only', key)
    return {c: dict(n=len(bad[c]), of=total[c], samples=bad[c][:15]) for c in CATEGORIES}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('schools', nargs='*')
    ap.add_argument('--report', action='store_true', help='count and write, never fail')
    ap.add_argument('--dir', default=str(P.HIERARCHY))
    ap.add_argument('--out', default=str(P.HIERARCHY))
    a = ap.parse_args(argv)
    schools = a.schools or P.SCHOOL_IDS
    wl = json.loads(WHITELIST.read_text()) if WHITELIST.exists() else {}
    res, over = {}, []
    for s in schools:
        res[s] = check(s, a.dir)
        for c, v in res[s].items():
            allowed = ((wl.get(c) or {}).get(s) or {}).get('max', 0)
            v['whitelisted'] = allowed
            if v['n'] > allowed:
                over.append(dict(school=s, category=c, n=v['n'], whitelisted=allowed))
    out = dict(at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), mode='report' if a.report else 'strict',
               whitelist=str(WHITELIST), schools=res, over_whitelist=over, ok=not over)
    Path(a.out, 'EVIDENCE-CHECK.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')
    L = [f"# Evidence check ({out['at']}, {out['mode']})", '',
         'Violations per category and school (whitelisted count in brackets; docs/evidence-whitelist.json).', '',
         '| category | ' + ' | '.join(schools) + ' |', '|---|' + '---|' * len(schools)]
    for c in CATEGORIES:
        L.append(f'| {c} | ' + ' | '.join(f"{res[s][c]['n']} of {res[s][c]['of']}" + (f" [{res[s][c]['whitelisted']}]" if res[s][c]['whitelisted'] else '')
                                         for s in schools) + ' |')
    L += ['', 'Over the whitelist: ' + (', '.join(f"{x['school']}/{x['category']} {x['n']}>{x['whitelisted']}" for x in over) or 'none')]
    Path(a.out, 'EVIDENCE-CHECK.md').write_text('\n'.join(L) + '\n')
    print('\n'.join(L))
    return 0 if (a.report or not over) else 1


if __name__ == '__main__':
    sys.exit(main())
