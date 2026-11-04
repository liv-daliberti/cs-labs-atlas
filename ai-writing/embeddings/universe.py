"""The paper list of the study: every lab paper of the released schools (and the onboarding schools whose packages exist), one row per work.

reads   hierarchy/<school>/derived/{lab_papers.jsonl.gz, pis.json}   (atlas_paths data slots)
writes  EMB/universe.sqlite
          papers(paper_id PK, oa, doi, title, year, date, home_school, schools json, n_labs)
          lab_papers(paper_id, school, lab_id, pi, lab_name, dept, year)      one row per (work, lab); a work of two labs has two
          oa_ids(oa PK)                                                        the OpenAlex ids to pull abstracts and topics for
paper_id is the work's atlas id (atl:w:...); a row the build gave none (older packages) gets oa:<W id> or key:<school>:<work>.
home_school is the first school in ecommon.SCHOOLS order that has the work: its embeddings live in that school's container.
usage: universe.py build
"""
import gzip
import json
import sqlite3
import sys

import ecommon as C
P = C.P


def rows_of(school):
    with gzip.open(P.data('lab_papers.jsonl.gz', school), 'rt') as f:
        for line in f:
            yield json.loads(line)


def lab_table(school):
    """{pi name: (lab id, lab name, department)} from the school's pis.json."""
    out = {}
    for q in json.load(open(P.data('pis.json', school))):
        lab = q.get('lab') or {}
        out[q['pi']] = (q.get('labId') or f'atl:l:{school}:{q["pi"]}', lab.get('name') or q['pi'], (q.get('departments') or [None])[0])
    return out


def paper_id(r, school):
    if r.get('atlasWorkId'):
        return r['atlasWorkId']
    if r.get('oa'):
        return 'oa:' + r['oa'].rsplit('/', 1)[-1]
    return f'key:{school}:{r.get("work") or r.get("doi") or r.get("title")}'


def build(schools=None, out=None):
    schools = [s for s in (schools or C.SCHOOLS) if P.data('lab_papers.jsonl.gz', s).exists()]
    papers, labs = {}, []
    for s in schools:
        tab = lab_table(s)
        seen = set()
        for r in rows_of(s):
            pid = paper_id(r, s)
            lab = tab.get(r['pi'], (f'atl:l:{s}:{r["pi"]}', r['pi'], None))
            if (pid, lab[0]) not in seen:
                seen.add((pid, lab[0]))
                labs.append((pid, s, lab[0], r['pi'], lab[1], lab[2], r.get('year')))
            p = papers.setdefault(pid, dict(paper_id=pid, oa=r.get('oa'), doi=r.get('doi'), title=r.get('title') or '', year=r.get('year'),
                                            date=r.get('date'), schools=[]))
            for k in ('oa', 'doi', 'title', 'year', 'date'):
                if not p.get(k) and r.get(k):
                    p[k] = r[k]
            if s not in p['schools']:
                p['schools'].append(s)
    out = out or C.UNIVERSE_DB
    out.parent.mkdir(parents=True, exist_ok=True)

    def write(t):
        db = sqlite3.connect(t)
        db.execute('create table papers (paper_id text primary key, oa text, doi text, title text, year int, date text, home_school text, schools text, n_labs int)')
        db.execute('create table lab_papers (paper_id text, school text, lab_id text, pi text, lab_name text, dept text, year int)')
        db.execute('create table oa_ids (oa text primary key)')
        nl = {}
        for x in labs:
            nl[x[0]] = nl.get(x[0], 0) + 1
        db.executemany('insert into papers values (?,?,?,?,?,?,?,?,?)',
                       [(p['paper_id'], p['oa'], p['doi'], p['title'], p['year'], p['date'], sorted(p['schools'], key=C.SCHOOLS.index)[0],
                         json.dumps(sorted(p['schools'], key=C.SCHOOLS.index)), nl.get(p['paper_id'], 0)) for p in papers.values()])
        db.executemany('insert into lab_papers values (?,?,?,?,?,?,?)', labs)
        db.executemany('insert or ignore into oa_ids values (?)', [(p['oa'].rsplit('/', 1)[-1],) for p in papers.values() if (p['oa'] or '').startswith('https://openalex.org/W')])
        db.execute('create index lp_paper on lab_papers(paper_id)'); db.execute('create index lp_lab on lab_papers(lab_id)')
        db.commit(); db.close()
    C.atomic_write(out, write)
    by = {}
    for p in papers.values():
        by[sorted(p['schools'], key=C.SCHOOLS.index)[0]] = by.get(sorted(p['schools'], key=C.SCHOOLS.index)[0], 0) + 1
    C.log(universe=str(out), schools=schools, papers=len(papers), lab_paper_rows=len(labs), home_school_papers=by,
          no_atlas_id=sum(not str(k).startswith('atl:w:') for k in papers))
    return papers


def load_papers(db=None):
    """[(paper_id, oa, title, year, home_school)] from the universe."""
    d = sqlite3.connect(f'file:{db or C.UNIVERSE_DB}?mode=ro', uri=True)
    rows = d.execute('select paper_id, oa, title, year, home_school from papers order by paper_id').fetchall()
    d.close()
    return rows


if __name__ == '__main__':
    if sys.argv[1:] == ['build']:
        build()
    else:
        raise SystemExit(__doc__)
