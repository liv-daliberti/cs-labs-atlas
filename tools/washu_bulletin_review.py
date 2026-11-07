"""Offline review of the official WashU engineering Bulletin PDFs.

Read only the school_web live cache; never fetch, infer appointment intervals,
or write listing coverage. The academic edition and printed document date are
separate evidence fields. A PDF generated after its academic year needs review.

Usage: atlas run tools/washu_bulletin_review.py --out <review-json>
"""
import argparse
import datetime as dt
import hashlib
import json
import re
import sqlite3
import zlib
from pathlib import Path

import atlas_paths as P

DEPARTMENTS = {
    'Biomedical Engineering': 'BME',
    'Computer Science & Engineering': 'CSE',
    'Electrical & Systems Engineering': 'ESE',
}
INDEX_URL = 'https://bulletin.wustl.edu/about/prior/'


def faculty_section(pages):
    """Return a verbatim whitespace-normalized Faculty section, fail closed."""
    text = '\n'.join(pages)
    start = re.search(r'\nFaculty\n', text)
    if not start:
        raise ValueError('missing Faculty heading')
    text = text[start.start() + 1:]
    end = re.search(r'\n(?:Degree Requirements|Requirements|Degrees? Offered|Doctoral Degrees)\n', text)
    if not end:
        raise ValueError('missing end of Faculty section')
    return ' '.join(text[:end.start()].split())


def printed_date(pages):
    """Use the document's printed date, never its filename or fetch date."""
    dates = {m for text in pages for m in re.findall(r'\((\d\d/\d\d/\d\d)\)', text[:300])}
    if len(dates) != 1:
        raise ValueError(f'expected one printed date, found {sorted(dates)}')
    return dt.datetime.strptime(dates.pop(), '%m/%d/%y').date().isoformat()


def review_pdf(url, sha256, fetched_at, raw):
    import pymupdf

    if hashlib.sha256(raw).hexdigest() != sha256:
        raise ValueError(f'raw SHA mismatch: {url}')
    edition = re.search(r'Bulletin_(\d{4})-(\d{2})_', url)
    if not edition:
        raise ValueError(f'no academic edition: {url}')
    academic_year = edition.group(1) + '-' + edition.group(2)
    academic_end = int(edition.group(1)) + 1
    with pymupdf.open(stream=raw, filetype='pdf') as doc:
        pages = [p.get_text() for p in doc]
        date = printed_date(pages)
        toc = doc.get_toc()
        records = []
        for i, (level, name, page) in enumerate(toc):
            if name not in DEPARTMENTS:
                continue
            end = next((x[2] for x in toc[i + 1:] if x[0] <= level), len(pages))
            section_pages = pages[page - 1:end]
            quote = faculty_section(section_pages)
            # Confirm department ownership from the PDF's own bookmark and text.
            if name not in ' '.join('\n'.join(section_pages).split()):
                raise ValueError(f'department heading absent: {url}, {name}')
            records.append(dict(
                dept=DEPARTMENTS[name], department=name, bookmark_page=page,
                source_url=url, sha256=sha256, fetched_at=fetched_at,
                academic_edition=academic_year, printed_date=date,
                pdf_creation_date=doc.metadata.get('creationDate'),
                date_review=('generated_after_academic_year' if date > f'{academic_end}-08-31'
                             else 'edition_and_printed_date_preserved'),
                appointment_attribution='not_imported', quote=quote,
            ))
    if {x['dept'] for x in records} != set(DEPARTMENTS.values()) or len(records) != 3:
        raise ValueError(f'expected exactly three department faculty sections: {url}')
    return records


def build(cache):
    records = []
    with sqlite3.connect(f'file:{Path(cache).resolve()}?mode=ro', uri=True) as con:
        index = con.execute('select sha256, raw_zlib from live where url=? and status=200', (INDEX_URL,)).fetchone()
        if not index:
            raise ValueError('official index not cached')
        index_html = zlib.decompress(index[1]).decode('utf-8')
        for url, sha, fetched, compressed in con.execute(
                "select url, sha256, fetched_at, raw_zlib from live where status=200 "
                "and lower(url) like 'https://bulletin.wustl.edu/about/prior/bulletin_%grad_engineering.pdf' order by url"):
            if url.rsplit('/', 1)[-1] not in index_html:
                raise ValueError(f'PDF not linked by cached official index: {url}')
            records.extend(review_pdf(url, sha, fetched, zlib.decompress(compressed)))
    return dict(
        school='washu', review='2026-11-06 historical source discovery',
        scope='Faculty section evidence only; no appointment intervals or listing coverage inferred.',
        access=dict(index_url=INDEX_URL, index_sha256=index[0],
                    allowed_path='/about/prior/', disallowed_path='/prior/',
                    note='Robots-aware school_web fetched index and linked PDFs; disallowed HTML was not fetched.'),
        records=records,
    )


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cache', type=Path, default=P.data('school-captures.sqlite', 'washu'))
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args(argv)
    review = build(args.cache)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(review, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(dict(out=str(args.out), documents=len(review['records']) // 3,
                          faculty_sections=len(review['records']))))


if __name__ == '__main__':
    main()
