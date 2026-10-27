"""Publication-page parsing for the lab-page pass: entries, titles, years, links, and the held/missing compare.

parse(school, row, capture, url, mode) -> [entry] with keys text, title, year, venue, links, quote, held, held_title,
in_window. Modes:
  auto   innermost block elements (li/p/tr/dd/div...) of 40-2500 chars; blocks with several <br>-separated entries
         are split; entries without a year inherit the nearest preceding year heading.
  bib    a BibTeX file (title/year/booktitle|journal fields).
  links  every <a> whose text is 20+ characters is a title (pages that list titles as links only).
Held compare (normalized: accents folded, lower case, non-alphanumerics to single spaces): an entry is held when one of
the PI's lab-paper titles (12+ chars, 3+ words) occurs in the entry's normalized text, or the extracted title equals,
prefixes (30+ chars) or nearly equals (difflib ratio >= 0.92) a held title.
"""
import difflib
import re
from functools import lru_cache
from urllib.parse import urljoin

from bs4 import NavigableString, Tag

import lpcap
import lpdom
import lplab

VENUE_RX = re.compile(r"proceedings|proc\.|conference|journal|transactions|workshop|symposium|arxiv|preprint|"
                      r"\b(icml|neurips|nips|iclr|cvpr|iccv|eccv|acl|emnlp|naacl|sigmod|vldb|osdi|sosp|nsdi|sigcomm|"
                      r"usenix|ccs|crypto|eurocrypt|stoc|focs|soda|chi|uist|isca|micro|asplos|pldi|popl|icse|fse|"
                      r"www|kdd|aaai|ijcai|icra|iros|rss|corl|siggraph|tog|jmlr|tpami|ieee|acm)\b", re.I)
YEAR_ONLY = re.compile(r"^\s*((?:19|20)\d{2})\s*:?\s*$")
YEAR_IN = re.compile(r"(?<![\d.:/])((?:19[89]\d|20[0-2]\d))(?![\d])")


def norm(s):
    return lpdom.norm_title(s)


@lru_cache(maxsize=512)
def held_titles(school, pi):
    out = []
    for p in lplab.lab_papers(school).get(pi, []):
        t = p.get("title") or ""
        n = norm(t)
        if n:
            out.append((n, t))
    return out


def held_match(school, pi, title, text):
    nt, nx = norm(title), norm(text)
    hs = held_titles(school, pi)
    for n, t in hs:
        if len(n) >= 12 and n.count(" ") >= 2 and (" " + n + " ") in (" " + nx + " "):
            return t
    if nt:
        for n, t in hs:
            if n == nt:
                return t
            if len(nt) >= 30 and len(n) >= 30 and (n.startswith(nt) or nt.startswith(n)):
                return t
        first = nt.split(" ")[0]
        for n, t in hs:
            if n.split(" ")[0] == first and abs(len(n) - len(nt)) < 25 and \
                    difflib.SequenceMatcher(None, n, nt).ratio() >= 0.92:
                return t
    return None


def _years(text):
    ys = [int(y) for y in YEAR_IN.findall(text)]
    ys = [y for y in ys if 1980 <= y <= 2026]
    return ys


def _looks_authors(seg):
    s = seg.strip()
    if not s:
        return False
    toks = s.split()
    commas = s.count(",") + len(re.findall(r"\band\b|&", s))
    caps = sum(1 for t in toks if t[:1].isupper())
    if commas >= 1 and caps >= 0.6 * len(toks) and len(toks) <= 60:
        # mostly short capitalised tokens separated by commas
        avg = sum(len(t) for t in toks) / max(1, len(toks))
        return avg <= 9
    if lpdom.looks_like_name(s):
        return True
    return False


def _split_sentences(text):
    # split on '. ' not preceded by a single capital (initials) or common abbreviations
    parts, cur = [], ""
    for piece in re.split(r"(?<=[.?!])\s+", text):
        cur = (cur + " " + piece).strip() if cur else piece
        if re.search(r"(?:\b[A-Z]|\bet al|\bvol|\bno|\bpp|\bProc|\bIn|\be\.g|\bi\.e|\bvs|\bJr|\bSt|\bDr)\.$", cur):
            continue
        parts.append(cur)
        cur = ""
    if cur:
        parts.append(cur)
    return [p.strip() for p in parts if p.strip()]


def _clean_title(t):
    t = lpdom.collapse(t).strip(" .,;:-–—\"“”'‘’")
    t = re.sub(r"^\[\s*[A-Za-z]*\d+[a-z]?\s*\]\s*", "", t)  # "[422] Title" numbering
    t = re.sub(r"^\(?\d{1,3}\)\s+|^\d{1,3}\.\s+", "", t)
    t = t.strip(" .,;:-–—\"“”'‘’")
    t = re.sub(r"\s*\[(pdf|PDF|paper|code|arxiv|arXiv|slides|bib|video|project)\]\s*$", "", t)
    return t


def _title_from_el(el):
    if el is None:
        return None
    for c in el.find_all(True):
        cls = " ".join(c.get("class") or [])
        if re.search(r"(^|[\s_-])(title|pub-title|paper-title|ptitle)([\s_-]|$)", cls, re.I):
            t = _clean_title(c.get_text(" "))
            if len(t) >= 12:
                return t
    for tag in (("b", "strong"), ("a",), ("i", "em", "cite")):
        for c in el.find_all(list(tag)):
            t = _clean_title(c.get_text(" "))
            if len(t) < 15 or len(t) > 300:
                continue
            if lpdom.looks_like_name(t) or re.match(r"^(https?://|www\.|doi:)", t, re.I):
                continue
            if tag[0] == "a" and re.fullmatch(r"(pdf|paper|arxiv|code|project page|slides|video|bibtex|abstract|link|"
                                              r"website|talk|poster|doi|preprint|supplementary.*)", t, re.I):
                continue
            if tag[0] in ("i", "b") and VENUE_RX.search(t) and len(t) < 120:
                continue
            if _looks_authors(t) and t.count(",") >= 2:
                continue
            return t
    return None


def _title_from_text(text):
    m = re.search(r"[“\"]([^”\"]{15,300})[”\"]", text)
    if m:
        return _clean_title(m.group(1))
    segs = _split_sentences(text)
    if not segs:
        return None
    # Authors first?  "A. Smith, B. Jones. Title. Venue 2019."
    if _looks_authors(segs[0]) and len(segs) > 1:
        for s in segs[1:]:
            s2 = re.sub(r"^\(?(19|20)\d{2}[a-z]?\)?[.:]?\s*", "", s)
            if len(s2) >= 15 and not _looks_authors(s2):
                return _clean_title(s2)
    s0 = re.sub(r"^\[?\d+\]?\.?\s+", "", segs[0])
    return _clean_title(s0) if len(s0) >= 12 else None


def _venue(text, title):
    rest = text
    if title and title in text:
        rest = text[text.index(title) + len(title):]
    for s in _split_sentences(rest):
        if VENUE_RX.search(s):
            return lpdom.collapse(s)[:200]
    return None


def _links(el, base):
    out = []
    if el is None:
        return out
    for a in el.find_all("a", href=True):
        h = urljoin(base, a["href"])
        if h.startswith(("http://", "https://")) and h not in out:
            out.append(h)
    return out[:10]


def _quote(views, entry_text, title):
    """Exact substring of a stored text view containing the title: the entry text when it fits, else a window."""
    html = views.get("html") or ""
    raw = views.get("raw") or ""
    pdf = views.get("pdf") or ""
    for t in (html, pdf, raw):
        if not t:
            continue
        if entry_text and len(entry_text) <= 600 and entry_text in t and (not title or title in entry_text):
            return entry_text
        if title and title in t:
            i = t.find(title)
            # extend to the end of the entry text when that follows
            if entry_text and entry_text in t:
                j = t.find(entry_text)
                if j <= i <= j + len(entry_text):
                    s = max(j, i - 200)
                    e = min(j + len(entry_text), i + len(title) + 200)
                    return t[s:e]
            return t[i:i + len(title)]
    return None


def _year_headings_and_entries(soup, cands):
    """Walk the document once: each candidate element gets the last year heading seen before it."""
    cand_ids = {id(c): c for c in cands}
    cur = None
    out = {}
    body = soup.body or soup
    for node in body.descendants:
        if isinstance(node, Tag):
            if id(node) in cand_ids:
                out[id(node)] = cur
                continue
            if node.name in ("h1", "h2", "h3", "h4", "h5", "h6", "strong", "b", "dt", "span", "div", "a", "p", "th",
                             "button", "summary", "td", "li"):
                t = node.get_text(" ", strip=True)
                if len(t) <= 8:
                    m = YEAR_ONLY.match(t)
                    if m:
                        cur = int(m.group(1))
            if node.get("id") and re.fullmatch(r"(y|year)?-?((?:19|20)\d{2})", node.get("id")):
                cur = int(re.search(r"(19|20)\d{2}", node.get("id")).group(0))
    return out


def _split_br(el):
    """Split an element's children at <br> runs into text chunks; merge chunks until one carries a year."""
    chunks, cur = [], []
    brs = 0
    for c in el.children:
        if isinstance(c, Tag) and c.name == "br":
            brs += 1
            if cur:
                chunks.append(cur)
                cur = []
            continue
        cur.append(c)
    if cur:
        chunks.append(cur)
    if brs < 2:
        return None
    texts = []
    for ch in chunks:
        t = lpdom.collapse(" ".join(x.get_text(" ") if isinstance(x, Tag) else str(x) for x in ch))
        if t:
            texts.append((t, ch))
    entries, acc, nodes = [], [], []
    for t, ch in texts:
        acc.append(t)
        nodes.extend(ch)
        if _years(t):
            entries.append((" ".join(acc), nodes))
            acc, nodes = [], []
    if acc and entries:
        entries[-1] = (entries[-1][0] + " " + " ".join(acc), entries[-1][1] + nodes)
    return entries if len(entries) >= 2 else None


def parse_auto(school, row, cap, url):
    soup = lpdom.soup_of(cap["content"])
    base = cap.get("final_url") or url
    if cap.get("capture_url"):
        base = url
    cands, _ = lpdom.pub_entries(cap["content"], base)
    # pub_entries built its own soup; rebuild candidates on this soup for the year walk
    body = soup.body or soup
    els = []
    for el in body.find_all(lpdom.ENTRY_TAGS):
        t = lpdom.collapse(el.get_text(" "))
        if 40 <= len(t) <= 2500:
            inner = any(len(lpdom.collapse(d.get_text(" "))) >= 40 and
                        len(lpdom.collapse(d.get_text(" "))) >= 0.6 * len(t) for d in el.find_all(lpdom.ENTRY_TAGS))
            if not inner:
                els.append(el)
        elif len(t) > 2500 and el.find("br") is not None and not el.find(lpdom.ENTRY_TAGS):
            els.append(el)
    heads = _year_headings_and_entries(soup, els)
    views = lpcap.texts(cap["content"], cap.get("content_type"))
    out = []
    for el in els:
        hy = heads.get(id(el))
        pieces = None
        t_all = lpdom.collapse(el.get_text(" "))
        if el.find("br") is not None and len(_years(t_all)) >= 2:
            pieces = _split_br(el)
        if pieces:
            for text, nodes in pieces:
                wrap = soup.new_tag("div")
                title = None
                for n in nodes:
                    if isinstance(n, Tag):
                        title = title or _title_from_el(n) if n.name not in ("br",) else title
                title = title or _title_from_text(text)
                out.append(_entry(school, row, text, title, hy, views, [h for n in nodes if isinstance(n, Tag)
                                                                        for h in _links(n, base)] +
                                  [urljoin(base, n["href"]) for n in nodes if isinstance(n, Tag) and n.name == "a"
                                   and n.get("href")]))
            continue
        if len(t_all) > 2500:
            continue
        title = _title_from_el(el) or _title_from_text(t_all)
        out.append(_entry(school, row, t_all, title, hy, views, _links(el, base)))
    return [e for e in out if e]


ABSTRACT_RX = re.compile(r"^(we|in this|in recent|in the past|this (chapter|paper|work|thesis|article|talk)|our|here,? we|"
                         r"the goal|prior to|department|university|school of|institute|professor|she|he|they|"
                         r"recently|abstract|keywords)\b", re.I)
LINKY_RX = re.compile(r"\.pdf|arxiv\.org|doi\.org|dl\.acm\.org|ieeexplore|springer|openreview|proceedings|"
                      r"neurips\.cc|aclanthology|usenix\.org|biorxiv|/papers?/|/pubs?/|\.bib$|infoscience", re.I)
PERSONISH = re.compile(r"advis|\bph\.?d\b|\bms 20|\bm\.?s\. 20|postdoc|student|graduat|alumn|now at|moved to|"
                       r"\bintern\b|visiting|assistant professor|professor at", re.I)


BAD_TITLE = re.compile(r"^(in\s+(the\s+)?(proc|proceedings|advances|international|ieee|acm|neural|conference|journal|"
                       r"workshop|symposium|annual|\d)|arxiv\b|biorxiv|medrxiv|preprint|proceedings|proc\.|"
                       r"accepted|to appear|submitted|under review|technical report|tech\. ?rep|vol\.|pp\.|doi\b|"
                       r"https?://|available at|journal of|transactions on|\(|\[|"
                       r"in\s.*\b(journal|proceedings|conference|workshop|symposium|transactions|letters)\b)", re.I)
AUTHOR_RUN = re.compile(r",\s+(?:[A-Z][\w'\-.]*\*?\s){1,3}[A-Z][\w'\-]+\*?,\s(?:[A-Z][\w'\-.]*\*?\s){1,3}[A-Z][\w'\-]+\*?,"
                        r"\s(?:[A-Z][\w'\-.]*\*?\s){0,3}[A-Z][\w'\-]+")


def _trim_authors(t):
    """Cut an author list run into the end of a title: 'Title, Ann Lee, Bo Xu, Cy Wu' -> 'Title'."""
    m = AUTHOR_RUN.search(t)
    if m and m.start() >= 15:
        return t[:m.start()].strip(" ,.;:")
    return t


def _author_string(t):
    segs = [x.strip() for x in re.split(r"\s;\s|,\s|\sand\s|\s&\s", t) if x.strip()]
    segs = [re.sub(r"\s+et al\.?$", "", x) for x in segs]
    if not segs:
        return False
    namey = sum(1 for x in segs if lpdom.looks_like_name(x) or re.fullmatch(r"(?:[A-Z][a-z]?(?:-[A-Z][a-z]?)?\.\s?)+[A-Z][\w'\-]+(?:\s[A-Z][\w'\-]+)?", x))
    return namey >= max(1, 0.7 * len(segs))


def _bad_title(t):
    if t and (_author_string(t) or re.search(r"Director\(s\)|Advisor\(s\)", t)):
        return True
    return (not t or len(t) < 10 or BAD_TITLE.match(t) is not None or _looks_authors(t) and t.count(",") >= 2
            or len(re.findall(r"[A-Za-z]", t)) < 8)


def _entry(school, row, text, title, head_year, views, links):
    if title:
        title = _trim_authors(title)
    if _bad_title(title):
        alt = _title_from_text(text)
        alt = _trim_authors(alt) if alt else alt
        if _bad_title(alt):
            return None
        title = alt
    nm, rest = lpdom.name_prefix(title)
    if nm and (not rest or rest[:1] in "(,-–|") and PERSONISH.search(text) and not VENUE_RX.search(text):
        return None  # a person line ("Jane Doe (co-advised with ...) (PhD 2020, Google)"), not a publication
    ys = _years(text)
    year = max(ys) if ys else head_year
    if ys and head_year and head_year in ys:
        year = head_year
    if len(title) > 250 or ABSTRACT_RX.match(title):
        return None
    namey = sum(1 for seg in re.split(r",|\band\b|;", text) if lpdom.looks_like_name(seg.strip(" .*0123456789")))
    linky = any(LINKY_RX.search(h) for h in links)
    if not (VENUE_RX.search(text) or linky or namey >= 2):
        return None  # no venue, no paper link, no author list: not a publication entry
    held = held_match(school, row["pi"], title, text)
    q = _quote(views, text, title)
    q = lpdom.collapse(q) if q else q
    seen, lk = set(), []
    for h in links:
        if h not in seen and h.startswith(("http://", "https://")):
            seen.add(h)
            lk.append(h)
    return {"text": text, "title": title, "year": year, "venue": _venue(text, title), "links": lk[:10], "quote": q,
            "held": bool(held), "held_title": held, "in_window": bool(year and 2016 <= year <= 2026)}


def parse_bib(school, row, cap, url):
    raw = lpcap.decode(cap["content"])
    views = lpcap.texts(cap["content"], cap.get("content_type"))
    out = []
    for m in re.finditer(r"@(\w+)\s*\{([^,]*),(.*?)(?=\n\s*@\w+\s*\{|\Z)", raw, re.S):
        body = m.group(3)

        def field(name):
            mm = re.search(r"\b" + name + r"\s*=\s*(\{(?:[^{}]|\{[^{}]*\})*\}|\"[^\"]*\"|\d+)", body, re.I | re.S)
            if not mm:
                return None, None
            v = mm.group(1)
            return lpdom.collapse(v.strip("{}\"").replace("{", "").replace("}", "")), lpdom.collapse(mm.group(0))
        title, tq = field("title")
        year, _ = field("year")
        venue, _ = field("booktitle")
        if not venue:
            venue, _ = field("journal")
        if not title:
            continue
        links = re.findall(r"https?://[^\s,}\"]+", body)[:6]
        y = int(year) if year and year.isdigit() else None
        held = held_match(school, row["pi"], title, title)
        q = tq if tq and tq in (views.get("raw") or "") else None
        out.append({"text": title, "title": title, "year": y, "venue": venue, "links": links, "quote": q,
                    "held": bool(held), "held_title": held, "in_window": bool(y and 2016 <= y <= 2026)})
    return out


def parse_links(school, row, cap, url):
    soup = lpdom.soup_of(cap["content"])
    base = url if cap.get("capture_url") else (cap.get("final_url") or url)
    views = lpcap.texts(cap["content"], cap.get("content_type"))
    heads = _year_headings_and_entries(soup, soup.find_all("a"))
    out = []
    for a in soup.find_all("a", href=True):
        t = _clean_title(a.get_text(" "))
        if len(t) < 20 or lpdom.looks_like_name(t):
            continue
        par = a.find_parent(lpdom.ENTRY_TAGS)
        text = lpdom.collapse(par.get_text(" ")) if par is not None else t
        if len(text) > 1500:
            text = t
        e = _entry(school, row, text, t, heads.get(id(a)), views, [urljoin(base, a["href"])] + _links(par, base))
        if e:
            out.append(e)
    return out


def parse_infoscience(school, row, cap, url):
    """EPFL lab pages that embed an Infoscience listing: div.list-group-item-publication with h4.infoscience_title,
    p.infoscience_authors, p.infoscience_publication_date, the venue in italics, DOI and record links."""
    soup = lpdom.soup_of(cap["content"])
    views = lpcap.texts(cap["content"], cap.get("content_type"))
    html = views.get("html") or ""
    base = url
    out = []
    for item in soup.select("div.list-group-item-publication"):
        te = item.select_one(".infoscience_title")
        if te is None:
            continue
        title = _clean_title(te.get_text(" "))
        if not title:
            continue
        de = item.select_one(".infoscience_publication_date")
        ys = _years(de.get_text(" ")) if de is not None else []
        if not ys:
            ys = _years(lpdom.collapse(item.get_text(" ")))
        year = max(ys) if ys else None
        ve = item.select_one(".infoscience_journal_publisher i, .infoscience_conference i, .infoscience_host i")
        venue = lpdom.collapse(ve.get_text(" ")) if ve is not None else None
        links = _links(item, base)
        ae = item.select_one(".infoscience_authors")
        authors = lpdom.collapse(ae.get_text(" ")) if ae is not None else ""
        q = None
        for cand in (lpdom.collapse(title + " " + authors) if authors else None, lpdom.collapse(te.get_text(" "))):
            if cand and cand in html:
                q = cand
                break
        held = held_match(school, row["pi"], title, title)
        out.append({"text": title + " " + authors, "title": title, "year": year, "venue": venue, "links": links,
                    "quote": q, "held": bool(held), "held_title": held, "in_window": bool(year and 2016 <= year <= 2026)})
    return out


def parse(school, row, cap, url, mode="auto"):
    nbib = len(re.findall(rb"@(?:inproceedings|article|misc|incollection|techreport|phdthesis|book|inbook|unpublished|"
                          rb"conference|online)\s*\{", cap["content"], re.I))
    if mode == "infoscience" or (mode == "auto" and b"infoscience_title" in cap["content"]):
        res = parse_infoscience(school, row, cap, url)
    elif mode == "bib" or (mode == "auto" and (url.endswith(".bib") or nbib >= 5)):
        res = parse_bib(school, row, cap, url)
    elif mode == "links":
        res = parse_links(school, row, cap, url)
    else:
        res = parse_auto(school, row, cap, url)
    # dedupe by normalized title (same page can repeat an entry in a "selected" list)
    seen, out = set(), []
    for e in res:
        k = norm(e["title"])
        if k in seen:
            continue
        seen.add(k)
        out.append(e)
    return out
