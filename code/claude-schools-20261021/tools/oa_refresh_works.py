"""Refresh a school's recent OpenAlex works in the stores the build reads (ROADMAP #24 follow-up, 2026-11-05).

The sweeps (hierarchy/<school>/raw/openalex-sweep.sqlite) and pi-works.sqlite are snapshots of the API on the day they were pulled; OpenAlex then
creates, changes and merges records, so the current year drifts (2026-11-04: Princeton's API count was 7,804, the sweep held 7,075 distinct papers).
The API has no `from_updated_date`/`from_created_date` filter or updated/created sort on this key (HTTP 429 "Plan upgrade required": daily sync is a
paid plan), so a refresh is a full re-pull of the recent years under the sweep's own filter. Two steps, the API step costs credits and writes only to
scratch, the merge step is local:

  fetch  <school>... [--years 2026,2025] [--cap N]
         -> <SCRATCH>/oa-refresh-<tag>/<school>.sqlite. Per year: the sweep's filter (`authorships.institutions.lineage:<charter ids>,authors_count:<101`,
         `publication_year:Y`) minus datasets (`type:!dataset`: datasets are not papers (NOT_PAPERS), they are 20-75% of a school's records and a
         third of the credits; the stored dataset records are left as they are), cursor paging at 200; one count query per year for the report; and the
         school's PI author ids (pis.json oaAuthorIds[:6] + reviewedOpenAlex, 25 per query) for the same years. Resumable (cursor per page).
         Every request goes through tools/oa_api.py: key redacted everywhere, one ledger line each in raw/openalex_budget.jsonl, a hard credit cap.
  merge  <school>... [--apply]
         the stored years of the sweep are replaced by (old records minus the dropped ones) updated with the fresh ones, in the same page layout
         (cursor 'refresh:<tag>'); the PI works are inserted or replaced by id in pi-works.sqlite. A record the API no longer returns is
         reconciled: the same DOI under a fresh id = merged into it (old id dropped, not duplicated); otherwise a singleton lookup follows the
         redirect (merged: dropped), a 404 drops it, an id that still resolves without redirect is kept (de-credited, reported). A school whose sweep
         came from the snapshot (uchicago, gatech) applies the snapshot's own keep rule (per-affiliation exclusion and related-id gate) to the API
         records. A dry run prints the per-school report and writes nothing; --apply first copies the replaced rows to <stage>/backup-<school>.sqlite.
  report <school>...   the numbers of the last merge (JSON per school).

Repeat before each release: `atlas pipeline`-less, see docs/RUNBOOK.md "Refresh the recent OpenAlex works". Tests: tests/test_oa_refresh_works.py.
"""
import argparse
import json
import re
import sqlite3
import sys
import time
import zlib

import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
import oa_api  # noqa: E402

SELECT = 'id,doi,title,publication_year,publication_date,type,authorships,ids,primary_location,locations'
SWEEP_FIELDS = ('id', 'doi', 'title', 'publication_year', 'publication_date', 'type', 'authorships', 'ids', 'primary_location')
PAGE = 200
TAG = '20261105'


def stage_dir(tag=TAG):
    d = P.SCRATCH / f'oa-refresh-{tag}'
    d.mkdir(parents=True, exist_ok=True)
    return d


def short(i):
    return (i or '').rsplit('/', 1)[-1]


def pack(o):
    return zlib.compress(json.dumps(o, ensure_ascii=False).encode(), 6)


def unpack(b):
    return json.loads(zlib.decompress(b))


def project(w):
    return {k: w.get(k) for k in SWEEP_FIELDS if k in w}


def pi_author_ids(school):
    pis = json.load(open(P.data('pis.json', school)))
    return sorted({short(a) for p in pis for a in (p.get('oaAuthorIds') or [])[:6] + (p.get('reviewedOpenAlex') or []) if a})


def inst_filter(school, year):
    return f'authorships.institutions.lineage:{"|".join(S.sweep_ids(school))},authors_count:<101,publication_year:{year}'


# ------------------------------------------------------------------ fetch
def stage_db(school, tag=TAG):
    c = sqlite3.connect(str(stage_dir(tag) / f'{school}.sqlite'), timeout=60)
    c.execute('create table if not exists pages (kind text, key text, page int, next_cursor text, n int, count int, fetched_at text, body blob, primary key (kind, key, page))')
    c.execute('create table if not exists done (kind text, key text, n int, primary key (kind, key))')
    c.execute('create table if not exists counts (key text primary key, count int, at text)')
    return c


def count(cl, c, key, flt):
    r = c.execute('select count from counts where key=?', (key,)).fetchone()
    if r:
        return r[0]
    j, _ = cl.get('works', {'filter': flt, 'per-page': 1, 'select': 'id'}, kind='count')
    c.execute('insert or replace into counts values (?,?,?)', (key, j['meta']['count'], time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())))
    c.commit()
    return j['meta']['count']


def fetch_query(cl, c, school, kind, key, flt):
    if c.execute('select 1 from done where kind=? and key=?', (kind, key)).fetchone():
        return
    last = c.execute('select page, next_cursor from pages where kind=? and key=? order by page desc limit 1', (kind, key)).fetchone()
    page, cursor = (last[0] + 1, last[1]) if last else (0, '*')
    n = 0
    while cursor:
        j, _ = cl.get('works', {'filter': flt, 'per-page': PAGE, 'cursor': cursor, 'select': SELECT}, kind=f'{school}:{kind}')
        nxt = j['meta'].get('next_cursor') if j['results'] else None
        c.execute('insert or replace into pages values (?,?,?,?,?,?,?,?)', (kind, key, page, nxt, len(j['results']), j['meta']['count'],
                  time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), pack(j['results'])))
        c.commit()
        n += len(j['results'])
        page += 1
        cursor = nxt
    c.execute('insert or replace into done values (?,?,?)', (kind, key, n))
    c.commit()
    print(json.dumps(dict(school=school, kind=kind, key=key[:60], works=n, credits_used=cl.used, remaining=cl.remaining)), flush=True)


def fetch(school, years, cl, tag=TAG, pi=True):
    c = stage_db(school, tag)
    for y in years:
        base = inst_filter(school, y)
        count(cl, c, f'all:{y}', base)                      # for the report: the API's count under the sweep's own filter, all types
        fetch_query(cl, c, school, 'inst', str(y), base + ',type:!dataset')
    if pi:
        ids = pi_author_ids(school)
        yr = f'{min(years)}-{max(years)}' if len(years) > 1 else str(years[0])
        for i in range(0, len(ids), 25):
            batch = '|'.join(ids[i:i + 25])
            fetch_query(cl, c, school, 'pi', batch, f'author.id:{batch},publication_year:{yr},type:!dataset')
    c.close()


def fetch_ids(school, ids, cl, tag=TAG, batch=50):
    """Fetch OpenAlex works by id (a list of `W...`/URL ids the build lost: batched `ids.openalex:` filter, `batch` ids per call, no cursor paging) into the
    stage store as kind 'pi' pages (key `ids:<first id>`), so `merge --ids-only --apply` inserts them into pi-works.sqlite like any PI work. The ids the API
    returns nothing for (merged away, deleted) are listed in table `missing`. Resumable: a batch already stored is skipped. Returns (fetched, missing)."""
    c = stage_db(school, tag)
    c.execute('create table if not exists missing (id text primary key)')
    want = sorted({short(i) for i in ids if i})
    got = 0
    for i in range(0, len(want), batch):
        part = want[i:i + batch]
        key = 'ids:' + part[0]
        if c.execute('select 1 from done where kind=? and key=?', ('pi', key)).fetchone():
            got += c.execute('select n from done where kind=? and key=?', ('pi', key)).fetchone()[0]
            continue
        j, _ = cl.get('works', {'filter': 'ids.openalex:' + '|'.join(part), 'per-page': batch, 'select': SELECT}, kind=f'{school}:ids')
        res = (j or {}).get('results') or []
        returned = {short(w['id']) for w in res}
        for w in res:   # a merged id comes back under its canonical id: both are accounted for
            returned |= {short(x) for x in (w.get('ids') or {}).get('openalex', '').split('|') if x}
        c.execute('insert or replace into pages values (?,?,?,?,?,?,?,?)', ('pi', key, 0, None, len(res), len(res), time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), pack(res)))
        for m in part:
            if m not in returned:
                c.execute('insert or ignore into missing values (?)', (m,))
        c.execute('insert or replace into done values (?,?,?)', ('pi', key, len(res)))
        c.commit()
        got += len(res)
        print(json.dumps(dict(school=school, kind='ids', batch=key, asked=len(part), works=len(res), credits_used=cl.used, remaining=cl.remaining)), flush=True)
    missing = [r[0] for r in c.execute('select id from missing order by id')]
    c.close()
    return got, missing


# ------------------------------------------------------------------ merge
def sweep_source(sc):
    """The snapshot date when the school's sweep came from the snapshot (tools/sweep_from_snapshot.py writes a meta table), else None."""
    if not sc.execute("select count(*) from sqlite_master where name='meta'").fetchone()[0]:
        return None
    r = sc.execute("select value from meta where key='source'").fetchone()
    return json.loads(r[0]).get('snapshot_date') if r else None


def keeper(school):
    """The snapshot's keep rule for this school (per-affiliation exclusion, related-id gate, ENCODE drop): a work -> bool."""
    import oa_snapshot as O
    cfg = S.get(school)
    inst, excl = set(S.sweep_ids(school)), set(cfg['ids'].get('openalex_excluded') or [])
    rel = O.related_gates([school])
    return lambda w: O.keep_work(w, inst - excl, excl, set(), rel) is not None


def load_year(sc, y):
    out = {}
    for (b,) in sc.execute('select body from pages where year=? order by page', (y,)):
        for w in unpack(b):
            out[w['id']] = w
    return out


def fresh_records(stc, kind, year=None):
    out = {}
    for key, b in stc.execute('select key, body from pages where kind=? order by key, page', (kind,)):
        if kind == 'inst' and year is not None and key != str(year):
            continue
        for w in unpack(b):
            out[w['id']] = w
    return out


def lookup_redirect(cl, wid):
    """('merged', target id) | ('gone', None) | ('alive', None) for an id the list queries no longer return (a singleton fetch, not followed)."""
    j, _ = cl.get(f'works/{short(wid)}', {'select': 'id'}, kind='singleton')
    if j is None:
        return 'gone', None
    if 'redirect' in j:
        return 'merged', 'https://openalex.org/' + short(j['redirect'])
    return ('merged', j['id']) if j.get('id') and short(j['id']) != short(wid) else ('alive', None)


def merge(school, years, tag=TAG, apply=False, cl=None, lookups=0, guard=None):
    stc = sqlite3.connect(str(stage_dir(tag) / f'{school}.sqlite'))
    sweep_path = P.data_w('openalex-sweep.sqlite', school)
    sc = sqlite3.connect(str(sweep_path), timeout=120)
    done_years = {int(k) for (k,) in stc.execute("select key from done where kind='inst'")}
    years = [y for y in years if y in done_years]   # a year that was never fetched must not look like 'everything was removed'
    snap = sweep_source(sc)
    ok = keeper(school) if snap else (lambda w: True)
    pis = set(pi_author_ids(school))
    rep = dict(school=school, tag=tag, sweep_source=f'snapshot:{snap}' if snap else 'api', years={}, pi={})
    all_fresh = {}
    for y in years:
        all_fresh.update({i: w for i, w in fresh_records(stc, 'inst', y).items() if ok(w)})
    doi_to_id = {}
    for i, w in all_fresh.items():
        if w.get('doi'):
            doi_to_id.setdefault(w['doi'].lower(), i)
    merged_map = {}
    new_pages = {}
    for y in years:
        old = load_year(sc, y)
        fresh = {i: w for i, w in fresh_records(stc, 'inst', y).items() if ok(w)}
        np_old = {i for i, w in old.items() if w.get('type') != 'dataset'}
        removed = sorted(np_old - set(fresh))
        why = dict(doi=0, redirect=0, gone=0, alive=0, unresolved=0)
        drop = set()
        for i in removed:
            t = doi_to_id.get((old[i].get('doi') or '').lower())
            if t and t != i:
                merged_map[i] = t; drop.add(i); why['doi'] += 1
        for i in removed:
            if i in drop:
                continue
            if cl is None or lookups <= 0:
                why['unresolved'] += 1; continue
            lookups -= 1
            kind, t = lookup_redirect(cl, i)
            if kind == 'merged':
                merged_map[i] = t; drop.add(i); why['redirect'] += 1
            elif kind == 'gone':
                drop.add(i); why['gone'] += 1
            else:
                why['alive'] += 1
        new_ids = sorted(set(fresh) - set(old))
        changed = sum(1 for i in fresh if i in old and project(old[i]) != project(fresh[i]))
        new_store = {i: w for i, w in old.items() if i not in drop}
        for i, w in fresh.items():
            new_store[i] = project(w)
        ours_before, ours_after = len(old), len(new_store)
        np_before, np_after = len(np_old), sum(1 for w in new_store.values() if w.get('type') != 'dataset')
        api_all = stc.execute('select count from counts where key=?', (f'all:{y}',)).fetchone()
        api_np = stc.execute("select max(count) from pages where kind='inst' and key=?", (str(y),)).fetchone()
        new_pi = len([i for i in new_ids if any(short((a.get('author') or {}).get('id')) in pis for a in fresh[i].get('authorships') or [])])
        rep['years'][y] = dict(api_all=api_all and api_all[0], api_papers=api_np and api_np[0], fetched=len(fresh), ours_before=ours_before, ours_after=ours_after,
                               papers_before=np_before, papers_after=np_after, new=len(new_ids), changed=changed, dropped=len(drop), merged_ids=len([i for i in drop if i in merged_map]),
                               not_returned_reasons=why, new_pi_credited=new_pi)
        new_pages[y] = (new_store, old)
    # pi works
    pi_w = fresh_records(stc, 'pi')
    pc = sqlite3.connect(str(P.data_w('pi-works.sqlite', school)), timeout=120)
    have = {r[0] for r in pc.execute('select id from works')}
    dois_have = {}
    for i, b in pc.execute('select id, body from works'):
        d = (unpack(b).get('doi') or '').lower()
        if d:
            dois_have.setdefault(d, []).append(i)
    pi_new = [i for i in pi_w if i not in have]
    pi_stale = sorted({o for i, w in pi_w.items() for o in dois_have.get((w.get('doi') or '').lower(), []) if o != i and o in have} | {i for i in merged_map if i in have})
    rep['pi'] = dict(fetched=len(pi_w), new=len(pi_new), rows_before=len(have), stale_ids_replaced=len(pi_stale), rows_after=len(have) + len(pi_new) - len(pi_stale),
                     new_pi_credited_in_sweep=sum(v['new_pi_credited'] for v in rep['years'].values()))
    rep['years'] = {str(k): v for k, v in rep['years'].items()}
    if apply:
        if guard:
            guard()   # raises when the stores must not be written now (tools/oa_repull_trickle.py: a release build is running)
        bk = sqlite3.connect(str(stage_dir(tag) / f'backup-{school}.sqlite'))
        bk.execute('create table if not exists sweep_pages (year int, page int, cursor text, next_cursor text, n int, count int, fetched_at text, body blob)')
        bk.execute('create table if not exists pi_works (id text, body blob)')
        now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        for y, (new_store, old) in new_pages.items():
            if bk.execute('select count(*) from sweep_pages where year=?', (y,)).fetchone()[0]:
                raise SystemExit(f'{school}: backup of year {y} already exists in the stage dir; merge --apply runs once per tag')
            for row in sc.execute('select year, page, cursor, next_cursor, n, count, fetched_at, body from pages where year=?', (y,)):
                bk.execute('insert into sweep_pages values (?,?,?,?,?,?,?,?)', row)
            ws = [new_store[i] for i in sorted(new_store)]
            sc.execute('delete from pages where year=?', (y,))
            for p in range(max(1, (len(ws) + PAGE - 1) // PAGE)):
                chunk = ws[p * PAGE:(p + 1) * PAGE]
                sc.execute('insert into pages values (?,?,?,?,?,?,?,?)', (y, p, f'refresh:{tag}', None, len(chunk), len(ws), now, pack(chunk)))
        sc.execute('create table if not exists refreshes (tag text, years text, fetched_at text, report text)')
        sc.execute('insert into refreshes values (?,?,?,?)', (tag, ','.join(map(str, years)), now, json.dumps(rep)))
        sc.commit()
        for i in pi_stale:
            r = pc.execute('select body from works where id=?', (i,)).fetchone()
            if r:
                bk.execute('insert into pi_works values (?,?)', (i, r[0]))
            pc.execute('delete from works where id=?', (i,))
        for i, w in pi_w.items():
            if i in have:
                r = pc.execute('select body from works where id=?', (i,)).fetchone()
                if r:
                    bk.execute('insert into pi_works values (?,?)', (i, r[0]))
            pc.execute('insert or replace into works values (?,?)', (i, pack(w)))
        pc.commit(); bk.commit(); bk.close()
        rep['applied'] = now
        (stage_dir(tag) / f'report-{school}.json').write_text(json.dumps(rep, indent=1))
    sc.close(); pc.close(); stc.close()
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    f = sub.add_parser('fetch'); f.add_argument('schools', nargs='+'); f.add_argument('--years', default='2026'); f.add_argument('--cap', type=int, default=1000)
    f.add_argument('--floor', type=int, default=8000); f.add_argument('--tag', default=TAG); f.add_argument('--no-pi', action='store_true')
    f.add_argument('--ids', help='fetch these OpenAlex ids (a file, one W id or URL per line) instead of years: batched ids.openalex filter, 50 per call; one school')
    m = sub.add_parser('merge'); m.add_argument('schools', nargs='+'); m.add_argument('--years', default='2026'); m.add_argument('--apply', action='store_true')
    m.add_argument('--ids-only', action='store_true', help='merge only the PI works of the stage store (a `fetch --ids` tag): no sweep year is touched')
    m.add_argument('--tag', default=TAG); m.add_argument('--lookups', type=int, default=0, help='singleton lookups allowed for ids the DOI map cannot resolve (API credits)')
    m.add_argument('--cap', type=int, default=100)
    r = sub.add_parser('report'); r.add_argument('schools', nargs='+'); r.add_argument('--tag', default=TAG)
    a = ap.parse_args(argv)
    years = [int(y) for y in re.split(r'[,+]', getattr(a, 'years', '2026'))]  # '+' because sbatch --export splits values on commas
    if a.cmd == 'merge' and a.ids_only:
        years = []
    if a.cmd == 'fetch' and a.ids:
        if len(a.schools) != 1:
            ap.error('--ids takes one school')
        cl = oa_api.Client(cap=a.cap, kind='repull-ids', floor=a.floor)
        ids = [l.split('#')[0].strip() for l in open(a.ids) if l.split('#')[0].strip()]
        try:
            got, missing = fetch_ids(a.schools[0], ids, cl, a.tag)
        except oa_api.Spent as e:
            print(json.dumps(dict(school=a.schools[0], stopped=str(e), credits_used=cl.used))); return 2
        print(json.dumps(dict(school=a.schools[0], asked=len(set(ids)), fetched=got, missing=len(missing), requests=cl.requests, credits_used=cl.used, remaining=cl.remaining)))
        return 0
    if a.cmd == 'fetch':
        cl = oa_api.Client(cap=a.cap, kind='refresh2026', floor=a.floor)
        for s in a.schools:
            try:
                fetch(s, years, cl, a.tag, pi=not a.no_pi)
            except oa_api.Spent as e:
                print(json.dumps(dict(school=s, stopped=str(e), credits_used=cl.used))); return 2
    elif a.cmd == 'merge':
        cl = oa_api.Client(cap=a.cap, kind='refresh2026', floor=8000) if a.lookups else None
        for s in a.schools:
            print(json.dumps(merge(s, years, a.tag, a.apply, cl, a.lookups)), flush=True)
    else:
        for s in a.schools:
            p = stage_dir(a.tag) / f'report-{s}.json'
            print(p.read_text() if p.exists() else json.dumps(dict(school=s, report=None)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
