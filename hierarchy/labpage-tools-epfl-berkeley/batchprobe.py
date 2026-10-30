"""Fetch every guessed URL in guesses.json (Wayback fallback) plus one level of people/pubs-like links found on them,
and record per-page stats in discover/probe-<school>.jsonl (resumable). usage: batchprobe.py SCHOOL"""
import json, os, sys
TOOLS = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, TOOLS)
import lpcap, lplab, discover  # noqa: F401,E402
school = sys.argv[1]
G = json.load(open(f"{TOOLS}/guesses.json"))[school]
out = f"{TOOLS}/discover/probe-{school}.jsonl"
done = {json.loads(l)["pi"] for l in open(out)} if os.path.exists(out) else set()
for pi, urls in G.items():
    if pi in done:
        continue
    row = lplab.lab(school, lplab.slug(pi))
    pages, seen = [], set()
    queue = [(u, "guess") for u in urls]
    while queue and len(pages) < 10:
        u, kind = queue.pop(0)
        if u in seen:
            continue
        seen.add(u)
        r = discover.fetch_any(school, u)
        info = {"url": u, "kind": kind, "status": r.get("status"), "capture_url": r.get("capture_url"),
                "final_url": r.get("final_url"), "error": (r.get("error") or "")[:80]}
        if r.get("status") == 200 and r.get("content"):
            info.update(discover.page_stats(school, row, r, u))
            if kind == "guess":
                for lk, t in discover.links_of(r, u):
                    if discover.SKIP_HOSTS.search(lk) or not lk.startswith("http"):
                        continue
                    if (discover.PEOPLE_TXT.match(t or "") or discover.PUBS_TXT.match(t or "") or t == "BIBFILE") \
                            and discover.same_site(r.get("final_url") if not r.get("capture_url") else u, lk):
                        queue.append((lk, "link:" + (t or "")[:20]))
        pages.append(info)
    with open(out, "a") as f:
        f.write(json.dumps({"pi": pi, "pages": pages}, ensure_ascii=False) + "\n")
    print(pi, len(pages), flush=True)
print("DONE", flush=True)
