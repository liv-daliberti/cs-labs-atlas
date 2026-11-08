"""Complete source-bound author blocks correct flags only; wrong/partial evidence retains existing behavior."""
import copy
import hashlib
import zlib

import pytest

from pihier import primary_affiliations as P

NAMES = ['Lillian Sun', 'Martin Pawelczyk', 'Zhenting Qi', 'Aounon Kumar', 'Himabindu Lakkaraju']
AFFILIATIONS = [['Harvard University Cambridge, MA, USA'], ['University of Vienna Faculty of Computer Science'],
                ['Harvard University Cambridge, MA, USA'], ['Harvard University Cambridge, MA, USA'],
                ['Harvard University Cambridge, MA, USA']]
TEXT = '''Generalizing Trust: Weak-to-Strong Trustworthiness in Language Models
Lillian Sun*                         Martin Pawelczyk*
Harvard University                  University of Vienna
Cambridge, MA, USA                  Faculty of Computer Science
Zhenting Qi          Aounon Kumar            Himabindu Lakkaraju
Harvard University   Harvard University      Harvard University
Cambridge, MA, USA   Cambridge, MA, USA      Cambridge, MA, USA
Abstract
This is the research text.
'''


def fixture():
    work = dict(id='https://openalex.org/W7166886059', doi='https://doi.org/10.18653/v1/2026.acl-long.2163',
                title='Generalizing Trust: Weak-to-Strong Trustworthiness in Language Models',
                publication_year=2026, type='conference-paper', authorships=[])
    # Actual positional-error shape: target Hima/Qi slots empty; Harvard incorrectly appears on Martin's slot.
    for i, name in enumerate(NAMES):
        work['authorships'].append(dict(author=dict(id=f'https://openalex.org/A{i}', display_name=name), raw_author_name=name,
                                       institutions=[dict(display_name='Harvard University')] if i in (0, 1, 3) else [],
                                       raw_affiliation_strings=['Harvard University'] if i in (0, 1, 3) else []))
    boxes = [[10, 10, 100, 50], [110, 10, 220, 50], [10, 60, 90, 100], [100, 60, 180, 100], [190, 60, 290, 100]]
    blocks = [dict(index=i, raw_name=n, author_id=f'https://openalex.org/A{i}', affiliations=aff,
                   block_text='\n'.join([n] + aff), bbox=box) for i, (n, aff, box) in enumerate(zip(NAMES, AFFILIATIONS, boxes))]
    page = dict(url='https://aclanthology.org/2026.acl-long.2163.pdf', pdf_sha256='9' * 64, how='near',
                quotes=['Himabindu Lakkaraju Harvard University'])
    page['author_affiliation_review'] = dict(version=1, work=work['id'], doi='10.18653/v1/2026.acl-long.2163',
        source_work_sha256=P.digest(work), source_authorships_sha256=P.digest(work['authorships']),
        pdf_sha256=page['pdf_sha256'], pdf_url=page['url'], page1_text_sha256=hashlib.sha256(TEXT.encode()).hexdigest(),
        byline_names=NAMES[:], blocks=blocks, reviewed_by='independent-reviewer', reviewed_at='2026-11-08')
    return work, page, TEXT


def school(school_name):
    return lambda work, a: any(school_name in s for s in a['raw_affiliation_strings'])


def test_actual_five_author_shape_corrects_all_flags_without_changing_raw_source_or_admission():
    work, page, text = fixture(); before = copy.deepcopy((work, page)); result = P.resolve(work, page, zlib.compress(text.encode()))
    assert result['status'] == 'accepted'
    assert P.school_flags(work, result, school('Harvard University')) == [NAMES[i] for i in (0, 2, 3, 4)]
    assert P.school_flags(work, result, school('University of Vienna')) == [NAMES[1]]
    assert (work, page) == before
    assert work['authorships'][-1]['institutions'] == []  # normal PI R10 source remains unchanged
    assert result['evidence']['pdf_sha256'] == page['pdf_sha256']
    assert [a['author_id'] for a in result['authors']] == [a['author']['id'] for a in work['authorships']]


@pytest.mark.parametrize('change', ['work_id', 'doi', 'work_hash', 'authorship_hash', 'PDF_hash', 'PDF_url', 'page1_hash',
    'byline_order', 'byline_cardinality', 'missing_block', 'wrong_block_name', 'wrong_author_id', 'wrong_index',
    'empty_affiliations', 'empty_block', 'missing_named_block', 'institution_not_in_block', 'not_in_header',
    'missing_bbox', 'negative_bbox', 'nan_bbox', 'overlap', 'missing_reviewer', 'invalid_version', 'block_words'])
def test_invalid_or_partial_review_holds_and_supplies_no_replacement_flags(change):
    work, page, text = fixture(); r = page['author_affiliation_review']; baseline = [a['raw_author_name'] for a in work['authorships'] if school('Harvard University')(work, a)]
    if change == 'work_id': r['work'] = 'https://openalex.org/W1'
    elif change == 'doi': r['doi'] = '10.18653/v1/2026.acl-long.1'
    elif change == 'work_hash': work['publication_year'] = 2025
    elif change == 'authorship_hash': r['source_authorships_sha256'] = '0' * 64
    elif change == 'PDF_hash': r['pdf_sha256'] = '0' * 64
    elif change == 'PDF_url': r['pdf_url'] = 'https://other.example/paper.pdf'
    elif change == 'page1_hash': text += 'changed'
    elif change == 'byline_order': r['byline_names'].reverse()
    elif change == 'byline_cardinality': r['byline_names'].pop()
    elif change == 'missing_block': r['blocks'].pop()
    elif change == 'wrong_block_name': r['blocks'][1]['raw_name'] = NAMES[0]
    elif change == 'wrong_author_id': r['blocks'][1]['author_id'] = 'https://openalex.org/A0'
    elif change == 'wrong_index': r['blocks'][1]['index'] = 0
    elif change == 'empty_affiliations': r['blocks'][1]['affiliations'] = []
    elif change == 'empty_block': r['blocks'][1]['block_text'] = ''
    elif change == 'missing_named_block': r['blocks'][1]['block_text'] = 'University of Vienna Faculty of Computer Science'
    elif change == 'institution_not_in_block': r['blocks'][1]['affiliations'] = ['Harvard University']
    elif change == 'not_in_header':
        text = text.replace('Himabindu Lakkaraju', '') + 'Himabindu Lakkaraju'
        r['page1_text_sha256'] = hashlib.sha256(text.encode()).hexdigest()
    elif change == 'missing_bbox': r['blocks'][1].pop('bbox')
    elif change == 'negative_bbox': r['blocks'][1]['bbox'][0] = -1
    elif change == 'nan_bbox': r['blocks'][1]['bbox'][0] = float('nan')
    elif change == 'overlap': r['blocks'][1]['bbox'] = r['blocks'][0]['bbox'][:]
    elif change == 'missing_reviewer': r.pop('reviewed_by')
    elif change == 'invalid_version': r['version'] = 2
    else: r['blocks'][1]['block_text'] += ' Unstated Institution'
    before = copy.deepcopy(work); result = P.resolve(work, page, text)
    assert result['status'] == 'held', change
    assert P.school_flags(work, result, school('Harvard University')) is None
    assert [a['raw_author_name'] for a in work['authorships'] if school('Harvard University')(work, a)] == baseline
    assert work == before


def test_ambiguous_punctuation_or_case_variant_raw_names_hold():
    work, page, text = fixture(); work['authorships'][1]['raw_author_name'] = 'LILLIAN. SUN'
    r = page['author_affiliation_review']; r['source_work_sha256'] = P.digest(work); r['source_authorships_sha256'] = P.digest(work['authorships'])
    assert P.resolve(work, page, text)['reason'] == 'ambiguous_raw_byline'


def test_borrowing_one_harvard_block_for_another_author_exceeds_actual_header_words():
    work, page, text = fixture(); block = page['author_affiliation_review']['blocks'][1]
    block['affiliations'] = ['Harvard University']; block['block_text'] = NAMES[1] + '\nHarvard University'
    assert P.resolve(work, page, text)['status'] == 'held'


def test_missing_review_is_a_noop_and_unreadable_page1_is_held():
    work, page, text = fixture(); no = copy.deepcopy(page); no.pop('author_affiliation_review')
    assert P.resolve(work, no, text) == {'status': 'not_requested'}
    assert P.resolve(work, page, b'not a compressed page')['status'] == 'held'
    assert P.school_flags(work, {'status': 'not_requested'}, school('Harvard University')) is None


def test_no_DOI_is_bound_to_exact_original_work_instead_of_guessed():
    work, page, text = fixture(); work['doi'] = None; r = page['author_affiliation_review']; r['doi'] = None; r['source_work_sha256'] = P.digest(work)
    assert P.resolve(work, page, text)['status'] == 'accepted'


def test_unicode_literal_names_are_preserved_without_romanization_or_global_identity_matching():
    work, page, _ = fixture(); names = ['李娜', '王強']; work['authorships'] = [dict(raw_author_name=n, author=dict(id=None)) for n in names]
    text = '李娜\n香港科技大學（廣州）\n王強\n香港科技大學\nAbstract'; r = page['author_affiliation_review']; r.update(source_work_sha256=P.digest(work), source_authorships_sha256=P.digest(work['authorships']), byline_names=names,
        page1_text_sha256=hashlib.sha256(text.encode()).hexdigest(), blocks=[dict(index=i, raw_name=n, author_id=None, affiliations=[aff], block_text=n+'\n'+aff, bbox=[i*100, 0, i*100+90, 40]) for i,(n,aff) in enumerate(zip(names,['香港科技大學（廣州）','香港科技大學']))])
    result = P.resolve(work, page, text); assert result['status'] == 'accepted'
    ordinary_scope_predicate = lambda w,a: '香港科技大學' in ' '.join(a['raw_affiliation_strings']) and '廣州' not in ' '.join(a['raw_affiliation_strings'])
    assert P.school_flags(work, result, ordinary_scope_predicate) == ['王強']
