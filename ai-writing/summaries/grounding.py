"""Per-sentence grounding check: one query per summary sentence, the paper in context (owner target 2026-11-23: < 1% of SUMMARIES with any
unsupported sentence).

Why per sentence (pilot 4 + first Gemma audit): asking for a numbered list of verdicts with quotes failed two ways — both models "quoted" the
summary back instead of the paper, and the numbering drifted on 40-sentence lists (Gemma gave reasons that belonged to other sentences).
One sentence per query, with the previous sentence for pronouns, removes both. The paper is the shared prefix of every query of a paper, so
vLLM prefix caching computes it once: queries run in groups of GROUP papers, one warm-up query per paper first, then the rest.

Verdict: SUPPORTED, or UNSUPPORTED: <the part not stated>. A sentence also fails when its numbers are not in the paper
(summarize.unsupported_numbers) or the answer has no verdict. Long papers are checked part by part (supported if any part supports it).
"""
import re

HEADER = 'Below is the main text of a research paper titled "{title}" ({year}).\n\n<paper>\n{text}\n</paper>\n\n'
PART_HEADER = 'Below is part {i} of {n} of the main text of a research paper titled "{title}" ({year}).\n\n<part>\n{text}\n</part>\n\n'

CHECK = """A summary of this paper contains the sentence below.{prev}

Sentence: "{s}"

Is everything this sentence states (each fact, number, name, comparison, result and claim) stated in the {where} above, or a direct consequence of it? Generic or evaluative statements that the {where} does not make, for example about limitations, applications, significance, further findings or what the authors acknowledge, count as not stated.
Answer on one line: SUPPORTED, or UNSUPPORTED followed by a colon and the part that is not stated."""

GROUP = 12
MAX_TOKENS = 60

ABBR = r'(?:e\.g|i\.e|et al|etc|vs|Fig|Figs|Eq|Eqs|Sec|Ref|No|approx|cf|resp|Dr|Mr|Ms|Prof|al)'


def sentences(para):
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
    """[(paragraph index, sentence)]"""
    return [(pi, s) for pi, p in enumerate(t for t in text.split('\n\n') if t.strip()) for s in sentences(p)]


def join_summary(sents):
    paras = {}
    for pi, s in sents:
        paras.setdefault(pi, []).append(s)
    return '\n\n'.join(' '.join(v) for _, v in sorted(paras.items()))


def parse(answer):
    """(True, '') | (False, reason)"""
    t = answer.strip().lstrip('*#>-• ').strip()
    if re.match(r'^SUPPORTED\b', t, re.I):
        return True, ''
    if re.match(r'^(UN|NOT\s)SUPPORTED\b', t, re.I):
        return False, re.sub(r'^(UN|NOT\s)SUPPORTED\s*[:.\-]?\s*', '', t, flags=re.I)[:240] or 'unsupported'
    return False, 'no_verdict: ' + t[:120]


def contexts(paper, tok, title, year, max_paper_tokens, split_parts):
    """[(header, where)] : the whole paper when it fits, else its parts."""
    n = len(tok(paper, add_special_tokens=False)['input_ids'])
    if n <= max_paper_tokens:
        return [(HEADER.format(title=title, year=year, text=paper), 'paper text')]
    parts = split_parts(paper, tok, budget=max_paper_tokens // 2)
    return [(PART_HEADER.format(i=i + 1, n=len(parts), title=title, year=year, text=p), 'part of the paper') for i, p in enumerate(parts)]


def check(llm, sampling, chat, papers, numbers_bad):
    """papers: {key: dict(ctx=[(header, where)], sents=[(pi, s)], src=str)}; checks every sentence not yet in papers[key]['verdict'].
    Fills papers[key]['verdict'][s] = (ok, reason). numbers_bad(s, src) -> list of unsupported numbers."""
    keys = list(papers)
    for g0 in range(0, len(keys), GROUP):
        group = keys[g0:g0 + GROUP]
        reqs = []
        for k in group:
            p = papers[k]
            p.setdefault('verdict', {})
            prev = ''
            for _, s in p['sents']:
                if s not in p['verdict']:
                    for ci, (h, where) in enumerate(p['ctx']):
                        pv = f'\n\nThe sentence just before it, for context: "{prev}"' if prev else ''
                        reqs.append((k, s, ci, chat(h + CHECK.format(prev=pv, s=s, where=where))))
                prev = s
        if not reqs:
            continue
        # warm the prefix cache: the first query of every (paper, part) alone, then the rest
        first, seen = [], set()
        for i, r in enumerate(reqs):
            if (r[0], r[2]) not in seen:
                seen.add((r[0], r[2])); first.append(i)
        rest = [i for i in range(len(reqs)) if i not in set(first)]
        outs = {}
        for batch in (first, rest):
            if batch:
                for i, o in zip(batch, llm.generate([reqs[i][3] for i in batch], sampling, use_tqdm=False)):
                    outs[i] = o.outputs[0].text
        agg = {}
        for i, (k, s, ci, _) in enumerate(reqs):
            ok, why = parse(outs[i])
            if ok:
                bad = numbers_bad(s, papers[k]['src'])
                if bad:
                    ok, why = False, 'number_not_in_paper: ' + ', '.join(bad[:5])
            cur = agg.get((k, s))
            if cur is None or (ok and not cur[0]):
                agg[(k, s)] = (ok, why)
        for (k, s), v in agg.items():
            papers[k]['verdict'][s] = v
