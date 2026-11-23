"""Full texts for the field-300 papers straight from the open venues (owner 2026-11-23: "try ICLR, NeurIPS, ICML, ACL directly, all open").

Targets: field-300 works (snapshots/field300-2026-11-08, 300 GRAS CS&E universities, 2016-2025) whose normalized title (>= 20 characters) equals an entry of
the open-proceedings index (archive/sweeps/claude-princeton-20261015/cs-structure/raw/proceedings/index.json.gz: title, year, pdf, landing, venue) for
ACL Anthology, PMLR (ICML), NeurIPS and ICLR (OpenReview); the entry with the nearest year wins. Works already held as lab full texts are skipped.
Hosts: aclanthology.org (CC BY 4.0 since 2016), proceedings.mlr.press, papers.nips.cc, openreview.net; none disallows these paths in robots.txt
(checked 2026-11-23; OpenReview disallows only ?email= URLs). One request at a time per worker, >= 1 s apart, backoff on 429/5xx; the PDF goes to
node-local scratch, is checked (PDF header; the paper's title on page 1), split (fulltext_sections.split_file: main / appendix / references) and DELETED:
only the text sections and the reference years are kept (no PDF archive on the shared filesystem).
Output: a run directory in the e32 layout, WORK = studies/homogenization/work/entropy32-<id>-field/ (papers.parquet, RUN.json, sections/sections-<i>.sqlite
with meta complete=1, ftrefs.parquet), so `e32.py gpu --id <id>-field` scores and embeds it exactly like the lab papers.
stages  targets | fetch I (array task = chunk; resumable, stops after --budget s) | refs (merge reference years) | status
"""
import argparse
import gzip
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import e32  # noqa: E402

INDEX = Path('/n/fs/resemble/homogenizing-science/archive/sweeps/claude-princeton-20261015/cs-structure/raw/proceedings/index.json.gz')
SNAP = Path(e32.P.HOMOGENIZATION_STUDY) / 'snapshots' / 'field300-2026-11-08'
UA = 'HomogenizingScienceResearch/0.2 (academic full-text study; polite, 1 req/s)'
CHUNK = 1500
VENUE = {'ACL': 'acl', 'NeurIPS': 'neurips', 'ICLR': 'iclr'}


def vkey(v):
    if 'PMLR' in v or 'ICML' in v:
        return 'icml'
    if 'ACL' in v or 'Anthology' in v:
        return 'acl'
    return VENUE.get(v)


def fid(a):
    return f'{a.id}-field'


def nt(t):
    sys.path.insert(0, str(Path(e32.P.CODE) / 'vendor' / 'cmu_tools'))
    import arxiv_oai as ao
    return ao.nt(t)


def cmd_targets(a):
    import pandas as pd
    import pyarrow.parquet as pq
    sys.path.insert(0, str(Path(e32.P.CODE) / 'vendor' / 'cmu_tools'))
    import arxiv_oai as ao
    I = pd.DataFrame(json.load(gzip.open(INDEX, 'rt')), columns=['title', 'year', 'pdf', 'landing', 'venue'])
    I['v'] = I.venue.map(vkey)
    I = I[I.v.notna() & I.pdf.notna()]
    I['nt'] = I.title.map(ao.nt)
    I = I[I.nt.str.len() >= 20]
    held = set(pd.read_parquet(e32.work_dir(a.id) / 'papers_scored.parquet', columns=['k', 'has_emb']).query('has_emb').k)
    out = []
    for y in range(2016, 2026):
        t = pq.read_table(SNAP / 'corpus' / f'year={y}.parquet', columns=['work', 'title', 'year']).to_pandas()
        t['nt'] = t.title.fillna('').map(ao.nt)
        m = t.merge(I[['nt', 'year', 'pdf', 'landing', 'v']].rename(columns={'year': 'pyear'}), on='nt')
        m['gap'] = (m.pyear - m.year).abs()
        m = m.sort_values('gap').drop_duplicates('work')
        out.append(m[m.gap <= 2])
    T = pd.concat(out)
    T['k'] = 'W' + T.work.astype(str)
    T = T[~T.k.isin(held)]
    T = T.sort_values(['v', 'year', 'k']).reset_index(drop=True)
    T['chunk'] = -1
    nxt = 0
    plan = {}
    for v, g in T.groupby('v', sort=True):
        n = -(-len(g) // CHUNK)
        T.loc[g.index, 'chunk'] = nxt + (pd.Series(range(len(g)), index=g.index) // CHUNK)
        plan[v] = [nxt, nxt + n - 1]
        nxt += n
    w = e32.work_dir(fid(a))
    T['paper_id'] = T.k
    T['home_school'] = 'field300'
    T['path'] = T.pdf
    T['kind'] = 'pdf'
    T['shard'] = T.chunk
    T[['k', 'paper_id', 'work', 'year', 'title', 'v', 'pdf', 'landing', 'home_school', 'path', 'kind', 'shard']].to_parquet(w / 'papers.parquet')
    (w / 'RUN.json').write_text(json.dumps(dict(id=fid(a), base=a.id, nshards=int(nxt), schools=['field300'], chunks_by_venue=plan, papers=len(T),
                                                built=time.strftime('%Y-%m-%dT%H:%M:%S'), source='open proceedings index + field-300 corpus'), indent=1))
    print(json.dumps(dict(targets=len(T), by_venue=T.v.value_counts().to_dict(), post_2023=int((T.year >= 2023).sum()), chunks=int(nxt), plan=plan)))


class Polite:
    def __init__(self):
        import requests
        self.s = requests.Session()
        self.s.headers['User-Agent'] = UA
        self.last = 0.0

    def get(self, url, tries=4):
        for i in range(tries):
            wait = 1.0 - (time.time() - self.last)
            if wait > 0:
                time.sleep(wait)
            self.last = time.time()
            try:
                r = self.s.get(url, timeout=60, allow_redirects=True)
            except Exception as e:  # noqa: BLE001
                err = type(e).__name__
                time.sleep(5 * (i + 1)); continue
            if r.status_code == 200:
                return r.content, None
            err = f'http {r.status_code}'
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(int(r.headers.get('Retry-After', 0) or 0) or 15 * (i + 1)); continue
            return None, err
        return None, err


def page1_has_title(path, title):
    try:
        t = subprocess.run(['pdftotext', '-l', '1', '-q', str(path), '-'], capture_output=True, timeout=60).stdout.decode('utf-8', 'ignore')
    except Exception:  # noqa: BLE001
        return False
    want = set(re.findall(r'[a-z0-9]{3,}', title.lower()))
    have = set(re.findall(r'[a-z0-9]{3,}', t.lower()))
    return bool(want) and len(want & have) / len(want) >= 0.8


def cmd_fetch(a):
    import pandas as pd
    import fulltext_sections as S
    import ftrefs as F
    w = e32.work_dir(fid(a))
    (w / 'sections').mkdir(exist_ok=True)
    dst = w / 'sections' / f'sections-{a.i}.sqlite'
    T = pd.read_parquet(w / 'papers.parquet')
    T = T[T.shard == a.i]
    tmpd = Path(os.environ.get('TMPDIR') or '/tmp') / f'fieldft-{a.i}-{os.getpid()}'
    tmpd.mkdir(parents=True, exist_ok=True)
    loc = tmpd / 'sections.sqlite'
    if dst.exists():
        db = sqlite3.connect(f'file:{dst}?mode=ro', uri=True)
        if dict(db.execute('select key, value from meta')).get('complete') == '1':
            print(json.dumps(dict(chunk=a.i, skip='complete'))); return
        db.close(); shutil.copyfile(dst, loc)
    db = sqlite3.connect(loc)
    db.executescript(e32.SECTIONS_SQL + '''create table if not exists refs (k text primary key, refs_chars int, ft_n_years int, ft_cite_age_mean real,
        ft_cite_age_median real, ft_recent2 real); create table if not exists fails (k text primary key, why text);''')
    done = {r[0] for r in db.execute('select k from sections union select k from fails')}
    todo = [r for r in T.itertuples() if r.k not in done]
    http = Polite()
    t0, n, ok = time.time(), 0, 0
    stopped = False
    for r in todo:
        if time.time() - t0 > a.budget:
            stopped = True; break
        body, err = http.get(r.pdf)
        why = err
        if body is not None and not body[:5].startswith(b'%PDF'):
            why = 'not a pdf'
        if why is None:
            pdf = tmpd / 'p.pdf'
            pdf.write_bytes(body)
            if not page1_has_title(pdf, r.title or ''):
                why = 'title not on page 1'
            else:
                x = S.split_file(pdf, 'pdf')
                if x.get('error'):
                    why = f"split: {x['error']}"[:120]
                else:
                    main_t, app, refs = x['main'], x['appendix'], x.get('references') or ''
                    f = x['flags']
                    from common import passages  # noqa: E402  (the v3 splitter's passages, as run_split)
                    pm, pa = passages(main_t), passages(app) if app else []
                    db.execute('insert or replace into sections values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (
                        r.k, 'field300', r.pdf, 'pdf', zlib.compress(main_t.encode(), 6), zlib.compress(app.encode(), 6), json.dumps(f),
                        len(main_t.split()), len(app.split()), int(bool(f.get('appendix_found'))), 0, None, len(pm), len(pa)))
                    ys = F.years_of(refs, int(r.year))
                    import numpy as np
                    age = np.clip(int(r.year) - np.array(ys, dtype=int), 0, None) if ys else np.array([])
                    db.execute('insert or replace into refs values (?,?,?,?,?,?)', (r.k, len(refs), len(ys), float(age.mean()) if len(age) else None,
                                                                                   float(np.median(age)) if len(age) else None, float((age <= 2).mean()) if len(age) else None))
                    ok += 1
            pdf.unlink(missing_ok=True)
        if why is not None:
            db.execute('insert or replace into fails values (?,?)', (r.k, why))
        n += 1
        if n % 100 == 0:
            db.commit()
            print(json.dumps(dict(chunk=a.i, done=len(done) + n, of=len(T), ok_this_run=ok, minutes=round((time.time() - t0) / 60, 1))), flush=True)
    db.execute('insert or replace into meta values (?,?)', ('complete', '0' if stopped else '1'))
    db.commit(); db.close()
    tmp = dst.with_suffix('.tmp'); shutil.copyfile(loc, tmp); tmp.replace(dst)
    shutil.rmtree(tmpd, ignore_errors=True)
    print(json.dumps(dict(chunk=a.i, fetched_this_run=n, ok_this_run=ok, complete=not stopped)))
    if stopped:
        sys.exit(75)


def cmd_refs(a):
    import pandas as pd
    w = e32.work_dir(fid(a))
    fs = sorted((w / 'sections').glob('sections-*.sqlite'))
    R = pd.concat([pd.read_sql('select * from refs', sqlite3.connect(f'file:{f}?mode=ro', uri=True)) for f in fs]) if fs else pd.DataFrame()
    (w / 'ftrefs').mkdir(exist_ok=True)
    R.to_parquet(w / 'ftrefs' / 'ftrefs.parquet', index=False)
    print(json.dumps(dict(papers_with_refs=len(R))))


def cmd_status(a):
    import pandas as pd
    w = e32.work_dir(fid(a))
    run = json.loads((w / 'RUN.json').read_text())
    ok = fail = comp = 0
    why = {}
    for i in range(run['nshards']):
        f = w / 'sections' / f'sections-{i}.sqlite'
        if not f.exists():
            continue
        db = sqlite3.connect(f'file:{f}?mode=ro', uri=True)
        ok += db.execute('select count(*) from sections').fetchone()[0]
        for k, c in db.execute('select why, count(*) from fails group by why'):
            why[k] = why.get(k, 0) + c; fail += c
        comp += dict(db.execute('select key, value from meta')).get('complete') == '1'
        db.close()
    print(json.dumps(dict(targets=run['papers'], chunks=run['nshards'], chunks_complete=comp, fetched_ok=ok, failed=fail, fail_reasons=why)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['targets', 'fetch', 'refs', 'status'])
    ap.add_argument('i', type=int, nargs='?', default=int(os.environ.get('SLURM_ARRAY_TASK_ID', 0)))
    ap.add_argument('--id', default='20261123')
    ap.add_argument('--budget', type=int, default=3000)
    a = ap.parse_args()
    sys.path.insert(0, str(HERE.parent / 'diversity'))
    globals()['cmd_' + a.cmd](a)


if __name__ == '__main__':
    main()
