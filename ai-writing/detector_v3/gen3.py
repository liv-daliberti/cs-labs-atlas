"""AI versions of the v3 sources (data/sources3.jsonl) with one open generator, vLLM, resumable in parts.

tasks (six; the v2 prompts for polish / paraphrase / notes are reused):
  polish, paraphrase   whole passage rewritten (v2 prompts)
  notes                key points, then a passage written from title + points
  continue             the model continues the passage after its first half; the AI text is the continuation alone
  humanize             rewrite "so it does not read like AI text": plain wording, varied sentences, no stock AI phrases
  partial              1/3-2/3 of the sentences each rewritten by the model, the rest stays human; ai_frac = share of
                       words in rewritten sentences (a mixed passage: reported separately, not part of the 0.5% claim)
Each source has its own temperature (0.3 / 0.7 / 1.0), top-p 0.95, at most 700 new tokens, seed 20261022. Every prompt is
one user turn (no system turn: Gemma and Mistral templates reject it). Outputs are cleaned by v2's gen.clean.
Parts of PART sources are written as data/gen3/<gen>-<part>.jsonl.gz; a part that exists is skipped, and the job stops
starting parts after --budget minutes (Slurm limit 59), so resubmitting the same command resumes.
usage: gen3.py generate <gen> [--tp N] [--budget MIN] | gen3.py selftest
"""
import argparse, gzip, json, re, time
import os
import v3common as C
import gen as G2  # detector_v2/gen.py: clean, prompt (polish / paraphrase), KEEP

V = C.V
PART = 500
SRC = os.environ.get('AIW3_SRC', 'sources3.jsonl')  # v3.1: sources31.jsonl
OUTD = os.environ.get('AIW3_OUT', 'gen3')      # v3.1: gen31
SENT = re.compile(r'(?<=[.!?])\s+(?=[A-Z(\[])')
HUMAN = ("Rewrite the passage below, from the body of a computer science research paper titled \"{title}\", so that it does not read as "
         "AI-generated: use plain, direct wording, vary the sentence lengths, avoid stock phrases such as 'delve', 'moreover', 'crucial', "
         "'furthermore' and 'in the realm of', and write like a busy researcher. Keep the content and about {n} words. " + G2.KEEP +
         " Return only the rewritten passage, as plain text in a single paragraph.\n\n{text}")
CONT = ("Here is the beginning of a paragraph from the body of a computer science research paper titled \"{title}\". Continue the "
        "paragraph in the same style with about {n} more words. Return only the continuation, as plain text, without repeating the beginning.\n\n{head}")
NOTES1 = "List the key points of this passage from a computer science research paper as 3 to 6 short bullet points. Return only the bullet points.\n\n{text}"
NOTES2 = ("Write a passage of about {n} words for the body of a computer science research paper titled \"{title}\" that covers these points:\n{pts}\n\n"
          "Write continuous academic prose as a single paragraph, without headings or bullet points. Return only the passage.")
MINIMAL = ("Here is a passage from the body of a computer science research paper titled \"{title}\". Make only the smallest edits needed: fix "
           "grammar, typos and clumsy phrasing and change nothing else, so that most of the original wording stays. Keep all content and about {n} words. "
           + G2.KEEP + " Return only the edited passage, as plain text in a single paragraph.\n\n{text}")
SENTP = ("Rewrite this sentence from a computer science research paper to improve its clarity and style, keeping its meaning and any citation "
         "markers, numbers and symbols. It sits in this passage:\n\n{text}\n\nSentence to rewrite: {sent}\n\nReturn only the rewritten sentence.")


def chat(tok, user):
    return tok.apply_chat_template([{'role': 'user', 'content': user}], tokenize=False, add_generation_prompt=True)


def one_line(raw):
    t, _ = G2.clean(raw)  # (clean's 40-word floor is for whole passages)
    t = t.strip().strip('"“”')
    return t, not G2.REFUSE.search(t[:200]) and 3 <= len(t.split()) <= 120


def run_part(llm, tok, SP, src):
    n = len(src)
    sp = lambda s: SP(temperature=s['temp'], top_p=0.95, max_tokens=700, seed=V.SEED)  # noqa: E731
    out = {}

    def stage(items, make):  # items: [(key, source, extra)] -> list of (key, source, extra, text, finish)
        if not items:
            return []
        rs = llm.generate([chat(tok, make(s, x)) for _, s, x in items], [sp(s) for _, s, x in items], use_tqdm=False)
        return [(k, s, x, r.outputs[0].text, r.outputs[0].finish_reason) for (k, s, x), r in zip(items, rs)]

    def emit(k, s, raw, fin, text_override=None, ai_frac=1.0, points=None):
        out[k] = (s, raw, fin, text_override, ai_frac, points)

    direct = [(s['sid'], s, None) for s in src if s['task'] in ('polish', 'paraphrase', 'humanize', 'minimal')]
    def mk(s, x):
        n = len(s['text'].split())
        if s['task'] == 'humanize':
            return HUMAN.format(title=s['title'], n=n, text=s['text'])
        if s['task'] == 'minimal':
            return MINIMAL.format(title=s['title'], n=n, text=s['text'])
        return G2.prompt(s)
    for k, s, x, raw, fin in stage(direct, mk):
        emit(k, s, raw, fin)
    notes = [(s['sid'], s, None) for s in src if s['task'] == 'notes']
    r1 = stage(notes, lambda s, x: NOTES1.format(text=s['text']))
    r2 = stage([(k, s, p.strip()) for k, s, x, p, f in r1], lambda s, p: NOTES2.format(n=len(s['text'].split()), title=s['title'], pts=p))
    for k, s, p, raw, fin in r2:
        emit(k, s, raw, fin, points=p)
    cont = []
    for s in src:
        if s['task'] == 'continue':
            ss = SENT.split(s['text'])
            if len(ss) < 2:
                continue
            h = max(1, len(ss) // 2)
            head, rest = ' '.join(ss[:h]), ' '.join(ss[h:])
            cont.append((s['sid'], s, (head, len(rest.split()))))
    for k, s, x, raw, fin in stage(cont, lambda s, x: CONT.format(title=s['title'], n=max(30, x[1]), head=x[0])):
        emit(k, s, raw, fin, points=None)
        head = x[0]
        out[k] = (s, raw.strip()[len(head):].strip() if raw.strip().startswith(head[:80]) else raw, fin, None, 1.0, None)
    items = []
    for s in src:
        if s['task'] == 'partial':
            ss = SENT.split(s['text'])
            for i in s.get('sel', []):
                if i < len(ss):
                    items.append((f"{s['sid']}#{i}", s, (ss, i)))
    res = {}
    for k, s, (ss, i), raw, fin in stage(items, lambda s, x: SENTP.format(text=s['text'], sent=x[0][x[1]])):
        res[k] = (one_line(raw), fin)
    for s in src:
        if s['task'] == 'partial':
            ss = SENT.split(s['text']); new, ch, ok = [], 0, True
            for i, t in enumerate(ss):
                r = res.get(f"{s['sid']}#{i}")
                if r is None:
                    new.append(t)
                else:
                    (nt, good), fin = r
                    if not good or fin == 'length':
                        ok = False
                    new.append(nt); ch += len(nt.split())
            tot = sum(len(x.split()) for x in new)
            emit(s['sid'], s, ' '.join(new), 'stop' if ok else 'length', text_override=' '.join(new), ai_frac=round(ch / max(1, tot), 3))
    recs = []
    for k in sorted(out):
        s, raw, fin, over, frac, pts = out[k]
        if fin == 'length':
            continue
        text, ok = (over, len(over.split()) >= 40) if over else G2.clean(raw)
        if not ok:
            continue
        recs.append(dict(sid=k, gen=s['gen'], family=s['family'], split=s['split'], key=s['key'], task=s['task'], temp=s['temp'], text=text,
                         words=len(text.split()), src_words=len(s['text'].split()), ai_frac=frac, finish=fin, raw_head=raw[:100], points=pts))
    return recs, n


def generate(gen, tp, budget):
    t0 = time.time()
    from vllm import LLM, SamplingParams
    src = [json.loads(l) for l in open(C.DATA / SRC)]
    src = [s for s in src if s['gen'] == gen]
    (C.DATA / OUTD).mkdir(exist_ok=True)
    parts = [src[i:i + PART] for i in range(0, len(src), PART)]
    todo = [i for i in range(len(parts)) if not (C.DATA / OUTD / f'{gen}-{i}.jsonl.gz').exists()]
    print(json.dumps(dict(gen=gen, sources=len(src), parts=len(parts), todo=len(todo))), flush=True)
    if not todo:
        return
    kw = dict(limit_mm_per_prompt={'image': 0}) if gen.startswith('gemma3') else dict(trust_remote_code=True) if gen.startswith('internlm') else {}
    llm = LLM(V.snapshot(C.GEN[gen][1]), tensor_parallel_size=tp, max_model_len=4096, gpu_memory_utilization=0.92, disable_custom_all_reduce=True,
              seed=V.SEED, enforce_eager=False, **kw)
    tok = llm.get_tokenizer()
    print(json.dumps(dict(loaded_min=round((time.time() - t0) / 60, 1))), flush=True)
    for i in todo:
        if (time.time() - t0) / 60 > budget:
            print('budget reached; resubmit to continue', flush=True); return
        p = [s for s in parts[i] if len(tok(s['text'])['input_ids']) <= G2.MAX_SRC_TOKENS]
        recs, n = run_part(llm, tok, SamplingParams, p)
        tmp = C.DATA / OUTD / f'tmp-{gen}-{i}.jsonl.gz'
        with gzip.open(tmp, 'wt') as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
        tmp.replace(C.DATA / OUTD / f'{gen}-{i}.jsonl.gz')
        print(json.dumps(dict(part=i, sources=len(parts[i]), kept=len(recs), minutes=round((time.time() - t0) / 60, 1))), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd'); ap.add_argument('gen', nargs='?'); ap.add_argument('--tp', type=int, default=1)
    ap.add_argument('--budget', type=float, default=44)
    a = ap.parse_args()
    generate(a.gen, a.tp, a.budget) if a.cmd == 'generate' else G2.selftest()
