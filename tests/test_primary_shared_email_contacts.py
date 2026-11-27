"""Printed spacing in shared email lists must not hide affiliation text."""
import pytest

from pihier import primary_affiliations as A
from test_primary_pdf_footnotes import fixture, rebind


@pytest.mark.parametrize('contact', ['{ada, alan}@princeton.edu', '{ ada, alan }@princeton.edu'])
def test_complete_primary_mapping_accepts_shared_email_spacing(contact):
    work, page, text = fixture()
    text = text.replace('{ada,alan}@princeton.edu', contact)
    page['author_affiliation_review']['contact_quote'] = contact
    rebind(work, page, text)
    assert A.resolve(work, page, text)['status'] == 'accepted'


@pytest.mark.parametrize('contact', [
    '{ada, alan}@princeton.edu University of Vienna',
    '{ada, University of Vienna}@princeton.edu',
    'ada, alan princeton.edu',
])
def test_contact_tail_cannot_hide_an_unmapped_institution(contact):
    work, page, text = fixture()
    text = text.replace('{ada,alan}@princeton.edu', contact)
    page['author_affiliation_review']['contact_quote'] = contact
    rebind(work, page, text)
    assert A.resolve(work, page, text)['status'] == 'held'
