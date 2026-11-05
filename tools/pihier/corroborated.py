"""R-STU-19 (2026-11-05, owner: Hanin deep dive): lab-page students corroborated by the PI's byline.

A school whose lab-page student additions are not accepted (labpage-acceptance.json, `students.accepted` false: the hand rounds
failed) wires none of them. That leaves a PI's own PhD students off the lab although they are on the PI's byline (Hanin: Tianze
Jiang on three lab papers, Boris Shigida, Shaunak Bhandarkar). The roster alone and co-authorship alone are never evidence
(Stanford rule); the two together are (the UChicago roster rule of 2026-11-04 and R-STU-02 already use that pairing). So a
not-accepted additions row is wired when, and only when, all of these hold:
  1. the row names a student: its role is phd, masters, undergraduate or visiting; or the role is empty and the stored capture
     (sha256) shows a student cue nearest before the name (`cue_role`: 'supervise several excellent PhD students: A, B, C' is a
     prose list the audit's heading reader cannot see; a postdoc, staff, collaborator or alumni cue nearer to the name rejects it);
  2. an alumni row carries stated years (a capture year is not a membership year, R-STU-14);
  3. the student's full first given name and family name (no initials) stand on the byline of a lab paper of that PI, the
     given-name guard passes, the paper has at most MAX_AUTHORS authors, and its year is within three years of the row's years
     (stated years, else the capture year, R-STU-14);
  4. the lab holds no student of that name already (R-STU-13 merges stay the only way to join two records).
The wired row goes through the same record builder as an accepted row (relation `researched_advising`, `auto`), and the normal link
bases then link it. -> counters `labpage_students_corroborated_*`, report block `labpageStudentsCorroborated`."""
import collections, html, re, sqlite3, zlib

import atlas_paths as P

from .common import as_years, read
from .names import Name, byline_name, given_conflict, nick_ok, nosuffix, toks

MAX_AUTHORS = 15  # a hyper-authored paper (a collaboration) says nothing about who the PI's students are
STUDENT_KINDS = ('phd', 'masters', 'undergraduate', 'visiting')

# role cues, read from the page text before the name; the nearest cue decides
CUES = [('phd', re.compile(r"\bph\.?\s?d\.?(?:\s+(?:students?|candidates?))?|\bdoctoral(?:\s+(?:students?|candidates?))?|\bgrad(?:uate)?\s+students?", re.I)),
        ('masters', re.compile(r"\bmaster'?s(?:\s+students?)?|\bm\.?s\.?c?\.?\s+students?|\bmeng\b", re.I)),
        ('undergraduate', re.compile(r"\bundergrad(?:uate)?s?(?:\s+students?)?|\bbachelor'?s", re.I)),
        ('not', re.compile(r"\bpost-?docs?\b|\bpostdoctoral|\bresearch(?:ers| scientists?| associates?| staff| fellows?)\b|\bscientists?\b|\bstaff\b|\bengineers?\b|\bvisitors?\b|\bfaculty\b|\bcollaborat\w+|\bco-?authors?\b"
                           r"|\balumni\b|\bformer\b|\bpast\b|\bgraduated\b|\bformerly\b|\bprevious\b|\bplacements?\b|\bpublications?\b|\bpapers?\b", re.I))]
WINDOW = 700  # characters of page text before the name that are searched for the nearest cue


def page_text(sha, dbs):
    """The visible text of the stored capture whose bytes hash to `sha` (and its fetch date), else (None, None)."""
    for c in dbs:
        r = c.execute('select content, fetched_at from captures where sha256=? and content is not null limit 1', (sha,)).fetchone()
        if not r:
            continue
        b = r[0]
        try:
            b = zlib.decompress(b, 47)  # zlib or gzip header
        except Exception:  # noqa: BLE001 (stored uncompressed)
            pass
        t = b.decode('utf-8', 'replace') if isinstance(b, bytes) else str(b)
        t = re.sub(r'<(script|style)\b.*?</\1>', ' ', t, flags=re.S | re.I)
        return ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', t)).split()), r[1]
    return None, None


def cue_role(text, quote, name):
    """The role the page shows for `name` (the end of `quote` in `text`): the nearest cue before it. 'phd' / 'masters' /
    'undergraduate' for a student cue, None when the nearest cue is a postdoc, staff, alumni, collaborator or publication cue or
    there is none."""
    nq = ' '.join((quote or '').split())
    i = text.find(nq) if nq else -1
    if i < 0:
        return None
    end = i + len(nq)
    j = text.rfind(name, i, end)
    pos = j if j >= 0 else end
    before = text[max(0, pos - WINDOW):pos]
    best = None
    for kind, rx in CUES:
        for m in rx.finditer(before):
            if best is None or m.end() > best[0]:
                best = (m.end(), kind)
    return best[1] if best and best[1] != 'not' else None


def full_name_on(name_toks, byline, forms):
    """The byline spells the student's first given name and family name out (no initials); the given-name guard passes."""
    t = toks(byline_name(byline))
    if len(t) < 2 or len(name_toks) < 2 or len(t[0]) < 2 or len(name_toks[0]) < 2 or t[-1] != name_toks[-1]:
        return False
    return (t[0] == name_toks[0] or nick_ok(t[0], name_toks[0])) and not given_conflict(forms, byline, strict=True)


def corroborated_rows(school, papers_by_pi, existing, dbs, here=None, n=None):
    """The not-accepted additions rows that pass R-STU-19: [(row with role, years and role_basis filled in, [work ids])]."""
    add_f = P.data('labpage-additions.json', school, root=here)
    if not add_f.exists():
        return []
    out = []
    for s_ in read(add_f).get('students') or []:
        pi = s_.get('pi')
        if pi not in papers_by_pi or not (s_.get('name') and s_.get('quote') and s_.get('sha256') and s_.get('url')):
            continue
        name = s_['name']
        nt = nosuffix(toks(name))
        if len(nt) < 2 or any(Name([name]).match(x) for x in existing.get(pi, ())):
            n['labpage_students_corroborated_skipped:in_lab'] += any(Name([name]).match(x) for x in existing.get(pi, ()))
            continue
        role = s_.get('role')
        if role in ('postdoc', 'other', 'staff', 'member'):
            n['labpage_students_corroborated_skipped:role'] += 1
            continue
        text, fetched = page_text(s_['sha256'], dbs)
        basis = s_.get('role_basis')
        if role not in STUDENT_KINDS:
            role = cue_role(text, s_['quote'], name) if text else None
            basis = 'page_cue'
            if role is None:
                n['labpage_students_corroborated_skipped:no_student_cue'] += 1
                continue
        years = as_years(s_.get('years'))
        if not years:
            if s_.get('alumni'):
                n['labpage_students_corroborated_skipped:alumni_without_years'] += 1
                continue
            m = re.search(r'/web/(\d{4})', s_['url'])
            cy = int(m.group(1)) if m else int(str(fetched or '0')[:4]) or None
            if not cy:
                continue
            years = [cy]
        works = []
        for r in papers_by_pi[pi]:
            if not r.get('year') or not (min(years) - 3 <= int(r['year']) <= max(years) + 3):
                continue
            if len(r['byline']) > MAX_AUTHORS:
                continue
            if any(full_name_on(nt, b, [name]) for bl, _ in r['_bylines'] for b in bl):
                works.append(r['work'])
        if not works:
            n['labpage_students_corroborated_skipped:no_byline'] += 1
            continue
        out.append((dict(s_, role=role, role_basis=basis if basis else s_.get('role_basis'), years=sorted(set(years)), years_basis=s_.get('years_basis') or 'capture_date'), works))
    return out


def open_capture_dbs(school, here=None):
    return [sqlite3.connect(f"file:{P.data(n_, school, root=here)}?mode=ro", uri=True) for n_ in ('labpage-audit-captures.sqlite', 'labpage-captures.sqlite')
            if P.data(n_, school, root=here).exists()]


def tally(rows):
    return collections.Counter(r['pi'] for r, _ in rows)
