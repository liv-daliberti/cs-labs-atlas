"""Shared pieces of the passage-level AI-written-text detector (v2, DESIGN-v2.md section 1).

passages  the diversity battery's splitter, imported from ai-writing/diversity/common.py (passages(body): consecutive
          sentence-bounded passages of ~150 words, 40-400 words, >= 70% printable words, <= 100 evenly spaced per
          paper; usable_text: >= 1,000 body words and, for a PDF, the title found on page 1). Not copied, so the
          detector scores exactly the segments the battery embeds; SPLITTER_SHA records which version was used.
norm      v1's normalizer (detector.py: markup, HTML, 'Abstract' labels, whitespace), extended for PDF bodies:
          NFKC (ligatures, math-italic letters), LaTeX math rendered as a PDF text layer shows it (delatex), end-of-line
          hyphenation undone, numeric and author-year citation markers removed. Applied to every text, human or generated, training or scoring.
split     by paper: sha1(seed|key) -> train 70% / cal 10% / test 20%; a paper's passages and their AI versions
          always share a split.
"""
import hashlib, inspect, re, sys, unicodedata
from pathlib import Path

sys.dont_write_bytecode = True  # importing diversity/common.py must not write a __pycache__ there
HERE = Path(__file__).resolve().parent
AIW = HERE.parent
DATA, MODELS, RESULTS, LOGS = HERE / 'data', HERE / 'models', HERE / 'results', HERE / 'logs'
FULLTEXT = AIW / 'fulltext.sqlite'
HF = '/n/fs/resemble/cs-atlas-env/hf-cache/hub'
SEED = 20261022
PRE = range(2016, 2022)  # human training text: published 2016-2021, before ChatGPT
GENS = ('qwen72b', 'qwen7b', 'llama70b')
GEN_REPO = {'qwen72b': 'Qwen/Qwen2.5-72B-Instruct', 'qwen7b': 'Qwen/Qwen2.5-7B-Instruct', 'llama70b': 'meta-llama/Llama-3.3-70B-Instruct'}
TASKS = ('polish', 'paraphrase', 'notes')
BASE = 'answerdotai/ModernBERT-large'

sys.path.insert(0, str(AIW / 'diversity'))
from common import passages, usable_text, wordish_ratio  # noqa: E402  (numpy-only import)
import common as _div  # noqa: E402

SPLITTER_SHA = hashlib.sha1(inspect.getsource(_div.passages).encode()).hexdigest()[:12]


def snapshot(repo):
    """Local snapshot directory of a cached model (the cache lacks refs/main for some repos, so a repo id cannot
    be resolved offline)."""
    import glob
    snap = sorted(glob.glob(f"{HF}/models--{repo.replace('/', '--')}/snapshots/*/config.json"))
    if not snap:
        raise FileNotFoundError(repo)
    return str(Path(snap[0]).parent)


def split_of(key):
    u = int(hashlib.sha1(f'{SEED}|{key}'.encode()).hexdigest()[:8], 16) / 16 ** 8
    return 'train' if u < 0.7 else 'cal' if u < 0.8 else 'test'


CITE_NUM = re.compile(r'\[\s*\d+(?:\s*[,;–—\-]\s*\d+)*\s*\]')
_NAME = r"[A-Z][A-Za-z\-'’]+(?: [A-Z][A-Za-z\-'’]+)?(?: et al\.?| and [A-Z][A-Za-z\-'’]+| & [A-Z][A-Za-z\-'’]+)?,? (?:19|20)\d{2}[a-z]?"
CITE_AY = re.compile(r'\((?:see |e\.g\., ?|cf\. ?|i\.e\., ?)?' + _NAME + r'(?:\s*[;,]\s*' + _NAME + r')*\)')


SYM = {'alpha': 'α', 'beta': 'β', 'gamma': 'γ', 'delta': 'δ', 'epsilon': 'ϵ', 'varepsilon': 'ε', 'zeta': 'ζ', 'eta': 'η', 'theta': 'θ',
       'kappa': 'κ', 'lambda': 'λ', 'mu': 'μ', 'nu': 'ν', 'xi': 'ξ', 'pi': 'π', 'rho': 'ρ', 'sigma': 'σ', 'tau': 'τ', 'phi': 'ϕ',
       'varphi': 'φ', 'chi': 'χ', 'psi': 'ψ', 'omega': 'ω', 'Gamma': 'Γ', 'Delta': '∆', 'Theta': 'Θ', 'Lambda': 'Λ', 'Sigma': 'Σ',
       'Phi': 'Φ', 'Pi': 'Π', 'Psi': 'Ψ', 'Omega': 'Ω', 'in': '∈', 'notin': '∉', 'leq': '≤', 'le': '≤', 'geq': '≥', 'ge': '≥',
       'neq': '≠', 'ne': '≠', 'approx': '≈', 'sim': '∼', 'times': '×', 'cdot': '·', 'pm': '±', 'sum': '∑', 'prod': '∏', 'int': '∫',
       'infty': '∞', 'partial': '∂', 'nabla': '∇', 'forall': '∀', 'exists': '∃', 'subset': '⊂', 'subseteq': '⊆', 'cup': '∪',
       'cap': '∩', 'rightarrow': '→', 'to': '→', 'leftarrow': '←', 'Rightarrow': '⇒', 'mapsto': '7→', 'ldots': '...', 'dots': '...',
       'cdots': '···', 'log': 'log', 'exp': 'exp', 'max': 'max', 'min': 'min', 'arg': 'arg', 'sqrt': '√', 'mid': '|', 'langle': '⟨',
       'rangle': '⟩', 'top': '⊤', 'ell': 'ℓ', 'emptyset': '∅', 'circ': '◦', 'star': '⋆', 'ast': '∗', 'propto': '∝', 'equiv': '≡'}
MATH = re.compile(r'\\\((.+?)\\\)|\\\[(.+?)\\\]|\$\$(.+?)\$\$|\$([^$]{1,300}?)\$', re.S)
WRAP = re.compile(r'\\(?:mathbf|mathcal|mathrm|mathit|mathbb|mathsf|boldsymbol|textbf|textit|textrm|text|emph|operatorname|hat|bar|tilde|vec|widehat|overline)\s*\{([^{}]*)\}')


def _tex(t):
    t = WRAP.sub(r'\1', t)
    t = re.sub(r'\\(?:frac|dfrac|tfrac)\s*\{([^{}]*)\}\s*\{([^{}]*)\}', r'\1/\2', t)
    t = re.sub(r'\\([A-Za-z]+)', lambda k: SYM.get(k.group(1), ''), t)
    return re.sub(r'[{}_^$]|\\[,;:! ]?', '', t)


def delatex(t):
    """LaTeX math as a PDF's text layer shows it: delimiters, braces, sub/superscript marks and commands go, Greek
    letters and common operators become their glyphs (generators write '\\( r_{i-1} \\)' where pdftotext gives 'ri−1')."""
    t = MATH.sub(lambda m: ' ' + _tex(next(g for g in m.groups() if g is not None)).strip() + ' ', t)
    if '\\' in t:  # stray LaTeX outside delimiters: wrappers unwrapped, known commands as glyphs
        t = WRAP.sub(r'\1', t)
        t = re.sub(r'\\([A-Za-z]+)', lambda k: SYM.get(k.group(1), k.group(0)), t)
    return t


def norm(t):
    t = unicodedata.normalize('NFKC', str(t or ''))
    t = delatex(t)
    t = re.sub(r'<[^>]+>', ' ', t); t = re.sub(r'\*\*|__|^#+\s*', '', t, flags=re.M)
    t = re.sub(r'^\s*(?:abstract|summary)\s*[:.\-—]?\s*', '', t, flags=re.I)
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'(?<=[a-z])- (?=[a-z])', '', t)  # "algo- rithm" (pdftotext line-end hyphenation)
    t = CITE_NUM.sub('', t); t = CITE_AY.sub('', t)
    t = re.sub(r'\s+([.,;:)])', r'\1', t)
    return re.sub(r'\s+', ' ', t).strip()


_SENT = re.compile(r'(?<=[.!?])\s+')


def quality(text):
    """Cheap extraction-quality proxies of a raw passage, for stratifying the false-positive rate:
    wordish   share of printable words (the splitter's own filter, >= 0.7 by construction)
    midcap    share of words after a sentence's first that start upper-case (column interleaving and inline
              headers raise it)
    nonascii  share of characters outside ASCII (math symbols, garbled glyphs)"""
    w = text.split()
    mid = [x for s in _SENT.split(text) for x in s.split()[1:]]
    return dict(wordish=round(wordish_ratio(w), 4), midcap=round(sum(x[:1].isupper() for x in mid) / max(1, len(mid)), 4),
                nonascii=round(sum(ord(c) > 127 for c in text) / max(1, len(text)), 4))
