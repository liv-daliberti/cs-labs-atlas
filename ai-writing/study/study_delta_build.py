"""Score and embed the release papers the earlier build never saw (owner 2026-11-07 "yes to all"): the delta of a snapshot.

stages (each restartable; outputs in WORK = studies/homogenization/work/delta-<id>/, then copied into the snapshot by study_snapshot.py build):
  list       delta papers = release membership (2016-2025) not in the earlier universe by OpenAlex id -> delta_papers.jsonl.gz
             (paper_id = atlas id else oa:W, home school, year, title, doi, stored copy path/kind via the school stores' catalogs)
  sections   CPU: split each stored copy into main / appendix (ai-writing/sections/run_split.one, the splitter of the v3 rescoring) -> sections.sqlite
  score      GPU: detector v3 on every main and appendix passage (same model, threshold and abstain rule as detector_v3/score_sections.py) -> scores.sqlite
  paper      CPU: per-paper table (ai_share_main, ai_share_main_appendix, abstained shares, usable) -> delta_scores.parquet (+ abstract flag when scored)
  texts      CPU: EMB-shaped texts.sqlite (abstracts) and universe.sqlite of the delta papers, for embed.py and dose_score.py (via CS_ATLAS_EMBEDDINGS=WORK/emb)
usage: study_delta_build.py <stage> [--id 2026-11-08] [--shard I --nshards N] [-j N]
Delta papers have no citation measures, no IPW weights and (unless scored by the abstract step) no abstract flag; the study reports that coverage.
"""
import argparse
import gzip
import hashlib
import json
import sqlite3
import sys
import time
import zlib
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import study_common as C

AIW = Path(C.P.AI_WRITING)
ROOT = Path(C.P.WORLD_ATLAS)


def work_dir(snap_id):
    d = C.STUDY / 'work' / f'delta-{snap_id}'
    d.mkdir(parents=True, exist_ok=True)
    return d


def old_oa(snap):
    db = sqlite3.connect(f'file:{snap / "universe" / "universe.sqlite"}?mode=ro', uri=True)
    s = {C.oa_short(r[0]) for r in db.execute('select oa from papers where oa is not null')}
    db.close()
    return s


def membership_rows(snap):
    for s in C.SCHOOLS:
        for line in gzip.open(snap / 'release' / 'hierarchy' / s / 'lab_papers.jsonl.gz', 'rt'):
            r = json.loads(line)
            if r.get('year') and C.FIRST <= r['year'] <= C.LAST:
                yield s, r


def stage_list(a):
    """Every membership paper is matched to a stored copy (catalog work id, <school>_oa_<W>, DOI, normalised title; home school first). The delta is
    (new) papers the earlier build never saw plus (rescore) papers it had but never scored although we hold a copy. copies_held.parquet lists every paper
    with its copy, so the coverage table can report held versus scored per school."""
    import pandas as pd
    sys.path.append(str(C.P.VENDOR / 'homogenization_tools'))
    import fulltext_store as fs
    snap = C.snapshot_dir(a.snapshot)
    db = sqlite3.connect(f'file:{snap / "universe" / "universe.sqlite"}?mode=ro', uri=True)
    uni = {C.oa_short(o): p for p, o in db.execute('select paper_id, oa from papers where oa is not null')}
    db.close()
    sc = pd.read_parquet(snap / 'ai' / 'papers_v3.parquet', columns=['paper_id', 'ai_share_main'])
    scored_old = set(sc.loc[sc['ai_share_main'].notna(), 'paper_id'])
    papers = {}
    for s, r in membership_rows(snap):
        oa = C.oa_short(r.get('oa'))
        k = oa or r.get('atlasWorkId')
        if not k:
            continue
        d = papers.setdefault(k, dict(k=k, oa=oa, paper_id=uni.get(oa) or r.get('atlasWorkId') or f'oa:{oa}', new=oa not in uni, schools=[], year=r['year'],
                                      title=r.get('title') or '', doi=r.get('doi'), rows=[]))
        if s not in d['schools']:
            d['schools'].append(s)
        d['rows'].append((s, r.get('work') or '', f"{s}_oa_{oa or ''}"))
    cats = {}
    out = []
    for k, d in papers.items():
        d['schools'].sort(key=C.SCHOOLS.index)
        d['home_school'] = d['schools'][0]
        hit = None
        for s, wid, oaw in sorted(d['rows'], key=lambda x: C.SCHOOLS.index(x[0])):
            if s not in cats:
                cats[s] = fs.catalog(s) if (fs.FT / s / 'catalog.sqlite').exists() else {}
            cat = cats[s]
            hit = cat.get(wid) or cat.get(oaw) or (cat.get('doi:' + d['doi'].lower()) if d['doi'] else None) or (cat.get('t:' + fs.nt(d['title'])) if d['title'] else None)
            if hit:
                d['school_copy'] = s
                break
        d['path'], d['kind'] = (hit[0], hit[1]) if hit else (None, None)
        d['rescore'] = bool(hit) and not d['new'] and d['paper_id'] not in scored_old
        d.pop('rows')
        out.append(d)
    w = work_dir(a.snapshot)
    pd.DataFrame([dict(k=d['k'], paper_id=d['paper_id'], home_school=d['home_school'], year=d['year'], has_copy=bool(d['path']), new=d['new'], rescore=d['rescore']) for d in out]
                 ).to_parquet(w / 'copies_held.parquet')
    keep = [d for d in out if d['new'] or d['rescore']]
    with gzip.open(w / 'delta_papers.jsonl.gz', 'wt') as f:
        for d in keep:
            f.write(json.dumps(d) + '\n')
    held = {s: [sum(1 for d in out if d['home_school'] == s and d['path']), sum(1 for d in out if d['home_school'] == s)] for s in C.SCHOOLS}
    print(json.dumps({'papers': len(out), 'new': sum(d['new'] for d in out), 'rescore': sum(d['rescore'] for d in out), 'to_score': sum(1 for d in keep if d['path']),
                      'held_total_by_school': held, 'rescore_by_school': {s: sum(1 for d in out if d['home_school'] == s and d['rescore']) for s in C.SCHOOLS}}))


def load_delta(a):
    seen, out = set(), []
    for line in gzip.open(work_dir(a.snapshot) / 'delta_papers.jsonl.gz', 'rt'):
        d = json.loads(line)
        if d['paper_id'] not in seen:        # two OpenAlex ids can share one atlas paper id
            seen.add(d['paper_id'])
            out.append(d)
    return out


def _split(job):
    sys.path.insert(0, str(AIW / 'sections'))
    import run_split as RS
    pid, school, path, kind = job
    return RS.one((pid, None, school, path, kind, None, None))


def stage_sections(a):
    rows = [d for d in load_delta(a) if d['path']]
    rows = [d for i, d in enumerate(rows) if i % a.nshards == a.shard]
    w = work_dir(a.snapshot)
    dst = w / f'sections-{a.shard}.sqlite'
    tmp = w / f'tmp-sections-{a.shard}.sqlite'
    tmp.unlink(missing_ok=True)
    db = sqlite3.connect(tmp)
    db.executescript('''create table sections (paper_id text primary key, school text, path text, kind text, main blob, appendix blob, flags text, main_words int, appendix_words int,
        appendix_found int, copy_missing int, split_error text, n_main_passages int, n_appendix_passages int);''')
    t0 = time.time()
    n = 0
    with ProcessPoolExecutor(a.j) as ex:
        for rec in ex.map(_split, [(d['paper_id'], d['school_copy'], d['path'], d['kind']) for d in rows], chunksize=4):
            f, err = rec['flags'], rec['err']
            main_t, app = (rec['main'], rec['appendix']) if not err else ('', '')
            pm = 0 if err else sum(1 for s, _ in rec['new'] if s == 'main')
            pa = 0 if err else sum(1 for s, _ in rec['new'] if s == 'appendix')
            db.execute('insert into sections values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (
                rec['paper_id'], rec['school'], rec['path'], rec['kind'], zlib.compress(main_t.encode(), 6), zlib.compress(app.encode(), 6), json.dumps(f),
                len(main_t.split()), len(app.split()), int(bool(f.get('appendix_found'))), int(err == 'missing'), err if err != 'missing' else None, pm, pa))
            n += 1
            if n % 500 == 0:
                db.commit()
                print(json.dumps(dict(done=n, of=len(rows), seconds=round(time.time() - t0))), flush=True)
    db.commit()
    db.close()
    tmp.replace(dst)
    print(json.dumps(dict(shard=a.shard, sections=n, out=str(dst), seconds=round(time.time() - t0))))


def stage_score(a):
    """GPU. Same operating point and abstain rule as detector_v3/score_sections.py; nothing is written to the main results directory."""
    import numpy as np
    sys.path.insert(0, str(AIW / 'detector_v3'))
    import v3common as V3          # puts detector_v2 on the path
    import detector as D2          # noqa: I001
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    V = V3.V
    data = Path(C.P.CODE) / 'ai-writing' / 'detector_v3'      # data and models live in the main checkout, never in a job's code snapshot
    V3.RESULTS, V3.MODELS = data / 'results', data / 'models'
    op = json.load(open(V3.RESULTS / 'operating_point.json'))
    thr, cut = op['thr_z'], op['midcap_cut']
    w = work_dir(a.snapshot)
    dst = w / 'scores.sqlite'
    if dst.exists():
        print('scores.sqlite exists; delete it to rescore')
        return
    tok = AutoTokenizer.from_pretrained(V3.MODELS / 'all' / 'model')
    model = AutoModelForSequenceClassification.from_pretrained(V3.MODELS / 'all' / 'model').cuda().eval()
    rows = []
    for f in sorted(w.glob('sections-*.sqlite')):
        db = sqlite3.connect(f'file:{f}?mode=ro', uri=True)
        for pid, m, ap_ in db.execute('select paper_id, main, appendix from sections'):
            mt = zlib.decompress(m).decode('utf-8', 'ignore') if m else ''
            at = zlib.decompress(ap_).decode('utf-8', 'ignore') if ap_ else ''
            for i, (s, p) in enumerate([('main', x) for x in V.passages(mt)] + [('appendix', x) for x in (V.passages(at) if at else [])]):
                rows.append((pid, i, s, p))
        db.close()
    t0 = time.time()
    print(json.dumps(dict(passages=len(rows))), flush=True)
    p = D2.predict(model, tok, [V.norm(r[3]) for r in rows], bs=128)
    z = np.log(np.clip(p, 1e-300, None)) - np.log(np.clip(1 - p, 1e-300, None))
    tmp = w / 'tmp-scores.sqlite'
    tmp.unlink(missing_ok=True)
    o = sqlite3.connect(tmp)
    o.execute('create table scores (paper_id text, i int, section text, words int, midcap real, z real, abstain int, flagged int)')
    batch = []
    for (pid, i, s, t), zz in zip(rows, z):
        n_w = len(t.split())
        mc = V.quality(t)['midcap']
        ab = int(n_w < op['abstain_words'] or mc > cut)
        batch.append((pid, i, s, n_w, mc, float(zz), ab, int((not ab) and zz >= thr)))
    o.executemany('insert into scores values (?,?,?,?,?,?,?,?)', batch)
    o.execute('create index sc on scores (paper_id, i)')
    o.commit()
    o.close()
    tmp.replace(dst)
    print(json.dumps(dict(done=str(dst), rows=len(batch), minutes=round((time.time() - t0) / 60, 1))))


def paper_table(sc, sections, delta):
    """Per-paper table from passage scores (pandas frames): shares over main and main + appendix, abstained shares, usable (main >= 1,000 words)."""
    import numpy as np
    import pandas as pd
    sc = sc.copy()
    sc['scored'] = 1 - sc['abstain']
    out = []
    for pid, g in sc.groupby('paper_id'):
        m, ap = g[g.section == 'main'], g[g.section == 'appendix']
        ms, mf, ma = int(m.scored.sum()), int(m.flagged.sum()), int(m.abstain.sum())
        as_, af, aa = int(ap.scored.sum()), int(ap.flagged.sum()), int(ap.abstain.sum())
        out.append(dict(paper_id=pid, n_main_scored=ms, n_main_flagged=mf, n_main_abstained=ma, n_app_scored=as_, n_app_flagged=af, n_app_abstained=aa,
                        ai_share_main=mf / ms if ms else np.nan, ai_share_main_appendix=(mf + af) / (ms + as_) if ms + as_ else np.nan,
                        abstained_share_main=ma / (ms + ma) if ms + ma else np.nan))
    df = pd.DataFrame(out)
    df = df.merge(sections[['paper_id', 'main_words', 'appendix_found', 'split_error']], on='paper_id', how='left')
    usable = df['main_words'].fillna(0) >= 1000
    for c in ('ai_share_main', 'ai_share_main_appendix'):
        df.loc[~usable, c] = np.nan
    df['trained_on_v3'] = False                  # papers the earlier build never saw were never detector training data
    return df.merge(delta[['paper_id', 'oa', 'year', 'home_school']], on='paper_id', how='left')


def stage_paper(a):
    import pandas as pd
    w = work_dir(a.snapshot)
    sc = pd.read_sql('select * from scores', sqlite3.connect(f'file:{w / "scores.sqlite"}?mode=ro', uri=True))
    secs = pd.concat([pd.read_sql('select paper_id, main_words, appendix_found, split_error from sections', sqlite3.connect(f'file:{f}?mode=ro', uri=True))
                      for f in sorted(w.glob('sections-*.sqlite'))])
    delta = pd.DataFrame(load_delta(a))
    df = paper_table(sc, secs, delta)
    ab = sorted((w / 'ai').glob('parts/abstract/*.parquet')) if (w / 'ai').exists() else []
    if ab:
        p = pd.concat([pd.read_parquet(f) for f in ab]).drop_duplicates('paper_id')
        thr = float(pd.read_parquet(C.snapshot_dir(a.snapshot) / 'ai' / 'papers_v3.parquet', columns=['thr_abstract'])['thr_abstract'].dropna().iloc[0])
        p['flag_abstract'] = (p['p_v1'] >= thr).astype(float)
        df = df.merge(p[['paper_id', 'p_v1', 'flag_abstract']], on='paper_id', how='outer')
    df.to_parquet(w / 'delta_scores.parquet')
    print(json.dumps(dict(papers=len(df), scored_main=int(df.ai_share_main.notna().sum()), abstract_flag=int(df.get('flag_abstract', pd.Series(dtype=float)).notna().sum()))))


def stage_texts(a):
    """EMB-shaped texts.sqlite (abstracts) + universe.sqlite of the delta papers (the layout embed.py and dose_score.py read via CS_ATLAS_EMBEDDINGS)."""
    snap = C.snapshot_dir(a.snapshot)
    w = work_dir(a.snapshot)
    emb = w / 'emb'
    emb.mkdir(exist_ok=True)
    delta = [d for d in load_delta(a) if d['new']]
    ab = {}
    for name in ('delta/oa_fields_delta.sqlite',):
        db = sqlite3.connect(f'file:{snap / name}?mode=ro', uri=True)
        ab.update({r[0]: (r[1], r[2]) for r in db.execute('select id, title, abstract from works where abstract is not null')})
        db.close()
    t = emb / 'texts.sqlite'
    t.unlink(missing_ok=True)
    db = sqlite3.connect(t)
    db.execute('create table abstracts (paper_id text primary key, title text, abstract text, src text, words int, text_hash text)')
    db.execute('create table fulltext (paper_id text primary key, school text, path text, kind text, chars int, words int, usable int, body blob, flags text, text_hash text)')
    n = 0
    for d in delta:
        if d['oa'] in ab and len((ab[d['oa']][1] or '').split()) >= 10:
            title, abstract = ab[d['oa']][0] or d['title'], ab[d['oa']][1]
            h = hashlib.sha1(((title or '') + ' ' + abstract).encode('utf-8', 'ignore')).hexdigest()[:16]
            db.execute('insert into abstracts values (?,?,?,?,?,?)', (d['paper_id'], title, abstract, 'openalex-api', len(abstract.split()), h))
            n += 1
    db.commit()
    db.close()
    u = emb / 'universe.sqlite'
    u.unlink(missing_ok=True)
    db = sqlite3.connect(u)
    db.execute('create table papers (paper_id text primary key, oa text, doi text, title text, year int, date text, home_school text, schools text, n_labs int)')
    db.executemany('insert into papers values (?,?,?,?,?,?,?,?,?)', [(d['paper_id'], d['oa'], d['doi'], d['title'], d['year'], None, d['home_school'], json.dumps(d['schools']), len(d['schools'])) for d in delta])
    db.commit()
    db.close()
    print(json.dumps(dict(abstracts=n, papers=len(delta), emb=str(emb))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['list', 'sections', 'score', 'paper', 'texts'])
    ap.add_argument('--id', dest='snapshot', default='2026-11-07', help='snapshot whose membership defines the delta (a sealed snapshot or the one being built)')
    ap.add_argument('--shard', type=int, default=0)
    ap.add_argument('--nshards', type=int, default=1)
    ap.add_argument('-j', type=int, default=8)
    a = ap.parse_args()
    globals()['stage_' + a.stage](a)


if __name__ == '__main__':
    main()
