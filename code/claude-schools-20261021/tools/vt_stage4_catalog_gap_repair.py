"""Close three VT PI listing gaps using dated, full-name registrar directories.

The 2018–19 and 2019–20 academic-year faculty directories are explicit
professor-rank listings. They supplement the dated Wayback captures already
reviewed by periods_school.gaps; no unproven year is silently bridged.
"""

import hashlib
import json
import zlib

import atlas_paths as P
import census_overrides as CO
import school_web as W


CATALOGS = {
    '2018-19': 'https://www.undergradcatalog.registrar.vt.edu/1819/faculty.html',
    '2019-20': 'https://www.undergradcatalog.registrar.vt.edu/1920/faculty.html',
}
CASES = {
    'Doug Bowman': ('2019-20', 'BOWMAN, Doug A. (1999), Prof. of Computer Science.', [2020], [2021, 2024]),
    'Wu-chun Feng': ('2018-19', 'FENG, Wu-chun (2006), Prof. of Computer Science.', [2018, 2019], [2024]),
    'Wenjing Lou': ('2019-20', 'LOU, Wenjing (2011), Prof. of Computer Science.', [2020], [2021, 2024]),
}


def main():
    db = W.con('vt')
    saved = {}
    for label, url in CATALOGS.items():
        row = db.execute('select status,sha256,raw_zlib,content_type,fetched_at from live where url=?', (url,)).fetchone()
        assert row and row[0] == 200 and row[2], label
        raw = zlib.decompress(row[2])
        assert hashlib.sha256(raw).hexdigest() == row[1], label
        saved[label] = (url, row[1], W.flat(W.extract.blocks(raw, row[3], url)))
    gap = json.loads(P.data('gap-year-evidence.json', 'vt').read_text())
    census = {x['name']: x for x in json.loads(P.data('census-faculty.json', 'vt').read_text())['faculty']}
    sec, save = CO.open_section('vt')
    for name, (label, quote, catalog_years, archived_years) in CASES.items():
        url, sha, text = saved[label]
        assert quote in text, name
        g = gap[name]
        assert not g['closed']
        assert sorted(g['gap_years']) == sorted(catalog_years + archived_years), name
        assert set(map(str, archived_years)) <= set(g['evidence']), name
        assert name in census and census[name]['is_pi']
        for year in archived_years:
            e = g['evidence'][str(year)]
            assert e['observed'].startswith(str(year)) and e['quote'] and len(e['sha256']) == 64
        evidence = [dict(url=url, sha256=sha, quote=quote, kind='registrar_faculty_catalog',
                         academic_year=label, proves_years=catalog_years)]
        evidence.extend(dict(url=g['evidence'][str(y)]['url'],
                             sha256=g['evidence'][str(y)]['sha256'],
                             quote=g['evidence'][str(y)]['quote'],
                             observed=g['evidence'][str(y)]['observed'],
                             kind=g['evidence'][str(y)]['kind'], proves_years=[y])
                        for y in archived_years)
        first, last = min(census[name]['years_listed']), max(census[name]['years_listed'])
        assert first == 2016 and last == 2026
        entry = sec.setdefault(name, {})
        entry['periods'] = [dict(
            id='override_period_catalog_gaps_vt_' + name.lower().replace(' ', '_').replace('-', '_'),
            start=str(first), end=None, asof='2026-11-10', datePrecision='year', evidence=evidence,
            note=(f'Lower-bound VT faculty interval from {first} through {last}: dated CS listings '
                  f'plus full-name professor entry in the {label} official faculty catalog for '
                  f'{catalog_years}, and dated Wayback professor-title captures for {archived_years}. '
                  'No end date or exact appointment start is claimed.'),
            reviewed='vt_stage4_catalog_gap_repair_20261110',
        )]
        entry['why_periods'] = 'Every missing calendar year is supported by the official academic-year faculty directory or a dated professor-title capture.'
    save()
    print(json.dumps({'catalog_gap_periods': list(CASES)}))


if __name__ == '__main__':
    main()
