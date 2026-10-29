"""Print text windows of the latest 200 capture of URL (live url or Wayback capture_url) around REGEX.

usage: insp.py URL [REGEX] [--w WIDTH] [--max N] [--from STR] [--len N]
  --from STR  print --len chars starting at the first occurrence of STR
"""
import argparse
import re
import sys
import zlib

sys.path.insert(0, "/n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/gap-tools-cmu")
import capstore  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("url")
ap.add_argument("rx", nargs="?")
ap.add_argument("--w", type=int, default=300)
ap.add_argument("--max", type=int, default=8)
ap.add_argument("--frm", default=None)
ap.add_argument("--len", type=int, default=3000)
ap.add_argument("--raw", action="store_true")
a = ap.parse_args()
con = capstore.connect()
row = con.execute("SELECT content, sha256, url, capture_url FROM captures WHERE (url=? OR capture_url=? OR final_url=?) "
                  "AND content IS NOT NULL AND status=200 ORDER BY id DESC LIMIT 1", (a.url, a.url, a.url)).fetchone()
if not row:
    print("NO CAPTURE", a.url)
    sys.exit()
c = zlib.decompress(row[0])
t = capstore.raw_text(c) if a.raw else capstore.page_text(c)
print("##", row[2], row[3], row[1][:16], "len", len(t))
if a.frm:
    i = t.find(a.frm)
    print(t[i:i + a.len] if i >= 0 else "(from-string not found)")
elif a.rx:
    n = 0
    for m in re.finditer(a.rx, t, flags=re.I):
        print("  >>", t[max(0, m.start() - a.w):m.end() + a.w])
        n += 1
        if n >= a.max:
            break
    if n == 0:
        print("  (no match)")
else:
    print(t[:a.len])
