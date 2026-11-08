"""Full source labels can omit PI initials without weakening observed-name ambiguity or source guards."""
import copy

import pytest

import atlas_ids as A
import test_atlas_ids_coadvising as C
from test_atlas_ids import pi


@pytest.mark.parametrize('canonical,label', [
    ('John D. Kubiatowicz', 'John Kubiatowicz'),
    ('Abigail Z. Jacobs', 'Abigail Jacobs'),
    ('J. Zico Kolter', 'Zico Kolter'),
    ('John D. X. Smith', 'John Smith'),
    ('Kubiatowicz, John D.', 'John Kubiatowicz'),
])
def test_complete_first_family_source_labels_omit_only_given_initials(canonical, label):
    assert A._coadvisers_named(label, {canonical: [canonical]}) == {canonical}


@pytest.mark.parametrize('label,expected', [
    ('John Smith', set()),
    ('John D. Smith', {'pi-d'}),
    ('John X. Smith', {'pi-x'}),
])
def test_observed_sequence_ambiguity_survives_optional_initials(label, expected):
    assert A._coadvisers_named(label, {'pi-d': ['John D. Smith'], 'pi-x': ['John X. Smith']}) == expected


@pytest.mark.parametrize('label', ['J. Kubiatowicz', 'Kubiatowicz', 'D. Kubiatowicz', 'J. D.', 'J.'])
def test_no_surname_only_or_initial_only_full_label_match(label):
    assert A._coadvisers_named(label, {'pi': ['John D. Kubiatowicz']}) == set()


def test_full_middle_words_are_mandatory_and_initial_only_canonical_names_stay_unresolved():
    assert A._coadvisers_named('John Smith', {'pi': ['John Daniel Smith']}) == set()
    assert A._coadvisers_named('John Daniel Smith', {'pi': ['John Daniel Smith']}) == {'pi'}
    assert A._coadvisers_named('J. D. Smith', {'pi': ['J. D. Smith']}) == set()
    assert A._coadvisers_named('John D.', {'pi': ['John Daniel D.']}) == set()


def test_collision_with_an_existing_full_name_and_given_only_behavior_are_unchanged():
    names = {'pi-d': ['John D. Smith'], 'pi-short': ['John Smith']}
    assert A._coadvisers_named('John Smith', names) == set()
    assert A._coadvisers_named('John D. Smith', names) == {'pi-d'}
    assert A._coadvisers_named('John', names) == {'pi-d', 'pi-short'}
    assert A._coadvisers_named('Abigail', {'pi': ['Abigail Z. Jacobs']}) == {'pi'}


def source_fixture(quotes=True):
    # Synthetic student/citations; only the two PI canonical/source label spellings are actual cases.
    return C.fixture(('Dana Student', 'John D. Kubiatowicz', 'Abigail Z. Jacobs',
                      'Dana Student co-advised with Abigail Jacobs',
                      'Dana Student co-supervised with John Kubiatowicz'), quotes=quotes)


def test_actual_adviser_labels_require_reciprocal_cited_student_specific_sources(tmp_path):
    fx = source_fixture(); original = copy.deepcopy(fx)
    result = C.run(tmp_path/'trial', tmp_path/'registry.sqlite', fx)
    assert len(set(C.student_ids(result).values())) == 1
    assert result['report']['coadvised_student_groups'] == 1
    assert len(result['report']['coadvising_evidence'][0]['sources']) == 2
    assert fx == original
    separate = C.run(tmp_path/'no-statements', tmp_path/'other.sqlite', source_fixture(quotes=False))
    assert len(set(C.student_ids(separate).values())) == 2


def test_omitted_initial_ambiguity_does_not_narrow_to_current_membership_group(tmp_path):
    fx = source_fixture(); fx['example']['pis'].append(pi('Abigail X. Jacobs'))
    with pytest.raises(A.CoadvisingIDConflict, match='reciprocal'):
        C.run(tmp_path/'trial', tmp_path/'registry.sqlite', fx)


def test_accepted_label_variants_still_hold_two_issued_ids(tmp_path):
    registry = tmp_path/'registry.sqlite'
    previous = C.run(tmp_path/'before', registry, source_fixture(quotes=False))
    assert len(set(C.student_ids(previous).values())) == 2
    with pytest.raises(A.CoadvisingIDConflict, match='multiple issued'):
        C.run(tmp_path/'after', registry, source_fixture())
