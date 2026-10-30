# Vendored 2026-10-30 from /n/fs/resemble/maxent-grpo/.research-sweeps/claude-homogenization-20261019/tools/homog.py (sha256 623a9d09df9a701e13ddfdfac6b6537efce10e470936acd3603a5b440938b005); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Shared pieces for the homogenization measures: corpus loading (with Semantic Scholar enrichment), LLM-paper flag,
lab panels, equal-size sampling, and the interrupted-time-series test.

Periods: pre 2016–2022, transition 2023 (many papers written before ChatGPT, released 2022-11-30), post 2024–2026.
Variants every measure reports:
  all      every paper
  no_llm   papers whose title/abstract are not about LLMs / foundation models / prompting (is the change just the move
           into LLM research?)
  panel    only labs with >= PANEL_MIN papers in both 2016–2022 and 2024–2026 (the same labs before and after)
  pi_papers only papers in a lab by the strict rule, a school PI named on the paper (the user's 2026-10-20 choice: keep
           every paper, but the study is strict); school-level measures without student-only and unidentified papers
ITS: a linear trend fitted on 2016–2022 is extrapolated to 2024–2026; the effect is the mean post-period deviation in
units of the pre-period residual spread, with placebo breaks at 2019 and 2020 (fit on the years before the placebo,
test 2019/2020–2022) to show how large a "break" the method finds when there is none.
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import gzip, json, re, sqlite3
from collections import defaultdict
from pathlib import Path
import numpy as np

HERE = P.HOMOGENIZATION_STUDY  # vendored: the data root (was Path(__file__).resolve().parents[1])
CORPUS = HERE / 'corpus'
LLM = re.compile(r'\b(large language models?|llms?|gpt-?\d\w*|chatgpt|foundation models?|in-context learning|instruction[- ]tun\w*|'
                 r'chain[- ]of[- ]thought|prompt(s|ing|ed)?|language models?)\b', re.I)
PRE, POST = range(2016, 2023), range(2024, 2027)
PANEL_MIN = 10
# the schools the corpus holds, in build_corpus.py's order (Princeton, CMU, EPFL, then MIT once built)
SCHOOLS = tuple(json.loads((CORPUS / 'summary.json').read_text())['schools']) if (CORPUS / 'summary.json').exists() else ('princeton', 'cmu', 'epfl')


def lookup_id(r):
    d = (r.get('doi') or '').lower()
    if d and not d.startswith('10.48550/'):
        return 'DOI:' + r['doi']
    if r.get('arxiv'):
        return 'ARXIV:' + r['arxiv']
    return None


def nt(t):
    import unicodedata
    t = unicodedata.normalize('NFKD', t or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', t)


def load(embeddings=False):
    """Corpus rows with S2 fields merged in: abstract (filled when missing), s2_id, publication_date, references
    [(paperId, year, venue id)], and, with embeddings=True, a float32 L2-normalized matrix aligned to the rows (rows
    without an embedding get None in 'emb_row')."""
    rows = [json.loads(l) for l in gzip.open(CORPUS / 'papers.jsonl.gz', 'rt')]
    recs, embs = {}, {}
    if (CORPUS / 's2.sqlite').exists():
        db = sqlite3.connect(f"file:{CORPUS / 's2.sqlite'}?mode=ro", uri=True)
        q = 'SELECT lookup_id, record, embedding FROM records WHERE record IS NOT NULL' if embeddings else \
            'SELECT lookup_id, record, NULL FROM records WHERE record IS NOT NULL'
        for lid, rec, emb in db.execute(q):
            recs[lid] = json.loads(rec)
            if emb is not None:
                embs[lid] = emb
    vecs = []
    for r in rows:
        rec = recs.get(r.get('s2_lookup') or lookup_id(r) or ('match:' + nt(r['title'])))
        r['s2'] = bool(rec)
        r['abstract_source'] = 'own' if len(r['abstract']) >= 200 else None
        if rec:
            if len(r['abstract']) < 200 and len(rec.get('abstract') or '') >= 200:
                r['abstract'] = rec['abstract']; r['abstract_source'] = 's2'
            r['s2_id'] = rec.get('paperId'); r['publication_date'] = rec.get('publicationDate')
            r['refs'] = [(x.get('paperId'), x.get('year'), (x.get('publicationVenue') or {}).get('id')) for x in rec.get('references') or [] if x.get('paperId')]
        else:
            r['refs'] = None
        if r['abstract_source'] is None and r.get('abstract_extra'):  # OpenAlex / Crossref / the stored PDF (tools/corpus_checks.py)
            r['abstract'] = r['abstract_extra']; r['abstract_source'] = r.get('abstract_extra_source')
        r['llm'] = bool(LLM.search(r['title'] + ' ' + r['abstract']))
        if embeddings:
            e = embs.get(r.get('s2_lookup') or lookup_id(r) or ('match:' + nt(r['title'])))
            if e is not None:
                r['emb_row'] = len(vecs); vecs.append(np.frombuffer(e, dtype=np.float16).astype(np.float32))
            else:
                r['emb_row'] = None
    if embeddings:
        M = np.vstack(vecs) if vecs else np.zeros((0, 768), np.float32)
        M /= np.linalg.norm(M, axis=1, keepdims=True) + 1e-9
        return rows, M
    return rows


def panel(rows, school):
    pre, post = defaultdict(int), defaultdict(int)
    for r in rows:
        if r['school'] != school:
            continue
        for l in r['labs']:
            if r['year'] in PRE:
                pre[l] += 1
            elif r['year'] in POST:
                post[l] += 1
    return {l for l in pre if pre[l] >= PANEL_MIN and post.get(l, 0) >= PANEL_MIN}


def variants(rows, school):
    """{variant: predicate(row)} for one school."""
    keep = panel(rows, school)
    return {'all': lambda r: True, 'no_llm': lambda r: not r['llm'], 'panel': lambda r, k=keep: bool(set(r['labs']) & k),
            'pi_papers': lambda r: bool(r['labs'])}


def lab_groups(rows, k, min_labs=5, labs_filter=None):
    """{lab: [rows]} for labs with >= k rows (each row may belong to several labs)."""
    g = defaultdict(list)
    for r in rows:
        for l in r['labs']:
            if labs_filter is None or l in labs_filter:
                g[l].append(r)
    g = {l: v for l, v in g.items() if len(v) >= k}
    return g if len(g) >= min_labs else {}


TEST_POST = (2024, 2025)  # 2026 is a partial year: shown, not tested, until year-to-date dates are in


def disjoint_draw(groups, k, rng):
    """{lab: k rows} with no paper drawn for two labs (a paper attributed to two labs would make them look alike
    mechanically; the literature's pitfall 6). Labs are visited in random order; a lab with fewer than k unused papers
    is left out of this draw."""
    used, out = set(), {}
    for l in rng.permutation(list(groups)):
        pool = [r for r in groups[l] if r['id'] not in used]
        if len(pool) < k:
            continue
        pick = [pool[i] for i in rng.choice(len(pool), k, replace=False)]
        used.update(r['id'] for r in pick); out[l] = pick
    return out


def its(series):
    """series {year: value}. With only seven pre-period years, a residual-SD z-score is badly inflated (a line through
    a few points leaves tiny residuals), so the test is calibrated against placebo breaks instead:
      level_change    mean(2024–2025) - mean(2019–2022)
      trend_dev       mean deviation of 2024–2025 from the 2016–2022 linear trend, extended forward
      placebo_devs    the same deviation for fake breaks at 2019, 2020 and 2021 (trend fitted on 2016..break-1,
                      deviation measured on break..2022), when there was no ChatGPT
      beyond_placebo  |trend_dev| exceeds every |placebo_dev| (a break larger than the method finds without one)"""
    def dev(train, test):
        xs = [y for y in train if series.get(y) is not None]
        tx = [y for y in test if series.get(y) is not None]
        if len(xs) < 3 or not tx:
            return None
        b = np.polyfit(xs, [series[y] for y in xs], 1)
        return float(np.mean([series[y] - np.polyval(b, y) for y in tx]))
    mean = lambda ys: float(np.mean([series[y] for y in ys if series.get(y) is not None])) if any(series.get(y) is not None for y in ys) else None
    pre, post = mean(range(2019, 2023)), mean(TEST_POST)
    d = dev(PRE, TEST_POST)
    plac = [p for b in (2019, 2020, 2021) if (p := dev(range(2016, b), range(b, 2023))) is not None]
    r = lambda v: None if v is None else round(v, 5)
    return dict(level_change=r(post - pre) if pre is not None and post is not None else None, trend_dev=r(d),
                placebo_devs=[r(p) for p in plac], beyond_placebo=bool(d is not None and plac and abs(d) > max(abs(p) for p in plac)))


def save(name, doc, results):
    (HERE / 'results').mkdir(exist_ok=True)
    out = dict(rule=doc, results=results)
    for school, by_var in results.items():
        for var, by_metric in by_var.items():
            for metric, series in list(by_metric.items()):
                if isinstance(series, dict) and series and all(isinstance(k, int) for k in series):
                    by_metric[metric] = dict(series=series, its=its(series))
    (HERE / 'results' / f'{name}.json').write_text(json.dumps(out, indent=1, default=str))
    return out
