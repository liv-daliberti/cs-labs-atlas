"""Detector v4 candidates: v3's recipe (ModernBERT-large, 2 epochs, same data, same batches/seeds) with ONE change per variant.

  tri   route 1, re-label: three classes, 0 human / 1 AI-written (notes, continue) / 2 AI-edited (polish, paraphrase, humanize,
        partial >= half rewritten). Any-AI score z = log(P1+P2) - log P0 (what v3 scores); written-only score zw = log P1 - log(P0+P2).
        Batches are identical to v3's (same rows, same order), only the labels differ.
  pair  route 2, paired/contrastive: each light-edit AI passage is trained together with its human source (adjacent in the batch)
        under CE plus a margin loss softplus(MARGIN - (z_ai - z_src)), z = logit1 - logit0. The paired sources replace the same
        number of random human negatives, so the number of sequences and steps equals v3's.
  base  v3 itself (control: same code path, for checking that the harness reproduces v3).
  Selection among variants uses the unseen family's TRAIN-split outputs (never the test split).
usage: detector4.py train --tag T --variant tri|pair|base [--holdout FAMILY] [--budget MIN] | detector4.py score --tag T --variant V
"""
import argparse, gzip, json, os, random, time
import numpy as np, torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup
import v4common as K
import detector3 as D3
import detector as D2

C, V = D3.C, K.V
BS, EPOCHS, LR, MAXLEN = D3.BS, D3.EPOCHS, D3.LR, D3.MAXLEN
MARGIN, LAM = 4.0, 1.0   # fixed a priori (no sweep)
SMOKE = os.environ.get('AIW3_SMOKE') == '1'
log, jl = D3.log, D3.jl


BASE = V.BASE


def fwd(model, enc):
    """Logits with the encoder in bf16 autocast and pooling/head in fp32 (resolution near the 0.3% threshold); ModernBERT or DeBERTa."""
    if hasattr(model, 'deberta'):
        with torch.autocast('cuda', dtype=torch.bfloat16):
            h = model.deberta(input_ids=enc['input_ids'], attention_mask=enc['attention_mask'])[0]
        return model.classifier(model.dropout(model.pooler(h.float())))
    return D2.logits(model, enc)


def sources():
    out = {}
    v2 = {s['sid']: s for s in jl(C.V2DATA / 'sources.jsonl')}
    for g in ('qwen72b', 'qwen7b', 'llama70b'):
        for r in jl(C.V2DATA / f'generated-{g}.jsonl'):
            out[f'v2-{g}-{r["sid"]}'] = v2[r['sid']]['text']
    for s in jl(C.DATA / 'sources3.jsonl'):
        out[s['sid']] = s['text']
    return out


def build(holdout, variant):
    """Units: list of dict(seqs=[(text, y)], pair=bool). Base/tri: one sequence per unit, v3's exact row order."""
    rng = random.Random(C.SEED)
    hum = jl(C.DATA / 'human_train.jsonl.gz')
    sc = D3.v2_scores()
    for h in hum:
        h['v2p'] = sc.get((h['key'], h['pidx']), 0.0)
    hum.sort(key=lambda h: -h['v2p'])
    hard, rest = hum[:D3.HARD_N], hum[D3.HARD_N:]
    rng.shuffle(rest)
    neg = [dict(text=V.norm(h['text']), y=0) for h in hard + rest[:D3.HUMAN_RANDOM]]
    arows = [r for r in D3.ai_rows(False) if r['split'] == 'train' and r['family'] != holdout and (r['task'] != 'partial' or r['ai_frac'] >= 0.5)]
    pos = [dict(text=V.norm(r['text']), y=1, task=r['task'], sid=r['sid']) for r in arows]
    if variant == 'tri':
        for p in pos:
            p['y'] = 1 if p['task'] in K.WRITTEN_TASKS else 2
    log(variant=variant, train_human=len(neg), train_ai=len(pos), holdout=holdout, edits=sum(p['task'] in K.EDIT_TASKS for p in pos))
    if variant in ('base', 'tri'):
        rows = neg + pos * D3.AI_REPEAT
        units = [dict(seqs=[(r['text'], r['y'])], pair=False) for r in rows]
    else:
        src = sources()
        units, n_pair = [], 0
        for _ in range(D3.AI_REPEAT):
            for p in pos:
                if p['task'] in K.EDIT_TASKS and src.get(p['sid']):
                    units.append(dict(seqs=[(V.norm(src[p['sid']]), 0), (p['text'], 1)], pair=True)); n_pair += 1
                else:
                    units.append(dict(seqs=[(p['text'], 1)], pair=False))
        keep = len(neg) - n_pair
        units += [dict(seqs=[(r['text'], 0)], pair=False) for r in neg[:keep]]  # the hard negatives come first in neg: the tail is the random part
        log(pairs=n_pair, negatives_kept=keep)
    if SMOKE:
        units = units[::400] + [u for u in units if u['pair']][:50]
    return units


def make_batches(units, ep):
    r = random.Random(f'{C.SEED}|{ep}')
    idx = list(range(len(units))); r.shuffle(idx)
    lens = [len(u['seqs'][0][0]) for u in units]
    out = []
    for c in range(0, len(idx), BS * 50):
        ch = sorted(idx[c:c + BS * 50], key=lambda i: lens[i])
        cur, n = [], 0
        for i in ch:
            k = len(units[i]['seqs'])
            if n + k > BS and cur:
                out.append(cur); cur, n = [], 0
            cur.append(i); n += k
        if cur:
            out.append(cur)
    r.shuffle(out)
    return out


def train(tag, variant, holdout, budget):
    t0 = time.time()
    ck = K.MODELS / tag / 'ckpt'; ck.mkdir(parents=True, exist_ok=True)
    final = K.MODELS / tag / 'model'
    if (final / 'config.json').exists():
        log(done=tag); return
    units = build(holdout, variant)
    tok = AutoTokenizer.from_pretrained(V.snapshot(BASE))
    ncls = 3 if variant == 'tri' else 2
    model = AutoModelForSequenceClassification.from_pretrained(V.snapshot(BASE), num_labels=ncls).cuda()
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=0.01)
    nb = len(make_batches(units, 0))
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
        batches = make_batches(units, ep)
        for k in range(pos['step'] if ep == pos['ep'] else 0, len(batches)):
            if (time.time() - t0) / 60 > budget:
                save(dict(ep=ep, step=k)); log(paused=dict(ep=ep, step=k, of=len(batches)), minutes=round((time.time() - t0) / 60, 1)); return
            seqs = [s for i in batches[k] for s in units[i]['seqs']]
            enc = tok([s[0] for s in seqs], padding=True, truncation=True, max_length=MAXLEN, return_tensors='pt').to('cuda')
            y = torch.tensor([s[1] for s in seqs]).cuda()
            if hasattr(model, 'deberta'):
                lg = fwd(model, enc).float()
            else:  # exactly v3's training forward
                with torch.autocast('cuda', dtype=torch.bfloat16):
                    lg = model(**enc).logits.float()
            loss = F.cross_entropy(lg, y)
            if variant == 'pair':
                z = lg[:, 1] - lg[:, 0]; off = 0; d = []
                for i in batches[k]:
                    n = len(units[i]['seqs'])
                    if units[i]['pair']:
                        d.append(z[off + 1] - z[off])
                    off += n
                if d:
                    loss = loss + LAM * F.softplus(MARGIN - torch.stack(d)).mean()
            loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); sch.step(); opt.zero_grad()
            if k % 500 == 0:
                log(epoch=ep, step=k, of=len(batches), loss=round(loss.item(), 4), minutes=round((time.time() - t0) / 60, 1))
        pos = dict(ep=ep + 1, step=0)
    model.eval()
    final.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(final); tok.save_pretrained(final)
    json.dump(dict(tag=tag, base=BASE, variant=variant, holdout=holdout, units=len(units), epochs=epochs), open(K.MODELS / tag / 'train.json', 'w'))
    for f in ck.iterdir():
        f.unlink()
    log(finished=tag)


@torch.inference_mode()
def predict_logits(model, tok, texts, bs=128):
    order = np.argsort([len(t) for t in texts])
    lg = None
    for i in range(0, len(order), bs):
        ix = order[i:i + bs]
        enc = tok([texts[j] for j in ix], padding=True, truncation=True, max_length=MAXLEN, return_tensors='pt').to('cuda')
        l = fwd(model, enc).double().cpu().numpy()
        if lg is None:
            lg = np.zeros((len(texts), l.shape[1]))
        lg[ix] = l
    return lg


def zs(lg):
    """(z, zw): any-AI log-odds, and AI-written-only log-odds (equal to z for two classes)."""
    if lg.shape[1] == 2:
        z = lg[:, 1] - lg[:, 0]
        return z, z
    lse = lambda a: np.logaddexp.reduce(a, axis=1)  # noqa: E731
    return lse(lg[:, 1:]) - lg[:, 0], lg[:, 1] - lse(lg[:, [0, 2]])


def score(tag, variant):
    t0 = time.time()
    d = K.RESULTS / tag; d.mkdir(parents=True, exist_ok=True)
    path = K.MODELS / tag / 'model'
    tok = AutoTokenizer.from_pretrained(path)
    model = AutoModelForSequenceClassification.from_pretrained(path).cuda().eval()
    stride = 100 if SMOKE else 1

    def part(name, texts, fn_meta):
        f = d / f'part-{name}.npz'
        if f.exists():
            return np.load(f)['lg']
        lg = predict_logits(model, tok, texts)
        np.savez_compressed(f.with_suffix('.tmp.npz'), lg=lg.astype(np.float32)); f.with_suffix('.tmp.npz').replace(f)
        log(part=name, n=len(texts), minutes=round((time.time() - t0) / 60, 1))
        return lg

    meta, out = {}, {}
    for pt in ('cal', 'test'):
        rows = jl(C.DATA / f'{pt}_real3.jsonl.gz')[::stride]
        lg = part(f'{pt}_real', [V.norm(r['text']) for r in rows], None)
        out[f'{pt}_real_lg'] = lg
        meta[f'{pt}_real'] = [dict(key=r['key'], pidx=r['pidx'], school=r['school'], year=r['year'], kind=r['kind'], words=len(r['text'].split()), **V.quality(r['text'])) for r in rows]
    allr = D3.ai_rows()
    ai = [r for r in allr if r['split'] in ('cal', 'test')][::50 if SMOKE else 1]
    out['ai_lg'] = part('ai', [V.norm(r['text']) for r in ai], None)
    meta['ai'] = [dict({k: v for k, v in r.items() if k != 'text'}, words=len(r['text'].split()), midcap=V.quality(r['text'])['midcap']) for r in ai]
    tr = [r for r in allr if r['split'] == 'train' and r['family'] in C.HELD][::50 if SMOKE else 1]
    out['ai_train_lg'] = part('ai_train', [V.norm(r['text']) for r in tr], None)
    meta['ai_train'] = [dict({k: v for k, v in r.items() if k != 'text'}, words=len(r['text'].split()), midcap=V.quality(r['text'])['midcap']) for r in tr]
    save = {}
    for k in ('cal_real', 'test_real', 'ai', 'ai_train'):
        z, zw = zs(out[f'{k}_lg'])
        save[f'{k}_z' if k.endswith('real') else (f'{k}_z')] = z.astype(np.float32)
        save[f'{k}_zw'] = zw.astype(np.float32)
        save[f'{k}_lg'] = out[f'{k}_lg'].astype(np.float32)
    np.savez_compressed(d / 'scores.npz', **save)
    with gzip.open(d / 'scores_meta.jsonl.gz', 'wt') as f:
        f.write(json.dumps(meta))
    log(scored=tag, minutes=round((time.time() - t0) / 60, 1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd'); ap.add_argument('--tag', required=True); ap.add_argument('--variant', required=True)
    ap.add_argument('--holdout'); ap.add_argument('--base', default=V.BASE); ap.add_argument('--budget', type=float, default=44)
    a = ap.parse_args()
    BASE = a.base
    train(a.tag, a.variant, a.holdout, a.budget) if a.cmd == 'train' else score(a.tag, a.variant)
