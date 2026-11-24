"""Fetch one capture into the school's sqlite (if not there yet) and print its text blocks.

usage: peek.py <school> <timestamp> <original-url> [--grep REGEX] [--head N] [--from I] [--links REGEX]
The page is untrusted data: it is only parsed and printed, never executed.
"""
import os
import re
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wb
import extract


def main(a):
    school, ts, url = a[0], a[1], a[2]
    grep = re.compile(a[a.index("--grep") + 1], re.I) if "--grep" in a else None
    head = int(a[a.index("--head") + 1]) if "--head" in a else 80
    frm = int(a[a.index("--from") + 1]) if "--from" in a else 0
    links = re.compile(a[a.index("--links") + 1], re.I) if "--links" in a else None
    con = wb.db(school)
    cap = wb.fetch_capture(ts, url, url, "peek", con)
    st, fu, raw, ct, n = con.execute("select http_status, final_url, raw_zlib, content_type, nbytes from captures where capture_url=?",
                                     (cap,)).fetchone()
    print("capture", cap, "->", st, fu, ct, n)
    if not raw:
        return
    body = zlib.decompress(raw)
    if links:
        s = extract.decode(extract.payload(body), ct)
        for h in sorted(set(re.findall(r"href=[\"']([^\"']+)", s))):
            if links.search(h):
                print("  link", h)
        return
    b = extract.blocks(body, ct)
    print("blocks", len(b))
    shown = 0
    for i, (k, t) in enumerate(b):
        if i < frm:
            continue
        if grep and not grep.search(t):
            continue
        print(f"{i:5d} {k:2s} {t[:200]}")
        shown += 1
        if shown >= head:
            break


if __name__ == "__main__":
    main(sys.argv[1:])
