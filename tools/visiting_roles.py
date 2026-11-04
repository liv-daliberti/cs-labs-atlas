"""R-STU-17 (2026-11-04, owner): convert past decisions about visiting students to the role `visiting`.

For each school, read the researched student evidence the build reads (gap-evidence, few-students-evidence, thesis-evidence, labpage-evidence,
labpage-additions) and propose, per (PI, student), a `visiting` decision when the row itself says the person is a visiting student:
  entry     the visiting phrase follows the name directly in the quote ('Name (visiting PhD ...', 'Name Visiting Ph.D. from Tsinghua')
  section   the row's section heading is a visiting-students heading ('Visiting Students', 'Visitors (students)'), not a mixed one ('Undergraduate and Visiting
            Students'), and the entry does not itself state a postdoc, staff or scientist title
  note      the reviewer's note on the row says visiting student / PhD / undergraduate / master's ('visiting masters student (ETH Zurich)')
A person who also has a non-visiting PhD row in the same lab is left alone (listed as `mixed`). Visiting professors, faculty, scientists and scholars never
match (tools/visiting.py). The original quote and url are kept; `converted_from` records the file and the role the row had.
The result is merged into hierarchy/<school>/reviewed/student-decisions.json (`decision: visiting`), which the build and labpage_audit read
(tools/student_decisions.py); nothing in the evidence files is edited.

  visiting_roles.py propose <school> ...          print what would be converted
  visiting_roles.py write <school> ... [--root R] merge into R/hierarchy/<school>/reviewed/student-decisions.json (default: this checkout's worktree)
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

import atlas_paths as P  # noqa: E402
import student_decisions as SD  # noqa: E402
import visiting as V  # noqa: E402

SOURCES = ['gap-evidence.json', 'few-students-evidence.json', 'thesis-evidence.json', 'labpage-evidence.json']
TODAY = '2026-11-04'
_POSTDOC = re.compile(r'post-?doc', re.I)
_OTHER = re.compile(r'scientist|engineer|\bstaff\b|professor|scholar|research (?:associate|assistant)|manager|visit|lecturer|faculty', re.I)
_NOTE_BAD = re.compile(r'rotation|post-?bachelor|professor|faculty|postdoc|scholar|scientist', re.I)


def mini_role_of(text):
    """The few role words the visiting rule needs from an entry's own start: postdoc, or a staff / scientist / visitor title."""
    t = text or ''
    return ('postdoc', None) if _POSTDOC.search(t) else (('other', None) if _OTHER.search(t) else (None, None))


def rows_of(school, root=None):
    """[(file, pi, student row)] of every researched student row of the school."""
    out = []
    for fn in SOURCES + ['labpage-additions.json']:
        f = P.data(fn, school, root=root)
        if not f.exists():
            continue
        d = json.loads(f.read_text())
        if fn == 'labpage-additions.json':
            out += [(fn, r.get('pi'), r) for r in d.get('students') or []]
        else:
            out += [(fn, e.get('pi'), r) for e in d if isinstance(e, dict) for r in e.get('students') or [] if isinstance(r, dict)]
    return [x for x in out if x[1] and x[2].get('name')]


def signal(row):
    """(basis, evidence text) when the row itself says the person is a visiting student, else None."""
    q, nm = row.get('quote') or '', row['name']
    i = q.find(nm)
    if i >= 0:
        desc = q[i + len(nm): i + len(nm) + 110]
        m = V.VISITING_RX.search(desc)
        if m and m.start() <= 4 and V.entry_says_visiting(desc):
            return 'entry', desc[:80].strip()
    sec = row.get('section') or (re.search(r'section: (.*)$', row.get('note') or '') or [None, None])[1]
    if sec and '(' not in sec and V.heading_says_visiting(sec, mini_role_of) and _heading_fits_role(sec, row.get('role')):
        desc = q[i + len(nm): i + len(nm) + 45] if i >= 0 else ''
        before = q[max(0, i - 45):i] if i >= 0 else ''   # 'Visiting research scientist Peter Hase': a label before the name belongs to the name
        if mini_role_of(desc)[0] not in ('postdoc', 'other') and not re.search(r'(?:scientist|post-?docs?|professor|scholar|researcher|staff|engineer|faculty)\s*$', before, re.I):
            return 'section', sec[:80]
    note = (row.get('note') or '').split('section:')[0]
    nm_ = V.VISITING_RX.search(note)
    if nm_ and nm_.start() <= 30 and not _NOTE_BAD.search(note):   # the reviewer's note opens with the visiting phrase (a later mention may be about someone else)
        return 'note', note[:80]
    return None


def _heading_fits_role(sec, role):
    """A row whose own role is a degree the heading does not name (a PhD row under 'Visiting Undergraduate Research Assistant') took that role from its own text:
    the heading is not about this person."""
    if role in (None, 'other', 'member', 'visiting', 'visitor'):
        return True
    return bool(re.search({'phd': r'ph\.?\s?d|doctoral|(?<!under)graduate', 'masters': r'master|(?<!under)graduate', 'undergraduate': r'undergrad'}.get(role, r'$^'), sec, re.I))


def propose(school, root=None):
    rows = rows_of(school, root)
    by = collections.defaultdict(list)
    for fn, pi, r in rows:
        by[(pi, SD.fold(r['name']))].append((fn, r))
    found, mixed = {}, []
    for (pi, fn_name), items in by.items():
        sig = [(fn, r, signal(r)) for fn, r in items]
        hits = [x for x in sig if x[2]]
        if not hits:
            continue
        if any(not x[2] and x[1].get('role') == 'phd' and not V.says_visiting(x[1].get('quote') or '') and not re.search(r'\(\s*visiting\s*$', x[1].get('quote') or '', re.I) for x in sig):   # a quote cut at '(Visiting' is the same entry
            mixed.append((pi, items[0][1]['name']))
            continue
        if all(x[1].get('role') == 'postdoc' for x in hits):
            continue
        fn, r, (basis, ev) = next(x for x in hits if x[1].get('role') != 'postdoc')
        found[(pi, r['name'])] = dict(
            decision='visiting', role_was=sorted({str(x[1].get('role')) for x in sig}), basis=basis, rule='R-STU-17',
            why=f"visiting student of this lab ({basis}: {ev})", url=r.get('capture_url') or r.get('url'), quote=r.get('quote'), observed=TODAY,
            converted_from=sorted({x[0] for x in hits}))
    return found, mixed


def merge(school, found, root):
    f = P.data_w('student-decisions.json', school, root=root)
    d = json.loads(f.read_text()) if f.exists() else {}
    n = 0
    for (pi, nm), v in sorted(found.items()):
        cur = (d.setdefault(pi, {})).get(nm)
        if cur and cur.get('decision') in ('not', 'unclear', 'uchicago'):
            continue   # a reviewed decision stands; the converter never overrides it (UChicago's `not` rows are changed by hand with their quote kept)
        d[pi][nm] = v
        n += 1
    f.write_text(json.dumps(d, ensure_ascii=False, indent=1, sort_keys=True) + '\n')
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('cmd', choices=['propose', 'write'])
    ap.add_argument('schools', nargs='+')
    ap.add_argument('--root', default=str(Path(__file__).resolve().parents[1]), help='where write puts the reviewed file (default: this checkout)')
    a = ap.parse_args(argv)
    for s in a.schools:
        found, mixed = propose(s)
        by = collections.Counter(v['basis'] for v in found.values())
        print(f'{s}: {len(found)} visiting {dict(by)}; mixed (left alone) {len(mixed)}')
        if a.cmd == 'propose':
            for (pi, nm), v in sorted(found.items()):
                print(f"  {pi} | {nm} | was {v['role_was']} | {v['basis']} | {v['why'][:110]}")
            for pi, nm in mixed:
                print(f'  MIXED {pi} | {nm}')
        else:
            print(f'  wrote {merge(s, found, a.root)} decisions')
    return 0


if __name__ == '__main__':
    sys.exit(main())
