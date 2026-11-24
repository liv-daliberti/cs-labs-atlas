"""Resolve the Mingyu Kim VT-byline candidate from an exact CV/publication chain."""

import collections
import hashlib
import json
import subprocess
import tempfile
import zlib

import atlas_paths as P
import school_web as W


CV = 'https://mingyu272.github.io/Ben-Mingyu-Kim.github.io/files/CV.pdf'
GSU = 'https://scholars.georgiasouthern.edu/en/persons/mingyu-kim/'


def captured(db, url):
    row = db.execute('select status,sha256,raw_zlib,content_type,fetched_at from live where url=?',
                     (url,)).fetchone()
    assert row and row[0] == 200 and row[2], url
    raw = zlib.decompress(row[2])
    assert hashlib.sha256(raw).hexdigest() == row[1]
    return row, raw


def main():
    db = W.con('vt')
    cvrow, pdf = captured(db, CV)
    with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
        f.write(pdf)
        f.flush()
        cv = subprocess.check_output(['pdftotext', '-layout', f.name, '-']).decode('utf8', 'replace')
    cv = ' '.join(cv.split()).lower()
    assert 'ph.d. in electrical and computer engineering' in cv
    assert 'graduated in may 2025' in cv
    assert 'supervised by prof. daniel j. stilwell' in cv
    assert 'toward optimal placement of spatial sensors to detect poisson-distributed targets' in cv
    grow, html = captured(db, GSU)
    body = W.flat(W.extract.blocks(html, grow[3], GSU))
    assert 'MinGyu Kim Assistant Professor, Electrical & Computer Engineering' in body
    assert 'Prof. Kim joined Georgia Southern University in 2026' in body
    assert 'Near-Optimal Sensor Placement for Detecting Stochastic Target Trajectories in Barrier Coverage Systems' in body
    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    assert 'Mingyu Kim' not in {x['name'] for x in doc['decisions']}
    candidate = next(x for x in json.loads(P.data('cs-related-candidates.json', 'vt').read_text())
                     if x['name'] == 'Mingyu Kim')
    assert candidate['dblp'] == 'https://dblp.org/pid/64/10624-3'
    doc['decisions'].append(dict(
        name='Mingyu Kim', aliases=candidate.get('aliases') or [], source=candidate['source'],
        decision='not_faculty_listed',
        reason='Exact candidate publication and adviser connect the 2025 VT ECE PhD CV to the DBLP person; Georgia Southern records his subsequent faculty start in 2026. No VT professor-rank appointment is established.',
        cs_basis=dict(dblp=[candidate['dblp']], dblp_window=candidate['dblp_window'],
                      affiliation_notes=candidate.get('affiliations') or []),
        faculty_evidence=[], status_evidence=[
            dict(url=CV, sha256=cvrow[1], observed=cvrow[4][:10],
                 quote='Virginia Tech, Blacksburg, VA Ph.D. in Electrical and Computer Engineering ... Graduated in May 2025; supervised by Prof. Daniel J. Stilwell; Toward optimal placement of spatial sensors to detect Poisson-distributed targets'),
            dict(url=GSU, sha256=grow[1], observed=grow[4][:10],
                 quote='Prof. Kim joined Georgia Southern University in 2026'),
        ], years_listed=[], units_searched=['VT official faculty rosters 2016–2026'],
        provisional='Reopen if a dated VT professor-rank appointment is found.',
    ))
    doc['counts'] = dict(collections.Counter(x['decision'] for x in doc['decisions']))
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'reviewed': 'Mingyu Kim'}))


if __name__ == '__main__':
    main()
