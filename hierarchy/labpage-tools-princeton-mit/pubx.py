"""Publication-list extraction for the lab-page pass, and the compare against the PI's lab papers.

extract(school, src, spec) -> list of entries {title, year, venue, links, quote, text} from a stored capture (src = live
URL, Wayback id_ URL, or sha256). Each entry's quote is an exact substring of one whitespace-collapsed text view of the
stored bytes (the entry's own text when <= 900 chars, else the title).

spec (all optional; CSS selectors are BeautifulSoup .select syntax):
  root        container to search in (default: <body>)
  item        selector of one publication entry (default: auto-detected repeated element)
  title       selector of the title inside an entry (default: heuristics: .title, quoted text, long link, bold, ...)
  venue       selector of the venue inside an entry
  year        selector of the year inside an entry
  year_heading  true: take the year from the nearest preceding heading (h1-h6/strong/b/dt whose text is a year)
              (default: the year in the entry text, else the heading year)
  title_rx    regex with one group applied to the entry text to get the title (overrides `title`)
  title_br    true: the title is the entry's text before its first <br>
  skip_rx     regex: entries whose text matches are dropped (e.g. talks, patents)
  min_len     minimum entry text length (default 25)
  split       tag name (e.g. "hr", "br"): entries are the runs of HTML between these tags inside root (for layouts with no
              per-entry container); `item` then optionally selects inside each run
  default_year  year to use when an entry shows none (e.g. a page section known to be one year)
  (BibTeX files are parsed automatically: title/year/booktitle|journal/url/doi; quote = the raw title field)
  json        for a JSON data file: {"list": "dotted.path.to.list" or "", "title": "key", "year": "key", "venue": "key",
              "links": ["key", ...]}; quote = the title as it appears in the raw JSON text

usage (CLI, for checking a page): pubx.py SCHOOL "PI name" URL [--spec JSON] [--show N] [--all]
"""
import argparse
import difflib
import gzip
import json
import os
import re
import sys
from urllib.parse import urljoin

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lpcap  # noqa: E402
import lpev  # noqa: E402

ROOT = lpcap.ROOT
YEAR_RX = re.compile(r"(?<![0-9])((?:19[89]|20[0-2])[0-9])(?![0-9])")
LINKWORD = re.compile(r"^\s*\[?\s*(pdf|paper|arxiv|code|slides?|video|talk|poster|bib(tex)?|project( page)?|website|"
                      r"doi|abstract|html|link|preprint|full ?text|supplement(ary)?|data(set)?|github|blog|demo|"
                      r"press|media|acm|ieee|springer|openreview|proceedings|journal|conference|extended version|"
                      r"tech(nical)? report|ssrn|biorxiv|medrxiv|pubmed|nature|science|camera[- ]ready|award|"
                      r"\d+ citations?)\s*\]?\s*$", re.I)
VENUE_HINT = re.compile(r"\b(proceedings|conference|journal|transactions|symposium|workshop|arxiv|preprint|in proc|"
                        r"advances in|letters|review|neurips|icml|iclr|cvpr|iccv|eccv|acl|emnlp|naacl|sigcomm|nsdi|"
                        r"osdi|sosp|pldi|popl|stoc|focs|soda|chi|cscw|uist|kdd|www|aaai|ijcai|usenix|ccs|siggraph)\b", re.I)
LINK_KEEP = re.compile(r"(\.pdf($|\?)|arxiv\.org|doi\.org|/doi/|openreview\.net|aclanthology|dl\.acm\.org|ieeexplore|"
                       r"proceedings\.|papers\.nips|neurips\.cc|mlr\.press|biorxiv|medrxiv|nature\.com|science\.org|"
                       r"springer|sciencedirect|usenix\.org|jmlr|pubmed|ncbi\.nlm|ssrn)", re.I)


def norm_title(t):
    t = lpev.fold(t or "")
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"[^a-z0-9]+", "", t)


_lab = {}


def lab_titles(school, pi):
    if school not in _lab:
        d = {}
        with gzip.open(f"{ROOT}/{school}/lab_papers.jsonl.gz", "rt", encoding="utf-8") as f:
            for line in f:
                o = json.loads(line)
                d.setdefault(o["pi"], []).append(o)
        _lab[school] = d
    return _lab[school].get(pi, [])


def matcher(school, pi):
    rows = lab_titles(school, pi)
    normed = [(norm_title(r.get("title")), r) for r in rows if r.get("title")]
    exact = {n: r for n, r in normed}

    def find(title):
        n = norm_title(title)
        if not n:
            return None
        if n in exact:
            return exact[n]
        best, br = None, 0.0
        for m, r in normed:
            if not m:
                continue
            short, long_ = (n, m) if len(n) <= len(m) else (m, n)
            if len(short) >= 30 and long_.startswith(short) and len(short) / len(long_) >= 0.5:
                return r
            sm = difflib.SequenceMatcher(None, n, m, autojunk=False)
            if sm.real_quick_ratio() < 0.9 or sm.quick_ratio() < 0.9:
                continue
            ratio = sm.ratio()
            if ratio > br:
                best, br = r, ratio
        return best if br >= 0.92 else None
    return find


def _soup(content):
    import warnings
    from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
    soup = BeautifulSoup(lpcap.decode(content), "lxml")
    for t in soup(["script", "style", "noscript", "template"]):
        t.decompose()
    return soup


def _txt(el):
    return lpcap.collapse(el.get_text(" "))


def _sig(el):
    return el.name, tuple(sorted(c for c in (el.get("class") or []) if not re.match(r"^(odd|even|active|first|last|show|hidden|"
                                                                                       r"col-\S+|row|clearfix)$", c)))


def auto_items(root, min_len=25):
    groups = {}
    for el in root.find_all(["li", "p", "div", "tr", "dd", "article", "section", "td", "span", "dt", "blockquote"]):
        t = _txt(el)
        if not (min_len <= len(t) <= 2500):
            continue
        has_year = bool(YEAR_RX.search(t))
        has_link = any(LINK_KEEP.search(a.get("href") or "") for a in el.find_all("a", href=True))
        if not (has_year or has_link):
            continue
        groups.setdefault(_sig(el), []).append(el)
    best, score = None, 0
    pref = {"li": 1.15, "div": 1.05, "p": 1.0, "tr": 1.0, "dd": 1.0, "article": 1.1, "td": 0.8, "span": 0.6, "section": 0.7,
            "dt": 0.6, "blockquote": 0.9}
    for sig, els in groups.items():
        ids = set(map(id, els))
        # drop elements that contain other members of the same group (keep the innermost)
        leaf = [e for e in els if not any(id(d) in ids for d in e.find_all(sig[0]))]
        s = len(leaf) * pref.get(sig[0], 0.8) * (1.1 if sig[1] else 1.0)
        if s > score:
            best, score = leaf, s
    return best or []


def _is_authorish(s):
    words = re.findall(r"[A-Za-zÀ-ÿ'’.-]+", s)
    if not words:
        return False
    caps = sum(1 for w in words if w[0].isupper() or w in ("and", "&"))
    commas = s.count(",")
    if commas >= 2 and caps / len(words) >= 0.75:
        return True
    if re.search(r"^[A-Z][\w.'’-]+( [A-Z][\w.'’-]+){0,3} (and|&) [A-Z][\w.'’-]+( [A-Z][\w.'’-]+){0,3}\.?$", s.strip()):
        return True
    return False


def auto_title(item):
    cands = []
    for el in item.select("[class*=title]"):
        cl = " ".join(el.get("class") or [])
        if re.search(r"subtitle|booktitle", cl):
            continue
        t = _txt(el)
        if len(t.split()) >= 2:
            return t
    t = _txt(item)
    m = re.search(r"[“\"]([^”\"]{12,400}?)[,.]?[”\"]", t)
    if m and len(m.group(1).split()) >= 3:
        return m.group(1).strip().rstrip(",.")
    for a in item.find_all("a"):
        at = _txt(a)
        if len(at) >= 15 and len(at.split()) >= 3 and not LINKWORD.match(at) and not _is_authorish(at) \
                and not VENUE_HINT.match(at):
            cands.append(at)
            break
    if cands:
        return cands[0]
    for tag in ("b", "strong", "h3", "h4", "h5", "h2"):
        for el in item.find_all(tag):
            et = _txt(el)
            if len(et.split()) >= 3 and not _is_authorish(et) and not YEAR_RX.fullmatch(et):
                return et.rstrip(".")
    for el in item.find_all(["em", "i"]):
        et = _txt(el)
        if len(et.split()) >= 4 and not VENUE_HINT.search(et) and not _is_authorish(et):
            return et.rstrip(".")
    # fallback: first sentence-ish segment that is not an author list or a venue
    segs = [s.strip() for s in re.split(r"(?<=[.?!])\s+(?=[A-Z0-9“\"])", t) if s.strip()]
    for s in segs:
        if len(s.split()) >= 3 and not _is_authorish(s) and not VENUE_HINT.search(s[:40]) and not re.match(r"^In\b", s):
            return s.rstrip(".")
    return None


def _heading_year(el):
    for prev in el.find_all_previous(["h1", "h2", "h3", "h4", "h5", "h6", "strong", "b", "dt", "button", "summary", "a"]):
        t = _txt(prev)
        m = re.fullmatch(r"\D{0,20}((?:19[89]|20[0-2])\d)\D{0,12}", t)
        if m and prev.name != "a" or (prev.name == "a" and m and len(t) <= 6):
            return int(m.group(1))
    return None


def _year_of(text, title):
    rest = text.replace(title or "", " ")
    ys = [int(y) for y in YEAR_RX.findall(rest) if 1980 <= int(y) <= 2026]
    if ys:
        return ys[-1]
    m = re.search(r"\b[A-Z][A-Za-z+]{1,12}\s?['’](\d\d)\b", rest)  # venue with a two-digit year: STOC'21
    if m:
        y = 2000 + int(m.group(1))
        return y if y <= 2026 else None
    return None


def extract(school, src, spec=None):
    spec = spec or {}
    r, views = lpev.cap(school, src)
    kind = lpcap.kind_of(r["content"], r.get("content_type"))
    base = r.get("final_url") or r["url"]
    out = []
    if spec.get("json") or kind == "json":
        js = spec.get("json") or {}
        data = json.loads(lpcap.decode(r["content"]))
        lst = data
        for k in [k for k in (js.get("list") or "").split(".") if k]:
            lst = lst[int(k)] if isinstance(lst, list) else lst[k]
        raw = views.get("raw", "")
        for o in lst if isinstance(lst, list) else []:
            if not isinstance(o, dict):
                continue
            title = lpcap.collapse(str(o.get(js.get("title", "title")) or ""))
            if not title:
                continue
            y = o.get(js.get("year", "year"))
            try:
                y = int(str(y)[:4])
            except Exception:
                y = None
            venue = o.get(js.get("venue", "venue"))
            links = [o.get(k) for k in js.get("links", []) if o.get(k)]
            q = title if title in raw else lpcap.collapse(json.dumps(title, ensure_ascii=False)[1:-1])
            if q not in raw:
                continue
            out.append({"title": title, "year": y, "venue": venue if isinstance(venue, str) else None, "links": links,
                        "quote": q, "text": title})
        return r, out
    if kind != "html":
        raw = views.get("raw", "")
        if re.search(r"@(article|inproceedings|misc|incollection|phdthesis|techreport|book|unpublished)\s*\{", raw, re.I):
            for m in re.finditer(r"@(\w+)\s*\{(.*?)(?=@\w+\s*\{|$)", raw, re.S):
                body = m.group(2)
                def fld(name):
                    mm = re.search(r"\b%s\s*=\s*(\{(?:[^{}]|\{[^{}]*\})*\}|\"[^\"]*\"|\d+)" % name, body, re.I)
                    return mm if mm else None
                tm = fld("title")
                if not tm:
                    continue
                title = lpcap.collapse(re.sub(r"[{}\\]", "", tm.group(1)).strip('"'))
                ym = fld("year")
                y = int(re.sub(r"\D", "", ym.group(1))[:4]) if ym and re.sub(r"\D", "", ym.group(1)) else None
                vm = fld("booktitle") or fld("journal")
                venue = lpcap.collapse(re.sub(r"[{}\\]", "", vm.group(1)).strip('"')) if vm else None
                links = [lpcap.collapse(re.sub(r"[{}]", "", x.group(1)).strip('"')) for x in [fld("url"), fld("doi")] if x]
                q = lpcap.collapse(tm.group(0))
                if q in raw:
                    out.append({"title": title, "year": y, "venue": venue, "links": links, "quote": q, "text": q})
        return r, out
    soup = _soup(r["content"])
    root = soup.select_one(spec["root"]) if spec.get("root") else (soup.body or soup)
    if root is None:
        return r, out
    min_len = spec.get("min_len", 25)
    if spec.get("split"):
        # entries are runs of siblings separated by a tag (e.g. <hr> or <br>): parse each run as one pseudo-entry
        from bs4 import BeautifulSoup
        tag = spec["split"]
        chunks = re.split(r"<%s\b[^>]*/?>" % re.escape(tag), str(root), flags=re.I)
        items = [BeautifulSoup(c, "lxml") for c in chunks if c.strip()]
        if spec.get("item"):
            items = [x for c in items for x in c.select(spec["item"])]
    else:
        items = root.select(spec["item"]) if spec.get("item") else auto_items(root, min_len)
    page_views = [v for v in views.values() if v]
    for it in items:
        t = _txt(it)
        if len(t) < min_len:
            continue
        if spec.get("skip_rx") and re.search(spec["skip_rx"], t, re.I):
            continue
        title = None
        if spec.get("title_br"):
            from bs4 import BeautifulSoup
            first = re.split(r"<br\s*/?>", str(it), maxsplit=1, flags=re.I)[0]
            title = lpcap.collapse(BeautifulSoup(first, "lxml").get_text(" ")) or None
        elif spec.get("title_rx"):
            m = re.search(spec["title_rx"], t, re.I if spec.get("title_rx_i") else 0)
            title = m.group(1).strip() if m else None
        elif spec.get("title"):
            el = it.select_one(spec["title"])
            title = _txt(el) if el else None
        if not title:
            title = auto_title(it)
        if not title:
            continue
        title = title.strip().strip("“”\"").rstrip(",.").strip()
        title = re.sub(r"^(?:\d{1,4}\.\s+|\[[A-Za-z]+\d{2}[a-z]?\]\s+)+", "", title)  # "299. Title", "[Riv20e] Title"
        if len(title) < 8:
            continue
        if spec.get("year"):
            el = it.select_one(spec["year"])
            m = YEAR_RX.search(_txt(el)) if el else None
            year = int(m.group(1)) if m else None
        elif spec.get("year_heading"):
            year = _heading_year(it)
        else:
            year = _year_of(t, title) or _heading_year(it)
        if year is None:
            for h in [urljoin(base, a["href"]) for a in it.find_all("a", href=True)]:
                m = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{2})(\d{2})\.\d{4,5}", h)
                if m and 7 <= int(m.group(1)) <= 26:
                    year = 2000 + int(m.group(1))
                    break
        if year is None:
            year = spec.get("default_year")
        venue = None
        if spec.get("venue"):
            el = it.select_one(spec["venue"])
            venue = _txt(el) if el else None
        else:
            for el in it.find_all(["em", "i"]):
                et = _txt(el)
                if et and et != title and title not in et and len(et) >= 3:
                    venue = et
                    break
            if not venue:
                after = t.split(title, 1)[1] if title in t else ""
                m = re.search(r"([^.]*\b(?:proceedings|conference|journal|transactions|symposium|workshop|arxiv|preprint|"
                              r"neurips|icml|iclr|cvpr|acl|emnlp|chi|cscw|kdd|aaai|usenix|nature|science)\b[^.]*)", after, re.I)
                venue = m.group(1).strip(" ,.") if m else None
        links = []
        for a in it.find_all("a", href=True):
            h = urljoin(base, a["href"])
            if LINK_KEEP.search(h) and h not in links:
                links.append(h)
        quote = t if len(t) <= 900 and any(t in v for v in page_views) else None
        if quote is None:
            if any(title in v for v in page_views):
                quote = title
            else:
                continue
        out.append({"title": title, "year": year, "venue": venue, "links": links, "quote": quote, "text": t})
    return r, out


def missing(school, pi, src, spec=None, years=(2016, 2026)):
    """(capture row, all entries in the year window, entries not among the PI's lab papers)."""
    r, ents = extract(school, src, spec)
    find = matcher(school, pi)
    inwin, miss, seen = [], [], set()
    for e in ents:
        if e["year"] is None or not (years[0] <= e["year"] <= years[1]):
            continue
        k = norm_title(e["title"])
        if k in seen:
            continue
        seen.add(k)
        inwin.append(e)
        m = find(e["title"])
        e["matched"] = (m or {}).get("title")
        if not m:
            miss.append(e)
    return r, inwin, miss


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("school")
    ap.add_argument("pi")
    ap.add_argument("url")
    ap.add_argument("--spec", default=None)
    ap.add_argument("--show", type=int, default=15)
    ap.add_argument("--all", action="store_true", help="show every entry incl. out-of-window and matched")
    a = ap.parse_args()
    spec = json.loads(a.spec) if a.spec else None
    r, ents = extract(a.school, a.url, spec)
    yrs = [e["year"] for e in ents]
    print(f"{len(ents)} entries; years: none={sum(1 for y in yrs if y is None)} <2016={sum(1 for y in yrs if y and y < 2016)} "
          f"2016-2026={sum(1 for y in yrs if y and 2016 <= y <= 2026)}; lab papers for PI: {len(lab_titles(a.school, a.pi))}")
    r, inwin, miss = missing(a.school, a.pi, a.url, spec)
    print(f"in window: {len(inwin)}; matched: {len(inwin) - len(miss)}; missing: {len(miss)}")
    show = ents if a.all else miss
    for e in show[:a.show]:
        print(json.dumps({k: e.get(k) for k in ("year", "title", "venue", "matched")}, ensure_ascii=False)[:400])
        print("    links:", e["links"][:3], "| quote:", e["quote"][:160])


if __name__ == "__main__":
    main()
