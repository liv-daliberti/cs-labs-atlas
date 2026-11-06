"""Shared pieces of the writing-style study (README.md): paths and years. Environment: STYLE_OUT (default <ai-writing>/data/style), STYLE_TAG
(default 'latest'), STYLE_AI (detector table, default AI_SCORES/papers.parquet), STYLE_FULLTEXT_DB (texts DB with the full-text bodies, default
EMB/texts.sqlite: today's body; the section-split main body replaces it when `agent/fulltext-sections` lands).
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AIW = HERE.parent
for _d in (AIW / 'embeddings', AIW / 'lineage'):
    if str(_d) not in sys.path:
        sys.path.append(str(_d))
import ecommon as C  # noqa: E402

P = C.P
OUT = Path(os.environ.get('STYLE_OUT') or (P.AI_WRITING / 'data' / 'style'))
RUN = OUT / (os.environ.get('STYLE_TAG') or 'latest')
AI_TABLE = Path(os.environ.get('STYLE_AI') or (P.AI_SCORES / 'papers.parquet'))
FT_DB = Path(os.environ.get('STYLE_FULLTEXT_DB') or C.TEXTS_DB)
ABS_DB = C.TEXTS_DB
ALLAI_DB = C.EMB / 'allai' / 'texts_polish.sqlite'
KOBAK_CSV = P.HOMOGENIZATION_STUDY / 'lit' / 'kobak_reference' / 'kobak_2024_style_words.csv'
Y0, Y1 = 2016, 2025


def kobak_words():
    return {w.strip().lower() for w in KOBAK_CSV.read_text().splitlines()[1:] if w.strip()}
