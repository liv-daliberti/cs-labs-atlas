"""Page ranges of every record on the persons' DBLP pages, read from DBLP's official dump (2026-11-02, accuracy pass).

Why: OpenAlex's sweep works carry no `biblio`, so the build cannot tell a one-page column ('Technical perspective', a CACM
Viewpoint) or a two-page keynote abstract from a paper by the title alone. DBLP's `<pages>` field is the page evidence the
build already holds (the records are those of hierarchy/dblp-dump-persons.json.gz, matched by DOI or title like every
other DBLP signal). A side file, so the persons file and the released packages stay as they are.

Source: external/dblp-dump/dblp-2026-09-01.xml.gz (DBLP's bulk release, never dblp.org).
-> hierarchy/dblp-dump-pages.json.gz  {dump, pages: {dblp key: pages string}}
usage: dblp_dump_pages.py [school]
  A school reads its own persons extraction and writes its own page sidecar; shared metadata is never rewritten.
"""
import argparse, gzip, html, json, re

import atlas_paths as P  # noqa: E402  (every path in one place)

REC = re.compile(r'<(article|inproceedings|incollection) ([^>]*?)key="([^"]+)"[^>]*>(.*?)</\1>', re.S)
PAGES = re.compile(r'<pages>([^<]*)</pages>')


def page_count(pages):
    """The number of pages a DBLP `pages` string spans: '502-503' -> 2, '97' -> 1, '12:1-12:20' -> 20, '28-30' -> 3;
    None when it is not a numeric range ('e123', '', '1-')."""
    s = html.unescape(str(pages or '')).strip()
    m = re.fullmatch(r'(?:\d+:)?(\d+)(?:\s*[-–]\s*(?:\d+:)?(\d+))?', s)
    if not m:
        return None
    a = int(m.group(1)); b = int(m.group(2)) if m.group(2) else a
    return b - a + 1 if b >= a else None


def records(path):
    tail = ''
    with gzip.open(path, 'rt', encoding='utf-8', errors='replace') as f:
        while True:
            chunk = f.read(8 << 20); buf = tail + chunk; end = 0
            for m in REC.finditer(buf):
                end = m.end(); yield m.group(3), m.group(4)
            tail = buf[end:]
            if not chunk:
                break


def load_page_ranges(school=None, root=None):
    """Shared ranges plus this school's local extraction, without changing either source."""
    files = [P.data('dblp-dump-pages.json.gz', root=root)]
    if school:
        files.append(P.data('dblp-dump-pages-school.json.gz', school, root=root))
    pages = {}
    for path in files:
        if path.exists():
            pages.update(json.loads(gzip.decompress(path.read_bytes()))['pages'])
    return pages


def main(school=None):
    source = P.data('dblp-dump-persons-school.json.gz', school) if school else P.data('dblp-dump-persons.json.gz')
    dest = P.data_w('dblp-dump-pages-school.json.gz', school) if school else P.data_w('dblp-dump-pages.json.gz')
    persons = json.loads(gzip.open(source, 'rt').read())
    want = {r['key'] for p in persons['persons'].values() for r in p.get('pubs') or []}
    pages = {}
    for key, body in records(P.DBLP_DUMP_XML):
        if key in want:
            m = PAGES.search(body)
            if m:
                pages[key] = html.unescape(m.group(1)).strip()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(dest, 'wt') as f:
        json.dump(dict(dump=P.DBLP_DUMP_XML.name, pages=pages), f)
    print(json.dumps(dict(school=school, wanted=len(want), with_pages=len(pages), out=str(dest))), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('school', nargs='?')
    main(ap.parse_args().school)
