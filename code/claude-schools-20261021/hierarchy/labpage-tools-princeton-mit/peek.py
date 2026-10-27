"""Show a stored people page as heading-delimited sections with the person-like names found in each, marked against
the lab's students_held (names.match). A reading aid for writing decisions; it decides nothing.

usage: peek.py SCHOOL "PI" SRC [--raw N]   (SRC = live URL, Wayback id_ URL or sha256 of a stored capture)
  --raw N   also print the first N chars of the page's visible text
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lpcap  # noqa: E402
import lpev  # noqa: E402
import names  # noqa: E402

STOP = re.compile(r"^(people|members?|team|students?|phd|ph\.d\.?|alumni|former|current|research|publications?|lab|group|"
                  r"contact|home|news|university|department|professor|postdoc(toral)?|graduate|undergraduate|masters?|"
                  r"visitors?|staff|faculty|fellows?|director|principal investigator|pi|join|join us|about|teaching|"
                  r"collaborators?|affiliates?|scientists?|engineers?|interns?|meng|ms|bs|sb|sm|alumni & former members|"
                  r"computer science|electrical engineering|mit|princeton|csail|eecs|google scholar|twitter|github|"
                  r"linkedin|website|email|cv|bio|more|read more|learn more|back to top|menu|search|skip to main content|"
                  r"show more|projects?|software|code|data|events|talks|courses?)$", re.I)
PART = {"de", "van", "von", "da", "del", "della", "la", "le", "di", "bin", "al", "el", "dos", "das", "du", "ter", "der", "den", "y"}


def namey(t):
    t = t.strip(" ,;:|·•-–—()")
    if not (3 <= len(t) <= 60) or re.search(r"\d|@|http|[{}<>=]", t) or STOP.match(t):
        return False
    toks = t.split()
    if not (1 <= len(toks) <= 6):
        return False
    caps = 0
    for w in toks:
        w2 = w.strip(".,()'’\"")
        if not w2:
            continue
        if w2.lower() in PART or re.match(r"^[a-z]{1,3}['’][A-Z]", w2):
            continue
        if not (w2[0].isupper() or (w2[0].isalpha() and not w2[0].isascii())):
            return False
        caps += 1
    return caps >= 1 and (len(toks) >= 2 or len(t) >= 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("school")
    ap.add_argument("pi")
    ap.add_argument("src")
    ap.add_argument("--raw", type=int, default=0)
    a = ap.parse_args()
    labs = {l["pi"]: l for l in json.load(open(f"{lpcap.ROOT}/{a.school}/labpage-input.json"))}
    held = labs[a.pi]["students_held"] if a.pi in labs else []
    r, views = lpev.cap(a.school, a.src)
    print({k: r.get(k) for k in ("url", "capture_url", "sha256", "fetched_at")})
    kind = lpcap.kind_of(r["content"], r.get("content_type"))
    if kind != "html":
        t = views.get("pdf") or views.get("raw") or ""
        print(f"[{kind}] {len(t)} chars")
        print(t[: max(a.raw, 4000)])
        return
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(lpcap.decode(r["content"]), "lxml")
    for x in soup(["script", "style", "noscript", "template"]):
        x.decompose()
    sections, cur = [], ["(top)", []]
    seen = set()
    for el in (soup.body or soup).descendants:
        if not getattr(el, "name", None):
            continue
        if re.fullmatch(r"h[1-6]", el.name):
            ht = lpcap.collapse(el.get_text(" "))
            if ht and not namey(ht):
                sections.append(cur)
                cur = [ht[:80], []]
                continue
        if el.name in ("a", "strong", "b", "h3", "h4", "h5", "h6", "li", "td", "span", "p", "div", "figcaption", "dt", "dd", "em"):
            if el.find(["div", "p", "li", "td", "table", "ul"]) is not None and el.name in ("div", "li", "td"):
                continue
            t = lpcap.collapse(el.get_text(" "))
            cand = re.split(r"\s[,|·•–—]\s|\s\(|,\s(?=[A-Z])", t)[0] if t else ""
            for c in {t, cand}:
                if c and namey(c) and c not in seen:
                    seen.add(c)
                    cur[1].append(c)
    sections.append(cur)
    for head, ns in sections:
        if not ns:
            continue
        print(f"## {head}")
        for n in ns:
            h, k = names.match(n, held)
            print(f"   {n}" + (f"    [HELD {k}: {h}]" if h else ""))
    unmatched_held = [h for h in held if not any(names.match(n, [h])[0] for _, ns in sections for n in ns)]
    print(f"held not seen on this page ({len(unmatched_held)}/{len(held)}):", unmatched_held[:40])
    if a.raw:
        print((views.get("html") or "")[: a.raw])


if __name__ == "__main__":
    main()
