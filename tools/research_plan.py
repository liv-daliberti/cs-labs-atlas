"""Finite, reusable source research for school_closeout; never an accuracy signoff.

Case IDs bind school, PI context, source bytes, capture year and evidence policy.
Student counts and native build hashes are deliberately absent: changing a
package does not by itself change the factual source work already completed.
Only an explicit whole-source review receipt resolves a case. No network calls.
"""
import collections
import contextlib
import copy
import datetime
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import urldefrag, urljoin, urlsplit

from bs4 import BeautifulSoup
import zlib

import atlas_paths as P
import school_config as S
import student_recall as R

CODE = Path(__file__).resolve().parents[1]
POLICY_FILES = ('docs/RULES.md', 'tools/visiting.py', 'tools/pihier/role_cues.py',
                'tools/labpage_students_school.py', 'tools/student_recall.py')
CONTEXT_FILES = ('census-overrides-school.json', 'faculty-periods.json', 'lab-websites.json')
SCHEMA = 1
REVIEW_FIELDS = ('status', 'coverage', 'outcome', 'reviewer', 'date', 'why', 'receipt')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), default=str).encode()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def reviewed_inputs(school):
    """Small reviewed files only; never hash gigabyte capture/sweep stores."""
    result, docs = {}, {}
    for name, kind, flat, _ in P.DATA_FILES:
        if kind != 'reviewed' or '{school}' not in flat or name == 'student-recall-check.json':
            continue
        path = Path(P.data(name, school))
        obj = read_json(path) if path.is_file() else None
        result[name] = digest(obj)
        if obj is not None:
            docs[name] = obj
    return result, docs


def context_index(docs, names):
    index = collections.defaultdict(list)

    def visit(obj, filename):
        if isinstance(obj, list):
            for item in obj:
                visit(item, filename)
        elif isinstance(obj, dict):
            pi = obj.get('pi') or obj.get('name')
            if isinstance(pi, str) and pi in names:
                index[pi].append(dict(file=filename, context=obj))
                return
            for key, value in obj.items():
                if key in names:
                    index[key].append(dict(file=filename, context=value))
                else:
                    visit(value, filename)

    for name in CONTEXT_FILES:
        if name in docs:
            visit(docs[name], name)
    return index


def source_leads(pis, students, audit, docs):
    """All known leads, without the recall drawer's eight-URL presentation cap.

    Reviewed student sources are discovery leads even when not yet in a native
    build. Their presence never proves membership or roster completeness.
    """
    leads = {p['pi']: set() for p in pis}
    by = {p['pi']: p for p in pis}
    for pi in leads:
        a = audit.get(pi) or {}
        urls = list(((a.get('lab_page') or {}).get('urls') or {}).values())
        urls += (a.get('students') or {}).get('pages') or []
        urls.append((by[pi].get('lab') or {}).get('url'))
        for row in students.get(pi, []):
            for rel in row.get('relations') or []:
                if rel.get('type') not in ('academic_advising', 'thesis_adviser'):
                    urls += [s.get('url') for s in rel.get('sources') or []]
        leads[pi].update(u for u in urls if isinstance(u, str) and u.startswith(('http://', 'https://'))
                         and not R.THESIS_URL.search(u))

    def visit(obj, pi=None, members=False, declared_pages=False):
        if isinstance(obj, list):
            for item in obj:
                visit(item, pi, members, declared_pages)
        elif isinstance(obj, dict):
            pi = obj.get('pi', pi)
            members = members or isinstance(obj.get('students'), list) or 'student' in obj or 'student_name' in obj
            if isinstance(pi, str) and pi in leads and (members or declared_pages):
                for key in ('url', 'source_url', 'people_page', 'lab_site'):
                    url = obj.get(key)
                    if isinstance(url, str) and url.startswith(('http://', 'https://')) and not R.THESIS_URL.search(url):
                        leads[pi].add(url)
            for key, value in obj.items():
                visit(value, key if key in leads else pi, members, declared_pages)
        elif declared_pages and isinstance(obj, str) and isinstance(pi, str) and pi in leads:
            if obj.startswith(('http://', 'https://')) and not R.THESIS_URL.search(obj):
                leads[pi].add(obj)

    for name, doc in docs.items():
        declared = name in ('extra-lab-pages.json', 'lab-websites.json')
        if declared or name.endswith('evidence.json') or name == 'student-decisions.json':
            visit(doc, declared_pages=declared)
    return leads


MEMBER_LABEL = re.compile(
    r'(?:(?:current|former|past|our|lab|group)\s+)*(?:students?|people|members?|team|group|alumni|advisees|collaborators)'
    r'|学生(?:信息|名单)?|团队(?:成员)?|研究团队|课题组成员|毕业学生|已毕业学生|组内成员', re.I)


MEMBER_PATH = re.compile(r'/(?:people|members|team|group|students?|alumni|advisees|collaborators|xsxx)(?:[./_-]|$)', re.I)


def member_navigation(raw, base):
    """Owned-path navigation leads only, never evidence of PI membership.

    Stay in the existing site's account path. In particular, a shared faculty
    directory profile or an institution's root is not an owned lab site.
    """
    if b'<a' not in raw.lower():
        return []
    origin = urlsplit(base)
    parts = [part for part in origin.path.split('/') if part]
    if parts and parts[0].lower() in ('jiaoshiml', 'faculty-directory', 'directory'):
        return []
    if not parts and re.search(r'\.(?:edu(?:\.[a-z]+)?|ac\.[a-z]+)$', origin.hostname or ''):
        return []
    scope = parts[:1]
    if scope and scope[0].lower() in ('people', 'faculty', 'home', 'labs', 'groups', 'view', 'site', 'sites', 'users'):
        scope = parts[:2]
    # A root HTML file belongs to the personal host, not an account directory.
    if len(parts) == 1 and re.search(r'\.[a-z0-9]+$', parts[0], re.I) and not parts[0].startswith('~'):
        scope = []
    prefix = '/' + '/'.join(scope) + '/' if scope else '/'
    result = []
    for anchor in BeautifulSoup(raw, 'html.parser').find_all('a', href=True):
        target = urldefrag(urljoin(base, anchor['href']))[0]
        dest = urlsplit(target)
        if dest.scheme not in ('http', 'https') or dest.netloc != origin.netloc:
            continue
        if not dest.path.startswith(prefix) or target == urldefrag(base)[0]:
            continue
        label = anchor.get_text(' ', strip=True)
        if MEMBER_LABEL.fullmatch(label) or MEMBER_PATH.search(dest.path):
            result.append((target, label))
    return sorted(set(result))


def cached_inventory(path, leads, *, follow_members=True):
    """Verify exact cached bytes and follow only already-cached member links.

    One read transaction, one byte check/parse per URL, no requests or writes.
    Refusal metadata is preserved; existing genuine bytes remain readable.
    Each discovered URL retains its PI and parent URL/SHA for manual scope review.
    """
    expanded = {pi: set(urls) for pi, urls in leads.items()}
    versions, blocked, discoveries = {}, {}, []
    if not Path(path).exists():
        return expanded, versions, blocked, discoveries
    with contextlib.closing(sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)) as conn:
        conn.execute('begin')
        tables = {r[0] for r in conn.execute("select name from sqlite_master where type='table'")}
        if 'blocked' in tables:
            blocked = {host.lower().removeprefix('www.'): why for host, why in conn.execute('select host,why from blocked')}
        if 'live' not in tables:
            raise ValueError('Source cache has no live table: ' + str(path))
        queue = collections.deque((pi, url) for pi in sorted(expanded) for url in sorted(expanded[pi]))
        checked, links = set(), {}
        while queue:
            pi, url = queue.popleft()
            if url not in checked:
                checked.add(url)
                row = conn.execute('select fetched_at,status,sha256,raw_zlib from live where url=?', (url,)).fetchone()
                if row is not None:
                    fetched, status, sha, compressed = row
                    raw = zlib.decompress(compressed) if compressed is not None else None
                    if raw is None or hashlib.sha256(raw).hexdigest() != sha:
                        raise ValueError('Cached source bytes do not match their hash: ' + url)
                    versions[url] = dict(sha256=sha, status=status, capture_year=str(fetched or '')[:4])
                    links[url] = member_navigation(raw, url) if follow_members and status == 200 else []
            for target, label in links.get(url, []):
                if target in expanded[pi]:
                    continue
                # Never invent an acquisition or expand to an uncached target.
                if not conn.execute('select 1 from live where url=?', (target,)).fetchone():
                    continue
                expanded[pi].add(target)
                discoveries.append(dict(pi=pi, url=target, parent_url=url,
                                        parent_sha256=versions[url]['sha256'], label=label))
                queue.append((pi, target))
    return expanded, versions, blocked, discoveries



def cached_sources(path, urls, allow_missing_live=False):
    """Read each exact URL once; verify actual bytes, preserving refusal facts."""
    versions, blocked = {}, {}
    if not Path(path).exists():
        return versions, blocked
    with contextlib.closing(sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)) as conn:
        conn.execute('begin')
        tables = {r[0] for r in conn.execute("select name from sqlite_master where type='table'")}
        if 'blocked' in tables:
            blocked = {host.lower().removeprefix('www.'): why for host, why in conn.execute('select host,why from blocked')}
        if 'live' not in tables:
            if allow_missing_live:
                # Historical school collectors can create this database before
                # the live-page collector initializes its own tables.
                return versions, blocked
            raise ValueError('Source cache has no live table: ' + str(path))
        for url in sorted(urls):
            row = conn.execute('select fetched_at,status,sha256,raw_zlib from live where url=?', (url,)).fetchone()
            if row is None:
                continue
            fetched, status, sha, raw = row
            if status != 200 and (raw is None or not sha):
                # A saved failed request is a lead/refusal, not readable source
                # bytes. It must not hide the other valid captures in a cache.
                versions[url] = dict(status=status, capture_year=str(fetched or '')[:4])
                continue
            if raw is None or hashlib.sha256(zlib.decompress(raw)).hexdigest() != sha:
                raise ValueError('Cached source bytes do not match their hash: ' + url)
            versions[url] = dict(sha256=sha, status=status, capture_year=str(fetched or '')[:4])
    return versions, blocked


def merge_cached_version(versions, url, source):
    """Merge flat versions, retaining the first cache's primary binding."""
    incoming = [{k: v for k, v in source.items() if k != 'snapshots'}] + list(source.get('snapshots', []))
    for row in incoming:
        if url not in versions:
            versions[url] = copy.deepcopy(row)
            continue
        current = versions[url]
        if row == {k: v for k, v in current.items() if k != 'snapshots'}:
            continue
        snapshots = {digest(item): item for item in current.get('snapshots', [])}
        snapshots[digest(row)] = copy.deepcopy(row)
        current['snapshots'] = [snapshots[key] for key in sorted(snapshots)]


def cached_audit_sources(path, urls):
    """Read registered lpcap stores without fetching, copying or accepting rows.

    Unlike school_web's live table, captures can hold many versions per URL;
    archive dates belong to the actual capture URL, not our later fetch time.
    """
    versions, blocked = {}, collections.defaultdict(set)
    if not Path(path).exists():
        return versions, {}
    with contextlib.closing(sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)) as conn:
        conn.execute('begin')
        tables = {row[0] for row in conn.execute("select name from sqlite_master where type='table'")}
        if 'captures' not in tables:
            raise ValueError('Audit source cache has no captures table: ' + str(path))
        if 'blocked' in tables:
            for host, why in conn.execute('select host,why from blocked'):
                blocked[host.lower().removeprefix('www.')].add(why)
        # Refusals on another path of the same host still apply. Do not load
        # unrelated response bodies merely to inventory their transport status.
        for url, capture, final, status, error in conn.execute(
                "select url,capture_url,final_url,status,error from captures where status in (401,403,429) "
                "or error in ('bot-challenge','robots-disallowed','host-challenged-skip','off-limits-host')"):
            reason = error if error in ('bot-challenge', 'robots-disallowed', 'host-challenged-skip', 'off-limits-host') else 'HTTP ' + str(status)
            for target in (capture or url, final):
                host = (urlsplit(target or '').hostname or '').lower().removeprefix('www.')
                if host:
                    blocked[host].add(reason + ' at ' + (capture or url))
        requested, seen = set(urls), set()
        ordered = sorted(requested)
        for start in range(0, len(ordered), 200):
            batch = ordered[start:start + 200]
            marks = ','.join('?' for _ in batch)
            rows = conn.execute('select id,url,capture_url,final_url,fetched_at,status,sha256,content,error from captures '
                                f'where url in ({marks}) or capture_url in ({marks}) order by id desc', batch + batch)
            for ident, url, capture, final, fetched, status, sha, raw, error in rows:
                if ident in seen:
                    continue
                seen.add(ident)
                actual = final or capture or url
                archive = re.match(r'^https?://(?:web\.)?archive\.org/web/(\d{4})', actual)
                if (urlsplit(actual).hostname or '') in ('archive.org', 'web.archive.org') and not archive:
                    raise ValueError('Audit archive URL has no dated timestamp: ' + actual)
                year = archive.group(1) if archive else str(fetched or '')[:4]
                source = dict(status=999 if error == 'bot-challenge' else status, capture_year=year)
                if error:
                    source['capture_error'] = error if error in ('bot-challenge', 'robots-disallowed', 'robots-unknown',
                                                                 'host-challenged-skip', 'off-limits-host') else 'transport_error'
                if error == 'bot-challenge':
                    source['http_status'] = status
                if source['status'] == 200 or (raw is not None and sha):
                    if raw is not None:
                        try:
                            body = zlib.decompress(raw)
                        except zlib.error:
                            body = raw  # legacy lpcap captures can retain original, uncompressed response bytes
                    else:
                        body = None
                    if body is None or not sha or hashlib.sha256(body).hexdigest() != sha:
                        raise ValueError('Cached audit source bytes do not match their hash: ' + url)
                    source['sha256'] = sha
                for target in {url, capture} & requested:
                    merge_cached_version(versions, target, source)
    return versions, {host: '; '.join(sorted(reasons)) for host, reasons in blocked.items()}


def source_caches(paths, urls, optional_live=(), audit_paths=()):
    """Inventory existing registered caches once; retain conflicting versions.

    Prefer the recall cache's exact binding when another cache has identical
    metadata. File locations are inventory pointers, never scientific bindings.
    Nothing is fetched, promoted to a verdict, or written back to either cache.
    """
    versions, blocked, seen = {}, collections.defaultdict(set), set()
    optional_live = {Path(path).resolve() for path in optional_live}
    audit_paths = {Path(path).resolve() for path in audit_paths}
    for path in paths:
        identity = Path(path).resolve()
        if identity in seen:
            continue
        seen.add(identity)
        if identity in audit_paths:
            incoming, refusals = cached_audit_sources(path, urls)
        elif identity in optional_live:
            incoming, refusals = cached_sources(path, urls, allow_missing_live=True)
        else:
            incoming, refusals = cached_sources(path, urls)
        for host, reason in refusals.items():
            blocked[host].add(reason)
        for url, source in incoming.items():
            merge_cached_version(versions, url, source)
    return versions, {host: '; '.join(sorted(reasons)) for host, reasons in blocked.items()}


def saved_snapshots(docs, leads, versions):
    """Reuse exact reviewed capture pointers; no directory searches or refetches.

    A saved snapshot is not represented as a fresh HTTP response. Multiple
    versions stay explicit, and moving identical files does not reopen work.
    """
    known_urls = {url for urls in leads.values() for url in urls}
    snapshots, hashes = collections.defaultdict(dict), {}

    def visit(obj):
        if isinstance(obj, list):
            for row in obj:
                visit(row)
        elif isinstance(obj, dict):
            url, sha = obj.get('url'), obj.get('sha256')
            pointer = obj.get('source_capture') or obj.get('source_raw_path') or obj.get('local_bytes')
            if isinstance(url, str) and url in known_urls and isinstance(sha, str) and isinstance(pointer, str):
                path = Path(pointer)
                path = path if path.is_absolute() else P.CODE / path
                if path not in hashes:
                    hashes[path] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
                if hashes[path] == sha:
                    year = str(obj.get('captured') or obj.get('observedAt') or '')[:4]
                    snapshot = dict(sha256=sha, capture_year=year, kind='saved_source_file')
                    snapshots[url][digest(snapshot)] = snapshot
            for value in obj.values():
                visit(value)

    for name, doc in docs.items():
        if name.endswith('evidence.json'):
            visit(doc)
    result = copy.deepcopy(versions)
    for url, rows in snapshots.items():
        current = result.setdefault(url, {})
        rows.update({digest(row): row for row in current.get('snapshots', [])})
        current['snapshots'] = [rows[k] for k in sorted(rows)]
    return result


def has_source_bytes(source):
    return bool(source.get('sha256') or any(row.get('sha256') for row in source.get('snapshots', [])))


def has_readable_source(source):
    """Saved redirects/errors are bytes, but not successful source responses."""
    return any(row.get('sha256') and not row.get('capture_error')
               and (row.get('status') == 200 or row.get('kind') == 'saved_source_file')
               for row in [source] + list(source.get('snapshots', [])))


def pi_context(pi):
    # Derived publication counters inside piBasis are not identity evidence.
    context = {k: pi.get(k) for k in ('pi', 'personIds', 'names', 'rank', 'title', 'departments', 'periods')}
    evidence_keys = ('kind', 'url', 'sha256', 'quote', 'observed', 'role')

    def evidence(value):
        if isinstance(value, list):
            return [evidence(row) for row in value]
        if isinstance(value, dict):
            return {k: value[k] for k in evidence_keys if k in value}
        return value or {}

    context['piBasis'] = evidence(pi.get('piBasis'))
    lab = pi.get('lab') or {}
    context['lab'] = {k: lab.get(k) for k in ('unitId', 'name', 'url', 'basis', 'collectives')}
    context['lab']['evidence'] = evidence(lab.get('evidence'))
    return context


def receipt_valid(case, hashes=None):
    if (case.get('status') != 'resolved' or case.get('coverage') != 'whole_source'
            or case.get('outcome') not in ('reviewed', 'no_roster', 'unavailable')
            or not str(case.get('reviewer') or '').strip() or not str(case.get('why') or '').strip()):
        return False
    if case.get('outcome') != 'unavailable' and not has_source_bytes(case.get('binding', {}).get('source') or {}):
        return False
    try:
        datetime.date.fromisoformat(case.get('date', ''))
        receipt = case.get('receipt') or {}
        if not isinstance(receipt, dict):
            return False
        path = Path(receipt.get('path', ''))
        if not path.is_file():
            return False
        hashes = {} if hashes is None else hashes
        key = str(path.resolve())
        if key not in hashes:
            hashes[key] = hashlib.sha256(path.read_bytes()).hexdigest()
        return hashes[key] == receipt.get('sha256')
    except (OSError, TypeError, ValueError):
        return False


def plan(school, pis, students, leads, versions, blocked, policy, contexts, inputs, previous=None):
    if not pis:
        raise ValueError('No PI snapshot: finish the census and baseline build before planning source research')
    previous = previous or {}
    if previous and (previous.get('school') != school or previous.get('research', {}).get('schema') != SCHEMA):
        raise ValueError('Previous research board has a different school or unsupported schema')
    old_cases = {c['id']: c for c in previous.get('cases', [])}
    if len(old_cases) != len(previous.get('cases', [])):
        raise ValueError('Previous research board repeats a case ID')
    cases, groups, receipt_hashes = [], collections.defaultdict(list), {}
    for p in sorted(pis, key=lambda p: (len(students.get(p['pi'], [])), p['pi'])):
        pi = p['pi']
        context = digest(dict(native=pi_context(p), reviewed=contexts.get(pi, [])))
        for url in sorted(leads.get(pi) or []) or [None]:
            source = copy.deepcopy(versions.get(url, {}))
            host = (urlsplit(url).hostname or '').lower().removeprefix('www.') if url else ''
            refusal = blocked.get(host)
            binding = dict(school=school, pi=pi, context_sha256=context, url=url,
                           source=source, access_refusal=refusal, policy_sha256=policy)
            case_id = 'source-' + digest(binding)
            case = dict(id=case_id, binding=binding, status='pending',
                        native_members=len(students.get(pi, [])),
                        next_action='inspect_saved_source' if has_source_bytes(source) else 'respect_recorded_refusal' if refusal else
                                    'recover_exact_source_or_research_lead' if url else 'find_owned_roster',
                        coverage='', outcome='', reviewer='', date='', why='', receipt={})
            old = old_cases.get(case_id)
            if old and old.get('binding') == binding and receipt_valid(old, receipt_hashes):
                for key in REVIEW_FIELDS:
                    case[key] = copy.deepcopy(old[key])
            cases.append(case)
            if url:
                groups[url].append(dict(pi=pi, case_id=case_id))
    pending = sum(c['status'] != 'resolved' for c in cases)
    prior_inputs = previous.get('research', {}).get('reviewed_inputs')
    changed = sorted(n for n in set(inputs) | set(prior_inputs or {}) if inputs.get(n) != (prior_inputs or {}).get(n))
    advice = 'finish_source_batch' if pending else 'check_other_build_dependencies' if prior_inputs == inputs else 'seal_and_rebuild_once'
    return dict(school=school, research=dict(schema=SCHEMA, policy_sha256=policy, reviewed_inputs=dict(inputs)),
        cases=cases, shared_sources=[dict(url=u, contexts=cs) for u, cs in sorted(groups.items()) if len(cs) > 1],
        summary=dict(pis=len(pis), source_cases=len(cases), unique_urls=len(groups),
                     sources_with_bytes=sum(has_source_bytes(versions.get(url, {})) for url in groups),
                     reusable_reviews=len(cases)-pending, pending=pending, retired_cases=len(set(old_cases)-{c['id'] for c in cases}),
                     changed_reviewed_inputs=changed, next_action=advice),
        qualification='Research planning only. A resolved case is not membership approval, a passing recall/accuracy verdict or a fresh signoff. '
                      'Unchanged school-reviewed inputs do not prove the raw stores or build code are unchanged; use atlas stale and closeout seal.')


def collect(school, previous=None):
    charter = S.get(school)
    pis, students, audit = R._pis(school), R._students(school), R._audit(school)
    inputs, docs = reviewed_inputs(school)
    leads = source_leads(pis, students, audit, docs)
    capture_stores = [P.data(name, school) for name in ('student-recall-captures.sqlite', 'school-captures.sqlite')]
    audit_stores = [P.data(name, school) for name in ('labpage-audit-captures.sqlite', 'labpage-captures.sqlite')]
    capture_stores += audit_stores
    try:
        leads, _, _, discoveries = cached_inventory(P.data('student-recall-captures.sqlite', school), leads)
        versions, blocked = source_caches(capture_stores, {u for us in leads.values() for u in us},
                                         optional_live=capture_stores[1:2], audit_paths=audit_stores)
    except (sqlite3.Error, zlib.error) as exc:
        raise ValueError('Cannot read the source cache safely: ' + str(exc)) from exc
    versions = saved_snapshots(docs, leads, versions)
    policy = digest(dict(charter=charter, files={name: hashlib.sha256((CODE / name).read_bytes()).hexdigest()
                                               for name in POLICY_FILES}))
    board = plan(school, pis, students, leads, versions, blocked, policy,
                 context_index(docs, {p['pi'] for p in pis}), inputs, previous)
    board['data_root'] = str(P.CODE)
    board['capture_store'] = str(capture_stores[0])
    board['capture_stores'] = [str(path) for path in capture_stores]
    board['cached_member_navigation'] = discoveries
    return board


def apply_reviews(board, reviews):
    """Register explicit reviews atomically against a freshly collected board.

    The full binding is required: neither a URL nor a receipt for another PI
    supplies the missing context. No membership or gate decision is accepted.
    """
    if not isinstance(reviews, dict) or reviews.get('school') != board['school'] or not isinstance(reviews.get('cases'), list):
        raise ValueError('Source reviews need the same school and a cases list')
    result = copy.deepcopy(board)
    cases = {case['id']: case for case in result['cases']}
    seen, hashes = set(), {}
    for review in reviews['cases']:
        if not isinstance(review, dict):
            raise ValueError('Each source review must be an object with its exact binding')
        ident = review.get('id')
        if not isinstance(ident, str) or ident not in cases or ident in seen:
            raise ValueError('Source review case is unknown, changed or repeated: ' + str(ident))
        seen.add(ident)
        case = cases[ident]
        if review.get('binding') != case['binding']:
            raise ValueError('Source review binding changed; refresh and review the affected context: ' + ident)
        updated = dict(case, **{key: copy.deepcopy(review.get(key)) for key in REVIEW_FIELDS})
        if not receipt_valid(updated, hashes):
            raise ValueError('Source review needs a whole-source decision and an intact receipt: ' + ident)
        if case['status'] == 'resolved' and any(case[key] != updated[key] for key in REVIEW_FIELDS):
            raise ValueError('Existing source review must be preserved; record a new source/context to reopen: ' + ident)
        cases[ident] = updated
    result['cases'] = [cases[case['id']] for case in result['cases']]
    pending = sum(case['status'] != 'resolved' for case in result['cases'])
    result['summary'].update(reusable_reviews=len(cases) - pending, pending=pending,
                             next_action='finish_source_batch' if pending else 'seal_and_rebuild_once'
                             if result['summary']['changed_reviewed_inputs'] else 'check_other_build_dependencies')
    return result


def review_batch(board, limit=20):
    """Read shared sources once, keeping every PI's binding and decision distinct.

    The finite batch prioritizes saved sources for sparse labs; refusal-only
    cases remain explicit work with an instruction to respect the refusal.
    """
    if type(limit) is not int or limit < 1:
        raise ValueError('Batch size must be a positive integer')
    groups = {}
    for case in board['cases']:
        if case['status'] == 'resolved':
            continue
        binding = case['binding']
        shared = {key: binding[key] for key in ('url', 'source', 'access_refusal')}
        # Empty leads are individual research tasks, not one shared source.
        key = digest(shared) if binding['url'] else case['id']
        group = groups.setdefault(key, dict(shared, next_action=case['next_action'],
                                           readable_saved_source=has_readable_source(binding['source']), cases=[]))
        group['cases'].append(copy.deepcopy(case))
    priority = {'inspect_saved_source': 0, 'find_owned_roster': 2,
                'recover_exact_source_or_research_lead': 3, 'respect_recorded_refusal': 4}
    sources = sorted(groups.values(), key=lambda group: (
        priority[group['next_action']] + int(group['next_action'] == 'inspect_saved_source' and not group['readable_saved_source']),
        min(case['native_members'] for case in group['cases']),
        -len(group['cases']), group['url'] or '', digest(group['source'])))
    selected = sources[:limit]
    return dict(school=board['school'], research=copy.deepcopy(board['research']),
                source_board_sha256=digest(board), capture_stores=board.get('capture_stores', []),
                summary=dict(pending_cases=sum(len(group['cases']) for group in sources),
                             pending_sources=len(sources), selected_sources=len(selected),
                             selected_cases=sum(len(group['cases']) for group in selected)),
                sources=selected, qualification=board['qualification'])


def validate_board(board):
    current = collect(board['school'], previous=board)
    if {c['id'] for c in current['cases']} != {c['id'] for c in board['cases']}:
        raise ValueError('Research inventory changed: refresh closeout research before sealing')
    if current['summary']['pending']:
        raise ValueError('Finish whole-source reviews with intact receipts before sealing: '
                         + str(current['summary']['pending']) + ' pending')


def render(board):
    s = board['summary']
    lines = [f"{board['school']}: {s['pis']} PIs, {s['unique_urls']} known source URLs; "
             f"{s['reusable_reviews']} reusable reviews, {s['pending']} pending.",
             'Next action: ' + s['next_action'], board['qualification']]
    if board.get('data_root'):
        lines.append('Selected data root: ' + board['data_root'])
    if s['unique_urls'] and not s['sources_with_bytes']:
        lines.append('No source bytes found in this data root. Check the existing candidate overlay and capture pointers before repeating research.')
    for case in [c for c in board['cases'] if c['status'] != 'resolved'][:12]:
        b = case['binding']
        lines.append(f"  {b['pi']} ({case['native_members']} members): {case['next_action']} {b['url'] or ''}")
    if s['pending'] > 12:
        lines.append(f"  ... {s['pending'] - 12} more cases in the JSON board")
    return '\n'.join(lines)
