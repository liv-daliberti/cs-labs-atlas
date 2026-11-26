"""Sentence-level grounding pass for the summaries (owner 2026-11-23: "get fabrications under 1%").

Pilot 4 (v3.2 prompt) still had numbers absent from the paper in ~9% of summaries, and the number guard cannot see non-numeric inventions
(made-up limitations, applications, comparisons). This pass checks EVERY sentence against the paper and keeps only grounded ones:

  1. verify   the summary is split into numbered sentences; the model (paper in context) answers per sentence
              SUPPORTED | "verbatim quote"  or  UNSUPPORTED | reason.  A SUPPORTED verdict counts only when its quote is really in the
              paper (normalised substring, or >= 80% of the quote's word 4-grams in the paper) and the sentence's numbers are all in the
              paper (summarize.unsupported_numbers). Missing / unparsable lines count as unsupported.
  2. fix      the flagged sentences (with the reasons) go back once: rewrite them from the paper or drop them, keep the rest verbatim.
  3. verify   again, only for sentences not already verified (cache by sentence text).
  4. delete   any sentence still not verified is deleted. The result is ok when it keeps >= MIN_FINAL words and passes the format checks.
Long papers (paper + summary + output over the context) are verified part by part: a sentence is supported if any part supports it.

Every verdict, quote, reason and deletion is stored, so the residual rate can be measured (audit.py, an independent model family).
usage   verify.py run --shard I --tag pilot4-tp2 [--out-tag v1] [--budget S] [--limit N]
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import time
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import summarize as S  # noqa: E402

VERIFY_MAX_TOKENS = 4500
VERIFY_DIRECT_MAX = S.MAX_MODEL_LEN - 2500 - 600 - VERIFY_MAX_TOKENS     # paper tokens that fit next to a numbered summary and the verdicts
MIN_FINAL = 750

HEADER = 'Below is the main text of a research paper titled "{title}" ({year}).\n\n<paper>\n{text}\n</paper>\n\n'
PART_HEADER = 'Below is part {i} of {n} of the main text of a research paper titled "{title}" ({year}).\n\n<part>\n{text}\n</part>\n\n'

VERIFY = """Below is a summary of this paper, split into numbered sentences.

<summary>
{numbered}
</summary>

Check every sentence against the paper text above. A sentence is SUPPORTED only if everything it states (each number, name, comparison, result, claim and qualifier) is stated in the paper text or follows directly from it. A sentence is UNSUPPORTED if any part of it is missing from the paper text, goes beyond it or contradicts it. General framing such as "The paper addresses ..." is SUPPORTED when the paper text says so.

Answer with exactly one line per sentence, in order, in one of these two formats:
[n] SUPPORTED | "an exact quote from the paper text that supports the sentence"
[n] UNSUPPORTED | what the paper text does not say
Copy each quote exactly, character for character, from the paper text; at most 30 words. Output nothing else."""

VERIFY_PART = VERIFY.replace('against the paper text above', 'against this part of the paper').replace(
    'A sentence is UNSUPPORTED if any part of it is missing from the paper text',
    'A sentence is UNSUPPORTED if any part of it is missing from this part')

FIX = """Below is a summary of this paper. Some of its sentences are not supported by the paper text:

{flagged}

<summary>
{summary}
</summary>

Rewrite the summary in full. Replace each listed sentence with one that states only what the paper text says, using the paper's own facts, or remove it if the paper offers nothing on that point. Use no number that is not in the paper text. Keep every other sentence exactly as it is and keep the paragraphs. Return only the summary."""

V_SQL = '''create table if not exists v (k text primary key, ok int, why text, text text, words int, n_sent int, n_flag1 int, n_flag2 int, n_deleted int,
    fixed text, flags1 text, flags2 text, deleted text, verdicts text, src_words int, mode text, seconds real);
create table if not exists meta (key text primary key, value text);'''

ABBR = r'(?:e\.g|i\.e|et al|etc|vs|Fig|Figs|Eq|Eqs|Sec|Ref|No|approx|cf|resp|Dr|Mr|Ms|Prof|al)'


def sentences(para):
    """Split a paragraph into sentences, not after common abbreviations or inside decimals."""
    out, cur = [], ''
    for piece in re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"“(])', para.strip()):
        cur = f'{cur} {piece}'.strip() if cur else piece
        if re.search(r'\b' + ABBR + r'\.$', cur) or re.search(r'\b[A-Z]\.$', cur):
            continue
        out.append(cur); cur = ''
    if cur:
        out.append(cur)
    return out


def split_summary(text):
    """[(para_index, sentence)]"""
    return [(pi, s) for pi, p in enumerate(t for t in text.split('\n\n') if t.strip()) for s in sentences(p)]


def join_summary(sents):
    paras = {}
    for pi, s in sents:
        paras.setdefault(pi, []).append(s)
    return '\n\n'.join(' '.join(v) for _, v in sorted(paras.items()))


def _norm(t):
    t = t.lower().replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    t = re.sub(r'[‐-―-]', ' ', t)
    t = re.sub(r'(?<!\d)\.|\.(?!\d)', ' ', t).replace('%', ' % ')
    t = re.sub(r'[^a-z0-9%.]+', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


class Source:
    def __init__(self, text):
        self.norm = _norm(text)
        w = self.norm.split()
        self.grams = {' '.join(w[i:i + 4]) for i in range(len(w) - 3)}

    def has_quote(self, q):
        q = _norm(q.strip(' "\''))
        w = q.split()
        if len(w) < 3:
            return False
        if q in self.norm:
            return True
        g = [' '.join(w[i:i + 4]) for i in range(len(w) - 3)]
        return bool(g) and sum(x in self.grams for x in g) / len(g) >= 0.8


LINE = re.compile(r'^\s*\[(\d+)\]\s*(SUPPORTED|UNSUPPORTED)\s*\|?\s*(.*)$', re.I)


def parse(out, n):
    """{index: (verdict, payload)} for indices 1..n"""
    res = {}
    for line in out.splitlines():
        m = LINE.match(line)
        if m:
            i = int(m.group(1))
            if 1 <= i <= n and i not in res:
                res[i] = (m.group(2).upper(), m.group(3).strip())
    return res


def run(a):
    t0 = time.time()
    shards = S.WORK / 'shards'
    src_db = sqlite3.connect(f"file:{shards / f'sum-{a.shard}-{a.tag}.sqlite' if a.tag else shards / f'sum-{a.shard}.sqlite'}?mode=ro", uri=True)
    out_p = shards / f"ver-{a.shard}{('-' + a.tag) if a.tag else ''}{('-' + a.out_tag) if a.out_tag else ''}.sqlite"
    db = sqlite3.connect(out_p, timeout=600)
    db.executescript(V_SQL)
    done = {r[0] for r in db.execute('select k from v')}
    rows = [r for r in src_db.execute("select k, title, year, text, mode from s where text is not null and text != '' order by k") if r[0] not in done]
    if a.limit:
        rows = rows[:a.limit]
    sec = sqlite3.connect(f"file:{S.E32 / 'sections' / f'sections-{a.shard}.sqlite'}?mode=ro", uri=True)
    S.log(verify_shard=a.shard, todo=len(rows), already=len(done))
    if not rows:
        return
    from vllm import LLM, SamplingParams
    path = S.snapshot_dir()
    llm = LLM(path, tensor_parallel_size=S.TP, dtype='bfloat16', max_model_len=S.MAX_MODEL_LEN, gpu_memory_utilization=0.92, seed=S.SEED,
              enable_chunked_prefill=True, max_num_batched_tokens=8192, max_num_seqs=64, disable_custom_all_reduce=True, enable_prefix_caching=True)
    tok = llm.get_tokenizer()
    db.executemany('insert or replace into meta values (?,?)', [('model', S.GEN), ('verify', VERIFY), ('verify_part', VERIFY_PART), ('fix', FIX),
                   ('min_final', str(MIN_FINAL)), ('source_tag', a.tag), ('started', time.strftime('%Y-%m-%dT%H:%M:%S'))])
    db.commit()
    greedy = SamplingParams(temperature=0.0, max_tokens=VERIFY_MAX_TOKENS, seed=S.SEED)
    gfix = SamplingParams(temperature=0.0, max_tokens=S.SUM_MAX_TOKENS, seed=S.SEED, repetition_penalty=1.05)

    def chat(user):
        return tok.apply_chat_template([{'role': 'system', 'content': S.SYSTEM}, {'role': 'user', 'content': user}], tokenize=False, add_generation_prompt=True)

    def contexts(j):
        """[(header, task-template)] : the whole paper when it fits, else its parts."""
        if j['ntok'] <= VERIFY_DIRECT_MAX:
            return [HEADER.format(title=j['ttl'], year=j['yr'], text=j['src'])]
        parts = S.split_parts(j['src'], tok, budget=VERIFY_DIRECT_MAX // 2)
        return [PART_HEADER.format(i=i + 1, n=len(parts), title=j['ttl'], year=j['yr'], text=p) for i, p in enumerate(parts)]

    def verify(jobs, key):
        """jobs[k][key] = list of (pi, sentence); fills jobs[k]['verdict'][sentence] = (ok, payload) for sentences not cached."""
        reqs = []
        for k, j in jobs.items():
            todo = [s for _, s in j[key] if s not in j['verdict']]
            if not todo:
                continue
            numbered = '\n'.join(f'[{i + 1}] {s}' for i, s in enumerate(todo))
            for ci, h in enumerate(j['ctx']):
                task = (VERIFY if len(j['ctx']) == 1 else VERIFY_PART).format(numbered=numbered)
                reqs.append((k, todo, chat(h + task)))
        if not reqs:
            return
        outs = llm.generate([r[2] for r in reqs], greedy, use_tqdm=False)
        agg = {}
        for (k, todo, _), o in zip(reqs, outs):
            j = jobs[k]
            res = parse(o.outputs[0].text, len(todo))
            j.setdefault('raw_verdicts', []).append(o.outputs[0].text[:6000])
            for i, s in enumerate(todo):
                v, pay = res.get(i + 1, ('MISSING', ''))
                good = v == 'SUPPORTED' and j['srcx'].has_quote(pay) and not S.unsupported_numbers(s, j['src'])
                why = '' if good else ('no_verdict' if v == 'MISSING' else 'unsupported: ' + pay[:200] if v == 'UNSUPPORTED'
                                       else 'quote_not_in_paper' if not j['srcx'].has_quote(pay) else 'number_not_in_paper')
                prev = agg.get((k, s))
                if prev is None or (good and not prev[0]):        # supported by any part wins
                    agg[(k, s)] = (good, pay[:300] if good else why)
        for (k, s), v in agg.items():
            jobs[k]['verdict'][s] = v

    n_ok = 0
    last = 0.0
    for c0 in range(0, len(rows), S.CHUNK):
        if c0 and time.time() - t0 + last * 1.2 > a.budget:
            S.log(stopped_for_budget=True, remaining=len(rows) - c0); sys.exit(75)
        t1 = time.time()
        jobs = {}
        for k, title, year, text, mode in rows[c0:c0 + S.CHUNK]:
            src = zlib.decompress(sec.execute('select main from sections where k=?', (k,)).fetchone()[0]).decode()
            j = dict(k=k, ttl=(title or '').strip() or 'untitled', yr=str(year) if year else 'year unknown', src=src, srcx=Source(src), mode=mode,
                     text=text, s1=split_summary(text), verdict={}, ntok=len(tok(src, add_special_tokens=False)['input_ids']))
            j['ctx'] = contexts(j)
            jobs[k] = j
        verify(jobs, 's1')
        # fix flagged sentences (one pass), with the first context (the whole paper, or part 1 + the instruction to use the paper's facts)
        freqs = []
        for k, j in jobs.items():
            j['flags1'] = [(s, j['verdict'][s][1]) for _, s in j['s1'] if not j['verdict'][s][0]]
            if j['flags1']:
                fl = '\n'.join(f'- "{s}" (problem: {why})' for s, why in j['flags1'])
                ctx = j['ctx'][0] if len(j['ctx']) == 1 else HEADER.format(title=j['ttl'], year=j['yr'], text=j['src'][:60000])
                pr = chat(ctx + FIX.format(flagged=fl, summary=j['text']))
                if len(tok(pr, add_special_tokens=False)['input_ids']) + S.SUM_MAX_TOKENS <= S.MAX_MODEL_LEN:
                    freqs.append((k, pr))
        if freqs:
            outs = llm.generate([p for _, p in freqs], gfix, use_tqdm=False)
            for (k, p), o in zip(freqs, outs):
                j = jobs[k]
                fixed = S.clean(o.outputs[0].text)
                if o.outputs[0].finish_reason == 'stop' and fixed:
                    j['fixed'] = fixed; j['s2'] = split_summary(fixed)
        for j in jobs.values():
            j.setdefault('s2', j['s1'])
        verify(jobs, 's2')
        out_rows = []
        for k, j in jobs.items():
            keep = [(pi, s) for pi, s in j['s2'] if j['verdict'][s][0]]
            dele = [s for _, s in j['s2'] if not j['verdict'][s][0]]
            final = join_summary(keep)
            n = len(final.split())
            ok, why, _ = S.judge(final, 'stop', j['src'])
            if why in ('too_short', 'too_long') or ok:
                ok, why = (1, '') if MIN_FINAL <= n <= S.MAX_WORDS else (0, 'too_short_after_verify' if n < MIN_FINAL else 'too_long')
            n_ok += ok
            out_rows.append((k, ok, why, final, n, len(j['s1']), len(j['flags1']), sum(1 for _, s in j['s2'] if not j['verdict'][s][0]), len(dele),
                             j.get('fixed'), json.dumps(j['flags1']), json.dumps([(s, j['verdict'][s][1]) for s in dele]), json.dumps(dele),
                             json.dumps(j.get('raw_verdicts', [])), len(j['src'].split()), j['mode'], (time.time() - t1) / len(jobs)))
        db.executemany(f'insert or replace into v values ({",".join("?" * 17)})', out_rows)
        db.commit()
        last = time.time() - t1
        S.log(verify_shard=a.shard, chunk=c0 // S.CHUNK, papers=len(jobs), ok=n_ok, flagged1=sum(1 for j in jobs.values() if j['flags1']),
              deleted=sum(r[8] for r in out_rows), seconds=round(last), per_paper=round(last / len(jobs), 2))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['run'])
    ap.add_argument('--shard', type=int, required=True)
    ap.add_argument('--tag', default='')
    ap.add_argument('--out-tag', default='')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--budget', type=int, default=int(os.environ.get('SUM_BUDGET', 10 ** 9)))
    run(ap.parse_args())
