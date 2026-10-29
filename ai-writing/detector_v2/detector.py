"""Passage-level AI-written-text detector (v2): ModernBERT-large on single ~150-word body passages, v1's recipe.

data      human (y=0): data/humans.jsonl (25,000 passages) and the sources' own passages (18,000), all from lab papers
          published 2016-2021; AI (y=1): data/generated-<gen>.jsonl (polish / paraphrase / notes by Qwen2.5-72B,
          Qwen2.5-7B, Llama-3.3-70B). Every text goes through v2common.norm. Splits are by paper (v2common.split_of).
train     answerdotai/ModernBERT-large, max 512 tokens, AdamW 2e-5 (wd 0.01, 6% warmup, linear decay), 2 epochs, bs 16,
          bf16 autocast, classes balanced by repeating the AI passages (as v1); batches are length-bucketed.
          --holdout GEN drops that generator from training and calibration (leave-one-generator-out).
threshold the 99th percentile of the scores of every passage of the cal-split papers (59,838 passages of 1,522 papers):
          a 1% passage false-positive rate on held-out human text by design.
evaluate  AUC (AI vs every passage of the test-split papers) and TPR at the threshold per generator x task, on the
          test-split sources; for a held-out generator also on all of its outputs. Real-text check: the flagged share
          of every passage of the 2,928 test-split 2016-2021 papers (114,050), overall (paper-cluster bootstrap CI) and
          by year, school, text kind, first passage, length and extraction-quality quintile; the paper-level null
          (ai_share, ai_any) on those papers.
score     (final model) every passage of every stored full text, sharded: --shard i --nshards n
          (a contiguous rowid range of ai-writing/fulltext.sqlite per task, read in place)
          -> results/scores/shard-<i>.jsonl.gz {key, pidx, words, p}, results/scores/papers-<i>.jsonl.gz
             {key, kind, usable, body_words, n_passages}
-> models/<tag>/model (with --save), results/<tag>/metrics.json, results/<tag>/test_scores.jsonl.gz
usage: detector.py train [--holdout GEN] [--save] | detector.py score --shard I --nshards N [--db LOCAL_FULLTEXT] [--name NAME]
          (incremental: --db a store of only the not-yet-scored texts, --name e.g. d20261028-<i> -> shard-<name>.jsonl.gz)
"""
import argparse, gzip, json, os, random, sqlite3, time, zlib
from collections import defaultdict
from pathlib import Path
import numpy as np, torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup
from sklearn.metrics import roc_auc_score
import v2common as V

rng = random.Random(V.SEED)
MAXLEN = 512
SCORE_BS = 128
SMOKE = os.environ.get('AIW2_SMOKE') == '1'  # code-path test: fake AI rows, tiny sets, outputs under smoke-* names


def log(**kw):
    print(json.dumps(kw, default=str), flush=True)


def jl(path):
    op = gzip.open if str(path).endswith('.gz') else open
    with op(path, 'rt') as f:
        return [json.loads(l) for l in f]


def load():
    src = {s['sid']: s for s in jl(V.DATA / 'sources.jsonl')}
    rows = [dict(text=V.norm(s['text']), y=0, split=s['split'], kind='source_human', gen=None, task=None, key=s['key']) for s in src.values()]
    rows += [dict(text=V.norm(h['text']), y=0, split=h['split'], kind='human', gen=None, task=None, key=h['key']) for h in jl(V.DATA / 'humans.jsonl')]
    if SMOKE:
        return rows[::40] + [dict(text=V.norm(s['text']).upper(), y=1, split=s['split'], kind=s['task'], gen=s['gen'], task=s['task'], key=s['key'], sid=s['sid'])
                             for s in list(src.values())[:1500]]
    for g in V.GENS:
        p = V.DATA / f'generated-{g}.jsonl'
        if not p.exists():
            log(missing=str(p)); continue
        for r in jl(p):
            s = src[r['sid']]
            rows.append(dict(text=V.norm(r['text']), y=1, split=s['split'], kind=r['task'], gen=g, task=r['task'], key=s['key'], sid=r['sid']))
    return rows


def real(part):
    rows = jl(V.DATA / f'{part}_real.jsonl.gz')
    return [dict(r, ntext=V.norm(r['text'])) for r in (rows[::50] if SMOKE else rows)]


def train_batches(tok, rows, bs):
    """Length-bucketed: shuffle, sort within chunks of 50 batches by length, shuffle the batch order."""
    idx = list(range(len(rows))); rng.shuffle(idx)
    lens = [len(r['text']) for r in rows]
    out = []
    for c in range(0, len(idx), bs * 50):
        chunk = sorted(idx[c:c + bs * 50], key=lambda i: lens[i])
        out += [chunk[i:i + bs] for i in range(0, len(chunk), bs)]
    rng.shuffle(out)
    for b in out:
        enc = tok([rows[j]['text'] for j in b], padding=True, truncation=True, max_length=MAXLEN, return_tensors='pt')
        yield enc, torch.tensor([rows[j]['y'] for j in b])


def logits(model, enc):
    """The classification forward with the encoder under bf16 autocast and the pooling, head and classifier in fp32,
    so that the scores keep their resolution near a 1%-FPR threshold (bf16 logits come in steps of ~0.06)."""
    with torch.autocast('cuda', dtype=torch.bfloat16):
        h = model.model(input_ids=enc['input_ids'], attention_mask=enc['attention_mask'])[0]
    h, m = h.float(), enc['attention_mask'].float()
    pooled = h[:, 0] if model.config.classifier_pooling == 'cls' else (h * m.unsqueeze(-1)).sum(1) / m.sum(1, keepdim=True)
    return model.classifier(model.drop(model.head(pooled)))


@torch.inference_mode()
def predict(model, tok, texts, bs=128):
    """P(AI) in float64, from the fp32 logit difference."""
    order = np.argsort([len(t) for t in texts])
    z = np.zeros(len(texts), dtype=np.float64)
    for i in range(0, len(order), bs):
        ix = order[i:i + bs]
        enc = tok([texts[j] for j in ix], padding=True, truncation=True, max_length=MAXLEN, return_tensors='pt').to('cuda')
        lg = logits(model, enc).double()
        z[ix] = (lg[:, 1] - lg[:, 0]).cpu().numpy()
    return 1.0 / (1.0 + np.exp(-z))


def r6(x):
    return float(f'{x:.6g}')


def auc(pos, neg):
    if len(pos) == 0 or len(neg) == 0:
        return None
    return float(roc_auc_score(np.r_[np.ones(len(pos)), np.zeros(len(neg))], np.r_[pos, neg]))


def cluster_ci(flags, keys, n=1000):
    """95% CI of a passage share, resampling papers."""
    by = defaultdict(list)
    for f, k in zip(flags, keys):
        by[k].append(f)
    s = np.array([sum(v) for v in by.values()], float); c = np.array([len(v) for v in by.values()], float)
    r = np.random.default_rng(V.SEED)
    b = [s[ix].sum() / c[ix].sum() for ix in (r.integers(0, len(s), len(s)) for _ in range(n))]
    return [float(np.quantile(b, 0.025)), float(np.quantile(b, 0.975))]


def share(mask, flags):
    mask = np.asarray(mask, bool)
    return dict(n=int(mask.sum()), flagged=float(flags[mask].mean()) if mask.any() else None)


def real_check(test, p, thr):
    f = p >= thr
    keys = [r['key'] for r in test]
    q = [V.quality(r['text']) for r in test]
    words = np.array([len(r['text'].split()) for r in test])
    out = dict(passages=len(test), papers=len(set(keys)), flagged=float(f.mean()), flagged_ci95=cluster_ci(f, keys),
               by_year={y: share([r['year'] == y for r in test], f) for y in V.PRE},
               by_school={s: share([r['school'] == s for r in test], f) for s in sorted({r['school'] for r in test})},
               by_kind={k: share([r['kind'] == k for r in test], f) for k in sorted({r['kind'] for r in test})},
               first_passage=share([r['pidx'] == 0 for r in test], f), later_passages=share([r['pidx'] > 0 for r in test], f),
               by_words={f'{lo}-{hi}': share((words >= lo) & (words < hi), f) for lo, hi in ((40, 100), (100, 150), (150, 200), (200, 401))})
    for name in ('midcap', 'nonascii', 'wordish'):
        v = np.array([x[name] for x in q])
        edges = np.quantile(v, [0, .2, .4, .6, .8, 1.0])
        bins = np.clip(np.searchsorted(edges, v, side='right') - 1, 0, 4)
        out[f'by_{name}_quintile'] = {f'q{b + 1} [{edges[b]:.3f},{edges[b + 1]:.3f}]': share(bins == b, f) for b in range(5)}
    per = defaultdict(list)
    for k, x in zip(keys, f):
        per[k].append(x)
    sh = np.array([np.mean(v) for v in per.values()]); n = np.array([len(v) for v in per.values()])
    out['paper_null'] = dict(papers=len(per), mean_ai_share=float(sh.mean()), share_ai_any=float((sh > 0).mean()), share_ai_share_ge_025=float((sh >= 0.25).mean()),
                             median_passages=float(np.median(n)), expected_ai_any_if_independent=float(np.mean(1 - (1 - f.mean()) ** n)))
    return out


def gen_task_metrics(rows, p, neg_p, thr):
    out = {}
    for g in V.GENS:
        for t in V.TASKS + ('all',):
            ix = [i for i, r in enumerate(rows) if r['gen'] == g and (t == 'all' or r['task'] == t)]
            if ix:
                out[f'{g}/{t}'] = dict(n=len(ix), auc=auc(p[ix], neg_p), tpr=float((p[ix] >= thr).mean()))
    for t in V.TASKS:
        ix = [i for i, r in enumerate(rows) if r['task'] == t]
        if ix:
            out[f'all/{t}'] = dict(n=len(ix), auc=auc(p[ix], neg_p), tpr=float((p[ix] >= thr).mean()))
    return out


def train(holdout, save):
    t0 = time.time()
    rows = load()
    tr = [r for r in rows if r['split'] == 'train' and not (holdout and r['gen'] == holdout)]
    pos, neg = [r for r in tr if r['y']], [r for r in tr if not r['y']]
    rep = max(1, round(len(neg) / max(1, len(pos))))
    tr = neg + pos * rep
    log(train_human=len(neg), train_ai=len(pos), ai_repeat=rep, train_examples=len(tr), holdout=holdout)
    tok = AutoTokenizer.from_pretrained(V.snapshot(V.BASE))
    model = AutoModelForSequenceClassification.from_pretrained(V.snapshot(V.BASE), num_labels=2).cuda()
    opt = torch.optim.AdamW(model.parameters(), lr=2e-5, weight_decay=0.01); epochs, bs = (1, 16) if SMOKE else (2, 16)
    steps = epochs * ((len(tr) + bs - 1) // bs); sch = get_linear_schedule_with_warmup(opt, int(0.06 * steps), steps)
    model.train(); k = 0
    for ep in range(epochs):
        for enc, y in train_batches(tok, tr, bs):
            with torch.autocast('cuda', dtype=torch.bfloat16):
                loss = torch.nn.functional.cross_entropy(model(**enc.to('cuda')).logits.float(), y.cuda())
            loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); sch.step(); opt.zero_grad()
            if k % 500 == 0:
                log(epoch=ep, step=k, of=steps, loss=round(loss.item(), 4), minutes=round((time.time() - t0) / 60, 1))
            k += 1
    model.eval()
    tag = ('smoke-' if SMOKE else '') + (f'holdout-{holdout}' if holdout else 'all')
    out = V.RESULTS / tag; out.mkdir(parents=True, exist_ok=True)
    if save:
        (V.MODELS / tag).mkdir(parents=True, exist_ok=True)
        model.save_pretrained(V.MODELS / tag / 'model'); tok.save_pretrained(V.MODELS / tag / 'model')
    cal = real('cal')
    pc = predict(model, tok, [r['ntext'] for r in cal])
    thr = float(np.quantile(pc, 0.99))
    cal_ai = [r for r in rows if r['y'] and r['split'] == 'cal' and not (holdout and r['gen'] == holdout)]
    pca = predict(model, tok, [r['text'] for r in cal_ai])
    log(threshold=thr, cal_passages=len(cal), cal_auc=auc(pca, pc), minutes=round((time.time() - t0) / 60, 1))
    test = real('test')
    pt = predict(model, tok, [r['ntext'] for r in test])
    te_ai = [r for r in rows if r['y'] and r['split'] == 'test']
    pta = predict(model, tok, [r['text'] for r in te_ai])
    te_h = [r for r in rows if not r['y'] and r['split'] == 'test']
    pth = predict(model, tok, [r['text'] for r in te_h])
    m = dict(tag=tag, holdout=holdout, base=V.BASE, splitter_sha=V.SPLITTER_SHA, train_human=len(neg), train_ai=len(pos), ai_repeat=rep,
             threshold=thr, cal_real_passages=len(cal), cal_real_papers=len({r['key'] for r in cal}), cal_auc=auc(pca, pc),
             test_ai=len(te_ai), test_by_gen_task=gen_task_metrics(te_ai, pta, pt, thr),
             sampled_test_humans=dict(n=len(te_h), flagged=float((pth >= thr).mean()),
                                      by_kind={k: float((pth[[i for i, r in enumerate(te_h) if r['kind'] == k]] >= thr).mean()) for k in ('human', 'source_human')}),
             real_check=real_check(test, pt, thr))
    if holdout:
        ho = [r for r in rows if r['y'] and r['gen'] == holdout]
        pho = predict(model, tok, [r['text'] for r in ho])
        m['holdout_all_outputs'] = gen_task_metrics(ho, pho, pt, thr)
    m['minutes'] = round((time.time() - t0) / 60, 1)
    json.dump(m, open(out / 'metrics.json', 'w'), indent=1)
    with gzip.open(out / 'test_scores.jsonl.gz', 'wt') as f:
        for r, s in zip(test, pt):
            f.write(json.dumps(dict(set='test_real', key=r['key'], pidx=r['pidx'], p=r6(s))) + '\n')
        for r, s in zip(te_ai, pta):
            f.write(json.dumps(dict(set='test_ai', key=r['key'], sid=r['sid'], gen=r['gen'], task=r['task'], p=r6(s))) + '\n')
    log(**{k: v for k, v in m.items() if k not in ('real_check', 'test_by_gen_task', 'holdout_all_outputs')})
    log(test_by_gen_task=m['test_by_gen_task'])
    log(real_flagged=m['real_check']['flagged'], ci=m['real_check']['flagged_ci95'], by_year=m['real_check']['by_year'])


def score(shard, nshards, db_path=None, name=None):
    db_path = db_path or V.FULLTEXT
    name = name or str(shard)  # --name: output file suffix, so a delta store's shards sit beside the full run's (merge.py globs shard-*)
    t0 = time.time()
    tag = V.MODELS / ('smoke-all' if SMOKE else 'all') / 'model'
    tok = AutoTokenizer.from_pretrained(tag)
    model = AutoModelForSequenceClassification.from_pretrained(tag).cuda().eval()
    db = sqlite3.connect(f'file:{db_path}?mode=ro&immutable=1', uri=True)
    hi = db.execute('select max(rowid) from texts').fetchone()[0]
    step = hi // nshards + 1; lo = shard * step  # a contiguous rowid range: each task reads only its part of the store
    keys, pidx, words, texts, papers = [], [], [], [], []
    for key, kind, body, flags in db.execute('select key, kind, body, flags from texts where rowid >= ? and rowid < ?' + (' limit 60' if SMOKE else ''), (lo, lo + step)):
        body = zlib.decompress(body).decode('utf-8', 'ignore') if body else ''
        ps = V.passages(body) if body else []
        papers.append(dict(key=key, kind=kind, usable=bool(body) and V.usable_text(kind, body, json.loads(flags or '{}')),
                           body_words=len(body.split()), n_passages=len(ps)))
        for i, t in enumerate(ps):
            keys.append(key); pidx.append(i); words.append(len(t.split())); texts.append(V.norm(t))
    db.close()
    log(shard=shard, passages=len(texts), papers=len(set(keys)), minutes=round((time.time() - t0) / 60, 1))
    p = predict(model, tok, texts, bs=SCORE_BS)
    out = V.RESULTS / ('smoke-scores' if SMOKE else 'scores'); out.mkdir(parents=True, exist_ok=True)
    tmp = out / f'tmp_shard-{name}.jsonl.gz'
    with gzip.open(tmp, 'wt') as f:
        for k, i, w, s in zip(keys, pidx, words, p):
            f.write(json.dumps(dict(key=k, pidx=i, words=w, p=r6(s))) + '\n')
    tmp.replace(out / f'shard-{name}.jsonl.gz')
    with gzip.open(out / f'papers-{name}.jsonl.gz', 'wt') as f:
        for r in papers:
            f.write(json.dumps(r) + '\n')
    log(shard=shard, done=len(texts), minutes=round((time.time() - t0) / 60, 1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd'); ap.add_argument('--holdout'); ap.add_argument('--save', action='store_true')
    ap.add_argument('--shard', type=int); ap.add_argument('--nshards', type=int); ap.add_argument('--db'); ap.add_argument('--name')
    a = ap.parse_args()
    train(a.holdout, a.save) if a.cmd == 'train' else score(a.shard, a.nshards, a.db, a.name)
