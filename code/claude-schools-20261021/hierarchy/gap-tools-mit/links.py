"""Print hrefs (absolute) + anchor text of the latest stored capture of URL, filtered by regex. usage: links.py URL [RX]"""
import re, sys
from urllib.parse import urljoin
sys.path.insert(0, '/n/fs/similarity/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/gap-tools-mit')
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
