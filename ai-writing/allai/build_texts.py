"""Rewrites -> an `abstracts` table that embed.py can read (--texts-db), after the content-preservation filter.

  build_texts.py build --style polish|paraphrase [--subsample]
reads   EMB/allai/rewrites_<style>.sqlite (rewrite.py merge) and EMB/texts.sqlite (title, original abstract)
writes  EMB/allai/texts_<style>.sqlite   abstracts(paper_id PK, title, abstract = the rewrite, src, words, text_hash = hash(title + '\\n' + rewrite))
        EMB/allai/flags_<style>.parquet   one row per rewrite: ok, why, the preservation checks and keep (the filter's verdict)
The filter (preserve.py `keep_rule`): the rewrite is ok (not truncated, not a refusal), loses fewer than 25% of the source's numbers, adds
no more than 25% new numbers, and loses fewer than 25% of its named methods (acronyms / CamelCase / hyphenated names). Rows that fail are
reported with their reason and left out of the all-AI corpus; the analyses then compare the SAME papers' originals and rewrites.
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'embeddings'))
sys.path.insert(0, str(HERE))
import ecommon as C  # noqa: E402
import preserve as PR  # noqa: E402

ALLAI = C.EMB / 'allai'


def build(style, subsample=False):
    rw = sqlite3.connect(f'file:{ALLAI / f"rewrites_{style}.sqlite"}?mode=ro', uri=True)
    rows = rw.execute('select paper_id, text, ok, why, words from rw').fetchall()
    tx = sqlite3.connect(f'file:{C.TEXTS_DB}?mode=ro', uri=True, timeout=600)
    src = {p: (t or '', a) for p, t, a in tx.execute('select paper_id, title, abstract from abstracts')}
    tx.close()
    flags, keep = [], []
    for pid, text, ok, why, words in rows:
        title, ab = src[pid]
        f = PR.checks(ab, text) if ok else {}
        k, reason = PR.keep_rule(ok, why, f)
        flags.append(dict(paper_id=pid, ok=int(ok), why=why or '', keep=int(k), reason=reason, **f))
        if k:
            keep.append((pid, title, text, f'allai_{style}', len(text.split()), C.text_hash(title + '\n' + text)))
    out = ALLAI / f'texts_{style}.sqlite'

    def write(t):
        db = sqlite3.connect(t)
        db.execute('create table abstracts (paper_id text primary key, title text, abstract text, src text, words int, text_hash text)')
        db.executemany('insert into abstracts values (?,?,?,?,?,?)', keep)
        db.commit(); db.close()
    C.atomic_write(out, write)
    df = pd.DataFrame(flags)
    df.to_parquet(ALLAI / f'flags_{style}.parquet', index=False)
    C.log(style=style, rewrites=len(rows), kept=len(keep), reasons=json.dumps(df[df['keep'] == 0]['reason'].value_counts().to_dict()))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd', choices=['build']); ap.add_argument('--style', default='polish')
    a = ap.parse_args()
    build(a.style)
