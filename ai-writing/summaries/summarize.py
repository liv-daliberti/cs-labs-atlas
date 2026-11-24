"""Uniform-style ~1,000-word summaries of every locally held paper (owner 2026-11-23).

Owner: "For every paper that we have locally for our homogenizing science work, I want to re-write every paper to be a 1000 word summary
of the paper (all in the same style of writing, capturing all the main contributions) ... careful / solid / clear summary of the paper."
Model choice (owner, same day): "a 14B model (for now)".

Source  the entropy-32 build (studies/homogenization/work/entropy32-<id>): papers.parquet (every 2016-2025 lab paper of the 32 schools, one
        row per work, its stored copy) and sections/sections-<i>.sqlite (main body = Introduction up to the references, appendix excluded,
        the v3 splitter). A paper is summarized when its main body has >= 1,000 words (v3's `usable` rule); the rest get a row with why.
Model   Qwen/Qwen2.5-14B-Instruct, bf16, vLLM, one GPU (TP=1), max_model_len 32,768, greedy (temperature 0) with repetition_penalty 1.05
        (Qwen's own generation_config value), seed 20261123. One fixed system prompt and one fixed instruction (STYLE) for every paper.
Long    a main body over DIRECT_MAX tokens is cut at paragraph boundaries into parts of <= PART_TOKENS; each part gets faithful notes
        (NOTES prompt), and the summary is written from the notes with the same STYLE requirements (mode = 'notes').
Accept  ok = 1 when generation stopped on its own, the cleaned text has MIN_WORDS..MAX_WORDS words, is not a refusal, has no markdown
        residue and no runaway repetition. A failed paper is retried once with Qwen's sampling defaults (temperature 0.7, top_p 0.8,
        seed fixed); the row keeps the attempt and the first failure. Rows that stay ok = 0 keep their reason (why), so nothing is hidden.
Output  WORK = studies/homogenization/work/summaries14b-<id>/
        shards/sum-<i>.sqlite   (one writer per file; i = the entropy-32 shard)   s(k PK, ...), notes(k, part, text), meta
        summaries.sqlite        merged (stage merge)
usage   summarize.py run --shard I [--limit N] [--ids FILE] [--budget S] [--tag pilot]
        summarize.py pilot-ids [--n 120]          stratified pilot list -> WORK/pilot_ids.json
        summarize.py merge | status
"""
import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
import zlib
from pathlib import Path

ROOT = Path(os.environ.get('CS_ATLAS_ROOT', '/n/fs/resemble/homogenizing-science'))
E32 = ROOT / 'studies/homogenization/work' / f"entropy32-{os.environ.get('E32_ID', '20261123')}"
RUN_ID = os.environ.get('SUM_ID', '20261123')
WORK = ROOT / 'studies/homogenization/work' / f'summaries14b-{RUN_ID}'
HF_HUB = Path(os.environ.get('HF_HOME', ROOT / 'env/hf-cache')) / 'hub'

GEN = os.environ.get('SUM_MODEL', 'Qwen/Qwen2.5-14B-Instruct')   # or Qwen/Qwen2.5-14B-Instruct-AWQ (the official int4 build of the same model)
TP = int(os.environ.get('SUM_TP', 1))                                # 2 = one model over two cards (A6000 pair: ~4x the KV room)
KV_DTYPE = os.environ.get('SUM_KV', 'auto')                       # 'fp8' halves the KV cache (A6000: ~7 -> ~14 papers in flight)
SEED = 20261123
MAX_MODEL_LEN = 32768
SUM_MAX_TOKENS = 2300        # ~1,700 words: room above the 1,200-word ceiling so a stop is the model's, not the cap's
NOTE_MAX_TOKENS = 1200
DIRECT_MAX = 28500           # main-body tokens; 28,500 + ~700 instruction + 2,300 output < 32,768 (a length revision adds the draft: see REVISE)
PART_TOKENS = 12000
MIN_MAIN_WORDS = 1000
MIN_WORDS, MAX_WORDS = 850, 1200
CHUNK = int(os.environ.get('SUM_CHUNK', 192))   # papers per generate() call and per commit

SYSTEM = 'You are a careful scientific editor. You write accurate, clear and neutral summaries of research papers.'

# Pilot 1 (2026-11-23, 60 papers): "about 1,000 words" gave a median of ~620 words. Pilot 2 (7 x ~150 words) gave a median of ~860: the
# model writes ~125 words per "150-word" paragraph, so v3 asks for eight. Pilot 2 also repeated paragraph 3 in paragraph 4, echoed the
# prompt ("stated one by one... Firstly"), let LaTeX through and (AWQ) misread a flattened results table: v3 addresses each.
# Pilot 3 (v3, "eight paragraphs of about 150 words"): first drafts ~800 words, 70% needed the revision turn -> "at least 140 words" each.
STYLE = """Write a summary of this paper of about 1,000 to 1,200 words: exactly eight paragraphs, each at least 140 words long.

The eight paragraphs, in this order:
1. The problem the paper addresses and why it matters.
2. What the paper contributes, in plain sentences.
3. The approach: its key ideas and how it works.
4. Further technical detail that paragraph 3 did not cover: important design choices, assumptions, components or theoretical results.
5. How the paper tests its claims: the experiments, data, baselines and metrics, or the proofs, analyses or studies it uses.
6. The main results, with the important numbers.
7. Further findings: comparisons, ablations, analyses or secondary results the paper reports.
8. The limitations, open questions and implications that the authors themselves state.

Requirements:
- Be faithful. State only what the paper itself says. Do not add outside knowledge, speculation or your own evaluation. Do not invent applications, future work or numbers the paper does not give. If the paper says nothing on a point, say less rather than fill the gap.
- Numbers must be exact. Tables in the text above have lost their layout, so read each number from its correct row and column, and report a number only when you are sure which method, dataset, setting and metric it belongs to.
- Each paragraph adds new content; never restate what an earlier paragraph said.
- Write clear, precise prose for a reader with a general computer science background. Briefly define specialized terms the first time they appear, and keep the paper's own names for its methods, models, datasets and metrics. Describe mathematical results in words, using only simple inline notation when it is needed.
- Refer to the work as "the paper" or "the authors", in the present tense. Do not name the authors or their institutions, and do not cite other works by reference number.
- Use continuous prose only: no headings, paragraph labels, bullet points, numbered lists, enumerations such as "firstly" and "secondly", tables, LaTeX or markdown. Do not end with a generic concluding sentence or paragraph.
- Return only the summary, beginning directly with its first sentence."""

REVISE = {'too_short': ('Your summary has {n} words, but it must be about 1,000 words (eight paragraphs, each at least 140 words long). Rewrite it in full at '
                        'that length by adding more of the paper\'s own specific content: the details of the method, the setup of the evidence and '
                        'the results with their numbers, without repeating anything. Keep every requirement above. Return only the summary.'),
          'too_long': ('Your summary has {n} words, but it must be about 1,000 words (eight paragraphs, each at least 140 words long). Rewrite it in full '
                       'at that length, keeping the most important content and every requirement above. Return only the summary.')}

DIRECT = 'Below is the main text of a research paper titled "{title}" ({year}).\n\n<paper>\n{text}\n</paper>\n\n' + STYLE

FROM_NOTES = ('Below are detailed notes on consecutive parts of the main text of a research paper titled "{title}" ({year}). The paper was too '
              'long to show in full, so the notes stand in for it; treat them as the paper.\n\n<notes>\n{text}\n</notes>\n\n' + STYLE)

NOTES = """Below is part {i} of {n} of the main text of a research paper titled "{title}" ({year}).

<part>
{text}
</part>

Write detailed, faithful notes on this part, about 400 to 600 words. Record what it says about the problem and motivation, the method and its key ideas, theoretical results, the experimental setup (datasets, baselines, metrics), the results with their important numbers, and any limitations. State only what this part says. Write plain prose paragraphs with no headings, lists or markdown. Return only the notes."""

# retry: a too-short/too-long draft is sent back for one length revision (REVISE, greedy, the paper still in context; prefix caching reuses it);
# any other failure (cap, repetition, markdown, refusal) is resampled once with Qwen's own sampling defaults.
SAMPLING = dict(first=dict(temperature=0.0, top_p=1.0, repetition_penalty=1.05), retry=dict(temperature=0.7, top_p=0.8, repetition_penalty=1.05),
                seed=SEED, max_tokens=dict(summary=SUM_MAX_TOKENS, notes=NOTE_MAX_TOKENS))

S_SQL = '''create table if not exists s (k text primary key, paper_id text, school text, year int, title text, ok int, why text, first_why text,
    attempt text, mode text, n_parts int, text text, words int, paragraphs int, src_words int, src_tokens int, prompt_tokens int, gen_tokens int,
    finish text, raw_head text, src_hash text, seconds real, num_support real, has_latex int, first_words int);
create table if not exists notes (k text, part int, text text, gen_tokens int, finish text, primary key (k, part));
create table if not exists meta (key text primary key, value text);'''

LEAD = re.compile(r'^(?:here is|here\'s|below is|sure|certainly|summary\b|the following)', re.I)
TAIL = re.compile(r'^(?:note:|this summary|word count|\(word count|\[word count|i hope|let me know)', re.I)
REFUSE = re.compile(r"\b(?:I'm sorry|I am sorry|I cannot|I can't|as an AI)\b", re.I)
MD = re.compile(r'(^\s*(?:#+\s|[-*•]\s|\d+[.)]\s))|\*\*|__|\|\s*-{3}|^\s*\\\[|\$\$', re.M)   # markdown, lists, tables, display math
# Pilot 3: 11/96 rejections were theory papers stating bounds in inline LaTeX (O(\alpha \sqrt{d}) ...). That is content, so inline LaTeX is
# accepted and flagged (has_latex) rather than rejected; display math and markdown still fail.
LATEX = re.compile(r'\\[A-Za-z]+|\$[^$\s\d][^$]*\$|[_^]\{')


def log(**kw):
    print(json.dumps(dict(at=time.strftime('%H:%M:%S'), **kw)), flush=True)


def sha(s):
    return hashlib.sha1(s.encode()).hexdigest()


def clean(raw):
    """Keep paragraphs; drop a leading preamble line and trailing commentary; strip stray emphasis markers. -> text"""
    paras = [re.sub(r'\s+', ' ', p).strip() for p in re.split(r'\n\s*\n|\n(?=\S)', raw.strip())]
    paras = [p for p in paras if p]
    if len(paras) > 1 and len(paras[0]) < 160 and (paras[0].rstrip('*').endswith(':') or LEAD.match(paras[0].lstrip('*# '))):
        paras.pop(0)
    for i, p in enumerate(paras):
        if i > 0 and TAIL.match(p.lstrip('*#>-• ')):
            paras = paras[:i]; break
    paras = [re.sub(r'\*\*|__|\\[()]', '', p) for p in paras]   # inline-math delimiters \( \) are dropped, their content kept
    return '\n\n'.join(paras)


def looped(t, n=8, rep=4):
    w = t.lower().split()
    seen = {}
    for i in range(len(w) - n + 1):
        g = ' '.join(w[i:i + n]); seen[g] = seen.get(g, 0) + 1
        if seen[g] >= rep:
            return True
    return False


def num_support(summary, source):
    """Share of the summary's numbers (decimals and 2+ digit integers, years excluded) found verbatim in the source; None when it has none.
    Pilot 1: 245 of 252 (97%); the misses were roundings. A cheap fabrication check, not a proof of faithfulness."""
    nums = {n for n in re.findall(r'(?<![\w.])\d+\.\d+|(?<![\w.])\d{2,}(?!\w)', summary or '') if not re.fullmatch(r'(19|20)\d\d', n)}
    return round(sum(n in source for n in nums) / len(nums), 4) if nums else None


def judge(text, finish):
    """(ok, why)"""
    if finish == 'length':
        return 0, 'hit_token_cap'
    if not text or REFUSE.search(text[:300]):
        return 0, 'refusal_or_empty'
    if looped(text):
        return 0, 'repetition'
    if MD.search(text):
        return 0, 'markdown_or_list'
    n = len(text.split())
    if n < MIN_WORDS:
        return 0, 'too_short'
    if n > MAX_WORDS:
        return 0, 'too_long'
    return 1, ''


def split_parts(text, tok, budget=PART_TOKENS):
    """Paragraph-boundary parts of <= budget tokens (a paragraph longer than the budget is cut by tokens)."""
    parts, cur, cur_n = [], [], 0
    for p in re.split(r'\n\s*\n', text):
        ids = tok(p, add_special_tokens=False)['input_ids']
        while len(ids) > budget:
            if cur:
                parts.append('\n\n'.join(cur)); cur, cur_n = [], 0
            parts.append(tok.decode(ids[:budget])); ids = ids[budget:]
            p = tok.decode(ids)
        if cur_n + len(ids) > budget and cur:
            parts.append('\n\n'.join(cur)); cur, cur_n = [], 0
        cur.append(p); cur_n += len(ids)
    if cur:
        parts.append('\n\n'.join(cur))
    return parts


def snapshot_dir():
    snap = sorted(HF_HUB.glob(f"models--{GEN.replace('/', '--')}/snapshots/*/config.json"))
    if not snap:
        raise FileNotFoundError(GEN)
    return str(snap[0].parent)


def paper_meta():
    import pandas as pd
    d = pd.read_parquet(E32 / 'papers.parquet', columns=['k', 'paper_id', 'year', 'title', 'home_school'])
    return {r.k: (r.paper_id, r.year, r.title or '', r.home_school) for r in d.itertuples()}


def shard_db(shard, tag=''):
    p = WORK / 'shards' / f"sum-{shard}{('-' + tag) if tag else ''}.sqlite"
    p.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(p, timeout=600)
    db.executescript(S_SQL)
    return db


def run(a):
    t0 = time.time()
    db = shard_db(a.shard, a.tag)
    done = {r[0] for r in db.execute('select k from s')}
    want = set(json.loads(Path(a.ids).read_text())) if a.ids else None
    src = sqlite3.connect(f"file:{E32 / 'sections' / f'sections-{a.shard}.sqlite'}?mode=ro", uri=True, timeout=600)
    keys = [k for (k,) in src.execute('select k from sections order by k') if k not in done and (want is None or k in want)]
    if a.limit:
        keys = keys[:a.limit]
    meta = paper_meta()
    log(shard=a.shard, todo=len(keys), already=len(done))
    if not keys:
        if a.ids is None and not a.limit:
            db.execute("insert or replace into meta values ('complete', '1')"); db.commit()
        return
    os.environ.setdefault('VLLM_USE_V1', '0')   # V0 unless SUM_V1=1 (the slurm scripts export it)
    from vllm import LLM, SamplingParams
    import vllm
    path = snapshot_dir()
    kw = dict(quantization='awq_marlin') if 'AWQ' in GEN else {}
    llm = LLM(path, tensor_parallel_size=TP, dtype='bfloat16' if not kw else 'float16', max_model_len=MAX_MODEL_LEN, gpu_memory_utilization=0.92,
              seed=SEED, kv_cache_dtype=KV_DTYPE, enable_chunked_prefill=True, max_num_batched_tokens=8192, max_num_seqs=64,
              disable_custom_all_reduce=True, enable_prefix_caching=True, **kw)
    tok = llm.get_tokenizer()
    db.executemany('insert or replace into meta values (?,?)', [
        ('model', GEN), ('tp', str(TP)), ('vllm_v1', os.environ.get('VLLM_USE_V1', '')), ('kv_cache_dtype', KV_DTYPE), ('revise', json.dumps(REVISE)), ('revision', Path(path).name), ('vllm', vllm.__version__), ('system', SYSTEM), ('style', STYLE), ('direct', DIRECT),
        ('from_notes', FROM_NOTES), ('notes', NOTES), ('sampling', json.dumps(SAMPLING)), ('direct_max', str(DIRECT_MAX)),
        ('part_tokens', str(PART_TOKENS)), ('min_main_words', str(MIN_MAIN_WORDS)), ('words', f'{MIN_WORDS}-{MAX_WORDS}'),
        ('source', str(E32)), ('started', time.strftime('%Y-%m-%dT%H:%M:%S'))])
    db.commit()

    def chat(user, draft=None, revise=None):
        m = [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': user}]
        if draft is not None:
            m += [{'role': 'assistant', 'content': draft}, {'role': 'user', 'content': revise}]
        return tok.apply_chat_template(m, tokenize=False, add_generation_prompt=True)

    def sp(kind, retry=False):
        s = SAMPLING['retry' if retry else 'first']
        return SamplingParams(max_tokens=SAMPLING['max_tokens'][kind], seed=SEED, **s)

    n_ok = n_bad = 0
    last = None
    for c0 in range(0, len(keys), CHUNK):
        if last and time.time() - t0 + last * 1.2 > a.budget:
            log(stopped_for_budget=True, elapsed=round(time.time() - t0), remaining=len(keys) - c0)
            sys.exit(75)
        t1 = time.time()
        ks = keys[c0:c0 + CHUNK]
        q = ','.join('?' * len(ks))
        rows, jobs = [], {}       # jobs[k] = dict(...) for papers that get generated
        for k, school, mw, blob in src.execute(f'select k, school, main_words, main from sections where k in ({q})', ks):
            pid, year, title, home = meta.get(k, (None, None, '', school))
            base = dict(k=k, paper_id=pid, school=home or school, year=year, title=title, src_words=mw or 0)
            if not mw or mw < MIN_MAIN_WORDS:
                rows.append(dict(base, ok=0, why='main_under_1000_words')); continue
            text = zlib.decompress(blob).decode()
            ids = tok(text, add_special_tokens=False)['input_ids']
            yr = str(year) if year else 'year unknown'
            ttl = title.strip() or 'untitled'
            j = dict(base, src_tokens=len(ids), src_hash=sha(text), yr=yr, ttl=ttl, src_text=text)
            if len(ids) <= DIRECT_MAX:
                u = DIRECT.format(title=ttl, year=yr, text=text)
                j.update(mode='direct', n_parts=1, user=u, prompt=chat(u))
            else:
                parts = split_parts(text, tok)
                j.update(mode='notes', n_parts=len(parts),
                         note_prompts=[chat(NOTES.format(i=i + 1, n=len(parts), title=ttl, year=yr, text=p)) for i, p in enumerate(parts)])
            jobs[k] = j
        # phase 1: notes for long papers
        nreq = [(k, i, p) for k, j in jobs.items() if j['mode'] == 'notes' for i, p in enumerate(j['note_prompts'])]
        if nreq:
            outs = llm.generate([p for _, _, p in nreq], sp('notes'), use_tqdm=False)
            nrows = []
            for (k, i, _), o in zip(nreq, outs):
                jobs[k].setdefault('notes', {})[i] = clean(o.outputs[0].text)
                nrows.append((k, i, jobs[k]['notes'][i], len(o.outputs[0].token_ids), o.outputs[0].finish_reason))
            db.executemany('insert or replace into notes values (?,?,?,?,?)', nrows)
            for k, j in jobs.items():
                if j['mode'] == 'notes':
                    body = '\n\n'.join(f'[Notes on part {i + 1} of {j["n_parts"]}]\n{j["notes"][i]}' for i in range(j['n_parts']))
                    j['user'] = FROM_NOTES.format(title=j['ttl'], year=j['yr'], text=body)
                    j['prompt'] = chat(j['user'])
        # phase 2: summaries, then one retry for generation failures
        order = list(jobs)
        for attempt in (1, 2):
            todo = [k for k in order if attempt == 1 or not jobs[k]['ok']]
            if not todo:
                break
            prompts, sps = [], []
            for k in todo:
                j = jobs[k]
                if attempt == 2 and j['why'] in REVISE:
                    pr = chat(j['user'], j['text'], REVISE[j['why']].format(n=len(j['text'].split())))
                    if len(tok(pr, add_special_tokens=False)['input_ids']) + SUM_MAX_TOKENS <= MAX_MODEL_LEN:
                        prompts.append(pr); sps.append(sp('summary')); j['retry_kind'] = 'revise'; continue
                prompts.append(j['prompt']); sps.append(sp('summary', retry=attempt == 2)); j['retry_kind'] = 'resample'
            outs = llm.generate(prompts, sps, use_tqdm=False)
            for k, o in zip(todo, outs):
                j = jobs[k]
                raw, fin = o.outputs[0].text, o.outputs[0].finish_reason
                text = clean(raw)
                ok, why = judge(text, fin)
                if attempt == 1:
                    j['first_words'] = len(text.split())
                if attempt == 1:
                    j['first_why'] = why
                j.update(ok=ok, why=why, attempt=attempt, text=text, finish=fin, raw_head=raw[:160], prompt_tokens=len(o.prompt_token_ids),
                         gen_tokens=len(o.outputs[0].token_ids))
        el = time.time() - t1
        for k in order:
            j = jobs[k]
            rows.append(dict(j, words=len(j['text'].split()), paragraphs=j['text'].count('\n\n') + 1 if j['text'] else 0, seconds=el / max(1, len(order)),
                             num_support=num_support(j['text'], j['src_text']), has_latex=int(bool(LATEX.search(j['text']))), attempt=j['attempt'] if j['attempt'] == 1 else f"2:{j.get('retry_kind')}"))
        cols = ['k', 'paper_id', 'school', 'year', 'title', 'ok', 'why', 'first_why', 'attempt', 'mode', 'n_parts', 'text', 'words', 'paragraphs',
                'src_words', 'src_tokens', 'prompt_tokens', 'gen_tokens', 'finish', 'raw_head', 'src_hash', 'seconds', 'num_support', 'has_latex', 'first_words']
        db.executemany(f'insert or replace into s values ({",".join("?" * len(cols))})', [tuple(r.get(c) for c in cols) for r in rows])
        db.commit()
        n_ok += sum(1 for r in rows if r['ok']); n_bad += sum(1 for r in rows if not r['ok'])
        last = el
        log(shard=a.shard, chunk=c0 // CHUNK, papers=len(ks), generated=len(order), long=sum(1 for j in jobs.values() if j['mode'] == 'notes'),
            ok=n_ok, bad=n_bad, seconds=round(el), per_paper=round(el / max(1, len(order)), 2), elapsed=round(time.time() - t0))
    db.execute("insert or replace into meta values ('complete', ?)", ('1' if a.ids is None and not a.limit else '0',))
    db.execute("insert or replace into meta values ('finished', ?)", (time.strftime('%Y-%m-%dT%H:%M:%S'),))
    db.commit()


def pilot_ids(a):
    """n papers from shard 0 and 1, stratified: mostly by main length quartile, plus every long (>DIRECT_MAX-ish, >21k words) paper up to 8."""
    out = []
    for sh in (0, 1):
        src = sqlite3.connect(f"file:{E32 / 'sections' / f'sections-{sh}.sqlite'}?mode=ro", uri=True)
        rows = sorted(src.execute('select k, main_words from sections where main_words >= ?', (MIN_MAIN_WORDS,)), key=lambda r: sha(f'{SEED}|{r[0]}'))
        longs = [k for k, w in rows if w > 21000][:4]
        out += longs + [k for k, _ in rows if k not in longs][:a.n // 2 - len(longs)]
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / 'pilot_ids.json').write_text(json.dumps(sorted(out)))
    log(pilot=len(out))


def status(a):
    for f in sorted((WORK / 'shards').glob('sum-*.sqlite')):
        db = sqlite3.connect(f'file:{f}?mode=ro', uri=True)
        n, ok = db.execute('select count(*), coalesce(sum(ok),0) from s').fetchone()
        why = dict(db.execute("select why, count(*) from s where ok = 0 group by why"))
        log(file=f.name, rows=n, ok=ok, failures=why)


def merge(a):
    files = sorted(f for f in (WORK / 'shards').glob('sum-*.sqlite') if re.fullmatch(r'sum-\d+\.sqlite', f.name))
    tmp = WORK / 'summaries.sqlite.tmp'
    tmp.unlink(missing_ok=True)
    db = sqlite3.connect(tmp)
    db.executescript(S_SQL)
    for f in files:
        db.execute('attach ? as x', (str(f),))
        db.execute('insert or replace into s select * from x.s'); db.execute('insert or replace into notes select * from x.notes')
        db.execute('insert or replace into meta select * from x.meta where key not in ("started", "finished", "complete")')
        db.commit(); db.execute('detach x')
    db.execute("insert or replace into meta values ('merged', ?)", (time.strftime('%Y-%m-%dT%H:%M:%S'),))
    db.execute("insert or replace into meta values ('shards', ?)", (str(len(files)),))
    db.commit()
    n, ok = db.execute('select count(*), sum(ok) from s').fetchone()
    db.close()
    os.replace(tmp, WORK / 'summaries.sqlite')
    log(merged=len(files), rows=n, ok=ok)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['run', 'pilot-ids', 'merge', 'status'])
    ap.add_argument('--shard', type=int, default=0)
    ap.add_argument('--limit', type=int)
    ap.add_argument('--ids')
    ap.add_argument('--tag', default='')
    ap.add_argument('--n', type=int, default=120)
    ap.add_argument('--budget', type=int, default=int(os.environ.get('SUM_BUDGET', 10 ** 9)))
    a = ap.parse_args()
    {'run': run, 'pilot-ids': pilot_ids, 'merge': merge, 'status': status}[a.cmd](a)
