"""D-0073: reviewed OpenAlex works created after the sweep snapshot: the proposal filter and the pihier wiring."""
import collections
import json
import re
import sqlite3
import zlib

import atlas_paths as P  # noqa: E402
import post_snapshot_works as PS  # noqa: E402
from pihier import common as C  # noqa: E402

AT = lambda a: any('Maryland' in r for r in a.get('raw_affiliation_strings') or [])   # noqa: E731
RX = re.compile(r'\buniv(?:ersity)?\s+of\s+maryland\b', re.I)


def work(created='2026-11-03', year=2026, aid='https://openalex.org/A1', raw='University of Maryland , College Park', orcid=None):
    return dict(id='https://openalex.org/W9', title='T', publication_year=year, publication_date=f'{year}-05-01', created_date=created + 'T00:00:00',
                authorships=[dict(author=dict(id=aid, orcid=orcid), raw_author_name='Ann Lee', author_position='first', institutions=[], raw_affiliation_strings=[raw])])


def test_the_filter_keeps_only_post_snapshot_in_window_school_affiliated_works_by_the_pis_id():
    ok = lambda w, **k: PS.hits(w, {'https://openalex.org/A1'}, set(), AT, k.get('years', [2025, 2026]), 2016, RX)   # noqa: E731
    assert len(ok(work())) == 1 and ok(work())[0]['raw_affiliation'].startswith('University of Maryland')
    assert ok(work(created='2026-10-14')) == [] and ok(work(created='2026-09-01')) == []       # pre-snapshot (the snapshot day itself is in the sweep)
    assert ok(work(year=2024)) == [] and ok(work(year=2015), years=[2015]) == []                # not a listed year; before the atlas window
    assert ok(work(raw='Columbia University')) == []                                            # another affiliation (a merged profile's other works)
    assert ok(work(aid='https://openalex.org/A2')) == []                                        # not the PI's author id
    got = PS.hits(work(aid='https://openalex.org/A2', orcid='https://orcid.org/0000-0001-0000-0001'), set(), {'0000-0001-0000-0001'}, AT, [2026], 2016, RX)
    assert len(got) == 1                                                                         # a bound ORCID counts
    assert ok(dict(work(), type='dataset')) == [] and ok(dict(work(), publication_date='2099-01-01')) == []   # not a paper; dated after today
    assert ok(work(raw='Google Research, Mountain View')) == []                                 # raw affiliation does not name the school (institution lineage alone is not the quote)


def write_review(tmp_path, monkeypatch, **entry):
    w = work()
    e = dict(pi='Ann Lee', work=w['id'], url='https://api.openalex.org/works/W9', sha256=C.work_sha(w), record=w)
    e.update(entry)
    (tmp_path / 'post-snapshot-works.json').write_text(json.dumps({'works': {w['id']: e}}))
    monkeypatch.setattr(P, 'data', lambda name, school=None, root=None, layout=None: tmp_path / name)
    return e


def test_only_reviewed_unchanged_post_snapshot_works_are_wired(tmp_path, monkeypatch):
    write_review(tmp_path, monkeypatch)
    n = collections.Counter()
    assert list(C.post_snapshot_works('x', n=n)) == [] and n['post_snapshot_works_not_wired:not_reviewed'] == 1
    write_review(tmp_path, monkeypatch, reviewed_by='me', why='tie')
    n = collections.Counter()
    assert [w['id'] for w in C.post_snapshot_works('x', n=n)] == ['https://openalex.org/W9'] and n['post_snapshot_works_wired'] == 1
    e = write_review(tmp_path, monkeypatch, reviewed_by='me', why='tie', sha256='0' * 64)
    n = collections.Counter()
    assert list(C.post_snapshot_works('x', n=n)) == [] and n['post_snapshot_works_not_wired:hash_changed'] == 1
    w = work(created='2026-10-01')
    write_review(tmp_path, monkeypatch, reviewed_by='me', why='tie', record=w, sha256=C.work_sha(w))
    n = collections.Counter()
    assert list(C.post_snapshot_works('x', n=n)) == [] and n['post_snapshot_works_not_wired:not_after_snapshot'] == 1
    assert e['pi'] == 'Ann Lee'


def test_sweep_works_appends_the_wired_work_once(tmp_path, monkeypatch):
    con = sqlite3.connect(tmp_path / 'openalex-sweep.sqlite')
    con.execute('create table pages (year int, page int, body blob)')
    snap = dict(id='https://openalex.org/W1', authorships=[])
    con.execute('insert into pages values (2026, 1, ?)', (zlib.compress(json.dumps([snap]).encode()),)); con.commit(); con.close()
    write_review(tmp_path, monkeypatch, reviewed_by='me', why='tie')
    monkeypatch.setattr(C, 'related_gate', lambda school: None)
    assert [w['id'] for w in C.sweep_works('x')] == ['https://openalex.org/W1', 'https://openalex.org/W9']
    # a work the snapshot already holds is not added a second time
    con = sqlite3.connect(tmp_path / 'openalex-sweep.sqlite')
    con.execute('insert into pages values (2026, 2, ?)', (zlib.compress(json.dumps([dict(id='https://openalex.org/W9', authorships=[])]).encode()),)); con.commit(); con.close()
    assert [w['id'] for w in C.sweep_works('x')].count('https://openalex.org/W9') == 1
