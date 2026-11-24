"""Actual normalized monograph/article originals; finite private-body hashes, no live sources or IDs."""
import collections
import copy
import gzip
import hashlib
import json
import sqlite3
import zlib
from pathlib import Path
from types import SimpleNamespace

import pytest

import atlas_paths as P
from pihier import papers, source_metadata as M
from schema_check import validate

FIXTURE = Path(__file__).parent / 'fixtures/source_type_review.json'


def fixture():
    return json.loads(FIXTURE.read_text())


def setup(root, reviews=None):
    f = fixture()
    ds = copy.deepcopy(f['reviews'] if reviews is None else reviews)
    path = P.data_w('paper-source-review.json', 'tsinghua', root=root)
    path.write_text(json.dumps(dict(version=1, school='tsinghua', reviews=ds)))
    cache = P.data_w('school-captures.sqlite', 'tsinghua', root=root)
    with sqlite3.connect(cache) as c:
        c.execute('CREATE TABLE live(url TEXT PRIMARY KEY,status INT,sha256 TEXT,raw_zlib BLOB)')
        for page in f['reconstructed_HTML']:
            raw = page['body'].encode()
            c.execute('INSERT INTO live VALUES(?,?,?,?)',
                      (page['url'], 200, hashlib.sha256(raw).hexdigest(), zlib.compress(raw)))
    ctx = SimpleNamespace(here=root, school='tsinghua', pid0=f['pis'], n=collections.Counter(),
                          dblp_persons=dict(persons=f['owned_book_person']),
                          hits=[(s['pi'], s['work']) for s in f['works']],
                          stu={'unchanged': {'member': {'roles': ['member']}}}, sp=[{'status': 'candidate'}],
                          tied={'ordinary': 'unchanged'}, page_read={'ordinary': 'unchanged'}, from_pw=[])
    return f, ctx


def date(source, title, row):
    return papers.venue_version_date(dict(source, title=title), {})[0]


def source(ctx, oa):
    return next(w for _, w in ctx.hits if w['id'] == oa)


def put(root, ds):
    P.data_w('paper-source-review.json', 'tsinghua', root=root).write_text(json.dumps(
        dict(version=1, school='tsinghua', reviews=ds)))


def snapshot(ctx, rows):
    return copy.deepcopy((rows, ctx.hits, ctx.pid0, ctx.dblp_persons, ctx.stu, ctx.sp,
                          ctx.tied, ctx.page_read, ctx.from_pw))


@pytest.mark.usefixtures('layout')
def test_actual_seven_chapters_and_article_use_whole_sources_fold_and_leave_identity_inputs_unchanged(tmp_path):
    f, ctx = setup(tmp_path); rows = f['rows']; before = snapshot(ctx, rows)
    old, _, _ = papers.fold_books(copy.deepcopy(rows), 'tsinghua')
    corrected = M.apply(ctx, rows, date)
    after, _, _ = papers.fold_books(copy.deepcopy(corrected), 'tsinghua')
    assert len(old) == 9 and len(after) == 2
    assert next(r for r in old if r['type'] == 'book')['chapters_folded'] == 5
    assert next(r for r in after if r['type'] == 'book')['chapters_folded'] == 12
    assert snapshot(ctx, rows) == before
    changed = [(a, b) for a, b in zip(rows, corrected) if a != b]
    assert len(changed) == 8
    for original, projected in changed:
        assert {k: v for k, v in projected.items() if k not in {'type', 'sourceMetadataReviews'}} == {
            k: v for k, v in original.items() if k != 'type'}
        marker = projected['sourceMetadataReviews'][-1]
        assert marker['original_type'] == original['type'] and marker['review_kind'] == 'source_type'
    assert collections.Counter(d['status'] for d in ctx.paper_source_review['decisions']) == {'projected': 8}
    for d in ctx.paper_source_review['decisions']:
        assert d['original_complete_source'] == source(ctx, d['oa'])
        assert d['original_eligible_row'] == next(r for r in rows if r['oa'] == d['oa'])
        assert d['available_complete_sources']
        if d['proposed_type'] == 'book-chapter':
            assert d['available_complete_book_sources'] and d['available_eligible_book_rows']


@pytest.mark.usefixtures('layout')
def test_no_input_is_exact_noop_and_real_lncs_conference_is_not_reclassified(tmp_path):
    f, ctx = setup(tmp_path)
    P.data('paper-source-review.json', 'tsinghua', root=tmp_path).unlink()
    rows = f['rows'] + [f['conference_control']['row']]
    before = snapshot(ctx, rows)
    assert M.apply(ctx, rows, date) is rows and snapshot(ctx, rows) == before
    assert rows[-1]['type'] == 'conference-paper'
    assert f['conference_control']['work']['primary_location']['raw_type'] == 'book-chapter'


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('fault', ['source_hash', 'eligible_hash', 'new_variant', 'doi', 'identity_hold',
                                  'candidate', 'appointment', 'date', 'book_pid', 'book_record', 'book_doi',
                                  'book_absent', 'book_candidate', 'book_date', 'book_series', 'container',
                                  'source_author', 'book_author', 'book_title', 'book_year'])
def test_book_source_or_ordinary_eligibility_changes_hold_without_lending_metadata(tmp_path, fault):
    f = fixture(); d = next(d for d in f['reviews'] if d['authority']['kind'] == 'owned_monograph_chapter')
    if fault == 'source_hash': d['source']['work_sha256'] = '0' * 64
    if fault == 'eligible_hash': d['source']['eligible_row_sha256'] = '0' * 64
    if fault == 'doi': d['match']['doi'] = '10.9/unrelated'
    if fault == 'book_pid': d['authority']['book']['owned_dblp']['pid'] = 'https://dblp.org/pid/unowned'
    if fault == 'book_record': d['authority']['book']['owned_dblp']['record_sha256'] = '0' * 64
    if fault == 'book_doi': d['authority']['book']['doi'] = '10.9/unrelated'
    if fault == 'container': d['authority']['container_title'] = 'Unrelated Container'
    f, ctx = setup(tmp_path, [d]); rows = f['rows']; r = next(r for r in rows if r['oa'] == d['match']['oa'])
    b = d['authority']['book']; br = next(r for r in rows if r['oa'] == b['oa']); w = source(ctx, r['oa'])
    if fault == 'new_variant': ctx.hits.append((r['pi'], dict(w, publication_date='2000-01-01')))
    if fault == 'identity_hold': ctx.pid0[r['pi']]['identityHold'] = {'reason': 'unresolved actual PI'}
    if fault == 'candidate': r['identity'] = 'candidate'; d['source']['eligible_row_sha256'] = M.digest(r)
    if fault == 'appointment': r['appointment'] = None; d['source']['eligible_row_sha256'] = M.digest(r)
    if fault == 'book_absent': rows.remove(br)
    if fault == 'book_candidate': br['identity'] = 'candidate'; b['eligible_row_sha256'] = M.digest(br)
    if fault == 'book_date': br['date'] = '1999-01-01'; b['eligible_row_sha256'] = M.digest(br)
    if fault in {'book_series', 'source_author'}:
        if fault == 'book_series': w['primary_location']['source']['type'] = 'book series'
        else: w['authorships'][0]['raw_author_name'] = 'Different Source Author'
        d['source']['work_sha256'] = M.digest(w); d['source']['available_work_sha256s'] = [M.digest(w)]
    if fault in {'book_author', 'book_title', 'book_year'}:
        pid = b['owned_dblp']['pid']; pub = ctx.dblp_persons['persons'][pid]['pubs'][0]
        if fault == 'book_author': pub['authors'][0][0] = 'Different Book Author'
        elif fault == 'book_title': pub['title'] = 'Unrelated Same DOI Book'
        else: pub['year'] = 1999
        b['owned_dblp']['record_sha256'] = M.digest(pub)
    put(tmp_path, [d]); before = snapshot(ctx, rows)
    callback = (lambda w, t, r: '1999') if fault == 'date' else date
    with pytest.raises(ValueError, match='requires renewed proof'): M.apply(ctx, rows, callback)
    assert snapshot(ctx, rows) == before
    assert ctx.paper_source_review['decisions'][-1]['status'] == 'held'


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('fault', ['body_bytes', 'owner_name', 'home_href', 'citation_doi', 'author_order',
                                  'missing_author', 'missing_paper_link', 'journal', 'raw_kind', 'missing_cache'])
def test_primary_authority_replays_bytes_named_owner_literal_chain_doi_all_authors_and_paper_link(tmp_path, fault):
    f = fixture(); d = next(d for d in f['reviews'] if d['authority']['kind'] == 'owned_primary_journal_article')
    if fault == 'owner_name': d['authority']['homepage']['name_quote'] = 'Another Named PI'
    if fault == 'home_href': d['authority']['homepage']['publication_href'] = 'unobserved.html'
    if fault == 'journal': d['authority']['publication']['journal'] = 'Different Journal'
    f, ctx = setup(tmp_path, [d]); rows = f['rows']; w = source(ctx, d['match']['oa']); p = d['authority']['publication']
    cache = P.data('school-captures.sqlite', 'tsinghua', root=tmp_path)
    if fault == 'missing_cache': cache.unlink()
    elif fault in {'body_bytes', 'citation_doi', 'author_order', 'missing_author', 'missing_paper_link'}:
        with sqlite3.connect(cache) as c:
            raw = zlib.decompress(c.execute('SELECT raw_zlib FROM live WHERE url=?', (p['url'],)).fetchone()[0]).decode()
            if fault == 'body_bytes': raw += '\n'
            if fault == 'citation_doi': raw = raw.replace('10.1145/3813801', '10.9/unrelated'); p['citation_quote'] = p['citation_quote'].replace('10.1145/3813801', '10.9/unrelated')
            if fault == 'author_order': raw = raw.replace('Weisong Sun, Chunrong Fang', 'Chunrong Fang, Weisong Sun'); p['citation_quote'] = p['citation_quote'].replace('Weisong Sun, Chunrong Fang', 'Chunrong Fang, Weisong Sun')
            if fault == 'missing_author': raw = raw.replace('Yun Miao, ', ''); p['citation_quote'] = p['citation_quote'].replace('Yun Miao, ', '')
            if fault == 'missing_paper_link': raw = raw.replace('href="'+p['paper_href']+'"', 'href="unobserved.pdf"')
            c.execute('UPDATE live SET raw_zlib=? WHERE url=?', (zlib.compress(raw.encode()), p['url']))
            if fault != 'body_bytes':
                p['sha256'] = hashlib.sha256(raw.encode()).hexdigest(); c.execute('UPDATE live SET sha256=? WHERE url=?', (p['sha256'], p['url']))
    if fault == 'raw_kind':
        w['primary_location']['raw_type'] = 'proceedings-article'
        d['source']['work_sha256'] = M.digest(w); d['source']['available_work_sha256s'] = [M.digest(w)]
    put(tmp_path, [d]); before = snapshot(ctx, rows)
    with pytest.raises(ValueError, match='requires renewed proof'): M.apply(ctx, rows, date)
    assert snapshot(ctx, rows) == before


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('extra', ['title', 'date', 'byline', 'publication_year'])
def test_type_contract_cannot_project_another_scientific_field(tmp_path, extra):
    f = fixture(); d = copy.deepcopy(f['reviews'][0]); d['changes'][extra] = 'unreviewed'
    f, ctx = setup(tmp_path, [d]); before = snapshot(ctx, f['rows'])
    with pytest.raises(ValueError, match='type-only'): M.apply(ctx, f['rows'], date)
    assert snapshot(ctx, f['rows']) == before


@pytest.mark.usefixtures('layout')
def test_arbitrary_source_path_and_competing_selectors_rejected(tmp_path):
    f = fixture(); d = next(d for d in f['reviews'] if d['authority']['kind'] == 'owned_primary_journal_article')
    d['authority']['raw_source_path'] = '/tmp/unreviewed-body'
    f, ctx = setup(tmp_path, [d])
    with pytest.raises(ValueError, match='authority fields'): M.apply(ctx, f['rows'], date)
    del d['authority']['raw_source_path']; put(tmp_path, [d, dict(d, id='competing')])
    with pytest.raises(ValueError, match='competing'): M.apply(ctx, f['rows'], date)


@pytest.mark.usefixtures('layout')
def test_missing_ordinary_eligible_source_stays_absent_and_schema_accepts_provenance(tmp_path):
    f, ctx = setup(tmp_path)
    assert M.apply(ctx, [], date) == []
    assert all(d['status'] == 'no_eligible_source' for d in ctx.paper_source_review['decisions'])
    schema = json.loads((Path(__file__).parents[1] / 'schemas/paper_source_review.schema.json').read_text())
    assert validate(dict(version=1, school='tsinghua', reviews=f['reviews']), schema) == []
    schema = json.loads((Path(__file__).parents[1] / 'schemas/lab_papers.schema.json').read_text())['properties']['sourceMetadataReviews']
    del ctx._source_metadata_reviews
    corrected = M.apply(ctx, f['rows'], date)
    for r in corrected:
        if r.get('sourceMetadataReviews'): assert validate(r['sourceMetadataReviews'], schema) == []


@pytest.mark.usefixtures('layout')
def test_gzip_encoded_legitimate_primary_bodies_keep_original_byte_identity(tmp_path):
    f = fixture(); d = next(d for d in f['reviews'] if d['authority']['kind'] == 'owned_primary_journal_article')
    f, ctx = setup(tmp_path, [d]); cache = P.data('school-captures.sqlite', 'tsinghua', root=tmp_path)
    with sqlite3.connect(cache) as c:
        for proof in [d['authority']['homepage'], d['authority']['publication']]:
            raw = zlib.decompress(c.execute('SELECT raw_zlib FROM live WHERE url=?', (proof['url'],)).fetchone()[0])
            encoded = gzip.compress(raw, mtime=0); proof['sha256'] = hashlib.sha256(encoded).hexdigest()
            c.execute('UPDATE live SET sha256=?,raw_zlib=? WHERE url=?', (proof['sha256'], zlib.compress(encoded), proof['url']))
    ctx.pid0[d['pi']]['lab']['evidence']['sha256'] = d['authority']['homepage']['sha256']
    put(tmp_path, [d]); out = M.apply(ctx, f['rows'], date)
    assert next(r for r in out if r['oa'] == d['match']['oa'])['type'] == 'article'


@pytest.mark.usefixtures('layout')
def test_malformed_positive_review_cannot_be_cached_as_absent_on_repeated_call(tmp_path):
    f = fixture(); d = f['reviews'][0]; d['changes']['date'] = 'unreviewed'
    f, ctx = setup(tmp_path, [d]); before = snapshot(ctx, f['rows'])
    for _ in range(2):
        with pytest.raises(ValueError, match='type-only'): M.apply(ctx, f['rows'], date)
    assert snapshot(ctx, f['rows']) == before
