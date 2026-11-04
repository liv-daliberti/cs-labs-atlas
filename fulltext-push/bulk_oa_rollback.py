"""Roll a bulk open-access channel back (2026-11-04): the hand check of 20 matched copies per source allowed at most 1 wrong identity.
For each school: a catalog backup, then (1) the listed wrong downloads are reverted (revert_downloads.revert), (2) every candidate of the channel's
evidence files (`<channel>-20261104*`) that is not the download_url of a downloaded work is deleted (copies that passed the hand check stay),
(3) Princeton's discovery packages of the channel are renamed `*.rolledback` so the import path no longer globs them.
Every change -> raw/bulk-oa/rollback-<channel>.jsonl.
usage: bulk_oa_rollback.py <channel> <wrong.json>      wrong.json: [{school, work, url, reason}]
"""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bulk_oa as B  # noqa: E402
import ftp_common as F  # noqa: E402
import revert_downloads as RD  # noqa: E402


def main(ch, wrong_path):
    wrong = json.load(open(wrong_path))
    B.DIR.mkdir(parents=True, exist_ok=True)
    log = open(B.DIR / f'rollback-{ch}.jsonl', 'a')
    for s in ['cmu', 'epfl', 'mit', 'berkeley', 'stanford', 'michigan', 'uchicago', 'gatech', 'princeton']:
        store = F.FT / s
        if s == 'princeton':
            for d in sorted((store / 'discovery').glob(f'claude-labpapers-{ch}-20261104*')):
                if d.is_dir():
                    d.rename(d.with_name(d.name + '.rolledback'))
                    log.write(json.dumps(dict(school=s, renamed=d.name)) + '\n')
        if not (store / 'catalog.sqlite').exists():
            continue
        for w in [x for x in wrong if x['school'] == s]:
            log.write(json.dumps(dict(school=s, revert=RD.revert(s, w['work'], w['url'], w['reason']))) + '\n')
        F.backup_catalog(store, f'before-bulk-oa-rollback-{ch}', keep=10)
        db = sqlite3.connect(str(store / 'catalog.sqlite'), timeout=120)
        like = f'%/{ch}-20261104%'
        keep = {u for (u,) in db.execute("SELECT download_url FROM works WHERE status IN ('downloaded','fulltext_xml') AND download_url IS NOT NULL")}
        rows = [(w, u) for w, u in db.execute('SELECT work_id, url FROM candidates WHERE metadata_source LIKE ?', (like,)) if u not in keep]
        n = F.write_batches(db, 'DELETE FROM candidates WHERE work_id=? AND url=?', rows)
        log.write(json.dumps(dict(school=s, channel=ch, candidates_deleted=n)) + '\n')
        log.flush()
        print(json.dumps(dict(school=s, channel=ch, candidates_deleted=n)), flush=True)
        db.close()


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
