from pathlib import Path
"""2026-11-10 HKUST incident: a tool run in a --private overlay wrote main's raw .json.gz through a symlink. Private overlays now copy small raw files,
and atlas_paths.data_w refuses to write a file that is itself a symlink leading out of an overlay root."""
import json

import pytest

import atlas_paths as P
import overlay_root as O
from test_overlay_root import tree


def test_private_overlay_copies_small_raw_files(tmp_path):
    main, wt = tree(tmp_path)
    (main / 'hierarchy' / 'newu' / 'raw' / 'dblp-dump-persons-school.json.gz').write_bytes(b'orig')
    out, _ = O.build('newu', main / 'hierarchy' / 'newu' / 'tmp' / 'ov', worktree=wt, main=main, private=True)
    f = out / 'hierarchy' / 'newu' / 'raw' / 'dblp-dump-persons-school.json.gz'
    assert f.is_file() and not f.is_symlink()
    f.write_bytes(b'changed')
    assert (main / 'hierarchy' / 'newu' / 'raw' / 'dblp-dump-persons-school.json.gz').read_bytes() == b'orig'


def test_data_w_refuses_a_symlink_out_of_the_overlay(tmp_path, monkeypatch):
    main, wt = tree(tmp_path)
    (main / 'hierarchy' / 'newu' / 'raw' / 'big.bin').write_bytes(b'main')
    out, _ = O.build('newu', main / 'hierarchy' / 'newu' / 'tmp' / 'ov', worktree=wt, main=main, private=True)
    link = out / 'hierarchy' / 'newu' / 'raw' / 'linked.json'
    link.symlink_to(main / 'hierarchy' / 'newu' / 'raw' / 'big.bin')
    monkeypatch.setattr(P, 'CODE', out)
    monkeypatch.setattr(P, 'data', lambda *a, **k: link)
    with pytest.raises(PermissionError, match='outside the overlay root'):
        P.data_w('hosts.json', 'newu')
    assert (main / 'hierarchy' / 'newu' / 'raw' / 'big.bin').read_bytes() == b'main'


def test_data_w_allows_a_plain_file_in_an_overlay(tmp_path, monkeypatch):
    main, wt = tree(tmp_path)
    out, _ = O.build('newu', main / 'hierarchy' / 'newu' / 'tmp' / 'ov', worktree=wt, main=main, private=True)
    target = out / 'hierarchy' / 'newu' / 'raw' / 'plain.json'
    (out / '.overlay.json').write_text(json.dumps(dict(main=str(main), school='newu', worktree=str(wt))))
    monkeypatch.setattr(P, 'CODE', out)
    monkeypatch.setattr(P, 'data', lambda *a, **k: target)
    assert P.data_w('hosts.json', 'newu') == target


def test_rebuilding_a_non_private_overlay_never_moves_mains_listings(tmp_path):
    """2026-11-25 ZJU incident: rebuilding a NON-private overlay moved main's listings/<school> into the overlay (is_private followed the
    whole-dir listings symlink)."""
    from test_overlay_root import tree
    main, wt = tree(tmp_path)
    (main / 'listings' / 'newu' / 'derived').mkdir(parents=True)
    (main / 'listings' / 'newu' / 'derived' / 'listings.json').write_text('main-listings')
    (main / 'listings' / 'other').mkdir()
    out_dir = main / 'hierarchy' / 'newu' / 'tmp' / 'ov'
    out, _ = O.build('newu', out_dir, worktree=wt, main=main)
    assert (out / 'listings').is_symlink()
    assert not O.is_private(out, Path('listings') / 'newu')
    O.build('newu', out_dir, worktree=wt, main=main)          # the rebuild that used to park (move) main's directory
    assert (main / 'listings' / 'newu' / 'derived' / 'listings.json').read_text() == 'main-listings'
    assert (out_dir / 'listings').is_symlink()
