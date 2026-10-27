"""b02 helper: run lp.py commands (one per line in a job file, args separated by ' ||| ')
and retry each while Wayback refuses connections. Fetching still goes only through lp.py.
usage: w_b02_retry.py JOBFILE OUTFILE [--tries N] [--wait S]
"""
import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = "/usr/local/anaconda3/2024.02/bin/python"

p = argparse.ArgumentParser()
p.add_argument("jobfile")
p.add_argument("outfile")
p.add_argument("--tries", type=int, default=8)
p.add_argument("--wait", type=int, default=90)
a = p.parse_args()

jobs = [ln.strip() for ln in open(a.jobfile) if ln.strip() and not ln.startswith("#")]
with open(a.outfile, "a") as out:
    for job in jobs:
        args = [x.strip() for x in job.split("|||")]
        for t in range(a.tries):
            r = subprocess.run([PY, "-I", os.path.join(HERE, "lp.py")] + args,
                               capture_output=True, text=True, cwd="/tmp")
            txt = r.stdout + r.stderr
            bad = ("Connection refused" in txt or "ConnectionError" in txt or "Read timed out" in txt
                   or txt.strip().endswith("0 captures"))
            if not bad or t == a.tries - 1:
                out.write("### JOB " + job + f"  (try {t + 1})\n" + txt + "\n")
                out.flush()
                break
            time.sleep(a.wait)
print("done", file=sys.stderr)
