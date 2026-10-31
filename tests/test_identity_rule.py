"""The automatic identity rule (fulltext-push/identity_rule.py) and its use at download time in the vendored collector
wrapper (vendor/cmu_tools/collector_wrapper.py check_identity): pass, reject and undecided (2026-10-31)."""
import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'fulltext-push', ROOT / 'vendor' / 'cmu_tools'):
    if str(p) not in sys.path:
        sys.path.append(str(p))
import identity_rule as IR  # noqa: E402

TITLE = 'Learning Fixture Representations for Channel Plugins'
PAGE_OK = 'arXiv:2101.00001v2 [cs.LG]  Learning Fixture Representations for Channel Plugins  Ada Lovelace1, Charles Babbage2 ' + 'x' * 200
PAGE_OTHER = 'Privacy statement of the repository. This document describes how personal data of users is processed. ' * 3


def test_judge_pass_fail_undecided():
    assert IR.judge(PAGE_OK, TITLE, 'lovelace', None, None, None)[0] == 'pass_title'
    assert IR.judge(PAGE_OTHER, TITLE, 'lovelace', '10.5555/x', None, None)[0] == 'fail'
    assert IR.judge('', TITLE, 'lovelace', None, None, None)[0] == 'undecided'               # no text layer
    assert IR.judge(PAGE_OTHER, TITLE, '', None, None, None)[0] == 'undecided'               # no author, no DOI known
    retitled = 'arXiv:2101.00001v2 [cs.LG]  Something Else Entirely  Ada Lovelace ' + 'y' * 200
    assert IR.judge(retitled, TITLE, 'lovelace', '10.5555/x', 'https://x/2101.00001v2.pdf', '2101.00001')[0] == 'pass_arxiv'
    assert IR.judge(retitled, TITLE, 'lovelace', '10.5555/x', 'https://x/2101.00009v1.pdf', '2101.00001')[0] == 'fail'
    assert IR.judge('Queueing Delay Minimization in Overloaded Networks  Xinyu Wu, Dan Wu ' + 'z' * 100, 'Queueing Delay Minimization in Overloaded Networks', 'wu',
                    None, None, None)[0] == 'pass_title'                                            # a two-letter family name


@pytest.fixture
def store(tmp_path, monkeypatch):
    st = tmp_path / 'mit'
    (st / 'objects').mkdir(parents=True)
    db = sqlite3.connect(str(st / 'catalog.sqlite'))
    db.execute('CREATE TABLE works (id TEXT, file_path TEXT, status TEXT, graph_json TEXT)')
    db.execute("INSERT INTO works VALUES ('w1', 'objects/a.pdf', 'queued', '{}')")
    db.commit(); db.close()
    (st / 'objects' / 'a.pdf').write_bytes(b'%PDF-1.4 fixture')
    import collector_wrapper as W
    monkeypatch.setattr(W, '_check_identity', lambda row, path: IR.PENDING)
    monkeypatch.setattr(IR, 'first_author', lambda *a, **k: 'lovelace')
    monkeypatch.setattr(IR, 'mapped_arxiv', lambda *a, **k: None)
    return st, W


ROW = dict(id='w1', title=TITLE, doi='10.5555/x')


def test_wrapper_pass(store, monkeypatch):
    st, W = store
    monkeypatch.setattr(IR, 'page_text', lambda *a: PAGE_OK)
    assert W.check_identity(ROW, st / 'objects' / 'a.pdf') == 'auto_title_author_page1'
    assert (st / 'objects' / 'a.pdf').exists()


def test_wrapper_reject_moves_the_file_out_of_objects(store, monkeypatch):
    st, W = store
    monkeypatch.setattr(IR, 'page_text', lambda *a: PAGE_OTHER)
    with pytest.raises(ValueError, match='identity unconfirmed'):
        W.check_identity(ROW, st / 'objects' / 'a.pdf')
    assert not (st / 'objects' / 'a.pdf').exists()
    assert (st / 'quarantine' / 'identity-rejected' / 'a.pdf').exists()
    m = [json.loads(l) for l in open(st / 'quarantine' / 'identity-rejected' / 'manifest.jsonl')]
    assert m[0]['work_id'] == 'w1' and m[0]['kept_as'] == 'quarantine/identity-rejected/a.pdf'


def test_wrapper_undecided_keeps_pending(store, monkeypatch):
    st, W = store
    monkeypatch.setattr(IR, 'page_text', lambda *a: '')
    assert W.check_identity(ROW, st / 'objects' / 'a.pdf') == IR.PENDING
    assert (st / 'objects' / 'a.pdf').exists()


def test_review_access_reads_the_rejection():
    from review_access import cause
    assert cause(dict(url='https://x/a.pdf', status='unavailable', detail='identity unconfirmed: 10% of the title')) == ('identity_mismatch', False)
