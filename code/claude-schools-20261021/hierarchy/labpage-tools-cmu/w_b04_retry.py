"""b04 helper: fetch a list of URLs through lp.py get, retrying when Wayback refuses connections.

usage: python -I w_b04_retry.py OUTFILE URL [URL ...]
Each URL is fetched with `lp.py get URL --compact`; on a connection/read error the fetch is retried
(up to 8 attempts, 60 s apart). Output of the successful (or last) attempt is appended to OUTFILE.
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = "/usr/local/anaconda3/2024.02/bin/python"


def main():
    out, urls = sys.argv[1], sys.argv[2:]
    for u in urls:
        txt = ""
        for attempt in range(8):
            p = subprocess.run([PY, "-I", os.path.join(HERE, "lp.py"), "get", u, "--compact"],
                               capture_output=True, text=True, timeout=900)
            txt = p.stdout + p.stderr
            first = txt.split("\n", 1)[0]
            if '"status": 200' in first or '"status": 404' in first:
                break
            time.sleep(60)
        with open(out, "a") as f:
            f.write(f"##### {u} (attempts={attempt + 1})\n{txt}\n")


if __name__ == "__main__":
    main()
