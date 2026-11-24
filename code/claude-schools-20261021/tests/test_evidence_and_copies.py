"""The build-time evidence check (tools/evidence_check.py) and the copies check's access-review causes (2026-10-29)."""
import gzip
import json

import chain_audit
import evidence_check

SHA = 'a' * 64


def _package(tmp_path, link):
    d = tmp_path / 'princeton'
    d.mkdir(parents=True)
    pis = [dict(pi='P', periods=[dict(id='p1', start='2010', end=None, evidence=[dict(url='u', sha256=SHA, quote='Professor P')])],
                listings=[dict(year=2020, url='u', sha256=SHA, quote='P, Professor')])]
    students = {'P': [dict(person='s1', name='S One', relations=[dict(type='researched_advising', sources=[dict(url='u', sha256=SHA, quote='Adviser: P')])])]}
    papers = [dict(pi='P', oa='W1', authorship=dict(school_via=['Princeton University']), appointment=dict(periodId='p1')),
              dict(pi='P', oa='W2', authorship=dict(school_via=['Princeton University']), appointment=dict(listing=pis[0]['listings'][0]))]
    (d / 'pis.json').write_text(json.dumps(pis)); (d / 'students.json').write_text(json.dumps(students))
    for name, rows in (('lab_papers', papers), ('student_papers', [link])):
        with gzip.open(d / f'{name}.jsonl.gz', 'wt') as f:
            f.write(''.join(json.dumps(r) + '\n' for r in rows))
    return tmp_path


def test_R_AUD_05_evidence_check_clean_and_violations(tmp_path):
    good = dict(pi='P', student='s1', oa='W1', basis='within_lab_byline_match', byline='S. One',
                relation_source=dict(relation='researched_advising', url='u', sha256=SHA, quote='Adviser: P'))
    res = evidence_check.check('princeton', _package(tmp_path / 'a', good))
    assert all(v['n'] == 0 for v in res.values())
    bad = dict(good, byline='', relation_source=dict(url='u', sha256='', quote='x'))
    res = evidence_check.check('princeton', _package(tmp_path / 'b', bad))
    assert res['link_byline']['n'] == 1 and res['link_relation_source']['n'] == 1
    # a collection link is not a byline link: no byline evidence is asked of it
    res = evidence_check.check('princeton', _package(tmp_path / 'c', dict(bad, basis='collection_person_link')))
    assert res['link_byline']['of'] == 0


def test_R_AUD_07_access_causes_explain_missing_copies():
    for cause in ('paywall_or_forbidden', 'login', 'challenge'):
        assert any(w in chain_audit.ACCESS_REASON[cause] for w in ('paywalled', 'login', 'challenge'))
    for cause in ('robots_disallow', 'landing_no_pdf', 'not_found', 'policy_skip', 'transient_exhausted', 'unapproved_redirect',
                  'not_pdf', 'identity_mismatch'):
        r = chain_audit.ACCESS_REASON[cause]
        assert 'paywall' not in r and 'login' not in r

def test_default_audit_replaces_the_report_consumed_by_release(tmp_path, monkeypatch):
    legacy = tmp_path / 'legacy-output'; legacy.mkdir()
    derived = legacy / 'derived'; derived.mkdir()
    report = derived / 'EVIDENCE-CHECK.json'
    report.write_text(json.dumps({'ok': True, 'mode': 'strict'}))
    original_data = evidence_check.P.data

    def data(name, *args, **kwargs):
        if name in ('EVIDENCE-CHECK.json', 'EVIDENCE-CHECK.md') and not args and not kwargs:
            return derived / name
        return original_data(name, *args, **kwargs)

    monkeypatch.setattr(evidence_check.P, 'HIERARCHY', legacy)
    monkeypatch.setattr(evidence_check.P, 'data', data)
    monkeypatch.setattr(evidence_check, 'WHITELIST', tmp_path / 'no-whitelist.json')
    package = _package(tmp_path / 'package', dict(pi='P', student='s1', oa='W1',
                       basis='within_lab_byline_match', byline='', relation_source={}))
    assert evidence_check.main(['--dir', str(package), 'princeton']) == 1
    assert json.loads(report.read_text())['ok'] is False
    assert not (legacy / 'EVIDENCE-CHECK.json').exists()
