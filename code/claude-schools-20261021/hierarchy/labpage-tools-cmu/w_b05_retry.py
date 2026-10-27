"""b05 helper: run `lp.py <args>` again with backoff while Wayback refuses connections.

usage: w_b05_retry.py [--tries N] [--wait S] -- <lp.py args...>
Retries only when the output shows a connection error to web.archive.org (refused / timeout / reset),
or when a cdx listing comes back as '0 captures' because of such an error.
"""
import os
import subprocess
import sys
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

args = sys.argv[1:]
tries, wait = 6, 40
while args and args[0] != "--":
    if args[0] == "--tries":
        tries = int(args[1]); args = args[2:]
    elif args[0] == "--wait":
        wait = int(args[1]); args = args[2:]
    else:
        break
if args and args[0] == "--":
    args = args[1:]

BAD = ("Connection refused", "ConnectTimeout", "Connection reset", "ReadTimeout", "RemoteDisconnected",
       "Max retries exceeded with url")
for i in range(tries):
    p = subprocess.run([PY, "-I", os.path.join(TOOLS, "lp.py")] + args, capture_output=True, text=True)
    out = p.stdout + p.stderr
    wb_err = any(b in out for b in BAD) and "web.archive.org" in out
    zero_cdx = args and args[0] == "cdx" and out.strip().endswith("0 captures")
    if not wb_err and not zero_cdx:
        sys.stdout.write(out)
        sys.exit(p.returncode)
    if i == tries - 1:
        sys.stdout.write(out)
        sys.exit(1)
    sys.stderr.write(f"[retry {i + 1}/{tries}] wayback refused; waiting {wait}s\n")
    time.sleep(wait)
    wait = min(int(wait * 1.5), 180)
