"""Prepare current CS PI home evidence without writing the shared Stage 3 home ledger."""
import hashlib
import json
import sqlite3
import zlib

import atlas_paths as P
import school_web as W

VT_REVIEWED = P.reviewed_path('', 'vt')
URL = 'https://cs.vt.edu/people/faculty.html'


def main():
    con = sqlite3.connect(f'file:{P.data("school-captures.sqlite", "vt")}?mode=ro', uri=True)
    source = con.execute('select status,sha256,raw_zlib from live where url=?', (URL,)).fetchone()
    assert source and source[0] == 200
    sha, raw = source[1], zlib.decompress(source[2])
    assert hashlib.sha256(raw).hexdigest() == sha
    flat = W.flat(W.extract.blocks(raw, 'text/html', URL))
    labs = json.loads((VT_REVIEWED / 'lab-websites.json').read_text())['labs']
    census = json.loads((P.data('census-faculty.json', 'vt')).read_text())['faculty']
    people = {x['name'].rstrip('.'): x for x in census}
    rows = []
    for lab in labs:
        person = people[lab['pi'].rstrip('.')]
        sources = [s for s in person['sources']
                   if s['kind'] == 'dept_listing:CS' and s['rank'] == 'ladder'
                   and str(s['observed']).startswith('2026')]
        assert len(sources) == 1, lab['pi']
        evidence = sources[0]
        assert evidence['url'] == URL and evidence['sha256'] == sha
        assert ' '.join(evidence['quote'].split()) in flat
        rows.append(dict(pi=lab['pi'], census_name=person['name'],
                         home_department='Computer Science',
                         status='source_backed_precheck',
                         pi_basis='2026 official CS professor-rank listing',
                         evidence=dict(url=URL, sha256=sha, quote=evidence['quote'],
                                       observed=evidence['observed'], rank=evidence['rank_as_listed'])))
    assert len(rows) == 64 and len({r['pi'] for r in rows}) == 64
    out = VT_REVIEWED / 'current-cs-home-precheck.json'
    out.write_text(json.dumps(dict(school='vt', scope='64 provisional current 2026 CS PIs',
                                   provisional=True,
                                   shared_home_ledger_written=False,
                                   source_sha256=sha, count=len(rows), rows=rows),
                              ensure_ascii=False, indent=2) + '\n')
    print(f'{len(rows)} current CS PI home quotes verified')


if __name__ == '__main__':
    main()
