"""The overlay code root in the school placement (2026-11-26): <out>/school-data/<school>/ stands in for <schools tree>/<school>/, its reviewed
entry is the overlaid decision files, work/ is the overlay's own, every other part is main's."""
import subprocess

import pytest

import atlas_paths as P
import overlay_root as O


def school_tree(tmp_path):
    main, wt, tree = tmp_path / 'main', tmp_path / 'wt', tmp_path / 'schools'
    for root in (main, wt):
        (root / 'tools').mkdir(parents=True)
        (root / 'tools' / 'x.py').write_text(root.name)
    for d in ('hierarchy/newu/reviewed', 'hierarchy/reviewed', 'census', 'listings'):
        (main / d).mkdir(parents=True)
    (main / 'hierarchy/newu/reviewed/a.json').write_text('main-a')
    (main / 'hierarchy/reviewed/census-overrides.json').write_text('main-co')
    for d in ('derived', 'raw', 'work', 'reports', 'tmp'):
        (tree / 'newu' / d).mkdir(parents=True)
    (tree / 'mit' / 'derived').mkdir(parents=True)
    (tree / 'newu/derived/pis.json').write_text('main-pis')
    (tree / 'newu/raw/school-captures.sqlite').write_text('main-cap')
    (tree / 'newu/work/dblp-recover.sqlite').write_text('main-work')
    subprocess.run(['git', 'init', '-q', str(wt)], check=True)
    (wt / 'hierarchy/newu/reviewed').mkdir(parents=True)
    (wt / 'hierarchy/newu/reviewed/a.json').write_text('branch-a')
    subprocess.run(['git', '-C', str(wt), 'add', 'hierarchy/newu/reviewed/a.json'], check=True)
    return main, wt, tree


def test_school_overlay_reads_branch_reviewed_and_mains_data(tmp_path, monkeypatch):
    main, wt, tree = school_tree(tmp_path)
    out_dir = tree / 'newu' / 'tmp' / 'ov'
    out, n = O.build('newu', out_dir, worktree=wt, main=main, layout='school', tree=tree)
    sd = out / 'school-data'
    assert (sd / 'newu' / 'reviewed' / 'a.json').read_text() == 'branch-a'            # the branch's decision file wins
    assert (sd / 'newu' / 'derived').resolve() == (tree / 'newu' / 'derived').resolve()  # main's data
    assert (sd / 'mit').resolve() == (tree / 'mit').resolve()
    work = sd / 'newu' / 'work'
    assert work.is_dir() and not work.is_symlink() and list(work.iterdir()) == []         # the overlay's own
    monkeypatch.setenv('CS_ATLAS_DATA_LAYOUT', 'school')
    monkeypatch.delenv('CS_ATLAS_SCHOOLS_TREE', raising=False)
    monkeypatch.setattr(P, 'CODE', out); monkeypatch.setattr(P, 'HIERARCHY', out / 'hierarchy')
    assert P.data('pis.json', 'newu') == out / 'school-data' / 'newu' / 'derived' / 'pis.json'
    assert P.data('pis.json', 'newu').read_text() == 'main-pis'
    assert P.data('gap-evidence.json', 'newu').parent.resolve() == (out / 'hierarchy' / 'newu' / 'reviewed').resolve()
    assert (main / 'hierarchy/newu/reviewed/a.json').read_text() == 'main-a'


def test_school_overlay_private_copies_and_receipt(tmp_path):
    main, wt, tree = school_tree(tmp_path)
    out, _ = O.build('newu', tree / 'newu' / 'tmp' / 'ov', worktree=wt, main=main, private=True, layout='school', tree=tree)
    raw = out / 'school-data' / 'newu' / 'raw' / 'school-captures.sqlite'
    assert raw.read_text() == 'main-cap' and not raw.is_symlink()
    raw.write_text('grown')
    assert (tree / 'newu/raw/school-captures.sqlite').read_text() == 'main-cap'
    assert O.verify(out) == []
    (tree / 'newu/derived/pis.json').write_text('changed')
    assert O.verify(out) != []


def test_school_overlay_refuses_an_output_inside_main(tmp_path):
    main, wt, tree = school_tree(tmp_path)
    with pytest.raises(SystemExit):
        O.build('newu', main / 'census' / 'ov', worktree=wt, main=main, layout='school', tree=tree)
