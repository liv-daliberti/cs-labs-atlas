"""Adviser basis quotes stop at the next profile section before extracting names."""
import pytest

from pihier.students import basis_advisees


def test_stanford_original_publications_boundary():
    # Greg Zaharchuk, https://profiles.stanford.edu/greg-zaharchuk, captured 2026-11-09.
    # Original body SHA-256: a9a4a6b5acb5e9bb48f9573cf299b4a9f95efb185d591d71b8e618cd2879100d.
    # This is the exact reviewed pi_basis quote; the HTML links only "Ashwin Kumar" as the advisee.
    quote = ('Doctoral Dissertation Co-Advisor (AC) Ashwin Kumar All Publications '
             'Evaluation of Image-Level Harmonization Me')
    assert basis_advisees(quote) == [('Ashwin Kumar', None)]


@pytest.mark.parametrize('heading', ['All Publications', 'Selected Publications', 'Publications'])
def test_publications_heading_preserves_comma_separated_advisees(heading):
    quote = f'Doctoral Dissertation Advisor (AC) Jane Doe, John Smith {heading} A Paper Title'
    assert basis_advisees(quote) == [('Jane Doe', None), ('John Smith', None)]


@pytest.mark.parametrize('quote', [
    'Doctoral Dissertation Reader (AC) Jane Doe All Publications A Paper Title',
    'Doctoral (Program) Jane Doe All Publications A Paper Title',
])
def test_publications_boundary_does_not_admit_weak_advising(quote):
    assert basis_advisees(quote) == []
