"""Count PI-years newly covered relative to an earlier listings.json snapshot.

usage: filled.py <school> <old-listings.json>
A PI-year is covered when some row of that PI has that year and no future-start note.
"""
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wb


def covered(rows):
    return {(r["pi"], r["year"]) for r in rows if not r["future_start_note"]}


def main(school, old_path):
    new = json.load(open(wb.school_dir(school) / "listings.json"))
    old = json.load(open(old_path))
    a, b = covered(old), covered(new)
    gained = sorted(b - a)
    by_year = collections.Counter(y for _, y in gained)
    by_kind = collections.Counter()
    for pi, y in gained:
        kinds = {r["listing"] if r["listing"] in ("department profile page", "home department faculty list") else r["listing"]
                 for r in new if r["pi"] == pi and r["year"] == y and not r["future_start_note"]}
        by_kind[" + ".join(sorted(kinds))] += 1
    lost = sorted(a - b)
    print(json.dumps({"school": school, "pi_years_filled": len(gained), "by_year": dict(sorted(by_year.items())),
                      "by_source": dict(by_kind), "pis_gaining": len({p for p, _ in gained}),
                      "pi_years_lost": len(lost)}, ensure_ascii=False))
    return gained


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
