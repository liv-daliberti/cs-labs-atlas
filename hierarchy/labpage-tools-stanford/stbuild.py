"""Build hierarchy/stanford/labpage-pubs.jsonl.gz and labpage-pubs-report.json from the reviewed decisions
(decisions.json in this directory: {pi: {"pages": [{"url", "mode", "css"?, "title_css"?}], "notes"}} or
{pi: {"none": reason}}) and the stored captures (hierarchy/stanford/labpage-captures.sqlite).

Per page: lppubs.parse (auto/bib/links, the EPFL/Berkeley parser), or mode 'css' (entries = elements matching css,
title = first title_css match inside each; for pages whose markup the auto parser splits badly). Rows written (the
same convention as the other five schools): entries with a year in 2016-2026 that the PI's lab papers do not hold
(lppubs.held_match), deduplicated per PI by normalized title, whose title passes the title check below and whose quote
is an exact substring of a text view of the stored bytes and contains the title.
Row: pi, title, year, venue, links, url (live page URL, or the Wayback id_ URL when the bytes came from the archive),
page_url (the original page URL), capture_url (Wayback only), sha256 (stored bytes), quote.
Title check (drops, counted by reason in the report): venue/citation-tail lines, author lists, news/award/talk lines.
usage: stbuild.py [--write] [--only PI ...] [--show]"""
import gzip
import json
import os
import re
import sys
import tempfile
from urllib.parse import urljoin

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stcap  # noqa: E402,F401
import lpcap  # noqa: E402
import lpdom  # noqa: E402
import lplab  # noqa: E402
import lppubs  # noqa: E402

S = "stanford"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = lpcap.data("labpage-pubs.jsonl.gz", S)
REP = lpcap.data("labpage-pubs-report.json", S)
VENUE_TITLE = re.compile(r"^(?:in\s+(?:proc|the\s|ieee|acm|international|annual|\d)|proc\.|proceedings|ieee|acm|international|annual|journal|transactions|conference|"
                         r"workshop|symposium|arxiv|advances in|neural information|nature\b|science\b|accepted|to appear|"
                         r"under review|submitted|preprint|technical report|vol\.|pp\.|pages\s|\d+(?:st|nd|rd|th)\s)", re.I)
NEWS = re.compile(r"\b(?:papers? (?:accepted|to appear|at|in)|accepted (?:to|at|by)|congratulat|award(?:ed)?\b|"
                  r"welcome|we are hiring|is hiring|keynote|invited talk|best paper|graduat|defended|"
                  r"successfully)\b", re.I)


VENUE_KW = re.compile(r"\b(?:symposium|conference|journal|transactions|proceedings|workshop|communications of the acm|"
                      r"letters|magazine|review|annals)\b", re.I)


TRAIL = re.compile(r"(?:\s*[\[(|•·,]?\s*(?:pdf|arxiv|code|codebase|paper|slides|video|bibtex|bib|project(?: page)?|website|"
                   r"webpage|preprint|link|poster|talk|blog(?: post)?|docs|abstract|html|doi)\s*[\])|•·]?)+\s*$", re.I)
LINKWORDS = re.compile(r"\b(?:pdf|paper|code|codebase|docs|blog|webpage|slides|video|arxiv|project page|bibtex)\b", re.I)


def clean(t):
    t2 = re.sub(r"\s*\[\s*(?:arxiv|link|code|pdf|paper|video|slides|bib|bibtex|project|website|html)\b[^\]]*\].*$", "", t, flags=re.I)
    t2 = re.sub(r"^\d{1,3}\s+(?=[A-Z])", "", t2)
    m = re.search(r"[“\"]([^”\"]{15,300}?)[,.]?[”\"]", t2)
    if m and m.start() > 10 and t2[:m.start()].count(",") >= 1:  # 'A. B, C. D, "Title," venue'
        t2 = m.group(1)
    t2 = re.sub(r"\s*\|\s*[^|]{2,40}\b(?:19|20)\d\d\s*$", "", t2)  # "Title | CVPR 2025"
    t2 = re.sub(r"(?<=\w),\s*(?:19|20)\d\d\s*$", "", t2)          # "Title, 2021"
    t2 = TRAIL.sub("", t2).strip(" ,.;:-–—|•·")
    t2 = re.sub(r"^(?:[A-Z][\w'’-]+,\s*[A-Z]{1,3}\.?,?\s*(?:et al\.?,?|and [^,]{3,40},)\s*|[A-Z][\w ]{2,30} Consortium,\s*)", "", t2)
    return t2 if len(t2) >= 12 else t


def title_problem(t, pi):
    if not t or len(t) < 12 or len(t.split()) < 3:
        return "fragment"
    if re.match(r"^(?:on|in|of|and|for|the|to|at|with|by|from)\s", t):
        return "fragment"
    if re.search(r"\b(?:program committee|video of|slides\b|tenure|full list of authors|nominated|sloan|outstanding paper|"
                 r"honou?rable mention|more results|syllabus|lecture notes|research statement|teaching statement|"
                 r"papers online)\b", t, re.I):
        return "service_award_news"
    if len(t.split()) <= 8 and ":" not in t and re.search(r"[,(]?\s*\(?(?:[A-Z][A-Za-z]{1,10}\s*)?(?:19|20)\d\d\)?\s*$", t):
        return "venue_line"
    if len(re.sub(r"\s*\([^)]*\)", "", t).split()) <= 4 and lpdom.looks_like_name(re.sub(r"\s*\([^)]*\)", "", t)):
        return "person_line"
    if len(LINKWORDS.findall(t)) >= 2 and re.search(r"[•·|]", t):
        return "link_line"
    if re.match(r"^[A-Z][A-Za-z]{1,9}[\'’]?\s?(?:19|20)?\d{2}\b", t) and len(t.split()) <= 8:
        return "venue_line"
    if len(t.split()) <= 5 and re.search(r"\b(?:workshop|symposium|conference|seminar|tutorial)\s*$", t, re.I):
        return "venue_line"
    if re.match(r"^(?:supersedes|extended version|journal version|conference version|full version|see also|with )", t, re.I):
        return "fragment"
    if re.search(r"\bnow at\b|\bco-advised\b|\bph\.?d\.? student\b|\bpostdoc(?:toral)? (?:scholar|fellow|researcher)\b|"
                 r"\bdistinguished lecturer\b|\bfellow(?:ship)?\b.{0,20}\b(?:19|20)\d\d\b", t, re.I):
        return "person_or_honor_line"
    if re.search(r"\binvited to\b|\bspecial issue\b|\bpromotion\b|\bslide deck\b|\bpostdoc\b|\bhonou?rs? include\b", t, re.I) or \
            re.match(r"^(?:[A-Z]{2,4}\s?\d{2,3}[A-Z]?\s*:|(?:[\w.]+ )?(?:professor|chair)\b)", t) or \
            (len(t.split()) <= 5 and re.search(r"\bprofessor(?:ship)?\b", t, re.I)):
        return "person_or_honor_line"
    if re.search(r"https?://|\bdoi\.org\b", t) or re.match(r"^\d+\s*\(\d+\)", t):
        return "identifier_line"
    if re.match(r"^(?:pubmed pmid|pmid|pmcid|view details for|doi\b|isbn)", t, re.I):
        return "identifier_line"
    if re.match(r"^(?:publication type|year|type|filter|sort by|show)\s*:", t, re.I):
        return "filter_or_heading"
    if len(t.split()) <= 6 and re.search(r"\b(?:university|institute|college|school of|department)\b", t, re.I):
        return "affiliation_line"
    if len(t.split()) <= 5 and re.fullmatch(r"(?:[A-Z][\w&-]*|of|and|in|on|the|for|&)(?:\s+(?:[A-Z][\w&-]*|of|and|in|on|the|for|&))*", t) and \
            re.search(r"\b(?:economic|operations research|management science|econometrica|quarterly|annals|statistics|"
                      r"mathematics|physics|letters|review|science|neuron|nature|cell|biology|medicine)\b", t, re.I):
        return "venue_line"
    if re.match(r"^" + re.escape(pi.split()[0]) + r"\b.{0,40}\b(?:is|was|has|received|directs|leads|joined)\b", t):
        return "bio_line"
    full = re.escape(pi.split()[0]) + r"\b.{0,12}\b" + re.escape(pi.split()[-1])
    if re.search(full, t) and "," in t:
        return "author_line"
    if VENUE_TITLE.match(t):
        return "venue_line"
    if NEWS.search(t):
        return "news_line"
    if VENUE_KW.search(t) and (re.search(r"(?:19|20)\d\d\)?\W*$", t) or re.search(r"\d+\s*\(\d+\)", t)) and ":" not in t:
        return "venue_line"
    fam = pi.split()[-1].lower()
    if re.match(r"^(?:he|she|they|his|her|their|prof\.?|professor|dr\.?|" + re.escape(fam) + r")\b.{0,80}\b(?:is|was|has|received|directs|leads|joined|holds|serves)\b", t, re.I):
        return "bio_line"
    t = t.replace("*", "").replace("†", "")
    if lppubs._author_string(t) or (t.count(",") >= 3 and lppubs._looks_authors(t)):
        return "author_line"
    fam = pi.split()[-1].lower()
    if re.search(r"\b" + re.escape(fam) + r"\b", t.lower()) and t.count(",") >= 2:
        return "author_line"
    return None


def parse_css(row, cap, url, css, title_css, year_css=None, drop_css=None):
    soup = lpdom.soup_of(cap["content"], strip_chrome=False)
    if drop_css:
        for x in soup.select(drop_css):
            x.decompose()
    views = lpcap.texts(cap["content"], cap.get("content_type"))
    base = url if cap.get("capture_url") else (cap.get("final_url") or url)
    out = []
    els = soup.select(css)
    heads = lppubs._year_headings_and_entries(soup, els)
    for el in els:
        text = lpdom.collapse(el.get_text(" "))
        te = el.select_one(title_css) if title_css else None
        title = lppubs._clean_title(te.get_text(" ")) if te is not None else lppubs._title_from_text(text)
        if not title:
            continue
        ys = lppubs._years(text)
        if year_css:
            ye = el.select_one(year_css)
            ys = lppubs._years(lpdom.collapse(ye.get_text(" "))) if ye is not None else []
        year = max(ys) if ys else None
        if not year:
            m = re.search(r"year\s*=\s*[{\"]?((?:19|20)\d\d)", str(el))
            year = int(m.group(1)) if m else None
        if not year:
            year = heads.get(id(el))
        if not year:  # two-digit conference years: "PLDI '18"
            m = re.search(r"\b[A-Z][A-Za-z]{1,10}\s?['’](\d\d)\b", text)
            year = 2000 + int(m.group(1)) if m and int(m.group(1)) <= 26 else None
        held = lppubs.held_match(S, row["pi"], title, text)
        q = lppubs._quote(views, text, title)
        links = []
        for a in el.find_all("a", href=True):
            h = urljoin(base, a["href"])
            if h.startswith("http") and h not in links:
                links.append(h)
        out.append({"text": text, "title": title, "year": year, "venue": lppubs._venue(text, title), "links": links[:10],
                    "quote": lpdom.collapse(q) if q else q, "held": bool(held), "held_title": held,
                    "in_window": bool(year and 2016 <= year <= 2026)})
    return out


def _dedupe(es):
    seen, out = set(), []
    for e in es:
        k = lpdom.norm_title(e["title"])
        if k and k not in seen:
            seen.add(k)
            out.append(e)
    return out


def _bib_field(body, name):
    m = re.search(r"(?<![a-z])" + name + r"\s*=\s*", body, re.I)
    if not m:
        return None, None
    i = m.end()
    if i < len(body) and body[i] in "{\"":
        close = "}" if body[i] == "{" else "\""
        depth, j = 0, i
        while j < len(body):
            c = body[j]
            if close == "}" and c == "{":
                depth += 1
            elif close == "}" and c == "}":
                depth -= 1
                if depth == 0:
                    break
            elif close == "\"" and c == "\"" and j > i:
                break
            j += 1
        v = body[i + 1:j]
        return lpdom.collapse(re.sub(r"[{}]", "", v)), body[m.start():j + 1]
    mm = re.match(r"\d{4}", body[i:])
    return (mm.group(0), body[m.start():i + 4]) if mm else (None, None)


def parse_bibhtml(row, cap, url):
    """BibTeX entries shown in a page's visible text (jekyll-scholar 'BibTeX: @article{...}' blocks) or its raw bytes
    (bibtex inside attributes): title/year/booktitle|journal fields; the quote is the title field as it appears."""
    views = lpcap.texts(cap["content"], cap.get("content_type"))
    out = []
    for vname in ("html", "raw"):
        t = views.get(vname) or ""
        starts = [m.start() for m in re.finditer(r"@(?:article|inproceedings|incollection|misc|techreport|book|inbook|"
                                                   r"unpublished|conference|phdthesis|mastersthesis|online)\s*\{", t, re.I)]
        for k, st in enumerate(starts):
            body = t[st:starts[k + 1] if k + 1 < len(starts) else st + 4000]
            title, tq = _bib_field(body, "title")
            if not title or title.startswith("@") or len(title) > 400:
                continue
            year, _ = _bib_field(body, "year")
            venue, _ = _bib_field(body, "booktitle")
            if not venue:
                venue, _ = _bib_field(body, "journal")
            y = int(year) if year and year.isdigit() else None
            links = re.findall(r"https?://[^\s,}\"]+", body)[:6]
            held = lppubs.held_match(S, row["pi"], title, title)
            q = lpdom.collapse(tq) if tq and lpdom.collapse(tq) in t else None
            out.append({"text": title, "title": title, "year": y, "venue": venue, "links": links, "quote": q,
                        "held": bool(held), "held_title": held, "in_window": bool(y and 2016 <= y <= 2026)})
        if out:
            break
    return _dedupe(out)


def wayback_row(url):
    """Newest stored Wayback 200 capture whose original url is url (with or without the trailing slash / scheme)."""
    import sqlite3
    con = sqlite3.connect(f"file:{lpcap.DBS[S]}?mode=ro", uri=True, timeout=60)
    base = re.sub(r"^https?://", "", url).rstrip("/")
    host, _, rest = base.partition("/")
    hosts = [host, host + ":80", host + ":443"]
    cands = [p + h + ("/" + rest if rest else "") + t for p in ("http://", "https://") for h in hosts for t in ("", "/")]
    row = con.execute(f"SELECT {lpcap.COLS} FROM captures WHERE url IN ({','.join('?' * len(cands))}) AND capture_url IS NOT NULL "
                      "AND status=200 AND content IS NOT NULL AND error IS NULL ORDER BY capture_url DESC LIMIT 1", cands).fetchone()
    con.close()
    return lpcap._row(row) if row else None


def parse_json(row, cap, url, key=None):
    """A lab site's own publication data file (JSON list of {title, author, published|venue|year, ...}); key selects one
    top-level list. The quote is the '"title": "..."' pair as it appears in the raw bytes."""
    views = lpcap.texts(cap["content"], cap.get("content_type"))
    raw = views.get("raw") or ""
    data = json.loads(lpcap.decode(cap["content"]))
    items = data.get(key, []) if key else (data if isinstance(data, list) else [x for v in data.values() if isinstance(v, list) for x in v])
    out = []
    for it in items:
        if not isinstance(it, dict) or not it.get("title"):
            continue
        title = lpdom.collapse(str(it["title"]))
        rest = " ".join(str(v) for k, v in it.items() if k != "title" and isinstance(v, (str, int)))
        ys = lppubs._years(rest)
        y = max(ys) if ys else None
        q = None
        for cand in (f'"title": "{title}"', f'"title":"{title}"'):
            if cand in raw:
                q = cand
                break
        held = lppubs.held_match(S, row["pi"], title, title)
        links = [str(v) for k, v in it.items() if isinstance(v, str) and v.startswith("http")][:6]
        out.append({"text": title + " " + rest, "title": title, "year": y,
                    "venue": lpdom.collapse(str(it.get("published") or it.get("venue") or ""))[:200] or None,
                    "links": links, "quote": q, "held": bool(held), "held_title": held,
                    "in_window": bool(y and 2016 <= y <= 2026)})
    return _dedupe(out)


def parse_lines(row, cap, url):
    """Pages whose entries are <br>-separated lines ("Title (2026)"): every text line of 20-600 characters that carries
    a year; the title is the line without a trailing '(year)' and citation tail."""
    base = url if cap.get("capture_url") else (cap.get("final_url") or url)
    views = lpcap.texts(cap["content"], cap.get("content_type"))
    out = []
    for ln in lpdom.lines(cap["content"], base):
        t = ln.text
        ys = lppubs._years(t)
        if not (20 <= len(t) <= 600) or not ys:
            continue
        core = re.sub(r"\s*\(\s*(?:19|20)\d\d[a-z]?\s*\)\s*\.?$", "", t)
        title = core if core != t and len(core) >= 12 else lppubs._title_from_text(t)
        if not title:
            continue
        title = lppubs._clean_title(title)
        held = lppubs.held_match(S, row["pi"], title, t)
        q = lppubs._quote(views, t, title)
        out.append({"text": t, "title": title, "year": max(ys), "venue": None, "links": list(ln.hrefs)[:6],
                    "quote": lpdom.collapse(q) if q else q, "held": bool(held), "held_title": held,
                    "in_window": 2016 <= max(ys) <= 2026})
    return _dedupe(out)


def parse_pdfcv(row, cap, url):
    """A PI's publication-list PDF whose entries read 'Authors. Title. Venue (Month Year). [DOI: ...]': the collapsed
    pdftotext view is split after each '(... YYYY)' date group (and its DOI/URL); the title is the second sentence."""
    views = lpcap.texts(cap["content"], cap.get("content_type"))
    t = views.get("pdf") or ""
    out = []
    pos = 0
    END = re.compile(r"(?:DOI|URL):\s*\S+?\.(?=\s|$)(?:\s+(?:To appear|Best [^.]{0,60}|Honorable Mention|[A-Z][a-z]+ Award)\.)*"
                     r"|\((?:[A-Z][a-z]+\.?\s+)?(?:\d{1,2},?\s+)?(?:19|20)\d\d\)[^.]{0,120}\.(?!\s*(?:DOI|URL):)")
    for m in END.finditer(t):
        ent = t[pos:m.end()].strip()
        pos = m.end()
        if not (30 <= len(ent) <= 1500):
            continue
        ys = [int(x) for x in re.findall(r"(?<![\d/.])((?:19|20)\d\d)(?![\d/])", re.sub(r"(?:DOI|URL):\s*\S+", " ", ent))]
        if not ys:
            continue
        y = ys[-1]
        title = lppubs._title_from_text(ent)
        if not title:
            continue
        held = lppubs.held_match(S, row["pi"], title, ent)
        out.append({"text": ent, "title": title, "year": y, "venue": None, "links": re.findall(r"https?://\S+?(?=\.?\s|$)", ent)[:4],
                    "quote": ent if ent in t else None, "held": bool(held), "held_title": held,
                    "in_window": 2016 <= y <= 2026})
    return _dedupe(out)


def views_of(url):
    r = lplab.stored(S, url)
    if not r and not lpcap.WAYBACK_RX.match(url):
        r = wayback_row(url)
    if not r:
        return None, None
    return r, lpcap.texts(r["content"], r.get("content_type"))


def build(only=None, show=False):
    dec = json.load(open(f"{HERE}/decisions.json"))
    pis = [p["pi"] for p in json.load(open(lpcap.data("pis.json", S)))]
    rows, rep = [], {}
    for pi in pis:
        if only and pi not in only:
            continue
        d = dec.get(pi)
        if d is None:
            rep[pi] = {"status": "not_reviewed"}
            continue
        if d.get("none"):
            rep[pi] = {"status": "no_pubs_page", "why": d["none"]}
            continue
        seen, pages = set(), []
        for pg in d["pages"]:
            url, mode = pg["url"], pg.get("mode", "auto")
            r, views = views_of(url)
            st = {"url": url, "mode": mode, "entries": 0, "in_window": 0, "no_year": 0, "held": 0, "missing": 0,
                  "dropped": {}}
            if not r:
                st["problem"] = "not stored"
                pages.append(st)
                continue
            st["sha256"] = r["sha256"]
            if r.get("capture_url"):
                st["capture_url"] = r["capture_url"]
            if mode == "css":
                es = _dedupe(parse_css({"pi": pi}, r, url, pg["css"], pg.get("title_css"), pg.get("year_css"), pg.get("drop_css")))
            elif mode == "html":
                es = _dedupe(lppubs.parse_auto(S, {"pi": pi}, r, url))
            elif mode == "pdfcv":
                es = parse_pdfcv({"pi": pi}, r, url)
            elif mode == "lines":
                es = parse_lines({"pi": pi}, r, url)
            elif mode == "json":
                es = parse_json({"pi": pi}, r, url, pg.get("key"))
            elif mode == "bibhtml":
                es = parse_bibhtml({"pi": pi}, r, url)
            else:
                es = lppubs.parse(S, {"pi": pi}, r, url, mode=mode)
            st["entries"] = len(es)
            for e in es:
                if not e["year"]:
                    st["no_year"] += 1
                    continue
                if not e["in_window"]:
                    continue
                st["in_window"] += 1
                if e["held"]:
                    st["held"] += 1
                    continue
                e["title"] = clean(e["title"])
                why = title_problem(e["title"], pi)
                k = lpdom.norm_title(e["title"])
                if not why and k in seen:
                    why = "duplicate"
                q = e.get("quote")
                if not why and (not q or not any(q in v for v in views.values())):
                    why = "no_quote"
                if not why and k not in lpdom.norm_title(q):
                    why = "quote_lacks_title"
                if why:
                    st["dropped"][why] = st["dropped"].get(why, 0) + 1
                    if show:
                        print(f"   DROP {why}: {e['title'][:100]}")
                    continue
                seen.add(k)
                st["missing"] += 1
                o = {"pi": pi, "title": e["title"], "year": e["year"], "venue": e["venue"], "links": e["links"],
                     "url": r.get("capture_url") or r["url"], "page_url": r["url"]}
                if r.get("capture_url"):
                    o["capture_url"] = r["capture_url"]
                o["sha256"] = r["sha256"]
                o["quote"] = q
                rows.append(o)
                if show:
                    print(f"   {e['year']} {e['title'][:110]} | {(e['venue'] or '')[:50]}")
            pages.append(st)
        rep[pi] = {"status": "pubs_page", "pages": pages, "entries": sum(p["entries"] for p in pages),
                   "in_window": sum(p["in_window"] for p in pages), "held": sum(p["held"] for p in pages),
                   "missing": sum(p["missing"] for p in pages), "notes": d.get("notes", "")}
    return rows, rep


def atomic(path, write):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp-")
    os.close(fd)
    write(tmp)
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)


if __name__ == "__main__":
    a = sys.argv[1:]
    only = set(a[a.index("--only") + 1:]) if "--only" in a else None
    rows, rep = build(only, show="--show" in a)
    have = [k for k, v in rep.items() if v.get("status") == "pubs_page"]
    print(f"PIs with pages {len(have)}, no page {sum(1 for v in rep.values() if v.get('status') == 'no_pubs_page')}, "
          f"not reviewed {sum(1 for v in rep.values() if v.get('status') == 'not_reviewed')}; rows {len(rows)}; "
          f"in-window entries {sum(rep[k]['in_window'] for k in have)}, held {sum(rep[k]['held'] for k in have)}")
    for k in have:
        for p in rep[k]["pages"]:
            if p.get("problem"):
                print("  PROBLEM", k, p["url"], p["problem"])
    if "--write" in a and not only:
        def w1(t):
            with gzip.open(t, "wt") as f:
                for r in rows:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
        atomic(OUT, w1)

        def w2(t):
            summ = {"school": S, "built_at": lpcap.now(), "rows": len(rows),
                    "rows_2016_2026": sum(1 for r in rows if 2016 <= r["year"] <= 2026),
                    "pis_with_page": len(have), "pis": rep}
            json.dump(summ, open(t, "w"), ensure_ascii=False, indent=1)
        atomic(REP, w2)
        print("written", OUT, REP)
