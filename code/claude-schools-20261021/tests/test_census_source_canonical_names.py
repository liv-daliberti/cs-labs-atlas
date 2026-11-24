"""Reviewed historical headings join existing names without a global name alias."""
import copy
import hashlib
import json
import sqlite3
import zlib

from bs4 import BeautifulSoup
import pytest

import census_build as C
import listing_formats as L
from listing_rows import quote_of


@pytest.fixture
def source_review(tmp_path, monkeypatch):
    old_url = 'https://web.archive.org/web/20160101000000id_/https://university.example/faculty'
    new_url = 'https://web.archive.org/web/20260101000000id_/https://university.example/faculty'
    old = '''<table><tr><td><img src="person.jpg"></td><td>Srikanthan Thambipillai (Professor)<br>
      <a href="mailto:[email removed]">Email</a></td><td>Interests</td><td>Research</td></tr></table>'''
    profile = 'https://profiles.example/person/srikanthan'
    new = f'''<div class="img-card--academic"><h3 class="img-card__title"><a href="{profile}">Prof Thambipillai Srikanthan</a></h3>
      <p class="img-card__desc">Appointments: Professor, Computing</p></div>'''
    db = tmp_path / 'captures.sqlite'
    rows, evidence = [], []
    with sqlite3.connect(db) as c:
        c.execute('create table captures(capture_url text, http_status int, sha256 text, raw_zlib blob, text text)')
        for url, html, fmt, name in [(old_url, old, 'ntu_moss_faculty', 'Srikanthan Thambipillai'),
                                      (new_url, new, 'ntu_img_cards', 'Thambipillai Srikanthan')]:
            raw = html.encode(); sha = hashlib.sha256(raw).hexdigest()
            flat = ' '.join(BeautifulSoup(html, 'html.parser').get_text(' ', strip=True).split())
            c.execute('insert into captures values(?,?,?,?,?)', (url, 200, sha, zlib.compress(raw), flat))
            entry = L.parse(html, fmt)[1][0]
            quote = quote_of(flat, entry, html)
            rows.append(dict(name=name, name_listed=name, observed='2016' if fmt == 'ntu_moss_faculty' else '2026',
                             profile=entry.get('profile'), capture_url=url, sha256=sha, quote=quote, dblp=[], orcid=[]))
            evidence.append(dict(url=url, sha256=sha, format=fmt, name_listed=name, profile=entry.get('profile'), quote=quote))
    doc = dict(school='ntu', rows=[], source_names=[dict(canonical_name='Thambipillai Srikanthan', evidence=evidence)])
    path = tmp_path / 'aliases.json'; path.write_text(json.dumps(doc))
    monkeypatch.setattr(C.P, 'data', lambda name, key=None: path if name == 'census-name-aliases.json' else db)
    return rows, doc, path, db


def test_profileless_history_joins_only_reviewed_source_rows(source_review):
    rows, _, _, _ = source_review
    original = copy.deepcopy(rows)
    mapped = C.reviewed_profile_names('ntu', rows)
    assert rows == original
    groups = C.merge_people(mapped)
    assert len(groups) == 1 and len(groups[0]['rows']) == 2
    assert groups[0]['names'] == ['Thambipillai Srikanthan']
    assert mapped[0]['reviewed_name_forms'] == ['Srikanthan Thambipillai']
    assert [r['name_listed'] for r in mapped] == [r['name_listed'] for r in rows]
    assert [r['quote'] for r in mapped] == [r['quote'] for r in rows]
    assert all(r['dblp'] == [] and r['orcid'] == [] for r in mapped)


@pytest.mark.parametrize('field,value', [('capture_url', 'https://unreviewed.example/faculty'),
                                         ('profile', 'https://profiles.example/other-person'),
                                         ('sha256', 'wrong'), ('quote', 'Invented Professor')])
def test_new_capture_profile_or_changed_heading_cannot_reuse_name_binding(source_review, field, value):
    rows, _, _, _ = source_review
    rows[0][field] = value
    with pytest.raises(ValueError, match='unreviewed source row'):
        C.reviewed_profile_names('ntu', rows)


def test_wrong_original_status_hash_format_or_quote_cannot_authorize_name(source_review):
    rows, doc, path, db = source_review
    original = copy.deepcopy(doc)
    doc['source_names'][0]['evidence'][0]['format'] = 'ntu_img_cards'
    path.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match='heading mismatch'):
        C.reviewed_profile_names('ntu', rows)
    path.write_text(json.dumps(original))
    with sqlite3.connect(db) as c:
        c.execute('update captures set http_status=403')
    with pytest.raises(ValueError, match='hash mismatch'):
        C.reviewed_profile_names('ntu', rows)
    with sqlite3.connect(db) as c:
        c.execute('update captures set http_status=200,raw_zlib=?', (zlib.compress(b'changed original'),))
    with pytest.raises(ValueError, match='hash mismatch'):
        C.reviewed_profile_names('ntu', rows)


def test_source_row_and_profile_reviews_must_agree(source_review):
    rows, doc, path, _ = source_review
    doc['profile_names'] = [dict(profile=rows[-1]['profile'], canonical_name='Another Scholar',
                                 listed_names=[rows[-1]['name_listed']], evidence=[doc['source_names'][0]['evidence'][-1]])]
    path.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match='conflicting source-row and profile'):
        C.reviewed_profile_names('ntu', rows)


def test_profileless_source_and_same_name_profiled_namesakes_stay_distinct(source_review):
    rows, doc, path, db = source_review
    canonical = 'Thambipillai Srikanthan'
    math_profile = 'https://profiles.example/person/srikanthan-math'
    with sqlite3.connect(db) as c:
        url = rows[-1]['capture_url']
        raw = zlib.decompress(c.execute('select raw_zlib from captures where capture_url=?', (url,)).fetchone()[0])
        raw += f'''<div class="img-card--academic"><h3 class="img-card__title"><a href="{math_profile}">Prof {canonical}</a></h3>
          <p class="img-card__desc">Appointments: Professor, Mathematics</p></div>'''.encode()
        sha = hashlib.sha256(raw).hexdigest()
        flat = ' '.join(BeautifulSoup(raw, 'html.parser').get_text(' ', strip=True).split())
        c.execute('update captures set sha256=?,raw_zlib=?,text=? where capture_url=?', (sha, zlib.compress(raw), flat, url))
    rows[-1]['sha256'] = sha
    entries = L.parse(raw.decode(), 'ntu_img_cards')[1]
    doc['source_names'][0]['evidence'] = doc['source_names'][0]['evidence'][:1]
    doc['profile_names'] = []
    for entry, identity in zip(entries, [canonical, canonical + ' [Mathematics]']):
        quote = quote_of(flat, entry)
        doc['profile_names'].append(dict(profile=entry['profile'], canonical_name=identity,
                                         listed_names=[canonical], evidence=[dict(url=url, sha256=sha,
                                         format='ntu_img_cards', name_listed=canonical, quote=quote)]))
        if entry['profile'] == math_profile:
            rows.append(dict(name=canonical, name_listed=canonical, observed='2026', profile=math_profile,
                             capture_url=url, sha256=sha, quote=quote))
    path.write_text(json.dumps(doc))
    mapped = C.reviewed_profile_names('ntu', rows)
    groups = C.merge_people(mapped)
    assert {g['names'][0]: len(g['rows']) for g in groups} == {canonical: 2, canonical + ' [Mathematics]': 1}
