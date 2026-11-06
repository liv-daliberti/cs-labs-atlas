"""Binoculars-style zero-shot score (Hong et al. 2024) with two open LMs, for the ensemble.

observer Qwen2.5-1.5B (base), performer Qwen2.5-1.5B-Instruct. score = log-perplexity of the text under the observer divided
by the cross-perplexity (cross-entropy of the observer's next-token distribution against the performer's); low = machine-like.
Computed for the same passages, in the same order, as detector3.score writes (cal / test real, cal / test AI, held-out families'
train-split AI): results/bino/scores.npz {cal_real, test_real, ai, ai_train} (score, log-ppl, x-ppl per passage).
usage: bino3.py (resumable; chunks results/bino/<set>-<i>.npy, order: ai, cal_real, test_real; ai_train is skipped)
"""
import time
import numpy as np, torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import v3common as C
import detector3 as D3

V = C.V
MAXTOK = 256


@torch.inference_mode()
def feats(obs, per, tok, texts, bs=10):
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


def chunked(name, rows, obs, per, tok, t0, budget, step=10000):
    """Features of rows in chunks of `step`, each saved as results/bino/<name>-<i>.npy (a chunk that exists is skipped)."""
    d = C.RESULTS / 'bino'; d.mkdir(parents=True, exist_ok=True)
    for i in range(0, len(rows), step):
        p = d / f'{name}-{i // step}.npy'
        if p.exists():
            continue
        if (time.time() - t0) / 60 > budget:
            return False
        np.save(p, feats(obs, per, tok, [V.norm(r['text']) for r in rows[i:i + step]]))
        D3.log(chunk=p.name, minutes=round((time.time() - t0) / 60, 1))
    return True


def main():
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(V.snapshot('Qwen/Qwen2.5-1.5B'), padding_side='right')
    obs = AutoModelForCausalLM.from_pretrained(V.snapshot('Qwen/Qwen2.5-1.5B'), torch_dtype=torch.bfloat16).cuda().eval()
    per = AutoModelForCausalLM.from_pretrained(V.snapshot('Qwen/Qwen2.5-1.5B-Instruct'), torch_dtype=torch.bfloat16).cuda().eval()
    ai = D3.ai_rows()
    sets = [('ai', [r for r in ai if r['split'] in ('cal', 'test')]), ('cal_real', D3.jl(C.DATA / 'cal_real3.jsonl.gz')),
            ('test_real', D3.jl(C.DATA / 'test_real3.jsonl.gz'))]
    for name, rows in sets:
        if not chunked(name, rows, obs, per, tok, t0, 48):
            D3.log(paused=name); return
    D3.log(done=True, minutes=round((time.time() - t0) / 60, 1))


if __name__ == '__main__':
    main()
