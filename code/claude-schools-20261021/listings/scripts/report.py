"""Print a compact per-school report from the built outputs (listings/<school>/*.json).

usage: report.py <school> [<school> ...]
"""
import collections
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wb


def main(schools):
    for s in schools:
        d = wb.school_dir(s)
        summ = json.load(open(d / "summary.json"))
        ver = json.load(open(d / "verify.json"))
        amb = json.load(open(d / "ambiguous.json"))
        gaps = json.load(open(d / "gaps.json"))
        con = sqlite3.connect(wb.db_path(s))
        n200 = con.execute("select count(*) from captures where http_status=200").fetchone()[0]
        nall = con.execute("select count(*) from captures").fetchone()[0]
        ncdx = con.execute("select count(*) from cdx").fetchone()[0]
        print(f"===== {s}")
        print(f"captures stored: {nall} ({n200} HTTP 200), used in plan: {summ['captures_used']}, CDX queries: {ncdx}")
        print(f"rows: {summ['rows']}; verify pass {ver['pass']} fail {ver['fail']}")
        print(f"PIs with >=1 row: {summ['pis_with_row']} / {summ['pis_in_input']}")
        print("PIs listed per year:", " ".join(f"{y}:{n}" for y, n in summ["pis_listed_per_year"].items()))
        print("department-years without a usable main listing:", "; ".join(summ.get("department_years_without_main_listing", [])))
        kinds = collections.Counter(g["kind"] for g in gaps if g["scope"] == "pi-year")
        print("PI-year gaps by kind:", dict(kinds))
        ak = collections.Counter((a["kind"], tuple(a.get("pis") or [a.get("pi")])) for a in amb)
        print("ambiguous / shared entries:")
        for (k, p), n in ak.most_common():
            print(f"  {n:4d} {k}: {', '.join(p)}")
        print("never found:", summ["pis_never_found"])


if __name__ == "__main__":
    main(sys.argv[1:])
