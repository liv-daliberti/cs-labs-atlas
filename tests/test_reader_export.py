"""tools/reader_export.py: licence normalisation, the arXiv-licence lookup, never quarantined or pending, the link fallback order."""
import gzip, hashlib, json, sqlite3, textwrap

import pytest

import atlas_paths as P
import reader_export as R

def pdf_bytes(title, body=('We measured the complete experimental response and compared it with a controlled baseline. '
                          'The result remained stable across repeated measurements, including the uncertainty reported '
                          'in this brief letter. The method and conditions are described here so that the measurement '
                          'can be reproduced independently.')):
    stream = (f'BT /F1 12 Tf 30 700 Td ({title}) Tj /F1 10 Tf 0 -30 Td '+
              ' '.join(f'({line}) Tj 0 -14 Td' for line in textwrap.wrap(body,70))+' ET').encode()
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>',
               b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    data=b'%PDF-1.4\n';offsets=[0]
    for i,obj in enumerate(objects,1):offsets.append(len(data));data+=f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n'
    start=len(data);data+=b'xref\n0 6\n0000000000 65535 f \n'+b''.join(f'{off:010d} 00000 n \n'.encode() for off in offsets[1:])
    return data+f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode()


def SHA(n):
    titles=['One','Two','Three','Four','Five','Six','Seven','Eight']
    return hashlib.sha256(pdf_bytes('Paper '+titles[n-1])).hexdigest() if 1 <= n <= 8 else f'{n:064x}'


@pytest.mark.parametrize('raw,want', [
    ('CC BY', 'cc-by'), ('cc_by', 'cc-by'), ('cc-by-4.0', 'cc-by'), ('CC-BY-NC-ND 4.0', 'cc-by-nc-nd'), ('cc by-sa', 'cc-by-sa'),
    ('https://creativecommons.org/licenses/by-nc/4.0/', 'cc-by-nc'), ('https://creativecommons.org/publicdomain/zero/1.0/', 'cc0'),
    ('CC0', 'cc0'), ('cc0-1.0', 'cc0'), ('Public Domain', 'public-domain'), ('publicdomain', 'public-domain'),
    ('http://arxiv.org/licenses/nonexclusive-distrib/1.0/', 'arxiv-nonexclusive'), ('other-oa', 'other-oa'), ('tdm', 'tdm'),
    ('cc-byncnd', 'cc-by-nc-nd'), ('CC BY-NC 3.0', 'cc-by-nc'), ('ccby', 'cc-by'), ('', None), (None, None), ('unknown', None)])
def test_normalise_license(raw, want):
    assert R.normalise_license(raw) == want


def test_local_hosting_preserves_licence_metadata_without_requiring_one():
    assert R.HOST == {'cc-by', 'cc-by-sa', 'cc-by-nc', 'cc-by-nc-sa', 'cc-by-nd', 'cc-by-nc-nd', 'cc0', 'public-domain'}
    for lic in ('other-oa', 'tdm', 'arxiv-nonexclusive', None, 'implied-oa'):
        assert R.decide((lic, 'asset') if lic else None, None, None)[0] == 'host'
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
    assert R.decide(None, '2222.2222', A)[0] == 'host' and R.decide(None, '1111.1111', A)[0] == 'host'


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
    (root / 'objects').mkdir()
    db = sqlite3.connect(root / 'catalog.sqlite')
    db.executescript('''create table works (id text primary key, title text, doi text, year integer, graph_json text not null default '{}', oa_json text,
        metadata_source text, status text not null default 'queued', file_path text, sha256 text, byte_count integer, pages integer, download_url text,
        downloaded_at text, identity_check text);
        create table assets (work_id text, kind text, url text, path text, sha256 text, bytes integer, version text, license text, metadata_source text,
        downloaded_at text, identity_check text, primary key (work_id, kind, url));
        create table candidates (work_id text, url text, landing_url text, license text, version text, metadata_source text, primary key (work_id, url));
        create table attempts (id integer primary key, work_id text, url text, observed_at text, status text, detail text);''')
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
        # Licence/identity fixtures now contain actual parseable PDFs, so the
        # production asset-quality path runs rather than a metadata-only bypass.
        data=pdf_bytes(title)
        (root/'objects'/f'{sha}.pdf').write_bytes(data)
        db.execute('insert into works (id, title, doi, year, status, file_path, sha256, byte_count, download_url, identity_check) values (?,?,?,?,?,?,?,?,?,?)',
                   (wid, title, doi, 2020, st, f'objects/{sha}.pdf', sha, len(data), dl, ic))
        db.execute('insert into assets values (?,?,?,?,?,?,?,?,?,?,?)', (wid, 'pdf', dl, f'objects/{sha}.pdf', sha, len(data), 'publishedVersion', lic, None, None, ic))
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
    recs, stats, chk, _ = R.school_rows('mit', papers, A)
    by = {r['key']: r for r in recs}
    assert set(by) == {'w_ccby', 'w_arx_lic', 'w_arx_def', 'w_repo', 'w_none', 'w_cand'}      # pending and quarantined are not readable
    assert 'w_pending' not in by and 'w_quar' not in by
    assert (by['w_ccby']['decision'], by['w_ccby']['license'], by['w_ccby']['license_basis']) == ('host', 'cc-by', 'asset')
    assert by['w_ccby']['path'] == f'objects/{SHA(1)}.pdf' and by['w_ccby']['readable'] is True
    assert (by['w_arx_lic']['decision'], by['w_arx_lic']['license_basis']) == ('host', 'arxiv_openalex')
    assert (by['w_arx_def']['decision'], by['w_arx_def']['license'], by['w_arx_def']['source_url']) == ('host', 'arxiv-nonexclusive', 'https://arxiv.org/abs/2222.2222')
    assert by['w_arx_def']['path'] == f'objects/{SHA(3)}.pdf' and by['w_arx_def']['readable'] is True              # linked papers are readable too
    assert (by['w_repo']['decision'], by['w_repo']['source_kind']) == ('host', 'repository')    # repository landing page over the bare PDF url
    assert by['w_repo']['source_url'] == 'https://dspace.mit.edu/handle/1721/6'
    assert (by['w_none']['decision'], by['w_none']['license'], by['w_none']['source_url'], by['w_none']['source_kind']) == ('host', None, 'https://pub.example.com/seven.pdf', 'publisher')
    assert (by['w_cand']['decision'], by['w_cand']['license'], by['w_cand']['license_basis']) == ('host', 'cc-by-nc', 'candidate')
    assert stats['host'] == 6 and stats['link'] == 0 and stats['not_readable'] == 2 and stats['lab_papers'] == 8


def test_hosted_not_permitted_is_strict(tmp_path, monkeypatch):
    papers = make_store(tmp_path, monkeypatch)
    hosted = frozenset([SHA(1), SHA(3), SHA(5), SHA(99)])
    A = R.ArxivLicenses()
    A.add_body(dict(locations=[dict(id='pmh:oai:arXiv.org:2222.2222', landing_page_url='https://arxiv.org/abs/2222.2222', license=None)]))
    _, _, chk, _ = R.school_rows('mit', papers, A, hosted)
    files = {s: dict(bytes=1000, path=f'papers/{s}.pdf') for s in hosted}
    rows = {r[0]: r for r in R.hosted_not_permitted(files, {'mit': chk})}
    assert SHA(1) not in rows                                       # cc-by: permitted
    assert SHA(3) not in rows
    assert rows[SHA(5)][3] == 'no_confirmed_copy'                  # quarantined
    assert rows[SHA(99)][3] == 'not_in_stores'


def test_full_text_xml_copy_takes_its_file_from_the_asset_row(tmp_path):
    w = dict(id='w', doi='10.1/x', title='t', year=2020, status='fulltext_xml', file_path=None, sha256=None, byte_count=None,
             download_url='https://europepmc.org/x', identity_check=None)
    a = [dict(work_id='w', kind='xml', url='https://europepmc.org/x', path='objects/' + SHA(9) + '.xml', sha256=SHA(9), bytes=50, version='publishedVersion',
              license='cc-by', identity_check=None)]
    raw=('<article><body><p>'+('Complete experimental results and reproducible methods. '*6)+'</p></body></article>').encode()
    h=hashlib.sha256(raw).hexdigest();(tmp_path/'objects').mkdir();(tmp_path/'objects'/(h+'.xml')).write_bytes(raw)
    a[0].update(path='objects/'+h+'.xml',sha256=h,bytes=len(raw))
    cp = R.copy_for('w', w, a, [], R.ArxivLicenses(),store=tmp_path)
    assert (cp['format'], cp['decision'], cp['sha256'], cp['bytes']) == ('xml', 'host', h, len(raw))
    w['status'] = 'quarantined_robots_ai'
    assert R.copy_for('w', w, a, [], R.ArxivLicenses(),store=tmp_path) is None


def test_verified_local_copy_does_not_require_a_source_link(tmp_path, monkeypatch):
    papers = make_store(tmp_path, monkeypatch)
    db = sqlite3.connect(tmp_path / 'stores' / 'mit' / 'catalog.sqlite')
    db.execute("update works set doi=null, download_url='ftp://nowhere/x.pdf' where id='w_none'")
    db.execute("update assets set url='ftp://nowhere/x.pdf' where work_id='w_none'")
    db.commit()
    papers[6]['doi'] = None
    recs, stats, _, _ = R.school_rows('mit', papers, R.ArxivLicenses())
    assert 'w_none' in {r['key'] for r in recs} and stats['link_without_source_url'] == 0
    assert all(r['source_url'] or r['decision'] == 'host' for r in recs)


# ---- source links from candidate URLs (owner, 2026-11-01) ------------------------------------------------------------------------


import reader_links as RL


def test_norm_url_forms():
    assert RL.norm_url('https://arxiv.org/abs/2504.10745v2') == RL.norm_url('http://www.arxiv.org/pdf/2504.10745.pdf') == 'arxiv:2504.10745'
    assert RL.norm_url('https://doi.org/10.1234/ABC') == RL.norm_url('10.1234/abc') == 'doi:10.1234/abc'
    assert RL.norm_url('https://dspace.mit.edu/handle/1721.1/12345') == RL.norm_url('http://hdl.handle.net/1721.1/12345') == 'handle:1721.1/12345'
    assert RL.norm_url('https://www.Example.com/a/b.pdf/') == RL.norm_url('http://example.com/a/b') == 'example.com/a/b'
    assert RL.norm_url('ftp://x') is None


class FakeArxiv:
    def __init__(self, recs):
        self.recs = recs

    def lookup(self, ids):
        return {i: self.recs[i] for i in ids if i in self.recs}


PAPER = dict(key='k', doi=['10.1/x'], oa=['W1'], title='Learning Sparse Representations of Graph Data', first_author='lovelace')


def test_confirm_bases_in_order():
    urls = [('https://arxiv.org/pdf/1111.1111v3', False), ('https://repo.example.edu/handle/1/2', True)]
    no_arx = FakeArxiv({})
    same = FakeArxiv({'1111.1111': ('Learning Sparse Representations of Graphs', ['Smith'])})
    assert RL.confirm(PAPER, urls, {}, lambda d: '1111.1111v2', same) == ('arxiv_id_doi', ['https://arxiv.org/pdf/1111.1111v3'])
    assert RL.confirm(PAPER, urls, {}, lambda d: '1111.1111v2', no_arx)[0] is None                                        # the index lacks the id: not accepted
    wrong = FakeArxiv({'1111.1111': ('Transformer language models beyond a fixed length', ['Dai'])})
    assert RL.confirm(PAPER, urls, {}, lambda d: '1111.1111v2', wrong)[0] is None                                         # the mapping is contradicted by the arXiv title
    assert RL.confirm(PAPER, urls, {}, lambda d: '9999.9999', same) == (None, [])                                         # mapping names another arXiv id
    assert RL.confirm(PAPER, urls, {'W1': {'handle:1/2'}}, lambda d: None, no_arx) == ('openalex_location', ['https://repo.example.edu/handle/1/2'])
    assert RL.confirm(PAPER, urls, {'W2': {'handle:1/2'}}, lambda d: None, no_arx)[0] is None                           # another work's location
    meta = FakeArxiv({'1111.1111': ('Learning sparse representations of graph data', ['Lovelace', 'Babbage'])})
    assert RL.confirm(PAPER, urls, {}, lambda d: None, meta)[0] == 'arxiv_metadata'
    other_author = FakeArxiv({'1111.1111': ('Learning sparse representations of graph data', ['Babbage', 'Lovelace'])})
    assert RL.confirm(PAPER, urls, {}, lambda d: None, other_author)[0] is None                                          # first author must match
    other_title = FakeArxiv({'1111.1111': ('Quantum error correction with surface codes', ['Lovelace'])})
    assert RL.confirm(PAPER, urls, {}, lambda d: None, other_title)[0] is None
    deposit = dict(PAPER, doi=['10.5281/zenodo.123'])
    assert RL.confirm(deposit, urls, {}, lambda d: '1111.1111', same)[0] is None                                         # a deposit's DOI mapping is not the paper
    longer = FakeArxiv({'1111.1111': ('Learning sparse representations of graph data and many more unrelated additional words', ['Lovelace'])})
    assert RL.confirm(PAPER, urls, {}, lambda d: None, longer)[0] is None                                                # both ways 80%
    assert RL.confirm(PAPER, urls, {}, lambda d: None, no_arx, {('k', RL.norm_url(urls[1][0])): 'match'})[0] == 'landing_page_metadata'
    assert RL.confirm(PAPER, urls, {}, lambda d: None, no_arx, {('k', RL.norm_url(urls[1][0])): 'mismatch'})[0] is None


def test_candidate_links_in_school_rows(tmp_path, monkeypatch):
    papers = make_store(tmp_path, monkeypatch)
    db = sqlite3.connect(tmp_path / 'stores' / 'mit' / 'catalog.sqlite')
    for wid, title in (('w_q1', 'Alpha Beta Gamma Delta'), ('w_q2', 'Epsilon Zeta Eta Theta'), ('w_q3', 'Iota Kappa Lambda Omega'), ('w_q4', 'Sigma Tau Upsilon Phi')):
        db.execute("insert into works (id, title, doi, year, status) values (?,?,?,2020,'queued')", (wid, title, f'10.7/{wid}'))
    db.executemany('insert into candidates (work_id, url, landing_url) values (?,?,?)', [
        ('w_q1', 'https://arxiv.org/pdf/3333.3333', None), ('w_q2', 'https://repo.example.edu/files/2.pdf', 'https://repo.example.edu/handle/9/2'),
        ('w_q3', 'https://unknown.example.com/3', None), ('w_q4', 'https://arxiv.org/pdf/4444.4444', None)])
    db.execute("insert into attempts (work_id, url, status, detail) values ('w_q4', 'https://arxiv.org/pdf/4444.4444', 'identity_mismatch', 'x')")
    db.commit()
    extra = [dict(work=w, oa=f'https://openalex.org/W{i}', doi=f'10.7/{w}', title=t, year=2020, atlasWorkId=f'atl:w:{i:012x}', editions=[], byline=['Ann Lovelace'])
             for i, (w, t) in enumerate([('w_q1', 'Alpha Beta Gamma Delta'), ('w_q2', 'Epsilon Zeta Eta Theta'), ('w_q3', 'Iota Kappa Lambda Omega'), ('w_q4', 'Sigma Tau Upsilon Phi')], 100)]
    A = R.ArxivLicenses()
    A.locs['W101'] = {'handle:9/2'}
    lt = R.LinkTools.__new__(R.LinkTools)
    lt.IR = type('IR', (), {'mapped_arxiv': staticmethod(lambda doi, s2, oa, oa_id=None: '3333.3333' if doi == '10.7/w_q1' else ('4444.4444' if doi == '10.7/w_q4' else None))})
    lt.locs, lt.s2, lt.oa, lt.arx_index, lt.verdicts = A.locs, None, None, FakeArxiv({'3333.3333': ('Alpha Beta Gamma Delta', ['Lovelace'])}), {}
    recs, stats, _, reqs = R.school_rows('mit', papers + extra, A, links=lt)
    by = {r['key']: r for r in recs}
    assert by['w_q1']['link_basis'] == 'arxiv_id_doi' and by['w_q1']['source_url'] == 'https://arxiv.org/abs/3333.3333' and by['w_q1']['stored_copy'] is False
    assert by['w_q1']['sha256'] is None and by['w_q1']['path'] is None and by['w_q1']['decision'] == 'link' and by['w_q1']['readable'] is True
    assert by['w_q2']['link_basis'] == 'openalex_location' and by['w_q2']['source_url'] == 'https://repo.example.edu/handle/9/2' and by['w_q2']['source_kind'] == 'repository'
    assert 'w_q3' not in by and 'w_q4' not in by                                  # unconfirmed; and a candidate the catalog found to be another document
    assert [r[2] for r in reqs] == ['w_q3'] and reqs[0][0] == 'unknown.example.com'
    assert stats['newly_readable_from_candidates'] == 2 and stats['link_basis:arxiv_id_doi'] == 1 and stats['link_basis:openalex_location'] == 1
    assert all(r['decision'] == 'link' for r in recs if not r['stored_copy'])      # never hosted


def test_site_sync_lists_what_to_unpublish_and_upload(tmp_path, monkeypatch):
    papers = make_store(tmp_path, monkeypatch)
    A = R.ArxivLicenses()
    A.add_body(dict(id='https://openalex.org/W1', locations=[dict(id='pmh:oai:arXiv.org:2222.2222', landing_page_url='https://arxiv.org/abs/2222.2222', license=None),
                                                           dict(id='pmh:oai:arXiv.org:1111.1111', landing_page_url='https://arxiv.org/abs/1111.1111', license='cc-by')]))
    site = {R_sha: dict(bytes=1000, path=f'papers/{R_sha}.pdf') for R_sha in (SHA(1), SHA(3), SHA(5), SHA(77))}   # cc-by (kept), arXiv non-exclusive, quarantined, unknown
    recs, stats, chk, reqs = R.school_rows('mit', papers, A, frozenset(site))
    notp = R.hosted_not_permitted(site, {'mit': chk})
    out = tmp_path / 'o'
    summ = R.write_outputs({'mit': recs}, {'mit': stats}, notp, out, '2026-11-01T00:00:00Z', None, requests={'mit': reqs}, site_files=site)
    rows = {l.split('\t')[0]: l.split('\t') for l in (out / 'unpublish.tsv').read_text().splitlines()[1:]}
    assert SHA(1) not in rows and SHA(3) not in rows and rows[SHA(5)][3] == 'no_confirmed_copy' and rows[SHA(77)][3] == 'not_in_stores'
    up = {l.split('\t')[0] for l in (out / 'upload.tsv').read_text().splitlines()[1:]}
    assert SHA(1) not in up and SHA(2) in up                       # w_arx_lic's cc-by arXiv copy is to be added, the kept one is already there
    assert summ['site_sync']['unpublish'] == 2 and summ['site_sync']['keep'] == 2


def test_compact_site_admission_preserves_xml_and_rejects_disagreement(tmp_path):
    index = tmp_path / 'local-papers.json'
    objects = tmp_path / 'reader-objects.json'
    sha = 'a' * 64
    index.write_text(json.dumps(dict(schema=2, release='reader-one', records=[], works={})))
    objects.write_text(json.dumps(dict(release='reader-one', files={sha: 512}, formats={sha: 'xml'})))
    assert R.site_admission(index) == {sha: dict(bytes=512, path=f'papers/{sha}.xml')}
    index.write_text(json.dumps(dict(release='reader-one', files={sha: dict(bytes=512, path=f'papers/{sha}.pdf')})))
    with pytest.raises(ValueError, match='format mismatch'):
        R.site_admission(index, objects)
    objects.write_text(json.dumps(dict(release='reader-two', files={sha: 512})))
    with pytest.raises(ValueError, match='release mismatch'):
        R.site_admission(index, objects)
    objects.unlink()
    index.write_text(json.dumps(dict(schema=2, release='reader-one', records=[], works={})))
    with pytest.raises(ValueError, match='requires reader-objects'):
        R.site_admission(index)


def test_independent_library_survives_formal_sync_without_lab_assignment(tmp_path):
    sha = 'b' * 64
    snapshot = tmp_path / 'snapshot'
    (snapshot / 'evidence').mkdir(parents=True)
    (snapshot / 'reader').mkdir()
    document = dict(id='local:' + sha, title='Held paper', copy=dict(sha256=sha, bytes=512, format='xml'))
    payload = gzip.compress(json.dumps(dict(schema=1, documents=[document], counts=dict(documents=1, bytes=512))).encode())
    (snapshot / 'evidence/local-library.json.gz').write_bytes(payload)
    (snapshot / 'local-papers.json').write_text(json.dumps(dict(release='reviewed-library', files={sha: dict(bytes=512, format='xml', path=f'papers/{sha}.xml')})))
    (snapshot / 'reader/hosted-files.tsv').write_text(f'sha256\tbytes\tschool\tpath\n{sha}\t512\tsourcearchive\tobjects/{sha}.xml\n')
    manifest = dict(kind='reader-admission-snapshot', release='reviewed-library', files={
        name: dict(bytes=(snapshot / name).stat().st_size, sha256=hashlib.sha256((snapshot / name).read_bytes()).hexdigest())
        for name in ['evidence/local-library.json.gz', 'local-papers.json', 'reader/hosted-files.tsv']})
    (snapshot / 'MANIFEST.json').write_text(json.dumps(manifest))
    digest = hashlib.sha256((snapshot / 'MANIFEST.json').read_bytes()).hexdigest()
    library = R.independent_library(snapshot, digest)
    out = tmp_path / 'out'
    summary = R.write_outputs({}, {}, [(sha, 512, f'papers/{sha}.xml', 'not_in_stores', '', '', '', '')],
        out, '2026-11-17', None, site_files={sha: dict(bytes=512, path=f'papers/{sha}.xml')}, library=library)
    assert summary['site_sync']['unpublish'] == 0
    assert summary['currently_hosted_not_permitted'] == 0
    assert summary['hosted_files'] == 1 and summary['schools'] == {}
    assert (out / 'local-library.json.gz').read_bytes() == payload
    assert f'{sha}\t512\tsourcearchive\tobjects/{sha}.xml' in (out / 'hosted-files.tsv').read_text()
    assert json.loads((out / 'library-admission.json').read_text())['no_lab_assignment'] is True
    (snapshot / 'reader/hosted-files.tsv').write_text('changed')
    with pytest.raises(ValueError, match='artifact changed'):
        R.independent_library(snapshot, digest)
    with pytest.raises(ValueError, match='manifest checksum'):
        R.independent_library(snapshot, 'wrong')


def test_public_library_cannot_be_silently_dropped_or_bound_to_another_reader(tmp_path):
    data = tmp_path / 'atlas/data'
    data.mkdir(parents=True)
    index = data / 'local-papers.json'
    index.write_text(json.dumps(dict(release='reader-one')))
    (data / 'local-library.json.gz').write_bytes(b'held metadata')
    with pytest.raises(ValueError, match='explicit reviewed admission'):
        R.library_for_site(index)
    (tmp_path / 'deployment').mkdir()
    (tmp_path / 'deployment/reader-publication.json').write_text(json.dumps(
        dict(reader='reader-two', snapshot='outputs/snapshot', manifestSha256='a' * 64)))
    with pytest.raises(ValueError, match='differs from reader index'):
        R.library_for_site(index)
