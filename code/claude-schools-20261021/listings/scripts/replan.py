"""Forget plan rows so plan_fetch reconsiders them (after a config or extractor change).

usage: replan.py <school> <slot-substring> [status ...]   (default statuses: unusable nocapture)
Captures stay in the sqlite (no refetch); their cached text blocks are cleared so they are re-extracted.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wb


def main(a):
    school, sub = a[0], a[1]
    statuses = a[2:] or ["unusable", "nocapture"]
    con = wb.db(school)
    rows = con.execute("select slot, year, half, status, tried, capture_url from plan").fetchall()
    n = 0
    for slot, y, h, st, tried, cap in rows:
        if sub.lower() not in slot.lower() or st not in statuses:
            continue
        caps = [t["capture_url"] for t in json.loads(tried or "[]")] + ([cap] if cap else [])
        for c in caps:
            con.execute("update captures set blocks_json=NULL, text=NULL where capture_url=?", (c,))
        con.execute("delete from plan where slot=? and year=? and half=?", (slot, y, h))
        n += 1
    con.commit()
    print("forgot", n, "plan rows")


if __name__ == "__main__":
    main(sys.argv[1:])
