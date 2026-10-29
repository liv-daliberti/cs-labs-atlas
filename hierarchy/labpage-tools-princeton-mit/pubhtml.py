"""Print the raw HTML (whitespace-collapsed) around the first occurrence of a text in a stored page, to write a pubx
spec. usage: pubhtml.py SCHOOL SRC TEXT [N]"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lpcap  # noqa: E402
import lpev  # noqa: E402

school, src, text = sys.argv[1:4]
n = int(sys.argv[4]) if len(sys.argv) > 4 else 900
r, v = lpev.cap(school, src)
h = re.sub(r"\s+", " ", lpcap.decode(r["content"]))
i = h.find(text)
print(h[max(0, i - n // 3): i + n] if i >= 0 else f"not found; head: {h[:400]}")
