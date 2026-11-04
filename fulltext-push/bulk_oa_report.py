"""Per source and school: the new candidates the bulk open-access channels wrote, how many works they cover, the copies obtained so far, and the
hand-check sample (2026-11-04). A candidate belongs to a channel when its evidence file is that channel's (`<channel>-<stamp>-NNNN.json`,
lab_channels.write); a copy is obtained from it when the work is downloaded and its download_url is one of that channel's candidate URLs.
Read-only on the catalogs (short chunks).
usage: bulk_oa_report.py report [<school> ...]        counts as JSON lines
       bulk_oa_report.py sample <channel> <n> [seed]  n downloaded copies from the channel, page-1 text for the identity hand check (all schools)
"""
import json
import random
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F  # noqa: E402

CHANNELS = ['oa_locations', 's2_bulk', 'core_bulk', 'arxiv_bulk', 'wayback_escholarship']
SCHOOLS = ['princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford', 'michigan', 'uchicago', 'gatech']


def ro(school):
    p = F.FT / school / 'catalog.sqlite'
    return sqlite3.connect(f'file:{p}?mode=ro', uri=True, timeout=120) if p.exists() else None


def report(schools):
    for s in schools:
        db = ro(s)
        if db is None:
            continue
        for ch in CHANNELS:
            like = f'%/{ch}-20261104%'
            cand = db.execute('SELECT count(*), count(DISTINCT work_id) FROM candidates WHERE metadata_source LIKE ?', (like,)).fetchone()
            got = db.execute("SELECT count(*) FROM works w JOIN candidates c ON c.work_id=w.id AND c.url=w.download_url WHERE c.metadata_source LIKE ? "
                             "AND w.status IN ('downloaded','fulltext_xml')", (like,)).fetchone()[0]
            tried = db.execute('SELECT count(DISTINCT c.work_id) FROM candidates c JOIN attempts a ON a.work_id=c.work_id AND a.url=c.url WHERE c.metadata_source LIKE ?', (like,)).fetchone()[0]
            print(json.dumps(dict(school=s, channel=ch, candidates=cand[0], works=cand[1], works_attempted=tried, copies=got)), flush=True)
        db.close()


def sample(ch, n, seed=1):
    pool = []
    for s in SCHOOLS:
        db = ro(s)
        if db is None:
            continue
        like = f'%/{ch}-20261104%'
        for w, t, fp, url, idc in db.execute("SELECT w.id, w.title, w.file_path, w.download_url, w.identity_check FROM works w JOIN candidates c ON c.work_id=w.id AND c.url=w.download_url "
                                              "WHERE c.metadata_source LIKE ? AND w.status IN ('downloaded','fulltext_xml')", (like,)):
            pool.append((s, w, t, fp, url, idc))
        db.close()
    random.Random(seed).shuffle(pool)
    for s, w, t, fp, url, idc in pool[:n]:
        path = Path(fp) if fp and Path(fp).is_absolute() else F.FT / s / (fp or '')
        try:
            txt = subprocess.run(['pdftotext', '-f', '1', '-l', '1', str(path), '-'], capture_output=True, text=True, timeout=60).stdout
        except Exception:
            txt = ''
        print(json.dumps(dict(school=s, work=w, catalog_title=t, url=url, identity_check=idc, page1=' '.join(txt.split())[:700])))
    print(json.dumps(dict(pool=len(pool))), file=sys.stderr)


if __name__ == '__main__':
    if sys.argv[1] == 'report':
        report(sys.argv[2:] or SCHOOLS)
    else:
        sample(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else 1)
