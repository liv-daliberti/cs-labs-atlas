"""Recorded reasons for the labs of an onboarding school that have no students (owner rule 2026-11-03, docs/DECISIONS.md: every lab gets students or an
evidence-backed reason). For each lab `tools/lab_coverage.py` reports 'open' for students, one `sources_exhausted` entry is written to
hierarchy/<key>/reviewed/lab-coverage-reasons.json with the facts of that lab's own audit record (hierarchy/<key>/labpage-audit.jsonl.gz: the lab page found or
not, the students section's status, how many members the page lists and why none was admitted) and the school-level sources checked (the charter's rosters and
adviser lists, the thesis repository's status). These are the weakest reasons: they say where we looked, not that no student exists. Hand-written entries are never replaced.
usage: lab_coverage_reasons.py <key>
"""
import gzip
import json
import sys

import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
import lab_coverage as LC  # noqa: E402


def school_sources(key):
    st = S.get(key).get('students') or {}
    out = []
    for r in st.get('rosters') or []:
        out.append(f"names-only PhD roster {r['url']} ({r.get('kind', 'students')}, Wayback captures): a name counts only with a co-authored lab paper of this PI (R-STU-02); none does")
    for u in st.get('adviser_directories') or []:
        out.append(f'adviser list {u}: no student names this PI')
    if not st.get('adviser_directories'):
        out.append('adviser-bearing student directories: none exist or are archived for this school (checked at stage 6)')
    note = (S.get(key).get('thesis') or {}).get('note')
    if note:
        out.append('thesis repository: ' + note)
    return out


def lab_facts(rec):
    lp, stu = rec.get('lab_page') or {}, rec.get('students') or {}
    site = (lp.get('urls') or {}).get('lab_site') or (lp.get('urls') or {}).get('people_page')
    listed = len(stu.get('listed_current') or []) + len(stu.get('listed_alumni') or [])
    f = f"lab page: status {lp.get('status')} ({lp.get('reason_code')}), {'site ' + site if site else 'no site found'}; students section: {stu.get('page_status')} ({stu.get('reason_code')})"
    if listed:
        f += f"; the page lists {listed} members, none admitted by the lab-page rules or by the hand-checked additions ({stu.get('reason') or 'see labpage-audit.jsonl.gz'})"
    return f


def main(key):
    audit = {}
    for line in gzip.open(P.data('labpage-audit.jsonl.gz', key), 'rt'):
        r = json.loads(line)
        audit[r['pi']] = r
    rf = P.data_w('lab-coverage-reasons.json', key)
    cur = json.loads(rf.read_text()) if rf.exists() else {}
    base = school_sources(key)
    n = 0
    for row in LC.lab_rows(key):
        rs = row['reasons'].get('students')
        if not rs or rs['code'] != 'open':
            continue
        e = cur.setdefault(row['pi'], {})
        if 'students' in e:
            continue
        rec = audit.get(row['pi']) or {}
        e['students'] = dict(code='sources_exhausted', why=f"No student of this PI in any allowed source checked ({row['title']}).",
                             sources_checked=[lab_facts(rec)] + base)
        n += 1
    rf.parent.mkdir(parents=True, exist_ok=True)
    rf.write_text(json.dumps(cur, indent=1, ensure_ascii=False))
    print(json.dumps(dict(written=n, total=len(cur))))


if __name__ == '__main__':
    main(sys.argv[1])
