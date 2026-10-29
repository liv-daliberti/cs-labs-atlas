#!/usr/bin/env python3
"""Export the shareable dataset repository: the CS PI-lab hierarchy of every built school, the wider 300-university
atlas, and the code that builds them. Read-only over the sources; writes only inside <repo dir>.

schools  every school with hierarchy/<school>/pis.json (SCHOOLS) that the site builder lists (EXPORT), from its package:
           data/schools/<school>/pis.jsonl.gz            one row per PI lab (stable pi_id = <school>:<name slug>)
           data/schools/<school>/papers.jsonl.gz         one row per unique lab paper (paper_id from its OpenAlex / DBLP /
                                                         lab-page key), with every lab it belongs to and why
           data/schools/<school>/students.jsonl.gz       one row per student id, with every advising PI and the sources
           data/schools/<school>/student_papers.jsonl.gz one row per (PI, student, paper) link
           data/schools/<school>/{lab_papers,lab_students,student_papers,pis}.csv   flat joins
           data/schools/<school>/{zero_labs.json, excluded_pis.json, scope_review.json.gz, build_report.json}
         Departments are assigned exactly as the site does: the site builder's own department()
         (princeton-live-20261015/scripts/build-cs-hierarchy.py), with the accepted reviewed home departments.
atlas    princeton-live-20261015/atlas: data.json universities, data/universities/<id>.json.gz units, data/labs/*.json.gz
         unit papers + works, data/lab-people/*.json.gz unit people + their works, pi-groups.json, metrics.json.gz
           -> data/atlas/{universities,units,works,unit_papers,unit_people,unit_person_papers,pi_identities}.jsonl.gz
code     the tools that build all of it -> code/ (emails redacted: the owner's address becomes you@example.org), taken from
         the code repository's HEAD commit (git -C work), never from uncommitted files; MANIFEST export.code.commit
Data comes from a dated release (tools/make_release.py; default /n/fs/resemble/cs-atlas/releases/latest), recorded as
MANIFEST export.release; --from-working reads the working hierarchy/ instead (development only).
Every string is scrubbed: e-mail addresses everywhere; phone numbers and office addresses inside quotes; local file
paths. Rows are sorted and gzip is written with mtime=0, so a rerun on unchanged sources is byte-identical.
Ends with tests/verify_release.py <repo dir> when the repo has it.

usage: export_release.py <repo dir> [--release ID|DIR] [--from-working] [--skip-code] [--skip-atlas]
       EXPORT_ATLAS_CACHE=<pickle> reuses a local pickle of the atlas shard files (development only)
"""
import collections, csv, gzip, hashlib, importlib.util, io, json, os, pickle, re, shutil, subprocess, sys, time, zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as AP  # noqa: E402  (every path in one place)

HERE = AP.WORK                       # the code repository (/n/fs/resemble/cs-atlas/work; was .research-sweeps/claude-schools-20261021)
DATA = HERE                          # where the data is read: a release directory (configure()) or the working root
H = DATA / 'hierarchy'
RELEASE = None                       # the release read: dict(id, dir, manifest_sha256)
SITE_ROOT = AP.SITE_ROOT
ATLAS = SITE_ROOT / 'atlas'
ORDER = list(AP.SCHOOL_IDS)  # display order; any other built school follows
SCHOOLS = [s for s in ORDER if (H / s / 'pis.json').exists()] + sorted(
    d.name for d in H.iterdir() if d.is_dir() and d.name not in ORDER and (d / 'pis.json').exists())
OWNER_EMAIL_SHA256 = '3d295a08f3a63465645d9d4e99fbe34f11aa0622bbf29a754e0b23cb4263aacf'  # the owner's address, kept out of the code itself
PLACEHOLDER_EMAIL = 'you@example.org'
MAX_FILE = 50 * 1024 * 1024
SHARD_AT = 45 * 1024 * 1024

_spec = importlib.util.spec_from_file_location('build_cs_hierarchy', SITE_ROOT / 'scripts/build-cs-hierarchy.py')
SITE = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(SITE)
# exported: the built schools the site's department rule knows (a school is ready once it is added to the site builder's
# SCHOOLS); a package the site does not know yet (e.g. a school still being built) is listed in the manifest as skipped
EXPORT = [s for s in SCHOOLS if s in SITE.SCHOOLS]
SKIPPED = {s: 'package exists but the site builder (scripts/build-cs-hierarchy.py SCHOOLS) does not list it yet' for s in SCHOOLS if s not in EXPORT}


def configure(release=None):
    """Read the data from a release (an id, 'latest' or a directory), or from the working root when release is None."""
    global DATA, H, RELEASE, SCHOOLS, EXPORT, SKIPPED
    if release is not None:
        d = (AP.RELEASES / release if (AP.RELEASES / release).exists() else Path(release)).resolve()
        if not (d / 'MANIFEST.json').exists():
            raise SystemExit(f'not a release (no MANIFEST.json): {d}')
        RELEASE = dict(id=json.loads((d / 'MANIFEST.json').read_text())['release'], dir=str(d),
                       manifest_sha256=hashlib.sha256((d / 'MANIFEST.json').read_bytes()).hexdigest())
        DATA = d
    H = DATA / 'hierarchy'
    SCHOOLS = [s for s in ORDER if (H / s / 'pis.json').exists()] + sorted(
        d.name for d in H.iterdir() if d.is_dir() and d.name not in ORDER and (d / 'pis.json').exists())
    EXPORT = [s for s in SCHOOLS if s in SITE.SCHOOLS]
    SKIPPED = {s: 'package exists but the site builder (scripts/build-cs-hierarchy.py SCHOOLS) does not list it yet' for s in SCHOOLS if s not in EXPORT}

# ---------------------------------------------------------------- reading (retry while a file is being rewritten)


def read(p, tries=12):
    for i in range(tries):
        try:
            b = Path(p).read_bytes()
            if b[:2] == b'\x1f\x8b':
                b = gzip.decompress(b)
            return json.loads(b)
        except (json.JSONDecodeError, EOFError, OSError, zlib.error) as e:
            if i == tries - 1:
                raise
            print(f'  retry {p}: {type(e).__name__}', file=sys.stderr); time.sleep(20)


def jsonl(p, tries=12):
    for i in range(tries):
        try:
            with gzip.open(p, 'rt') as f:
                return [json.loads(s) for s in f if s.strip()]
        except (json.JSONDecodeError, EOFError, OSError, zlib.error) as e:
            if i == tries - 1:
                raise
            print(f'  retry {p}: {type(e).__name__}', file=sys.stderr); time.sleep(20)


# ---------------------------------------------------------------- scrubbing

EMAIL = re.compile(r'(?<![\w.%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b')
OBF_EMAIL = re.compile(r'(?i)\b[\w.\-]+\s*(?:\[at\]|\(at\)|\{at\}|<at>| at )\s*[\w\-]+(?:\s*(?:\[dot\]|\(dot\)|\{dot\}|<dot>| dot )\s*[\w\-]+)+'
                       r'|\b[\w.\-]+\s*(?:\[at\]|\(at\)|\{at\}|<at>)\s*[\w\-]+(?:\.[\w\-]+)+')
PHONE = re.compile(r'(?i)\b(?:phone|tel|telephone|fax|mobile|cell)\b\.?\s*:?\s*[+\d(][\d\s().\-/]{6,}\d'
                   r'|\+\d{1,3}(?:[\s.\-/]?\(?\d{1,4}\)?){2,6}(?=\D|$)'
                   r'|(?<!\d)\(\d{3}\)\s?\d{3}[\s.\-]\d{4}(?!\d)|(?<![\d./-])\d{3}[.\-]\d{3}[.\-]\d{4}(?![\d./-])')
ADDRESS = re.compile(r'(?i)\b(?:campus address|office address|mailing address|office location|office|room|bureau)\s*:\s*[^.;|\n]{0,40}?\d+[A-Z]?\b'
                     r'|(?i:\bcampus address|\boffice address|\bmailing address|\boffice location)\s+[^.;|\n]{0,40}?\d+[A-Z]?\b')
LOCAL_PATH = re.compile(r'(?:/n/fs|/u/[a-z0-9]+|/tmp/claude-\d+)/[^\s"\'<>]*')
QUOTE_KEYS = {'quote', 'quotes', 'excerpt', 'evidence_excerpt', 'text', 'statement', 'snippet', 'notes', 'note', 'reason',
              'summary', 'why', 'unitEvidenceQuote', 'researchSummary', 'gapNote', 'title_as_listed', 'evidence'}
DROP_KEYS = {'capturePath', 'rawPath', 'capture', 'metadataSnapshot', 'profileUrl', 'allResearchUrl', 'readerId', 'hosted',
             'cachedMetadata', 'primaryReceipt', 'copies', 'library', 'priorLibraryObservations', 'captureEncoding',
             'email', 'emails', 'phone', 'phones', 'telephone', 'office', 'address',
             # local provenance paths of the build machine (the values are paths only)
             'sourceDatabase', 'localSourcePath', 'cache_path', 'reusedFrom', 'cacheReuseFrom', 'extractedCapture', 'localSource',
             'textPath', 'sourcePath', 'inputFile', 'database', 'rawSource'}
RED = collections.Counter()


def is_owner(e):
    return hashlib.sha256(e.strip().lower().encode()).hexdigest() == OWNER_EMAIL_SHA256


def _phone_ok(m):
    return sum(c.isdigit() for c in m.group(0)) >= 9


def scrub_str(s, quoteish=False):
    if quoteish and s.startswith(('http://', 'https://')):  # a URL inside an evidence record: e-mails only, never digit runs
        quoteish = False
    if '@' in s:
        def em(m):
            if re.search(r'@lists\.', m.group(0), re.I):  # a public mailing-list address (e.g. in a list-archive URL), not a person's
                return m.group(0)
            own = is_owner(m.group(0))
            RED['email_owner' if own else 'email'] += 1
            return PLACEHOLDER_EMAIL if own else '[email removed]'
        s = EMAIL.sub(em, s)
    if quoteish:
        def ob(m):
            RED['email_obfuscated'] += 1; return '[email removed]'
        s = OBF_EMAIL.sub(ob, s)

        def ph(m):
            if not _phone_ok(m):
                return m.group(0)
            RED['phone'] += 1; return '[phone removed]'
        s = PHONE.sub(ph, s)

        def ad(m):
            RED['office_address'] += 1; return '[address removed]'
        s = ADDRESS.sub(ad, s)
    if '/n/fs' in s or re.search(r'/u/[a-z0-9]+/', s) or '/tmp/claude-' in s:
        def lp(m):
            RED['local_path'] += 1; return '[local path]'
        s = LOCAL_PATH.sub(lp, s)
    return s


def scrub(x, key=None, quoteish=False):
    """Recursively scrub; drop contact / local-file keys."""
    q = quoteish or key in QUOTE_KEYS
    if isinstance(x, str):
        return scrub_str(x, q)
    if isinstance(x, list):
        return [scrub(v, key, q) for v in x]
    if isinstance(x, dict):
        out = {}
        for k, v in x.items():
            if k in DROP_KEYS:
                RED['dropped_key:' + k] += 1; continue
            out[k] = scrub(v, k, q)
        return out
    return x


# ---------------------------------------------------------------- writing

MANIFEST = {}


def _record(path, data_bytes, rows):
    MANIFEST[str(path)] = dict(bytes=len(data_bytes), sha256=hashlib.sha256(data_bytes).hexdigest(), rows=rows)


def dumps(r):  # U+2028/2029 escaped too, so line-oriented readers never split a row
    return json.dumps(r, ensure_ascii=False, separators=(',', ':')).replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')


def write_jsonl(repo, rel, rows, shard_key=None):
    """Gzip JSONL with mtime=0; sharded into <rel minus .jsonl.gz>/<key>.jsonl.gz when it would pass ~45 MB."""
    body = ''.join(dumps(r) + '\n' for r in rows).encode()
    gz = gzip.compress(body, compresslevel=9, mtime=0)
    p = repo / rel
    if len(gz) < SHARD_AT or not shard_key:
        p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(gz); _record(rel, gz, len(rows))
        return [rel]
    groups = collections.defaultdict(list)
    for r in rows:
        groups[str(r.get(shard_key) or '_none')].append(r)
    d = rel[:-len('.jsonl.gz')]
    out = []
    for k in sorted(groups):
        out += write_jsonl(repo, f'{d}/{k}.jsonl.gz', groups[k])
    return out


def write_json(repo, rel, obj):
    b = (json.dumps(obj, ensure_ascii=False, indent=1) + '\n').encode()
    if rel.endswith('.gz'):
        b = gzip.compress(b, compresslevel=9, mtime=0)
    p = repo / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b)
    _record(rel, b, None)


def write_csv(repo, rel, header, rows):
    s = io.StringIO(); w = csv.writer(s, lineterminator='\n'); w.writerow(header)
    for r in rows:
        w.writerow(['' if v is None else v for v in r])
    b = s.getvalue().encode()
    p = repo / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b)
    _record(rel, b, len(rows))


def write_bytes(repo, rel, b):
    p = repo / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b); _record(rel, b, None)


# ---------------------------------------------------------------- schools


def slug(s):
    import unicodedata
    s = unicodedata.normalize('NFKD', str(s)); s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def paper_id(oa):
    oa = str(oa or '')
    if oa.startswith('https://openalex.org/'):
        return oa.rsplit('/', 1)[1]
    if oa.startswith('https://dblp.org/rec/'):
        return 'dblp:' + oa[len('https://dblp.org/rec/'):]
    return oa


def source_row(s):
    """One evidence source, without capture-store internals."""
    if not isinstance(s, dict):
        return s
    obs = s.get('observedOn') or s.get('date') or s.get('observedAt') or s.get('fetchedAt')
    r = dict(url=s.get('url') or s.get('capture_url'), final_url=s.get('finalUrl') if s.get('finalUrl') != s.get('url') else None,
             sha256=s.get('sha256'), quote=s.get('quote') or s.get('statement'), kind=s.get('kind') or s.get('type'),
             observed=str(obs)[:10] if obs else None, note=s.get('representation'))
    return {k: v for k, v in r.items() if v not in (None, '', [])}


def site_lab_map(school, cfg):
    """The site's atlas lab for a reused collection unit (build-cs-hierarchy.py: canonical id, if the atlas has it)."""
    site_labs = set()
    up = SITE.D / f"universities/{cfg['uni']}.json.gz"
    if up.exists():
        site_labs = {l['id'] for l in read(up)['labs']}
    canon = {}
    cp = SITE.D / f'collection-{school}.json.gz'
    if cp.exists():
        canon = {u['id']: u.get('canonicalId') or u['id'] for u in read(cp)['units']}
    return site_labs, canon


def export_school(repo, s, homes_all, profiles, zero):
    if s not in SITE.SCHOOLS:
        raise SystemExit(f'{s}: not in the site builder SCHOOLS ({SITE_ROOT}/scripts/build-cs-hierarchy.py); add it there '
                         f'first so departments follow the site rule')
    cfg = SITE.SCHOOLS[s]; src = H / s
    for attempt in range(6):  # a consistent snapshot: the package must not be rebuilt while it is read
        rep = read(src / 'report.json')
        pis = read(src / 'pis.json'); rows = jsonl(src / 'lab_papers.jsonl.gz'); stu = read(src / 'students.json')
        sp = jsonl(src / 'student_papers.jsonl.gz')
        if read(src / 'report.json').get('builtAt') == rep.get('builtAt'):
            break
        print(f'  {s}: package rebuilt while reading, retrying', file=sys.stderr); time.sleep(30)
    else:
        raise SystemExit(f'{s}: package kept changing')
    home = {x['name']: x for x in homes_all if x.get('school') == s and x.get('status') == 'accepted' and x.get('home_department')}
    adds = {a['name'] for a in (read(DATA / f'census/{s}-additions.json') if (DATA / f'census/{s}-additions.json').exists() else [])
            if 'cs_related' in str(a.get('added'))}
    site_labs, canon = site_lab_map(s, cfg)
    out = f'data/schools/{s}'

    # PIs
    pid = {}
    P = []
    for p in pis:
        i = f'{s}:{slug(p["pi"])}'
        pid[p['pi']] = i
        dept, cov = SITE.department(s, cfg, p, home)
        lab = p['lab']; unit = lab.get('unitId'); site = canon.get(unit, unit) if unit else None
        h = home.get(p['pi'])
        P.append(dict(
            pi_id=i, school=s, name=p['pi'], name_forms=p.get('names') or [], merged_census_rows=p.get('mergedCensusRows') or [],
            department=dept, department_coverage=cov, departments_as_listed=p.get('departments') or [],
            home_department_review=dict(home_department=h['home_department'], also=h.get('also') or [], no_academic_department=bool(h.get('no_academic_department')),
                                        evidence=source_row(h.get('evidence') or {}), note=h.get('note')) if h else None,
            scope='cs_related_addition' if p['pi'] in adds else 'core_computing_department',
            rank=p.get('rank'), title=p.get('title'),
            identifiers=dict(dblp=p.get('dblp') or [], dblp_basis=p.get('dblpBasis'), dblp_dropped=p.get('dblpDropped') or [],
                             openalex_reviewed=p.get('reviewedOpenAlex') or [], openalex_anchored=p.get('oaAuthorIds') or [],
                             openalex_not_this_person=p.get('notOpenAlex') or [], orcid=p.get('orcid') or [], collection_person_ids=p.get('personIds') or []),
            pi_basis=p.get('piBasis'),
            lab=dict(lab_id=unit or f"{s}-pi-lab-{re.sub('[^a-z0-9]+', '-', p['pi'].lower()).strip('-')}", name=lab.get('name') or f"{p['pi']} group",
                     url=lab.get('url'), basis=lab.get('basis'), collection_unit_id=unit, atlas_unit_id=site if site in site_labs else None,
                     evidence=lab.get('evidence'), collectives=lab.get('collectives') or []),
            periods=[dict(period_id=q.get('id'), start=q.get('start'), end=q.get('end'), as_of=q.get('asof'),
                          evidence=[source_row(e) for e in q.get('evidence') or []]) for q in p.get('periods') or []],
            listings=[{k: v for k, v in dict(year=l.get('year'), url=l.get('url'), sha256=l.get('sha256'), quote=l.get('quote'), kind=l.get('kind'),
                                             rank_as_listed=l.get('rank'), emeritus=l.get('emeritus'), visiting=l.get('visiting')).items() if v is not None}
                      for l in p.get('listings') or []],
            counts=p.get('counts') or {}, funnel=p.get('funnel') or {}))
    P = scrub(sorted(P, key=lambda r: r['pi_id']))
    byp = {r['pi_id']: r for r in P}

    # papers
    papers = {}
    dup_pairs = 0
    pair_work = {}      # (pi, paper id) -> collection work of the row that took it
    by_pi_work = {}     # (pi, collection work) -> paper id, for student-paper links
    for r in rows:
        k = paper_id(r['oa']); i = pid[r['pi']]; split = None
        if (i, k) in pair_work and pair_work[(i, k)] != r.get('work'):
            # two distinct works (different DOI / collection work, e.g. Zenodo versions) that DOI resolution mapped to one
            # OpenAlex record: the package keeps both rows, so the release keeps both papers
            split = k; k = 'doi:' + r['doi'] if r.get('doi') else 'work:' + str(r.get('work'))
        pair_work.setdefault((i, k), r.get('work'))
        if r.get('work'):
            by_pi_work.setdefault((i, r['work']), k)
        x = papers.get(k)
        if x is None:
            x = papers[k] = dict(paper_id=k, openalex=r['oa'] if str(r['oa']).startswith('https://openalex.org/') else None, doi=r.get('doi') or None,
                                 title=r.get('title'), year=r.get('year'), date=r.get('date'), venue=r.get('venue'), type=r.get('type'),
                                 landing_url=r.get('landing'), byline=r.get('byline') or [], byline_school=r.get('byline_school') or [],
                                 collection_work=r.get('work'), openalex_shared_with=split, editions=[], labs=[])
        x['collection_work'] = x['collection_work'] or r.get('work')
        for e in r.get('editions') or []:
            e2 = dict(paper_id=paper_id(e.get('oa')), collection_work=e.get('work'), doi=e.get('doi'), year=e.get('year'), venue=e.get('venue'))
            if e2 not in x['editions']:
                x['editions'].append(e2)
        if any(l['pi_id'] == i for l in x['labs']):
            dup_pairs += 1; continue
        ap = r['appointment']
        a = r.get('authorship') or {}
        x['labs'].append(dict(
            pi_id=i, lab_id=byp[i]['lab']['lab_id'], identity=r['identity'],
            appointment=dict(basis='faculty_period', period_id=ap['periodId']) if 'periodId' in ap else
            dict(basis='same_year_listing', **{k: v for k, v in (ap.get('listing') or {}).items() if k in ('year', 'url', 'sha256', 'quote', 'kind')}),
            authorship={k: v for k, v in dict(position=a.get('position'), raw_name=a.get('raw_name'), openalex_author=a.get('author_id'),
                                              institutions=a.get('institutions') or None, raw_affiliations=a.get('raw_affiliations') or None,
                                              school_via=a.get('school_via') or None, page1=a.get('page1')).items() if v is not None},
            source=r.get('source')))
    for x in papers.values():
        x['labs'].sort(key=lambda l: l['pi_id']); x['editions'].sort(key=lambda e: (str(e['paper_id']), str(e['doi'])))
    PA = scrub([papers[k] for k in sorted(papers)])
    pap = {r['paper_id']: r for r in PA}

    # students
    S = {}
    for pi, recs in stu.items():
        i = pid[pi]
        for r in recs:
            sid = r['person'] if str(r['person']).startswith('ext:') else f"{s}:{r['person']}"
            x = S.get(sid)
            if x is None:
                x = S[sid] = dict(student_id=sid, school=s, source_person_id=r['person'], name=r['name'], aliases=[], merged_ids=[],
                                  roles=[], role_label=None, advisors=[])
            for a in [r['name']] + list(r.get('aliases') or []):
                if a != x['name'] and a not in x['aliases']:
                    x['aliases'].append(a)
            for m in r.get('merged') or []:  # former ids, in student_id form, so old ids map to this record
                m = m if str(m).startswith('ext:') else f'{s}:{m}'
                if m not in x['merged_ids']:
                    x['merged_ids'].append(m)
            for ro in r.get('roles') or []:
                if ro not in x['roles']:
                    x['roles'].append(ro)
            rels = r.get('relations') or []
            yrs = sorted({y for rel in rels for y in rel.get('years') or [] if isinstance(y, int)})
            x['advisors'].append(dict(
                pi_id=i, pi_name=pi, lab_id=byp[i]['lab']['lab_id'],
                relation='member' if rels and all(rel['type'] == 'direct_lab_membership' for rel in rels) else 'advisee',
                role_label=SITE.role_label(r.get('roles') or [], rels), first_year=yrs[0] if yrs else None, last_year=yrs[-1] if yrs else None,
                relations=[{k: v for k, v in dict(type=rel.get('type'), role=rel.get('role'), years=[y for y in rel.get('years') or [] if y] or None,
                                                  thesis_work=rel.get('work'), sources=[source_row(z) for z in rel.get('sources') or []]).items() if v is not None}
                           for rel in rels]))
    for x in S.values():
        x['advisors'].sort(key=lambda a: a['pi_id'])
        x['role_label'] = SITE.role_label(x['roles'], [rel for a in x['advisors'] for rel in a['relations']])
    ST = scrub([S[k] for k in sorted(S)])
    stud = {r['student_id']: r for r in ST}

    # student papers
    SP = []
    for x in sp:
        sid = x['student'] if str(x['student']).startswith('ext:') else f"{s}:{x['student']}"
        i = pid[x['pi']]
        SP.append(dict(pi_id=i, student_id=sid, paper_id=by_pi_work.get((i, x.get('work'))) or paper_id(x['oa']), status=x.get('status'), basis=x.get('basis'),
                       collection_work=x.get('work'), student_name=x.get('name')))
    SP = scrub(sorted(SP, key=lambda r: (r['pi_id'], r['student_id'], r['paper_id'])))

    write_jsonl(repo, f'{out}/pis.jsonl.gz', P)
    write_jsonl(repo, f'{out}/papers.jsonl.gz', PA)
    write_jsonl(repo, f'{out}/students.jsonl.gz', ST)
    write_jsonl(repo, f'{out}/student_papers.jsonl.gz', SP)

    # flat CSVs
    write_csv(repo, f'{out}/pis.csv', ['pi_id', 'name', 'department', 'department_coverage', 'scope', 'rank', 'title', 'lab_id', 'lab_name', 'lab_url',
                                       'atlas_unit_id', 'dblp', 'openalex', 'orcid', 'first_period_start', 'listing_years', 'lab_papers', 'students',
                                       'student_paper_links'],
              [[p['pi_id'], p['name'], p['department'], p['department_coverage'], p['scope'], p['rank'], p['title'], p['lab']['lab_id'], p['lab']['name'],
                p['lab']['url'], p['lab']['atlas_unit_id'], ' '.join(p['identifiers']['dblp']),
                ' '.join(p['identifiers']['openalex_reviewed'] or p['identifiers']['openalex_anchored'][:3]), ' '.join(p['identifiers']['orcid']),
                min((str(q['start']) for q in p['periods'] if q['start']), default=None), ' '.join(str(l['year']) for l in p['listings']),
                p['counts'].get('labPapers', 0), p['counts'].get('students', 0), p['counts'].get('studentPaperLinks', 0)] for p in P])
    lp = sorted(((l['pi_id'], x) for x in PA for l in x['labs']), key=lambda t: (t[0], t[1]['paper_id']))
    write_csv(repo, f'{out}/lab_papers.csv', ['pi_id', 'pi_name', 'lab_id', 'department', 'paper_id', 'doi', 'title', 'year', 'venue', 'type', 'identity', 'appointment_basis',
                                              'appointment_ref'],
              [[i, byp[i]['name'], byp[i]['lab']['lab_id'], byp[i]['department'], x['paper_id'], x['doi'], x['title'], x['year'], x['venue'], x['type'],
                l['identity'], l['appointment']['basis'], l['appointment'].get('period_id') or l['appointment'].get('year')]
               for i, x in lp for l in x['labs'] if l['pi_id'] == i])
    ls_rows = []
    for x in ST:
        for a in x['advisors']:
            src0 = next((z for rel in a['relations'] for z in rel.get('sources') or [] if z.get('url')), {})
            ls_rows.append([a['pi_id'], a['pi_name'], x['student_id'], x['name'], a['role_label'], a['relation'], a['first_year'], a['last_year'],
                            ' '.join(sorted({rel['type'] for rel in a['relations']})), src0.get('url')])
    write_csv(repo, f'{out}/lab_students.csv', ['pi_id', 'pi_name', 'student_id', 'student_name', 'role_label', 'relation', 'first_year', 'last_year',
                                                'relation_types', 'source_url'], sorted(ls_rows, key=lambda r: (r[0], r[2])))
    write_csv(repo, f'{out}/student_papers.csv', ['pi_id', 'student_id', 'student_name', 'paper_id', 'doi', 'title', 'year', 'status', 'basis'],
              [[r['pi_id'], r['student_id'], r['student_name'], r['paper_id'], (pap.get(r['paper_id']) or {}).get('doi'),
                (pap.get(r['paper_id']) or {}).get('title'), (pap.get(r['paper_id']) or {}).get('year'), r['status'], r['basis']] for r in SP])

    # review ledgers
    zp = [dict(r, pi_id=pid.get(r['pi'])) for r in zero.get('zero_papers', []) if r.get('school') == s]
    zs = [dict(r, pi_id=pid.get(r['pi'])) for r in zero.get('zero_students', []) if r.get('school') == s]
    write_json(repo, f'{out}/zero_labs.json', scrub(dict(
        note='Labs with zero lab papers (hidden on the site) or zero students, with the funnel diagnosis and the reviewed verdict '
             '(tools/zero_paper_ledger.py).', zero_papers=zp, zero_students=zs)))
    write_json(repo, f'{out}/excluded_pis.json', scrub(dict(
        note='Census PIs excluded by review: no faculty appointment at the school in 2016-2026 (hierarchy/census-overrides.json, gap research).',
        excluded=rep.get('excluded') or [])))
    cr = H / s / 'cs-related-review.json'
    if cr.exists():
        write_json(repo, f'{out}/scope_review.json.gz', scrub(read(cr)))
    write_json(repo, f'{out}/build_report.json', scrub({k: v for k, v in rep.items()}))

    prof = next((x for x in profiles if x['school'] == s), None)
    return dict(school=s, pis=len(P), papers=len(PA), papers_split_from_shared_openalex=sum(bool(x.get('openalex_shared_with')) for x in PA), lab_paper_rows=sum(len(x['labs']) for x in PA), lab_paper_dups_dropped=dup_pairs,
                students=len(ST), lab_student_pairs=sum(len(x['advisors']) for x in ST), student_papers=len(SP),
                pending_department=sum(p['department'] == SITE.PENDING for p in P), profile=bool(prof), package_built=rep.get('builtAt'))


# ---------------------------------------------------------------- atlas

CORE_UNIT = ['id', 'name', 'type', 'field', 'department', 'departments', 'sourceDepartment', 'departmentSource', 'url', 'source', 'aliases', 'years',
             'activity', 'leadershipStatus', 'pi', 'pis', 'leadership', 'evidence', 'paperCounts', 'csScope', 'csScopeReason', 'csShown', 'csHidden',
             'researchSummary', 'papersFile', 'peopleFile', 'peopleCount', 'studentCount']
SNAKE = lambda k: re.sub(r'(?<!^)(?=[A-Z])', '_', k).lower()


def atlas_files(sub):
    """{file name: parsed JSON} for one atlas shard directory (read once)."""
    cache = os.environ.get('EXPORT_ATLAS_CACHE')
    if cache:
        return pickle.load(open(cache, 'rb'))[sub]
    d = ATLAS / 'data' / sub
    return {f: read(d / f) for f in sorted(os.listdir(d))}


def export_atlas(repo):
    data = read(ATLAS / 'data.json')
    unis = data['universities']
    out = 'data/atlas'
    U = []
    for u in unis:
        U.append(dict(university_id=u['id'], name=u['name'], country=u.get('country'), rank=u.get('rank'), rank_low=u.get('rankLow'), url=u.get('url'),
                      cs_scope=u.get('csScope'), counts=u.get('counts'), overview=u.get('overview'), discovery=u.get('discovery'),
                      institution_audit=u.get('institutionAudit')))
    U = scrub(sorted(U, key=lambda r: r['university_id']))
    write_jsonl(repo, f'{out}/universities.jsonl.gz', U)

    shards = atlas_files('universities')
    units, uni_of = [], {}
    for u in unis:
        x = shards.get(u['id'] + '.json.gz') or {}
        for l in x.get('labs') or []:
            uni_of[l['id']] = u['id']
            core = {SNAKE(k): l.get(k) for k in CORE_UNIT if k != 'id'}
            core['papers_file'] = bool(l.get('papersFile')); core['people_file'] = bool(l.get('peopleFile'))
            extra = {k: l[k] for k in sorted(l) if k not in CORE_UNIT}
            units.append(dict(unit_id=l['id'], university_id=u['id'], **core, extra=extra))
    units = scrub(sorted(units, key=lambda r: (r['university_id'], r['unit_id'])))
    files_u = write_jsonl(repo, f'{out}/units.jsonl.gz', units, shard_key='university_id')

    labs = atlas_files('labs')
    works, wconf, UP = {}, 0, []
    WCORE = ['id', 'openalex', 'doi', 'title', 'year', 'date', 'type', 'journal', 'venue', 'authors', 'byline', 'citations', 'topic', 'field',
             'retracted', 'oa', 'url', 'arxiv', 'handle', 'canonicalGraphWorkId', 'aliases', 'countries']
    for f in sorted(labs):
        x = labs[f]; lid = x['labId']
        for wid, w in sorted((x.get('works') or {}).items()):
            if wid in works:
                wconf += any(works[wid].get(k) != w.get(k) for k in ('title', 'doi', 'year'))
                continue
            core = {SNAKE(k): w.get(k) for k in WCORE if k != 'id'}
            core['open_access'] = core.pop('oa'); core['venue'] = core.pop('journal') or core.get('venue'); core['author_count'] = core.pop('authors')
            works[wid] = dict(work_id=wid, **core, extra={k: w[k] for k in sorted(w) if k not in WCORE})
        seen_edge = {}
        for p in x.get('papers') or []:
            w = (x.get('works') or {}).get(p['work']) or works.get(p['work']) or {}
            if p['work'] in seen_edge:  # a second observation of the same unit-work edge: one row, views OR-ed, observation kept
                e = seen_edge[p['work']]
                for v in ('strict', 'reviewed', 'combined'):
                    e['views'][v] = bool(e['views'][v] or p.get(v))
                e['extra'].setdefault('additional_observations', []).append({k: p[k] for k in sorted(p) if k != 'work'})
                continue
            UP.append(dict(unit_id=lid, university_id=uni_of.get(lid), work_id=p['work'], openalex=w.get('openalex') or None, doi=w.get('doi') or None,
                           title=w.get('title'), year=w.get('year'), views=dict(strict=p.get('strict'), reviewed=p.get('reviewed'), combined=p.get('combined')),
                           reason=p.get('reason'), review_source=p.get('reviewSource') or None, temporal=p.get('temporal'), groups=p.get('groups'),
                           unit_attribution_policy=x.get('labAttributionPolicy'),
                           extra={k: p[k] for k in sorted(p) if k not in ('work', 'strict', 'reviewed', 'combined', 'reason', 'reviewSource', 'temporal', 'groups')}))
            seen_edge[p['work']] = UP[-1]
    W = scrub([works[k] for k in sorted(works)])
    files_w = write_jsonl(repo, f'{out}/works.jsonl.gz', W)
    UP = scrub(sorted(UP, key=lambda r: (str(r['university_id']), r['unit_id'], r['work_id'])))
    files_up = write_jsonl(repo, f'{out}/unit_papers.jsonl.gz', UP, shard_key='university_id')

    people = atlas_files('lab-people')
    PE, PW, nctx_drop = [], [], 0
    for f in sorted(people):
        x = people[f]; lid = x['labId']
        for p in x.get('people') or []:
            ctx = []
            for kind in ('memberships', 'researchContexts', 'advisingContexts', 'departmentContexts'):
                for m in p.get(kind) or []:
                    if m.get('labId') == lid:
                        ctx.append(dict(context_kind=kind, **{SNAKE(k): v for k, v in m.items() if k not in ('labId',)}))
            if not ctx:
                nctx_drop += 1; continue
            names = {c.get('lab_name') for c in ctx}
            PE.append(dict(unit_id=lid, university_id=uni_of.get(lid), school=x.get('school'), person_id=p['id'], name=p['name'], aliases=p.get('aliases') or [],
                           roles=p.get('roles') or [], departments=p.get('departments') or [], identity_review=p.get('identityReview'),
                           personal_work_count=p.get('personalWorkCount'), contexts=ctx))
            for w in p.get('works') or []:
                if (w.get('labId') == lid) or (not w.get('labId') and w.get('labName') in names):
                    PW.append(dict(unit_id=lid, university_id=uni_of.get(lid), person_id=p['id'], work_id=w.get('id'), doi=w.get('doi') or None,
                                   title=w.get('title'), year=w.get('year'), date=w.get('date'), type=w.get('type'), status=w.get('status'), role=w.get('role'),
                                   lab_period=w.get('labPeriod'), lab_eligibility=w.get('labEligibility'), identity_basis=w.get('identityBasis'),
                                   evidence=w.get('evidence')))
    PE = scrub(sorted(PE, key=lambda r: (str(r['university_id']), r['unit_id'], r['person_id'])))
    PW = scrub(sorted(PW, key=lambda r: (str(r['university_id']), r['unit_id'], r['person_id'], str(r['work_id']))))
    files_pe = write_jsonl(repo, f'{out}/unit_people.jsonl.gz', PE, shard_key='university_id')
    files_pw = write_jsonl(repo, f'{out}/unit_person_papers.jsonl.gz', PW, shard_key='university_id')

    G = []
    for g in read(ATLAS / 'data/pi-groups.json'):
        r = {k: v for k, v in g.items()}
        for k in ('author_aliases', 'name_aliases_json'):
            if isinstance(r.get(k), str):
                try:
                    r[k] = json.loads(r[k])
                except json.JSONDecodeError:
                    pass
        G.append(r)
    G = scrub(sorted(G, key=lambda r: r['group_id']))
    write_jsonl(repo, f'{out}/pi_identities.jsonl.gz', G)
    write_json(repo, f'{out}/metrics.json.gz', scrub(read(ATLAS / 'data/metrics.json.gz')))
    write_json(repo, f'{out}/scope_rule.json', read(ATLAS / 'data/cs-scope-rule.json'))
    write_json(repo, f'{out}/atlas_summary.json', scrub(dict(
        as_of=data.get('asOf'), title=data.get('title'), window=data.get('window'), fields=data.get('fields'), cs_scope=data.get('csScope'),
        publication_summary=data.get('publicationSummary'), summary=data.get('summary'), census_summary=data.get('censusSummary'),
        leadership_summary=data.get('leadershipSummary'))))
    return dict(universities=len(U), units=len(units), works=len(W), work_conflicts_first_kept=wconf, unit_papers=len(UP),
                unit_paper_observations_merged=sum(len(r['extra'].get('additional_observations') or []) for r in UP), unit_people=len(PE),
                unit_people_without_unit_context=nctx_drop, unit_person_papers=len(PW), pi_identities=len(G),
                units_without_university=sum(1 for r in UP if not r['university_id']),
                files=dict(units=files_u, works=files_w, unit_papers=files_up, unit_people=files_pe, unit_person_papers=files_pw))


# ---------------------------------------------------------------- code


CODE_RULES = [  # (directory in the code repository, max depth, patterns); repo paths mirror it under code/claude-schools-20261021/
    ('tools', 1, ('*.py', '*.slurm')),
    ('hierarchy', 1, ('*.sh', '*.slurm', 'period-targets-method.py')),
    ('hierarchy/nicknames', 1, ('*.csv',)),
    ('census', 1, ('*.py',)),
    ('census/tools', 1, ('*.py', '*.sh')),
    ('listings/scripts', 1, ('*.py', '*.sh')),
    ('fulltext-push', 1, ('*.py', '*.sh')),
    ('tests', 2, ('*.py', '*.json')),     # since 2026-10-29
    ('docs', 1, ('*.md',)),               # since 2026-10-29
    ('', 1, ('paths.sh', '.gitignore')),  # since 2026-10-29
]
CODE_TOOL_DIRS = ['thesis-tools', 'period-tools', 'cs-related-tools', 'few-students-tools', 'few-students-tools-cmu', 'gap-tools-berkeley', 'gap-tools-cmu',
                  'gap-tools-mit', 'gap-tools-princeton-epfl', 'home-dept-tools', 'labpage-tools-cmu', 'labpage-tools-epfl-berkeley',
                  'labpage-tools-princeton-mit', 'missing-pi-tools']
SKIP_DIRS = {'__pycache__', 'work', 'logs', 'local', 'state', 'discover', 'raw', 'captures', 'cache'}
SITE_SCRIPTS = ['build-cs-hierarchy.py', 'build-cs-scope.py', 'cs_scope.py', 'lazy_atlas.py']
CODE = dict(commit=None, uncommitted_tracked_changes=[])


def _git(*a, **kw):
    return subprocess.run(['git', '-C', str(HERE), *a], capture_output=True, check=True, **kw).stdout


def code_files():
    """[(bytes, repo path)]: the files the rules select among those tracked at the code repository's HEAD, with their
    committed content (git cat-file), plus the site builder's scripts the export documents."""
    import fnmatch
    CODE['commit'] = _git('rev-parse', 'HEAD', text=True).strip()
    CODE['uncommitted_tracked_changes'] = [l[3:] for l in _git('status', '--porcelain', '--untracked-files=no', text=True).split('\n') if l.strip()]
    rules = list(CODE_RULES) + [(f'hierarchy/{d}', 3, ('*.py', '*.sh', '*.slurm', '*.md')) for d in CODE_TOOL_DIRS] + \
        [(f'hierarchy/{s}/cs-related-tools', 2, ('*.py', '*.sh', '*.md')) for s in AP.SCHOOL_IDS]
    want = []
    for path in _git('ls-tree', '-r', '--name-only', '-z', CODE['commit']).decode().split('\0'):
        if not path:
            continue
        parts = path.split('/')
        for d, depth, pats in rules:
            dp = d.split('/') if d else []
            rest = parts[len(dp):]
            if parts[:len(dp)] != dp or not 1 <= len(rest) <= depth or any(x in SKIP_DIRS or x.startswith('.') for x in rest[:-1]):
                continue
            name = rest[-1]
            if any(fnmatch.fnmatch(name, p) for p in pats) and '.bak' not in name and not name.endswith('.env'):
                want.append(path); break
    out = []
    if want:
        blobs = subprocess.run(['git', '-C', str(HERE), 'cat-file', '--batch'], input=''.join(f"{CODE['commit']}:{p}\n" for p in want).encode(),
                               capture_output=True, check=True).stdout
        i = 0
        for p in want:
            header_end = blobs.index(b'\n', i)
            size = int(blobs[i:header_end].split()[2])
            out.append((blobs[header_end + 1:header_end + 1 + size], 'code/claude-schools-20261021/' + p))
            i = header_end + 1 + size + 1
    for f in SITE_SCRIPTS:
        if (SITE_ROOT / 'scripts' / f).exists():
            out.append(((SITE_ROOT / 'scripts' / f).read_bytes(), 'code/princeton-live-20261015/scripts/' + f))
    return sorted(out, key=lambda t: t[1])


def scrub_code(s):
    if '@' not in s:
        return s

    def em(m):
        e = m.group(0).lower()
        if e == PLACEHOLDER_EMAIL or e.endswith('@example.org') or e.startswith('noreply@') or '@lists.' in e:
            return m.group(0)
        RED['code_email_owner' if is_owner(e) else 'code_email'] += 1
        return PLACEHOLDER_EMAIL if is_owner(e) else '[email removed]'
    return EMAIL.sub(em, s)


def export_code(repo):
    stats = collections.Counter()
    old = repo / 'code'
    for sub in ('claude-schools-20261021', 'princeton-live-20261015'):
        if (old / sub).exists():
            shutil.rmtree(old / sub)
    for t, rel in code_files():
        try:
            s = t.decode()
        except UnicodeDecodeError:
            stats['skipped_binary'] += 1; continue
        n0 = sum(RED.values())
        s = scrub_code(s)  # e-mails only (owner -> placeholder); paths stay as written: they document the original layout
        stats['files'] += 1; stats['files_redacted'] += sum(RED.values()) > n0
        write_bytes(repo, rel, s.encode())
    return dict(stats, commit=CODE['commit'], uncommitted_tracked_changes_not_exported=CODE['uncommitted_tracked_changes'])


# ---------------------------------------------------------------- README coverage table


def _load_tool(name):
    spec = importlib.util.spec_from_file_location(name, HERE / 'tools' / f'{name}.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    if hasattr(m, 'H'):  # the tool reads the same data this export reads (a release, or the working root)
        m.H = H
    if hasattr(m, 'HERE'):
        m.HERE = DATA
    return m


def derived_ledgers(homes_all):
    """school-profiles.json and zero-paper-labs.json as written by their tools, or, when a package was rebuilt after them,
    recomputed in memory with those tools' own functions (nothing is written to the sources)."""
    newest = max(read(H / s / 'report.json').get('builtAt') or '' for s in EXPORT)
    import datetime
    mt = lambda p: datetime.datetime.utcfromtimestamp(p.stat().st_mtime).isoformat() if p.exists() else ''
    zp, pp = H / 'zero-paper-labs.json', H / 'school-profiles.json'
    out = {}
    if mt(zp) >= newest[:26]:
        zero = read(zp); out['zero_paper_labs'] = 'file'
    else:
        Z = _load_tool('zero_paper_ledger')
        rv = read(H / 'zero-paper-review.json') if (H / 'zero-paper-review.json').exists() else {}
        zero = dict(built_by='tools/zero_paper_ledger.py (recomputed by export_release.py)', zero_papers=[], zero_students=[])
        for s in EXPORT:
            for p in read(H / s / 'pis.json'):
                c = p.get('counts') or {}; f = p.get('funnel') or {}
                if not c.get('labPapers'):
                    r = (rv.get(s) or {}).get(p['pi']) or {}
                    zero['zero_papers'].append(dict(school=s, pi=p['pi'], departments=p.get('departments'), rank=p.get('rank'), title=p.get('title'),
                                                    diagnosis=Z.diagnose(p), verdict=r.get('verdict', 'unreviewed'), reason=r.get('reason'), evidence=r.get('evidence'),
                                                    funnel={k: v for k, v in f.items() if not k.startswith('outside_appointment_')},
                                                    outside_appointment_by_year={k[-4:]: v for k, v in f.items() if k.startswith('outside_appointment_')},
                                                    periods=[(q.get('start'), q.get('end')) for q in p.get('periods') or []],
                                                    listing_years=[l['year'] for l in p.get('listings') or []], students=c.get('students', 0)))
                if not c.get('students'):
                    zero['zero_students'].append(dict(school=s, pi=p['pi'], departments=p.get('departments'), lab_papers=c.get('labPapers', 0)))
        out['zero_paper_labs'] = 'recomputed (file older than the packages)'
    if mt(pp) >= newest[:26] and all(any(x['school'] == s for x in read(pp)) for s in EXPORT):
        profiles = read(pp); out['school_profiles'] = 'file'
    else:
        SPF = _load_tool('school_profiles')
        homes = collections.defaultdict(dict)
        for r in homes_all:
            if r.get('status') == 'accepted' and r.get('home_department'):
                homes[r['school']][r['name']] = r
        audit = read(H / 'missing-papers-audit.json') if (H / 'missing-papers-audit.json').exists() else []
        missing = [s for s in EXPORT if s not in SPF.NAMES]
        if missing:
            raise SystemExit(f'add {missing} to NAMES in tools/school_profiles.py')
        profiles = [SPF.profile(s, homes, audit, zero) for s in EXPORT]
        out['school_profiles'] = 'recomputed (file older than the packages)'
    return profiles, zero, out


def readme_coverage(repo, profiles, summary):
    """Rewrite the table between <!-- coverage:start --> and <!-- coverage:end --> in README.md from the profiles."""
    rp = repo / 'README.md'
    if not rp.exists():
        return
    t = rp.read_text()
    a, b = '<!-- coverage:start -->', '<!-- coverage:end -->'
    if a not in t or b not in t:
        return
    P = [next(p for p in profiles if p['school'] == s) for s in EXPORT if any(p['school'] == s for p in profiles)]
    rep = {x['school']: x for x in summary['schools']}
    fmt = lambda v: f'{v:,}' if isinstance(v, int) else str(v)
    rows_ = [('PI labs', lambda p: p['pis']), ('… core computing departments', lambda p: p['pis_core']),
             ('… CS-related, other departments', lambda p: p['pis_cs_related_additions']), ('Home departments', lambda p: p['departments']),
             ('Unique lab papers', lambda p: p['lab_papers_unique']), ('Lab–paper rows (a paper can belong to several labs)', lambda p: p['lab_paper_rows']),
             ('Median lab papers per PI', lambda p: p['median_papers_per_pi']), ('Students (unique people)', lambda p: p['students_unique']),
             ('Lab–student pairs', lambda p: rep[p['school']]['lab_student_pairs']), ('Student–paper links', lambda p: p['student_paper_links']),
             ('Labs with papers', lambda p: p['pis_with_lab_papers']), ('Labs with students', lambda p: p['pis_with_students']),
             ('Labs with papers, students and links', lambda p: p['pis_complete_chain']),
             ('DBLP-published papers we hold', lambda p: f"{p['dblp_reference']['published']['coverage']:.0%}" if (p.get('dblp_reference') or {}).get('published') else '—')]
    out = ['| | ' + ' | '.join(p['name'] for p in P) + ' |', '|---|' + '---|' * len(P)]
    out += ['| ' + label + ' | ' + ' | '.join(fmt(f(p)) for p in P) + ' |' for label, f in rows_]
    old = t[t.index(a) + len(a):t.index(b)]
    atlas_line = next((l for l in old.splitlines() if l.startswith('Wider atlas:')), '')
    if summary.get('atlas'):
        x = summary['atlas']
        atlas_line = (f"Wider atlas: {x['universities']:,} universities, {x['units']:,} units, {x['works']:,} works, {x['unit_papers']:,} unit–paper links, "
                      f"{x['unit_people']:,} unit–person rows,\n{x['unit_person_papers']:,} person–paper links, {x['pi_identities']:,} PI identities.")
    body = '\n' + '\n'.join(out) + '\n\n' + atlas_line + '\n'
    rp.write_text(t[:t.index(a) + len(a)] + body + t[t.index(b):])


def methods_student_audit(repo, audit):
    """Rewrite the student-audit table between <!-- student-audit:start/end --> in docs/METHODS.md."""
    mp = repo / 'docs/METHODS.md'
    if not mp.exists() or not audit:
        return
    t = mp.read_text(); a, b = '<!-- student-audit:start -->', '<!-- student-audit:end -->'
    if a not in t or b not in t:
        return
    A = [next(x for x in audit if x['school'] == s) for s in EXPORT if any(x['school'] == s for x in audit)]
    rows_ = [('Lab–student pairs', 'lab_student_pairs'), ('Probable duplicate pairs within one lab', 'within_lab_pairs'),
             ('People under several student ids across labs', 'across_lab_people'), ('Papers linked to two ids of one person', 'same_paper_pairs'),
             ('Students with probably missed paper links', 'students_with_missed_links'), ('Probably missed student–paper links', 'missed_links'),
             ('Students with no paper link', 'students_without_links')]
    out = ['| | ' + ' | '.join(x['school'] for x in A) + ' |', '|---|' + '---|' * len(A)]
    out += ['| ' + l + ' | ' + ' | '.join(f"{(x.get('counts') or {}).get(k, 0):,}" for x in A) + ' |' for l, k in rows_]
    mp.write_text(t[:t.index(a) + len(a)] + '\n' + '\n'.join(out) + '\n' + t[t.index(b):])


# ---------------------------------------------------------------- main


def main():
    argv = list(sys.argv[1:]); rel = None
    if '--release' in argv:
        i = argv.index('--release'); rel = argv[i + 1]; del argv[i:i + 2]
    rel = next((a.split('=', 1)[1] for a in argv if a.startswith('--release=')), rel)
    args = [a for a in argv if not a.startswith('--')]
    if len(args) != 1:
        raise SystemExit(__doc__)
    repo = Path(args[0]).resolve(); repo.mkdir(parents=True, exist_ok=True)
    configure(None if '--from-working' in sys.argv else (rel or 'latest'))
    print('data', RELEASE or f'working root {DATA} (--from-working)', flush=True)
    homes_all = read(H / 'home-departments.json')
    profiles, zero, derived = derived_ledgers(homes_all)
    summary = dict(schools=[], atlas=None, code=None, derived_ledgers=derived)
    for s in EXPORT:
        print('school', s, flush=True)
        summary['schools'].append(export_school(repo, s, homes_all, profiles, zero))
    write_json(repo, 'data/schools/profiles.json', scrub(profiles))
    audit = None
    ap = H / 'student-audit.json'
    newest = max(read(H / s / 'report.json').get('builtAt') or '' for s in EXPORT)
    import datetime
    if ap.exists() and datetime.datetime.utcfromtimestamp(ap.stat().st_mtime).isoformat() >= newest[:26] \
            and {x['school'] for x in read(ap)} >= set(EXPORT):
        audit = read(ap); summary['derived_ledgers']['student_audit'] = 'file'
    elif (HERE / 'tools/student_audit.py').exists():  # older than a package: recompute with the tool's own read-only audit()
        audit = [_load_tool('student_audit').audit(s) for s in EXPORT]; summary['derived_ledgers']['student_audit'] = 'recomputed (file older than the packages)'
    if audit:  # tools/student_audit.py: probable duplicate student records and missed student-paper links
        write_json(repo, 'data/schools/student_audit.json', scrub(audit))
    if summary['derived_ledgers']['school_profiles'] == 'file' and (H / 'SCHOOL-PROFILES.md').exists():
        md = (H / 'SCHOOL-PROFILES.md').read_text()
    else:
        md = _load_tool('school_profiles').md(profiles)
    write_bytes(repo, 'docs/SCHOOL-PROFILES.md', scrub_str(md).encode())
    if '--skip-atlas' not in sys.argv:
        print('atlas', flush=True)
        summary['atlas'] = export_atlas(repo)
    if '--skip-code' not in sys.argv:
        print('code', flush=True)
        n0 = RED.copy()
        summary['code'] = export_code(repo)
        summary['code']['redactions'] = dict(RED - n0)
    summary['redactions'] = dict(sorted(RED.items()))
    readme_coverage(repo, profiles, summary)
    methods_student_audit(repo, audit)
    summary['sources'] = dict(hierarchy=str(H), atlas=str(ATLAS), schools=EXPORT, skipped_schools=SKIPPED)
    summary['release'] = RELEASE  # the dated release the school data came from (None: the working root, development only)
    files = {k: MANIFEST[k] for k in sorted(MANIFEST)}
    mp = repo / 'MANIFEST.json'
    if mp.exists() and ('--skip-atlas' in sys.argv or '--skip-code' in sys.argv):  # keep the entries this run did not rewrite
        prev_m = json.loads(mp.read_text()); prev = prev_m['files']
        for part in ('atlas', 'code'):  # carry the summary of the part this run did not rewrite
            if summary.get(part) is None and (prev_m.get('export') or {}).get(part):
                summary[part] = prev_m['export'][part]
        files = {k: v for k, v in sorted({**prev, **files}.items()) if (repo / k).exists()}
    mp.write_text(json.dumps(dict(export=summary, files=files), ensure_ascii=False, indent=1) + '\n')
    print(json.dumps(summary, indent=1))
    big = [k for k, v in files.items() if v['bytes'] >= MAX_FILE]
    if big:
        raise SystemExit(f'files over 50 MB: {big}')
    t = repo / 'tests/verify_release.py'
    if t.exists():
        sys.exit(subprocess.call([sys.executable, str(t), str(repo)]))


if __name__ == '__main__':
    main()
