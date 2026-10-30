"""The unavailability ledger (docs/UNAVAILABLE.md, R-AUD-10; 2026-10-30): lab_paper_copies.attach_ledger, the evidence
check's unavailable_* gate, the organized tree's papers.csv columns, the release manifest counts and the regression swings."""
import csv
import gzip
import json
import os
import time
from datetime import datetime, timedelta, timezone

import build_regression as br
import evidence_check
import lab_paper_copies
import make_release
import organize_tree

SHA = 'a' * 64
NOW = datetime.now(timezone.utc)


def iso(d):
    return d.strftime('%Y-%m-%dT%H:%M:%SZ')


def _jsonl(p, rows):
    with gzip.open(p, 'wt') as f:
        f.write(''.join(json.dumps(r) + '\n' for r in rows))


def _school(tmp_path, fx, ledger=True, drop=(), checked_at=None, counted_at=None):
    """A princeton package (clean on every other evidence category) with the fixture's copies.json and ledger."""
    d = tmp_path / 'princeton'
    d.mkdir(parents=True)
    pis = [dict(pi='P', periods=[dict(id='p1', start='2010', end=None, evidence=[dict(url='u', sha256=SHA, quote='Professor P')])],
                listings=[])]
    students = {'P': [dict(person='s1', name='S One', relations=[dict(type='researched_advising', sources=[dict(url='u', sha256=SHA, quote='Adviser: P')])])]}
    papers = [dict(pi='P', work=k, oa=c['oa'], doi=c['doi'], year=c['year'], title=f'Paper {k}', authorship=dict(school_via=['Princeton University']),
                   appointment=dict(periodId='p1'))
              for k, c in fx['copies']['papers'].items()]
    (d / 'pis.json').write_text(json.dumps(pis)); (d / 'students.json').write_text(json.dumps(students))
    _jsonl(d / 'lab_papers.jsonl.gz', papers)
    _jsonl(d / 'student_papers.jsonl.gz', [dict(pi='P', student='s1', name='S One', work='W2', oa='https://openalex.org/W2', basis='collection_person_link')])
    cop = json.loads(json.dumps(fx['copies']))
    if counted_at:
        cop['summary']['counted_at'] = counted_at
    (d / 'copies.json').write_text(json.dumps(cop))
    if ledger:
        _jsonl(d / 'unavailable.jsonl.gz', [dict(r, checked_at=checked_at or iso(NOW)) for r in fx['ledger'] if r['key'] not in drop])
        (d / 'unavailable-summary.json').write_text(json.dumps(fx['ledger_summary']))
    return d


def _gate(tmp_path, monkeypatch, root, incomplete_max=1):
    wl = tmp_path / 'whitelist.json'
    wl.write_text(json.dumps({'unavailable_incomplete': {'princeton': {'max': incomplete_max, 'why': 'test: CORE not reached yet'}}}))
    monkeypatch.setattr(evidence_check, 'WHITELIST', wl)
    out = tmp_path / 'out'; out.mkdir(exist_ok=True)
    rc = evidence_check.main(['--dir', str(root), '--out', str(out), 'princeton'])
    return rc, json.loads((out / 'EVIDENCE-CHECK.json').read_text())


def test_attach_ledger_sets_the_fields(tmp_path, fixture_json):
    fx = fixture_json('unavailable-ledger.json')
    d = _school(tmp_path, fx)
    doc = lab_paper_copies.attach_ledger('princeton', d)
    p = json.loads((d / 'copies.json').read_text())
    assert p == doc
    assert p['papers']['W2']['unavailable_reason'] == 'paywall_only'
    assert p['papers']['W2']['unavailable_summary'].startswith('Listed open at IEEE')
    assert p['papers']['W3']['unavailable_reason'] == 'no_doi_no_match'
    assert p['papers']['W4']['unavailable_reason'] == 'incomplete_check'
    assert 'unavailable_reason' not in p['papers']['W1'] and 'unavailable_summary' not in p['papers']['W1']  # local now: stale row ignored
    s = p['summary']
    assert (s['unavailable:paywall_only'], s['unavailable:no_doi_no_match'], s['unavailable:incomplete_check']) == (1, 1, 1)
    assert s['ledger_built_at'] == '2026-10-30T12:00:00Z' and s['local'] == 1  # the coverage counts stay
    # a paper that became local since: its reason is cleared on the next attach, and the counts follow
    p['papers']['W2']['status'] = 'downloaded'
    (d / 'copies.json').write_text(json.dumps(p))
    p = lab_paper_copies.attach_ledger('princeton', d)
    assert 'unavailable_reason' not in p['papers']['W2'] and 'unavailable:paywall_only' not in p['summary']


def test_gate_passes_when_covered(tmp_path, monkeypatch, fixture_json):
    root = _school(tmp_path / 'r', fixture_json('unavailable-ledger.json'), counted_at=iso(NOW - timedelta(hours=1))).parent
    rc, ev = _gate(tmp_path, monkeypatch, root)
    res = ev['schools']['princeton']
    assert rc == 0 and ev['ok'], ev['over_whitelist']
    assert res['unavailable_missing'] == dict(n=0, of=3, samples=[], whitelisted=0)
    assert res['unavailable_stale']['n'] == 0 and res['unavailable_incomplete']['n'] == 1


def test_gate_fails_on_a_missing_entry(tmp_path, monkeypatch, fixture_json):
    root = _school(tmp_path / 'r', fixture_json('unavailable-ledger.json'), drop=('W3',)).parent
    rc, ev = _gate(tmp_path, monkeypatch, root)
    assert rc == 1 and [x['category'] for x in ev['over_whitelist']] == ['unavailable_missing']
    assert ev['schools']['princeton']['unavailable_missing']['samples'] == ['W3 | not_in_catalog']


def test_gate_fails_without_a_ledger(tmp_path, monkeypatch, fixture_json):
    root = _school(tmp_path / 'r', fixture_json('unavailable-ledger.json'), ledger=False).parent
    rc, ev = _gate(tmp_path, monkeypatch, root)
    assert rc == 1 and ev['schools']['princeton']['unavailable_missing']['n'] == 3  # every non-local paper, not the local W1


def test_gate_fails_on_a_stale_entry(tmp_path, monkeypatch, fixture_json):
    fx = fixture_json('unavailable-ledger.json')
    # checked before the package was rebuilt (lab_papers.jsonl.gz is newer)
    root = _school(tmp_path / 'a', fx, checked_at=iso(NOW - timedelta(days=2))).parent
    rc, ev = _gate(tmp_path, monkeypatch, root)
    assert rc == 1 and ev['schools']['princeton']['unavailable_stale']['n'] == 3
    # checked after the build, but before the copies were counted again
    d = _school(tmp_path / 'b', fx, checked_at=iso(NOW - timedelta(hours=1)), counted_at=iso(NOW))
    t = time.time() - 3 * 3600
    os.utime(d / 'lab_papers.jsonl.gz', (t, t))
    rc, ev = _gate(tmp_path, monkeypatch, d.parent)
    assert rc == 1 and ev['schools']['princeton']['unavailable_stale']['n'] == 3
    # within the tolerance: not stale
    d = _school(tmp_path / 'c', fx, checked_at=iso(NOW - timedelta(seconds=60)), counted_at=iso(NOW))
    os.utime(d / 'lab_papers.jsonl.gz', (t, t))
    rc, ev = _gate(tmp_path, monkeypatch, d.parent)
    assert rc == 0 and ev['schools']['princeton']['unavailable_stale']['n'] == 0


def test_gate_fails_on_incomplete_over_its_whitelist(tmp_path, monkeypatch, fixture_json):
    root = _school(tmp_path / 'r', fixture_json('unavailable-ledger.json')).parent
    rc, ev = _gate(tmp_path, monkeypatch, root, incomplete_max=0)
    assert rc == 1 and ev['over_whitelist'] == [dict(school='princeton', category='unavailable_incomplete', n=1, whitelisted=0)]
    assert ev['schools']['princeton']['unavailable_incomplete']['samples'] == ['W4 | missing core']


def test_papers_csv_has_the_ledger_columns(tmp_path, monkeypatch, fixture_json):
    fx = fixture_json('unavailable-ledger.json')
    d = _school(tmp_path / 'release' / 'hierarchy', fx)
    lab_paper_copies.attach_ledger('princeton', d)
    c = json.loads((d / 'copies.json').read_text())  # W3 as a copies.json written before the ledger: read from the ledger file
    del c['papers']['W3']['unavailable_reason'], c['papers']['W3']['unavailable_summary']
    (d / 'copies.json').write_text(json.dumps(c))
    pdf = tmp_path / 'store' / 'c1.pdf'; pdf.parent.mkdir(); pdf.write_bytes(b'%PDF-1.4 test')
    monkeypatch.setattr(organize_tree, 'H', d.parent)
    monkeypatch.setattr(organize_tree, 'OUT', tmp_path / 'tree')
    monkeypatch.setattr(organize_tree, 'RELEASE', dict(id='test', dir=str(d.parent.parent), copies='release'))
    monkeypatch.setattr(organize_tree, 'stored_files', lambda school: {'c1': pdf})
    organize_tree.build('princeton', {})
    rows = {r['work']: r for r in csv.DictReader(open(tmp_path / 'tree/princeton/labs/p/papers.csv', newline='', encoding='utf-8'))}
    assert {'copy_status', 'unavailable_reason', 'unavailable_summary'} <= set(next(iter(rows.values())))
    assert (rows['W1']['copy_status'], rows['W1']['unavailable_reason'], rows['W1']['unavailable_summary']) == ('local', '', '')
    assert rows['W1']['pdf'].startswith('papers/')
    assert (rows['W2']['copy_status'], rows['W2']['unavailable_reason']) == ('needs_access_review', 'paywall_only')
    assert rows['W2']['unavailable_summary'].startswith('Listed open at IEEE')
    assert (rows['W3']['copy_status'], rows['W3']['unavailable_reason']) == ('not_in_catalog', 'no_doi_no_match')
    assert (rows['W4']['copy_status'], rows['W4']['unavailable_reason']) == ('queued', 'incomplete_check')


def test_release_manifest_ledger_counts(tmp_path, fixture_json):
    d = _school(tmp_path, fixture_json('unavailable-ledger.json'))
    assert {'unavailable.jsonl.gz', 'unavailable-summary.json'} <= set(make_release.SCHOOL_EXTRA)
    led = make_release.ledger_counts(d)
    assert led['built_at'] == '2026-10-30T12:00:00Z' and led['papers'] == 4
    assert led['by_reason'] == {'incomplete_check': 1, 'no_doi_no_match': 1, 'paywall_only': 2}
    (d / 'unavailable-summary.json').unlink()  # recounted from the records
    assert make_release.ledger_counts(d)['by_reason'] == {'incomplete_check': 1, 'no_doi_no_match': 1, 'paywall_only': 2}
    (d / 'unavailable.jsonl.gz').unlink()
    assert make_release.ledger_counts(d) is None


def test_regression_flags_ledger_swings():
    def snap(by_reason):
        return dict(at='t', source='s', code='c', schools={'princeton': dict(
            builtAt='b', report={}, rows=dict(lab_papers=10, student_papers=1, lab_student_pairs=1, pis=1),
            digests={}, per_pi={'A': 10}, ledger=dict(built_at='x', papers=sum(by_reason.values()), by_reason=by_reason) if by_reason is not None else None)})
    assert br.compare(snap({'paywall_only': 100}), snap({'paywall_only': 115}))['flags'] == []  # 15%: not flagged
    assert br.compare(snap({'paywall_only': 40}), snap({'paywall_only': 55}))['flags'] == []    # 37%, but only 15 papers
    f = br.compare(snap({'paywall_only': 100, 'pending_retry': 10}), snap({'paywall_only': 60, 'pending_retry': 40}))['flags']
    assert sorted((x['kind'], x['count']) for x in f) == [('ledger_reason', 'paywall_only'), ('ledger_reason', 'pending_retry')]
    assert [x['kind'] for x in br.compare(snap({'paywall_only': 1}), snap(None))['flags']] == ['ledger_missing']
    assert br.compare(snap(None), snap({'paywall_only': 100}))['flags'] == []  # the first ledger is not a swing
