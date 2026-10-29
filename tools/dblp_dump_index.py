"""Which works are in CS venues: every DBLP record's DOI and title, from DBLP's official monthly dump.

The dump is DBLP's own bulk release on Dagstuhl DROPS (doi:10.4230/dblp.xml.2026-09-01; robots.txt allows the storage
path), not the bot-walled dblp.org site:
  var/data/dblp-dump/dblp-2026-09-01.xml.gz (md5 in the .md5 file next to it)
Records are streamed (no DTD; entities in titles are left as is, which only costs a few title matches). CoRR (arXiv
mirror, key journals/corr/), person pages (homepages/) and data records are not venues and are skipped.
-> var/data/dblp-dump/dblp-2026-09-01-index.npz: doi (sorted uint64 hashes of lower-cased DOIs), title (sorted uint64
   hashes of pi_hierarchy.norm_title, titles of 30+ normalized characters only), plus counts
usage: dblp_dump_index.py
"""
import gzip, hashlib, html, json, re, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from pi_hierarchy import norm_title  # noqa: E402

import atlas_paths as P  # noqa: E402  (every path in one place)
DUMP = P.DBLP_DUMP_XML
OUT = DUMP.with_name('dblp-2026-09-01-index.npz')
DOI = re.compile(r'<ee[^>]*>https?://(?:dx\.)?doi\.org/([^<]+)</ee>')
TITLE = re.compile(r'<title[^>]*>(.*?)</title>', re.S)


def h(s):
    return int.from_bytes(hashlib.blake2b(s.encode(), digest_size=8).digest(), 'little')


def doi_hash(d):
    return h(d.strip().lower())


def title_hash(t):
    return h(norm_title(t))


REC = re.compile(r'<(article|inproceedings|proceedings|book|incollection|phdthesis|mastersthesis|www|data) [^>]*?key="([^"]+)"[^>]*>(.*?)</\1>', re.S)


def main():
    """Whole records are matched in a streaming buffer: one line can close a record and open the next
    ('</incollection><incollection key=...>'), so line-by-line parsing loses records."""
    dois, titles, n, skipped, tail = [], [], 0, 0, ''
    with gzip.open(DUMP, 'rt', encoding='utf-8', errors='replace') as f:
        while True:
            chunk = f.read(8 << 20)
            buf = tail + chunk
            end = 0
            for m in REC.finditer(buf):
                end = m.end(); n += 1
                typ, key, body = m.group(1), m.group(2), m.group(3)
                if typ in ('www', 'data') or key.startswith(('journals/corr/', 'homepages/', 'data/')):
                    skipped += 1; continue
                for d in DOI.findall(body):
                    dois.append(doi_hash(html.unescape(d)))
                t = TITLE.search(body)
                if t:
                    tt = re.sub(r'<[^>]+>', '', html.unescape(t.group(1)))
                    if len(norm_title(tt)) >= 30:
                        titles.append(title_hash(tt))
                if n % 1_000_000 == 0:
                    print(json.dumps(dict(records=n, dois=len(dois), titles=len(titles))), flush=True)
            tail = buf[end:]
            if not chunk:
                break
    d = np.unique(np.array(dois, dtype=np.uint64)); t = np.unique(np.array(titles, dtype=np.uint64))
    np.savez(OUT, doi=d, title=t)
    print(json.dumps(dict(records=n, skipped=skipped, dois=int(d.size), titles=int(t.size), out=str(OUT))))


class Index:
    """Membership tests against the saved hashes: Index().has(doi=..., title=...)."""
    def __init__(self):
        z = np.load(OUT); self.d, self.t = z['doi'], z['title']

    @staticmethod
    def _in(arr, x):
        i = np.searchsorted(arr, np.uint64(x)); return bool(i < arr.size and arr[i] == np.uint64(x))

    def has(self, doi=None, title=None):
        if doi and self._in(self.d, doi_hash(re.sub(r'^https?://(dx\.)?doi\.org/', '', doi))):
            return True
        return bool(title and len(norm_title(title)) >= 30 and self._in(self.t, title_hash(title)))


if __name__ == '__main__':
    main()
