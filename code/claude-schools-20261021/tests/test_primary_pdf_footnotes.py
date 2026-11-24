"""Explicit complete source reviews, including shared/numeric/symbol markers and comma-form raw names."""
import copy
import gzip
import hashlib
import json
import sqlite3
import zlib

import pytest

import test_build_rules as T
from pihier import build, common, identity, primary_affiliations as A


def fixture():
    names = ['Lovelace, Ada', 'Turing, Alan', 'Person, Outside']
    quotes = ['Ada Lovelace1*', 'Alan Turing1', 'Outside Person2']
    work = T.work('W801', 'Shared Primary Block Research', 2020,
                  [T.au(names[0], 'A1'), T.au(names[1], 'A9', school=False), T.au(names[2], 'A700')],
                  doi='10.1000/shared')
    prefix = work['title']; byline = ' '.join(quotes); region = '1Princeton University\n2University of Vienna'
    contact = '{ada,alan}@princeton.edu'
    text = '\n'.join([prefix, byline, region, contact, 'Abstract', 'Research text.', '*Equal Contribution'])
    page = dict(url='https://proceedings.example/paper.pdf', pdf_sha256='a' * 64)
    r = dict(version=2, layout='footnotes', work=work['id'], doi=work['doi'], source_work_sha256=A.digest(work),
             source_authorships_sha256=A.digest(work['authorships']), pdf_sha256=page['pdf_sha256'], pdf_url=page['url'],
             page1_text_sha256=hashlib.sha256(text.encode()).hexdigest(), byline_names=names,
             reviewed_by='independent-reviewer', reviewed_at='2026-11-08', prefix_quote=prefix, byline_quote=byline,
             affiliation_region_quote=region, contact_quote=contact,
             authors=[dict(index=i, raw_name=names[i], author_id=work['authorships'][i]['author']['id'], pdf_name=n,
                           quote=q, markers=m, affiliation_ids=g, bbox=[10 + i*100, 10, 90 + i*100, 20])
                      for i, (n, q, m, g) in enumerate(zip(['Ada Lovelace', 'Alan Turing', 'Outside Person'], quotes,
                                                          [['1', '*'], ['1'], ['2']], [['p'], ['p'], ['v']]))],
             groups=[dict(id='p', marker='1', text='Princeton University', quote='1Princeton University', bbox=[10, 30, 200, 40]),
                     dict(id='v', marker='2', text='University of Vienna', quote='2University of Vienna', bbox=[10, 50, 200, 60])],
             notes=[dict(marker='*', kind='equal_contribution', quote='*Equal Contribution', bbox=[10, 80, 200, 90])])
    page['author_affiliation_review'] = r
    return work, page, text


def rebind(work, page, text):
    r = page['author_affiliation_review']; r['source_work_sha256'] = A.digest(work)
    r['source_authorships_sha256'] = A.digest(work['authorships']); r['page1_text_sha256'] = hashlib.sha256(text.encode()).hexdigest()


def school(work, author):
    return any('Princeton University' in s for s in author['raw_affiliation_strings'])


def test_shared_affiliation_counted_once_and_only_explicit_comma_name_format_changes():
    w, p, text = fixture(); before = copy.deepcopy((w, p)); result = A.resolve(w, p, zlib.compress(text.encode()))
    assert result['status'] == 'accepted'
    assert A.school_flags(w, result, school) == ['Lovelace, Ada', 'Turing, Alan']
    assert (w, p) == before
    assert [a['author_id'] for a in result['authors']] == [a['author']['id'] for a in w['authorships']]
    assert result['evidence']['version'] == 2


@pytest.mark.parametrize('change', [
    'work', 'doi', 'source', 'authorship_hash', 'pdf_hash', 'pdf_url', 'page_hash', 'order', 'missing_author',
    'author_id', 'index', 'raw_name', 'nickname', 'initial', 'transliteration', 'missing_group', 'duplicate_group',
    'duplicate_marker', 'undefined_marker', 'extra_marker', 'marker_case', 'wrong_group_link', 'default_instead',
    'missing_note', 'wrong_note_marker', 'unproven_note', 'unused_note', 'unused_group', 'missing_bbox',
    'nan_bbox', 'bool_bbox', 'overlap', 'group_quote', 'author_quote', 'partition', 'omitted_contact_affiliation',
    'prefix', 'byline_extra_author', 'reviewer', 'float_version', 'empty_title_key'])
def test_invalid_partial_or_ambiguous_maps_hold_all_flags(change):
    w, p, text = fixture(); r = p['author_affiliation_review']
    if change == 'work': r['work'] = 'other'
    elif change == 'doi': r['doi'] = '10.1000/other'
    elif change == 'source': w['publication_year'] = 2019
    elif change == 'authorship_hash': r['source_authorships_sha256'] = '0' * 64
    elif change == 'pdf_hash': r['pdf_sha256'] = '0' * 64
    elif change == 'pdf_url': r['pdf_url'] += '?changed'
    elif change == 'page_hash': text += 'changed'
    elif change == 'order': r['byline_names'].reverse()
    elif change == 'missing_author': r['authors'].pop()
    elif change == 'author_id': r['authors'][0]['author_id'] = 'different'
    elif change == 'index': r['authors'][0]['index'] = 1
    elif change == 'raw_name': r['authors'][0]['raw_name'] = 'Ada Lovelace'
    elif change == 'nickname': r['authors'][0]['pdf_name'] = 'Addie Lovelace'
    elif change == 'initial': r['authors'][0]['pdf_name'] = 'A. Lovelace'
    elif change == 'transliteration': r['authors'][0]['pdf_name'] = '艾达'
    elif change == 'missing_group': r['groups'].pop()
    elif change == 'duplicate_group': r['groups'][1]['id'] = 'p'
    elif change == 'duplicate_marker': r['groups'][1]['marker'] = '1'
    elif change == 'undefined_marker': r['authors'][0]['markers'] = ['1', '?']
    elif change == 'extra_marker': r['authors'][0]['markers'] = ['1']
    elif change == 'marker_case':
        text = text.replace('1*', 'a*').replace('Turing1', 'Turinga').replace('1Princeton', 'aPrinceton')
        r['authors'][0]['quote'] = 'Ada Lovelacea*'; r['authors'][1]['quote'] = 'Alan Turinga'
        r['byline_quote'] = ' '.join(a['quote'] for a in r['authors']); r['groups'][0].update(marker='A', quote='APrinceton University')
        r['affiliation_region_quote'] = 'APrinceton University\n2University of Vienna'; r['authors'][0]['markers'] = ['A', '*']; r['authors'][1]['markers'] = ['A']; rebind(w, p, text)
    elif change == 'wrong_group_link': r['authors'][2]['affiliation_ids'] = ['p']
    elif change == 'default_instead': r['groups'][0]['marker'] = ''
    elif change == 'missing_note': r['notes'] = []
    elif change == 'wrong_note_marker': r['notes'][0]['marker'] = '?'
    elif change == 'unproven_note': r['notes'][0]['kind'] = 'funding'
    elif change == 'unused_note': r['notes'].append(dict(marker='†', kind='correspondence', quote='†Corresponding author', bbox=[10, 100, 200, 110])); text += '\n†Corresponding author'; rebind(w, p, text)
    elif change == 'unused_group':
        r['groups'].append(dict(id='x', marker='3', text='Other University', quote='3Other University', bbox=[10, 100, 200, 110])); text = text.replace('Abstract', '3Other University\nAbstract'); rebind(w, p, text)
    elif change == 'missing_bbox': r['groups'][0].pop('bbox')
    elif change == 'nan_bbox': r['authors'][0]['bbox'][0] = float('nan')
    elif change == 'bool_bbox': r['authors'][0]['bbox'][0] = True
    elif change == 'overlap': r['authors'][1]['bbox'] = r['authors'][0]['bbox'][:]
    elif change == 'group_quote': r['groups'][0]['text'] = 'University of Vienna'
    elif change == 'author_quote': r['authors'][0]['quote'] = 'Ada Lovelace1**'
    elif change == 'partition': r['affiliation_region_quote'] = '1Princeton University'
    elif change == 'omitted_contact_affiliation':
        text = text.replace('{ada,alan}@princeton.edu', 'Unlisted University\n{ada,alan}@princeton.edu'); r['contact_quote'] = 'Unlisted University\n{ada,alan}@princeton.edu'; rebind(w, p, text)
    elif change == 'prefix': r['prefix_quote'] = 'Different paper'
    elif change == 'byline_extra_author':
        text = text.replace('Outside Person2', 'Outside Person2 Unknown Scholar2'); r['byline_quote'] += ' Unknown Scholar2'; rebind(w, p, text)
    elif change == 'reviewer': r.pop('reviewed_by')
    elif change == 'float_version': r['version'] = 2.0
    else:
        w['title'] = '!!!'; text = text.replace(r['prefix_quote'], '!!!'); r['prefix_quote'] = '!!!'; rebind(w, p, text)
    before = copy.deepcopy(w); result = A.resolve(w, p, text)
    assert result['status'] == 'held', (change, result)
    assert A.school_flags(w, result, school) is None
    assert w == before


def test_default_affiliation_is_not_a_correspondence_or_equal_contribution_marker():
    w, p, text = fixture(); r = p['author_affiliation_review']
    text = text.replace('1*', '*').replace('Turing1', 'Turing').replace('1Princeton', 'Princeton')
    r['groups'][0].update(marker='', quote='Princeton University'); r['authors'][0].update(quote='Ada Lovelace*', markers=['*'])
    r['authors'][1].update(quote='Alan Turing', markers=[]); r['byline_quote'] = ' '.join(a['quote'] for a in r['authors'])
    r['affiliation_region_quote'] = 'Princeton University\n2University of Vienna'; rebind(w, p, text)
    assert A.resolve(w, p, text)['status'] == 'accepted'
    assert A.school_flags(w, A.resolve(w, p, text), school) == ['Lovelace, Ada', 'Turing, Alan']


def test_numeric_ten_is_not_marker_one_and_zero():
    w, p, text = fixture(); r = p['author_affiliation_review']
    text = text.replace('1*', '10*').replace('Turing1', 'Turing10').replace('1Princeton', '10Princeton')
    r['groups'][0].update(marker='10', quote='10Princeton University'); r['authors'][0].update(quote='Ada Lovelace10*', markers=['10', '*'])
    r['authors'][1].update(quote='Alan Turing10', markers=['10']); r['byline_quote'] = ' '.join(a['quote'] for a in r['authors'])
    r['affiliation_region_quote'] = '10Princeton University\n2University of Vienna'; rebind(w, p, text)
    assert A.resolve(w, p, text)['status'] == 'accepted'
    r['authors'][0]['markers'] = ['1', '0', '*']
    assert A.resolve(w, p, text)['status'] == 'held'


def test_inline_comma_format_does_not_join_nicknames_or_borrow_a_nearby_statement():
    w, p, _ = fixture(); names = ['Ada Lovelace', 'Alan Turing', 'Outside Person']; affs = ['Princeton University', 'Princeton University', 'University of Vienna']
    text = '\n'.join(n + ', ' + aff for n, aff in zip(names, affs)) + '\nAbstract\nResearch text.'
    r = p['author_affiliation_review']; r['layout'] = 'inline'; r['blocks'] = [dict(index=i, raw_name=r['byline_names'][i], author_id=w['authorships'][i]['author']['id'], pdf_name=n, block_text=n+', '+aff, affiliations=[aff], bbox=[i*100, 0, i*100+90, 20]) for i, (n, aff) in enumerate(zip(names, affs))]; rebind(w, p, text)
    assert A.resolve(w, p, text)['status'] == 'accepted'
    r['blocks'][2]['affiliations'] = ['Princeton University']
    assert A.resolve(w, p, text)['status'] == 'held'


def native_source(root, review=True, wrong=False, year=2020, typ='article'):
    w, page, text = fixture(); w['publication_year'] = year; w['publication_date'] = str(year)+'-05-01'; w['type'] = typ
    rebind(w, page, text); T.write_school(root, sweep=[w]); r = page['author_affiliation_review']
    if not review: page.pop('author_affiliation_review')
    if wrong: r['source_work_sha256'] = '0' * 64
    db = sqlite3.connect(T.put(root, 'pi-works.sqlite'))
    db.executescript('create table works(id text primary key,body blob);create table pages(work text primary key,arxiv text,url text,status text,pdf_sha256 text,page1 blob,school_named int,quote text,fetched_at text);')
    db.execute('insert into works values(?,?)', (w['id'], zlib.compress(json.dumps(w).encode())))
    quote = {k: v for k, v in page.items() if k not in ['url', 'pdf_sha256']}
    db.execute('insert into pages values(?,?,?,?,?,?,?,?,?)', (w['id'], None, page['url'], 'ok', page['pdf_sha256'], zlib.compress(text.encode()), 1, json.dumps(quote), '2026-11-08'))
    db.commit(); db.close(); return w


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('mode', ['accepted', 'absent', 'wrong', 'old_year', 'nonpaper'])
def test_full_native_shared_review_changes_only_derived_flags_and_candidate_links(tmp_path, monkeypatch, mode):
    w = native_source(tmp_path, review=mode != 'absent', wrong=mode == 'wrong', year=2010 if mode == 'old_year' else 2020, typ='dataset' if mode == 'nonpaper' else 'article')
    before = T.put(tmp_path, 'pi-works.sqlite').read_bytes(); monkeypatch.setattr(identity, 'DUMP_PERSONS', None)
    ctx = T.run_stages(tmp_path, upto='links'); rows = [r for r in ctx.rows if r['oa'] == w['id']]
    if mode in ['old_year', 'nonpaper']:
        assert not rows
        assert not ctx.n['primary_pdf_affiliation_review_accepted']
    else:
        assert len(rows) == 1 and rows[0]['identity'] == 'reviewed_openalex_author_id'
        assert rows[0]['authorship']['raw_affiliations'] == ['Princeton University']
        assert rows[0]['byline_school'] == (['Lovelace, Ada', 'Turing, Alan'] if mode == 'accepted' else ['Lovelace, Ada', 'Person, Outside'])
        links = [l for l in ctx.sp if l['oa'] == w['id']]
        assert len(links) == 1 and links[0]['student'] == 'p_alan'
        assert links[0]['basis'] == ('byline_name_with_school_affiliation' if mode == 'accepted' else 'advisee_name_on_lab_paper_byline')
        assert all(l['status'] == 'candidate' for l in links)
    assert T.put(tmp_path, 'pi-works.sqlite').read_bytes() == before


@pytest.mark.usefixtures('layout')
def test_full_native_package_serializes_shared_evidence_without_admission_or_source_changes(tmp_path, monkeypatch):
    w = native_source(tmp_path)
    before = T.put(tmp_path, 'pi-works.sqlite').read_bytes()
    monkeypatch.setattr(identity, 'DUMP_PERSONS', None)
    monkeypatch.setattr(build, 'HERE', tmp_path)
    monkeypatch.setattr(build, 'Ctx', lambda school, out: common.Ctx(school, here=tmp_path, site=tmp_path, out=out))
    monkeypatch.setattr(build.provenance, 'block', lambda school: {})
    monkeypatch.setenv('PI_HIERARCHY_OUT', str(tmp_path / 'trial'))
    build.build(T.SCHOOL)
    out = tmp_path / 'trial' / T.SCHOOL
    rows = [json.loads(line) for line in gzip.open(out / 'lab_papers.jsonl.gz', 'rt')]
    row = next(r for r in rows if r['oa'] == w['id'])
    assert row['byline_school'] == ['Lovelace, Ada', 'Turing, Alan']
    assert row['identity'] == 'reviewed_openalex_author_id'
    assert row['authorship']['raw_affiliations'] == ['Princeton University']
    assert row['byline_affiliation_review']['version'] == 2
    links = [json.loads(line) for line in gzip.open(out / 'student_papers.jsonl.gz', 'rt')]
    assert any(l['student'] == 'p_alan' and l['status'] == 'candidate' for l in links)
    assert T.put(tmp_path, 'pi-works.sqlite').read_bytes() == before


@pytest.mark.parametrize('first_aff,expected', [
    ('The Hong Kong University of Science and Technology (Guangzhou )', ['Turing, Alan']),
    ('The Hong Kong University of Science and Technology, Hong Kong', ['Lovelace, Ada', 'Turing, Alan']),
])
def test_shared_groups_use_existing_campus_predicate_without_borrowing_maincampus(first_aff, expected):
    from pihier import papers
    w, p, text = fixture(); r = p['author_affiliation_review']
    second_aff = 'The Hong Kong University of Science and Technology, Hong Kong'
    text = text.replace('Ada Lovelace1*', 'Ada Lovelace2*').replace('1Princeton University', '1'+second_aff).replace('2University of Vienna', '2'+first_aff)
    r['authors'][0].update(quote='Ada Lovelace2*', markers=['2', '*'], affiliation_ids=['v'])
    r['groups'][0].update(text=second_aff, quote='1'+second_aff)
    r['groups'][1].update(text=first_aff, quote='2'+first_aff)
    r['byline_quote'] = ' '.join(a['quote'] for a in r['authors'])
    r['affiliation_region_quote'] = '1'+second_aff+'\n2'+first_aff
    rebind(w, p, text)
    result = A.resolve(w, p, text)
    assert result['status'] == 'accepted'
    flags = A.school_flags(w, result, lambda work, a: papers._authorship_school_via(
        work, a, common.INST['hkust'], __import__('re').compile(common.AFF['hkust'], __import__('re').I), school='hkust'))
    # Outside Person shares group2 too; inspect the first two authors only for the campus gate.
    assert [x for x in flags if x != 'Person, Outside'] == expected


def test_a_marker_note_cannot_borrow_a_different_printed_note_symbol():
    w, p, text = fixture(); r = p['author_affiliation_review']
    text = text.replace('Ada Lovelace1*', 'Ada Lovelace1?')
    r['authors'][0].update(quote='Ada Lovelace1?', markers=['1', '?'])
    r['notes'][0]['marker'] = '?'; r['byline_quote'] = ' '.join(a['quote'] for a in r['authors'])
    rebind(w, p, text)
    assert A.resolve(w, p, text)['reason'] == 'unproven_non_affiliation_marker'


def test_explicit_font_decoded_envelope_needs_visual_extraction_attestation_and_contact():
    w, p, text = fixture(); r = p['author_affiliation_review']
    text = text.replace('Ada Lovelace1*', 'Ada Lovelace1B').replace('{ada,alan}@princeton.edu', '[email removed]')
    r['authors'][0].update(quote='Ada Lovelace1B', markers=['1', 'B'])
    r['notes'] = [dict(marker='B', kind='correspondence', quote='[email removed]', bbox=[10, 80, 200, 90],
                       display_symbol='envelope', extraction_note='Rendered envelope is extracted as B; visually reviewed')]
    r['byline_quote'] = ' '.join(a['quote'] for a in r['authors']); r['contact_quote'] = '[email removed]'
    rebind(w, p, text)
    assert A.resolve(w, p, text)['status'] == 'accepted'
    r['notes'][0].pop('extraction_note')
    assert A.resolve(w, p, text)['status'] == 'held'


def test_opaque_unicode_names_and_titles_are_literal_and_do_not_trigger_transliteration():
    w, p, text = fixture(); r = p['author_affiliation_review']
    w['title'] = '中文研究标题'; text = text.replace(r['prefix_quote'], w['title']); r['prefix_quote'] = w['title']
    w['authorships'][0]['raw_author_name'] = '张三'; w['authorships'][0]['author']['display_name'] = '张三'
    r['byline_names'][0] = '张三'; text = text.replace('Ada Lovelace1*', '张三1*')
    r['authors'][0].update(raw_name='张三', pdf_name='张三', quote='张三1*'); r['byline_quote'] = ' '.join(a['quote'] for a in r['authors'])
    rebind(w, p, text)
    assert A.resolve(w, p, text)['status'] == 'accepted'
    r['authors'][0]['pdf_name'] = 'Zhang San'
    assert A.resolve(w, p, text)['status'] == 'held'
