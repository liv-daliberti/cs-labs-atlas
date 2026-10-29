"""Copy every row of a worker-local capture DB into hierarchy/<school>/labpage-captures.sqlite (single writer).
Rows already present (same url, capture_url, fetched_at, sha256) are skipped, so a rerun is harmless.
usage: merge.py SCHOOL LOCAL_DB [LOCAL_DB ...]
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
for k in list(os.environ):
    if k.startswith("LPCAP_LOCAL"):
        os.environ.pop(k)
import lpcap  # noqa: E402

school = sys.argv[1]
dst = lpcap.connect(school, lpcap.DBS[school])
cols = "url,final_url,capture_url,fetched_at,status,sha256,content_type,content,error,copied_from"
for local in sys.argv[2:]:
    if not os.path.exists(local):
        print("missing", local)
        continue
    src = sqlite3.connect(f"file:{local}?mode=ro", uri=True)
    n = k = 0
    for row in src.execute(f"SELECT {cols} FROM captures ORDER BY id"):
        u, f, c, t, st, sha = row[:6]
        if dst.execute("SELECT 1 FROM captures WHERE url=? AND capture_url IS ? AND fetched_at=? AND sha256 IS ?",
                       (u, c, t, sha)).fetchone():
            k += 1
            continue
        dst.execute(f"INSERT INTO captures({cols}) VALUES (?,?,?,?,?,?,?,?,?,?)", row)
        n += 1
    dst.commit()
    src.close()
    print(f"merged {n} rows ({k} already present) from {local} into {lpcap.DBS[school]}")
