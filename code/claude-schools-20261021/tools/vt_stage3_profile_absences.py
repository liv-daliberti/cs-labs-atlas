"""Document scoped no-site outcomes for three VT CS profiles already hand reviewed."""

import hashlib
import json
import zlib

import atlas_paths as P
import school_web as W


NAMES = ('Kirk Cameron', 'Atul Mantri', 'Kirshanthan Sundararajah')


def main():
    path = P.data('lab-websites.json', 'vt')
    doc = json.loads(path.read_text())
    rows = {r['pi']: r for r in doc['labs']}
    census = {p['name']: p for p in json.loads(P.data('census-faculty.json', 'vt').read_text())['faculty']}
    db = W.con('vt')
    for name in NAMES:
        site = rows[name]
        assert site['coverage'] == 'reason' and not site.get('url'), name
        if site.get('checks'):
            continue
        url = census[name]['profile_url']
        row = db.execute('select status,sha256,raw_zlib,content_type,fetched_at from live where url=?', (url,)).fetchone()
        assert row and row[0] == 200 and row[2], name
        raw = zlib.decompress(row[2])
        assert hashlib.sha256(raw).hexdigest() == row[1]
        text = W.flat(W.extract.blocks(raw, row[3], url))
        assert name in text, name
        at = row[4][:10]
        site.update(
            reason_code='profile_only_no_homepage', audited_at=at, checked_at=at,
            reason=(site['reason'] + '; dated official profile checked ' + at +
                    '. This is the outcome of the recorded search, not proof that no site exists.'),
            checks=[dict(source='school_profile', url=url, result='no_eligible_lab_link_recorded',
                         at=at, sha256=row[1], quote=name)],
        )
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'documented_profile_only': list(NAMES)}))


if __name__ == '__main__':
    main()
