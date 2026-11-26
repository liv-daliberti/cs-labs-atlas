"""A recorded public POST response must never masquerade as a GET cache row."""
from copy import deepcopy
import hashlib
import json
import sqlite3

import pytest

import cs_related_school as C


def install(tmp_path, monkeypatch, *, serial='112697', person='Avery Scientist', contact=True, request_serial=None):
    endpoint = 'https://api.reporter.nih.gov/v2/projects/search'
    request = dict(criteria=dict(project_num_split=dict(activity_code='R21', ic_code='HD', serial_num=request_serial or serial)), limit=5)
    body = dict(results=[dict(appl_id=int(serial), project_num='1R21HD' + serial + '-01A1',
                             principal_investigators=[dict(full_name=person, is_contact_pi=contact)])])
    raw = json.dumps(body).encode()
    sha = hashlib.sha256(raw).hexdigest()
    captured = '2026-11-24T20:00:00+00:00'
    receipt = dict(queries=[dict(url=endpoint, method='POST', status=200, request_json=request,
                                 sha256=sha, fetched_at=captured)])
    receipt_raw = json.dumps(receipt).encode()
    receipt_sha = hashlib.sha256(receipt_raw).hexdigest()
    folder = tmp_path / 'metadata/nih-reporter-post'
    folder.mkdir(parents=True, exist_ok=True)
    response_file = folder / (sha + '.json')
    response_file.write_bytes(raw)
    (folder / (receipt_sha + '.json')).write_bytes(receipt_raw)
    fingerprint = hashlib.sha256(json.dumps(request, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    entry = dict(name=person, unit='Pediatrics', url=endpoint, method='POST', status=200, request_json=request,
                 request_fingerprint_sha256=fingerprint, sha256=sha, quote=person,
                 json_pointer='/results/0/principal_investigators/0/full_name', observed='20261124',
                 post_source_binding=dict(method='POST', request_url=endpoint, request_json=request,
                     request_fingerprint_sha256=fingerprint, response_sha256=sha, response_file=sha + '.json',
                     receipt_sha256=receipt_sha, receipt_file=receipt_sha + '.json',
                     receipt_query_index=0, status=200, captured=captured))
    monkeypatch.setattr(C.P, 'store', lambda key: tmp_path)
    return entry, response_file


def cache():
    con = sqlite3.connect(':memory:')
    con.execute('create table captures (sha256 text, text text)')
    con.execute('create table live (url text, sha256 text, raw_zlib blob)')
    return con


def test_contact_pi_original_replays_without_get_cache_write(tmp_path, monkeypatch):
    entry, source = install(tmp_path, monkeypatch)
    before = source.read_bytes()
    con = cache()
    result = C.hand_evidence('harvard', con, entries=[entry])
    assert result['avery scientist'][0]['quote'] == 'Avery Scientist'
    assert source.read_bytes() == before
    assert con.execute('select count(*) from live').fetchone()[0] == 0
    assert con.execute('select count(*) from captures').fetchone()[0] == 0


def test_distinct_posts_at_one_endpoint_keep_distinct_originals(tmp_path, monkeypatch):
    first, _ = install(tmp_path, monkeypatch)
    second, _ = install(tmp_path, monkeypatch, serial='112698', person='Another Scientist')
    result = C.hand_evidence('harvard', cache(), entries=[first, second])
    assert set(result) == {'avery scientist', 'another scientist'}
    assert first['sha256'] != second['sha256']


@pytest.mark.parametrize('options', [dict(contact=False), dict(request_serial='999999')])
def test_valid_original_of_other_role_or_project_cannot_establish_contact_pi(tmp_path, monkeypatch, options):
    entry, _ = install(tmp_path, monkeypatch, **options)
    with pytest.raises(SystemExit):
        C.hand_evidence('harvard', cache(), entries=[entry])


@pytest.mark.parametrize('failure', ['response_bytes', 'missing', 'method', 'endpoint', 'fingerprint',
                                   'request', 'receipt', 'path', 'pointer', 'summary'])
def test_wrong_or_stale_post_provenance_fails_closed(tmp_path, monkeypatch, failure):
    entry, source = install(tmp_path, monkeypatch)
    entry = deepcopy(entry)
    proof = entry['post_source_binding']
    if failure == 'response_bytes': source.write_bytes(source.read_bytes() + b' ')
    elif failure == 'missing': source.unlink()
    elif failure == 'method': entry['method'] = 'GET'
    elif failure == 'endpoint': entry['url'] = 'https://unrelated.example/source'
    elif failure == 'fingerprint': proof['request_fingerprint_sha256'] = '0' * 64
    elif failure == 'request': proof['request_json']['limit'] = 6
    elif failure == 'receipt': proof['receipt_sha256'] = '0' * 64
    elif failure == 'path': proof['response_file'] = '../source.json'
    elif failure == 'pointer': entry['json_pointer'] = '/results/0/project_num'
    else:
        entry['source_summary'] = dict(appl_id=999)
        entry['source_summary_json_pointers'] = dict(appl_id='/results/0/appl_id')
    with pytest.raises(SystemExit):
        C.hand_evidence('harvard', cache(), entries=[entry])
