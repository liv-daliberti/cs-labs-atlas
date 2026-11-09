"""Profile pass for the missed-labs verify queue (coordinator decision 2026-11-09): fetch likely official profile pages of unverified leads into a
SCRATCH capture store (never main's raw school-captures.sqlite) and record where the name is followed by a professor title.

store     <scratch>/missed-labs-profile/<school>.sqlite  (school_web's live / captures / robots / blocked tables, db_path patched to this file)
live      hosts robots.txt allows us AND the AI agents by name (school_web.robots_ok), one request per host per max(2 s, crawl-delay); a challenge,
          401/403/429 marks the host blocked and it is not used again
wayback   challenged or 403 hosts (JHU, cs.uchicago.edu): the latest id_ capture through the shared throttle with WAYBACK_LOW=1 (set below); a 429 stops
          the Wayback side of the run and nothing is retried
urls      per-school profile URL templates over the lead's first and last name (a template miss is a 404, recorded as such)
-> <scratch>/missed-labs-profile/<school>-fetch.json {name: [{url, status, via, sha256, observed}]}
usage: missed_labs_fetch.py <school> [--limit N] [--no-wayback]    (leads: verify_queue first, then the rest by DBLP-indexed count)
"""
import json, os, re, sys
from pathlib import Path

os.environ['WAYBACK_LOW'] = '1'
import school_web as W  # noqa: E402
from pi_hierarchy import toks  # noqa: E402

SCRATCH = Path('/n/fs/resemble/homogenizing-science/scratch/missed-labs-profile')
WB_HOSTS = {'michigan': (), 'uchicago': ('cs.uchicago.edu',), 'gatech': (), 'harvard': (), 'jhu': ('jhu.edu',), 'washu': ()}   # wayback-only (challenged / 403)
TEMPLATES = {
    'michigan': ['https://www.si.umich.edu/people/{f}-{l}', 'https://ece.engin.umich.edu/people/directory/faculty/{f}-{l}/', 'https://lsa.umich.edu/stats/people/faculty/{f}-{l}.html'],
    'uchicago': ['https://cs.uchicago.edu/people/{f}-{l}/', 'https://stat.uchicago.edu/people/profile/{f}-{l}/', 'https://datascience.uchicago.edu/people/{f}-{l}/',
                 'https://www.chicagobooth.edu/faculty/directory/{l0}/{f}-{l}'],
    'gatech': ['https://www.cc.gatech.edu/people/{f}-{l}', 'https://ece.gatech.edu/directory/{f}-{l}', 'https://www.isye.gatech.edu/users/{f}-{l}'],
    'harvard': ['https://seas.harvard.edu/person/{f}-{l}', 'https://www.hsph.harvard.edu/profile/{f}-{l}/', 'https://dbmi.hms.harvard.edu/people/{f}-{l}'],
    'jhu': ['https://engineering.jhu.edu/faculty/{f}-{l}/', 'https://www.cs.jhu.edu/faculty/{f}-{l}/', 'https://ece.jhu.edu/faculty/{f}-{l}/'],
    'washu': ['https://engineering.washu.edu/faculty/{f}-{l}.html', 'https://olin.wustl.edu/faculty-and-research/faculty-directory/{f}-{l}.php',
              'https://profiles.wustl.edu/{f}-{l}'],
}


def slug(s):
    return re.sub(r'[^a-z0-9]', '', s)


def main(school, limit=40, wayback=True):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    dbf = str(SCRATCH / f'{school}.sqlite')
    W.db_path = lambda key, _p=dbf: Path(_p)
    c = W.con(school)
    rev = json.loads((Path(__file__).resolve().parents[1] / f'hierarchy/{school}/reviewed/missed-labs-review.json').read_text())
    q = [x['name'] for x in rev['verify_queue']]
    rest = [d for d in rev['decisions'] if d['decision'] == 'no_appointment_evidence' and d['name'] not in q]
    order = q + [d['name'] for d in sorted(rest, key=lambda d: -d['dblp_indexed'])]
    out_f = SCRATCH / f'{school}-fetch.json'
    out = json.loads(out_f.read_text()) if out_f.exists() else {}
    wb_stop = not wayback
    for name in order[:limit]:
        t = [x for x in toks(name) if len(x) > 1]
        if len(t) < 2 or name in out:
            continue
        subs = dict(f=slug(t[0]), l=slug(t[-1]), l0=slug(t[-1])[:1])
        res = []
        for tpl in TEMPLATES[school]:
            url = tpl.format(**subs)
            host = re.sub(r'^https?://', '', url).split('/')[0]
            via = 'wayback' if any(host == h or host.endswith('.' + h) for h in WB_HOSTS[school]) else 'live'
            if via == 'wayback':
                if wb_stop:
                    res.append(dict(url=url, status='queued_wayback', via=via)); continue
                try:
                    rows = W.cdx_rows(c, re.sub(r'^https?://', '', url), collapse='timestamp:4')
                    got = None
                    for r in sorted(rows, key=lambda x: x['timestamp'], reverse=True)[:1]:
                        cap, st, sha, b = W.capture(c, r['timestamp'], r['original'], url, 'profile')
                        got = dict(url=cap, status=st, via=via, sha256=sha, observed=r['timestamp'])
                    res.append(got or dict(url=url, status='no_capture', via=via))
                except Exception as e:  # noqa: BLE001
                    if '429' in repr(e):
                        wb_stop = True
                    res.append(dict(url=url, status='error:' + repr(e)[:80], via=via))
                continue
            r = W.live(c, url)
            if r is None:
                res.append(dict(url=url, status='robots_or_blocked', via=via))
            else:
                res.append(dict(url=url, status=r[0], via=via, sha256=r[1], observed=__import__('time').strftime('%Y%m%d')))
        out[name] = res
        out_f.write_text(json.dumps(out, indent=1))
    print(school, 'leads tried', len(out), 'pages 200', sum(1 for v in out.values() for x in v if x.get('status') == 200))


if __name__ == '__main__':
    a = sys.argv[1:]
    main(a[0], int(a[a.index('--limit') + 1]) if '--limit' in a else 40, '--no-wayback' not in a)
