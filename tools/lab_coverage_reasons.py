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


def thesis_facts(key):
    """The repository crawl's own counts (fulltext-push/etd_crawl.py, read-only): pages read, dissertations 2016-2026 with an advisor field, and the
    advisor family names seen, so each lab's reason can say how many dissertations name its family name without matching the PI (None without a crawl)."""
    import re
    import sqlite3
    db = P.FT_RAW / 'etd_crawl' / f'{key}.sqlite'
    if not db.exists():
        return None
    c = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    total = c.execute('select count(*) from queue').fetchone()[0]
    done = c.execute('select count(*) from pages').fetchone()[0]
    fam, n = {}, 0
    for adv, in c.execute('select advisors from pages where dissertation=1 and year between 2016 and 2026'):
        n += 1
        for a in json.loads(adv or '[]'):
            f = re.sub(r'[^a-z]', '', a.split(',')[0].lower())
            fam[f] = fam.get(f, 0) + 1
    return dict(total=total, done=done, dissertations=n, fam=fam)


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
    th = thesis_facts(key)
    n = 0
    for row in LC.lab_rows(key):
        rs = row['reasons'].get('students')
        old = (cur.get(row['pi']) or {}).get('students') or {}
        refresh = old.get('code') == 'sources_exhausted' and not row.get('students')   # a generated reason is rewritten with the current facts
        if not refresh and (not rs or rs['code'] != 'open'):
            if old.get('code') == 'sources_exhausted' and row.get('students'):   # the lab has students now: a generated reason is stale
                cur[row['pi']].pop('students')
            continue
        e = cur.setdefault(row['pi'], {})
        if 'students' in e and e['students'].get('code') != 'sources_exhausted':   # hand-written reasons stay; generated ones are refreshed
            continue
        rec = audit.get(row['pi']) or {}
        extra = []
        if th:
            fam = ''.join(ch for ch in row['pi'].split()[-1].lower() if ch.isalpha())
            extra.append(f"thesis repository crawl 2026-11-05: {th['done']} of {th['total']} item pages read, {th['dissertations']} dissertations of 2016-2026 with an advisor field; "
                         f"{th['fam'].get(fam, 0)} of them name the family name '{fam}' as an advisor, none of which became a relation of this PI (no full-name match or outside the PI's listed years); the crawl continues, rerun etd_crawl.py evidence")
        e['students'] = dict(code='sources_exhausted', why=f"No student of this PI in any allowed source checked ({row['title']}).",
                             sources_checked=[lab_facts(rec)] + extra + base)
        n += 1
    rf.parent.mkdir(parents=True, exist_ok=True)
    rf.write_text(json.dumps(cur, indent=1, ensure_ascii=False))
    print(json.dumps(dict(written=n, total=len(cur))))


if __name__ == '__main__':
    main(sys.argv[1])
