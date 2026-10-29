"""Publication-list extraction for the CMU lab-page pass.

extract(content, base_url, mode="auto", **opts) -> list of entries
  {title, year, venue, links, quote, entry, title_how}
  quote is an exact substring of capstore.page_text(content) (or raw_text for bibtex/json modes) that contains
  the title.

Modes (the worker picks the one that reads the page correctly; check with `lp.py pubs`):
  auto            choose between li / leaf-block / anchor modes by how citation-like the candidates look
  li              each <li> is one entry
  block           leaf block elements (p, div, td, dd, li) are entries
  css:<selector>  each element matching the CSS selector is one entry (e.g. css:div.publication)
  anchor          titles are link texts; the entry is the link text plus the following text up to the next title
  bibtex          the content is a BibTeX file
  json            the content is JSON; any dict with a title key is an entry
  text            plain text / PDF: entries are separated by blank-ish line breaks (uses raw lines)
Options: title_css=<selector> (title element inside each entry), min_len, max_len.

match_lab(title, entry_text, lab_index) -> matched lab title or None.
"""
import json
import re
import unicodedata
from urllib.parse import urljoin

import capstore

YEAR_RX = re.compile(r"(?<![\d./-])((?:19[89]\d|20[0-2]\d))(?![\d])(?!\.\d)")
GENERIC_ANCHOR = re.compile(r"^\s*(\[?\s*)?(pdf|paper|arxiv|code|slides?|video|talk|poster|bib(tex)?|abstract|"
                            r"project( page)?|website|doi|link|html|preprint|supplement(ary)?( material)?|data(set)?|"
                            r"github|demo|blog|press|news|acm|ieee|springer|openreview|proceedings|journal version|"
                            r"full version|extended version|conference version|tech(nical)? report|ps|ppt|"
                            r"published version|online appendix( link)?|appendix|errata|award|best paper.*)\s*(\]?)\s*$",
                            re.I)
VENUE_RX = re.compile(r"\b(conference|symposium|proceedings|workshop|journal|transactions|international|annual|"
                      r"letters|magazine|arxiv|preprint|thesis|technical report|in submission|under review)\b", re.I)
BLOCK_TAGS = ["p", "li", "div", "td", "dd", "dt", "tr", "article", "section", "blockquote"]
HEAD_TAGS = ["h1", "h2", "h3", "h4", "h5", "h6"]


def norm_title(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    s = re.sub(r"\\[a-z]+\{([^}]*)\}", r"\1", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def collapse(s):
    return re.sub(r"\s+", " ", s or "").strip()


def lab_index(titles):
    idx = []
    for t in titles:
        n = norm_title(t)
        if n:
            idx.append((n, t))
    return idx


def match_lab(title, entry_text, idx):
    """Return the lab-paper title this entry corresponds to, or None (normalized title compare)."""
    nt = norm_title(title)
    ne = norm_title(entry_text)
    if not nt and not ne:
        return None
    import difflib
    best = None
    for n, t in idx:
        if nt and (n == nt):
            return t
        if len(n) >= 25 and n in ne:
            return t
        if nt and len(nt) >= 25 and len(n) >= 25 and (nt in n or n in nt) and min(len(nt), len(n)) / max(len(nt), len(n)) > 0.7:
            return t
        if nt and abs(len(n) - len(nt)) < 0.25 * max(len(n), len(nt)):
            if n[:8] == nt[:8] or n[-8:] == nt[-8:]:
                r = difflib.SequenceMatcher(None, n, nt).ratio()
                if r >= 0.9 and (best is None or r > best[0]):
                    best = (r, t)
    if best:
        return best[1]
    # fall back: fuzzy over all titles with similar length (slower)
    if nt and len(nt) >= 20:
        for n, t in idx:
            if abs(len(n) - len(nt)) < 0.15 * max(len(n), len(nt)):
                if difflib.SequenceMatcher(None, n, nt).quick_ratio() >= 0.9 and \
                        difflib.SequenceMatcher(None, n, nt).ratio() >= 0.9:
                    return t
    return None


def years_in(text):
    out = []
    for m in YEAR_RX.finditer(text):
        y = int(m.group(1))
        if 1990 <= y <= 2026:
            out.append(y)
    return out


def _links(el, base):
    out = []
    for a in el.find_all("a", href=True):
        h = a["href"].strip()
        if h.startswith(("mailto:", "javascript:", "#")):
            continue
        u = urljoin(base, h)
        o, cap = capstore.split_wayback(u)
        if cap:
            u = o
        if u not in out:
            out.append(u)
    return out[:12]


def _is_authorish(seg):
    toks = seg.split()
    if len(toks) < 2:
        return False
    caps = sum(1 for t in toks if t[:1].isupper() or t.lower() in ("and", "&", "de", "van", "von", "der", "la", "et", "al.", "al"))
    return (seg.count(",") >= 1 or " and " in seg) and caps / len(toks) > 0.8


def _title_from_text(t):
    """Heuristic title from a citation string."""
    m = re.search(r"[\u201c\"]([^\u201d\"]{12,400})[\u201d\"]", t)
    if m:
        return m.group(1).strip().rstrip(",."), "quoted"
    segs = [s.strip() for s in re.split(r"(?<=[a-z0-9\)\]\?!])\.\s+(?=[A-Z0-9\"\u201c])", t) if s.strip()]
    if len(segs) >= 2:
        if _is_authorish(segs[0]) and len(segs[1].split()) >= 3:
            return segs[1].rstrip("."), "after-authors"
        if len(segs[0].split()) >= 4 and not _is_authorish(segs[0]):
            return segs[0].rstrip("."), "first-sentence"
    return None, None


def _title_in(el, text, base, title_css=None):
    if title_css:
        x = el.select_one(title_css)
        if x is not None:
            tt = collapse(x.get_text(" "))
            if len(tt) >= 8:
                return tt, "title_css"
    for x in el.find_all(True, class_=re.compile(r"title", re.I)):
        tt = collapse(x.get_text(" "))
        if 12 <= len(tt) <= 400:
            return tt, "class-title"
    m = re.search(r"[\u201c\"]([^\u201d\"]{12,400})[\u201d\"]", text)
    if m:
        return m.group(1).strip().rstrip(",."), "quoted"
    for a in el.find_all("a"):
        tt = collapse(a.get_text(" "))
        if len(tt.split()) >= 3 and len(tt) >= 15 and not GENERIC_ANCHOR.match(tt) and not tt.startswith("http"):
            return tt.rstrip("."), "anchor"
    for x in el.find_all(["b", "strong"]):
        if x.find_parent(["i", "em"]):
            continue
        tt = collapse(x.get_text(" "))
        if len(tt.split()) >= 3 and len(tt) >= 15:
            return tt.rstrip("."), "bold"
    t, how = _title_from_text(text)
    if t:
        return t, how
    return None, None


def _venue(text, title):
    i = text.find(title) if title else -1
    rest = text[i + len(title):] if i >= 0 else ""
    rest = re.sub(r"^[\s.,:;\"\u201d]+", "", rest)
    m = YEAR_RX.search(rest)
    v = rest[:m.start()] if m else rest[:160]
    v = re.sub(r"\[(pdf|bib|arxiv|code|slides|video)[^\]]*\]", " ", v, flags=re.I)
    v = collapse(v).strip(" ,.;:()")
    if len(v) < 3:
        return None
    return v[:200]


def _venue_el(el, title):
    """Italic / emphasised text in the entry that is not the title (typical venue markup)."""
    nt = norm_title(title)
    for x in el.find_all(["i", "em", "cite"]) + el.find_all(True, class_=re.compile(r"venue|journal|booktitle|conf", re.I)):
        tt = collapse(x.get_text(" "))
        if len(tt) >= 3 and not re.fullmatch(r"[\d\s().,:-]+", tt) and norm_title(tt) != nt and norm_title(tt) not in nt:
            return tt[:200]
    return None


def _heading_years(soup):
    """Map each element to the year of the nearest preceding heading/strong-only block that is just a year."""
    marks = []
    for h in soup.find_all(HEAD_TAGS + ["strong", "b", "p", "div", "span", "dt", "button", "summary"]):
        tt = collapse(h.get_text(" "))
        if re.fullmatch(r"(19[89]\d|20[0-2]\d)\s*:?", tt) or re.fullmatch(r"(Year\s*)?(19[89]\d|20[0-2]\d)\s*(publications?|papers)?", tt, re.I):
            marks.append(h)
    return marks


def _leaf_blocks(soup):
    out = []
    for el in soup.find_all(BLOCK_TAGS):
        if el.find(BLOCK_TAGS):
            # a block containing blocks is a container unless its own direct text dominates
            continue
        out.append(el)
    return out


def _citationish(text):
    return 40 <= len(text) <= 1500 and bool(years_in(text)) and len(text.split()) >= 6


def _entries_for(soup, mode):
    if mode == "li":
        return [el for el in soup.find_all("li")]
    if mode == "block":
        return _leaf_blocks(soup)
    if mode.startswith("css:"):
        return soup.select(mode[4:])
    raise ValueError(mode)


def _assign_heading_years(soup, els):
    """Year from the nearest preceding year heading, for entries with no year of their own."""
    marks = set(id(m) for m in _heading_years(soup))
    if not marks:
        return {}
    cur = None
    res = {}
    targets = set(id(e) for e in els)
    for el in soup.find_all(True):
        if id(el) in marks:
            cur = int(re.search(r"(19[89]\d|20[0-2]\d)", el.get_text(" ")).group(1))
        if id(el) in targets:
            res[id(el)] = cur
    return res


def extract(content, base_url, mode="auto", title_css=None, min_len=25, max_len=2500):
    if mode == "bibtex":
        return _bibtex(content)
    if mode == "json":
        return _json(content)
    if mode == "text" or capstore.is_pdf(content):
        return _text(content)
    soup = capstore.soup_of(content)
    ptext = collapse(soup.get_text(" "))
    if mode == "auto":
        best = None
        for m in ("li", "block"):
            els = _entries_for(soup, m)
            n = sum(1 for e in els if _citationish(collapse(e.get_text(" "))))
            if best is None or n > best[1]:
                best = (m, n)
        an = _anchor_entries(soup, base_url, ptext, count_only=True)
        if best[1] < 5 and an > best[1] * 2:
            mode = "anchor"
        else:
            mode = best[0]
    if mode == "anchor":
        return _anchor_entries(soup, base_url, ptext)
    els = _entries_for(soup, mode)
    hy = _assign_heading_years(soup, els)
    out, seen = [], set()
    for el in els:
        text = collapse(el.get_text(" "))
        if not (min_len <= len(text) <= max_len):
            continue
        title, how = _title_in(el, text, base_url, title_css)
        if not title:
            continue
        if how in ("first-sentence", "after-authors") and VENUE_RX.search(title):
            continue
        ys = years_in(text.replace(title, " "))
        year = ys[-1] if ys else hy.get(id(el))
        key = norm_title(title)
        if key in seen:
            continue
        seen.add(key)
        quote = text if text in ptext else (title if title in ptext else None)
        if quote and len(quote) > 900:
            i = quote.find(title)
            quote = quote[max(0, i - 200): i + len(title) + 300].strip() if i >= 0 else title
            if quote not in ptext:
                quote = title if title in ptext else None
        out.append({"title": title, "year": year, "venue": _venue_el(el, title) or _venue(text, title),
                    "links": _links(el, base_url),
                    "quote": quote, "entry": text[:1500], "title_how": how})
    return out


def _anchor_entries(soup, base, ptext, count_only=False):
    anchors = []
    for a in soup.find_all("a"):
        tt = collapse(a.get_text(" "))
        if len(tt.split()) >= 3 and len(tt) >= 15 and not GENERIC_ANCHOR.match(tt) and not tt.startswith("http") \
                and len(tt) <= 300:
            anchors.append((a, tt))
    if count_only:
        return len(anchors)
    out, seen = [], set()
    # text after each anchor up to the next anchor title, located in the page text
    pos = 0
    locs = []
    for a, tt in anchors:
        i = ptext.find(tt, pos)
        if i < 0:
            i = ptext.find(tt)
            if i < 0:
                continue
        locs.append((i, a, tt))
        pos = i + len(tt)
    locs.sort(key=lambda x: x[0])
    hy = _assign_heading_years(soup, [a for _, a, _ in locs])
    for k, (i, a, tt) in enumerate(locs):
        j = locs[k + 1][0] if k + 1 < len(locs) else min(len(ptext), i + 600)
        j = min(j, i + 900)
        text = ptext[i:j].strip()
        key = norm_title(tt)
        if key in seen:
            continue
        seen.add(key)
        ys = years_in(text[len(tt):])
        year = ys[0] if ys else hy.get(id(a))
        par = a.find_parent(BLOCK_TAGS) or a
        out.append({"title": tt.rstrip("."), "year": year, "venue": _venue(text, tt), "links": _links(par, base),
                    "quote": text if text in ptext else tt, "entry": text, "title_how": "anchor"})
    return out


def _bibtex(content):
    raw = capstore._decode(content)
    rt = capstore.raw_text(content)
    out = []
    for m in re.finditer(r"@(\w+)\s*\{", raw):
        start = m.end()
        depth, i = 1, start
        while i < len(raw) and depth:
            if raw[i] == "{":
                depth += 1
            elif raw[i] == "}":
                depth -= 1
            i += 1
        body = raw[start:i - 1]
        f = {}
        for fm in re.finditer(r"(\w+)\s*=\s*", body):
            k = fm.group(1).lower()
            j = fm.end()
            if j < len(body) and body[j] == "{":
                d, q = 1, j + 1
                while q < len(body) and d:
                    if body[q] == "{":
                        d += 1
                    elif body[q] == "}":
                        d -= 1
                    q += 1
                f.setdefault(k, body[j + 1:q - 1])
            elif j < len(body) and body[j] == '"':
                q = body.find('"', j + 1)
                f.setdefault(k, body[j + 1:q])
            else:
                mm = re.match(r"[^,\n]+", body[j:])
                f.setdefault(k, mm.group(0).strip() if mm else "")
        if "title" not in f:
            continue
        rawtitle = collapse(f["title"])
        title = collapse(re.sub(r"[{}]", "", f["title"]))
        y = years_in(f.get("year", ""))
        quote = None
        for cand in (rawtitle, title):
            if cand and cand in rt:
                quote = cand
                break
        out.append({"title": title, "year": y[0] if y else None,
                    "venue": collapse(re.sub(r"[{}]", "", f.get("booktitle") or f.get("journal") or "")) or None,
                    "links": [x for x in (f.get("url"), ("https://doi.org/" + f["doi"]) if f.get("doi") else None,
                                          f.get("pdf"), f.get("eprint")) if x],
                    "quote": quote, "entry": collapse(body)[:1500], "title_how": "bibtex", "raw": True})
    return out


def _json(content):
    try:
        d = json.loads(capstore._decode(content))
    except Exception:
        return []
    rt = capstore.raw_text(content)
    out = []

    def walk(x):
        if isinstance(x, dict):
            t = x.get("title") or x.get("Title") or x.get("name")
            if isinstance(t, str) and len(t) >= 10 and any(k in x for k in ("year", "date", "venue", "authors",
                                                                           "author", "booktitle", "journal", "pub_year")):
                yv = str(x.get("year") or x.get("pub_year") or x.get("date") or "")
                y = years_in(yv)
                venue = x.get("venue") or x.get("booktitle") or x.get("journal") or x.get("conference")
                links = [v for k, v in x.items() if isinstance(v, str) and v.startswith("http")][:8]
                tq = json.dumps(t)[1:-1]
                quote = t if t in rt else (tq if tq in rt else None)
                out.append({"title": collapse(t), "year": y[0] if y else None,
                            "venue": venue if isinstance(venue, str) else None, "links": links, "quote": quote,
                            "entry": collapse(json.dumps(x))[:1500], "title_how": "json", "raw": True})
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(d)
    return out


def _text(content):
    if capstore.is_pdf(content):
        raw = capstore.pdf_text(content)
    else:
        raw = capstore._decode(content)
    pt = capstore.page_text(content)
    paras = re.split(r"\n\s*\n|\n(?=\s*\[?\d{1,3}[\].]\s)", raw)
    out = []
    for p in paras:
        text = collapse(p)
        if not _citationish(text):
            continue
        title, how = _title_from_text(text)
        if not title:
            continue
        ys = years_in(text.replace(title, " "))
        out.append({"title": title, "year": ys[-1] if ys else None, "venue": _venue(text, title), "links": [],
                    "quote": text if text in pt else (title if title in pt else None), "entry": text[:1500],
                    "title_how": how})
    return out
