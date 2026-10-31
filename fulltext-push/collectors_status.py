"""Collector status page (ROADMAP item 12; 2026-10-31): one generated page for the download loops of every school.

Per school: the loop's Slurm job and host, its phase and last round (loop-state.json), attempts and downloads in the
last 24 h (the catalog's attempts table, read newest first in short read-only chunks until 24 h back), the catalog's
status counts and pending identity reviews (the collector's last progress line in loop.log), the sources the last pass
paused (loop.log), the lab papers' queue / access-review counts and coverage (copies.json, the coverage counter's
output, with the time it was counted).
-> hierarchy/COLLECTORS-STATUS.md and .json (generated; not in git). The loop calls this after every round
(lab_first_loop.py), so the page is never more than one round old; it can also be run by hand.
usage: collectors_status.py [school ...]          (default: every store with a loop-state.json)
"""
import json, os, re, sqlite3, sys, time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ftp_common as F  # noqa: E402


def tail_lines(p, nbytes=400_000):
    if not p.exists():
        return []
    with open(p, 'rb') as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(max(0, size - nbytes))
        return f.read().decode('utf-8', 'replace').splitlines()


def last_json(lines, key):
    for line in reversed(lines):
        if f'"{key}"' in line:
            try:
                return json.loads(line)
            except ValueError:
                continue
    return None


def recent_attempts(store, hours=24):
    cut = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    db = sqlite3.connect(f'file:{store / "catalog.sqlite"}?mode=ro', uri=True, timeout=60)
    db.execute('PRAGMA busy_timeout=60000')
    hi = db.execute('SELECT MAX(id) FROM attempts').fetchone()[0] or 0
    n, done = Counter(), False
    while hi > 0 and not done:
        rows = db.execute('SELECT observed_at, status, detail FROM attempts WHERE id > ? AND id <= ?', (hi - 5000, hi)).fetchall()
        for at, st, d in rows:
            if (at or '') >= cut:
                n['attempts'] += 1
                n[st] += 1
                if st not in ('downloaded', 'fulltext_xml'):
                    n['detail:' + f'{st}: ' + re.sub(r'\d+', 'N', (d or '')[:90])] += 1
        done = not rows or min((r[0] or '') for r in rows) < cut
        hi -= 5000
        time.sleep(0.02)
    db.close()
    return n


def school_status(school):
    store = F.FT / school
    st = json.loads((store / 'loop-state.json').read_text()) if (store / 'loop-state.json').exists() else {}
    lines = tail_lines(store / 'loop.log')
    prog = last_json(lines, 'status_counts') or {}
    paused = (last_json(lines, 'paused_sources') or {}).get('paused_sources') or {}
    cp = F.SCHOOLS / 'hierarchy' / school / 'copies.json'
    summ = json.loads(cp.read_text()).get('summary', {}) if cp.exists() else {}
    att = recent_attempts(store) if (store / 'catalog.sqlite').exists() else Counter()
    fails = Counter({k[7:]: v for k, v in att.items() if k.startswith('detail:')})
    downloads = att.get('downloaded', 0) + att.get('fulltext_xml', 0)
    # attempts but no download in 24 h: the loop runs but nothing lands (2026-10-31: Michigan's missing sources/)
    alarm = (f"{att.get('attempts', 0):,} attempts and no download in 24 h; most common failure: "
             f"{fails.most_common(1)[0][0]} ({fails.most_common(1)[0][1]:,})") if att.get('attempts', 0) and not downloads and fails else None
    return dict(school=school, slurm_job=st.get('slurm_job'), host=st.get('host'), phase=st.get('phase'), rounds=st.get('rounds'),
                updated_at=st.get('updated_at'), lab_work_ids=st.get('lab_work_ids'), idle_rounds=st.get('idle_rounds'),
                attempts_24h=att.get('attempts', 0), downloads_24h=downloads, alarm=alarm, top_failures=dict(fails.most_common(3)),
                catalog=prog.get('status_counts'), pending_identity_review=prog.get('pending_identity_review'), paused_sources=paused,
                lab_papers=summ.get('lab_papers'), local=summ.get('local'), coverage=summ.get('local_share'), lab_queued=summ.get('queued'),
                lab_access_review=summ.get('needs_access_review'), counted_at=summ.get('counted_at'))


def render(rows):
    out = ['# Collector status', '', f'Generated {F.now()[:19]}Z by `fulltext-push/collectors_status.py` (do not edit). '
           'Coverage is the coverage counter\'s (copies.json, counted at the time shown).', '',
           '| school | job | phase | rounds | last update (UTC) | attempts 24h | downloads 24h | lab queued | lab access review | coverage | counted |',
           '|---|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        cov = f"{r['local']:,} / {r['lab_papers']:,} ({r['coverage']:.1%})" if r.get('local') is not None and r.get('coverage') is not None else '—'
        out.append(f"| {r['school']} | {r['slurm_job'] or '—'} | {r['phase'] or '—'} | {r['rounds'] or '—'} | {(r['updated_at'] or '—')[:16]} | "
                   f"{r['attempts_24h']:,} | {r['downloads_24h']:,} | {r['lab_queued'] or 0:,} | {r['lab_access_review'] or 0:,} | {cov} | {(r['counted_at'] or '—')[:16]} |")
    alarms = [r for r in rows if r.get('alarm')]
    out += ['', '## Alarms', '']
    out += [f"- **{r['school']}**: {r['alarm']}" for r in alarms] or ['- none']
    out += ['', '## Paused sources (last pass)', '']
    for r in rows:
        ps = r['paused_sources'] or {}
        out.append(f"- **{r['school']}**: " + ('; '.join(f'{h} ({why})' for h, why in sorted(ps.items())) if ps else 'none'))
    out += ['', '## Catalog status counts (the collector\'s last progress line)', '']
    for r in rows:
        out.append(f"- **{r['school']}**: {json.dumps(r['catalog'] or {})}; pending identity review {r['pending_identity_review']}")
    return '\n'.join(out) + '\n'


def main(schools=None):
    schools = schools or sorted(p.name for p in F.FT.iterdir() if (p / 'loop-state.json').exists())
    rows = [school_status(s) for s in schools]
    d = F.SCHOOLS / 'hierarchy'
    tmp = d / f'.COLLECTORS-STATUS.md.{os.getpid()}'
    tmp.write_text(render(rows)); os.replace(tmp, d / 'COLLECTORS-STATUS.md')
    tmp = d / f'.COLLECTORS-STATUS.json.{os.getpid()}'
    tmp.write_text(json.dumps(dict(generated_at=F.now(), schools=rows), indent=1)); os.replace(tmp, d / 'COLLECTORS-STATUS.json')
    return rows


if __name__ == '__main__':
    for r in main(sys.argv[1:] or None):
        print(json.dumps({k: r[k] for k in ('school', 'phase', 'attempts_24h', 'downloads_24h', 'coverage')}))
