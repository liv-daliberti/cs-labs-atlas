"""Exact reviewed targets choose complete eligible metadata before native edition folding."""
import copy
from collections import Counter

import pytest

from pihier import papers, reviewed_claims as R
from test_paper_claim_review import OA, context, decision, paper, write_review
import test_build_rules as T


def fold(ctx):
    ctx.rows = papers.merge_editions(ctx.rows, ctx.n, preferred=lambda group: R.preferred_edition(ctx, group))
    R.apply(ctx)
    return ctx.rows


def same_title(wid, **kwargs):
    return paper(wid, title=kwargs.pop('title', 'A Complete Scientific Research Paper'), **kwargs)


@pytest.mark.usefixtures('layout')
def test_sudan_drops_case_uses_exact_eligible_target_despite_bad_repository_flags(tmp_path):
    # Original frozen records: W4404342406 is arXiv; W7110142740 is the PI-linked RANDOM2025 DROPS article.
    doi = '10.4230/lipics.approx/random.2025.59'
    bad_flags = dict(version='submittedVersion', is_published=False, source_type='repository')
    names = ['Garg, Sumegha', 'Sudan, Madhu', 'Wu, Gabriel']
    authorship = dict(raw_name='Sudan, Madhu', institutions=['Harvard University'],
                      raw_affiliations=['School of Engineering and Applied Sciences, Harvard University, Cambridge, MA, USA'])
    source = same_title('W4404342406', pi='Madhu Sudan', doi=doi, type='preprint', venue='arXiv',
                        _edition_source=copy.deepcopy(bad_flags), byline=names, byline_school=names[1:],
                        title='Testing Tensor Products of Algebraic Codes', date='2024-10-30', year=2025,
                        identity='pi_orcid', authorship=authorship, appointment={'periodId': 'harvard_reviewed_3'})
    target = same_title('W7110142740', pi='Madhu Sudan', doi=doi, type='article', venue='DROPS',
                        _edition_source=copy.deepcopy(bad_flags), byline=names, byline_school=names[1:],
                        title=source['title'], date='2025-01-01', year=2025, identity='pi_orcid', authorship=authorship,
                        landing='https://doi.org/' + doi, appointment={'periodId': 'harvard_reviewed_3'})
    assert papers.merge_editions([copy.deepcopy(source), copy.deepcopy(target)], Counter())[0]['oa'] == source['oa']
    review = decision('W4404342406', 'merge', into={'oa': target['oa'], 'doi': doi}); review['pi'] = 'Madhu Sudan'
    write_review(tmp_path, [review])
    ctx = context(tmp_path, [source, target]); ctx.pis = [dict(pi='Madhu Sudan')]; rows = fold(ctx)
    assert len(rows) == 1 and rows[0]['oa'] == target['oa']
    assert rows[0]['authorship'] == target['authorship'] and rows[0]['appointment'] == target['appointment']
    assert rows[0]['landing'] == target['landing'] and rows[0]['type'] == 'article'
    assert rows[0]['date'] == target['date'] != source['date']
    assert rows[0]['_bylines'] == [(names, names[1:]), (names, names[1:])]
    assert rows[0]['editions'][0]['oa'] == source['oa']
    assert ctx.paper_claim_review['decisions'][0]['outcome'] == 'preferred_edition_selected'



@pytest.mark.usefixtures('layout')
def test_native_selection_keeps_source_only_student_byline_and_no_identity_upgrade(tmp_path):
    source = T.work('W501', 'A Source Bound Edition Preference Research Paper', 2020,
                    [T.au('Ada Lovelace', 'A1'), T.au('Alan Turing', 'A9')], doi='10.1000/shared')
    target = T.work('W502', source['title'], 2020, [T.au('Ada Lovelace', 'A1')], doi='10.1000/shared')
    for w in [source, target]:
        w['primary_location'].update(version='submittedVersion', is_published=False)
        w['primary_location']['source']['type'] = 'repository'
    T.write_school(tmp_path, sweep=[source, target]); write_review(tmp_path, [decision('W501', 'merge', into={'oa': OA + 'W502'})])
    ctx = T.run_stages(tmp_path, upto='papers'); R.apply(ctx)
    row = next(r for r in ctx.rows if r['pi'] == 'Ada Lovelace')
    assert row['oa'] == target['id'] and any('Alan Turing' in names for names, _ in row['_bylines'])
    from pihier import links
    links.link_students(ctx)
    assert any(x['student'] == 'p_alan' and x['oa'] == target['id'] for x in ctx.sp)
    assert all(x['status'] == 'candidate' for x in ctx.sp)


@pytest.mark.usefixtures('layout')
def test_compact_folded_target_is_not_reconstructed_into_a_publisher_record(tmp_path):
    source = same_title('W1', editions=[dict(oa=OA + 'W2', work=None, doi='10.1000/pub', year=2020, venue='Publisher')])
    write_review(tmp_path, [decision('W1', 'merge', into={'oa': OA + 'W2'})])
    ctx = context(tmp_path, [source]); R.apply(ctx)
    assert ctx.rows == []
    assert ctx.paper_claim_review['decisions'][0]['outcome'] == 'held_missing_preferred_target_record'


@pytest.mark.usefixtures('layout')
def test_ineligible_native_target_is_not_admitted_even_with_the_same_title(tmp_path):
    source = T.work('W501', 'A Source Bound Unavailable Target Research Paper', 2020, [T.au('Ada Lovelace', 'A1')])
    target = T.work('W502', source['title'], 2020, [T.au('Ada Lovelace', 'A1', school=False, raw=['Other University'])])
    T.write_school(tmp_path, sweep=[source, target]); write_review(tmp_path, [decision('W501', 'merge', into={'oa': OA + 'W502'})])
    ctx = T.run_stages(tmp_path, upto='papers'); R.apply(ctx)
    assert not T.rows_of(ctx, 'Ada Lovelace')
    assert ctx.paper_claim_review['decisions'][0]['outcome'] == 'held_missing_merge_target'


@pytest.mark.usefixtures('layout')
def test_same_doi_cannot_ambiguously_select_source_and_target(tmp_path):
    write_review(tmp_path, [decision('W1', 'merge', into={'doi': '10.1000/shared'})])
    ctx = context(tmp_path, [same_title('W1', doi='10.1000/shared'), same_title('W2', doi='10.1000/shared')])
    before = copy.deepcopy(ctx.rows)
    with pytest.raises(ValueError, match='ambiguous'):
        fold(ctx)
    assert ctx.rows == before


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('cycle', [True, False])
def test_cycles_and_conflicting_preferred_destinations_stop_before_row_mutation(tmp_path, cycle):
    reviews = [decision('W1', 'merge', into={'oa': OA + 'W2'}),
               decision('W2' if cycle else 'W3', 'merge', into={'oa': OA + ('W1' if cycle else 'W4')})]
    write_review(tmp_path, reviews)
    ctx = context(tmp_path, [same_title('W' + str(i)) for i in range(1, 5)])
    before = copy.deepcopy(ctx.rows)
    with pytest.raises(ValueError, match='cycle|conflicting'):
        fold(ctx)
    assert ctx.rows == before


@pytest.mark.usefixtures('layout')
def test_preferred_chains_resolve_to_complete_eligible_root_and_are_order_independent(tmp_path):
    write_review(tmp_path, [decision('W1', 'merge', into={'oa': OA + 'W2'}), decision('W2', 'merge', into={'oa': OA + 'W3'})])
    original = [same_title('W' + str(i), authorship={'raw_name': str(i)}) for i in range(1, 4)]
    a = context(tmp_path, original); b = context(tmp_path, list(reversed(original)))
    assert fold(a)[0]['oa'] == fold(b)[0]['oa'] == OA + 'W3'
    assert a.rows[0]['authorship'] == b.rows[0]['authorship'] == {'raw_name': '3'}
    assert all(d['outcome'] == 'preferred_edition_selected' for d in a.paper_claim_review['decisions'])
    assert {e['oa'] for e in a.rows[0]['editions']} == {OA + 'W1', OA + 'W2'}


@pytest.mark.usefixtures('layout')
def test_a_different_pi_or_identifier_never_becomes_the_requested_target(tmp_path):
    write_review(tmp_path, [decision('W1', 'merge', into={'oa': OA + 'W2'})])
    ctx = context(tmp_path, [same_title('W1'), same_title('W2', pi='Grace Hopper'), same_title('W3')])
    fold(ctx)
    assert not any(r['pi'] == 'Ada Lovelace' for r in ctx.rows)
    assert len(ctx.rows) == 1 and ctx.rows[0]['pi'] == 'Grace Hopper'
