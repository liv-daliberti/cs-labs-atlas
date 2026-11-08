"""Career-age input for the heterogeneity analysis: the publication-year histogram of every PI's OpenAlex author profile(s).

The sealed snapshot holds each PI's OpenAlex author ids (release hierarchy/<school>/pis.json: reviewedOpenAlex, else oaAuthorIds) but no author records, so this step
asks OpenAlex once: works?filter=author.id:A1|A2|...&group_by=publication_year (one credit per request, <= 50 ids per request) and stores the counts per
year in <results>/heterogeneity/work/pi_career.jsonl (one JSON line per PI; restartable: PIs already in the file are skipped). It never touches the snapshot.
Budget: one credit per PI (about 2,550 in total) through tools/oa_api.Client, which keeps the key out of every message and logs to the shared ledger;
it stops at --cap credits or when fewer than --floor credits remain on the shared key.
usage: study_hetero_authors.py [--id 2026-11-08] [--cap 2800] [--floor 3500]
"""
import argparse
import json
import time

import study_common as C

import oa_api  # noqa: E402  (tools/ is on sys.path through study_common)


def pi_ids(snap):
    """[(school, pi, [author ids])] for every PI of the 12 schools."""
    out = []
    for s in C.SCHOOLS:
        for q in json.loads((snap / 'release' / 'hierarchy' / s / 'pis.json').read_text()):
            ids = q.get('reviewedOpenAlex') or q.get('oaAuthorIds') or []
            out.append((s, q['pi'], sorted({C.oa_short(i) for i in ids if i}), 'reviewed' if q.get('reviewedOpenAlex') else 'oaAuthorIds'))
    return out


def fetch_years(client, ids):
    years = {}
    for i in range(0, len(ids), 50):
        j, _ = client.get('works', {'filter': 'author.id:' + '|'.join(ids[i:i + 50]), 'group_by': 'publication_year', 'per_page': 200}, kind='career')
        for g in (j or {}).get('group_by', []):
            if str(g['key']).isdigit():
                years[str(g['key'])] = years.get(str(g['key']), 0) + int(g['count'])
    return years


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', default='2026-11-08')
    ap.add_argument('--cap', type=int, default=2800)
    ap.add_argument('--floor', type=int, default=3500)
    a = ap.parse_args()
    snap = C.snapshot_dir(a.id)
    out = C.results_dir(a.id) / 'heterogeneity' / 'work'
    out.mkdir(parents=True, exist_ok=True)
    f = out / 'pi_career.jsonl'
    done = {(r['school'], r['pi']) for r in map(json.loads, f.read_text().splitlines())} if f.exists() else set()
    todo = [x for x in pi_ids(snap) if (x[0], x[1]) not in done]
    print(len(done), 'done,', len(todo), 'to fetch', flush=True)
    client = oa_api.Client(cap=a.cap, kind='study-hetero', floor=a.floor)
    client.pause = 0.4
    t0 = time.time()
    with f.open('a') as fh:
        for n, (s, pi, ids, basis) in enumerate(todo):
            years = fetch_years(client, ids) if ids else {}
            fh.write(json.dumps(dict(school=s, pi=pi, n_ids=len(ids), basis=basis, years=years)) + '\n')
            fh.flush()
            if n % 200 == 0:
                print(n, round(time.time() - t0), 's, credits used', client.used, 'remaining', client.remaining, flush=True)
    print('finished; credits used', client.used, 'remaining', client.remaining)


if __name__ == '__main__':
    main()
