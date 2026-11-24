"""The advising-sentence parser of identity.adviser_anchor_basis (D-0007 rule 1803966d): a source that states the PI as adviser must be read
whatever the title punctuation or the thesis-record layout (Georgia Tech 2026-11-18 replay: 'advised by Prof. X', DSpace 'Advisor(s) A; B', 'Chair, Advisor')."""
import pytest

from pihier import identity as ID

SHA = 'a' * 64


def basis(quote, pi_names, student='Some Student'):
    rel = ID.ADVISER_RELATIONS if isinstance(ID.ADVISER_RELATIONS, (set, frozenset, list, tuple)) else ['researched_advising']
    rtype = sorted(rel)[0] if rel else 'researched_advising'
    member = dict(name=student, aliases=[], relations=[dict(type='researched_advising' if 'researched_advising' in rel else rtype, role='phd', years=[2020, 2024],
                                                            sources=[dict(url='https://example.org/x', sha256=SHA, quote=quote)])])
    return ID.adviser_anchor_basis('PI', member, pi_names, {})


@pytest.mark.parametrize('quote,pi', [
    ('Some Student is a PhD student, advised by Prof. Ümit V. Çatalyürek.', ['Ümit V. Çatalyürek']),
    ('Some Student is supervised by Prof. Bo Zhu at Georgia Tech.', ['Bo Zhu']),
    ('Some Student is advised by C. Karen Liu.', ['C. Karen Liu', 'Karen Liu']),
])
def test_titles_and_initials_do_not_cut_the_adviser_name(quote, pi):
    assert (basis(quote, pi) or {}).get('basis') == 'literal_named_supervision'


def test_a_bare_roster_line_still_gives_no_basis():
    assert basis('PhD Students: Some Student (Ph.D 2021)', ['Bo Zhu']) is None
    assert basis('Some Student is advised by Prof. Someone Else.', ['Bo Zhu']) is None


def test_flattened_dspace_advisor_field_and_committee_chair_line_are_read():
    dspace = 'Title X | Advisor(s) Rozell, Christopher; Clifford, Gari D. | Date 2020 | Department Biomedical Engineering'
    assert (basis(dspace, ['Gari D. Clifford', 'Gari Clifford']) or {}).get('basis') == 'literal_named_supervision'
    chair = 'Committee: Dr. Irfan Essa, IC, Chair, Advisor; Dr. Someone Else, ECE'
    assert (basis(chair, ['Irfan Essa']) or {}).get('basis') == 'literal_named_supervision'
