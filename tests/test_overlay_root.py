"""ROADMAP #44 workaround: the overlay code root resolves a school's reviewed files to the worktree's branch copies and leaves main alone."""
import subprocess

import pytest

import overlay_root as O


def tree(tmp_path):
    main, wt = tmp_path / 'main', tmp_path / 'wt'
    for root in (main, wt):
        (root / 'tools').mkdir(parents=True)
        (root / 'tools' / 'x.py').write_text(root.name)
    (main / 'hierarchy' / 'newu' / 'reviewed').mkdir(parents=True)
    (main / 'hierarchy' / 'newu' / 'derived').mkdir()
    (main / 'hierarchy' / 'newu' / 'raw').mkdir()
    (main / 'hierarchy' / 'newu' / 'tmp').mkdir()
    (main / 'hierarchy' / 'mit').mkdir()
    (main / 'hierarchy' / 'newu' / 'reviewed' / 'a.json').write_text('main-a')
    (main / 'hierarchy' / 'newu' / 'reviewed' / 'b.json').write_text('main-b')
    (main / 'census').mkdir()
    subprocess.run(['git', 'init', '-q', str(wt)], check=True)
    (wt / 'hierarchy' / 'newu' / 'reviewed').mkdir(parents=True)
    (wt / 'hierarchy' / 'newu' / 'reviewed' / 'a.json').write_text('branch-a')
    subprocess.run(['git', '-C', str(wt), 'add', 'hierarchy/newu/reviewed/a.json'], check=True)
    return main, wt


def test_overlay_reads_branch_reviewed_files_and_main_for_the_rest(tmp_path):
    main, wt = tree(tmp_path)
    out, n = O.build('newu', main / 'hierarchy' / 'newu' / 'tmp' / 'ov', worktree=wt, main=main)
    assert n == 1
    rv = out / 'hierarchy' / 'newu' / 'reviewed'
    assert (rv / 'a.json').read_text() == 'branch-a' and (rv / 'b.json').read_text() == 'main-b'   # branch wins, main fills in
    assert (out / 'tools' / 'x.py').read_text() == 'wt'                                            # code is the worktree's
    assert (out / 'hierarchy' / 'newu' / 'derived').resolve() == (main / 'hierarchy' / 'newu' / 'derived').resolve()
    assert (out / 'hierarchy' / 'mit').resolve() == (main / 'hierarchy' / 'mit').resolve() and (out / 'census').is_symlink()


def test_a_write_through_the_overlay_lands_in_the_worktree_not_main(tmp_path):
    main, wt = tree(tmp_path)
    out, _ = O.build('newu', main / 'hierarchy' / 'newu' / 'tmp' / 'ov', worktree=wt, main=main)
    (out / 'hierarchy' / 'newu' / 'reviewed' / 'a.json').write_text('edited')
    assert (wt / 'hierarchy' / 'newu' / 'reviewed' / 'a.json').read_text() == 'edited'
    assert (main / 'hierarchy' / 'newu' / 'reviewed' / 'a.json').read_text() == 'main-a'


def test_refuses_an_output_inside_main_outside_the_school_tmp(tmp_path):
    main, wt = tree(tmp_path)
    with pytest.raises(SystemExit):
        O.build('newu', main / 'census' / 'ov', worktree=wt, main=main)
