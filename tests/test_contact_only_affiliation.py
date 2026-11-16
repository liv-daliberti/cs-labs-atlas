"""A retained institutional email cannot override a named outside affiliation."""
import copy

import pytest
import school_config as S
from pihier import papers

PRIMARY = 'https://openalex.org/I200769079'
FOREIGN = 'https://openalex.org/I47720641'


def via(raw, own=False):
    author = dict(raw_author_name='Wei Wang', institutions=[dict(
        id=PRIMARY if own else FOREIGN, display_name='HKUST' if own else 'Huazhong University of Science and Technology',
        lineage=[PRIMARY if own else FOREIGN])], raw_affiliation_strings=raw)
    before = copy.deepcopy(author)
    result = papers._authorship_school_via(dict(authorships=[author]), author, PRIMARY, S.aff_rx('hkust'), school='hkust')
    assert author == before
    return result


@pytest.mark.parametrize('raw', [
    ['School of Computer Science, Huazhong University of Science and Technology (e-mail: gswwang@connect.ust.hk)'],
    ['Huazhong University of Science and Technology', 'gswwang@connect.ust.hk'],
    ['Microsoft Research, contact person@cse.hkust.edu.hk'],
])
def test_R_PAP_47_contact_address_does_not_override_explicit_outside_institution(raw):
    assert via(raw) == []


def test_full_school_name_still_supports_a_dual_affiliation():
    assert via(['Huazhong University of Science and Technology; Hong Kong University of Science and Technology; gswwang@connect.ust.hk'])


def test_an_independent_structured_school_affiliation_is_preserved():
    assert via(['Huazhong University of Science and Technology; gswwang@connect.ust.hk'], own=True) == ['HKUST']


def test_contact_only_without_an_outside_institution_retains_the_existing_rule():
    assert via(['Department of Computer Science, gswwang@connect.ust.hk'])
