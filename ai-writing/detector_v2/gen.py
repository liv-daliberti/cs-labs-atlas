"""AI versions of the source passages (data/sources.jsonl), one generator per run, with vLLM.

tasks    polish      "revise for clarity, flow and academic style", content and length kept (an author polishing a draft)
         paraphrase  the same content reworded, length kept
         notes       the model lists the passage's key points, then writes a passage from the paper title and the points
                     alone (Liang et al. 2025's outline-then-expand; the words are the model's)
         Each source has one generator and one task (prep.py): 2,000 sources per generator per task.
filter   a source of more than 1,200 tokens (the generator's tokenizer) is skipped: extraction junk such as base64 blobs.
         (The Qwen2.5-72B run, 31950260, predates this filter; its longest source has 1,683 tokens and fits.)
sampling temperature 0.7, top-p 0.9, max 900 new tokens (a truncated output is dropped), seed 20261022.
clean    preambles ("Here is the revised passage:"), trailing notes ("Note: ...", "Changes made: ..."), wrapping quotes
         and markdown are stripped; refusals and outputs under 40 words are dropped.
-> data/generated-<gen>.jsonl {sid, key, gen, task, text, words, finish, points}
usage: gen.py generate <qwen72b|qwen7b|llama70b> [--tp N] | gen.py selftest
"""
import argparse, json, re
import v2common as V

LEAD = re.compile(r"^(?:sure|certainly|of course|okay|ok|absolutely|here(?:'s| is| are)|below is|the following is|"
                  r"(?:the )?(?:revised|improved|polished|refined|paraphrased|rewritten|reworded|edited|final)\b|"
                  r"(?:paraphrase|passage|revision|rewrite|version)\s*:)", re.I)
TAIL = re.compile(r"^(?:\(?\s*note\b|\(?\s*word count|\(?\s*\d+ words\)?$|i (?:have|'ve)\b|this (?:revision|revised|version|paraphrase|rewrite|passage)\b|"
                  r"(?:key |main |the )?changes(?: made)?\b|let me know\b|i hope\b|explanation of changes|summary of changes|---+$)", re.I)
INLINE = re.compile(r"^(?:\*\*)?(?:sure|certainly|of course|okay)?[!,.]?\s*(?:here(?:'s| is)[^:\n]{0,100}|(?:the )?(?:revised|improved|polished|refined|"
                    r"paraphrased|rewritten)(?: version of the)?(?: passage| text| paragraph)?)(?:\*\*)?\s*:\s*(?:\*\*)?", re.I)
REFUSE = re.compile(r"\b(?:I'm sorry|I am sorry|I cannot|I can't|as an AI)\b", re.I)


def clean(raw):
    """(text, ok). Lines: leading preamble lines (short, and either ending in ':' or opening with a preamble word) are
    dropped; the first trailing-commentary line and everything after it is dropped; an inline 'Here is ...:' prefix is
    cut; wrapping quotes and markdown emphasis go."""
    lines = [l.strip() for l in raw.strip().splitlines()]
    lines = [l for l in lines if l]
    while lines and len(lines) > 1 and len(lines[0]) < 160 and (lines[0].rstrip('*').endswith(':') or LEAD.match(lines[0].lstrip('*# '))):
        lines.pop(0)
    for i, l in enumerate(lines):
        if i > 0 and TAIL.match(l.lstrip('*#>-• ')):
            lines = lines[:i]; break
    t = ' '.join(lines)
    t = INLINE.sub('', t, count=1)
    t = re.sub(r'\*\*|__|^#+\s*', '', t).strip()
    if len(t) > 1 and t[0] in '"“' and t[-1] in '"”':
        t = t[1:-1].strip()
    ok = len(t.split()) >= 40 and not REFUSE.search(t[:200])
    return t, ok


def chat(tok, user):
    return tok.apply_chat_template([{'role': 'system', 'content': 'You are a helpful assistant.'}, {'role': 'user', 'content': user}],
                                   tokenize=False, add_generation_prompt=True)


MAX_SRC_TOKENS = 1200  # a 40-400-word passage is ~60-600 tokens; more means extraction junk (and can overflow the 4,096 context)
KEEP = 'Keep citation markers, numbers, symbols and technical terms as they are.'


def prompt(s):
    n = len(s['text'].split())
    if s['task'] == 'polish':
        return (f"Here is a passage from the body of a computer science research paper titled \"{s['title']}\". Revise it to improve its "
                f"clarity, flow and academic style. Keep the content and roughly the same length (about {n} words). {KEEP} "
                f"Return only the revised passage, as plain text in a single paragraph.\n\n{s['text']}")
    if s['task'] == 'paraphrase':
        return (f"Here is a passage from the body of a computer science research paper titled \"{s['title']}\". Paraphrase it: rewrite it "
                f"in your own words, keeping its meaning, its technical details and roughly the same length (about {n} words). {KEEP} "
                f"Return only the paraphrased passage, as plain text in a single paragraph.\n\n{s['text']}")
    raise ValueError(s['task'])


def generate(gen, tp):
    from vllm import LLM, SamplingParams
    src = [json.loads(l) for l in open(V.DATA / 'sources.jsonl')]
    src = [s for s in src if s['gen'] == gen]
    llm = LLM(V.snapshot(V.GEN_REPO[gen]), tensor_parallel_size=tp, max_model_len=4096, gpu_memory_utilization=0.9,
              disable_custom_all_reduce=True, seed=V.SEED)
    tok = llm.get_tokenizer()
    n0 = len(src)
    src = [s for s in src if len(tok(s['text'])['input_ids']) <= MAX_SRC_TOKENS]  # extraction junk (base64 blobs, glyph runs)
    print(json.dumps(dict(gen=gen, sources=n0, dropped_too_many_tokens=n0 - len(src))), flush=True)
    sp = SamplingParams(temperature=0.7, top_p=0.9, max_tokens=900, seed=V.SEED)
    out = {}
    direct = [s for s in src if s['task'] in ('polish', 'paraphrase')]
    for s, r in zip(direct, llm.generate([chat(tok, prompt(s)) for s in direct], sp)):
        out[s['sid']] = (s, r.outputs[0].text, r.outputs[0].finish_reason, None)
    notes = [s for s in src if s['task'] == 'notes']
    pts = llm.generate([chat(tok, "List the key points of this passage from a computer science research paper as 3 to 6 short bullet "
                                  f"points. Return only the bullet points.\n\n{s['text']}") for s in notes], sp)
    pts = [p.outputs[0].text.strip() for p in pts]
    res = llm.generate([chat(tok, f"Write a passage of about {len(s['text'].split())} words for the body of a computer science research paper "
                                  f"titled \"{s['title']}\" that covers these points:\n{p}\n\nWrite continuous academic prose as a single "
                                  "paragraph, without headings or bullet points. Return only the passage.") for s, p in zip(notes, pts)], sp)
    for s, p, r in zip(notes, pts, res):
        out[s['sid']] = (s, r.outputs[0].text, r.outputs[0].finish_reason, p)
    kept = dropped_len = dropped_clean = 0
    with open(V.DATA / f'generated-{gen}.jsonl', 'w') as f:
        for sid in sorted(out):
            s, raw, fin, p = out[sid]
            text, ok = clean(raw)
            if fin == 'length':
                dropped_len += 1; continue
            if not ok:
                dropped_clean += 1; continue
            kept += 1
            f.write(json.dumps(dict(sid=sid, key=s['key'], gen=gen, task=s['task'], text=text, words=len(text.split()), src_words=len(s['text'].split()),
                                    finish=fin, raw_head=raw[:120], points=p), ensure_ascii=False) + '\n')
    print(json.dumps(dict(gen=gen, sources=len(src), kept=kept, dropped_truncated=dropped_len, dropped_clean=dropped_clean)))


def selftest():
    body = ' '.join(['word'] * 60)
    cases = [f"Here is the revised passage:\n\n{body}", f"**Revised Passage:**\n{body}\n\nNote: I kept the citations.",
             f"Sure! Here's a paraphrased version of the passage: {body}", f'"{body}"', f"{body}\n\nChanges made:\n- clarity\n- flow",
             f"Certainly. Below is the revised text.\n{body}\n(Word count: 150)", "I'm sorry, but I cannot help with that."]
    for c in cases:
        t, ok = clean(c)
        print(ok, repr(t[:40]), repr(t[-20:]), len(t.split()))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd'); ap.add_argument('gen', nargs='?'); ap.add_argument('--tp', type=int, default=1)
    a = ap.parse_args()
    selftest() if a.cmd == 'selftest' else generate(a.gen, a.tp)
