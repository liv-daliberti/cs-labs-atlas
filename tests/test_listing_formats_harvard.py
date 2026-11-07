"""Harvard SEAS people directory (Drupal 10) and its `?page=%2C<n>` pager (excerpts of a real page)."""
import listing_formats as F

SEAS = """<h2 class="node-title teaching-area-dark person__detailed-name">
<a href="/person/david-alvarez-melis"><span class="person__name person__name--person-directory">David Alvarez-Melis</span></a></h2>
<div class="person-directory__primary-title"><div class="person__primary-title person__primary-title--person-directory field field-name-field-person-primary-title">
<div class="field-items"><div class="field-item">Assistant Professor of Computer Science</div></div></div></div>
<h2 class="node-title person__detailed-name"><a href="/person/joanna-aizenberg"><span class="person__name person__name--person-directory">Joanna Aizenberg</span></a></h2>
<div class="person__primary-title"><div class="field-items"><div class="field-item">Professor of Materials Science &amp; Chemistry</div></div></div>
<nav class="pager"><a href="?page=%2C1">2</a><a href="?page=%2C4">last</a></nav>"""


def test_seas_directory():
    name, rows = F.parse(SEAS)
    assert name == 'seas_directory' and [r['name_listed'] for r in rows] == ['David Alvarez-Melis', 'Joanna Aizenberg']
    assert rows[0]['titles'] == ['Assistant Professor of Computer Science']
    assert rows[1]['titles'] == ['Professor of Materials Science & Chemistry']


def test_seas_pager():
    assert F.is_paged(SEAS)
    assert sorted(F.page_links(SEAS, 'https://seas.harvard.edu/faculty')) == [1, 2, 3, 4]
    assert F.page_links(SEAS, 'https://seas.harvard.edu/faculty')[3] == 'https://seas.harvard.edu/faculty?page=%2C3'


# Excerpt of the saved 2020-era faculty page (raw sha256
# 50e6c59497b54687ecd554911a3b6087f8594fc3125e872ea17ec733a4cd2dd0).
# The original probe URL was not an exact timestamp; this fixture proves the
# markup era only, and must not supply a dated appointment or listing year.
SEAS_WRAPPED = '''<h2 class="node-title teaching-area-dark person__detailed-name">
<a href="/person/frederick-abernathy"><span class="field-wrapper person__name person__name--person-directory">Frederick H. Abernathy</span></a></h2>
<div class="person-directory__primary-title">
<div class="field-wrapper person__primary-title person__primary-title--person-directory field field-node--field-person-primary-title">
<div class="field-items"><div class="field-item">Gordon McKay Professor of Mechanical Engineering and Abbott and James Lawrence Professor of Engineering, Emeritus</div></div></div></div>
<h2 class="node-title person__detailed-name"><a href="/person/example-no-title"><span class="field-wrapper person__name person__name--person-directory">Example No Title</span></a></h2>
<nav class="pager"><a href="?search=&amp;sort_by=field_last_name&amp;page=%2C8">Last</a></nav>'''


def test_seas_wrapped_field_classes():
    fmt, rows = F.parse(SEAS_WRAPPED)
    assert fmt == 'seas_directory'
    assert [r['name_listed'] for r in rows] == ['Frederick H. Abernathy', 'Example No Title']
    assert rows[0]['titles'][0].endswith('Engineering, Emeritus')
    assert rows[0]['homepage'] == '/person/frederick-abernathy'
    assert rows[1]['titles'] == []


def test_seas_old_pager_keeps_filter_and_sort():
    pages = F.page_links(SEAS_WRAPPED, 'https://seas.harvard.edu/faculty')
    assert F.is_paged(SEAS_WRAPPED)
    assert len(pages) == 8
    assert pages[1] == 'https://seas.harvard.edu/faculty?search=&sort_by=field_last_name&page=%2C1'


def test_school_wide_seas_title_filter_does_not_change_capture_parsing(tmp_path, monkeypatch):
    import importlib.util
    import json
    from pathlib import Path
    import sqlite3
    import zlib

    spec = importlib.util.spec_from_file_location('harvard_listing_rows', Path(F.__file__).with_name('listing_rows.py'))
    R = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(R)
    slot = dict(slot='SEAS faculty', kind='main', format='seas_directory', title_filter=r'\bComputer Science\b')
    cfg = dict(departments=[dict(code='CS', title_match='Computer Science', listings=[slot])])
    db = tmp_path / 'captures.sqlite'
    c = sqlite3.connect(db)
    c.execute('create table plan(slot, dept, year, half, capture_url, status, reason)')
    c.execute('create table captures(capture_url, raw_zlib, sha256, text, wayback_timestamp)')
    cap = 'https://web.archive.org/web/20261106120000id_/https://seas.harvard.edu/faculty'
    c.execute('insert into plan values(?,?,?,?,?,?,?)', ('SEAS faculty', 'CS', 2026, 'H2', cap, 'ok', None))
    c.execute('insert into captures values(?,?,?,?,?)', (cap, zlib.compress(SEAS.encode()), 'fixture-sha', F.clean(SEAS), '20261106120000'))
    c.commit()
    c.close()
    monkeypatch.setattr(R.S, 'get', lambda key: cfg)
    monkeypatch.setattr(R.S, 'listing_slots', lambda key: [slot])
    route = lambda name, key: db if name == 'listings-captures.sqlite' else tmp_path / name
    monkeypatch.setattr(R.P, 'data', route)
    monkeypatch.setattr(R.P, 'data_w', route)
    R.main('harvard')
    rows = json.loads((tmp_path / 'rows.json').read_text())
    assert [r['name'] for r in rows] == ['David Alvarez-Melis']
    assert rows[0]['rank'] == 'ladder'
    assert len(F.parse(SEAS)[1]) == 2  # usability/pagination still sees all people
    del slot['title_filter']
    R.main('harvard')
    assert len(json.loads((tmp_path / 'rows.json').read_text())) == 2
