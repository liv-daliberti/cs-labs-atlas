"""AI dose x knowledge entropy on every school with downloads (owner 2026-11-23).

Owner: "for all 32 schools where we have downloads make sure we can get the AI detector run over them + do the knowledge entropy stuff over all
papers. THEN a continuous variable for the amount of AI vs the knowledge entropy in the way we did it before (cosine and the default)."

One uniform build over every school store (the 12 study schools are rebuilt too: their copies grew since 2026-11-08, and the overlap with the
sealed v3 table is the consistency check). Nothing here writes to the study snapshots, the canonical embedding store or detector_v3/results.

stages (WORK = studies/homogenization/work/entropy32-<id>/; every stage restartable)
  list      CPU, login-light: every lab paper 2016-2025 of the 32 schools (hierarchy/<school>/derived/lab_papers.jsonl.gz), one row per work
            (OpenAlex id, else atlas work id), its schools and labs (school::pi), and its stored copy, matched exactly as study_delta_build.py
            does (catalog work id, <school>_oa_<W>, DOI, normalised title; home school first) -> papers.parquet (shard = sha1(k) % NSHARDS)
  sections  CPU array task: main / appendix split of each copy of the shard (sections/run_split.one, the v3 rescoring's splitter), built in
            node-local /tmp, copied back once -> sections/sections-<i>.sqlite. Stops starting work after --budget s and saves what it has;
            the next run continues (done ids are skipped).
  gpu       A5000 array task (needs sections-<i> complete): (a) detector v3 'all' on every main and appendix passage, the same operating point,
            abstain rule and z as study_delta_build.stage_score / detector_v3/score_sections.py; (b) SPECTER2 base on the MAIN body (the text
            before the references, appendix excluded), exactly embeddings/embed.py's full-text recipe (512-token windows, cap 64, CLS, mean of
            the windows) -> gpu/scores-<i>.sqlite, gpu/emb-<i>.npz. Checkpoints every part; a rerun resumes.
  paper     CPU: per-paper table (ai_share_main, ai_share_main_appendix, abstained share, usable = main >= 1,000 words, v3's rule) joined to the
            paper list -> papers_scored.parquet, X_specter2_base.npy (float16, rows = papers_scored order where has_emb), coverage.csv
  status    counts per stage and shard
usage: e32.py <stage> [--id 20261123] [--shard I] [--nshards 64] [-j 8] [--budget 3000]
"""
import argparse
import gzip
import hashlib
import json
import os
import shutil
import signal
import sqlite3
import sys
import time
import zlib
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / 'tools'))
import atlas_paths as P  # noqa: E402

MAIN_AIW = Path(os.environ.get('CS_ATLAS_CODE', '/n/fs/resemble/homogenizing-science/code')) / 'ai-writing'   # models + data: main checkout
STUDY12 = ['princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford', 'michigan', 'uchicago', 'gatech', 'harvard', 'jhu', 'washu']
FIRST, LAST = 2016, 2025
NSHARDS = 64


def schools():
    """The 12 study schools first (their order decides a shared paper's home school, as in the study), then every other store."""
    stores = sorted(p.name for p in Path(P.STORES).iterdir() if p.is_dir() and not p.name.startswith('_') and (p / 'catalog.sqlite').exists())
    have = [s for s in stores if Path(P.data('lab_papers.jsonl.gz', s)).exists()]   # a store still onboarding has no membership yet: it joins once it does
    if len(have) < len(stores):
        log(skipped_no_lab_papers=sorted(set(stores) - set(have)))
    stores = have
    return [s for s in STUDY12 if s in stores] + [s for s in stores if s not in STUDY12]


def work_dir(run_id):
    d = Path(P.HOMOGENIZATION_STUDY) / 'work' / f'entropy32-{run_id}'
    d.mkdir(parents=True, exist_ok=True)
    return d


def oa_short(x):
    return x.rsplit('/', 1)[-1] if isinstance(x, str) and x else None


def shard_of(k, n=NSHARDS):
    return int(hashlib.sha1(k.encode()).hexdigest()[:8], 16) % n


def log(**kw):
    print(json.dumps(dict(at=time.strftime('%H:%M:%S'), **kw)), flush=True)


# ---------------------------------------------------------------- list
def build_list(nshards):
    """Every lab paper 2016-2025 of the stores' schools with its stored copy (current catalogs) -> (DataFrame, schools)."""
    import pandas as pd
    sys.path.append(str(Path(P.VENDOR) / 'homogenization_tools'))
    import fulltext_store as fs
    S = schools()
    papers = {}
    for s in S:
        with gzip.open(P.data('lab_papers.jsonl.gz', s), 'rt') as f:
            for line in f:
                r = json.loads(line)
                y = r.get('year')
                if not y or not FIRST <= int(y) <= LAST:
                    continue
                oa = oa_short(r.get('oa'))
                k = oa or r.get('atlasWorkId') or (f"key:{s}:{r['work']}" if r.get('work') else None)
                if not k:
                    continue
                d = papers.setdefault(k, dict(k=k, oa=oa, paper_id=r.get('atlasWorkId') or (f'oa:{oa}' if oa else k), year=int(y), title=r.get('title') or '',
                                              doi=(r.get('doi') or '').lower() or None, schools=[], labs=[], rows=[]))
                if s not in d['schools']:
                    d['schools'].append(s)
                lab = f"{s}::{r.get('pi')}"
                if r.get('pi') and lab not in d['labs']:
                    d['labs'].append(lab)
                d['rows'].append((s, r.get('work') or '', f"{s}_oa_{oa or ''}"))
        log(school=s, papers_so_far=len(papers))
    order = {s: i for i, s in enumerate(S)}
    cats = {}
    out = []
    for k, d in papers.items():
        d['schools'].sort(key=order.get)
        d['home_school'] = d['schools'][0]
        hit, sc = None, None
        for s, wid, oaw in sorted(d['rows'], key=lambda x: order[x[0]]):
            if s not in cats:
                t0 = time.time()
                cats[s] = fs.catalog(s)
                log(catalog=s, keys=len(cats[s]), seconds=round(time.time() - t0))
            c = cats[s]
            hit = c.get(wid) or c.get(oaw) or (c.get('doi:' + d['doi']) if d['doi'] else None) or (c.get('t:' + fs.nt(d['title'])) if d['title'] else None)
            if hit:
                sc = s
                break
        out.append(dict(k=k, paper_id=d['paper_id'], oa=d['oa'], year=d['year'], title=d['title'], doi=d['doi'], home_school=d['home_school'],
                        schools=json.dumps(d['schools']), labs=json.dumps(d['labs']), n_labs=len(d['labs']), school_copy=sc,
                        path=hit[0] if hit else None, kind=hit[1] if hit else None, shard=shard_of(k, nshards)))
    return pd.DataFrame(out), S


def stage_list(a):
    df, S = build_list(a.nshards)
    w = work_dir(a.id)
    df.to_parquet(w / 'papers.parquet')
    cov = df.groupby('home_school').agg(papers=('k', 'size'), with_copy=('path', lambda x: int(x.notna().sum()))).reindex(S)
    cov.to_csv(w / 'copies_by_school.csv')
    (w / 'RUN.json').write_text(json.dumps(dict(id=a.id, nshards=a.nshards, schools=S, years=[FIRST, LAST], built=time.strftime('%Y-%m-%dT%H:%M:%S'),
                                                papers=len(df), with_copy=int(df.path.notna().sum())), indent=1))
    log(papers=len(df), with_copy=int(df.path.notna().sum()), schools=len(S))
    print(cov.to_string())


def load_shard(a, need_copy=True):
    import pandas as pd
    w = work_dir(a.id)
    n = json.loads((w / 'RUN.json').read_text())['nshards']
    df = pd.read_parquet(w / 'papers.parquet', columns=['k', 'paper_id', 'school_copy', 'path', 'kind', 'shard'])
    df = df[df['shard'] == a.shard % n]
    return df[df.path.notna()] if need_copy else df


# ---------------------------------------------------------------- sections
def _split(job):
    sys.path.insert(0, str(HERE.parent / 'sections'))
    import run_split as RS
    k, school, path, kind = job
    try:
        return RS.one((k, None, school, path, kind, None, None))
    except Exception as e:  # never lose a shard to one bad file
        return dict(paper_id=k, school=school, path=path, kind=kind, err=f'exception: {type(e).__name__}: {e}'[:300], flags={}, main='', appendix='', new=[])


SECTIONS_SQL = '''create table if not exists sections (k text primary key, school text, path text, kind text, main blob, appendix blob, flags text,
    main_words int, appendix_words int, appendix_found int, copy_missing int, split_error text, n_main_passages int, n_appendix_passages int);
    create table if not exists meta (key text primary key, value text);'''


def stage_sections(a):
    w = work_dir(a.id)
    (w / 'sections').mkdir(exist_ok=True)
    dst = w / 'sections' / f'sections-{a.shard}.sqlite'
    rows = load_shard(a)
    loc = Path(os.environ.get('TMPDIR') or '/tmp') / f'e32-sections-{a.shard}-{os.getpid()}.sqlite'
    if dst.exists():
        db = sqlite3.connect(f'file:{dst}?mode=ro', uri=True)
        if dict(db.execute('select key, value from meta')).get('complete') == '1':
            log(shard=a.shard, skip='complete'); return
        db.close()
        shutil.copyfile(dst, loc)
    db = sqlite3.connect(loc)
    db.executescript(SECTIONS_SQL)
    done = {r[0] for r in db.execute('select k from sections')}
    todo = [(r.k, r.school_copy, r.path, r.kind) for r in rows.itertuples() if r.k not in done]
    log(shard=a.shard, papers=len(rows), done=len(done), todo=len(todo))
    t0, n, stopped = time.time(), 0, False
    with ProcessPoolExecutor(a.j) as ex:
        for c0 in range(0, len(todo), 40 * a.j):
            if time.time() - t0 > a.budget:
                stopped = True; break
            for rec in ex.map(_split, todo[c0:c0 + 40 * a.j], chunksize=2):
                err = rec.get('err')
                f = rec.get('flags') or {}
                main_t, app = (rec['main'], rec['appendix']) if not err else ('', '')
                pm = sum(1 for s, _ in rec.get('new', []) if s == 'main') if not err else 0
                pa = sum(1 for s, _ in rec.get('new', []) if s == 'appendix') if not err else 0
                db.execute('insert or replace into sections values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (
                    rec['paper_id'], rec['school'], rec['path'], rec['kind'], zlib.compress(main_t.encode(), 6), zlib.compress(app.encode(), 6), json.dumps(f),
                    len(main_t.split()), len(app.split()), int(bool(f.get('appendix_found'))), int(err == 'missing'), err if err != 'missing' else None, pm, pa))
                n += 1
            db.commit()
            log(shard=a.shard, done=len(done) + n, of=len(rows), seconds=round(time.time() - t0))
    db.execute('insert or replace into meta values (?,?)', ('complete', '0' if stopped else '1'))
    db.commit(); db.close()
    tmp = dst.with_suffix('.tmp')
    shutil.copyfile(loc, tmp); tmp.replace(dst); loc.unlink()
    log(shard=a.shard, sections=len(done) + n, complete=not stopped, seconds=round(time.time() - t0))
    if stopped:
        sys.exit(75)   # EX_TEMPFAIL: the wrapper resubmits


# ---------------------------------------------------------------- gpu: detector v3 + SPECTER2 base on the main body
def stage_gpu(a):
    import numpy as np
    import torch
    w = work_dir(a.id)
    src = w / 'sections' / f'sections-{a.shard}.sqlite'
    sdb = sqlite3.connect(f'file:{src}?mode=ro', uri=True)
    if dict(sdb.execute('select key, value from meta')).get('complete') != '1':
        log(shard=a.shard, error='sections incomplete'); sys.exit(75)
    gdir = w / 'gpu'
    gdir.mkdir(exist_ok=True)
    out_sc, out_emb = gdir / f'scores-{a.shard}.sqlite', gdir / f'emb-{a.shard}.npz'
    marker = gdir / f'complete-{a.shard}'
    if marker.exists():
        log(shard=a.shard, skip='complete'); return
    # detector v3, exactly as study_delta_build.stage_score
    sys.path.insert(0, str(HERE.parent / 'detector_v3'))
    import v3common as V3
    import detector as D2
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    V = V3.V
    data = MAIN_AIW / 'detector_v3'
    op = json.load(open(data / 'results' / 'operating_point.json'))
    thr, cut = op['thr_z'], op['midcap_cut']
    tok = AutoTokenizer.from_pretrained(data / 'models' / 'all' / 'model')
    model = AutoModelForSequenceClassification.from_pretrained(data / 'models' / 'all' / 'model').cuda().eval()
    # SPECTER2 base, exactly as embeddings/embed.py (fulltext kind)
    sys.path.insert(0, str(HERE.parent / 'embeddings'))
    os.environ.setdefault('EMB_BUDGET_SCALE', '2')
    import embed as EM
    emb = EM.Embedder('specter2_base')
    loc = Path(os.environ.get('TMPDIR') or '/tmp') / f'e32-scores-{a.shard}-{os.getpid()}.sqlite'
    if out_sc.exists():
        shutil.copyfile(out_sc, loc)
    o = sqlite3.connect(loc)
    o.execute('create table if not exists scores (k text, i int, section text, words int, midcap real, z real, abstain int, flagged int)')
    o.execute('create table if not exists done (k text primary key, n_passages int, n_windows int, main_tokens int)')
    done = {r[0] for r in o.execute('select k from done')}
    E = dict(np.load(out_emb, allow_pickle=False)) if out_emb.exists() else dict(keys=np.array([], dtype='U64'), X=np.zeros((0, 768), np.float32))
    keys, Xs = list(E['keys']), [E['X']]
    todo = [r[0] for r in sdb.execute('select k from sections where main_words > 0 order by k') if r[0] not in done]
    log(shard=a.shard, todo=len(todo), done=len(done), gpu=torch.cuda.get_device_name(0))
    t0, last, PART = time.time(), None, 300

    def save():
        o.commit()
        tmp = out_sc.with_suffix('.tmp'); shutil.copyfile(loc, tmp); tmp.replace(out_sc)
        X = np.vstack(Xs).astype(np.float32)
        tmpe = gdir / f'emb-{a.shard}.tmp.npz'
        np.savez(tmpe, keys=np.array(keys, dtype='U64'), X=X); tmpe.replace(out_emb)

    for c0 in range(0, len(todo), PART):
        el = time.time() - t0
        if last and el + 1.3 * last > a.budget:
            save(); log(shard=a.shard, stopped_for_budget=True, remaining=len(todo) - c0); sys.exit(75)
        t1 = time.time()
        ks = todo[c0:c0 + PART]
        q = ','.join('?' * len(ks))
        rows, bodies = [], {}
        for k, m, ap_ in sdb.execute(f'select k, main, appendix from sections where k in ({q})', ks):
            mt = zlib.decompress(m).decode('utf-8', 'ignore') if m else ''
            at = zlib.decompress(ap_).decode('utf-8', 'ignore') if ap_ else ''
            bodies[k] = mt
            for i, (s, p) in enumerate([('main', x) for x in V.passages(mt)] + [('appendix', x) for x in (V.passages(at) if at else [])]):
                rows.append((k, i, s, p))
        if rows:
            p = D2.predict(model, tok, [V.norm(r[3]) for r in rows], bs=128)
            z = np.log(np.clip(p, 1e-300, None)) - np.log(np.clip(1 - p, 1e-300, None))
            batch = []
            for (k, i, s, t), zz in zip(rows, z):
                n_w = len(t.split()); mc = V.quality(t)['midcap']
                ab = int(n_w < op['abstain_words'] or mc > cut)
                batch.append((k, i, s, n_w, mc, float(zz), ab, int((not ab) and zz >= thr)))
            o.executemany('insert into scores values (?,?,?,?,?,?,?,?)', batch)
        seqs, owner, ntok = [], [], {}
        ek = [k for k in ks if bodies.get(k, '').strip()]
        for j, k in enumerate(ek):
            s, nt = emb.encode_body(bodies[k]); ntok[k] = nt
            seqs += s; owner += [j] * len(s)
        nwin = np.bincount(owner, minlength=len(ek)) if ek else np.zeros(0, int)
        if seqs:
            Vv, _ = emb.embed(seqs)
            off = np.concatenate([[0], np.cumsum(nwin)])
            M = np.vstack([Vv[off[j]:off[j + 1]].mean(0) if nwin[j] else np.full(768, np.nan, np.float32) for j in range(len(ek))])
            keep = nwin > 0
            keys += [k for k, kk in zip(ek, keep) if kk]; Xs.append(M[keep].astype(np.float32))
        npass = {}
        for r in rows:
            npass[r[0]] = npass.get(r[0], 0) + 1
        wmap = dict(zip(ek, nwin.tolist()))
        o.executemany('insert or replace into done values (?,?,?,?)', [(k, npass.get(k, 0), int(wmap.get(k, 0)), int(ntok.get(k, 0))) for k in ks])
        last = time.time() - t1
        if (c0 // PART) % 4 == 3:
            save()
        log(shard=a.shard, part=c0 // PART, papers=len(ks), passages=len(rows), windows=len(seqs), seconds=round(last), elapsed=round(time.time() - t0))
    save()
    o.close(); loc.unlink(missing_ok=True)
    marker.write_text(time.strftime('%Y-%m-%dT%H:%M:%S'))
    log(shard=a.shard, complete=True, minutes=round((time.time() - t0) / 60, 1))


# ---------------------------------------------------------------- incremental refresh (owner 2026-11-23: pick up new full texts)
def delta_dirs(base):
    root = Path(P.HOMOGENIZATION_STUDY) / 'work'
    return sorted((d for d in root.glob(f'entropy32-{base}-d*') if (d / 'RUN.json').exists()), key=lambda d: int(d.name.rsplit('-d', 1)[1]))


def run_dirs(base):
    return [work_dir(base)] + delta_dirs(base)


def stage_delta(a):
    """Re-read the catalogs; papers with a stored copy that no earlier round split (base or any delta) become the next delta round
    WORK-dN/papers.parquet (same stages: sections, gpu). The full current list goes to the base as papers_latest.parquet (paper stage uses it).
    Prints the new round id, or 'none' when nothing is new (fewer than --min-new papers)."""
    import math
    import pandas as pd
    base = work_dir(a.id)
    df, S = build_list(NSHARDS)
    done = set()
    for d in run_dirs(a.id):
        for f in sorted((d / 'sections').glob('sections-*.sqlite')):
            db = sqlite3.connect(f'file:{f}?mode=ro', uri=True)
            done |= {r[0] for r in db.execute('select k from sections')}
            db.close()
    tmp = base / 'papers_latest.tmp.parquet'
    df.to_parquet(tmp); tmp.replace(base / 'papers_latest.parquet')
    new = df[df.path.notna() & ~df.k.isin(done)].copy()
    if len(new) < a.min_new:
        log(delta='none', new=len(new), held=int(df.path.notna().sum()), processed=len(done)); print('DELTA=none'); return
    rnd = len(delta_dirs(a.id)) + 1
    did = f'{a.id}-d{rnd}'
    w = work_dir(did)
    n = max(1, math.ceil(len(new) / 2300))
    new['shard'] = [shard_of(k, n) for k in new.k]
    new.to_parquet(w / 'papers.parquet')
    (w / 'RUN.json').write_text(json.dumps(dict(id=did, base=a.id, round=rnd, nshards=n, schools=S, years=[FIRST, LAST], built=time.strftime('%Y-%m-%dT%H:%M:%S'),
                                                papers=len(new), with_copy=len(new)), indent=1))
    log(delta=did, new=len(new), shards=n, by_school=new.home_school.value_counts().to_dict())
    print(f'DELTA={did} NSHARDS={n}')


# ---------------------------------------------------------------- paper table
def stage_paper(a):
    import numpy as np
    import pandas as pd
    w = work_dir(a.id)
    latest = w / 'papers_latest.parquet'
    papers = pd.read_parquet(latest if latest.exists() else w / 'papers.parquet')
    if latest.exists():   # keep the base shard numbering for reference; the copy columns come from the newest catalog read
        papers['shard'] = papers['shard'].astype(int)
    secs, per, keys, Xs, missing = [], [], [], [], []
    for d in run_dirs(a.id):
        _paper_collect(d, secs, per, keys, Xs, missing)
    _paper_finish(a, w, papers, secs, per, keys, Xs, missing)


def _paper_collect(w, secs, per, keys, Xs, missing):
    import numpy as np
    import pandas as pd
    n = json.loads((w / 'RUN.json').read_text())['nshards']
    for i in range(n):
        f = w / 'sections' / f'sections-{i}.sqlite'
        g = w / 'gpu' / f'scores-{i}.sqlite'
        if not (w / 'gpu' / f'complete-{i}').exists():
            missing.append(f'{w.name}:{i}')
        if f.exists():
            secs.append(pd.read_sql('select k, main_words, appendix_words, appendix_found, copy_missing, split_error from sections', sqlite3.connect(f'file:{f}?mode=ro', uri=True)))
        if g.exists():
            db = sqlite3.connect(f'file:{g}?mode=ro', uri=True)
            per.append(pd.read_sql('''select k, sum(section='main' and abstain=0) n_main_scored, sum(section='main' and flagged=1) n_main_flagged,
                sum(section='main' and abstain=1) n_main_abstained, sum(section='appendix' and abstain=0) n_app_scored, sum(section='appendix' and flagged=1) n_app_flagged,
                avg(case when section='main' and abstain=0 then z end) mean_z_main from scores group by k''', db))
            db.close()
        e = w / 'gpu' / f'emb-{i}.npz'
        if e.exists():
            E = np.load(e); keys += list(E['keys']); Xs.append(E['X'])


def _paper_finish(a, w, papers, secs, per, keys, Xs, missing):
    import numpy as np
    import pandas as pd
    S = pd.concat(secs).drop_duplicates('k', keep='last') if secs else pd.DataFrame(columns=['k'])
    G = pd.concat(per).drop_duplicates('k', keep='last') if per else pd.DataFrame(columns=['k'])
    S_ = json.loads((w / 'RUN.json').read_text())['schools']
    S = S if secs else pd.DataFrame(columns=['k'])
    df = papers.merge(S, on='k', how='left').merge(G, on='k', how='left')
    df['usable'] = df['main_words'].fillna(0) >= 1000
    ms, mf = df['n_main_scored'], df['n_main_flagged']
    df['ai_share_main'] = np.where(df.usable & (ms > 0), mf / ms.where(ms > 0), np.nan)
    tot = ms + df['n_app_scored'].fillna(0)
    df['ai_share_main_appendix'] = np.where(df.usable & (tot > 0), (mf + df['n_app_flagged'].fillna(0)) / tot.where(tot > 0), np.nan)
    df['abstained_share_main'] = df['n_main_abstained'] / (ms + df['n_main_abstained'])
    X = np.vstack(Xs) if Xs else np.zeros((0, 768), np.float32)
    ki = {k: j for j, k in enumerate(keys)}
    df['emb_row'] = df['k'].map(ki).astype('Int64')
    df['has_emb'] = df['emb_row'].notna() & df.usable
    df.to_parquet(w / 'papers_scored.parquet')
    np.save(w / 'X_specter2_base.npy', X.astype(np.float16))
    cov = df.groupby('home_school').agg(papers=('k', 'size'), with_copy=('path', lambda x: int(x.notna().sum())), split=('main_words', lambda x: int(x.notna().sum())),
                                        usable=('usable', 'sum'), scored=('ai_share_main', lambda x: int(x.notna().sum())), embedded=('has_emb', 'sum')).reindex(S_)
    cov.to_csv(w / 'coverage.csv')
    print(cov.to_string())
    log(papers=len(df), scored=int(df.ai_share_main.notna().sum()), embedded=int(df.has_emb.sum()), shards_missing=missing)


def stage_status(a):
    w = work_dir(a.id)
    n = json.loads((w / 'RUN.json').read_text())['nshards']
    sec_done = gpu_done = 0
    for i in range(n):
        f = w / 'sections' / f'sections-{i}.sqlite'
        if f.exists():
            db = sqlite3.connect(f'file:{f}?mode=ro', uri=True)
            sec_done += dict(db.execute('select key, value from meta')).get('complete') == '1'
            db.close()
        gpu_done += (w / 'gpu' / f'complete-{i}').exists()
    log(nshards=n, sections_complete=sec_done, gpu_complete=gpu_done)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['list', 'sections', 'gpu', 'paper', 'status', 'delta'])
    ap.add_argument('--id', default='20261123')
    ap.add_argument('--shard', type=int, default=int(os.environ.get('SLURM_ARRAY_TASK_ID', 0)))
    ap.add_argument('--nshards', type=int, default=NSHARDS)
    ap.add_argument('-j', type=int, default=8)
    ap.add_argument('--budget', type=int, default=3000)
    ap.add_argument('--min-new', type=int, default=200)
    a = ap.parse_args()
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    globals()['stage_' + a.stage](a)


if __name__ == '__main__':
    main()
