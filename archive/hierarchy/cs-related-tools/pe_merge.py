"""Merge the Princeton supplement and the EPFL review (pe_princeton.py, pe_epfl.py outputs in <work>) into the shared files.

census/<school>-additions.json            appended (rows whose name is already there are skipped; existing rows untouched)
hierarchy/census-overrides.json           re-read right before writing; only this review's names under princeton/epfl are added
hierarchy/<school>/cs-related-home-departments.json   written (Princeton: the first review's 33 accepted rows + the supplement)
hierarchy/princeton/cs-related-review.json            first review kept; supplement decisions appended (review_round marks them)
hierarchy/epfl/cs-related-review.json                 written
usage: pe_merge.py <work_dir> [--dry]
"""
import collections, json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
W = Path(sys.argv[1]); DRY = '--dry' in sys.argv
ROUND = 'dblp_list_supplement_20261026'
RULE = ('Owner decision 2026-10-22: "All universities should include all faculty that work on CS-related topics / publish in CS venues (Even if not in CS)." '
        'Candidates: hierarchy/<school>/cs-related-candidates.json (tools/cs_related_candidates.py: OpenAlex authors with 8+ school works 2016-2026, 5+ and 20%+ of '
        'them DBLP-indexed, last author on 30%+ or 30+ works, not already a PI). A candidate is accepted when (1) faculty at the school in some year 2016-2026 in any '
        'department (professor ranks incl. adjunct/titular and emeriti; EPFL MER/Senior Scientist heading a group; not postdocs, research staff, lecturers without '
        'PhD direction, visitors/host professors or students), (2) a PI: first-listed thesis director / named adviser of a 2016-2026 doctoral thesis record, or a lab '
        'they head alone, and (3) appointment years come from dated faculty lists (emeritus entries are not appointment years); a reviewed period is added to '
        'hierarchy/census-overrides.json when the appointment does not cover 2016-2026.')


def load(p):
    return json.load(open(p))


def dump(obj, p):
    if DRY:
        print('dry: would write', p); return
    tmp = str(p) + '.tmp'
    json.dump(obj, open(tmp, 'w'), indent=1, ensure_ascii=False)
    os.replace(tmp, p)


out = {}
# --- census additions
for school, f in (('princeton', 'princeton-additions-new.json'), ('epfl', 'epfl-additions-new.json')):
    p = HERE / f'census/{school}-additions.json'
    cur = load(p); have = {r['name'] for r in cur}
    new = [r for r in load(W / f) if r['name'] not in have]
    dump(cur + new, p)
    out[f'census/{school}-additions.json'] = dict(before=len(cur), appended=len(new))

# --- periods (re-read right before writing)
P = {'princeton': load(W / 'princeton-periods.json'), 'epfl': load(W / 'epfl-periods.json')}
p = HERE / 'hierarchy/census-overrides.json'
ov = load(p); added = collections.Counter()
for school, per in P.items():
    sch = ov.setdefault(school, {})
    for name, v in per.items():
        if name in sch and sch[name].get('periods'):
            continue
        sch.setdefault(name, {})['periods'] = v['periods']; added[school] += 1
dump(ov, p)
out['hierarchy/census-overrides.json'] = dict(added)

# --- home departments
first = [r for r in load(HERE / 'census/princeton-additions.json') if r.get('added') == 'cs_related_scope_20261022']
new_h = {h['name']: h for h in load(W / 'princeton-home-departments.json')}
rows = []
for r in first:
    if r['name'] in new_h:
        continue
    dep = r['departments'][0]
    src = [s for s in r.get('sources') or [] if s.get('kind', '').endswith(dep)] or r.get('sources') or []
    e = src[-1] if src else None
    rows.append(dict(school='princeton', name=r['name'], home_department=dep, also=r['departments'][1:], no_academic_department=False, status='accepted',
                     evidence={k: e[k] for k in ('url', 'sha256', 'quote')} if e else None,
                     note='First CS-related review (princeton_build.py): home = first department of the census addition; evidence = its latest dated listing there.'))
rows += list(new_h.values())
dump(rows, HERE / 'hierarchy/princeton/cs-related-home-departments.json')
dump(load(W / 'epfl-home-departments.json'), HERE / 'hierarchy/epfl/cs-related-home-departments.json')
out['home_departments'] = dict(princeton=len(rows), epfl=len(load(W / 'epfl-home-departments.json')))

# --- reviews
p = HERE / 'hierarchy/princeton/cs-related-review.json'
rv = load(p)
sup = load(W / 'princeton-review-supplement.json')
have = {(d['name'], d.get('review_round')) for d in rv['decisions']}
for d in sup:
    d['review_round'] = ROUND
rv['decisions'] += [d for d in sup if (d['name'], ROUND) not in have]
rv['supplement'] = dict(
    round=ROUND, reviewed='2026-10-26',
    scope='Candidates of the current DBLP-based hierarchy/princeton/cs-related-candidates.json (81) that the first review does not cover (37, matched by OpenAlex id '
          'and name), plus a re-decision of Ronnie Sircar (rejected above only as not_cs_related; on the DBLP list). The first review\'s decisions are unchanged.',
    rule=RULE, captures='hierarchy/princeton/cs-related-captures.sqlite', tools='hierarchy/cs-related-tools/pe_index.py, pe_princeton.py, pe_merge.py, pecap.py',
    counts=dict(collections.Counter(d['decision'] for d in sup)),
    first_review_spot_check='2026-10-23: all 33 accepted rows of census/princeton-additions.json re-verified (337 evidence items: listing sources + pi_basis); every quote is an '
                            'exact substring of the stored capture text in hierarchy/cs-related-captures-princeton.sqlite and every sha256 matches the stored bytes recomputed.')
dump(rv, p)
er = load(W / 'epfl-review.json')
dump(dict(reviewed='2026-10-26', rule=RULE, captures='hierarchy/epfl/cs-related-captures.sqlite',
          tools='hierarchy/cs-related-tools/pe_index.py, pe_epfl.py, pe_merge.py, pecap.py (+ epfl_listtext.py for faculty-list entries)',
          sources='Faculty lists: listings/epfl/captures.sqlite and hierarchy/cs-related-captures-epfl.sqlite (school, institute and EPFL-wide lists 2016-2026, the EDEE '
                  'thesis-director list); Infoscience doctoral thesis records (hierarchy/epfl/thesis-captures.sqlite); live people.epfl.ch profiles.',
          counts=dict(candidates=len(er), **collections.Counter(d['decision'] for d in er)), decisions=er),
     HERE / 'hierarchy/epfl/cs-related-review.json')
out['reviews'] = dict(princeton_appended=len(sup), epfl=len(er))
print(json.dumps(out, indent=1))
