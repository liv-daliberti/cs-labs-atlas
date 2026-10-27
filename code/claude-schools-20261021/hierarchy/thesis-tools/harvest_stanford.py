"""Stanford thesis harvest into hierarchy/stanford/thesis-captures.sqlite (single writer).

The Stanford Digital Repository dissertations were fetched by the Stanford base sweep
(claude-stanford-20261027/tools/st_dissertations.py: DataCite REST list of SDR Dissertation DOIs -> each PURL's public
MODS, robots.txt allowing; SearchWorks answers bots with a JavaScript traffic check and is not used). Their stored bytes
are copied in unchanged here (same fetched_at and sha256; copied_from names the source store), so records.stanford()
reads them like any other capture. Resumable (a URL already stored is skipped).
usage: harvest_stanford.py
"""
import json, os, sqlite3, sys, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tcap  # noqa: E402

SRC = "/n/fs/similarity/maxent-grpo/.research-sweeps/claude-stanford-20261027/raw/captures.sqlite"


def main():
    src = sqlite3.connect(f"file:{SRC}?mode=ro", uri=True, timeout=120)
    con = tcap.connect("stanford")
    have = {u for (u,) in con.execute("select url from captures")}
    n = 0
    for url, fetched, st, sha, ct, raw in src.execute("select url, fetched_at, status, sha256, content_type, raw_zlib from live "
                                                       "where (url like 'https://purl.stanford.edu/%.mods' or url like 'https://api.datacite.org/dois?%') and status=200"):
        if url in have:
            continue
        body = zlib.decompress(raw)
        tcap._insert(con, url, url, None, st, body, ct, None, fetched_at=fetched, copied_from="claude-stanford-20261027/raw/captures.sqlite#live", sha=sha)
        n += 1
    print(json.dumps(dict(copied=n, stored=len(have) + n)))


if __name__ == "__main__":
    main()
