"""Merge every lab-page capture part into hierarchy/cmu/labpage-captures.sqlite (single writer).

Sources: labpage-parts/*.sqlite (share) plus any host-local scratch parts given as arguments.
Rows are copied unchanged (url, final_url, capture_url, fetched_at, status, sha256, content_type, content, error);
exact duplicates (same url/final_url/capture_url/fetched_at/sha256/status/error) are skipped.
usage: python -I merge.py [extra.sqlite ...]
"""
import glob
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capstore  # noqa: E402

COLS = capstore.COLS
srcs = sorted(glob.glob(capstore.PARTS + "/*.sqlite")) + [p for p in sys.argv[1:] if os.path.exists(p)]
dst = capstore.connect(capstore.MAIN_DB)
seen = set(dst.execute("SELECT url,ifnull(final_url,''),ifnull(capture_url,''),fetched_at,ifnull(sha256,''),"
                       "ifnull(status,-1),ifnull(error,'') FROM captures").fetchall())
total = 0
for s in srcs:
    con = sqlite3.connect("file:" + s + "?mode=ro", uri=True)
    n = 0
    for row in con.execute(f"SELECT {COLS} FROM captures"):
        k = (row[0], row[1] or "", row[2] or "", row[3], row[5] or "", row[4] if row[4] is not None else -1, row[8] or "")
        if k in seen:
            continue
        seen.add(k)
        dst.execute(f"INSERT INTO captures({COLS}) VALUES (?,?,?,?,?,?,?,?,?)", row)
        n += 1
    con.close()
    dst.commit()
    total += n
    print(f"{n:6d} new rows from {s}", flush=True)
print("total new", total, "rows now", dst.execute("SELECT count(*) FROM captures").fetchone()[0])
dst.close()
