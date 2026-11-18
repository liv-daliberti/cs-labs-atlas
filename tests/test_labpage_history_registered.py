"""V4a (540b0f98) read labpage-audit-history.jsonl through atlas_paths.data() without registering it, so `labpage_audit.py audit <school>` died with
KeyError on every school (Georgia Tech promotion, 2026-11-18). The file stays optional: no file means no history."""
import atlas_paths as P
import discovery_marker as D


def test_history_file_is_registered_and_optional(tmp_path, monkeypatch):
    names = [n for n, *_ in P.DATA_FILES]
    assert 'labpage-audit-history.jsonl' in names
    assert 'labpage-audit-errors.json' in names   # cmd_audit writes/unlinks it after every audit (same V4a commit)
    assert isinstance(D.record_files('gatech', 'labpage-audit-history.jsonl'), list)
