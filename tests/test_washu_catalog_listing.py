import hashlib
import json
import sqlite3
import zlib
from types import SimpleNamespace

import pytest

import listing_rows as R


def test_washu_catalog_coverage_requires_all_original_faculty_sections(tmp_path, monkeypatch):
    monkeypatch.setattr(R.P, 'HIERARCHY', tmp_path / 'hierarchy')
    monkeypatch.setattr(R.P, 'LISTINGS', tmp_path / 'listings')
    reviewed = tmp_path / 'hierarchy' / 'washu' / 'reviewed'
    raw_dir = tmp_path / 'listings' / 'washu' / 'raw'
    reviewed.mkdir(parents=True)
    raw_dir.mkdir(parents=True)
    records = []
    with sqlite3.connect(raw_dir / 'catalog-captures.sqlite') as c:
        c.execute('create table captures(url text,year integer,status integer,sha256 text,raw_zlib blob,content_type text)')
        for year in range(2016, 2020):
            raw = f'%PDF-1.4\n{year}'.encode()
            sha = hashlib.sha256(raw).hexdigest()
            url = f'https://bulletin.wustl.edu/{year}.pdf'
            c.execute('insert into captures values(?,?,?,?,?,?)',
                      (url, year, 200, sha, zlib.compress(raw), 'application/pdf'))
            for dept in ('BME', 'CSE', 'ESE'):
                records.append(dict(academic_edition=f'{year}-{str(year + 1)[-2:]}',
                                    dept=dept, source_url=url, sha256=sha,
                                    quote='Faculty Chair ' + dept + ' ' + 'Professor Name ' * 90))
    manifest = reviewed / 'historical-source-review.json'
    manifest.write_text(json.dumps(dict(school='washu', records=records)))
    monkeypatch.setattr(R.subprocess, 'run', lambda *a, **kw: SimpleNamespace(
        stdout=' '.join(r['quote'] for r in records)))
    assert len(R.washu_catalog_listing_coverage('washu')) == 12

    records.pop()
    manifest.write_text(json.dumps(dict(school='washu', records=records)))
    with pytest.raises(ValueError, match='sections missing'):
        R.washu_catalog_listing_coverage('washu')

    records[-1]['sha256'] = '0' * 64
    manifest.write_text(json.dumps(dict(school='washu', records=records)))
    with pytest.raises(ValueError, match='source mismatch'):
        R.washu_catalog_listing_coverage('washu')
