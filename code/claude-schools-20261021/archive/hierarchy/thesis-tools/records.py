"""Normalized thesis records from the stored captures (hierarchy/<school>/thesis-captures.sqlite; read-only here).

Every record: {school, source, id, url, capture_url, sha256, student (natural order), author_raw, advisers [raw adviser
person strings], year, role (phd|masters|undergraduate|other), degree, dept, cs (CS-relevant collection), title, q}
where q(adviser_raw) returns a quote (an exact substring of one whitespace-collapsed text view of the stored capture)
that names the student and the adviser relation, or raises ValueError.

Sources: Princeton DataSpace OAI-PMH (dim); MIT DSpace REST discover JSON; EPFL Infoscience REST discover JSON;
Berkeley EECS dissertations-by-year pages and EECS technical-report pages; CMU SCS report-archive abstract pages and
KiltHub (figshare API) article JSON.
"""
import json
import os
import re
import sqlite3
import sys
import unicodedata
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tcap  # noqa: E402
import names  # noqa: E402

Y0, Y1 = 2016, 2026
collapse = tcap.collapse


def rows(school, like):
    con = sqlite3.connect(f"file:{tcap.DBS[school]}?mode=ro", uri=True, timeout=120)
    out = con.execute("SELECT id, url, capture_url, sha256, content_type, content FROM captures WHERE url LIKE ? AND status=200 "
                      "AND content IS NOT NULL AND error IS NULL ORDER BY id", (like,)).fetchall()
    con.close()
    seen, res = set(), []
    for rid, url, cap, sha, ct, content in out:  # newest capture of a URL wins
        res.append((rid, url, cap, sha, ct, content))
    latest = {}
    for r in res:
        latest[(r[1], r[2])] = r
    for r in sorted(latest.values()):
        if r[3] in seen:
            continue
        seen.add(r[3])
        yield r[1], r[2], r[3], r[4], zlib.decompress(r[5])


class View:
    """Lazy whitespace-collapsed text views of one capture."""
    _cache = {}

    def __init__(self, content, ctype, sha):
        self.content, self.ctype, self.sha = content, ctype, sha

    def views(self):
        if self.sha not in View._cache:
            if len(View._cache) > 64:
                View._cache.clear()
            View._cache[self.sha] = tcap.texts(self.content, self.ctype)
        return View._cache[self.sha]

    def check(self, quote):
        qq = collapse(quote)
        if not any(qq in t for t in self.views().values()):
            raise ValueError(f"quote not in capture {self.sha[:12]}: {qq[:160]}")
        return qq


def year_of(s):
    m = re.search(r"(19|20)\d\d", s or "")
    return int(m.group(0)) if m else None


def rec(**kw):
    kw.setdefault("capture_url", None)
    return kw


# ====================================================================== Princeton (DataSpace OAI-PMH, dim)
P_SETS = None


def princeton():
    import harvest_princeton as hp
    out, seen = [], set()
    cs_sets = {"col_88435_dsp018c97kq43p", "col_88435_dsp01mp48sc83w", "col_88435_dsp010z709067j"}
    for url, cap, sha, ct, content in rows("princeton", "https://dataspace.princeton.edu/oai/request?verb=ListRecords%"):
        t = content.decode("utf-8", "replace")
        view = View(content, ct, sha)
        for m in re.finditer(r"<record>(.*?)</record>", t, flags=re.S):
            body = m.group(1)
            oid = (re.findall(r"<identifier>([^<]+)</identifier>", body) or [""])[0]
            sets = re.findall(r"<setSpec>([^<]+)</setSpec>", body)
            kinds = {hp.SETS[s][0] for s in sets if s in hp.SETS}
            if not kinds:
                continue

            def f(el, qual=None):
                return [collapse(re.sub(r"<[^>]+>", "", v)) for v in re.findall(
                    r'<dim:field mdschema="dc" element="%s"%s[^>]*>(.*?)</dim:field>' % (el, (' qualifier="%s"' % qual) if qual else ""), body, flags=re.S)]
            adv = f("contributor", "advisor")
            au = f("contributor", "author")
            y = year_of((f("date", "issued") or [""])[0])
            if not au or not adv or y is None or not (Y0 <= y <= Y1) or oid in seen:
                continue
            seen.add(oid)
            kind = "dissertations" if "dissertations" in kinds else ("masters" if "masters" in kinds else "senior")
            role = {"dissertations": "phd", "masters": "masters", "senior": "undergraduate"}[kind]
            other = f("contributor", "other")
            dept = "; ".join(other) or "; ".join(hp.SETS[s][1] for s in sets if s in hp.SETS)
            cs = bool(set(sets) & cs_sets) or any(re.search(r"Computer Science", o) for o in other)
            au0 = au[0]

            def q(adv_raw, body=body, view=view, au0=au0):
                i = body.find('<dim:field mdschema="dc" element="contributor" qualifier="advisor"')
                k = body.find('<dim:field mdschema="dc" element="contributor" qualifier="author"')
                e = body.find("</dim:field>", k)
                if i < 0 or k < 0 or e < 0:
                    raise ValueError("no advisor/author fields")
                lo, hi = min(i, k), max(e + len("</dim:field>"), body.find("</dim:field>", i) + len("</dim:field>"))
                span = body[lo:hi]
                if len(span) > 3000:
                    raise ValueError("advisor/author fields not adjacent")
                qq = view.check(span)
                if not names.has_tokens(qq, names.nat(au0)) or not names.has_tokens(qq, names.nat(adv_raw)):
                    raise ValueError("quote lacks a name")
                return qq
            out.append(rec(school="princeton", source="dataspace-oai", id=oid, url=url, capture_url=cap, sha256=sha,
                           student=names.nat(re.sub(r'\s*"[^"]*"', "", au0)), author_raw=au0,
                           advisers=[a for v in adv for a in names.split_advisers(v, "inverted")], year=y, role=role,
                           degree=kind, dept=dept, cs=cs, title=(f("title") or [""])[0][:200],
                           handle=(f("identifier", "uri") or [""])[0], q=q))
    return out


# ====================================================================== DSpace REST discover JSON (MIT, EPFL)
def dspace_items(content):
    j = json.loads(content)
    for o in j["_embedded"]["searchResult"]["_embedded"]["objects"]:
        it = o["_embedded"]["indexableObject"]
        md = {k: [x["value"] for x in v] for k, v in (it.get("metadata") or {}).items()}
        yield it, md


def dspace_quote(view, au, adv_raw):
    """'"dc.contributor.advisor" : [ ... <adviser> ... ], "dc.contributor.author" : [ { "value" : "<author>"' in the raw
    JSON view (metadata keys are sorted, so the two fields are adjacent)."""
    raw = view.views().get("raw", "")
    esc_au = re.escape(collapse(json.dumps(au, ensure_ascii=False)[1:-1]))
    esc_adv = re.escape(collapse(json.dumps(adv_raw, ensure_ascii=False)[1:-1]))
    for m_ in re.finditer(r'"dc\.contributor\.advisor" : \[ (?:(?!\], ").)*?\], "dc\.contributor\.author" : \[ \{ "value" : "%s"' % esc_au, raw):
        if re.search(esc_adv, m_.group(0)):
            return m_.group(0)
    esc_au2 = re.escape(collapse(json.dumps(au)[1:-1]))
    if esc_au2 != esc_au:
        for m_ in re.finditer(r'"dc\.contributor\.advisor" : \[ (?:(?!\], ").)*?\], "dc\.contributor\.author" : \[ \{ "value" : "%s"' % esc_au2, raw):
            return m_.group(0)
    raise ValueError(f"no DSpace advisor/author span for {au}")


MIT_SCHOOL = re.compile(r"\s*,?\s*(?:Massachusetts Institute of Technology|Sloan School of Management|Department of|Program in)\b.*$")
MIT_TRAIL = re.compile(r"[\s,]*(?:Ph\.?\s?D|M\.?\s?Eng|S\.?\s?M|S\.?\s?B|Sc\.?\s?D|M\.?\s?B\.?\s?A|M\.?\s?S|M\.?\s?Arch|Eng|Nav\.?\s?E|Jr|Sr|II|III|IV|Lieutenant|Commander|Captain|Major|\d{4}-(?:\d{4})?)\.?\s*$")


def mit_author(au):
    """'Deng, Xinyue, M. Eng. Massachusetts Institute of Technology' -> 'Deng, Xinyue'; degree, school and Jr/III dropped."""
    a = MIT_SCHOOL.sub("", re.sub(r"\s*\(.*$", "", au))
    while MIT_TRAIL.search(a) and MIT_TRAIL.sub("", a) != a:
        a = MIT_TRAIL.sub("", a)
    a = MIT_RANK_TAIL.sub("", a)  # 'Herrling, Austin Donald, First Lieutenant' (2026-10-27)
    a = MIT_RANK_HEAD.sub(r"\1", a)  # 'Denove, ENS George Thomas' / 'Schatz, Ensign Nathan Caleb'
    return a.strip().rstrip(",").strip()


MIT_RANK_TAIL = re.compile(r"\s*,\s*(?:First|Second)\s*$")
MIT_RANK_HEAD = re.compile(r"^([^,]+,\s*)(?:ENS|Ensign|LTJG|LT|Lieutenant|Captain|Major|Commander|LCDR|CDR|Cadet|Midshipman)\s+(?=[A-Z])")


def mit_role(md):
    deg = " ".join(md.get("dc.description.degree", []) + md.get("mit.thesis.degree", []) + [d for d in md.get("dc.description", []) if d.startswith("Thesis")])
    if re.search(r"Ph\.? ?D|Sc\.? ?D|Doctoral|Doctor", deg):
        return "phd", deg
    if re.search(r"S\.? ?M\.?|M\.? ?Eng|M\.B\.A|Master|M\.? ?Arch|M\.C\.P|Engineer", deg):
        return "masters", deg
    if re.search(r"S\.? ?B\.?|B\.? ?S\.?|Bachelor|Undergrad", deg):
        return "undergraduate", deg
    return "other", deg


def mit():
    out, seen = [], set()
    for url, cap, sha, ct, content in rows("mit", "https://dspace.mit.edu/server/api/discover/search/objects?%"):
        try:
            items = list(dspace_items(content))
        except Exception:
            continue
        view = View(content, ct, sha)
        for it, md in items:
            h = it.get("handle")
            if (md.get("dc.type") or [""])[0].lower() not in ("thesis", "") and "Thesis" not in " ".join(md.get("dc.description", [])):
                continue
            advs = md.get("dc.contributor.advisor", [])
            au = (md.get("dc.contributor.author") or [""])[0]
            y = year_of((md.get("dc.date.issued") or [""])[0])
            if not advs or not au or y is None or not (Y0 <= y <= Y1) or h in seen:
                continue
            seen.add(h)
            role, deg = mit_role(md)
            dept = "; ".join(md.get("dc.relation.orgunit", []) or md.get("dc.contributor.department", []) or md.get("dc.contributor.other", []))
            cs = bool(re.search(r"Electrical Engineering and Computer Science", dept)) or "EECS" in md.get("mit.thesis.department", [])

            def q(adv_raw, view=view, au=au, advs=advs):
                val = next((v for v in advs if adv_raw in v or names.has_tokens(v, names.nat(adv_raw))), advs[0])
                qq = view.check(dspace_quote(view, au, val))
                if not names.has_tokens(qq, names.nat(au)):
                    raise ValueError("quote lacks the student")
                return qq
            out.append(rec(school="mit", source="dspace-discover", id=h, url=url, capture_url=cap, sha256=sha,
                           student=names.nat(mit_author(au)), author_raw=au,  # "Xia, Yu(Scientist in ...)Massachusetts Institute of Technology."
                           advisers=[a for v in advs for a in names.split_advisers(v, "natural")],
                           adviser_values=advs, year=y, role=role, degree=deg[:120], dept=dept[:200], cs=cs,
                           title=(md.get("dc.title") or [""])[0][:200], handle=h, q=q))
    return out


def epfl():
    out, seen = [], set()
    for url, cap, sha, ct, content in rows("epfl", "https://infoscience.epfl.ch/server/api/discover/search/objects?%"):
        try:
            items = list(dspace_items(content))
        except Exception:
            continue
        view = View(content, ct, sha)
        for it, md in items:
            h = it.get("handle")
            typ = (md.get("dc.type") or [""])[0]
            if "thesis" not in typ:
                continue
            advs = md.get("dc.contributor.advisor", [])
            au = (md.get("dc.contributor.author") or [""])[0]
            y = year_of((md.get("dc.date.issued") or md.get("dc.date.accepted") or [""])[0])
            if not advs or not au or y is None or not (Y0 <= y <= Y1) or h in seen:
                continue
            seen.add(h)
            role = "masters" if "master" in typ else ("phd" if "doctoral" in typ else "other")
            school_ = "; ".join(md.get("epfl.thesis.doctoralSchool", []))
            sec = "; ".join(md.get("epfl.thesis.section", []) + md.get("epfl.studentwork.section", []) + md.get("epfl.section", []))
            fac = "; ".join(md.get("epfl.thesis.faculty", []))
            dept = "; ".join(x for x in (school_, fac, sec, "; ".join(md.get("epfl.thesis.originalUnit", []))) if x)
            cs = school_ == "EDIC" or (role == "masters" and bool(re.search(r"\b(IC|IN|SC|DS|CYBER|Computer|Communication|Data Science)\b", sec + " " + fac)))

            def q(adv_raw, view=view, au=au, advs=advs):
                val = next((v for v in advs if v == adv_raw), advs[0])
                qq = view.check(dspace_quote(view, au, val))
                if not names.has_tokens(qq, names.nat(au)):
                    raise ValueError("quote lacks the student")
                return qq
            out.append(rec(school="epfl", source="infoscience", id=h, url=url, capture_url=cap, sha256=sha,
                           student=names.nat(au), author_raw=au, advisers=list(advs), year=y, role=role, degree=typ,
                           dept=dept[:200], cs=cs, title=(md.get("dc.title") or [""])[0][:200], handle=h,
                           jury=(md.get("epfl.thesis.jury") or [""])[0][:400], q=q))
    return out


# ====================================================================== Berkeley
def berkeley():
    from bs4 import BeautifulSoup
    out = []
    for y in range(Y0, Y1 + 1):
        u = f"https://www2.eecs.berkeley.edu/Pubs/Dissertations/Years/{y}.html"
        for url, cap, sha, ct, content in rows("berkeley", u):
            view = View(content, ct, sha)
            soup = BeautifulSoup(tcap.decode(content), "lxml")
            main = soup.find(id="site-main") or soup.find("main") or soup
            for p in main.find_all("p"):
                txt = collapse(p.get_text(" "))
                m = re.match(r"^(.*?)\s*\[advisors?: (.*?)\]\s*$", txt)
                a = p.find("a")
                if not m or not a:
                    continue
                title = collapse(a.get_text(" "))
                rest = m.group(1)
                student = rest[len(title):].strip() if rest.startswith(title) else rest.rsplit("  ", 1)[-1]
                advs = names.split_advisers(m.group(2), "natural")

                def q(adv_raw, view=view, txt=txt, student=student):
                    qq = view.check(txt)
                    if not names.has_tokens(qq, student):
                        raise ValueError("quote lacks the student")
                    return qq
                out.append(rec(school="berkeley", source="eecs-dissertations", id=f"{y}:{student}", url=url, capture_url=cap, sha256=sha,
                               student=student, author_raw=student, advisers=advs, year=y, role="phd", degree="Ph.D. dissertation",
                               dept="EECS", cs=True, title=title[:200], q=q))
    for url, cap, sha, ct, content in rows("berkeley", "https://www2.eecs.berkeley.edu/Pubs/TechRpts/20%/EECS-%.html"):
        m = re.search(r"/TechRpts/(\d{4})/(EECS-\d{4}-\d+)\.html$", url)
        if not m or not (Y0 <= int(m.group(1)) <= Y1):
            continue
        view = View(content, ct, sha)
        t = view.views().get("html", "")
        bm = re.search(r"Advisors?: (.*?) BibTeX citation: @(phdthesis|mastersthesis)\{([^,]*), Author= \{(.*?)\}", t)
        if not bm:
            continue
        authors = [a.strip() for a in re.split(r"\s+and\s+", bm.group(4)) if a.strip()]
        first = authors[0]
        student = names.nat(first)
        advs = names.split_advisers(bm.group(1), "natural")
        role = "phd" if bm.group(2) == "phdthesis" else "masters"
        ym = re.search(r"Year= \{(\d{4})\}", t[bm.start():bm.start() + 3000])
        y = int(ym.group(1)) if ym else int(m.group(1))
        tm = re.search(r"Title= \{(.*?)\}", t[bm.start():bm.start() + 3000])
        head = t[bm.start():bm.end()]
        cut = head.find(first)

        def q(adv_raw, view=view, head=head, cut=cut, first=first):
            qq = view.check(head[:cut + len(first)] if cut >= 0 else head)
            if not names.has_tokens(qq, names.nat(first)):
                raise ValueError("quote lacks the student")
            return qq
        out.append(rec(school="berkeley", source="eecs-techreport", id=m.group(2), url=url, capture_url=cap, sha256=sha,
                       student=student, author_raw=first, advisers=advs, year=y, role=role, degree="@" + bm.group(2),
                       dept="EECS", cs=True, title=(tm.group(1) if tm else "")[:200], q=q))
    return out + berkeley_depts()


# ---------------------------------------------------------------------- Berkeley outside EECS (berkeley_depts.py)
def _capture(school, u):
    """(url, capture_url, sha256, content_type, content, year) of the newest stored 200 capture of u (a live URL or a
    Wayback id_ URL), or None."""
    con = sqlite3.connect(f"file:{tcap.DBS[school]}?mode=ro", uri=True, timeout=120)
    if tcap.WAYBACK_RX.match(u):
        r = con.execute("SELECT url, capture_url, sha256, content_type, content, fetched_at FROM captures WHERE capture_url=? AND "
                        "status=200 AND content IS NOT NULL AND error IS NULL ORDER BY id DESC LIMIT 1", (u,)).fetchone()
    else:
        r = con.execute("SELECT url, capture_url, sha256, content_type, content, fetched_at FROM captures WHERE url=? AND "
                        "capture_url IS NULL AND status=200 AND content IS NOT NULL AND error IS NULL ORDER BY id DESC LIMIT 1",
                        (u,)).fetchone()
    con.close()
    if not r:
        return None
    m = tcap.WAYBACK_RX.match(r[1] or "")
    y = int(m.group(1)[:4]) if m else int(r[5][:4])
    return r[0], r[1], r[2], r[3], zlib.decompress(r[4]), y


def pi_window(text, anchor, pi_names, qmax, student=None):
    """Shortest stretch of text from a PI family-name occurrence to the end of an anchor occurrence (or from the anchor to
    the end of the next PI family-name occurrence), at most qmax characters; None if there is none."""
    fams = sorted({names.toks(n)[-1] for n in pi_names if names.toks(n)} |
                  {n.split()[-1] for n in pi_names if n.split()}, key=len, reverse=True)
    if student and any(re.search(r"(?<![A-Za-zÀ-ÿ])%s(?![A-Za-zÀ-ÿ])" % re.escape(f), student, re.I) for f in fams):
        fams = sorted(set(pi_names), key=len, reverse=True)  # 'Kelly Easterday' (PI Maggi Kelly): only the PI's full name counts
    rx = re.compile(r"(?<![A-Za-zÀ-ÿ])(?:%s)(?![A-Za-zÀ-ÿ])" % "|".join(re.escape(f) for f in fams if len(f) > 1), re.I)
    pis = [(m.start(), m.end()) for m in rx.finditer(text)]
    best = None
    for am in re.finditer(re.escape(anchor), text):
        a0, a1 = am.start(), am.end()
        # a PI name inside the anchor counts only when the anchor is more than the student's name ('... co-advised by
        # Prof. Hannah Stuart'); a student who shares the PI's family name ('Kelly Easterday') needs an occurrence outside
        k = text.find(student, a0, a1) if student else -1
        inner = [(s, e) for s, e in pis if s >= a0 and e <= a1 and not (k >= 0 and s >= k and e <= k + len(student))]
        if inner:
            cand = (a0, a1)
        else:
            before = [s for s, e in pis if e <= a0 and not (k >= 0 and s >= k and e <= k + len(student))]
            after = [e for s, e in pis if s >= a1]
            cs_ = ([(before[-1], a1)] if before else []) + ([(a0, after[0])] if after else [])
            if not cs_:
                continue
            cand = min(cs_, key=lambda x: x[1] - x[0])
        if cand[1] - cand[0] <= qmax and (best is None or cand[1] - cand[0] < best[1] - best[0]):
            best = cand
    return text[best[0]:best[1]] if best else None


def berkeley_depts():
    """Theses and advisee listings outside EECS: Math 'Past PhD Students', I School dissertations, and the PIs' own pages
    (berkeley_depts.py)."""
    import berkeley_depts as bd
    from bs4 import BeautifulSoup
    out = []
    # Math: table rows 'Title | Student; Advisor[; Advisor] | Year | PhD Thesis (Author field refers to student + advisor)'
    for u in bd.MATH_PAGES:
        c = _capture("berkeley", u)
        if not c:
            continue
        url, cap, sha, ct, content, _ = c
        view = View(content, ct, sha)
        soup = BeautifulSoup(tcap.decode(content), "lxml")
        for tr in soup.select("table tbody tr"):
            tds = [collapse(td.get_text(" ")) for td in tr.find_all("td")]
            if len(tds) < 4 or not re.fullmatch(r"(19|20)\d\d", tds[2]):
                continue
            y = int(tds[2])
            role = "phd" if tds[3].startswith("PhD") else ("masters" if tds[3].startswith("Master") else None)
            people = [p.strip() for p in tds[1].split(";") if p.strip()]
            if not role or len(people) < 2 or not (Y0 <= y <= Y1):
                continue
            row = " ".join(tds)

            def q(adv_raw, view=view, row=row):
                return view.check(row)
            out.append(rec(school="berkeley", source="math-past-phd", id=f"{y}:{people[0]}", url=url, capture_url=cap, sha256=sha,
                           student=people[0], author_raw=people[0], advisers=people[1:], year=y, role=role,
                           degree=tds[3][:60], dept="Mathematics", cs=False, title=tds[0][:200], q=q))
    # I School: '<Student>. <Title>. Ph.D. dissertation. Advisor(s): A[, B] and C. University of California, Berkeley. <Year>.'
    for u in bd.ISCHOOL_PAGES:
        c = _capture("berkeley", u)
        if not c:
            continue
        url, cap, sha, ct, content, _ = c
        view = View(content, ct, sha)
        t = view.views().get("html", "")
        i = t.rfind("Completed Ph.D. Dissertations")
        j = t.find("Pagination", i)
        region = t[i + len("Completed Ph.D. Dissertations"):j if j > 0 else len(t)] if i >= 0 else ""
        bound = re.compile(r"University of California, Berkeley[.,]? (?:(?:19|20)\d\d\.? )?|(?<![^ ])(?:19|20)\d\d (?=[A-Z])|https?://\S+ ")
        for m in re.finditer(r"Ph\.? ?D\.?,? [Dd]iss+ertation\.,? Advisors?: (.+?)\. University of California, Berkeley\. ((?:19|20)\d\d)\.", region):
            y = int(m.group(2))
            if not (Y0 <= y <= Y1):
                continue
            starts = [b.end() for b in bound.finditer(region, 0, m.start())]
            s0 = starts[-1] if starts else 0
            entry = re.sub(r"^(?:(?:19|20)\d\d )+", "", region[s0:m.end()].strip())  # a year heading right after a URL
            nm = re.match(r"^(.+?(?<![ .][A-Z]))\s?\.\s", entry)
            if not nm:
                continue
            student = collapse(nm.group(1))
            advs = names.split_advisers(m.group(1), "natural")

            def q(adv_raw, view=view, entry=entry):
                return view.check(entry)
            out.append(rec(school="berkeley", source="ischool-dissertations", id=f"{y}:{student}", url=url, capture_url=cap, sha256=sha,
                           student=student, author_raw=student, advisers=advs, year=y, role="phd", degree="Ph.D. dissertation",
                           dept="School of Information", cs=False, title=entry[len(nm.group(0)):].split(" Ph.")[0].strip(" .")[:200], q=q))
    # the PIs' own pages
    pis = {p["pi"]: p for p in json.load(open(f"{names.ROOT}/berkeley/pis.json"))}
    for src in bd.LAB_SOURCES:
        pi = src["pi"]
        pnames = list(dict.fromkeys([pi] + list(pis.get(pi, {}).get("names") or [])))
        caps = {}

        def read(u):
            c_ = _capture("berkeley", u)
            return c_[4] if c_ else None
        for u in bd.all_captures(src, read):
            c = _capture("berkeley", u)
            if c:
                caps[u] = c

        def emit(u, student, anchor, role, y0, y1, label):
            url, cap, sha, ct, content, ycap = caps[u]
            view = View(content, ct, sha)
            tv = view.views()
            text = tv.get("pdf") or tv.get("html") or tv.get("raw") or ""
            anc = collapse(anchor)
            for form in ("NFC", "NFD"):  # PDF text keeps decomposed accents ('Simón' as o + U+0301)
                if anc not in text and unicodedata.normalize(form, anc) in text:
                    anc = unicodedata.normalize(form, anc)
            qq = pi_window(text, anc, pnames, src.get("qmax") or bd.QMAX, student=collapse(student))
            if qq is None:  # kept as a record whose quote fails, so build.py reports it under quote_failures
                def q(adv_raw, anchor=anchor):
                    raise ValueError(f"no PI-to-student window <= {bd.QMAX} chars for '{anchor}'")
            else:
                def q(adv_raw, view=view, qq=qq):
                    return view.check(qq)
            out.append(rec(school="berkeley", source=src["kind"], id=f"{(cap or url)[-60:]}:{student}", url=url, capture_url=cap,
                           sha256=sha, student=student, author_raw=student, advisers=[pi], year=y1, years=[y0, y1], role=role,
                           degree=label, dept="; ".join(pis.get(pi, {}).get("departments") or [])[:80], cs=False,
                           title=(src.get("title") or "")[:200], q=q))
        for e in src.get("entries") or []:
            student, role, y0, y1 = e[:4]
            anchor = e[4] if len(e) > 4 and e[4] else student
            u = e[5] if len(e) > 5 else src["captures"][0]
            if u in caps:
                emit(u, student, anchor, role, max(y0, Y0), min(y1, Y1), "listed on the PI's page")
        pa = src.get("parse")  # numbered thesis lists: a regex with named groups 'name' and 'y' over the default capture
        if pa and src["captures"][0] in caps:
            c = caps[src["captures"][0]]
            tv = View(c[4], c[3], c[2]).views()
            text = tv.get("pdf") or tv.get("html") or tv.get("raw") or ""
            for m in re.finditer(pa["rx"], text):
                y = int(m.group("y"))
                if Y0 <= y <= Y1:
                    emit(src["captures"][0], collapse(m.group("name")), m.group("name"), pa["role"], y, y, pa.get("label") or "thesis list")
        ro = src.get("roster")
        if ro:
            for u, c in caps.items():
                text = None
                tv = View(c[4], c[3], c[2]).views()
                text = tv.get("pdf") or tv.get("html") or tv.get("raw") or ""
                m0 = re.search(ro["section"][0], text)
                if not m0:
                    continue
                m1 = re.search(ro["section"][1], text[m0.end():])
                sec = text[m0.start():m0.end() + (m1.start() if m1 else len(text))]
                for n in ro["names"]:
                    nn, anc = (n, n) if isinstance(n, str) else n
                    if collapse(anc) in sec and max(Y0, src.get("from") or Y0) <= c[5] <= Y1:
                        emit(u, nn, anc, ro["role"], c[5], c[5], f"current {ro['role']} on the {c[5]} capture")
    return out


# ====================================================================== CMU
SCS_DEPTS = {"Computer Science", "Computer Science Department", "Machine Learning", "Robotics Institute",
             "Language Technologies Institute", "Human-Computer Interaction Institute", "Institute for Software Research",
             "Software and Societal Systems (S3D)", "Computational Biology"}


def cmu():
    import harvest_cmu as hc
    out = []
    # A. SCS report archive: index entries '<b>Title</b><br> Author, Ph.D. Thesis<br> <A HREF="...abstracts/NN-NNN.html">'
    import html as _html
    from urllib.parse import urljoin
    idx = {}
    for series, iu in hc.INDEXES:
        for url, cap, sha, ct, content in rows("cmu", iu):
            raw = tcap.decode(content)
            for m in re.finditer(r"<b>(.*?)</b>\s*<br>\s*([^<]*?),\s*((?:Ph\.\s?D\.|M\.\s?S\.|Masters?|Master's)\s+Thesis)[^<]*<br>\s*"
                                 r'<A HREF="([^"]*abstracts/(\d\d)-\d{3}\.html)"', raw, flags=re.S | re.I):
                if series == "hcii" and int(m.group(5)) < 16:
                    continue
                h = urljoin(iu, m.group(4))
                idx[h] = (series, collapse(_html.unescape(re.sub(r"<[^>]+>", "", m.group(1)))),
                          collapse(_html.unescape(m.group(2))), m.group(3))
    for h, (series, title, author, degree) in idx.items():
        got = list(rows("cmu", h))
        if not got:
            continue
        url, cap, sha, ct, content = got[-1]
        view = View(content, ct, sha)
        t = view.views().get("html", "")
        dm = re.search(r"(Ph\.\s?D\.|M\.\s?S\.|Masters?|Master's)\s+Thesis", t)
        if not dm:
            continue
        if author not in t[:dm.start() + 1]:
            # the index and the abstract page spell the author differently ('Dhiyva'/'Dhivya', 'Dana'/'Dan'): use the
            # page's own author, the text between the title and the degree (date removed)
            head = t[:dm.start()].rstrip()
            head = re.sub(r"\s*(?:(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+)?(?:19|20)\d\d$", "", head)
            ti = head.rfind(title) if title else -1
            cand = head[ti + len(title):].strip() if ti >= 0 else ""
            if not cand or len(cand.split()) > 5:
                words = head.split()
                best = None
                for k in range(2, 6):
                    c_ = " ".join(words[-k:])
                    d_ = names.lev(names.fold(c_), names.fold(author))
                    if best is None or d_ < best[0]:
                        best = (d_, c_)
                cand = best[1] if best and best[0] <= 3 else ""
            if not cand or names.lev(names.fold(cand), names.fold(author)) > max(3, len(author) // 3):
                continue
            author = cand
        ym = re.search(r"((?:19|20)\d\d)", t[t.rfind(author, 0, dm.start() + 1):dm.end() + 40])
        rep = re.search(r"CMU-[A-Z]+-(\d\d)-\d{3}", t)
        y = int(ym.group(1)) if ym else (2000 + int(rep.group(1)) if rep else None)
        end_rx = r"(?:,\s*(?:Interim\s+)?Head,|,\s*(?:Interim\s+)?Director,|,\s*Dean,|Return to:|$)"
        cm = re.search(r"Thesis Com\s?mittee( Members)?:?(.*?)" + end_rx, t) or \
            re.search(r"(?:Com\s?mittee|Advisor)s?()?:(.*?)" + end_rx, t) or \
            re.search(r"\d+ pages()? (.*?)" + end_rx, t)
        committee = cm.group(2).strip()[:1500] if cm else ""
        chairs = []
        for x in re.finditer(r"([A-Z][^()]{2,60}?)\s*\(((?:Co-?\s?)?(?:[Cc]hair|[Aa]dvis[eo]r|[Ss]upervisor)[^)]*)\)", committee):
            chairs.append((x.group(1).strip(), x.group(0)))
        for x in re.finditer(r"([A-Z][A-Za-z.\- ']{2,50}?),\s*((?:Co-?)?(?:[Cc]hair|[Aa]dvis[eo]r))", committee):
            chairs.append((x.group(1).strip(), x.group(0)))
        if not chairs or y is None or not (Y0 <= y <= Y1):
            continue
        role = "phd" if degree.startswith("Ph") else "masters"
        deg_at = dm.start()

        def q(adv_raw, view=view, t=t, aut=author, chairs=chairs, deg_at=deg_at):
            mark = next((m_ for a_, m_ in chairs if a_ == adv_raw), None)
            i = t.rfind(aut, 0, deg_at + 1)
            j = t.find(mark, deg_at) if mark else -1
            if i < 0 or j < 0:
                raise ValueError("student or chair mark not found")
            return view.check(t[i:j + len(mark)])
        out.append(rec(school="cmu", source="scs-reports-archive", id=(rep.group(0) if rep else h), url=url, capture_url=cap, sha256=sha,
                       student=author, author_raw=author, advisers=[a_ for a_, _ in chairs], year=y, role=role, degree=degree,
                       dept={"cs": "CSD", "ml": "MLD", "isr": "ISR/S3D", "hcii": "HCII"}[series], cs=True, title=title[:200], q=q,
                       committee=committee[:400]))
    # B. KiltHub article JSON
    for url, cap, sha, ct, content in rows("cmu", "https://api.figshare.com/v2/articles/%"):
        if not re.match(r"^https://api\.figshare\.com/v2/articles/\d+$", url):
            continue
        try:
            d = json.loads(content)
        except Exception:
            continue
        if d.get("defined_type") != 8 and d.get("defined_type_name") != "thesis":
            continue
        cf = {c["name"]: c.get("value") for c in d.get("custom_fields", [])}
        adv = cf.get("Advisor(s)") or ""
        if isinstance(adv, list):
            adv = ", ".join(adv)
        authors = d.get("authors") or []
        if not adv or not authors:
            continue
        au = authors[0].get("full_name") or ""
        y = year_of(cf.get("Date") or "") or year_of(d.get("published_date") or "")
        if y is None or not (Y0 <= y <= Y1):
            continue
        dep = cf.get("Thesis Department") or []
        dep = dep if isinstance(dep, list) else [dep]
        dt = cf.get("Degree Type") or []
        dt = " ".join(dt if isinstance(dt, list) else [dt])
        dn = cf.get("Degree Name") or []
        dn = " ".join(dn if isinstance(dn, list) else [dn])
        role = "phd" if re.search(r"Dissertation|Doctor", dt + " " + dn) else ("masters" if re.search(r"Master", dt + " " + dn) else
                                                                              ("undergraduate" if re.search(r"Bachelor|Undergrad|Senior", dt + " " + dn) else "other"))
        view = View(content, ct, sha)

        def q(adv_raw, view=view, au=au, adv=adv):
            qq = kq(view.views().get("raw", ""), view, au, adv)
            if "\\u" in qq and "json" in view.views():
                # names stored only as \u-escaped JSON: quote the unescaped view (tcap.texts 'json'), which names them
                return kq(view.views()["json"], view, au, adv)
            return qq

        def kq(raw, view, au, adv):
            a = '"full_name": %s' % json.dumps(au, ensure_ascii=False)
            b = '"name": "Advisor(s)", "value": %s' % json.dumps(adv, ensure_ascii=False)
            i, j = raw.find(collapse(a)), raw.find(collapse(b))
            if i < 0:
                a = '"full_name": %s' % json.dumps(au)
                i = raw.find(collapse(a))
            if j < 0:
                b = '"name": "Advisor(s)", "value": %s' % json.dumps(adv)
                j = raw.find(collapse(b))
            if i < 0 or j < 0 or j < i:
                raise ValueError("author/advisor not found in article JSON")
            return view.check(raw[i:j + len(collapse(b))])
        out.append(rec(school="cmu", source="kilthub", id=str(d.get("id")), url=url, capture_url=cap, sha256=sha,
                       student=collapse(au), author_raw=au, advisers=names.split_advisers(adv, "natural"), adviser_values=[adv], year=y,
                       role=role, degree=(dt + " | " + dn).strip(" |"), dept="; ".join(dep), cs=bool(set(dep) & SCS_DEPTS),
                       title=(d.get("title") or "")[:200], q=q))
    return out


# ====================================================================== Stanford (SDR PURL MODS, harvest_stanford.py)
STANFORD_CS_DEPTS = re.compile(r"Computer Science|Electrical Engineering|Statistics|Management Science|Computational and Mathematical|"
                               r"Linguistics|Psychology|Biomedical (?:Data Science|Informatics)|Symbolic Systems|Mathematics|Mechanical|"
                               r"Aeronautics|Education|Bioengineering|Business|Law|Economics|Music|Communication", re.I)


def stanford():
    """Stanford Digital Repository dissertations: each stored PURL MODS record (purl.stanford.edu/<druid>.mods) with an
    'author' name and 'degree supervisor' names (the adviser; 'thesis advisor' / 'degree committee member' alone are the
    reading committee and are not advisers). The quote is the stretch of the MODS from the author's <name> element to
    the supervisor's (or the reverse), whitespace-collapsed, as stored."""
    out = []
    for url, cap, sha, ct, content in rows("stanford", "https://purl.stanford.edu/%.mods"):
        t = content.decode("utf-8", "replace")
        view = View(content, ct, sha)
        els = [(m.start(), m.end(), m.group(0)) for m in re.finditer(r'<name[^>]*type="personal"[^>]*>.*?</name>', t, flags=re.S)]
        def part(e):
            import html as H
            n = H.unescape(" ".join(re.findall(r"<namePart[^>]*>(.*?)</namePart>", e, flags=re.S))).strip()
            return re.sub(r",?\s*(?:\d{4}-(?:\d{4})?|\(\d{4}-?\d*\))\s*$", "", n).strip().rstrip(",")  # 'Clark, Tom S., 1980-' -> 'Clark, Tom S.'
        def roles(e):
            return [x.strip() for x in re.findall(r"<roleTerm[^>]*>(.*?)</roleTerm>", e, flags=re.S)]
        au = next((e for e in els if "author" in roles(e[2])), None)
        sups = [e for e in els if "degree supervisor" in roles(e[2])]
        if not au or not sups:
            continue
        ym = re.search(r"Thesis\s+(Ph\.?\s?D\.?|Ed\.?\s?D\.?|J\.?S\.?D\.?|D\.?M\.?A\.?|Engineer|M\.?S\.?)[^<]*?(\d{4})", t)
        y = int(ym.group(2)) if ym else None
        if y is None or not (Y0 <= y <= Y1):
            continue
        deg = ym.group(1)
        role = "phd" if re.match(r"Ph|J\.?S|D\.?M|Ed", deg) else ("masters" if re.match(r"M|Eng", deg) else "other")
        dm = re.search(r"Submitted to the (?:Department|Program|School|Graduate School|Institute) (?:of|for|in) ([^.<]+)", t)
        dept = dm.group(1).strip() if dm else ""
        au_raw = part(au[2])

        def q(adv_raw, view=view, t=t, au=au, sups=sups, au_raw=au_raw):
            e = next((s_ for s_ in sups if names.has_tokens(collapse(re.sub(r"<[^>]+>", " ", s_[2])), names.nat(adv_raw))), sups[0])
            lo, hi = min(au[0], e[0]), max(au[1], e[1])
            span = t[lo:hi]
            if len(span) > 4000:
                raise ValueError("author and supervisor name elements not near")
            qq = view.check(span)
            if not names.has_tokens(qq, names.nat(au_raw)):
                raise ValueError("quote lacks the student")
            return qq
        druid = re.search(r"purl\.stanford\.edu/([a-z0-9]+)\.mods", url).group(1)
        title = collapse(re.sub(r"<[^>]+>", " ", (re.search(r"<titleInfo>(.*?)</titleInfo>", t, flags=re.S) or [None, ""])[1]))
        out.append(rec(school="stanford", source="sdr-purl-mods", id=druid, url=url, capture_url=cap, sha256=sha,
                       student=names.nat(au_raw), author_raw=au_raw, advisers=[part(s_[2]) for s_ in sups], year=y, role=role,
                       degree="Thesis " + deg, dept=dept, cs=bool(STANFORD_CS_DEPTS.search(dept)), title=title[:200], q=q))
    return out


SCHOOL_FN = {"princeton": princeton, "mit": mit, "epfl": epfl, "berkeley": berkeley, "cmu": cmu, "stanford": stanford}


def load(school):
    out = SCHOOL_FN[school]()
    if school != "berkeley":  # the PIs' own pages (lab_sources.py; Berkeley's are in berkeley_depts.py)
        import records_labs
        out += records_labs.records_for(school)
    return out
