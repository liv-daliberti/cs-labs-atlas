"""Review CLI for the Stanford lab-page publication pass.
  get URL [--links RX] [--grep RX] [--head N] [--wb]   fetch (cached, polite) and print text / matching links / grep windows
  wb URL [--from Y] [--to Y]                            Wayback captures (distinct digests), newest last
  pubs PI URL [--mode auto|bib|links] [--show N] [--all] parsed entries: year, held flag, title | venue
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stcap  # noqa: E402,F401
import lpcap  # noqa: E402
import lplab  # noqa: E402
import lppubs  # noqa: E402

S = "stanford"


def opt(a, k, d=None):
    return a[a.index(k) + 1] if k in a else d


def main():
    a = sys.argv[1:]
    cmd = a[0]
    if cmd == "get":
        url = a[1]
        r = lpcap.get(S, url, wb="--wb" in a) if "--wb" in a else lpcap.fetch(S, url)
        print(f"# status={r.get('status')} err={r.get('error')} final={r.get('final_url')} cap={r.get('capture_url')} "
              f"sha={r.get('sha256')} ct={r.get('content_type')}")
        if not r.get("content"):
            return
        if "--links" in a:
            rx = re.compile(opt(a, "--links"), re.I)
            for h, t in lpcap.links(r["content"], r.get("final_url") or url):
                if rx.search(h) or rx.search(t):
                    print(f"  {t[:70]!r} -> {h}")
            return
        t = lpcap.page_text(r["content"], r.get("content_type"))
        if "--grep" in a:
            for m in re.finditer(opt(a, "--grep"), t, re.I):
                print("...", t[max(0, m.start() - 150):m.end() + 250])
            return
        n = int(opt(a, "--head", 3000))
        print(len(t), t[:n])
    elif cmd == "html":
        import stbuild
        r = lplab.stored(S, a[1]) or stbuild.wayback_row(a[1]) or lpcap.fetch(S, a[1])
        h = lpcap.decode(r["content"])
        for m in list(re.finditer(opt(a, "--grep"), h, re.I))[:int(opt(a, "--n", 2))]:
            print("...", h[max(0, m.start() - int(opt(a, "--before", 300))):m.end() + int(opt(a, "--after", 900))])
            print()
    elif cmd == "wb":
        for row in lpcap.wayback_cdx(S, a[1], frm=opt(a, "--from"), to=opt(a, "--to")):
            print(row[0], lpcap.wayback_id(row[0], row[1]))
    elif cmd == "pubs":
        pi, url = a[1], a[2]
        import stbuild
        r = lplab.stored(S, url) or stbuild.wayback_row(url) or lpcap.fetch(S, url)
        if not r or not r.get("content"):
            print("not stored", r and r.get("error"))
            return
        es = lppubs.parse(S, {"pi": pi}, r, url, mode=opt(a, "--mode", "auto"))
        w = [e for e in es if e["in_window"]]
        print(f"# entries={len(es)} in_window={len(w)} held={sum(e['held'] for e in w)} "
              f"no_year={sum(1 for e in es if not e['year'])} noquote={sum(1 for e in w if not e['quote'])} "
              f"held_total={len(lplab.lab_papers(S).get(pi, []))}")
        n = int(opt(a, "--show", 40))
        sel = es if "--all" in a else w
        if "--missing" in a:
            sel = [e for e in sel if not e["held"]]
        for e in sel[:n]:
            print(f"{e['year']} {'H' if e['held'] else '-'} {e['title'][:120]} | {(e['venue'] or '')[:60]}")


if __name__ == "__main__":
    main()
