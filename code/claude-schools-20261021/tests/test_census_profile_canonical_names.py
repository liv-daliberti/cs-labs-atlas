"""Same-name faculty cards stay distinct while reviewed profile continuations join."""
import copy
import hashlib
import json
import sqlite3
import zlib

from bs4 import BeautifulSoup
import pytest

import census_build as C


@pytest.fixture
def profile_review(tmp_path, monkeypatch):
    old_url = 'https://web.archive.org/web/20210101000000id_/https://university.example/faculty'
    new_url = 'https://web.archive.org/web/20250101000000id_/https://university.example/faculty'
    legacy = 'https://profiles.example/cris/rp/rp00572'
    cs = 'https://profiles.example/person/Li-Yi'
    math = 'https://profiles.example/person/yili'
    def card(name, profile, title):
        return f'<div class="img-card--academic"><h3 class="img-card__title"><a href="{profile}">Assoc Prof {name}</a></h3><p class="img-card__desc">Appointments: {title}</p></div>'
    cs_title = 'Associate Professor, Computing'
    math_title = 'Associate Professor, Mathematics'
    old = card('Yi Li', legacy, cs_title)
    new = card('Li Yi', cs, cs_title) + card('Li Yi', math, math_title)
    db = tmp_path / 'captures.sqlite'
    with sqlite3.connect(db) as c:
        c.execute('create table captures(capture_url text, http_status int, sha256 text, raw_zlib blob, text text)')
        for url, html in [(old_url, old), (new_url, new)]:
            raw = html.encode()
            c.execute('insert into captures values(?,?,?,?,?)', (url, 200, hashlib.sha256(raw).hexdigest(), zlib.compress(raw), BeautifulSoup(html, 'html.parser').get_text(' ', strip=True)))
    def binding(profile, canonical, listed, url, html, title):
        return dict(profile=profile, canonical_name=canonical, listed_names=[listed], evidence=[
            dict(url=url, sha256=hashlib.sha256(html.encode()).hexdigest(), format='ntu_img_cards', name_listed=listed,
                 quote=f'Assoc Prof {listed} [...] Appointments: {title}')])
    doc = dict(school='ntu', rows=[], profile_names=[
        binding(legacy, 'Yi Li', 'Yi Li', old_url, old, cs_title),
        binding(cs, 'Yi Li', 'Li Yi', new_url, new, cs_title),
        binding(math, 'Yi Li [SPMS]', 'Li Yi', new_url, new, math_title),
    ])
    path = tmp_path / 'aliases.json'
    path.write_text(json.dumps(doc))
    monkeypatch.setattr(C.P, 'data', lambda name, key=None: path if name == 'census-name-aliases.json' else db)
    rows = [dict(name='Yi Li', name_listed='Yi Li', observed='2021', profile=legacy.replace('/cris/', '//cris/'), quote='Original old quote'),
            dict(name='Li Yi', name_listed='Li Yi', observed='2025', profile=cs, quote='Original CS quote'),
            dict(name='Li Yi', name_listed='Li Yi', observed='2025', profile=math, quote='Original math quote')]
    return rows, doc, path, db


def test_profile_qualified_names_preserve_namesakes_and_historical_identity(profile_review):
    rows, _, _, _ = profile_review
    original = copy.deepcopy(rows)
    mapped = C.reviewed_profile_names('ntu', rows)
    groups = C.merge_people(mapped)
    by_name = {g['names'][0]: g for g in groups}
    assert set(by_name) == {'Yi Li', 'Yi Li [SPMS]'}
    assert len(by_name['Yi Li']['rows']) == 2
    assert len(by_name['Yi Li [SPMS]']['rows']) == 1
    assert rows == original
    assert [r['name_listed'] for r in mapped] == ['Yi Li', 'Li Yi', 'Li Yi']
    assert [r['quote'] for r in mapped] == [r['quote'] for r in original]


def test_unknown_profile_for_reviewed_ambiguous_name_stops(profile_review):
    rows, _, _, _ = profile_review
    rows[-1]['profile'] = 'https://profiles.example/person/unreviewed'
    with pytest.raises(ValueError, match='unreviewed source profile'):
        C.reviewed_profile_names('ntu', rows)


def test_changed_original_or_wrong_source_card_cannot_authorize_mapping(profile_review):
    rows, doc, path, db = profile_review
    doc['profile_names'][-1]['evidence'][0]['quote'] = 'Assoc Prof Li Yi [...] Appointments: Invented Professor'
    path.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match='source card mismatch'):
        C.reviewed_profile_names('ntu', rows)
    doc['profile_names'][-1]['evidence'][0]['quote'] = 'Assoc Prof Li Yi [...] Appointments: Associate Professor, Mathematics'
    path.write_text(json.dumps(doc))
    with sqlite3.connect(db) as c:
        c.execute('update captures set raw_zlib=?', (zlib.compress(b'changed page'),))
    with pytest.raises(ValueError, match='hash mismatch'):
        C.reviewed_profile_names('ntu', rows)


def test_qualified_primary_identity_keeps_source_forms_without_native_name_merge(profile_review):
    from collections import Counter
    from pihier.census import merge_census_rows
    rows, _, _, _ = profile_review
    mapped = C.reviewed_profile_names('ntu', rows)
    assert mapped[-1]['name'] == 'Yi Li [SPMS]'
    assert mapped[-1]['reviewed_name_forms'] == ['Li Yi']
    # The same literal source name is a matching form, not a primary identity
    # or permission to inherit the other person's bibliographic anchor.
    native = [dict(name='Yi Li', aliases=['Li Yi'], is_pi=True, collection_person_id='cs', dblp=['cs-pid']),
              dict(name='Yi Li [SPMS]', aliases=['Yi Li', 'Li Yi'], is_pi=True, collection_person_id='math', dblp=[])]
    grouped, _ = merge_census_rows(native, {}, Counter())
    assert len(grouped) == 2
    assert grouped['Yi Li [SPMS]'][0]['dblp'] == []
