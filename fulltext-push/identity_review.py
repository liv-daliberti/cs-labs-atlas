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
usage: identity_review.py plan|apply <school> ... [--all-pending]
       --all-pending: every downloaded catalog work still pending (lab papers, their siblings and the rest of the catalog,
       which the full-text studies read); the first author then comes from the work's graph when no lab paper names it
       --reverted: the copies the round-1 review reverted under the earlier rule, judged again (pass -> restored confirmed,
       undecided -> restored pending, fail -> stays reverted)
"""
import json, re, sqlite3, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ftp_common as F  # noqa: E402
import identity_rule as R  # noqa: E402  (the rule itself, shared with the collector wrapper)

OUT = HERE / 'review-20261030'
SUFFIX = {'lab': '', 'all': '-all', 'reverted': '-reverted'}
PENDING = R.PENDING



def catalog_pending(school, db, lab_ids):
    """Every downloaded catalog work still at the pending identity, lab-related or not (the full-text studies read the
    whole catalog), with its kind: lab (a lab paper's own work), sibling (a work sharing its DOI / title) or other."""
    copies = json.loads((F.SCHOOLS / 'hierarchy' / school / 'copies.json').read_text())['papers']
    cids = {c.get('catalog') for c in copies.values()}
    ids = [i for i, ic, st in F.works_rows(db, 'id, identity_check, status') if ic == PENDING and st == 'downloaded']
    rows = {}
    for k in range(0, len(ids), 500):
        part = ids[k:k + 500]
        q = ','.join('?' * len(part))
        for i, fp, sha, du, yr, g in db.execute(f'SELECT id, file_path, sha256, download_url, year, graph_json FROM works WHERE id IN ({q})', part):
            rows[i] = dict(id=i, file_path=fp, sha256=sha, download_url=du, year=yr, attempt_urls=[], graph=g,
                           kind='lab' if i in cids else ('sibling' if i in lab_ids else 'other'))
        for w, u in db.execute(f"SELECT work_id, url FROM attempts WHERE work_id IN ({q}) AND status='downloaded'", part):
            rows[w]['attempt_urls'].append(u)
    return rows



def reverted_rows(school):
    """The copies the round-1 automatic review (2026-10-31, the earlier rule) reverted, whose file is still in objects/
    and whose work is still reverted: the fixed rule judges them again."""
    store = F.FT / school
    recs = {}
    log = store / 'staged' / 'reverted-downloads.jsonl'
    for line in open(log) if log.exists() else []:
        r = json.loads(line)
        if str(r.get('reason', '')).startswith('automatic identity review 2026-10-31') and 'before' in r:
            recs[r['work']] = r
    db = sqlite3.connect(f'file:{store / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
    rows = {}
    for w, r in recs.items():
        cur = db.execute('SELECT status FROM works WHERE id=?', (w,)).fetchone()
        b = r['before']
        if not cur or cur[0] not in ('needs_access_review', 'queued') or not b.get('file_path') or not (store / b['file_path']).exists():
            continue
        rows[w] = dict(id=w, file_path=b['file_path'], sha256=b.get('sha256'), download_url=b.get('download_url'), year=b.get('year'),
                       attempt_urls=[r['url']], kind='reverted_round1', revert=r)
    db.close()
    return rows, len(recs)


def plan(school, scope='lab'):
    import shutil
    if not shutil.which('pdftotext'):  # without it every copy would fail the check
        raise SystemExit('pdftotext is not on PATH: identity review not run')
    sys.path.insert(0, str(HERE))
    from quarantine_robots_ai import lab_local_works
    store = F.FT / school
    rows = lab_local_works(school)
    papers = F.lab_papers(school)
    if scope == 'all':
        dbr = sqlite3.connect(f'file:{store / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
        rows = catalog_pending(school, dbr, set(rows))
        dbr.close()
    elif scope == 'reverted':
        rows, n_logged = reverted_rows(school)
        print(json.dumps(dict(school=school, reverted_round1_logged=n_logged, files_still_present_and_reverted=len(rows))), flush=True)
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
        if scope == 'reverted':
            ic = PENDING  # judged again from the file the revert left in objects/
        if ic != PENDING or not row['file_path'] or not row['file_path'].endswith('.pdf'):
            continue
        r = by_id.get(w) or by_doi.get(F.ndoi(doi)) or by_t.get(F.nt(title)) or {}
        p1, p12 = R.page_text(store / row['file_path'], 1, 1), R.page_text(store / row['file_path'], 1, 2)
        first, auth = R.first_author(F.SCHOOLS, school, w, title, doi, graph_json=row.get('graph'), catalog=store / 'catalog.sqlite')
        d = F.ndoi(doi or r.get('doi'))
        import s2_key_lookup as s2k
        mapped = R.mapped_arxiv(d, s2k.CACHE, HERE / 'raw' / 'ledger_openalex.jsonl', r.get('oa'))
        verdict, ev = R.judge(p1, title, first, d, row['download_url'], mapped, p12=p12, author_authoritative=auth)
        n[verdict] += 1
        out.append(dict(work=w, kind=row.get('kind', 'lab'), verdict=verdict, title=title, **ev, url=(row['attempt_urls'] or [row['download_url']])[0],
                        download_url=row['download_url'], page1=re.sub(r'\s+', ' ', p1)[:400], revert=row.get('revert')))
    db.close()
    OUT.mkdir(exist_ok=True)
    (OUT / f'identity-review{SUFFIX[scope]}-{school}.json').write_text(json.dumps(dict(school=school, at=F.now(), scope=scope, rows=out), indent=0))
    print(json.dumps(dict(school=school, scope=scope, pending=len(out), by_kind=dict(Counter(x['kind'] for x in out)), **n)), flush=True)


def apply(school, scope='lab'):
    from revert_downloads import revert
    store = F.FT / school
    rows = json.loads((OUT / f'identity-review{SUFFIX[scope]}-{school}.json').read_text())['rows']
    if scope == 'reverted':  # passes come back confirmed, undecided ones come back pending (not counted), failures stay reverted
        from revert_downloads import restore
        n = Counter()
        for x in rows:
            if x['verdict'] == 'fail':
                n['still_reverted'] += 1; continue
            ident = R.TAGS.get(x['verdict'], PENDING)
            r = restore(school, x['work'], x['revert'], ident, f"identity rule fixed 2026-10-31: {x['verdict']}")
            n['skipped' if 'skipped' in r else ('restored_confirmed' if ident != PENDING else 'restored_pending')] += 1
        print(json.dumps(dict(school=school, scope=scope, **n)), flush=True)
        return
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
            r = revert(school, x['work'], x['url'], 'automatic identity review 2026-10-31: ' + R.reason(x))
            n['reverted' if 'skipped' not in r else 'revert_skipped'] += 1
    print(json.dumps(dict(school=school, **n)), flush=True)


if __name__ == '__main__':
    scope = 'all' if '--all-pending' in sys.argv else ('reverted' if '--reverted' in sys.argv else 'lab')
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    cmd, schools = args[0], args[1:]
    for s in schools:
        {'plan': plan, 'apply': apply}[cmd](s, scope)
