"""Save a CURRENT (live) paged faculty directory and write its reviewed manifest `hierarchy/<key>/reviewed/live-listing-sources.json` entry (the Stage 1
"current live supplement", docs/SCHOOL-PROCESS.md): every page of the listing is fetched with school_web.live (robots.txt and challenges honoured), the pager
(listing_formats.page_links) is followed, and the group is written as {dept, slot, format, complete: true, expected_entries: <parsed count>, pages: [{url, sha256}]}.
The listing then supplies sourced person rows for its observation half-year; no earlier year is inferred.

  live_listing_manifest.py <key> <dept> <slot> <first-page-url> <format>
"""
import json, sys
import atlas_paths as P  # noqa: E402
import listing_formats as LF  # noqa: E402
import school_web as W  # noqa: E402
from school_web import body  # noqa: E402


def fetch_all(c, url, fmt, limit=60):
    pages, seen, todo = [], set(), [url]
    while todo and len(pages) < limit:
        u = todo.pop(0)
        if u in seen:
            continue
        seen.add(u)
        res = W.live(c, u)
        if not res or res[0] != 200:
            raise SystemExit(f'not fetched (robots, challenge or status {res and res[0]}): {u}')
        import zlib
        raw = c.execute('select raw_zlib from live where url=?', (u,)).fetchone()[0]
        html = body(raw).decode('utf-8', 'replace') if raw else ''
        _, es = LF.parse(html, fmt)
        pages.append(dict(url=u, sha256=res[1], entries=len(es)))
        todo += [x for x in LF.page_links(html, u).values() if x not in seen]
    return pages


def main(key, dept, slot, url, fmt):
    c = W.con(key)
    pages = fetch_all(c, url, fmt)
    path = P.data_w('live-listing-sources.json', key)
    doc = json.loads(path.read_text()) if path.exists() else {'sources': []}
    doc['sources'] = [s for s in doc['sources'] if (s['dept'], s['slot']) != (dept, slot)]
    doc['sources'].append(dict(dept=dept, slot=slot, format=fmt, complete=True, expected_entries=sum(p['entries'] for p in pages),
                               pages=[dict(url=p['url'], sha256=p['sha256']) for p in pages]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps(dict(key=key, pages=len(pages), entries=sum(p['entries'] for p in pages))))


if __name__ == '__main__':
    main(*sys.argv[1:6])
