"""Build hierarchy/period-tools/proposals/cmu.json (CMU appointment-period review, 2026-10-26).
Every evidence item is made by pcap.ev against hierarchy/period-captures.sqlite; existing override evidence is re-made
from the same capture (copied unchanged from the cs-related / listings stores)."""
import json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cmu_util  # noqa: E402  (retrying fetch, copy helpers)
import pcap  # noqa: E402

H = HERE.parent
TODAY = '2026-10-26'
OVR = json.load(open(H / 'census-overrides.json'))['cmu']
TARGETS = [t['pi'] for t in json.load(open(HERE / 'cmu-targets-20261026.json'))]
SCH = 'https://scholars.cmu.edu/'
WB = re.compile(r'web\.archive\.org/web/(\d{8})')


def observed(url):
    m = WB.search(url)
    if m:
        s = m.group(1)
        return f'{s[:4]}-{s[4:6]}-{s[6:8]}'
    con = pcap.mpcap.connect()
    row = con.execute('select fetched_at from captures where (url=? or capture_url=?) and status=200 and error is null '
                      'order by id desc limit 1', (url, url)).fetchone()
    con.close()
    return (row[0] or TODAY)[:10] if row else TODAY


def E(url, quote, kind, note=None):
    if not pcap.cached(url):
        cmu_util.copy_any(url)
    return pcap.ev(url, quote, kind, observed(url), note)


def old(pi, i, kind, note=None):
    """re-make evidence item i of the existing override period of pi"""
    e = OVR[pi]['periods'][0]['evidence'][i]
    return E(e['url'], e['quote'], kind, note or 'evidence of the existing override period')


def oid(pi):
    return OVR[pi]['periods'][0]['id']


P = {}


def period(pi, start, end, asof, prec, evidence, note, existing=None, departure=None, dep_ev=None):
    if end is None:  # asof = observed date of the latest evidence of an active appointment (profile/listing; else any)
        act = [e['observed'] for e in evidence if e['kind'] == 'faculty_profile' or e['kind'].startswith('dept_listing')
               or e['kind'].startswith('dated_profile')]
        asof = max(act or [e['observed'] for e in evidence])
    else:
        asof = None
    P[pi] = dict(pi=pi, existing_period_id=existing, verdict='period',
                 period=dict(start=start, end=end, asof=asof, datePrecision=prec, evidence=evidence, note=note),
                 departure=departure, departure_evidence=dep_ev or [], why=None)


def nochange(pi, why, departure=None, dep_ev=None):
    P[pi] = dict(pi=pi, existing_period_id=None, verdict='no_change', period=None, departure=departure,
                 departure_evidence=dep_ev or [], why=why)


exec(open(HERE / 'cmu_entries.py').read())

missing = [t for t in TARGETS if t not in P]
extra = [p for p in P if p not in TARGETS]
assert not missing and not extra, (missing, extra)
out = [P[t] for t in TARGETS]
(HERE / 'proposals').mkdir(exist_ok=True)
json.dump(out, open(HERE / 'proposals' / 'cmu.json', 'w'), indent=1, ensure_ascii=False)
from collections import Counter
print(Counter(p['verdict'] for p in out), len(out))
