"""Every (name, title) entry on the stored Princeton department faculty-list captures outside Computer Science
(claude-princeton-listings-20261022/captures/listings.sqlite, plus captures this review fetched into
hierarchy/cs-related-captures-princeton.sqlite that carry a 'dept_listing' note in the side file), read with the listings
sweep's own block extraction: a block that is a person's name followed within two blocks by a faculty title.
-> <out>/princeton-listing-entries.json  [{dept, page_url, capture_url, ts, year, sha256, name, title, heading, src}]
usage: princeton_listing_entries.py <out_dir> [extra_captures.json]
"""
import json, re, sqlite3, sys, zlib
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]; SW = Path('/n/fs/resemble/maxent-grpo/.research-sweeps')
LST = SW / 'claude-princeton-listings-20261022'
sys.path.insert(0, str(LST / 'scripts'))
import extract, match  # noqa: E402

NAME = re.compile(r"^[A-ZÀ-Ž][\w'’.\-À-ž]+(?: (?:[A-ZÀ-Ž(][\w'’.\-À-ž)]*|de|van|von|der|da|del|di|la|le)){1,4}$")
BAD = re.compile(r'Professor|Faculty|Department|Lecturer|Emerit|People|Staff|Students|Research|Program|Office|Contact|Center|Institute|'
                 r'Search|Directory|Menu|Princeton|University|Home|News|Events|About|Courses|Graduate|Undergraduate|Admission', re.I)


def entries(dept, page_url, capture_url, ts, sha, raw, ct, src):
    b = extract.blocks(raw, ct); out = []
    heading = ''
    for i, (k, t) in enumerate(b):
        if k.startswith('h'):
            heading = t
        if not (NAME.match(t) and not BAD.search(t) and len(t) < 50):
            continue
        for j in (1, 2):
            if i + j >= len(b):
                break
            tt = b[i + j][1]
            if match.FAC_RX.search(tt) and len(tt) < 160:
                out.append(dict(dept=dept, page_url=page_url, capture_url=capture_url, ts=ts, year=int(ts[:4]), sha256=sha, name=t,
                                title=tt, between=[x[1] for x in b[i + 1:i + j]], heading=heading, src=src))
                break
            if NAME.match(tt):
                break
    return out


def main(out, extra=None):
    con = sqlite3.connect(f'file:{LST}/captures/listings.sqlite?mode=ro', uri=True)
    rows = con.execute("select department, page_url, capture_url, wayback_timestamp, sha256, raw_zlib, content_type from captures "
                       "where http_status=200 and department not in ('Computer Science','CS')").fetchall()
    res = []
    for dept, pu, cu, ts, sha, raw, ct in rows:
        res += entries(dept, pu, cu, ts, sha, zlib.decompress(raw), ct, 'claude-princeton-listings-20261022/captures/listings.sqlite')
    if extra:  # captures fetched by this review: [{dept, page_url, capture_url, ts}]
        c2 = sqlite3.connect(f"file:{HERE / 'hierarchy/cs-related-captures-princeton.sqlite'}?mode=ro", uri=True)
        for e in json.load(open(extra)):
            r = c2.execute('select sha256, content, content_type from captures where (url=? or capture_url=?) and status=200 and error is null order by id desc limit 1',
                           (e['capture_url'], e['capture_url'])).fetchone()
            if r:
                res += entries(e['dept'], e['page_url'], e['capture_url'], e['ts'], r[0], zlib.decompress(r[1]), r[2], 'hierarchy/cs-related-captures-princeton.sqlite')
    json.dump(res, open(Path(out) / 'princeton-listing-entries.json', 'w'), ensure_ascii=False, indent=0)
    print(len(res), len({(r['dept'], r['name']) for r in res}))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
