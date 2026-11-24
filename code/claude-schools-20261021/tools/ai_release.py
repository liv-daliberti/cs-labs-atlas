"""The AI-writing pages' data in a release (owner 2026-11-04): the release directory carries an `ai/` folder with exactly
the JSON files the three site pages read, and `ai/manifest.json` with their hashes. The site's release step
(site/scripts/import-ai-release.py) copies them from the release; the site never reads the working paths.

  ai/ai_hist.json, ai/ai_position.json, ai/labs_ai_hist_<school>.json[.gz]     page "How much AI" and "Given AI, how much"
                                                                               (ai-writing/dose/dose_site.py; git-ignored)
  ai/ai_share.json                                                             optional: the homogenization study's AI-share layer (ai-writing/study/study_ai_share.py): year-by-year rise with
                                                                               lab-bootstrap intervals, main body vs main body + appendix, false-positive correction, coverage, detector error table
  ai/lab_ai_scores_2025.json                                                   optional: each lab's 2025 AI-use score (Data page and CS departments page)
  ai/words/{words,word_curves}.json                                            optional: the AI words page (ai-writing/dose/ai_words_site.py)
  ai/all-ai/{labs,methods,novelty,overall,preservation,schools,trend}.json     page "All papers AI-written" (tracked)
  ai/manifest.json   schema, release, source commit, last year, bytes and sha256 per file

Opt-in: a release carries `ai/` only when the source folder is named (make_release.py --ai-site-data DIR, or the
CS_ATLAS_AI_SITE_DATA variable), because the dose files are generated, not tracked. A named folder must be complete.
Owner rule: no 2026 anywhere (a partial year); a series that includes it refuses the release.
"""
import gzip
import hashlib
import json
import re
from pathlib import Path

LAST_YEAR = 2025
DOSE_FILES = ['ai_hist.json', 'ai_position.json']
LAB_SCORE_FILE = 'lab_ai_scores_2025.json'
SHARE_FILE = 'ai_share.json'
SHARE_MEASURES = ['heavy_main', 'heavy_main_appendix', 'dose_main', 'dose_main_appendix']
LAB_FILE = re.compile(r'^labs_ai_hist_[a-z0-9_-]+\.json(\.gz)?$')
ALL_AI_FILES = ['labs.json', 'methods.json', 'novelty.json', 'overall.json', 'preservation.json', 'schools.json', 'trend.json']
WORDS_FILES = ['words.json', 'word_curves.json']   # ai-writing/dose/ai_words_site.py; optional, but a words/ folder must hold both
MANIFEST_NAME = 'ai/manifest.json'


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def collect(root):
    """{release path: source file} for the named folder; SystemExit when it is incomplete."""
    root = Path(root)
    src = {}
    for n in DOSE_FILES:
        if not (root / n).is_file():
            raise SystemExit(f'AI site data incomplete: {root / n} is missing (ai-writing/dose/dose_site.py)')
        src[f'ai/{n}'] = root / n
    labs = sorted(p for p in root.iterdir() if p.is_file() and LAB_FILE.match(p.name))
    if not labs:
        raise SystemExit(f'AI site data incomplete: no labs_ai_hist_<school>.json in {root}')
    for p in labs:
        src[f'ai/{p.name}'] = p
    if (root / LAB_SCORE_FILE).is_file():    # optional: the per-lab 2025 AI-use scores (ai-writing/dose/lab_ai_score.py, site/ copy)
        src[f'ai/{LAB_SCORE_FILE}'] = root / LAB_SCORE_FILE
    if (root / SHARE_FILE).is_file():        # optional: the AI-share layer of the study snapshot; checked by check_share
        src[f'ai/{SHARE_FILE}'] = root / SHARE_FILE
    for n in ALL_AI_FILES:
        if not (root / 'all-ai' / n).is_file():
            raise SystemExit(f'AI site data incomplete: {root / "all-ai" / n} is missing (ai-writing/allai/site_data.py build)')
        src[f'ai/all-ai/{n}'] = root / 'all-ai' / n
    if (root / 'words').is_dir():
        for n in WORDS_FILES:
            if not (root / 'words' / n).is_file():
                raise SystemExit(f'AI site data incomplete: {root / "words" / n} is missing (ai-writing/dose/ai_words_site.py assemble)')
            src[f'ai/words/{n}'] = root / 'words' / n
    return src


def _load(p):
    p = Path(p)
    raw = p.read_bytes()
    return json.loads(gzip.decompress(raw) if p.suffix == '.gz' else raw)


def years_in(obj, path=''):
    """Every year value found under a key named year / years or as a key of a series map, as (path, year)."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if re.fullmatch(r'(19|20)\d\d', str(k)):
                out.append((f'{path}/{k}', int(k)))
            if k == 'year' and isinstance(v, (int, float)) and not isinstance(v, bool):
                out.append((f'{path}/year', int(v)))
            out += years_in(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:5000]):
            out += years_in(v, f'{path}[{i}]')
    return out


def check_years(src):
    """Refuse a file with any year after LAST_YEAR (the owner's no-2026 rule), in series keys, `year` fields and meta."""
    bad = []
    for rel, p in src.items():
        data = _load(p)
        for where, y in years_in(data):
            if y > LAST_YEAR:
                bad.append(f'{rel}{where}={y}')
                break
        meta = data.get('meta') if isinstance(data, dict) else None
        if isinstance(meta, dict) and isinstance(meta.get('last_year'), int) and meta['last_year'] > LAST_YEAR:
            bad.append(f'{rel}/meta/last_year={meta["last_year"]}')
    if bad:
        raise SystemExit(f'AI site data includes a year after {LAST_YEAR} (owner rule: no 2026): {bad[:5]}')


def check_share(src):
    """ai_share.json must carry the series the site page draws (SystemExit otherwise): meta, error_table, and for scope `all` every measure for every year 2016-2025."""
    p = src.get(f'ai/{SHARE_FILE}')
    if p is None:
        return
    d = _load(p)
    for k in ('meta', 'series', 'contrasts', 'coverage', 'error_table'):
        if k not in d:
            raise SystemExit(f'ai/{SHARE_FILE} lacks `{k}` (ai-writing/study/study_ai_share.py)')
    for m in SHARE_MEASURES:
        yrs = [r['year'] for r in d['series'].get('all', {}).get(m, [])]
        if yrs != list(range(2016, LAST_YEAR + 1)):
            raise SystemExit(f'ai/{SHARE_FILE}: series all/{m} must cover exactly 2016-{LAST_YEAR}, got {yrs[:3]}...{yrs[-1:]}')


def manifest(release_id, commit, entries):
    """The ai/manifest.json body: bytes and sha256 of every ai/ file but itself (entries = {path: {bytes, sha256}})."""
    files = {k: dict(bytes=v['bytes'], sha256=v['sha256']) for k, v in sorted(entries.items()) if k.startswith('ai/') and k != MANIFEST_NAME}
    return dict(schema=1, release=release_id, source_commit=commit, last_year=LAST_YEAR, files=files)
