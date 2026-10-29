"""Fetch URLs into the gap capture DB and print text windows.

usage: f.py [--grep RX] [--chars N] [--force] [--wb] [--head N] [--file F] URL...
  --wb    when the live fetch is not 200 (or robots-disallowed), try the newest Wayback id_ capture
  --links RX  print hrefs whose URL or anchor text matches RX
"""
import argparse
import json
import re
import sys
from collections import defaultdict, deque
from urllib.parse import urlsplit, urljoin

sys.path.insert(0, "/n/fs/resemble/cs-atlas/work/hierarchy/gap-tools-cmu")
import capstore  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--file")
ap.add_argument("--grep", default=None)
ap.add_argument("--chars", type=int, default=600)
ap.add_argument("--head", type=int, default=1500)
ap.add_argument("--force", action="store_true")
ap.add_argument("--wb", action="store_true")
ap.add_argument("--links", default=None)
ap.add_argument("--maxhits", type=int, default=8)
ap.add_argument("urls", nargs="*")
a = ap.parse_args()
urls = list(a.urls)
if a.file:
    urls += [l.strip() for l in open(a.file) if l.strip() and not l.startswith("#")]
byhost = defaultdict(deque)
for u in urls:
    byhost[urlsplit(u).netloc].append(u)
order = []
while any(byhost.values()):
    for h in list(byhost):
        if byhost[h]:
            order.append(byhost[h].popleft())


def wb_latest(url):
    rows = capstore.wayback_cdx(url)
    if not rows:
        return None
    ts, orig = rows[-1]
    return f"https://web.archive.org/web/{ts}id_/{orig}"


for u in order:
    r = capstore.fetch(u, force=a.force)
    if a.wb and r.get("status") != 200 and "web.archive.org" not in u:
        w = wb_latest(u)
        if w:
            r = capstore.fetch(w)
    meta = {k: r.get(k) for k in ("url", "final_url", "capture_url", "status", "sha256", "error", "cached")}
    print(json.dumps(meta))
    if r.get("content"):
        t = capstore.page_text(r["content"])
        print("  [len %d]" % len(t))
        if a.grep:
            n = 0
            for m in re.finditer(a.grep, t, flags=re.I):
                s = max(0, m.start() - a.chars // 2)
                print("  >>" + t[s:m.end() + a.chars // 2])
                n += 1
                if n >= a.maxhits:
                    break
            if n == 0:
                print("  (no grep match) head: " + t[:400])
        else:
            print(t[: a.head])
        if a.links:
            from bs4 import BeautifulSoup
            try:
                soup = BeautifulSoup(capstore._decode(r["content"]), "lxml")
                seen = set()
                for el in soup.find_all("a", href=True):
                    href = urljoin(r.get("final_url") or u, el["href"])
                    txt = re.sub(r"\s+", " ", el.get_text(" ")).strip()
                    if re.search(a.links, href + " " + txt, re.I) and href not in seen:
                        seen.add(href)
                        print("  LINK", href, "|", txt[:80])
            except Exception as e:
                print("  link parse error", e)
    print("=" * 60, flush=True)
