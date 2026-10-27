"""Spec helpers for decisions/*.py (CMU lab-page pass). Resolved by build.py against the capture stores.

Member row:
  M(name, role, years, url, q=..., near=..., s=..., e=..., after=..., must=[...], note=..., raw=False)
    name   the name exactly as written on the page (accents, nickname, hyphens). If the page writes
           "Last, First", give name="Last, First" as written.
    role   phd | postdoc | masters | undergraduate | staff | visitor | member | other
    years  [first, last] ints/None, or None when the source states no years
    url    live URL (as fetched) or a Wayback id_ URL ("https://web.archive.org/web/<ts>id_/<orig>")
    quote spec, one of:
      q="exact text"              exact substring of the stored page's whitespace-collapsed text
      near="PhD Students"         auto quote: from the nearest occurrence of NEAR before the name (or the first
                                  one shortly after it) through the name; NEAR = a section heading or role text
      s="start", e="end"          from the first START (after AFTER, if given) to the first END after it
    must   tokens that must appear in the quote (default [name])
    raw    match the raw collapsed bytes (JSON data files)

Publications page:
  PUB(url, mode="auto", title_css=None, note=None)
    mode: auto | li | block | anchor | css:<selector> | bibtex | json | text   (see pubx.py)

Lab decision:
  D[pi] = dict(lab_site=URL|None, people_page=URL|None, members=[M(...)], pubs=[PUB(...)],
               notes="what was searched / why", blocked=[URL, ...])
"""

WB = "https://web.archive.org/web/"


def M(name, role, years, url, q=None, near=None, s=None, e=None, after=None, must=None, note=None, raw=False):
    d = {"name": name, "role": role, "years": years, "url": url}
    if q is not None:
        d["q"] = q
    if near is not None:
        d["near"] = near
    if s is not None:
        d["s"] = s
        d["e"] = e
    if after is not None:
        d["after"] = after
    if must:
        d["must"] = must
    if note:
        d["note"] = note
    if raw:
        d["raw"] = True
    return d


def PUB(url, mode="auto", title_css=None, note=None):
    d = {"url": url, "mode": mode}
    if title_css:
        d["title_css"] = title_css
    if note:
        d["note"] = note
    return d
