"""Full run of the main / references / appendix split over every stored full-text copy (PLAN.md), one shard per job.

input   EMB/texts.sqlite fulltext(paper_id, school, path, kind, body ...)  (the dose pipeline's texts; ai_scores.sqlite passages are cut from these bodies)
        ai-writing/fulltext.sqlite texts(key, path, body)                    (the detector_v2 texts; passage_scores.jsonl.gz keys)
        the stored copy at STORES/<path>  (pdftotext up to 400 pages, or the XML)
output  <out>/shard-<i>.sqlite:
  sections(paper_id PK, key, school, path, kind, main zlib, appendix zlib, flags JSON, main_words, appendix_words, references_chars,
           appendix_found, appendix_position, appendix_rule, truncated, copy_missing, split_error, n_main_passages, n_appendix_passages,
           n_main_identical, n_old_passages)
  passage_tags(src, id, pidx, section, words)   src 'ai_scores' (id = paper_id, pidx of common.passages(texts.sqlite body)) or
           'detector_v2' (id = fulltext.sqlite key, pidx of common.passages(fulltext.sqlite body)); section main | appendix | references | unknown
  passages(paper_id, i, section, text_hash, words)   common.passages(main) then common.passages(appendix): the lists a main+appendix scorer cuts
A paper with a missing or unreadable copy keeps today's body as main (copy_missing / split_error) and all its passages are tagged main.
usage: run_split.py --texts TEXTS.sqlite --ft FULLTEXT.sqlite --shard I --nshards N --out DIR [-j 8] [--limit N]
"""
import argparse
import hashlib
import json
import sqlite3
import sys
import time
import zlib
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE.parent / 'diversity')); sys.path.insert(0, str(HERE.parent.parent / 'tools'))
import atlas_paths as P  # noqa: E402
import fulltext_sections as S  # noqa: E402
from common import passages  # noqa: E402  (the splitter the detector and the dose scores use)

K = 8


def shingles(text):
    w = text.split()
    return {' '.join(w[i:i + K]) for i in range(0, max(1, len(w) - K + 1))}


def tag(plist, sets):
    """Section of each passage: the part holding most of its 8-word shingles (>= half), else unknown."""
    out = []
    for p in plist:
        sh = shingles(p)
        best, n = 'unknown', 0
        for name, s in sets:
            c = len(sh & s)
            if c > n:
                best, n = name, c
        out.append(best if n * 2 >= len(sh) else 'unknown')
    return out


def one(job):
    paper_id, key, school, path, kind, old_body, ft_body = job
    r = S.split_file(P.STORES / path, kind)
    flags = {}
    err = r.get('error')
    if err:
        main, app, refs = old_body or ft_body or '', '', ''
        flags = dict(appendix_found=False)
    else:
        main, app, refs, flags = r['main'], r['appendix'], r['references'], r['flags']
    rec = dict(paper_id=paper_id, key=key, school=school, path=path, kind=kind, err=err, flags=flags, main=main, appendix=app, refs_chars=len(refs))
    pm, pa = passages(main), passages(app) if app else []
    rec['new'] = [('main', p) for p in pm] + [('appendix', p) for p in pa]
    sets = None if err else [('main', shingles(main)), ('appendix', shingles(app) if app else set()), ('references', shingles(refs) if refs else set())]
    tags = {}
    for src, ident, body in (('ai_scores', paper_id, old_body), ('detector_v2', key, ft_body)):
        if not body or ident is None:
            continue
        pl = passages(body)
        tags[src] = (ident, [(len(p.split())) for p in pl], ['main'] * len(pl) if err else tag(pl, sets), pl)
    rec['tags'] = {s: (i, w, t) for s, (i, w, t, _) in tags.items()}
    ref = tags.get('ai_scores') or tags.get('detector_v2')
    rec['n_old'] = len(ref[3]) if ref else 0
    rec['n_identical'] = len(set(ref[3]) & set(pm)) if ref else 0
    rec['n_main'], rec['n_app'] = len(pm), len(pa)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--texts', required=True); ap.add_argument('--ft', required=True)
    ap.add_argument('--shard', type=int, default=0); ap.add_argument('--nshards', type=int, default=1)
    ap.add_argument('--out', required=True); ap.add_argument('-j', type=int, default=8); ap.add_argument('--limit', type=int)
    a = ap.parse_args()
    t0 = time.time()
    tx = sqlite3.connect(f'file:{a.texts}?mode=ro', uri=True)
    ft = sqlite3.connect(f'file:{a.ft}?mode=ro', uri=True)
    key_of = {}
    for k, path in ft.execute('select key, path from texts'):
        key_of.setdefault(path, k)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    dst = out / f'shard-{a.shard}.sqlite'
    tmp = Path(f'/tmp/split-{a.shard}-{time.time_ns()}.sqlite')
    db = sqlite3.connect(tmp)
    db.executescript('''create table sections (paper_id text primary key, key text, school text, path text, kind text, main blob, appendix blob, flags text, main_words int,
        appendix_words int, references_chars int, appendix_found int, appendix_position text, appendix_rule text, truncated int, copy_missing int, split_error text,
        n_main_passages int, n_appendix_passages int, n_main_identical int, n_old_passages int);
        create table passage_tags (src text, id text, pidx int, section text, words int);
        create table passages (paper_id text, i int, section text, text_hash text, words int);''')

    def jobs():
        n = 0
        for rid, paper_id, school, path, kind, body in tx.execute('select rowid, paper_id, school, path, kind, body from fulltext where rowid % ? = ?', (a.nshards, a.shard)):
            key = key_of.get(path)
            ftb = None
            if key:
                row = ft.execute('select body from texts where key=?', (key,)).fetchone()
                ftb = zlib.decompress(row[0]).decode('utf-8', 'ignore') if row and row[0] else None
            old = zlib.decompress(body).decode('utf-8', 'ignore') if body else None
            yield (paper_id, key, school, path, kind, old, ftb)
            n += 1
            if a.limit and n >= a.limit:
                return
    done = 0
    with ProcessPoolExecutor(a.j) as ex:
        for rec in ex.map(one, jobs(), chunksize=4):
            f = rec['flags']; err = rec['err']
            db.execute('insert into sections values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (
                rec['paper_id'], rec['key'], rec['school'], rec['path'], rec['kind'], zlib.compress(rec['main'].encode(), 6), zlib.compress(rec['appendix'].encode(), 6),
                json.dumps(f), len(rec['main'].split()), len(rec['appendix'].split()), rec['refs_chars'], int(bool(f.get('appendix_found'))), f.get('appendix_position'),
                f.get('appendix_rule'), int(bool(f.get('truncated'))), int(err == 'missing'), err if err != 'missing' else None, rec['n_main'], rec['n_app'], rec['n_identical'], rec['n_old']))
            for src, (ident, words, tg) in rec['tags'].items():
                db.executemany('insert into passage_tags values (?,?,?,?,?)', [(src, ident, i, t, w) for i, (w, t) in enumerate(zip(words, tg))])
            db.executemany('insert into passages values (?,?,?,?,?)', [(rec['paper_id'], i, s, hashlib.sha1(p.encode()).hexdigest()[:16], len(p.split())) for i, (s, p) in enumerate(rec['new'])])
            done += 1
            if done % 1000 == 0:
                db.commit(); print(json.dumps(dict(shard=a.shard, done=done, seconds=round(time.time() - t0))), flush=True)
    db.execute('create index pt on passage_tags (src, id)'); db.execute('create index pp on passages (paper_id)')
    db.commit(); db.close()
    import shutil
    shutil.copy2(tmp, dst.with_suffix('.tmp')); dst.with_suffix('.tmp').rename(dst); tmp.unlink()
    print(json.dumps(dict(shard=a.shard, finished=done, seconds=round(time.time() - t0), out=str(dst))))


if __name__ == '__main__':
    main()
