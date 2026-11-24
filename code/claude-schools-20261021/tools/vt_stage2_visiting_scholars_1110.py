"""Resolve VT-affiliated bylines with dated publisher author biographies."""

import hashlib
import json
import subprocess
import zlib

import atlas_paths as P
import school_web as W


ROWS = (
    ('Feng Tian', 'https://www.cnsr.ictas.vt.edu/publication/t7.pdf',
     'He was a visiting scholar at Virginia Tech, USA from 2013-2015.',
     'research_or_other_rank',
     'A captured VT-hosted paper biography identifies a 2013–2015 visiting-scholar role and a Nanjing professorship, not a VT faculty appointment in the study window.'),
    ('Jianhui Zhao', 'https://virtualhumans.mpi-inf.mpg.de/papers/YuPAMI2019/YuPAMI2019.pdf',
     'He has been working in Virginia Tech as a visiting scholar from 2009 to 2010.',
     'research_or_other_rank',
     'A captured publisher manuscript biography identifies a 2009–2010 VT visiting-scholar role and long Beihang faculty tenure, not a VT faculty appointment in the study window.'),
    ('Yubo Yuan', 'https://www.jsoftware.us/vol8/jsw0809-27.pdf',
     'From July 2006 to August 2008, he worked as Research Assistant Professor in Mathematics Department of Virginia Tech, USA.',
     'not_faculty_listed',
     'The captured author biography dates his VT research-assistant professorship in Mathematics to 2006–2008, before the 2016–2026 window, and records a China Jiliang appointment from 2009.'),
)


def main():
    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    candidates = {x['name']: x for x in json.loads(P.data('cs-related-candidates.json', 'vt').read_text())}
    existing = {x['name'] for x in doc['decisions']}
    db = W.con('vt')
    for name, url, quote, decision, reason in ROWS:
        if name in existing:
            continue
        r = db.execute('select status,sha256,raw_zlib,fetched_at from live where url=?',
                       (url,)).fetchone()
        assert r and r[0] == 200 and r[2], name
        raw = zlib.decompress(r[2])
        assert hashlib.sha256(raw).hexdigest() == r[1]
        text = ' '.join(subprocess.run(['pdftotext', '-raw', '-', '-'], input=raw,
                                       capture_output=True, check=True).stdout.decode('utf8', 'replace').split())
        assert quote in text, name
        c = candidates[name]
        doc['decisions'].append(dict(
            name=name, aliases=c.get('aliases') or [], source=c['source'], decision=decision,
            reason=reason,
            cs_basis=dict(dblp=[c['dblp']], dblp_window=c.get('dblp_window', 0),
                          affiliation_notes=c.get('affiliations') or []),
            faculty_evidence=[], status_evidence=[dict(url=url, sha256=r[1], quote=quote,
                                                      observed=r[3][:10])],
            years_listed=[], units_searched=['VT official faculty rosters 2016–2026'],
            provisional='Reopen if a dated VT professor-rank appointment is found.',
        ))
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'reviewed': [x[0] for x in ROWS]}))


if __name__ == '__main__':
    main()
