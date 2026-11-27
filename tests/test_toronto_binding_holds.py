"""Prior name-only candidates need corroboration, an owned-source binding, or a hold.

Check the effective reviewed layers used by the builder. A later sourced binding
supersedes its historical hold while retaining the hold's reason for audit.
"""
import copy
import datetime
import json
from pathlib import Path
import re

import pytest

import atlas_paths as P
import census_overrides as CO

pytestmark = pytest.mark.live_school_data   # reads live reviewed files through data()

ROOT = Path(__file__).resolve().parents[1]
OV = ROOT / 'hierarchy/toronto/reviewed/census-overrides-school.json'
BINDINGS = OV.with_name('identity-bindings-school.json')
NAME_ONLY = ['Murat Erdogdu', 'Yashar Ganjali', 'Eitan Grinspun', 'Rahul G. Krishnan', 'Aleksandar Nikolov', 'Ben Rossman', 'Sam Toueg', 'Nandita Vijaykumar',
             'Nathan Wiebe', 'Henry Yuen', 'Niv Dayan', 'Xujie Si', 'Aviad Levis', 'Colin Raffel', 'Varinia Bernales', 'Thomas Ristenpart']


def assert_owned_binding(binding):
    assert binding['reviewed_by'] and binding['why']
    datetime.date.fromisoformat(binding['reviewed_at'])
    selected = set(binding['dblp'])
    assert selected
    candidates = {row['pid']: row for row in binding['candidate_review']}
    for pid in selected:
        matches = candidates[pid]['owned_exact_title_matches']
        assert len({row['dblp_key'] for row in matches}) >= 3
        assert len({row['title'].strip().casefold() for row in matches}) >= 3
        for row in matches:
            assert row['url'].startswith('https://') and row['quote']
            assert re.fullmatch('[0-9a-f]{64}', row['sha256'])


def test_name_only_candidates_are_corroborated_or_held():
    raw = json.loads(OV.read_text())
    bindings = json.loads(BINDINGS.read_text())
    ov = CO.section('toronto', resolve=lambda name, school=None: P.data(name, school, root=ROOT, layout='split'))   # the repo's tracked reviewed files: hierarchy/<s>/reviewed in any placement
    for n in NAME_ONLY:
        e = ov[n]
        if n in bindings:
            assert_owned_binding(bindings[n])
            assert not e['no_identity']
            assert e['superseded_hold'] == raw[n]['why_no_identity']
        elif e.get('no_identity'):
            assert e.get('why_no_identity'), n
            assert not e.get('dblp'), n
        elif e.get('openalex') and 'strict identity pass' in (e.get('why_openalex') or ''):
            continue
        else:
            corr = e['dblp_identity_review']['corroboration']
            assert any(c.get('kind') == 'dblp_candidate_works_with_school_authorship' and c['count'] >= 10 and c['sample_titles'] for c in corr), n


def test_owned_binding_cannot_replace_a_hold_with_only_two_citations():
    binding = copy.deepcopy(json.loads(BINDINGS.read_text())['Ben Rossman'])
    assert_owned_binding(binding)
    for candidate in binding['candidate_review']:
        candidate['owned_exact_title_matches'] = candidate['owned_exact_title_matches'][:2]
    with pytest.raises(AssertionError):
        assert_owned_binding(binding)
