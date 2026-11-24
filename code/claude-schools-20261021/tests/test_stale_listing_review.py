"""R-PAP-30 (2026-11-02, the Michigan stage-9 sample: Ziyou Song). A department listing contradicted by OpenAlex (the PI's works
of that year credit another institution, none the school) is a review item, and a record whose twin credits the PI elsewhere
only is not credited to the school; no period is closed."""
import pytest

import test_build_rules as T

OA, au, work = T.OA, T.au, T.work
pytestmark = pytest.mark.usefixtures('layout')


def au_at(name, aid, inst_id, inst_name, pos='middle'):
    return dict(author_position=pos, raw_author_name=name, author=dict(id=OA + aid, display_name=name),
                institutions=[dict(id=OA + inst_id, display_name=inst_name, type='education', lineage=[OA + inst_id])], raw_affiliation_strings=[inst_name])


def faculty(monkeypatch, *years):
    """Grace Hopper's faculty listings of these years (the first and last are her arrival and departure years)."""
    monkeypatch.setattr(T, 'LISTINGS', [dict(pi='Grace Hopper', year=y, capture_url=f'https://web.archive.org/web/{y}0301000000/https://cs.example.edu/people',
                                             sha256=T.SHA, quote='Grace Hopper Professor of Computer Science', rank_as_listed='Professor',
                                             department='Computer Science') for y in years])


def build(tmp_path, sweep):
    T.write_school(tmp_path, sweep)
    return T.run_stages(tmp_path, upto='papers')


def test_R_PAP_30_listing_year_contradicted_by_openalex(tmp_path, monkeypatch):
    faculty(monkeypatch, 2019, 2020, 2022)
    sweep = [work('W60', 'Elsewhere One', 2020, [au_at('Grace Hopper', 'A2', 'I77', 'Elsewhere U', pos='first')]),
             work('W61', 'Elsewhere Two', 2020, [au_at('Grace Hopper', 'A2', 'I77', 'Elsewhere U', pos='first')]),
             work('W62', 'Advisee Route 2020', 2020, [au('Grace Hopper', 'A2', school=False, pos='first'), au('Rosa Researched', 'A66')])]
    ctx = build(tmp_path, sweep)
    assert 'Advisee Route 2020' not in T.rows_of(ctx, 'Grace Hopper')
    (e,) = [x for x in ctx.listing_review if x['kind'] == 'listing_year']
    assert (e['pi'], e['year'], e['works_at_school']) == ('Grace Hopper', 2020, 0) and e['works_at_other_institutions'] == {'Elsewhere U': 2}
    assert e['listing']['quote'].startswith('Grace Hopper') and [w['title'] for w in e['withheld']] == ['Advisee Route 2020']
    assert ctx.n['stale_listing_pi_years'] == 1 and ctx.n['stale_listing_withheld'] == 1
    assert all(not q['end'] or q['id'] for p in ctx.pis for q in p['periods'])      # no period was touched


def test_R_PAP_30_arrival_and_departure_years_are_left_to_the_transition_rules(tmp_path, monkeypatch):
    """A move year has works at both institutions: the first and last listing years (R-PAP-13) are never flagged."""
    faculty(monkeypatch, 2020)                                                   # 2020 is her only listing year
    sweep = [work('W60', 'Elsewhere One', 2020, [au_at('Grace Hopper', 'A2', 'I77', 'Elsewhere U', pos='first')]),
             work('W61', 'Elsewhere Two', 2020, [au_at('Grace Hopper', 'A2', 'I77', 'Elsewhere U', pos='first')])]
    assert build(tmp_path, sweep).n['stale_listing_pi_years'] == 0


def test_R_PAP_30_listing_year_with_a_school_work_is_not_flagged(tmp_path, monkeypatch):
    faculty(monkeypatch, 2019, 2020, 2022)
    sweep = [work('W60', 'Elsewhere One', 2020, [au_at('Grace Hopper', 'A2', 'I77', 'Elsewhere U', pos='first')]),
             work('W61', 'Elsewhere Two', 2020, [au_at('Grace Hopper', 'A2', 'I77', 'Elsewhere U', pos='first')]),
             work('W7', 'A Listed Year', 2020, [au('Grace Hopper', 'A2')])]
    ctx = build(tmp_path, sweep)
    assert ctx.n['stale_listing_pi_years'] == 0 and 'A Listed Year' in T.rows_of(ctx, 'Grace Hopper')


def dated(w, date):
    w['publication_date'] = date
    return w


def test_R_PAP_30_twin_dated_in_a_contradicted_listing_year(tmp_path, monkeypatch):
    """Song's pattern: the unaffiliated record is dated 2025-01-01, its other record (another university) 2024-12, and the 2024
    listing is contradicted by the PI's works: the paper is withheld; the review list says why."""
    faculty(monkeypatch, 2019, 2020, 2021, 2022)
    sweep = [work('W60', 'Elsewhere One', 2020, [au_at('Grace Hopper', 'A2', 'I77', 'Elsewhere U', pos='first')]),
             work('W61', 'Elsewhere Two', 2020, [au_at('Grace Hopper', 'A2', 'I77', 'Elsewhere U', pos='first')]),
             dated(work('W63', 'Twin Late Paper', 2020, [au_at('Grace Hopper', 'A2', 'I77', 'Elsewhere U', pos='first')]), '2020-12-15'),
             dated(work('W64', 'Twin Late Paper', 2021, [au('Grace Hopper', 'A2', school=False, pos='first'), au('Rosa Researched', 'A66')],
                        typ='preprint'), '2021-01-01')]
    ctx = build(tmp_path, sweep)
    assert 'Twin Late Paper' not in T.rows_of(ctx, 'Grace Hopper')
    (e,) = [x for x in ctx.listing_review if x['kind'] == 'twin_record']
    assert e['withheld'] is True and e['twin'][0]['institutions'] == ['Elsewhere U'] and e['twin'][0]['date'] == '2020-12-15'
    assert ctx.n['twin_record_credits_elsewhere'] == 1 and ctx.n['twin_record_withheld'] == 1


def twin_sweep(twin_inst):
    return [work('W50', 'Twin Paper On Batteries', 2020, [au('Ada Lovelace', 'A1', school=False, pos='first'), au('Alan Turing', 'A9')]),
            dated(work('W51', 'Twin Paper On Batteries', 2019, [twin_inst, au('Alan Turing', 'A9')], typ='preprint'), '2019-12-01')]


def test_R_PAP_30_twin_elsewhere_in_an_ordinary_year_is_review_only(tmp_path):
    ctx = build(tmp_path, twin_sweep(au_at('Ada Lovelace', 'A1', 'I77', 'National University of Singapore', pos='first')))
    assert 'Twin Paper On Batteries' in T.rows_of(ctx, 'Ada Lovelace')            # no contradicted listing year: kept
    (e,) = [x for x in ctx.listing_review if x['kind'] == 'twin_record']
    assert e['oa'].endswith('W50') and e['withheld'] is False and ctx.n['twin_record_credits_elsewhere'] == 1


def test_R_PAP_30_twin_crediting_the_school_is_no_review_item(tmp_path):
    ctx = build(tmp_path, twin_sweep(au('Ada Lovelace', 'A1', pos='first')))
    assert 'Twin Paper On Batteries' in T.rows_of(ctx, 'Ada Lovelace') and ctx.n['twin_record_credits_elsewhere'] == 0


def test_R_PAP_30_review_list_renders(tmp_path):
    import json
    import stale_listing_review as R
    review = [dict(pi='Grace Hopper', kind='listing_year', year=2020, listing=dict(url='u', quote='Grace Hopper Professor'),
                   works_at_other_institutions={'Elsewhere U': 2}, works_at_school=0, withheld=[dict(oa='W1')], withheld_n=1),
              dict(pi='Ada Lovelace', kind='twin_record', year=2025, title='A | B', twin=[dict(oa='W2', institutions=['NUS'], date='2024-12')], withheld=True)]
    (tmp_path / 'princeton').mkdir()
    (tmp_path / 'princeton' / 'report.json').write_text(json.dumps(dict(staleListingReview=review)))
    out = tmp_path / 'r.md'
    R.main(['princeton', '--root', str(tmp_path), '--out', str(out)])
    text = out.read_text()
    assert '| Grace Hopper | 2020 |' in text and 'Elsewhere U (2)' in text and '| Ada Lovelace | 2025 | A / B | NUS (2024-12) | yes |' in text
