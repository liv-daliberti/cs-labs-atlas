"""usage: links.py URL REGEX: absolute links on the stored page whose href or anchor text matches REGEX."""
import sys, re, zlib, mpcap
from urllib.parse import urljoin
con = mpcap.connect()
r = con.execute('select content, final_url from captures where (url=? or capture_url=?) and status=200 order by id desc', (sys.argv[1], sys.argv[1])).fetchone()
b = zlib.decompress(r[0]).decode('utf8', 'replace')
seen = set()
for m in re.finditer(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', b, re.S | re.I):
    h, txt = m.group(1), re.sub(r'<[^>]+>|\s+', ' ', m.group(2)).strip()
    if re.search(sys.argv[2], h + ' ' + txt, re.I):
        u = urljoin(r[1] or sys.argv[1], h)
        if u not in seen:
            seen.add(u); print(u, '|', txt[:60])
