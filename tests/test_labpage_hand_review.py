"""Reviewed source limits survive a regenerated proposal and its native import."""
from collections import Counter, defaultdict
import copy
import hashlib
import json
from types import SimpleNamespace

import pytest

import labpage_audit as L
from pihier import students


def reference_case():
    html = b'<a href="/a">Paper</a><a href="/b">Invited Paper</a><a href="/b">Paper</a>'
    body = b'{"message":{"title":["A complete scholarly title"], "published":{"date-parts":[[2022]]}}}'
    old_body = b'{"message":{"title":["An older scholarly title"], "published":{"date-parts":[[2001]]}}}'
    sources = {
        'https://example.edu/publications': dict(url='https://example.edu/publications', content=html,
                                                sha256=hashlib.sha256(html).hexdigest(), status=200),
        'https://publisher.example/metadata': dict(url='https://publisher.example/metadata', content=body,
                                                  sha256=hashlib.sha256(body).hexdigest(), status=200),
        'https://publisher.example/old': dict(url='https://publisher.example/old', content=old_body,
                                             sha256=hashlib.sha256(old_body).hexdigest(), status=200)}
    proof = dict(url='https://publisher.example/metadata', sha256=hashlib.sha256(body).hexdigest())
    entries = [dict(source_index=i, literal_href=href, link_label=label,
                    url='https://example.edu' + href, reason='Independent whole-source review')
               for i, (href, label) in enumerate([('/a', 'Paper'), ('/b', 'Invited Paper'), ('/b', 'Paper')])]
    entries[0].update(disposition='matched_existing_native_paper', metadata_proofs=[proof],
                      title='A complete scholarly title', years=[2022], native_matches=[dict(title='A complete scholarly title')])
    entries[1].update(disposition='outside_publication_window',
                      metadata_proofs=[dict(url='https://publisher.example/old', sha256=hashlib.sha256(old_body).hexdigest())],
                      title='An older scholarly title', years=[2001])
    entries[2].update(disposition='unresolved_metadata', attempts=[dict(url='https://example.edu/b', error='robots-disallowed')])
    review = dict(url='https://example.edu/publications', sha256=sources['https://example.edu/publications']['sha256'],
                  whole_source_read=True, reviewed_by='Independent reader', reviewed_on='2026-11-24', entries=entries)
    kit = SimpleNamespace(stored=lambda uri: (sources.get(uri), {}),
                          lpcap=SimpleNamespace(decode=lambda b: b.decode(), collapse=lambda s: ' '.join(s.split())))
    return kit, dict(publication_reference_review=review), [dict(pubs_page=review['url'])], sources


def test_untitled_reference_review_keeps_every_anchor_and_exact_matches_only():
    kit, prior, pages, _ = reference_case()
    idx = L.PaperIndex([dict(title='A complete scholarly title')])
    kept, refs = L.reviewed_publication_references(kit, prior, pages + [dict(pubs_page='https://example.edu/other')], idx)
    assert kept == [dict(pubs_page='https://example.edu/other')]
    assert len(refs) == 3 and refs[1]['url'] == refs[2]['url']
    assert 'title' not in refs[2]
    assert prior['publication_reference_review']['entries'] == refs


@pytest.mark.parametrize('change', ['source', 'omit', 'duplicate', 'order', 'href', 'metadata',
                                  'partial_title', 'window', 'attempts', 'unconfigured'])
def test_untitled_reference_reviews_fail_closed(change):
    kit, prior, pages, sources = reference_case()
    review = prior['publication_reference_review']
    idx = L.PaperIndex([dict(title='A complete scholarly title')])
    if change == 'source':
        review['sha256'] = 'b' * 64
    elif change == 'omit':
        review['entries'].pop()
    elif change == 'duplicate':
        review['entries'].append(copy.deepcopy(review['entries'][-1]))
    elif change == 'order':
        review['entries'][0], review['entries'][1] = review['entries'][1], review['entries'][0]
    elif change == 'href':
        review['entries'][0]['url'] = 'https://other.example/paper'
    elif change == 'metadata':
        sources.pop('https://publisher.example/metadata')
    elif change == 'partial_title':
        review['entries'][0]['native_matches'] = [dict(title='A complete scholarly title with an unsupported suffix')]
    elif change == 'window':
        review['entries'][1]['years'] = [2022]
    elif change == 'attempts':
        review['entries'][2]['attempts'] = []
    else:
        pages = []
    with pytest.raises(ValueError):
        L.reviewed_publication_references(kit, prior, pages, idx)


def test_untitled_references_are_counted_and_never_proposed_as_papers(monkeypatch):
    kit, prior, pages, _ = reference_case()
    monkeypatch.setattr(L, 'paper_sources', lambda *args: (pages, []))
    ctx = dict(prior={'Professor Example': prior}, lab_papers={'Professor Example': [dict(title='A complete scholarly title')]})
    p = dict(pi='Professor Example')
    sec, ents = L.collect_papers(kit, ctx, p, dict(status='found'), {})
    assert ents == [] and sec['listed'] == 3 and sec['matched_in_lab_papers'] == 1
    assert sec['pubs_page_status'] == 'audited'
    assert [r['reason_code'] for r in sec['missing']] == ['outside_window', 'unresolved_metadata']
    monkeypatch.setattr(L, 'pi_start_year', lambda p: 2016)
    assert L.finish_papers(sec, ents, p, {}) == []
    assert sec['reason_code'] == 'all_missing_explained'


@pytest.mark.parametrize('field', ['reference', 'created', 'indexed'])
def test_reference_dates_cannot_come_from_bibliography_or_indexing(field):
    kit, prior, pages, sources = reference_case()
    row = prior['publication_reference_review']['entries'][1]
    data = dict(message=dict(title=['An older scholarly title'], published={'date-parts': [[2022]]}))
    data['message'][field] = ([dict(year='2001')] if field == 'reference' else {'date-parts': [[2001]]})
    body = json.dumps(data).encode()
    sources['https://publisher.example/old'].update(content=body, sha256=hashlib.sha256(body).hexdigest())
    row['metadata_proofs'][0]['sha256'] = hashlib.sha256(body).hexdigest()
    with pytest.raises(ValueError, match='facts'):
        L.reviewed_publication_references(kit, prior, pages, L.PaperIndex([dict(title='A complete scholarly title')]))


def test_reference_exact_metadata_must_bind_original_publisher_identifier():
    kit, prior, pages, sources = reference_case()
    review = prior['publication_reference_review']
    source = sources[review['url']]
    source['content'] = source['content'].replace(b'href="/a"', b'href="https://ieeexplore.ieee.org/document/99999"')
    source['sha256'] = hashlib.sha256(source['content']).hexdigest()
    review['sha256'] = source['sha256']
    row = review['entries'][0]
    row.update(literal_href='https://ieeexplore.ieee.org/document/99999', url='https://ieeexplore.ieee.org/document/99999')
    with pytest.raises(ValueError, match='facts'):
        L.reviewed_publication_references(kit, prior, pages, L.PaperIndex([dict(title='A complete scholarly title')]))


@pytest.fixture
def audit_files(tmp_path, monkeypatch):
    monkeypatch.setattr(L.P, 'data', lambda fn, school=None, root=None: tmp_path / fn)
    monkeypatch.setattr(L.P, 'data_w', lambda fn, school=None: tmp_path / fn)
    monkeypatch.setattr(L, 'Kit', lambda school: None)
    monkeypatch.setattr(L, 'school_summary', lambda *args: {})
    monkeypatch.setattr(L, 'onboarding', lambda school: True)
    monkeypatch.setattr(L, 'fix_titles_from_arxiv', lambda rows, **kwargs: None)
    monkeypatch.setattr(L, 'withhold_heading_conflict', lambda kit, school, row: row)
    monkeypatch.setattr(L, 'withhold_bio_degree_role', lambda row: row)
    return tmp_path / 'labpage-additions.json'


@pytest.mark.parametrize('decision', ['membership_only', 'alumni_membership_only'])
def test_membership_review_survives_regeneration_and_native_import(audit_files, tmp_path, monkeypatch, decision):
    review = [{'pi': 'Professor Example', 'name': 'Jane Researcher', 'decision': decision}]
    audit_files.write_text(json.dumps({'hand_review_students': review}))
    row = dict(pi='Professor Example', name='Jane Researcher', role='undergraduate', years=None,
               relationship='advising', alumni=False, section='current', url='https://example.edu/group', sha256='a' * 64,
               quote='Current group members: Jane Researcher (undergraduate).')
    original = copy.deepcopy(row)
    for _ in range(2):
        L.write_audit('test', [], [row], [])
        proposal = json.loads(audit_files.read_text())
        assert proposal['hand_review_students'] == review
        expected = dict(row, relationship='membership')
        if decision == 'alumni_membership_only':
            expected.update(alumni=True, section='alumni')
        assert proposal['students'] == [expected]
    assert row == original

    monkeypatch.setattr(students, 'accepted_additions', lambda *args: proposal['students'])
    ctx = SimpleNamespace(here=tmp_path, school='test', pis=[dict(pi='Professor Example')], ge={}, n=Counter())
    native = defaultdict(dict)
    students.researched(ctx, native, {})
    member, = native['Professor Example'].values()
    assert member['roles'] == ['undergraduate']
    relation, = member['relations']
    assert relation['type'] == 'researched_membership'
    assert relation['role'] == 'undergraduate'
    assert relation['years'] == []


@pytest.mark.parametrize('decision', ['rejected', 'held'])
def test_paper_title_review_survives_regeneration(audit_files, decision):
    review = [{'pi': 'Professor Example', 'title': 'Unproven school paper', 'decision': decision}]
    audit_files.write_text(json.dumps({'hand_review_papers': review}))
    papers = [dict(pi='Professor Example', title='Unproven school paper'),
              dict(pi='Professor Example', title='Supported paper')]
    for _ in range(2):
        L.write_audit('test', [], [], papers)
        proposal = json.loads(audit_files.read_text())
        assert proposal['papers'] == [papers[1]]
        assert proposal['hand_review_papers'] == review


def correction_case():
    row = dict(pi='Professor Example', name='Jane Researcher', role='phd', years=None,
               alumni=False, url='https://example.edu/group', sha256='a' * 64,
               quote='Jane Researcher, DEng student', rule='LP-STU-01', auto=True)
    review = dict(pi=row['pi'], name=row['name'], decision='source_corrected', original=copy.deepcopy(row),
                  changes=dict(role='student', degree='DEng', relationship='membership'),
                  reviewer='independent source reviewer', date='2026-11-24', reason='The original names DEng, not PhD.')
    return row, review


def quote_checker(*args, **kwargs):
    if kwargs.get('quote') != 'Jane Researcher, DEng student':
        raise ValueError('quote not in original')
    assert args[1] == 'Jane Researcher' and args[2] == 'member' and args[4] == 'a' * 64
    return dict(url='https://example.edu/group', sha256='a' * 64, quote=kwargs['quote'])


def test_source_correction_survives_regeneration_without_changing_original(audit_files, monkeypatch):
    row, review = correction_case()
    original = copy.deepcopy(row)
    monkeypatch.setattr(L, 'Kit', lambda school: SimpleNamespace(lpev=SimpleNamespace(M=quote_checker)))
    metadata = dict(hand_review_20261124c=[review])
    audit_files.write_text(json.dumps(metadata))
    for _ in range(2):
        L.write_audit('test', [], [row], [])
        doc = json.loads(audit_files.read_text())
        member, = doc['students']
        assert member['role'] == 'student' and member['degree'] == 'DEng'
        assert member['relationship'] == 'membership'
        assert member['source_correction_review']['reviewer'] == review['reviewer']
        assert doc['hand_review_20261124c'] == [review]
    assert row == original


@pytest.mark.parametrize('field,value', [
    ('pi', 'Other PI'), ('name', 'Other Person'), ('role', 'masters'), ('years', [2025]),
    ('url', 'https://other.example.edu/group'), ('capture_url', 'https://archive.example/capture'),
    ('sha256', 'b' * 64), ('quote', 'Different extraction'), ('alumni', True),
    ('relationship', 'membership'), ('degree', 'masters'), ('section', 'alumni'),
    ('role_basis', 'reviewer'), ('years_basis', 'reviewer'), ('observed', '2025'),
    ('pi_first_year', 2025), ('note', 'section: previous school'),
])
def test_changed_source_or_extraction_does_not_reuse_correction(field, value):
    row, review = correction_case()
    changed = dict(row, **{field: value})
    assert L.apply_source_corrections([changed], {'hand_review_20261124c': [review]}, 'test', None) == [changed]


@pytest.mark.parametrize('changes', [dict(pi='Other PI'), dict(url='https://other.example/group'),
                                     dict(sha256='b' * 64), dict(person='existing-issued-id')])
def test_correction_cannot_reassign_pi_source_or_issued_identity(changes):
    row, review = correction_case()
    review['changes'] = changes
    with pytest.raises(ValueError, match='Malformed'):
        L.apply_source_corrections([row], {'hand_review_20261124c': [review]}, 'test', None)


def test_corrected_quote_must_still_exist_in_retained_original():
    row, review = correction_case()
    review['changes']['quote'] = 'An invented role claim'
    kit = SimpleNamespace(lpev=SimpleNamespace(M=quote_checker))
    with pytest.raises(ValueError, match='quote not in original'):
        L.apply_source_corrections([row], {'hand_review_20261124c': [review]}, 'test', kit)


def test_duplicate_correction_is_rejected():
    row, review = correction_case()
    with pytest.raises(ValueError, match='Conflicting'):
        L.apply_source_corrections([row], {'hand_review_20261124c': [review, review]}, 'test', None)


@pytest.mark.parametrize('bad', [None, {}, [None], [dict(decision='source_corrected')]])
def test_malformed_correction_ledger_fails_closed(bad):
    row, _ = correction_case()
    with pytest.raises(ValueError):
        L.apply_source_corrections([row], {'hand_review_20261124c': bad}, 'test', None)


@pytest.mark.parametrize('role', ['misspelled-role', 'staff', 'phd_fake'])
def test_source_correction_cannot_emit_unknown_role(role):
    row, review = correction_case()
    review['changes']['role'] = role
    with pytest.raises(ValueError, match='violates the additions schema'):
        L.apply_source_corrections([row], {'hand_review_20261124c': [review]}, 'test', None)


@pytest.mark.parametrize('field,value', [('sha256', 'b' * 64), ('url', 'https://other.example/group'),
                                       ('capture_url', 'https://archive.example/capture')])
def test_quote_validator_returned_source_must_match(field, value):
    row, review = correction_case()
    def wrong_source(*args, **kwargs):
        return dict(quote_checker(*args, **kwargs), **{field: value})
    kit = SimpleNamespace(lpev=SimpleNamespace(M=wrong_source))
    with pytest.raises(ValueError, match='different retained source'):
        L.apply_source_corrections([row], {'hand_review_20261124c': [review]}, 'test', kit)


@pytest.mark.parametrize('decision', ['role_withheld', 'membership_only', 'alumni_membership_only'])
def test_old_name_restrictions_follow_a_corrected_name(decision):
    row, review = correction_case()
    row['name'] = 'Jane R'
    review.update(name=row['name'], original=copy.deepcopy(row))
    review['changes'].update(name='Jane Researcher', role='phd', relationship='advising', alumni=False)
    old = dict(pi=row['pi'], name=row['name'], decision=decision, reason='Earlier source limit')
    kit = SimpleNamespace(lpev=SimpleNamespace(M=quote_checker))
    corrected, = L.apply_source_corrections([row], {'hand_review_20261124c': [old, review]}, 'test', kit)
    assert corrected['name'] == 'Jane Researcher'
    if decision == 'role_withheld':
        assert corrected['role'] is None
    else:
        assert corrected['relationship'] == 'membership'
    if decision == 'alumni_membership_only':
        assert corrected['alumni'] is True


def test_complete_correction_ledger_and_output_validate(audit_files, monkeypatch):
    import schema_check
    row, review = correction_case()
    monkeypatch.setattr(L, 'Kit', lambda school: SimpleNamespace(lpev=SimpleNamespace(M=quote_checker)))
    audit_files.write_text(json.dumps({'hand_review_20261124c': [review]}))
    L.write_audit('test', [], [row], [])
    schema = json.loads((L.P.TOOLS.parent / 'schemas/labpage-additions.schema.json').read_text())
    assert schema_check.validate(json.loads(audit_files.read_text()), schema) == []


def test_real_quote_reader_uses_exact_original_body(tmp_path):
    """Two different retained bodies for one archive URL must never be interchangeable."""
    import subprocess
    import sys
    from pathlib import Path
    code = r'''
import copy, hashlib, json, os, runpy, sys, zlib
from pathlib import Path
repo, temporary = map(Path, sys.argv[1:])
os.environ['CS_ATLAS_TOOLS'] = str(repo / 'tools')
os.environ['CS_ATLAS_SCHOOL_CONFIGS'] = str(repo / 'schools')
runpy.run_path(str(repo / 'tools/pi_hierarchy.py'))
import atlas_paths as P
import labpage_audit as L

def local(name, school=None, **kwargs):
    path = temporary / (school or '_') / name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
P.data = P.data_w = local
local('pis.json', 'jhu').write_text('[]')
kit = L.Kit('jhu')
url = 'https://example.edu/group'
cap = 'https://web.archive.org/web/20200101000000id_/https://example.edu/group'
quote = 'Jane Researcher, DEng student'
old = ('<html><body>' + quote + '<footer>old version</footer></body></html>').encode()
new = old.replace(b'old version', b'changed version')
old_sha, new_sha = [hashlib.sha256(body).hexdigest() for body in (old, new)]
with kit.lpcap.connect('jhu') as db:
    for body, sha in [(old, old_sha), (new, new_sha)]:
        db.execute('insert into captures(url,final_url,capture_url,fetched_at,status,sha256,content_type,content) '
                   'values (?,?,?,?,?,?,?,?)',
                   (url, url, cap, '2026-01-01T00:00:00Z', 200, sha, 'text/html', zlib.compress(body)))
kit.lpev._cache.clear()
assert kit.lpev.M('jhu', 'Jane Researcher', 'member', None, cap, quote=quote)['sha256'] == new_sha
row = dict(pi='Professor Example', name='Jane Researcher', role='phd', years=None,
           alumni=False, url=url, capture_url=cap, sha256=old_sha, quote=quote, rule='LP-STU-01', auto=True)
review = dict(pi=row['pi'], name=row['name'], decision='source_corrected', original=copy.deepcopy(row),
              changes=dict(role='student', degree='DEng'), reviewer='fresh source reviewer',
              date='2026-11-24', reason='DEng is not a PhD label')
got, = L.apply_source_corrections([row], {'hand_review_20261124c': [review]}, 'jhu', kit)
assert got['sha256'] == old_sha and got['role'] == 'student' and got['degree'] == 'DEng'
review['changes']['quote'] = quote + ' changed version'
try:
    L.apply_source_corrections([row], {'hand_review_20261124c': [review]}, 'jhu', kit)
except ValueError:
    pass
else:
    raise AssertionError('Quote from the newer archive body was accepted for the old source hash')
print('exact original retained; newer body rejected')
'''
    result = subprocess.run([sys.executable, '-I', '-c', code, str(Path(L.__file__).resolve().parents[1]), str(tmp_path)],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'exact original retained; newer body rejected' in result.stdout


def test_manual_source_member_survives_an_extractor_omission(audit_files, monkeypatch):
    row, _ = correction_case()
    row.update(auto=False, role='student', degree='DEng')
    monkeypatch.setattr(L, 'Kit', lambda school: SimpleNamespace(lpev=SimpleNamespace(M=quote_checker)))
    audit_files.write_text(json.dumps(dict(students=[row])))
    for _ in range(2):
        L.write_audit('test', [], [], [])
        assert json.loads(audit_files.read_text())['students'] == [row]


def test_manual_source_correction_keeps_old_name_role_limit():
    original, _ = correction_case()
    original['name'] = 'Jane R'
    row = dict(original, name='Jane Researcher', auto=False, source_correction_original=copy.deepcopy(original))
    review = dict(pi=original['pi'], name=original['name'], decision='role_withheld', reason='Earlier role limit')
    kit = SimpleNamespace(lpev=SimpleNamespace(M=quote_checker))
    out, = L.preserve_manual_members([original], dict(students=[row], hand_review_20261124c=[review]), 'test', kit)
    assert out['name'] == 'Jane Researcher' and out['role'] is None


def test_manual_source_correction_reopens_changed_extraction():
    original, _ = correction_case()
    row = dict(original, auto=False, role='student', source_correction_original=copy.deepcopy(original))
    kit = SimpleNamespace(lpev=SimpleNamespace(M=quote_checker))
    with pytest.raises(ValueError, match='changed automatic extraction'):
        L.preserve_manual_members([dict(original, section='Different scope')], dict(students=[row]), 'test', kit)


def test_manual_source_correction_cannot_reassign_source():
    original, _ = correction_case()
    row = dict(original, auto=False, sha256='b' * 64, source_correction_original=copy.deepcopy(original))
    with pytest.raises(ValueError, match='cannot reassign'):
        L.preserve_manual_members([], dict(students=[row]), 'test', None)


def test_manual_member_retains_two_distinct_source_episodes():
    row, _ = correction_case()
    first = dict(row, auto=False, role='masters', years=[2018, 2019])
    second = dict(row, auto=False, role='phd', years=[2020, 2024])
    kit = SimpleNamespace(lpev=SimpleNamespace(M=quote_checker))
    assert L.preserve_manual_members([], dict(students=[first, second]), 'test', kit) == [first, second]
    assert L.preserve_manual_members([first], dict(students=[second]), 'test', kit) == [first, second]


def test_conflicting_manual_members_do_not_silently_choose_last():
    row, _ = correction_case()
    first = dict(row, auto=False, role='masters', years=[2020, 2024])
    second = dict(row, auto=False, role='phd', years=[2020, 2024])
    kit = SimpleNamespace(lpev=SimpleNamespace(M=quote_checker))
    with pytest.raises(ValueError, match='Conflicting manual'):
        L.preserve_manual_members([], dict(students=[first, second]), 'test', kit)


def test_manual_omission_does_not_replace_an_ambiguous_automatic_claim():
    row, _ = correction_case()
    manual = dict(row, auto=False, role='student')
    kit = SimpleNamespace(lpev=SimpleNamespace(M=quote_checker))
    with pytest.raises(ValueError, match='changed automatic'):
        L.preserve_manual_members([row], dict(students=[manual]), 'test', kit)


def test_review_marker_alone_cannot_replace_a_changed_automatic_claim():
    row, _ = correction_case()
    manual = dict(row, auto=False, source_correction_original=copy.deepcopy(row))
    automatic = dict(row, years=[2026, 2026], source_correction_review={'reviewer': 'unrelated review'})
    kit = SimpleNamespace(lpev=SimpleNamespace(M=quote_checker))
    with pytest.raises(ValueError, match='changed automatic'):
        L.preserve_manual_members([automatic], dict(students=[manual]), 'test', kit)


@pytest.mark.parametrize('field', ['source_record_key', 'person', 'key'])
def test_manual_correction_cannot_add_an_issued_identity_key(field):
    row, _ = correction_case()
    manual = dict(row, auto=False, source_correction_original=copy.deepcopy(row), **{field: 'different-id'})
    with pytest.raises(ValueError, match='immutable extraction field'):
        L.preserve_manual_members([], dict(students=[manual]), 'test', None)


def test_manual_correction_ignores_only_the_incidental_audit_date():
    row, _ = correction_case()
    row['note'] = 'lab-page audit 2026-11-23; section: Students'
    manual = dict(row, auto=False, source_correction_original=copy.deepcopy(row))
    automatic = dict(row, note='lab-page audit 2026-11-24; section: Students')
    kit = SimpleNamespace(lpev=SimpleNamespace(M=quote_checker))
    assert L.preserve_manual_members([automatic], dict(students=[manual]), 'test', kit) == [manual]


@pytest.mark.parametrize('field,value', [('note', 'section: Previous university'), ('pi_first_year', 2025),
                                       ('source_record_key', 'different-issued-id')])
def test_manual_full_claim_dedup_cannot_bypass_changed_context(field, value):
    row, _ = correction_case()
    manual = dict(row, auto=False, source_correction_original=copy.deepcopy(row))
    automatic = dict(row, **{field: value})
    kit = SimpleNamespace(lpev=SimpleNamespace(M=quote_checker))
    with pytest.raises(ValueError, match='changed automatic'):
        L.preserve_manual_members([automatic], dict(students=[manual]), 'test', kit)


def test_one_original_cannot_be_corrected_into_two_different_identities(monkeypatch):
    row, _ = correction_case()
    first = dict(row, auto=False, source_correction_original=copy.deepcopy(row))
    second = dict(first, name='Different Researcher')
    monkeypatch.setattr(L, 'checked_source_member', lambda row, *args: dict(row))
    with pytest.raises(ValueError, match='share one original'):
        L.preserve_manual_members([], dict(students=[first, second]), 'test', None)


@pytest.mark.parametrize('decision', ['held', 'rejected'])
def test_corrected_name_hold_also_removes_only_its_exact_original(decision):
    original, _ = correction_case()
    manual = dict(original, name='Corrected Name', auto=False, source_correction_original=copy.deepcopy(original))
    other = dict(original, years=[2015, 2016], role='masters')
    existing = dict(students=[manual], hand_review_20261124c=[dict(pi=original['pi'], name=manual['name'], decision=decision)])
    auto = L.apply_source_corrections([original, other], existing, 'test', None)
    output = L.preserve_manual_members(auto, existing, 'test', None)
    assert L.apply_hand_review(output, L.recorded_hand_review(existing)) == [other]


def test_identical_body_retains_the_exact_other_archive_date_context():
    row, _ = correction_case()
    row['capture_url'] = 'https://web.archive.org/web/20240101000000id_/https://example.edu/group'
    context = dict(url=row['url'], capture_url=row['capture_url'], sha256=row['sha256'])
    lookups = []
    def stored(src):
        lookups.append(src)
        return context, {}
    kit = SimpleNamespace(lpev=SimpleNamespace(M=quote_checker), stored=stored)
    assert L.checked_source_member(row, 'test', kit) == row
    assert lookups == [row['capture_url']]


@pytest.mark.parametrize('changes', [dict(sha256='b' * 64), dict(url='https://different.example/group'),
                                    dict(capture_url='https://archive.example/other')])
def test_identical_body_does_not_authorize_an_unverified_capture_context(changes):
    row, _ = correction_case()
    row['capture_url'] = 'https://web.archive.org/web/20240101000000id_/https://example.edu/group'
    context = dict(url=row['url'], capture_url=row['capture_url'], sha256=row['sha256'])
    context.update(changes)
    kit = SimpleNamespace(lpev=SimpleNamespace(M=quote_checker), stored=lambda src: (context, {}))
    with pytest.raises(ValueError, match='different retained source'):
        L.checked_source_member(row, 'test', kit)


def test_reviewed_source_preserves_all_discrete_years_without_interpolation():
    row, _ = correction_case()
    row['years'] = [2016, 2019, 2026]
    def evidence_only(*args, **kwargs):
        assert args[3] is None  # The legacy evidence API must not reinterpret the reviewed year list.
        return quote_checker(*args, **kwargs)
    kit = SimpleNamespace(lpev=SimpleNamespace(M=evidence_only))
    checked = L.checked_source_member(row, 'test', kit)
    from pihier.common import as_years
    assert checked['years'] == as_years(checked['years']) == [2016, 2019, 2026]


def test_disjoint_explicit_full_year_episodes_are_retained():
    row, _ = correction_case()
    masters = dict(row, auto=False, role='masters', years=[2016, 2017, 2018])
    doctoral = dict(row, auto=False, role='phd', years=[2021, 2022, 2023])
    kit = SimpleNamespace(lpev=SimpleNamespace(M=quote_checker))
    assert L.preserve_manual_members([], dict(students=[masters, doctoral]), 'test', kit) == [masters, doctoral]
