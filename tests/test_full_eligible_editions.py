"""Keep complete admitted editions, source-distinct DOI evidence and honest candidate bylines."""
import copy
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

import test_build_rules as T
from test_paper_claim_review import decision, write_review
from pihier import links, papers, reviewed_claims

FIXTURE = Path(__file__).parent / 'fixtures/full-eligible-editions-source.json'


def sources():
    packet = json.loads(FIXTURE.read_text())
    for source in packet['original_sources']:
        projection = source['projection']
        raw = json.dumps(projection, sort_keys=True, ensure_ascii=False).encode()
        assert hashlib.sha256(raw).hexdigest() == source['projection_sha256']
        assert projection['id'] == source['id']
        assert len(source['decoded_original_sha256']) == 64
    return packet


def folded(rows, school='cmu', preferred=None):
    n = Counter()
    eligible, _ = papers.eligible_untranslated_sources(copy.deepcopy(rows), school)
    unique = papers.collapse_eligible_sources(eligible, n)
    unique, n['book_chapters_folded'], _ = papers.fold_books(unique, school)
    return papers.merge_editions(unique, n, preferred=preferred), n


@pytest.mark.parametrize('case,expected', [
    ('polar_complete_native_records', 'https://openalex.org/W2964241527'),
    ('hmm_complete_native_records', 'https://dblp.org/rec/conf/innovations/GuruswamiNS19'),
])
@pytest.mark.parametrize('reverse', [False, True])
def test_source_bound_actual_full_publisher_metadata_remains_selectable(case, expected, reverse):
    packet = sources(); original = packet[case]
    inputs = list(reversed(original)) if reverse else original
    before = copy.deepcopy(inputs)
    rows, _ = folded(inputs)
    assert inputs == before
    assert len(rows) == 1 and rows[0]['oa'] == expected
    target = next(r for r in original if r['oa'] == expected)
    for field in ['doi', 'type', 'venue', 'date', 'landing', 'authorship', 'appointment', 'identity']:
        assert rows[0][field] == target[field]
    assert rows[0]['_bylines'] == [(target['byline'], target['byline_school']),
                                  (original[0]['byline'], original[0]['byline_school'])]
    assert rows[0]['editions'][0]['oa'] == original[0]['oa']
    assert not any(k.startswith('_eligible') or k == '_source_partition' for k in rows[0])


def test_actual_hmm_preprint_without_full_publisher_is_not_reconstructed():
    source = sources()['hmm_complete_native_records'][0]
    source['editions'] = [dict(oa='publisher-pointer-only', doi=source['doi'], work=source['work'], year=2019, venue='ITCS')]
    rows, _ = folded([source])
    assert rows[0]['oa'] == source['oa'] and rows[0]['type'] == 'preprint'
    assert rows[0]['landing'] == source['landing'] and rows[0]['authorship'] == source['authorship']


def test_actual_balcan_encoding_duplicate_joins_only_on_exact_oa_with_compatible_evidence():
    group = next(g for g in sources()['native_duplicate_groups'] if g['pi'] == 'Maria Balcan')
    before = copy.deepcopy(group['rows']); rows, _ = folded(group['rows'])
    assert group['rows'] == before and len(rows) == 1
    assert rows[0]['oa'] == group['oa']
    assert set(rows[0]['byline']) <= set(a for names, _ in rows[0]['_bylines'] for a in names)
    assert len(rows[0]['_bylines']) == 2
    assert {r.get('doi') or '' for r in before} == {rows[0].get('doi') or '', *[e.get('doi') or '' for e in rows[0]['editions']]}


def test_actual_ryan_source_distinct_dois_and_ordered_bylines_are_not_blindly_joined():
    group = next(g for g in sources()['native_duplicate_groups'] if g['pi'] == "Ryan O'Donnell")
    original = copy.deepcopy(group['rows']); rows, n = folded(group['rows'])
    assert len(rows) == 2 and n['source_distinct_same_oa_records'] == 2
    assert {r['doi'] for r in rows} == {r['doi'] for r in original}
    assert {r['work'] for r in rows} == {r['work'] for r in original}
    assert all(r['byline'] == next(s['byline'] for s in original if s['doi'] == r['doi']) for r in rows)


def test_new_cross_component_contradictions_withhold_join_without_rewriting_sources():
    a, b = copy.deepcopy(sources()['native_duplicate_groups'][0]['rows'])
    b['doi'] = '10.2000/different'
    original = [a, b]; before = copy.deepcopy(original); diagnostics = []; n = Counter()
    unique = papers.collapse_eligible_sources(original, n, diagnostics=diagnostics)
    rows = papers.merge_editions(unique, n, diagnostics=diagnostics)
    assert original == before and len(rows) == 2
    assert any(d.get('reason') == 'distinct_populated_doi_components' for d in diagnostics)


def test_new_transitive_missing_doi_bridge_never_picks_the_first_neighbor():
    a, template = copy.deepcopy(sources()['native_duplicate_groups'][0]['rows'])
    a['title'] = 'First independent scientific component'
    b = copy.deepcopy(template); b.update(title='Unidentified independent scientific component', doi='', work='missing')
    c = copy.deepcopy(template); c.update(title='Second independent scientific component', doi='10.2000/different', work='other')
    for original in [[a, b, c], [c, b, a]]:
        before = copy.deepcopy(original); diagnostics = []; n = Counter()
        unique = papers.collapse_eligible_sources(original, n, diagnostics=diagnostics)
        rows = papers.merge_editions(unique, n, diagnostics=diagnostics)
        assert original == before and len(rows) == 3
        assert any(d.get('reason') == 'transitive_missing_doi_bridge' for d in diagnostics)


def test_missing_doi_cannot_transitively_join_two_source_distinct_collection_works():
    a, b = copy.deepcopy(sources()['native_duplicate_groups'][0]['rows'])
    third = copy.deepcopy(b); third.update(oa='another-complete-oa', doi='10.2000/different')
    rows, _ = folded([a, b, third])
    assert len(rows) == 2
    assert {r.get('doi') for r in rows} == {a['doi'], third['doi']}
    assert len({r['work'] for r in rows}) == 2


def test_preferred_target_must_be_one_of_the_complete_eligible_records():
    original = sources()['polar_complete_native_records'][:1]
    missing = copy.deepcopy(sources()['polar_complete_native_records'][1])
    with pytest.raises(papers.EditionIdentityConflict, match='not a complete eligible source'):
        folded(original, preferred=lambda group: missing)


def chapter(work, number, oa):
    return dict(pi='Ada Lovelace', work=work, oa=oa, doi=f'10.1000/book_{number}', title='Chapter ' + str(number),
                year=2020, type='book-chapter', venue='Collected Research Book', byline=['Ada Lovelace'], byline_school=[])


def test_six_source_versions_of_one_chapter_never_trigger_five_chapter_book_fold():
    originals = [chapter('one-scientific-chapter', 1, 'version-' + str(i)) for i in range(6)]
    rows, n = folded(originals, 'princeton')
    assert len(rows) == 1 and n['book_chapters_folded'] == 0 and 'chapters_folded' not in rows[0]
    assert len(rows[0]['_bylines']) == 6


def test_five_distinct_chapters_fold_once_even_with_duplicate_source_editions():
    originals = [chapter('chapter-' + str(i), i, f'oa-{i}-{j}') for i in range(5) for j in range(2)]
    rows, n = folded(originals, 'princeton')
    assert len(rows) == 1 and n['book_chapters_folded'] == 4 and rows[0]['chapters_folded'] == 5
    assert len(rows[0]['_bylines']) == 2


def native_pair(tmp_path, target_fault=None, review=False, reverse=False):
    title = 'A Complete Source Bound Collection Research Paper'
    source = T.work('W501', title, 2020, [T.au('Ada Lovelace', 'A1'), T.au('Alan Turing', 'A9')],
                    typ='preprint', doi='10.1/w1')
    source['primary_location'].update(version='submittedVersion', is_published=False)
    source['primary_location']['source']['type'] = 'repository'
    target = T.work('W502', title, 2020, [T.au('Ada Lovelace', 'A1')], doi='10.1/w1')
    target['primary_location'].update(version='publishedVersion', is_published=True)
    if target_fault == 'school':
        target['authorships'] = [T.au('Ada Lovelace', 'A1', school=False, raw=['Other University'])]
    elif target_fault == 'identity':
        target['authorships'] = [T.au('Another Researcher', 'A1')]
    elif target_fault == 'appointment':
        target.update(publication_year=2018, publication_date='2018-05-01')
    elif target_fault == 'type':
        target['type'] = 'dataset'
        target['authorships'].append(T.au('Bruno Schmitt Antunes', 'A8'))
    T.write_school(tmp_path, sweep=[target, source] if reverse else [source, target])
    if target_fault == 'appointment':
        overrides = copy.deepcopy(T.OVERRIDES); overrides[T.SCHOOL]['Ada Lovelace']['periods'][0]['start'] = '2019'
        T.put(tmp_path, 'census-overrides.json', None).write_text(json.dumps(overrides))
    if review:
        write_review(tmp_path, [decision('W501', 'merge', into={'oa': T.OA + 'W502'})])
    return source, target


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('reverse', [False, True])
def test_native_same_collection_publisher_preserves_members_and_source_only_candidate_byline(tmp_path, reverse):
    source, target = native_pair(tmp_path, reverse=reverse)
    before = T.run_stages(tmp_path, upto='students'); members = copy.deepcopy(before.stu)
    ctx = T.run_stages(tmp_path, upto='papers'); rows = list(T.rows_of(ctx, 'Ada Lovelace').values())
    assert len(rows) == 1 and rows[0]['oa'] == target['id']
    assert rows[0]['authorship']['raw_name'] == 'Ada Lovelace' and rows[0]['appointment']
    assert any(source['id'] == e['oa'] for e in rows[0]['editions'])
    assert ctx.stu == members
    links.link_students(ctx)
    relevant = [x for x in ctx.sp if x['pi'] == 'Ada Lovelace']
    assert {x['student']: x['status'] for x in relevant} == {'p_alan': 'candidate', 'p_linus': 'verified'}
    # The fixture's pre-existing verified collection-person link remains verified; a byline match never upgrades.
    assert all(x['oa'] == target['id'] for x in relevant)


@pytest.mark.usefixtures('layout')
def test_exact_preferred_target_can_select_complete_same_collection_metadata(tmp_path):
    source, target = native_pair(tmp_path, review=True)
    ctx = T.run_stages(tmp_path, upto='papers'); reviewed_claims.apply(ctx)
    assert len(ctx.rows) == 1 and ctx.rows[0]['oa'] == target['id']
    assert ctx.paper_claim_review['decisions'][0]['outcome'] == 'preferred_edition_selected'
    assert any('Alan Turing' in names for names, _ in ctx.rows[0]['_bylines'])


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('fault', ['school', 'identity', 'appointment', 'type'])
def test_same_collection_target_still_needs_every_native_gate(tmp_path, fault):
    source, target = native_pair(tmp_path, target_fault=fault)
    ctx = T.run_stages(tmp_path, upto='papers'); row = next(r for r in ctx.rows if r['pi'] == 'Ada Lovelace')
    assert row['oa'] == source['id'] and not row['editions']
    assert all(target['id'] != r['oa'] for r in ctx.rows)
    links.link_students(ctx)
    assert not any(x['student'] == 'p_bruno' for x in ctx.sp)


@pytest.mark.usefixtures('layout')
def test_independently_eligible_recovery_is_not_skipped_for_an_existing_collection_work(tmp_path):
    source, _ = native_pair(tmp_path)
    # Leave only the manuscript raw source; the full publisher record enters through ordinary R36 recovery.
    db = T.put(tmp_path, 'openalex-sweep.sqlite'); db.unlink(); T.write_school(tmp_path, sweep=[source])
    recovered = dict(pi='Ada Lovelace', title=source['title'], year=2020, doi='10.1/w1', dblp_key='conf/example/Full20',
                     byline=['Ada Lovelace'], venue='Published Proceedings',
                     evidence=dict(oa='https://dblp.org/rec/conf/example/Full20', basis='page1_publisher', how='publisher PDF',
                                   url='https://example.edu/paper.pdf', pdf_sha256='a' * 64,
                                   quotes=['Ada Lovelace, Princeton University']))
    T.put(tmp_path, 'dblp-recovered.jsonl.gz').write_bytes(gzip.compress((json.dumps(recovered)+'\n').encode()))
    ctx = T.run_stages(tmp_path, upto='papers'); row = next(r for r in ctx.rows if r['pi'] == 'Ada Lovelace')
    assert row['oa'] == recovered['evidence']['oa'] and row['type'] == 'article'
    assert row['authorship']['page1']['pdf_sha256'] == 'a' * 64
    assert row['source'] == 'dblp_recover:page1_publisher' and row['identity'] == 'dblp_person_page'
    assert any('Alan Turing' in names for names, _ in row['_bylines'])


@pytest.mark.usefixtures('layout')
def test_nonpaper_duplicate_cannot_hide_the_real_paper_or_lend_its_student_byline(tmp_path):
    invalid, target = native_pair(tmp_path)
    invalid.update(title='Editorial: A Source Bound Issue Introduction', type='article')
    db = T.put(tmp_path, 'openalex-sweep.sqlite'); db.unlink(); T.write_school(tmp_path, sweep=[invalid, target])
    ctx = T.run_stages(tmp_path, upto='papers'); row = next(r for r in ctx.rows if r['pi'] == 'Ada Lovelace')
    assert row['oa'] == target['id'] and not row['editions']
    links.link_students(ctx)
    assert not any(x['student'] == 'p_alan' for x in ctx.sp)


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('fault', ['identity', 'school', 'appointment', 'type'])
def test_newly_preserved_recovery_cannot_waive_existing_work_gates(tmp_path, fault):
    source, _ = native_pair(tmp_path)
    T.put(tmp_path, 'openalex-sweep.sqlite').unlink(); T.write_school(tmp_path, sweep=[source])
    recovered = dict(pi='Ada Lovelace', title=source['title'], year=2020, doi='10.1/w1', dblp_key='conf/example/Full20',
                     byline=['Ada Lovelace'], venue='Published Proceedings',
                     evidence=dict(oa='https://dblp.org/rec/conf/example/Full20', basis='page1_publisher', how='publisher PDF',
                                   url='https://example.edu/paper.pdf', pdf_sha256='a' * 64,
                                   quotes=['Ada Lovelace, Princeton University']))
    if fault == 'identity':
        recovered['byline'] = ['Another Researcher']
    elif fault == 'school':
        recovered['evidence'] = dict(oa='https://openalex.org/W599', basis='openalex_authorship', school_via=['Other University'],
                                     openalex_work=T.work('W599', source['title'], 2020,
                                                          [T.au('Ada Lovelace', 'A1', school=False, raw=['Other University'])]))
    elif fault == 'appointment':
        recovered['year'] = 2018
        overrides = copy.deepcopy(T.OVERRIDES); overrides[T.SCHOOL]['Ada Lovelace']['periods'][0]['start'] = '2019'
        T.put(tmp_path, 'census-overrides.json', None).write_text(json.dumps(overrides))
    else:
        recovered['type'] = 'dataset'
    T.put(tmp_path, 'dblp-recovered.jsonl.gz').write_bytes(gzip.compress((json.dumps(recovered)+'\n').encode()))
    ctx = T.run_stages(tmp_path, upto='papers'); row = next(r for r in ctx.rows if r['pi'] == 'Ada Lovelace')
    assert row['oa'] == source['id'] and not row['editions']


@pytest.mark.parametrize('index', range(51))
def test_actual_51_source_conflicts_preserve_established_identity_and_all_bylines(index):
    corpus = sources()['actual_native_51_case_corpus']; case = corpus['cases'][index]
    original = copy.deepcopy(case['records']); before = copy.deepcopy(original); diagnostics = []; n = Counter()
    assert hashlib.sha256(json.dumps(original, sort_keys=True, ensure_ascii=False).encode()).hexdigest() == case['reviewed_projection_sha256']
    unique = papers.collapse_eligible_sources(original, n, diagnostics=diagnostics)
    rows = papers.merge_editions(unique, n, diagnostics=diagnostics)
    assert original == before and len(rows) == 1
    assert diagnostics and not any(d['kind'] == 'new_oa_join_withheld' for d in diagnostics)
    assert sorted(json.dumps([r['byline'], r['byline_school']]) for r in original) == sorted(json.dumps(b) for b in rows[0]['_bylines'])
    fields = ['oa', 'work', 'title', 'doi', 'date', 'year', 'type', 'identity', 'byline', 'byline_school']
    # Equal title/DOI records can carry different types; selection must copy one entire source, not a field mixture.
    assert any(all(rows[0].get(field) == r.get(field) for field in fields) for r in original)
    assert not any(k.startswith('_legacy') or k.startswith('_eligible') for k in rows[0])


def test_actual_navcog_metadata_title_change_cannot_join_an_unrelated_legacy_component():
    case = next(c for c in sources()['actual_native_51_case_corpus']['cases'] if c['oa'].endswith('W2477723829'))
    actual = copy.deepcopy(case['records']); alternate = actual[1]
    # The first two records are exact source-bound native observations. The third is an explicit synthetic
    # collision: its legacy identity has the alternate's long title but an independent source/DOI/work.
    other = copy.deepcopy(actual[0]); other.update(oa='https://example.test/independent-work', work='independent-work',
                                                  doi='10.2000/independent', title=alternate['title'])
    original = actual + [other]
    preferred = lambda group: next((r for r in group if r.get('source', '').startswith('dblp_recover:')), None)
    rows, _ = folded(original, preferred=preferred)
    assert len(rows) == 2 and rows[0]['title'] == rows[1]['title']
    assert {r['work'] for r in rows} == {actual[0]['work'], other['work']}
    assert {r['doi'] for r in rows} == {actual[0]['doi'], other['doi']}
    assert len(next(r for r in rows if r['work'] == actual[0]['work'])['_bylines']) == 2


@pytest.mark.usefixtures('layout')
def test_exact_held_recovery_cannot_poison_a_genuine_existing_work(tmp_path):
    source, _ = native_pair(tmp_path)
    T.put(tmp_path, 'openalex-sweep.sqlite').unlink(); T.write_school(tmp_path, sweep=[source])
    recovered = dict(pi='Ada Lovelace', title=source['title'], year=2020, doi='10.1/w1', dblp_key='conf/example/Bad20',
                     byline=['Ada Lovelace'], venue='Proceedings', evidence=dict(oa=T.OA + 'W599', basis='page1_publisher',
                     how='publisher PDF', url='https://example.edu/paper.pdf', pdf_sha256='a'*64, quotes=['Ada Lovelace, Princeton University']))
    T.put(tmp_path, 'dblp-recovered.jsonl.gz').write_bytes(gzip.compress((json.dumps(recovered)+'\n').encode()))
    write_review(tmp_path, [decision('W599', 'hold')])
    ctx = T.run_stages(tmp_path, upto='papers'); reviewed_claims.apply(ctx)
    assert len(ctx.rows) == 1 and ctx.rows[0]['oa'] == source['id'] and not ctx.rows[0]['editions']
    assert ctx.paper_claim_review['decisions'][0]['outcome'] == 'held_before_identity'


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('reverse', [False, True])
def test_translated_source_cannot_become_identity_representative_or_lend_a_student_byline(tmp_path, reverse):
    source, target = native_pair(tmp_path)
    source.update(title='Die Theorie der Berechnung', type='book-chapter')
    target['type'] = 'book-chapter'
    T.put(tmp_path, 'openalex-sweep.sqlite').unlink()
    T.write_school(tmp_path, sweep=[target, source] if reverse else [source, target])
    ctx = T.run_stages(tmp_path, upto='papers')
    row = next(r for r in ctx.rows if r['pi'] == 'Ada Lovelace')
    assert row['oa'] == target['id'] and not row['editions']
    assert ctx.n['translated_editions_dropped'] == 1
    links.link_students(ctx)
    assert not any(x['student'] == 'p_alan' for x in ctx.sp)


def test_foreign_title_exception_remains_available_for_an_original_language_source():
    row = chapter('source-work', 1, 'source-oa'); row['title'] = 'Die Theorie der Berechnung'
    assert papers.eligible_untranslated_sources([row], 'epfl') == ([row], None)
