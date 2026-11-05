"""Embed the study's texts with one model on one GPU: resumable, sharded, parts written atomically.

  embed.py run --model M --kind abstract|fulltext [--shard i --of n] [--budget SECONDS] [--limit N] [--store-name NAME] [--texts-db PATH]
  embed.py merge --model M --kind K            parts -> one container per home school (CPU job; store.merge)
  embed.py status [--model M]                  papers todo / done per model and kind
  embed.py selftest --model M                  a few abstracts in fp16 vs fp32 (GPU): cosine must be > 0.99

A paper belongs to shard int(sha1(paper id)) % n, so shards stay disjoint while the todo list shrinks. A run reads the todo from EMB/texts.sqlite
(abstract rows; full-text rows with usable = 1), skips every paper whose text hash is already in a part or container, and writes a part per
PART papers. No new part starts after --budget seconds; the next job resumes. Never loads anything on the login host: run through embed.slurm.
"""
import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
import zlib

import numpy as np

import ecommon as C
import store
from models import MODELS

PART = {'abstract': 3000, 'fulltext': 200}
PART_8K = 40   # full-text papers per part for the 8k-token models (a 59-minute task must finish a part)


# ---------------------------------------------------------------- pure helpers (tested on fixtures)
def shard_of(pid, n):
    return int(hashlib.sha1(pid.encode()).hexdigest()[:8], 16) % n


def windows(ids, size, cap, min_tail):
    """Consecutive windows of `size` token ids; a tail shorter than min_tail is dropped unless it is the only window; more than `cap`
    windows keep `cap` evenly spaced ones."""
    if not ids:
        return []
    w = [ids[i:i + size] for i in range(0, len(ids), size)]
    if len(w) > 1 and len(w[-1]) < min_tail:
        w.pop()
    if len(w) > cap:
        w = [w[i] for i in np.linspace(0, len(w) - 1, cap).round().astype(int)]
    return w


def make_batches(lengths, budget, max_items=256):
    """Index arrays over items sorted by length, each batch's padded size (items x longest) within `budget` tokens (a single longer item
    gets its own batch)."""
    order = np.argsort(lengths, kind='stable')
    out, i = [], 0
    while i < len(order):
        j = i + 1
        while j < len(order) and (j - i + 1) * lengths[order[j]] <= budget and j - i < max_items:
            j += 1
        out.append(order[i:j])
        i = j
    return out


def merge_sparse(dicts):
    """Max over a paper's chunks of {token id: weight}; returned as sorted (idx int32, val float16)."""
    best = {}
    for d in dicts:
        for k, v in d.items():
            if v > best.get(k, 0.0):
                best[k] = v
    ks = sorted(best)
    return np.array(ks, np.int32), np.array([best[k] for k in ks], np.float16)


# ---------------------------------------------------------------- the model
class Embedder:
    def __init__(self, key, dtype='float16', device=None):
        import torch
        self.torch = torch
        self.key, self.cfg = key, dict(MODELS[key])
        # EMB_BUDGET_SCALE (float, default 1): multiplies the per-batch padded-token budget, which models.py sizes for an 8 GB RTX 2080; node105's
        # 24 GB A5000 runs 2-3x. An env override so the 2080 defaults stay as they are; a batch that still runs out of memory is split.
        self.cfg['budget'] = int(self.cfg['budget'] * float(os.environ.get('EMB_BUDGET_SCALE', 1)))
        cfg = self.cfg
        C.use_extras()
        from transformers import AutoModel, AutoTokenizer
        self.dev = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.dtype = getattr(torch, dtype) if self.dev == 'cuda' else torch.float32
        kw = dict(torch_dtype=self.dtype)
        if cfg.get('remote'):
            kw.update(trust_remote_code=True, rotary_scaling_factor=2)
        else:
            kw.update(attn_implementation='sdpa')
        self.tok = AutoTokenizer.from_pretrained(cfg['hf'], trust_remote_code=bool(cfg.get('remote')))
        if cfg.get('adapter'):
            from adapters import AutoAdapterModel
            self.model = AutoAdapterModel.from_pretrained(cfg['hf'], torch_dtype=self.dtype)
            self.model.load_adapter(cfg['adapter'], source='hf', load_as=cfg['adapter_name'], set_active=True)
        else:
            try:
                self.model = AutoModel.from_pretrained(cfg['hf'], **kw)
            except (TypeError, ValueError):
                kw.pop('attn_implementation', None)
                self.model = AutoModel.from_pretrained(cfg['hf'], **kw)
        self.model = self.model.to(self.dev, self.dtype).eval()   # adapter weights load as float32
        self.sparse = None
        if cfg.get('sparse'):
            from huggingface_hub import hf_hub_download
            w = torch.load(hf_hub_download(cfg['hf'], 'sparse_linear.pt'), map_location='cpu')
            self.sparse = torch.nn.Linear(w['weight'].shape[1], 1)
            self.sparse.load_state_dict(w)
            self.sparse = self.sparse.to(self.dev, self.dtype).eval()
        self.special = set(self.tok.all_special_ids)
        self.prefix_ids = self.tok(cfg['prefix'], add_special_tokens=False)['input_ids'] if cfg['prefix'] else []
        self.revision = self._revision()
        C.log(model=key, hf=cfg['hf'], revision=self.revision, device=torch.cuda.get_device_name(0) if self.dev == 'cuda' else 'cpu', dtype=str(self.dtype))

    def _revision(self):
        from huggingface_hub import snapshot_download
        try:
            rev = os.path.basename(snapshot_download(self.cfg['hf'], local_files_only=True))
        except Exception:
            rev = getattr(getattr(self.model, 'config', None), '_commit_hash', None) or 'unknown'
        if self.cfg.get('adapter'):
            try:
                rev += '+adapter:' + os.path.basename(snapshot_download(self.cfg['adapter'], local_files_only=True))
            except Exception:
                rev += '+adapter:unknown'
        return rev

    # --- tokenization: every item is a list of token ids, special tokens included
    def encode_abstract(self, title, abstract):
        c = self.cfg
        if c['abs_fmt'] == 'sep':
            text = title + self.tok.sep_token + abstract
        else:
            text = title + '\n\n' + abstract
        if c['pool'] == 'last':
            ids = self.tok(text, add_special_tokens=False, truncation=True, max_length=c['abs_max'] - 1)['input_ids'] + [self.tok.eos_token_id]
            return ids
        ids = self.tok(text, add_special_tokens=False, truncation=True, max_length=c['abs_max'] - 2 - len(self.prefix_ids))['input_ids']
        return self.tok.build_inputs_with_special_tokens(self.prefix_ids + ids)

    def encode_body(self, body):
        c = self.cfg
        raw = self.tok(body, add_special_tokens=False, truncation=False, verbose=False)['input_ids']
        extra = 1 if c['pool'] == 'last' else 2 + len(self.prefix_ids)
        out = []
        for w in windows(raw, c['chunk'] - extra, c['cap'], c['min_tail']):
            out.append(w + [self.tok.eos_token_id] if c['pool'] == 'last' else self.tok.build_inputs_with_special_tokens(self.prefix_ids + w))
        return out, len(raw)

    # --- forward
    def _forward(self, seqs):
        """(float32 pooled vectors, [sparse dict] or None) for token id lists (right-padded batch)."""
        torch = self.torch
        L = max(len(s) for s in seqs)
        pad = self.tok.pad_token_id if self.tok.pad_token_id is not None else 0
        ids = torch.full((len(seqs), L), pad, dtype=torch.long)
        att = torch.zeros((len(seqs), L), dtype=torch.long)
        for r, s in enumerate(seqs):
            ids[r, :len(s)] = torch.tensor(s); att[r, :len(s)] = 1
        ids, att = ids.to(self.dev), att.to(self.dev)
        with torch.inference_mode():
            h = self.model(input_ids=ids, attention_mask=att).last_hidden_state
            pool = self.cfg['pool']
            if pool == 'cls':
                v = h[:, 0]
            elif pool == 'last':
                v = h[torch.arange(len(seqs), device=self.dev), att.sum(1) - 1]
            else:
                m = att.unsqueeze(-1).to(h.dtype)
                v = (h * m).sum(1) / m.sum(1)
            sp = None
            if self.sparse is not None:
                wts = torch.relu(self.sparse(h)).squeeze(-1).float().cpu().numpy()
        out = v.float().cpu().numpy()
        if self.sparse is not None:
            sp = []
            for r, s in enumerate(seqs):
                d = {}
                for t, w in zip(s, wts[r, :len(s)]):
                    if t not in self.special and w > 0 and w > d.get(t, 0.0):
                        d[t] = float(w)
                sp.append(d)
        return out, sp

    def _safe(self, seqs):
        torch = self.torch
        try:
            return self._forward(seqs)
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            if len(seqs) == 1:
                raise
            h = len(seqs) // 2
            a, sa = self._safe(seqs[:h]); b, sb = self._safe(seqs[h:])
            return np.vstack([a, b]), (sa + sb if sa is not None else None)

    def embed(self, seqs):
        """float32 (len(seqs) x dim) and the sparse dicts (BGE-M3) or None, in the order of `seqs`."""
        lengths = np.array([len(s) for s in seqs])
        out = np.zeros((len(seqs), self.cfg['dim']), np.float32)
        sp = [None] * len(seqs) if self.sparse is not None else None
        for b in make_batches(lengths, self.cfg['budget']):
            v, s = self._safe([seqs[i] for i in b])
            if not np.isfinite(v).all():
                raise RuntimeError(f'{self.key}: non-finite vectors in fp16 (batch of {len(b)}, longest {lengths[b].max()}); rerun this model in float32')
            out[b] = v
            if sp is not None:
                for i, d in zip(b, s):
                    sp[i] = d
        return out, sp


# ---------------------------------------------------------------- the todo
def load_todo(kind, done, shard=None, of=None, limit=None, texts_db=None):
    """[(paper id, text hash, payload)] not yet embedded (hash not in `done`), this shard only, ordered by paper id. Abstract payload:
    (title, abstract). Full-text payload: None until fetch_bodies() reads the bodies of a part (the bodies are most of a 5 GB file)."""
    db = sqlite3.connect(f'file:{texts_db or C.TEXTS_DB}?mode=ro', uri=True, timeout=600)
    if kind == 'abstract':
        q = 'select paper_id, text_hash, title, abstract from abstracts order by paper_id'
    else:
        q = 'select paper_id, text_hash from fulltext where usable = 1 and body is not null order by paper_id'
    out = []
    for row in db.execute(q):
        pid, h = row[0], row[1]
        if done.get(pid) == h or (of and shard_of(pid, of) != shard):
            continue
        out.append((pid, h, row[2:] if kind == 'abstract' else None))
        if limit and len(out) >= limit:
            break
    db.close()
    return out


def fetch_bodies(pids):
    """{paper id: body text} for a part's full-text papers."""
    db = sqlite3.connect(f'file:{C.TEXTS_DB}?mode=ro', uri=True, timeout=600)
    out = {}
    for i in range(0, len(pids), 200):
        q = pids[i:i + 200]
        out.update({p: zlib.decompress(b).decode('utf-8', 'ignore') for p, b in db.execute(
            f'select paper_id, body from fulltext where paper_id in ({",".join("?" * len(q))})', q)})
    db.close()
    return out


def run(model, kind, shard, of, budget, limit, store_name, texts_db=None):
    t0 = time.time()
    name = store_name or model
    done = store.done_map(name, kind)
    todo = load_todo(kind, done, shard, of, limit, texts_db)
    C.log(model=model, kind=kind, shard=shard, of=of, todo=len(todo), already=len(done))
    if not todo:
        return
    emb = Embedder(model)
    job = os.environ.get('SLURM_ARRAY_JOB_ID') or os.environ.get('SLURM_JOB_ID', 'local')
    tag = f'{job}_{os.environ.get("SLURM_ARRAY_TASK_ID", shard if shard is not None else 0)}'
    pdir = store.part_dir(name, kind)
    pdir.mkdir(parents=True, exist_ok=True)
    per, seq, last = (PART_8K if kind == 'fulltext' and emb.cfg['chunk'] > 512 else PART[kind]), 0, None
    for c0 in range(0, len(todo), per):
        el = time.time() - t0
        if last and el + last * 1.25 > budget:
            C.log(stopped_for_budget=True, elapsed=round(el), remaining=len(todo) - c0); break
        t1 = time.time()
        chunk = todo[c0:c0 + per]
        bodies = fetch_bodies([c[0] for c in chunk]) if kind == 'fulltext' else {}
        seqs, owner, ntok = [], [], []
        for i, (pid, h, payload) in enumerate(chunk):
            if kind == 'abstract':
                s = [emb.encode_abstract(*payload)]; ntok.append(len(s[0]))
            else:
                s, nt = emb.encode_body(bodies[pid]); ntok.append(sum(len(x) for x in s))
            seqs += s; owner += [i] * len(s)
        V, SP = emb.embed(seqs)
        n = np.bincount(owner, minlength=len(chunk)).astype(np.int32)
        off = np.concatenate([[0], np.cumsum(n)])
        M = np.vstack([V[off[i]:off[i + 1]].mean(0) for i in range(len(chunk))]) if kind == 'fulltext' else None
        sparse = None
        if SP is not None:
            pieces = [merge_sparse(SP[off[i]:off[i + 1]]) for i in range(len(chunk))]
            sparse = (np.concatenate([[0], np.cumsum([len(a) for a, _ in pieces])]), np.concatenate([a for a, _ in pieces]), np.concatenate([b for _, b in pieces]))
        store.write_part(pdir / f'part_{tag}_{seq:04d}.npz', [c[0] for c in chunk], [c[1] for c in chunk], n, V, M, ntok, sparse)
        last = time.time() - t1; seq += 1
        C.log(part=seq, papers=len(chunk), vectors=len(seqs), tokens=int(sum(ntok)), seconds=round(last), tok_per_s=round(sum(ntok) / last), elapsed=round(time.time() - t0))
    meta = dict(model=model, hf=emb.cfg['hf'], revision=emb.revision, pool=emb.cfg['pool'], dtype='float16', note=emb.cfg['note'], prefix=emb.cfg['prefix'])
    (pdir / 'meta.json').write_text(json.dumps(meta))


def merge(model, kind, store_name=None):
    name = store_name or model
    db = sqlite3.connect(f'file:{C.UNIVERSE_DB}?mode=ro', uri=True)
    school_of = dict(db.execute('select paper_id, home_school from papers'))
    db.close()
    meta = json.loads((store.part_dir(name, kind) / 'meta.json').read_text()) if (store.part_dir(name, kind) / 'meta.json').exists() else dict(model=model)
    meta.update(text_kind=kind, universe=str(C.UNIVERSE_DB.name))
    store.merge(name, kind, school_of, meta)


def status(models):
    for m in models:
        for kind in MODELS[m]['kinds']:
            db = sqlite3.connect(f'file:{C.TEXTS_DB}?mode=ro', uri=True)
            total = db.execute('select count(*) from abstracts' if kind == 'abstract' else 'select count(*) from fulltext where usable=1').fetchone()[0]
            db.close()
            C.log(model=m, kind=kind, total=total, done=len(store.done_map(m, kind)))


SYNTH = ('Deep neural networks trained with stochastic gradient descent generalize well although they are heavily overparameterized. '
         'We study the implicit regularization of the optimizer and relate the flat minima it finds to margin bounds and to the spectrum of the Hessian. '
         'Experiments on image classification and language modelling show that wider models with careful normalization reach lower loss. ')


def selftest(model, long_tokens=9000):
    """fp16 against fp32 on a few synthetic abstracts (no database: it may be locked by a writer), plus one body long enough for two windows of the
    model's chunk size: cosine must be > 0.99, vectors finite; logs tokens per second and the peak GPU memory of an 8k window."""
    import torch
    rows = [(f'A study of overparameterized networks {i}', SYNTH * (1 + i % 3) + f' Variant {i}.') for i in range(12)]
    body = ' '.join(f'{SYNTH} Section {i} continues with numbered observations about trial {i}.' for i in range(long_tokens // 40))
    e16 = Embedder(model)
    seqs = [e16.encode_abstract(t, a) for t, a in rows]
    wins, ntok = e16.encode_body(body)
    seqs += wins[:3]
    torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    try:
        v16, sp = e16.embed(seqs)
    except torch.cuda.OutOfMemoryError:
        C.log(selftest=model, oom=True, peak_gb=round(torch.cuda.max_memory_allocated() / 2 ** 30, 2), longest=max(len(s) for s in seqs), ok=False)
        return
    dt = time.time() - t0
    peak = torch.cuda.max_memory_allocated() / 2 ** 30 if torch.cuda.is_available() else 0
    total = torch.cuda.get_device_properties(0).total_memory / 2 ** 30 if torch.cuda.is_available() else 0
    ok_shape = v16.shape == (len(seqs), e16.cfg['dim']) and bool(np.isfinite(v16).all())
    rev, tokens = e16.revision, sum(len(s) for s in seqs)
    del e16
    torch.cuda.empty_cache()
    big = bool(MODELS[model].get('big'))
    nabs = len(rows)
    e32 = Embedder(model, dtype='float32', device='cpu' if big else None)   # a 4B model in fp32 does not fit the card: compare the abstracts on the CPU
    if big:
        seqs, v16 = seqs[:nabs], v16[:nabs]
    v32, _ = e32.embed(seqs)
    cos = (v16 * v32).sum(1) / (np.linalg.norm(v16, axis=1) * np.linalg.norm(v32, axis=1))
    C.log(selftest=model, revision=rev, items=len(seqs), windows=len(wins), body_tokens=ntok, longest=max(len(s) for s in seqs), min_cos=float(cos.min()),
          mean_cos=float(cos.mean()), finite_and_shaped=ok_shape, sparse_nnz=(len(sp[0]) if sp and sp[0] else None), tok_per_s=round(tokens / dt), peak_gb=round(peak, 2), card_gb=round(total, 2), headroom_gb=round(total - peak, 2),
          ok=bool(cos.min() > 0.99 and ok_shape))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['run', 'merge', 'status', 'selftest'])
    ap.add_argument('--model'); ap.add_argument('--kind', choices=['abstract', 'fulltext'])
    ap.add_argument('--shard', type=int, default=0); ap.add_argument('--of', type=int, default=1)
    ap.add_argument('--budget', type=int, default=int(os.environ.get('EMB_BUDGET', 40000)))
    ap.add_argument('--limit', type=int); ap.add_argument('--store-name')
    ap.add_argument('--texts-db', help='abstracts table to read instead of EMB/texts.sqlite (the all-AI rewrites: ai-writing/allai/build_texts.py)')
    a = ap.parse_args()
    if a.cmd == 'run':
        run(a.model, a.kind, a.shard, a.of, a.budget, a.limit, a.store_name, a.texts_db)
    elif a.cmd == 'merge':
        merge(a.model, a.kind, a.store_name)
    elif a.cmd == 'status':
        status([a.model] if a.model else list(MODELS))
    else:
        selftest(a.model)
    sys.stdout.flush()
