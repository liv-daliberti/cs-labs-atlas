"""Coverage must not silently turn unsearched PIs or moved sites into successes."""
import gzip
import json

import lab_websites as W


def record(code='lab_site', url='https://school.edu/lab/'):
    return {'pi': 'Ada Example', 'audited_at': '2026-11-07', 'lab_page': {
        'status': 'found' if code == 'lab_site' else 'none_found', 'reason_code': code,
        'reason': 'A recorded search outcome', 'urls': {'lab_site': url},
        'source': 'prior_pass', 'evidence': {'sha256': 'a' * 64},
        'checks': [{'source': 'school_profile', 'url': 'https://school.edu/people/ada',
                    'at': '2026-11-07', 'result': 'ok'}]}}


def test_moved_site_is_a_reason_not_a_school_website():
    r = W.entry(record('site_at_other_institution'))
    assert r['coverage'] == 'reason' and r['kind'] == 'other_institution_site'
    assert W.counts({'labs': [r]})['website'] == 0


def test_empty_checks_cannot_satisfy_coverage():
    rec = record('no_web_presence_found', None)
    rec['lab_page']['checks'] = []
    assert W.entry(rec)['coverage'] == 'pending'
    rec['lab_page']['checks'] = [{'source': 'openalex_author', 'url': 'https://openalex.org/A1',
                                 'at': '2026-11-07', 'result': 'no_homepage_field_in_schema'}]
    assert W.entry(rec)['coverage'] == 'pending'


def test_missing_hash_and_missing_provenance_are_pending():
    rec = record()
    rec['lab_page']['evidence'] = {}
    rec['lab_page'].pop('source')
    e = W.entry(rec)
    assert e['coverage'] == 'pending'
    assert {'page_capture_hash_missing', 'discovery_source_missing'} <= set(e['evidence_gaps'])


def test_official_provenance_is_separate_from_url_capture():
    rec = record()
    e = W.entry(rec)
    assert e['coverage'] == 'website'
    assert not W.counts({'labs': [e]})['official_provenance_complete']
    rec['lab_page']['checks'].append({'source': 'school_profile_link', 'url': rec['lab_page']['urls']['lab_site'],
                                    'on': 'https://school.edu/people/ada', 'at': '2026-11-07', 'result': 'listed'})
    assert W.counts({'labs': [W.entry(rec)]})['official_provenance_complete']


def test_missing_and_stale_audits_preserve_every_current_pi(tmp_path, monkeypatch):
    (tmp_path / 'pis.json').write_text(json.dumps([{'pi': 'Ada Example'}, {'pi': 'New PI'}]))
    monkeypatch.setattr(W.P, 'data', lambda name, school: tmp_path / name)
    doc = W.build('newschool')
    assert len(doc['labs']) == 2 and W.counts(doc)['neither'] == 2
    with gzip.open(tmp_path / 'labpage-audit.jsonl.gz', 'wt') as f:
        f.write(json.dumps(record()) + '\n')
        stale = record()
        stale['pi'] = 'Former excluded PI'
        f.write(json.dumps(stale) + '\n')
    doc = W.build('newschool')
    assert [r['pi'] for r in doc['labs']] == ['Ada Example', 'New PI']
    assert W.counts(doc)['neither'] == 1


def test_gate_checks_every_census_pi_and_does_not_trust_coverage_label():
    row = W.entry(record())
    row['coverage'] = 'website'
    bad = W.gate({'labs': [row]}, ['Ada Example', 'Missing PI'])
    assert any('Missing PI' in x for x in bad)
    assert any('official discovery' in x for x in bad)
    row['reason_code'] = 'no_web_presence_found'
    row['checks'] = []
    row['coverage'] = 'reason'
    assert any('dated source check' in x for x in W.gate({'labs': [row]}, ['Ada Example']))


def test_access_and_archive_reasons_are_not_absence_claims():
    rec = record('no_web_presence_found', None)
    rec['lab_page']['checks'][0]['result'] = 'wayback_only_host'
    assert W.entry(rec)['reason_type'] == 'pending_archive'
    rec['lab_page']['checks'][0]['result'] = 'robots_disallowed'
    assert W.entry(rec)['reason_type'] == 'access_blocked'


def test_exact_cached_official_link_provenance(monkeypatch):
    import labpage_audit as L
    rec = record()
    rec['lab_page']['checks'][0]['sha256'] = 'b' * 64
    doc = {'labs': [W.entry(rec)]}

    class Kit:
        def __init__(self, school):
            pass

        def stored(self, url):
            return ({'status': 200, 'sha256': 'b' * 64, 'content': b'<a>lab</a>'}, {})

    monkeypatch.setattr(L, 'Kit', Kit)
    monkeypatch.setattr(L, 'site_links', lambda *args: [('http://school.edu/lab/#home', 'Lab website')])
    monkeypatch.setattr(L, 'link_base', lambda row, url: url)
    monkeypatch.setattr(L, 'SCHOOLS', {'u': {'domain': r'school\.edu'}})
    out = W.enrich_official_links('u', doc)['labs'][0]
    assert out['official_link_status'] == 'recorded'
    assert out['official_link_evidence'][0]['source_sha256'] == 'b' * 64
    assert out['listed_on'] == 'https://school.edu/people/ada'
    assert W.normalized_link('https://other.school.edu/lab/') != W.normalized_link('https://school.edu/lab/')


def test_archive_pending_is_unresolved_at_gate():
    rec = record('no_web_presence_found', None)
    rec['lab_page']['checks'][0]['result'] = 'wayback_only_host'
    e = W.entry(rec)
    assert any('archive evidence pending' in x for x in W.gate({'labs': [e]}, ['Ada Example']))


def test_dated_publication_page_is_not_a_lab_website():
    rec = record(url='https://cyber.harvard.edu/publications/2016/Cybersecurity/Dont_Panic')
    row = W.entry(rec)
    assert row['coverage'] == 'pending'
    assert 'selected_url_is_research_output' in row['evidence_gaps']
    assert any('research-output' in b for b in W.gate({'labs': [row]}, ['Ada Example']))
