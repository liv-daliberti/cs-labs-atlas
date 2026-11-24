"""Publisher-only recoveries require source facts and pass the native paper gates."""
import copy
import hashlib
import json
from collections import Counter, defaultdict
from types import SimpleNamespace

import pytest

import atlas_paths as P
from pihier import papers, primary_publications as R


def source(tmp_path, filename, text):
    raw = ('<html><body>' + text + '</body></html>').encode()
    path = tmp_path / filename
    path.write_bytes(raw)
    return dict(url='https://publisher.example/' + filename, source_file=str(path),
                sha256=hashlib.sha256(raw).hexdigest(), format='html')


def case(tmp_path):
    # Metadata from the original 2017 Computer Education article; compact HTML
    # fixtures exercise extraction without checking in the entire publisher site.
    title = '以计算思维能力为导向的硬件课程体系建设'
    byline = ['贺莲', '龚奕利', '蔡朝晖', '刘树波']
    block = ' '.join(byline) + ' 1.武汉大学计算机学院'
    pub = source(tmp_path, 'article.html', title + ' ' + block
                 + ' 计算机教育 DOI: 10.16512/j.cnki.jsjjy.2017.08.019 出版时间：2017-08-10')
    fac = source(tmp_path, 'faculty.html', '武汉大学计算机学院 贺莲 女 副教授')
    d = dict(id='whu-he-lian-2017', pi='贺莲', decision='reviewed_primary_publication',
             reviewed_by='source-reviewer', reviewed_on='2026-11-23', why='Literal named faculty and publisher byline with three established school colleagues.',
             publication=dict(title=title, title_quote=title, year=2017, date='2017-08-10', publication_date_label='出版时间',
                              publication_quote='出版时间：2017-08-10', type='article', kind_quote='计算机教育',
                              venue='计算机教育', venue_quote='计算机教育', doi='10.16512/j.cnki.jsjjy.2017.08.019',
                              identifier_quote='DOI: 10.16512/j.cnki.jsjjy.2017.08.019', byline=byline,
                              byline_quote=block, complete_credited_byline=True, source=pub),
             ownership=dict(name='贺莲', basis='literal_faculty_and_primary_authorship', source=fac, quote='贺莲 女 副教授'),
             school_authorship=dict(name='贺莲', affiliation='武汉大学计算机学院', source=pub, quote=block,
                                    assignment='all_authors_single_affiliation', single_affiliation_reviewed=True))
    p = dict(pi='贺莲', names=['贺莲'], dblp=[], periods=[], listings=[dict(year=2017)])
    ctx = SimpleNamespace(school='whu', here=tmp_path, pid0={'贺莲': p}, n=Counter(), hits=[], cwork=lambda w: None)
    return ctx, p, d


def test_actual_article_facts_keep_complete_byline_and_honest_source_identifier(tmp_path):
    ctx, p, d = case(tmp_path)
    before = copy.deepcopy((p, d))
    row = R.project(ctx, d, {})
    assert row['key'].startswith('publisher:') and row['byline'] == d['publication']['byline']
    assert row['evidence']['basis'] == 'reviewed_primary_publisher'
    assert row['date'] == '2017-08-10'
    assert (p, d) == before
    assert 'openalex.org' not in json.dumps(row)


@pytest.mark.parametrize('fault', ['capture_changed', 'missing_capture', 'title', 'year', 'byline', 'partial_byline',
                                  'initials', 'wrong_pi', 'wrong_school', 'borrowed_affiliation', 'missing_review',
                                  'wrong_doi', 'printing_date', 'identity_hold', 'missing_faculty_role'])
def test_changed_incomplete_or_borrowed_evidence_is_held(tmp_path, fault):
    ctx, p, d = case(tmp_path)
    if fault == 'capture_changed':
        d['publication']['source']['sha256'] = '0' * 64
    elif fault == 'missing_capture':
        d['publication']['source']['source_file'] = str(tmp_path / 'absent')
    elif fault == 'title':
        d['publication']['title'] += ' other'
    elif fault == 'year':
        d['publication']['year'] = 2022
    elif fault == 'byline':
        d['publication']['byline'].append('Uncredited Author')
    elif fault == 'partial_byline':
        d['publication']['complete_credited_byline'] = False
    elif fault == 'initials':
        d['ownership']['name'] = 'L. He'
    elif fault == 'wrong_pi':
        p['names'] = ['Someone Else']
    elif fault == 'wrong_school':
        d['school_authorship']['affiliation'] = 'Wuhan University of Science and Technology'
    elif fault == 'borrowed_affiliation':
        d['school_authorship']['name'] = '刘树波'
    elif fault == 'missing_review':
        d['decision'] = 'proposal'
    elif fault == 'wrong_doi':
        d['publication']['doi'] = '10.1000/wrong'
    elif fault == 'printing_date':
        original_text = R.capture(d['publication']['source'], {})
        src = source(tmp_path, 'dates.html', original_text + ' 印刷时间：2026-08-10')
        d['school_authorship']['source'] = src
        d['publication'].update(source=src, date='2026-08-10', year=2026,
                                publication_quote='出版时间：2017-08-10 印刷时间：2026-08-10')
    elif fault == 'identity_hold':
        p['identityHold'] = 'unresolved person'
    else:
        d['ownership']['quote'] = '贺莲'
    with pytest.raises((KeyError, ValueError)) as error:
        R.project(ctx, d, {})
    if fault == 'printing_date':
        assert str(error.value) == 'publication_date_not_attested'


@pytest.mark.parametrize('fault', [None, 'appointment', 'window', 'excluded_claim', 'nonpaper'])
def test_publisher_recovery_runs_existing_native_admission_and_genre_gates(tmp_path, monkeypatch, fault):
    ctx, p, d = case(tmp_path)
    row = R.project(ctx, d, {})
    if fault == 'appointment':
        p['listings'] = []
    elif fault == 'window':
        monkeypatch.setattr(papers, 'WINDOW_START', 2018)
    elif fault == 'excluded_claim':
        monkeypatch.setattr(papers.reviewed_claims, 'excluded', lambda *a: True)
    elif fault == 'nonpaper':
        row['title'] = 'Corrections to "A source publication"'
    monkeypatch.setattr(papers, 'recovered_source', lambda ctx, kind: [row] if kind == 'publisher' else [])
    result = []
    papers.recovered_rows(ctx, result, set())
    kept, _ = papers.drop_not_papers(result, defaultdict(dict), ctx.n)
    assert bool(kept) is (fault is None)
    if kept:
        assert kept[0]['date'] == '2017-08-10'
        assert kept[0]['identity'] == 'reviewed_primary_publisher'
        assert kept[0]['appointment'] == {'listing': {'year': 2017}}


@pytest.mark.usefixtures('layout')
def test_absent_input_is_legacy_and_bad_target_does_not_add_publications(tmp_path):
    ctx, p, d = case(tmp_path)
    assert R.rows(ctx) == []
    path = P.data('publisher-publications.json', 'whu', root=tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    d['publication']['doi'] = '10.1000/wrong'
    path.write_text(json.dumps(dict(version=1, school='whu', publications=[d])))
    assert R.rows(ctx) == [] and ctx.n['publisher_review_held:publication_doi_not_attested'] == 1


def test_native_script_school_name_is_explicit_and_distinct_from_other_wuhan_schools():
    assert R.own_school('whu', '武汉大学计算机学院')
    assert R.own_school('whu', 'School of Computer Science, Wuhan University')
    assert not R.own_school('whu', '武汉科技大学计算机学院')
    assert not R.own_school('whu', 'Wuhan University of Science and Technology')
    assert not R.own_school('whu', 'Wuhan University of Technology')


def test_book_isbn_and_publication_year_are_not_a_reprint_date(tmp_path):
    ctx, p, d = case(tmp_path)
    p.update(pi='刘英', names=['刘英'], listings=[dict(year=2021)])
    ctx.pid0 = {'刘英': p}
    text = '多媒体技术与虚拟现实 刘英 主编 刘英，武汉大学计算机学院副教授，博士学位。 ISBN 978-7-307-22106-2 出版时间：2021-04 印刷时间：2024-01 武汉大学出版社'
    src = source(tmp_path, 'book.html', text)
    d.update(pi='刘英', ownership=dict(name='刘英', basis='literal_faculty_and_primary_authorship', source=src,
                                  quote='刘英，武汉大学计算机学院副教授，博士学位。'))
    d['publication'] = dict(title='多媒体技术与虚拟现实', title_quote='多媒体技术与虚拟现实', year=2021,
                            date='2021', publication_quote='出版时间：2021', publication_date_label='出版时间',
                            type='book', kind_quote='ISBN 978-7-307-22106-2', venue='武汉大学出版社',
                            venue_quote='武汉大学出版社', isbn='9787307221062', identifier_quote='ISBN 978-7-307-22106-2',
                            byline=['刘英'], byline_quote='刘英 主编', complete_credited_byline=True, source=src)
    d['school_authorship'] = dict(name='刘英', affiliation='武汉大学计算机学院', source=src,
                                  quote='刘英，武汉大学计算机学院副教授，博士学位。', assignment='individual_author_block')
    result = R.project(ctx, d, {})
    assert result['year'] == 2021 and result['type'] == 'book' and result['doi'] is None
    assert result['key'] != 'publisher:' + '0' * 40
    d['publication']['isbn'] = '9787307221063'
    with pytest.raises(ValueError, match='invalid_book_isbn'):
        R.project(ctx, d, {})


def test_publisher_imprint_cannot_stand_in_for_individual_school_affiliation(tmp_path):
    ctx, p, d = case(tmp_path)
    d['school_authorship']['affiliation'] = '武汉大学出版社'
    with pytest.raises(ValueError, match='publisher_imprint_is_not_author_affiliation'):
        R.project(ctx, d, {})


@pytest.mark.parametrize('fault', [None, 'other_edition', 'unlinked_material', 'different_publisher'])
def test_exact_book_edition_links_its_named_individual_contribution(tmp_path, fault):
    ctx, p, d = case(tmp_path)
    p.update(pi='喻丹丹', names=['喻丹丹'], listings=[dict(year=2023)])
    ctx.pid0 = {'喻丹丹': p}
    title = '算法设计与分析基础（C++版）（微课视频版）'
    contribution = '第2章和第9章由武汉大学喻丹丹编写'
    main = source(tmp_path, 'main.html', title + ' 作者：李春葆、陈良臣、喻丹丹 出版日期：2023.06.01 ISBN：9787302609483 清华大学出版社'
                  + '<a href="bookpreface?id=09577001">前言</a>')
    main['url'] = 'https://publisher.example/booksCenter/book_09577001.html'
    front = source(tmp_path, 'front.html', contribution)
    front['url'] = 'https://publisher.example/booksCenter/bookpreface?id=09577001'
    fac = source(tmp_path, 'yu.html', '喻丹丹 女 副教授')
    d.update(pi='喻丹丹', ownership=dict(name='喻丹丹', basis='literal_faculty_and_primary_authorship',
                                      source=fac, quote='喻丹丹 女 副教授'))
    d['publication'] = dict(title=title, title_quote=title, year=2023, date='2023', publication_date_label='出版日期',
                            publication_quote='出版日期：2023', type='book', kind_quote='ISBN：9787302609483',
                            venue='清华大学出版社', venue_quote='清华大学出版社', isbn='9787302609483',
                            identifier_quote='ISBN：9787302609483', byline=['李春葆', '陈良臣', '喻丹丹'],
                            byline_quote='作者：李春葆、陈良臣、喻丹丹', complete_credited_byline=True, source=main)
    d['school_authorship'] = dict(name='喻丹丹', affiliation='武汉大学', source=front,
                                  quote=contribution, assignment='individual_author_block')
    if fault == 'other_edition':
        front['url'] = front['url'].replace('09577001', '00000000')
    elif fault == 'unlinked_material':
        path = tmp_path / 'main.html'
        path.write_text(path.read_text().replace('bookpreface?id=09577001', 'unrelated'))
        main['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    elif fault == 'different_publisher':
        front['url'] = front['url'].replace('publisher.example', 'other.example')
    if fault:
        with pytest.raises(ValueError, match='school_proof_not_this_publisher_record'):
            R.project(ctx, d, {})
    else:
        row = R.project(ctx, d, {})
        assert row['byline'] == ['李春葆', '陈良臣', '喻丹丹']
        assert front['sha256'] in row['evidence']['school_via'][0]
        assert front['url'] in row['evidence']['school_via'][0]


def issue_case(tmp_path):
    """A real, tiny PDF exercises extraction, hashing and the printed-header join."""
    ctx, p, d = case(tmp_path)
    title = 'An exact verified article'
    byline = ['Ada Lovelace', 'Charles Babbage']
    header = 'Vol.43 No.4 Apr2016'
    text = header + ' ' + title + ' ' + ' '.join(byline)
    stream = f'BT /F1 10 Tf 30 700 Td ({text}) Tj ET'.encode()
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
               b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 2000 800] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
               f'<< /Length {len(stream)} >>\nstream\n'.encode() + stream + b'\nendstream']
    raw = bytearray(b'%PDF-1.4\n')
    offsets = []
    for i, obj in enumerate(objects, 1):
        offsets.append(len(raw))
        raw.extend(f'{i} 0 obj\n'.encode() + obj + b'\nendobj\n')
    xref = len(raw)
    raw.extend(b'xref\n0 6\n0000000000 65535 f \n')
    for offset in offsets:
        raw.extend(f'{offset:010} 00000 n \n'.encode())
    raw.extend(f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    path = tmp_path / 'original.pdf'
    path.write_bytes(raw)
    pdf = dict(url='https://publisher.example/original.pdf', source_file=str(path),
               sha256=hashlib.sha256(raw).hexdigest(), format='pdf')
    doi = '10.11896/j.issn.1002-137x.2016.04.004'
    citation = ','.join(byline) + f'. {title} [J]. Computer Science, 2016, 43(4): 24-27. https://doi.org/{doi}'
    block = ' '.join(byline) + ' School of Computer Science, Wuhan University'
    primary = source(tmp_path, 'issue.html', citation + ' ' + block + ' Published: 2018-12-01 <a href="original.pdf">PDF</a>')
    p.update(pi='Ada Lovelace', names=['Ada Lovelace'], listings=[dict(year=2016)])
    ctx.pid0 = {p['pi']: p}
    faculty = source(tmp_path, 'ada.html', 'Ada Lovelace, Professor, Wuhan University')
    d.update(pi=p['pi'], ownership=dict(name=p['pi'], basis='literal_faculty_and_primary_authorship',
                                      source=faculty, quote='Ada Lovelace, Professor, Wuhan University'))
    d['school_authorship'].update(name=p['pi'], affiliation='Wuhan University', source=primary, quote=block)
    d['publication'].update(title=title, title_quote=title, byline=byline, byline_quote=block,
                            source=primary, year=2016, date='2016', venue='Computer Science',
                            venue_quote='Computer Science', kind_quote='[J]', doi=doi, identifier_quote=doi,
                            publication_quote=citation, publication_date_basis='publisher_issue_citation',
                            issue_date_review=dict(decision='confirmed_original_issue', volume='43', issue='4', pages='24-27',
                                                   source=pdf, printed_issue_quote=header,
                                                   why='The printed issue and full own-article citation agree; the website upload date is later.'))
    return ctx, p, d


def test_linked_original_issue_year_survives_later_website_timestamp(tmp_path, monkeypatch):
    ctx, p, d = issue_case(tmp_path)
    row = R.project(ctx, d, {})
    assert row['year'] == 2016 and row['date'] == '2016'
    monkeypatch.setattr(papers, 'recovered_source', lambda ctx, kind: [row] if kind == 'publisher' else [])
    result = []
    papers.recovered_rows(ctx, result, set())
    assert len(result) == 1 and result[0]['appointment'] == {'listing': {'year': 2016}}
    p['listings'] = [dict(year=2018)]
    result = []
    papers.recovered_rows(ctx, result, set())
    assert result == []


@pytest.mark.parametrize('fault', ['missing_review', 'unknown_basis', 'book', 'invented_day', 'wrong_issue',
                                  'other_citation', 'wrong_title', 'wrong_doi', 'other_pdf_host', 'unlinked_pdf',
                                  'changed_pdf', 'reference_year', 'wrong_pdf_title', 'wrong_pdf_author'])
def test_issue_date_cannot_use_references_unlinked_files_or_other_articles(tmp_path, fault):
    ctx, p, d = issue_case(tmp_path)
    pub = d['publication']
    issue = pub['issue_date_review']
    if fault == 'missing_review':
        issue['decision'] = 'proposed'
    elif fault == 'unknown_basis':
        pub['publication_date_basis'] = 'url_year'
    elif fault == 'book':
        pub['type'] = 'book'
    elif fault == 'invented_day':
        pub['date'] = '2016-04-01'
    elif fault == 'wrong_issue':
        issue['issue'] = '5'
    elif fault == 'other_citation':
        pub['publication_quote'] = pub['publication_quote'].replace('Ada Lovelace', 'Another Author')
    elif fault == 'wrong_title':
        pub['title'] = 'Another Article'
    elif fault == 'wrong_doi':
        pub['doi'] = '10.1000/wrong'
    elif fault == 'other_pdf_host':
        issue['source']['url'] = 'https://unrelated.example/original.pdf'
    elif fault == 'unlinked_pdf':
        issue['source']['url'] = 'https://publisher.example/unlinked.pdf'
    elif fault == 'changed_pdf':
        issue['source']['sha256'] = '0' * 64
    elif fault == 'reference_year':
        issue['printed_issue_quote'] = 'Apr2016'
    else:
        path = tmp_path / 'original.pdf'
        before, after = ((b'An exact verified article', b'An other verified article') if fault == 'wrong_pdf_title'
                         else (b'Ada Lovelace', b'Eva Lovelace'))
        path.write_bytes(path.read_bytes().replace(before, after))
        issue['source']['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises((KeyError, ValueError)):
        R.project(ctx, d, {})
