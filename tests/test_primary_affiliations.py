"""An internship note repeats a source-proven group; it cannot create one."""
import copy

import pytest

from pihier import primary_affiliations as A
from test_primary_pdf_footnotes import fixture, rebind, school


def internship():
    work, page, text = fixture()
    note = page['author_affiliation_review']['notes'][0]
    quote = '*Work done while the author was interning at Princeton University.'
    text = text.replace(note['quote'], quote)
    note.update(kind='work_during_internship', affiliation_id='p', quote=quote)
    rebind(work, page, text)
    return work, page, text


def test_complete_internship_note_preserves_only_the_assigned_header_groups():
    work, page, text = internship()
    before = copy.deepcopy((work, page))
    result = A.resolve(work, page, text)
    assert result['status'] == 'accepted'
    assert A.school_flags(work, result, school) == ['Lovelace, Ada', 'Turing, Alan']
    assert result['evidence']['marker_notes'][0]['affiliation_id'] == 'p'
    assert (work, page) == before


def asterisk_extraction():
    work, page, text = internship()
    review = page['author_affiliation_review']
    text = text.replace('Lovelace1*', 'Lovelace1∗')
    author = review['authors'][0]
    author.update(quote='Ada Lovelace1∗', markers=['1', '∗'])
    review['byline_quote'] = review['byline_quote'].replace('Lovelace1*', 'Lovelace1∗')
    review['notes'][0].update(marker='∗', pdf_marker='*',
                              extraction_note='The source font extracts one asterisk in two literal forms.')
    rebind(work, page, text)
    return work, page, text


def test_explicit_asterisk_extraction_keeps_both_literal_source_quotes():
    work, page, text = asterisk_extraction()
    result = A.resolve(work, page, text)
    assert result['status'] == 'accepted'
    assert result['evidence']['marker_notes'][0]['quote'].startswith('*Work done')
    assert A.school_flags(work, result, school) == ['Lovelace, Ada', 'Turing, Alan']


@pytest.mark.parametrize('change', ['no_note', 'other_symbol', 'ambiguous_note', 'group_marker', 'bad_marker_type'])
def test_asterisk_extraction_cannot_join_distinct_or_unreviewed_markers(change):
    work, page, text = asterisk_extraction()
    review = page['author_affiliation_review']
    note = review['notes'][0]
    if change == 'no_note':
        note.pop('extraction_note')
    elif change == 'other_symbol':
        note['pdf_marker'] = '†'
    elif change == 'ambiguous_note':
        review['notes'].append(dict(marker='*', kind='equal_contribution',
                                    quote='*Equal Contribution', bbox=[10, 100, 200, 110]))
        text += '\n*Equal Contribution'
    elif change == 'group_marker':
        review['groups'][1]['marker'] = '*'
    else:
        note['pdf_marker'] = []
    rebind(work, page, text)
    assert A.resolve(work, page, text)['status'] == 'held'


@pytest.mark.parametrize('change', [
    'missing_group', 'invalid_group_type', 'unknown_group', 'other_group', 'new_institution',
    'additional_institution', 'wrong_author_group', 'multiple_authors',
    'missing_note', 'changed_quote', 'general_work_note', 'internship_not_completed',
])
def test_internship_note_never_supplies_or_hides_an_affiliation(change):
    work, page, text = internship()
    review = page['author_affiliation_review']
    note = review['notes'][0]
    old_quote = note['quote']
    if change == 'missing_group':
        note.pop('affiliation_id')
    elif change == 'invalid_group_type':
        note['affiliation_id'] = []
    elif change == 'unknown_group':
        note['affiliation_id'] = 'unknown'
    elif change == 'other_group':
        note['affiliation_id'] = 'v'
    elif change == 'new_institution':
        note['quote'] = old_quote.replace('Princeton University', 'Unlisted University')
    elif change == 'additional_institution':
        note['quote'] = old_quote.replace('Princeton University', 'Princeton University and Unlisted University')
    elif change == 'wrong_author_group':
        note.update(affiliation_id='v', quote=old_quote.replace('Princeton University', 'University of Vienna'))
    elif change == 'multiple_authors':
        author = review['authors'][1]
        text = text.replace(author['quote'], author['quote'] + '*')
        review['byline_quote'] = review['byline_quote'].replace(author['quote'], author['quote'] + '*')
        author['quote'] += '*'
        author['markers'].append('*')
    elif change == 'missing_note':
        review['notes'] = []
    elif change == 'changed_quote':
        note['quote'] = old_quote.replace('Work done', 'Research conducted')
        # Deliberately do not update the actual page text.
    elif change == 'general_work_note':
        note['quote'] = '*Work supported by Princeton University.'
    else:
        note['quote'] = '*The author will intern at Princeton University.'
    if change != 'changed_quote':
        text = text.replace(old_quote, note['quote'])
    rebind(work, page, text)
    before = copy.deepcopy(work)
    result = A.resolve(work, page, text)
    assert result['status'] == 'held', (change, result)
    assert A.school_flags(work, result, school) is None
    assert work == before
