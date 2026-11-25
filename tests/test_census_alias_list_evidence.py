"""census_build.reviewed_name_aliases re-verifies list-form alias evidence (hash + quote) and fails closed; the pair itself is applied by the builder."""
import hashlib

import pytest

import atlas_paths as P
import census_build as C


def doc(tmp_path, quote, sha=None):
    html = b'<html><body><p>JIA Jiaya\xc2\xa0Leo Professor</p><p>Jiaya Jia</p></body></html>'
    (tmp_path / 'a.html').write_bytes(html)
    ev = [dict(url='u%d' % i, sha256=sha or hashlib.sha256(html).hexdigest(), artifact='a.html', quote=quote) for i in range(2)]
    return dict(school='t', rows=[dict(name_a='JIA Jiaya Leo', name_b='Jiaya Jia', evidence=ev)])


def run(monkeypatch, tmp_path, d):
    monkeypatch.setattr(C, 'read', lambda p, default=None: d)
    monkeypatch.setattr(P, 'CODE', tmp_path)
    return C.reviewed_name_aliases('t')


def test_list_evidence_verified_and_not_applied_by_census(monkeypatch, tmp_path):
    assert run(monkeypatch, tmp_path, doc(tmp_path, 'JIA Jiaya Leo Professor')) == []


def test_bad_quote_or_hash_fails_closed(monkeypatch, tmp_path):
    with pytest.raises(AssertionError):
        run(monkeypatch, tmp_path, doc(tmp_path, 'Somebody Else'))
    with pytest.raises(AssertionError):
        run(monkeypatch, tmp_path, doc(tmp_path, 'Jiaya Jia', sha='0' * 64))
