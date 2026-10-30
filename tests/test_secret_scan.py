"""tools/secret_scan.py: token shapes, listed address hashes (as an address and written out), and the history mode."""
import hashlib
import subprocess

import secret_scan as S


def test_listed_hash_caught_as_address_and_written_out():
    addr = 'someone@example.net'
    h = hashlib.sha256(addr.encode()).hexdigest()
    assert [k for _, _, k in S.scan_bytes('a.txt', f'contact {addr}\n'.encode(), [], {h})] == ['listed email (by hash)']
    kinds = [k for _, _, k in S.scan_bytes('b.py', f"X = '{h.upper()}'\n".encode(), [], {h})]
    assert kinds == ['listed hash written out']
    assert not S.scan_bytes('c.py', b"X = 'other@example.net'\n", [], {h})


def test_token_shapes():
    assert S.scan_bytes('t', b'key = "hf_' + b'a' * 34 + b'"', [], set())
    assert not S.scan_bytes('t', b'nothing here', [], set())


def test_history_mode(tmp_path):
    def git(*a):
        subprocess.run(['git', '-C', str(tmp_path), *a], check=True, capture_output=True)
    git('init', '-q'); git('config', 'user.email', 'ci@example.org'); git('config', 'user.name', 'ci')
    (tmp_path / 'a.py').write_text('x = 1\n'); git('add', '.'); git('commit', '-qm', 'one')
    (tmp_path / 'a.py').write_text('x = "ghp_' + 'b' * 36 + '"\n'); git('commit', '-qam', 'two')
    (tmp_path / 'a.py').write_text('x = 2\n'); git('commit', '-qam', 'three')
    names = [n for n, _ in S.history(tmp_path)]
    assert len(names) == 3  # every distinct blob once, the removed secret included
    found = [f for n, b in S.history(tmp_path) for f in S.scan_bytes(n, b, [], set())]
    assert len(found) == 1 and ':a.py#' in found[0][0]


def test_allowlist_is_scoped_to_old_blobs(tmp_path):
    def git(*a):
        return subprocess.run(['git', '-C', str(tmp_path), *a], check=True, capture_output=True, text=True).stdout.strip()
    h = hashlib.sha256(b'someone@example.net').hexdigest()
    git('init', '-q'); git('config', 'user.email', 'ci@example.org'); git('config', 'user.name', 'ci')
    (tmp_path / 'e.py').write_text(f"H = '{h}'\n"); git('add', '.'); git('commit', '-qm', 'old')
    old_blob = git('rev-parse', 'HEAD:e.py')
    (tmp_path / 'e.py').write_text(f"H = '{h}'  # again\n"); git('commit', '-qam', 'new')
    found = [f for n, b in S.history(tmp_path) for f in S.scan_bytes(n, b, [], {h})]
    assert len(found) == 2
    left, acc = S.split_accepted(found, {(old_blob, 'listed hash written out')})
    assert len(acc) == 1 and acc[0][0].endswith('#' + old_blob)
    assert len(left) == 1 and not left[0][0].endswith('#' + old_blob)  # the new occurrence still fails
