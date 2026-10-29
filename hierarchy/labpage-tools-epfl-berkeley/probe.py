"""Compact probe of candidate pages for labs the discovery pass left without a people page.

usage: probe.py SCHOOL URL [URL ...] [--key KEY]
For each URL (fetched, cached; Wayback fallback when the live fetch fails): status, people/pubs-like links (any host,
anchor text or path), and short grep windows around student/postdoc/member headings; with --key, the member-name
candidate count and held matches for that lab.
"""
import re
import sys

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import lpcap  # noqa: E402
import lpdom  # noqa: E402
import lplab  # noqa: E402
import lpnames  # noqa: E402

LINK_RX = re.compile(r"people|member|team|student|alumni|group|lab\b|advisee|postdoc|publication|papers|pubs|bib", re.I)
GREP_RX = re.compile(r"(ph\.?\s?d\.? students|graduate students|current students|students|postdocs?|post-docs?|"
                     r"alumni|lab members|group members|advisees)", re.I)

args = [a for a in sys.argv[1:] if not a.startswith("--")]
key = None
if "--key" in sys.argv:
    key = sys.argv[sys.argv.index("--key") + 1]
    args = [a for a in args if a != key]
school, urls = args[0], args[1:]
row = lplab.lab(school, key) if key else None
for u in urls:
    r = lpcap.get(school, u)
    print(f"## {u} -> {r.get('status')} {r.get('error') or ''} {('via ' + r['capture_url']) if r.get('capture_url') else ''}")
    if r.get("status") != 200 or not r.get("content"):
        continue
    base = u if r.get("capture_url") else (r.get("final_url") or u)
    seen = set()
    out = []
    for h, t in lpcap.links(r["content"], base):
        m = lpcap.WAYBACK_RX.match(h)
        if m:
            h = m.group(2)
        if (LINK_RX.search(t or "") or LINK_RX.search(h.split("?")[0][-40:])) and h not in seen and \
                not re.search(r"\.(pdf|jpg|png|gif)$", h, re.I) and len(t) < 60:
            seen.add(h)
            out.append(f"{t[:30]}={h}")
    print("  links:", " | ".join(out[:25]))
    t = lpcap.page_text(r["content"], r.get("content_type"))
    hits = 0
    for m in GREP_RX.finditer(t):
        print("  ..", t[max(0, m.start() - 60):m.end() + 160].replace("\n", " "))
        hits += 1
        if hits >= 4:
            break
    if row:
        cands, _ = lpdom.member_candidates(r["content"], base)
        held = sum(1 for c in cands if lpnames.match_held(c[1], row["students_held"])[0])
        print(f"  candidates {len(cands)} held {held}")
