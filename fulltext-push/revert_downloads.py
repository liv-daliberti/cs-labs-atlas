"""Revert downloads that are not the paper (2026-10-30): a work whose downloaded file failed a hand identity check goes
back to needs_access_review, its PDF asset row is removed, and the download's attempt row becomes status
'identity_mismatch' with the reason (so the collector never asks that URL again and the access review reads the cause).
The file object stays in objects/ (content-addressed; other works may share it); a by_lab symlink of the work is removed.
Every change -> <store>/staged/reverted-downloads.jsonl. Writes commit per work with a 120 s busy timeout.
usage: revert_downloads.py <list.json>      list: [{school, work, url, reason}]
"""
import json, os, sqlite3, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ftp_common as F  # noqa: E402


def revert(school, work, url, reason):
    store = F.FT / school
    db = sqlite3.connect(str(store / 'catalog.sqlite'), timeout=120)
    db.execute('PRAGMA busy_timeout=120000')
    db.row_factory = sqlite3.Row
    for attempt in range(30):
        try:
          with F.catalog_lock(store):  # one writer per catalog
            w = db.execute('SELECT * FROM works WHERE id=?', (work,)).fetchone()
            if not w or w['status'] != 'downloaded':
                db.close(); return dict(school=school, work=work, skipped=f"status {w['status'] if w else None}")
            before = {k: w[k] for k in ('status', 'file_path', 'sha256', 'download_url', 'identity_check', 'year')}
            db.execute("UPDATE works SET status='needs_access_review', file_path=NULL, sha256=NULL, byte_count=NULL, pages=NULL, download_url=NULL, "
                       "downloaded_at=NULL, identity_check=NULL WHERE id=? AND status='downloaded'", (work,))
            db.execute("DELETE FROM assets WHERE work_id=? AND kind='pdf'", (work,))
            n = db.execute("UPDATE attempts SET status='identity_mismatch', detail=? WHERE work_id=? AND url=? AND status='downloaded'",
                           (f'identity unconfirmed: {reason} (hand check 2026-10-30; download reverted)', work, url)).rowcount
            db.commit()
          break
        except sqlite3.OperationalError:
            db.rollback(); time.sleep(20)
    else:
        raise RuntimeError('catalog stayed locked')
    db.close()
    removed = []
    for link in (store / 'by_lab').glob(f"*/{before['year']}--{work}.pdf"):
        if link.is_symlink():
            link.unlink(); removed.append(str(link))
    rec = dict(school=school, work=work, url=url, reason=reason, before=before, attempts_marked=n, links_removed=removed, at=F.now(),
               by='fulltext-push/revert_downloads.py')
    with open(store / 'staged' / 'reverted-downloads.jsonl', 'a') as f:
        f.write(json.dumps(rec) + '\n')
    return rec


if __name__ == '__main__':
    for x in json.load(open(sys.argv[1])):
        print(json.dumps(revert(x['school'], x['work'], x['url'], x['reason'])), flush=True)


def restore(school, work, rec, identity, why):
    """Undo a revert (2026-10-31: the round-1 automatic identity review reverted true papers): the work is 'downloaded'
    again from its revert record (file path, sha256, download URL), with the identity the fixed rule gives (a confirmed
    tag, or the pending identity, which the coverage counter does not count); its asset row and its download attempt
    come back and its by_lab link is re-made. Logged to <store>/staged/restored-downloads.jsonl."""
    store = F.FT / school
    b = rec['before']
    fp = b['file_path']
    if not fp or not (store / fp).exists():
        return dict(school=school, work=work, skipped='file gone')
    size = (store / fp).stat().st_size
    db = sqlite3.connect(str(store / 'catalog.sqlite'), timeout=120)
    db.execute('PRAGMA busy_timeout=120000')
    for attempt in range(30):
        try:
          with F.catalog_lock(store):  # one writer per catalog
            c = db.execute("UPDATE works SET status='downloaded', file_path=?, sha256=?, byte_count=?, download_url=?, identity_check=? "
                           "WHERE id=? AND status IN ('needs_access_review','queued')", (fp, b['sha256'], size, b['download_url'], identity, work)).rowcount
            if not c:
                db.rollback(); db.close()
                return dict(school=school, work=work, skipped='status changed since the revert')
            db.execute('INSERT OR REPLACE INTO assets VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                       (work, 'pdf', b['download_url'], fp, b['sha256'], size, None, None, None, F.now(), identity))
            db.execute("UPDATE attempts SET status='downloaded', detail=? WHERE work_id=? AND url=? AND status='identity_mismatch'",
                       (json.dumps(dict(final_url=b['download_url'], sha256=b['sha256'], restored_by='revert_downloads.restore', why=why)), work, rec['url']))
            db.commit()
          break
        except sqlite3.OperationalError:
            db.rollback(); time.sleep(20)
    else:
        raise RuntimeError('catalog stayed locked')
    db.close()
    for link in rec.get('links_removed') or []:
        if not os.path.lexists(link):
            os.symlink(Path('../..') / fp, link)
    out = dict(school=school, work=work, identity=identity, file_path=fp, why=why, at=F.now(), by='fulltext-push/revert_downloads.py restore')
    with open(store / 'staged' / 'restored-downloads.jsonl', 'a') as f:
        f.write(json.dumps(out) + '\n')
    return out
