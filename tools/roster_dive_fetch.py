"""Polite fetcher for the UChicago roster deep dive (2026-11-04): tools/mpcap.fetch with two changes.

- Every web.archive.org / archive.org request takes its slot from fulltext-push/host_throttle.py (the shared 5 s clock) and waits out the
  shared 429 cooldown; a 429 is recorded there (record_429) so every other client backs off too.
- Captures go to hierarchy/uchicago/raw/roster-dive-captures.sqlite (data, git-ignored), not the missing-PI store.

robots.txt (including groups naming ClaudeBot or anthropic-ai is honoured by mpcap's own rule reader for its user agent; a host whose robots.txt
names ClaudeBot/anthropic-ai with Disallow is skipped here too), the bot-challenge stop and the off-limits hosts are mpcap's.

  python3 tools/roster_dive_fetch.py URL [URL...]      # fetch and print status + length
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'fulltext-push'))
import atlas_paths as P  # noqa: E402
import mpcap  # noqa: E402
import host_throttle as HT  # noqa: E402

mpcap.DB = str(P.school_part('uchicago', 'raw') / 'roster-dive-captures.sqlite')
_orig_wait = mpcap._wait
ARCHIVE = 'web.archive.org'


def _wait(host):
    if host.endswith('archive.org'):
        HT.wait_slot(ARCHIVE, 8.0)   # waits out a cooldown up to WAIT_MAX, raises above it, re-checks after the slot (2026-11-05)
        return
    _orig_wait(host)


mpcap._wait = _wait

_orig_allowed = mpcap.robots_allowed
_AI_AGENTS = ('claudebot', 'anthropic-ai', 'claude-web')


def _ai_rules(base):
    """Disallow/allow rules of any robots.txt group naming ClaudeBot / anthropic-ai / claude-web (the stored robots capture)."""
    import zlib
    con = mpcap.connect()
    row = con.execute('SELECT status, content FROM captures WHERE url=? AND error IS NULL ORDER BY id DESC LIMIT 1',
                      (base + '/robots.txt',)).fetchone()
    con.close()
    if not row or row[0] != 200 or not row[1]:
        return []
    txt = zlib.decompress(row[1]).decode('utf-8', 'replace')
    if '<html' in txt[:500].lower():
        return []
    groups, agents, rules, last = [], [], [], False
    for raw in txt.splitlines():
        line = raw.split('#', 1)[0].strip()
        if ':' not in line:
            continue
        k, v = [x.strip() for x in line.split(':', 1)]
        k = k.lower()
        if k == 'user-agent':
            if not last and (agents or rules):
                groups.append((agents, rules)); agents, rules = [], []
            agents.append(v.lower()); last = True
        elif k in ('allow', 'disallow'):
            rules.append((k == 'allow', v)); last = False
        else:
            last = False
    if agents or rules:
        groups.append((agents, rules))
    return [x for a, r in groups if any(g in a for g in _AI_AGENTS) for x in r]


def _allowed(url):
    from urllib.parse import urlsplit
    ok = _orig_allowed(url)          # also stores robots.txt
    if not ok:
        return False
    sp = urlsplit(url)
    path = sp.path + ('?' + sp.query if sp.query else '')
    best = None
    for allow, pat in _ai_rules(f'{sp.scheme}://{sp.netloc}'):
        if not pat:
            continue
        rx = re.escape(pat).replace(r'\*', '.*')
        rx = rx[:-2] + '$' if rx.endswith(r'\$') else rx
        if re.match(rx, path) and (best is None or len(pat) > len(best[1]) or (len(pat) == len(best[1]) and allow)):
            best = (allow, pat)
    return best is None or best[0]


mpcap.robots_allowed = _allowed


def fetch(url, refetch=False):
    r = mpcap.fetch(url, refetch=refetch)
    if r.get('status') == 429 and mpcap.host_of(url) and urlhost(url).endswith('archive.org'):
        HT.record_429(ARCHIVE)
    return r


def urlhost(url):
    from urllib.parse import urlsplit
    return urlsplit(url).hostname or ''


def wb(url, ts):
    """Wayback id_ capture URL nearest to timestamp ts (YYYY[MMDD...])."""
    return f'https://web.archive.org/web/{ts}id_/{url}'


def grep(r, pat, w=300, n=5):
    t = re.sub(r'\s+', ' ', r.get('text') or '')
    out = []
    for m in re.finditer(pat, t, re.I):
        out.append(t[max(0, m.start() - w):m.end() + w])
        if len(out) >= n:
            break
    return out


if __name__ == '__main__':
    for u in sys.argv[1:]:
        r = fetch(u)
        print(r.get('status'), r.get('error'), len(r.get('text') or ''), u)
