"""R-STU-17 (2026-11-04, owner): the `visiting` student role.

A visiting student is a PhD, master's or undergraduate student, a "visiting student researcher", or an exchange or visiting intern who is a
student elsewhere, listed on THIS lab's page: a member of the lab (role `visiting`), not a student of another institution who is dropped. A visiting
professor, faculty member, scientist or scholar is not one (`not_a_student`); a bare "Visitors" heading with no student wording is not decided here
(the role stays `other`, the doubtful path). `visiting` is a non-PhD role: it never makes an adviser relation (researched_membership), and the chain
audit already excuses it from the thesis-link check (tools/chain_audit.py, roles <= {undergraduate, masters, visiting, intern}).

Pure helpers shared by tools/labpage_audit.py (extraction), tools/pihier/students.py (the build's role overlay) and tools/export_release.py.
"""
import re

_BAD_TOKEN = r"(?:professor|faculty|scientists?|scholars?|post-?docs?|lecturers?|fellows?|and|or)"
_KEYWORD = (r"(?:students?|undergrad\w*|ph\.?\s?d\b\.?|doctoral|graduate|grad\b|master['’]?s?\b|m\.?s\.?(?=[\s,)]|$)|m\.?eng\b|"
            r"bachelor['’]?s?\b|b\.?s\.?(?=[\s,)]|$)|candidates?)")
# 'Visiting Students, Scholars and Scientists' / 'Visiting students and researchers' name students among others: not a student heading
_PLURAL_MIX = r"(?!s?\s*(?:,|and|&|/)\s*(?:visiting\s+)?(?:scholars?|scientists?|faculty|professors?|researchers?|post-?docs?|staff)\b)"
VISITING_RX = re.compile(
    r"\bvisiting\s+(?:(?!" + _BAD_TOKEN + r"\b)[\w.'’-]+\s+){0,2}?" + _KEYWORD + _PLURAL_MIX +
    r"|\bvisitors?\s*\(\s*students?\s*\)|\bstudent\s+visitors?\b|\bvisitor\s+students?\b|\(\s*visiting\s*[,)]", re.I)
_EARLIER_STAY = re.compile(r"\b(?:previously|formerly|was an?|spent|during (?:his|her|their)|prior to)\b", re.I)
_OWN_STUDENT_ROLE = re.compile(r"\b(?:ph\.?\s?d\.?|doctoral|graduate|master'?s?|undergraduate)\s+(?:student|candidate)\b", re.I)
_MIXED_HEAD = re.compile(r"\b(?:ph\.?\s?d|undergrad\w*|master\w*|graduate|post-?docs?|staff|faculty|researchers?|scholars?|scientists?|collaborators?)\b", re.I)
_NOT_VISITING_ROLE = ('postdoc', 'other')   # an entry that itself states a postdoc / staff / scientist / visitor title under a visiting-students heading


def says_visiting(text):
    """True when the text names a visiting student (the pattern of R-STU-17)."""
    return bool(VISITING_RX.search(text or ''))


def entry_says_visiting(desc):
    """The entry's own text (what follows the name) states the person is a visiting student: the visiting phrase sits in the first 100 characters
    and is not an earlier stay ('previously a visiting student at ...', 'spent a summer as a visiting student') nor preceded by the entry's own
    'PhD student' / 'master's student' statement."""
    d = (desc or '')[:100]
    m = VISITING_RX.search(d)
    if not m:
        return False
    pre = d[:m.start()]
    return not (_EARLIER_STAY.search(pre) or _OWN_STUDENT_ROLE.search(pre))


def heading_says_visiting(head, role_of):
    """The nearest section heading that names a role is a visiting-students heading. `role_of(text)` -> (role, match): the extractor's role words."""
    for comp in reversed([c for c in (head or '').split(' > ') if c.strip()]):
        m = VISITING_RX.search(comp)
        if m:   # 'Undergraduate and Visiting Students' names two kinds of member: the entries decide, not the heading
            return not _MIXED_HEAD.search(comp[:m.start()] + ' ' + comp[m.end():])
        if role_of(comp)[0]:
            return False
    return False


def visiting_role(desc, head, role_of):
    """(role, basis) when the entry is a visiting student, else None: the entry's own text first ('visiting student from CUHK', '(visiting, CUHK)'), else
    its section heading ('Visiting Students', 'Visitors (students)') unless the entry itself states a postdoc, staff, scientist or visitor title."""
    if entry_says_visiting(desc):
        return 'visiting', 'entry'
    if heading_says_visiting(head, role_of):
        own = role_of((desc or '')[:45])[0]
        if own not in _NOT_VISITING_ROLE:
            return 'visiting', 'section_heading'
    return None
