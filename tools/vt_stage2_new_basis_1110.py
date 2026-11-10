"""Retain candidate DBLP identity fields on newly sourced VT role decisions."""

import json

import atlas_paths as P


NAMES = {'Anders Eklund', 'Robert G. Capra', 'Salman Ahmed', 'Mohamed W. Hassan'}


def main():
    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    cand = {x['name']: x for x in json.loads(P.data('cs-related-candidates.json', 'vt').read_text())}
    count = 0
    for row in doc['decisions']:
        if row['name'] not in NAMES:
            continue
        c = cand[row['name']]
        assert row['decision'] == 'not_faculty_listed'
        row['cs_basis'] = dict(dblp=[c['dblp']] if c.get('dblp') else [],
                               dblp_window=c.get('dblp_window', 0),
                               affiliation_notes=c.get('affiliations') or [])
        count += 1
    assert count == len(NAMES)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'reconciled': count}))


if __name__ == '__main__':
    main()
