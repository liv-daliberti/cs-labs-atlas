"""Role cues read from a roster entry's own words (R-STU-19 B; the same cues R-STU-20 reads on agent/michigan-round2, `corroborated.cue_role` and
`local_cue`): a student role stated right after the name ('Zihan Zhou (Master, Winter 2025)', 'David Deriso (Ph.D. Student, CS)') beats the nearest role
heading before it ('PhD Students: A, B, C'); a postdoc, staff, alumni, collaborator or publication cue nearer than a student cue rejects.
Applied to a relation source's quote, which is the page's own whitespace-collapsed text from the heading through the person's name."""
import re

CUES = [('phd', re.compile(r"\bph\.?\s?d\.?(?:\s+(?:students?|candidates?))?|\bdoctoral(?:\s+(?:students?|candidates?))?|\bgrad(?:uate)?\s+students?", re.I)),
        ('masters', re.compile(r"\bmaster'?s(?:\s+students?)?|\bm\.?s\.?c?\.?\s+students?|\bmeng\b", re.I)),
        ('undergraduate', re.compile(r"\bundergrad(?:uate)?s?(?:\s+students?)?|\bbachelor'?s", re.I)),
        ('not', re.compile(r"\bpost-?docs?\b|\bpostdoctoral|\bresearch(?:ers| scientists?| associates?| staff| fellows?)\b|\bscientists?\b|\bstaff\b|\bengineers?\b|\bvisitors?\b|\bfaculty\b|\bcollaborat\w+|\bco-?authors?\b"
                           r"|\balumni\b|\bformer\b|\bpast\b|\bgraduated\b|\bformerly\b|\bprevious\b|\bplacements?\b|\bpublications?\b|\bpapers?\b", re.I))]
LOCAL_CUES = [('other', re.compile(r"medical\s+students?|\bm\.?d\.?\s+students?|\bresidents?\b|post-?doc|\bvisiting\b|\bresearch(?:er|\s+scientist|\s+engineer|\s+assistant)\b|\bengineer\b|\bstaff\b|\bdevelopers?\b", re.I))] \
    + [(k, re.compile(rx.pattern + (r"|\(\s*master\b|\(\s*m\.?s\.?\b" if k == 'masters' else (r"|\bug\b" if k == 'undergraduate' else '')), re.I)) for k, rx in CUES[:3]]
VISITING_STUDENT = re.compile(r"visiting\s+(?:ph\.?d\.?|graduate|grad|master'?s?|undergrad\w*|student|intern)\b|\bvisiting\s+\w+\s+student", re.I)
VISITING_NOT_STUDENT = re.compile(r"visiting\s+(?:scholar|professor|faculty|researcher|scientist|fellow|postdoc)", re.I)
WINDOW = 700   # characters before the name searched for the nearest cue


def local_cue(text, name):
    """The role the entry states within 40 characters after `name` ('phd', 'masters', 'undergraduate', 'other'), or None."""
    j = text.rfind(name)
    if j < 0:
        return None
    after = text[j + len(name):j + len(name) + 40]
    best = None
    for kind, rx in LOCAL_CUES:
        m = rx.search(after)
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), kind)
    return best[1] if best else None


def heading_cue(text, name):
    """The nearest role cue before `name`: a student kind, or None when it is a postdoc, staff, alumni, collaborator or publication cue or there is none."""
    j = text.rfind(name)
    before = text[max(0, (j if j >= 0 else len(text)) - WINDOW):(j if j >= 0 else len(text))]
    best = None
    for kind, rx in CUES:
        for m in rx.finditer(before):
            if best is None or m.end() > best[0]:
                best = (m.end(), kind)
    return best[1] if best and best[1] != 'not' else None


def student_by_entry(quote, names):
    """True when the entry's own words (first) or its heading (second) make the person a student: 'phd', 'masters', 'undergraduate'."""
    q = ' '.join((quote or '').split())
    for name in names:
        if not name or name not in q:
            continue
        local = local_cue(q, name)
        if local == 'other':
            continue
        if local in ('phd', 'masters', 'undergraduate'):
            return True
        if heading_cue(q, name) in ('phd', 'masters', 'undergraduate'):
            return True
    return False
