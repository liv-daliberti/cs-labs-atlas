"""Merge the staged Berkeley CS-related outputs into place (only this review's own keys/rows)."""
import json, sys, os
H = '/n/fs/similarity/maxent-grpo/.research-sweeps/claude-schools-20261021'
S = sys.argv[1]
adds = json.load(open(f'{S}/additions.json'))
for a in adds:
    lab = a.pop('lab_name', None)
    a.pop('pi_basis_more', None); a.pop('capture_store', None)
    a['identity_note'] += (f' Own lab: {lab}.' if lab else '') + ' Evidence store: hierarchy/berkeley/cs-related-captures.sqlite.'
# 1. census additions (append; keep existing rows; replace earlier rows of this review by name)
p = f'{H}/census/berkeley-additions.json'
cur = json.load(open(p))
mine = {a['name'] for a in adds}
cur = [r for r in cur if not (r.get('added') == 'cs_related_scope_20261022' and r['name'] in mine)]
clash = [r['name'] for r in cur if r['name'] in mine]
assert not clash, clash
json.dump(cur + adds, open(p + '.tmp', 'w'), indent=1, ensure_ascii=False); os.replace(p + '.tmp', p)
# 2. periods: re-read the shared overrides file right before writing; touch only our names
p = f'{H}/hierarchy/census-overrides.json'
per = json.load(open(f'{S}/overrides.json'))
ov = json.load(open(p))
b = ov.setdefault('berkeley', {})
for name, v in per.items():
    e = b.setdefault(name, {})
    assert 'periods' not in e or all(q['id'].startswith('override_period_berkeley_') for q in e['periods']), name
    e['periods'] = v['periods']; e['why_periods'] = v['why']
json.dump(ov, open(p + '.tmp', 'w'), indent=1, ensure_ascii=False); os.replace(p + '.tmp', p)
# 3. home departments, 4. review
json.dump(json.load(open(f'{S}/home-departments.json')), open(f'{H}/hierarchy/berkeley/cs-related-home-departments.json', 'w'), indent=1, ensure_ascii=False)
rev = json.load(open(f'{S}/review.json'))
import collections
out = dict(reviewed='2026-10-26', scope='owner decision 2026-10-22: all faculty in any department who work on CS-related topics / publish in CS venues, if they are PIs',
           rule='faculty = a Berkeley professor rank 2016-2026 in any department (incl. in residence; adjuncts only when they advise PhDs; teaching professors without PhD advising, lecturers, researchers, postdocs and students do not count); PI = stated PhD advising 2016-2026 or a lab they head alone',
           input='hierarchy/berkeley/cs-related-candidates.json', captures='hierarchy/berkeley/cs-related-captures.sqlite (quotes are exact substrings of the stored text, whitespace collapsed)',
           tools='hierarchy/berkeley/cs-related-tools/{mpcap.py,accepted.py,others.py,build.py,apply.py}',
           caveat='web.archive.org refused connections from this host on 2026-10-26; past-year evidence comes only from Wayback captures already stored by earlier sweeps (EECS lists) and live pages',
           counts=dict(collections.Counter(r['decision'] for r in rev)), decisions=rev)
json.dump(out, open(f'{H}/hierarchy/berkeley/cs-related-review.json', 'w'), indent=1, ensure_ascii=False)
print('additions now', len(cur) + len(adds), '| periods written', len(per), '| review', len(rev), out['counts'])
