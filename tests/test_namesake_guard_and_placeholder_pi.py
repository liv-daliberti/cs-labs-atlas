"""R-PAP-35 (the middle-name guard on name-only identities; Michigan's M. E. J. Newman vs Mark W Newman) and R-PAP-34 (a placeholder PI name)."""
import json
from pathlib import Path

import pytest

from pihier import identity, names

HIER = Path(__file__).resolve().parents[1] / 'hierarchy'


def test_R_PAP_35_middle_initials():
    assert names.middle_initials('M. E. J. Newman') == {'e', 'j'} and names.middle_initials('M. E. J. Newman') == {'e', 'j'}
    assert names.middle_initials('Mark W Newman') == {'w'} and names.middle_initials('Mark Newman') == set()


@pytest.mark.parametrize('pi_names,raw,conflict', [
    (['Mark W Newman', 'Mark W. Newman', 'Mark Newman'], 'M. E. J. Newman', True),    # the real failing row
    (['Mark W Newman', 'Mark Newman'], 'Mark W. Newman', False),
    (['Mark W Newman', 'Mark Newman'], 'Mark Newman', False),                                    # no middle name on the byline: nothing contradicts
    (['Mark Newman'], 'M. E. J. Newman', False),                                                 # the PI writes no middle name
    (['Jean-Philippe Thiran'], 'J.-P. Thiran', False), (['Jean-Philippe Thiran'], 'Jean Philippe Thiran', False),
    (['Xiang Lisa Li'], 'Xiang L. Li', False), (['Xiang Lisa Li'], 'Xiang B. Li', True)])
def test_R_PAP_35_middle_conflict(pi_names, raw, conflict):
    assert names.middle_conflict(pi_names, raw) is conflict


def test_R_PAP_35_only_name_only_identities():
    assert 'dblp_person_page_title' in identity.NAME_ONLY_IDENTITY and 'pi_orcid' not in identity.NAME_ONLY_IDENTITY
    assert 'reviewed_openalex_author_id' not in identity.NAME_ONLY_IDENTITY and 'advisee_coauthor' not in identity.NAME_ONLY_IDENTITY


@pytest.mark.parametrize('name,flag', [('Y Z', True), ('X Y', True), ('', True), ('Weinan E', False), ('H.V. Jagadish', False), ('R. Ravi', False),
                                       ('E.J. Chichilnisky', False), ('Arvind', False)])
def test_R_PAP_34_placeholder_names(name, flag):
    assert names.placeholder_name(name) is flag


def test_R_PAP_34_michigan_y_z_is_named_from_evidence():
    ov = json.loads((HIER / 'reviewed/census-overrides.json').read_text())['michigan']['Y Z']
    assert ov['display_name'] == 'Yang Zhang' and 'https://openalex.org/A5113215889' in ov['openalex']
    assert ov['why_display_name'] and all(e.get('sha256') for e in ov['openalex_evidence'])
