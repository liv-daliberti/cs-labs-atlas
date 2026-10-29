"""Merge the scoring shards into the per-passage and per-paper files, and the flagged share by year and school.

flag      p >= the final model's threshold (results/all/metrics.json: 1% of every passage of the cal-split
          2016-2021 papers flagged).
passages  -> passage_scores.jsonl.gz {key, pidx, words, p_ai, flagged}, every passage of every stored full text
papers    -> paper_ai_fulltext.jsonl.gz {key, school, year, kind, usable, split, n_passages, n_flagged, ai_share, ai_any,
             mean_p, n_paragraphs}; ai_share = n_flagged / n_passages (DESIGN-v2's dose), ai_any = n_flagged >= 1,
             n_paragraphs = n_passages (the name diversity/common.load_ai reads). split is the detector's paper split
             for 2016-2021 papers (train-split papers lent passages to training; 'test' papers never did), '' after.
by year   -> results/flagged_by_year_school.csv: usable full texts, 2016-2026, per year x school (and 'all'): papers,
             passages, the flagged passage share with a paper-bootstrap 95% CI, the mean paper ai_share, the share of
             papers with ai_any and with ai_share >= 0.25; for 2016-2021 also the same over test-split papers only.
publish   (--publish) ai-writing/paragraph_scores.jsonl.gz {key, n_paragraphs, n_flagged, ai_share, ai_any, mean_p}, one row
             per usable full text with >= 1 passage, the file diversity/common.load_ai switches to. Written last, to a
             temporary name and renamed, and only when the final model passes the held-out gate (gate()).
usage: merge.py [--publish]
"""
import argparse, csv, glob, gzip, json, os
from collections import defaultdict
import numpy as np
import v2common as V


def boot(s, c, n=1000, seed=V.SEED):
    if len(s) == 0:
        return (None, None)
    r = np.random.default_rng(seed)
    b = [s[ix].sum() / max(1, c[ix].sum()) for ix in (r.integers(0, len(s), len(s)) for _ in range(n))]
    return float(np.quantile(b, 0.025)), float(np.quantile(b, 0.975))


def gate():
    """The held-out checks the final model must pass before the battery may read its scores: on every passage of the
    2,928 test-split 2016-2021 papers, the flagged share <= 1.5% overall and <= 2% in every year; on the test-split AI
    passages, AUC >= 0.95 and TPR >= 0.5 for every generator."""
    m = json.load(open(V.RESULTS / 'all' / 'metrics.json'))
    rc = m['real_check']; why = []
    if rc['flagged'] > 0.015:
        why.append(f"real flagged {rc['flagged']:.4f} > 0.015")
    for y, v in rc['by_year'].items():
        if v['flagged'] is not None and v['flagged'] > 0.02:
            why.append(f"{y} flagged {v['flagged']:.4f} > 0.02")
    for g in V.GENS:
        r = m['test_by_gen_task'].get(f'{g}/all')
        if not r or r['auc'] < 0.95 or r['tpr'] < 0.5:
            why.append(f'{g}: {r}')
    return not why, why


def publish(recs):
    ok, why = gate()
    print(json.dumps(dict(gate_passed=ok, failures=why)))
    if not ok:
        return
    dst = V.AIW / 'paragraph_scores.jsonl.gz'; tmp = V.AIW / '.tmp_paragraph_scores.jsonl.gz'
    n = 0
    with gzip.open(tmp, 'wt') as f:
        for r in recs:
            if r['usable'] and r['n_passages']:
                f.write(json.dumps(dict(key=r['key'], n_paragraphs=r['n_passages'], n_flagged=r['n_flagged'], ai_share=r['ai_share'],
                                        ai_any=r['ai_any'], mean_p=r['mean_p'])) + '\n'); n += 1
    os.replace(tmp, dst)
    print(json.dumps(dict(published=str(dst), papers=n)))


def main(do_publish=False):
    thr = json.load(open(V.RESULTS / 'all' / 'metrics.json'))['threshold']
    meta = {}
    for line in gzip.open(V.AIW / 'papers.jsonl.gz', 'rt'):
        p = json.loads(line)
        try:
            y = int(p.get('year'))
        except (TypeError, ValueError):
            y = None
        meta[p['key']] = (p['school'], y)
    papers = {}
    for f in sorted(glob.glob(str(V.RESULTS / 'scores' / 'papers-*.jsonl.gz'))):
        for line in gzip.open(f, 'rt'):
            r = json.loads(line); papers[r['key']] = r
    agg = defaultdict(lambda: [0, 0, 0.0])
    n_pass = 0
    shards = sorted(glob.glob(str(V.RESULTS / 'scores' / 'shard-*.jsonl.gz')))
    rows = []
    for f in shards:
        for line in gzip.open(f, 'rt'):
            r = json.loads(line)
            rows.append((r['key'], r['pidx'], r['words'], r['p']))
    rows.sort()
    with gzip.open(V.HERE / 'passage_scores.jsonl.gz', 'wt') as out:
        for k, i, w, p in rows:
            fl = p >= thr
            out.write(json.dumps(dict(key=k, pidx=i, words=w, p_ai=p, flagged=fl)) + '\n')
            a = agg[k]; a[0] += 1; a[1] += fl; a[2] += p; n_pass += 1
    del rows
    recs = []
    with gzip.open(V.HERE / 'paper_ai_fulltext.jsonl.gz', 'wt') as out:
        for k in sorted(papers):
            pr = papers[k]; school, year = meta.get(k, (None, None))
            n, nf, sp = agg.get(k, [0, 0, 0.0])
            r = dict(key=k, school=school, year=year, kind=pr['kind'], usable=pr['usable'], split=V.split_of(k) if year in V.PRE else '',
                     n_passages=n, n_flagged=nf, ai_share=round(nf / n, 5) if n else None, ai_any=bool(nf) if n else None,
                     mean_p=round(sp / n, 5) if n else None, n_paragraphs=n)
            out.write(json.dumps(r) + '\n'); recs.append(r)
    sel = [r for r in recs if r['usable'] and r['n_passages'] and r['year'] in range(2016, 2027)]
    table = []
    for y in range(2016, 2027):
        for s in V_SCHOOLS + ('all',):
            for scope in ('all papers', 'test-split papers') if y in V.PRE else ('all papers',):
                g = [r for r in sel if r['year'] == y and (s == 'all' or r['school'] == s) and (scope == 'all papers' or r['split'] == 'test')]
                if not g:
                    continue
                nf = np.array([r['n_flagged'] for r in g], float); n = np.array([r['n_passages'] for r in g], float)
                sh = nf / n
                lo, hi = boot(nf, n)
                table.append(dict(year=y, school=s, scope=scope, papers=len(g), passages=int(n.sum()), flagged_share=round(float(nf.sum() / n.sum()), 5),
                                  ci_lo=round(lo, 5), ci_hi=round(hi, 5), mean_ai_share=round(float(sh.mean()), 5),
                                  share_ai_any=round(float((nf > 0).mean()), 4), share_ai_share_ge_025=round(float((sh >= 0.25).mean()), 4)))
    with open(V.RESULTS / 'flagged_by_year_school.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(table[0])); w.writeheader(); w.writerows(table)
    summary = dict(threshold=thr, shards=len(shards), passages_scored=n_pass, texts_scored=len(papers), texts_with_passages=sum(1 for r in recs if r['n_passages']),
                   usable_papers_2016_2026=len(sel), usable_passages_2016_2026=int(sum(r['n_passages'] for r in sel)),
                   flagged_passages=int(sum(r['n_flagged'] for r in recs)))
    json.dump(dict(summary=summary, table=table), open(V.RESULTS / 'flagged_by_year_school.json', 'w'), indent=1)
    print(json.dumps(summary))
    for t in table:
        if t['school'] == 'all':
            print(json.dumps(t))
    if do_publish:
        publish(recs)


V_SCHOOLS = ('princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford')

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--publish', action='store_true')
    main(ap.parse_args().publish)
