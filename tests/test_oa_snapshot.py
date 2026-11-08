"""The OpenAlex snapshot filter, merge and reader, on three hand-made gzipped parts served from a local HTTP server."""
import gzip
import http.server
import json
import os
import threading
from functools import partial
from pathlib import Path

import pytest

CODE = Path(__file__).resolve().parents[1]
import atlas_paths as P  # noqa: E402
import oa_snapshot as S  # noqa: E402

OA = 'https://openalex.org/'


def auth(aid, *insts):
    return {'author': {'id': OA + aid, 'display_name': aid}, 'author_position': 'first',
            'institutions': [{'id': OA + i, 'display_name': i, 'lineage': [OA + i, OA + 'I1'] if i != 'I20' else [OA + i, OA + 'I2']} for i in insts],
            'raw_affiliation_strings': ['x']}


def work(wid, year, ships, doi=None, typ='article'):
    return {'id': OA + wid, 'doi': doi, 'title': wid, 'display_name': wid, 'publication_year': year, 'publication_date': f'{year}-01-01', 'type': typ,
            'authorships': ships, 'locations': [], 'primary_location': None, 'updated_date': '2026-10-01', 'abstract_inverted_index': {'big': [0]}}


WORKS_A = [work('W1', 2020, [auth('A1', 'I10')], 'https://doi.org/10.1/a'),                         # charter lineage I10
           work('W2', 2020, [auth('A9', 'I99')]),                                                    # nobody of ours
           work('W3', 2021, [auth('A7', 'I99')], 'https://doi.org/10.1/c'),                          # our author A7 elsewhere
           work('W4', 2022, [auth('A8', 'I20')]),                                                    # excluded institution
           work('W5', 2022, [auth('A8', 'I10')], 'https://doi.org/10.17989/enc', 'dataset')]         # ENCODE dataset
WORKS_B = [work('W6', 2023, [auth('A2', 'I10'), auth('A7', 'I11')])]
AUTHORS = [{'id': OA + 'A7', 'display_name': 'Ours', 'orcid': None, 'works_count': 3, 'affiliations': [], 'last_known_institutions': [], 'updated_date': '2026-10-01'},
           {'id': OA + 'A50', 'display_name': 'Affiliated', 'affiliations': [{'institution': {'id': OA + 'I10'}}], 'updated_date': '2026-10-01'},
           {'id': OA + 'A51', 'display_name': 'Elsewhere', 'affiliations': [{'institution': {'id': OA + 'I99'}}], 'updated_date': '2026-10-01'}]
INSTS = [{'id': OA + 'I10', 'display_name': 'Univ', 'ror': 'https://ror.org/x', 'lineage': [OA + 'I10']}]


@pytest.fixture
def served(tmp_path, monkeypatch):
    root = tmp_path / 'www'
    for ent, parts in {'works': [WORKS_A, WORKS_B], 'authors': [AUTHORS], 'institutions': [INSTS]}.items():
        files = []
        for i, rows in enumerate(parts):
            f = root / 'data/jsonl' / ent / 'updated_date=2026-10-01' / f'part_{i:04d}.gz'
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(gzip.compress(('\n'.join(json.dumps(r) for r in rows) + '\n').encode()))
            files.append({'url': f's3://openalex/data/jsonl/{ent}/updated_date=2026-10-01/part_{i:04d}.gz', 'meta': {'content_length': f.stat().st_size, 'record_count': len(rows)}})
        (root / 'data/jsonl' / ent / 'manifest.json').write_text(json.dumps({'date': '2026-10-14', 'format': 'jsonl', 'entity': ent, 'files': files}))
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), partial(http.server.SimpleHTTPRequestHandler, directory=str(root)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setattr(S, 'BASE', f'http://127.0.0.1:{srv.server_address[1]}/')
    monkeypatch.setattr(S, 'targets', lambda: ({'I10', 'I11'}, {'I20'}, {'A7'}))
    monkeypatch.setattr(P, 'OA_SNAPSHOT', tmp_path / 'snap')
    monkeypatch.setattr(P, 'SCRATCH', tmp_path / 'scratch')
    monkeypatch.setattr(S, '_conns', {})
    yield tmp_path
    srv.shutdown()


def test_filter_merge_and_reader(served):
    date, parts = S.all_parts()
    assert date == '2026-10-14' and len(parts) == 4
    # two array tasks share the parts; together they cover each part once
    got = [p[1] for t in range(2) for p in S.share(parts, t, 2)]
    assert sorted(got) == sorted(p[1] for p in parts)
    for t in range(2):
        S.cmd_filter(t, 2, tmp=served)
    S.cmd_merge(date, of=2, parts=parts)
    assert not list((served / 'scratch').glob('openalex-*/*'))  # the parts are cleaned up after the merge
    assert S.snapshot_date() == '2026-10-14'
    # kept: W1 (lineage), W3 (our author elsewhere), W6 (both); dropped: W2, W4 (excluded institution), W5 (ENCODE dataset)
    assert {w['id'].rsplit('/', 1)[-1] for w in S.works_by_lineage('I10')} == {'W1', 'W6'}
    assert [w['id'].rsplit('/', 1)[-1] for w in S.works_by_author('A7')] == ['W3', 'W6']
    assert {w['id'].rsplit('/', 1)[-1] for w in S.works_by_lineage('I10', 2020)} == {'W1'}
    assert S.work('W4') is None and S.work('W5') is None and S.work('W2') is None
    w = S.work('10.1/A')  # a DOI, any case
    assert w['id'].endswith('W1') and w['snapshot_date'] == '2026-10-14'
    assert w['abstract_inverted_index'] == {'big': [0]}  # projected since 2026-11-04
    assert S.author('A7')['display_name'] == 'Ours' and S.author('A50') and S.author('A51') is None
    assert S.institution('I10')['ror'] == 'https://ror.org/x'
    man = json.loads((served / 'snap' / '2026-10-14' / 'manifest.json').read_text())
    assert man['counts']['works'] == 3 and man['counts']['parts'] == 4


def test_a_missing_part_stops_the_merge(served):
    date, parts = S.all_parts()
    S.cmd_filter(0, 2, tmp=served)
    with pytest.raises(SystemExit):
        S.cmd_merge(date, of=2, parts=parts)


def test_exclusion_is_per_affiliation_not_per_authorship():
    """UChicago PROTOCOL-FRICTION 20: an authorship with a school institution AND an excluded one keeps the school hit; an
    authorship touching only the excluded institution (whose lineage reaches the school) is still dropped."""
    inst, excl = {'I1'}, {'I9'}
    joint = {'id': OA + 'I8', 'lineage': [OA + 'I8', OA + 'I1']}
    argonne = {'id': OA + 'I9', 'lineage': [OA + 'I9', OA + 'I1']}
    def w(*institutions):
        return {'id': OA + 'W1', 'type': 'article', 'authorships': [{'author': {'id': OA + 'A1'}, 'institutions': list(institutions)},
                                                                     {'author': {'id': OA + 'A2'}, 'institutions': [argonne]}]}
    assert S.keep_work(w(joint, argonne), inst, excl, set())[1] == {'I1'}
    assert S.keep_work(w(argonne), inst, excl, set()) is None
    assert S.keep_work(w(argonne, joint), inst, excl, set())[1] == {'I1'}


def test_an_extension_adds_a_school_without_touching_the_main_store(served, monkeypatch):
    """`filter --ext KEY` / `merge --ext KEY` (a school onboarded after the snapshot was filtered): ext-<key>.sqlite beside the main store."""
    date, parts = S.all_parts()
    monkeypatch.setattr(S, 'targets', lambda only=None: ({'I10'}, set(), set()) if not only else ({'I99'}, set(), set()))
    for t in range(2):
        S.cmd_filter(t, 2, tmp=served)
    S.cmd_merge(date, of=2, parts=parts)
    main = served / 'snap' / '2026-10-14' / 'openalex.sqlite'
    before = (main.stat().st_size, main.stat().st_mtime_ns)
    assert S.work('W2') is None and list(S.works_by_lineage('I99')) == []
    for t in range(2):
        S.cmd_filter(t, 2, tmp=served, ext='newu')
    S.cmd_merge(date, of=2, parts=parts, ext='newu')
    assert (main.stat().st_size, main.stat().st_mtime_ns) == before and S.snapshot_date() == '2026-10-14'
    ext = served / 'snap' / '2026-10-14' / 'ext-newu.sqlite'
    assert ext.exists() and json.loads((ext.parent / 'ext-newu.manifest.json').read_text())['extension'] == 'newu'
    assert not list((served / 'scratch').glob('openalex-*/*'))
    S._conns.clear()
    assert S.work('W2')['id'].endswith('W2') and S.work('10.1/c')['id'].endswith('W3')
    assert {w['id'].rsplit('/', 1)[-1] for w in S.works_by_lineage('I99')} == {'W2', 'W3'}
    assert {w['id'].rsplit('/', 1)[-1] for w in S.works_by_lineage('I10')} == {'W1', 'W6'}   # main rows still come from the main store
    assert S.institution('I10') is not None   # institutions are not repeated in an extension


def test_exclusion_is_per_affiliation_not_per_authorship():
    """UChicago PROTOCOL-FRICTION 20: an authorship with a school institution AND an excluded one keeps the school hit; an
    authorship touching only the excluded institution (whose lineage reaches the school) is still dropped."""
    inst, excl = {'I1'}, {'I9'}
    joint = {'id': OA + 'I8', 'lineage': [OA + 'I8', OA + 'I1']}
    argonne = {'id': OA + 'I9', 'lineage': [OA + 'I9', OA + 'I1']}
    def w(*institutions):
        return {'id': OA + 'W1', 'type': 'article', 'authorships': [{'author': {'id': OA + 'A1'}, 'institutions': list(institutions)},
                                                                     {'author': {'id': OA + 'A2'}, 'institutions': [argonne]}]}
    assert S.keep_work(w(joint, argonne), inst, excl, set())[1] == {'I1'}
    assert S.keep_work(w(argonne), inst, excl, set()) is None
    assert S.keep_work(w(argonne, joint), inst, excl, set())[1] == {'I1'}


def test_related_institutions_count_only_with_an_affiliation_string_naming_the_school():
    """UChicago D3 (2026-11-03): Argonne is 'related'. A joint UChicago + Argonne byline keeps the UChicago hit (its own entry); an Argonne-only
    authorship counts only when its raw affiliation string matches the school's regex."""
    import re
    inst = {'I1', 'I7'}                      # the school's lineage id and the related Argonne id (swept)
    rel = [({'I7'}, re.compile(r'University of Chicago|UChicago', re.I))]
    uchi = {'id': OA + 'I1', 'lineage': [OA + 'I1']}
    argonne = {'id': OA + 'I7', 'lineage': [OA + 'I7', OA + 'I1']}   # a lineage child of the school

    def w(insts, raws):
        return {'id': OA + 'W1', 'type': 'article', 'authorships': [{'author': {'id': OA + 'A1'}, 'institutions': insts, 'raw_affiliation_strings': raws}]}
    joint = S.keep_work(w([uchi, argonne], ['University of Chicago', 'Argonne National Laboratory']), inst, set(), set(), rel)
    assert joint and joint[1] == {'I1', 'I7'}
    assert S.keep_work(w([argonne], ['Argonne National Laboratory, Lemont, IL']), inst, set(), set(), rel) is None
    only = S.keep_work(w([argonne], ['Argonne National Laboratory and the University of Chicago']), inst, set(), set(), rel)
    assert only and only[1] == {'I1', 'I7'}
    assert S.keep_work(w([uchi], ['x']), inst, set(), set(), rel)[1] == {'I1'}


def test_projection_keeps_abstract_and_topics_and_drops_the_rest():
    w = dict(work('W9', 2024, [auth('A1', 'I10')]), primary_topic={'id': OA + 'T1', 'display_name': 'x'}, topics=[{'id': OA + 'T1'}],
             referenced_works=['a'], concepts=[{'id': 'c'}], counts_by_year=[1])
    p = S.project_work(w)
    assert p['abstract_inverted_index'] == {'big': [0]} and p['primary_topic']['id'].endswith('T1') and p['topics'][0]['id'].endswith('T1')
    assert not {'referenced_works', 'concepts', 'counts_by_year'} & set(p)


def test_merge_temp_dir_avoids_node_tmp_and_fails_early(tmp_path, monkeypatch):
    shm = tmp_path / 'shm'
    out = tmp_path / 'out'
    big = 1 << 62
    assert S.sqlite_tmpdir(1000, out, env={}, shm=str(shm)) == shm                       # room in shm: used
    monkeypatch.setattr(S.shutil, 'disk_usage', lambda p: type('U', (), dict(free=0 if str(p) == str(shm) else big))())
    assert S.sqlite_tmpdir(1000, out, env={}, shm=str(shm)) == out / '.sqlite-tmp'        # shm full: the job's scratch (NFS)
    assert S.sqlite_tmpdir(1000, out, env={'OA_MERGE_TMP': str(tmp_path / 'mine')}, shm=str(shm)) == tmp_path / 'mine'
    monkeypatch.setattr(S.shutil, 'disk_usage', lambda p: type('U', (), dict(free=10))())
    with pytest.raises(SystemExit, match='no scratch directory with room'):
        S.sqlite_tmpdir(1000, out, env={}, shm=str(shm))


def test_merge_points_sqlite_temp_files_away_from_tmp(served, monkeypatch):
    date, parts = S.all_parts()
    for t in range(2):
        S.cmd_filter(t, 2, tmp=served)
    seen = []
    real = S.sqlite_tmpdir
    monkeypatch.setattr(S, 'sqlite_tmpdir', lambda need, out, **k: (seen.append(need), real(need, out, env={'OA_MERGE_TMP': str(served / 'mt')}))[1])
    monkeypatch.delenv('SQLITE_TMPDIR', raising=False)
    S.cmd_merge(date, of=2, parts=parts)
    assert seen and seen[0] > 0 and os.environ['SQLITE_TMPDIR'] == str(served / 'mt')
    monkeypatch.delenv('SQLITE_TMPDIR', raising=False)


def test_author_only_extension_keeps_exact_authors_and_records_filter(served, monkeypatch):
    date, parts = S.all_parts()
    authors_file = served / 'pi-ids.json'
    authors_file.write_text(json.dumps(['https://openalex.org/A7']))
    monkeypatch.setattr(S, 'targets', lambda *args: pytest.fail('author-only extension must not load charters'))
    for task in range(2):
        S.cmd_filter(task, 2, date=date, parts=parts, tmp=served, ext='cohort', authors_file=authors_file)
    S.cmd_merge(date, of=2, parts=parts, ext='cohort')
    import sqlite3
    with sqlite3.connect(served / 'snap' / date / 'ext-cohort.sqlite') as db:
        assert {r[0] for r in db.execute('SELECT id FROM works')} == {OA + 'W3', OA + 'W6'}
        assert {r[0] for r in db.execute('SELECT id FROM authors')} == {OA + 'A7'}
    manifest = json.loads((served / 'snap' / date / 'ext-cohort.manifest.json').read_text())
    assert manifest['authors_file_sha256'] == S.sha(authors_file)
    assert manifest['authors'] == 1
    assert not (served / 'snap' / 'current').exists()


def test_author_filter_cli_is_forwarded(monkeypatch):
    calls = []
    monkeypatch.setattr(S, 'cmd_filter', lambda *args, **kwargs: calls.append((args, kwargs)))
    S.main(['filter', '0', '2', '--ext', 'cohort', '--authors-file', 'pi-ids.json'])
    assert calls[0][1]['authors_file'] == 'pi-ids.json'


def test_invalid_author_filter_does_not_fetch_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(S, 'all_parts', lambda *args: pytest.fail('invalid filter must fail before network'))
    f = tmp_path / 'ids.json'
    f.write_text('[]')
    with pytest.raises(SystemExit, match='needs --ext'):
        S.cmd_filter(0, 1, authors_file=f)
    with pytest.raises(SystemExit, match='no author ids'):
        S.cmd_filter(0, 1, ext='cohort', authors_file=f)
    f.write_text('42')
    with pytest.raises(SystemExit, match='JSON list'):
        S.load_author_ids(f)


def test_merge_rejects_mixed_author_filters(served):
    date, parts = S.all_parts()
    f = served / 'ids.txt'
    for task, aid in enumerate(('A7', 'A9')):
        f.write_text(aid)
        S.cmd_filter(task, 2, date=date, parts=parts, tmp=served, ext='cohort', authors_file=f)
    with pytest.raises(SystemExit, match='different author filters'):
        S.cmd_merge(date, of=2, parts=parts, ext='cohort')
    assert not (served / 'snap' / date / 'ext-cohort.sqlite').exists()


def test_explicit_institution_extension_uses_lineage_and_preserves_main(served):
    date, parts = S.all_parts()
    for task in range(2):
        S.cmd_filter(task, 2, date=date, parts=parts, tmp=served)
    S.cmd_merge(date, of=2, parts=parts)
    main = served / 'snap' / date / 'openalex.sqlite'
    before = main.read_bytes()
    f = served / 'institutions.json'
    # I2 is an ancestor of I20 in the fixture; I99 is an exact hit.
    f.write_text(json.dumps(['https://openalex.org/I2', 'I99']))
    for task in range(2):
        S.cmd_filter(task, 2, date=date, parts=parts, tmp=served, ext='top25', institutions_file=f)
    S.cmd_merge(date, of=2, parts=parts, ext='top25')
    assert main.read_bytes() == before
    S._conns.clear()
    assert {w['id'].rsplit('/', 1)[-1] for w in S.works_by_lineage('I99')} == {'W2', 'W3'}
    assert {w['id'].rsplit('/', 1)[-1] for w in S.works_by_lineage('I2')} == {'W4'}
    manifest = json.loads((main.parent / 'ext-top25.manifest.json').read_text())
    assert manifest['institutions_file_sha256'] == S.sha(f)
    assert manifest['institutions'] == 2


def test_institution_input_errors_precede_any_manifest_fetch(tmp_path, monkeypatch):
    monkeypatch.setattr(S, 'all_parts', lambda *a: pytest.fail('must not fetch'))
    f = tmp_path / 'ids.json'
    f.write_text('["I99"]')
    with pytest.raises(SystemExit, match='needs --ext'):
        S.cmd_filter(0, 1, institutions_file=f)
    with pytest.raises(SystemExit, match='mutually exclusive'):
        S.cmd_filter(0, 1, ext='top25', authors_file=f, institutions_file=f)
    for bad in [[], ['A7'], ['I99', 'typo'], {'I99': 'not a list'}]:
        f.write_text(json.dumps(bad))
        with pytest.raises(SystemExit, match='nonempty JSON list'):
            S.cmd_filter(0, 1, ext='top25', institutions_file=f)


def test_merge_rejects_mixed_institution_filters(served):
    date, parts = S.all_parts()
    f = served / 'ids.json'
    for task, iid in enumerate(('I99', 'I10')):
        f.write_text(json.dumps([iid]))
        S.cmd_filter(task, 2, date=date, parts=parts, tmp=served, ext='top25', institutions_file=f)
    with pytest.raises(SystemExit, match='different institution filters'):
        S.cmd_merge(date, of=2, parts=parts, ext='top25')
    assert not (served / 'snap' / date / 'ext-top25.sqlite').exists()
