"""Fetch Wayback history for every plan people page: for each URL in P[pi]['wb'] (plan_<school>.py), CDX (2016-2026,
trailing-slash variant tried) and up to N id_ captures spread over the years (earliest, latest, evenly between),
skipping years before the plan's wb_from. Writes T/wb_<school>.part<i>.json {url: [capture_url, ...]} (one file per shard; lpauto reads all wb_<school>*.json) (only captures fetched
with status 200). Resumable: URLs already in the JSON are skipped unless --redo.
usage: LPCAP_LOCAL=... wbbatch.py SCHOOL [--n 3] [--only PI ...] [--redo]
"""
import argparse
import importlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lpcap  # noqa: E402

T = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("school")
ap.add_argument("--n", type=int, default=3)
ap.add_argument("--only", nargs="*")
ap.add_argument("--redo", action="store_true")
ap.add_argument("--shard", default="0/1", help="i/n: this worker takes every n-th plan URL starting at i")
a = ap.parse_args()
si, sn = map(int, a.shard.split("/"))
P = importlib.import_module(f"plan_{a.school}").P
import glob
path = f"{T}/wb_{a.school}.part{si}.json"
done = {}
for p_ in glob.glob(f"{T}/wb_{a.school}*.json"):
    done.update(json.load(open(p_)))
out = json.load(open(path)) if os.path.exists(path) else {}
k = -1
for pi, plan in P.items():
    if a.only and pi not in a.only:
        continue
    for u in plan.get("wb", []):
        k += 1
        if k % sn != si:
            continue
        if u in done and not a.redo:
            continue
        import lpauto
        frm = lpauto.wb_from(a.school, pi, plan)
        rows = []
        for v in ([u, u.rstrip("/")] if u.endswith("/") else [u, u + "/"]):
            rows = lpcap.wayback_cdx(a.school, v, frm=str(frm), to=str(plan.get("wb_to", 2026)))
            if rows:
                break
        rows = [r for r in rows if r[0][:8] < "20261020"]
        by_year = {}
        for r in rows:
            by_year.setdefault(r[0][:4], []).append(r)
        years = sorted(by_year)
        if len(rows) <= a.n:
            pick = list(rows)
        elif len(years) < a.n:
            idx = sorted({round(i * (len(rows) - 1) / (a.n - 1)) for i in range(a.n)})
            pick = [rows[i] for i in idx]
        else:
            idx = sorted({round(i * (len(years) - 1) / (a.n - 1)) for i in range(a.n)})
            pick = [by_year[years[i]][-1] for i in idx]
        caps = []
        for ts, orig, dig in pick:
            w = lpcap.wayback_id(ts, orig)
            r = lpcap.fetch(a.school, w, check_robots=False)
            if r.get("status") == 200 and r.get("content"):
                caps.append(w)
        out[u] = caps
        json.dump(out, open(path + ".tmp", "w"), indent=1)
        os.replace(path + ".tmp", path)
        print(f"{pi}: {u} -> {len(rows)} captures, fetched {len(caps)}", flush=True)
