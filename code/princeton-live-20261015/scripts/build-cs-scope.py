#!/usr/bin/env python3
"""Mark the atlas's computer-science scope and what it shows; write CS-only counts.

Owner requests 2026-10-21 (only computer science) and 2026-10-22 ("PI labs with papers only";
the site is two pages). Both rules live in scripts/cs_scope.py. This script
  * adds to every lab in atlas/data/universities/*.json.gz `csScope` (true/false) and
    `csScopeReason` ("field", "department", "field_and_department", "cs_department_pi_lab" or
    null), and `csShown` / `csHidden` (cs_scope.unit_visibility: a hidden CS unit has reason
    "no_papers" or "replaced_by_pi_labs"), keeping each shard's own serialization and gzip header;
  * writes, for each school of the CS departments view (atlas/data/cs-hierarchy, built first by
    scripts/build-cs-hierarchy.py), atlas/data/cs-pi-labs/<university>.json.gz: that school's PI
    labs as atlas lab records (shown ones with paper counts by year and lab-paper / student / link
    counts; hidden ones, "no_lab_papers", with their name only) and their metrics. The atlas loads
    this file instead of the school's shard and reads papers and students from the school's
    cs-hierarchy file when a lab is opened (atlas/assets/cs-pi-labs.js);
  * writes, per university in data.json, `csScope` = {labs, counts, overview, inScope, hidden
    [, labsFile, school, piLabs]}: count cells with the semantics of `counts`
    (cs_scope.count_cells) over exactly the labs the atlas shows, the per-view summaries of their
    metrics, the number of in-scope inventory units and the hidden counts by reason;
  * writes data.json `csScope` = {rule, ruleFile, metricsFile, counts, overview, summary,
    hierarchy} and the assets data/cs-metrics.json.gz (unit cells and publication buckets of the
    shown labs, shaped like data/metrics.json.gz) and data/cs-scope-rule.json (the browser's copy
    of the rule), and records every changed or new asset's sha256 in data.json `assets`
    (including the cs-hierarchy school files the atlas reads).
Nothing is deleted: hidden labs, non-CS labs, counts and metrics stay as they are.

    python3 scripts/build-cs-scope.py            # apply (idempotent)
    python3 scripts/build-cs-scope.py --check    # compute and report, write nothing
    python3 scripts/build-cs-scope.py --restore  # remove every addition, byte for byte

Build order: scripts/build-cs-hierarchy.py, then this script. Re-run it after anything rewrites
the cs-hierarchy files, university shards, data.json counts or metrics (it is the last step after
the Princeton checkpoints). Before replaying an earlier checkpoint whose guard compares live
files, run --restore first, as for the other checkpoints.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
import sys
import zlib
from collections import Counter, defaultdict
from pathlib import Path

R = Path(__file__).resolve().parents[1]
A = R / 'atlas'
sys.path.insert(0, str(R / 'scripts'))
import cs_scope  # noqa: E402

_spec = importlib.util.spec_from_file_location('lazy_atlas', R / 'scripts/lazy_atlas.py')
lazy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lazy)

METRICS = 'data/cs-metrics.json.gz'
RULE = 'data/cs-scope-rule.json'
PI_LABS = 'data/cs-pi-labs'
REPORT = R / 'research/cs-scope-20261021/report.json'
LAB_KEYS = ('csScope', 'csScopeReason', 'csShown', 'csHidden')
VIEWS = ('combined', 'reviewed', 'strict')
PI_STATUS = 'publication_identity_verified'  # the PI's publication identity is anchored (DBLP page etc.)
STUDY = ['princeton-university', 'carnegie-mellon-university', 'swiss-federal-institute-of-technology-lausanne',
         'massachusetts-institute-of-technology-mit', 'university-of-california-berkeley']
COMPARE = ['harvard-university', 'stanford-university', 'eth-zurich', 'university-of-oxford', 'tsinghua-university']


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


# ---- byte-faithful JSON / gzip round trips -------------------------------------------------

def manifest_bytes(value):
    """data.json: compact, UTF-8, insertion order, trailing newline (as every writer uses)."""
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')


def shard_style(text):
    """Return (sort_keys, newline) of a shard: lazy_atlas writes sorted + newline; the
    collection projectors write insertion order without one."""
    value = json.loads(text)
    for sort_keys in (True, False):
        for newline in ('\n', ''):
            if json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=sort_keys) + newline == text:
                return value, (sort_keys, newline)
    raise SystemExit('Unrecognised shard serialization; refusing to rewrite it')


def shard_json(value, style):
    sort_keys, newline = style
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=sort_keys) + newline).encode('utf-8')


def gzip_like(raw, original):
    """Level-9 deflate with the original gzip header (mtime 0; OS byte as written before)."""
    body = zlib.compressobj(9, zlib.DEFLATED, 31)
    out = body.compress(raw) + body.flush()
    header = original[:10] if original and original[:4] == b'\x1f\x8b\x08\x00' else out[:10]
    return header + out[10:]


def atomic_write(path, raw):
    if path.exists() and path.read_bytes() == raw:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.cs-scope.tmp')
    tmp.write_bytes(raw)
    os.replace(tmp, path)
    return True


# ---- metrics -------------------------------------------------------------------------------

def cs_buckets(buckets, keep):
    """Keep only shown members; a bucket stays once if any member remains. Buckets whose
    remaining members coincide are merged, as lazy_atlas does per university."""
    merged = {}
    for bucket in buckets:
        members = [m for m in bucket['members'] if keep(m)]
        if not members:
            continue
        key = (bucket['view'], lazy._signature(members))
        if key not in merged:
            merged[key] = dict(view=bucket['view'], members=sorted(members, key=lambda m: (m['uni'], m['lab'])), years={})
        for year, stats in bucket['years'].items():
            lazy._merge_year(merged[key]['years'].setdefault(year, lazy._empty_year()), stats)
    return [merged[key] for key in sorted(merged)]


def overview(metrics, window):
    return {view: lazy.summarize_metrics(metrics, view, window[0], window[1]) for view in VIEWS}


def strip_lab(lab):
    for key in LAB_KEYS:
        lab.pop(key, None)


# ---- PI labs of the CS departments view ----------------------------------------------------

def work_key(paper, school):
    """One key per distinct paper across the schools: OpenAlex id, else DOI, else the school's work id."""
    if paper.get('oa'):
        return 'openalex:' + paper['oa'].rsplit('/', 1)[-1].upper()
    if paper.get('doi'):
        return 'doi:' + paper['doi'].lower()
    return school + ':' + str(paper.get('w'))


def pi_lab_records(school, h):
    """Atlas lab records (shown and hidden) and per-record hierarchy labs of one school."""
    out = []
    for i, (atlas_id, lab) in enumerate(zip(cs_scope.atlas_lab_ids(h['labs']), h['labs'])):
        shown, hidden = cs_scope.pi_lab_visibility(lab)
        ref = dict(school=school['id'], index=i, id=lab['id'], file=school['file'])
        base = dict(id=atlas_id, name=lab['name'], pi=lab['pi']['name'], department=lab['dept'], hierarchy=ref,
                    csScope=True, csScopeReason=cs_scope.PI_LAB, csShown=shown, csHidden=hidden)
        if not shown:
            out.append((base, lab))
            continue
        years = [h['papers'][p[0]].get('y') for p in lab['papers']]
        by_year = Counter(str(y) for y in years if isinstance(y, int))
        dblp = lab['pi'].get('dblp') or []
        base.update(
            type='pi_lab', unitType='pi_lab', field=cs_scope.FIELD, leadershipStatus=PI_STATUS,
            pis=[dict(name=lab['pi']['name'], source=dblp[0])] if dblp else [], leadership=[], evidence=[],
            departments=[lab['dept']], departmentCoverage=lab['coverage'], otherDepartments=lab.get('otherDepts') or [],
            years=sorted({y for y in years if isinstance(y, int)}), url=lab.get('url') or '', source=dblp[0] if dblp else '',
            paperCounts=dict(combined=dict(sorted(by_year.items())), reviewed={}, strict={}),
            labPapers=len(lab['papers']), students=len(lab['students']), studentPaperLinks=len(lab['links']),
            verifiedStudentPaperLinks=sum(k[2] == 'v' for k in lab['links']))
        out.append((base, lab))
    return out


def pi_buckets(schools):
    """Publication buckets (combined view) of the shown PI labs, one distinct paper counted once
    across the schools; PI-lab papers carry no open-access flag (oaUnknown)."""
    by_work, stats = defaultdict(dict), {}
    for school, uid, h, records in schools:
        for rec, lab in records:
            if not rec['csShown']:
                continue
            member = dict(lab=rec['id'], uni=uid, field=rec['field'], status=rec['leadershipStatus'],
                          department=rec['department'], groups=['pi-lab:' + uid + ':' + rec['id']])
            for p in lab['papers']:
                paper = h['papers'][p[0]]
                key = work_key(paper, school['id'])
                by_work[key][(uid, rec['id'])] = member
                stats.setdefault(key, (paper.get('y'), paper.get('nb') or 0))
    buckets = {}
    for key, members in by_work.items():
        year, authors = stats[key]
        if not isinstance(year, int):
            continue
        members = sorted(members.values(), key=lambda m: (m['uni'], m['lab']))
        sig = ('combined', lazy._signature(members))
        bucket = buckets.setdefault(sig, dict(view='combined', members=members, years={}))
        y = bucket['years'].setdefault(str(year), dict(lazy._empty_year(), oaUnknown=0))
        y['works'] += 1
        y['oaUnknown'] += 1
        if authors > 0:
            y['authorsKnown'] += 1
            y['authorsSum'] += authors
    return [buckets[k] for k in sorted(buckets)]


# ---- main ----------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--check', action='store_true', help='compute and report; write nothing')
    parser.add_argument('--restore', action='store_true', help='remove every CS-scope addition')
    args = parser.parse_args()
    write = not args.check

    data_path = A / 'data.json'
    data_raw = data_path.read_bytes()
    data = json.loads(data_raw)
    assert manifest_bytes(data) == data_raw, 'data.json is not in the expected compact form'
    window = data.get('window', [2016, 2026])
    previous_pi_files = {name for name in data['assets'] if name.startswith(PI_LABS + '/')}
    previous_hierarchy = data.get('csScope', {}).get('hierarchy', {})
    for u in data['universities']:
        u.pop('csScope', None)
    data.pop('csScope', None)
    for name in [METRICS, RULE, *previous_pi_files, *(x['file'] for x in previous_hierarchy.values())]:
        data['assets'].pop(name, None)

    schools = [] if args.restore else cs_scope.hierarchy_schools()
    school_by_uni = {s['uni']: s for s in schools}
    pi_labs = cs_scope.pi_lab_ids() if schools else {}  # the CS departments' PI labs (built first)
    hierarchies = {s['uni']: cs_scope.read_hierarchy(s) for s in schools}
    labs_by_uni, shard_writes, report_unis = {}, {}, {}
    reasons, hidden_total, borderline = Counter(), Counter(), defaultdict(Counter)
    shown_ids, scope_ids = set(), set()
    for u in data['universities']:
        path = A / u['labsFile']
        original = path.read_bytes()
        assert sha(original) == data['assets'][u['labsFile']], ('shard digest out of date before this build', u['id'])
        raw = gzip.decompress(original) if u['labsFile'].endswith('.gz') else original
        shard, style = shard_style(raw.decode('utf-8'))
        assert shard['id'] == u['id']
        in_scope, shown, hidden = [], [], Counter()
        for lab in shard['labs']:
            strip_lab(lab)
            if args.restore:
                continue
            why = cs_scope.reason(lab, pi_labs.get(u['id'], frozenset()))
            visible, hidden_by = cs_scope.unit_visibility(lab, why, u['id'] in school_by_uni)
            lab['csScope'] = why is not None
            lab['csScopeReason'] = why
            lab['csShown'] = visible
            lab['csHidden'] = hidden_by
            reasons[why] += 1
            if why:
                in_scope.append(lab)
                scope_ids.add(lab['id'])
                department = lab.get('department') or ''
                if cs_scope.borderline_department(department):
                    borderline[department][why] += 1
            if visible:
                shown.append(lab)
            elif hidden_by:
                hidden[hidden_by] += 1
        out = shard_json(shard, style)
        new = gzip_like(out, original) if u['labsFile'].endswith('.gz') else out
        shard_writes[path] = new
        data['assets'][u['labsFile']] = sha(new)
        labs_by_uni[u['id']] = dict(shard=shard, inScope=in_scope, shown=shown, hidden=hidden)

    pi_writes, pi_schools = {}, []
    if not args.restore:
        # PI labs of the CS departments view replace the inventory units of their schools.
        for s in schools:
            uid = s['uni']
            assert uid in labs_by_uni, ('school without a university shard', s['id'])
            records = pi_lab_records(s, hierarchies[uid])
            pi_schools.append((s, uid, hierarchies[uid], records))
        buckets = pi_buckets(pi_schools)
        scoped = lazy._by_university(buckets)
        for s, uid, h, records in pi_schools:
            entry = labs_by_uni[uid]
            entry['shown'] = [rec for rec, _ in records if rec['csShown']]
            entry['hidden'].update(rec['csHidden'] for rec, _ in records if not rec['csShown'])
            entry['piLabs'] = len(records)
            entry['metrics'] = dict(units=cs_scope.count_cells(entry['shown'], uid, departments=True), buckets=scoped.get(uid, []))
            raw = gzip.compress(lazy._json_bytes(dict(
                schema=1, id=uid, school=s['id'], hierarchyFile=s['file'], hierarchySha256=sha((A / s['file']).read_bytes()),
                rule=cs_scope.SHOWN_RULE, labs=[rec for rec, _ in records], metrics=entry['metrics'])), compresslevel=9, mtime=0)
            name = f'{PI_LABS}/{uid}.json.gz'
            pi_writes[A / name] = raw
            data['assets'][name] = sha(raw)
            data['assets'][s['file']] = sha((A / s['file']).read_bytes())  # read by the atlas when a lab opens
            entry['labsFile'] = name

        metrics_path = A / data['metricsFile']
        assert sha(metrics_path.read_bytes()) == data['assets'][data['metricsFile']], 'metrics digest out of date'
        global_metrics = json.loads(gzip.decompress(metrics_path.read_bytes()))
        inventory_shown = {lab['id'] for u in data['universities'] if u['id'] not in school_by_uni
                           for lab in labs_by_uni[u['id']]['shown']}
        keep = lambda m: m['lab'] in inventory_shown and m['uni'] not in school_by_uni  # noqa: E731
        units, all_counts = [], []
        for u in data['universities']:
            entry = labs_by_uni[u['id']]
            shown = entry['shown']
            if 'metrics' not in entry:
                entry['metrics'] = dict(units=cs_scope.count_cells(shown, u['id'], departments=True),
                                        buckets=cs_buckets(entry['shard']['metrics']['buckets'], keep))
            counts = cs_scope.count_cells(shown, u['id'])
            block = dict(labs=len(shown), counts=counts, overview=overview(entry['metrics'], window),
                         inScope=len(entry['inScope']), hidden={k: entry['hidden'][k] for k in cs_scope.HIDDEN_REASONS})
            if u['id'] in school_by_uni:
                block.update(labsFile=entry['labsFile'], school=school_by_uni[u['id']]['id'], piLabs=entry['piLabs'])
            u['csScope'] = block
            hidden_total.update(entry['hidden'])
            all_counts += counts
            units += entry['metrics']['units']
            shown_ids.update((u['id'], lab['id']) for lab in shown)
        metrics = dict(units=units, buckets=cs_buckets(global_metrics['buckets'], keep) + buckets)
        metrics['buckets'].sort(key=lambda b: (b['view'], lazy._signature(b['members'])))
        metrics_raw = gzip.compress(lazy._json_bytes(metrics), compresslevel=9, mtime=0)
        rule = cs_scope.browser_rule()
        rule_raw = (json.dumps(rule, ensure_ascii=False, indent=1, sort_keys=True) + '\n').encode('utf-8')
        data['assets'][METRICS] = sha(metrics_raw)
        data['assets'][RULE] = sha(rule_raw)
        shown_reasons = Counter(lab['csScopeReason'] for u in data['universities'] for lab in labs_by_uni[u['id']]['shown'])
        summary = dict(
            labs=len(shown_ids), labsInCollection=sum(len(x['shard']['labs']) for x in labs_by_uni.values()),
            universities=sum(1 for x in labs_by_uni.values() if x['shown']),
            byReason={k: shown_reasons[k] for k in cs_scope.REASONS},
            inScopeUnits=len(scope_ids), inScopeByReason={k: reasons[k] for k in cs_scope.REASONS}, outOfScope=reasons[None],
            hidden={k: hidden_total[k] for k in cs_scope.HIDDEN_REASONS},
            universitiesWithoutShownLabs=sum(1 for x in labs_by_uni.values() if x['inScope'] and not x['shown']),
            piLabs=dict(schools=len(pi_schools), labs=sum(len(r) for *_, r in pi_schools),
                        shown=sum(rec['csShown'] for *_, r in pi_schools for rec, _ in r)))
        data['csScope'] = dict(rule=rule, ruleFile=RULE, metricsFile=METRICS, counts=all_counts,
                               overview=overview(metrics, window), summary=summary,
                               hierarchy={s['id']: dict(file=s['file'], sha256=data['assets'][s['file']], labsFile=labs_by_uni[uid]['labsFile'])
                                          for s, uid, *_ in pi_schools},
                               builtBy='scripts/build-cs-scope.py')
        assert sum(c['n'] for c in all_counts) == len(shown_ids)
        for u in data['universities']:
            entry = labs_by_uni[u['id']]
            report_unis[u['id']] = dict(name=u['name'], inventoryLabs=len(entry['shard']['labs']), csUnitsBefore=len(entry['inScope']),
                                        shown=len(entry['shown']), hidden=dict(+entry['hidden']),
                                        byReason=dict(Counter(lab['csScopeReason'] for lab in entry['shown'])))

    new_data = manifest_bytes(data)
    if not args.restore:
        border = sorted(([name, sum(c.values()), dict(c)] for name, c in borderline.items()), key=lambda r: (-r[1], r[0]))
        report = dict(rule=cs_scope.browser_rule(), summary=data['csScope']['summary'],
                      studySchools={uid: report_unis[uid] for uid in STUDY if uid in report_unis},
                      otherUniversities={uid: report_unis[uid] for uid in COMPARE if uid in report_unis},
                      borderlineDepartments=[dict(department=n, labs=t, byReason=c) for n, t, c in border],
                      universities=report_unis)
        print(json.dumps(dict(summary=report['summary'], studySchools=report['studySchools'],
                              otherUniversities=report['otherUniversities'], borderlineDepartments=len(border)), indent=1, ensure_ascii=False))
    if not write:
        return
    # Concurrency guard: refuse if data.json or a cs-hierarchy file changed while this ran.
    assert data_path.read_bytes() == data_raw, 'data.json changed during the build; re-run'
    for s in schools:
        assert sha((A / s['file']).read_bytes()) == data['assets'][s['file']], ('cs-hierarchy changed during the build; re-run', s['id'])
    changed = sum(atomic_write(path, raw) for path, raw in shard_writes.items())
    changed += sum(atomic_write(path, raw) for path, raw in pi_writes.items())
    for name in previous_pi_files - {str(p.relative_to(A)) for p in pi_writes}:
        if (A / name).exists():
            (A / name).unlink()
    if args.restore:
        for name in (METRICS, RULE):
            if (A / name).exists():
                (A / name).unlink()
    else:
        atomic_write(A / METRICS, metrics_raw)
        atomic_write(A / RULE, rule_raw)
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    atomic_write(data_path, new_data)
    print(json.dumps(dict(restored=args.restore, filesRewritten=changed, dataJsonSha256=sha(new_data))))


if __name__ == '__main__':
    # lazy_atlas.summarize_metrics sums floats over set-ordered lab ids; a fixed hash seed
    # keeps the written bytes identical from run to run.
    if os.environ.get('PYTHONHASHSEED') != '0':
        os.environ['PYTHONHASHSEED'] = '0'
        os.execv(sys.executable, [sys.executable] + sys.argv)
    main()
