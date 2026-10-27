"""Lab-page pass CLI (EPFL + Berkeley, 2026-10-22). Run with /usr/local/anaconda3/2024.02/bin/python -I.

  lp.py lab SCHOOL KEY                 lab row (KEY = index, slug, or PI substring) + seed URLs + spec path
  lp.py disc SCHOOL KEY                what the automatic discovery pass fetched for this lab (pages, stats)
  lp.py get SCHOOL URL [--grep RX] [--chars N] [--head N] [--links RX] [--wb] [--force]
                                       fetch (cached) and print text / grep windows / matching links
  lp.py wb SCHOOL URL [--from Y] [--to Y] [--n 3] [--prefix]
                                       list Wayback captures (distinct digests); --n picks N spread across years
  lp.py people SCHOOL KEY URL [--all]  sectioned member-name candidates on a stored page, matched to students_held
  lp.py pubs SCHOOL KEY URL [--show N] [--held]
                                       publication entries on a page, held vs missing against the PI's lab papers
  lp.py check SCHOOL KEY               build this lab's spec (work/SCHOOL/<slug>.json) and print problems/summary
Workers set LPCAP_LOCAL=<their own sqlite file> so they never write the NFS store concurrently.
"""
import argparse
import json
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import lpcap  # noqa: E402
import lpdom  # noqa: E402
import lplab  # noqa: E402
import lpnames  # noqa: E402


def disc_row(school, pi):
    import glob
    for f in glob.glob(f"{TOOLS}/discover/{school}-*.jsonl"):
        for l in open(f):
            d = json.loads(l)
            if d["pi"] == pi:
                return d
    return None


def cmd_disc(a):
    row = lplab.lab(a.school, a.key)
    d = disc_row(a.school, row["pi"])
    if not d:
        print("no discovery row yet")
        return
    if d.get("error"):
        print("ERROR", d["error"])
    for p in d.get("pages", []):
        st = {k: p[k] for k in ("names", "held", "pubs", "pubs_held") if k in p}
        cu = (" via " + p["capture_url"]) if p.get("capture_url") else ""
        print(f"  {p['kind']:8s} {p.get('status')} {p['url']}{cu} {st if st else (p.get('error') or '')}")
    print("people candidates:", [(x["url"], x["text"]) for x in d.get("people", [])])
    print("pubs candidates:", [(x["url"], x["text"]) for x in d.get("pubs", [])])


def cmd_lab(a):
    row = lplab.lab(a.school, a.key)
    print(json.dumps({k: row[k] for k in row if k not in ("students_held",)}, ensure_ascii=False, indent=1))
    print("students_held (%d):" % len(row["students_held"]), "; ".join(row["students_held"]))
    print("spec:", lplab.spec_path(a.school, row))
    print("seeds:", json.dumps(lplab.seeds(a.school, row), ensure_ascii=False, indent=1))


def fetch_print(a, u):
    if a.wb:
        r = lpcap.get(a.school, u, frm=a.wbfrom, to=a.wbto)
    else:
        r = lpcap.fetch(a.school, u, force=a.force)
    meta = {k: r.get(k) for k in ("url", "final_url", "capture_url", "status", "sha256", "error", "cached")}
    print(json.dumps(meta), flush=True)
    if r.get("content") and r.get("status") == 200:
        t = lpcap.page_text(r["content"], r.get("content_type"))
        print("  [len %d]" % len(t))
        if a.grep:
            n = 0
            for m in re.finditer(a.grep, t, re.I):
                s, e = max(0, m.start() - a.chars), min(len(t), m.end() + a.chars)
                print("  ...", t[s:e], "...")
                n += 1
                if n >= a.maxhits:
                    break
            if n == 0:
                print("  (no match)")
        elif a.head:
            print(" ", t[a.offset:a.offset + a.head])
        if a.links:
            seen = set()
            for href, txt in lpcap.links(r["content"], r.get("final_url") or u):
                if (re.search(a.links, href, re.I) or re.search(a.links, txt, re.I)) and href not in seen:
                    seen.add(href)
                    print("  LINK", href, "|", txt[:100])
    print("=" * 80, flush=True)


def cmd_get(a):
    for u in a.urls:
        fetch_print(a, u)


def cmd_wb(a):
    rows = lpcap.wayback_cdx(a.school, a.url, frm=a.wbfrom, to=a.wbto, match_prefix=a.prefix)
    by_year = {}
    for ts, orig, dig in rows:
        by_year.setdefault(ts[:4], []).append((ts, orig))
    print(f"{len(rows)} distinct captures; per year:", {y: len(v) for y, v in sorted(by_year.items())})
    if a.n:
        for u in lplab.spread(rows, a.n):
            print("  PICK", u)
    if a.list:
        for ts, orig, dig in rows:
            print("  ", ts, orig)


def cmd_people(a):
    row = lplab.lab(a.school, a.key)
    r = lplab.stored(a.school, a.url)
    if not r:
        print("not stored (fetch it with get first):", a.url)
        return
    cands, ls = lpdom.member_candidates(r["content"], r.get("final_url") or a.url)
    held = row["students_held"]
    cur = None
    for path, name, rest, nxt, i in cands:
        head = " › ".join(path)
        if head != cur:
            print(f"[§ {head}]")
            cur = head
        h, how = lpnames.match_held(name, held)
        fz = lpnames.fuzzy_held(name, held) if not h else []
        tag = f"HELD({how}: {h})" if h else ("AMBIG" if how == "ambiguous" else ("FUZZY?" + "|".join(fz) if fz else "new"))
        if a.pi and lpnames.match_one(name, row["pi"]):
            tag = "PI"
        extra = rest or ""
        if a.all and nxt:
            extra += "  ⟶ " + nxt[:90]
        print(f"  {name} | {extra[:110]} | {tag}")
    print(f"-- {len(cands)} candidates; capture_url={r.get('capture_url')} sha={r['sha256'][:12]}")


def cmd_pubs(a):
    import lppubs
    row = lplab.lab(a.school, a.key)
    r = lplab.stored(a.school, a.url)
    if not r:
        print("not stored (fetch it with get first):", a.url)
        return
    res = lppubs.parse(a.school, row, r, a.url, mode=a.mode)
    ins = [e for e in res if e["in_window"]]
    miss = [e for e in ins if not e["held"]]
    print(f"entries {len(res)}; 2016-2026 {len(ins)}; held {len(ins)-len(miss)}; missing {len(miss)}; "
          f"no-year {sum(1 for e in res if e['year'] is None)}")
    show = miss if not a.held else ins
    for e in show[:a.show]:
        print(f"  {'HELD ' if e['held'] else 'MISS '}{e['year']} | {e['title'][:110]} | {(e['venue'] or '')[:40]} | "
              f"{len(e['links'])} links")
    if a.raw:
        for e in res[:a.raw]:
            print("  RAW", e["year"], "|", e["text"][:200])


def cmd_check(a):
    import lpbuild
    row = lplab.lab(a.school, a.key)
    out, pubs, problems = lpbuild.build_lab(a.school, row, verbose=True)
    print(json.dumps({"pi": out["pi"], "lab_site": out["lab_site"], "people_page": out["people_page"],
                      "students": len(out["students"]),
                      "new": sum(1 for s in out["students"] if not s["already_held"]),
                      "held_variants": [(s["name"], s.get("held_name")) for s in out["students"]
                                        if s["already_held"] and s.get("match") not in ("exact",)],
                      "missing_pubs": len(pubs)}, ensure_ascii=False, indent=1))
    if a.rows:
        for s in out["students"]:
            tag = (f"HELD[{s.get('match')}:{s.get('held_name')}]" if s["already_held"] else
                   ("NEW?" + "|".join(s["possible_held"]) if s.get("possible_held") else "NEW"))
            y = s.get("years")
            print(f"  {s['name']} | {s['role']}{' alum' if s['alumni'] else ''} | {y} | {tag} | "
                  f"{(s.get('section') or '')[-50:]} | q={len(s['quote'])}{' +%d' % len(s['other_sources']) if s.get('other_sources') else ''}")
    if a.pubs:
        for p in pubs[:a.pubs]:
            print(f"  PUB {p['year']} | {p['title'][:100]} | {(p['venue'] or '')[:40]}")
    for p in problems:
        print("PROBLEM", p)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("lab"); p.add_argument("school"); p.add_argument("key"); p.set_defaults(f=cmd_lab)
    p = sub.add_parser("disc"); p.add_argument("school"); p.add_argument("key"); p.set_defaults(f=cmd_disc)
    p = sub.add_parser("get"); p.add_argument("school"); p.add_argument("urls", nargs="+")
    p.add_argument("--grep"); p.add_argument("--chars", type=int, default=300); p.add_argument("--head", type=int, default=1500)
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--links"); p.add_argument("--wb", action="store_true"); p.add_argument("--force", action="store_true")
    p.add_argument("--wbfrom"); p.add_argument("--wbto"); p.add_argument("--maxhits", type=int, default=15)
    p.set_defaults(f=cmd_get)
    p = sub.add_parser("wb"); p.add_argument("school"); p.add_argument("url")
    p.add_argument("--from", dest="wbfrom"); p.add_argument("--to", dest="wbto"); p.add_argument("--n", type=int, default=0)
    p.add_argument("--prefix", action="store_true"); p.add_argument("--list", action="store_true"); p.set_defaults(f=cmd_wb)
    p = sub.add_parser("people"); p.add_argument("school"); p.add_argument("key"); p.add_argument("url")
    p.add_argument("--all", action="store_true"); p.add_argument("--pi", action="store_true", default=True)
    p.set_defaults(f=cmd_people)
    p = sub.add_parser("pubs"); p.add_argument("school"); p.add_argument("key"); p.add_argument("url")
    p.add_argument("--show", type=int, default=25); p.add_argument("--held", action="store_true")
    p.add_argument("--raw", type=int, default=0); p.add_argument("--mode", default="auto")
    p.set_defaults(f=cmd_pubs)
    p = sub.add_parser("check"); p.add_argument("school"); p.add_argument("key")
    p.add_argument("--rows", action="store_true"); p.add_argument("--pubs", type=int, default=0); p.set_defaults(f=cmd_check)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
