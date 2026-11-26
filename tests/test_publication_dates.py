"""Original issue dates must not silently revert to platform migration dates."""
import copy
import hashlib
import sqlite3
from types import SimpleNamespace
import zlib

import pymupdf
import pytest

from pihier import publisher_issue_dates as D
from pihier.source_metadata import digest


@pytest.fixture
def case(tmp_path, monkeypatch):
    pdf_url = 'https://publisher.example/article/download/1/2'
    work = dict(id='https://openalex.org/W1', doi='https://doi.org/10.1000/article',
                title='A Scientific Study', publication_date='2021-08-04', publication_year=2021,
                authorships=[dict(raw_author_name=n) for n in ['Ada Lovelace', 'Alan Turing']],
                primary_location=dict(pdf_url=pdf_url))
    pub = dict(key='conf/example/AT16', type='inproceedings', year=2016, title=work['title'],
               authors=[['Ada Lovelace', None], ['Alan Turing', None]], dois=[])
    doc = pymupdf.open(); page = doc.new_page()
    # Deliberately write the physically top header LAST in PDF stream order.
    page.insert_text((50, 130), 'A Scientific Study\nAda Lovelace\nAlan Turing\nAbstract')
    header = 'Proceedings of the Research Conference (2016)'
    page.insert_text((50, 40), header); body = doc.tobytes(); doc.close()
    metas = {'DC.Date.issued': '2016-05-17', 'DC.Date.created': work['publication_date'],
             'citation_date': '2016', 'citation_title': work['title'], 'citation_doi': work['doi'],
             'citation_pdf_url': pdf_url}
    html = ('<html><head>' + ''.join(f'<meta name="{k}" content="{v}">' for k, v in metas.items())
            + ''.join(f'<meta name="citation_author" content="{n}">' for n in ['Ada Lovelace', 'Alan Turing'])
            + '</head><body><a href="/article/view/1/2">PDF viewer</a></body></html>').encode()
    path = tmp_path / 'captures.sqlite'; con = sqlite3.connect(path)
    con.execute('create table live(url text primary key,status int,sha256 text,raw_zlib blob)')
    def store(url, raw):
        sha = hashlib.sha256(raw).hexdigest()
        con.execute('insert or replace into live values(?,?,?,?)', (url, 200, sha, zlib.compress(raw)))
        con.commit(); return dict(url=url, sha256=sha)
    publisher = store('https://publisher.example/article/view/1', html)
    printed = dict(store(pdf_url, body), printed_issue_quote=header,
                   printed_names=['Ada Lovelace', 'Alan Turing'])
    review = dict(id='date1', pi='Ada Lovelace', decision='publisher_issued_date',
                  match=dict(oa=work['id'], doi=work['doi']), changes=dict(publication_date='2016-05-17'),
                  why='Original issue vs platform migration', independent_reviewer='reviewer',
                  source=dict(work_sha256=digest(work), original_publication_date=work['publication_date'],
                              original_title=work['title'], ordered_byline=['Ada Lovelace', 'Alan Turing']),
                  publisher=publisher, pdf=printed,
                  owned_dblp=dict(pid='https://dblp.org/pid/1', key=pub['key'], record_sha256=digest(pub)))
    ctx = SimpleNamespace(school='test', here=tmp_path,
                          pid0={'Ada Lovelace': dict(dblp=['https://dblp.org/pid/1'])},
                          dblp_persons={'persons': {'https://dblp.org/pid/1': {'pubs': [pub]}}},
                          paper_source_review={'decisions': []})
    monkeypatch.setattr(D.P, 'data', lambda *a, **kw: path)
    monkeypatch.setattr(D.M, 'prepare', lambda ctx: [review])
    yield ctx, work, review, html, store
    con.close()


def test_exact_issued_date_is_replayed_without_modifying_original_index_work(case):
    ctx, work, review, _, _ = case; before = copy.deepcopy(work)
    D.validate(review)
    date, basis = D.resolve(ctx, 'Ada Lovelace', work, work['publication_date'], None)
    assert date == '2016-05-17' and basis['oa_date'] == '2021-08-04'
    assert basis['venue_year'] == 2016 and work == before
    assert ctx.paper_source_review['decisions'][0]['status'] == 'projected'


@pytest.mark.parametrize('change', ['index', 'ordered_byline', 'doi', 'owned_record', 'other_pi',
                                  'pdf_hash', 'header', 'printed_name', 'platform_date', 'issued_date',
                                  'duplicate_date', 'other_pdf', 'other_title', 'publisher_authors'])
def test_changed_positive_date_proof_stops_before_publishing_the_known_wrong_date(case, change):
    ctx, work, review, html, store = case
    if change == 'index': work['publication_year'] = 2020
    elif change == 'ordered_byline': review['source']['ordered_byline'].reverse()
    elif change == 'doi': review['match']['doi'] = '10.1000/other'
    elif change == 'owned_record': review['owned_dblp']['record_sha256'] = '0' * 64
    elif change == 'other_pi': ctx.pid0['Ada Lovelace']['dblp'] = []
    elif change == 'pdf_hash': review['pdf']['sha256'] = '0' * 64
    elif change == 'header': review['pdf']['printed_issue_quote'] = 'A citation to Research Conference 2016'
    elif change == 'printed_name': review['pdf']['printed_names'][1] = 'Another Person'
    else:
        if change == 'platform_date': html = html.replace(b'2021-08-04', b'2022-08-04')
        elif change == 'issued_date': html = html.replace(b'2016-05-17', b'2015-05-17')
        elif change == 'duplicate_date': html = html.replace(b'</head>', b'<meta name="DC.Date.issued" content="2015-05-17"></head>')
        elif change == 'other_pdf': html = html.replace(b'download/1/2', b'download/1/3')
        elif change == 'other_title': html = html.replace(b'A Scientific Study', b'Another Scientific Study')
        elif change == 'publisher_authors': html = html.replace(b'Alan Turing', b'Another Person')
        review['publisher'] = store(review['publisher']['url'], html)
    with pytest.raises(ValueError, match='requires renewed proof'):
        D.resolve(ctx, 'Ada Lovelace', work, work['publication_date'], None)
    assert ctx.paper_source_review['decisions'][-1]['status'] == 'held'


def test_ordinary_date_authority_and_unrelated_rows_are_preserved(case, monkeypatch):
    ctx, work, _, _, _ = case
    with pytest.raises(ValueError, match='competing ordinary date'):
        D.resolve(ctx, 'Ada Lovelace', work, '2019', dict(venue_year=2019))
    monkeypatch.setattr(D.M, 'prepare', lambda ctx: [])
    assert D.resolve(ctx, 'Ada Lovelace', work, '2021-08-04', None) == ('2021-08-04', None)


def test_primary_publisher_link_can_supply_a_missing_index_pdf_url(case):
    ctx, work, review, _, _ = case
    work['primary_location']['pdf_url'] = None
    review['source']['work_sha256'] = digest(work)
    assert D.resolve(ctx, 'Ada Lovelace', work, work['publication_date'], None)[0] == '2016-05-17'
    work['primary_location']['pdf_url'] = 'https://publisher.example/another-version.pdf'
    review['source']['work_sha256'] = digest(work)
    with pytest.raises(ValueError, match='requires renewed proof'):
        D.resolve(ctx, 'Ada Lovelace', work, work['publication_date'], None)


def test_literal_copyright_date_and_physical_title_are_independent_of_pdf_stream_order(case):
    ctx, work, review, _, store = case
    doc = pymupdf.open(); page = doc.new_page()
    page.insert_textbox(pymupdf.Rect(20, 300, 570, 650), 'Body research words ' * 200, fontsize=8)
    page.insert_text((50, 130), 'A Scientific Study\nAda Lovelace\nAlan Turing')
    quote = 'Copyright (c) 2016, Research Association. All rights reserved.'
    page.insert_text((50, 720), quote)
    assert page.get_text().index('A Scientific Study') > 3000
    raw = doc.tobytes(); doc.close()
    review['pdf'].update(store(review['pdf']['url'], raw), date_proof='copyright',
                         date_bbox=[20, 695, 590, 740], printed_issue_quote=quote)
    assert D.resolve(ctx, 'Ada Lovelace', work, work['publication_date'], None)[0] == '2016-05-17'
    review['pdf']['date_bbox'] = [20, 300, 590, 400]
    with pytest.raises(ValueError, match='requires renewed proof'):
        D.resolve(ctx, 'Ada Lovelace', work, work['publication_date'], None)


def test_standalone_pdf_acute_accent_is_typography_not_a_new_author(case):
    ctx, work, review, _, store = case
    work['authorships'][0]['raw_author_name'] = 'Ada Lovelace'
    doc = pymupdf.open(); page = doc.new_page()
    page.insert_text((50, 40), review['pdf']['printed_issue_quote'])
    page.insert_text((50, 130), 'A Scientific Study\nAda Lovelac\u00b4e\nAlan Turing')
    raw = doc.tobytes(); doc.close()
    review['pdf'].update(store(review['pdf']['url'], raw), printed_names=['Ada Lovelac\u00b4e', 'Alan Turing'])
    assert D.resolve(ctx, 'Ada Lovelace', work, work['publication_date'], None)[0] == '2016-05-17'
    review['pdf']['printed_names'][0] = 'Another Lovelac\u00b4e'
    with pytest.raises(ValueError, match='requires renewed proof'):
        D.resolve(ctx, 'Ada Lovelace', work, work['publication_date'], None)
