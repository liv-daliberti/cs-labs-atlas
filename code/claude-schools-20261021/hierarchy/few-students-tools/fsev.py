"""Evidence helpers for the few-students decision modules (decisions_<school>.py).

Every student row is resolved against a stored 200 capture in hierarchy/<school>/few-students-captures.sqlite; its quote
is an exact substring of one of the capture's whitespace-collapsed text views (fscap.texts) and contains every token of
the student's name (case- and diacritics-insensitive). Nothing is written that fails either check.

Row shape: {name, role, years, url, capture_url?, sha256, quote, note?}
roles: phd | postdoc | masters | undergraduate | member | other
"""
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fscap  # noqa: E402

ROLES = {"phd", "postdoc", "masters", "undergraduate", "member", "other"}
_cache = {}


def cap(school, src):
    """(row, views) for the newest stored 200 capture of src: a Wayback id_ URL matches capture_url; a live URL matches
    url (or final_url) of a live row."""
    k = (school, src)
    if k not in _cache:
        r = fscap.cached(school, src, sister=False)
        if not r and not fscap.WAYBACK_RX.match(src):
            con = fscap.connect(school)
            row = con.execute(f"SELECT {fscap.COLS} FROM captures WHERE final_url=? AND capture_url IS NULL AND status=200 "
                              "AND content IS NOT NULL AND error IS NULL ORDER BY id DESC LIMIT 1", (src,)).fetchone()
            con.close()
            r = fscap._row(row) if row else None
        if not r:
            raise KeyError(f"no stored 200 capture for {src}")
        _cache[k] = (r, fscap.texts(r["content"], r["content_type"]))
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


def name_tokens(name):
    n = re.sub(r"\([^)]*\)", " ", name)
    return [t for t in re.split(r"[^a-z0-9]+", fold(n)) if len(t) > 1]


def has_name(quote, name):
    """Every token (2+ chars) of the name occurs as a word in the quote (case/diacritics-insensitive, any order)."""
    q = fold(quote)
    toks = name_tokens(name)
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
    """Evidence with a literal quote (whitespace collapsed before checking)."""
    r, views = cap(school, src)
    qq = fscap.collapse(quote)
    for v, t in views.items():
        if qq in t:
            _check_name(name, qq)
            return _ev(r, qq)
    raise ValueError(f"quote not found in {src}: {qq[:200]}")


def se(school, src, start, end, name=None, after=None, max_span=1500, views=("html", "pdf", "raw")):
    """Quote from the last occurrence of `start` before the first occurrence of `end` (searched after `after` when given)
    through the end of `end`. Falls back to `end` alone when the span would exceed max_span."""
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
        i = t.rfind(start, base, j + 1) if start else -1
        if i >= 0 and (j + len(end) - i) <= max_span:
            qq = t[i:j + len(end)]
        else:
            qq = end
        qq = qq.strip()
        _check_name(name, qq)
        return _ev(r, qq)
    raise ValueError(f"end marker {end!r} not found in {src}")


def rx(school, src, pattern, name=None, group=0, flags=re.I | re.S, views=("html", "pdf", "raw"), nth=0):
    """Evidence whose quote is the (nth) regex match in the first text view that matches."""
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


def S(school, name, role, years, src, quote=None, start=None, end=None, pattern=None, after=None, note=None, max_span=1500):
    """A student row. Give exactly one of: quote (literal), end (+ optional start heading), pattern (regex)."""
    if role not in ROLES:
        raise ValueError(f"bad role {role}")
    if years is not None:
        assert isinstance(years, (list, tuple)) and len(years) == 2, years
    if quote is not None:
        ev = q(school, src, quote, name=name)
    elif end is not None:
        ev = se(school, src, start, end, name=name, after=after, max_span=max_span)
    elif pattern is not None:
        ev = rx(school, src, pattern, name=name)
    else:
        raise ValueError("S needs quote, end or pattern")
    row = {"name": name, "role": role, "years": list(years) if years else None}
    row.update(ev)
    if note:
        row["note"] = note
    return row


def nat(n):
    """'Last, First' -> 'First Last' (parenthesised expansions dropped)."""
    n = re.sub(r"\s*\([^)]*\)", "", n).strip().rstrip(".")
    if "," in n:
        a, b = n.split(",", 1)
        return f"{b.strip()} {a.strip()}"
    return n


def dedupe(rows):
    """Merge rows naming the same person (first + last token after folding); widen years."""
    out, seen = [], {}
    for r in rows:
        k = [t for t in re.split(r"[^a-z]+", fold(r["name"])) if t]
        k = (k[0], k[-1]) if k else ("", "")
        if k in seen:
            prev = out[seen[k]]
            if prev.get("years") and r.get("years"):
                ys = [y for y in (prev["years"] + r["years"]) if y]
                if ys:
                    prev["years"] = [min(ys), max(ys)]
            continue
        seen[k] = len(out)
        out.append(r)
    return out


# ================================================================ Princeton DataSpace OAI-PMH
OAI = "https://dataspace.princeton.edu/oai/request?"


def oai_pages(params, school="princeton"):
    from urllib.parse import urlencode
    url = OAI + urlencode(params)
    while url:
        r = fscap.fetch(school, url)
        if r.get("status") != 200:
            print("FAIL", url, r.get("status"), r.get("error"), flush=True)
            return
        t = r["content"].decode("utf-8", "replace")
        yield url, r, t
        m = re.search(r"<resumptionToken[^>]*>([^<]+)</resumptionToken>", t)
        url = OAI + urlencode({"verb": params["verb"], "resumptionToken": m.group(1)}) if m else None


def oai_records(t):
    for rec in re.findall(r"<record>(.*?)</record>", t, flags=re.S):
        f = lambda el, qual=None: [fscap.collapse(re.sub(r"<[^>]+>", "", v)) for v in re.findall(
            r'<dim:field mdschema="dc" element="%s"%s[^>]*>(.*?)</dim:field>' % (el, (' qualifier="%s"' % qual) if qual else ""), rec, flags=re.S)]
        yield dict(id=(re.findall(r"<identifier>([^<]+)</identifier>", rec) or [""])[0], title=(f("title") or [""])[0],
                   author=f("contributor", "author"), advisor=f("contributor", "advisor"), issued=(f("date", "issued") or [""])[0],
                   uri=(f("identifier", "uri") or [""])[0], sets=re.findall(r"<setSpec>([^<]+)</setSpec>", rec))


def oai_find(advisor_rx, sets, school="princeton"):
    """(set, url, record) for stored/fetched records whose contributor.advisor matches advisor_rx (case-insensitive)."""
    out = []
    for st in sets:
        for url, r, t in oai_pages({"verb": "ListRecords", "metadataPrefix": "dim", "set": st}, school):
            for x in oai_records(t):
                if any(re.search(advisor_rx, a, re.I) for a in x["advisor"]):
                    out.append((st, url, x))
    return out


def oai_students(advisor_variants, sets_roles, from_year=2016, to_year=2026, exclude=(), school="princeton"):
    """Student rows from DataSpace OAI-PMH (metadataPrefix=dim) records whose contributor.advisor starts with one of
    advisor_variants ('Last, First' as DataSpace writes it). sets_roles maps setSpec -> role. Quote: the record's advisor
    field(s) through its author field, e.g. '<dim:field ... qualifier="advisor">Stellato, Bartolomeo</dim:field>
    <dim:field ... qualifier="author">Hua, Yixuan</dim:field>' (exact bytes of the stored OAI page, whitespace-collapsed)."""
    rows, seen = [], set()
    for st, role in sets_roles.items():
        for url, r, t in oai_pages({"verb": "ListRecords", "metadataPrefix": "dim", "set": st}, school):
            for x in oai_records(t):
                if not any(a.startswith(v) for a in x["advisor"] for v in advisor_variants):
                    continue
                y = re.match(r"\d{4}", x["issued"] or "")
                if not y or not (from_year <= int(y.group(0)) <= to_year) or not x["author"]:
                    continue
                y = int(y.group(0))
                au = x["author"][0]
                name = nat(re.sub(r'\s*"[^"]*"', "", au)).strip()
                key = fold(name)
                if key in seen or au in exclude or name in exclude:
                    continue
                adv = r'(?:<dim:field mdschema="dc" element="contributor" qualifier="advisor"[^>]*>[^<]*</dim:field> ?)*'
                pat = (adv + r'<dim:field mdschema="dc" element="contributor" qualifier="advisor"[^>]*>(?:%s)[^<]*</dim:field> ?'
                       % "|".join(map(re.escape, advisor_variants)) + adv +
                       r'<dim:field mdschema="dc" element="contributor" qualifier="author"[^>]*>%s</dim:field>')
                ev = None
                for form in (fscap.collapse(au).replace('"', "&quot;"), fscap.collapse(au)):
                    try:
                        ev = rx(school, url, pat % re.escape(form), name=name, views=("raw",))
                        break
                    except ValueError:
                        continue
                if ev is None:
                    raise ValueError(f"no OAI quote for {au} in {url}")
                seen.add(key)
                row = {"name": name, "role": role, "years": [y, y]}
                row.update(ev)
                row["note"] = f"DataSpace {x['uri']} ({x['issued'][:10]}, set {st}): '{x['title'][:120]}'; advisor field {x['advisor']}"
                rows.append(row)
    return rows


# ================================================================ EPFL
EPFL_HEADS = [("Past EPFL PhD Students as codirector", "codirector"), ("Past EPFL PhD Students", "past"), ("PhD Students", "current")]
EPFL_STOP = r"(?=\s(?:Past EPFL PhD Students|Courses|Contact EPFL|Teaching & PhD|Awards|Publications|Research|Infoscience|Mentor of)\b|$)"


def _cap_year(r):
    m = re.search(r"/web/(\d{4})", r.get("capture_url") or "")
    if m:
        return int(m.group(1))
    return int((r.get("fetched_at") or "2026")[:4])


def epfl_people_students(src, from_year=2016, include_current=True, exclude=(), school="epfl"):
    """Rows from a people.epfl.ch profile's 'PhD Students' / 'Past EPFL PhD Students [as codirector]' lists. Each quote runs
    from the section heading to the student's name (with defence year when given)."""
    r, views = cap(school, src)
    t = views.get("html") or views.get("raw")
    cy = _cap_year(r)
    rows = []
    for m in re.finditer(r"(Past EPFL PhD Students as codirector|Past EPFL PhD Students|(?<!Past EPFL )PhD Students)\s(.*?)" + EPFL_STOP, t):
        head, body = m.group(1), m.group(2)
        kind = dict(EPFL_HEADS)[head]
        if kind == "current" and not include_current:
            continue
        start, pos = m.start(1), m.start(2)
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
                years = [cy, cy]
            quote = t[start:i + len(part)]
            ev = q(school, src, quote, name=name)
            note = {"current": "current doctoral student listed on the director's EPFL profile (capture year)",
                    "past": "thesis directed (defence year) per the director's EPFL profile",
                    "codirector": "thesis co-directed (defence year) per the co-director's EPFL profile"}[kind]
            row = {"name": name, "role": "phd", "years": years, "note": note}
            row.update(ev)
            rows.append(row)
    return rows


def infoscience_theses(src, pi_surnames, from_year=2016, to_year=2026, school="epfl"):
    """Rows from a stored Infoscience discover JSON page: theses whose dc.contributor.advisor names the PI. Quote: the
    citation '... Supervised by <PI>. PhD thesis, EPFL, <year>.' when present, else the advisor-through-author JSON span."""
    r, vs = cap(school, src)
    raw = vs["raw"]
    j = json.loads(r["content"])
    rows = []
    for o in j["_embedded"]["searchResult"]["_embedded"]["objects"]:
        it = o["_embedded"]["indexableObject"]
        md = it.get("metadata") or {}
        val = lambda k: [x["value"] for x in md.get(k) or []]
        typ = (val("dc.type") or [""])[0]
        if "thesis" not in typ:
            continue
        advs = val("dc.contributor.advisor")
        if not any(fold(s) in fold(a) for a in advs for s in pi_surnames):
            continue
        y = (val("dc.date.issued") or val("dc.date.accepted") or [""])[0][:4]
        y = int(y) if y.isdigit() else None
        if y is None or y < from_year or y > to_year:
            continue
        au = (val("dc.contributor.author") or [""])[0]
        name = nat(au)
        quote = None
        for k in ("epfl.citation.chicago", "epfl.citation.apa"):
            for c in val(k):
                for cand in (fscap.collapse(c), fscap.collapse(json.dumps(c, ensure_ascii=False)[1:-1])):
                    m_ = re.search(r"Supervised by (.*?)\. (?:PhD|Master|Doctoral)", cand)
                    if cand in raw and m_ and has_name(cand, name) and any(fold(s_) in fold(m_.group(1)) for s_ in pi_surnames):
                        quote = cand
                        break
                if quote:
                    break
            if quote:
                break
        if not quote:
            esc_au = re.escape(fscap.collapse(json.dumps(au, ensure_ascii=False)[1:-1]))
            m_ = re.search(r'"dc\.contributor\.advisor" : \[ (?:(?!\]).)*?(?:%s)(?:(?!\]).)*?\], "dc\.contributor\.author" : \[ \{ "value" : "%s"'
                           % ("|".join(re.escape(s_) for s_ in pi_surnames), esc_au), raw)
            if m_ and has_name(m_.group(0), name):
                quote = m_.group(0)
        if not quote:
            raise ValueError(f"no citation quote for {au} in {src}")
        kind = "masters" if "master" in typ.lower() else "phd"
        row = {"name": name, "role": kind, "years": [y, y], "url": r["url"], "sha256": r["sha256"], "quote": quote,
               "note": f"Infoscience {typ}; dc.contributor.advisor = {advs}; handle {it.get('handle')}"}
        if r.get("capture_url"):
            row["capture_url"] = r["capture_url"]
        rows.append(row)
    return rows


# ================================================================ MIT DSpace
def dspace_items(school, src):
    r, vs = cap(school, src)
    j = json.loads(r["content"])
    for o in j["_embedded"]["searchResult"]["_embedded"]["objects"]:
        it = o["_embedded"]["indexableObject"]
        md = it.get("metadata") or {}
        yield it, {k: [x["value"] for x in v] for k, v in md.items()}


def dspace_theses(src, advisor_rx, from_year=2016, to_year=2026, school="mit", exclude=()):
    """Rows from a stored DSpace@MIT discover JSON response: items whose dc.contributor.advisor matches advisor_rx.
    Quote: the raw JSON span from '"dc.contributor.advisor" : [' through the author's value (keys are sorted, so the
    advisor and author fields are adjacent), which names both the supervisor and the student."""
    r, vs = cap(school, src)
    raw = vs["raw"]
    rows = []
    for it, md in dspace_items(school, src):
        advs = md.get("dc.contributor.advisor", [])
        if not any(re.search(advisor_rx, a, re.I) for a in advs):
            continue
        y = (md.get("dc.date.issued") or [""])[0][:4]
        y = int(y) if y.isdigit() else None
        if y is None or y < from_year or y > to_year:
            continue
        au = (md.get("dc.contributor.author") or [""])[0]
        name = nat(au)
        if name in exclude or au in exclude:
            continue
        esc_au = re.escape(fscap.collapse(json.dumps(au, ensure_ascii=False)[1:-1]))
        m_ = re.search(r'"dc\.contributor\.advisor" : \[ (?:(?!\], ").)*?\], "dc\.contributor\.author" : \[ \{ "value" : "%s"' % esc_au, raw)
        if not m_ or not any(re.search(advisor_rx, m_.group(0), re.I) for _ in [0]):
            raise ValueError(f"no DSpace quote for {au} in {src}")
        desc = " ".join(md.get("dc.description", []) + md.get("dc.description.degree", []))
        role = "phd" if re.search(r"Ph\. ?D|Sc\. ?D", desc) else ("masters" if re.search(r"S\.M\.|M\. ?Eng|M\.B\.A|S\.M|Master", desc) else
                                                                ("undergraduate" if re.search(r"S\.B\.|B\.S\.", desc) else "other"))
        quote = m_.group(0)
        if not has_name(quote, name):
            raise ValueError(f"DSpace quote lacks {name}: {quote[:200]}")
        row = {"name": name, "role": role, "years": [y, y], "url": r["url"], "sha256": r["sha256"], "quote": quote,
               "note": f"DSpace@MIT {it.get('handle')} ({y}): {desc[:160]}; advisor {advs}"}
        if r.get("capture_url"):
            row["capture_url"] = r["capture_url"]
        rows.append(row)
    return rows


# ================================================================ Berkeley EECS dissertations-by-faculty
def eecs_dissertations(src, heading, from_year=2016, school="berkeley", max_span=700):
    """Rows from a stored www2.eecs.berkeley.edu/Pubs/Dissertations/Faculty/<id>.html page ('Ph.D. Dissertations - <PI>'):
    each entry 'Title Student [year]'. Quote = heading through the entry when short enough, else the entry alone."""
    from bs4 import BeautifulSoup
    r, vs = cap(school, src)
    soup = BeautifulSoup(fscap.decode(r["content"]), "lxml")
    main = soup.find(id="site-main") or soup.find("main") or soup
    t = vs["html"]
    rows = []
    for p in main.find_all("p"):
        a = p.find("a")
        txt = fscap.collapse(p.get_text(" "))
        mm = re.search(r"^(.*?)\s*\[(\d{4})\]\s*$", txt)
        if not a or not mm:
            continue
        title = fscap.collapse(a.get_text(" "))
        rest = mm.group(1)
        student = rest[len(title):].strip() if rest.startswith(title) else rest
        y = int(mm.group(2))
        if y < from_year:
            continue
        entry = txt
        ev = se(school, src, heading, entry, name=student, max_span=max_span)
        row = {"name": student, "role": "phd", "years": [y, y], "note": f"EECS Ph.D. dissertation ({y}): {title[:120]}"}
        row.update(ev)
        rows.append(row)
    return rows
