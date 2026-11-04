"""The texts that are embedded: one abstract and one full-text body per paper, with hashes, in EMB/texts.sqlite.

abstracts   every paper with an abstract of >= MIN_ABSTRACT_WORDS words: the OpenAlex abstract (oa_fields.sqlite, rebuilt from the bulk
            snapshot's abstract_inverted_index), else the one the API pass of ai-writing/build_corpus.py cached in ai-writing/abstracts.sqlite.
            Never the API here. -> abstracts(paper_id PK, title, abstract, src, words, text_hash)   text_hash = hash of title + abstract
fulltext    every paper with a local copy (the stores' catalogs, matched exactly as ai-writing/fulltext.py does: catalog work id,
            <school>_oa_<W id>, DOI, normalized title; the home school's copy first). The body text is the existing extraction
            (vendor fulltext_store: pdftotext 60 pages, intro + body to the last References heading, <= 300,000 characters): reused from
            ai-writing/fulltext.sqlite and the homogenization corpus where the same file was extracted, extracted here for the rest.
            -> fulltext(paper_id PK, school, path, kind, chars, words, usable, body zlib, flags, text_hash)
            usable = common.usable_text's rule (>= 1000 words after the References cut; a PDF must show the paper's title on its first page).
usage: texts.py abstracts | texts.py fulltext [-j N] | texts.py status
"""
import json
import os
import sqlite3
import sys
import time
import zlib
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import ecommon as C
import universe as U

P = C.P
sys.path.append(str(P.vendor('homogenization_tools')))   # the study's extractor, vendored (tools/vendor_sync.py)
MIN_WORDS_FT = 1000


def usable(kind, words, flags):
    return words >= MIN_WORDS_FT and (kind != 'pdf' or bool(flags.get('title_found', True)))


def connect(path=None, ro=False):
    path = Path(path or C.TEXTS_DB)
    if ro:
        return sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=600)
    db.execute('create table if not exists abstracts (paper_id text primary key, title text, abstract text, src text, words int, text_hash text)')
    db.execute('create table if not exists fulltext (paper_id text primary key, school text, path text, kind text, chars int, words int, usable int,'
               ' body blob, flags text, text_hash text)')
    return db


def abstract_rows(papers, oa_fields_db=None, api_db=None):
    """[(paper_id, title, abstract, src, words, hash)] for papers with an abstract. oa_fields_db/api_db: sqlite paths (None = skip)."""
    oa = {}
    if oa_fields_db and Path(oa_fields_db).exists():
        d = sqlite3.connect(f'file:{oa_fields_db}?mode=ro', uri=True)
        oa = {i: a for i, a in d.execute('select id, abstract from works where abstract is not null')}
        d.close()
    api = {}
    if api_db and Path(api_db).exists():
        import oa_fields
        d = sqlite3.connect(f'file:{api_db}?mode=ro', uri=True)
        for k, b in d.execute('select oa, inverted from abstracts'):
            t = oa_fields.abstract_text(json.loads(zlib.decompress(b)))
            if t:
                api[k.rsplit('/', 1)[-1]] = t
        d.close()
    out = []
    for pid, o, title, year, home in papers:
        w = (o or '').rsplit('/', 1)[-1]
        src, ab = ('oa_snapshot', oa.get(w)) if oa.get(w) else (('api_cache', api.get(w)) if api.get(w) else (None, None))
        if ab and len(ab.split()) >= C.MIN_ABSTRACT_WORDS:
            out.append((pid, title or '', ab, src, len(ab.split()), C.text_hash((title or '') + '\n' + ab)))
    return out


def build_abstracts():
    papers = U.load_papers()
    rows = abstract_rows(papers, C.OA_FIELDS, P.AI_WRITING / 'abstracts.sqlite')
    db = connect()
    db.execute('delete from abstracts')
    db.executemany('insert into abstracts values (?,?,?,?,?,?)', rows)
    db.commit()
    by = {}
    home = {p[0]: p[4] for p in papers}
    for r in rows:
        by[(home[r[0]], r[3])] = by.get((home[r[0]], r[3]), 0) + 1
    C.log(abstracts=len(rows), papers=len(papers), by_school_src={f'{a}/{b}': n for (a, b), n in sorted(by.items())})


# ---------------------------------------------------------------- full texts
def match_copies(schools):
    """{paper_id: (school, path, kind, title)}: the stored copy of each paper, the home school's first."""
    import fulltext_store as fs
    want = {}
    for s in schools:
        if not (fs.FT / s / 'catalog.sqlite').exists():
            C.log(no_store=s); continue
        cat = fs.catalog(s)
        n = 0
        for r in U.rows_of(s):
            pid = U.paper_id(r, s)
            if pid in want:
                continue
            wid, oaw = r.get('work') or '', f"{s}_oa_{(r.get('oa') or '').rsplit('/', 1)[-1]}"
            hit = cat.get(wid) or cat.get(oaw) or (cat.get('doi:' + r['doi'].lower()) if r.get('doi') else None) or (
                cat.get('t:' + fs.nt(r['title'])) if r.get('title') else None)
            if hit:
                want[pid] = (s, hit[0], hit[1], r.get('title') or ''); n += 1
        C.log(school=s, copies_matched=n)
    return want


def _old_bodies():
    """{path: (body text, flags)} readers for the extractions that already exist (by file path)."""
    srcs = []
    a = P.AI_WRITING / 'fulltext.sqlite'
    if a.exists():
        srcs.append(('ai', sqlite3.connect(f'file:{a}?mode=ro', uri=True, timeout=600), 'select body, flags from texts where path=?'))
    h = P.HOMOGENIZATION_STUDY / 'corpus' / 'fulltext.sqlite'
    if h.exists():
        srcs.append(('hom', sqlite3.connect(f'file:{h}?mode=ro', uri=True, timeout=600), 'select body, flags from texts where path=?'))
    return srcs


def build_fulltext(workers):
    import fulltext_store as fs
    want = match_copies(C.SCHOOLS)
    db = connect()
    have = {p: pa for p, pa in db.execute('select paper_id, path from fulltext')}
    todo = {p: v for p, v in want.items() if have.get(p) != v[1]}
    C.log(papers_with_copy=len(want), already=len(want) - len(todo), todo=len(todo))
    old = _old_bodies()
    # an index on path makes the reuse lookups cheap (ai-writing/fulltext.sqlite has none: build it in memory by one scan)
    idx = {}
    for name, d, _ in old:
        if name == 'ai':
            idx[name] = {p: r for r, p in d.execute('select rowid, path from texts')}
    reused, jobs = 0, []
    for pid, (s, path, kind, title) in todo.items():
        got = None
        for name, d, q in old:
            if name == 'ai':
                r = idx['ai'].get(path)
                row = d.execute('select body, flags from texts where rowid=?', (r,)).fetchone() if r else None
            else:
                row = d.execute(q, (path,)).fetchone()
            if row and row[0]:
                got = row; break
        if got:
            body = zlib.decompress(got[0]).decode('utf-8', 'ignore'); flags = json.loads(got[1] or '{}')
            _put(db, pid, s, path, kind, body, flags); reused += 1
        else:
            jobs.append((pid, s, path, kind, title))
        if reused % 2000 == 0:
            db.commit()
    db.commit()
    C.log(reused=reused, to_extract=len(jobs))
    t0 = time.time()
    with ProcessPoolExecutor(workers) as ex:
        for n, ((pid, s, path, kind, title), res) in enumerate(zip(jobs, ex.map(fs.extract, [(j[2], j[3], j[4]) for j in jobs], chunksize=8))):
            _, _, sec, flags = res
            if sec:
                _put(db, pid, s, path, kind, sec.get('body') or '', flags)
            else:
                _put(db, pid, s, path, kind, '', dict(flags, failed=True))
            if n % 500 == 499:
                db.commit(); C.log(extracted=n + 1, of=len(jobs), per_s=round((n + 1) / (time.time() - t0), 1))
    db.commit()
    C.log(fulltext=db.execute('select count(*) from fulltext').fetchone()[0], usable=db.execute('select count(*) from fulltext where usable=1').fetchone()[0])


def _put(db, pid, school, path, kind, body, flags):
    words = len(body.split())
    db.execute('insert or replace into fulltext values (?,?,?,?,?,?,?,?,?,?)',
               (pid, school, path, kind, len(body), words, int(usable(kind, words, flags)), zlib.compress(body.encode('utf-8', 'ignore'), 6) if body else None,
                json.dumps(flags), C.text_hash(body)))


def status():
    if not C.TEXTS_DB.exists():
        C.log(texts='missing'); return
    db = connect(ro=True)
    C.log(abstracts=db.execute('select count(*) from abstracts').fetchone()[0], fulltext=db.execute('select count(*) from fulltext').fetchone()[0],
          usable=db.execute('select count(*) from fulltext where usable=1').fetchone()[0])


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:1] == ['abstracts']:
        build_abstracts()
    elif a[:1] == ['fulltext']:
        build_fulltext(int(a[a.index('-j') + 1]) if '-j' in a else (os.cpu_count() or 8))
    elif a[:1] == ['status']:
        status()
    else:
        raise SystemExit(__doc__)
