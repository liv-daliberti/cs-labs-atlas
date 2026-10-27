"""Write the staged CMU CS-related outputs: append to census/cmu-additions.json (refusing if it changed since the given
baseline sha256 or if a name is already there), add reviewed periods under census-overrides.json -> cmu -> name (re-read
right before writing; only new cmu keys), and write hierarchy/cmu/cs-related-home-departments.json and
hierarchy/cmu/cs-related-review.json. usage: commit.py <stage_dir> <additions_baseline_sha256>"""
import collections, hashlib, json, os, sys
from pathlib import Path
HERE = Path(__file__).resolve().parents[3]
S, base = Path(sys.argv[1]), sys.argv[2]
add_f, ovr_f = HERE / 'census/cmu-additions.json', HERE / 'hierarchy/census-overrides.json'
A, P, H, R = (json.load(open(S / f)) for f in ('additions.json', 'periods.json', 'home_departments.json', 'review.json'))


def atomic(path, obj):
    tmp = path.with_name(path.name + '.tmp-cmu-csr')
    with open(tmp, 'w') as f:
        json.dump(obj, f, indent=1, ensure_ascii=False); f.write('\n')
    os.replace(tmp, path)


raw = open(add_f, 'rb').read()
if hashlib.sha256(raw).hexdigest() != base:
    sys.exit('census/cmu-additions.json changed since the baseline: stop')
cur = json.loads(raw)
have = {r['name'] for r in cur}
dup = [a['name'] for a in A if a['name'] in have]
if dup:
    sys.exit(f'already in additions: {dup}')
atomic(add_f, cur + A)

raw = open(ovr_f, 'rb').read(); O = json.loads(raw)  # re-read right before writing
cmu = O.setdefault('cmu', {})
clash = [n for n in P if n in cmu]
if clash:
    sys.exit(f'override keys already present: {clash}')
for n, v in P.items():
    cmu[n] = v
if hashlib.sha256(open(ovr_f, 'rb').read()).hexdigest() != hashlib.sha256(raw).hexdigest():
    sys.exit('census-overrides.json changed during the merge: stop')
atomic(ovr_f, O)

atomic(HERE / 'hierarchy/cmu/cs-related-home-departments.json', H)
cnt = collections.Counter(r['decision'] for r in R)
atomic(HERE / 'hierarchy/cmu/cs-related-review.json', dict(
    reviewed='2026-10-26', school='cmu',
    rule=('Owner decision 2026-10-22: "All universities should include all faculty that work on CS-related topics / publish in CS venues (Even if not in CS)." '
          'A candidate of hierarchy/cmu/cs-related-candidates.json (DBLP-based: 8+ CMU works 2016-2026, 5+ and 20%+ DBLP-indexed, last author on 30%+ or 30+ works, '
          'not already a PI) is accepted when (1) faculty at CMU in some year 2016-2026 in any department: professor ranks incl. research professors; postdocs, '
          'research scientists/staff (systems/project scientists), teaching-track faculty without PhD advising, adjunct/courtesy-only, visitors and students do not count; '
          '(2) a PI: stated PhD advising 2016-2026 (named in the Advisor(s) field of a CMU dissertation record, KiltHub or the SCS reports archive, or advisees named on a '
          'dated page) or a lab they head alone; (3) home department from a dated department listing/profile; (4) appointment years from dated department listings and '
          'dated profiles, with a reviewed period (hierarchy/census-overrides.json -> cmu) whenever the dated listings do not span 2016-2026. Emeritus listings end the period; '
          'adjunct/courtesy/visiting listings in the home department, and listings naming a post at another university, do not count as appointment years.'),
    captures='hierarchy/cmu/cs-related-captures.sqlite (fetched or copied pages; each quote is an exact substring of the stored text, whitespace collapsed; copied rows keep '
             'their bytes, sha256 and fetched_at and name copied_from)',
    tools='hierarchy/cs-related-tools/{csrcap.py,people.py,listing_rows.py,evidence.py,plan.py} and hierarchy/cmu/cs-related-tools/{decisions.py,build.py,verify.py,commit.py,theses.py,wb.py,fetch_show.py}',
    outputs=dict(additions="census/cmu-additions.json rows with added='cs_related_scope_20261022'", periods='hierarchy/census-overrides.json -> cmu -> <name> -> periods',
                 home_departments='hierarchy/cmu/cs-related-home-departments.json'),
    counts=dict(candidates=len(R), people_accepted=len(A), periods=len(P), by_decision=dict(cnt)),
    decisions=R))
print(json.dumps(dict(appended=len(A), periods=len(P), homes=len(H), review=len(R), by_decision=dict(cnt))))
