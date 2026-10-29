"""Which lab papers can feed the figures -> lab classifier: every CS-hierarchy lab paper with a local PDF, labelled with
its lab (PI) and year, and the AI-writing study's flag.

paper   hierarchy/<school>/lab_papers.jsonl.gz rows; a paper in two or more labs of its school is left out (its label
        would be ambiguous), as is anything outside 2016-2026
pdf     the school's full-text catalog (data/fulltext/<school>/catalog.sqlite): works.status 'downloaded' with a PDF
        file_path, matched by catalog id = the paper's collection work id or <school>_oa_<W id> (copies.json records it)
flag    the full-text detector (ai-writing/paragraph_scores.jsonl.gz): ai_share >= 0.25 -> 1, scored but lower -> 0,
        unscored -> None (Stanford is not in the AI-writing study yet)
-> data/manifest.jsonl.gz, one row per (school, paper); prints papers per school and year
usage: manifest.py [school ...]
"""
import collections, gzip, json, sqlite3, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent; AIW = HERE.parent; ROOT = AIW.parent
H = ROOT / 'hierarchy'; FT = Path('/n/fs/resemble/homogenizing-science/data/fulltext')
SCHOOLS = ['princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford']
FLAG = 0.25


def catalog_pdfs(school):
    """{catalog id: absolute pdf path} for downloaded PDFs, read in short rowid chunks (collectors write the file)."""
    db = sqlite3.connect(f'file:{FT / school / "catalog.sqlite"}?mode=ro', uri=True, timeout=60)
    hi = db.execute('select max(rowid) from works').fetchone()[0] or 0
    out = {}
    for lo in range(0, hi + 1, 2000):
        for wid, fp in db.execute("select id, file_path from works where rowid >= ? and rowid < ? and status = 'downloaded' "
                                  "and file_path like '%.pdf'", (lo, lo + 2000)):
            out[wid] = str(FT / school / fp) if not fp.startswith('/') else fp
        time.sleep(0.02)
    return out


def flags():
    out = {}
    for l in gzip.open(AIW / 'paragraph_scores.jsonl.gz', 'rt'):
        r = json.loads(l)
        s = r.get('ai_share', r.get('share'))
        if r.get('key') and s is not None:
            out[r['key']] = int(s >= FLAG)
    return out


def main(schools):
    F = flags()
    (HERE / 'data').mkdir(exist_ok=True)
    rows = []
    for school in schools:
        labs = collections.defaultdict(set); rec = {}
        for l in gzip.open(H / school / 'lab_papers.jsonl.gz', 'rt'):
            r = json.loads(l)
            k = r.get('work') or r.get('oa')
            labs[k].add(r['pi']); rec[k] = r
        copies = json.loads((H / school / 'copies.json').read_text())['papers']
        pdfs = catalog_pdfs(school)
        n = collections.Counter()
        for k, r in rec.items():
            y = int(str(r.get('year') or 0)[:4] or 0)
            if len(labs[k]) != 1 or not 2016 <= y <= 2026:
                n['multi_lab_or_out_of_window'] += 1; continue
            cat = (copies.get(k) or {}).get('catalog')
            pdf = pdfs.get(cat) if cat else None
            if not pdf:
                n['no_local_pdf'] += 1; continue
            rows.append(dict(school=school, key=k, pi=r['pi'], year=y, title=(r.get('title') or '')[:200], pdf=pdf,
                             ai=next((F[f'{school}:{i}'] for i in (r.get('work'), r.get('oa')) if i and f'{school}:{i}' in F), None)))  # Berkeley keys by OpenAlex id
            n['kept'] += 1
        by_year = collections.Counter(x['year'] for x in rows if x['school'] == school)
        print(json.dumps(dict(school=school, **n, by_year=dict(sorted(by_year.items())),
                              flagged=sum(x['ai'] == 1 for x in rows if x['school'] == school))), flush=True)
    with gzip.open(HERE / 'data' / 'manifest.jsonl.gz', 'wt') as f:
        for x in rows:
            f.write(json.dumps(x) + '\n')


if __name__ == '__main__':
    main(sys.argv[1:] or SCHOOLS)
