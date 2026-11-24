"""Copy every row of a worker-local capture DB (TCAP_LOCAL) into the school's thesis-captures.sqlite.
Run only when no other process is writing the school's store (single writer on NFS). Rows already present
(same url, capture_url, fetched_at, sha256) are skipped, so a rerun is harmless.
usage: merge.py SCHOOL LOCAL_DB
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.pop("TCAP_LOCAL", None)
import tcap  # noqa: E402

school, local = sys.argv[1], sys.argv[2]
src = sqlite3.connect(f"file:{local}?mode=ro", uri=True)
dst = tcap.connect(school, tcap.DBS[school])
cols = "url,final_url,capture_url,fetched_at,status,sha256,content_type,content,error,copied_from"
n = k = 0
for row in src.execute(f"SELECT {cols} FROM captures ORDER BY id"):
    u, f, c, t, st, sha = row[:6]
    if dst.execute("SELECT 1 FROM captures WHERE url=? AND capture_url IS ? AND fetched_at=? AND sha256 IS ?", (u, c, t, sha)).fetchone():
        k += 1
        continue
    dst.execute(f"INSERT INTO captures({cols}) VALUES (?,?,?,?,?,?,?,?,?,?)", row)
    n += 1
dst.commit()
print(f"merged {n} rows ({k} already present) from {local} into {tcap.DBS[school]}")
