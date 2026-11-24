"""Worker CLI for the CMU lab-page pass. Every fetch goes through capstore (polite, robots-aware, cached).
Set LABPAGE_DB to the worker's own local SQLite file before using it.

  lp.py info PI                        input row + pre-crawl summary (seed, people/pubs candidates, Wayback years)
  lp.py get URL [--compact] [--grep RX] [--links RX] [--from STR] [--head N] [--chars N] [--wb] [--force]
  lp.py cdx URL [--all]                yearly (or all distinct) Wayback 200 captures
  lp.py wb URL YEAR [YEAR ...] [--compact|--grep RX]   fetch the capture of URL in each YEAR (id_)
  lp.py find URL NAME [NAME ...]       where each name occurs in the stored page text, with the nearest heading
  lp.py pubs PI URL [--mode M] [--title-css S] [--show N]   preview publication extraction vs lab papers
  lp.py check MODULE                   dry build of decisions/MODULE.py (quotes, held matches, pubs stats)
  lp.py held NAME                      which CMU PIs already hold a person of this name (students.json)

URLs may be live or Wayback ("https://web.archive.org/web/<ts>id_/<orig>"; other Wayback forms are normalised).
"""
import argparse
import gzip
import signal
import json
import os
import re
import subprocess
import sys
from urllib.parse import urljoin

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import capstore  # noqa: E402

SUMMARY = capstore.STATE + "/crawl-summary.jsonl"
HEADS = ["h1", "h2", "h3", "h4", "h5", "h6"]
LEAF = ["p", "li", "td", "th", "dd", "dt", "figcaption", "caption", "a", "span", "div", "strong", "b", "em", "i",
        "small", "label", "button"]


def meta(r):
    m = {k: r.get(k) for k in ("url", "final_url", "capture_url", "status", "sha256", "error", "cached")}
    if r.get("final_url") and capstore.WAYBACK_RX.match(r.get("final_url") or ""):
        m["actual_capture"] = capstore.actual_capture(r)
    return m


BLOCKS = set(HEADS + ["p", "li", "td", "th", "dd", "dt", "div", "section", "article", "tr", "ul", "ol", "table",
                      "figcaption", "blockquote", "header", "footer", "nav", "main", "aside", "body", "br", "hr",
                      "form", "dl", "figure", "address", "pre"])


def compact(content, width=160):
    """Page text as one line per block element (headings marked ##); long lines (bios) are cut to WIDTH chars."""
    if capstore.is_pdf(content) or not capstore.is_html(capstore._decode(content)):
        return capstore.page_text(content)[:20000]
    from bs4 import NavigableString, Comment
    soup = capstore.soup_of(content)
    lines, cur, cur_blk = [], [], None

    def flush():
        if cur:
            t = re.sub(r"\s+", " ", " ".join(cur)).strip()
            if t:
                h = cur_blk is not None and cur_blk.name in HEADS
                t = t if len(t) <= width else t[:width] + " ..."
                lines.append(("## " if h else "") + t)
    for sstr in soup.find_all(string=True):
        if isinstance(sstr, Comment) or not sstr.strip():
            continue
        blk = sstr.parent
        while blk is not None and blk.name not in BLOCKS:
            blk = blk.parent
        # a <br> between strings of the same block also breaks the line
        prev_br = False
        pv = sstr.previous_sibling
        while pv is not None and isinstance(pv, NavigableString) and not pv.strip():
            pv = pv.previous_sibling
        if pv is not None and getattr(pv, "name", None) == "br":
            prev_br = True
        if blk is not cur_blk or prev_br:
            flush()
            cur, cur_blk = [], blk
        cur.append(str(sstr))
    flush()
    out, last = [], None
    for l in lines:
        if l != last:
            out.append(l)
        last = l
    return "\n".join(out)


def cmd_info(a):
    rows = json.load(open(capstore.P.data("labpage-input.json", "cmu")))
    row = next((r for r in rows if r["pi"] == a.pi), None)
    if not row:
        cands = [r["pi"] for r in rows if a.pi.lower() in r["pi"].lower()]
        print("no such PI; candidates:", cands)
        return
    print(json.dumps(row, indent=1, ensure_ascii=False))
    if os.path.exists(SUMMARY):
        for line in open(SUMMARY):
            d = json.loads(line)
            if d.get("pi") != a.pi:
                continue
            print("--- crawl summary")
            print("seed:", json.dumps(d.get("seed")))
            if d.get("meta_refresh"):
                print("meta refresh ->", d["meta_refresh"], json.dumps(d.get("seed_refresh")))
            for k in ("labs", "people", "pubs"):
                for x in d.get(k) or []:
                    f = x.get("fetch") or {}
                    print(f"{k}: {x['url']} | {x.get('text', '')[:50]} | status={f.get('status')} "
                          f"err={f.get('error')} final={f.get('final_url')}")
            for u, ys in (d.get("cdx") or {}).items():
                print("wayback yearly:", u, " ".join(t[:8] for t in ys))
            if d.get("errors") or d.get("fatal"):
                print("errors:", d.get("errors"), d.get("fatal"))


def show(r, a):
    print(json.dumps(meta(r)))
    c = r.get("content")
    if not c:
        return
    if a.compact:
        t = compact(c)
        if a.frm:
            i = t.find(a.frm)
            t = t[i:] if i >= 0 else t
        print(t[: a.head])
        return
    t = capstore.page_text(c)
    print(f"  [len {len(t)}]")
    if a.grep:
        n = 0
        for m in re.finditer(a.grep, t, flags=re.I):
            s = max(0, m.start() - a.chars // 2)
            print("  >>" + t[s:m.end() + a.chars // 2])
            n += 1
            if n >= a.maxhits:
                break
        if n == 0:
            print("  (no grep match) head: " + t[:300])
    elif a.frm:
        i = t.find(a.frm)
        print(t[i:i + a.head] if i >= 0 else "(from-string not found)")
    else:
        print(t[: a.head])
    if a.links:
        try:
            soup = capstore.soup_of(c)
            seen = set()
            base = r.get("url")
            for el in soup.find_all("a", href=True):
                href = urljoin(base, el["href"])
                o, cap = capstore.split_wayback(href)
                href = o if cap else href
                txt = re.sub(r"\s+", " ", el.get_text(" ")).strip()
                if re.search(a.links, href + " " + txt, re.I) and href not in seen:
                    seen.add(href)
                    print("  LINK", href, "|", txt[:80])
        except Exception as e:
            print("  link parse error", e)


def wb_latest(url):
    rows = capstore.wayback_cdx(url)
    if not rows:
        return None
    ts, orig = rows[-1]
    return f"https://web.archive.org/web/{ts}id_/{orig}"


def cmd_get(a):
    for u in a.urls:
        r = capstore.fetch(u, force=a.force, retry_failed=a.force)
        if a.wb and r.get("status") != 200 and "web.archive.org" not in u:
            w = wb_latest(u)
            if w:
                print("live failed:", json.dumps(meta(r)), "-> wayback", w)
                r = capstore.fetch(w)
        show(r, a)
        print("=" * 70, flush=True)


def cmd_cdx(a):
    rows = capstore.wayback_cdx(a.url, yearly=not a.all)
    for ts, o in rows:
        print(ts, f"https://web.archive.org/web/{ts}id_/{o}")
    print(len(rows), "captures")


def cmd_wb(a):
    rows = capstore.wayback_cdx(a.url, yearly=True)
    byyear = {}
    for ts, o in rows:
        byyear.setdefault(ts[:4], (ts, o))
    for y in a.years:
        if str(y) not in byyear:
            print(f"no capture in {y}; years available:", " ".join(sorted(byyear)))
            continue
        ts, o = byyear[str(y)]
        r = capstore.fetch(f"https://web.archive.org/web/{ts}id_/{o}")
        show(r, a)
        print("=" * 70, flush=True)


def nearest_headings(content, t):
    """(position-in-text, heading) for h1-h6 / strong-only blocks, located sequentially in the page text."""
    out = []
    try:
        soup = capstore.soup_of(content)
    except Exception:
        return out
    pos = 0
    for h in soup.find_all(HEADS + ["strong", "b", "dt", "th"]):
        ht = re.sub(r"\s+", " ", h.get_text(" ")).strip()
        if not ht or len(ht) > 80:
            continue
        i = t.find(ht, pos)
        if i >= 0:
            out.append((i, ht))
            pos = i
    return out


def cmd_find(a):
    r = capstore.fetch(a.url)
    print(json.dumps(meta(r)))
    if not r.get("content"):
        return
    t = capstore.page_text(r["content"])
    heads = nearest_headings(r["content"], t)
    for nm in a.names:
        hits = [m.start() for m in re.finditer(re.escape(nm), t)]
        if not hits:
            hits = [m.start() for m in re.finditer(re.escape(nm), t, flags=re.I)]
            if hits:
                print(f"[{nm}] only case-insensitive matches")
        if not hits:
            print(f"[{nm}] NOT FOUND")
            continue
        for i in hits[:4]:
            hd = [h for h in heads if h[0] <= i]
            hh = hd[-1] if hd else None
            dist = (i - hh[0]) if hh else None
            print(f"[{nm}] at {i}: ...{t[max(0, i - a.chars):i + len(nm) + a.chars]}...")
            if hh:
                print(f"      nearest heading {dist} chars before: {hh[1]!r}")


def cmd_pubs(a):
    import pubx
    r = capstore.fetch(a.url)
    print(json.dumps(meta(r)))
    if r.get("status") != 200:
        return
    titles = []
    with gzip.open(capstore.P.data("lab_papers.jsonl.gz", "cmu"), "rt") as f:
        for line in f:
            d = json.loads(line)
            if d["pi"] == a.pi and d.get("title"):
                titles.append(d["title"])
    idx = pubx.lab_index(titles)
    ents = pubx.extract(r["content"], r["url"], mode=a.mode, title_css=a.title_css)
    inw = [e for e in ents if e["year"] and 2016 <= e["year"] <= 2026]
    noy = [e for e in ents if not e["year"]]
    matched, missing = [], []
    for e in inw:
        (matched if pubx.match_lab(e["title"], e["entry"], idx) else missing).append(e)
    print(f"lab papers for PI: {len(titles)} | entries={len(ents)} in_window={len(inw)} no_year={len(noy)} "
          f"matched={len(matched)} missing={len(missing)} no_quote={sum(1 for e in missing if not e.get('quote'))}")
    hows = {}
    for e in ents:
        hows[e["title_how"]] = hows.get(e["title_how"], 0) + 1
    print("title heuristics:", hows)
    for lab, xs in (("MISSING", missing), ("MATCHED", matched), ("NO-YEAR", noy)):
        print(f"--- {lab} (first {a.show})")
        for e in xs[: a.show]:
            print(f"  [{e['year']}] {e['title'][:150]!r} | venue={str(e.get('venue'))[:60]!r} | how={e['title_how']}")


def cmd_check(a):
    env = dict(os.environ)
    cmd = [sys.executable, "-I", TOOLS + "/build.py", "--dry", "--only", a.module]
    if a.pi:
        cmd += ["--pi"] + a.pi
    p = subprocess.run(cmd, env=env, capture_output=True, text=True)
    out = p.stdout
    if len(out) > 30000:
        lines = out.splitlines()
        keep = [l for l in lines if l.startswith(("labs=", "  ", "PROBLEM")) and not l.startswith("      ")]
        out = "\n".join(keep) + "\n(per-member lines omitted: output too long; use --pi PI)"
    print(out)
    if p.returncode:
        print(p.stderr[-5000:])


def cmd_held(a):
    import names
    st = json.load(open(capstore.P.data("students.json", "cmu")))
    for pi, rows in st.items():
        for r in rows:
            for n in [r.get("name")] + list(r.get("aliases") or []):
                if n and names.match(a.name, n):
                    print(pi, "|", n, "|", r.get("roles"))


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("info")
    p.add_argument("pi")
    for name in ("get", "wb"):
        p = sp.add_parser(name)
        if name == "get":
            p.add_argument("urls", nargs="+")
            p.add_argument("--force", action="store_true")
            p.add_argument("--wb", action="store_true")
        else:
            p.add_argument("url")
            p.add_argument("years", nargs="+", type=int)
        p.add_argument("--compact", action="store_true")
        p.add_argument("--grep")
        p.add_argument("--links")
        p.add_argument("--from", dest="frm")
        p.add_argument("--head", type=int, default=6000)
        p.add_argument("--chars", type=int, default=400)
        p.add_argument("--maxhits", type=int, default=10)
    p = sp.add_parser("cdx")
    p.add_argument("url")
    p.add_argument("--all", action="store_true")
    p = sp.add_parser("find")
    p.add_argument("url")
    p.add_argument("names", nargs="+")
    p.add_argument("--chars", type=int, default=120)
    p = sp.add_parser("pubs")
    p.add_argument("pi")
    p.add_argument("url")
    p.add_argument("--mode", default="auto")
    p.add_argument("--title-css", dest="title_css")
    p.add_argument("--show", type=int, default=8)
    p = sp.add_parser("check")
    p.add_argument("module")
    p.add_argument("--pi", nargs="*")
    p = sp.add_parser("held")
    p.add_argument("name")
    a = ap.parse_args()
    {"info": cmd_info, "get": cmd_get, "cdx": cmd_cdx, "wb": cmd_wb, "find": cmd_find, "pubs": cmd_pubs,
     "check": cmd_check, "held": cmd_held}[a.cmd](a)


if __name__ == "__main__":
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)   # quiet when piped to head
    main()
