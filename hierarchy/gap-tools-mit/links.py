"""Print hrefs (absolute) + anchor text of the latest stored capture of URL, filtered by regex. usage: links.py URL [RX]"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import re, sys
from urllib.parse import urljoin
sys.path.insert(0, str(P.HIERARCHY / 'gap-tools-mit'))
import capstore
from bs4 import BeautifulSoup
r = capstore.latest(sys.argv[1]); rx = re.compile(sys.argv[2] if len(sys.argv) > 2 else '.', re.I)
base = r['final_url'] or r['url']
soup = BeautifulSoup(capstore.decode(r['content']), 'lxml')
seen = set()
for a in soup.find_all('a', href=True):
    h = urljoin(base, a['href']); t = re.sub(r'\s+', ' ', a.get_text(' ')).strip()
    if (rx.search(h) or rx.search(t)) and (h, t) not in seen:
        seen.add((h, t)); print(h, '|', t[:80])
