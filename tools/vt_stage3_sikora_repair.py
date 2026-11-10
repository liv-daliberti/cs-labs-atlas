"""Attach dated checks to the reviewed Jamie Sikora duplicate href repair."""

import hashlib
import json
import zlib

import atlas_paths as P
import school_web as W


def main():
    path = P.data('lab-websites.json', 'vt')
    doc = json.loads(path.read_text())
    repair = json.loads((path.parent / 'jamie-sikora-website-repair.json').read_text())
    source = repair['official_profile_url']
    site = repair['repaired_url']
    db = W.con('vt')
    rows = [db.execute('select status,sha256,raw_zlib,content_type,fetched_at from live where url=?',
                       (url,)).fetchone() for url in (source, site)]
    assert all(row and row[0] == 200 and row[2] for row in rows)
    raw = [zlib.decompress(row[2]) for row in rows]
    assert all(hashlib.sha256(blob).hexdigest() == row[1] for blob, row in zip(raw, rows))
    assert rows[0][1] == repair['official_profile_sha256']
    assert rows[1][1] == repair['repaired_site_sha256']
    assert repair['literal_malformed_anchor_url'] in raw[0].decode('utf-8', 'replace')
    assert repair['literal_malformed_anchor_url'] == site + site
    site_text = W.flat(W.extract.blocks(raw[1], rows[1][3], site))
    assert repair['repaired_site_quote'] in site_text
    row = next(row for row in doc['labs'] if row['pi'] == 'Jamie Sikora')
    at = rows[0][4][:10]
    row.update(coverage='website', kind='pi_homepage', reason_code='pi_homepage_only_no_lab_site',
               found_via='school_profile_link', listed_on=source, fetched=True,
               sha256=rows[1][1], names_person=True, audited_at=at, checked_at=at,
               checks=[dict(source='school_profile_link', url=site, on=source,
                            result='listed_after_duplicate_href_repair', at=at,
                            source_sha256=rows[0][1], literal_href=repair['literal_malformed_anchor_url'],
                            repair_rule=repair['repair_rule'],
                            reviewed_receipt='hierarchy/vt/reviewed/jamie-sikora-website-repair.json'),
                       dict(source='candidate_site', url=site, result='ok', at=rows[1][4][:10],
                            sha256=rows[1][1], quote=repair['repaired_site_quote'])])
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print('Jamie Sikora')


if __name__ == '__main__':
    main()
