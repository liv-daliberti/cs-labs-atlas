"""Print the whitespace-collapsed text of stored Princeton captures (read-only): show_princeton.py SRC [START [LEN]]"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fsev  # noqa: E402

src = sys.argv[1]
start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
n = int(sys.argv[3]) if len(sys.argv) > 3 else 6000
t = fsev.text("princeton", src)
print(f"[len {len(t)}]")
print(t[start:start + n])
