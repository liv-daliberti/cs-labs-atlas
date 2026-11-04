"""The embedding store: parts while a run is going, one container per model x school x text kind once merged.

Layout (EMB = ecommon.EMB):
  EMB/parts/<model>/<kind>/part_<job>_<seq>.npz     a run's finished chunk (atomic rename); a killed job loses at most one chunk
  EMB/<model>/<school>/<kind>.npz                   the container: arrays below
  EMB/<model>/<school>/<kind>.index.sqlite          papers(paper_id PK, row, off, n, ntok, text_hash), meta(key, value)
kind: 'abstract' (one vector per paper) or 'fulltext' (one vector per chunk plus the per-paper mean).
Container arrays: ids (str), hashes (str), n (int32 vectors per paper), ntok (int32 tokens embedded), off (int64, P+1 offsets into X),
  M (float16 P x d: the vector for 'abstract', the mean over chunks for 'fulltext'), X (float16 chunk vectors, 'fulltext' only),
  sp_ptr / sp_idx / sp_val (optional CSR of lexical weights per paper, BGE-M3: token id -> weight, max over chunks).
A paper is stored once, under its home school (the first school, in ecommon.SCHOOLS order, whose lab papers include it);
its other schools are in universe.sqlite (lab_papers). The text hash binds a vector to the text it came from.
numpy and sqlite3 only.
"""
import json
import sqlite3
from pathlib import Path

import numpy as np

import ecommon as C

KINDS = ('abstract', 'fulltext')


def part_dir(model, kind, emb=None):
    return Path(emb or C.EMB) / 'parts' / model / kind


def container_path(model, school, kind, emb=None):
    return Path(emb or C.EMB) / model / school / f'{kind}.npz'


def write_part(path, ids, hashes, n, X, M=None, ntok=None, sparse=None):
    """One finished chunk of a run. X: float16 (sum(n) x d) vectors in paper order; M: float16 (P x d) per-paper vector (fulltext)."""
    n = np.asarray(n, np.int32)
    assert len(ids) == len(hashes) == len(n) and X.shape[0] == int(n.sum())
    arrs = dict(ids=np.array(ids), hashes=np.array(hashes), n=n, X=np.asarray(X, np.float16),
                ntok=np.asarray(ntok if ntok is not None else np.zeros(len(ids)), np.int32))
    if M is not None:
        arrs['M'] = np.asarray(M, np.float16)
    if sparse is not None:
        arrs.update(sp_ptr=np.asarray(sparse[0], np.int64), sp_idx=np.asarray(sparse[1], np.int32), sp_val=np.asarray(sparse[2], np.float16))
    C.atomic_write(path, lambda t: np.savez(open(t, 'wb'), **arrs))


def part_files(model, kind, emb=None):
    d = part_dir(model, kind, emb)
    return sorted(d.glob('part_*.npz')) if d.exists() else []


def part_ids(path):
    with np.load(path) as Z:
        return [str(x) for x in Z['ids']], [str(x) for x in Z['hashes']]


def done_map(model, kind, emb=None):
    """{paper id: text hash} of everything already embedded: unmerged parts and the merged containers (their index files)."""
    out = {}
    base = Path(emb or C.EMB) / model
    if base.exists():
        for idx in sorted(base.glob(f'*/{kind}.index.sqlite')):
            db = sqlite3.connect(f'file:{idx}?mode=ro', uri=True)
            out.update(db.execute('select paper_id, text_hash from papers'))
            db.close()
    for p in part_files(model, kind, emb):
        out.update(zip(*part_ids(p)))
    return out


def _view(Z, kind, container):
    """A part or a container as one dict: ids, hashes, n, ntok, off, X (all vectors), M (per paper), sp (CSR triple or None)."""
    d = {k: Z[k] for k in Z.files}
    n = d['n']
    off = np.concatenate([[0], np.cumsum(n)]).astype(np.int64)
    if container and kind == 'abstract':
        X = M = d['M']
    else:
        X = d['X']
        M = d['M'] if 'M' in d else (X if kind == 'abstract' else None)
        if M is None:
            M = np.vstack([X[off[r]:off[r + 1]].astype(np.float32).mean(0) for r in range(len(n))]).astype(np.float16)
    sp = (d['sp_ptr'], d['sp_idx'], d['sp_val']) if 'sp_ptr' in d else None
    return dict(ids=[str(x) for x in d['ids']], hashes=[str(x) for x in d['hashes']], n=n, ntok=d['ntok'], off=off, X=X, M=M, sp=sp)


def _write_container(model, school, kind, rows, meta, emb=None):
    """rows: [(view, row)] in the order to store."""
    ids = [v['ids'][r] for v, r in rows]
    hashes = [v['hashes'][r] for v, r in rows]
    n = np.array([int(v['n'][r]) for v, r in rows], np.int32)
    ntok = np.array([int(v['ntok'][r]) for v, r in rows], np.int32)
    off = np.concatenate([[0], np.cumsum(n)]).astype(np.int64)
    arrs = dict(ids=np.array(ids), hashes=np.array(hashes), n=n, ntok=ntok, off=off, M=np.vstack([v['M'][r] for v, r in rows]).astype(np.float16))
    if kind == 'fulltext':
        arrs['X'] = np.vstack([v['X'][v['off'][r]:v['off'][r + 1]] for v, r in rows]).astype(np.float16)
    if all(v['sp'] is not None for v, _ in rows):
        pieces = [(v['sp'][1][v['sp'][0][r]:v['sp'][0][r + 1]], v['sp'][2][v['sp'][0][r]:v['sp'][0][r + 1]]) for v, r in rows]
        arrs['sp_ptr'] = np.concatenate([[0], np.cumsum([len(a) for a, _ in pieces])]).astype(np.int64)
        arrs['sp_idx'] = np.concatenate([a for a, _ in pieces]).astype(np.int32)
        arrs['sp_val'] = np.concatenate([b for _, b in pieces]).astype(np.float16)
    path = container_path(model, school, kind, emb)
    C.atomic_write(path, lambda t: np.savez(open(t, 'wb'), **arrs))

    def idx(t):
        db = sqlite3.connect(t)
        db.execute('create table papers (paper_id text primary key, row int, off int, n int, ntok int, text_hash text)')
        db.execute('create table meta (key text primary key, value text)')
        db.executemany('insert into papers values (?,?,?,?,?,?)', [(i, r, int(off[r]), int(n[r]), int(ntok[r]), hashes[r]) for r, i in enumerate(ids)])
        info = dict(meta, school=school, kind=kind, papers=len(ids), dim=int(arrs['M'].shape[1]), merged_at=C.now())
        db.executemany('insert into meta values (?,?)', [(k, json.dumps(v)) for k, v in info.items()])
        db.commit(); db.close()
    C.atomic_write(path.with_name(f'{kind}.index.sqlite'), idx)


def merge(model, kind, school_of, meta, emb=None, keep_parts=False):
    """Fold the parts and the school containers already there into one container per home school (`school_of`: paper id -> school).
    A later part wins over an earlier one and over a container row for the same paper. Papers with no home school are counted
    and dropped. Parts are removed once the containers are in place (unless keep_parts). Returns {school: papers}."""
    parts = part_files(model, kind, emb)
    base = Path(emb or C.EMB) / model
    old = sorted(base.glob(f'*/{kind}.npz')) if base.exists() else []
    latest, views, dropped = {}, [], 0
    for p, container in [(p, True) for p in old] + [(p, False) for p in parts]:
        with np.load(p) as Z:
            v = _view(Z, kind, container)
        views.append(v)
        for r, i in enumerate(v['ids']):
            latest[i] = (len(views) - 1, r)
    by_school = {}
    for i, (vi, r) in latest.items():
        s = school_of.get(i)
        if s is None:
            dropped += 1
            continue
        by_school.setdefault(s, []).append((i, views[vi], r))
    out = {}
    for s in sorted(by_school):
        rows = [(v, r) for _, v, r in sorted(by_school[s], key=lambda t: t[0])]
        _write_container(model, s, kind, rows, meta, emb)
        out[s] = len(rows)
    if not keep_parts:
        for p in parts:
            p.unlink()
    C.log(merged=model, kind=kind, parts=len(parts), schools=out, dropped_no_school=dropped)
    return out


def load(model, school, kind, chunks=False, emb=None):
    """dict(ids, hashes, n, ntok, off, M[, X][, sp_ptr, sp_idx, sp_val]) of a merged container."""
    with np.load(container_path(model, school, kind, emb)) as Z:
        return {k: Z[k] for k in Z.files if chunks or k != 'X'}


def meta(model, school, kind, emb=None):
    db = sqlite3.connect(f'file:{container_path(model, school, kind, emb).with_name(kind + ".index.sqlite")}?mode=ro', uri=True)
    out = {k: json.loads(v) for k, v in db.execute('select key, value from meta')}
    db.close()
    return out
