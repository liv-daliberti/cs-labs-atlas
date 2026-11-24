import gzip
import json

import reader_links as R


def test_arxiv_queries_read_each_shard_once_and_keep_matching_fields(tmp_path, monkeypatch):
    for name, rows in [('a', [dict(id='1', title='First title', families=['One']),
                            dict(id='2', title='Older title', families=['Two'])]),
                       ('b', [dict(id='2', title='Updated title', families=['Two', 'Three'])])]:
        with gzip.open(tmp_path / f'{name}.jsonl.gz', 'wt') as f:
            for row in rows:
                f.write(json.dumps(row) + '\n')
    opened = []
    real_open = gzip.open

    def count_open(path, *args, **kwargs):
        opened.append(path)
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(R.gzip, 'open', count_open)
    index = R.ArxivIndex(tmp_path)
    assert index.lookup([]) == {} and not opened
    assert index.lookup(['1']) == {'1': ('First title', ['One'])}
    assert len(opened) == 2
    assert index.lookup(['2', 'missing']) == {'2': ('Updated title', ['Two', 'Three'])}
    assert index.lookup(['missing', 'another missing']) == {}
    assert len(opened) == 2


def test_missing_index_can_be_loaded_when_it_appears(tmp_path):
    directory = tmp_path / 'index'
    index = R.ArxivIndex(directory)
    assert index.lookup(['1']) == {}
    directory.mkdir()
    with gzip.open(directory / 'a.jsonl.gz', 'wt') as f:
        f.write(json.dumps(dict(id='1', title='Available now', families=[])) + '\n')
    assert index.lookup(['1']) == {'1': ('Available now', [])}
