# Vendored 2026-10-30 from /n/fs/resemble/maxent-grpo/.research-sweeps/claude-homogenization-20261019/tools/fulltext_store.py (sha256 5b5a04e0596f48c6ae096dc167b1600214a3328f992d682cfee5ed8f18876544); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Full texts of the study-set papers (corpus/papers.jsonl.gz) at all four schools, for the full-text versions of the
text measures (tools/fulltext_style.py, lm_surprisal.py --section intro).

match    each corpus paper -> its stored copy, by the coverage counter's rule (tools/fulltext_coverage_count.py): the
         catalog work with the paper's work key, else its DOI, else its normalized title, among works whose status is
         downloaded (asset kind pdf) or fulltext_xml (asset kind xml; JATS / TEI). Catalogs are read in rowid chunks so
         the running collectors' commits are not starved. A PDF is preferred to an XML copy of the same paper.
extract  pdftotext (first 60 pages, 120 s limit) or the XML's <body>, then sections:
           intro  from an Introduction heading ('1 Introduction', '1. INTRODUCTION', 'I. Introduction' or the bare word on
                  its own line) to the next section heading (numbered 2 / II, or Related Work, Background,
                  Preliminaries, Method(s), Approach, Model, Problem ...), at most 20,000 characters
           body   from the Introduction (else from the end of the first page's abstract, else the start) to the last
                  References / Bibliography heading in the second half of the text, at most 300,000 characters
         flags: title_found (the normalized title's first 40 characters occur in the normalized first 4,000 characters:
         a check on the collector's identity check), intro_found, refs_cut, pages, chars.
store    texts(path PRIMARY KEY, kind, pages, chars, intro zlib, body zlib, flags JSON, at) keyed by the stored file, so a
         later corpus only extracts files it has not seen; matches(id, school, year, path) rewritten on every run. Built
         in local /tmp (high-I/O intermediate) and copied to corpus/fulltext.sqlite at the end of the run.
usage: fulltext_store.py [-j workers]   (default 12; nice)
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import gzip, html, json, os, re, shutil, sqlite3, subprocess, sys, time, unicodedata, zlib
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

HERE = P.HOMOGENIZATION_STUDY  # vendored: the data root (was Path(__file__).resolve().parents[1])
FT = P.STORES
OUT = HERE / 'corpus' / 'fulltext.sqlite'
WORK = Path(os.environ.get('FULLTEXT_WORK', '/tmp/od2961-fulltext-store'))
INTRO_MAX, BODY_MAX = 20000, 300000

INTRO = re.compile(r'^[ \t]*(?:(?:1|I)[.:]?[ \t]+)?(?:INTRODUCTION|Introduction)[ \t]*$', re.M)
NEXT = re.compile(r'^[ \t]*(?:(?:2|II)[.:]?[ \t]+[A-Z][^\n]{2,80}|(?:2|II)[.:]?[ \t]*\n[ \t]*[A-Z][^\n]{2,80}|[A-Z][A-Z\-:&]+(?: [A-Z\-:&]+)+|'
                  r'(?:\d[.:]?[ \t]+)?(?:RELATED WORK|Related Work|Related work|BACKGROUND|Background|PRELIMINARIES|Preliminaries|METHODS?|Methods?|'
                  r'APPROACH|Approach|PROBLEM [A-Z ]+|Problem [A-Za-z ]+|MODEL|Model|OVERVIEW|Overview))[ \t]*$', re.M)  # number and heading may sit on two lines; an all-caps heading line ends it too
TOC = re.compile(r'(?:\. ){4,}|\.{6,}')  # dot leaders: a table of contents, not the Introduction
REFS = re.compile(r'^[ \t]*(?:\d+[.:]?[ \t]+)?(?:REFERENCES|References|BIBLIOGRAPHY|Bibliography|Literature Cited|LITERATURE CITED)[ \t]*$', re.M)
ABS_END = re.compile(r'^[ \t]*(?:Keywords|KEYWORDS|Index Terms|CCS Concepts|ACM Reference Format)\b', re.M)


def nt(t):
    t = unicodedata.normalize('NFKD', t or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', t)


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def clean(t):
    t = t.replace('ﬁ', 'fi').replace('ﬂ', 'fl').replace('ﬀ', 'ff').replace('ﬃ', 'ffi').replace('ﬄ', 'ffl').replace('\x0c', '\n')
    return re.sub(r'-\n(?=[a-z])', '', t)


def flat(t):
    return ' '.join(t.split())


def sections(t, title):
    t = clean(t)
    m = next((x for x in INTRO.finditer(t, 0, min(len(t), 60000)) if not TOC.search(t, x.end(), x.end() + 400)), None)
    r = [x for x in REFS.finditer(t) if x.start() > len(t) * 0.5]
    end = r[-1].start() if r else len(t)
    intro = ''
    if m:
        n = NEXT.search(t, m.end() + 200, end)
        intro = t[m.end():n.start() if n else min(end, m.end() + INTRO_MAX)]
        start = m.end()
    else:
        a = ABS_END.search(t, 0, min(len(t), 8000))
        start = a.start() if a else 0
    head = nt(t[:4000])
    return dict(intro=flat(intro)[:INTRO_MAX], body=flat(t[start:end])[:BODY_MAX],
                flags=dict(title_found=bool(title) and nt(title)[:40] in head, intro_found=bool(m), refs_cut=bool(r), chars=len(t)))


def xml_text(raw):
    """JATS / TEI: the <body>, sections as heading lines, tags stripped."""
    b = re.search(r'<body[^>]*>(.*)</body>', raw, re.S)
    x = b.group(1) if b else raw
    x = re.sub(r'<(?:title|head)[^>]*>(.*?)</(?:title|head)>', lambda m: '\n' + re.sub(r'<[^>]+>', '', m.group(1)).strip() + '\n', x, flags=re.S)
    x = re.sub(r'</(?:p|sec|div)>', '\n', x)
    return html.unescape(re.sub(r'<[^>]+>', ' ', x))


def extract(job):
    path, kind, title = job
    p = FT / path
    try:
        if kind == 'pdf':
            r = subprocess.run(['pdftotext', '-q', '-l', '60', '-enc', 'UTF-8', str(p), '-'], capture_output=True, timeout=120)
            t = r.stdout.decode('utf-8', 'ignore')
            pages = t.count('\x0c')
        else:
            t = xml_text(p.read_text('utf-8', 'ignore'))
            pages = None
    except Exception as e:
        return path, kind, None, dict(error=type(e).__name__)
    if len(t.strip()) < 500:
        return path, kind, None, dict(error='no_text', chars=len(t.strip()))
    s = sections(t, title)
    s['flags']['pages'] = pages
    return path, kind, s, s['flags']


def excerpt(text, words=400):
    """The first `words` words, cut back to the last sentence end when that keeps at least half of them. The full-text
    measures read fixed-length excerpts, so longer papers (or longer introductions) cannot raise a word's presence rate."""
    t = ' '.join(text.split()[:words])
    k = t.rfind('. ')
    return t[:k + 1] if k > len(t) * 0.5 else t


def load_texts(path=OUT):
    """{corpus id: dict(intro, body, flags, school, year)} for the matched papers with extracted text. intro is the
    Introduction's 400-word excerpt (the body's opening when no Introduction was found: flags['intro_found'] says which),
    body the 2,000-word excerpt of the body; papers with fewer than 100 words of either are left out."""
    db = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    out = {}
    for i, school, year, intro, body, flags in db.execute('SELECT m.id, m.school, m.year, t.intro, t.body, t.flags FROM matches m JOIN texts t ON t.path = m.path '
                                                         'WHERE t.body IS NOT NULL'):
        intro, body, flags = zlib.decompress(intro).decode(), zlib.decompress(body).decode(), json.loads(flags)
        src = intro if len(intro.split()) >= 100 else body
        if len(src.split()) < 100:
            continue
        out[i] = dict(intro=excerpt(src, 400), body=excerpt(body, 2000), flags=dict(flags, intro_used=src is intro), school=school, year=year)
    db.close()
    return out


def catalog(school):
    """work id / 'doi:' / 't:' keys -> (relative path, kind), from the copies on disk."""
    db = sqlite3.connect(f'file:{FT / school / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
    assets = {}
    hi = db.execute('SELECT MAX(rowid) FROM assets').fetchone()[0] or 0
    for lo in range(0, hi + 1, 5000):
        for w, k, p in db.execute('SELECT work_id, kind, path FROM assets WHERE rowid >= ? AND rowid < ?', (lo, lo + 5000)):
            if p and (k == 'pdf' or (k == 'xml' and w not in assets)):  # a PDF wins over an XML copy
                assets[w] = (f'{school}/{p}', k)
        time.sleep(0.05)
    out = {}
    hi = db.execute('SELECT MAX(rowid) FROM works').fetchone()[0] or 0
    for lo in range(0, hi + 1, 2000):
        for i, title, doi, st, fp in db.execute('SELECT id, title, doi, status, file_path FROM works WHERE rowid >= ? AND rowid < ?', (lo, lo + 2000)):
            if st not in ('downloaded', 'fulltext_xml'):
                continue
            a = assets.get(i) or ((f'{school}/{fp}', 'pdf') if fp and fp.endswith('.pdf') else None)
            if not a:
                continue
            for k in (i, 'doi:' + doi.lower() if doi else None, 't:' + nt(title) if title else None):
                if k and (k not in out or (a[1] == 'pdf' and out[k][1] != 'pdf')):
                    out[k] = a
        time.sleep(0.05)
    db.close()
    return out


def main():
    a = sys.argv[1:]
    n = int(a[a.index('-j') + 1]) if '-j' in a else 12
    WORK.mkdir(parents=True, exist_ok=True)
    work = WORK / 'fulltext.sqlite'
    if not work.exists() and OUT.exists():
        shutil.copy2(OUT, work)  # resume from the last copy on the share
    db = sqlite3.connect(str(work))
    db.execute('CREATE TABLE IF NOT EXISTS texts (path TEXT PRIMARY KEY, kind TEXT, pages INTEGER, chars INTEGER, intro BLOB, body BLOB, flags TEXT, at TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS matches (id TEXT PRIMARY KEY, school TEXT, year INTEGER, path TEXT)')
    rows = [json.loads(l) for l in gzip.open(HERE / 'corpus' / 'papers.jsonl.gz', 'rt')]
    match, n_match = {}, Counter()
    for school in sorted({r['school'] for r in rows}):
        cat = catalog(school)
        for r in rows:
            if r['school'] != school:
                continue
            hit = cat.get(r.get('work_key')) or (cat.get('doi:' + r['doi'].lower()) if r.get('doi') else None) or cat.get('t:' + nt(r['title']))
            if hit:
                match[r['id']] = (school, r['year'], hit[0], hit[1], r['title'])
                n_match[school] += 1
        print(json.dumps(dict(school=school, papers=sum(1 for r in rows if r['school'] == school), with_copy=n_match[school])), flush=True)
    db.execute('DELETE FROM matches')
    db.executemany('INSERT OR REPLACE INTO matches VALUES (?,?,?,?)', [(i, s, y, p) for i, (s, y, p, k, t) in match.items()])
    db.commit()
    done = {p for (p,) in db.execute('SELECT path FROM texts')}
    jobs = list({p: (p, k, t) for s, y, p, k, t in match.values() if p not in done}.values())
    print(json.dumps(dict(files=len({m[2] for m in match.values()}), done=len(done), todo=len(jobs), workers=n)), flush=True)
    got, t0 = Counter(), time.monotonic()
    with ProcessPoolExecutor(n) as ex:
        for i, (path, kind, s, flags) in enumerate(ex.map(extract, jobs, chunksize=8)):
            if s:
                db.execute('INSERT OR REPLACE INTO texts VALUES (?,?,?,?,?,?,?,?)', (path, kind, flags.get('pages'), flags.get('chars'),
                           zlib.compress(s['intro'].encode(), 6), zlib.compress(s['body'].encode(), 6), json.dumps(flags), now()))
                got['ok'] += 1; got['intro'] += flags['intro_found']; got['title_found'] += flags['title_found']
            else:
                db.execute('INSERT OR REPLACE INTO texts VALUES (?,?,?,?,?,?,?,?)', (path, kind, None, flags.get('chars'), None, None, json.dumps(flags), now()))
                got[flags.get('error', 'error')] += 1
            if i % 500 == 499:
                db.commit(); print(json.dumps(dict(done=i + 1, of=len(jobs), per_s=round((i + 1) / (time.monotonic() - t0), 1), **got)), flush=True)
            if i % 10000 == 9999:
                db.close(); shutil.copy2(work, OUT); db = sqlite3.connect(str(work))  # a periodic copy on the share
    db.commit(); db.close()
    shutil.copy2(work, OUT)
    print(json.dumps(dict(finished=now(), **got)), flush=True)


if __name__ == '__main__':
    main()
