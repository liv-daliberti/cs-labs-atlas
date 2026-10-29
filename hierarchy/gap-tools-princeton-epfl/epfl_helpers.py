"""EPFL-only helpers (used by decisions_epfl.py). Built on evlib/gapcap; quotes are checked by evlib.q.

people_page_students(url, ...) parses an EPFL people-directory profile (people.epfl.ch/<name>) "Teaching & PhD" block:
  "PhD Students A , B , C"                         current doctoral students the person directs
  "Past EPFL PhD Students X (2017) , Y (2023)"     theses directed, with defence year
  "Past EPFL PhD Students as codirector Z (2019)"  theses co-directed
Each row's quote runs from the section heading to the student's name (and year), so it names both the student and the
relation. Current students get years [Y, Y] where Y is the capture year (live fetch = 2026).
"""
import re

import evlib
import gapcap

HEADS = [("Past EPFL PhD Students as codirector", "codirector"), ("Past EPFL PhD Students", "past"), ("PhD Students", "current")]
STOP = r"(?=\s(?:Past EPFL PhD Students|Courses|Contact EPFL|Teaching & PhD|Awards|Publications|Research|Infoscience)\b|$)"


def _year_of(r):
    m = re.search(r"/web/(\d{4})", r.get("capture_url") or "")
    if m:
        return int(m.group(1))
    return 2026


def people_page_students(url, school="epfl", from_year=2016, include_current=True, exclude=()):
    r, views = evlib._cap(school, url)
    t = views.get("html") or views.get("raw")
    cap_year = _year_of(r)
    rows = []
    for m in re.finditer(r"(Past EPFL PhD Students as codirector|Past EPFL PhD Students|(?<!Past EPFL )PhD Students)\s(.*?)" + STOP, t):
        head, body = m.group(1), m.group(2)
        kind = dict(HEADS)[head]
        if kind == "current" and not include_current:
            continue
        start = m.start(1)
        pos = m.start(2)
        for part in body.split(" , "):
            part = part.strip()
            if not part:
                continue
            i = t.find(part, pos)
            pos = i + len(part)
            ym = re.search(r"\((\d{4})\)\s*$", part)
            name = re.sub(r"\s*\(\d{4}\)\s*$", "", part).strip()
            if name in exclude:
                continue
            if ym:
                y = int(ym.group(1))
                if y < from_year:
                    continue
                years = [y, y]
            else:
                years = [cap_year, cap_year]
            quote = t[start:i + len(part)]
            ev = evlib.q(school, url, quote, name=name)
            note = {"current": "current doctoral student listed on the director's EPFL profile",
                    "past": "thesis directed (defence year in parentheses) per the director's EPFL profile",
                    "codirector": "thesis co-directed (defence year in parentheses) per the co-director's EPFL profile"}[kind]
            row = {"name": name, "role": "phd", "years": years, "note": note}
            row.update(ev)
            rows.append(row)
    return rows
