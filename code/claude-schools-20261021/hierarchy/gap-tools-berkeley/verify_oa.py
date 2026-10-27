"""Check an OpenAlex author's 2016+ works against a stored publication list (PI homepage / CV / lab page).

usage: verify_oa.py AUTHOR_ID PAGE_URL SURNAME [--from 2016] [--minlen 20]
Prints each 2016+ work whose title appears (normalised) in the page text, with a suggested exact quote:
the page-text span covering the title plus the nearest occurrence of SURNAME (within 400 chars).
"""
import argparse
import re
import sys
import zlib

sys.path.insert(0, "/n/fs/similarity/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/gap-tools-berkeley")
import capstore  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("author")
ap.add_argument("page")
ap.add_argument("surname")
ap.add_argument("--from", dest="frm", type=int, default=2016)
ap.add_argument("--minlen", type=int, default=20)
ap.add_argument("--show", type=int, default=12)
a = ap.parse_args()


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^0-9a-z]+", " ", s.lower())).strip()


works = []
cursor = "*"
while cursor:
    row, j = capstore.openalex("works", {"filter": f"author.id:{a.author},from_publication_date:{a.frm}-01-01",
                                         "per-page": 200, "cursor": cursor,
                                         "select": "id,title,publication_year,authorships"})
    if not j:
        break
    works += j.get("results", [])
    cursor = (j.get("meta") or {}).get("next_cursor")
    if not j.get("results"):
        break
r = capstore.find_capture(a.page)
if not r:
    sys.exit("no capture of page")
text = capstore.page_text(r[0])
ntext = norm(text)
print(f"author {a.author}: {len(works)} works >= {a.frm}; page sha {r[1][:16]} len {len(text)}")
seen, hits = set(), 0
for w in works:
    t = w.get("title") or ""
    nt = norm(t)
    if len(nt) < a.minlen or nt in seen:
        continue
    seen.add(nt)
    if nt in ntext:
        hits += 1
        words = [re.escape(x) for x in re.findall(r"[0-9A-Za-z]+", t)]
        m = re.search(r"\W*".join(words), text, flags=re.I)
        q = None
        if m:
            best = None
            for sm in re.finditer(re.escape(a.surname), text):
                d = min(abs(sm.start() - m.start()), abs(sm.end() - m.end()))
                if d <= 400 and (best is None or d < best[0]):
                    best = (d, sm.start(), sm.end())
            if best:
                s, e = min(best[1], m.start()), max(best[2], m.end())
                q = text[s:e]
        if hits <= a.show:
            print(f"  MATCH {w['publication_year']} {w['id'].rsplit('/',1)[-1]} | {t[:90]}")
            print(f"     quote: {q!r}" if q else "     (no surname within 400 chars)")
print("matches:", hits)
