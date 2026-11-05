"""Shared pieces of the lab-level study (README.md here): configuration, paths and the paper/lab frames.

Paths come from tools/atlas_paths.py (AI_SCORES, EMBEDDINGS slots; the outputs go to ai-writing/data/labstudy, git-ignored) and can be
redirected by config.json / LABSTUDY_* environment variables, so a re-run on the final paper set or on detector v3 needs no code change:
  LABSTUDY_SCORES_DB   an ai_scores.sqlite-shaped container (papers table: paper_id, ai_share, flag_abstract, ...)   default AI_SCORES/ai_scores.sqlite
  LABSTUDY_UNIVERSE_DB universe.sqlite (papers, lab_papers)                                                          default EMBEDDINGS/universe.sqlite
  LABSTUDY_PAPER_SET   optional file with one paper id per line (or a parquet with paper_id): the final paper set; the universe is cut to it
  LABSTUDY_IPW_TABLE   the weights table (default OUT/ipw/ipw_weights.parquet)
  LABSTUDY_OUT         output directory (default ai-writing/data/labstudy)
Owner rules (2026-11-04/05): no 2026 in any series or estimate (last_year 2025); intervals not point estimates; lab measures use the strict lab set
(lab_papers = a lab's PI is on the byline; advisers' labs never count).
"""
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

_AIW = Path(__file__).resolve().parents[1]
sys.path.append(str(_AIW.parent / 'tools'))
import atlas_paths as P  # noqa: E402
import pandas as pd  # noqa: E402

for _d in ('dose', 'embeddings', 'diversity', 'allai', 'detector_v2'):
    if str(_AIW / _d) not in sys.path:
        sys.path.append(str(_AIW / _d))

HERE = Path(__file__).resolve().parent


def load_config(path=None):
    cfg = json.loads((Path(path or os.environ.get('LABSTUDY_CONFIG') or HERE / 'config.json')).read_text())
    for k in ('scores_db', 'universe_db', 'paper_set', 'ipw_table', 'out_dir'):
        v = os.environ.get('LABSTUDY_' + k.upper())
        if v:
            cfg[k] = v
    return cfg


CFG = load_config()
EMB = P.EMBEDDINGS
AI_DATA = Path(P.AI_SCORES).parent                      # ai-writing/data (main checkout)
OUT = Path(CFG['out_dir'] or AI_DATA / 'labstudy')
SCORES_DB = Path(CFG['scores_db'] or Path(P.AI_SCORES) / 'ai_scores.sqlite')
UNIVERSE_DB = Path(CFG['universe_db'] or EMB / 'universe.sqlite')
IPW_TABLE = Path(CFG['ipw_table'] or OUT / 'ipw' / 'ipw_weights.parquet')
REPORTS = Path(os.environ.get('LABSTUDY_REPORT_DIR') or _AIW / 'diversity' / 'reports')
YEARS = list(range(CFG['first_year'], CFG['last_year'] + 1))
PRE = [y for y in YEARS if y <= CFG['pre_end']]
POST = [y for y in YEARS if y >= CFG['post_start']]
BREAKS = CFG['placebo_breaks']
SEED = 20261105
MODELS_ABS = ['specter2_base', 'specter2_proximity', 'scincl', 'qwen3_0p6b', 'gte_qwen2_1p5b', 'bge_m3', 'nomic_v15']


def log(**kw):
    print(json.dumps(kw, default=str), flush=True)


def out(*parts):
    p = OUT.joinpath(*parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def write_atomic(df, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name('.tmp-' + path.name)
    df.to_parquet(tmp, index=False)
    os.replace(tmp, path)


# ---- department types (the dept string of lab_papers is the PI's first listed department; 226 spellings across schools)
_DEPT_RULES = [
    ('social_business', r'^(Sloan|BOOTH|Tepper|Heinz|Operations, Information|Business Analytics|Marketing)'),
    ('eecs', r'^EECS|/ EECS|^Physics / EECS'),
    ('ee', r'^(ECE|EE|Electrical|Distributed Electrical|Signal Processing|Communication Theory|STI/IEL)\b|^Electrical|^STI/IEL|Information and Inference'),
    ('cs', r'^(CS|CSE|CSD|CSAIL|IC|HCII|RI|MLD|ML|LTI|ROB|TTIC|CBD|S3D|UMSI|DSI|LMC|CSP|ID|CHILI)\b|Computer|Computing|Machine Learning|Machine learning|Robot|'
           r'Artificial|Intelligen|Information|Learning|Language|Vision|Software|Data\b|Algorithm|Network|Systems|Security|Theory of|Neuro(AI|science & AI)|^(SCI-IC|ENAC/IIC|DATA|LA[A-Z0-9]*|L[A-Z]{2,4}[0-9]?|DIS[A-Z]*|DCSL|DEDIS|IVRL|LCAV1|CVLAB|BIOROB|MLO|PARSA|VLSC)$'),
    ('math_stats', r'^(MATH|STAT|SB/MATH|Math|Statistic|Biostat|Statistical|Continuous Optimization)'),
    ('engineering', r'^(ISYE|ME|MechE|Mechanical|Aeronautics|AE|AERO|CEE|Civil|ChemE|Chemical|BME|Bioengineering|IOE|Operations Research|Industrial|Management Science|STI/|ENAC|Energy|MSE|Intelligent Maintenance)|Engineering|Aerospace'),
    ('life_medical', r'Radiolog|Neuro|Brain|BIOS|Molecular|Biomedical|Biology|Psychiatr|Urolog|Oncolog|Medicine|Clinical|Optometr|Integrative|Ecology|Earth|Environmental|SV/BMI|SCHELLER|Princeton Neuroscience'),
    ('social_business', r'Sloan|BOOTH|Tepper|Heinz|Operations, Information|Marketing|Econom|Psycholog|PSYC|Communication|Philosoph|Education|Sociolog|Linguistic|SPP|EPP|Music|MUSIC|Architecture|ARCH|Design|Media|Law|Anthropolog|Urban|Social|Business|Museology|RISD'),
]


def dept_type(d):
    d = (d or '').strip()
    if not d:
        return 'unknown'
    for name, rx in _DEPT_RULES:
        if re.search(rx, d):
            return name
    return 'other'


# ---- universe, labs
def universe(first=None, last=None):
    """(papers, lab_papers): papers 2016-2025 (config), restricted to config paper_set when given; lab_papers with dept_type."""
    db = sqlite3.connect(f'file:{UNIVERSE_DB}?mode=ro', uri=True)
    papers = pd.read_sql('select paper_id, oa, doi, title, year, home_school, schools, n_labs from papers', db)
    lp = pd.read_sql('select * from lab_papers', db)
    db.close()
    papers = papers[papers['year'].between(first or CFG['first_year'], last or CFG['last_year'])]
    if CFG.get('paper_set'):
        ps = CFG['paper_set']
        keep = set(pd.read_parquet(ps)['paper_id']) if ps.endswith('.parquet') else set(Path(ps).read_text().split())
        papers = papers[papers['paper_id'].isin(keep)]
    papers = papers.reset_index(drop=True)
    lp = lp[lp['paper_id'].isin(set(papers['paper_id']))].copy()
    lp['year'] = lp['paper_id'].map(papers.set_index('paper_id')['year'])
    lp['dept_type'] = lp['dept'].map(dept_type)
    return papers, lp.reset_index(drop=True)


def scores():
    db = sqlite3.connect(f'file:{SCORES_DB}?mode=ro', uri=True)
    df = pd.read_sql('select * from papers', db)
    db.close()
    return df


def lab_table(lp):
    """One row per lab: lab_id, school, dept, dept_type, n_papers (strict membership)."""
    g = lp.groupby('lab_id')
    t = g.agg(school=('school', 'first'), dept=('dept', lambda s: s.dropna().iloc[0] if s.notna().any() else None), n_papers=('paper_id', 'nunique')).reset_index()
    t['dept_type'] = t['dept'].map(dept_type)
    return t


def load_weights(col='w_ft'):
    """Series paper_id -> weight from the IPW table (None when the table does not exist yet)."""
    if not IPW_TABLE.exists():
        return None
    return pd.read_parquet(IPW_TABLE).set_index('paper_id')[col]


# ---- LLM topics (from topic labels; reported separately everywhere)
LLM_LABEL_RE = re.compile(r'language model|\bllms?\b|\bgpt|chatgpt|\bprompt|in-?context|instruction[- ]?(tun|follow)|\brlhf|chatbot|generative ai|large language|'
                          r'foundation model|\bagents?\b.*\b(llm|language)|retrieval[- ]augmented|\brag\b|hallucinat|chain[- ]of[- ]thought|\bvlms?\b|diffusion models', re.I)
LLM_STRICT_RE = re.compile(r'language model|\bllms?\b|\bgpt|chatgpt|\bprompt|in-?context|instruction[- ]?(tun|follow)|\brlhf|chatbot|generative ai|large language|hallucinat|chain[- ]of[- ]thought', re.I)
