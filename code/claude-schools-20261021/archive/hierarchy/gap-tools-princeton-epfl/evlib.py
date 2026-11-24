"""Helpers for the per-school decision modules (decisions_<school>.py): every evidence item is resolved against a stored
capture in hierarchy/<school>/gap-captures.sqlite and its quote is checked to be an exact substring of one of the
capture's whitespace-collapsed text views (gapcap.texts) before it is written.
"""
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gapcap  # noqa: E402

_cache = {}


def _cap(school, url):
    k = (school, url)
    if k not in _cache:
        r = gapcap.cached(school, url)
        if not r:
            raise KeyError(f"no stored 200 capture for {url}")
        _cache[k] = (r, gapcap.texts(r["content"], r["content_type"]))
    return _cache[k]


def fold(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def name_in(name, quote):
    """The person's family name (or, for 'Last, First' forms, the part before the comma) occurs in the quote."""
    n = name.split(",")[0] if "," in name else name.split()[-1]
    return fold(n) in fold(quote) or fold(n.replace("-", " ")) in fold(quote)


def _out(r, quote, view):
    o = {"url": r["url"], "sha256": r["sha256"], "quote": quote}
    if r.get("capture_url"):
        o["capture_url"] = r["capture_url"]
    return o


def q(school, url, quote, name=None):
    """Evidence with a literal quote (whitespace is collapsed before checking)."""
    r, views = _cap(school, url)
    qq = gapcap.collapse(quote)
    for v, t in views.items():
        if qq in t:
            if name and not name_in(name, qq):
                raise ValueError(f"quote lacks the name {name!r}: {qq[:120]}")
            return _out(r, qq, v)
    raise ValueError(f"quote not found in {url}: {qq[:160]}")


def rx(school, url, pattern, name=None, group=0, flags=re.I | re.S, views=("html", "pdf", "raw"), nth=0):
    """Evidence whose quote is the (nth) regex match in the first text view that matches."""
    r, vs = _cap(school, url)
    for v in views:
        t = vs.get(v)
        if not t:
            continue
        ms = list(re.finditer(pattern, t, flags))
        if len(ms) > nth:
            qq = ms[nth].group(group).strip()
            if name and not name_in(name, qq):
                raise ValueError(f"match lacks the name {name!r}: {qq[:120]}")
            return _out(r, qq, v)
    raise ValueError(f"pattern not found in {url}: {pattern[:120]}")


def window(school, url, needle, name=None, before=120, after=120, heading=None, max_span=2500, views=("html", "pdf", "raw")):
    """Quote = text around the first occurrence of needle (case-insensitive, literal). With heading (a regex), the
    quote starts at the last heading match before the needle when it lies within max_span characters."""
    r, vs = _cap(school, url)
    for v in views:
        t = vs.get(v)
        if not t:
            continue
        i = t.lower().find(needle.lower())
        if i < 0:
            ft = fold(t)
            i = ft.find(fold(needle)) if len(ft) == len(t) else -1
        if i < 0:
            continue
        s = max(0, i - before)
        if heading:
            hs = [m.start() for m in re.finditer(heading, t[:i], re.I)]
            if hs and i - hs[-1] <= max_span:
                s = min(s, hs[-1])
        e = min(len(t), i + len(needle) + after)
        qq = t[s:e].strip()
        if name and not name_in(name, qq):
            raise ValueError(f"window lacks the name {name!r}")
        return _out(r, qq, v)
    raise ValueError(f"needle {needle!r} not found in {url}")


def student(school, url, name, role, years=None, needle=None, heading=None, before=60, after=80, max_span=2500, quote=None,
            pattern=None, note=None):
    """A student row; the quote names the student (and, with heading, starts at the section heading)."""
    if quote:
        ev = q(school, url, quote, name=name)
    elif pattern:
        ev = rx(school, url, pattern, name=name)
    else:
        ev = window(school, url, needle or name, name=name, before=before, after=after, heading=heading, max_span=max_span)
    row = {"name": name, "role": role, "years": years}
    row.update(ev)
    if note:
        row["note"] = note
    return row


def _nat(n):
    """'Last, First' -> 'First Last'."""
    if "," in n:
        a, b = n.split(",", 1)
        return f"{b.strip()} {a.strip()}"
    return n


def infoscience_theses(url, pi_surnames, from_year=2016, to_year=2026, role="phd", include_types=("thesis",)):
    """Student rows from a stored Infoscience discover page: theses whose dc.contributor.advisor names the PI.
    Quote preference: the Chicago citation ('... Supervised by <PI>. PhD thesis, EPFL, <year>.'), else the APA citation."""
    r, vs = _cap("epfl", url)
    raw = vs["raw"]
    j = json.loads(r["content"])
    rows = []
    for o in j["_embedded"]["searchResult"]["_embedded"]["objects"]:
        it = o["_embedded"]["indexableObject"]
        md = it.get("metadata") or {}
        val = lambda k: [x["value"] for x in md.get(k) or []]
        typ = (val("dc.type") or [""])[0]
        if not any(t in typ for t in include_types):
            continue
        advs = val("dc.contributor.advisor")
        if not any(fold(s) in fold(a) for a in advs for s in pi_surnames):
            continue
        y = (val("dc.date.issued") or val("dc.date.accepted") or [""])[0][:4]
        y = int(y) if y.isdigit() else None
        if y is None or y < from_year or y > to_year:
            continue
        au = (val("dc.contributor.author") or [""])[0]
        name = _nat(au)
        quote = None
        for k in ("epfl.citation.chicago", "epfl.citation.apa"):
            for c in val(k):
                c1 = gapcap.collapse(c)
                esc = gapcap.collapse(json.dumps(c, ensure_ascii=False)[1:-1])
                for cand in (c1, esc):
                    m_ = re.search(r"Supervised by (.*?)\. (?:PhD|Master|Doctoral)", cand)
                    if cand in raw and m_ and name_in(au, cand) and any(fold(s_) in fold(m_.group(1)) for s_ in pi_surnames):
                        quote = cand
                        break
                if quote:
                    break
            if quote:
                break
        if not quote:  # co-directed theses: the citation may name only the first director; quote the record's
            # advisor list through its author field instead (DSpace JSON keys are sorted, so they are adjacent)
            esc_au = re.escape(gapcap.collapse(json.dumps(au, ensure_ascii=False)[1:-1]))
            m_ = re.search(r'"dc\.contributor\.advisor" : \[ (?:(?!\]).)*?(?:%s)(?:(?!\]).)*?\], "dc\.contributor\.author" : \[ \{ "value" : "%s"'
                           % ("|".join(re.escape(s_) for s_ in pi_surnames), esc_au), raw)
            if m_:
                quote = m_.group(0)
        if not quote:
            raise ValueError(f"no citation quote for {au} in {url}")
        kind = "masters" if "master" in typ else ("phd" if "doctoral" in typ else role)
        row = {"name": name, "role": kind, "years": [y, y], "url": r["url"], "sha256": r["sha256"], "quote": quote,
               "note": f"Infoscience {typ}; dc.contributor.advisor = {advs}; handle {it.get('handle')}"}
        rows.append(row)
    return rows


def dedupe_students(rows):
    out, seen = [], {}
    for r in rows:
        k = fold(re.sub(r"[^A-Za-z ]", " ", r["name"])).split()
        k = (k[0], k[-1]) if k else ("", "")
        if k in seen:
            prev = out[seen[k]]
            if prev.get("years") and r.get("years"):
                prev["years"] = [min(prev["years"][0], r["years"][0]), max(prev["years"][1], r["years"][1])]
            continue
        seen[k] = len(out)
        out.append(r)
    return out


def _norm_title(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]", "", s)


def oa_author_quote(school, aid, name):
    """OpenAlex author record quote: id, orcid and display_name together (contains the name)."""
    res, j = gapcap.openalex(school, "authors/" + aid)
    url = res["url"]
    return dict(kind="openalex_author_record", **rx(school, url, r'"id": ?"https://openalex\.org/' + aid + r'".{0,200}?"display_name": ?"[^"]+"',
                                                    name=name, views=("raw",)),
                note=f"OpenAlex author {aid}")


def oa_verify(school, aid, page_url, surname, n=3, frm=2016, span=250, reach=4000, skip=(), manual=(), kind="own_publication_list_title"):
    """Evidence that OpenAlex author aid is the PI: n of the author's frm+ works whose titles appear on the PI's own
    publication list (page_url, stored). One item per work: the title as it stands on the PI's page, extended to the PI's
    surname when it occurs within span characters around the title, else back to the nearest earlier occurrence within
    reach characters (the page header); otherwise marked name_exempt (the page is the PI's own). The note names the OpenAlex
    work and the stored works response (filter author.id:<aid>) that lists it."""
    res, j = gapcap.oa_author_works(school, aid, frm)
    works_url, works_sha = res["url"], res["sha256"]
    rp, vp = _cap(school, page_url)
    t = vp.get("pdf") or vp.get("html") or vp.get("raw")
    ft = fold(t)
    same = len(ft) == len(t)
    idx, nt = [], []
    for i, ch in enumerate(t):
        for c in _norm_title(ch):
            nt.append(c); idx.append(i)
    nts = "".join(nt)
    sur = fold(surname)
    out, seen = [], set()
    for w in (j or {}).get("results", []):
        k = _norm_title(w.get("title"))
        wid = w["id"].rsplit("/", 1)[-1]
        if len(k) < 20 or k in seen or wid in skip:
            continue
        p = nts.find(k)
        if p < 0:
            continue
        me = [x for x in w.get("authorships") or [] if ((x.get("author") or {}).get("id") or "").endswith(aid)]
        if not me:
            continue
        s, e = idx[p], idx[p + len(k) - 1] + 1
        exempt = True
        if same:
            lo, hi = max(0, s - span), min(len(t), e + span)
            sp = [m.start() + lo for m in re.finditer(re.escape(sur), ft[lo:hi])]
            if sp:
                near = min(sp, key=lambda x: min(abs(x - s), abs(x - e)))
                s, e = min(s, near), max(e, near + len(sur))
                exempt = False
            else:
                b = ft.rfind(sur, max(0, s - reach), s)
                if b >= 0:
                    s, exempt = b, False
        pe = q(school, page_url, t[s:e])
        pe.update(kind=kind,
                  note=f"OpenAlex {wid} ({w.get('publication_year')}) '{w.get('title')}' is in the works of {aid} "
                       f"(stored response {works_url} sha256 {works_sha}) and is listed on " +
                       ("the PI's own publication list" if kind == "own_publication_list_title" else "the PI's DBLP person page"))
        if exempt:
            pe["name_exempt"] = True
        seen.add(k)
        out.append(pe)
        if len(out) >= n:
            break
    for wid, page_quote in manual:  # hand-matched: the page lists the work under a slightly different title
        w = next((w for w in (j or {}).get("results", []) if w["id"].endswith("/" + wid)), None)
        if w is None:
            raise ValueError(f"{wid} is not among the works of {aid}")
        pe = q(school, page_url, page_quote)
        pe.update(kind=kind,
                  note=f"OpenAlex {wid} ({w.get('publication_year')}) '{w.get('title')}' is in the works of {aid} "
                       f"(stored response {works_url} sha256 {works_sha}) and is listed on the PI's " +
                       ("own publication list" if kind == "own_publication_list_title" else "DBLP person page") +
                       " (matched by hand: title wording differs)")
        if not name_in(surname, pe["quote"]):
            pe["name_exempt"] = True
        out.append(pe)
    if len(out) < n:
        raise ValueError(f"only {len(out)} verified works for {aid} on {page_url}")
    return out


def oai_students(advisor_variants, sets_roles, from_year=2016, to_year=2026, exclude=()):
    """Princeton DataSpace (OAI-PMH, metadataPrefix=dim; stored pages) student rows: records whose contributor.advisor is
    one of advisor_variants ('Last, First' as written in DataSpace, prefix match). sets_roles maps setSpec -> role.
    Quote: the record's advisor field(s) through its author field, e.g. '<dim:field ... qualifier="advisor">Fan,
    Jianqing</dim:field> <dim:field ... qualifier="author">Xiao, Edward</dim:field>'."""
    import oai
    rows, seen = [], set()
    for st, role in sets_roles.items():
        for url, r, t in oai.pages({"verb": "ListRecords", "metadataPrefix": "dim", "set": st}):
            for x in oai.records(t):
                if not any(a.startswith(v) for a in x["advisor"] for v in advisor_variants):
                    continue
                y = re.match(r"\d{4}", x["issued"] or "")
                if not y or not (from_year <= int(y.group(0)) <= to_year) or not x["author"]:
                    continue
                y = int(y.group(0))
                au = x["author"][0]
                name = _nat(re.sub(r'\s*"[^"]*"', "", au)).strip()
                key = fold(name)
                if key in seen or au in exclude:
                    continue
                adv = r'(?:<dim:field mdschema="dc" element="contributor" qualifier="advisor"[^>]*>[^<]*</dim:field> ?)*'
                pat = (adv + r'<dim:field mdschema="dc" element="contributor" qualifier="advisor"[^>]*>(?:%s)[^<]*</dim:field> ?' % "|".join(map(re.escape, advisor_variants))
                       + adv + r'<dim:field mdschema="dc" element="contributor" qualifier="author"[^>]*>' + re.escape(gapcap.collapse(au).replace('"', "&quot;")) + r'</dim:field>')
                try:
                    ev = rx("princeton", url, pat, views=("raw",))
                except ValueError:
                    pat2 = pat.replace(re.escape(gapcap.collapse(au).replace('"', "&quot;")), re.escape(gapcap.collapse(au)))
                    ev = rx("princeton", url, pat2, views=("raw",))
                seen.add(key)
                row = {"name": name, "role": role, "years": [y, y]}
                row.update(ev)
                row["note"] = f"DataSpace {x['uri']} ({x['issued'][:10]}): '{x['title'][:120]}'; advisor field {x['advisor']}"
                rows.append(row)
    return rows
