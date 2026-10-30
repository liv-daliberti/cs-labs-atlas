"""The organized view of the CS PI-lab data on disk: school -> lab -> papers, one folder per PI lab (owner 2026-10-29).

  /n/fs/resemble/cs-atlas/schools/<school>/   (atlas_paths.SCHOOLS_TREE)
    school.json                     school name, departments, lab list and counts
    labs/<pi-slug>/                 one PI's own lab (the slug the GitHub export uses: <school>:<pi-slug>)
      lab.json                      PI, names, departments, lab name, PI basis, appointment periods with evidence, identity
                                    (reviewed OpenAlex ids, ORCID), counts, and the hidden-lab reason when it has no papers;
                                    the atlas ids (docs/IDS.md): labId (atl:l:), piAtlasId (atl:p:), appointments (every
                                    atlas school where this person is a PI) and asStudent (their student records elsewhere)
      students.csv                  the lab's students: atlas_id (atl:p:), name, id (the package's record id), roles, years,
                                    relation types, sources, linked lab papers, also_pi (lab ids where the person is a PI)
      papers.csv                    the lab's papers: atlas_work_id (atl:w:), year, title, venue, type, DOI, OpenAlex id, students on it, and the
                                    local PDF (the file in papers/, or the copy status and reason when there is none)
      papers/<year>_<title>_<id>.pdf  a HARDLINK to the stored copy (homogenizing-science/data/fulltext/<school>/objects or
                                    cs-atlas-fulltext/stanford/objects): no extra bytes, and a paper in two labs is in both

Inputs, read-only, from a dated release (since 2026-10-29; tools/make_release.py; default releases/latest):
<release>/hierarchy/<school>/{pis,students}.json, {lab,student}_papers.jsonl.gz, copies.json (which catalog work holds
each paper's copy, from tools/lab_paper_copies.py) and <release>/hierarchy/zero-paper-labs.json for hidden-lab reasons;
plus the school's catalog.sqlite (the stored file of that work). With --fresh-copies the copies come from the working
hierarchy/<school>/copies.json instead (rerun tools/lab_paper_copies.py first), so PDFs the collectors fetched since the
release are linked; the lab and paper lists still come from the release. school.json records the release id and the
copies' source. Rerunnable: links that already point at the right file are kept, new copies are linked, and PDFs in
papers/ that are no longer a lab paper with a copy are unlinked (only inside this tree).
usage: organize_tree.py [--release ID|DIR] [--fresh-copies] [school ...]          (default: all six)
"""
import argparse, csv, gzip, json, os, re, sqlite3, sys, time, unicodedata
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402  (every path in one place)

HERE = P.WORK; H = P.HIERARCHY  # H is re-pointed at <release>/hierarchy by main()
OUT = P.SCHOOLS_TREE
FT = P.STORES
SCHOOLS = list(P.SCHOOL_IDS)
RELEASE = dict(id=None, dir=None, copies='release')
import school_config as _S  # noqa: E402  (the school charters)
NAMES = _S.full_names()


def slug(s, n=None):  # as tools/export_release.py
    s = unicodedata.normalize('NFKD', str(s)); s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s[:n].rstrip('-') if n else s


def short_id(r):
    oa = str(r.get('oa') or '')
    if oa.startswith('https://openalex.org/'):
        return oa.rsplit('/', 1)[1]
    return slug(r.get('work') or r.get('doi') or 'paper', 40)


def stored_files(school):
    """{catalog work id: absolute path of its stored PDF}, read in short rowid chunks (collectors write the catalog)."""
    db = sqlite3.connect(f'file:{FT / school / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
    hi = db.execute('select max(rowid) from works').fetchone()[0] or 0
    out = {}
    for lo in range(0, hi + 1, 5000):
        for wid, fp in db.execute("select id, file_path from works where rowid >= ? and rowid < ? and status = 'downloaded' "
                                  "and file_path like '%.pdf'", (lo, lo + 5000)):
            p = Path(fp) if fp.startswith('/') else FT / school / fp
            out[wid] = p
        time.sleep(0.01)
    return out


def link(src, dst):
    """dst becomes a hardlink of src; returns 'kept', 'linked' or a failure reason."""
    try:
        s = src.stat()
    except OSError:
        return 'stored_file_missing'
    try:
        d = dst.stat()
        if d.st_ino == s.st_ino and d.st_dev == s.st_dev:
            return 'kept'
        dst.unlink()
    except FileNotFoundError:
        pass
    try:
        os.link(src, dst)
        return 'linked'
    except OSError as e:
        return f'link_failed:{e.errno}'


def write_csv(path, rows, cols):
    tmp = path.with_suffix('.csv.part')
    with open(tmp, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
    tmp.replace(path)


def write_json(path, data):
    tmp = path.with_suffix('.json.part'); tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False)); tmp.replace(path)


def build(school, hidden):
    D = H / school
    pis = json.loads((D / 'pis.json').read_text())
    stu = json.loads((D / 'students.json').read_text())
    lp = defaultdict(list)
    for l in gzip.open(D / 'lab_papers.jsonl.gz', 'rt'):
        r = json.loads(l); lp[r['pi']].append(r)
    sp = defaultdict(list)  # (pi, paper key) -> student names
    sp_by_student = defaultdict(int)
    for l in gzip.open(D / 'student_papers.jsonl.gz', 'rt'):
        r = json.loads(l)
        sp[(r['pi'], r.get('work') or r.get('oa'))].append(r.get('name') or r['student'])
        sp_by_student[(r['pi'], r['student'])] += 1
    copies = json.loads(((P.HIERARCHY / school if RELEASE['copies'] != 'release' else D) / 'copies.json').read_text())['papers']
    files = stored_files(school)
    sdir = OUT / school; (sdir / 'labs').mkdir(parents=True, exist_ok=True)
    n = defaultdict(int); labs = []
    for p in sorted(pis, key=lambda p: p['pi']):
        ls = slug(p['pi']); ldir = sdir / 'labs' / ls; (ldir / 'papers').mkdir(parents=True, exist_ok=True)
        rows, want = [], set()
        for r in sorted(lp[p['pi']], key=lambda r: (str(r.get('year') or ''), r.get('title') or '')):
            k = r.get('work') or r.get('oa'); c = copies.get(k) or {}
            src = files.get(c.get('catalog')) if c.get('status') == 'downloaded' else None
            name = f"{r.get('year') or 'nd'}_{slug(r.get('title') or 'untitled', 60)}_{short_id(r)}.pdf"
            res = link(src, ldir / 'papers' / name) if src else None
            if res in ('kept', 'linked'):
                want.add(name); n['pdfs_' + res] += 1
            elif res:
                n['pdf_' + res] += 1
            row = dict(atlas_work_id=r.get('atlasWorkId'), year=r.get('year'), title=r.get('title'), venue=r.get('venue'), type=r.get('type'), doi=r.get('doi'),
                       openalex=r.get('oa'), work=r.get('work'), students='; '.join(sorted(set(sp[(p['pi'], k)]))),
                       n_students=len(set(sp[(p['pi'], k)])), pdf=f'papers/{name}' if name in want else '',
                       copy_status=c.get('status') or 'not_in_catalog',
                       landing=r.get('landing'), appointment=json.dumps(r.get('appointment'), ensure_ascii=False))
            rows.append(row)
        for f in (ldir / 'papers').iterdir():  # stale links: only this tree's own files
            if f.suffix == '.pdf' and f.name not in want:
                f.unlink(); n['pdfs_unlinked_stale'] += 1
        write_csv(ldir / 'papers.csv', rows, ['atlas_work_id', 'year', 'title', 'venue', 'type', 'doi', 'openalex', 'work', 'students', 'n_students',
                                                'pdf', 'copy_status', 'landing', 'appointment'])
        srows = []
        for s in sorted(stu.get(p['pi']) or [], key=lambda s: s['name']):
            rel = s.get('relations') or []
            srows.append(dict(atlas_id=s.get('atlasId'), name=s['name'], id=s['person'], also_pi='; '.join(a['labId'] for a in s.get('alsoPi') or []), aliases='; '.join(s.get('aliases') or []), roles='; '.join(s.get('roles') or []),
                              years='; '.join(str(y) for y in sorted({str(y) for r in rel for y in (r.get('years') or []) if y})),
                              relations='; '.join(sorted({r.get('type') or '' for r in rel})),
                              sources=' | '.join(dict.fromkeys(q.get('url') for r in rel for q in r.get('sources') or [] if q.get('url')))[:2000],
                              lab_papers_linked=sp_by_student[(p['pi'], s['person'])]))
        write_csv(ldir / 'students.csv', srows, ['atlas_id', 'name', 'id', 'aliases', 'roles', 'years', 'relations', 'sources', 'lab_papers_linked', 'also_pi'])
        n_pdf = len(want)
        lab = dict(id=f'{school}:{ls}', labId=p.get('labId'), piAtlasId=p.get('atlasId'), appointments=p.get('appointments'),
                   asStudent=p.get('asStudent') or None, school=school, pi=p['pi'], names=p.get('names'), lab=(p.get('lab') or {}).get('name'),
                   departments=p.get('departments'), rank=p.get('rank'), title=p.get('title'), piBasis=p.get('piBasis'),
                   periods=p.get('periods'), listings=p.get('listings'), reviewedOpenAlex=p.get('reviewedOpenAlex'),
                   orcid=p.get('orcid'), dblp=p.get('dblp'),
                   counts=dict(papers=len(rows), papers_with_pdf=n_pdf, students=len(srows),
                               student_paper_links=sum(len(set(v)) for (pi, _), v in sp.items() if pi == p['pi'])),
                   hidden=hidden.get((school, p['pi'])))
        write_json(ldir / 'lab.json', lab)
        labs.append(dict(id=lab['id'], labId=lab['labId'], piAtlasId=lab['piAtlasId'], pi=p['pi'], folder=f'labs/{ls}', departments=p.get('departments'), **lab['counts'],
                         hidden=bool(lab['hidden'])))
        n['labs'] += 1; n['papers'] += len(rows); n['papers_with_pdf'] += n_pdf; n['students'] += len(srows)
    for d in (sdir / 'labs').iterdir():  # folders of PIs no longer in the package (renamed or dropped)
        if d.is_dir() and d.name not in {slug(p['pi']) for p in pis}:
            n['stale_lab_folders'] += 1; print(json.dumps(dict(school=school, stale_lab_folder=str(d))), flush=True)
    write_json(sdir / 'school.json', dict(school=school, name=NAMES.get(school, school), builtAt=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                                          release=RELEASE['id'], releaseDir=RELEASE['dir'], copiesFrom=RELEASE['copies'],
                                          counts=dict(n), labs=labs))
    print(json.dumps(dict(school=school, **n)), flush=True)
    return n


def release_dir(rel):
    """A release id ('2026-10-29'), 'latest', or a directory -> the release directory (resolved, so the id is the real one)."""
    d = (P.RELEASES / rel if (P.RELEASES / rel).exists() else Path(rel)).resolve()
    if not (d / 'MANIFEST.json').exists():
        raise SystemExit(f'not a release (no MANIFEST.json): {d}')
    return d


def main(schools, release='latest', fresh_copies=False):
    global H
    d = release_dir(release)
    H = d / 'hierarchy'
    RELEASE.update(id=json.loads((d / 'MANIFEST.json').read_text())['release'], dir=str(d),
                   copies='hierarchy (fresh, tools/lab_paper_copies.py)' if fresh_copies else 'release')
    hidden = {}
    zf = H / 'zero-paper-labs.json'
    if zf.exists():
        for r in json.loads(zf.read_text()).get('zero_papers') or []:
            hidden[(r['school'], r['pi'])] = {k: r.get(k) for k in ('diagnosis', 'verdict', 'reason', 'evidence') if r.get(k)}
    for s in schools:
        build(s, hidden)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('schools', nargs='*')
    ap.add_argument('--release', default='latest', help="release id, 'latest' (default) or a release directory")
    ap.add_argument('--fresh-copies', action='store_true', help="link copies from the working hierarchy/<school>/copies.json")
    a = ap.parse_args()
    main(a.schools or SCHOOLS, a.release, a.fresh_copies)
