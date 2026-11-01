"""Routing through atlas_paths.data (ROADMAP item 10): flat_of undoes the split layout, so releases keep the flat names."""
import atlas_paths as P


def test_flat_of_maps_every_split_path_back_to_its_flat_path():
    for name, kind, flat, split in P.DATA_FILES:
        s = 'mit' if '{school}' in flat else None
        got = P.flat_of(P.data(name, s, root='/r', layout='split').relative_to('/r').as_posix())
        assert got == flat.format(school=s), (name, got)


def test_data_w_creates_the_directory(tmp_path):
    p = P.data_w('pis.json', 'mit', root=tmp_path, layout='split')
    assert p == tmp_path / 'hierarchy/mit/derived/pis.json' and p.parent.is_dir()
    assert P.flat_of('docs/RULES.md') == 'docs/RULES.md'
