"""Shared constants and helpers of the field-300 abstract-level homogenization study (owner decision 2026-11-08): all 300 GRAS 2025 CS&E universities.

Standard library + pandas/numpy only (the py310 env). Paths come from study_common (atlas_paths); the roster is the copy of the GRAS work in docs/cohort.
Conventions are those of the 12-school study: 2016-2025, pre = 2016-2022, post = 2023-2025, placebo = 2019-21 minus 2016-18, no 2026.
"""
import csv
import os
import re
from pathlib import Path

import study_common as SC

ID = 'field300-2026-11-08'
FIRST, LAST = SC.FIRST, SC.LAST
PRE = list(range(2016, 2023))
POST = [2023, 2024, 2025]
PLACEBO_A, PLACEBO_B = [2016, 2017, 2018], [2019, 2020, 2021]
ENGLISH_SPEAKING = {'US', 'GB', 'CA', 'AU', 'NZ', 'IE'}   # institution country (OpenAlex); names are never used
CS_FIELD = 'fields/17'                                       # OpenAlex field "Computer Science"
KEEP_TYPES = {'article', 'conference-paper', 'preprint', 'review', 'book-chapter'}
TIERS = [('top10', 1, 10), ('11-50', 11, 50), ('51-100', 51, 100), ('101-200', 101, 200), ('201-300', 201, 300)]
REGIONS = {   # country code -> region (fixed table; the institution country is the OpenAlex one)
    'US': 'North America', 'CA': 'North America',
    'GB': 'Europe', 'DE': 'Europe', 'FR': 'Europe', 'IT': 'Europe', 'NL': 'Europe', 'SE': 'Europe', 'DK': 'Europe', 'CH': 'Europe', 'ES': 'Europe',
    'PT': 'Europe', 'FI': 'Europe', 'AT': 'Europe', 'NO': 'Europe', 'IE': 'Europe', 'BE': 'Europe', 'LU': 'Europe', 'GR': 'Europe',
    'CN': 'East Asia', 'HK': 'East Asia', 'TW': 'East Asia', 'MO': 'East Asia', 'KR': 'East Asia', 'JP': 'East Asia',
    'AU': 'Oceania', 'NZ': 'Oceania',
    'SG': 'South/Southeast Asia', 'MY': 'South/Southeast Asia', 'IN': 'South/Southeast Asia',
    'SA': 'Middle East', 'QA': 'Middle East', 'AE': 'Middle East', 'IL': 'Middle East', 'LB': 'Middle East',
}
LLM_RX = None   # the 12-school LLM-topic regex is imported lazily from study_analyze (never copied)


def cohort_dir():
    return Path(__file__).resolve().parents[2] / 'docs' / 'cohort'


def tier_of(rank_low):
    for name, lo, hi in TIERS:
        if lo <= rank_low <= hi:
            return name
    return None


def load_roster():
    """[dict(idx, site_id, name, country_name, rank_low, rank_high, tier, oa_id, oa_ids (main + related), cc, region, english)] for the 300 cohort rows,
    ordered by cohort rank; idx = position 0..299. cc = OpenAlex institution country of the main id (from the map)."""
    roster = {r['site_id']: r for r in csv.DictReader(open(cohort_dir() / 'gras-2025-cse-roster.tsv'), delimiter='\t')}
    out = []
    for m in csv.DictReader(open(cohort_dir() / 'gras-2025-cse-openalex-map.tsv'), delimiter='\t'):
        r = roster.get(m['sr_slug'])
        if not r or r['in_cohort'] != 'true':
            continue
        rel = [x for x in re.split(r'[;, ]+', m['related_oa_ids'].strip()) if x]
        lo = int(r['rank_low'])
        cc = (m['oa_country'] or '').upper()
        out.append(dict(site_id=m['sr_slug'], name=m['gras_name'], country_name=m['gras_country'], rank_low=lo, rank_high=int(r['rank_high']), tier=tier_of(lo),
                        oa_id=m['oa_id'], oa_ids=[m['oa_id']] + rel, cc=cc, region=REGIONS.get(cc, 'Other'), english=cc in ENGLISH_SPEAKING))
    out.sort(key=lambda d: (d['rank_low'], d['name']))
    for i, d in enumerate(out):
        d['idx'] = i
    return out


def work_dir():
    return Path(os.environ.get('FIELD300_WORK') or SC.STUDY / 'work' / ID)


def snapshot_dir():
    return SC.snapshot_dir(ID)


def results_dir():
    return SC.results_dir(ID)


def short_int(x):
    """Trailing number of an OpenAlex id or URL ('https://openalex.org/W123', 'T10586', 'https://openalex.org/fields/17' -> 123, 10586, 17); None otherwise."""
    m = re.search(r'(\d+)$', x) if isinstance(x, str) else None
    return int(m.group(1)) if m else None


def abstract_of(inv):
    """Plain text from an OpenAlex abstract_inverted_index (word -> positions); '' when absent."""
    if not inv:
        return ''
    n = max(p for ps in inv.values() for p in ps) + 1
    words = [''] * n
    for w, ps in inv.items():
        for p in ps:
            if 0 <= p < n:
                words[p] = w
    return ' '.join(w for w in words if w)
