"""Shared helpers for the Berkeley gap decision modules (decisions_*.py).

Evidence specs name a stored capture by URL (live URL or Wayback id_ URL) and give either an exact quote (Q) or
start/end markers (SE); build.py extracts and validates the quote, fills sha256/capture_url and re-verifies
every quote against the stored bytes. Options: after=STR (search START after STR), must=[tokens], raw=True
(match against the raw whitespace-collapsed bytes, e.g. JSON).
"""
import json
import re

TOOLS = "/n/fs/similarity/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/gap-tools-berkeley"
WB = "https://web.archive.org/web/"
PROF = "https://www2.eecs.berkeley.edu/Faculty/Homepages/"
DISS = "https://www2.eecs.berkeley.edu/Pubs/Dissertations/Faculty/"
PUBS = "https://www2.eecs.berkeley.edu/Pubs/Faculty/"
OA = "https://api.openalex.org/"

_seed = None


def seed():
    global _seed
    if _seed is None:
        _seed = json.load(open(TOOLS + "/seed.json"))
    return _seed


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


def ID(kind, ev, note=""):
    return {"kind": kind, "ev": ev, "note": note}


def oa_author_url(aid):
    """URL under which capstore.openalex('authors/<aid>') stores the author record."""
    return OA + "authors/" + aid


def oa_author_quote(aid, display_name, **kw):
    """Quote spec for an OpenAlex author record (compact JSON): from '{"id":"https://openalex.org/<aid>"' through
    '"display_name":"<name>"' -- carries the id, the record's ORCID (if any) and the name."""
    return SE(oa_author_url(aid), '{"id":"https://openalex.org/' + aid + '"', f'"display_name":"{display_name}"',
              raw=True, **kw)


def diss_page_url(pi):
    s = seed()[pi]
    dp = s.get("diss_page") or {}
    return dp.get("capture_url") or dp.get("url") or (DISS + s["slug"] + ".html")


def diss_heading(pi):
    """The dissertations page heading text, e.g. 'Ph.D. Dissertations - Jelani Nelson'."""
    return "Ph.D. Dissertations - " + seed()[pi].get("diss_name", pi)


def diss_entries(pi, min_year=2016):
    return [e for e in seed()[pi].get("dissertations", []) if e["year"] >= min_year]


def diss_students(pi, min_year=2016, heading_name=None, maxspan=650):
    """ST rows for each dissertation (year >= min_year) on the PI's EECS dissertations-by-faculty page.
    Quote = heading through the entry when that span is short enough, else just 'Title Student [year]'."""
    url = diss_page_url(pi)
    head = "Ph.D. Dissertations - " + (heading_name or pi)
    out = []
    acc = 0
    for i, e in enumerate(seed()[pi].get("dissertations", [])):
        entry = f"{e['title']} {e['student']} [{e['year']}]"
        acc += len(entry) + 1
        if e["year"] < min_year:
            continue
        if acc + len(head) <= maxspan:
            ev = SE(url, head, entry, must=[e["student"].split()[-1]])
        else:
            ev = Q(url, entry)
        out.append(ST(e["student"], "phd", [None, e["year"]], ev, must=[e["student"].split()[-1]],
                      note="EECS Ph.D. dissertations-by-faculty page (dissertation year)"))
    return out


def diss_status(pi, heading_name=None, min_year=2016):
    """Status evidence: heading through the newest dissertation entry (must be >= min_year)."""
    url = diss_page_url(pi)
    head = "Ph.D. Dissertations - " + (heading_name or pi)
    ents = seed()[pi].get("dissertations", [])
    if not ents or ents[0]["year"] < min_year:
        raise ValueError(f"{pi}: newest dissertation is not >= {min_year}")
    e = ents[0]
    return SE(url, head, f"{e['title']} {e['student']} [{e['year']}]")


def surname(name):
    return re.sub(r"[,.]", "", name).split()[-1]
