"""The cohort roster agrees with the school charters: every charter school is in the cohort, with the charter's OpenAlex id."""
import csv
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COHORT = ROOT / 'docs/cohort'


def roster():
    return list(csv.DictReader(open(COHORT / 'gras-2025-cse-roster.tsv'), delimiter='\t'))


def test_cohort_counts_and_ranks():
    rows = roster()
    ins = [r for r in rows if r['in_cohort'] == 'true']
    assert len(ins) == 300 and len(rows) - len(ins) == 107
    assert len({r['site_id'] for r in rows}) == len(rows)
    for r in ins:
        assert re.fullmatch(r'\d+|\d+-\d+', r['cohort_rank']) and re.fullmatch(r'I\d+', r['openalex_id']), r
    assert not any('score' in k for k in rows[0])


def test_every_charter_school_is_in_the_cohort():
    rows = {r['openalex_id']: r for r in roster() if r['in_cohort'] == 'true'}
    for charter in sorted((ROOT / 'schools').glob('*.toml')):
        if charter.name == 'TEMPLATE.toml':
            continue
        t = tomllib.loads(charter.read_text())
        oa = t['ids']['openalex'][0] if 'ids' in t else t['openalex'][0]
        assert oa in rows, (charter.name, 'is not in the GRAS cohort')


def test_map_and_roster_agree():
    m = {r['sr_slug']: r for r in csv.DictReader(open(COHORT / 'gras-2025-cse-openalex-map.tsv'), delimiter='\t')}
    for r in roster():
        if r['in_cohort'] == 'true' and r['site_id'] in m:
            assert m[r['site_id']]['oa_id'] == r['openalex_id'], r['site_id']
