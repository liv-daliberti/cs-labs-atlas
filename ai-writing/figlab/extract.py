"""Figures out of lab-paper PDFs (PyMuPDF), stored as small PNG crops in one SQLite file per shard.

A figure is a region of drawn content on a page: the bounding boxes of embedded images and of vector drawings
(page.get_drawings, which carry most CS plots and diagrams) are merged when they lie within GAP points of each other,
and a merged region is kept when it covers >= 2% of the page and is >= 15% of the page wide and >= 6% high. Text
lines inside the region stay in the crop (axis labels and legends are part of the figure). Regions that are table
rules (only horizontal lines, no images) are dropped. A caption 'Figure N' / 'Fig. N' within 80 points below or above
the region is recorded, not required. At most MAX_PAGES pages and MAX_FIGS figures per paper; the crop is rendered at
150 dpi and its shorter side scaled to 256 pixels.
-> data/figures-<shard>.sqlite: figures(key, school, page, idx, x0, y0, x1, y1, caption, png) and papers(key, n_pages,
   n_figs, error); rerunning skips papers already in the shard
usage: extract.py [--limit N] [--shard i --of n] [--keys FILE]
"""
import argparse, hashlib, os, gzip, io, json, re, signal, sqlite3, sys, time
from pathlib import Path

import pymupdf
from PIL import Image

HERE = Path(__file__).resolve().parent
DATA = Path(os.environ.get('FIGLAB_DATA', HERE / 'data'))  # a mini run uses its own folder
GAP, MAX_PAGES, MAX_FIGS, DPI, SIDE, PAPER_SECONDS = 12, 40, 30, 150, 256, 120  # a drawing-heavy PDF stops after 120 s
CAPTION = re.compile(r'^\s*(fig(ure)?\.?)\s*\d+', re.I)


def merge(rects, gap=GAP):
    rects = [pymupdf.Rect(r) for r in rects if r.is_valid and not r.is_empty]
    changed = True
    while changed:
        changed = False
        out = []
        for r in rects:
            for i, o in enumerate(out):
                g = pymupdf.Rect(o.x0 - gap, o.y0 - gap, o.x1 + gap, o.y1 + gap)
                if g.intersects(r):
                    out[i] = o | r; changed = True; break
            else:
                out.append(r)
        rects = out
    return rects


def page_figures(page):
    W, Hh = page.rect.width, page.rect.height
    imgs = [pymupdf.Rect(b['bbox']) for b in page.get_text('dict')['blocks'] if b.get('type') == 1]
    draws = []
    for d in page.get_drawings():
        r = pymupdf.Rect(d['rect'])
        if r.width < 2 and r.height < 2:
            continue
        horiz = all(it[0] == 'l' and abs(it[1].y - it[2].y) < 0.5 for it in d['items'])
        draws.append((r, horiz))
    regions = merge(imgs + [r for r, _ in draws])
    caps = [(pymupdf.Rect(b[:4]), b[4].strip()) for b in page.get_text('blocks') if CAPTION.match(b[4] or '')]
    out = []
    for g in regions:
        g = g & page.rect
        if g.width < 0.15 * W or g.height < 0.06 * Hh or g.width * g.height < 0.02 * W * Hh:
            continue
        inside = [h for r, h in draws if g.contains(r)]
        if inside and all(inside) and not any(g.intersects(i) for i in imgs):
            continue  # table rules
        cap = next((t for r, t in caps if (0 <= r.y0 - g.y1 <= 80 or 0 <= g.y0 - r.y1 <= 80) and r.x0 < g.x1 and r.x1 > g.x0), None)
        out.append((g, cap))
    return out


def crop_png(page, rect):
    pix = page.get_pixmap(clip=rect, dpi=DPI, alpha=False)
    im = Image.open(io.BytesIO(pix.tobytes('png'))).convert('RGB')
    s = SIDE / min(im.size)
    if s < 1:
        im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.BICUBIC)
    b = io.BytesIO(); im.save(b, 'PNG', optimize=True)
    return b.getvalue()


def open_db(path):
    db = sqlite3.connect(path)
    db.execute('create table if not exists figures(key text, school text, page int, idx int, x0 real, y0 real, x1 real, y1 real, caption text, png blob, primary key(key, page, idx))')
    db.execute('create table if not exists papers(key text primary key, school text, n_pages int, n_figs int, error text, seconds real)')
    return db


def run(rows, db):
    done = {k for (k,) in db.execute('select key from papers')}
    for x in rows:
        if x['key'] in done:
            continue
        t = time.time(); n_pages = n = 0; err = None
        signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError(f'over {PAPER_SECONDS} s')))
        signal.alarm(PAPER_SECONDS)
        try:
            doc = pymupdf.open(x['pdf'])
            n_pages = doc.page_count
            for pno in range(min(n_pages, MAX_PAGES)):
                page = doc[pno]
                for i, (g, cap) in enumerate(page_figures(page)):
                    if n >= MAX_FIGS:
                        break
                    db.execute('insert or replace into figures values (?,?,?,?,?,?,?,?,?,?)',
                               (x['key'], x['school'], pno, i, g.x0, g.y0, g.x1, g.y1, (cap or '')[:300], crop_png(page, g)))
                    n += 1
        except Exception as e:  # damaged or encrypted PDFs are recorded, not fatal
            err = f'{type(e).__name__}: {e}'[:300]
        finally:
            signal.alarm(0)
        db.execute('insert or replace into papers values (?,?,?,?,?,?)', (x['key'], x['school'], n_pages, n, err, round(time.time() - t, 2)))
        db.commit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int); ap.add_argument('--shard', type=int, default=0); ap.add_argument('--of', type=int, default=1)
    ap.add_argument('--keys', help='a file of paper keys (one per line) to extract instead of the whole manifest')
    a = ap.parse_args()
    rows = [json.loads(l) for l in gzip.open(DATA / 'manifest.jsonl.gz', 'rt')]
    if a.keys:
        want = set(Path(a.keys).read_text().split())
        rows = [x for x in rows if x['key'] in want]
    # shard by a hash of the paper key: a grown manifest keeps every paper in its shard, so reruns only add new papers
    rows = [x for x in rows if int(hashlib.md5(x['key'].encode()).hexdigest(), 16) % a.of == a.shard][:a.limit]
    db = open_db(DATA / f'figures-{a.shard:02d}.sqlite')
    run(rows, db)
    n = db.execute('select count(*), sum(n_figs), sum(error is not null) from papers').fetchone()
    print(json.dumps(dict(shard=a.shard, papers=n[0], figures=n[1], errors=n[2])))


if __name__ == '__main__':
    main()
