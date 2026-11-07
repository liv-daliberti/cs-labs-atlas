"""Experiment B step 2: v1 and final-version texts of the matched arXiv papers, from arXiv's public cloud mirror (storage.googleapis.com), never arxiv.org.

  rv_fetch.py plan [--max-a N --max-s N] choose the pairs -> DATA/revision.sqlite `plan` (kind S: v1 vs the stored copy; kind A: v1 vs the bucket's latest version), capped per cell
  rv_fetch.py chunk <task> <of>          one array task: downloads, extracts and stores its share of the plan in resumable chunks of CHUNK pairs
  rv_fetch.py merge                      chunk files -> DATA/revision.sqlite `texts`
Extraction is the stores' own (vendor fulltext_store: pdftotext 60 pages; the intro/body to the last References heading, <= 300,000 characters), so a
version's body is built exactly as the lab-paper bodies the detector scored. The version's date is the margin stamp on page 1 ('arXiv:ID vN [cs.LG] 12 Oct 2021');
without a stamp the version's date is unknown (v1: the OAI record's `created`; final: left empty and the pair is dropped from the date contrasts).
Table plan(arxiv_id, paper_id, kind, n_versions, final_v, created, final_created_ub, cell, title, pub_date; PK arxiv_id+kind);
texts(arxiv_id, role 'v1'|'final', v, stamp_v, date, title_found, abstract, body blob zlib, words, flags, pdf_bytes, PRIMARY KEY (arxiv_id, role)).
"""
import argparse
import hashlib
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

import rv_common as C

sys.path.append(str(C.P.vendor('homogenization_tools')))
CHUNK = int(os.environ.get('RV_CHUNK', '200'))
THREADS = 4
ABS_START = re.compile(r'^[ \t]*a\s?b\s?s\s?t\s?r\s?a\s?c\s?t\b[ \t.:\-—–]*', re.I | re.M)
ABS_END = re.compile(r'^[ \t]*(?:(?:\d+|I|1)[.:]?[ \t]+)?(?:introduction|keywords?|index terms|ccs concepts|categories and subject descriptors)\b', re.I | re.M)


def scratch():
    return C.P.SCRATCH / 'rv-fetch'


def abstract_of(raw):
    t = raw.replace('\x0c', '\n')[:12000]
    m = ABS_START.search(t)
    if not m:
        return None
    e = ABS_END.search(t, m.end())
    a = t[m.end():e.start() if e else m.end() + 2500]
    a = re.sub(r'-\n(?=[a-z])', '', a)
    a = ' '.join(a.split())[:3500]
    return a if len(a.split()) >= 40 else None


def cell_of(created, final_date):
    """'pre_pre' (v1 and final before 1 Dec 2022), 'pre_post' (the key contrast), 'post_post'."""
    a = created < C.CHATGPT
    b = (final_date or '') < C.CHATGPT
    return ('pre' if a else 'post') + '_' + ('pre' if b else 'post')


def cmd_plan(max_a, max_s, seed=20261105):
    """Two pair kinds. S: arXiv v1 (bucket) against the lab paper's STORED copy (texts.sqlite fulltext, scored by the dose study; the version the stores captured, dated by the
    paper's publication date) - the only source of a final text after Dec 2022, because the bucket does not hold late revisions of old papers (listing check, see the report).
    A: arXiv v1 against the bucket's latest arXiv version (revisions made within weeks of v1)."""
    import rv_match as M
    db = M.connect()
    db.execute('drop table if exists plan')
    db.execute('create table plan (arxiv_id text, paper_id text, kind text, n_versions int, final_v int, created text, final_created_ub text, cell text, title text, pub_date text, '
               'primary key (arxiv_id, kind))')
    db.execute(f"attach '{C.P.AI_SCORES / 'ai_scores.sqlite'}' as s")
    db.execute(f"attach '{C.UNIVERSE_DB}' as u")
    rng = np.random.default_rng(seed)
    s_rows = db.execute('select m.paper_id, m.arxiv_id, m.created, m.arxiv_title, up.date, coalesce(v.n_versions, 0) from matches m join s.papers sp using (paper_id) '
                        'join u.papers up using (paper_id) left join versions v using (arxiv_id) where sp.n_passages >= 10 and up.year between 2016 and 2025 and m.created >= "2016-01-01" '
                        'and (v.n_versions is null or v.n_versions >= 1) order by m.arxiv_id').fetchall()
    seen, plan_s = set(), []
    for pid, aid, created, title, pub, nv in s_rows:
        if aid in seen or not pub:
            continue
        seen.add(aid)
        cell = ('pre' if created < C.CHATGPT else 'post') + '_' + ('pre' if pub < '2022-12-01' else 'post')
        plan_s.append((aid, pid, 'S', nv, None, created, None, cell, title, pub))
    keep = []
    for name in sorted({r[7] for r in plan_s}):
        rs = [r for r in plan_s if r[7] == name]
        quota = len(rs) if (name == 'pre_post' or max_s is None) else min(len(rs), max_s)
        keep += [rs[i] for i in sorted(rng.permutation(len(rs))[:quota])]
    a_rows = db.execute('select m.paper_id, m.arxiv_id, m.created, m.arxiv_title, v.n_versions, up.date from matches m join versions v using (arxiv_id) join u.papers up using (paper_id) '
                        'where v.n_versions >= 2 and m.created >= "2016-01-01" and up.year between 2016 and 2025 order by m.arxiv_id').fetchall()
    tc = {(x, n): t for x, n, t in db.execute('select arxiv_id, v, time_created from version_list')}
    seen_a, plan_a = set(), []
    for pid, aid, created, title, n, pub in a_rows:
        if aid in seen_a:
            continue
        seen_a.add(aid)
        ub = (tc.get((aid, n)) or '')[:10]
        plan_a.append((aid, pid, 'A', n, n, created, ub, ('pre' if created < C.CHATGPT else 'post') + '_' + ('pre' if ub < C.CHATGPT else 'post'), title, pub))
    for name in sorted({r[7] for r in plan_a}):
        rs = [r for r in plan_a if r[7] == name]
        quota = len(rs) if (name == 'pre_post' or max_a is None) else min(len(rs), max_a)
        keep += [rs[i] for i in sorted(rng.permutation(len(rs))[:quota])]
    db.executemany('insert into plan values (?,?,?,?,?,?,?,?,?,?)', keep); db.commit()
    C.log(candidates_S=len(plan_s), candidates_A=len(plan_a), planned=db.execute('select kind, cell, count(*) from plan group by 1,2').fetchall())


def get_pdf(session, aid, v, dest):
    tail = aid.split('/')[-1]
    yymm = tail.split('.')[0] if '.' in tail else tail[:4]
    url = f'{C.BUCKET}/{yymm}/{tail}v{v}.pdf'
    for attempt in range(3):
        try:
            r = session.get(url, timeout=90)
            if r.status_code == 200:
                Path(dest).write_bytes(r.content)
                return len(r.content)
            if r.status_code == 404:
                return None
            time.sleep(10 * (attempt + 1))
        except Exception:
            time.sleep(10 * (attempt + 1))
    return None


def extract_pdf(path, title):
    import fulltext_store as FT
    r = subprocess.run(['pdftotext', '-q', '-l', '60', '-enc', 'UTF-8', str(path), '-'], capture_output=True, timeout=180)
    t = r.stdout.decode('utf-8', 'ignore')
    if len(t.strip()) < 500:
        return None
    s = FT.sections(t, title)
    first = t.split('\x0c')[0]
    sv, sd = C.stamp_date(first[:6000])
    return dict(body=s['body'], abstract=abstract_of(FT.clean(t)), flags=s['flags'], stamp_v=sv, date=sd)


def one(args):
    session, aid, v, title = args
    with tempfile.TemporaryDirectory(dir=str(C.P.SCRATCH) if os.environ.get('RV_TMP_SCRATCH') else None) as d:
        p = Path(d) / 'x.pdf'
        n = get_pdf(session, aid, v, p)
        if not n:
            return None
        try:
            r = extract_pdf(p, title)
        except Exception:
            return None
        if r:
            r['pdf_bytes'] = n
        return r


def cmd_chunk(task, of):
    import requests
    s = requests.Session(); s.headers['User-Agent'] = C.UA
    db = sqlite3.connect(f'file:{C.DB}?mode=ro', uri=True)
    plan = [r for r in db.execute('select arxiv_id, max(final_v), title from plan group by arxiv_id order by arxiv_id') if int(hashlib.md5(r[0].encode()).hexdigest(), 16) % of == task]
    db.close()
    out = scratch(); out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    for c in range(0, len(plan), CHUNK):
        dest = out / f'chunk-{task:03d}-{c // CHUNK:03d}.sqlite'
        if dest.exists():
            continue
        tmp = Path(tempfile.gettempdir()) / f'rv-{task}-{c}.sqlite'
        tmp.unlink(missing_ok=True)
        cdb = sqlite3.connect(tmp)
        cdb.execute('create table texts (arxiv_id text, role text, v int, stamp_v int, date text, title_found int, abstract text, body blob, words int, flags text, pdf_bytes int, primary key (arxiv_id, role))')
        jobs = [(s, a, v, t) for a, fv, t in plan[c:c + CHUNK] for v in ((1, fv) if fv else (1,))]
        import json
        with ThreadPoolExecutor(THREADS) as ex:
            res = list(ex.map(one, jobs))
        k = 0
        for (_, a, v, _t), r in zip(jobs, res):
            if r is None:
                continue
            role = 'v1' if v == 1 else 'final'
            cdb.execute('insert or replace into texts values (?,?,?,?,?,?,?,?,?,?,?)',
                        (a, role, v, r['stamp_v'], r['date'], int(bool(r['flags'].get('title_found'))), r['abstract'], zlib.compress(r['body'].encode()),
                         len(r['body'].split()), json.dumps(r['flags']), r['pdf_bytes']))
            k += 1
        cdb.commit(); cdb.close()
        os.replace(tmp, dest) if tmp.stat().st_dev == dest.parent.stat().st_dev else (dest.write_bytes(tmp.read_bytes()), tmp.unlink())
        C.log(task=task, chunk=c // CHUNK, texts=k, of_pairs=len(plan), seconds=int(time.time() - t0))


def cmd_merge():
    import rv_match as M
    db = M.connect()
    db.execute('create table if not exists texts (arxiv_id text, role text, v int, stamp_v int, date text, title_found int, abstract text, body blob, words int, flags text, pdf_bytes int, primary key (arxiv_id, role))')
    n = 0
    for f in sorted(scratch().glob('chunk-*.sqlite')):
        db.execute(f"attach '{f}' as c")
        db.execute('insert or replace into texts select * from c.texts')
        db.commit(); db.execute('detach c'); n += 1
    C.log(merged_chunks=n, texts=db.execute('select count(*) from texts').fetchone()[0])


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['plan', 'chunk', 'merge'])
    ap.add_argument('a', nargs='?', type=int)
    ap.add_argument('b', nargs='?', type=int, default=64)
    ap.add_argument('--max-a', type=int, default=4000)
    ap.add_argument('--max-s', type=int, default=5000)
    x = ap.parse_args()
    if x.cmd == 'plan':
        cmd_plan(x.max_a, x.max_s)
    elif x.cmd == 'chunk':
        cmd_chunk(x.a, x.b)
    else:
        cmd_merge()
