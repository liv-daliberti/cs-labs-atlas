"""Fetch URLs politely into hierarchy/cmu/cs-related-captures.sqlite (via cs-related-tools/csrcap.py) and print, per page,
the status and short text windows around appointment/advising keywords. usage: fetch_show.py URL [URL ...] (or - for stdin)."""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'cs-related-tools'))
import csrcap  # noqa: E402

KW = re.compile(r'(joined|since (?:19|20)\d\d|faculty in (?:19|20)\d\d|arrived at|came to Carnegie|Ph\.? ?D\.? [Ss]tudents?|PhD [Ss]tudents?|advis(?:ee|or|es|ed)|[Ll]ab\b|Laboratory|Professor[^.]{0,60})')
urls = [l.strip() for l in sys.stdin] if sys.argv[1:] == ['-'] else sys.argv[1:]
for u in urls:
    if not u:
        continue
    try:
        r = csrcap.fetch(u)
    except Exception as e:
        print(f'## {u} ERROR {e!r}'[:300]); continue
    t = r.get('text') or ''
    print(f"## {u} status={r.get('status')} err={r.get('error')} id={r.get('id')} n={len(t)}")
    seen = 0
    for m in KW.finditer(t):
        print('   ', t[max(0, m.start() - 90):m.end() + 110].replace('\n', ' '))
        seen += 1
        if seen >= 7:
            break
    sys.stdout.flush()
