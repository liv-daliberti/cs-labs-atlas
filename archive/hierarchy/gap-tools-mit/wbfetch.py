"""Fetch Wayback id_ capture URLs into the MIT gap store with the store's convention (url = original, capture_url = the
Wayback id_ URL), then print a text window. (New-PI gap research 2026-10-22; look.py stores a pasted Wayback URL as a live url.)
usage: wbfetch.py [--grep RX] [--chars N] [--head N] WAYBACK_ID_URL...
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import argparse, json, re, sys
sys.path.insert(0, str(P.HIERARCHY / 'gap-tools-mit'))
import capstore  # noqa: E402

RX = re.compile(r"^https?://web\.archive\.org/web/(\d{4,14})id_/(.+)$")
ap = argparse.ArgumentParser()
ap.add_argument("--grep"); ap.add_argument("--chars", type=int, default=600); ap.add_argument("--head", type=int, default=0)
ap.add_argument("urls", nargs="+")
a = ap.parse_args()
for u in a.urls:
    m = RX.match(u)
    if not m:
        print("not a Wayback id_ URL:", u); continue
    r = capstore.fetch(m.group(2), capture_url=u, check_robots=False)
    t = capstore.page_text(r["content"]) if r.get("content") else ""
    print(json.dumps({k: r.get(k) for k in ("url", "capture_url", "status", "sha256", "error", "cached")}), "len", len(t))
    if a.head:
        print(t[:a.head])
    if a.grep and t:
        n = 0
        for mm in re.finditer(a.grep, t, flags=re.I):
            s = max(0, mm.start() - a.chars // 2)
            print("  >>", t[s:mm.end() + a.chars // 2]); n += 1
            if n >= 8: break
    print("=" * 60, flush=True)
