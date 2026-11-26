"""OpenAlex metadata of every lab paper of the e32 build, for the within-topic analysis (owner 2026-11-23: within topic, within area + Gini,
de-meaning, within-topic mean citations and variance, within-topic fixed effects).

Same stream as citeage.py (the public works snapshot, part by part, never stored; no API credits), keeping only our papers:
primary topic (id, name), subfield, field, domain, cited_by_count, fwci, citation_normalized_percentile, primary source (id, name, type).
stages (WORK/oameta/)  chunk I -> chunks/meta-III.parquet | merge -> oameta.parquet (k = W id) | status
"""
import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import citeage as CA  # noqa: E402  (parts, chunks, the id regex, our ids)
import e32  # noqa: E402

OA = CA.OA


def out_dir(a):
    d = e32.work_dir(a.id) / 'oameta'
    (d / 'chunks').mkdir(parents=True, exist_ok=True)
    return d


def tail(x):
    return x.rsplit('/', 1)[-1] if isinstance(x, str) else None


def row(w):
    t = w.get('primary_topic') or {}
    src = ((w.get('primary_location') or {}).get('source') or {})
    pct = w.get('citation_normalized_percentile') or {}
    return dict(k=tail(w['id']), topic_id=tail(t.get('id')), topic=t.get('display_name'),
                subfield_id=tail((t.get('subfield') or {}).get('id')), subfield=(t.get('subfield') or {}).get('display_name'),
                field=(t.get('field') or {}).get('display_name'), domain=(t.get('domain') or {}).get('display_name'),
                cited_by=w.get('cited_by_count'), fwci=w.get('fwci'), cite_pct=pct.get('value') if isinstance(pct, dict) else None,
                source_id=tail(src.get('id')), venue=src.get('display_name'), venue_type=src.get('type'), oa_year=w.get('publication_year'))


def cmd_chunk(a):
    import pandas as pd
    d = out_dir(a)
    dest = d / 'chunks' / f'meta-{a.i:03d}.parquet'
    if dest.exists():
        print(json.dumps(dict(chunk=a.i, skipped='done'))); return
    want = CA.ours(a)
    rows, t0 = [], time.time()
    todo = CA.chunks()[a.i]
    for n, (url, size, _) in enumerate(todo):
        for attempt in range(4):
            try:
                pr = []
                for line in OA.stream_lines(url):
                    m = CA.ID_RX.match(line)
                    if m and int(m.group(1)) in want:
                        pr.append(row(json.loads(line)))
                break
            except Exception as e:  # noqa: BLE001
                print(json.dumps(dict(part_retry=url, attempt=attempt, error=str(e)[:120])), flush=True)
                time.sleep(20 * (attempt + 1))
        else:
            raise SystemExit(f'part failed after retries: {url}')
        rows += pr
        print(json.dumps(dict(chunk=a.i, part=n + 1, of=len(todo), ours=len(rows), seconds=int(time.time() - t0))), flush=True)
    cols = list(row({'id': 'x'}).keys())
    tmp = dest.with_name(f'.tmp-{dest.name}')
    pd.DataFrame(rows, columns=cols).to_parquet(tmp, index=False)
    tmp.replace(dest)
    print(json.dumps(dict(chunk=a.i, finished=True, ours=len(rows), minutes=round((time.time() - t0) / 60, 1))), flush=True)


def cmd_merge(a):
    import pandas as pd
    d = out_dir(a)
    n = len(CA.chunks())
    miss = [i for i in range(n) if not (d / 'chunks' / f'meta-{i:03d}.parquet').exists()]
    if miss:
        raise SystemExit(f'chunks missing: {miss}')
    df = pd.concat([pd.read_parquet(d / 'chunks' / f'meta-{i:03d}.parquet') for i in range(n)])
    df = df.sort_values('cited_by', na_position='first').drop_duplicates('k', keep='last')   # a work can sit in two parts (updates)
    df.to_parquet(d / 'oameta.parquet', index=False)
    print(json.dumps(dict(papers=len(df), with_topic=int(df.topic_id.notna().sum()), cs_field=int((df.field == 'Computer Science').sum()))))


def cmd_status(a):
    d = out_dir(a)
    n = len(CA.chunks())
    print(json.dumps(dict(chunks=n, done=sum((d / 'chunks' / f'meta-{i:03d}.parquet').exists() for i in range(n)), merged=(d / 'oameta.parquet').exists())))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['chunk', 'merge', 'status'])
    ap.add_argument('i', type=int, nargs='?')
    ap.add_argument('--id', default='20261123')
    a = ap.parse_args()
    globals()['cmd_' + a.cmd](a)


if __name__ == '__main__':
    main()
