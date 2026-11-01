"""tools/reader_export.py: licence normalisation, the arXiv-licence lookup, never quarantined or pending, the link fallback order."""
import sqlite3

import pytest

import atlas_paths as P
import reader_export as R

SHA = lambda n: f'{n:064x}'   # noqa: E731


@pytest.mark.parametrize('raw,want', [
    ('CC BY', 'cc-by'), ('cc_by', 'cc-by'), ('cc-by-4.0', 'cc-by'), ('CC-BY-NC-ND 4.0', 'cc-by-nc-nd'), ('cc by-sa', 'cc-by-sa'),
    ('https://creativecommons.org/licenses/by-nc/4.0/', 'cc-by-nc'), ('https://creativecommons.org/publicdomain/zero/1.0/', 'cc0'),
    ('CC0', 'cc0'), ('cc0-1.0', 'cc0'), ('Public Domain', 'public-domain'), ('publicdomain', 'public-domain'),
    ('http://arxiv.org/licenses/nonexclusive-distrib/1.0/', 'arxiv-nonexclusive'), ('other-oa', 'other-oa'), ('tdm', 'tdm'),
    ('cc-byncnd', 'cc-by-nc-nd'), ('CC BY-NC 3.0', 'cc-by-nc'), ('ccby', 'cc-by'), ('', None), (None, None), ('unknown', None)])
def test_normalise_license(raw, want):
    assert R.normalise_license(raw) == want


def test_host_set_is_exactly_the_redistributable_licences():
    assert R.HOST == {'cc-by', 'cc-by-sa', 'cc-by-nc', 'cc-by-nc-sa', 'cc-by-nd', 'cc-by-nc-nd', 'cc0', 'public-domain'}
    for lic in ('other-oa', 'tdm', 'arxiv-nonexclusive', None, 'implied-oa'):
        assert R.decide((lic, 'asset') if lic else None, None, None)[0] == 'link'
    assert R.decide(('CC BY', 'asset'), None, None) == ('host', 'cc-by', 'asset')


def test_arxiv_ids():
    assert R.arxiv_id_of('https://arxiv.org/abs/2504.10745v2') == '2504.10745'
    assert R.arxiv_id_of('https://storage.googleapis.com/arxiv-dataset/arxiv/arxiv/pdf/1708/1708.03044v1.pdf') == '1708.03044'
    assert R.arxiv_id_of('10.48550/arxiv.1907.00837') == '1907.00837'
    assert R.arxiv_id_of('https://arxiv.org/pdf/cs/0501001') == 'cs/0501001'
    assert R.arxiv_id_of('https://example.org/x.pdf', None) is None


def test_arxiv_licence_lookup_from_local_openalex_bodies():
    A = R.ArxivLicenses()
    loc = lambda aid, lic: dict(id=f'pmh:oai:arXiv.org:{aid}', landing_page_url=f'https://arxiv.org/abs/{aid}', license=lic)   # noqa: E731
    A.add_body(dict(locations=[loc('1111.1111', 'cc-by'), dict(id='doi:10.1/x', license=None)]))
    A.add_body(dict(locations=[loc('2222.2222', None)]))
    assert A.get('1111.1111') == ('cc-by', 'arxiv_openalex')
    assert A.get('2222.2222') == ('arxiv-nonexclusive', 'arxiv_default')    # seen with no licence = arXiv's non-exclusive licence
    assert A.get('3333.3333') == (None, 'arxiv_unknown')                    # not in any local record: unknown, so LINK
    assert R.decide(None, '2222.2222', A)[0] == 'link' and R.decide(None, '1111.1111', A)[0] == 'host'


def test_source_link_fallback_order():
    urls = [('https://publisher.example.com/article/1', True), ('https://dspace.mit.edu/handle/1721/1', True), ('https://arxiv.org/pdf/1111.1111', False)]
    assert R.pick_source('10.1/x', '1111.1111', urls) == ('https://arxiv.org/abs/1111.1111', 'arxiv')       # arXiv first
    assert R.pick_source('10.1/x', None, urls) == ('https://dspace.mit.edu/handle/1721/1', 'repository')    # then a repository landing page
    assert R.pick_source('10.1/x', None, urls[:1]) == ('https://publisher.example.com/article/1', 'publisher')
    assert R.pick_source('https://doi.org/10.1/x', None, [(None, False)]) == ('https://doi.org/10.1/x', 'doi')
    assert R.pick_source(None, None, []) == (None, None)


def make_store(tmp_path, monkeypatch):
    root = tmp_path / 'stores' / 'mit'
    root.mkdir(parents=True)
    db = sqlite3.connect(root / 'catalog.sqlite')
    db.executescript('''create table works (id text primary key, title text, doi text, year integer, graph_json text not null default '{}', oa_json text,
        metadata_source text, status text not null default 'queued', file_path text, sha256 text, byte_count integer, pages integer, download_url text,
        downloaded_at text, identity_check text);
        create table assets (work_id text, kind text, url text, path text, sha256 text, bytes integer, version text, license text, metadata_source text,
        downloaded_at text, identity_check text, primary key (work_id, kind, url));
        create table candidates (work_id text, url text, landing_url text, license text, version text, metadata_source text, primary key (work_id, url));''')
    rows = [  # id, title, doi, status, sha, download_url, identity_check, asset license, candidate (url, landing, license)
        ('w_ccby', 'Paper One', '10.1/one', 'downloaded', SHA(1), 'https://pub.example.com/one.pdf', 'title_in_first_three_pages', 'CC BY', None),
        ('w_arx_lic', 'Paper Two', '10.1/two', 'downloaded', SHA(2), 'https://arxiv.org/pdf/1111.1111', 'title_in_first_three_pages', None, None),
        ('w_arx_def', 'Paper Three', '10.1/three', 'downloaded', SHA(3), 'https://arxiv.org/pdf/2222.2222', 'title_in_first_three_pages', None, None),
        ('w_pending', 'Paper Four', '10.1/four', 'downloaded', SHA(4), 'https://pub.example.com/four.pdf', R.PENDING, 'CC BY', None),
        ('w_quar', 'Paper Five', '10.1/five', 'quarantined_robots_ai', SHA(5), 'https://pub.example.com/five.pdf', 'title_in_first_three_pages', 'CC BY', None),
        ('w_repo', 'Paper Six', '10.1/six', 'downloaded', SHA(6), 'https://pub.example.com/six.pdf', 'title_in_first_three_pages', 'other-oa',
         ('https://pub.example.com/six.pdf', 'https://dspace.mit.edu/handle/1721/6', 'other-oa')),
        ('w_none', 'Paper Seven', '10.1/seven', 'downloaded', SHA(7), 'https://pub.example.com/seven.pdf', 'title_in_first_three_pages', None, None),
        ('w_cand', 'Paper Eight', '10.1/eight', 'downloaded', SHA(8), 'https://pub.example.com/eight.pdf', 'title_in_first_three_pages', None,
         ('https://pub.example.com/eight.pdf', None, 'cc-by-nc')),
    ]
    for wid, title, doi, st, sha, dl, ic, lic, cand in rows:
        db.execute('insert into works (id, title, doi, year, status, file_path, sha256, byte_count, download_url, identity_check) values (?,?,?,?,?,?,?,?,?,?)',
                   (wid, title, doi, 2020, st, f'objects/{sha}.pdf', sha, 1000, dl, ic))
        db.execute('insert into assets values (?,?,?,?,?,?,?,?,?,?,?)', (wid, 'pdf', dl, f'objects/{sha}.pdf', sha, 1000, 'publishedVersion', lic, None, None, ic))
        if cand:
            db.execute('insert into candidates values (?,?,?,?,?,?)', (wid, cand[0], cand[1], cand[2], None, None))
    db.commit()
    monkeypatch.setattr(P, 'STORES', tmp_path / 'stores')
    papers = [dict(work=f'p_{i}', oa=f'https://openalex.org/W{i}', doi=r[2], title=r[1], year=2020, atlasWorkId=f'atl:w:{i:012x}', editions=[], arxiv=None)
              for i, r in enumerate(rows)]
    for p, r in zip(papers, rows):
        p['work'] = r[0]
    return papers


def test_school_rows_decisions_and_exclusions(tmp_path, monkeypatch):
    papers = make_store(tmp_path, monkeypatch)
    A = R.ArxivLicenses()
    A.add_body(dict(locations=[dict(id='pmh:oai:arXiv.org:1111.1111', landing_page_url='https://arxiv.org/abs/1111.1111', license='cc-by'),
                               dict(id='pmh:oai:arXiv.org:2222.2222', landing_page_url='https://arxiv.org/abs/2222.2222', license=None)]))
    recs, stats, chk = R.school_rows('mit', papers, A)
    by = {r['key']: r for r in recs}
    assert set(by) == {'w_ccby', 'w_arx_lic', 'w_arx_def', 'w_repo', 'w_none', 'w_cand'}      # pending and quarantined are not readable
    assert 'w_pending' not in by and 'w_quar' not in by
    assert (by['w_ccby']['decision'], by['w_ccby']['license'], by['w_ccby']['license_basis']) == ('host', 'cc-by', 'asset')
    assert by['w_ccby']['path'] == f'objects/{SHA(1)}.pdf' and by['w_ccby']['readable'] is True
    assert (by['w_arx_lic']['decision'], by['w_arx_lic']['license_basis']) == ('host', 'arxiv_openalex')
    assert (by['w_arx_def']['decision'], by['w_arx_def']['license'], by['w_arx_def']['source_url']) == ('link', 'arxiv-nonexclusive', 'https://arxiv.org/abs/2222.2222')
    assert by['w_arx_def']['path'] is None and by['w_arx_def']['readable'] is True              # linked papers are readable too
    assert (by['w_repo']['decision'], by['w_repo']['source_kind']) == ('link', 'repository')    # repository landing page over the bare PDF url
    assert by['w_repo']['source_url'] == 'https://dspace.mit.edu/handle/1721/6'
    assert (by['w_none']['decision'], by['w_none']['license'], by['w_none']['source_url'], by['w_none']['source_kind']) == ('link', None, 'https://pub.example.com/seven.pdf', 'publisher')
    assert (by['w_cand']['decision'], by['w_cand']['license'], by['w_cand']['license_basis']) == ('host', 'cc-by-nc', 'candidate')
    assert stats['host'] == 3 and stats['link'] == 3 and stats['not_readable'] == 2 and stats['lab_papers'] == 8


def test_hosted_not_permitted_is_strict(tmp_path, monkeypatch):
    papers = make_store(tmp_path, monkeypatch)
    hosted = frozenset([SHA(1), SHA(3), SHA(5), SHA(99)])
    A = R.ArxivLicenses()
    A.add_body(dict(locations=[dict(id='pmh:oai:arXiv.org:2222.2222', landing_page_url='https://arxiv.org/abs/2222.2222', license=None)]))
    _, _, chk = R.school_rows('mit', papers, A, hosted)
    files = {s: dict(bytes=1000, path=f'papers/{s}.pdf') for s in hosted}
    rows = {r[0]: r for r in R.hosted_not_permitted(files, {'mit': chk})}
    assert SHA(1) not in rows                                       # cc-by: permitted
    assert rows[SHA(3)][3] == 'license' and rows[SHA(3)][4] == 'arxiv-nonexclusive'
    assert rows[SHA(5)][3] == 'no_confirmed_copy'                  # quarantined
    assert rows[SHA(99)][3] == 'not_in_stores'


def test_full_text_xml_copy_takes_its_file_from_the_asset_row():
    w = dict(id='w', doi='10.1/x', title='t', year=2020, status='fulltext_xml', file_path=None, sha256=None, byte_count=None,
             download_url='https://europepmc.org/x', identity_check=None)
    a = [dict(work_id='w', kind='xml', url='https://europepmc.org/x', path='objects/' + SHA(9) + '.xml', sha256=SHA(9), bytes=50, version='publishedVersion',
              license='cc-by', identity_check=None)]
    cp = R.copy_for('w', w, a, [], R.ArxivLicenses())
    assert (cp['format'], cp['decision'], cp['sha256'], cp['bytes']) == ('xml', 'host', SHA(9), 50)
    w['status'] = 'quarantined_robots_ai'
    assert R.copy_for('w', w, a, [], R.ArxivLicenses()) is None


def test_link_without_a_source_url_is_not_readable(tmp_path, monkeypatch):
    papers = make_store(tmp_path, monkeypatch)
    db = sqlite3.connect(tmp_path / 'stores' / 'mit' / 'catalog.sqlite')
    db.execute("update works set doi=null, download_url='ftp://nowhere/x.pdf' where id='w_none'")
    db.execute("update assets set url='ftp://nowhere/x.pdf' where work_id='w_none'")
    db.commit()
    papers[6]['doi'] = None
    recs, stats, _ = R.school_rows('mit', papers, R.ArxivLicenses())
    assert 'w_none' not in {r['key'] for r in recs} and stats['link_without_source_url'] == 1
    assert all(r['source_url'] or r['decision'] == 'host' for r in recs)
