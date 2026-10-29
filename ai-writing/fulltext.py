"""Full texts of every CS lab paper with a local copy, for the full-paper AI-writing and diversity study.

match    ai-writing/papers.jsonl.gz -> a stored copy by the coverage counter's rule (claude-homogenization's
         fulltext_store.catalog: catalog work id, the fulltext-push's <school>_oa_<W id>, DOI, normalized title)
reuse    a copy already extracted for the homogenization study (claude-homogenization-20261019/corpus/fulltext.sqlite)
extract  the rest with the same extractor (fulltext_store.extract: pdftotext, 60 pages; intro + body up to the last
         References heading)
paragraphs  the body split into paragraphs of 40-400 words (blank-line blocks, hyphenation undone, lines joined;
         captions, tables, equations and headers dropped by a printable-word ratio check)
-> ai-writing/fulltext.sqlite: texts(key PRIMARY KEY, school, path, kind, chars, intro zlib, body zlib, flags), paragraphs(key, i, text)
usage: fulltext.py [-j 24]
"""
import argparse, gzip, json, re, sqlite3, sys, zlib
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOM = Path('/n/fs/resemble/maxent-grpo/.research-sweeps/claude-homogenization-20261019')
sys.path.insert(0, str(HOM / 'tools'))
import fulltext_store as fs  # noqa: E402

WORDISH = re.compile(r'^[A-Za-z][A-Za-z\-\']*[.,;:]?$')


def paragraphs(body):
    body = re.sub(r'-\n(?=[a-z])', '', body.replace('\x0c', '\n'))
    out = []
    for block in re.split(r'\n\s*\n', body):
        t = re.sub(r'\s+', ' ', block).strip()
        w = t.split()
        if not (40 <= len(w) <= 400):
            continue
        if sum(bool(WORDISH.match(x)) for x in w) / len(w) < 0.7:  # tables, equations, reference lists
            continue
        out.append(t)
    return out


def main(j):
    papers = [json.loads(l) for l in gzip.open(HERE / 'papers.jsonl.gz', 'rt')]
    cats = {s: fs.catalog(s) for s in sorted({p['school'] for p in papers}) if (fs.FT / s / 'catalog.sqlite').exists()}
    want = {}
    for p in papers:
        c = cats.get(p['school']) or {}
        wid = p['key'].split(':', 1)[1]
        oaw = f"{p['school']}_oa_{(p.get('oa') or '').rsplit('/', 1)[-1]}"
        hit = c.get(wid) or c.get(oaw) or (c.get('doi:' + p['doi'].lower()) if p.get('doi') else None) or (c.get('t:' + fs.nt(p['title'])) if p.get('title') else None)
        if hit:
            want[p['key']] = (p['school'], hit[0], hit[1], p.get('title') or '')
    out = sqlite3.connect(HERE / 'fulltext.sqlite')
    out.execute('create table if not exists texts (key text primary key, school text, path text, kind text, chars int, intro blob, body blob, flags text)')
    out.execute('create table if not exists paragraphs (key text, i int, text text, primary key (key, i))')
    have = {r[0] for r in out.execute('select key from texts')}
    old = sqlite3.connect(f'file:{HOM}/corpus/fulltext.sqlite?mode=ro', uri=True)
    reused = 0; todo = []
    for k, (school, path, kind, title) in want.items():
        if k in have:
            continue
        r = old.execute('select intro, body, flags from texts where path=?', (path,)).fetchone()
        if r and r[1]:
            body = zlib.decompress(r[1]).decode()
            out.execute('insert or replace into texts values (?,?,?,?,?,?,?,?)', (k, school, path, kind, len(body), r[0], r[1], r[2]))
            out.executemany('insert or replace into paragraphs values (?,?,?)', [(k, i, t) for i, t in enumerate(paragraphs(body))]); reused += 1
        else:
            todo.append((k, school, path, kind, title))
    out.commit()
    print(json.dumps(dict(lab_papers=len(papers), with_copy=len(want), reused=reused, to_extract=len(todo))), flush=True)
    with ProcessPoolExecutor(j) as ex:
        for n, ((k, school, path, kind, title), res) in enumerate(zip(todo, ex.map(fs.extract, [(t[2], t[3], t[4]) for t in todo], chunksize=8))):
            _, _, s, flags = res
            if s:
                body = s.get('body') or ''
                out.execute('insert or replace into texts values (?,?,?,?,?,?,?,?)', (k, school, path, kind, len(body), zlib.compress((s.get('intro') or '').encode()),
                                                                                       zlib.compress(body.encode()), json.dumps(flags)))
                out.executemany('insert or replace into paragraphs values (?,?,?)', [(k, i, t) for i, t in enumerate(paragraphs(body))])
            if n % 500 == 0:
                out.commit(); print(json.dumps(dict(extracted=n, of=len(todo))), flush=True)
    out.commit()
    print(json.dumps(dict(texts=out.execute('select count(*) from texts').fetchone()[0], paragraphs=out.execute('select count(*) from paragraphs').fetchone()[0])))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('-j', type=int, default=24); main(ap.parse_args().j)
