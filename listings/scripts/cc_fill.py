"""Fill a school's Wayback 'nocapture'/'unusable' plan rows from Common Crawl (second historical source).

usage: cc_fill.py <school> --db <captures.sqlite> [--slot substr ...] [--state state.json] [--gap-crawls] [--dry-run]

Read docs/COMMONCRAWL.md first.  Rules enforced here:
- Only the S3 bucket https://commoncrawl.s3.amazonaws.com is requested (cc.polite_get refuses index/data.commoncrawl.org); cc.gate() refuses
  (exit 5, before any request) unless the owner-approval marker cache/commoncrawl/OWNER-APPROVED exists.
- --db is REQUIRED.  Run it on a private copy of the school's captures.sqlite (the school's own worker writes the live one); merge with
  tools/... merge steps in docs/COMMONCRAWL.md.
- Same plan semantics as plan_fetch: one row per (slot, year, half); a row is only ever changed from nocapture/unusable to ok (or H2 to
  out_of_scope when H1 became ok for ONE_CAPTURE_PER_YEAR schools); never touches 'ok' rows; slot_usable() decides usability.
- Per half-year the crawl nearest the middle of the half is asked first (one crawl per calendar year), the others only with --gap-crawls.
- The target page host's current robots.txt must not disallow AI agents by name (recorded in cc_robots); else its rows are left alone.
Exit codes: 0 done, 3 unfinished (errors; re-run resumes from the cached index), 5 no owner-approval marker (fail-closed, before any request), 2 usage.
"""
import argparse
import json
import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'tools'))
import cc
import plan_fetch as PF


def open_db(path):
    con = sqlite3.connect(path, timeout=120)
    con.execute('create table if not exists captures(capture_url text primary key, page_url text, department text, wayback_timestamp text, '
                'final_url text, http_status integer, fetched_at text, sha256 text, nbytes integer, content_type text, raw_zlib blob, '
                'blocks_json text, text text, note text)')
    con.execute('create table if not exists plan(slot text, dept text, year integer, half text, page_url text, capture_url text, '
                'wayback_timestamp text, status text, reason text, tried text, primary key(slot, year, half))')
    cc.init_tables(con)
    return con


def candidates_for(s, y, half, crawls, con, errors, http, gap):
    """Index rows (best first) from the half's crawls for the slot's exact URLs within the half-year."""
    lo, hi = {'H1': (f'{y}0101', f'{y}0630'), 'H2': (f'{y}0701', f'{y}1231')}[half]
    out = []
    for crawl in (crawls if gap else crawls[:1]):
        for pri, spec in enumerate(s['urls']):
            u, ulo, uhi = spec[:3]
            opt = spec[3] if len(spec) > 3 else {}
            if opt.get('prefix'):
                continue  # exact-URL index queries only; prefix slots stay Wayback-only (recorded in the report)
            try:
                rows = cc.cdx_cached(con, crawl, u.split('://', 1)[-1], errors, http=http)
            except cc.CCRefused as e:
                print('  ', e, flush=True)
                continue
            for r in rows:
                d = r['timestamp'][:8]
                if lo <= d <= hi and ulo <= d <= uhi and cc.host_ok(con, r['original'], http):
                    out.append((pri, u, r))
    return out


def try_capture(con, s, pri_u_r, school, pis, http):
    _, u, r = pri_u_r
    status, body, hdrs = cc.fetch_record(r, http=http)
    cc.store(con, r, status, body, hdrs, u, s['dept'])
    cap = cc.capture_key(r)
    st, blocks = PF.ensure_extracted(con, cap)
    good, why = PF.slot_usable(con, cap, s, blocks, st, pis, school)
    return cap, st, good, why


def run(school, db, filters, state_path, gap, dry, http=None):
    try:
        cc.gate(http)
    except cc.CCRefused as e:
        print(f'REFUSED: {e} (waiting for the owner approval marker); nothing requested', flush=True)
        return 5
    cfg, pis = PF.load(school)
    con = open_db(db)
    st = json.load(open(state_path)) if state_path and os.path.exists(state_path) else {}
    errors = st.get('errors', {})
    crawls = cc.pick_crawls([{'id': c} for c in cc.CRAWLS])
    filled = scanned = 0
    for s in cfg.SLOTS:
        if filters and not any(f.lower() in s['slot'].lower() for f in filters):
            continue
        one = school in PF.ONE_CAPTURE_PER_YEAR
        for y in PF.YEARS:
            if y not in s.get('years', PF.YEARS):
                continue
            for half in ('H1', 'H2'):
                row = con.execute('select status from plan where slot=? and year=? and half=?', (s['slot'], y, half)).fetchone()
                if row is None or row[0] not in ('nocapture', 'unusable', 'out_of_scope'):
                    continue  # unplanned rows belong to Wayback's own re-run; ok rows are never replaced
                if half == 'H2' and one and con.execute("select 1 from plan where slot=? and year=? and half='H1' and status='ok'",
                                                        (s['slot'], y)).fetchone():
                    continue
                if row[0] == 'out_of_scope' and not (half == 'H2' and one):
                    continue
                scanned += 1
                tried = []
                for cand in candidates_for(s, y, half, crawls.get((y, half), []), con, errors, http, gap)[:3]:
                    if dry:
                        print(f'  {s["slot"]} {y}{half} candidate {cand[2]["crawl"]} {cand[2]["timestamp"]}', flush=True)
                        break
                    cap, status, good, why = try_capture(con, s, cand, school, pis, http)
                    tried.append({'capture_url': cap, 'source': cc.SOURCE, 'status': status, 'usable': good, 'why': why})
                    print(f'  {s["slot"]} {y}{half} {cand[2]["timestamp"]} -> {status} {"OK" if good else why}', flush=True)
                    if good:
                        con.execute('insert or replace into plan values(?,?,?,?,?,?,?,?,?,?)',
                                    (s['slot'], s['dept'], y, half, cand[1], cap, cand[2]['timestamp'], 'ok', None, json.dumps(tried)))
                        filled += 1
                        break
                con.commit()
        json.dump({'errors': errors, 'bytes': st.get('bytes', 0) + cc.BYTES['n'], 'requests': cc.BYTES['requests'], 'updated': time.strftime('%Y-%m-%dT%H:%M:%S')}, open(state_path, 'w')) if state_path else None
    if not dry and one:  # H2 rows whose H1 is now ok become out_of_scope, as plan_fetch does
        con.execute("update plan set status='out_of_scope', capture_url=null, page_url=null, wayback_timestamp=null, "
                    "reason='year already proven by its Jan-Jun capture (one capture per calendar year)' where half='H2' and status in "
                    "('nocapture','unusable') and exists (select 1 from plan p where p.slot=plan.slot and p.year=plan.year and p.half='H1' and p.status='ok')")
        con.commit()
    print(f'scanned {scanned} slot-halves, filled {filled}, bytes read {cc.BYTES["n"]} in {cc.BYTES["requests"]} requests', flush=True)
    return 3 if any(v >= cc.MAX_CRAWL_ERRORS for v in errors.values()) else 0


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('school')
    ap.add_argument('--db', required=True)
    ap.add_argument('--slot', action='append', default=[])
    ap.add_argument('--state')
    ap.add_argument('--gap-crawls', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args(argv)
    sys.exit(run(a.school, a.db, a.slot, a.state, a.gap_crawls, a.dry_run))


if __name__ == '__main__':
    main(sys.argv[1:])
