"""Helpers that turn researched facts into evidence rows whose quotes are exact substrings of stored captures.

A source key is either a live URL (stored with capture_url NULL) or a Wayback id_ capture URL (stored as capture_url).
Quotes are found with a regex on the whitespace-collapsed page text (capstore.page_text) and returned verbatim.
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import json
import re
import sys
import unicodedata
import zlib

sys.path.insert(0, str(P.HIERARCHY / 'gap-tools-mit'))
import capstore  # noqa: E402

_cache = {}


def row(src):
    """The newest 200 capture for a source key: (url, capture_url, sha256, text)."""
    if src in _cache:
        return _cache[src]
    con = capstore.connect()
    if "web.archive.org/web/" in src:
        r = con.execute("SELECT url, capture_url, sha256, content FROM captures WHERE capture_url=? AND status=200 "
                        "AND content IS NOT NULL ORDER BY id DESC LIMIT 1", (src,)).fetchone()
    else:
        r = con.execute("SELECT url, capture_url, sha256, content FROM captures WHERE (url=? OR final_url=?) AND capture_url IS NULL "
                        "AND status=200 AND content IS NOT NULL ORDER BY id DESC LIMIT 1", (src, src)).fetchone()
    con.close()
    if not r:
        raise KeyError("no stored 200 capture for " + src)
    out = (r[0], r[1], r[2], capstore.page_text(zlib.decompress(r[3])))
    _cache[src] = out
    return out


def fold(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def name_tokens(name):
    n = re.sub(r"\([^)]*\)", " ", name)
    return [t for t in re.split(r"[^a-z0-9]+", fold(n)) if len(t) > 1 or t.isalpha()]


def has_name(quote, name):
    """Every token of the name occurs in the quote (case/diacritics-insensitive, any order)."""
    q = fold(quote)
    toks = name_tokens(name)
    return bool(toks) and all(re.search(r"(?<![a-z])" + re.escape(t) + r"(?![a-z])", q) for t in toks)


def quote(src, rx, name=None, flags=re.I):
    url, cap, sha, text = row(src)
    m = re.search(rx, text, flags)
    if not m:
        raise ValueError(f"pattern not found in {src}: {rx!r}")
    q = m.group(0)
    if name and not has_name(q, name):
        raise ValueError(f"quote lacks name {name!r}: {q!r}")
    return url, cap, sha, q


def ev(src, rx, name):
    url, cap, sha, q = quote(src, rx, name)
    d = {"url": url}
    if cap:
        d["capture_url"] = cap
    d.update(sha256=sha, quote=q, name_check=name)
    return d


def student(name, role, years, src, rx, display_name=None, note=None):
    url, cap, sha, q = quote(src, rx, name)
    d = {"name": name}
    if display_name:
        d["display_name"] = display_name
    d.update(role=role, years=years, url=url)
    if cap:
        d["capture_url"] = cap
    d.update(sha256=sha, quote=q)
    if note:
        d["note"] = note
    return d


def idev(kind, src, rx, name, note):
    url, cap, sha, q = quote(src, rx, name)
    d = {"kind": kind, "url": cap or url}
    if cap:
        d["original_url"] = url
    d.update(sha256=sha, quote=q, name_check=name, note=note)
    return d


def appt(src, rx, name):
    url, cap, sha, q = quote(src, rx, name)
    d = {"url": cap or url}
    if cap:
        d["original_url"] = url
    d.update(sha256=sha, quote=q)
    return d


# ---- DSpace discover-search captures: one quote per thesis item, from its advisor field through its first author ----
def dspace_items(src):
    url, cap, sha, text = row(src)
    con = capstore.connect()
    r = con.execute("SELECT content FROM captures WHERE (url=? OR final_url=?) AND status=200 ORDER BY id DESC LIMIT 1", (src, src)).fetchone()
    con.close()
    d = json.loads(zlib.decompress(r[0]))
    out = []
    for o in d["_embedded"]["searchResult"]["_embedded"]["objects"]:
        it = o["_embedded"]["indexableObject"]
        md = it.get("metadata") or {}
        v = lambda k: [x["value"] for x in md.get(k) or []]
        out.append(dict(uuid=it["uuid"], handle=it.get("handle"), advisors=v("dc.contributor.advisor"), authors=v("dc.contributor.author"),
                        date=(v("dc.date.issued") or [""])[0], degree=v("dc.description.degree") + v("dc.description"), title=it.get("name"),
                        dept=v("dc.contributor.department")))
    return out


def dspace_student(src, author_value, advisor_rx, role, year, display_name, note=None):
    """Quote = text from this item's '"dc.contributor.advisor"' key through the author's value, inside one item."""
    url, cap, sha, text = row(src)
    a = re.escape(author_value)
    rx = r'"dc\.contributor\.advisor"\s?:\s?\[(?:(?!"dc\.contributor\.author").){0,600}?(?:' + advisor_rx + ')' + \
         r'(?:(?!"dc\.contributor\.author").){0,600}?"dc\.contributor\.author"\s?:\s?\[\s?\{\s?"value"\s?:\s?"' + a
    m = re.search(rx, text)
    if not m:
        raise ValueError(f"dspace quote not found for {author_value!r} / {advisor_rx!r}")
    q = m.group(0)
    name = author_value.split("(")[0].strip().rstrip(",. ")
    d = {"name": name, "display_name": display_name, "role": role, "years": [year, year] if year else None, "url": url,
         "sha256": sha, "quote": q}
    if note:
        d["note"] = note
    return d
