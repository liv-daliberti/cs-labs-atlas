"""Document historical VT PIs whose current personal pages moved with them."""

import hashlib
import json
import zlib

import atlas_paths as P
import school_web as W
from bs4 import BeautifulSoup


SITES = (
    ('Lifu Huang', 'https://wilburone.github.io/index.html',
     'Prior to joining UC Davis, I was an Assistant Professor in the Computer Science Department at Virginia Tech',
     'UC Davis'),
    ('B. Aditya Prakash', 'https://faculty.cc.gatech.edu/~badityap/',
     'Professor and Associate Chair for Academic Affairs School of Computational Science and Engineering College of Computing Georgia Institute of Technology',
     'Georgia Tech'),
    ('Gang Wang', 'https://gangw.cs.illinois.edu/index.html',
     'Before joining UIUC, I worked as an Assistant Professor at Virginia Tech from 2016 to 2019.',
     'University of Illinois Urbana-Champaign'),
    ('Changhee Jung', 'https://www.cs.purdue.edu/homes/chjung/',
     'My lab, the CompArch (Compiler and Architecture) research group, was established in 2013 at Virginia Tech and is now based at Purdue.',
     'Purdue University'),
    ('Dongyoon Lee', 'https://www3.cs.stonybrook.edu/~dongyoon/',
     'Before joining Stony Brook University, I worked as an assistant professor at Virginia Tech (2014-2019)',
     'Stony Brook University'),
    ('Sharath Raghvendra', 'https://engr.ncsu.edu/people/skraghve/',
     'Sharath Raghvendra SR Assoc Professor', 'NC State'),
    ('Ali Vakilian', 'https://www.mit.edu/~vakilian/',
     'Previously: Assistant Professor, CS at Virginia Tech', 'Rutgers Business School'),
)


def main():
    path = P.data('lab-websites.json', 'vt')
    doc = json.loads(path.read_text())
    existing = {row['pi'] for row in doc['labs']}
    db = W.con('vt')
    added = []
    for name, url, quote, institution in SITES:
        if name in existing:
            continue
        row = db.execute('select status,sha256,raw_zlib,content_type,fetched_at from live where url=?',
                         (url,)).fetchone()
        assert row and row[0] == 200 and row[2], name
        raw = zlib.decompress(row[2])
        assert hashlib.sha256(raw).hexdigest() == row[1]
        text = W.flat(W.extract.blocks(raw, row[3], url))
        if not text:
            text = BeautifulSoup(raw, 'html.parser').get_text(' ', strip=True)
        assert name.split()[-1] in text and quote in text, name
        at = row[4][:10]
        doc['labs'].append(dict(
            pi=name, url=url, coverage='reason', kind='other_institution_site',
            reason_code='site_at_other_institution',
            reason=(f'Current university or personal page identifies {institution} as the current institution. '
                    'The VT period remains historical; no current VT lab site is established by this page.'),
            checked_at=at, audited_at=at,
            checks=[dict(source='candidate_site', url=url, result='ok', at=at,
                         sha256=row[1], quote=quote)],
        ))
        added.append(name)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'added': added}))


if __name__ == '__main__':
    main()
