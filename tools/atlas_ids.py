"""Stable atlas ids for people, works and labs (2026-10-29, owner; docs/IDS.md, rules R-ID-01..05).

  atl:p:<12 hex>            a person (PI or student), one id across labs and schools
  atl:w:<12 hex>            a work (a unique paper; editions share it), one id across labs and schools
  atl:l:<school>:<pi-slug>  a PI lab (one per PI and school)

Ids are opaque and deterministic: an entity's anchors (identifiers) are ranked, and a new id is the sha256 of its strongest
anchor. Once issued an id never changes: the registry (hierarchy/ids/registry.sqlite) maps every anchor ever seen to its
id, and a later build finds an entity's id through any of its anchors, so a new ORCID or DOI joins the existing id.
Two issued ids that turn out to be one entity are merged by a redirect (the earlier-issued id stays; the other is kept in
the registry with status 'redirect', never reissued).

Anchors (strongest first)
  person  orcid:<id> | openalex:<A id> (reviewed for a PI; for a student, a byline author id that is a PI's reviewed id,
          with a compatible name) | dblp:<pid> | coll:<school>:<collection person id> | name:<school>:<name>:<evidence url>
  work    doi:<doi> (not arXiv) | openalex:<W id> | dblp:<key> | arxiv:<id> | coll:<school>:<collection work> | labpage:<sha1>
  lab     lab:<school>:<person atlas id>
Name anchors are a fallback for records with no identifier (ext: students); they carry the evidence url, so the same name
on two different pages never joins two records (R-HIER-03: a name alone never makes one person across labs). A join by
an identifier between two people whose family names differ is refused and reported (conflicts).

Writes the ids into the packages in place (hierarchy/<school>/):
  pis.json            atlasId, labId, appointments (every school where this person is a PI, with the lab id)
  students.json       atlasId (and alsoPi: the PI appointments of a student who is faculty in the atlas)
  lab_papers.jsonl.gz atlasWorkId
  student_papers.jsonl.gz  studentAtlasId, atlasWorkId, labId
and hierarchy/ids/: registry.sqlite, crossref.tsv.gz (atlas id <-> OpenAlex, DBLP, ORCID, DOI, arXiv, collection ids,
legacy ids), redirects.tsv, persons-cross-school.json, IDS-REPORT.json.
A missing registry is seeded from releases/latest/hierarchy/ids/registry.sqlite.
usage: atlas_ids.py [--registry PATH] [--dir HIERARCHY] [--no-sweep] [school ...]   (default: every released school)
"""
import argparse, collections, csv, gzip, hashlib, io, json, re, shutil, sqlite3, sys, unicodedata, zlib
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402  (every path in one place)

RANK = {'orcid': 0, 'openalex': 1, 'dblp': 2, 'coll': 3, 'name': 4,                                   # people
        'doi': 0, 'oaw': 1, 'dblpkey': 2, 'arxiv': 3, 'collw': 4, 'labpage': 5}                     # works
STRONG_PERSON = {'orcid', 'openalex', 'dblp'}
WSCHEME = {'doi': 'doi', 'oaw': 'openalex', 'dblpkey': 'dblp', 'arxiv': 'arxiv', 'collw': 'coll', 'labpage': 'labpage'}
SEP = '\x1f'


# ---------------------------------------------------------------- normalizers

def fold(s):
    s = unicodedata.normalize('NFKD', str(s or '')); s = ''.join(c for c in s if not unicodedata.combining(c))
    return s.translate(str.maketrans({'ı': 'i', 'ł': 'l', 'Ł': 'l', 'ø': 'o', 'Ø': 'o', 'đ': 'd', 'ß': 'ss', 'æ': 'ae'})).lower()


def nname(s):
    s = fold(s)
    if ',' in s:  # 'Family, Given'
        a, b = s.split(',', 1); s = b + ' ' + a
    return '-'.join(re.findall(r'[a-z0-9]+', s))


def slug(s):  # as tools/export_release.py and tools/organize_tree.py
    s = unicodedata.normalize('NFKD', str(s)); s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def name_toks(s):
    s = fold(s)
    if ',' in s:
        a, b = s.split(',', 1); s = b + ' ' + a
    t = [x for x in re.findall(r'[a-z]+', s) if x not in {'jr', 'sr', 'ii', 'iii', 'iv', 'dr', 'prof'}]
    return t


def family(s):
    t = name_toks(s)
    return t[-1] if t else ''


def compatible(a, b, nick=None):
    """Two forms of one person's name: the same family name and the same first full given name (or a nickname pair).
    Initials never count."""
    ta, tb = name_toks(a), name_toks(b)
    if not ta or not tb or ta[-1] != tb[-1]:
        return False
    ga = [x for x in ta[:-1] if len(x) > 1]; gb = [x for x in tb[:-1] if len(x) > 1]
    if not ga or not gb:
        return False
    if set(ga) & set(gb):
        return True
    return bool(nick) and any(nick(x, y) for x in ga for y in gb)


def norm_orcid(o):
    m = re.search(r'(\d{4}-\d{4}-\d{4}-\d{3}[\dXx])', str(o or ''))
    return m.group(1).upper() if m else None


def norm_oa(o, kind='A'):
    m = re.search(rf'\b({kind}\d+)\b', str(o or ''))
    return m.group(1) if m else None


def norm_dblp_pid(u):
    u = str(u or '')
    m = re.search(r'dblp\.org/pid/(.+?)(?:\.html|\.xml)?$', u) or re.match(r'^(?:pid/)?([a-z0-9]+/[\w-]+)$', u)
    return m.group(1) if m else None


def norm_dblp_key(u):
    u = str(u or '')
    while u.startswith('https://dblp.org/rec/'):
        u = u[len('https://dblp.org/rec/'):]
    return u if re.match(r'^(conf|journals|books|series|phd|reference|tr|persons|informal)/', u) else None


def norm_doi(d):
    d = str(d or '').strip().lower()
    d = re.sub(r'^(?:doi:|https?://(?:dx\.)?doi\.org/)', '', d)
    return d if d.startswith('10.') else None


def arxiv_of(doi):
    m = re.match(r'^10\.48550/arxiv\.(.+)$', doi or '')
    return re.sub(r'v\d+$', '', m.group(1)) if m else None


# ---------------------------------------------------------------- anchors

def work_anchors(r, school):
    """The anchors of one lab-paper row (and its editions)."""
    out = set()
    for x in [r] + list(r.get('editions') or []):
        oa = str(x.get('oa') or ''); w = str(x.get('work') or '')
        for d in (x.get('doi'), w[4:] if w.startswith('doi:') else None):
            d = norm_doi(d)
            if d:
                out.add(('arxiv', arxiv_of(d)) if arxiv_of(d) else ('doi', d))
        if w.startswith('arxiv:'):
            out.add(('arxiv', re.sub(r'v\d+$', '', w[6:])))
        if oa.startswith('https://openalex.org/') and norm_oa(oa, 'W'):
            out.add(('oaw', norm_oa(oa, 'W')))
        elif oa.startswith('https://dblp.org/rec/') and norm_dblp_key(oa):
            out.add(('dblpkey', norm_dblp_key(oa)))
        elif oa.startswith('labpage:'):
            out.add(('labpage', oa[8:]))
        if w and not re.match(r'^(doi:|arxiv:|https?:|labpage:)', w):
            out.add(('collw', f'{school}:{w}'))
    return out


def person_anchor_str(k, v):
    return f'p|{k}:{v}'


class UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        p = self.p
        p.setdefault(x, x)
        while p[x] != x:
            p[x] = p[p[x]]; x = p[x]
        return x

    def union(self, a, b):
        a, b = self.find(a), self.find(b)
        if a != b:
            if b < a:
                a, b = b, a
            self.p[b] = a


# ---------------------------------------------------------------- registry

SCHEMA = """
create table if not exists ids (id text primary key, kind text not null, minted_from text not null, issued text not null,
                                status text not null default 'active', redirect_to text, note text);
create table if not exists anchors (anchor text primary key, id text not null, kind text not null, first_seen text not null);
create table if not exists meta (k text primary key, v text);
"""


def open_registry(path, seed=True):
    path = Path(path)
    if not path.exists() and seed:
        rel = P.RELEASES / 'latest' / 'hierarchy' / 'ids' / 'registry.sqlite'
        if rel.exists():
            path.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(rel, path); path.chmod(0o644)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path), timeout=120)
    db.executescript(SCHEMA)
    return db


def resolve(db, i):
    seen = set()
    while i and i not in seen:
        seen.add(i)
        row = db.execute('select status, redirect_to from ids where id=?', (i,)).fetchone()
        if not row or row[0] != 'redirect':
            return i
        i = row[1]
    return i


def mint(db, prefix, anchor, kind, today, taken):
    n = 0
    while True:
        h = hashlib.sha256((anchor + ('' if n == 0 else f'#{n}')).encode()).hexdigest()[:12]
        i = f'{prefix}{h}'
        if i not in taken and not db.execute('select 1 from ids where id=?', (i,)).fetchone():
            db.execute('insert into ids (id, kind, minted_from, issued) values (?,?,?,?)', (i, kind, anchor, today))
            taken.add(i)
            return i
        n += 1


def assign(db, kind, prefix, comps, today, stats):
    """comps: {component key: sorted list of (rank, anchor string)}. Returns {component key: id}. Deterministic: components are
    processed in the order of their strongest anchor; a registry hit wins; several hits merge into the earliest issued."""
    out = {}
    taken = set()
    # an anchor held by two components (two rows of one lab the builder keeps apart behind one OpenAlex record; a join
    # refused for differing family names) is ambiguous: it never finds or merges ids, and it is never registered; it is
    # used only to recognise the id that was minted from it
    cnt = collections.Counter(a for c in comps for _, a in comps[c])
    amb = {a for a, n in cnt.items() if n > 1}
    stats['ambiguous_anchors'] += len(amb)
    order = sorted(comps, key=lambda c: (comps[c], str(c)))
    claims = collections.defaultdict(list)
    issued = lambda i: (db.execute('select issued from ids where id=?', (i,)).fetchone() or ('9',))[0] + i
    for c in order:
        own = [a for _, a in comps[c] if a not in amb]
        hits = set()
        for a in own:
            row = db.execute('select id from anchors where anchor=?', (a,)).fetchone()
            if row:
                hits.add(resolve(db, row[0]))
        if not hits:
            mine = {a for _, a in comps[c]}
            for a in mine & amb:
                row = db.execute('select id from anchors where anchor=?', (a,)).fetchone()
                if row:
                    i = resolve(db, row[0]); mf = db.execute('select minted_from from ids where id=?', (i,)).fetchone()
                    if mf and mf[0] in mine:
                        hits.add(i)
        hits = sorted(hits, key=issued)
        if hits:
            keep = hits[0]
            for other in hits[1:]:
                db.execute("update ids set status='redirect', redirect_to=? where id=?", (keep, other))
                db.execute('update anchors set id=? where id=?', (keep, other))
                stats['redirects_new'] += 1
            claims[keep].append(c)
        else:
            out[c] = mint(db, prefix, (own or [a for _, a in comps[c]])[0], kind, today, taken); stats['minted'] += 1
    for i, cs in claims.items():  # one id claimed by several components (an entity that the data now splits)
        if len(cs) == 1:
            out[cs[0]] = i; stats['reused'] += 1; continue
        mf = db.execute('select minted_from from ids where id=?', (i,)).fetchone()[0]
        keeper = next((c for c in cs if mf in {a for _, a in comps[c]}), cs[0])
        for c in cs:
            if c == keeper:
                out[c] = i; stats['reused'] += 1
            else:
                out[c] = mint(db, prefix, ([a for _, a in comps[c] if a not in amb] or [comps[c][0][1]])[0], kind, today, taken); stats['split_minted'] += 1
    for c, i in out.items():
        for _, a in comps[c]:
            if a in amb:
                continue
            row = db.execute('select id from anchors where anchor=?', (a,)).fetchone()
            if row is None:
                db.execute('insert into anchors (anchor, id, kind, first_seen) values (?,?,?,?)', (a, i, kind, today))
            elif resolve(db, row[0]) != i and len(claims.get(resolve(db, row[0]), [])) <= 1:
                db.execute('update anchors set id=? where anchor=?', (i, a))
    return out


# ---------------------------------------------------------------- reading

def load_school(D):
    pis = json.loads((D / 'pis.json').read_text())
    stu = json.loads((D / 'students.json').read_text())
    rows = [json.loads(l) for l in gzip.open(D / 'lab_papers.jsonl.gz', 'rt')]
    sp = [json.loads(l) for l in gzip.open(D / 'student_papers.jsonl.gz', 'rt')]
    return pis, stu, rows, sp


def student_urls(r):
    return sorted({q.get('url') for rel in r.get('relations') or [] for q in rel.get('sources') or [] if q.get('url')})


def byline_author_ids(school, wanted, hdir):
    """{(openalex work id, raw byline name): author id} for the wanted pairs, from the school's OpenAlex sweep."""
    out = {}
    db = hdir / school / 'openalex-sweep.sqlite'
    if not wanted or not db.exists():
        return out
    want_w = {w for w, _ in wanted}
    c = sqlite3.connect(f'file:{db}?mode=ro', uri=True, timeout=120)
    for (body,) in c.execute('select body from pages'):
        for w in json.loads(zlib.decompress(body)):
            wid = norm_oa(w.get('id'), 'W')
            if wid not in want_w:
                continue
            for a in w.get('authorships') or []:
                raw = a.get('raw_author_name') or (a.get('author') or {}).get('display_name')
                aid = norm_oa((a.get('author') or {}).get('id'), 'A')
                if aid and (wid, raw) in wanted:
                    out[(wid, raw)] = aid
    c.close()
    return out


# ---------------------------------------------------------------- main

def run(schools, hdir, registry, use_sweep=True, today=None, write=True):
    today = today or datetime.now(timezone.utc).strftime('%Y-%m-%d')
    hdir = Path(hdir)
    try:
        sys.path.insert(0, str(P.TOOLS)); from pi_hierarchy import nick_ok  # noqa: E402
    except Exception:  # pragma: no cover
        nick_ok = None
    data = {s: load_school(hdir / s) for s in schools}
    stats = collections.Counter()
    # ---- people
    ents = {}      # entity key -> dict(kind, school, name, anchors set of (k, v), ref)
    for s, (pis, stu, rows, sp) in data.items():
        for p in pis:
            k = ('pi', s, p['pi'])
            A = {('orcid', o) for o in map(norm_orcid, (p.get('orcid') or []) + (p.get('orcidFromDblp') or [])) if o}
            mixed = {norm_oa(x) for x in p.get('mixedOpenAlex') or []}
            A |= {('openalex', a) for a in map(norm_oa, p.get('reviewedOpenAlex') or []) if a and a not in mixed}
            A |= {('dblp', d) for d in map(norm_dblp_pid, p.get('dblp') or []) if d}
            A |= {('coll', f'{s}:{i}') for i in p.get('personIds') or [] if i and not str(i).startswith('ext:')}
            if not A:
                urls = sorted({e.get('url') for q in p.get('periods') or [] for e in q.get('evidence') or [] if e.get('url')}
                              | {l.get('url') for l in p.get('listings') or [] if l.get('url')})
                A = {('name', f'{s}:{nname(p["pi"])}:{u}') for u in urls[:1]} or {('name', f'{s}:{nname(p["pi"])}:pi')}
            ents[k] = dict(kind='pi', school=s, name=p['pi'], names=p.get('names') or [p['pi']], anchors=A)
        for pi, recs in stu.items():
            for r in recs:
                k = ('stu', s, pi, r['person'])
                ids_ = [r['person']] + [m for m in r.get('merged') or []]
                A = {('coll', f'{s}:{i}') for i in ids_ if i and not str(i).startswith('ext:')}
                if not A:
                    urls = student_urls(r)
                    A = {('name', f'{s}:{nname(r["name"])}:{u}') for u in urls} or {('name', f'{s}:{nname(r["name"])}:lab:{slug(pi)}')}
                ents[k] = dict(kind='stu', school=s, name=r['name'], names=[r['name']] + list(r.get('aliases') or []), anchors=A)
    # students who are PIs elsewhere in the atlas: a byline author id on one of the student's linked lab papers that is a
    # PI's reviewed OpenAlex id, with compatible names (Danqi Chen: Manning's student at Stanford, PI at Princeton)
    pi_by_oa = collections.defaultdict(list)
    for k, e in ents.items():
        if e['kind'] == 'pi':
            for a, v in e['anchors']:
                if a == 'openalex':
                    pi_by_oa[v].append(k)
    student_oa_evidence = {}
    if use_sweep:
        for s, (pis, stu, rows, sp) in data.items():
            wanted = {(norm_oa(x.get('oa'), 'W'), x.get('byline')) for x in sp if x.get('byline') and norm_oa(x.get('oa'), 'W')}
            # cheap prefilter: only bylines whose family name is some PI's family name
            pi_fams = {family(n) for e in ents.values() if e['kind'] == 'pi' for n in e['names']}
            wanted = {(w, b) for w, b in wanted if family(b) in pi_fams}
            got = byline_author_ids(s, wanted, hdir)
            for x in sp:
                aid = got.get((norm_oa(x.get('oa'), 'W'), x.get('byline')))
                if not aid or aid not in pi_by_oa:
                    continue
                sk = ('stu', s, x['pi'], x['student'])
                if sk not in ents:
                    continue
                for pk in pi_by_oa[aid]:
                    if pk[1:] == (s, x['pi']):
                        continue
                    if any(compatible(a, b, nick_ok) for a in ents[sk]['names'] for b in ents[pk]['names']) and \
                            any(compatible(x['byline'], b, nick_ok) for b in ents[pk]['names']):
                        ents[sk]['anchors'].add(('openalex', aid))
                        student_oa_evidence.setdefault(sk, dict(openalex=aid, work=x.get('oa'), byline=x.get('byline'), pi=pk[2], pi_school=pk[1]))
    uf = UF(); by_anchor = collections.defaultdict(list)
    for k, e in ents.items():
        uf.find(k)
        for a in e['anchors']:
            by_anchor[a].append(k)
    conflicts = []
    for a, ks in sorted(by_anchor.items()):
        k0 = ks[0]
        for k in ks[1:]:
            if a[0] in STRONG_PERSON and not any(family(x) == family(y) for x in ents[k0]['names'] for y in ents[k]['names']):
                conflicts.append(dict(anchor=person_anchor_str(*a), a=list(k0), b=list(k))); continue
            uf.union(k0, k)
    comps = collections.defaultdict(set)
    for k in ents:
        comps[uf.find(k)] |= {(RANK[a], person_anchor_str(a, v)) for a, v in ents[k]['anchors']}
    comps = {c: sorted(v) for c, v in comps.items()}
    pid = assign(db := registry, 'person', 'atl:p:', comps, today, stats)
    person_of = {k: pid[uf.find(k)] for k in ents}
    # ---- labs
    lab_comps = {}
    for k, e in ents.items():
        if e['kind'] == 'pi':
            lab_comps[k] = [(0, f'l|lab:{e["school"]}:{person_of[k]}')]
    lab_ids = {}
    for k, anchors in sorted(lab_comps.items()):
        row = db.execute('select id from anchors where anchor=?', (anchors[0][1],)).fetchone()
        if row:
            lab_ids[k] = row[0]; stats['labs_reused'] += 1
        else:
            i = f'atl:l:{k[1]}:{slug(k[2])}'
            n = 1
            while db.execute('select 1 from ids where id=?', (i,)).fetchone():
                n += 1; i = f'atl:l:{k[1]}:{slug(k[2])}-{n}'
            db.execute('insert into ids (id, kind, minted_from, issued) values (?,?,?,?)', (i, 'lab', anchors[0][1], today))
            db.execute('insert into anchors (anchor, id, kind, first_seen) values (?,?,?,?)', (anchors[0][1], i, 'lab', today))
            lab_ids[k] = i; stats['labs_minted'] += 1
    # ---- works
    wents = {}
    for s, (pis, stu, rows, sp) in data.items():
        for j, r in enumerate(rows):
            wents[(s, j)] = work_anchors(r, s) or {('collw', f'{s}:row:{r["pi"]}:{r.get("title")}')}
    wuf = UF(); wby = collections.defaultdict(list)
    for k, A in wents.items():
        wuf.find(k)
        for a in A:
            wby[a].append(k)
    for a, ks in wby.items():
        for k in ks[1:]:
            wuf.union(ks[0], k)
    # a component holding two rows of one lab is two papers the builder kept apart (e.g. two Zenodo versions behind one
    # OpenAlex record): such rows join only through their own lead record (row oa / doi / work), not through editions
    groups = collections.defaultdict(list)
    for k in wents:
        groups[wuf.find(k)].append(k)
    for g, ks in list(groups.items()):
        labs_ = collections.Counter((k[0], data[k[0]][2][k[1]]['pi']) for k in ks)
        if max(labs_.values()) > 1:
            stats['work_components_split'] += 1
            for k in ks:
                wuf.p[k] = k
            lead = {k: work_anchors(dict(data[k[0]][2][k[1]], editions=[]), k[0]) for k in ks}
            for k in ks:  # these rows register only their own lead anchors (an edition that is another row's lead is not theirs)
                wents[k] = lead[k] or wents[k]
            lb = collections.defaultdict(list)
            for k in ks:
                for a in lead[k]:
                    lb[a].append(k)
            for a, kk in lb.items():
                for k in kk[1:]:
                    if (k[0], data[k[0]][2][k[1]]['pi']) != (kk[0][0], data[kk[0][0]][2][kk[0][1]]['pi']):
                        wuf.union(kk[0], k)
    wcomps = collections.defaultdict(set)
    for k, A in wents.items():
        wcomps[wuf.find(k)] |= {(RANK[a], f'w|{WSCHEME[a]}:{v}') for a, v in A}
    wcomps = {c: sorted(v) for c, v in wcomps.items()}
    wid = assign(db, 'work', 'atl:w:', wcomps, today, stats)
    work_of = {k: wid[wuf.find(k)] for k in wents}
    db.commit()
    # ---- appointments and cross-school persons
    appts = collections.defaultdict(list)
    for k, e in ents.items():
        if e['kind'] == 'pi':
            appts[person_of[k]].append(dict(school=k[1], pi=k[2], labId=lab_ids[k]))
    for v in appts.values():
        v.sort(key=lambda a: (a['school'], a['pi']))
    stud_of = collections.defaultdict(list)
    for k, e in ents.items():
        if e['kind'] == 'stu':
            stud_of[person_of[k]].append(dict(school=k[1], pi=k[2], labId=lab_ids.get(('pi', k[1], k[2])), record=k[3]))
    cross = []
    for i in sorted(set(appts) | set(stud_of)):
        schools_ = {a['school'] for a in appts.get(i, [])} | {a['school'] for a in stud_of.get(i, [])}
        if len(appts.get(i, [])) > 1 or (appts.get(i) and stud_of.get(i) and len(schools_) > 1):
            ev = [student_oa_evidence[k] for k in ents if person_of[k] == i and k in student_oa_evidence]
            anchors_ = sorted({person_anchor_str(a, v) for k in ents if person_of[k] == i for a, v in ents[k]['anchors'] if a in STRONG_PERSON})
            cross.append(dict(atlasId=i, name=next(a['pi'] for a in appts[i]), appointments=appts[i],
                              studentRecords=stud_of.get(i, []), matchedBy=anchors_, studentEvidence=ev))
    # ---- write
    if write:
        for s, (pis, stu, rows, sp) in data.items():
            D = hdir / s
            for p in pis:
                k = ('pi', s, p['pi'])
                p['atlasId'] = person_of[k]; p['labId'] = lab_ids[k]
                p['appointments'] = appts[person_of[k]]
                p['asStudent'] = [x for x in stud_of.get(person_of[k], []) if (x['school'], x['pi']) != (s, p['pi'])]
            for pi, recs in stu.items():
                for r in recs:
                    i = person_of[('stu', s, pi, r['person'])]
                    r['atlasId'] = i
                    if appts.get(i):
                        r['alsoPi'] = appts[i]
                    else:
                        r.pop('alsoPi', None)
            key = {(s, j): r for j, r in enumerate(rows)}
            for j, r in enumerate(rows):
                r['atlasWorkId'] = work_of[(s, j)]
            by_work = {}
            for j, r in enumerate(rows):
                for x in (r.get('work'), r.get('oa')):
                    if x:
                        by_work.setdefault((r['pi'], x), r['atlasWorkId'])
            for x in sp:
                x['studentAtlasId'] = person_of.get(('stu', s, x['pi'], x['student']))
                x['atlasWorkId'] = by_work.get((x['pi'], x.get('work'))) or by_work.get((x['pi'], x.get('oa')))
                x['labId'] = lab_ids.get(('pi', s, x['pi']))
            del key
            tmpf = D / 'pis.json.ids-tmp'; tmpf.write_text(json.dumps(pis, indent=1, ensure_ascii=False)); tmpf.replace(D / 'pis.json')
            tmpf = D / 'students.json.ids-tmp'; tmpf.write_text(json.dumps(stu, indent=1, ensure_ascii=False)); tmpf.replace(D / 'students.json')
            for name, rr in (('lab_papers', rows), ('student_papers', sp)):
                tmpf = D / f'{name}.jsonl.gz.ids-tmp'
                with gzip.open(tmpf, 'wt') as f:
                    for r in rr:
                        f.write(json.dumps(r, ensure_ascii=False) + '\n')
                tmpf.replace(D / f'{name}.jsonl.gz')
        out = hdir / 'ids'; out.mkdir(exist_ok=True)
        # cross-reference table
        xr = set()
        for k, e in ents.items():
            i = person_of[k]
            for a, v in e['anchors']:
                scheme = {'orcid': 'orcid', 'openalex': 'openalex_author', 'dblp': 'dblp_person', 'coll': 'collection_person', 'name': 'name_evidence'}[a]
                xr.add((i, 'person', scheme, v))
            if e['kind'] == 'pi':
                xr.add((i, 'person', 'legacy_pi_id', f'{k[1]}:{slug(k[2])}'))
                xr.add((lab_ids[k], 'lab', 'legacy_lab_id', f'{k[1]}:{slug(k[2])}'))
                xr.add((lab_ids[k], 'lab', 'pi_atlas_id', i))
            else:
                xr.add((i, 'person', 'legacy_student_id', k[3] if str(k[3]).startswith('ext:') else f'{k[1]}:{k[3]}'))
        for k, A in wents.items():
            i = work_of[k]
            for a, v in A:
                scheme = {'doi': 'doi', 'oaw': 'openalex_work', 'dblpkey': 'dblp_key', 'arxiv': 'arxiv', 'collw': 'collection_work', 'labpage': 'labpage'}[a]
                xr.add((i, 'work', scheme, v))
        buf = io.StringIO(); w = csv.writer(buf, delimiter='\t', lineterminator='\n')
        w.writerow(['atlas_id', 'entity', 'scheme', 'value'])
        w.writerows(sorted(xr))
        with open(out / 'crossref.tsv.gz.tmp', 'wb') as f:
            with gzip.GzipFile(fileobj=f, mode='wb', mtime=0) as g:
                g.write(buf.getvalue().encode())
        (out / 'crossref.tsv.gz.tmp').replace(out / 'crossref.tsv.gz')
        red = db.execute("select id, redirect_to, kind from ids where status='redirect' order by id").fetchall()
        (out / 'redirects.tsv').write_text('old_id\tnew_id\tentity\n' + ''.join(f'{a}\t{resolve(db, b)}\t{c}\n' for a, b, c in red))
        (out / 'persons-cross-school.json').write_text(json.dumps(dict(
            _doc='People who hold PI appointments at two or more atlas schools, or are a student at one school and a PI at '
                 'another, joined by ORCID, a reviewed OpenAlex author id or a DBLP person (never by name alone); '
                 'tools/atlas_ids.py, docs/IDS.md.', persons=cross), indent=1, ensure_ascii=False) + '\n')
    rep = dict(at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), schools=list(schools), stats=dict(stats),
               people=len(set(person_of.values())), pi_people=len(appts), student_records=sum(1 for k in ents if k[0] == 'stu'),
               works=len(set(work_of.values())), work_rows=len(work_of), labs=len(lab_ids), cross_school_persons=len(cross),
               students_matched_to_pi_elsewhere=len(student_oa_evidence),
               conflicts_refused=len(conflicts), conflicts=conflicts[:50],
               registry=dict(ids=db.execute('select count(*) from ids').fetchone()[0],
                             anchors=db.execute('select count(*) from anchors').fetchone()[0],
                             redirects=db.execute("select count(*) from ids where status='redirect'").fetchone()[0]))
    if write:
        (hdir / 'ids' / 'IDS-REPORT.json').write_text(json.dumps(rep, indent=1, ensure_ascii=False) + '\n')
    return dict(report=rep, person_of=person_of, work_of=work_of, lab_ids=lab_ids, cross=cross)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('schools', nargs='*')
    ap.add_argument('--dir', default=str(P.HIERARCHY))
    ap.add_argument('--registry', default=str(P.data('ids') / 'registry.sqlite'))
    ap.add_argument('--no-sweep', action='store_true', help='skip the OpenAlex byline author ids (student -> PI elsewhere)')
    a = ap.parse_args(argv)
    db = open_registry(a.registry)
    res = run(a.schools or list(P.SCHOOL_IDS), a.dir, db, use_sweep=not a.no_sweep)
    db.close()
    r = res['report']
    print(json.dumps({k: v for k, v in r.items() if k != 'conflicts'}, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
