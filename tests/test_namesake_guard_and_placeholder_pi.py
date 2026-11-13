"""R-PAP-35 (the middle-name guard on name-only identities; Michigan's M. E. J. Newman vs Mark W Newman) and R-PAP-34 (a placeholder PI name)."""
import json
from pathlib import Path

import pytest

from pihier import identity, names, papers

HIER = Path(__file__).resolve().parents[1] / 'hierarchy'


def test_R_PAP_45_anchored_orcid_conflict_with_unrecognized_given_name():
    pi = dict(pi='Gang Wang', names=['Gang Wang'], orcid=['0000-0002-8910-8979'])
    author = dict(raw_author_name='G. Alan Wang', author=dict(orcid='https://orcid.org/0000-0002-5026-881X'))
    assert papers.anchored_orcid_given_name_conflict(pi, author, 'anchored_author_id')
    assert not papers.anchored_orcid_given_name_conflict(pi, author, 'dblp_person_page_doi')
    assert not papers.anchored_orcid_given_name_conflict(pi, dict(author, raw_author_name='Gang Wang'), 'anchored_author_id')
    assert not papers.anchored_orcid_given_name_conflict(pi, dict(author, author=dict(orcid='https://orcid.org/0000-0002-8910-8979')), 'anchored_author_id')
    alias = dict(pi='M. Frans Kaashoek', names=['M. Frans Kaashoek'], orcid=['0000-0000-0000-0001'])
    assert not papers.anchored_orcid_given_name_conflict(alias, dict(raw_author_name='M. Frans Kaashoek', author=dict(orcid='0000-0000-0000-0002')), 'anchored_author_id')


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


def test_R_PAP_35_census_dblp_id_of_the_namesake_is_dropped():
    import collections
    pis = [dict(pi='Mark W Newman', names=['Mark W Newman', 'Mark W. Newman', 'Mark Newman'], orcid=[],
                dblp=['https://dblp.org/pid/n/MEJNewman', 'https://dblp.org/pid/03/6629'])]
    dump = dict(persons={'https://dblp.org/pid/n/MEJNewman': dict(names=['Mark E. J. Newman', 'M. E. J. Newman'], pubs=[], orcid=[]),
                         'https://dblp.org/pid/03/6629': dict(names=['Mark W. Newman', 'Mark Wah Newman'], pubs=[], orcid=[])}, by_name={})
    n = collections.Counter()
    identity.apply_dump(pis, dump, collections.defaultdict(set), collections.defaultdict(dict), n)
    assert pis[0]['dblp'] == ['https://dblp.org/pid/03/6629'] and pis[0]['dblpDropped'] == ['https://dblp.org/pid/n/MEJNewman']


def test_R_PAP_35_mark_w_newman_override_names_his_page():
    ov = json.loads((HIER / 'reviewed/census-overrides.json').read_text())['michigan']['Mark W Newman']
    assert ov['dblp'] == ['https://dblp.org/pid/03/6629'] and ov['why_dblp']


def test_R_PAP_34_files_keyed_by_the_census_name_reach_the_renamed_pi():
    from pihier import students
    assert students.renamed_pis([dict(pi='Yang Zhang', censusName='Y Z'), dict(pi='Mark W Newman')]) == {'Y Z': 'Yang Zhang'}
