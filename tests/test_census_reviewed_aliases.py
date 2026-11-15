import hashlib
import json

import pytest

import census_build as C


def test_explicit_source_backed_alias_merges_only_named_groups(tmp_path, monkeypatch):
    raw = b'<p>Danfeng (Daphne) Yao is a professor.</p>'
    (tmp_path / 'alias.html').write_bytes(raw)
    doc = {'school': 'vt', 'rows': [{'name_a': 'Danfeng Yao', 'name_b': 'Daphne Yao',
           'evidence': {'raw_path': 'alias.html', 'sha256': hashlib.sha256(raw).hexdigest(),
                        'quote': 'Danfeng (Daphne) Yao', 'additional_quote': 'is a professor'}}]}
    p = tmp_path / 'aliases.json'
    p.write_text(json.dumps(doc))
    monkeypatch.setattr(C.P, 'ROOT', tmp_path)
    monkeypatch.setattr(C.P, 'data', lambda name, key=None, *a, **k: p)
    pairs = C.reviewed_name_aliases('vt')
    rows = [{'name': 'Danfeng Yao', 'observed': '2022'},
            {'name': 'Daphne Yao', 'observed': '2025'},
            {'name': 'Danfeng Li', 'observed': '2025'}]
    groups = C.merge_people(rows, pairs)
    assert len(groups) == 2
    assert {'Danfeng Yao', 'Daphne Yao'} in [set(g['names']) for g in groups]
    doc['rows'][0]['evidence']['quote'] = 'another person'
    p.write_text(json.dumps(doc))
    with pytest.raises(AssertionError):
        C.reviewed_name_aliases('vt')
    doc['rows'][0]['evidence']['quote'] = 'Danfeng (Daphne) Yao'
    doc['rows'][0]['evidence']['additional_quote'] = 'another person'
    p.write_text(json.dumps(doc))
    with pytest.raises(AssertionError):
        C.reviewed_name_aliases('vt')


def test_shared_dblp_pid_alias_checks_the_pinned_dump_record(tmp_path, monkeypatch):
    import gzip
    rec = dict(names=['Nick Sahinidis'], orcid=['0000-0003-2087-9131'], affiliations=['Georgia Institute of Technology, Atlanta, GA, USA'])
    (tmp_path / 'dump.json.gz').write_bytes(gzip.compress(json.dumps({'persons': {'https://dblp.org/pid/1/2': dict(rec, pubs=[])}}).encode()))
    ev = dict(kind='shared_dblp_pid', pid_url='https://dblp.org/pid/1/2', orcid='0000-0003-2087-9131', raw_path='dump.json.gz',
              sha256=hashlib.sha256(json.dumps(rec, sort_keys=True).encode()).hexdigest(), quote='Georgia Institute of Technology')
    doc = {'school': 'gt', 'rows': [{'name_a': 'Nick Sahinidis', 'name_b': 'Nikolaos Sahinidis', 'evidence': ev}]}
    p = tmp_path / 'aliases.json'
    p.write_text(json.dumps(doc))
    monkeypatch.setattr(C.P, 'ROOT', tmp_path)
    monkeypatch.setattr(C.P, 'data', lambda name, key=None, *a, **k: p)
    assert C.reviewed_name_aliases('gt') == [('Nick Sahinidis', 'Nikolaos Sahinidis')]
    doc['rows'][0]['evidence']['orcid'] = '0000-0000-0000-0000'
    p.write_text(json.dumps(doc))
    with pytest.raises(AssertionError):
        C.reviewed_name_aliases('gt')


def test_family_names_differing_by_a_space_are_one_family():
    assert ''.join(C.toks('Munmun De Choudhury')[1:]) == ''.join(C.toks('Munmun DeChoudhury')[1:])
