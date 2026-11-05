"""Binoculars-style zero-shot score (Hong et al. 2024) with two open LMs, for the ensemble.

observer Qwen2.5-1.5B (base), performer Qwen2.5-1.5B-Instruct. score = log-perplexity of the text under the observer divided
by the cross-perplexity (cross-entropy of the observer's next-token distribution against the performer's); low = machine-like.
Computed for the same passages, in the same order, as detector3.score writes (cal / test real, cal / test AI, held-out families'
train-split AI): results/bino/scores.npz {cal_real, test_real, ai, ai_train} (score, log-ppl, x-ppl per passage).
usage: bino3.py
"""
import time
import numpy as np, torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import v3common as C
import detector3 as D3

V = C.V
MAXTOK = 320


@torch.inference_mode()
def feats(obs, per, tok, texts, bs=48):
    order = np.argsort([len(t) for t in texts]); out = np.zeros((len(texts), 3), np.float32)
    for i in range(0, len(order), bs):
        ix = order[i:i + bs]
        enc = tok([texts[j] for j in ix], return_tensors='pt', padding=True, truncation=True, max_length=MAXTOK).to('cuda')
        lo = obs(**enc).logits[:, :-1].float(); lp = per(**enc).logits[:, :-1].float()
        tgt = enc['input_ids'][:, 1:]; m = enc['attention_mask'][:, 1:].float()
        lso = torch.log_softmax(lo, -1)
        nll = -lso.gather(-1, tgt.unsqueeze(-1)).squeeze(-1)
        x = -(torch.softmax(lp, -1) * lso).sum(-1)
        n = m.sum(1).clamp(min=1)
        a, b = (nll * m).sum(1) / n, (x * m).sum(1) / n
        out[ix] = torch.stack([a / b, a, b], 1).cpu().numpy()
    return out


def main():
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(V.snapshot('Qwen/Qwen2.5-1.5B'), padding_side='right')
    obs = AutoModelForCausalLM.from_pretrained(V.snapshot('Qwen/Qwen2.5-1.5B'), torch_dtype=torch.bfloat16).cuda().eval()
    per = AutoModelForCausalLM.from_pretrained(V.snapshot('Qwen/Qwen2.5-1.5B-Instruct'), torch_dtype=torch.bfloat16).cuda().eval()
    res = {}
    for part in ('cal', 'test'):
        rows = D3.jl(C.DATA / f'{part}_real3.jsonl.gz')
        res[f'{part}_real'] = feats(obs, per, tok, [V.norm(r['text']) for r in rows]); D3.log(part=part, n=len(rows), minutes=round((time.time() - t0) / 60, 1))
    ai = D3.ai_rows()
    a = [r for r in ai if r['split'] in ('cal', 'test')]
    res['ai'] = feats(obs, per, tok, [V.norm(r['text']) for r in a])
    tr = [r for r in ai if r['split'] == 'train' and r['family'] in C.HELD]
    res['ai_train'] = feats(obs, per, tok, [V.norm(r['text']) for r in tr])
    d = C.RESULTS / 'bino'; d.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(d / 'scores.npz', **res)
    D3.log(done=True, minutes=round((time.time() - t0) / 60, 1))


if __name__ == '__main__':
    main()
