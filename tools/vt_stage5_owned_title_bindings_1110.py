"""Bind exact DBLP people through a publication title on their own captured site."""

import json
import re
import zlib
from datetime import date
from pathlib import Path

import atlas_paths as P
import school_web as W


SITES = {
    'Anuj Karpatne': 'https://anujkarpatne.github.io/',
    'Bert Huang': 'https://berthuang.com/',
    'Changhee Jung': 'https://www.cs.purdue.edu/homes/chjung/',
    'Francisco Servant': 'https://fservant.github.io/',
    'Huaicheng Li': 'https://huaicheng.github.io/',
    'Ismini Lourentzou': 'https://isminoula.github.io/',
    'Pinar Yanardag': 'https://gemlab-vt.github.io/',
    'Tanushree Mitra': 'https://faculty.washington.edu/tmitra/',
}
NAME_FORMS = {'Tanushree Mitra': ('Tanu Mitra', 'Tanushree Mitra')}


def normalized(value):
    return ' '.join(re.findall(r'[a-z0-9]+', value.lower()))


def main():
    root = Path(P.CODE) / 'hierarchy/vt/reviewed'
    audit = json.loads((root / 'stage5-exact-dblp-audit.json').read_text())['people']
    pubs = json.loads((root / 'stage5-exact-dblp-pubs.json').read_text())['people']
    census = {x['name'] for x in json.loads(P.data('census-faculty.json', 'vt').read_text())['faculty']}
    path = P.data('census-overrides-school.json', 'vt')
    overrides = json.loads(path.read_text())
    db = W.con('vt')
    bound = []
    for name, url in SITES.items():
        assert name in census
        assert len(audit[name]) == 1 and not audit[name][0]['disambiguation']
        person = audit[name][0]
        assert pubs[name]['pid'] == person['pid'] and pubs[name]['count'] > 0
        row = db.execute('select status,sha256,fetched_at,raw_zlib,content_type from live where url=?',
                         (url,)).fetchone()
        assert row and row[0] == 200 and row[1]
        body = W.flat(W.extract.blocks(zlib.decompress(row[3]), row[4], url))
        normalized_body = normalized(body)
        assert any(normalized(form) in normalized_body for form in NAME_FORMS.get(name, (name,))), name
        matched = next((work for work in pubs[name]['titles']
                        if len(normalized(work['title'])) >= 40 and normalized(work['title']) in normalized_body), None)
        assert matched, name
        item = overrides.setdefault(name, {})
        assert not item.get('dblp') or item['dblp'] == [person['pid']]
        item['dblp'] = [person['pid']]
        item['why_dblp'] = ('The unique exact-name DBLP person record from the local September 2026 dump shares an exact publication title with this captured first-party PI site. The site names the PI. This binds a person, not all papers or a VT affiliation period.')
        item['dblp_evidence'] = [dict(
            source='dblp-2026-09-01.xml.gz', person_record_sha256=person['person_record_sha256'],
            pid=person['pid'], names=person['names'],
            site=url, site_sha256=row[1], site_fetched_at=row[2],
            matching_title=matched['title'], matching_dblp_key=matched['key'],
            observed=str(date.today()),
        )]
        bound.append(dict(name=name, pid=person['pid'], title=matched['title']))
    path.write_text(json.dumps(overrides, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({'bound': bound}, ensure_ascii=False))


if __name__ == '__main__':
    main()
