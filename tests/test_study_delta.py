"""The delta scoring of the 12-school study (ai-writing/study/study_delta_build.py): per-paper shares from passage scores (pandas)."""
import pytest

pytest.importorskip('pandas')
import pandas as pd  # noqa: E402
import study_delta_build as D  # noqa: E402


def test_paper_table_shares_and_usable_rule():
    rows = []
    # paper a: 4 main passages (1 flagged, 1 abstained), 2 appendix (1 flagged); paper b: short main body (<1000 words): shares are blanked
    for i, (sec, ab, fl) in enumerate([('main', 0, 1), ('main', 0, 0), ('main', 1, 0), ('main', 0, 0), ('appendix', 0, 1), ('appendix', 0, 0)]):
        rows.append(dict(paper_id='a', i=i, section=sec, abstain=ab, flagged=fl))
    rows += [dict(paper_id='b', i=0, section='main', abstain=0, flagged=1)]
    sc = pd.DataFrame(rows)
    secs = pd.DataFrame([dict(paper_id='a', main_words=5000, appendix_found=1, split_error=None), dict(paper_id='b', main_words=300, appendix_found=0, split_error=None)])
    delta = pd.DataFrame([dict(paper_id='a', oa='W1', year=2024, home_school='jhu'), dict(paper_id='b', oa='W2', year=2025, home_school='harvard')])
    t = D.paper_table(sc, secs, delta).set_index('paper_id')
    assert t.loc['a', 'n_main_scored'] == 3 and t.loc['a', 'n_main_abstained'] == 1
    assert t.loc['a', 'ai_share_main'] == pytest.approx(1 / 3)
    assert t.loc['a', 'ai_share_main_appendix'] == pytest.approx(2 / 5)
    assert t.loc['a', 'abstained_share_main'] == pytest.approx(1 / 4)
    assert pd.isna(t.loc['b', 'ai_share_main']) and pd.isna(t.loc['b', 'ai_share_main_appendix'])
    assert not t['trained_on_v3'].any() and t.loc['a', 'home_school'] == 'jhu'
