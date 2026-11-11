import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import listing_formats as F


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
