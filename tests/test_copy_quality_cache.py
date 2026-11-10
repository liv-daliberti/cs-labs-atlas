"""copy_quality.file_quality: a persistent per-store cache so a loop restart does not re-parse every downloaded asset (2026-11-10)."""
import importlib

import copy_quality as CQ

XML = '<article><body>' + ''.join(f'<p>{"word " * 60}{i}</p>' for i in range(3)) + '</body></article>'


def fresh():
    importlib.reload(CQ)
    return CQ


def test_second_process_reads_the_cache_not_the_file(tmp_path, monkeypatch):
    monkeypatch.delenv('COPY_QUALITY_CACHE_DIR', raising=False)
    cq = fresh()
    a = tmp_path / 'a.xml'
    a.write_text(XML)
    q1 = cq.file_quality(a, 'xml', tmp_path)
    assert q1['ok'] and (tmp_path / cq.CACHE_NAME).exists()
    cq = fresh()   # a new process: empty in-memory cache
    monkeypatch.setattr(cq, 'xml_quality', lambda data: (_ for _ in ()).throw(AssertionError('re-parsed')))
    assert cq.file_quality(a, 'xml', tmp_path) == q1


def test_changed_file_is_checked_again(tmp_path, monkeypatch):
    monkeypatch.delenv('COPY_QUALITY_CACHE_DIR', raising=False)
    cq = fresh()
    a = tmp_path / 'a.xml'
    a.write_text(XML)
    assert cq.file_quality(a, 'xml', tmp_path)['ok']
    a.write_text('<article><body><p>short</p></body></article>')
    cq = fresh()
    q = cq.file_quality(a, 'xml', tmp_path)
    assert not q['ok'] and q['reason'] == 'xml_no_substantive_body'


def test_torn_and_foreign_lines_are_ignored(tmp_path, monkeypatch):
    monkeypatch.delenv('COPY_QUALITY_CACHE_DIR', raising=False)
    (tmp_path / CQ.CACHE_NAME).write_text('{"k": "x"\nnot json\n{"k": "y", "v": 3}\n')
    cq = fresh()
    a = tmp_path / 'a.xml'
    a.write_text(XML)
    assert cq.file_quality(a, 'xml', tmp_path)['ok']


def test_transient_results_are_not_persisted_and_dir_is_redirectable(tmp_path, monkeypatch):
    cache = tmp_path / 'cache'
    cache.mkdir()
    monkeypatch.setenv('COPY_QUALITY_CACHE_DIR', str(cache))
    cq = fresh()
    cq._persist_put(tmp_path, 'k1', dict(ok=False, reason='pdf_parse_unconfirmed'))
    cq._persist_put(tmp_path, 'k2', dict(ok=True))
    lines = (cache / cq.CACHE_NAME).read_text().splitlines()
    assert len(lines) == 1 and 'k2' in lines[0] and not (tmp_path / cq.CACHE_NAME).exists()


def test_no_store_no_cache_file(tmp_path, monkeypatch):
    monkeypatch.delenv('COPY_QUALITY_CACHE_DIR', raising=False)
    cq = fresh()
    a = tmp_path / 'a.xml'
    a.write_text(XML)
    assert cq.file_quality(a, 'xml')['ok'] and not (tmp_path / cq.CACHE_NAME).exists()


def test_a_corrupted_cached_result_is_ignored(tmp_path, monkeypatch):
    monkeypatch.delenv('COPY_QUALITY_CACHE_DIR', raising=False)
    cq = fresh()
    a = tmp_path / 'a.xml'
    a.write_text(XML)
    cq.file_quality(a, 'xml', tmp_path)
    cache = tmp_path / cq.CACHE_NAME
    cache.write_text(cache.read_text().replace('actual_sha256', 'actuaal_sha256'))
    cq = fresh()
    q = cq.file_quality(a, 'xml', tmp_path)
    assert q['ok'] and len(q['actual_sha256']) == 64
