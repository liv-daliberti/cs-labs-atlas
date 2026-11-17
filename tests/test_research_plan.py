"""Research work survives rebuilds, while source/context changes reopen work."""
import copy
import hashlib
import json
import sqlite3
import zlib

import pytest

import research_plan as Q
import school_closeout as C


@pytest.fixture
def research(tmp_path):
    receipt = tmp_path / 'source-review.json'
    receipt.write_text('{"review": "complete current and dated alumni sections read"}')
    pis = [dict(pi='Ada Alpha', names=['Ada Alpha'], periods=[dict(start='2018')]),
           dict(pi='Ben Beta', names=['Ben Beta'])]
    url = 'https://lab.example/people'
    args = dict(school='u', pis=pis, students={}, leads={p['pi']: {url} for p in pis},
                versions={url: dict(sha256='a'*64, status=200, capture_year='2026')},
                blocked={}, policy='policy1', contexts={}, inputs={'roster-evidence.json': 'input1'})

    def resolve(board, index=0, **extra):
        row = board['cases'][index]
        row.update(status='resolved', coverage='whole_source', outcome='reviewed',
                   reviewer='independent-source-reviewer', date='2026-11-16',
                   why='Read complete current and dated alumni entries with individual PI scope.',
                   receipt=dict(path=str(receipt), sha256=hashlib.sha256(receipt.read_bytes()).hexdigest()))
        row.update(extra)
        return board

    return args, resolve, receipt


def test_native_rebuild_reuses_only_explicit_same_pi_source_review(research):
    args, resolve, _ = research
    previous = resolve(Q.plan(**args))
    args['students'] = {'Ada Alpha': [dict(name='New Student')]}
    args['pis'][0]['funnel'] = {'name_hits': 200}
    args['pis'][0]['piBasis'] = {'cs_related': {'dblp_window': 300}}
    current = Q.plan(**args, previous=previous)
    by_pi = {c['binding']['pi']: c for c in current['cases']}
    assert by_pi['Ada Alpha']['status'] == 'resolved'
    assert by_pi['Ada Alpha']['native_members'] == 1
    assert by_pi['Ben Beta']['status'] == 'pending'
    assert current['summary']['reusable_reviews'] == 1
    assert len(current['shared_sources'][0]['contexts']) == 2
    assert 'not membership approval' in current['qualification']


@pytest.mark.parametrize('change', ['source', 'capture_year', 'policy', 'period', 'reviewed_context'])
def test_material_source_or_interpretation_change_reopens_review(research, change):
    args, resolve, _ = research
    previous = resolve(Q.plan(**args))
    if change == 'source':
        next(iter(args['versions'].values()))['sha256'] = 'b'*64
    elif change == 'capture_year':
        next(iter(args['versions'].values()))['capture_year'] = '2027'
    elif change == 'policy':
        args['policy'] = 'policy2'
    elif change == 'period':
        args['pis'][0]['periods'][0]['end'] = '2023'
    else:
        args['contexts']['Ada Alpha'] = [dict(appointment='adjunct')]
    current = Q.plan(**args, previous=previous)
    assert current['summary']['reusable_reviews'] == 0
    assert current['summary']['pending'] == 2


def test_tampered_or_partial_source_review_receipt_never_closes_work(research):
    args, resolve, receipt = research
    previous = resolve(Q.plan(**args), coverage='one_quote')
    assert Q.plan(**args, previous=previous)['summary']['reusable_reviews'] == 0
    resolve(previous)
    receipt.write_text('changed since independent review')
    assert Q.plan(**args, previous=previous)['summary']['reusable_reviews'] == 0


def test_shared_receipt_is_hashed_once_per_plan(research, monkeypatch):
    args, resolve, receipt = research
    previous = resolve(resolve(Q.plan(**args)), index=1)
    original = Q.Path.read_bytes
    reads = []

    def read(path):
        if path == receipt:
            reads.append(path)
        return original(path)

    monkeypatch.setattr(Q.Path, 'read_bytes', read)
    assert Q.plan(**args, previous=previous)['summary']['reusable_reviews'] == 2
    assert len(reads) == 1


def test_no_source_bytes_cannot_be_reused_as_positive_review(research):
    args, resolve, _ = research
    args['versions'] = {}
    previous = resolve(Q.plan(**args))
    assert Q.plan(**args, previous=previous)['summary']['reusable_reviews'] == 0
    resolve(previous, outcome='unavailable', why='Exact original snapshot unavailable; documented search is in receipt.')
    assert Q.plan(**args, previous=previous)['summary']['reusable_reviews'] == 1


def test_new_known_source_prevents_sealing_an_old_closed_board(research, tmp_path, monkeypatch):
    args, resolve, _ = research
    previous = resolve(resolve(Q.plan(**args)), index=1)
    board = tmp_path / 'board.json'
    board.write_text(json.dumps(previous))
    monkeypatch.setattr(Q, 'collect', lambda school, previous: Q.plan(**args, previous=previous))
    assert C.repair_cases(board, 'u')['cases'][0]['status'] == 'resolved'
    args['leads']['Ada Alpha'].add('https://lab.example/alumni')
    with pytest.raises(ValueError, match='Research inventory changed'):
        C.repair_cases(board, 'u')


def test_existing_repair_board_hashes_shared_receipt_once(research, tmp_path, monkeypatch):
    args, resolve, _ = research
    board = resolve(resolve(Q.plan(**args)), index=1)
    del board['research']  # Existing non-research repair boards retain their rules.
    path = tmp_path / 'legacy-board.json'
    path.write_text(json.dumps(board))
    original = C.fingerprint
    calls = []

    def fingerprint(receipt, *a):
        calls.append(receipt)
        return original(receipt, *a)

    monkeypatch.setattr(C, 'fingerprint', fingerprint)
    assert C.repair_cases(path, 'u')['cases'] == board['cases']
    assert len(calls) == 1


def test_rebuild_advice_batches_work_and_identifies_unchanged_reviewed_inputs(research):
    args, resolve, _ = research
    previous = resolve(Q.plan(**args))
    assert Q.plan(**args, previous=previous)['summary']['next_action'] == 'finish_source_batch'
    resolve(previous, index=1)
    assert Q.plan(**args, previous=previous)['summary']['next_action'] == 'check_other_build_dependencies'
    args['inputs']['roster-evidence.json'] = 'input2'
    current = Q.plan(**args, previous=previous)
    assert current['summary']['next_action'] == 'seal_and_rebuild_once'
    assert current['summary']['reusable_reviews'] == 2
    assert current['summary']['changed_reviewed_inputs'] == ['roster-evidence.json']


def test_register_reviews_recounts_stale_totals_and_preserves_shared_pi_contexts(research):
    args, resolve, _ = research
    board = Q.plan(**args)
    decisions = resolve(copy.deepcopy(board))
    board['summary']['pending'] = 672  # A prior manually edited board.
    reviews = dict(school='u', cases=[decisions['cases'][0]])
    current = Q.apply_reviews(board, reviews)
    assert board['cases'][0]['status'] == 'pending'  # Registration is atomic.
    assert current['summary']['pending'] == 1
    assert current['summary']['reusable_reviews'] == 1
    assert current['cases'][1]['status'] == 'pending'
    assert current['cases'][1]['binding']['url'] == current['cases'][0]['binding']['url']
    assert Q.plan(**args, previous=current)['summary']['reusable_reviews'] == 1
    # Exact re-registration resumes; a replacement decision cannot erase work.
    assert Q.apply_reviews(current, reviews) == current
    reviews['cases'][0]['why'] = 'Different interpretation on unchanged evidence'
    with pytest.raises(ValueError, match='must be preserved'):
        Q.apply_reviews(current, reviews)


@pytest.mark.parametrize('invalid', ['wrong_school', 'unknown_id', 'duplicate', 'context', 'source',
                                    'partial', 'missing_receipt', 'bad_date', 'not_an_object'])
def test_registration_refuses_stale_or_unverifiable_review_without_partial_updates(research, invalid):
    args, resolve, _ = research
    board = Q.plan(**args)
    reviewed = resolve(resolve(copy.deepcopy(board)), index=1)
    reviews = dict(school='u', cases=reviewed['cases'])
    row = reviews['cases'][1]
    if invalid == 'wrong_school':
        reviews['school'] = 'other'
    elif invalid == 'unknown_id':
        row['id'] = 'source-not-in-this-inventory'
    elif invalid == 'duplicate':
        reviews['cases'].append(copy.deepcopy(row))
    elif invalid == 'context':
        row['binding']['context_sha256'] = 'different-appointment'
    elif invalid == 'source':
        row['binding']['source']['sha256'] = 'b' * 64
    elif invalid == 'partial':
        row['coverage'] = 'one_quote'
    elif invalid == 'missing_receipt':
        row['receipt'] = {}
    elif invalid == 'bad_date':
        row['date'] = '2026-02-30'
    else:
        reviews['cases'][1] = 'not a review'
    original = copy.deepcopy(board)
    with pytest.raises(ValueError):
        Q.apply_reviews(board, reviews)
    assert board == original


def test_batch_reads_shared_source_once_without_approving_other_pi(research):
    args, resolve, _ = research
    board = Q.plan(**args)
    batch = Q.review_batch(board, limit=1)
    assert batch['summary'] == dict(pending_cases=2, pending_sources=1, selected_sources=1, selected_cases=2)
    assert {c['binding']['pi'] for c in batch['sources'][0]['cases']} == {'Ada Alpha', 'Ben Beta'}
    assert all(c['status'] == 'pending' for c in batch['sources'][0]['cases'])
    current = Q.apply_reviews(board, dict(school='u', cases=[resolve(copy.deepcopy(board))['cases'][0]]))
    assert Q.review_batch(current)['summary']['pending_cases'] == 1
    assert board['summary']['pending'] == 2


def test_batch_keeps_unknown_leads_separate_and_prioritizes_saved_sparse_sources(research):
    args, _, _ = research
    args['pis'] += [dict(pi='Unknown One'), dict(pi='Unknown Two'), dict(pi='Blocked')]
    args['leads']['Blocked'] = {'https://blocked.example/people'}
    args['blocked']['blocked.example'] = 'robots_disallowed'
    args['students']['Ada Alpha'] = [dict(name='Member')]
    board = Q.plan(**args)
    batch = Q.review_batch(board, limit=2)
    assert batch['summary']['pending_sources'] == 4
    assert batch['summary']['selected_sources'] == 2
    assert batch['sources'][0]['next_action'] == 'inspect_saved_source'
    assert len(batch['sources'][0]['cases']) == 2
    assert len(batch['sources'][1]['cases']) == 1
    assert Q.review_batch(board)['sources'][-1]['next_action'] == 'respect_recorded_refusal'
    for limit in (0, -1, True):
        with pytest.raises(ValueError, match='positive integer'):
            Q.review_batch(board, limit)


def test_review_cli_refreshes_bindings_and_never_overwrites_previous_work(research, tmp_path, monkeypatch, capsys):
    args, resolve, _ = research
    board = Q.plan(**args)
    reviewed = resolve(copy.deepcopy(board))
    reviews = tmp_path / 'reviews.json'
    reviews.write_text(json.dumps(dict(school='u', cases=[reviewed['cases'][0]])))
    out = tmp_path / 'registered.json'
    monkeypatch.setattr(Q, 'collect', lambda *a: copy.deepcopy(board))
    assert C.main(['research', 'u', '--reviews', str(reviews), '--out', str(out), '--json']) == 0
    assert json.loads(capsys.readouterr().out)['summary']['pending'] == 1
    assert json.loads(out.read_text())['summary']['pending'] == 1
    # A changed context detected during refresh cannot reuse the old decision.
    board['cases'][0]['binding']['context_sha256'] = 'changed'
    refused = tmp_path / 'refused.json'
    assert C.main(['research', 'u', '--reviews', str(reviews), '--out', str(refused)]) == 1
    assert not refused.exists()
    assert json.loads(out.read_text())['summary']['pending'] == 1
    batch = tmp_path / 'batch.json'
    assert C.main(['research-batch', 'u', '--batch-size', '1', '--out', str(batch)]) == 0
    assert json.loads(batch.read_text())['summary']['selected_sources'] == 1


def test_all_known_sources_are_planned_before_next_build_without_eight_url_cap():
    pi = dict(pi='Ada Alpha', lab=dict(url='https://lab.example/home'))
    students = {'Ada Alpha': [dict(relations=[dict(type='researched_membership',
        sources=[dict(url=f'https://lab.example/people/{n}')])]) for n in range(12)]}
    docs = {'roster-evidence.json': [dict(pi='Ada Alpha', students=[dict(url='https://lab.example/new-roster',
              supporting_sources=[dict(url='https://lab.example/own-student-bio')])])],
            'extra-lab-pages.json': {'Ada Alpha': ['https://lab.example/alumni']}}
    leads = Q.source_leads([pi], students, {}, docs)
    assert len(leads['Ada Alpha']) == 16
    assert 'https://lab.example/new-roster' in leads['Ada Alpha']
    assert 'https://lab.example/own-student-bio' in leads['Ada Alpha']


def test_context_updates_are_local_to_the_affected_pi(research):
    args, resolve, _ = research
    previous = resolve(resolve(Q.plan(**args)), index=1)
    docs = {'faculty-periods.json': [dict(name='Ada Alpha', facultyEnd='2024')],
            'census-overrides-school.json': {'Ben Beta': {'aliases': ['B. Beta']}}}
    args['contexts'] = Q.context_index(docs, {'Ada Alpha', 'Ben Beta'})
    # Only Ada's actual context changes relative to this explicit baseline.
    previous = resolve(resolve(Q.plan(**args)), index=1)
    docs['faculty-periods.json'][0]['facultyEnd'] = '2023'
    args['contexts'] = Q.context_index(docs, {'Ada Alpha', 'Ben Beta'})
    by_pi = {c['binding']['pi']: c for c in Q.plan(**args, previous=previous)['cases']}
    assert by_pi['Ada Alpha']['status'] == 'pending'
    assert by_pi['Ben Beta']['status'] == 'resolved'


def test_reused_lab_preserves_each_evidence_record_in_context(research):
    args, resolve, _ = research
    args['pis'][0]['lab'] = {'unitId': 'lab1', 'evidence': [dict(url='https://lab.example', quote='Ada Alpha directs lab')]}
    previous = resolve(Q.plan(**args))
    args['pis'][0]['lab']['evidence'][0]['quote'] = 'Ada Alpha co-directs lab with Ben Beta'
    current = Q.plan(**args, previous=previous)
    assert current['summary']['reusable_reviews'] == 0


def test_cache_read_is_offline_and_hash_verified(tmp_path):
    cache = tmp_path / 'captures.sqlite'
    raw = b'<html><p>Actual roster</p></html>'
    with sqlite3.connect(cache) as conn:
        conn.execute('create table live (url text, fetched_at text, status int, sha256 text, raw_zlib blob)')
        conn.execute('create table blocked (host text, why text)')
        conn.execute('insert into live values (?,?,?,?,?)',
                     ('https://lab.example/people', '2026-11-16T12:00:00', 200,
                      hashlib.sha256(raw).hexdigest(), zlib.compress(raw)))
        conn.execute('insert into blocked values (?,?)', ('www.refused.example', 'robots_disallowed'))
    before = cache.read_bytes()
    versions, blocked = Q.cached_sources(cache, {'https://lab.example/people', 'https://unknown.example/'})
    assert versions['https://lab.example/people']['capture_year'] == '2026'
    assert blocked['refused.example'] == 'robots_disallowed'
    assert cache.read_bytes() == before
    with sqlite3.connect(cache) as conn:
        conn.execute('update live set sha256=?', ('0'*64,))
    with pytest.raises(ValueError, match='bytes do not match'):
        Q.cached_sources(cache, {'https://lab.example/people'})


def test_existing_school_cache_prevents_false_missing_source_and_keeps_reviews_pending(tmp_path, monkeypatch):
    url = 'https://lab.example/people'
    raw = b'<html>Complete lab roster, never read by a reviewer yet</html>'
    school_cache = tmp_path / 'school-captures.sqlite'
    with sqlite3.connect(school_cache) as conn:
        conn.execute('create table live (url text, fetched_at text, status int, sha256 text, raw_zlib blob)')
        conn.execute('insert into live values (?,?,?,?,?)',
                     (url, '2026-11-17', 200, hashlib.sha256(raw).hexdigest(), zlib.compress(raw)))
    before = school_cache.read_bytes()
    monkeypatch.setattr(Q.S, 'get', lambda school: {'status': 'onboarding'})
    monkeypatch.setattr(Q.R, '_pis', lambda school: [dict(pi='Ada Alpha', lab=dict(url=url))])
    monkeypatch.setattr(Q.R, '_students', lambda school: {})
    monkeypatch.setattr(Q.R, '_audit', lambda school: {})
    monkeypatch.setattr(Q, 'reviewed_inputs', lambda school: ({}, {}))
    monkeypatch.setattr(Q, 'POLICY_FILES', ())
    monkeypatch.setattr(Q.P, 'data', lambda name, school: tmp_path / name)
    board = Q.collect('u')
    assert board['summary']['sources_with_bytes'] == 1
    assert board['summary']['pending'] == 1
    assert board['cases'][0]['next_action'] == 'inspect_saved_source'
    assert board['cases'][0]['status'] == 'pending'
    assert len(board['capture_stores']) == 4
    assert school_cache.read_bytes() == before
    assert not (tmp_path / 'student-recall-captures.sqlite').exists()


def test_all_cache_versions_and_refusals_survive_without_path_binding(tmp_path, monkeypatch):
    url = 'https://lab.example/people'
    recall, school = tmp_path / 'recall.sqlite', tmp_path / 'school.sqlite'
    snapshots = {recall: ({url: dict(sha256='a'*64, status=200, capture_year='2026')},
                          {'lab.example': 'robots_disallowed'}),
                 school: ({url: dict(sha256='b'*64, status=200, capture_year='2025')},
                          {'lab.example': 'bot_challenge'})}
    reads = []

    def cached(path, urls):
        reads.append(path)
        return copy.deepcopy(snapshots[path])

    monkeypatch.setattr(Q, 'cached_sources', cached)
    versions, blocked = Q.source_caches([recall, school, recall], {url})
    assert reads == [recall, school]
    assert versions[url]['sha256'] == 'a'*64
    assert versions[url]['snapshots'] == [dict(sha256='b'*64, status=200, capture_year='2025')]
    assert blocked == {'lab.example': 'bot_challenge; robots_disallowed'}
    # Adding a local evidence pointer cannot erase the earlier cached version.
    raw = tmp_path / 'saved.html'
    raw.write_bytes(b'preserved original')
    docs = {'roster-evidence.json': [dict(url=url, source_capture=str(raw),
             sha256=hashlib.sha256(raw.read_bytes()).hexdigest(), captured='2024')]}
    merged = Q.saved_snapshots(docs, {'Ada Alpha': {url}}, versions)
    assert len(merged[url]['snapshots']) == 2
    assert versions[url]['snapshots'][0] in merged[url]['snapshots']


def test_failed_request_without_bytes_is_not_readable_source(tmp_path):
    cache = tmp_path / 'school.sqlite'
    url = 'https://missing.example/people'
    with sqlite3.connect(cache) as conn:
        conn.execute('create table live (url text, fetched_at text, status int, sha256 text, raw_zlib blob)')
        conn.execute('insert into live values (?,?,?,?,?)', (url, '2026-11-17', 404, None, None))
    versions, _ = Q.source_caches([cache], {url})
    assert versions[url] == dict(status=404, capture_year='2026')
    assert not Q.has_source_bytes(versions[url])
    assert not Q.has_source_bytes(dict(snapshots=[versions[url]]))
    # Missing/tampered original bytes on an asserted successful response fail closed.
    with sqlite3.connect(cache) as conn:
        conn.execute('update live set status=200')
    with pytest.raises(ValueError, match='bytes do not match'):
        Q.source_caches([cache], {url})


def test_archive_only_optional_school_cache_preserves_recall_source_and_refusals(tmp_path):
    recall, school = tmp_path / 'recall.sqlite', tmp_path / 'school.sqlite'
    url, raw = 'https://lab.example/people', b'Original saved roster'
    with sqlite3.connect(recall) as conn:
        conn.execute('create table live (url text, fetched_at text, status int, sha256 text, raw_zlib blob)')
        conn.execute('insert into live values (?,?,?,?,?)',
                     (url, '2026-11-17', 200, hashlib.sha256(raw).hexdigest(), zlib.compress(raw)))
    with sqlite3.connect(school) as conn:
        conn.execute('create table pages (url text)')
        conn.execute('create table blocked (host text, why text)')
        conn.execute('insert into blocked values (?,?)', ('blocked.example', 'robots_disallowed'))
    before = {p: p.read_bytes() for p in (recall, school)}
    versions, blocked = Q.source_caches([recall, school], {url}, optional_live=[school])
    assert versions[url]['sha256'] == hashlib.sha256(raw).hexdigest()
    assert blocked == {'blocked.example': 'robots_disallowed'}
    assert {p: p.read_bytes() for p in (recall, school)} == before
    with pytest.raises(ValueError, match='no live table'):
        Q.cached_sources(school, {url})  # Required recall caches still fail closed.


def test_reviewed_input_digest_ignores_formatting_and_recall_signoff(tmp_path, monkeypatch):
    roster, recall = tmp_path / 'roster-evidence.json', tmp_path / 'student-recall-check.json'
    roster.write_text('{"a": 1, "b": 2}')
    recall.write_text('{}')
    monkeypatch.setattr(Q.P, 'DATA_FILES', [entry for entry in Q.P.DATA_FILES if entry[0] in {roster.name, recall.name}])
    monkeypatch.setattr(Q.P, 'data', lambda name, school: tmp_path / name)
    before, _ = Q.reviewed_inputs('u')
    roster.write_text('{\n "b": 2, "a": 1\n}')
    recall.write_text('{"new signoff": true}')
    assert Q.reviewed_inputs('u')[0] == before
    roster.write_text('{"a": 2, "b": 2}')
    assert Q.reviewed_inputs('u')[0] != before


def test_exact_saved_capture_reused_without_cache_or_path_binding(tmp_path):
    raw = tmp_path / 'original.html'
    raw.write_text('<html>Actual preserved primary roster</html>')
    sha = hashlib.sha256(raw.read_bytes()).hexdigest()
    url = 'https://lab.example/people'
    row = dict(url=url, sha256=sha, source_capture=str(raw), captured='2025-11-16')
    docs = {'roster-evidence.json': [dict(pi='Ada Alpha', students=[row])]}
    leads = {'Ada Alpha': {url}}
    before = Q.saved_snapshots(docs, leads, {})
    assert before[url]['snapshots'] == [dict(sha256=sha, capture_year='2025', kind='saved_source_file')]
    assert 'status' not in before[url]
    moved = tmp_path / 'moved.html'
    moved.write_bytes(raw.read_bytes())
    row['source_capture'] = str(moved)
    assert Q.saved_snapshots(docs, leads, {}) == before
    moved.write_text('wrong source bytes')
    assert Q.saved_snapshots(docs, leads, {}) == {}


def test_collect_does_not_create_missing_data_directories(tmp_path, monkeypatch):
    monkeypatch.setattr(Q.S, 'get', lambda school: {'status': 'onboarding'})
    monkeypatch.setattr(Q.R, '_pis', lambda school: [dict(pi='Ada Alpha')])
    monkeypatch.setattr(Q.R, '_students', lambda school: {})
    monkeypatch.setattr(Q.R, '_audit', lambda school: {})
    monkeypatch.setattr(Q, 'reviewed_inputs', lambda school: ({}, {}))
    monkeypatch.setattr(Q, 'POLICY_FILES', ())
    monkeypatch.setattr(Q.P, 'CODE', tmp_path)
    monkeypatch.setattr(Q.P, 'data', lambda name, school: tmp_path / 'missing' / name)

    def no_writes(*args, **kwargs):
        pytest.fail('Planner used a writing data-path accessor')

    monkeypatch.setattr(Q.P, 'data_w', no_writes)
    assert Q.collect('u')['summary']['pending'] == 1
    assert not list(tmp_path.iterdir())


def test_research_cli_preserves_existing_work_and_never_writes_without_out(research, tmp_path, monkeypatch, capsys):
    args, _, _ = research
    board = Q.plan(**args)
    monkeypatch.setattr(Q, 'collect', lambda *a: copy.deepcopy(board))
    before = {p: p.read_bytes() for p in tmp_path.iterdir()}
    assert C.main(['research', 'u', '--json']) == 0
    assert json.loads(capsys.readouterr().out)['summary']['pending'] == 2
    assert {p: p.read_bytes() for p in tmp_path.iterdir()} == before
    out = tmp_path / 'plan.json'
    assert C.main(['research', 'u', '--out', str(out)]) == 0
    original = out.read_bytes()
    assert C.main(['research', 'u', '--out', str(out)]) == 1
    assert out.read_bytes() == original


def make_audit_cache(path, entries):
    with sqlite3.connect(path) as conn:
        conn.execute('create table captures (id integer primary key, url text, capture_url text, final_url text, '
                     'fetched_at text, status int, sha256 text, content blob, error text)')
        for entry in entries:
            raw = entry.get('raw', b'<html>Actual named members</html>')
            sha = entry.get('sha256', hashlib.sha256(raw).hexdigest() if raw is not None else None)
            conn.execute('insert into captures values (NULL,?,?,?,?,?,?,?,?)',
                         (entry['url'], entry.get('capture_url'), entry.get('final_url'),
                          entry.get('fetched_at', '2026-11-17T12:00:00+00:00'), entry.get('status', 200),
                          sha, zlib.compress(raw) if raw is not None else None, entry.get('error')))


def test_collect_finds_previously_invisible_audit_bytes_without_accepting_or_writing(tmp_path, monkeypatch):
    url = 'https://lab.example/people'
    audit = tmp_path / 'labpage-audit-captures.sqlite'
    make_audit_cache(audit, [dict(url=url)])
    before = audit.read_bytes()
    monkeypatch.setattr(Q.S, 'get', lambda school: {'status': 'onboarding'})
    monkeypatch.setattr(Q.R, '_pis', lambda school: [dict(pi='Ada Alpha', lab=dict(url=url))])
    monkeypatch.setattr(Q.R, '_students', lambda school: {})
    monkeypatch.setattr(Q.R, '_audit', lambda school: {})
    monkeypatch.setattr(Q.R, 'capture', lambda *a, **kw: pytest.fail('inventory must not fetch'))
    monkeypatch.setattr(Q, 'reviewed_inputs', lambda school: ({}, {}))
    monkeypatch.setattr(Q, 'POLICY_FILES', ())
    monkeypatch.setattr(Q.P, 'data', lambda name, school: tmp_path / name)
    board = Q.collect('u')
    assert board['summary']['sources_with_bytes'] == 1
    assert board['summary']['pending'] == 1 and board['summary']['reusable_reviews'] == 0
    assert board['cases'][0]['next_action'] == 'inspect_saved_source'
    assert board['cases'][0]['status'] == 'pending'
    assert audit.read_bytes() == before
    assert list(tmp_path.iterdir()) == [audit]


def test_audit_versions_remain_flat_and_archive_redirect_dates_use_actual_response(tmp_path):
    url = 'https://lab.example/people'
    recall, audit = tmp_path / 'recall.sqlite', tmp_path / 'audit.sqlite'
    with sqlite3.connect(recall) as conn:
        conn.execute('create table live (url text, fetched_at text, status int, sha256 text, raw_zlib blob)')
        conn.execute('insert into live values (?,?,?,?,?)',
                     (url, '2019-11-01', 200, hashlib.sha256(b'2019 roster').hexdigest(), zlib.compress(b'2019 roster')))
    requested = 'https://web.archive.org/web/20200101000000id_/' + url
    actual = 'https://web.archive.org/web/20210101000000id_/' + url
    make_audit_cache(audit, [dict(url=url, raw=b'2020 roster', capture_url=requested),
                             dict(url=url, raw=b'2021 roster', capture_url=requested, final_url=actual)])
    before = {path: path.read_bytes() for path in (recall, audit)}
    versions, _ = Q.source_caches([recall, audit], {url, requested}, audit_paths=[audit])
    main = versions[url]
    assert main['capture_year'] == '2019'
    assert {item['capture_year'] for item in main['snapshots']} == {'2020', '2021'}
    assert all('snapshots' not in item for item in main['snapshots'])
    assert versions[requested]['capture_year'] == '2021'
    assert versions[requested]['snapshots'][0]['capture_year'] == '2020'
    assert {path: path.read_bytes() for path in (recall, audit)} == before


def test_identical_audit_copy_does_not_change_existing_scientific_binding(tmp_path):
    url, raw = 'https://lab.example/people', b'Identical original roster'
    recall, audit = tmp_path / 'recall.sqlite', tmp_path / 'audit.sqlite'
    with sqlite3.connect(recall) as conn:
        conn.execute('create table live (url text, fetched_at text, status int, sha256 text, raw_zlib blob)')
        conn.execute('insert into live values (?,?,?,?,?)',
                     (url, '2026-11-17', 200, hashlib.sha256(raw).hexdigest(), zlib.compress(raw)))
    make_audit_cache(audit, [dict(url=url, raw=raw)])
    baseline, _ = Q.source_caches([recall], {url})
    merged, _ = Q.source_caches([recall, audit], {url}, audit_paths=[audit])
    assert merged == baseline
    assert 'snapshots' not in merged[url]


@pytest.mark.parametrize('bad', [dict(sha256='0' * 64), dict(raw=None, sha256='a' * 64)])
def test_audit_success_with_missing_or_corrupt_original_bytes_fails_closed(tmp_path, bad):
    audit = tmp_path / 'audit.sqlite'
    url = 'https://lab.example/people'
    make_audit_cache(audit, [dict(url=url), dict(url=url, **bad)])
    with pytest.raises(ValueError, match='audit source bytes do not match'):
        Q.cached_audit_sources(audit, {url})


def test_audit_refusals_on_other_paths_and_http200_challenges_are_preserved(tmp_path):
    audit = tmp_path / 'audit.sqlite'
    bot = 'https://challenged.example/people'
    make_audit_cache(audit, [dict(url='https://blocked.example/other', status=None, raw=None, error='robots-disallowed'),
                             dict(url=bot, raw=b'Verify you are human', status=200, error='bot-challenge'),
                             dict(url='https://rate.example/other', status=429, raw=None),
                             dict(url='https://archived.example/old', status=403, raw=None,
                                  capture_url='https://web.archive.org/web/20160101000000id_/https://archived.example/old')])
    versions, refusals = Q.cached_audit_sources(audit, {bot, 'https://blocked.example/people'})
    assert versions[bot]['status'] == 999 and versions[bot]['http_status'] == 200
    assert versions[bot]['capture_error'] == 'bot-challenge'
    assert 'robots-disallowed' in refusals['blocked.example']
    assert 'bot-challenge' in refusals['challenged.example']
    assert 'HTTP 429' in refusals['rate.example']
    assert 'web.archive.org' in refusals and 'archived.example' not in refusals
    assert 'https://blocked.example/people' not in versions


def test_undated_archive_url_cannot_be_presented_as_later_fetch_year(tmp_path):
    audit = tmp_path / 'audit.sqlite'
    url = 'https://lab.example/people'
    make_audit_cache(audit, [dict(url=url, capture_url='https://web.archive.org/web/unknown/' + url)])
    with pytest.raises(ValueError, match='no dated timestamp'):
        Q.cached_audit_sources(audit, {url})


def test_absent_audit_cache_is_not_created_and_existing_unknown_schema_is_rejected(tmp_path):
    audit = tmp_path / 'audit.sqlite'
    assert Q.cached_audit_sources(audit, {'https://lab.example/'}) == ({}, {})
    assert not audit.exists()
    with sqlite3.connect(audit) as conn:
        conn.execute('create table unrelated (value text)')
    with pytest.raises(ValueError, match='no captures table'):
        Q.cached_audit_sources(audit, {'https://lab.example/'})
