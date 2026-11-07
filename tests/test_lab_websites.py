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


def test_listing_link_requires_the_pi_named_card_not_another_card_or_page():
    html = b'''<html><body><article><h3>Ada Example</h3><a href="https://lab.example/">Website</a></article>
      <article><h3>Other Person</h3><a href="https://other.example/">Website</a></article></body></html>'''
    hit = W.listing_link_context(html, 'https://school.edu/faculty/', W.normalized_link('https://lab.example/'), 'Ada Example')
    assert hit == ('https://lab.example/', 'Website', 'Ada Example Website')
    assert not W.listing_link_context(html, 'https://school.edu/faculty/', W.normalized_link('https://other.example/'), 'Ada Example')
    assert not W.listing_link_context(b'<body>Ada Example <a href="https://lab.example/">Website</a></body>',
                                     'https://school.edu/', W.normalized_link('https://lab.example/'), 'Ada Example')
    assert not W.listing_link_context(b'<div><h3>Y Z</h3><a href="https://lab.example/">Website</a></div>',
                                     'https://school.edu/', W.normalized_link('https://lab.example/'), 'Y Z')


def test_cached_archive_listing_link_is_valid_official_provenance(monkeypatch):
    import labpage_audit as L
    import zlib
    rec = record()
    rec['lab_page']['checks'][0].update(source='department_listing', url='https://school.edu/faculty/')
    doc = {'labs': [W.entry(rec)]}
    page = {'url': 'https://school.edu/faculty/', 'status': 200, 'sha256': 'b' * 64,
            'capture_url': 'https://web.archive.org/web/20200101id_/https://school.edu/faculty/',
            'content': zlib.compress(b'<article><h3>Example, Ada</h3><a href="/lab/">Website</a></article>')}

    class Kit:
        def __init__(self, school):
            pass

        def stored(self, url):
            return (page if url.startswith('https://web.archive.org/') else None), {}

        def src_of(self, url):
            return page['capture_url']

    monkeypatch.setattr(L, 'Kit', Kit)
    monkeypatch.setattr(L, 'SCHOOLS', {'u': {'domain': r'school\.edu'}})
    out = W.enrich_official_links('u', doc)['labs'][0]
    assert out['official_link_status'] == 'recorded'
    check = out['official_link_evidence'][0]
    assert check['source'] == 'department_listing_link'
    assert check['source_quote'] == 'Example, Ada Website'
    assert check['source_capture_url'] == page['capture_url']
    assert not W.gate(doc, ['Ada Example'])


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


def test_institutional_profile_hostname_is_not_a_lab_homepage():
    import labpage_audit as L
    url = 'https://profiles.stanford.edu/ada-example'
    assert L.is_profile(url, r'stanford\.edu')
    row = W.entry(record(url=url))
    assert any('institutional profile card' in b for b in W.gate({'labs': [row]}, ['Ada Example']))
    assert not L.is_profile('https://ada.stanford.edu/', r'stanford\.edu')


def test_identity_indices_cv_documents_and_publication_indexes_remain_gaps():
    for url in ['https://orcid.org/0000-0000-0000-0001', 'https://ada.example/cv.pdf',
                'https://lab.school.edu/publications/2024', 'https://lab.school.edu/publications/']:
        row = W.entry(record(url=url))
        assert row['coverage'] == 'pending'
        assert W.gate({'labs': [row]}, ['Ada Example'], require_official=False)
    assert W.entry(record(url='https://lab.school.edu/people/'))['coverage'] == 'website'


def test_refresh_imports_landing_cache_without_transferring_old_review(monkeypatch):
    import labpage_audit as L
    imported = []
    rec = record()
    rec['students'] = {'page_status': 'audited'}
    rec['papers'] = {'pubs_page_status': 'audited'}
    new_lp = {**rec['lab_page'], 'urls': {'lab_site': 'https://school.edu/new-lab/'}}

    class Kit:
        def __init__(self, school):
            pass

        def import_school_web(self, path, urls):
            imported.extend(urls)

    monkeypatch.setattr(L, 'Kit', Kit)
    monkeypatch.setattr(L, 'load_ctx', lambda *a, **kw: {'pis': [{'pi': 'Ada Example'}], 'cfg': {'domain': r'school\.edu'}})
    monkeypatch.setattr(L, 'read_discovery', lambda s: {'Ada Example': {
        'chosen': {'lab_site': 'https://school.edu/new-lab/'}, 'checked_at': '2026-11-07',
        'checks': [{'source': 'school_profile', 'url': 'https://school.edu/people/ada'}]}})
    monkeypatch.setattr(L, 'lab_record', lambda *a: (new_lp, {}))
    out = W.refresh_records('u', {'Ada Example': rec})['Ada Example']
    assert set(imported) == {'https://school.edu/new-lab/', 'https://school.edu/people/ada'}
    assert out['students']['page_status'] == 'pending_review'
    assert out['papers']['pubs_page_status'] == 'pending_review'


def test_invalid_cached_selection_uses_verified_alternative_or_remains_pending(monkeypatch):
    import labpage_audit as L
    rec = record()
    bad_url = 'https://school.edu/publications/2020/a-report'
    good_url = 'https://school.edu/ada/'
    discovery = {'Ada Example': {'chosen': {'lab_site': bad_url}, 'checked_at': '2026-11-07',
                 'checks': [{'source': 'candidate_site', 'url': good_url, 'result': 'ok'}],
                 'sites': [{'url': good_url, 'other_school': False}]}}

    class Kit:
        def __init__(self, school):
            pass

        def import_school_web(self, *args):
            pass

    monkeypatch.setattr(L, 'Kit', Kit)
    monkeypatch.setattr(L, 'load_ctx', lambda *a, **kw: {'pis': [{'pi': 'Ada Example'}], 'cfg': {'domain': r'school\.edu'}})
    monkeypatch.setattr(L, 'read_discovery', lambda s: discovery)
    monkeypatch.setattr(L, 'lab_record', lambda kit, ctx, pi, disc: (
        {**rec['lab_page'], 'urls': {'lab_site': disc[pi['pi']]['chosen'].get('lab_site')}}, {}))
    out = W.refresh_records('u', {})['Ada Example']
    assert out['lab_page']['urls']['lab_site'] == good_url
    assert not out['website_review_needed']
    discovery['Ada Example']['chosen'] = {'lab_site': bad_url}
    discovery['Ada Example']['sites'] = []
    out = W.refresh_records('u', {})['Ada Example']
    assert out['website_review_needed']
    assert W.entry(out)['coverage'] == 'pending'


def test_blocked_reason_never_claims_an_archive_has_no_capture():
    rec = record('host_blocked_by_robots', None)
    rec['lab_page']['reason'] = 'robots.txt disallows site; Wayback holds no capture'
    rec['lab_page']['checks'][0]['result'] = 'robots_disallowed'
    row = W.entry(rec)
    assert row['reason_type'] == 'access_blocked'
    assert 'holds no capture' not in row['reason']
    assert 'school_profile https://school.edu/people/ada: robots_disallowed' in row['reason']
    assert row['upstream_audit_reason'] == rec['lab_page']['reason']


def test_website_refresh_does_not_claim_students_were_audited():
    rec = record('pi_homepage_only_no_lab_site')
    rec['lab_page']['reason'] = 'PI homepage was audited for students and papers'
    assert 'audited' not in W.entry(rec)['reason']
