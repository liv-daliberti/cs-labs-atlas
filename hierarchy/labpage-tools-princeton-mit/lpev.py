"""Evidence helpers for the lab-page decision modules (dec_<school>_<batch>.py).

Every member row is resolved against a stored status-200 capture (the worker-local store named by LPCAP_LOCAL, then
hierarchy/<school>/labpage-captures.sqlite): its quote is an exact substring of one of the capture's
whitespace-collapsed text views (lpcap.texts: visible HTML text, raw decoded bytes, or pdftotext) and contains every
token of the member's name (case- and diacritics-insensitive). A row that fails either check raises at construction.

Member row: {name, role, years, url, capture_url?, sha256, quote, note?}
roles: phd | postdoc | masters | undergraduate | member | other

Decision module shape:
    D[pi] = Lab(lab_site=..., people_page=..., students=[M(...), ...], pubs=[Pubs(url, spec) or P(...)], notes=...)
"""
import os
import re
import sqlite3
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lpcap  # noqa: E402

ROLES = {"phd", "postdoc", "masters", "undergraduate", "member", "other"}
_cache = {}


def _dbs(school):
    out = []
    loc = os.environ.get("LPCAP_LOCAL")
    if loc and os.path.exists(loc):
        out.append(loc)
    out.append(lpcap.DBS[school])
    for p in os.environ.get("LPCAP_EXTRA", "").split(":"):
        if p and os.path.exists(p) and p not in out:
            out.append(p)
    return out


def _find(school, src):
    is_sha = bool(re.fullmatch(r"[0-9a-f]{64}", src or ""))
    for p in _dbs(school):
        if not os.path.exists(p):
            continue
        con = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=60)
        try:
            if is_sha:
                row = con.execute(f"SELECT {lpcap.COLS} FROM captures WHERE sha256=? AND status=200 AND content IS NOT NULL "
                                  "AND error IS NULL ORDER BY id DESC LIMIT 1", (src,)).fetchone()
            elif lpcap.WAYBACK_RX.match(src):
                row = con.execute(f"SELECT {lpcap.COLS} FROM captures WHERE capture_url=? AND status=200 AND content IS NOT NULL "
                                  "AND error IS NULL ORDER BY id DESC LIMIT 1", (src,)).fetchone()
            else:
                row = con.execute(f"SELECT {lpcap.COLS} FROM captures WHERE (url=? OR final_url=?) AND capture_url IS NULL "
                                  "AND status=200 AND content IS NOT NULL AND error IS NULL ORDER BY (url=?) DESC, id DESC LIMIT 1",
                                  (src, src, src)).fetchone()
        except sqlite3.OperationalError:
            row = None
        con.close()
        if row:
            return lpcap._row(row)
    return None


def cap(school, src):
    """(row, views) of the newest stored 200 capture of src (live URL, Wayback id_ URL, or a sha256)."""
    k = (school, src)
    if k not in _cache:
        r = _find(school, src)
        if not r:
            raise KeyError(f"no stored 200 capture for {src} (fetch it first with f.py / wb3.py)")
        _cache[k] = (r, lpcap.texts(r["content"], r["content_type"]))
    return _cache[k]


def text(school, src, view=None):
    r, vs = cap(school, src)
    if view:
        return vs.get(view, "")
    return vs.get("pdf") or vs.get("html") or vs.get("raw") or ""


def fold(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = s.replace("ł", "l").replace("Ł", "L").replace("ø", "o").replace("Ø", "O").replace("ß", "ss").replace("đ", "d")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def norm(t):
    """Title key: folded, lowercase, letters and digits only (used to check that a quote contains a title)."""
    return re.sub(r"[^a-z0-9]+", "", fold(t or ""))


def name_tokens(name):
    n = re.sub(r"\([^)]*\)", " ", name)
    toks = [t for t in re.split(r"[^a-z0-9]+", fold(n)) if t]
    return [t for t in toks if len(t) > 1] or toks


def has_name(quote, name):
    """Every token (2+ chars; any length for a one-token name) of the name occurs as a word in the quote."""
    q = fold(quote)
    toks = [t for t in name_tokens(name) if t]
    return bool(toks) and all(re.search(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", q) for t in toks)


def _ev(r, quote):
    o = {"url": r["url"], "sha256": r["sha256"], "quote": quote}
    if r.get("capture_url"):
        o = {"url": r["url"], "capture_url": r["capture_url"], "sha256": r["sha256"], "quote": quote}
    return o


def _check_name(name, qq):
    if name and not has_name(qq, name):
        raise ValueError(f"quote lacks the name {name!r}: {qq[:200]}")


def q(school, src, quote, name=None):
    r, views = cap(school, src)
    qq = lpcap.collapse(quote)
    for v, t in views.items():
        if qq in t:
            _check_name(name, qq)
            return _ev(r, qq)
    raise ValueError(f"quote not found in {src}: {qq[:200]}")


def se(school, src, start, end, name=None, after=None, max_span=1500, views=("html", "pdf", "raw")):
    """Quote from the last occurrence of `start` before the first occurrence of `end` (searched from `after` when given)
    through the end of `end`. Raises when the span would exceed max_span."""
    r, vs = cap(school, src)
    for v in views:
        t = vs.get(v)
        if not t:
            continue
        base = 0
        if after:
            a = t.find(after)
            if a < 0:
                continue
            base = a
        j = t.find(end, base)
        if j < 0:
            continue
        if start:
            i = t.rfind(start, base, j + 1)
            if i < 0:
                continue
            if (j + len(end) - i) > max_span:
                raise ValueError(f"span {start!r}..{end!r} is {j + len(end) - i} chars (> {max_span}) in {src}")
            qq = t[i:j + len(end)]
        else:
            qq = end
        qq = qq.strip()
        _check_name(name, qq)
        return _ev(r, qq)
    raise ValueError(f"markers {start!r} / {end!r} not found in {src}")


def rx(school, src, pattern, name=None, group=0, flags=re.I | re.S, views=("html", "pdf", "raw"), nth=0):
    r, vs = cap(school, src)
    for v in views:
        t = vs.get(v)
        if not t:
            continue
        ms = list(re.finditer(pattern, t, flags))
        if len(ms) > nth:
            qq = ms[nth].group(group).strip()
            _check_name(name, qq)
            return _ev(r, qq)
    raise ValueError(f"pattern not found in {src}: {pattern[:160]}")


def M(school, name, role, years, src, quote=None, start=None, end=None, pattern=None, after=None, note=None,
      max_span=1500):
    """A member row. Give exactly one of: quote (literal), end (+ start heading; quote = heading..end), pattern (regex).
    `name` is the name as written on the page; years = [first, last] when the source states them, else None."""
    if role not in ROLES:
        raise ValueError(f"bad role {role}")
    if years is not None:
        assert isinstance(years, (list, tuple)) and len(years) == 2 and all(y is None or isinstance(y, int) for y in years), years
    if quote is not None:
        ev = q(school, src, quote, name=name)
    elif end is not None:
        ev = se(school, src, start, end, name=name, after=after, max_span=max_span)
    elif pattern is not None:
        ev = rx(school, src, pattern, name=name)
    else:
        raise ValueError("M needs quote, end or pattern")
    row = {"name": name, "role": role, "years": list(years) if years else None}
    row.update(ev)
    if note:
        row["note"] = note
    return row


def MS(school, src, role, names, heading, years=None, note=None, max_span=1500, after=None):
    """Rows for several members listed under one heading: each quote runs from `heading` (its last occurrence before
    the name, searched from `after` when given) to the name as written."""
    return [M(school, n, role, years, src, start=heading, end=n, after=after, note=note, max_span=max_span) for n in names]


def P(school, title, year, src, venue=None, links=None, quote=None, note=None):
    """A manually listed publication entry (for pages the extractor cannot parse). quote defaults to the title and
    must be an exact substring of the page text and contain the title."""
    r, views = cap(school, src)
    qq = lpcap.collapse(quote or title)
    if not any(qq in t for t in views.values()):
        raise ValueError(f"pub quote not found in {src}: {qq[:160]}")
    if norm(title)[:40] not in norm(qq):
        raise ValueError(f"pub quote does not contain the title: {title[:80]}")
    o = {"title": lpcap.collapse(title), "year": year, "venue": venue, "links": links or []}
    o.update(_ev(r, qq))
    if note:
        o["note"] = note
    return o


def Pubs(url, spec=None, years=(2016, 2026), note=None):
    """A publications page to run through pubx.extract at build time (spec: see pubx.py)."""
    return {"pubs_page": url, "spec": spec or {}, "years": list(years), "note": note}


def Lab(lab_site=None, people_page=None, students=(), pubs=(), notes="", other_pages=()):
    return {"lab_site": lab_site, "people_page": people_page, "students": list(students), "pubs": list(pubs),
            "notes": notes, "other_pages": list(other_pages)}
