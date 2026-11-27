"""Public author JSON bibliographies must yield the same guarded candidates as BibTeX."""
from collections import Counter, defaultdict
import json
import sqlite3
import zlib

import pytest

import labpage_channel as lc


TITLE = 'Setting the Bar Low: Are Websites Complying With the Minimum Requirements of the CCPA?'
SOURCE = 'https://author.example/json/papers.json'


def discover(body):
    row = dict(title=TITLE, doi='10.2478/popets-2022-0030', pis=['Reviewed PI'])
    other = dict(title='A separate research publication owned by a different investigator', pis=['Other PI'])
    return lc.match_pages([(SOURCE, {'Reviewed PI'}, body, 'application/json')],
                          {'Reviewed PI': [(row, 'work-1')], 'Other PI': [(other, 'work-2')]},
                          {'work-1': set(), 'work-2': set()}, Counter(), 'pihomes', lambda urls: False)


def test_owned_json_bibliography_discovers_only_guarded_matching_paper_links():
    body = json.dumps([
        dict(type='journal', title=TITLE, url='/publications/ccpa.pdf'),
        dict(title=TITLE, pdf='/publications/ccpa.pdf'),
        dict(title=TITLE, url='/publications/ccpa-slides.pdf'),
        dict(title=TITLE, url='https://dl.acm.org/doi/pdf/10.1/example'),
        dict(title=TITLE, url='javascript:alert(1)'),
        dict(title=TITLE, preprint='https://arxiv.org/abs/2201.00074v2'),
        dict(title='A separate research publication owned by a different investigator', url='/unrelated.pdf'),
    ])

    rows, arxiv = discover(body)

    assert [(r['work_id'], r['url']) for r in rows] == [('work-1', 'https://author.example/publications/ccpa.pdf')]
    assert rows[0]['landing_url'] == SOURCE
    assert json.loads(rows[0]['detail'])['pis'] == ['Reviewed PI']
    assert json.loads(rows[0]['detail'])['match'] == ['publication_json']
    assert arxiv == {'work-1': ('2201.00074', SOURCE)}


@pytest.mark.parametrize('body', [
    '[not valid JSON',
    '{"metadata": "not an author publication array"}',
    json.dumps(['not a publication', dict(title=7, url='/wrong.pdf')]),
    json.dumps([dict(title=TITLE, url=['/wrong.pdf'])]),
])
def test_unusable_json_metadata_supplies_no_download_candidate(body):
    assert discover(body) == ([], {})


def test_pihomes_consumes_explicit_author_json_hint_without_fetching_a_webpage(tmp_path, monkeypatch):
    monkeypatch.setattr(lc.F.P, 'FT_RAW', tmp_path)
    monkeypatch.setattr(lc, 'pi_pages', lambda school: (defaultdict(set), defaultdict(set)))
    monkeypatch.setattr(lc, 'lab_evidence', lambda school: [])
    monkeypatch.setattr(lc, 'iter_captures', lambda school: iter(()))
    monkeypatch.setattr(lc, 'DRY', True)
    (tmp_path/'pi-homepages-northeastern.json').write_text(json.dumps({'Reviewed PI': [SOURCE]}))
    body = json.dumps([dict(title=TITLE, url='/publications/ccpa.pdf')]).encode()
    with sqlite3.connect(tmp_path/'pihomes.sqlite') as db:
        db.execute('CREATE TABLE pages (url TEXT PRIMARY KEY, ok INT, fetched_at TEXT, body BLOB)')
        db.execute('INSERT INTO pages VALUES (?,1,?,?)', (SOURCE, '2026-11-27', zlib.compress(body)))
    paper = dict(title=TITLE, doi='10.2478/popets-2022-0030', pis=['Reviewed PI'])
    counts = Counter()

    rows = lc.step_pihomes('northeastern', [(paper, 'work-1')], {'work-1': set()}, counts, lambda urls: False)

    assert [(row['work_id'], row['url']) for row in rows] == [('work-1', 'https://author.example/publications/ccpa.pdf')]
    assert counts['pihomes_would_fetch'] == 0 and counts['pihomes_entries_matched'] == 1
