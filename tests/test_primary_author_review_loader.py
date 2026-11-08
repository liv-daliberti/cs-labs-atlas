"""Explicit source reviews correct derived flags without lending R8/R3 admission authority."""
import collections
import copy
import hashlib
import json
import re
import sqlite3
import types
import zlib

import pytest

import atlas_paths as P
import test_build_rules as T
from test_primary_pdf_affiliations import fixture as inline_fixture
from test_primary_pdf_footnotes import fixture as footnote_fixture
from pihier import common, identity, papers, primary_affiliations as A


def record(work, page, text, *, school=T.SCHOOL, review_id='fixture-review'):
    metadata = {k: copy.deepcopy(page[k]) for k in ('url', 'pdf_sha256', 'author_affiliation_review')}
    approval = dict(version=1, decision='reviewed', purpose=A.AUTHOR_REVIEW_PURPOSE, school=school,
                    review_id=review_id, work=work['id'], reviewed_by='contract-fixture-not-actual-source-approval',
                    reviewed_at='2026-11-08', source_packet_sha256='1' * 64, source_replay_sha256='2' * 64,
                    source_work_sha256=A.digest(work), source_authorships_sha256=A.digest(work['authorships']),
                    metadata_sha256=A.digest(metadata), page1_text_sha256=hashlib.sha256(text.encode()).hexdigest(),
                    pdf_sha256=page['pdf_sha256'], pdf_url=page['url'])
    return dict(review_id=review_id, work=work['id'], approval=json.dumps(approval), metadata=json.dumps(metadata),
                page1=zlib.compress(text.encode()))


def make_table(con, records=(), table='author_review_pages'):
    assert table in ('author_review_pages', 'proposed_author_review_pages')
    con.execute(f'create table {table}(review_id text primary key,work text,approval text,metadata text,page1 blob)')
    for row in records:
        con.execute(f'insert into {table} values (?,?,?,?,?)', tuple(row[k] for k in ('review_id', 'work', 'approval', 'metadata', 'page1')))
    con.commit()


def context(work, records, school=T.SCHOOL):
    return types.SimpleNamespace(school=school, inst=common.INST[school], aff=re.compile(common.AFF[school], re.I),
                                 tied={}, page_read={}, author_review_pages={work['id']: records}, n=collections.Counter())


def store(root, rows=(), table='author_review_pages'):
    con = sqlite3.connect(T.put(root, 'pi-works.sqlite'))
    con.executescript('''create table works(id text primary key,body blob);
        create table pages(work text primary key,arxiv text,url text,status text,pdf_sha256 text,
                           page1 blob,school_named int,quote text,fetched_at text);''')
    if table is not None:
        make_table(con, rows, table)
    con.close()


@pytest.mark.parametrize('fixture', [inline_fixture, footnote_fixture])
def test_explicit_complete_v1_and_v2_review_preserves_source_and_ordinary_context(fixture):
    work, page, text = fixture(); school = 'harvard' if fixture is inline_fixture else T.SCHOOL
    row = record(work, page, text, school=school)
    ctx = context(work, [row], school)
    before = copy.deepcopy((work, page, ctx.tied, ctx.page_read))
    flags, info = papers.reviewed_byline_school(ctx, work)
    assert info['status'] == 'accepted' and info['purpose'] == A.AUTHOR_REVIEW_PURPOSE
    assert info['input_table'] == 'author_review_pages' and info['review_id'] == 'fixture-review'
    assert len(info['approval_sha256']) == 64
    assert (work, page, ctx.tied, ctx.page_read) == before
    assert papers.reviewed_byline_school(ctx, work) == (flags, info)
    assert ctx.n['primary_pdf_affiliation_review_accepted'] == 1


def test_absent_table_and_proposal_table_are_exact_noops():
    work, page, text = footnote_fixture()
    for proposal in (False, True):
        con = sqlite3.connect(':memory:')
        if proposal: make_table(con, [record(work, page, text)], 'proposed_author_review_pages')
        assert A.load_author_review_pages(con) is None
        con.close()


@pytest.mark.parametrize('change', [
    'proposal', 'purpose', 'school', 'reviewer', 'date', 'version_bool', 'unknown_approval_field',
    'source_hash', 'authorship_hash', 'metadata_hash', 'page_hash', 'PDF_hash', 'PDF_url',
    'selector', 'packet_hash', 'approval_json', 'metadata_json', 'ordinary_quotes', 'compression', 'trailing_blob',
    'missing_author', 'reassigned_author', 'metadata_source_changed', 'oversize_page',
])
def test_invalid_stale_or_unreviewed_records_keep_original_flags(change):
    work, page, text = footnote_fixture(); row = record(work, page, text)
    approval, metadata = json.loads(row['approval']), json.loads(row['metadata'])
    if change == 'proposal': approval['decision'] = 'proposal'
    if change == 'purpose': approval['purpose'] = 'PI_identity_or_school_admission'
    if change == 'school': approval['school'] = 'harvard'
    if change == 'reviewer': approval['reviewed_by'] = ''
    if change == 'date': approval['reviewed_at'] = 'not-a-date'
    if change == 'version_bool': approval['version'] = True
    if change == 'unknown_approval_field': approval['guess'] = True
    if change == 'source_hash': approval['source_work_sha256'] = '0' * 64
    if change == 'authorship_hash': approval['source_authorships_sha256'] = '0' * 64
    if change == 'metadata_hash': approval['metadata_sha256'] = '0' * 64
    if change == 'page_hash': approval['page1_text_sha256'] = '0' * 64
    if change == 'PDF_hash': approval['pdf_sha256'] = '0' * 64
    if change == 'PDF_url': approval['pdf_url'] = 'https://different.example/paper.pdf'
    if change == 'selector': approval['work'] = 'https://openalex.org/W999'
    if change == 'packet_hash': approval['source_packet_sha256'] = 'invalid'
    if change == 'ordinary_quotes': metadata['quotes'] = ['Ada Lovelace Princeton University']
    if change == 'missing_author': metadata['author_affiliation_review']['authors'].pop()
    if change == 'reassigned_author': metadata['author_affiliation_review']['authors'][2]['affiliation_ids'] = ['p']
    if change == 'metadata_source_changed': metadata['author_affiliation_review']['source_work_sha256'] = '0' * 64
    if change in ('ordinary_quotes', 'missing_author', 'reassigned_author', 'metadata_source_changed'):
        approval['metadata_sha256'] = A.digest(metadata)  # strong inner validation must still hold
    row.update(approval=json.dumps(approval), metadata=json.dumps(metadata))
    if change == 'approval_json': row['approval'] = '[]'
    if change == 'metadata_json': row['metadata'] = 'unparseable'
    if change == 'compression': row['page1'] = b'not-zlib'
    if change == 'trailing_blob': row['page1'] += b'unbound bytes'
    if change == 'oversize_page': row['page1'] = zlib.compress(b'x' * ((2 << 20) + 1))
    ctx = context(work, [row]); before = copy.deepcopy(work)
    original, _ = papers.reviewed_byline_school(context(work, []), work)
    flags, info = papers.reviewed_byline_school(ctx, work)
    assert flags == original and info['status'] == 'held'
    assert ctx.tied == ctx.page_read == {} and work == before


def test_duplicate_work_reviews_hold_and_legacy_channel_stays_compatible():
    work, page, text = footnote_fixture(); row = record(work, page, text)
    ctx = context(work, [row, dict(row, review_id='second')])
    _, info = papers.reviewed_byline_school(ctx, work)
    assert info['status'] == 'held' and info['reason'] == 'competing_author_review_records'
    legacy = context(work, [])
    del legacy.author_review_pages
    legacy.tied[work['id']] = page
    legacy.page_read[work['id']] = ('ok', zlib.compress(text.encode()), page['url'])
    flags, info = papers.reviewed_byline_school(legacy, work)
    assert flags == ['Lovelace, Ada', 'Turing, Alan'] and info['status'] == 'accepted'
    dedicated = context(work, [row]); dedicated.tied = legacy.tied; dedicated.page_read = legacy.page_read
    _, info = papers.reviewed_byline_school(dedicated, work)
    assert info['status'] == 'held' and info['reason'] == 'competing_author_review_channels'


def test_cache_cannot_hide_changed_review_or_a_new_conflicting_channel():
    work, page, text = footnote_fixture(); row = record(work, page, text)
    ctx = context(work, [row])
    _, info = papers.reviewed_byline_school(ctx, work)
    assert info['status'] == 'accepted'
    row['page1'] += b'changed cached source'
    _, info = papers.reviewed_byline_school(ctx, work)
    assert info['status'] == 'held'
    ctx = context(work, [record(work, page, text)])
    assert papers.reviewed_byline_school(ctx, work)[1]['status'] == 'accepted'
    ctx.tied[work['id']] = page
    assert papers.reviewed_byline_school(ctx, work)[1]['reason'] == 'competing_author_review_channels'


@pytest.mark.usefixtures('layout')
def test_native_paired_fixture_preserves_hits_ties_admission_and_candidate_status(tmp_path, monkeypatch):
    monkeypatch.setattr(identity, 'DUMP_PERSONS', None)
    work, page, text = footnote_fixture()
    baseline, proposal = tmp_path / 'baseline', tmp_path / 'proposal'
    for root in (baseline, proposal): T.write_school(root, sweep=[work])
    store(baseline, table=None); store(proposal, [record(work, page, text)])
    before = T.put(proposal, 'pi-works.sqlite').read_bytes()
    old, new = T.run_stages(baseline), T.run_stages(proposal)
    assert old.hits == new.hits and old.anchored == new.anchored
    assert old.tied == new.tied == {} and old.page_read == new.page_read == {}
    assert old.from_pw == new.from_pw == set()
    assert old.stu == new.stu
    def strip(row):
        if isinstance(row, list):
            return [strip(v) for v in row]
        if isinstance(row, dict):
            return {k: strip(v) for k, v in row.items() if k not in ('byline_school', 'byline_affiliation_review', '_bylines')}
        return row
    assert [strip(r) for r in old.rows] == [strip(r) for r in new.rows]
    target = next(r for r in new.rows if r['oa'] == work['id'])
    assert target['byline_school'] == ['Lovelace, Ada', 'Turing, Alan']
    assert all(r['status'] == 'candidate' for r in new.sp if r['oa'] == work['id'])
    assert T.put(proposal, 'pi-works.sqlite').read_bytes() == before
    con = sqlite3.connect(f'file:{T.put(proposal, "pi-works.sqlite")}?mode=ro', uri=True)
    assert con.execute('select count(*) from works').fetchone()[0] == con.execute('select count(*) from pages').fetchone()[0] == 0
    con.close()


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('failure', ['no_school', 'no_identity', 'outside_period', 'nonpaper'])
def test_separate_review_never_rescues_an_ineligible_native_paper(tmp_path, monkeypatch, failure):
    monkeypatch.setattr(identity, 'DUMP_PERSONS', None)
    work, page, text = footnote_fixture()
    if failure == 'no_school':
        for a in work['authorships']: a['institutions'] = []; a['raw_affiliation_strings'] = []
    if failure == 'outside_period': work['publication_year'] = 2014; work['publication_date'] = '2014-01-01'
    if failure == 'nonpaper': work['type'] = 'dataset'
    page['author_affiliation_review']['source_work_sha256'] = A.digest(work)
    page['author_affiliation_review']['source_authorships_sha256'] = A.digest(work['authorships'])
    T.write_school(tmp_path, sweep=[work]); store(tmp_path, [record(work, page, text)])
    if failure == 'no_identity':
        path = T.put(tmp_path, 'census-overrides.json', None)
        overrides = json.loads(path.read_text())
        overrides[T.SCHOOL]['Ada Lovelace'].update(no_identity=True, why_no_identity='Explicit fixture identity hold.')
        path.write_text(json.dumps(overrides))
    ctx = T.run_stages(tmp_path, upto='papers')
    assert not any(r['oa'] == work['id'] for r in ctx.rows)
    assert ctx.tied == ctx.page_read == {} and not ctx.n['primary_pdf_affiliation_review_accepted']


def test_malformed_table_is_a_diagnostic_not_an_admission_source():
    con = sqlite3.connect(':memory:'); con.execute('create table author_review_pages(wrong text)')
    records, holds = A.load_author_review_pages(con)
    assert records == {} and holds[0]['reason'] == 'malformed_author_review_table'
    con.close()


@pytest.mark.nfs
def test_three_sealed_real_maps_are_only_in_memory_contract_examples():
    path = P.SCRATCH / 'tsinghua-first-chain-1108/primary-review/primary-author-affiliation-proposals.json'
    if not path.exists(): pytest.skip('sealed private primary packet is not installed')
    body = path.read_bytes()
    assert hashlib.sha256(body).hexdigest() == 'cfaa42087a89fd3a243335ef3df245df4c7ccada51186ea3f6a7367ff1fbc919'
    packet = json.loads(body); checked = []
    for i, proposal in enumerate(packet['proposals']):
        work, page, text = proposal['work'], proposal['page1'], proposal['page1_text']
        row = record(work, page, text, school='tsinghua', review_id='private-contract-fixture-' + str(i))
        approval = json.loads(row['approval'])
        approval['source_packet_sha256'] = packet['source_packet_sha256']
        approval['source_replay_sha256'] = hashlib.sha256((path.parent / 'v2-actual-source-comparison.json').read_bytes()).hexdigest()
        row['approval'] = json.dumps(approval)
        con = sqlite3.connect(':memory:'); make_table(con, [row]); rows, holds = A.load_author_review_pages(con)
        assert not holds
        ctx = context(work, rows[work['id']], 'tsinghua'); before = copy.deepcopy(work)
        flags, info = papers.reviewed_byline_school(ctx, work)
        assert info['status'] == 'accepted' and flags == proposal['desired_derived_byline_school']
        assert ctx.tied == ctx.page_read == {} and work == before
        con.close(); checked.append(len(work['authorships']))
    assert checked == [7, 6, 4] and path.read_bytes() == body
