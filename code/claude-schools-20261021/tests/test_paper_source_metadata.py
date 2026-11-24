"""A stale positive correction must stop before reintroducing the source-real false merge."""
import copy

import pytest

import test_source_metadata_review as T
from pihier import identity, papers, source_metadata as M


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('case_index', [0, 1])
@pytest.mark.parametrize('mutation', ['complete_source', 'eligible_byline', 'owned_record', 'ordinary_date'])
def test_actual_experience_stale_correction_stops_before_legacy_title_merge_and_keeps_originals(
        tmp_path, case_index, mutation):
    cs = T.cases(); rows = [T.row(c) for c in cs]
    ctx = T.context(tmp_path, cs)
    if mutation == 'complete_source':
        cs[case_index]['source_projection']['publication_date'] = '2020-02-03'
    elif mutation == 'eligible_byline':
        rows[case_index]['byline'] = list(reversed(rows[case_index]['byline']))
    elif mutation == 'owned_record':
        cs[case_index]['owned_publication']['title'] += ' Different source'
    before = copy.deepcopy((cs, rows, ctx.hits, ctx.dblp_persons))
    grouping_reached = False
    with pytest.raises(ValueError, match='requires renewed proof'):
        corrected = M.apply(ctx, rows, lambda w, title, row: '2001-01-01'
                            if mutation == 'ordinary_date' and row is rows[case_index] else row['date'])
        grouping_reached = True
        papers.collapse_eligible_sources(corrected, ctx.n)
    assert not grouping_reached
    assert (cs, rows, ctx.hits, ctx.dblp_persons) == before
    decision = ctx.paper_source_review['decisions'][-1]
    assert decision['status'] == 'held' and decision['original_eligible_row'] == rows[case_index]
    assert decision['available_complete_sources'] == [cs[case_index]['source_projection']]
    assert ctx.n['source_metadata_held'] == 1


@pytest.mark.usefixtures('layout')
def test_valid_two_source_real_corrections_leave_unrelated_complete_row_exact(tmp_path):
    cs = T.cases(); ctx = T.context(tmp_path, cs); rows = [T.row(c) for c in cs]
    unrelated = dict(rows[0], oa='https://openalex.org/W999999', doi='10.9/unrelated',
                     title='A distinct complete scientific title')
    before = copy.deepcopy((rows, unrelated, ctx.hits))
    out = M.apply(ctx, rows + [unrelated], lambda w, title, row: row['date'])
    assert (rows, unrelated, ctx.hits) == before and out[-1] is unrelated
    assert [r['title'] for r in out[:2]] == [c['expected_title'] for c in cs]
    assert ctx.n['source_metadata_projected'] == 2 and not ctx.n['source_metadata_held']


@pytest.mark.usefixtures('layout')
def test_native_matching_stale_review_raises_before_scientific_rows_or_links(tmp_path, monkeypatch):
    monkeypatch.setattr(identity, 'DUMP_PERSONS', None)
    cs = T.native_setup(tmp_path)
    review = T.review(cs[0]); review['source']['work_sha256'] = '0' * 64
    import json
    import atlas_paths as P
    import test_build_rules as B
    P.data_w('paper-source-review.json', B.SCHOOL, root=tmp_path).write_text(json.dumps(dict(
        version=1, school=B.SCHOOL, reviews=[review, T.review(cs[1])])))
    with pytest.raises(ValueError, match='requires renewed proof.*missing_complete_source'):
        B.run_stages(tmp_path, upto='links')
