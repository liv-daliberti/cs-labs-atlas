"""A department profile is retained when its row has no personal homepage."""
import gzip
import json

import census_build as C


def test_profile_only_directory_survives_census_and_collection(tmp_path, monkeypatch):
    def path(name, school=None):
        return tmp_path / (school or 'shared') / name

    def writable(name, school=None):
        p = path(name, school)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    monkeypatch.setattr(C.P, 'data', path)
    monkeypatch.setattr(C.P, 'data_w', writable)
    cfg = dict(name='Example University', window=[2016, 2026],
               departments=[dict(code='CS', coverage='full')])
    monkeypatch.setattr(C.S, 'get', lambda key: cfg)
    base = dict(observed='20261107000000', year=2026, half='H2', dept='CS', rank='ladder',
                titles=['Professor'], dept_title=['Professor'], kind='main',
                slot='regular', capture_url='https://example.edu/faculty/',
                sha256='a' * 64, quote='Alex Example Professor')
    profile = 'https://example.edu/faculty/alex'
    home = 'https://example.edu/~robin/'
    rows = [dict(base, name='Alex Example', homepage=None, profile=profile),
            dict(base, name='Robin Other', homepage=home, profile='https://example.edu/faculty/robin')]
    writable('rows.json', 'test').write_text(json.dumps(rows))
    C.main('test')
    faculty = json.loads(path('census-faculty.json', 'test').read_text())['faculty']
    assert {r['name']: r['profile_url'] for r in faculty} == {
        'Alex Example': profile, 'Robin Other': home}
    with gzip.open(path('collection.json.gz', 'test'), 'rt') as f:
        people = json.load(f)['people']
    assert {r['name']: r['profileUrl'] for r in people} == {
        'Alex Example': profile, 'Robin Other': home}
