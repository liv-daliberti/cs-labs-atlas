"""Canonical JSON remains readable if serialization or publication fails."""
import json

import pytest
from pihier import build


def test_shorter_rebuild_replaces_old_document_without_trailing_bytes(tmp_path):
    path = tmp_path / 'pis.json'
    path.write_text(json.dumps([{'pi': 'old', 'extra': 'x' * 5000}]))
    build.atomic_json(path, [{'pi': 'Zoë'}])
    assert json.loads(path.read_text()) == [{'pi': 'Zoë'}]
    assert list(tmp_path.iterdir()) == [path]


def test_failed_serialization_preserves_last_valid_document(tmp_path):
    path = tmp_path / 'pis.json'
    original = b'[{"pi": "verified prior build"}]'
    path.write_bytes(original)
    with pytest.raises(TypeError):
        build.atomic_json(path, [{'pi': 'new'}, {'unsupported': object()}])
    assert path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [path]


def test_failed_publication_preserves_old_document_and_cleans_temporary(tmp_path, monkeypatch):
    path = tmp_path / 'pis.json'
    original = b'[{"pi": "verified prior build"}]'
    path.write_bytes(original)
    def failed_replace(source, destination):
        assert json.loads(source.read_text()) == [{'pi': 'new'}]
        assert destination.read_bytes() == original
        raise OSError('simulated publish failure')
    monkeypatch.setattr(build.os, 'replace', failed_replace)
    with pytest.raises(OSError, match='simulated publish failure'):
        build.atomic_json(path, [{'pi': 'new'}])
    assert path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [path]
