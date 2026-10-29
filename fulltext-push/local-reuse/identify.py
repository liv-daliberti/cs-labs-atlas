"""Local-reuse inventory, pass 2 (2026-10-29): identify every PDF the find pass listed (lists/*.tsv) and match it to the
lab papers without a copy (missing.jsonl.gz, lr_common.py snapshot).

Per file (read once, in full): sha256, bytes, page count (pymupdf), the DOIs on page 1 and in the document / XMP metadata,
an arXiv id on page 1, the first-page title (the largest-font text in the top half of page 1).
Match rules (a candidate only; the importer re-runs the collector's own identity check before anything is recorded):
  doi    a missing paper's DOI (or one of its edition DOIs) appears on page 1 or in the PDF metadata
  title  a missing paper's normalized title (>= 20 characters) equals 1-6 consecutive lines among the first 80 lines of
         page 1, or the first-page title; AND a year on page 1 / in the metadata dates / of the arXiv id is within 1 of
         the paper's year; AND a byline family name (>= 3 letters) is a word on page 1
-> ident/shard-<i>.jsonl.gz (one row per listed path)
usage: identify.py <shard index> <shard count>
"""
import gzip, hashlib, json, os, re, sys, time, unicodedata, zlib
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOI = re.compile(r'\b(10\.\d{4,9}/[^\s"<>]+)', re.I)
ARX = re.compile(r'arXiv:\s?(\d{4}\.\d{4,5})(v\d+)?', re.I)
YEAR = re.compile(r'\b(19[89]\d|20[0-3]\d)\b')


def nt(t):
    t = re.sub(r'<[^>]+>', ' ', t or '')
    t = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', t)


def ndoi(s):
    s = re.sub(r'^https?://(?:dx\.)?doi\.org/', '', str(s or '').strip(), flags=re.I).lower()
    return s.rstrip('.,;:)]}\'"')


def family(name):
    toks = [re.sub(r'[^a-z]', '', t) for t in re.split(r'[\s,]+', unicodedata.normalize('NFKD', name or '').encode('ascii', 'ignore').decode().lower())]
    toks = [t for t in toks if t and t not in {'jr', 'sr', 'ii', 'iii', 'iv'}]
    return toks[-1] if toks and len(toks[-1]) >= 3 else ''


def load_index():
    by_doi, by_title = defaultdict(list), defaultdict(list)
    for l in gzip.open(HERE / 'missing.jsonl.gz', 'rt'):
        r = json.loads(l)
        if not r['work_id']:
            continue
        m = dict(school=r['school'], work_id=r['work_id'], key=r['key'], year=r.get('year'),
                 fam=sorted({family(n) for n in (r.get('byline') or []) + (r.get('pis') or [])} - {''}))
        for d in [r.get('doi')] + (r.get('editions') or []):
            if d:
                by_doi[ndoi(d)].append(m)
        k = nt(r.get('title'))
        if len(k) >= 20:
            by_title[k].append(m)
    return by_doi, by_title


def first_title(page):
    try:
        d = page.get_text('dict')
    except Exception:
        return ''
    h = page.rect.height or 1
    spans = []
    for b in d.get('blocks', []):
        for l in b.get('lines', []):
            for s in l.get('spans', []):
                if s.get('text', '').strip() and s['bbox'][1] < h / 2 and not s['text'].strip().lower().startswith('arxiv:'):
                    spans.append((round(s['size'], 1), s['bbox'][1], s['text'].strip()))
    if not spans:
        return ''
    top = max(s[0] for s in spans)
    return ' '.join(t for size, y, t in sorted(spans, key=lambda s: s[1]) if size >= top - 0.5)[:300]


def identify(path, size, idx):
    import fitz
    by_doi, by_title = idx
    rec = dict(path=path, bytes=size)
    try:
        h = hashlib.sha256()
        data = bytearray()
        with open(path, 'rb') as f:
            while True:
                b = f.read(8 << 20)
                if not b:
                    break
                h.update(b)
                if len(data) < 300 << 20:
                    data += b
        rec['sha256'] = h.hexdigest(); rec['bytes'] = len(data) if len(data) < 300 << 20 else size
    except Exception as e:
        rec['error'] = 'read: ' + type(e).__name__
        return rec
    if not bytes(data[:1024]).lstrip().startswith(b'%PDF-'):
        rec['error'] = 'not a PDF (no %PDF- header)'
        return rec
    try:
        doc = fitz.open(stream=bytes(data), filetype='pdf')
        rec['pages'] = doc.page_count
        p1 = doc[0].get_text() if doc.page_count else ''
        meta = doc.metadata or {}
        try:
            xmp = doc.get_xml_metadata() or ''
        except Exception:
            xmp = ''
        title = first_title(doc[0]) if doc.page_count else ''
        doc.close()
    except Exception as e:
        rec['error'] = 'pymupdf: ' + str(e)[:120]
        return rec
    metatext = ' '.join(str(v) for v in meta.values() if v) + ' ' + xmp[:20000]
    dois = list(dict.fromkeys(ndoi(m) for m in DOI.findall(p1 + ' ' + metatext)))
    arx = ARX.search(p1[:3000])
    rec.update(dois=dois[:8], arxiv=arx.group(1) if arx else None, title_found=title or (meta.get('title') or '')[:300], meta_title=(meta.get('title') or '')[:300])
    years = {int(y) for y in YEAR.findall(p1[:6000])}
    for k in ('creationDate', 'modDate'):
        m = re.match(r'D:(\d{4})', meta.get(k) or '')
        if m:
            years.add(int(m.group(1)))
    if arx:
        years.add(2000 + int(arx.group(1)[:2]))
    words = set(re.split(r'[^a-z]+', unicodedata.normalize('NFKD', p1[:8000]).encode('ascii', 'ignore').decode().lower()))
    matches = {}
    for d in dois + (['10.48550/arxiv.' + arx.group(1)] if arx else []):
        for m in by_doi.get(d, []):
            matches.setdefault((m['school'], m['work_id']), dict(school=m['school'], work_id=m['work_id'], key=m['key'], rule='doi', doi=d))
    lines = [l.strip() for l in p1.splitlines() if l.strip()][:80]
    keys = {nt(title), nt(meta.get('title'))}
    for i in range(len(lines)):
        for j in range(i + 1, min(i + 7, len(lines) + 1)):
            k = nt(' '.join(lines[i:j]))
            if len(k) > 400:
                break
            keys.add(k); keys.add(re.sub(r'\d+$', '', k))
    for k in keys:
        if len(k) < 20:
            continue
        for m in by_title.get(k, []):
            ok_year = not m['year'] or any(abs(y - int(m['year'])) <= 1 for y in years)
            fam = [f for f in m['fam'] if f in words]
            if ok_year and fam:
                cur = matches.get((m['school'], m['work_id']))
                if cur:
                    cur['rule'] = 'doi+title'
                else:
                    matches[(m['school'], m['work_id'])] = dict(school=m['school'], work_id=m['work_id'], key=m['key'], rule='title', byline_found=fam[:3])
    rec['matches'] = list(matches.values())
    return rec


def main():
    i, n = int(sys.argv[1]), int(sys.argv[2])
    files = []
    for f in sorted((HERE / 'lists').glob('*.tsv')):
        for line in f.open():
            size, path = line.rstrip('\n').split('\t', 1)
            if zlib.crc32(path.encode()) % n == i:
                files.append((path, int(size), f.stem))
    idx = load_index()
    out = HERE / 'ident' / f'shard-{i:02d}.jsonl.gz'
    done = set()
    if out.exists():  # resumable: keep what an earlier run of this shard wrote
        try:
            for l in gzip.open(out, 'rt'):
                done.add(json.loads(l)['path'])
        except Exception:
            pass
    t0, k = time.time(), 0
    with gzip.open(out, 'at') as f:
        for path, size, src in files:
            if path in done:
                continue
            rec = identify(path, size, idx)
            rec['source_list'] = src
            f.write(json.dumps(rec) + '\n'); k += 1
            if k % 500 == 0:
                f.flush(); print(json.dumps(dict(shard=i, done=k, of=len(files), seconds=round(time.time() - t0))), flush=True)
    print(json.dumps(dict(shard=i, done=k, of=len(files), seconds=round(time.time() - t0), finished=True)), flush=True)


if __name__ == '__main__':
    main()
