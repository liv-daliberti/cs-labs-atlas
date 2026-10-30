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
    assert len(found) == 1 and found[0][0].endswith(':a.py')
