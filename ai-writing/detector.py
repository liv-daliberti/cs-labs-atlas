"""The AI-written-text detector: ModernBERT-large fine-tuned on title + abstract, human (before ChatGPT) vs LLM-written.

data     human: humans.jsonl (12,000) and the sources' own abstracts (3,000), all published 2016-2021;
         AI: generated-<model>.jsonl (polish and outline-then-expand versions of the sources).
         Splits are by source paper (a source's own abstract and its AI versions share a split), 80/10/10, and so are
         the further human abstracts. A model can be held out entirely (--holdout) to measure generalization to an
         unseen generator.
train    answerdotai/ModernBERT-large, max 512 tokens, AdamW 2e-5, 2 epochs, bf16, balanced batches.
threshold the score at which 1% of the validation human abstracts are flagged (a 1% false-positive rate by design).
score    every lab paper with an abstract of 50+ words -> scores.jsonl.gz {key, p_ai, flagged}
-> ai-writing/detector/ (model, metrics.json), ai-writing/scores.jsonl.gz
usage: detector.py train [--holdout MODEL] | detector.py score
"""
import argparse, glob, gzip, json, random, re
from pathlib import Path
import numpy as np, torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score

HERE = Path(__file__).resolve().parent; OUT = HERE / 'detector'; BASE = 'answerdotai/ModernBERT-large'
rng = random.Random(20261022)


def norm(t):
    """The same surface for every text, human or generated, training or scoring: OpenAlex abstracts arrive as one line of
    words, so line breaks, markdown, HTML tags and leading 'Abstract' labels are removed and whitespace collapsed; the
    detector can then only use the wording."""
    t = re.sub(r'<[^>]+>', ' ', str(t or '')); t = re.sub(r'\*\*|__|^#+\s*', '', t, flags=re.M)
    t = re.sub(r'^\s*(?:abstract|summary)\s*[:.\-—]?\s*', '', t, flags=re.I)
    return re.sub(r'\s+', ' ', t).strip()


def text(title, abstract):
    return f'{norm(title)} | {norm(abstract)}'


def split_of(key):
    h = int.from_bytes(key.encode()[-8:].ljust(8, b'0'), 'little') % 10
    return 'test' if h == 0 else 'val' if h == 1 else 'train'


def load(holdout=None):
    src = {json.loads(l)['key']: json.loads(l) for l in open(HERE / 'sources.jsonl')}
    rows = [dict(text=text(s['title'], s['abstract']), y=0, split=split_of(k), kind='source_human', model=None) for k, s in src.items()]
    rows += [dict(text=text(h['title'], h['abstract']), y=0, split=split_of(h['key']), kind='human', model=None)
             for h in map(json.loads, open(HERE / 'humans.jsonl'))]
    for f in glob.glob(str(HERE / 'generated-*.jsonl')):
        for g in map(json.loads, open(f)):
            s = src[g['key']]
            if len(g['text'].split()) < 40:
                continue
            sp = 'test' if holdout and g['model'] == holdout else split_of(g['key'])
            rows.append(dict(text=text(s['title'], g['text']), y=1, split=sp, kind=g['task'], model=g['model']))
    return rows


def batches(tok, rows, bs, shuffle):
    idx = list(range(len(rows)))
    if shuffle:
        rng.shuffle(idx)
    for i in range(0, len(idx), bs):
        b = [rows[j] for j in idx[i:i + bs]]
        enc = tok([r['text'] for r in b], padding=True, truncation=True, max_length=512, return_tensors='pt')
        yield enc, torch.tensor([r['y'] for r in b])


@torch.inference_mode()
def predict(model, tok, texts, bs=64):
    out = []
    for i in range(0, len(texts), bs):
        enc = tok(texts[i:i + bs], padding=True, truncation=True, max_length=512, return_tensors='pt').to('cuda')
        with torch.autocast('cuda', dtype=torch.bfloat16):
            out += torch.softmax(model(**enc).logits.float(), -1)[:, 1].tolist()
    return np.array(out)


def train(holdout):
    rows = load(holdout)
    tr = [r for r in rows if r['split'] == 'train' and not (holdout and r['model'] == holdout)]
    pos, neg = [r for r in tr if r['y']], [r for r in tr if not r['y']]
    tr = neg + pos * max(1, round(len(neg) / max(1, len(pos))))  # balance classes by repeating the AI texts
    tok = AutoTokenizer.from_pretrained(BASE); model = AutoModelForSequenceClassification.from_pretrained(BASE, num_labels=2).cuda()
    opt = torch.optim.AdamW(model.parameters(), lr=2e-5, weight_decay=0.01); epochs, bs = 2, 16
    steps = epochs * (len(tr) + bs - 1) // bs; sch = get_linear_schedule_with_warmup(opt, int(0.06 * steps), steps)
    model.train()
    for ep in range(epochs):
        for k, (enc, y) in enumerate(batches(tok, tr, bs, True)):
            with torch.autocast('cuda', dtype=torch.bfloat16):
                loss = torch.nn.functional.cross_entropy(model(**enc.to('cuda')).logits.float(), y.cuda())
            loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); sch.step(); opt.zero_grad()
            if k % 200 == 0:
                print(json.dumps(dict(epoch=ep, step=k, loss=round(loss.item(), 4))), flush=True)
    model.eval()
    val = [r for r in rows if r['split'] == 'val' and not (holdout and r['model'] == holdout)]
    pv = predict(model, tok, [r['text'] for r in val]); yv = np.array([r['y'] for r in val])
    thr = float(np.quantile(pv[yv == 0], 0.99))  # 1% of held-out human abstracts flagged
    te = [r for r in rows if r['split'] == 'test']
    pt = predict(model, tok, [r['text'] for r in te]); yt = np.array([r['y'] for r in te]); ft = pt >= thr
    m = dict(holdout=holdout, base=BASE, train=len(tr), val=len(val), test=len(te), threshold=thr,
             val_auc=float(roc_auc_score(yv, pv)), test_auc=float(roc_auc_score(yt, pt)), test_f1=float(f1_score(yt, ft)),
             test_precision=float(precision_score(yt, ft)), test_recall=float(recall_score(yt, ft)), test_fpr_human=float(ft[yt == 0].mean()),
             recall_by_model={mm: float(ft[[i for i, r in enumerate(te) if r['model'] == mm]].mean()) for mm in sorted({r['model'] for r in te if r['model']})},
             recall_by_task={tt: float(ft[[i for i, r in enumerate(te) if r['kind'] == tt]].mean()) for tt in ('polish', 'outline')})
    tag = f'holdout-{holdout}' if holdout else 'all'
    (OUT / tag).mkdir(parents=True, exist_ok=True); json.dump(m, open(OUT / tag / 'metrics.json', 'w'), indent=1)
    model.save_pretrained(OUT / tag / 'model'); tok.save_pretrained(OUT / tag / 'model')
    print(json.dumps(m))


def score():
    tag = OUT / 'all'; m = json.load(open(tag / 'metrics.json'))
    tok = AutoTokenizer.from_pretrained(tag / 'model'); model = AutoModelForSequenceClassification.from_pretrained(tag / 'model').cuda().eval()
    papers = [json.loads(l) for l in gzip.open(HERE / 'papers.jsonl.gz', 'rt')]
    papers = [p for p in papers if p['abstract'] and len(p['abstract'].split()) >= 50 and p['title']]
    p = predict(model, tok, [text(x['title'], x['abstract']) for x in papers])
    with gzip.open(HERE / 'scores.jsonl.gz', 'wt') as f:
        for x, s in zip(papers, p):
            f.write(json.dumps(dict(key=x['key'], school=x['school'], year=x['year'], p_ai=round(float(s), 5), flagged=bool(s >= m['threshold']))) + '\n')
    print(json.dumps(dict(scored=len(papers), flagged=int((p >= m['threshold']).sum()))))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd'); ap.add_argument('--holdout'); a = ap.parse_args()
    train(a.holdout) if a.cmd == 'train' else score()
