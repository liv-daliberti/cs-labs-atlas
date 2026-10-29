"""Automatic first specs from the discovery pass (used because no worker agents could be started).

  autospec.py wayback SCHOOL SHARD NSHARDS   fetch up to 3 Wayback captures (2016-2025, spread over the years) of each
                                             lab's main people page into the worker-local DB (LPCAP_LOCAL_<SCHOOL>)
  autospec.py write SCHOOL [--force]         write work/<school>/<slug>.json for labs without a reviewed spec
A spec written here carries "auto": true; once reviewed by hand it gets "auto": false and is never overwritten.
Main people page: the discovered non-profile page with the most students_held matches (ties: more name candidates,
discovered as a people link). Extra people pages: others with >= 2 held matches. Publications page: the discovered
page with the most held lab-paper titles (>= 3).
"""
import glob
import json
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import lpcap  # noqa: E402
import lplab  # noqa: E402

PUBLIKE = re.compile(r"/(publications?|papers|pubs|bibliography|bib)(/|\.s?html?|\.php|$)|\.bib$|\.pdf$", re.I)


def disc(school):
    out = {}
    for f in glob.glob(f"{TOOLS}/discover/{school}-*.jsonl"):
        for l in open(f):
            d = json.loads(l)
            out[d["pi"]] = d
    return out


def people_pages(d):
    ps = [p for p in d.get("pages", []) if p.get("status") == 200 and p["kind"] not in ("profile",)
          and not PUBLIKE.search(p["url"]) and p.get("names", 0) > 0]
    scored = []
    for p in ps:
        held, names = p.get("held", 0), p.get("names", 0)
        if held < 1 and not (p["kind"] == "people?" and names >= 3):
            continue
        scored.append((held * 3 + min(names, 60) / 10 + (5 if p["kind"] == "people?" else 0), p))
    scored.sort(key=lambda x: -x[0])
    chosen, seen = [], set()
    for sc, p in scored:
        key = p.get("final_url") or p["url"]
        if key in seen:
            continue
        if chosen and p.get("held", 0) < 2:
            continue
        seen.add(key)
        chosen.append(p)
        if len(chosen) >= 3:
            break
    return chosen


def src_url(p):
    return p.get("capture_url") or p["url"]


def live_url(p):
    if p.get("capture_url"):
        m = lpcap.WAYBACK_RX.match(p["capture_url"])
        return re.sub(r":80/", "/", m.group(2)) if m else p["url"]
    return p.get("final_url") or p["url"]


def cmd_wayback(school, shard, n):
    D = disc(school)
    for i, row in enumerate(lplab.rows(school)):
        if i % n != shard:
            continue
        d = D.get(row["pi"])
        if not d:
            continue
        pp = people_pages(d)
        if not pp:
            print(i, row["pi"], "no people page", flush=True)
            continue
        u = live_url(pp[0])
        rows = lpcap.wayback_cdx(school, u, frm="2016", to="2025")
        picks = lplab.spread(rows, 3)
        got = 0
        for w in picks:
            if w == pp[0].get("capture_url"):
                continue
            r = lpcap.fetch(school, w, check_robots=False)
            got += r.get("status") == 200
        print(i, row["pi"], u, len(rows), "captures;", got, "fetched", flush=True)
    print("DONE", flush=True)


def manual(school):
    p = f"{TOOLS}/manual_pages.json"
    return (json.load(open(p)).get(school) or {}) if os.path.exists(p) else {}


def cmd_write(school, force=False, wb=True, only=None):
    D = disc(school)
    M = manual(school)
    n_w = 0
    for i, row in enumerate(lplab.rows(school)):
        if only is not None and i not in only:
            continue
        path = lplab.spec_path(school, row)
        if os.path.exists(path):
            old = json.load(open(path))
            if not old.get("auto") and not force:
                continue
        d = D.get(row["pi"]) or {}
        man = M.get(row["pi"]) or {}
        pp = people_pages(d)
        if man.get("people") is not None:
            pp = []
            for u in man["people"]:
                r = lpcap.get(school, u)
                if r.get("status") == 200:
                    pp.append({"url": u, "capture_url": r.get("capture_url"), "final_url": r.get("final_url")})
        sources = []
        before16 = None
        for p in pp:
            sources.append({"url": src_url(p), "auto": True})
        if pp and wb:
            u = live_url(pp[0])
            cdx = lpcap.wayback_cdx(school, u, frm="2016", to="2025")  # cached by the wayback phase
            b16 = None
            for w in lplab.spread(cdx, 3):
                if w == pp[0].get("capture_url"):
                    continue
                ok = lplab.stored(school, w) is not None
                if not ok and man.get("people") is not None:
                    ok = lpcap.fetch(school, w, check_robots=False).get("status") == 200
                if ok:
                    sources.append({"url": w, "auto": True})
                    if int(re.search(r"/web/(\d{4})", w).group(1)) <= 2016 and b16 is None:
                        b16 = w
            if b16 and not man.get("before_2016"):
                before16 = [{"url": b16, "sections": ["alumn|former|past|graduated"]}]
            else:
                before16 = None
        if school == "epfl":
            for p in d.get("pages", []):
                if p["kind"] == "profile" and p.get("status") == 200 and "people.epfl.ch" in p["url"]:
                    sources.append({"url": src_url(p), "kind": "epfl_profile"})
                    break
        pubs = sorted([p for p in d.get("pages", []) if p.get("status") == 200 and p["kind"] != "profile"
                       and p.get("pubs_held", 0) >= 3], key=lambda p: -p.get("pubs_held", 0))
        pubs_pages = [src_url(pubs[0])] if pubs else []
        if man.get("pubs") is not None:
            pubs_pages = []
            for u in man["pubs"]:
                r = lpcap.get(school, u)
                if r.get("status") == 200:
                    pubs_pages.append(r.get("capture_url") or u)
        homes = d.get("homes") or []
        if man.get("lab_site"):
            homes = [man["lab_site"]]
        spec = {"pi": row["pi"], "auto": True,
                "lab_site": homes[0] if homes else None,
                "people_page": live_url(pp[0]) if pp else None,
                "sources": sources, "pubs_pages": pubs_pages,
                "notes": man.get("notes") or "automatic spec from the discovery pass"}
        if man.get("no_pubs"):
            spec["pubs_pages"] = []
        if before16:
            spec["before_2016"] = before16
        for src in spec["sources"]:
            if src.get("auto"):
                for k in ("drop", "skip", "only", "role", "keep", "alumni_sections", "current_sections", "years",
                          "alumni", "section_role", "undated_is_alumni", "only_names", "before_2016_src"):
                    if man.get(k):
                        src[k] = man[k]
        for k in ("sources_extra", "members", "excluded", "held_as", "merge", "before_2016"):
            if man.get(k):
                if k == "sources_extra":
                    spec["sources"] += man[k]
                else:
                    spec[k] = man[k]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        json.dump(spec, open(path, "w"), ensure_ascii=False, indent=1)
        n_w += 1
    print(f"{school}: wrote {n_w} auto specs")


if __name__ == "__main__":
    if sys.argv[1] == "wayback":
        cmd_wayback(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
    elif sys.argv[1] == "write":
        only = None
        if "--only" in sys.argv:
            only = {int(x) for x in sys.argv[sys.argv.index("--only") + 1].split(",")}
        cmd_write(sys.argv[2], "--force" in sys.argv, wb="--no-wb" not in sys.argv, only=only)
