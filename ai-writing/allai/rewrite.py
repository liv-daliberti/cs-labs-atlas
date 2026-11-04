"""All-AI corpus: rewrite every abstract of the embeddings universe with one fixed LLM prompt, so that the wording is AI for every paper.

  rewrite.py run --style polish|paraphrase [--shard i --of n] [--subsample] [--limit N] [--budget SECONDS]
  rewrite.py merge --style polish|paraphrase            shards -> EMB/allai/rewrites_<style>.sqlite
  rewrite.py subsample                                   the 5,000-paper stratified subsample for the second style
  rewrite.py status

Source: EMB/texts.sqlite `abstracts` (112,260 abstracts, keyed by atlas paper id). The title is kept as it is (it is the human title).
Model: Qwen/Qwen2.5-7B-Instruct (vLLM, bf16, one A5000), chat template with the detector's system prompt, GREEDY decoding (temperature 0, seed 20261104).
polish      "revise for clarity, flow and academic style", every claim, number, method and technical term kept, length kept
            (the detector_v2 'polish' task, written for abstracts: ai-writing/detector_v2/gen.py)
paraphrase  the same content in the model's own words (the detector's 'paraphrase' task), 5,000-paper stratified subsample
Output cleaning is detector_v2/gen.py `clean` (preambles, trailing notes, wrapping quotes, markdown). A rewrite is kept (ok = 1) when it was not
cut at the token limit, is not a refusal, and has at least max(8, 40% of the source's words). The rows that are not ok stay in the container with
their reason (`why`) so failures are counted, not hidden.
Container: one sqlite per shard while running (EMB/allai/shards/<style>_<i>of<n>.sqlite, never two writers on one file), merged into
rewrites_<style>.sqlite: rw(paper_id PK, style, text, text_hash, ok, why, src_words, words, finish, raw_head, text_hash_src), meta(key, value).
text_hash is ecommon.text_hash(title + '\\n' + rewrite): the hash embed.py stores with each vector.
A run resumes: papers already in its shard file are skipped; rows are committed every CHUNK papers.
"""
import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'embeddings'))
sys.path.insert(0, str(HERE.parent / 'detector_v2'))
import ecommon as C  # noqa: E402

GEN = 'Qwen/Qwen2.5-7B-Instruct'
SEED = 20261104
CHUNK = 2000
MAX_SRC_TOKENS = 1800
ALLAI = C.EMB / 'allai'
SYSTEM = 'You are a helpful assistant.'
TASKS = {
    'polish': ('Here is the abstract of a research paper titled "{title}". Rewrite it as a polished academic abstract: improve its clarity, flow '
               'and academic style. Keep every claim, number, method name and technical term exactly as given; do not add or drop any information. '
               'Keep roughly the same length (about {n} words). Return only the rewritten abstract, as plain text in a single paragraph.\n\n{abstract}'),
    'paraphrase': ('Here is the abstract of a research paper titled "{title}". Paraphrase it: rewrite it in your own words, keeping its meaning, '
                   'every number, every named method and technical term, and roughly the same length (about {n} words). Return only the '
                   'paraphrased abstract, as plain text in a single paragraph.\n\n{abstract}'),
}
SAMPLING = dict(temperature=0.0, top_p=1.0, max_tokens_rule='min(1500, 1.5 * source tokens + 100)', seed=SEED)


def shard_of(pid, n):
    return int(hashlib.sha1(pid.encode()).hexdigest()[:8], 16) % n


def build_prompt(title, abstract, style):
    return TASKS[style].format(title=title, n=len(abstract.split()), abstract=abstract)


def accept(text, src_words, finish, ok_clean):
    """(ok, why)"""
    if finish == 'length':
        return 0, 'truncated'
    if not ok_clean:
        return 0, 'refusal_or_short'
    if len(text.split()) < max(8, 0.4 * src_words):
        return 0, 'much_shorter_than_source'
    return 1, ''


def clean_text(raw):
    import gen as G   # detector_v2/gen.py (imports numpy-only helpers; vllm is imported lazily there)
    t, _ = G.clean(raw)
    lines_ok = not G.REFUSE.search(t[:200]) and bool(t)
    return t, lines_ok


def sample_ids(of=5000):
    """Stratified (home school x year) subsample of the abstract papers, proportional, deterministic (sha1 order within a stratum)."""
    db = sqlite3.connect(f'file:{C.UNIVERSE_DB}?mode=ro', uri=True)
    meta = {p: (s, y) for p, s, y in db.execute('select paper_id, home_school, year from papers')}
    db.close()
    tx = sqlite3.connect(f'file:{C.TEXTS_DB}?mode=ro', uri=True)
    ids = [r[0] for r in tx.execute('select paper_id from abstracts')]
    tx.close()
    strata = {}
    for i in ids:
        s, y = meta.get(i, (None, None))
        if y is not None and 2016 <= y <= 2026:
            strata.setdefault((s, y), []).append(i)
    tot = sum(len(v) for v in strata.values())
    out = []
    for k, v in sorted(strata.items()):
        v.sort(key=lambda p: hashlib.sha1(f'{SEED}|{p}'.encode()).hexdigest())
        out += v[:max(1, round(of * len(v) / tot))]
    out.sort(key=lambda p: hashlib.sha1(f'{SEED}|{p}'.encode()).hexdigest())
    return sorted(out[:of])


def subsample_path():
    return ALLAI / 'subsample5000.json'


def snapshot_dir():
    import glob
    hub = str(C.P.HF_HOME / 'hub')
    snap = sorted(glob.glob(f"{hub}/models--{GEN.replace('/', '--')}/snapshots/*/config.json"))
    if not snap:
        raise FileNotFoundError(GEN)
    return str(Path(snap[0]).parent)


def shard_db(style, shard, of):
    p = ALLAI / 'shards' / f'{style}_{shard}of{of}.sqlite'
    p.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(p, timeout=600)
    db.execute('create table if not exists rw (paper_id text primary key, style text, text text, text_hash text, ok int, why text, src_words int, words int,'
               ' finish text, raw_head text, text_hash_src text)')
    db.execute('create table if not exists meta (key text primary key, value text)')
    return db


def run(style, shard, of, subsample, limit, budget):
    t0 = time.time()
    db = shard_db(style, shard, of)
    done = {r[0] for r in db.execute('select paper_id from rw')}
    tx = sqlite3.connect(f'file:{C.TEXTS_DB}?mode=ro', uri=True, timeout=600)
    want = set(json.loads(subsample_path().read_text())) if subsample else None
    todo = [(p, t or '', a, h) for p, t, a, h in tx.execute('select paper_id, title, abstract, text_hash from abstracts order by paper_id')
            if p not in done and shard_of(p, of) == shard and (want is None or p in want)]
    tx.close()
    if limit:
        todo = todo[:limit]
    C.log(style=style, shard=shard, of=of, todo=len(todo), already=len(done))
    if not todo:
        return
    os.environ.setdefault('VLLM_USE_V1', '0')
    from vllm import LLM, SamplingParams
    import vllm
    path = snapshot_dir()
    llm = LLM(path, tensor_parallel_size=1, max_model_len=4096, gpu_memory_utilization=0.9, seed=SEED, disable_custom_all_reduce=True)
    tok = llm.get_tokenizer()
    db.executemany('insert or replace into meta values (?,?)', [
        ('model', GEN), ('revision', Path(path).name), ('vllm', vllm.__version__), ('dtype', 'auto (bfloat16)'), ('style', style),
        ('prompt', TASKS[style]), ('system', SYSTEM), ('sampling', json.dumps(SAMPLING)), ('max_src_tokens', str(MAX_SRC_TOKENS)),
        ('title', 'kept as is (human title)'), ('started', C.now())])
    db.commit()
    n_ok = n_bad = 0
    last = None
    for c0 in range(0, len(todo), CHUNK):
        el = time.time() - t0
        if last and el + last * 1.25 > budget:
            C.log(stopped_for_budget=True, elapsed=round(el), remaining=len(todo) - c0)
            break
        t1 = time.time()
        chunk = todo[c0:c0 + CHUNK]
        prompts, idx, rows = [], [], []
        for i, (p, title, ab, h) in enumerate(chunk):
            nt = len(tok(ab)['input_ids'])
            if nt > MAX_SRC_TOKENS:
                rows.append((p, style, '', '', 0, 'source_too_long', len(ab.split()), 0, '', '', h)); continue
            chat = tok.apply_chat_template([{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': build_prompt(title, ab, style)}],
                                           tokenize=False, add_generation_prompt=True)
            prompts.append((chat, min(1500, int(1.5 * nt) + 100))); idx.append(i)
        sps = [SamplingParams(temperature=0.0, top_p=1.0, max_tokens=m, seed=SEED) for _, m in prompts]
        outs = llm.generate([c for c, _ in prompts], sps, use_tqdm=False)
        for i, o in zip(idx, outs):
            p, title, ab, h = chunk[i]
            raw, fin = o.outputs[0].text, o.outputs[0].finish_reason
            text, okc = clean_text(raw)
            ok, why = accept(text, len(ab.split()), fin, okc)
            rows.append((p, style, text, C.text_hash(title + '\n' + text) if ok else '', ok, why, len(ab.split()), len(text.split()), fin, raw[:120], h))
        db.executemany('insert or replace into rw values (?,?,?,?,?,?,?,?,?,?,?)', rows)
        db.commit()
        n_ok += sum(r[4] for r in rows); n_bad += sum(1 - r[4] for r in rows)
        last = time.time() - t1
        C.log(chunk=c0 // CHUNK, papers=len(chunk), ok=n_ok, bad=n_bad, seconds=round(last), elapsed=round(time.time() - t0))


def merge(style):
    out = ALLAI / f'rewrites_{style}.sqlite'
    files = sorted((ALLAI / 'shards').glob(f'{style}_*of*.sqlite'))

    def write(t):
        db = sqlite3.connect(t)
        db.execute('create table rw (paper_id text primary key, style text, text text, text_hash text, ok int, why text, src_words int, words int,'
                   ' finish text, raw_head text, text_hash_src text)')
        db.execute('create table meta (key text primary key, value text)')
        meta = {}
        for f in files:
            s = sqlite3.connect(f'file:{f}?mode=ro', uri=True)
            db.executemany('insert or replace into rw values (?,?,?,?,?,?,?,?,?,?,?)', s.execute('select * from rw'))
            meta.update(dict(s.execute('select key, value from meta')))
            s.close()
        meta.update(merged=C.now(), shards=str(len(files)))
        db.executemany('insert into meta values (?,?)', list(meta.items()))
        db.commit()
        n, ok = db.execute('select count(*), sum(ok) from rw').fetchone()
        why = dict(db.execute('select why, count(*) from rw where ok = 0 group by why'))
        db.close()
        C.log(merged=style, shards=len(files), rows=n, ok=ok, failures=why)
    C.atomic_write(out, write)


def status():
    for f in sorted((ALLAI / 'shards').glob('*.sqlite')):
        s = sqlite3.connect(f'file:{f}?mode=ro', uri=True)
        n, ok = s.execute('select count(*), coalesce(sum(ok), 0) from rw').fetchone()
        C.log(file=f.name, rows=n, ok=ok)
        s.close()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['run', 'merge', 'subsample', 'status'])
    ap.add_argument('--style', default='polish', choices=list(TASKS))
    ap.add_argument('--shard', type=int, default=0); ap.add_argument('--of', type=int, default=1)
    ap.add_argument('--subsample', action='store_true'); ap.add_argument('--limit', type=int)
    ap.add_argument('--budget', type=int, default=int(os.environ.get('RW_BUDGET', 10 ** 9)))
    a = ap.parse_args()
    if a.cmd == 'run':
        run(a.style, a.shard, a.of, a.subsample, a.limit, a.budget)
    elif a.cmd == 'merge':
        merge(a.style)
    elif a.cmd == 'subsample':
        ids = sample_ids()
        ALLAI.mkdir(parents=True, exist_ok=True)
        subsample_path().write_text(json.dumps(ids))
        C.log(subsample=len(ids))
    else:
        status()
