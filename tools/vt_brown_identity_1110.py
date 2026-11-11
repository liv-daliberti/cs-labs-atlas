"""Carry the reviewed Chris/Dwayne Brown join into periods and bibliography."""

import json
import subprocess
import tempfile
import zlib

from bs4 import BeautifulSoup

import atlas_paths as P
import school_web as W


HOME = 'https://chbrown13.github.io/'
CV = 'https://chbrown13.github.io/files/cv.pdf'
PROFILE = 'https://website.cs.vt.edu/people/faculty/chris-brown.html'
PID = 'https://dblp.org/pid/126/9627'


def main():
    census = json.loads(P.data('census-faculty.json', 'vt').read_text())['faculty']
    person = next(x for x in census if x['name'] == 'Chris Brown')
    assert 'Dwayne Brown' in person['aliases']
    assert not any(x['name'] == 'Dwayne Brown' for x in census)
    db = W.con('vt')
    home = db.execute('select status,sha256,fetched_at,raw_zlib from live where url=?',
                      (HOME,)).fetchone()
    assert home and home[0] == 200 and home[1]
    soup = BeautifulSoup(zlib.decompress(home[3]), 'html.parser')
    assert 'Chris Brown, Ph.D.' in ' '.join(soup.get_text(' ', strip=True).split())
    assert PID + '.html' in {a.get('href') for a in soup.select('a[href]')}
    official = db.execute('select status,sha256,raw_zlib from live where url=?',
                          (PROFILE,)).fetchone()
    assert official and official[0] == 200 and official[1]
    assert HOME in {a.get('href') for a in BeautifulSoup(zlib.decompress(official[2]), 'html.parser').select('a[href]')}
    cv = db.execute('select status,sha256,fetched_at,raw_zlib from live where url=?',
                    (CV,)).fetchone()
    assert cv and cv[0] == 200 and cv[1]
    with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
        f.write(zlib.decompress(cv[3]))
        f.flush()
        body = ' '.join(subprocess.check_output(['pdftotext', '-layout', f.name, '-']).decode('utf8', 'replace').split())
    assert 'DWAYNE CHRISTIAN BROWN, JR. (“CHRIS”)' in body
    assert 'Assistant Professor, Fall 2021 - present' in body
    path = P.data('census-overrides-school.json', 'vt')
    data = json.loads(path.read_text())
    item = data.setdefault('Chris Brown', {})
    item['periods'] = [dict(id='vt_chris_brown_faculty_2021_present', start='2021', end=None,
                            asof=cv[2][:10], datePrecision='year', evidence=[dict(
                                url=CV, sha256=cv[1], observed=cv[2][:10],
                                quote='Assistant Professor, Fall 2021 - present')])]
    item['why_periods'] = ('The captured first-party CV identifies Dwayne Christian Brown Jr. as Chris and dates his VT assistant professorship from fall 2021 to its observation; the 2022–23 and 2025–26 CS sources are one person. No period beyond the observed date is inferred.')
    item['dblp'] = [PID]
    item['why_dblp'] = ('The captured VT faculty page links his personal site, which names Chris Brown and directly links this DBLP person record. The first-party biography establishes the Dwayne/Chris alias. This binds identity, not individual papers.')
    item['dblp_evidence'] = [dict(source=HOME, source_type='officially linked personal homepage',
                                  source_sha256=home[1], fetched_at=home[2], self_link=PID + '.html',
                                  official_profile=PROFILE, official_profile_sha256=official[1],
                                  alias_source='https://chbrown13.github.io/biography.html')]
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({'period_reviewed': 'Chris Brown', 'dblp': PID}))


if __name__ == '__main__':
    main()
