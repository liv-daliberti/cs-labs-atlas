"""SPECTER2 (allenai/specter2_base, CLS, at most 512 tokens) on every body segment of the full texts, and on a fixed
arXiv CS background sample for N1.

snapshot  (login node) copy the live ai-writing/fulltext.sqlite into a local snapshot (common.snapshot_fulltext)
export    (login node) every usable full text (common.usable_text) -> its segments (common.segments: the paragraphs
          table's paragraphs when it has >= 3, else ~150-word passages at sentence ends; at most 100 per paper) and a
          signature of them; texts whose signature is not yet in the store go to data/embed_todo.jsonl.gz. Papers with
          no usable segment are recorded in the store at once (n_seg = 0).
          The background sample (once): 10,000 arXiv CS papers per year 2015-2025 with 50+ word abstracts, drawn with a
          fixed seed from claude-homogenization's corpus/background.sqlite -> data/background_todo.jsonl.gz. Its stored
          S2 'specter_v2' vectors are not this model's space (same-paper cosine ~0.956 against ~0.82 between random
          papers), so the sample is re-embedded with specter2_base, as ai-writing/embeddings.npz was.
run       (GPU, embed_fulltext.slurm) background first (-> data/background_specter2base.npz), then the todo in chunks of
          CHUNK papers, segments sorted by length into ~TOKENS-token batches, bf16 (fp16 on a GPU without bf16). Each
          chunk is written as one file data/parts/part_<job>_<n>.npz (atomic rename), so a job killed at its time limit
          loses at most one chunk. No new chunk starts after --budget seconds; the job then exits and the next job resumes.
merge     parts -> data/fulltext_emb.sqlite emb(key, sig, src, n_seg, mean float32, segs float16), built in node-local
          /tmp and copied back in one sequential write; the parts are removed after. The GPU jobs never open the store.
status    counts; --todo-jobs prints how many 59-minute jobs the todo needs at the last measured rate.
"""
import argparse, gzip, json, os, random, sqlite3, time
from datetime import datetime, timezone
import numpy as np
import common as C

TODO = C.DATA / 'embed_todo.jsonl.gz'
BG_TODO = C.DATA / 'background_todo.jsonl.gz'
PARTS = C.DATA / 'parts'
RATE = C.DATA / 'embed_rate.json'
MODEL = 'allenai/specter2_base'
CHUNK, TOKENS = 1500, 64000
BG_PER_YEAR, BG_YEARS = 10000, range(2015, 2026)


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def part_keys():
    out = {}
    for p in sorted(PARTS.glob('part_*.npz')):
        with np.load(p) as Z:
            out.update(zip([str(k) for k in Z['keys']], [str(s) for s in Z['sigs']]))
    return out


def export():
    have = {}
    if C.EMB_STORE.exists():
        db = C.emb_store()
        have = dict(db.execute('select key, sig from emb'))
        db.close()
    pend = part_keys() if PARTS.exists() else {}
    todo, empty, n_seg, n_src, skipped = [], [], 0, {}, 0
    for key, school, kind, body, flags, paras in C.iter_snapshot():
        if not C.usable_text(kind, body, flags):
            skipped += 1
            continue
        src, segs = C.segments(body, paras)
        sig = C.seg_signature(src, segs)
        if have.get(key) == sig or pend.get(key) == sig:
            continue
        if not segs:
            empty.append((key, sig, src, 0, b'', b'', now()))
            continue
        todo.append(dict(key=key, sig=sig, src=src, segs=segs)); n_seg += len(segs); n_src[src] = n_src.get(src, 0) + 1
    if empty:
        db = C.emb_store(write=True); db.executemany('insert or replace into emb values (?,?,?,?,?,?,?)', empty); db.commit(); db.close()
    tmp = C.DATA / 'tmp_embed_todo.jsonl.gz'
    with gzip.open(tmp, 'wt') as f:
        for t in todo:
            f.write(json.dumps(t) + '\n')
    os.replace(tmp, TODO)
    C.log(export_todo_papers=len(todo), segments=n_seg, by_source=n_src, no_segments=len(empty), not_usable=skipped,
          stored=len(have), in_parts=len(pend))
    if not C.BG_EMB.exists() and not BG_TODO.exists():
        export_background()


def export_background():
    db = C._ro(C.BACKGROUND)
    by_year = {}
    for a, created in db.execute('select arxiv_id, created from papers where abstract is not null'):
        y = int(created[:4])
        if y in BG_YEARS:
            by_year.setdefault(y, []).append(a)
    rnd = random.Random(C.SEED)
    rows = []
    for y in BG_YEARS:
        ids = rnd.sample(sorted(by_year.get(y, [])), min(len(by_year.get(y, [])), int(BG_PER_YEAR * 1.3)))
        got = {}
        for i in range(0, len(ids), 900):
            q = ids[i:i + 900]
            for a, t, ab in db.execute(f'select arxiv_id, title, abstract from papers where arxiv_id in ({",".join("?" * len(q))})', q):
                ab = C.zlib.decompress(ab).decode('utf-8', 'ignore')
                if t and len(ab.split()) >= 50:
                    got[a] = (t, ab)
        keep = [a for a in ids if a in got][:BG_PER_YEAR]
        rows += [dict(id=a, year=y, title=got[a][0], abstract=got[a][1]) for a in keep]
        C.log(background_year=y, available=len(by_year.get(y, [])), kept=len(keep))
    tmp = C.DATA / 'tmp_background_todo.jsonl.gz'
    with gzip.open(tmp, 'wt') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')
    os.replace(tmp, BG_TODO)


class Embedder:
    def __init__(self):
        import torch
        from transformers import AutoModel, AutoTokenizer
        self.torch = torch
        self.dev = 'cuda' if torch.cuda.is_available() else 'cpu'  # cpu only for dry runs
        self.dtype = (torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16) if self.dev == 'cuda' else torch.float32
        self.tok = AutoTokenizer.from_pretrained(MODEL)
        try:
            self.model = AutoModel.from_pretrained(MODEL, torch_dtype=self.dtype, attn_implementation='sdpa')
        except (TypeError, ValueError):
            self.model = AutoModel.from_pretrained(MODEL, torch_dtype=self.dtype)
        self.model = self.model.to(self.dev).eval()
        C.log(device=torch.cuda.get_device_name(0) if self.dev == 'cuda' else 'cpu', dtype=str(self.dtype))

    def __call__(self, texts):
        """float32 (len(texts) x 768) CLS vectors; batches of similar length, ~TOKENS padded tokens each."""
        torch = self.torch
        enc = self.tok(texts, truncation=True, max_length=512, add_special_tokens=True)['input_ids']
        order = np.argsort([len(e) for e in enc])
        out = np.zeros((len(texts), 768), np.float32)
        pad = self.tok.pad_token_id
        i = 0
        with torch.inference_mode():
            while i < len(order):
                j = i
                while j < len(order) and (j - i + 1) * len(enc[order[j]]) <= TOKENS:
                    j += 1
                j = max(j, i + 1)
                idx = order[i:j]; L = max(len(enc[k]) for k in idx)
                ids = torch.full((len(idx), L), pad, dtype=torch.long)
                att = torch.zeros((len(idx), L), dtype=torch.long)
                for r, k in enumerate(idx):
                    ids[r, :len(enc[k])] = torch.tensor(enc[k]); att[r, :len(enc[k])] = 1
                h = self.model(input_ids=ids.to(self.dev, non_blocking=True), attention_mask=att.to(self.dev, non_blocking=True)).last_hidden_state[:, 0]
                out[idx] = h.float().cpu().numpy()
                i = j
        return out


def run(budget):
    t0 = time.time()
    job = os.environ.get('SLURM_JOB_ID', 'local')
    PARTS.mkdir(parents=True, exist_ok=True)
    emb = Embedder()
    if not C.BG_EMB.exists() and BG_TODO.exists():
        rows = [json.loads(l) for l in gzip.open(BG_TODO, 'rt')]
        t1 = time.time()
        X = emb([r['title'] + emb.tok.sep_token + r['abstract'] for r in rows])
        tmp = C.DATA / 'tmp_background_specter2base.npz'
        np.savez(tmp, ids=np.array([r['id'] for r in rows]), years=np.array([r['year'] for r in rows], np.int16), X=X.astype(np.float16))
        os.replace(tmp, C.BG_EMB)
        C.log(background_embedded=len(rows), seconds=round(time.time() - t1))
    if not TODO.exists():
        return
    done = part_keys()
    todo = [t for t in (json.loads(l) for l in gzip.open(TODO, 'rt')) if done.get(t['key']) != t['sig']]
    C.log(job=job, todo_papers=len(todo), todo_segments=sum(len(t['segs']) for t in todo), already_in_parts=len(done))
    seq, last = 0, None
    for c0 in range(0, len(todo), CHUNK):
        el = time.time() - t0
        if el + (last or 0) * 1.3 > budget:
            C.log(stopped_for_budget=True, elapsed=round(el), remaining_papers=len(todo) - c0); break
        t1 = time.time()
        chunk = todo[c0:c0 + CHUNK]
        flat = [s for t in chunk for s in t['segs']]
        V = emb(flat)
        n = np.array([len(t['segs']) for t in chunk], np.int32)
        off = np.concatenate([[0], np.cumsum(n)])
        M = np.vstack([V[off[i]:off[i + 1]].mean(0) for i in range(len(chunk))]).astype(np.float32)
        tmp = PARTS / f'tmp_{job}_{seq:03d}.npz'
        np.savez(tmp, keys=np.array([t['key'] for t in chunk]), sigs=np.array([t['sig'] for t in chunk]), srcs=np.array([t['src'] for t in chunk]),
                 n=n, M=M, X=V.astype(np.float16))
        os.replace(tmp, PARTS / f'part_{job}_{seq:03d}.npz')
        last = time.time() - t1; seq += 1
        rate = len(flat) / last
        C.log(chunk=seq, papers=len(chunk), segments=len(flat), seconds=round(last), seg_per_s=round(rate), elapsed=round(time.time() - t0))
        RATE.write_text(json.dumps(dict(seg_per_s=rate, at=now(), job=job)))


def merge():
    """Parts -> the store. SQLite page writes over NFS are slow (minutes per 130 MB part), so the store is copied to
    node-local LOCAL, the parts are merged there, and the result is copied back in one sequential write (tmp + rename).
    Parts are removed only after the new store is in place."""
    import shutil
    parts = sorted(PARTS.glob('part_*.npz')) if PARTS.exists() else []
    if not parts:
        C.log(merged_parts=0); return
    t0 = time.time()
    C.LOCAL.mkdir(parents=True, exist_ok=True)
    local = C.LOCAL / 'emb_merge.sqlite'
    if C.EMB_STORE.exists():
        shutil.copyfile(C.EMB_STORE, local)
    elif local.exists():
        local.unlink()
    db = sqlite3.connect(local)
    db.execute('create table if not exists emb (key text primary key, sig text, src text, n_seg int, mean blob, segs blob, at text)')
    n = 0
    for p in parts:
        with np.load(p) as Z:  # NpzFile re-reads an array on every Z[name] access: load each once
            keys, sigs, srcs, ns, Mx, X = (Z[k] for k in ('keys', 'sigs', 'srcs', 'n', 'M', 'X'))
        off = np.concatenate([[0], np.cumsum(ns)])
        rows = [(str(k), str(s), str(src), int(m), Mx[i].astype(np.float32).tobytes(), X[off[i]:off[i + 1]].astype(np.float16).tobytes(), now())
                for i, (k, s, src, m) in enumerate(zip(keys, sigs, srcs, ns))]
        db.executemany('insert or replace into emb values (?,?,?,?,?,?,?)', rows); db.commit()
        n += len(rows)
    stored = db.execute('select count(*) from emb where n_seg > 0').fetchone()[0]
    db.close()
    tmp = C.EMB_STORE.with_name('tmp_' + C.EMB_STORE.name)
    shutil.copyfile(local, tmp)
    os.replace(tmp, C.EMB_STORE)
    for p in parts:
        p.unlink()
    local.unlink()
    C.log(merged_parts=len(parts), papers=n, stored=stored, seconds=round(time.time() - t0))


def status(todo_jobs=False):
    todo = [json.loads(l) for l in gzip.open(TODO, 'rt')] if TODO.exists() else []
    pend = part_keys() if PARTS.exists() else {}
    left = [t for t in todo if pend.get(t['key']) != t['sig']]
    segs = sum(len(t['segs']) for t in left)
    bg = 0 if C.BG_EMB.exists() or not BG_TODO.exists() else BG_PER_YEAR * len(BG_YEARS)
    rate = json.loads(RATE.read_text())['seg_per_s'] if RATE.exists() else 600.0
    jobs = int(np.ceil((segs + bg) / (rate * 2700))) if (segs + bg) else 0
    if todo_jobs:
        print(jobs); return
    stored = 0
    if C.EMB_STORE.exists():
        db = C.emb_store(); stored = db.execute('select count(*) from emb where n_seg > 0').fetchone()[0]; db.close()
    C.log(stored_papers=stored, in_parts=len(pend), todo_papers=len(left), todo_segments=segs, background_done=C.BG_EMB.exists(),
          seg_per_s=round(rate), jobs_needed=jobs)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['snapshot', 'export', 'run', 'merge', 'status'])
    ap.add_argument('--budget', type=int, default=3000)
    ap.add_argument('--todo-jobs', action='store_true')
    a = ap.parse_args()
    if a.cmd == 'snapshot':
        C.snapshot_fulltext()
    elif a.cmd == 'export':
        export()
    elif a.cmd == 'run':
        run(a.budget)
    elif a.cmd == 'merge':
        merge()
    else:
        status(a.todo_jobs)
