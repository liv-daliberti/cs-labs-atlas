"""Average citation age of every lab paper of the e32 build (owner 2026-11-23: "time vs %AI vs entropy, color by average citation age").

Citation age of a paper = its publication year - the publication year of each work it cites (OpenAlex referenced_works); the paper's
average over the references with a known year (negative ages, a cited preprint dated after the citing paper, count as 0). Median and
the share of references from the last two years are kept too.

Source: the public OpenAlex bulk snapshot (works, the manifest tools/oa_snapshot.py reads; 2026-10-14 when this was written), streamed
part by part exactly as field300_corpus.py does: no API credits, the dump is never stored. One pass keeps
  (1) id -> publication_year of EVERY work (the cited works are anything in OpenAlex, not only CS), as compact int arrays;
  (2) referenced_works of our lab papers (papers.parquet ids that are OpenAlex W ids).
stages (WORK/citeage/; restartable)
  chunk I    one array task: parts of chunk I (PER parts, balanced as field300) -> chunks/years-III.npz, chunks/refs-III.parquet
  merge      every chunk present -> citeage.parquet (k, year, n_refs, n_refs_dated, cite_age_mean, cite_age_median, recent2_share)
  status     chunks done / missing
usage: citeage.py chunk I | merge | status   [--id 20261123]
"""
import argparse
import json
import re
import sys
import time
from array import array
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / 'tools'))
import e32  # noqa: E402
import oa_snapshot as OA  # noqa: E402

PER = 20
ID_RX = re.compile(rb'^\{"id":"https://openalex\.org/W(\d+)"')
YEAR_RX = re.compile(rb'"publication_year":(\d{4})')


def parts():
    _, p = OA.manifest('works')
    return sorted(p, key=lambda x: x[0])


def chunks():
    p = parts()
    return [p[i:i + PER] for i in range(0, len(p), PER)]


def out_dir(a):
    d = e32.work_dir(a.id) / 'citeage'
    (d / 'chunks').mkdir(parents=True, exist_ok=True)
    return d


def ours(a):
    import pandas as pd
    df = pd.read_parquet(e32.work_dir(a.id) / 'papers.parquet', columns=['k'])
    return {int(k[1:]) for k in df.k if k.startswith('W') and k[1:].isdigit()}


def cmd_chunk(a):
    import numpy as np
    import pandas as pd
    d = out_dir(a)
    dest = d / 'chunks' / f'years-{a.i:03d}.npz'
    if dest.exists():
        print(json.dumps(dict(chunk=a.i, skipped='done'))); return
    want = ours(a)
    ids, yrs, refs = array('q'), array('h'), []
    t0 = time.time()
    todo = chunks()[a.i]
    for n, (url, size, _) in enumerate(todo):
        for attempt in range(4):
            try:
                pi, py, pr = array('q'), array('h'), []
                for line in OA.stream_lines(url):
                    m = ID_RX.match(line)
                    if not m:
                        continue
                    y = YEAR_RX.search(line)
                    wid = int(m.group(1))
                    pi.append(wid); py.append(int(y.group(1)) if y else 0)
                    if wid in want:
                        w = json.loads(line)
                        pr.append(dict(w=wid, year=w.get('publication_year'), refs=[int(r.rsplit('/W', 1)[1]) for r in (w.get('referenced_works') or [])]))
                break
            except Exception as e:  # noqa: BLE001  network or gzip error: the part restarts from its start
                print(json.dumps(dict(part_retry=url, attempt=attempt, error=str(e)[:120])), flush=True)
                time.sleep(20 * (attempt + 1))
        else:
            raise SystemExit(f'part failed after retries: {url}')
        ids.extend(pi); yrs.extend(py); refs += pr
        print(json.dumps(dict(chunk=a.i, part=n + 1, of=len(todo), works=len(ids), ours=len(refs), seconds=int(time.time() - t0))), flush=True)
    pd.DataFrame(refs, columns=['w', 'year', 'refs']).to_parquet(d / 'chunks' / f'refs-{a.i:03d}.parquet', index=False)
    tmp = dest.with_name(f'.tmp-years-{a.i:03d}.npz')
    np.savez(tmp, ids=np.frombuffer(ids, dtype=np.int64), years=np.frombuffer(yrs, dtype=np.int16))
    tmp.replace(dest)
    print(json.dumps(dict(chunk=a.i, finished=True, works=len(ids), ours=len(refs), minutes=round((time.time() - t0) / 60, 1))), flush=True)


def cmd_merge(a):
    import numpy as np
    import pandas as pd
    d = out_dir(a)
    n = len(chunks())
    miss = [i for i in range(n) if not (d / 'chunks' / f'years-{i:03d}.npz').exists()]
    if miss:
        raise SystemExit(f'chunks missing: {miss}')
    I, Y = [], []
    for i in range(n):
        z = np.load(d / 'chunks' / f'years-{i:03d}.npz')
        I.append(z['ids']); Y.append(z['years'])
    I, Y = np.concatenate(I), np.concatenate(Y)
    o = np.argsort(I, kind='stable')
    I, Y = I[o], Y[o]
    R = pd.concat([pd.read_parquet(d / 'chunks' / f'refs-{i:03d}.parquet') for i in range(n)]).drop_duplicates('w')
    P = pd.read_parquet(e32.work_dir(a.id) / 'papers.parquet', columns=['k', 'year'])
    P = P[P.k.str.match(r'^W\d+$')].assign(w=lambda x: x.k.str[1:].astype('int64'))
    R = P.merge(R.drop(columns='year'), on='w', how='left')
    out = []
    for k, y, refs in zip(R.k, R.year, R.refs):
        refs = np.asarray(refs if isinstance(refs, (list, np.ndarray)) else [], dtype=np.int64)
        if len(refs):
            j = np.clip(np.searchsorted(I, refs), 0, len(I) - 1)
            ok = (I[j] == refs) & (Y[j] > 1000)
            age = np.clip(int(y) - Y[j][ok].astype(int), 0, None)
        else:
            age = np.array([])
        out.append(dict(k=k, n_refs=len(refs), n_refs_dated=len(age), cite_age_mean=float(age.mean()) if len(age) else np.nan,
                        cite_age_median=float(np.median(age)) if len(age) else np.nan, recent2_share=float((age <= 2).mean()) if len(age) else np.nan))
    df = pd.DataFrame(out)
    df.to_parquet(d / 'citeage.parquet', index=False)
    print(json.dumps(dict(works_indexed=int(len(I)), papers=len(df), with_refs=int((df.n_refs_dated > 0).sum()), mean_age=float(df.cite_age_mean.mean()))))


def cmd_status(a):
    d = out_dir(a)
    n = len(chunks())
    done = sum((d / 'chunks' / f'years-{i:03d}.npz').exists() for i in range(n))
    print(json.dumps(dict(chunks=n, done=done, merged=(d / 'citeage.parquet').exists())))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['chunk', 'merge', 'status'])
    ap.add_argument('i', type=int, nargs='?')
    ap.add_argument('--id', default='20261123')
    a = ap.parse_args()
    globals()['cmd_' + a.cmd](a)


if __name__ == '__main__':
    main()
