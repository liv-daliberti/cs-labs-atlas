"""Single-writer merge of the per-worker local capture DBs into hierarchy/berkeley/gap-captures.sqlite.

Copies every worker row not already present in the main DB (same url, capture_url, fetched_at, sha256),
preserving all columns (url, final_url, capture_url, fetched_at, status, sha256, content_type, zlib content, error).
usage: merge_workers.py WORKER_DB [...]
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import sqlite3
import sys

sys.path.insert(0, str(P.HIERARCHY / 'gap-tools-berkeley'))
import capstore  # noqa: E402

COLS = "url,final_url,capture_url,fetched_at,status,sha256,content_type,content,error"
main = capstore.connect(capstore.DB_MAIN)
for w in sys.argv[1:]:
    src = sqlite3.connect(f"file:{w}?mode=ro", uri=True)
    n = added = 0
    for row in src.execute(f"SELECT {COLS} FROM captures ORDER BY id"):
        n += 1
        dup = main.execute("SELECT 1 FROM captures WHERE url=? AND capture_url IS ? AND fetched_at=? AND sha256 IS ? LIMIT 1",
                           (row[0], row[2], row[3], row[5])).fetchone()
        if dup:
            continue
        main.execute(f"INSERT INTO captures({COLS}) VALUES (?,?,?,?,?,?,?,?,?)", row)
        added += 1
    main.commit()
    src.close()
    print(f"{w}: {n} rows, {added} added")
main.close()
