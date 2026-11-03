"""Write university/lab assets and aggregate-only statistics for the lazy atlas.

The browser initially receives university metadata and aggregate counts only.
This module's full reconstruction helper is for offline validation, not a browser
loading strategy. No network calls or publication filtering occur here.
"""
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import gzip
import json
import math
from pathlib import Path, PurePosixPath
import re

VIEWS = ('strict', 'reviewed', 'combined')
FORMAT = 'lazy-atlas-v1'
_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]*$')
_OWNED = re.compile(r'^data/(?:metrics\.json(?:\.gz)?|pi-groups\.json|(?:universities|labs)/[A-Za-z0-9][A-Za-z0-9_.-]*\.json(?:\.gz)?)$')
_ANALYSIS_EXPORTS = frozenset('downloads/' + name for name in ('works.csv.gz', 'pi_groups.csv.gz', 'lab_papers.csv.gz'))


def _integer(value):
    try:
        return int(value or 0)
    except (ValueError, TypeError):
        return 0


def _flag(edge, view):
    if view == 'combined' and view not in edge:
        return bool(edge.get('strict') or edge.get('reviewed'))
    return bool(edge.get(view))


def _record_path(kind, identifier):
    if not isinstance(identifier, str) or not _ID.fullmatch(identifier):
        raise ValueError('Invalid atlas record ID: ' + repr(identifier))
    return 'data/' + kind + '/' + identifier + ('.json.gz' if kind == 'labs' else '.json')


def _path(root, relative):
    path = PurePosixPath(relative)
    if path.is_absolute() or '..' in path.parts or str(path) != relative:
        raise ValueError('Unsafe atlas asset path: ' + str(relative))
    destination = Path(root) / relative
    if not destination.resolve().is_relative_to(Path(root).resolve()):
        raise ValueError('Atlas asset escapes its bundle')
    return destination


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=True,
                       allow_nan=False) + '\n').encode('utf-8')


def _atomic_bytes(path, raw):
    if path.exists() and path.read_bytes() == raw:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_bytes(raw)
    temporary.replace(path)


def _cells(universities, by_department=False):
    cells = {}
    for university in universities:
        for lab in university['labs']:
            key = (university['id'], lab.get('field', ''), lab.get('leadershipStatus', ''))
            if by_department:
                key += (lab.get('department', ''),)
            if key not in cells:
                cells[key] = dict(u=key[0], field=key[1], status=key[2], n=0,
                                  named=0, verified=0, reviewed=0, active=0, years={})
                if by_department:
                    cells[key]['department'] = key[3]
            cell = cells[key]
            years = {_integer(y) for y in lab.get('years', [])}
            cell['n'] += 1
            cell['named'] += int(bool(str(lab.get('pi') or '').strip()))
            cell['verified'] += int(bool(lab.get('pis')))
            cell['reviewed'] += int(bool(lab.get('leadership') or lab.get('pis')))
            cell['active'] += int(bool(years))
            for year in sorted(years):
                y = str(year)
                cell['years'][y] = cell['years'].get(y, 0) + 1
    return [cells[key] for key in sorted(cells)]


def _empty_year():
    return dict(works=0, oa=0, authorsKnown=0, authorsSum=0,
                countriesKnown=0, international=0, topics={})


def _add_work(year, work):
    year['works'] += 1
    year['oa'] += int(bool(work.get('oa')))
    authors = _integer(work.get('authors'))
    countries = _integer(work.get('countries'))
    if authors > 0:
        year['authorsKnown'] += 1
        year['authorsSum'] += authors
    if countries > 0:
        year['countriesKnown'] += 1
        year['international'] += int(countries > 1)
    topic = work.get('topic')
    if topic:
        year['topics'][topic] = year['topics'].get(topic, 0) + 1


def _merge_year(target, source):
    for field in ('works', 'oa', 'authorsKnown', 'authorsSum', 'countriesKnown', 'international'):
        target[field] += source[field]
    if source.get('oaUnknown'):  # works without an open-access flag (CS departments PI-lab papers)
        target['oaUnknown'] = target.get('oaUnknown', 0) + source['oaUnknown']
    for topic, count in source['topics'].items():
        target['topics'][topic] = target['topics'].get(topic, 0) + count


def _signature(members):
    return tuple((m['lab'], m['uni'], m['field'], m['status'], m['department'], tuple(m['groups']))
                 for m in sorted(members, key=lambda m: (m['uni'], m['lab'])))


def _build_buckets(universities, works):
    by_view_work = {view: defaultdict(list) for view in VIEWS}
    for university in universities:
        for lab in university['labs']:
            seen = set()
            for edge in lab.get('papers', []):
                wid = edge['work']
                if wid in seen:
                    raise ValueError('Duplicate lab-work edge: ' + lab['id'] + '/' + wid)
                if wid not in works:
                    raise ValueError('Lab edge references absent work: ' + wid)
                seen.add(wid)
                for view in VIEWS:
                    if _flag(edge, view):
                        by_view_work[view][wid].append(dict(
                            lab=lab['id'], uni=university['id'], field=lab.get('field', ''),
                            status=lab.get('leadershipStatus', ''), department=lab.get('department', ''),
                            groups=sorted(set(edge.get('groups', {}).get(view, [])))))
    buckets = {}
    for view in VIEWS:
        for wid, members in by_view_work[view].items():
            signature = _signature(members)
            key = (view, signature)
            if key not in buckets:
                buckets[key] = dict(view=view, members=sorted(members, key=lambda m: (m['uni'], m['lab'])), years={})
            year = str(_integer(works[wid].get('year')))
            stats = buckets[key]['years'].setdefault(year, _empty_year())
            _add_work(stats, works[wid])
    return [buckets[key] for key in sorted(buckets)]


def _by_university(buckets):
    """Re-group after removing other universities' members to preserve deduplication."""
    scoped = defaultdict(dict)
    for bucket in buckets:
        members_by_uni = defaultdict(list)
        for member in bucket['members']:
            members_by_uni[member['uni']].append(member)
        for uid, members in members_by_uni.items():
            key = (bucket['view'], _signature(members))
            if key not in scoped[uid]:
                scoped[uid][key] = dict(view=bucket['view'], members=members, years={})
            target = scoped[uid][key]
            for year, stats in bucket['years'].items():
                _merge_year(target['years'].setdefault(year, _empty_year()), stats)
    return {uid: [mapping[key] for key in sorted(mapping)] for uid, mapping in scoped.items()}


def summarize_metrics(metrics, view, first_year, last_year):
    """Summarize aggregate buckets with the same definitions as the atlas UI.

    This helper is also useful for tests. Filtering should select members within
    each bucket and retain a bucket once if any members remain, never once per
    member. Its yearly sufficient statistics represent distinct works.
    """
    totals = _empty_year()
    groups = set()
    group_links = 0
    lab_counts = Counter()
    annual = {year: dict(year=year, activity=sum(c['years'].get(str(year), 0) for c in metrics['units']),
                         publishing=0, works=0, links=0, oa=None)
              for year in range(first_year, last_year + 1)}
    annual_groups = defaultdict(set)
    annual_oa = Counter()
    annual_oa_unknown = Counter()
    for bucket in metrics['buckets']:
        if bucket['view'] != view:
            continue
        member_groups = {gid for m in bucket['members'] for gid in m['groups']}
        members = {m['lab'] for m in bucket['members']}
        for year_string, stats in bucket['years'].items():
            year = int(year_string)
            if not first_year <= year <= last_year or not stats['works']:
                continue
            _merge_year(totals, stats)
            groups.update(member_groups)
            group_links += stats['works'] * len(member_groups)
            for lid in members:
                lab_counts[lid] += stats['works']
            row = annual[year]
            row['works'] += stats['works']
            row['links'] += stats['works'] * len(members)
            annual_oa[year] += stats['oa']
            annual_oa_unknown[year] += stats.get('oaUnknown', 0)
            annual_groups[year].update(member_groups)
    for year, row in annual.items():
        row['publishing'] = len(annual_groups[year])
        known = row['works'] - annual_oa_unknown[year]
        row['oa'] = annual_oa[year] / known if known else None
    topic_total = sum(totals['topics'].values())
    entropy = -sum((n / topic_total) * math.log2(n / topic_total) for n in totals['topics'].values()) if topic_total else None
    link_total = sum(lab_counts.values())
    oa_known = totals['works'] - totals.get('oaUnknown', 0)
    stats = dict(works=totals['works'], publishing=len(groups), groupLinks=group_links,
                 oa=totals['oa'] / oa_known if oa_known else None,
                 meanAuthors=totals['authorsSum'] / totals['authorsKnown'] if totals['authorsKnown'] else None,
                 topicCount=len(totals['topics']), entropy=entropy,
                 international=totals['international'] / totals['countriesKnown'] if totals['countriesKnown'] else None,
                 hhi=sum((n / link_total) ** 2 for n in lab_counts.values()) if link_total else None)
    return dict(stats=stats, annual=list(annual.values()))


def write_lazy_bundle(data, out):
    """Write aggregate manifest, per-university metadata, and per-lab papers."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    previous_assets = set()
    previous_path = out / 'data.json'
    if previous_path.exists():
        try:
            previous_assets = set(json.loads(previous_path.read_text()).get('assets', {}))
        except (ValueError, TypeError):
            pass
    universities = data['universities']
    works = data.get('works', {})
    university_ids = [u['id'] for u in universities]
    lab_ids = [lab['id'] for u in universities for lab in u['labs']]
    if len(set(university_ids)) != len(university_ids) or len(set(lab_ids)) != len(lab_ids):
        raise ValueError('Atlas universities and labs require unique IDs')
    linked = {edge['work'] for u in universities for lab in u['labs'] for edge in lab.get('papers', [])}
    if set(works) != linked:
        raise ValueError('Atlas works must be exactly the metadata referenced by accepted lab edges')
    counts = _cells(universities)
    units = _cells(universities, by_department=True)
    buckets = _build_buckets(universities, works)
    metrics = dict(units=units, buckets=buckets)
    scoped_buckets = _by_university(buckets)
    scoped_units = defaultdict(list)
    scoped_counts = defaultdict(list)
    for cell in units:
        scoped_units[cell['u']].append(cell)
    for cell in counts:
        scoped_counts[cell['u']].append(cell)
    assets = {}

    def save(relative, value):
        raw = _json_bytes(value)
        if relative.endswith('.gz'):
            raw = gzip.compress(raw, compresslevel=9, mtime=0)
        _atomic_bytes(_path(out, relative), raw)
        assets[relative] = hashlib.sha256(raw).hexdigest()

    save('data/metrics.json.gz', metrics)
    save('data/pi-groups.json', data.get('piGroups', []))
    manifest = {key: value for key, value in data.items() if key not in {'universities', 'works', 'piGroups'}}
    manifest.update(bundleFormat=FORMAT, lazy=True, legacyKeys=list(data), universities=[], works={},
                    counts=counts, fields=sorted({lab.get('field', '') for u in universities for lab in u['labs']} - {''}),
                    metricsFile='data/metrics.json.gz', piGroupsFile='data/pi-groups.json')
    first_year, last_year = data.get('window', [2016, 2026])
    manifest['overview'] = {view: summarize_metrics(metrics, view, first_year, last_year) for view in VIEWS}
    for university in universities:
        uid = university['id']
        labs_file = _record_path('universities', uid)
        if labs_file + '.gz' in previous_assets:
            labs_file += '.gz'
        university_record = {key: value for key, value in university.items() if key != 'labs'}
        university_metrics = dict(units=scoped_units[uid], buckets=scoped_buckets.get(uid, []))
        university_record.update(labs=[], labsFile=labs_file, counts=scoped_counts[uid],
                                 overview={view: summarize_metrics(university_metrics, view, first_year, last_year) for view in VIEWS})
        manifest['universities'].append(university_record)
        lab_records = []
        for lab in university['labs']:
            edges = lab.get('papers', [])
            lab_record = {key: value for key, value in lab.items() if key != 'papers'}
            paper_counts = {view: {} for view in VIEWS}
            for edge in edges:
                year = str(_integer(works[edge['work']].get('year')))
                for view in VIEWS:
                    if _flag(edge, view):
                        paper_counts[view][year] = paper_counts[view].get(year, 0) + 1
            papers_file = _record_path('labs', lab['id']) if edges else ''
            if papers_file and papers_file + '.gz' in previous_assets:
                papers_file += '.gz'
            lab_record.update(paperCounts=paper_counts, papersFile=papers_file)
            lab_records.append(lab_record)
            if edges:
                save(papers_file, dict(labId=lab['id'], papers=edges,
                                       works={edge['work']: works[edge['work']] for edge in edges}))
        save(labs_file, dict(id=uid, labs=lab_records,
                            metrics=university_metrics))
    manifest['bundleCounts'] = dict(universities=len(universities), labs=len(lab_ids), works=len(works),
                                    labWorkLinks=sum(len(lab.get('papers', [])) for u in universities for lab in u['labs']))
    manifest['assets'] = dict(sorted(assets.items()))
    _atomic_bytes(out / 'data.json', _json_bytes(manifest))
    # Only recorded obsolete assets and the old generator's explicit part pattern
    # are owned here. Never remove the data tree or arbitrary neighboring files.
    for relative in previous_assets - set(assets):
        if isinstance(relative, str) and _OWNED.fullmatch(relative):
            old = _path(out, relative)
            if old.is_file():
                old.unlink()
    for old in out.glob('data-part-*.json'):
        if old.is_file():
            old.unlink()
    return manifest


def _load_legacy(path, data):
    universities = {u['id']: u for u in data['universities']}
    for part in data.get('parts', []):
        raw = _path(path.parent, part['path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == part['sha256'], 'Atlas asset checksum mismatch'
        records = json.loads(raw)
        assert len(records) == part['records']
        if part['kind'] == 'labs':
            for uid, lab in records:
                universities[uid]['labs'].append(lab)
        elif part['kind'] == 'works':
            for wid, work in records:
                assert wid not in data['works']
                data['works'][wid] = work
        else:
            raise ValueError('Unknown legacy atlas part')
    if data.get('parts'):
        assert sum(len(u['labs']) for u in data['universities']) == data['bundleCounts']['labs']
        assert len(data['works']) == data['bundleCounts']['works']
    return data


def load_lazy_bundle(path):
    """Reconstruct the legacy full model offline, checking all asset hashes."""
    path = Path(path)
    manifest = json.loads(path.read_text())
    if manifest.get('bundleFormat') != FORMAT:
        return _load_legacy(path, manifest)
    raw_assets = {}
    for relative, checksum in manifest['assets'].items():
        if not _OWNED.fullmatch(relative) and relative not in _ANALYSIS_EXPORTS:
            raise ValueError('Unknown lazy atlas asset: ' + relative)
        raw = _path(path.parent, relative).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == checksum, 'Atlas asset checksum mismatch: ' + relative
        raw_assets[relative] = raw

    def read(relative):
        assert relative in raw_assets, 'Referenced asset missing from hash manifest'
        return json.loads(gzip.decompress(raw_assets[relative]) if relative.endswith('.gz') else raw_assets[relative])

    data = {key: deepcopy(manifest[key]) for key in manifest['legacyKeys'] if key in manifest}
    data['universities'] = []
    data['works'] = {}
    pi_groups = read(manifest['piGroupsFile'])
    if 'piGroups' in manifest['legacyKeys']:
        data['piGroups'] = pi_groups
    # Registered analysis exports are checked above but are not JSON graph
    # assets. Keep them outside _OWNED so graph writes never delete exports.
    referenced_assets = {manifest['metricsFile'], manifest['piGroupsFile']} | (_ANALYSIS_EXPORTS & raw_assets.keys())
    for university in manifest['universities']:
        payload = read(university['labsFile'])
        referenced_assets.add(university['labsFile'])
        assert payload['id'] == university['id']
        university_record = {key: deepcopy(value) for key, value in university.items()
                             if key not in {'labs', 'labsFile', 'counts', 'overview'}}
        university_record['labs'] = []
        for lab in payload['labs']:
            lab_record = {key: value for key, value in lab.items() if key not in {'paperCounts', 'papersFile'}}
            lab_record['papers'] = []
            if lab['papersFile']:
                papers = read(lab['papersFile'])
                referenced_assets.add(lab['papersFile'])
                assert papers['labId'] == lab['id']
                assert set(papers['works']) == {edge['work'] for edge in papers['papers']}
                lab_record['papers'] = papers['papers']
                for wid, work in papers['works'].items():
                    if wid in data['works']:
                        assert data['works'][wid] == work, 'Conflicting shared-work metadata'
                    data['works'][wid] = work
            university_record['labs'].append(lab_record)
        data['universities'].append(university_record)
    assert referenced_assets == set(raw_assets), 'Unexpected unreferenced lazy atlas assets'
    assert len(data['universities']) == manifest['bundleCounts']['universities']
    assert sum(len(u['labs']) for u in data['universities']) == manifest['bundleCounts']['labs']
    assert len(data['works']) == manifest['bundleCounts']['works']
    assert sum(len(lab['papers']) for u in data['universities'] for lab in u['labs']) == manifest['bundleCounts']['labWorkLinks']
    return data
