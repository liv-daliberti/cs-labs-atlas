"""Training data for the AI-written-text detector: human abstracts from before ChatGPT and LLM versions of them.

sample   from ai-writing/papers.jsonl.gz, lab papers published 2016-2021 (before ChatGPT, Nov 2022) with an abstract of
         80-400 words: 3,000 sources (stratified by school) and 12,000 further human abstracts, disjoint
         -> sources.jsonl, humans.jsonl
generate one model per run (vLLM). Each source gets two AI versions, by two different models:
           polish   "revise for clarity, flow and academic style" (an author polishing their own draft)
           outline  the model first lists the abstract's key points, then writes an abstract from the title and the
                    points alone (Liang et al. 2025's outline-then-expand; the words are the model's)
         source k: polish by MODELS[k % 3], outline by MODELS[(k + 1) % 3]
         -> generated-<model>.jsonl {key, model, task, text}
usage: gen.py sample | gen.py generate <model-short-name> [--tp N]
"""
import argparse, gzip, json, random, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
HF = '/n/fs/resemble/cs-atlas-env/hf-cache/hub'
MODELS = {'qwen7b': 'Qwen/Qwen2.5-7B-Instruct', 'qwen3b': 'Qwen/Qwen2.5-3B-Instruct', 'llama70b': 'meta-llama/Llama-3.3-70B-Instruct',
          'qwen72b': 'Qwen/Qwen2.5-72B-Instruct'}  # the 70B Llama cache is incomplete (no config.json); Qwen-72B is the large generator
ORDER = ['qwen7b', 'qwen3b', 'llama70b']


def sample():
    rng = random.Random(20261022)
    papers = [json.loads(l) for l in gzip.open(HERE / 'papers.jsonl.gz', 'rt')]
    pool = [p for p in papers if p['year'] and 2016 <= int(p['year']) <= 2021 and p['abstract'] and 80 <= len(p['abstract'].split()) <= 400 and p['title']]
    rng.shuffle(pool)
    by = {}
    for p in pool:
        by.setdefault(p['school'], []).append(p)
    share = {s: len(v) / len(pool) for s, v in by.items()}
    src = [p for s, v in by.items() for p in v[:round(3000 * share[s])]]
    used = {p['key'] for p in src}
    hum = [p for p in pool if p['key'] not in used][:12000]
    for name, rows in (('sources', src), ('humans', hum)):
        with open(HERE / f'{name}.jsonl', 'w') as f:
            for k, p in enumerate(rows):
                f.write(json.dumps(dict(idx=k, key=p['key'], school=p['school'], year=p['year'], title=p['title'], abstract=p['abstract']), ensure_ascii=False) + '\n')
    print(json.dumps(dict(pool=len(pool), sources=len(src), humans=len(hum), by_school={s: len(v) for s, v in by.items()})))


def chat(tok, user):
    return tok.apply_chat_template([{'role': 'system', 'content': 'You are a helpful assistant.'}, {'role': 'user', 'content': user}],
                                   tokenize=False, add_generation_prompt=True)


def clean(t):
    t = t.strip()
    t = re.sub(r'^(?:\*\*)?(?:revised |improved |polished )?abstract(?:\*\*)?\s*:?\s*', '', t, flags=re.I)
    return t.strip().strip('"').strip()


def generate(short, tp):
    from vllm import LLM, SamplingParams
    src = [json.loads(l) for l in open(HERE / 'sources.jsonl')]
    if short == 'qwen72b':  # the large generator writes one version of every source: polish for even idx, outline for odd
        jobs = [(s, 'polish') for s in src if s['idx'] % 2 == 0] + [(s, 'outline') for s in src if s['idx'] % 2 == 1]
    else:
        me = ORDER.index(short)
        jobs = [(s, 'polish') for s in src if s['idx'] % 3 == me] + [(s, 'outline') for s in src if (s['idx'] + 1) % 3 == me]
    import glob
    snap = sorted(glob.glob(f"{HF}/models--{MODELS[short].replace('/', '--')}/snapshots/*/config.json"))  # offline: a cache without refs/main cannot resolve the repo id
    llm = LLM(str(Path(snap[0]).parent) if snap else MODELS[short], tensor_parallel_size=tp, max_model_len=4096, gpu_memory_utilization=0.9, disable_custom_all_reduce=True, seed=20261022)
    tok = llm.get_tokenizer(); sp = SamplingParams(temperature=0.7, top_p=0.9, max_tokens=700, seed=20261022)
    out = {}
    pol = [(s, t) for s, t in jobs if t == 'polish']
    res = llm.generate([chat(tok, f"Here is the abstract of a computer science research paper titled \"{s['title']}\". Revise it to improve its clarity, flow and academic style. Keep the content and roughly the same length. Return only the revised abstract.\n\n{s['abstract']}") for s, _ in pol], sp)
    for (s, t), r in zip(pol, res):
        out[(s['key'], t)] = clean(r.outputs[0].text)
    outl = [(s, t) for s, t in jobs if t == 'outline']
    pts = llm.generate([chat(tok, f"List the key points of this abstract as 4 to 6 short bullet points. Return only the bullet points.\n\n{s['abstract']}") for s, _ in outl], sp)
    res = llm.generate([chat(tok, f"Write the abstract of a computer science research paper titled \"{s['title']}\" that covers these points:\n{p.outputs[0].text.strip()}\n\nReturn only the abstract, about {len(s['abstract'].split())} words.") for (s, _), p in zip(outl, pts)], sp)
    for (s, t), r in zip(outl, res):
        out[(s['key'], t)] = clean(r.outputs[0].text)
    with open(HERE / f'generated-{short}.jsonl', 'w') as f:
        for (k, t), text in out.items():
            f.write(json.dumps(dict(key=k, model=short, task=t, text=text), ensure_ascii=False) + '\n')
    print(json.dumps(dict(model=short, generated=len(out))))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd'); ap.add_argument('model', nargs='?'); ap.add_argument('--tp', type=int, default=1)
    a = ap.parse_args()
    sample() if a.cmd == 'sample' else generate(a.model, a.tp)
