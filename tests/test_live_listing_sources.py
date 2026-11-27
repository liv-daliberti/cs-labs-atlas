"""Reviewed live directory pages supplement historical captures without inventing archive provenance."""
import hashlib
import json
import sqlite3
import zlib

import pytest

import listing_rows as R


def card(name, title='Professor of Computer Science', href='/faculty/example/'):
    return (f'<li class="entity_list_item"><h2 class="entity_name"><a href="{href}">{name}</a></h2>'
            f'<div class="entity_title">{title}</div></li>')


@pytest.fixture
def live_setup(tmp_path, monkeypatch):
    paths = {name: tmp_path / name for name in ('live-listing-sources.json', 'school-captures.sqlite',
                                              'listings-captures.sqlite', 'rows.json', 'coverage.json', 'rows-coverage-only.json')}
    monkeypatch.setattr(R.P, 'data', lambda name, key=None: paths.setdefault(name, tmp_path / name))
    monkeypatch.setattr(R.P, 'data_w', lambda name, key=None: paths.setdefault(name, tmp_path / name))
    cfg = {'window': [2016, 2026], 'departments': [{'code': 'CS', 'title_match': 'Computer Science',
                                                'listings': [{'slot': 'CS faculty', 'kind': 'main', 'url': 'example.edu/faculty/'}]}]}
    monkeypatch.setattr(R.S, 'get', lambda key: cfg)
    c = sqlite3.connect(paths['school-captures.sqlite'])
    c.execute('create table live (url text primary key, fetched_at text, status int, sha256 text, raw_zlib blob, content_type text)')
    c.commit()

    def source(pages, complete=True, expected=None):
        receipts = []
        for i, html in enumerate(pages):
            url = 'https://example.edu/faculty/' + (f'?page={i}' if i else '')
            data = html.encode()
            sha = hashlib.sha256(data).hexdigest()
            c.execute('insert or replace into live values (?,?,?,?,?,?)',
                      (url, f'2025-11-0{i + 5}T15:02:46', 200, sha, zlib.compress(data), 'text/html'))
            receipts.append({'url': url, 'sha256': sha})
        c.commit()
        manifest = {'sources': [{'dept': 'CS', 'slot': 'CS faculty', 'format': 'wse_entity',
                                 'complete': complete, 'expected_entries': expected, 'pages': receipts}]}
        paths['live-listing-sources.json'].write_text(json.dumps(manifest))
        return manifest
    yield paths, cfg, c, source
    c.close()


def test_live_only_preserves_actual_dates_urls_quotes_and_relative_links(live_setup):
    paths, _, _, source = live_setup
    source([card('Alice Example') + '<nav class="pager"><a href="?page=1">2</a></nav>', card('Bob Example')], expected=2)
    R.main('test')
    rows = json.loads(paths['rows.json'].read_text())
    assert len(rows) == 2 and {r['year'] for r in rows} == {2025}
    assert rows[0]['observed'] == '20251105150246'
    assert rows[1]['observed'] == '20251106150246'
    assert rows[0]['capture_url'] == 'https://example.edu/faculty/'
    assert rows[0]['homepage'] == 'https://example.edu/faculty/example/'
    assert rows[0]['quote'] == 'Alice Example Professor of Computer Science'
    assert all(r['source_kind'] == 'live' and r['sha256'] for r in rows)
    assert not paths['listings-captures.sqlite'].exists()
    assert json.loads(paths['coverage.json'].read_text()) == {'CS': {'2025': {'CS faculty live H2': 'ok'}}}


def test_live_coverage_does_not_fill_historical_plan_gaps(live_setup):
    paths, _, _, source = live_setup
    source([card('Alice Example')], expected=1)
    with sqlite3.connect(paths['listings-captures.sqlite']) as c:
        c.execute('create table plan (slot text, dept text, year int, half text, capture_url text, status text, reason text)')
        c.execute("insert into plan values ('CS faculty','CS',2016,'H1',NULL,'nocapture','exact URL has no capture')")
    R.main('test')
    coverage = json.loads(paths['coverage.json'].read_text())['CS']
    assert coverage['2016'] == {'CS faculty H1': 'nocapture: exact URL has no capture'}
    assert coverage['2025'] == {'CS faculty live H2': 'ok'}


def test_live_partial_keeps_evidenced_rows_but_not_ok_coverage(live_setup):
    paths, _, _, source = live_setup
    source([card('Alice Example')], complete=False)
    R.main('test')
    assert len(json.loads(paths['rows.json'].read_text())) == 1
    assert json.loads(paths['coverage.json'].read_text())['CS']['2025']['CS faculty live H2'].startswith('partial:')


def test_contact_href_never_becomes_a_homepage(live_setup):
    paths, _, _, source = live_setup
    source([card('Alice Example', href='mailto:contact@example.edu')], expected=1)
    R.main('test')
    row = json.loads(paths['rows.json'].read_text())[0]
    assert row['homepage'] is None and 'profile' not in row


def test_live_respects_title_filter_and_courtesy_context(live_setup):
    paths, cfg, _, source = live_setup
    cfg['departments'][0]['listings'][0].update(kind='courtesy', title_filter='Computer Science')
    source([card('Alice Example') + card('Other Person', 'Professor of Chemistry')], expected=1)
    R.main('test')
    rows = json.loads(paths['rows.json'].read_text())
    assert len(rows) == 1 and rows[0]['rank'] == 'courtesy'
    assert rows[0]['titles'] == ['Professor of Computer Science']


@pytest.mark.parametrize('change,match', [('hash', 'hash mismatch'), ('date', 'fetch date mismatch'),
                                        ('count', 'entry count mismatch'), ('status', 'HTTP 200')])
def test_live_review_mismatches_fail_without_writing_rows(live_setup, change, match):
    paths, _, c, source = live_setup
    manifest = source([card('Alice Example')], expected=1)
    group = manifest['sources'][0]
    if change == 'hash':
        group['pages'][0]['sha256'] = '0' * 64
    elif change == 'date':
        group['pages'][0]['fetched_at'] = '2026-11-06T00:00:00'
    elif change == 'count':
        group['expected_entries'] = 2
    else:
        c.execute('update live set status=999'); c.commit()
    paths['live-listing-sources.json'].write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match=match):
        R.main('test')
    assert not paths['rows.json'].exists()


def test_complete_live_group_requires_every_linked_pager_page(live_setup):
    paths, _, _, source = live_setup
    source([card('Alice Example') + '<nav class="pager"><a href="?page=1">2</a></nav>'], expected=1)
    with pytest.raises(ValueError, match='unreviewed linked pages'):
        R.main('test')
    assert not paths['rows.json'].exists()
