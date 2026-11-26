"""Cross-model per-sentence grounding check (grounding.check) of summaries, with a model from another family than the writer.

Two uses (owner target 2026-11-23: < 1% of summaries with any unsupported sentence):
  --apply   a production pass: sentences this model flags are deleted (Gemma-3-12B after the Qwen writer's own grounding stage).
            A summary that falls below summarize.MIN_WORDS is marked ok = 0 (too_short_after_crosscheck).
  measure   (no --apply) the independent audit: a THIRD model (Mistral-Nemo-12B) flags what survived; its flags are then adjudicated by hand.

usage   crosscheck.py run --shard I --in sum-2-p5 [--in-table s|x] [--in-set gemma] --set NAME --model M [--apply]
        crosscheck.py report --shard I --out NAME
Input: WORK/shards/<in>.sqlite, table s (text where ok = 1) or table x (text_out where ok = 1, set = --in-set).
Output: WORK/shards/xc-<shard>-<out>.sqlite, table x(set, k, n_sent, n_flag, flags, text_out, words, ok, why).
"""
import argparse
import json
import os
import sqlite3
import sys
import time
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import grounding as G  # noqa: E402
import summarize as S  # noqa: E402

X_SQL = '''create table if not exists x (set_name text, k text, n_sent int, n_flag int, flags text, text_out text, words int, ok int, why text,
    primary key (set_name, k));
create table if not exists meta (key text primary key, value text);'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['run', 'report'])
    ap.add_argument('--shard', type=int, required=True)
    ap.add_argument('--in', dest='inp', default='')
    ap.add_argument('--in-table', default='s')
    ap.add_argument('--in-set', default='')
    ap.add_argument('--set', default='x')
    ap.add_argument('--out', default='')
    ap.add_argument('--model', default='unsloth/gemma-3-12b-it')
    ap.add_argument('--tp', type=int, default=int(os.environ.get('SUM_TP', 2)))
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    out_p = S.WORK / 'shards' / f'xc-{a.shard}-{a.out or a.set}.sqlite'
    db = sqlite3.connect(out_p, timeout=600)
    db.executescript(X_SQL)
    if a.cmd == 'report':
        for name, n, ns, nf, nany, nok in db.execute('select set_name, count(*), sum(n_sent), sum(n_flag), sum(n_flag > 0), sum(ok) from x group by set_name'):
            print(json.dumps(dict(set=name, summaries=n, sentences=ns, flagged_sentences=nf, sentence_rate=round(nf / max(ns, 1), 4),
                                  summaries_with_any=nany, summary_rate=round(nany / max(n, 1), 4), ok_after=nok)))
        return
    src_db = sqlite3.connect(f"file:{S.WORK / 'shards' / (a.inp + '.sqlite')}?mode=ro", uri=True)
    if a.in_table == 's':
        items = list(src_db.execute("select k, title, year, text from s where ok = 1 and text != ''"))
    else:
        items = [(k, '', None, t) for k, t in src_db.execute("select k, text_out from x where ok = 1 and set_name = ?", (a.in_set,))]
    done = {r[0] for r in db.execute('select k from x where set_name = ?', (a.set,))}
    items = [r for r in items if r[0] not in done]
    S.log(crosscheck=len(items), model=a.model, apply=a.apply)
    if not items:
        return
    sec = sqlite3.connect(f"file:{S.E32 / 'sections' / f'sections-{a.shard}.sqlite'}?mode=ro", uri=True)
    from vllm import LLM, SamplingParams
    snap = sorted(S.HF_HUB.glob(f"models--{a.model.replace('/', '--')}/snapshots/*/config.json"))[0].parent
    kw = dict(limit_mm_per_prompt={'image': 0}) if 'gemma-3' in a.model else {}
    llm = LLM(str(snap), tensor_parallel_size=a.tp, dtype='bfloat16', max_model_len=S.MAX_MODEL_LEN, gpu_memory_utilization=0.92, seed=S.SEED,
              enable_chunked_prefill=True, max_num_batched_tokens=8192, max_num_seqs=64, disable_custom_all_reduce=True, enable_prefix_caching=True, **kw)
    tok = llm.get_tokenizer()
    db.executemany('insert or replace into meta values (?,?)', [(f'{a.set}:model', a.model), (f'{a.set}:apply', str(a.apply)), (f'{a.set}:input', a.inp),
                   ('check_prompt', G.CHECK), (f'{a.set}:started', time.strftime('%Y-%m-%dT%H:%M:%S'))])
    db.commit()
    sp = SamplingParams(temperature=0.0, max_tokens=G.MAX_TOKENS, seed=S.SEED)

    def chat(user):
        return tok.apply_chat_template([{'role': 'user', 'content': user}], tokenize=False, add_generation_prompt=True)

    meta = S.paper_meta()
    for c0 in range(0, len(items), 48):
        t1 = time.time()
        papers = {}
        for k, title, year, text in items[c0:c0 + 48]:
            src = zlib.decompress(sec.execute('select main from sections where k=?', (k,)).fetchone()[0]).decode()
            _, yr, ttl, _ = meta.get(k, (None, year, title, None))
            papers[k] = dict(ctx=G.contexts(src, tok, (ttl or '').strip() or 'untitled', str(yr) if yr else 'year unknown', S.GROUND_PAPER_MAX, S.split_parts),
                             sents=G.split_summary(text), src=src)
        G.check(llm, sp, chat, papers, S.unsupported_numbers)
        rows = []
        for k, p in papers.items():
            flags = [(s, p['verdict'][s][1]) for _, s in p['sents'] if not p['verdict'][s][0]]
            if a.apply:
                out = G.join_summary([(pi, s) for pi, s in p['sents'] if p['verdict'][s][0]])
                n = len(out.split())
                ok, why = (1, '') if n >= S.MIN_WORDS else (0, 'too_short_after_crosscheck')
            else:
                out = G.join_summary(p['sents']); n = len(out.split()); ok, why = 1, ''
            rows.append((a.set, k, len(p['sents']), len(flags), json.dumps(flags), out, n, ok, why))
        db.executemany('insert or replace into x values (?,?,?,?,?,?,?,?,?)', rows)
        db.commit()
        S.log(crosschecked=c0 + len(papers), flagged=sum(r[3] for r in rows), with_any=sum(r[3] > 0 for r in rows), seconds=round(time.time() - t1))


if __name__ == '__main__':
    main()
