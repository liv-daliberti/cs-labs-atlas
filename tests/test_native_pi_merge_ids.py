from collections import Counter
from types import SimpleNamespace

import pytest

from pihier.census import pi_records


def context(person_ids=None):
    rows = [dict(name=name, aliases=[], is_pi=True, collection_person_id=pid,
                 dblp=[], orcid=[], sources=[], lab_units=[], departments=['CS'])
            for name, pid in [('Buster Dunsmore', 'buster'), ('H. E. Dunsmore', 'he')]]
    review = dict(canonical='Buster Dunsmore', aliases=['H. E. Dunsmore'],
                  reviewed_by='independent reviewer', why='Institutional name bridge',
                  evidence=[dict(url='https://example.edu/name', sha256='a' * 64,
                                 quote='H.E. (Buster) Dunsmore')])
    if person_ids is not None:
        review['person_ids'] = person_ids
    return SimpleNamespace(census=rows, ov={}, yearly={}, periods=[], units={},
                           Pid={pid: dict(id=pid, name=name)
                                for name, pid in [('Buster Dunsmore', 'buster'),
                                                  ('H. E. Dunsmore', 'he'), ('Other Person', 'other')]},
                           n=Counter(), native_pi_merges=[review])


def test_declared_duplicate_ids_remain_on_the_single_canonical_pi():
    ctx = context(['buster', 'he'])
    pi_records(ctx)
    assert len(ctx.pis) == 1
    assert ctx.pis[0]['personIds'] == ['buster', 'he']
    assert ctx.pis[0]['mergedCensusRows'] == ['H. E. Dunsmore']


def test_merges_without_a_declared_id_list_keep_existing_behavior():
    ctx = context()
    pi_records(ctx)
    assert ctx.pis[0]['personIds'] == ['buster']


@pytest.mark.parametrize('ids', [['buster', 'other'], ['buster'], ['buster', 'buster'], 'buster'])
def test_declared_merge_ids_cannot_omit_or_invent_a_person(ids):
    with pytest.raises(ValueError, match='exactly match'):
        pi_records(context(ids))


def test_missing_source_person_fails_instead_of_silently_losing_the_alias_id():
    ctx = context(['buster', 'he'])
    del ctx.Pid['he']
    with pytest.raises(ValueError, match='existing census people'):
        pi_records(ctx)
