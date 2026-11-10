"""R-PAP-42 (owner-delegated 2026-11-09): ORCID-conflict namesake evidence and exact reciprocal-URL DBLP bindings, on the real ZJU review."""
import json
import re

import atlas_paths as P
import orcid_namesake as o


def test_classify():
    assert o.classify('https://orcid.org/0000-0002-8365-4741', ['0000-0002-8365-4741'], 3) == 'match'
    assert o.classify('0000-0003-0655-3303', ['0000-0002-8365-4741'], 1) == 'mixed'
    assert o.classify('0000-0003-3444-8383', ['0000-0001-9817-4065'], 0) == 'not'
    assert o.classify(None, ['0000-0001-9817-4065'], 5) == 'undecided'


def _overrides():
    path = P.data('census-overrides-school.json', 'zju')
    return json.loads(path.read_text()) if path.exists() else {}


def test_zju_namesake_ids_conflict_with_the_dblp_orcids():
    checked = 0
    for pi, ov in _overrides().items():
        dblp_orcids = set()
        for e in (ov.get('identity_resolution') or {}).get('evidence', []):
            dblp_orcids |= set(re.findall(r'orcid\.org/([0-9X-]{19})', e['quote'])) if e['url'].startswith('https://dblp.org/') else set()
        for kind in ('mixed_openalex', 'not_openalex'):
            ev = ov.get(kind + '_evidence')
            if not ev:
                continue
            assert dblp_orcids, pi
            for item in ev:
                if item['url'].startswith('https://openalex.org/W'):
                    orc = o.bare(item['quote'])
                    assert orc and orc not in dblp_orcids, (pi, item['author_id'])
                    checked += 1
    assert checked in (0, 24)


def test_zju_reciprocal_url_bindings_name_the_profile_url():
    for pi, ov in _overrides().items():
        ir = ov.get('identity_resolution') or {}
        if ir.get('decision') != 'verified_source_exact_reciprocal_profile_url':
            continue
        record = ir['evidence'][0]
        assert record['url'].startswith('https://dblp.org/pid/') and '<url>' in record['quote'] and 'ype="affiliation"' in record['quote'], pi
        assert re.search(r'Zhejiang|ZJU', record['quote'], re.I), pi
        assert ov['dblp'] == [record['url']] and ov['no_identity'] is False
