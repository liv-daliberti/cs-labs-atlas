"""Literal CJK evidence must survive indexing/title keys without becoming an identity or school verdict."""
import base64
import collections
import copy
import hashlib
import json
from pathlib import Path
import re
import unicodedata
import zlib

import pytest

from pihier import common as C, identity, papers
import school_web
import test_build_rules as B

CN = '张荷花'
TITLE = '基于规则的自动合规审查体系的高层次规则间关系表示'
OTHER = '基于深度学习的公共建筑像素施工图空间识别'
AI = 'AI审图机器人在消防图审业务运营管理系统中的应用'


def test_original_official_profile_proves_literal_names_and_titles_only():
    r = json.loads((Path(__file__).resolve().parent / 'fixtures/tsinghua-cjk-publications-1108.json').read_text())
    raw = zlib.decompress(base64.b64decode(r['source_raw_zlib_base64']))
    assert hashlib.sha256(raw).hexdigest() == r['source_sha256']
    text = school_web.flat(school_web.extract.blocks(raw, 'text/html', r['source_url']))
    assert r['quote'] in text and all(s in r['quote'] for s in [CN, TITLE, OTHER, AI])
    assert C.norm_title(TITLE) and C.norm_title(OTHER) != C.norm_title(TITLE)


@pytest.mark.parametrize('text', ['ÉCOLE naïve Café', 'Straße Æ Ø æ œ ł đ Þ', 'Hawaiʻi', 'John’s 3-D: naïve résumé', 'ABC123', '...'])
def test_existing_latin_fold_stays_exact(text):
    old = re.sub('[^a-z0-9]', '', unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().lower())
    assert C.norm_title(text) == old


def row(title, oa, year=2025):
    return dict(pi=CN, work=None, oa=oa, doi=None, title=title, year=year, venue=None,
                type='article', byline=[CN], byline_school=[CN])


def test_distinct_chinese_titles_and_mixed_titles_with_the_same_acronym_do_not_merge():
    for a, b in [(TITLE, OTHER), (AI, AI.replace('消防', '交通'))]:
        assert C.norm_title(a) != C.norm_title(b)
        out = papers.merge_editions([row(a, 'W1'), row(b, 'W2')], collections.Counter())
        assert len(out) == 2


def test_the_same_chinese_title_can_merge_its_editions_without_losing_bylines():
    n = collections.Counter();out = papers.merge_editions([row(TITLE, 'W1'), row(TITLE, 'W2')], n)
    assert len(out) == 1 and len(out[0]['_bylines']) == 2 and n['edition_records_merged'] == 1


def test_collection_matcher_requires_a_nonempty_exact_title_key_or_a_doi():
    match = C.collection_work_matcher({'a': dict(title=TITLE, year=2025), 'p': dict(title='!!!', doi='10.1/p')})
    assert match(dict(title=TITLE, publication_year=2025)) == 'a'
    # Incomplete metadata has no year; a different literal title still cannot become this collection work.
    assert match(dict(title=OTHER)) is None
    assert match(dict(title='...')) is None
    assert match(dict(title='...', doi='10.1/p')) == 'p'


def rename_pi(monkeypatch, label):
    census = copy.deepcopy(B.CENSUS);people = copy.deepcopy(B.PEOPLE);overrides = copy.deepcopy(B.OVERRIDES)
    next(x for x in census if x['name'] == 'Ada Lovelace')['name'] = label
    next(x for x in people if x['id'] == 'p_ada')['name'] = label
    pi = overrides[B.SCHOOL].pop('Ada Lovelace');overrides[B.SCHOOL][label] = pi
    pi['periods'][0]['evidence'][0]['quote'] = label + ' joined Princeton in2015 (synthetic test appointment).'
    monkeypatch.setattr(B, 'CENSUS', census);monkeypatch.setattr(B, 'PEOPLE', people);monkeypatch.setattr(B, 'OVERRIDES', overrides)
    monkeypatch.setattr(identity, 'DUMP_PERSONS', None)
    return pi


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('case,keep', [('supported', True), ('unproved_identity', False), ('other_school', False), ('outside_appointment', False), ('different_literal', False)])
def test_exact_opaque_name_enters_candidates_but_all_admission_gates_still_apply(tmp_path, monkeypatch, case, keep):
    pi = rename_pi(monkeypatch, CN)
    if case == 'unproved_identity':pi['openalex'] = []
    if case == 'outside_appointment':pi['periods'][0]['start'] = '2026'
    raw = '张合花' if case == 'different_literal' else CN
    w = B.work('WCJK', TITLE, 2025, [B.au(raw, 'A1', school=case != 'other_school')])
    B.write_school(tmp_path, sweep=[w]);ctx = B.run_stages(tmp_path, upto='papers')
    assert any(r['oa'] == w['id'] for r in ctx.rows) is keep
    assert bool(ctx.hits) is (case != 'different_literal')
    if keep:
        r = next(r for r in ctx.rows if r['oa'] == w['id'])
        assert r['identity'] == 'reviewed_openalex_author_id' and r['authorship']['raw_name'] == CN
        assert r['authorship']['school_via'] and r['appointment']['periodId']


@pytest.mark.usefixtures('layout')
def test_explicit_bilingual_label_still_matches_its_supplied_latin_reading(tmp_path, monkeypatch):
    # Exact existing label from root's read-only HKUST diagnostic; no HKUST input or transliteration is generated.
    label = 'Song GUO 郭嵩';rename_pi(monkeypatch, label)
    w = B.work('WBILINGUAL', 'A Latin Reading', 2025, [B.au('Song Guo', 'A1')])
    B.write_school(tmp_path, sweep=[w]);ctx = B.run_stages(tmp_path, upto='papers')
    assert any(r['oa'] == w['id'] and r['pi'] == label for r in ctx.rows)


def test_blocked_coauthor_cluster_keeps_distinct_opaque_names_distinct():
    p = dict(blockedClusters=[dict(coauthors=[CN], min_coauthors=1)])
    assert not identity.in_blocked_cluster(p, dict(authorships=[dict(raw_author_name='李振华')]))
    assert identity.in_blocked_cluster(p, dict(authorships=[dict(raw_author_name=CN)]))


def test_title_identity_anchor_needs_a_nonempty_exact_literal_key():
    from types import SimpleNamespace
    dd = lambda: collections.defaultdict(set)
    ctx = SimpleNamespace(blocked=dd(), reviewed_oa=dd(), orcids=dd(), verified=dd(),
                          dblp_doi=dd(), dblp_title=collections.defaultdict(dict),
                          own_list=collections.defaultdict(dict),lab_page=collections.defaultdict(list),
                          advisee_names=collections.defaultdict(list),pid0={CN: dict(names=[CN])})
    ctx.own_list[CN][C.norm_title(TITLE)] = 2025
    a = B.au(CN, 'A1'); w = B.work('WCJK', TITLE, 2025, [a])
    assert identity._authorship_identity(ctx,CN,w,a,None) == 'pi_institutional_publication_list'
    assert identity._authorship_identity(ctx,CN,dict(w,title=OTHER),a,None) is None
    # Even a legacy empty key cannot establish any punctuation-only or missing title's identity.
    ctx.dblp_title[CN][''] = 2025;ctx.own_list[CN][''] = 2025
    assert identity._authorship_identity(ctx,CN,dict(w,title='...'),a,None) is None


@pytest.mark.parametrize('a,b', [('中文研究一','中文研究二'), ('Йод','Иод'), ('άλφα','αλφα'), ('نتيجة١','نتيجة٢')])
def test_other_script_letters_and_digits_do_not_vanish_or_collapse(a,b):
    assert C.norm_title(a) and C.norm_title(b) and C.norm_title(a) != C.norm_title(b)
