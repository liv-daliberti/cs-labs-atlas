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

  visiting_roles.py propose <school> ...          print what would be converted (reads the stored captures: needs the project environment)
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


_LIST_HEAD = re.compile(r"\b(?:Alum|Alumni|Alumnae|Postdocs?|Postdoctoral|Faculty|Staff|Collaborators?|Current|Past|Former|(?:PhD|Ph\.D\.|Graduate|Undergraduate|Master'?s|MS)\s+(?:Students?|Researchers?))\b")
_TITLE_WORD = re.compile(r"\b(?:scientists?|professors?|post-?docs?|scholars?|researchers?|staff|engineers?|faculty)\b", re.I)
_MIXED_BEFORE = re.compile(r"(?:undergrad\w*|graduate|ph\.?\s?d|master\w*|post-?docs?|staff|faculty|researchers?|scholars?|scientists?|collaborators?)\s*(?:and|&|,|/)\s*$", re.I)


def shown(text, name, heading_ok):
    """A verbatim span of `text` that shows the person is a visiting student, else None: the visiting phrase directly after the name ('Name (visiting PhD,
    ETH)', 'Name Visiting Student 2024'), or, when the row's own section is a visiting heading (`heading_ok`), a visiting-students heading before the name
    with no other role heading, staff or scientist title between them (400 characters at most). A label before a name is NOT read as the name's role
    otherwise: pages that put the role after the name would give each name the previous person's label."""
    start = 0
    while True:
        j = text.find(name, start)
        if j < 0:
            return None
        after = text[j + len(name): j + len(name) + 110]
        m = V.VISITING_RX.search(after)
        if m and m.start() <= 4 and V.entry_says_visiting(after):
            return text[j: j + len(name) + m.end()]
        if heading_ok:
            before = text[max(0, j - 400): j]
            ms = list(V.VISITING_RX.finditer(before))
            if ms:
                h = ms[-1]
                between = before[h.end():]
                if not (_LIST_HEAD.search(between) or _TITLE_WORD.search(between) or V.VISITING_RX.search(between) or _MIXED_BEFORE.search(before[max(0, h.start() - 30): h.start()])
                        or mini_role_of(after[:45])[0] in ('postdoc', 'other')):
                    return text[max(0, j - 400) + h.start(): j + len(name)]
        start = j + 1


def capture_text(kit, school, row):
    for key in (row.get('capture_url'), row.get('sha256')):
        if key:
            try:
                return kit.lpev.text(school, key)
            except (KeyError, ValueError):
                continue
    return None


def _heading_fits_role(sec, role):
    """A row whose own role is a degree the heading does not name (a PhD row under 'Visiting Undergraduate Research Assistant') took that role from its own text:
    the heading is not about this person."""
    if role in (None, 'other', 'member', 'visiting', 'visitor'):
        return True
    return bool(re.search({'phd': r'ph\.?\s?d|doctoral|(?<!under)graduate', 'masters': r'master|(?<!under)graduate', 'undergraduate': r'undergrad'}.get(role, r'$^'), sec, re.I))


def propose(school, root=None, kit=None):
    """({(pi, name): decision}, mixed, unverified): a row is converted only when its quote, or the stored capture it cites, SHOWS the person as a visiting student
    (`shown`): the row's own note or section is a hint, never the evidence. `unverified` are hinted rows the quote and capture do not show."""
    rows = rows_of(school, root)
    by = collections.defaultdict(list)
    for fn, pi, r in rows:
        by[(pi, SD.fold(r['name']))].append((fn, r))
    found, mixed, unverified = {}, [], []
    for (pi, fn_name), items in by.items():
        sig = [(fn, r, signal(r)) for fn, r in items]
        hints = [x for x in sig if x[2]]
        if not hints:
            continue
        if any(not x[2] and x[1].get('role') == 'phd' and not V.says_visiting(x[1].get('quote') or '') and not re.search(r'\(\s*visiting\s*$', x[1].get('quote') or '', re.I) for x in sig):   # a quote cut at '(Visiting' is the same entry
            mixed.append((pi, items[0][1]['name']))
            continue
        if all(x[1].get('role') == 'postdoc' for x in hints):
            continue
        done = None
        for fn, r, (basis, ev) in hints:
            if r.get('role') == 'postdoc':
                continue
            heading_ok = basis == 'section'
            span = shown(r.get('quote') or '', r['name'], heading_ok)
            where = 'quote'
            if not span and kit is not None:
                t = capture_text(kit, school, r)
                span = shown(t, r['name'], heading_ok) if t else None
                where = 'capture'
            if span:
                done = (fn, r, basis, ev, span if where == 'capture' else None, where)
                break
        if not done:
            unverified.append((pi, hints[0][1]['name'], hints[0][2][0]))
            continue
        fn, r, basis, ev, role_quote, where = done
        found[(pi, r['name'])] = dict(
            decision='visiting', role_was=sorted({str(x[1].get('role')) for x in sig}), basis=f'{where} ({basis})', rule='R-STU-17',
            why=f"visiting student of this lab (shown in the {where}; hint {basis}: {ev})", url=r.get('capture_url') or r.get('url'), quote=r.get('quote'), observed=TODAY,
            converted_from=sorted({x[0] for x in hints}), **({'role_quote': role_quote, 'sha256': r.get('sha256')} if role_quote else {}))
    return found, mixed, unverified


def merge(school, found, root):
    f = P.data_w('student-decisions.json', school, root=root)
    d = json.loads(f.read_text()) if f.exists() else {}
    n = 0
    for pi_ in list(d):   # a re-run replaces what an earlier run converted (entries with converted_from); hand decisions stay
        d[pi_] = {k: v for k, v in d[pi_].items() if not (v.get('decision') == 'visiting' and v.get('converted_from'))}
    for (pi, nm), v in sorted(found.items()):
        cur = (d.setdefault(pi, {})).get(nm)
        if cur and cur.get('decision') in ('not', 'unclear', 'uchicago'):
            continue   # a reviewed decision stands; the converter never overrides it (UChicago's `not` rows are changed by hand with their quote kept)
        d[pi][nm] = v
        n += 1
    d = {k: v for k, v in d.items() if v}
    f.write_text(json.dumps(d, ensure_ascii=False, indent=1, sort_keys=True) + '\n')
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('cmd', choices=['propose', 'write'])
    ap.add_argument('schools', nargs='+')
    ap.add_argument('--root', default=str(Path(__file__).resolve().parents[1]), help='where write puts the reviewed file (default: this checkout)')
    a = ap.parse_args(argv)
    for s in a.schools:
        import labpage_audit as LA
        found, mixed, unverified = propose(s, kit=LA.Kit(s))
        by = collections.Counter(v['basis'] for v in found.values())
        print(f'{s}: {len(found)} visiting {dict(by)}; mixed (left alone) {len(mixed)}; hinted but not shown (left alone) {len(unverified)}')
        if a.cmd == 'propose':
            for (pi, nm), v in sorted(found.items()):
                print(f"  {pi} | {nm} | was {v['role_was']} | {v['basis']} | {(v.get('role_quote') or v['why'])[:140]}")
            for pi, nm in mixed:
                print(f'  MIXED {pi} | {nm}')
            for pi, nm, b in unverified:
                print(f'  NOT SHOWN {pi} | {nm} | hint {b}')
        else:
            print(f'  wrote {merge(s, found, a.root)} decisions')
    return 0


if __name__ == '__main__':
    sys.exit(main())
