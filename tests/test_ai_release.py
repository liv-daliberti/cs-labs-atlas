"""The AI-writing pages' data in a release (tools/ai_release.py; owner 2026-11-04): complete folder or refusal, no 2026,
hashes in ai/manifest.json, and the files no longer travel twice as 'reviewed inputs'."""
import gzip
import json

import pytest

import ai_release
import make_release
import provenance


def folder(tmp_path, year_extra=None, skip=None):
    root = tmp_path / 'site-data'
    (root / 'all-ai').mkdir(parents=True)
    hist = {'meta': {'last_year': 2025}, 'series': {'all': {str(y): {'hist': [0] * 101} for y in range(2016, 2026)}}}
    if year_extra:
        hist['series']['all'][year_extra] = {'hist': [0] * 101}
    files = {'ai_hist.json': hist, 'ai_position.json': {'meta': {'last_year': 2025}, 'series': {}},
             'labs_ai_hist_mit.json': {'meta': {}, 'labs': [{'lab_id': 'x', 'year': 2024}]}}
    for n in ai_release.ALL_AI_FILES:
        files['all-ai/' + n] = {'rows': [{'year': 2025}]}
    for n, v in files.items():
        if n != skip:
            (root / n).write_text(json.dumps(v))
    return root


def test_collect_names_exactly_the_page_files(tmp_path):
    src = ai_release.collect(folder(tmp_path))
    assert sorted(src) == sorted(['ai/ai_hist.json', 'ai/ai_position.json', 'ai/labs_ai_hist_mit.json'] +
                                 ['ai/all-ai/' + n for n in ai_release.ALL_AI_FILES])
    ai_release.check_years(src)


def test_gzipped_lab_file_is_collected(tmp_path):
    root = folder(tmp_path)
    (root / 'labs_ai_hist_mit.json').rename(root / 'labs_ai_hist_mit.json.gz')
    (root / 'labs_ai_hist_mit.json.gz').write_bytes(gzip.compress(b'{"labs":[{"year":2026}]}'))
    src = ai_release.collect(root)
    assert 'ai/labs_ai_hist_mit.json.gz' in src
    with pytest.raises(SystemExit, match='2026'):
        ai_release.check_years(src)


@pytest.mark.parametrize('skip', ['ai_hist.json', 'ai_position.json', 'labs_ai_hist_mit.json', 'all-ai/methods.json'])
def test_incomplete_folder_refuses(tmp_path, skip):
    with pytest.raises(SystemExit, match='incomplete'):
        ai_release.collect(folder(tmp_path, skip=skip))


def test_a_2026_series_refuses_the_release(tmp_path):
    src = ai_release.collect(folder(tmp_path, year_extra='2026'))
    with pytest.raises(SystemExit, match='no 2026'):
        ai_release.check_years(src)
    root = folder(tmp_path / 'b')
    p = root / 'all-ai/trend.json'
    p.write_text(json.dumps({'rows': [{'year': 2026}]}))
    with pytest.raises(SystemExit, match='no 2026'):
        ai_release.check_years(ai_release.collect(root))


def test_manifest_lists_hashes_without_itself(tmp_path):
    entries = {'ai/a.json': {'bytes': 3, 'sha256': 'a' * 64, 'content_sha256': 'x'}, 'ai/manifest.json': {'bytes': 1, 'sha256': 'b' * 64},
               'hierarchy/x.json': {'bytes': 1, 'sha256': 'c' * 64}}
    m = ai_release.manifest('2026-11-05', 'abc', entries)
    assert m['files'] == {'ai/a.json': {'bytes': 3, 'sha256': 'a' * 64}} and m['last_year'] == 2025 and m['release'] == '2026-11-05'


def test_release_sources_carries_ai_only_when_named(tmp_path):
    assert not any(k.startswith('ai/') for k in make_release.release_sources())
    assert 'ai/ai_hist.json' in make_release.release_sources(folder(tmp_path))


def test_study_files_are_not_reviewed_inputs(monkeypatch):
    monkeypatch.setattr(provenance, '_git', lambda *a: 'ai-writing/diversity/site-data/all-ai/labs.json\nhierarchy/x.json\n')
    monkeypatch.setattr(provenance, 'onboarding_schools', lambda: [])
    assert provenance.tracked_inputs() == ['hierarchy/x.json']


def test_optional_words_and_lab_scores_are_carried(tmp_path):
    """2026-11-06: the AI words page data (words/) and the per-lab 2025 AI-use scores travel in the release when present."""
    root = folder(tmp_path)
    (root / 'words').mkdir()
    for n in ai_release.WORDS_FILES:
        (root / 'words' / n).write_text(json.dumps({'trend': {'2025': 1.0}}))
    (root / ai_release.LAB_SCORE_FILE).write_text(json.dumps({'labs': [{'lab': 'x', 'score': 3.4}]}))
    src = ai_release.collect(root)
    assert {'ai/words/words.json', 'ai/words/word_curves.json', 'ai/lab_ai_scores_2025.json'} <= set(src)
    ai_release.check_years(src)


def test_a_words_folder_needs_both_files(tmp_path):
    root = folder(tmp_path)
    (root / 'words').mkdir()
    (root / 'words' / 'words.json').write_text('{}')
    with pytest.raises(SystemExit, match='word_curves'):
        ai_release.collect(root)
