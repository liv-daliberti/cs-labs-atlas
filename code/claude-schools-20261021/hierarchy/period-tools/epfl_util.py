"""Helpers for the EPFL appointment-period review (2026-10-26): copy stored captures into period-captures.sqlite, fetch, grep.

usage: python -I epfl_util.py fetch <url> [needle ...]   fetch (polite, stored) and print contexts of needles
       python -I epfl_util.py prof <slug> [needle ...]   copy people.epfl.ch/<slug>?lang=en from the CS-related store
       python -I epfl_util.py show <url> [needle ...]    print contexts from an already stored capture
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'cs-related-tools'))
import pcap  # noqa: E402
pcap.mpcap._sess.headers['Accept-Encoding'] = 'gzip, deflate'  # requests here cannot decode zstd

ROOT = HERE.parents[1]
STORES = [ROOT / 'hierarchy/epfl/cs-related-captures.sqlite', ROOT / 'hierarchy/cs-related-captures-epfl.sqlite']


def copy_any(url):
    if pcap.cached(url):
        return pcap.cached(url)
    for s in STORES:
        try:
            return pcap.mpcap.copy(str(s), url, 'select fetched_at, sha256, content from captures where (url=? or capture_url=?) '
                                   'and status=200 and error is null order by id desc limit 1', (url, url),
                                   str(s.relative_to(ROOT)), ctype='text/html')
        except KeyError:
            continue
    raise KeyError(url)


def prof(slug):
    return copy_any(f'https://people.epfl.ch/{slug}?lang=en')


def show(url, needles, before=200, after=300):
    t = pcap.text(url)
    print(f'[{len(t)} chars] {url}')
    for n in needles:
        for h in pcap.around(url, n, before, after)[:6]:
            print('  >>', h.replace('\n', ' '))


if __name__ == '__main__':
    cmd, arg, needles = sys.argv[1], sys.argv[2], sys.argv[3:]
    if cmd == 'fetch':
        r = pcap.fetch(arg)
        print('status', r.get('status'), r.get('error'))
        show(arg, needles)
    elif cmd == 'prof':
        prof(arg)
        show(f'https://people.epfl.ch/{arg}?lang=en', needles)
    elif cmd == 'show':
        show(arg, needles)


def dates(url):
    import re
    t = pcap.text(url)
    return re.findall(r'.{50}\b\d{2}\.\d{2}\.\d{2}\b(?:\d\d)?', t)[:4]


if __name__ == '__main__' and sys.argv[1] == 'dates':
    for u in sys.argv[2:]:
        print(u, dates(u))
