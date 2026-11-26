"""Independent fabrication audit of summaries with a DIFFERENT model family (owner target 2026-11-23: fabrications under 1%).

The writer and its own verifier are Qwen2.5-14B; a model checking its own family's text shares its blind spots, so the residual rate is
measured here with Gemma-3-12B-it (cached; 128k context). Same sentence-level protocol as verify.py: per sentence SUPPORTED + a verbatim
quote (checked against the paper) or UNSUPPORTED + reason; numbers must be in the paper. Long papers are audited part by part.

Reported per set: sentences, unsupported sentences (rate), summaries with >= 1 unsupported sentence (rate), and a breakdown of why.
The auditor itself errs (false alarms, mostly paraphrase-level quotes); adjudicate a sample of its flags before quoting a final rate.

usage   audit.py run --shard I --set raw:sum-2-pilot4-tp2 --set ver:ver-2-pilot4-tp2-v1 [--model unsloth/gemma-3-12b-it] [--tp 2]
        (raw sets read s.text, ver sets read v.text where ok = 1 unless --all)
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
import summarize as S  # noqa: E402
import verify as V  # noqa: E402

A_SQL = '''create table if not exists a (set_name text, k text, n_sent int, n_unsup int, unsup text, raw text, primary key (set_name, k));
create table if not exists meta (key text primary key, value text);'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['run', 'report'])
    ap.add_argument('--shard', type=int, required=True)
    ap.add_argument('--set', action='append', default=[], help='name:file-stem (in WORK/shards)')
    ap.add_argument('--model', default=os.environ.get('AUDIT_MODEL', 'unsloth/gemma-3-12b-it'))
    ap.add_argument('--tp', type=int, default=int(os.environ.get('SUM_TP', 2)))
    ap.add_argument('--out', default='')
    ap.add_argument('--all', action='store_true')
    a = ap.parse_args()
    out_p = S.WORK / 'shards' / f"aud-{a.shard}{('-' + a.out) if a.out else ''}.sqlite"
    db = sqlite3.connect(out_p, timeout=600)
    db.executescript(A_SQL)
    if a.cmd == 'report':
        for name, n, ns, nu, nsum in db.execute('select set_name, count(*), sum(n_sent), sum(n_unsup), sum(n_unsup > 0) from a group by set_name'):
            print(json.dumps(dict(set=name, summaries=n, sentences=ns, unsupported_sentences=nu, sentence_rate=round(nu / ns, 4),
                                  summaries_with_any=nsum, summary_rate=round(nsum / n, 4))))
        return
    sec = sqlite3.connect(f"file:{S.E32 / 'sections' / f'sections-{a.shard}.sqlite'}?mode=ro", uri=True)
    items = []
    for spec in a.set:
        name, stem = spec.split(':', 1)
        f = S.WORK / 'shards' / f'{stem}.sqlite'
        sdb = sqlite3.connect(f'file:{f}?mode=ro', uri=True)
        q = ("select k, text from v" + ('' if a.all else ' where ok = 1')) if stem.startswith('ver-') else "select k, text from s where text != ''"
        done = {r[0] for r in db.execute('select k from a where set_name = ?', (name,))}
        items += [(name, k, t) for k, t in sdb.execute(q) if k not in done and t]
    S.log(audit=len(items), sets=a.set, model=a.model)
    if not items:
        return
    from vllm import LLM, SamplingParams
    snap = sorted((S.HF_HUB).glob(f"models--{a.model.replace('/', '--')}/snapshots/*/config.json"))[0].parent
    kw = dict(limit_mm_per_prompt={'image': 0}) if 'gemma-3' in a.model else {}
    llm = LLM(str(snap), tensor_parallel_size=a.tp, dtype='bfloat16', max_model_len=S.MAX_MODEL_LEN, gpu_memory_utilization=0.92, seed=S.SEED,
              enable_chunked_prefill=True, max_num_batched_tokens=8192, max_num_seqs=32, disable_custom_all_reduce=True, enable_prefix_caching=True, **kw)
    tok = llm.get_tokenizer()
    db.executemany('insert or replace into meta values (?,?)', [('model', a.model), ('protocol', V.VERIFY), ('started', time.strftime('%Y-%m-%dT%H:%M:%S'))])
    sp = SamplingParams(temperature=0.0, max_tokens=V.VERIFY_MAX_TOKENS, seed=S.SEED)
    src_cache = {}

    def chat(user):
        return tok.apply_chat_template([{'role': 'user', 'content': user}], tokenize=False, add_generation_prompt=True)

    for c0 in range(0, len(items), 64):
        t1 = time.time()
        reqs, meta = [], []
        for name, k, text in items[c0:c0 + 64]:
            if k not in src_cache:
                src = zlib.decompress(sec.execute('select main from sections where k=?', (k,)).fetchone()[0]).decode()
                src_cache[k] = (src, V.Source(src), len(tok(src, add_special_tokens=False)['input_ids']))
            src, srcx, ntok = src_cache[k]
            sents = [s for _, s in V.split_summary(text)]
            numbered = '\n'.join(f'[{i + 1}] {s}' for i, s in enumerate(sents))
            if ntok <= V.VERIFY_DIRECT_MAX:
                ctxs = [(V.HEADER.format(title='(see text)', year='', text=src), V.VERIFY)]
            else:
                parts = S.split_parts(src, tok, budget=V.VERIFY_DIRECT_MAX // 2)
                ctxs = [(V.PART_HEADER.format(i=i + 1, n=len(parts), title='(see text)', year='', text=p), V.VERIFY_PART) for i, p in enumerate(parts)]
            meta.append((name, k, sents, srcx, src, len(ctxs)))
            for h, task in ctxs:
                reqs.append((len(meta) - 1, chat(h + task.format(numbered=numbered))))
        outs = llm.generate([p for _, p in reqs], sp, use_tqdm=False)
        best = {}
        raws = {}
        for (mi, _), o in zip(reqs, outs):
            name, k, sents, srcx, src, _ = meta[mi]
            res = V.parse(o.outputs[0].text, len(sents))
            raws.setdefault(mi, []).append(o.outputs[0].text[:6000])
            for i, s in enumerate(sents):
                v, pay = res.get(i + 1, ('MISSING', ''))
                good = v == 'SUPPORTED' and srcx.has_quote(pay) and not S.unsupported_numbers(s, src)
                why = '' if good else ('no_verdict' if v == 'MISSING' else 'unsupported: ' + pay[:200] if v == 'UNSUPPORTED'
                                       else 'quote_not_in_paper' if not srcx.has_quote(pay) else 'number_not_in_paper')
                cur = best.setdefault(mi, {}).get(i)
                if cur is None or (good and not cur[0]):
                    best[mi][i] = (good, why)
        rows = []
        for mi, (name, k, sents, _, _, _) in enumerate(meta):
            uns = [(sents[i], w) for i, (g, w) in sorted(best.get(mi, {}).items()) if not g]
            rows.append((name, k, len(sents), len(uns), json.dumps(uns), json.dumps(raws.get(mi, []))))
        db.executemany('insert or replace into a values (?,?,?,?,?,?)', rows)
        db.commit()
        S.log(audited=c0 + len(meta), seconds=round(time.time() - t1))


if __name__ == '__main__':
    main()
