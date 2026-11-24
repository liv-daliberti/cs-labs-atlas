"""Reconcile collection with the website without promoting or matching by title."""
import gzip
import json

import onboarding_doctor as D


def paper(key='w1', **kw):
    return dict(work=key, oa=None, title='Same title', **kw)


def counter(**statuses):
    return {'papers': {key: {'status': status} for key, status in statuses.items()}}


def test_disjoint_local_copy_gaps_and_compact_record_zero():
    rows = [paper('w1'), paper('w1'), paper('w2'), paper('w3'), paper('w4'), paper('w5')]
    copies = counter(w1='downloaded', w2='fulltext_xml', w3='downloaded', w4='downloaded', w5='identity_unconfirmed')
    site = [dict(w='w1'), dict(w='w2'), dict(w='w3'), dict(w='w5')]
    reader = dict(schema=2, works={'w1': 0, 'w2': 1}, records=[
        dict(path='papers/a.pdf'), dict(link=True, sourceUrl='https://example.org/a', linkBasis='confirmed_copy')])
    counts, gaps = D.reconcile(rows, copies, site, reader)
    assert counts['package_papers'] == 5 and counts['local_copies'] == 4
    assert [counts[k] for k in ('local_hosted', 'local_linked', 'local_missing_reader', 'local_paper_missing_from_site')] == [1, 1, 1, 1]
    assert [(g['key'], g['reason']) for g in gaps] == [('w3', 'local_missing_reader'), ('w4', 'local_paper_missing_from_site')]


def test_source_link_does_not_prove_a_local_copy():
    counts, gaps = D.reconcile([paper()], counter(w1='queued'), [dict(w='w1')],
                              dict(works={'w1': dict(link=True, sourceUrl='https://example.org')}))
    assert counts['local_copies'] == 0 and not gaps


def test_exact_doi_case_and_openalex_short_id_but_never_title():
    copies = {'papers': {'renamed': {'status': 'downloaded', 'doi': '10.1/test'},
                          'another': {'status': 'downloaded', 'oa': 'W123'}}}
    rows = [paper('w1', doi='https://doi.org/10.1/TEST'), dict(work='w2', oa='https://openalex.org/W123'), paper('w3')]
    counts, gaps = D.reconcile(rows, copies, [dict(w='w3', t='Same title')], {})
    assert counts['local_copies'] == 2 and counts['local_paper_missing_from_site'] == 2
    assert {g['key'] for g in gaps} == {'w1', 'w2'}


def test_ambiguous_alias_and_conflicting_ids_are_withheld():
    rows = [dict(work='w1', doi='10.1/shared'), dict(work='w2', doi='10.1/shared')]
    mapping = D.identity_map(rows)
    assert D.match(dict(doi='10.1/shared'), mapping) is None
    assert D.match(dict(work='w1'), mapping) == 0
    assert D.match(dict(work='w1', oa='w2'), mapping) is None


def test_candidate_link_with_local_copy_needs_distinct_indicator():
    counts, gaps = D.reconcile([paper()], counter(w1='downloaded'), [dict(w='w1')],
                              dict(works={'w1': dict(link=True, sourceUrl='https://example.org', storedCopy=False)}))
    assert counts['local_linked'] == 1 and counts['local_linked_without_indicator'] == 1
    assert len(gaps) == 1


def test_bad_reader_index_and_unsafe_link_do_not_count_as_readable():
    assert D.reader_record(dict(schema=2, works={'w1': -1}, records=[dict(path='x')]), dict(w='w1')) is None
    assert D.reader_record(dict(works={'w1': dict(link=True, sourceUrl='javascript:bad')}), dict(w='w1')) is None


def test_missing_and_corrupt_inputs_are_unknown(tmp_path):
    errors = []
    assert D.read_json(tmp_path / 'missing', errors) is None
    bad = tmp_path / 'bad.gz'
    bad.write_bytes(b'not gzip')
    assert D.read_rows(bad, errors) is None
    assert len(errors) == 2


def test_school_report_is_read_only_and_distinguishes_absent_school(tmp_path, monkeypatch):
    package, copies = tmp_path / 'papers.gz', tmp_path / 'copies.json'
    with gzip.open(package, 'wt') as handle:
        handle.write(json.dumps(paper()) + '\n')
    copies.write_text(json.dumps(counter(w1='downloaded')))
    monkeypatch.setattr(D.P, 'data', lambda name, key: package if name == 'lab_papers.jsonl.gz' else copies)
    monkeypatch.setattr(D.ST, 'check', lambda *a: (False, 'fresh'))
    monkeypatch.setattr(D, 'gate_reports', lambda *a: [])
    site = tmp_path / 'site/atlas/data/cs-hierarchy'
    site.mkdir(parents=True)
    (site / 'index.json').write_text('{"schools": []}')
    before = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    report = D.school_report('u', tmp_path / 'site', {}, 'off')
    assert report['counts']['local_paper_missing_from_site'] == 1
    assert before == {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    (site / 'index.json').write_text('{"schools": [{"id": "u"}]}')
    report = D.school_report('u', tmp_path / 'site', {}, 'off')
    assert report['counts'] is None and report['errors']


def test_evidence_view_is_none_for_a_json_sourced_school_and_reports_problems_for_a_store_one(monkeypatch):
    import evidence_store as E
    monkeypatch.setattr(E, 'source_of', lambda s: 'json')
    assert D.evidence_view('x') is None
    monkeypatch.setattr(E, 'source_of', lambda s: 'store')
    monkeypatch.setattr(E, 'check_view', lambda s, root=None: ['x/a.json: differs'])
    assert D.evidence_view('x') == dict(source='store', problems=['x/a.json: differs'])
    monkeypatch.setattr(E, 'check_view', lambda s, root=None: (_ for _ in ()).throw(E.SourceOfTruth('no store')))
    assert 'not measured' in D.evidence_view('x')['problems'][0]
