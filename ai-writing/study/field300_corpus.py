"""Field-300 corpus: every 2016-2025 computer-science work with an author affiliated with one of the 300 GRAS 2025 CS&E universities (owner 2026-11-08).

Source: the public OpenAlex bulk snapshot (works jsonl, date 2026-10-14), streamed part by part as tools/oa_snapshot.py does (no API credits, raw dump never stored).
  field300_corpus.py plan   [--chunks N]            the part list, the chunk split and the cohort id table
  field300_corpus.py chunk  I [--chunks N]          one restartable array task: stream the parts of chunk I, keep matching works -> work/field300/chunks/chunk-III.parquet
  field300_corpus.py merge  [--chunks N]            chunks -> corpus/year=YYYY.parquet (+ counts tables); stops if a chunk is missing
  field300_corpus.py counts                         the size table per year from the merged corpus

A work is kept when (a) 2016 <= publication_year <= 2025, (b) its type is in KEEP_TYPES and it is not paratext, (c) at least one authorship institution has a lineage
id of a cohort institution (main or related id of the GRAS map), and (d) it is computer science: OpenAlex primary topic in the field Computer Science, or its primary
source is one of the 548 reviewed CS venues (hierarchy/reviewed/cs-venues.json). `cs_any` marks works with a CS field in any of the (up to 3) listed topics; those that
are neither are only counted (tables/sidecar), not stored, as the size sensitivity. One row per paper; institutions are cohort indices with the number of authorships.
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import field300_common as F

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import oa_snapshot as OA  # noqa: E402

DATE = '2026-10-14'
PER_CHUNK = 20   # manifest parts per array task (about 15 minutes of one core)
YEAR_RX = re.compile(rb'"publication_year":(20(?:1[6-9]|2[0-5]))')


def venues():
    p = Path(__file__).resolve().parents[2] / 'hierarchy' / 'reviewed' / 'cs-venues.json'
    return {int(v['source'].rsplit('/S', 1)[1]) for v in json.loads(p.read_text())}


def id_table(roster):
    """{OpenAlex institution short id: cohort idx} over main + related ids."""
    t = {}
    for r in roster:
        for i in r['oa_ids']:
            t[i] = r['idx']
    return t


def parts_of(date=DATE):
    d, parts = OA.manifest('works')
    if d != date:
        raise SystemExit(f'manifest date {d} != {date}')
    return sorted(parts, key=lambda p: p[0])


def chunks(parts, per=PER_CHUNK):
    return [parts[i:i + per] for i in range(0, len(parts), per)]


def topic_fields(w):
    ts = [t for t in (w.get('topics') or [])][:3]
    pt = w.get('primary_topic') or {}
    fid = lambda t: ((t.get('field') or {}).get('id') or '').rsplit('/fields/', 1)[-1]   # noqa: E731
    return fid(pt) == '17', any(fid(t) == '17' for t in ts)


def row_of(w, idtab, cs_venues):
    """The stored row of a matching work, or (None, reason) -> reason in {'year','type','inst','cs'} counted by the caller; (row, 'ok') otherwise."""
    y = w.get('publication_year')
    if not y or not (F.FIRST <= y <= F.LAST):
        return None, 'year'
    if w.get('is_paratext') or w.get('type') not in F.KEEP_TYPES:
        return None, 'type'
    per_inst, countries, n = {}, set(), 0
    for a in w.get('authorships') or []:
        n += 1
        seen = set()
        for x in a.get('institutions') or []:
            if x.get('country_code'):
                countries.add(x['country_code'])
            for i in {OA.short(l) for l in (x.get('lineage') or [])} | {OA.short(x.get('id'))}:
                if i in idtab:
                    seen.add(idtab[i])
        for k in seen:
            per_inst[k] = per_inst.get(k, 0) + 1
    if not per_inst:
        return None, 'inst'
    prim, anyc = topic_fields(w)
    loc = w.get('primary_location') or {}
    src = loc.get('source') or {}
    sid = F.short_int(src.get('id'))
    venue = sid in cs_venues if sid else False
    pt = w.get('primary_topic') or {}
    if not (prim or venue):
        return (None, 'cs_any') if anyc else (None, 'cs')
    inv = w.get('abstract_inverted_index')
    ks = sorted(per_inst)
    row = dict(work=F.short_int(w['id']), year=y, type=w.get('type'), lang=w.get('language'), title=w.get('title') or w.get('display_name') or '',
               abstract=F.abstract_of(inv), topic=F.short_int(pt.get('id')), subfield=F.short_int((pt.get('subfield') or {}).get('id')),
               field=F.short_int((pt.get('field') or {}).get('id')), domain=F.short_int((pt.get('domain') or {}).get('id')),
               topics3=[F.short_int(t.get('id')) for t in (w.get('topics') or [])[:3]],
               venue=sid, venue_name=src.get('display_name') or '', venue_type=src.get('type') or '', cs_primary=bool(prim), cs_venue=bool(venue), cs_any=bool(anyc),
               cited_by=w.get('cited_by_count') or 0, n_auth=n, inst=ks, inst_n=[per_inst[k] for k in ks], countries=sorted(countries),
               refs=[r for r in (F.short_int(x) for x in (w.get('referenced_works') or [])) if r], n_refs=len(w.get('referenced_works') or []),
               retracted=bool(w.get('is_retracted')), doi=(w.get('doi') or '').replace('https://doi.org/', ''))
    return row, 'ok'


def stream_part(url, idtab, cs_venues, tokens):
    rows, stat = [], dict(lines=0, year=0, hit=0, type=0, inst=0, cs=0, cs_any=0, ok=0)
    sidecar = {}
    for line in OA.stream_lines(url):
        stat['lines'] += 1
        if not line or not YEAR_RX.search(line):
            continue
        stat['year'] += 1
        if not ({t.decode() for t in OA.TOKEN.findall(line)} & tokens):
            continue
        stat['hit'] += 1
        w = json.loads(line)
        r, why = row_of(w, idtab, cs_venues)
        stat[why] += 1
        if r:
            rows.append(r)
        elif why in ('cs', 'cs_any'):    # size sensitivity: how many non-CS cohort works there are, per year and flag
            k = (w['publication_year'], why)
            sidecar[k] = sidecar.get(k, 0) + 1
    return rows, stat, sidecar


def cmd_chunk(i, per):
    import pandas as pd
    roster = F.load_roster()
    idtab, tokens, cs_v = id_table(roster), set(id_table(roster)), venues()
    todo = chunks(parts_of(), per)[i]
    out = F.work_dir() / 'chunks'
    out.mkdir(parents=True, exist_ok=True)
    dest = out / f'chunk-{i:03d}.parquet'
    if dest.exists():
        print(json.dumps(dict(chunk=i, skipped='done')), flush=True)
        return
    rows, tot, side, t0 = [], {}, {}, time.time()
    for n, (url, size, _) in enumerate(todo):
        for attempt in range(4):
            try:
                r, st, sd = stream_part(url, idtab, cs_v, tokens)
                break
            except Exception as e:  # noqa: BLE001  network or gzip error: the part restarts from its start
                print(json.dumps(dict(part_retry=url, attempt=attempt, error=str(e)[:120])), flush=True)
                time.sleep(20 * (attempt + 1))
        else:
            raise SystemExit(f'part failed after retries: {url}')
        rows += r
        for k, v in st.items():
            tot[k] = tot.get(k, 0) + v
        for k, v in sd.items():
            side[k] = side.get(k, 0) + v
        print(json.dumps(dict(chunk=i, part=n + 1, of=len(todo), kept=len(rows), seconds=int(time.time() - t0), **st)), flush=True)
    df = pd.DataFrame(rows)
    tmp = dest.with_name('.tmp-' + dest.name)
    df.to_parquet(tmp, index=False)
    tmp.replace(dest)
    pd.DataFrame([dict(year=k[0], reason=k[1], n=v) for k, v in sorted(side.items())], columns=['year', 'reason', 'n']).to_parquet(out / f'side-{i:03d}.parquet', index=False)
    print(json.dumps(dict(chunk=i, finished=str(dest), rows=len(df), **tot)), flush=True)


def cmd_merge(per):
    import pandas as pd
    n = len(chunks(parts_of(), per))
    d = F.work_dir() / 'chunks'
    miss = [i for i in range(n) if not (d / f'chunk-{i:03d}.parquet').exists() or not (d / f'side-{i:03d}.parquet').exists()]
    if miss:
        raise SystemExit(f'chunks missing: {miss}')
    out = F.work_dir() / 'corpus'
    out.mkdir(parents=True, exist_ok=True)
    frames = [pd.read_parquet(d / f'chunk-{i:03d}.parquet') for i in range(n)]
    df = pd.concat([f for f in frames if len(f.columns)], ignore_index=True)   # a chunk of old, stale parts can hold no match (an empty frame has no columns)
    df = df.drop_duplicates('work', keep='last').sort_values('work').reset_index(drop=True)   # a work lives in one part, but updated copies can recur across parts
    for y, g in df.groupby('year'):
        g.to_parquet(out / f'year={y}.parquet', index=False, compression='zstd')
    side = pd.concat([pd.read_parquet(d / f'side-{i:03d}.parquet') for i in range(n)], ignore_index=True).groupby(['year', 'reason'], as_index=False)['n'].sum()
    side.to_parquet(out / 'side_counts.parquet', index=False)
    print(json.dumps(dict(merged=len(df), chunks=n)), flush=True)
    cmd_counts()


def load_corpus(columns=None):
    import pandas as pd
    fs = sorted((F.work_dir() / 'corpus').glob('year=*.parquet'))
    return pd.concat([pd.read_parquet(f, columns=columns) for f in fs], ignore_index=True)


def cmd_counts():
    import pandas as pd
    df = load_corpus(['work', 'year', 'abstract', 'lang', 'cs_primary', 'cs_venue', 'cs_any', 'inst', 'type', 'venue_type', 'n_refs'])
    df['has_abs'] = df['abstract'].str.split().str.len().fillna(0) >= 50
    df['en_abs'] = df['has_abs'] & (df['lang'].fillna('en') == 'en')
    df['n_inst'] = df['inst'].map(len)
    g = df.groupby('year')
    t = pd.DataFrame(dict(papers=g.size(), cs_primary=g['cs_primary'].sum(), venue_only=g.apply(lambda x: int((x['cs_venue'] & ~x['cs_primary']).sum())),
                          abstract50=g['has_abs'].sum(), english_abstract50=g['en_abs'].sum(), paper_inst_pairs=g['n_inst'].sum(),
                          journal=g.apply(lambda x: int((x['venue_type'] == 'journal').sum())), with_refs=g.apply(lambda x: int((x['n_refs'] > 0).sum()))))
    side = pd.read_parquet(F.work_dir() / 'corpus' / 'side_counts.parquet').pivot_table(index='year', columns='reason', values='n', aggfunc='sum').fillna(0).astype(int)
    t = t.join(side.rename(columns={'cs_any': 'not_cs_but_cs_secondary_topic', 'cs': 'not_cs_other'}))
    t.loc['total'] = t.sum()
    t.to_csv(F.work_dir() / 'corpus' / 'counts_by_year.csv')
    print(t.to_string(), flush=True)


def cmd_pilot(idx):
    """Stream the manifest parts with these indices and print the stage counts and one stored row (size and rate estimate before the full run)."""
    roster = F.load_roster()
    idtab, cs_v = id_table(roster), venues()
    parts = parts_of()
    for i in idx:
        t0 = time.time()
        rows, st, sd = stream_part(parts[i][0], idtab, cs_v, set(idtab))
        print(json.dumps(dict(part=i, seconds=int(time.time() - t0), kept=len(rows), side=sorted((f'{k[0]}-{k[1]}', v) for k, v in sd.items())[:6], **st)), flush=True)
    if rows:
        print(json.dumps({k: (v[:200] if isinstance(v, str) else v[:5] if isinstance(v, list) else v) for k, v in rows[0].items()}, default=str))


def cmd_plan(per):
    parts = parts_of()
    ch = chunks(parts, per)
    print(json.dumps(dict(parts=len(parts), chunks=len(ch), per_chunk=per, bytes=sum(p[1] for p in parts), institutions=len(F.load_roster()), ids=len(id_table(F.load_roster())), cs_venues=len(venues()))))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['plan', 'chunk', 'merge', 'counts', 'pilot'])
    ap.add_argument('i', nargs='*', type=int)
    ap.add_argument('--per', type=int, default=PER_CHUNK)
    a = ap.parse_args()
    if a.cmd == 'plan':
        cmd_plan(a.per)
    elif a.cmd == 'chunk':
        cmd_chunk(a.i[0] if a.i else int(os.environ['SLURM_ARRAY_TASK_ID']), a.per)
    elif a.cmd == 'pilot':
        cmd_pilot(a.i)
    elif a.cmd == 'merge':
        cmd_merge(a.per)
    else:
        cmd_counts()
