"""Automatic identity review of lab-paper copies the collector accepted as 'provider_link_only_review_pending' (its title
check found neither the catalog title nor the DOI in the first three pages; 2026-10-31, owner).

A copy passes when
  title   at least 80% of the catalog title's significant words (>= 3 of them) are in the title region of page 1 (its
          first 600 characters; a title broken across lines, hyphenated or with ligatures still matches), AND the first
          author's family name (the lab paper's byline; letters only) or the DOI is on page 1; or
  arxiv   page 1 carries the arXiv stamp of the very arXiv id the copy was downloaded as, Semantic Scholar or OpenAlex
          maps the work's DOI to that arXiv id (an identifier match, for preprints whose title changed), and the first
          author's family name is on page 1.
plan   -> fulltext-push/review-20261030/identity-review-<school>.json (verdict, evidence, page-1 excerpt per work)
apply  passes: works.identity_check = 'auto_title_author_page1_20261031' / 'auto_arxiv_id_doi_mapping_20261031';
       failures: revert_downloads.revert (back to needs_access_review, the download's attempt marked identity_mismatch)
usage: identity_review.py plan|apply <school> ...
"""
import json, re, sqlite3, subprocess, sys, unicodedata
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ftp_common as F  # noqa: E402

OUT = HERE / 'review-20261030'
PENDING = 'provider_link_only_review_pending'
STOP = set('a an the of for and in on to with via from by at is are as its into using toward towards over under through '
           'what when how why which this that these those can be we our or not'.split())


def norm_words(t):
    t = unicodedata.normalize('NFKD', t or '').encode('ascii', 'ignore').decode().lower()
    t = t.replace('ﬁ', 'fi').replace('ﬂ', 'fl')
    return re.findall(r'[a-z0-9]+', t)


def fam(name):
    name = unicodedata.normalize('NFKD', name or '').encode('ascii', 'ignore').decode().lower()
    if ',' in name:
        return re.sub(r'[^a-z]', '', name.split(',', 1)[0])
    toks = [t for t in re.sub(r'[^a-z \-]', ' ', name).split() if t not in {'jr', 'sr', 'ii', 'iii', 'iv'}]
    return re.sub(r'[^a-z]', '', toks[-1]) if toks else ''


def text(path, first, last):
    try:
        return subprocess.run(['pdftotext', '-f', str(first), '-l', str(last), str(path), '-'], capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return ''


def s2_arxiv(doi, cache={}):
    if not cache:
        import s2_key_lookup as s2k
        for line in open(s2k.CACHE):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            d = r.get('data') or {}
            a = (d.get('externalIds') or {}).get('ArXiv') if isinstance(d, dict) else None
            if a and r['id'].startswith('DOI:'):
                cache[r['id'][4:].lower()] = a
        cache['_'] = 1
    return cache.get((doi or '').lower())


def oa_arxiv(oa_id, cache={}):
    if not cache:
        p = HERE / 'raw' / 'ledger_openalex.jsonl'
        if p.exists():
            for line in open(p):
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get('body'):
                    a = F.arxiv_of({}, r['body'])
                    if a:
                        cache[r['id']] = a
        cache['_'] = 1
    return cache.get(oa_id)


def plan(school):
    import shutil
    if not shutil.which('pdftotext'):  # without it every copy would fail the check
        raise SystemExit('pdftotext is not on PATH: identity review not run')
    sys.path.insert(0, str(HERE))
    from quarantine_robots_ai import lab_local_works
    store = F.FT / school
    rows = lab_local_works(school)
    papers = F.lab_papers(school)
    by_doi, by_t, by_id = {}, {}, {}
    for k, r in papers.items():
        if r.get('work'):
            by_id.setdefault(r['work'], r)
        by_id.setdefault(F.oa_work_id(school, r), r)
        if F.ndoi(r.get('doi')):
            by_doi.setdefault(F.ndoi(r['doi']), r)
        by_t.setdefault(F.nt(r.get('title')), r)
    db = sqlite3.connect(f'file:{store / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
    out, n = [], Counter()
    for w, row in rows.items():
        ic, title, doi = db.execute('SELECT identity_check, title, doi FROM works WHERE id=?', (w,)).fetchone()
        if ic != PENDING or not row['file_path'] or not row['file_path'].endswith('.pdf'):
            continue
        r = by_id.get(w) or by_doi.get(F.ndoi(doi)) or by_t.get(F.nt(title)) or {}
        path = store / row['file_path']
        p1 = text(path, 1, 1)
        # the title region: the first 600 characters of page 1 (arXiv stamp, venue line, title, authors). On the whole of
        # pages 1-3 the title's words also turn up in the abstract of another paper (a Princeton sample, 2026-10-31).
        head = set(norm_words(re.sub(r'\s+', ' ', p1)[:600]))
        letters1 = re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', p1[:4000]).encode('ascii', 'ignore').decode().lower())
        tw = [x for x in norm_words(title) if len(x) >= 3 and x not in STOP]
        frac = sum(x in head for x in tw) / max(1, len(tw))
        first = fam((r.get('byline') or [''])[0]) or (fam((r.get('pis') or [''])[0]) if not r.get('byline') else '')
        # letters only ('Chudnovsky1', 'Simmons-Edler' match); a two-letter family name (Wu, So, Li) as a whole word
        author_ok = (len(first) >= 3 and first in letters1) or (len(first) == 2 and first in set(norm_words(p1)))
        d = F.ndoi(doi or r.get('doi'))
        doi_ok = bool(d) and d in p1.lower()
        title_ok = (len(tw) >= 3 and frac >= 0.8) or (1 <= len(tw) < 3 and frac == 1.0 and author_ok)  # a short title: every word
        stamp = re.search(r'arXiv:(\d{4}\.\d{4,5})', p1)
        url_ax = re.search(r'(\d{4}\.\d{4,5})(?:v\d+)?\.pdf', row['download_url'] or '')
        mapped = s2_arxiv(d) or oa_arxiv(r.get('oa'))
        mapped = re.sub(r'v\d+$', '', mapped) if mapped else None
        arxiv_ok = bool(stamp and url_ax and stamp.group(1) == url_ax.group(1) == mapped and author_ok)
        verdict = 'pass_title' if title_ok and (author_ok or doi_ok) else ('pass_arxiv' if arxiv_ok else 'fail')
        n[verdict] += 1
        out.append(dict(work=w, verdict=verdict, title=title, first_author=first, title_words_found=round(frac, 2), author_on_page1=author_ok,
                        doi_on_page1=doi_ok, arxiv_stamp=stamp.group(1) if stamp else None, arxiv_mapped=mapped, url=(row['attempt_urls'] or [row['download_url']])[0],
                        download_url=row['download_url'], page1=re.sub(r'\s+', ' ', p1)[:400]))
    db.close()
    OUT.mkdir(exist_ok=True)
    (OUT / f'identity-review-{school}.json').write_text(json.dumps(dict(school=school, at=F.now(), rows=out), indent=0))
    print(json.dumps(dict(school=school, pending=len(out), **n)), flush=True)


def apply(school):
    from revert_downloads import revert
    store = F.FT / school
    rows = json.loads((OUT / f'identity-review-{school}.json').read_text())['rows']
    db = sqlite3.connect(str(store / 'catalog.sqlite'), timeout=120)
    db.execute('PRAGMA busy_timeout=120000')
    n = Counter()
    for x in rows:
        if x['verdict'].startswith('pass'):
            tag = 'auto_title_author_page1_20261031' if x['verdict'] == 'pass_title' else 'auto_arxiv_id_doi_mapping_20261031'
            n['confirmed'] += db.execute("UPDATE works SET identity_check=? WHERE id=? AND identity_check=?", (tag, x['work'], PENDING)).rowcount
            db.execute("UPDATE assets SET identity_check=? WHERE work_id=? AND identity_check=?", (tag, x['work'], PENDING))
            db.commit()
    db.close()
    for x in rows:
        if x['verdict'] == 'fail':
            r = revert(school, x['work'], x['url'], f"automatic identity review 2026-10-31: {x['title_words_found']:.0%} of the title's words in pages 1-3, "
                                                      f"first author {'on' if x['author_on_page1'] else 'not on'} page 1, DOI {'on' if x['doi_on_page1'] else 'not on'} page 1")
            n['reverted' if 'skipped' not in r else 'revert_skipped'] += 1
    print(json.dumps(dict(school=school, **n)), flush=True)


if __name__ == '__main__':
    cmd, schools = sys.argv[1], sys.argv[2:]
    for s in schools:
        {'plan': plan, 'apply': apply}[cmd](s)
