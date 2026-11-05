"""AI-writing detector v3: ModernBERT-large on ~150-word passages, v2's recipe with far more data, resumable training.

data   human (y=0): train-split 2016-2021 passages (data/human_train.jsonl.gz, ~all of them): HUMAN_RANDOM random ones plus
       the HARD_FRAC hardest by v2's score (hard-negative mining; v2 scores from detector_v2/passage_scores.jsonl.gz).
       AI (y=1): v2's generators (qwen72b, qwen7b, llama70b: polish / paraphrase / notes) and the ten v3 generators (six tasks),
       train-split sources only, partial edits only when >= half of the words were rewritten; repeated AI_REPEAT times.
       --holdout FAMILY drops that family's outputs from training (leave-one-family-out).
train  AdamW 2e-5, 2 epochs, bs 16, bf16 autocast with fp32 pooling/head (v2); checkpoints (model + optimizer + position) in
       models/<tag>/ckpt, so the job stops after --budget minutes and the same command resumes (Slurm limit 59 min).
score  `score --tag T`: logit of every cal / test real passage (v2 files), every cal / test AI passage (v2 and v3 generators)
       and the human originals -> results/<tag>/scores.npz (z = logit(P(AI)), float32).
usage: detector3.py train --tag T [--holdout FAMILY] [--budget MIN] | detector3.py score --tag T
"""
import argparse, gzip, json, os, random, time
import numpy as np, torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup
import v3common as C
import detector as D2  # v2: predict/logits (fp32 head)

V = C.V
MAXLEN = 512
BS, EPOCHS, LR = 16, 2, 2e-5
HUMAN_RANDOM, HARD_N, AI_REPEAT = 95000, 22000, 2
SMOKE = os.environ.get('AIW3_SMOKE') == '1'


def log(**kw):
    print(json.dumps(kw, default=str), flush=True)


def jl(path):
    with (gzip.open if str(path).endswith('.gz') else open)(path, 'rt') as f:
        return [json.loads(l) for l in f]


def v2_scores():
    d = {}
    for r in jl(C.AIW / 'detector_v2' / 'passage_scores.jsonl.gz'):
        d[(r['key'], r['pidx'])] = r['p_ai']
    return d


def ai_rows():
    """Every AI passage: dict(text, split, gen, family, task, key, sid, ai_frac)."""
    src = {s['sid']: s for s in jl(C.V2DATA / 'sources.jsonl')}
    rows = []
    for g in ('qwen72b', 'qwen7b', 'llama70b'):
        for r in jl(C.V2DATA / f'generated-{g}.jsonl'):
            s = src[r['sid']]
            rows.append(dict(text=r['text'], split=s['split'], gen=g, family=C.FAMILY[g], task=r['task'], key=s['key'], sid=f'v2-{g}-{r["sid"]}', ai_frac=1.0))
    for g in C.V3GENS:
        for i in range(0, 40):
            p = C.DATA / 'gen3' / f'{g}-{i}.jsonl.gz'
            if not p.exists():
                break
            for r in jl(p):
                rows.append(dict(text=r['text'], split=r['split'], gen=g, family=r['family'], task=r['task'], key=r['key'], sid=r['sid'], ai_frac=r['ai_frac']))
    return rows


def train_rows(holdout):
    rng = random.Random(C.SEED)
    hum = jl(C.DATA / 'human_train.jsonl.gz')
    sc = v2_scores()
    for h in hum:
        h['v2p'] = sc.get((h['key'], h['pidx']), 0.0)
    hum.sort(key=lambda h: -h['v2p'])
    hard, rest = hum[:HARD_N], hum[HARD_N:]
    rng.shuffle(rest)
    neg = [dict(text=V.norm(h['text']), y=0) for h in hard + rest[:HUMAN_RANDOM]]
    pos = [dict(text=V.norm(r['text']), y=1) for r in ai_rows()
           if r['split'] == 'train' and r['family'] != holdout and (r['task'] != 'partial' or r['ai_frac'] >= 0.5)]
    log(train_human=len(neg), hard=len(hard), hard_p_min=hard[-1]['v2p'], train_ai=len(pos), holdout=holdout)
    rows = neg + pos * AI_REPEAT
    if SMOKE:
        rows = rows[::400] + pos[:200]
    return rows


def epoch_batches(rows, ep):
    r = random.Random(f'{C.SEED}|{ep}')
    idx = list(range(len(rows))); r.shuffle(idx)
    lens = [len(x['text']) for x in rows]
    out = []
    for c in range(0, len(idx), BS * 50):
        ch = sorted(idx[c:c + BS * 50], key=lambda i: lens[i])
        out += [ch[i:i + BS] for i in range(0, len(ch), BS)]
    r.shuffle(out)
    return out


def train(tag, holdout, budget):
    t0 = time.time()
    ck = C.MODELS / tag / 'ckpt'; ck.mkdir(parents=True, exist_ok=True)
    final = C.MODELS / tag / 'model'
    if (final / 'config.json').exists():
        log(done=tag); return
    rows = train_rows(holdout)
    tok = AutoTokenizer.from_pretrained(V.snapshot(V.BASE))
    model = AutoModelForSequenceClassification.from_pretrained(V.snapshot(V.BASE), num_labels=2).cuda()
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=0.01)
    nb = (len(rows) + BS - 1) // BS
    epochs = 1 if SMOKE else EPOCHS
    sch = get_linear_schedule_with_warmup(opt, int(0.06 * epochs * nb), epochs * nb)
    pos = dict(ep=0, step=0)
    if (ck / 'meta.json').exists():
        pos = json.load(open(ck / 'meta.json'))
        st = torch.load(ck / 'state.pt', map_location='cuda')
        model.load_state_dict(st['model']); opt.load_state_dict(st['opt']); sch.load_state_dict(st['sch']); del st
        log(resumed=pos)
    model.train()

    def save(p):
        torch.save(dict(model=model.state_dict(), opt=opt.state_dict(), sch=sch.state_dict()), ck / 'state.tmp')
        (ck / 'state.tmp').replace(ck / 'state.pt'); json.dump(p, open(ck / 'meta.json', 'w'))

    for ep in range(pos['ep'], epochs):
        batches = epoch_batches(rows, ep)
        for k in range(pos['step'] if ep == pos['ep'] else 0, len(batches)):
            if (time.time() - t0) / 60 > budget:
                save(dict(ep=ep, step=k)); log(paused=dict(ep=ep, step=k, of=len(batches)), minutes=round((time.time() - t0) / 60, 1)); return
            b = batches[k]
            enc = tok([rows[j]['text'] for j in b], padding=True, truncation=True, max_length=MAXLEN, return_tensors='pt').to('cuda')
            y = torch.tensor([rows[j]['y'] for j in b]).cuda()
            with torch.autocast('cuda', dtype=torch.bfloat16):
                loss = torch.nn.functional.cross_entropy(model(**enc).logits.float(), y)
            loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); sch.step(); opt.zero_grad()
            if k % 500 == 0:
                log(epoch=ep, step=k, of=len(batches), loss=round(loss.item(), 4), minutes=round((time.time() - t0) / 60, 1))
        pos = dict(ep=ep + 1, step=0)
    model.eval()
    final.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(final); tok.save_pretrained(final)
    json.dump(dict(tag=tag, holdout=holdout, train_examples=len(rows), epochs=epochs), open(C.MODELS / tag / 'train.json', 'w'))
    for f in ck.iterdir():
        f.unlink()
    log(finished=tag)


def score(tag):
    t0 = time.time()
    path = C.AIW / 'detector_v2' / 'models' / 'all' / 'model' if tag == 'v2' else C.MODELS / tag / 'model'
    tok = AutoTokenizer.from_pretrained(path)
    model = AutoModelForSequenceClassification.from_pretrained(path).cuda().eval()
    out = dict()

    def z(texts):
        p = D2.predict(model, tok, texts)  # float64 P(AI)
        return np.log(np.clip(p, 1e-300, None)) - np.log(np.clip(1 - p, 1e-300, None))

    meta = {}
    for part in ('cal', 'test'):
        rows = jl(C.DATA / f'{part}_real3.jsonl.gz')
        if SMOKE:
            rows = rows[::100]
        out[f'{part}_real_z'] = z([V.norm(r['text']) for r in rows]).astype(np.float32)
        meta[f'{part}_real'] = [dict(key=r['key'], pidx=r['pidx'], school=r['school'], year=r['year'], kind=r['kind'], words=len(r['text'].split()),
                                     **V.quality(r['text'])) for r in rows]
        log(part=part, n=len(rows), minutes=round((time.time() - t0) / 60, 1))
    ai = [r for r in ai_rows() if r['split'] in ('cal', 'test')]
    if SMOKE:
        ai = ai[::50]
    out['ai_z'] = z([V.norm(r['text']) for r in ai]).astype(np.float32)
    meta['ai'] = [dict({k: v for k, v in r.items() if k != 'text'}, words=len(r['text'].split()), midcap=V.quality(r['text'])['midcap']) for r in ai]
    tr = [r for r in ai_rows() if r['split'] == 'train' and r['family'] in C.HELD]  # held-out families' unseen train-split outputs
    tr = tr[:: (50 if SMOKE else 1)]
    out['ai_train_z'] = z([V.norm(r['text']) for r in tr]).astype(np.float32)
    meta['ai_train'] = [dict({k: v for k, v in r.items() if k != 'text'}, words=len(r['text'].split()), midcap=V.quality(r['text'])['midcap']) for r in tr]
    d = C.RESULTS / tag; d.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(d / 'scores.npz', **out)
    with gzip.open(d / 'scores_meta.jsonl.gz', 'wt') as f:
        f.write(json.dumps(meta))
    log(scored=tag, minutes=round((time.time() - t0) / 60, 1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd'); ap.add_argument('--tag', required=True); ap.add_argument('--holdout')
    ap.add_argument('--budget', type=float, default=44)
    a = ap.parse_args()
    train(a.tag, a.holdout, a.budget) if a.cmd == 'train' else score(a.tag)
