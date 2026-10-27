"""CDX discovery: which listing URL variants have 200 captures in which years.

usage: discover.py <school> <url-prefix> [<url-prefix> ...] [--exact] [--grep REGEX] [--top N]
One CDX prefix query per argument (collapsed to one row per URL per month), cached in the school's sqlite.
"""
import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wb


def main(argv):
    school = argv[0]
    args = argv[1:]
    exact = "--exact" in args
    grep = None
    top = 60
    if "--grep" in args:
        grep = re.compile(args[args.index("--grep") + 1], re.I)
    if "--top" in args:
        top = int(args[args.index("--top") + 1])
    prefixes = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in ("--grep", "--top"))]
    con = wb.db(school)
    for p in prefixes:
        params = {"url": p, "from": "2016", "to": "2026", "output": "json",
                  "fl": "urlkey,timestamp,original,statuscode", "filter": "statuscode:200",
                  "collapse": "timestamp:6", "limit": "30000"}
        if not exact:
            params["matchType"] = "prefix"
        rows = wb.cdx(params, con) or []
        by = collections.defaultdict(collections.Counter)
        for r in rows:
            if grep and not grep.search(r["original"]):
                continue
            by[r["urlkey"]][r["timestamp"][:4]] += 1
        print(f"== {p}: {len(rows)} rows, {len(by)} urls", flush=True)
        for k, c in sorted(by.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:top]:
            ys = " ".join(f"{y[2:]}:{c[y]}" for y in sorted(c))
            print(f"  {k[:120]:120s} {ys}")


if __name__ == "__main__":
    main(sys.argv[1:])
