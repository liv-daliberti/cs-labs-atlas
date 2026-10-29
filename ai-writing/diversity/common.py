"""Shared loaders for the diversity battery (DESIGN-v2.md sections 2-3).

papers     ai-writing/papers.jsonl.gz, read fresh on every run (it is rebuilt as papers are recovered); 2016-2026 only.
           A lab is (school, PI); a paper of two labs counts in both.
ai usage   pluggable (AIW_AI_SOURCE = auto | abstract | paragraph):
             paragraph  ai-writing/paragraph_scores.jsonl.gz {key, n_paragraphs, ai_share, ai_any}: dose = ai_share,
                        flag = ai_share >= 0.25 (the design's per-lab cut)
             abstract   ai-writing/scores.jsonl.gz (v1 detector, threshold at 1% FPR): dose = flag = flagged
           auto picks paragraph when that file exists. p_ai (the abstract score) is always carried as its own column.
abstract   ai-writing/embeddings.npz (SPECTER2 base, CLS of title [SEP] abstract, papers with 50+ word abstracts)
full text  ai-writing/fulltext.sqlite is still being written by fulltext.py, so it is read in short rowid-chunked
           statements with a long busy timeout (a long read would starve the writer's commit, whose busy timeout is
           Python's default 5 s), into one snapshot file (SNAPSHOT, data/ft_snapshot.sqlite; jobs copy it to node-local
           /tmp). Segments for the full-text embeddings:
           the paragraphs table when it holds >= 3 paragraphs for a paper, else sentence-bounded passages of ~150 words
           cut from the body (the stored bodies are whitespace-flattened, so blank-line paragraphs cannot be recovered).
references corpus/s2.sqlite of the homogenization study (static), cached as data/s2_refs_cache.pkl.gz

Passage splitter for other tools (e.g. the v2 passage-level detector): `from common import passages, segments,
usable_text` with diversity/ on sys.path (numpy only). passages(body) gives the exact segments the full-text embeddings
use when a paper has < 3 rows in the paragraphs table; segments(body, paras) applies that rule; usable_text(kind, body,
flags) is the full-text filter; seg_signature(src, segs) identifies a segmentation.
"""
import getpass, gzip, hashlib, json, os, pickle, re, sqlite3, sys, time, zlib
from collections import defaultdict
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
AIW = ROOT.parent
HOM = Path('/n/fs/resemble/maxent-grpo/.research-sweeps/claude-homogenization-20261019')
BACKGROUND = HOM / 'corpus' / 'background.sqlite'
S2DB = HOM / 'corpus' / 's2.sqlite'
KOBAK = HOM / 'lit' / 'kobak_reference' / 'kobak_2024_rare_style_words.csv'
DATA, FIG, RES, LOGS = ROOT / 'data', ROOT / 'figures', ROOT / 'results', ROOT / 'logs'
LOCAL = Path(os.environ.get('AIW_DIV_LOCAL', f'/tmp/aiw-diversity-{getpass.getuser()}'))
EMB_STORE = DATA / 'fulltext_emb.sqlite'
EMB_READ = Path(os.environ.get('AIW_EMB_STORE', EMB_STORE))  # read-only copy: run_battery.slurm puts one on node-local /tmp
SNAPSHOT = Path(os.environ.get('AIW_SNAPSHOT', DATA / 'ft_snapshot.sqlite'))  # one file on the share; run_battery.slurm copies it to node-local /tmp
BG_EMB = DATA / 'background_specter2base.npz'
SCHOOLS = ('princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford')
LABEL = {'princeton': 'Princeton', 'cmu': 'CMU', 'epfl': 'EPFL', 'mit': 'MIT', 'berkeley': 'Berkeley', 'stanford': 'Stanford'}
YEARS = range(2016, 2027)
PRE, POST = range(2016, 2023), range(2023, 2027)
COMPARISONS = {'main': (PRE, POST), 'placebo2019': (range(2016, 2019), range(2019, 2023)),
               'placebo2020': (range(2016, 2020), range(2020, 2023))}
SEED = 20261022
MIN_WORDS_FT = 1000  # a full text shorter than this (after the References cut) is a stub, not a paper



def llm_pattern():
    """The homogenization study's LLM-topic pattern (title + abstract), imported lazily so that the text helpers below
    (passages, segments, usable_text) import with numpy alone."""
    if str(HOM / 'tools') not in sys.path:
        sys.path.insert(0, str(HOM / 'tools'))
    from homog import LLM
    return LLM


def log(**kw):
    print(json.dumps(kw, default=str), flush=True)


def lab_id(school, pi):
    return f'{school}|{pi}'


def load_papers():
    """[{key, school, year, title, abstract, doi, labs:[lab ids], llm}] for 2016-2026, and {lab id: meta}."""
    papers, meta = [], {}
    LLM = llm_pattern()
    with gzip.open(AIW / 'papers.jsonl.gz', 'rt') as f:
        for line in f:
            p = json.loads(line)
            try:
                y = int(p.get('year'))
            except (TypeError, ValueError):
                continue
            if y not in YEARS:
                continue
            labs = []
            for l in p['labs']:
                i = lab_id(p['school'], l['pi'])
                if i not in labs:
                    labs.append(i)
                meta.setdefault(i, dict(lab=i, school=p['school'], pi=l['pi'], name=l.get('lab') or l['pi'], dept=l.get('dept')))
            papers.append(dict(key=p['key'], school=p['school'], year=y, title=p.get('title') or '', abstract=p.get('abstract') or '',
                               doi=p.get('doi'), labs=labs, llm=bool(LLM.search((p.get('title') or '') + ' ' + (p.get('abstract') or '')))))
    return papers, meta


def load_ai(source=None):
    """({key: dict(dose, flag, p_ai)}, source name). dose is the per-paper AI amount (a share for the paragraph detector,
    0/1 for the abstract detector), flag the paper-level 'more AI' indicator, p_ai the abstract score (both sources)."""
    source = source or os.environ.get('AIW_AI_SOURCE', 'auto')
    para = AIW / 'paragraph_scores.jsonl.gz'
    p_ai = {}
    if (AIW / 'scores.jsonl.gz').exists():
        for line in gzip.open(AIW / 'scores.jsonl.gz', 'rt'):
            s = json.loads(line); p_ai[s['key']] = (float(s['p_ai']), bool(s['flagged']))
    out = {}
    if source == 'paragraph' or (source == 'auto' and para.exists()):
        for line in gzip.open(para, 'rt'):
            s = json.loads(line)
            if s.get('ai_share') is None or not s.get('n_paragraphs'):
                continue
            sh = float(s['ai_share'])
            out[s['key']] = dict(dose=sh, flag=sh >= 0.25, any=bool(s.get('ai_any')), n_par=int(s['n_paragraphs']),
                                 p_ai=p_ai.get(s['key'], (None, None))[0])
        return out, 'paragraph'
    for k, (p, fl) in p_ai.items():
        out[k] = dict(dose=float(fl), flag=fl, p_ai=p)
    return out, 'abstract'


def load_abstract_embeddings():
    """(keys, raw float32 X). Callers centre / normalize as the measure needs."""
    E = np.load(AIW / 'embeddings.npz')
    return [str(k) for k in E['keys']], E['X'].astype(np.float32)


def center_normalize(X, mu=None):
    """Subtract the corpus mean (SPECTER2 is anisotropic: two random CS papers sit at cosine ~0.8) and L2-normalize."""
    mu = X.mean(0) if mu is None else mu
    Y = X - mu
    return Y / (np.linalg.norm(Y, axis=1, keepdims=True) + 1e-9), mu


def normalize(X):
    return X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)


# ---------------------------------------------------------------- full texts

def _ro(path, timeout=1800):
    return sqlite3.connect(f'file:{path}?mode=ro', uri=True, timeout=timeout)


def snapshot_fulltext(rows_per_read=600):
    """Copy texts and paragraphs from the live ai-writing/fulltext.sqlite into SNAPSHOT, in rowid
    chunks (each statement reads ~10 MB, well under a second), pausing between chunks so the writer gets its locks."""
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    tmp, dst = SNAPSHOT.with_name('tmp_' + SNAPSHOT.name), SNAPSHOT
    if tmp.exists():
        tmp.unlink()
    src = _ro(AIW / 'fulltext.sqlite')
    out = sqlite3.connect(tmp)
    out.execute('create table texts (key text primary key, school text, kind text, chars int, body blob, flags text)')
    out.execute('create table paragraphs (key text, i int, text text, primary key (key, i))')
    t0 = time.time()
    hi = src.execute('select max(rowid) from texts').fetchone()[0] or 0
    for lo in range(0, hi + 1, rows_per_read):
        rows = src.execute('select key, school, kind, chars, body, flags from texts where rowid >= ? and rowid < ?', (lo, lo + rows_per_read)).fetchall()
        out.executemany('insert or replace into texts values (?,?,?,?,?,?)', rows)
        time.sleep(0.05)
    hi = src.execute('select max(rowid) from paragraphs').fetchone()[0] or 0
    for lo in range(0, hi + 1, 20000):
        rows = src.execute('select key, i, text from paragraphs where rowid >= ? and rowid < ?', (lo, lo + 20000)).fetchall()
        out.executemany('insert or replace into paragraphs values (?,?,?)', rows)
        time.sleep(0.05)
    out.commit()
    n = out.execute('select count(*) from texts').fetchone()[0], out.execute('select count(*) from paragraphs').fetchone()[0]
    out.close(); src.close()
    os.replace(tmp, dst)
    log(snapshot=str(dst), texts=n[0], paragraphs=n[1], seconds=round(time.time() - t0))
    return dst


def iter_snapshot(keys=None, chunk=2000):
    """Yield (key, school, kind, body text, flags dict, [paragraph texts]) from the local snapshot."""
    db = sqlite3.connect(SNAPSHOT)
    paras = defaultdict(list)
    for k, i, t in db.execute('select key, i, text from paragraphs order by key, i'):
        paras[k].append(t)
    hi = db.execute('select max(rowid) from texts').fetchone()[0] or 0
    for lo in range(0, hi + 1, chunk):
        for k, school, kind, chars, body, flags in db.execute('select key, school, kind, chars, body, flags from texts where rowid >= ? and rowid < ?', (lo, lo + chunk)):
            if keys is not None and k not in keys:
                continue
            if not body:
                continue
            yield k, school, kind, zlib.decompress(body).decode('utf-8', 'ignore'), json.loads(flags or '{}'), paras.get(k, [])
    db.close()


SENT = re.compile(r'(?<=[.!?])\s+(?=[A-Z(\[])')
WORDISH = re.compile(r'^[A-Za-z][A-Za-z\-\']*[.,;:]?$')  # fulltext.py's printable-word check


def wordish_ratio(words):
    return sum(bool(WORDISH.match(x)) for x in words) / max(1, len(words))


def passages(body, target=150, lo=40, hi=400, cap=100):
    """The body cut into consecutive passages at sentence ends: a passage closes once it reaches `target` words
    (sentences longer than `hi` words are hard-split), the remainder is kept if it has >= `lo` words. Passages whose
    words are < 70% printable words (tables, equations, reference lists) are dropped, as in fulltext.py. A paper with
    more than `cap` passages keeps `cap` evenly spaced ones (long theses would otherwise dominate the GPU budget)."""
    out, cur = [], []
    for s in SENT.split(body):
        cur.extend(s.split())
        while len(cur) >= target:
            if len(cur) <= hi:
                out.append(' '.join(cur)); cur = []
            else:
                out.append(' '.join(cur[:hi])); cur = cur[hi:]
    if len(cur) >= lo:
        out.append(' '.join(cur))
    keep = [p for p in out if wordish_ratio(p.split()) >= 0.7]
    if len(keep) > cap:
        keep = [keep[i] for i in np.linspace(0, len(keep) - 1, cap).round().astype(int)]
    return keep


def segments(body, paras):
    """('paragraphs', the table's paragraphs) when there are >= 3 of them, else ('passages', passages(body))."""
    if len(paras) >= 3:
        return 'paragraphs', list(paras)
    return 'passages', passages(body)


def seg_signature(src, segs):
    return hashlib.sha1((src + '\n' + '\n'.join(segs)).encode()).hexdigest()[:16]


def usable_text(kind, body, flags):
    """A full text counts when the body has >= MIN_WORDS_FT words and, for a PDF, the extractor found the paper's
    title on its first page (fulltext_store's identity check; XML bodies carry no title, so they are kept)."""
    if len(body.split()) < MIN_WORDS_FT:
        return False
    return kind != 'pdf' or bool(flags.get('title_found', True))


# ---------------------------------------------------------------- full-text embedding store

def emb_store(write=False):
    DATA.mkdir(exist_ok=True)
    db = sqlite3.connect(EMB_STORE, timeout=600) if write else _ro(EMB_READ, 600)
    if write:
        db.execute('create table if not exists emb (key text primary key, sig text, src text, n_seg int, mean blob, segs blob, at text)')
    return db


def load_fulltext_means():
    """{key: (n_seg, src, mean float32 768)} from the store (empty if nothing has been embedded yet)."""
    if not EMB_READ.exists():
        return {}
    db = emb_store()
    out = {k: (n, s, np.frombuffer(m, dtype=np.float32)) for k, n, s, m in db.execute('select key, n_seg, src, mean from emb where n_seg > 0')}
    db.close()
    return out


def iter_fulltext_segments(keys=None):
    """Yield (key, float32 n_seg x 768) for the stored papers."""
    db = emb_store()
    for k, n, b in db.execute('select key, n_seg, segs from emb where n_seg > 0'):
        if keys is None or k in keys:
            yield k, np.frombuffer(b, dtype=np.float16).reshape(n, -1).astype(np.float32)
    db.close()


def load_background():
    """(ids, years, raw float32 X) of the arXiv CS background sample re-embedded with specter2_base, or None."""
    if not BG_EMB.exists():
        return None
    B = np.load(BG_EMB)
    return [str(x) for x in B['ids']], B['years'].astype(int), B['X'].astype(np.float32)


# ---------------------------------------------------------------- references

def _nt(t):
    import unicodedata
    t = unicodedata.normalize('NFKD', t or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', t)


def s2_index():
    """{lookup id: (paperId, year, refs [(paperId, year, venue id)] or None)} plus {normalized title: lookup id},
    from the homogenization study's s2.sqlite, cached by that file's mtime."""
    cache = DATA / 's2_refs_cache.pkl.gz'
    stamp = S2DB.stat().st_mtime
    if cache.exists():
        with gzip.open(cache, 'rb') as f:
            c = pickle.load(f)
        if c.get('stamp') == stamp:
            return c['rec'], c['title']
    db = _ro(S2DB)
    rec, title = {}, {}
    for lid, r in db.execute('select lookup_id, record from records where record is not null'):
        d = json.loads(r)
        refs = d.get('references')
        refs = None if refs is None else [(x.get('paperId'), x.get('year'), (x.get('publicationVenue') or {}).get('id')) for x in refs if x.get('paperId')]
        rec[lid] = (d.get('paperId'), d.get('year'), refs)
        t = _nt(d.get('title'))
        if len(t) >= 20:
            title.setdefault(t, lid)
    db.close()
    with gzip.open(cache, 'wb') as f:
        pickle.dump(dict(stamp=stamp, rec=rec, title=title), f, protocol=4)
    return rec, title


def match_refs(papers):
    """{key: (s2 paperId, refs list)} for papers with an S2 record; refs is None when S2 holds no reference list."""
    rec, title = s2_index()
    out = {}
    for p in papers:
        d = (p.get('doi') or '').lower()
        cands = []
        if d.startswith('10.48550/arxiv.'):
            cands.append('ARXIV:' + d.split('arxiv.', 1)[1])
        elif d:
            cands += ['DOI:' + p['doi'], 'DOI:' + d]
        t = _nt(p['title'])
        cands.append('match:' + t)
        if t in title:
            cands.append(title[t])
        for c in cands:
            if c in rec:
                out[p['key']] = (rec[c][0], rec[c][2]); break
    return out
