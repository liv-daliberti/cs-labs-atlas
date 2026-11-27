"""Complete explicit CORE links correct source flags without lending identities."""
import collections
import copy
import hashlib
import json
import re
import sqlite3
import types
import xml.etree.ElementTree as ET
import zlib

import pytest

from pihier import common, papers, primary_affiliations as A, primary_xml_affiliations as X


def document(people, title='Explicit Author Research', year=2024, doi='10.9/xml', sid='123'):
    root = ET.Element('responseWrapper')
    record = ET.SubElement(ET.SubElement(root, 'resultList'), 'result')
    for key, value in [('source', 'MED'), ('id', sid), ('doi', doi), ('title', title+'.'), ('pubYear', str(year))]:
        ET.SubElement(record, key).text = value
    authors = ET.SubElement(record, 'authorList')
    for given, family, affiliations in people:
        author = ET.SubElement(authors, 'author')
        ET.SubElement(author, 'firstName').text = given
        ET.SubElement(author, 'lastName').text = family
        detail = ET.SubElement(author, 'authorAffiliationDetailsList')
        for affiliation in affiliations:
            ET.SubElement(ET.SubElement(detail, 'authorAffiliation'), 'affiliation').text = affiliation
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def row_for(work, body, mapping, duplicates, school='ucsd'):
    metadata = dict(source_format=X.FORMAT,
        source_url='https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID%3A123%20AND%20SRC%3AMED&resultType=core&format=xml',
        source_id='123', raw_to_source_author=mapping, duplicate_raw_observations=duplicates)
    approval = dict(version=1, decision='reviewed', purpose=A.AUTHOR_REVIEW_PURPOSE, school=school,
        review_id='review-xml', work=work['id'], reviewed_by='independent-fixture-reviewer', reviewed_at='2026-11-27',
        source_packet_sha256='a'*64, source_replay_sha256='b'*64, source_work_sha256=A.digest(work),
        source_authorships_sha256=A.digest(work['authorships']), source_xml_sha256=hashlib.sha256(body).hexdigest(),
        metadata_sha256=A.digest(metadata))
    return dict(review_id='review-xml', work=work['id'], approval=json.dumps(approval), metadata=json.dumps(metadata),
                document=zlib.compress(body), source_format=X.FORMAT)


def fixture():
    people = [('Sang-Hyeok', 'Cho', ['KAIST, Republic of Korea']), ('Suhyung', 'Cho', ['KAIST, Republic of Korea']),
              ('Donghui', 'Choe', ['University of California San Diego']),
              ('Bernhard', 'Palsson', ['University of California San Diego'])]
    names = ['Sang-Hyeok Cho', 'Sang-Hyeok Cho', 'Suhyung Cho', 'Suhyung Cho', 'Donghui Choe', 'Bernhard Palsson']
    work = dict(id='https://openalex.org/W123', title='Explicit Author Research', publication_year=2024, doi='10.9/xml', authorships=[])
    for i, name in enumerate(names):
        work['authorships'].append(dict(raw_author_name=name,
            author=dict(id='https://openalex.org/A'+str(i), display_name='Suhyung Cho' if i == 1 else name),
            institutions=[dict(id='https://openalex.org/'+common.INST['ucsd'], display_name='University of California San Diego')],
            raw_affiliation_strings=['University of California San Diego', 'KAIST']))
    body = document(people)
    return work, row_for(work, body, [0, 0, 1, 1, 2, 3], [[0, 1], [2, 3]]), body


def flags(work, result):
    return A.school_flags(work, result, lambda w, a: any('California San Diego' in x for x in a['raw_affiliation_strings']))


def test_explicit_full_names_and_duplicate_observations_correct_polluted_display_names():
    work, row, _ = fixture()
    before = copy.deepcopy((work, row))
    result = A.resolve_author_review(work, 'ucsd', [row])
    assert result['status'] == 'accepted'
    assert flags(work, result) == ['Donghui Choe', 'Bernhard Palsson']
    assert [a['source_author_index'] for a in result['authors']] == [0, 0, 1, 1, 2, 3]
    assert [a['author_id'] for a in result['authors']] == [a['author']['id'] for a in work['authorships']]
    assert result['evidence']['source_format'] == X.FORMAT
    assert 'pdf_sha256' not in result['evidence'] and (work, row) == before


@pytest.mark.parametrize('change', ['raw_display_only', 'initials', 'source_name_ambiguity', 'missing_affiliation',
    'undeclared_duplicate', 'partial_mapping', 'boolean_index', 'wrong_source_index', 'wrong_doi', 'wrong_title',
    'wrong_year', 'wrong_record', 'wrong_work', 'changed_document', 'changed_metadata', 'wrong_school',
    'wrong_purpose', 'missing_reviewer', 'invalid_date', 'unapproved', 'doctype', 'compressed_trailing_bytes'])
def test_incomplete_conflicting_or_changed_sources_hold_without_replacement_flags(change):
    work, row, body = fixture()
    metadata, approval = json.loads(row['metadata']), json.loads(row['approval'])
    if change == 'raw_display_only': work['authorships'][0]['raw_author_name'] = ''; approval['source_work_sha256'] = A.digest(work); approval['source_authorships_sha256'] = A.digest(work['authorships'])
    elif change == 'initials': body = body.replace(b'<firstName>Sang-Hyeok</firstName>', b'<firstName>S H</firstName>')
    elif change == 'source_name_ambiguity': body = body.replace(b'<firstName>Suhyung</firstName>', b'<firstName>Sang-Hyeok</firstName>')
    elif change == 'missing_affiliation': body = body.replace(b'KAIST, Republic of Korea', b'')
    elif change == 'undeclared_duplicate': metadata['duplicate_raw_observations'] = []
    elif change == 'partial_mapping': metadata['raw_to_source_author'].pop()
    elif change == 'boolean_index': metadata['raw_to_source_author'][0] = False
    elif change == 'wrong_source_index': metadata['raw_to_source_author'][:4] = [1, 1, 0, 0]
    elif change == 'wrong_doi': body = body.replace(b'10.9/xml', b'10.9/other')
    elif change == 'wrong_title': body = body.replace(b'Explicit Author Research', b'A Different Research Paper')
    elif change == 'wrong_year': body = body.replace(b'<pubYear>2024</pubYear>', b'<pubYear>2023</pubYear>')
    elif change == 'wrong_record': metadata['source_id'] = '999'
    elif change == 'wrong_work': approval['work'] = 'https://openalex.org/W2'
    elif change == 'wrong_school': approval['school'] = 'princeton'
    elif change == 'wrong_purpose': approval['purpose'] = 'ordinary_admission'
    elif change == 'missing_reviewer': approval['reviewed_by'] = ''
    elif change == 'invalid_date': approval['reviewed_at'] = '2026-02-31'
    elif change == 'unapproved': approval['decision'] = 'proposed'
    elif change == 'doctype': body = b'<!DOCTYPE responseWrapper [<!ENTITY external SYSTEM "file:///etc/passwd">]>'+body
    if change != 'changed_document': approval['source_xml_sha256'] = hashlib.sha256(body).hexdigest()
    else: body += b'\n'
    if change != 'changed_metadata': approval['metadata_sha256'] = A.digest(metadata)
    else: metadata['source_id'] = '111'
    row.update(approval=json.dumps(approval), metadata=json.dumps(metadata), document=zlib.compress(body))
    if change == 'compressed_trailing_bytes': row['document'] += b'extra'
    before = copy.deepcopy(work)
    result = A.resolve_author_review(work, 'ucsd', [row])
    assert result['status'] == 'held', (change, result)
    assert flags(work, result) is None and work == before


def test_reader_is_read_only_and_absent_table_preserves_legacy_behavior():
    con = sqlite3.connect(':memory:')
    assert A.load_author_review_pages(con) is None
    work, row, _ = fixture()
    con.execute('create table author_review_xml(review_id text primary key,work text,approval text,metadata text,document blob)')
    con.execute('insert into author_review_xml values(?,?,?,?,?)', tuple(row[k] for k in ('review_id', 'work', 'approval', 'metadata', 'document')))
    before = con.execute('select * from author_review_xml').fetchall()
    loaded, errors = A.load_author_review_pages(con)
    assert not errors and A.resolve_author_review(work, 'ucsd', loaded[work['id']])['status'] == 'accepted'
    assert con.execute('select * from author_review_xml').fetchall() == before


def test_normal_native_flag_hook_keeps_ordinary_source_and_uses_separate_xml_counter():
    work, row, _ = fixture()
    before = copy.deepcopy(work)
    ctx = types.SimpleNamespace(school='ucsd', inst='https://openalex.org/'+common.INST['ucsd'],
        aff=re.compile(common.AFF['ucsd'], re.I), author_review_pages={work['id']: [row]}, tied={}, n=collections.Counter())
    observed, evidence = papers.reviewed_byline_school(ctx, work)
    assert observed == ['Donghui Choe', 'Bernhard Palsson']
    assert evidence['status'] == 'accepted' and evidence['source_format'] == X.FORMAT
    assert ctx.n['primary_xml_affiliation_review_accepted'] == 1
    assert not ctx.n['primary_pdf_affiliation_review_accepted'] and work == before
    assert all(a['institutions'] == before['authorships'][i]['institutions'] for i, a in enumerate(work['authorships']))


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('year,typ,kept', [(2020, 'article', True), (2014, 'article', False), (2020, 'dataset', False)])
def test_native_eligibility_remains_ordinary_and_report_distinguishes_xml(tmp_path, monkeypatch, year, typ, kept):
    import test_build_rules as T
    import test_primary_pdf_affiliations_integration as N
    from pihier import identity
    from schema_check import validate
    from pathlib import Path

    monkeypatch.setattr(identity, 'DUMP_PERSONS', None)
    work, _, _ = N.native_source(tmp_path, review=False, year=year, typ=typ)
    body = document([('Ada', 'Lovelace', ['Princeton University']), ('Alan', 'Turing', ['Princeton University']),
                     ('Outside', 'Person', ['University of Vienna'])], title=work['title'], year=year, doi=work['doi'])
    row = row_for(work, body, [0, 1, 2], [], school=T.SCHOOL)
    path = T.put(tmp_path, 'pi-works.sqlite')
    with sqlite3.connect(path) as con:
        con.execute('create table author_review_xml(review_id text primary key,work text,approval text,metadata text,document blob)')
        con.execute('insert into author_review_xml values(?,?,?,?,?)', tuple(row[k] for k in ('review_id', 'work', 'approval', 'metadata', 'document')))
    before = path.read_bytes()
    ctx = T.run_stages(tmp_path, upto='links')
    matches = [r for r in ctx.rows if r['oa'] == work['id']]
    assert bool(matches) == kept
    if kept:
        assert matches[0]['byline_school'] == ['Ada Lovelace', 'Alan Turing']
        assert matches[0]['authorship']['school_via'] == ['page 1 (near): Ada Lovelace Princeton University']
        assert matches[0]['authorship']['institutions'] == []
        evidence = matches[0]['byline_affiliation_review']
        assert evidence['source_format'] == X.FORMAT and 'pdf_sha256' not in evidence
        schema = json.loads((Path(__file__).resolve().parents[1]/'schemas/report.schema.json').read_text())['properties']['primaryPDFAffiliationReviews']
        assert not validate([evidence], schema)
        wrong = dict(evidence, source_format='publisher_JATS_PDF')
        assert validate([wrong], schema)
    else:
        assert not ctx.n['primary_xml_affiliation_review_accepted']
    assert path.read_bytes() == before


def test_pdf_and_xml_channels_for_same_work_are_not_silently_combined():
    work, row, _ = fixture()
    other = dict(row, source_format='pdf')
    result = A.resolve_author_review(work, 'ucsd', [row, other])
    assert result['status'] == 'held' and result['reason'] == 'competing_author_review_records'
    assert flags(work, result) is None
