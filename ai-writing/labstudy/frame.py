"""Build the paper frame and the strict lab membership used by the three analyses.

  frame.py            -> OUT/frame.parquet (one row per universe paper, 2016-2025), OUT/lab_papers.parquet (paper_id, lab_id, school, dept, dept_type, year), OUT/labs.parquet
Columns of the frame: ids and year, home school, OpenAlex type/field/subfield/topic, venue type (source_type), open-access status, DOI prefix (publisher key),
team size, references, citations, detector scores (ai_share = scored full text only; flag_abstract, p_ai_abstract = every abstract), selection indicators
(has_abstract, has_ft = scored full text, usable_ft), the two BERTopic topic ids, and llm_text (title/abstract regex, the dose study's LLM_RE).
"""
import json
import sqlite3

import pandas as pd

import lcommon as L

LLM_RE_PATTERN = r'large language model|\bLLMs?\b|\bGPT[- ]?\d?|ChatGPT|language model|foundation model|in-context|prompt(?:ing)?\b|instruction[- ]tun'


def oa_fields():
    db = sqlite3.connect(f'file:{L.EMB / "oa_fields.sqlite"}?mode=ro', uri=True)
    rows = db.execute('select id, type, primary_topic from works').fetchall()
    db.close()
    out = []
    for i, ty, pt in rows:
        t = json.loads(pt) if pt and pt != 'null' else {}
        out.append((i, ty, t.get('name'), t.get('subfield'), t.get('field'), t.get('domain')))
    return pd.DataFrame(out, columns=['oa_id', 'work_type', 'oa_topic', 'oa_subfield', 'oa_field', 'oa_domain'])


def oa_extra():
    p = L.EMB / 'oa_extra.sqlite'
    db = sqlite3.connect(f'file:{p}?mode=ro', uri=True)
    df = pd.read_sql('select id as oa_id, oa_status, is_oa, source_type, source_name, n_authors, n_refs, cited_by from works', db)
    db.close()
    return df


def build():
    papers, lp = L.universe()
    sc = L.scores()
    keep = [c for c in ('paper_id', 'ai_share', 'ai_any', 'flag_abstract', 'p_ai_abstract', 'kobak_abs', 'kobak_ft', 'ai_share_cal', 'body_words', 'n_passages') if c in sc]
    df = papers.merge(sc[keep], on='paper_id', how='left')
    df['oa_id'] = df['oa'].fillna('').str.rsplit('/', n=1).str[-1]
    df = df.merge(oa_fields(), on='oa_id', how='left').merge(oa_extra(), on='oa_id', how='left')
    df['doi_prefix'] = df['doi'].fillna('').str.lower().str.extract(r'(10\.\d{4,9})', expand=False)
    db = sqlite3.connect(f'file:{L.EMB / "texts.sqlite"}?mode=ro', uri=True)
    ab = pd.read_sql('select paper_id, title, abstract from abstracts', db)
    ft = pd.read_sql('select paper_id, usable from fulltext', db)
    db.close()
    ab['llm_text'] = (ab['title'].fillna('') + ' ' + ab['abstract'].fillna('')).str.contains(LLM_RE_PATTERN, case=False, regex=True)
    df = df.merge(ab[['paper_id', 'llm_text']], on='paper_id', how='left')
    df['has_abstract'] = df['llm_text'].notna()
    df['llm_text'] = df['llm_text'].fillna(False)
    df['usable_ft'] = df['paper_id'].map(ft.set_index('paper_id')['usable']).fillna(0).astype(int)
    df['has_ft'] = df['ai_share'].notna()
    for m in ('qwen3_0p6b', 'specter2_proximity'):
        t = pd.read_parquet(L.EMB / 'results' / f'topics_{m}.parquet').set_index('paper_id')['topic']
        df['bt_' + m] = df['paper_id'].map(t)
    L.write_atomic(df, L.out('frame.parquet'))
    L.write_atomic(lp[['paper_id', 'lab_id', 'school', 'dept', 'dept_type', 'year']], L.out('lab_papers.parquet'))
    labs = L.lab_table(lp)
    L.write_atomic(labs, L.out('labs.parquet'))
    L.log(step='frame', papers=len(df), has_abstract=int(df['has_abstract'].sum()), has_ft=int(df['has_ft'].sum()), lab_rows=len(lp), labs=len(labs),
          dept_types=labs['dept_type'].value_counts().to_dict())


def load():
    return (pd.read_parquet(L.out('frame.parquet')), pd.read_parquet(L.out('lab_papers.parquet')), pd.read_parquet(L.out('labs.parquet')))


if __name__ == '__main__':
    build()
