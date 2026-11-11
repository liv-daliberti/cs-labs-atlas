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
