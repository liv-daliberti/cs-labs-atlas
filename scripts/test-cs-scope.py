#!/usr/bin/env python3
"""Check the CS-only atlas and what it shows (owner decisions 2026-10-21 and 2026-10-22; rules in
scripts/cs_scope.py, built by scripts/build-cs-scope.py after scripts/build-cs-hierarchy.py).

Data: every lab in every university shard carries csScope / csScopeReason equal to the scope rule
and csShown / csHidden equal to cs_scope.unit_visibility: at the CS departments' schools every
inventory unit is hidden (replaced_by_pi_labs); elsewhere a CS unit is shown exactly when it has a
linked paper. Each school's data/cs-pi-labs file holds every PI lab of its cs-hierarchy file, in
order, under cs_scope.atlas_lab_ids, shown exactly when it has lab papers, with its counts. No shown
lab has zero papers; every shown lab at those schools is a cs-hierarchy PI lab. Per-university
csScope counts equal count cells over exactly the shown labs, the hidden counts equal the hidden
records by reason, and totals, summaries and CS metrics hold shown labs only; every recorded digest
matches (the cs-hierarchy files the atlas reads included); the full inventory counts are untouched.
Departments: inventory labs are grouped (as atlas-affiliations.js + cs-scope.js do) only under
computing departments, or under the recorded department of a CS-field lab or a PI lab homed elsewhere;
the listed non-CS units (MIT IDSS, Media Lab, RLE, Lincoln Lab, plain engineering) never match.
App: runs scripts/test-cs-scope-app.cjs, which drives the real app.js against this data.
Pages: index.html offers no field choice and links only the two kept pages (test-site-pages.py checks
every link).
"""
import gzip
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

R = Path(__file__).resolve().parents[1]
A = R / 'atlas'
sys.path.insert(0, str(R / 'scripts'))
import cs_scope  # noqa: E402

spec = importlib.util.spec_from_file_location('lazy_atlas', R / 'scripts/lazy_atlas.py')
lazy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lazy)


def read(rel):
    raw = (A / rel).read_bytes()
    return json.loads(gzip.decompress(raw) if rel.endswith('.gz') else raw)


def sha(rel):
    return hashlib.sha256((A / rel).read_bytes()).hexdigest()


def canon(cells):
    return sorted(json.dumps(c, sort_keys=True) for c in cells)


def labels(lab, uid):
    """atlas/assets/atlas-affiliations.js labels(), then the CS view's department filter."""
    princeton = uid == 'princeton-university'
    raw = [lab.get('department')] + (lab.get('departments') if isinstance(lab.get('departments'), list) else [])
    out = []
    for x in raw:
        if not isinstance(x, str) or not x.strip():
            continue
        for part in (x.split(';') if princeton else [x]):
            part = part.strip()
            if princeton and part == 'Department of Computer Science':
                part = 'Computer Science'
            if part and part not in out:
                out.append(part)
    return cs_scope.department_labels(out) if out else out


I = read('data.json')
cs = I['csScope']
assert cs['rule'] == cs_scope.browser_rule(), 'data.json rule is not the current scripts/cs_scope.py rule; re-run build-cs-scope.py'
assert read(cs['ruleFile']) == cs_scope.browser_rule(), 'cs-scope-rule.json is stale'
for rel in [cs['ruleFile'], cs['metricsFile'], I['metricsFile']] + [u['labsFile'] for u in I['universities']] + [u['csScope']['labsFile'] for u in I['universities'] if 'labsFile' in u['csScope']]:
    assert I['assets'][rel] == sha(rel), ('asset digest', rel)

# Rule spot checks.
for name in ['Computer Science', 'EECS / CSAIL', 'Electrical Engineering and Computer Science', 'Institut für Informatik',
             'School of Informatics', "Département d'informatique", 'Robotics Institute', 'Language Technologies Institute',
             'Machine Learning Department', 'Human-Computer Interaction Institute', 'Human–Computer Interaction Institute',
             'Department of Information Science and Technology', 'School of Information', 'Statistics; EECS',
             '计算机学院', '软件学院', '人工智能学院', '컴퓨터학과', 'Software and Societal Systems Department', 'Halıcıoğlu Data Science Institute',
             'Computational Biology Department', 'Institute for Quantum Computing']:
    assert cs_scope.computing_department(name), name
for name in ['Institute for Data, Systems and Society', 'Media Lab', 'MIT Media Lab', 'Research Laboratory of Electronics',
             'MIT Lincoln Laboratory', 'Mechanical Engineering', 'Civil and Environmental Engineering', 'Chemical Engineering',
             'Materials Science and Engineering', 'Electrical Engineering', 'Electrical and Electronic Engineering',
             'Physics', 'Molecular Biology', 'Speech-Language Pathology', 'Geosciences', 'Electronics and Information']:
    assert not cs_scope.computing_department(name), name

universities = 0
PI_LABS = cs_scope.pi_lab_ids()
SCHOOLS = {x['uni']: x for x in cs_scope.hierarchy_schools()}
assert SCHOOLS and set(SCHOOLS) <= {u['id'] for u in I['universities']} and len(SCHOOLS) == len(cs['hierarchy'])
for x in SCHOOLS.values():
    assert cs['hierarchy'][x['id']]['file'] == x['file'] and cs['hierarchy'][x['id']]['sha256'] == sha(x['file']) == I['assets'][x['file']], \
        ('cs-hierarchy changed after the scope build; run scripts/build-cs-scope.py', x['id'])
total, scope_reasons, shown_reasons, outside = 0, Counter(), Counter(), 0
hidden_total, scope_total = Counter(), 0
all_cells, all_units, shown_ids, pi_member_ids = [], [], set(), set()
non_computing_branches = Counter()
study = {}
for u in I['universities']:
    shard = read(u['labsFile'])
    assert shard['id'] == u['id']
    labs = shard['labs']
    school = SCHOOLS.get(u['id'])
    # The full inventory and its original counts are untouched.
    assert canon(cs_scope.count_cells(labs, u['id'])) == canon(u['counts']), ('original counts changed', u['id'])
    hidden = Counter()
    for lab in labs:
        assert isinstance(lab.get('csScope'), bool) and 'csScopeReason' in lab, ('unmarked lab', u['id'], lab['id'])
        why = cs_scope.reason(lab, PI_LABS.get(u['id'], frozenset()))
        assert lab['csScope'] == (why is not None) and lab['csScopeReason'] == why, ('stale mark', lab['id'])
        visible, hidden_by = cs_scope.unit_visibility(lab, why, school is not None)
        assert lab.get('csShown') is visible and lab.get('csHidden') == hidden_by, ('stale shown mark', u['id'], lab['id'])
        # the rule itself, spelled out: a school of the CS departments view shows no inventory unit;
        # elsewhere a CS unit is shown exactly when it has a linked paper
        assert visible == (why is not None and school is None and cs_scope.unit_has_papers(lab))
        if hidden_by:
            hidden[hidden_by] += 1
        scope_reasons[why] += 1
    in_scope = [lab for lab in labs if lab['csScope']]
    scope_total += len(in_scope)
    outside += len(labs) - len(in_scope)
    block = u['csScope']
    if school:
        H = cs_scope.read_hierarchy(school)
        P = read(block['labsFile'])
        assert block['labsFile'] == f"data/cs-pi-labs/{u['id']}.json.gz" and block['school'] == school['id'] and block['piLabs'] == len(H['labs'])
        assert P['id'] == u['id'] and P['school'] == school['id'] and P['hierarchyFile'] == school['file'] and P['hierarchySha256'] == sha(school['file'])
        assert [r['id'] for r in P['labs']] == cs_scope.atlas_lab_ids(H['labs']) and len({r['id'] for r in P['labs']}) == len(P['labs'])
        shown = []
        for i, (r, h) in enumerate(zip(P['labs'], H['labs'])):
            assert r['hierarchy'] == dict(school=school['id'], index=i, id=h['id'], file=school['file'])
            assert r['csScope'] is True and r['csScopeReason'] == cs_scope.PI_LAB and r['name'] == h['name'] and r['pi'] == h['pi']['name'] and r['department'] == h['dept']
            assert (r['csShown'], r['csHidden']) == cs_scope.pi_lab_visibility(h) and r['csShown'] == bool(h['papers'])
            if not r['csShown']:
                hidden[r['csHidden']] += 1
                continue
            years = Counter(str(H['papers'][p[0]]['y']) for p in h['papers'])
            assert r['labPapers'] == len(h['papers']) > 0 and r['students'] == len(h['students']) and r['studentPaperLinks'] == len(h['links'])
            assert r['paperCounts'] == dict(combined=dict(sorted(years.items())), reviewed={}, strict={}) and r['years'] == sorted(int(y) for y in years)
            assert r['unitType'] == 'pi_lab' and r['departments'] == [h['dept']] and r['departmentCoverage'] == h['coverage']
            shown.append(r)
        metrics = P['metrics']
        assert canon(metrics['units']) == canon(cs_scope.count_cells(shown, u['id'], departments=True))
        assert all(m['uni'] == u['id'] and m['lab'] in {r['id'] for r in shown} for b in metrics['buckets'] for m in b['members'])
        pi_member_ids |= {(u['id'], r['id']) for r in shown}
        study[school['id']] = dict(piLabs=len(H['labs']), shown=len(shown), noLabPapers=hidden['no_lab_papers'],
                                   inventoryBefore=len(in_scope), inventoryWithPapersBefore=sum(map(cs_scope.unit_has_papers, in_scope)))
        # Departments the CS view shows: the PI lab's home department, exactly one per lab.
        for r in shown:
            assert labels(r, u['id']) == [r['department']]
    else:
        shown = [lab for lab in labs if lab['csShown']]
        keep = {lab['id'] for lab in shown}
        buckets = [dict(b, members=[m for m in b['members'] if m['lab'] in keep]) for b in shard['metrics']['buckets']]
        metrics = dict(units=cs_scope.count_cells(shown, u['id'], departments=True), buckets=[b for b in buckets if b['members']])
        # Departments the CS view can show.
        for lab in shown:
            for name in labels(lab, u['id']):
                if not cs_scope.computing_department(name):
                    # a CS-field lab, or a CS department's PI homed elsewhere (e.g. Psychology), keeps its own department
                    assert lab['csScopeReason'] in ('field', cs_scope.PI_LAB), ('non-computing department label on a department-scoped lab', u['id'], lab['id'], name)
                    non_computing_branches[(u['id'], name)] += 1
    # No shown lab has zero papers.
    assert all(r['labPapers'] > 0 if 'hierarchy' in r else cs_scope.unit_has_papers(r) for r in shown), ('shown lab without papers', u['id'])
    assert block['labs'] == len(shown), ('csScope.labs', u['id'])
    assert block['inScope'] == len(in_scope) and block['hidden'] == {k: hidden[k] for k in cs_scope.HIDDEN_REASONS}, ('hidden counts', u['id'])
    assert block['counts'] == cs_scope.count_cells(shown, u['id']), ('csScope counts', u['id'])
    assert sum(c['n'] for c in block['counts']) == len(shown)
    for key, test in [('named', lambda l: bool(l.get('pi'))), ('active', lambda l: bool(l.get('years'))),
                      ('reviewed', lambda l: l.get('leadershipStatus') in ('leadership_reviewed', 'publication_identity_verified')),
                      ('verified', lambda l: l.get('leadershipStatus') == 'publication_identity_verified')]:
        assert sum(c[key] for c in block['counts']) == sum(map(test, shown)), (key, u['id'])
    for view in ('combined', 'reviewed', 'strict'):
        want = lazy.summarize_metrics(metrics, view, *I.get('window', [2016, 2026]))
        got = block['overview'][view]
        assert got['stats']['works'] == want['stats']['works'] and [a['works'] for a in got['annual']] == [a['works'] for a in want['annual']], (u['id'], view)
        assert [a['activity'] for a in got['annual']] == [a['activity'] for a in want['annual']], (u['id'], view)
    all_cells += block['counts']
    all_units += cs_scope.count_cells(shown, u['id'], departments=True)
    shown_ids |= {(u['id'], r['id']) for r in shown}
    shown_reasons.update(r['csScopeReason'] for r in shown)
    hidden_total.update(hidden)
    universities += bool(shown)
    total += len(shown)

summary = cs['summary']
assert total == summary['labs'] == len(shown_ids) == sum(c['n'] for c in cs['counts'])
assert universities == summary['universities']
assert canon(all_cells) == canon(cs['counts'])
assert {k: shown_reasons[k] for k in cs_scope.REASONS} == summary['byReason'] and shown_reasons[None] == 0
assert {k: scope_reasons[k] for k in cs_scope.REASONS} == summary['inScopeByReason'] and outside == summary['outOfScope'] == scope_reasons[None]
assert scope_total == summary['inScopeUnits'] and {k: hidden_total[k] for k in cs_scope.HIDDEN_REASONS} == summary['hidden']
assert summary['piLabs'] == dict(schools=len(SCHOOLS), labs=sum(x['piLabs'] for x in study.values()), shown=sum(x['shown'] for x in study.values()))
M = read(cs['metricsFile'])
assert canon(M['units']) == canon(all_units)
assert all((m['uni'], m['lab']) in shown_ids for b in M['buckets'] for m in b['members']), 'a hidden or non-CS member in the CS metrics'
for view in ('combined', 'reviewed', 'strict'):
    want, got = lazy.summarize_metrics(M, view, *I.get('window', [2016, 2026])), cs['overview'][view]
    for key in ('works', 'publishing', 'groupLinks', 'topicCount', 'oa'):
        assert got['stats'][key] == want['stats'][key], ('CS overview', view, key)
    assert [(a['year'], a['works'], a['activity'], a['publishing'], a['links']) for a in got['annual']] == \
        [(a['year'], a['works'], a['activity'], a['publishing'], a['links']) for a in want['annual']], ('CS annual', view)
for x in SCHOOLS.values():  # each PI-lab paper is one distinct work in the CS metrics, at most once per school
    uni_buckets = [dict(b, members=[m for m in b['members'] if m['uni'] == x['uni']]) for b in M['buckets'] if b['view'] == 'combined']
    H = cs_scope.read_hierarchy(x)
    keys = set()
    for h in H['labs']:
        for p in h['papers']:
            q = H['papers'][p[0]]
            keys.add('openalex:' + q['oa'].rsplit('/', 1)[-1].upper() if q.get('oa') else 'doi:' + q['doi'].lower() if q.get('doi') else x['id'] + ':' + str(q.get('w')))
    assert sum(y['works'] for b in uni_buckets if b['members'] for y in b['years'].values()) == len(keys), ('PI-lab distinct works', x['id'])

# index.html: no discipline choice, no all-science views, only the two kept pages.
page = (A / 'index.html').read_text()
assert 'All sciences' not in page and re.search(r'<select id="field" disabled[^>]*><option value="">Computer science</option></select>', page)
for target in ['data-tab="organizations"', 'data-tab="audit"', 'downloads/labs.csv', 'downloads/works.csv', 'homogenizing_science.xlsx']:
    assert target not in page, ('index.html still links', target)
assert set(re.findall(r'[A-Za-z0-9_-]+\.html', page)) <= {'cs-departments.html'}, 'index.html links a removed page'
assert 'assets/cs-scope.js' in page and page.index('assets/cs-scope.js') < page.index('src="app.js"')
assert 'assets/cs-pi-labs.js' in page and page.index('assets/cs-pi-labs.js') < page.index('src="app.js"')

app = subprocess.run(['node', str(R / 'scripts/test-cs-scope-app.cjs')], capture_output=True, text=True)
if app.returncode:
    sys.stderr.write(app.stdout[-4000:] + app.stderr[-4000:])
    raise SystemExit('app harness failed')
app_report = json.loads(app.stdout)
assert app_report['passed'] and app_report['labsShown'] == total and app_report['piLabsShown'] == summary['piLabs']['shown']
print(json.dumps({'passed': True, 'labsShown': total, 'universities': universities, 'byReason': dict(shown_reasons),
                  'inScopeUnits': scope_total, 'hidden': dict(hidden_total), 'outOfScopeLabs': outside,
                  'schools': study, 'nonComputingDepartmentBranches': len(non_computing_branches),
                  'app': {k: v for k, v in app_report.items() if k != 'schools'}}, indent=1, ensure_ascii=False))
