"""peek.py N PI [PI...]: per PI, page stats, drop counts and the first N kept (missing) rows."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stbuild  # noqa: E402

n = int(sys.argv[1])
for pi in sys.argv[2:]:
    rows, rep = stbuild.build({pi})
    r = rep.get(pi, {})
    print(f"## {pi}: {r.get('status')} in_window={r.get('in_window')} held={r.get('held')} missing={r.get('missing')}")
    for p in r.get("pages", []):
        print(f"   {p['url']} entries={p['entries']} noyear={p['no_year']} dropped={p['dropped']} {p.get('problem', '')}")
    for x in rows[:n]:
        print(f"   {x['year']} {x['title'][:105]} | {(x['venue'] or '')[:40]}")
