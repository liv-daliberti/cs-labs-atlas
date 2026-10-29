"""Spec helpers for decisions_*.py (CMU few-students investigation).

Evidence spec (resolved by build.py against few-students-captures.sqlite):
  Q(url, quote)            exact quote; must be a substring of the capture's whitespace-collapsed text
  SE(url, start, end)      quote = text from the first START up to and including the first END after it
  options: after=STR (search START after the first STR), raw=True (match raw collapsed bytes, e.g. JSON/XML),
           long=True (allow quotes up to 4000 chars, e.g. thesis abstract page from author name to "(Chair)")
url is a live URL (latest 200 capture with that url / final_url) or a Wayback id_ URL (matched on capture_url).

Student row:
  ST(name, role, years, ev, must=None, note=None)
    role: phd | postdoc | masters | undergraduate | member | other
    years: [first, last] (ints or None) or None
    must: tokens that must all appear in the quote (default: [name]); set it when the page spells the name
          differently (e.g. "HAGHTALAB, Nika") - and then give name in its natural form.

PI decision:
  D[pi] = dict(students=[ST(...), ...], lab_note="...", notes="...")
"""


def Q(url, q, **kw):
    d = {"url": url, "q": q}
    d.update(kw)
    return d


def SE(url, s, e, **kw):
    d = {"url": url, "s": s, "e": e}
    d.update(kw)
    return d


def ST(name, role, years, ev, must=None, note=None):
    d = {"name": name, "role": role, "years": years, "ev": ev}
    if must:
        d["must"] = must
    if note:
        d["note"] = note
    return d


WB = "https://web.archive.org/web/"
