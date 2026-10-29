"""Print windows of the stored capture of URL (live or capture_url) around REGEX. usage: grep_cap.py URL REGEX [WIDTH]"""
import re, sys
sys.path.insert(0, '/n/fs/resemble/cs-atlas/work/hierarchy/gap-tools-mit')
import capstore
r = capstore.latest(sys.argv[1]); w = int(sys.argv[3]) if len(sys.argv) > 3 else 300
if not r: print('NO CAPTURE'); sys.exit()
t = capstore.page_text(r['content']); print('##', r['url'], r.get('capture_url'), r['sha256'][:16], 'len', len(t))
n = 0
for m in re.finditer(sys.argv[2], t, flags=re.I):
    print('  >>', t[max(0, m.start() - w):m.end() + w]); n += 1
    if n >= 10: break
if not n: print('  (no match) head:', t[:w * 3])
