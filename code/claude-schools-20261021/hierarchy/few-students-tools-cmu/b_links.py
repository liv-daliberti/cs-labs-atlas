"""Print hrefs from a cached capture whose anchor text matches REGEX. usage: b_links.py URL REGEX"""
import re, sys, zlib
from urllib.parse import urljoin
sys.path.insert(0, "/n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/few-students-tools-cmu")
import capstore
from bs4 import BeautifulSoup
url, rx = sys.argv[1], sys.argv[2]
con = capstore.connect()
row = con.execute("SELECT content, final_url FROM captures WHERE (url=? OR capture_url=?) AND status=200 AND content IS NOT NULL ORDER BY id DESC LIMIT 1", (url, url)).fetchone()
soup = BeautifulSoup(capstore._decode(zlib.decompress(row[0])), "lxml")
for a in soup.find_all("a", href=True):
    t = re.sub(r"\s+", " ", a.get_text(" ")).strip()
    if re.search(rx, t, re.I):
        print(urljoin(row[1] or url, a["href"]), "|", t[:80])
