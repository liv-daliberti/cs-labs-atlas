"""Reconcile the two source-backed VT appointment starts found in the Stage 4 precheck.

Run after periods_school.py extract vt; that extractor does not parse these page
wordings and rewrites faculty-periods.json, so this review must run last.
"""
import hashlib
import json
import zlib
from pathlib import Path

import school_web as W


ROOT = Path(__file__).resolve().parents[1]
CENSUS = ROOT / 'hierarchy/vt/derived/census-faculty.json'
PERIODS = ROOT / 'hierarchy/vt/reviewed/faculty-periods.json'
SOURCES = (
    ('Na Meng', '2015', 'https://people.cs.vt.edu/nm8247/',
     'She started working in Virginia Tech as an Assistant Professor in 2015.',
     'Na Meng is an Associate Professor in the Department of Computer Science at Virginia Tech since 2021.'),
    ('Pinar Yanardag', '2023', 'https://website.cs.vt.edu/research/Seminars/Pinar_Yanardag.html',
     'Since joining Virginia Tech in Fall 2023, her lab has produced over 25 publications', None),
)


def main():
    faculty = {x['name']: x for x in json.loads(CENSUS.read_text())['faculty']}
    periods = {x['name']: x for x in json.loads(PERIODS.read_text())}
    c = W.con('vt')
    for name, start, url, quote, corroboration in SOURCES:
        person = faculty[name]
        assert person['is_pi'], name
        row = c.execute('select status, sha256, raw_zlib, content_type, fetched_at from live where url=?', (url,)).fetchone()
        assert row and row[0] == 200 and row[2], url
        raw = zlib.decompress(row[2])
        assert hashlib.sha256(raw).hexdigest() == row[1], url
        page = W.flat(W.extract.blocks(raw, row[3], url))
        assert quote in page and (not corroboration or corroboration in page), url
        evidence = [{'url': url, 'sha256': row[1], 'quote': q, 'observedAt': row[4][:10]}
                    for q in (quote, corroboration) if q]
        periods[name] = {
            'id': 'vt_faculty_period_' + name.lower().replace(' ', '_'),
            'personId': person['collection_person_id'], 'name': name, 'school': 'vt', 'unitIds': [],
            'facultyStart': start, 'facultyEnd': None, 'labStart': None, 'labEnd': None,
            'datePrecision': 'year', 'endDatePrecision': None, 'evidence': evidence,
            'facultyPeriodStatus': 'supported_start', 'labPeriodStatus': 'unresolved',
            'boundaryYearUncertain': True, 'boundaryMonthUncertain': True,
            'conflictingStartYears': [], 'addedBy': 'tools/vt_stage4_precheck.py',
            'qualification': 'University-hosted page states the VT appointment start; end and lab period remain unresolved.',
        }
    PERIODS.write_text(json.dumps(sorted(periods.values(), key=lambda x: x['name']), indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({'reviewed_periods': list(x[0] for x in SOURCES), 'total_periods': len(periods)}))


if __name__ == '__main__':
    main()
