import hashlib
import json
import sqlite3
import zlib

import listing_formats as F
import listing_rows as R


def test_utaustin_people_cards_keep_source_titles_and_profile_links():
    html = '''<div class="views-row">
      <div class="views-field views-field-title"><span class="field-content">
        <a href="/people/faculty-researchers/scott-aaronson">Scott Aaronson</a>
      </span></div>
      <div class="views-field views-field-field-contact-faculty-title">
        <div class="field-content">Professor, David Bruton, Jr. Centennial Professorship in Computer Sciences #2</div>
      </div></div>
      <div class="views-row"><div class="views-field views-field-title">
        <a href="/people/staff/example">Staff Member</a></div>
        <div class="views-field views-field-field-contact-faculty-title">
        <div class="field-content">Coordinator</div></div></div>'''
    fmt, rows = F.parse(html, 'utaustin_cs_people')
    assert fmt == 'utaustin_cs_people'
    assert rows == [dict(name_listed='Scott Aaronson',
                         titles=['Professor, David Bruton, Jr. Centennial Professorship in Computer Sciences #2'],
                         homepage=None, division=None,
                         profile='/people/faculty-researchers/scott-aaronson')]


def test_utaustin_legacy_directory_preserves_rank_and_profile():
    html = '''<div class="views-row"><div class="views-field views-field-nothing">
      <span class="field-content"><span class="prof-name">Lorenzo Alvisi</span><br/>
      Professor<br/> GDC 6.510 <br/><a href="mailto:lorenzo@cs.utexas.edu">email</a><br/>
      <a href="/directory/lorenzo-alvisi">Profile</a> |
      <a href="http://www.cs.utexas.edu/~lorenzo/">Homepage</a></span>
      </div></div>'''
    fmt, rows = F.parse(html, 'utaustin_cs_faculty_legacy')
    assert fmt == 'utaustin_cs_faculty_legacy'
    assert rows == [dict(name_listed='Lorenzo Alvisi', titles=['Professor'],
                         homepage='http://www.cs.utexas.edu/~lorenzo/',
                         division=None, profile='/directory/lorenzo-alvisi')]


def test_utaustin_legacy_directory_handles_2016_and_2017_cards():
    html = '''<div class="views-row">
      <div class="views-field-view-user"><strong class="field-content">
        <a href="/directory/scott-aaronson">Scott Aaronson</a></strong></div>
      <div class="views-field-field-user-title"><div class="field-content">Professor</div></div>
      </div>
      <div class="views-row"><div class="views-field-nothing"><p>
        <strong><a href="/directory/chandrajit-bajaj">Chandrajit Bajaj</a></strong>
        <br/> Professor </p></div></div>'''
    rows = F.parse(html, 'utaustin_cs_faculty_legacy')[1]
    assert [(r['name_listed'], r['titles'], r['profile']) for r in rows] == [
        ('Scott Aaronson', ['Professor'], '/directory/scott-aaronson'),
        ('Chandrajit Bajaj', ['Professor'], '/directory/chandrajit-bajaj'),
    ]


def test_utaustin_people_parser_handles_archived_drupal_cards():
    html = '''<div class="node-facstaff-directory-page">
      <div class="field-name-title"><a href="/people/faculty-researchers/scott-aaronson">Scott Aaronson</a></div>
      <div class="field-name-field-contact-faculty-title"><div class="field-item">Professor</div></div>
      </div>
      <div class="faculty-and-researchers">
      <div class="views-field-title"><a href="/people/faculty-researchers/joydeep-biswas">Joydeep Biswas</a></div>
      <div class="views-field-field-contact-faculty-title"><div class="field-content">Associate Professor</div></div>
      </div>'''
    rows = F.parse(html, 'utaustin_cs_people')[1]
    assert [(r['name_listed'], r['titles']) for r in rows] == [
        ('Joydeep Biswas', ['Associate Professor']),
        ('Scott Aaronson', ['Professor']),
    ]


def test_utaustin_2018_catalog_checks_dated_cs_entries(tmp_path, monkeypatch):
    monkeypatch.setattr(R.P, 'HIERARCHY', tmp_path / 'hierarchy')  # route-ok: isolated listing_rows fixture root
    monkeypatch.setattr(R.P, 'LISTINGS', tmp_path / 'listings')  # route-ok: isolated listing_rows fixture root
    monkeypatch.setattr(R.S, 'get', lambda _key: {'census': {'rank_words': {}}})
    reviewed = tmp_path / 'hierarchy' / 'utaustin' / 'reviewed'  # route-ok: follows monkeypatched fixture root
    raw = tmp_path / 'listings' / 'utaustin' / 'raw'  # route-ok: follows monkeypatched fixture root
    reviewed.mkdir(parents=True)
    raw.mkdir(parents=True)
    body = b'''<p>The following faculty list represents those appointed in the 2018 spring semester.</p>
      <p class="faculty_entry"><span class="faculty_name">Ada Example</span>,
      <span class="faculty_title">Professor</span><span class="faculty_dept">Computer Science</span></p>
      <p class="faculty_entry"><span class="faculty_name">Grace Example</span>,
      <span class="faculty_dept">Computer Science</span></p>
      <p class="faculty_entry"><span class="faculty_name">Other Person</span>,
      <span class="faculty_title">Professor</span><span class="faculty_dept">Mathematics</span></p>'''
    sha = hashlib.sha256(body).hexdigest()
    entries = [('Ada Example', 'Professor'), ('Grace Example', '')]
    digest = hashlib.sha256('\n'.join('\t'.join(x) for x in sorted(entries)).encode()).hexdigest()
    url = 'https://catalog.example.edu/archive/2018-19/faculty/'
    record = dict(start_year=2018, academic_year='2018–2020', source_url=url,
                  raw_sha256=sha, source_type='official_UT_undergraduate_catalog',
                  cs_entry_count=2, cs_entries_sha256=digest)
    (reviewed / 'catalog-listing-sources.json').write_text(json.dumps(dict(school='utaustin', records=[record])))
    with sqlite3.connect(raw / 'catalog-captures.sqlite') as c:
        c.execute('create table captures(year integer,url text,status integer,sha256 text,raw_zlib blob,content_type text)')
        c.execute('insert into captures values(?,?,?,?,?,?)', (2018, url, 200, sha, zlib.compress(body), 'text/html'))
    assert R.catalog_listing_coverage('utaustin') == [('CS', 2018, 'official catalog spring 2018', 'ok')]
    rows = R.catalog_person_rows('utaustin')
    assert [r['name'] for r in rows] == ['Ada Example']
    assert rows[0]['observed'] == '2018 spring'
    record['cs_entry_count'] = 1
    (reviewed / 'catalog-listing-sources.json').write_text(json.dumps(dict(school='utaustin', records=[record])))
    try:
        R.catalog_listing_coverage('utaustin')
    except ValueError:
        pass
    else:
        raise AssertionError('altered roster count was accepted')
