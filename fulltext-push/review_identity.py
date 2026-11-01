"""Identity review of downloaded PDFs the collector left at identity_check='provider_link_only_review_pending' (2026-10-29).

The collector (homogenizing-science/scripts/collect_princeton_fulltext.py check_identity) confirms a PDF only when the
catalog title is an exact normalized substring of pages 1-3 (or the DOI is printed there); everything else waits here.
This review scores page 1 against the work's title (token recall and rapidfuzz partial ratio) and author family names
(lab_papers.jsonl.gz byline, graph_json, oa_json), with pages 1-3 as a guard against rejecting a file whose page 1 is a
cover sheet.

  score <school>   read-only: pending rows -> review-20261029/scores-<school>.jsonl (scores, verdict, page-1 excerpt)
  apply <school>   write the verdicts (conservative thresholds below; the middle band stays pending):
      confirm  works.identity_check and assets.identity_check -> CONFIRMED (+ an attempts row 'identity_rechecked',
               as homogenizing-science/scripts/verify_princeton_fulltext.py records an upgrade)
      reject   as the collector's reclassify_nonarticles: works.status='queued' and the file columns cleared; the asset
               row becomes kind 'identity_mismatch_pdf' (kept, so the object stays referenced and is not deleted;
               its url keeps its 'downloaded' attempts row, so the collector does not fetch the same file again); an
               attempts row 'identity_mismatch' with the reason; the work's by_lab/*/<year>--<id>.pdf links removed.
   Each write: short transaction, busy_timeout 120 s, <= 200 rows, WHERE on the old state (status='downloaded' AND
   identity_check pending AND sha256 unchanged), so a row the collector changed meanwhile is left alone.
   Every change -> review-20261029/<school>.jsonl.
usage: review_identity.py score|apply <school> [--workers N]
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[1] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import gzip, json, re, sqlite3, subprocess, sys, time, unicodedata, zlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from rapidfuzz import fuzz

HERE = Path(__file__).resolve().parent
OUT = P.ft_review('20261029')
STORES = P.STORES
WORK = HERE.parent
PENDING = 'provider_link_only_review_pending'
CONFIRMED = 'reviewed_title_and_authors_on_first_page'
CONFIRMED_ARXIV = 'reviewed_title_variant_and_exact_arxiv_identifier'  # the value an earlier manual review used
CONFIRMED_VARIANT = 'reviewed_title_variant_and_authors_on_first_page'
STOP = set('a an the of and or for in on at to with by from via into over under is are be as its it this that we our using use based '
           'toward towards new de la le des et du en und der die das'.split())

# thresholds (see the report: tuned against the hand-checked samples)
CONFIRM_FUZZ, CONFIRM_RECALL = 90, 0.85
REJECT_FUZZ, REJECT_RECALL = 55, 0.40


def now():
    return datetime.now(timezone.utc).isoformat()


def words(s):
    s = re.sub(r'<[^>]+>', ' ', s or '')
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'-\s*\n\s*', '', s)  # hyphenated line breaks
    return re.findall(r'[a-z]+|[0-9]+', s)


def nt(t):
    return ''.join(words(t))


def ndoi(s):
    return re.sub(r'^https?://(?:dx\.)?doi\.org/', '', str(s or '').strip(), flags=re.I).lower()


def family(name):
    name = re.sub(r'\([^)]*\)', ' ', name or '')
    if ',' in name:
        name = name.split(',')[0]
        w = words(name)
        return w[-1] if w and len(w[-1]) >= 2 else None
    w = words(name)
    w = [x for x in w if x not in {'jr', 'sr', 'ii', 'iii', 'iv', 'phd'}]
    return w[-1] if w and len(w[-1]) >= 2 else None


def byline_index(school):
    """lab paper bylines by work id, OpenAlex-keyed id, DOI and normalized title."""
    idx = {}
    p = P.data('lab_papers.jsonl.gz', school)
    if not p.exists():
        return idx
    for line in gzip.open(p, 'rt'):
        r = json.loads(line)
        names = r.get('byline') or r.get('byline_school') or []
        if not names:
            continue
        keys = [r.get('work'), f"{school}_oa_{(r.get('oa') or '').rsplit('/', 1)[-1]}", 'doi:' + ndoi(r.get('doi')), 't:' + nt(r.get('title'))]
        for k in keys:
            if k and k not in ('doi:', 't:'):
                idx.setdefault(k, names)
    # OpenAlex records the push holds for the school (hierarchy/<school>/pi-works.sqlite or raw/<school>-oa-works.sqlite) and
    # its single-work cache: authorships by OpenAlex id, DOI and normalized title
    def add(body):
        names = [((a or {}).get('author') or {}).get('display_name') or (a or {}).get('raw_author_name') or '' for a in body.get('authorships') or []]
        names = [n for n in names if n]
        if names:
            for k in ('oa:' + (body.get('id') or '').rsplit('/', 1)[-1], 'doi:' + ndoi(body.get('doi')), 't:' + nt(body.get('title'))):
                if k not in ('oa:', 'doi:', 't:'):
                    idx.setdefault(k, names)
    store = P.data('pi-works.sqlite', school)
    if not store.exists():
        store = P.FT_RAW / f'{school}-oa-works.sqlite'
    if store.exists():
        db = sqlite3.connect(f'file:{store}?mode=ro', uri=True, timeout=60)
        for _, b in db.execute('SELECT id, body FROM works'):
            try:
                add(json.loads(zlib.decompress(b)))
            except Exception:
                pass
        db.close()
    cache = P.FT_RAW / 'openalex_works.jsonl'
    if cache.exists():
        for line in cache.open():
            try:
                add(json.loads(line).get('body') or {})
            except Exception:
                pass
    return idx


def authors_of(row, bi):
    names, oa_ids = [], []
    graphs = []
    for blob in (row.get('graph_json'), row.get('oa_json')):
        try:
            g = json.loads(blob) if blob else {}
        except ValueError:
            g = {}
        if isinstance(g, dict):
            graphs.append(g)
            oa_ids.append('oa:' + str(g.get('openalex') or g.get('id') or '').rsplit('/', 1)[-1])
    for k in [row['id'], 'doi:' + ndoi(row['doi']), 't:' + nt(row['title'])] + oa_ids:
        if k in bi:
            names += bi[k]; break
    for g in graphs:
        for key, v in g.items():
            if key in ('authors', 'byline', 'byline_school', 'pis', 'author_names', 'creators') or key.endswith(('_faculty', '_students', '_postdocs')):
                if isinstance(v, list):
                    names += [x if isinstance(x, str) else (x.get('name') or x.get('display_name') or '') for x in v if x]
        for a in g.get('authorships') or []:
            names.append(((a or {}).get('author') or {}).get('display_name') or (a or {}).get('raw_author_name') or '')
        for key in g.get('dblp') or []:  # a DBLP record key starts with the first author's family name (journals/corr/HeckelSRW16)
            m = re.match(r'([A-Z][a-z]{2,})(?=[A-Z]|\d)', str(key).rsplit('/', 1)[-1])
            if m:
                names.append(m.group(1))
    fams = []
    for n in names:
        f = family(n)
        if f and f not in fams:
            fams.append(f)
    return fams


def pdftext(path, first, last):
    try:
        return subprocess.run(['pdftotext', '-q', '-f', str(first), '-l', str(last), str(path), '-'], capture_output=True, text=True,
                              timeout=60, errors='replace').stdout
    except Exception:
        return ''


def arxiv_from(row):
    d = ndoi(row['doi'])
    if d.startswith('10.48550/arxiv.'):
        return d.split('arxiv.', 1)[1]
    return None


COMMON_WORD_SURNAMES = set('''he an so do to in on or as be by us we it is of at no me my long young white brown black green hill price bell case
page cook strong may will best wise hard rich small little short rose park bond king law love hope field wood stone cross fair good grace
gray grey hall hunt knight lane light major mark mason miller moon north west east south power ray reed rice rule sharp snow summer wall
ward waters wells wolf fox bird day dean early frank free game gross guy hand hart house judge kind land low more new noble pace post
read rock root sage salt sand sun wing word work chen? '''.split()) - {'chen?'}
ROMAN = set('ii iii iv vi vii viii ix xi xii xiii xiv xv xvi xvii xviii xix xx xxi xxii xxiii xxiv xxv xxvi xxvii xxviii xxix xxx'.split())
ENGLISH = set('the of and to in a is for we that on with are this by as be from an which our it can'.split())  # readable-text probe
SCRATCH = Path('/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/identity-text')


def extract(row, store, bi):
    path = store / row['file_path']
    r = {k: row[k] for k in ('id', 'title', 'doi', 'year', 'file_path', 'sha256', 'download_url', 'graph_json', 'oa_json')}
    r['p1'] = pdftext(path, 1, 1)
    r['p13'] = pdftext(path, 1, 3)
    return r


def score(r):
    p1, p13 = r['p1'], r['p13']
    tw = [w for w in words(r['title']) if w not in STOP]
    tset = set(tw)
    w1, w3 = words(p1), words(p13)
    s1, s3 = set(w1), set(w3)
    recall1 = len(tset & s1) / len(tset) if tset else 0.0
    recall3 = len(tset & s3) / len(tset) if tset else 0.0
    tnorm = ' '.join(words(r['title']))
    head1 = ' '.join(w1[:400])
    fz1 = fuzz.partial_ratio(tnorm, head1) if tnorm and head1 else 0.0
    fz3 = fuzz.partial_ratio(tnorm, ' '.join(w3[:1500])) if tnorm and w3 else 0.0
    fams = authors_of(r, BI)
    a1 = [f for f in fams if f in s1]
    a3 = [f for f in fams if f in s3]
    distinct = [f for f in fams if f not in COMMON_WORD_SURNAMES and len(f) >= 3]
    d1 = [f for f in distinct if f in s1]
    ax = arxiv_from(r)
    url_ax = re.search(r'(\d{4}\.\d{4,5})(?:v\d+)?', r['download_url'] or '')
    exact_arxiv = bool(ax and url_ax and url_ax.group(1) == ax)
    found_ax = re.search(r'arXiv:(\d{4}\.\d{4,5})', p13[:3000] or '')
    eng3 = sum(1 for w in w3 if w in ENGLISH) / max(1, len(w3))
    # words outside repeated lines (a header or license line printed on every page, as bioRxiv's on an image-only PDF)
    lines = [l.strip() for l in p13.splitlines() if l.strip()]
    seen = {}
    for l in lines:
        seen[l] = seen.get(l, 0) + 1
    body3 = len(words(' '.join(l for l in lines if seen[l] == 1 and not re.search(r'preprint doi|copyright holder|license to display|available under', l, re.I))))
    tw_all = words(r['title'])
    marks = {w for w in tw_all if w.isdigit()} | {tw_all[i + 1] for i, w in enumerate(tw_all[:-1]) if w == 'part'}
    head = set(w1[:150])
    missing_marks = sorted(m for m in marks if m not in head)
    # a series title cut short in the catalog ('Planck 2015 results' for 'Planck 2015 results. XIII. Cosmological parameters')
    hs = ' ' + ' '.join(w1[:150]) + ' '
    k = hs.find(' ' + ' '.join(tw_all) + ' ') if tw_all else -1
    nxt = hs[k + len(' '.join(tw_all)) + 2:].split()[:1] if k >= 0 else []
    if nxt and (nxt[0] in ROMAN or nxt[0] == 'part'):
        missing_marks.append('series continues: ' + nxt[0])
    return dict(id=r['id'], title=r['title'], doi=r['doi'], file_path=r['file_path'], sha256=r['sha256'], year=r['year'],
                download_url=r['download_url'], chars1=len(p1.strip()), chars3=len(p13.strip()), title_tokens=len(tset),
                words1=len(w1), words3=len(w3), body_words3=body3, english3=round(eng3, 3), missing_marks=missing_marks,
                recall1=round(recall1, 3), recall3=round(recall3, 3), fuzz1=round(fz1, 1), fuzz3=round(fz3, 1),
                authors=fams[:12], n_authors=len(fams), author_hits1=a1, author_hits3=a3, n_distinct=len(distinct), distinct_hits1=d1,
                exact_arxiv=exact_arxiv, arxiv_on_page=found_ax.group(1) if found_ax else None, excerpt=re.sub(r'\s+', ' ', p1)[:900])


def strong_authors(s):
    """distinctive family names (not common English words, >= 3 letters) on page 1: 3 or more, or at least 60 % of them."""
    nd, d1 = s['n_distinct'], len(s['distinct_hits1'])
    return nd > 0 and (d1 >= 3 or d1 >= max(1, -(-6 * min(nd, 10) // 10)))


def verdict(s):
    """-> (verdict, reason, new identity value)."""
    if s['chars3'] < 200:
        return 'review', 'no extractable text on pages 1-3 (scanned or image PDF)', None
    na, a1, a3 = s['n_authors'], len(s['author_hits1']), len(s['author_hits3'])
    tt = s['title_tokens']
    if s['arxiv_on_page'] and arxiv_from(s) and s['arxiv_on_page'] != arxiv_from(s):
        return 'review', f"arXiv id on page {s['arxiv_on_page']} differs from catalog", None
    hits = ', '.join(s['author_hits1'][:5]) or 'none listed'
    short = s['words1'] < 120 or re.search(r'\bjoint work with\b|\bsupplementa(?:ry|l) (?:material|information|document)\b', s['excerpt'][:400], re.I)
    if short:  # slides, a poster, a cover sheet or a supplement can carry the title and authors: never confirmed automatically
        if tt >= 3 and not s['exact_arxiv'] and s['chars1'] >= 200 and na >= 1 and s['body_words3'] >= 150 and s['english3'] >= 0.08 \
                and s['fuzz3'] <= REJECT_FUZZ and s['recall3'] <= REJECT_RECALL and a3 == 0:
            return 'reject', f"pages 1-3 carry neither the title (fuzzy {s['fuzz3']}, token recall {s['recall3']}) nor any of {na} author names", None
        return 'review', f"page 1 is short ({s['words1']} words) or reads as slides / supplement: not confirmed automatically", None
    if s['missing_marks'] and not s['exact_arxiv']:  # 'A 2022 Report' vs 'A 2023 Report', 'Part I' vs 'Part II'
        return 'review', f"title numbers / part labels not on page 1: {', '.join(s['missing_marks'])}", None
    if tt >= 3 and s['fuzz1'] >= CONFIRM_FUZZ and s['recall1'] >= CONFIRM_RECALL and (a1 >= 1 or (na == 0 and s['fuzz1'] >= 97 and tt >= 5)):
        return 'confirm', f"title on page 1 (fuzzy {s['fuzz1']}, token recall {s['recall1']}); authors on page 1: {hits}", CONFIRMED
    if 0 < tt < 3 and s['fuzz1'] == 100 and s['recall1'] == 1 and strong_authors(s):
        return 'confirm', f"short title on page 1 with {len(s['distinct_hits1'])} of {s['n_distinct']} distinctive author names: {hits}", CONFIRMED
    if s['exact_arxiv'] and strong_authors(s) and s['recall1'] >= 0.5:
        return 'confirm', f"exact arXiv identifier in the download URL; {len(s['distinct_hits1'])} of {s['n_distinct']} distinctive author names on page 1; title variant (recall {s['recall1']})", CONFIRMED_ARXIV
    if tt >= 3 and s['fuzz1'] >= 85 and s['recall1'] >= 0.7 and len(s['distinct_hits1']) >= 2 and strong_authors(s):
        return 'confirm', f"title variant on page 1 (fuzzy {s['fuzz1']}, token recall {s['recall1']}); {len(s['distinct_hits1'])} of {s['n_distinct']} distinctive author names on page 1: {hits}", CONFIRMED_VARIANT
    # a reject needs readable English text: a broken font encoding (shifted glyphs: '&RQFHQWULF' for 'Concentric') or a
    # non-English page would otherwise look like a different paper
    if tt >= 3 and not s['exact_arxiv'] and s['chars1'] >= 200 and na >= 1 and s['body_words3'] >= 150 and s['english3'] >= 0.08:
        if s['fuzz3'] <= REJECT_FUZZ and s['recall3'] <= REJECT_RECALL and a3 == 0:
            return 'reject', f"pages 1-3 carry neither the title (fuzzy {s['fuzz3']}, token recall {s['recall3']}) nor any of {na} author names", None
        if s['fuzz3'] <= 45 and s['recall3'] <= 0.25 and na >= 3 and a3 <= 1:
            return 'reject', f"pages 1-3 do not carry the title (fuzzy {s['fuzz3']}, token recall {s['recall3']}); only {a3} of {na} author names", None
    return 'review', 'uncertain', None


def load_pending(school):
    store = STORES / school
    db = sqlite3.connect(f'file:{store / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
    db.row_factory = sqlite3.Row
    rows = [dict(r) for r in db.execute("SELECT id, title, doi, year, graph_json, oa_json, file_path, sha256, download_url FROM works "
                                         "WHERE status='downloaded' AND identity_check=?", (PENDING,))]
    db.close()
    return store, rows


def cmd_extract(school, workers):
    """pending rows' page texts -> scratchpad cache (re-scoring needs no second pass over the PDFs)."""
    store, rows = load_pending(school)
    bi = byline_index(school)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    t = time.time()
    with ThreadPoolExecutor(workers) as pool, gzip.open(SCRATCH / f'{school}.jsonl.gz', 'wt') as f:
        for r in pool.map(lambda r: extract(r, store, bi), rows):
            f.write(json.dumps(r) + '\n')
    print(json.dumps(dict(school=school, pending=len(rows), extract_seconds=round(time.time() - t))), flush=True)


def cmd_meta(school):
    """add graph_json / oa_json to a text cache written before extract() kept them."""
    _, rows = load_pending(school)
    meta = {r['id']: r for r in rows}
    src = SCRATCH / f'{school}.jsonl.gz'
    tmp = SCRATCH / f'{school}.jsonl.gz.tmp'
    n = 0
    with gzip.open(src, 'rt') as f, gzip.open(tmp, 'wt') as g:
        for line in f:
            r = json.loads(line)
            m = meta.get(r['id'])
            if m:
                r['graph_json'], r['oa_json'] = m['graph_json'], m['oa_json']; n += 1
            r.pop('authors', None)
            g.write(json.dumps(r) + '\n')
    tmp.replace(src)
    print(json.dumps(dict(school=school, cache_rows_with_meta=n)), flush=True)


BI = {}


def cmd_score(school):
    BI.update(byline_index(school))
    OUT.mkdir(exist_ok=True)
    from collections import Counter
    c = Counter()
    with gzip.open(SCRATCH / f'{school}.jsonl.gz', 'rt') as src, open(OUT / f'scores-{school}.jsonl', 'w') as f:
        for line in src:
            s = score(json.loads(line))
            v, why, val = verdict(s)
            s.update(verdict=v, reason=why, new_identity=val)
            c[v] += 1
            f.write(json.dumps(s) + '\n')
    print(json.dumps(dict(school=school, **c)), flush=True)


def connect_rw(store):
    db = sqlite3.connect(str(store / 'catalog.sqlite'), timeout=120)
    db.execute('PRAGMA busy_timeout=120000')
    return db


def by_lab_links(store, school):
    """{(year, work id) -> [link path]} of the store's by_lab/<lab>/<year>--<id>.pdf links, read one directory level deep."""
    out = {}
    root = store / 'by_lab'
    if not root.is_dir():
        return out
    for d in root.iterdir():
        if not d.is_dir():
            continue
        for e in d.iterdir():
            if e.name.endswith('.pdf') and '--' in e.name:
                out.setdefault(e.name, []).append(e)
    return out


def cmd_apply(school, only_ids=None):
    store = STORES / school
    scores = [json.loads(l) for l in open(OUT / f'scores-{school}.jsonl')]
    todo = [s for s in scores if s['verdict'] in ('confirm', 'reject') and (only_ids is None or s['id'] in only_ids)]
    db = connect_rw(store)
    log = open(OUT / f'{school}.jsonl', 'a')
    links = None
    n = {'confirmed': 0, 'rejected': 0, 'skipped_changed': 0}
    for i in range(0, len(todo), 200):
        part = todo[i:i + 200]
        recs = []
        for attempt in range(30):
            try:
                recs = []
                for s in part:
                    w = s['id']
                    if s['verdict'] == 'confirm':
                        c = db.execute("UPDATE works SET identity_check=? WHERE id=? AND status='downloaded' AND identity_check=? AND sha256=?",
                                       (s['new_identity'], w, PENDING, s['sha256'])).rowcount
                        if not c:
                            recs.append(dict(id=w, kind='identity', skipped='row changed since scoring')); continue
                        db.execute("UPDATE assets SET identity_check=? WHERE work_id=? AND kind='pdf' AND sha256=?", (s['new_identity'], w, s['sha256']))
                        db.execute('INSERT INTO attempts(work_id,url,observed_at,status,detail) VALUES (?,?,?,?,?)',
                                   (w, s['download_url'], now(), 'identity_rechecked', s['new_identity'] + ': ' + s['reason']))
                        recs.append(dict(id=w, kind='identity', old=dict(status='downloaded', identity_check=PENDING),
                                         new=dict(status='downloaded', identity_check=s['new_identity']), reason=s['reason'],
                                         score=dict(fuzz1=s['fuzz1'], recall1=s['recall1'], author_hits1=s['author_hits1'])))
                    else:
                        c = db.execute("UPDATE works SET status='queued',file_path=NULL,sha256=NULL,byte_count=NULL,pages=NULL,download_url=NULL,"
                                       "downloaded_at=NULL,identity_check=NULL WHERE id=? AND status='downloaded' AND identity_check=? AND sha256=?",
                                       (w, PENDING, s['sha256'])).rowcount
                        if not c:
                            recs.append(dict(id=w, kind='identity', skipped='row changed since scoring')); continue
                        db.execute("UPDATE OR IGNORE assets SET kind='identity_mismatch_pdf',identity_check='identity_mismatch_first_page_review' "
                                   "WHERE work_id=? AND kind='pdf' AND sha256=?", (w, s['sha256']))
                        db.execute('INSERT INTO attempts(work_id,url,observed_at,status,detail) VALUES (?,?,?,?,?)',
                                   (w, s['download_url'], now(), 'identity_mismatch', 'review-20261029: ' + s['reason']))
                        if db.execute("SELECT 1 FROM assets WHERE work_id=? AND kind='xml'", (w,)).fetchone():
                            db.execute("UPDATE works SET status='fulltext_xml' WHERE id=? AND status='queued'", (w,))  # its JATS copy still stands
                        others = db.execute('SELECT COUNT(*) FROM works WHERE sha256=? AND id<>?', (s['sha256'], w)).fetchone()[0]
                        recs.append(dict(id=w, kind='identity', old=dict(status='downloaded', identity_check=PENDING, sha256=s['sha256'], file_path=s['file_path']),
                                         new=dict(status='queued', identity_check=None), reason=s['reason'],
                                         score=dict(fuzz3=s['fuzz3'], recall3=s['recall3'], author_hits3=s['author_hits3'], n_authors=s['n_authors']),
                                         object_kept=True, other_works_with_sha=others))
                db.commit(); break
            except sqlite3.OperationalError as e:
                db.rollback(); print(json.dumps(dict(retry=str(e))), flush=True); time.sleep(20)
        else:
            raise RuntimeError('catalog stayed locked')
        for r in recs:
            r['at'] = now()
            if 'skipped' in r:
                n['skipped_changed'] += 1
            elif r['new']['status'] == 'queued':
                n['rejected'] += 1
                if links is None:
                    links = by_lab_links(store, school)
                s = next(x for x in part if x['id'] == r['id'])
                for p in links.get(f"{s['year']}--{r['id']}.pdf", []):
                    if p.is_symlink() and p.resolve() == (store / s['file_path']).resolve():
                        p.unlink(); r.setdefault('links_removed', []).append(str(p))
            else:
                n['confirmed'] += 1
            log.write(json.dumps(r) + '\n')
        log.flush()
        time.sleep(0.3)
    db.close(); log.close()
    print(json.dumps(dict(school=school, **n)), flush=True)


if __name__ == '__main__':
    cmd, school = sys.argv[1], sys.argv[2]
    workers = int(sys.argv[sys.argv.index('--workers') + 1]) if '--workers' in sys.argv else 8
    if cmd == 'meta':
        cmd_meta(school)
    elif cmd == 'extract':
        cmd_extract(school, workers)
    elif cmd == 'score':
        cmd_score(school)
    elif cmd == 'apply':
        cmd_apply(school)
