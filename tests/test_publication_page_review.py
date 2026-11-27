"""Publisher ranges resolve article numbers without granting paper admission."""
import collections
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pytest

from pihier import papers, publication_pages as D


def install(tmp_path, monkeypatch, pages='1-14', change=None):
    message = dict(DOI='10.1145/3173574.3173970', title=['A Computing Study'], page=pages,
                   published={'date-parts': [[2018, 4, 21]]}, publisher='ACM', type='proceedings-article')
    if change:
        change(message)
    raw = json.dumps({'status': 'ok', 'message-type': 'work', 'message': message}).encode()
    sha = hashlib.sha256(raw).hexdigest()
    target = tmp_path / 'publication-page-sources' / (sha + '.json')
    target.parent.mkdir(); target.write_bytes(raw)
    monkeypatch.setattr(D.P, 'school_part', lambda *a, **kw: tmp_path)
    path = tmp_path / 'review.json'
    monkeypatch.setattr(D.P, 'data', lambda *a, **kw: path)
    review = dict(decision='confirm_publisher_page_range', match=dict(oa='https://openalex.org/W1', doi=message['DOI']),
                  title='A Computing Study', year=2018, pages=pages, reviewed_by='independent-source-reviewer',
                  reviewed_on='2026-11-27', why='Publisher range resolves DBLP article number.',
                  source=dict(url='https://api.crossref.org/works/10.1145/3173574.3173970', format='crossref_json',
                              http_status=200, captured='2026-11-27T01:44:20+00:00', sha256=sha, source_file=target.name))
    path.write_text(json.dumps(dict(version=1, school='test', decisions=[review])))
    row = dict(pi='Ada', oa=review['match']['oa'], doi=message['DOI'], title=review['title'], year=2018,
               type='conference-paper', venue='CHI', byline=['Ada'])
    return SimpleNamespace(school='test', here=tmp_path), row, target


def drop(row, reviews, page=(1, True)):
    counts = collections.Counter()
    pages = dict(doi={'Ada': {row['doi']: page}}, title={'Ada': {}})
    kept, reasons = papers.drop_not_papers([deepcopy(row)], {'Ada': {}}, counts, pages, page_reviews=reviews)
    return kept, reasons, counts


def test_full_publisher_range_supersedes_ambiguous_article_number(tmp_path, monkeypatch):
    ctx, row, _ = install(tmp_path, monkeypatch)
    original = deepcopy(row)
    assert not drop(row, None)[0]
    kept, _, counts = drop(row, D.prepare(ctx))
    assert kept == [row] and row == original
    assert counts['publisher_page_range_overrides'] == 1


def test_one_page_range_and_other_genre_rules_are_not_bypassed(tmp_path, monkeypatch):
    ctx, row, _ = install(tmp_path, monkeypatch, pages='1-1')
    row['type'] = 'conference-abstract'
    assert not drop(row, D.prepare(ctx))[0]


def test_precise_dblp_range_remains_in_force(tmp_path, monkeypatch):
    ctx, row, _ = install(tmp_path, monkeypatch)
    assert not drop(row, D.prepare(ctx), page=(1, False))[0]


@pytest.mark.parametrize('field,value', [('DOI', '10.1/wrong'), ('title', ['Wrong title']),
                                        ('published', {'date-parts': [[2019]]}), ('page', '396')])
def test_wrong_or_unbounded_primary_metadata_fails(tmp_path, monkeypatch, field, value):
    ctx, _, _ = install(tmp_path, monkeypatch, change=lambda m: m.update({field: value}))
    with pytest.raises(ValueError):
        D.prepare(ctx)


def test_changed_bytes_and_changed_indexed_target_fail(tmp_path, monkeypatch):
    ctx, row, target = install(tmp_path, monkeypatch)
    reviews = D.prepare(ctx)
    for field, value in [('doi', '10.1/wrong'), ('title', 'Wrong title'), ('year', 2019)]:
        changed = dict(row, **{field: value})
        with pytest.raises(ValueError):
            drop(changed, reviews)
    target.write_bytes(target.read_bytes() + b' ')
    del ctx._publication_page_reviews
    with pytest.raises(ValueError):
        D.prepare(ctx)
