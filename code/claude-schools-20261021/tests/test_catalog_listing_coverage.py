import hashlib
import json
import sqlite3
import zlib

import pytest

import listing_rows as R


def test_catalog_listing_coverage_checks_original_and_role_lines(tmp_path, monkeypatch):
    monkeypatch.setattr(R.P, 'HIERARCHY', tmp_path / 'hierarchy')  # route-ok: listing_rows currently reads this legacy root
    monkeypatch.setattr(R.P, 'LISTINGS', tmp_path / 'listings')
    reviewed = tmp_path / 'hierarchy' / 'sample' / 'reviewed'  # route-ok: match listing_rows legacy root
    raw_dir = tmp_path / 'listings' / 'sample' / 'raw'  # route-ok: match listing_rows legacy root
    reviewed.mkdir(parents=True)
    raw_dir.mkdir(parents=True)
    body = b'<h1>Computer Science</h1><p>Professors: Ada Example</p><p>Assistant Professors: Grace Example</p>'
    sha = hashlib.sha256(body).hexdigest()
    url = 'https://example.edu/2020/catalog.html'
    record = dict(start_year=2020, source_url=url, raw_sha256=sha,
                  role_lines=['Professors: Ada Example', 'Assistant Professors: Grace Example'])
    manifest = reviewed / 'catalog-listing-sources.json'
    manifest.write_text(json.dumps(dict(school='sample', records=[record])))
    db = raw_dir / 'catalog-captures.sqlite'
    with sqlite3.connect(db) as c:
        c.execute('create table captures(year integer,url text,status integer,sha256 text,raw_zlib blob,content_type text)')
        c.execute('insert into captures values(?,?,?,?,?,?)',
                  (2020, url, 200, sha, zlib.compress(body), 'text/html'))
    assert R.catalog_listing_coverage('sample') == [('CS', 2020, 'official catalog 2020–2021', 'ok')]

    record['role_lines'][1] = 'Assistant Professors: Someone Else'
    manifest.write_text(json.dumps(dict(school='sample', records=[record])))
    with pytest.raises(ValueError, match='role line missing'):
        R.catalog_listing_coverage('sample')

    record['role_lines'][1] = 'Assistant Professors: Grace Example'
    record['raw_sha256'] = '0' * 64
    manifest.write_text(json.dumps(dict(school='sample', records=[record])))
    with pytest.raises(ValueError, match='metadata mismatch'):
        R.catalog_listing_coverage('sample')


def test_graduate_catalog_people_keep_year_and_exact_role_quote(tmp_path, monkeypatch):
    monkeypatch.setattr(R.P, 'HIERARCHY', tmp_path / 'hierarchy')  # route-ok: listing_rows currently reads this legacy root
    reviewed = tmp_path / 'hierarchy' / 'sample' / 'reviewed'  # route-ok: match listing_rows legacy root
    reviewed.mkdir(parents=True)
    lines = ['Professors: Ada Example; Grace Hopper;', 'Assistant Professors: Alan Example;']
    (reviewed / 'catalog-listing-sources.json').write_text(json.dumps(dict(school='sample', records=[
        dict(start_year=2023, source_url='https://example.edu/catalog.pdf', raw_sha256='a' * 64,
             source_type='official_VT_graduate_catalog', role_lines=lines)])))
    rows = R.catalog_person_rows('sample')
    assert [(r['name'], r['year'], r['rank']) for r in rows] == [
        ('Ada Example', 2023, 'ladder'), ('Grace Hopper', 2023, 'ladder'),
        ('Alan Example', 2023, 'ladder')]
    assert rows[1]['quote'] == lines[0] and rows[1]['observed'] == '2023'


def test_same_year_faculty_directory_match_requires_both_source_quotes(tmp_path, monkeypatch):
    monkeypatch.setattr(R.P, 'ROOT', tmp_path)
    monkeypatch.setattr(R.P, 'HIERARCHY', tmp_path / 'hierarchy')  # route-ok: listing_rows currently reads this legacy root
    reviewed = tmp_path / 'hierarchy/vt/reviewed'
    raw_dir = tmp_path / 'listings/vt/raw'
    reviewed.mkdir(parents=True)
    raw_dir.mkdir(parents=True)
    catalog_line = 'Professors: C. Barrett'
    catalog_url = 'https://example.edu/2017/cs.html'
    catalog_sha = 'a' * 64
    directory_url = 'https://example.edu/2017/faculty.html'
    entry = 'BARRETT, Christopher L. (2004), Prof. of Computer Science.'
    directory_body = f'<p>{entry}</p>'.encode()
    directory_sha = hashlib.sha256(directory_body).hexdigest()
    (reviewed / 'catalog-listing-sources.json').write_text(json.dumps({'records': [
        dict(start_year=2017, source_url=catalog_url, raw_sha256=catalog_sha, role_lines=[catalog_line])]}))
    match = dict(year=2017, printed='C. Barrett', role='Professors', catalog_source_url=catalog_url,
                 catalog_source_sha256=catalog_sha, catalog_line=catalog_line, status='exact_year_unique',
                 admitted_to_draft_census=True, same_year_full_name_entries=[
                     dict(name='Christopher L. Barrett', url=directory_url, raw_sha256=directory_sha, quote=entry)])
    manifest = reviewed / 'faculty-directory-identity-matches.json'
    manifest.write_text(json.dumps(dict(school='vt', original_capture_store='listings/vt/raw/faculty-directory-captures.sqlite',
                                        by_status={'exact_year_unique': 1}, records=[match])))
    with sqlite3.connect(raw_dir / 'faculty-directory-captures.sqlite') as c:
        c.execute('create table captures(year integer,url text,sha256 text,body_zlib blob)')
        c.execute('insert into captures values(?,?,?,?)',
                  (2017, directory_url, directory_sha, zlib.compress(directory_body)))
    rows = R.vt_paired_directory_rows('vt')
    assert len(rows) == 1
    assert rows[0]['name'] == 'Christopher L. Barrett'
    assert rows[0]['identity_basis']['quote'] == entry
    match['catalog_line'] = 'Professors: C. Someone Else'
    manifest.write_text(json.dumps(dict(school='vt', original_capture_store='listings/vt/raw/faculty-directory-captures.sqlite',
                                        by_status={'exact_year_unique': 1}, records=[match])))
    with pytest.raises(AssertionError):
        R.vt_paired_directory_rows('vt')
