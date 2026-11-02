"""The OpenAlex snapshot filter, merge and reader, on three hand-made gzipped parts served from a local HTTP server."""
import gzip
import http.server
import json
import sys
import threading
from functools import partial
from pathlib import Path

import pytest

CODE = Path(__file__).resolve().parents[1]
if str(CODE / 'tools') not in sys.path:
    sys.path.insert(0, str(CODE / 'tools'))
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
    assert 'abstract_inverted_index' not in w  # not projected
    assert S.author('A7')['display_name'] == 'Ours' and S.author('A50') and S.author('A51') is None
    assert S.institution('I10')['ror'] == 'https://ror.org/x'
    man = json.loads((served / 'snap' / '2026-10-14' / 'manifest.json').read_text())
    assert man['counts']['works'] == 3 and man['counts']['parts'] == 4


def test_a_missing_part_stops_the_merge(served):
    date, parts = S.all_parts()
    S.cmd_filter(0, 2, tmp=served)
    with pytest.raises(SystemExit):
        S.cmd_merge(date, of=2, parts=parts)
