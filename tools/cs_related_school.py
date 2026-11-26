"""CS-related faculty for a protocol school (protocol stage 2; owner rule 2026-10-22/28: computing-related faculty in any
department, computing being the object or the method of their research; administrative advisers are not PIs).

candidates  (a) every person a department with coverage "affiliated" lists with a professor rank (census rank ladder),
                whose computing work is to be decided (Michigan ECE)
            (b) every DBLP person whose dump record names the school (tools/dblp_affiliated.py: affiliation note or a URL
                on a school domain) with >= MIN_DBLP records 2016-2026 and who is not in the census
            (c) once the OpenAlex sweep is complete: tools/cs_related_candidates.py's rule on the school's sweep
                (>= 8 school works, >= 5 DBLP-indexed and >= 20% so, ...), read from
                hierarchy/<key>/cs-related-candidates-openalex.json (run it with --no-venues --stats --out that name);
                an author id whose names match a census person or an (a)/(b) candidate is not a new candidate
            -> hierarchy/<key>/cs-related-candidates.json
units       one Wayback capture per year 2016-2026 of every faculty listing URL the charter's [[affiliated_units]] name
            (`listings`), into captures/<key>.sqlite (live only where the host's charter `use` is live)
review      faculty evidence: a 2016-2026 unit capture whose text has the candidate's name followed (within 300
            characters, before the next person's name) by a professor title; the quote runs from the name through the
            title. For (a) the department listing itself is the evidence.
            computing evidence: the person's DBLP record (for (a) the one tools/dblp_ids_school.py decides; for (b) the
            record that names the school) with its 2016-2026 record count (every DBLP record is a computing venue or a CS
            preprint); >= MIN_DBLP records is computing as object or method. Learned 2026-10-29: a DBLP record without
            the school in its notes is not evidence of no computing output (Hun-Seok Kim, Nadakuditi), so (a) is decided
            negatively only when no DBLP person of the name has a 2016-2026 record.
            computing-share test (owner decision 2026-10-30, Michigan; once hierarchy/<key>/oa-author-stats.json.gz
            exists): it decides computing for pending (a) people, OpenAlex-rule (c) candidates, people without >=
            MIN_DBLP DBLP records, and the acceptances the charter's [cs_related].share_test_settles names. Any other
            DBLP-decided acceptance stands; its share result is recorded, with share_flag when the test fails. The person's
            OpenAlex author ids at the school are (1) ids carrying the person's ORCID (census, from DBLP), and (2) ids
            whose raw name has the person's family name and first spelled-out given name (nicknames allowed; 'Hyungjin
            Myra Kim' is not Hun-Seok Kim), unless the id carries another ORCID or all its works end more than one year
            before the person's first listing (a namesake: 'Joyce Wang', infectious diseases 2017-2023, is not Joyce
            Yan-Ran Wang, listed from 2026). Over these ids' school works (papers only, 2016-2026): computing when >=
            SHARE_MIN_CS are DBLP-indexed and they are >= SHARE_MIN of the works (the candidate rule's thresholds);
            not computing when the test fails on >= SHARE_MIN_N works. With fewer works the test cannot fail: the
            DBLP decision stands (>= MIN_DBLP records of the decided DBLP person: accepted), and a person with no
            decided DBLP record (pending) is too_few_school_works (new and recent faculty: nothing to place in a lab
            yet; revisit at the next sweep). When the person has no ORCID and the name-matched ids carry several, the
            ids of the ORCID with the most school works are kept (with ids that carry none).
            decision  accepted                 faculty evidence (ladder professor title) and computing evidence
                      faculty_not_computing    faculty evidence, < MIN_DBLP DBLP records naming the school
                      not_faculty_listed       reviewed source-specific exclusion (for example, an owner-decided
                                               non-faculty record in the school charter)
                      pending_source_coverage  no faculty evidence in the collected pages; absence cannot be decided
                                               until the unit directories and pagination are reviewed for completeness
                      research_or_other_rank   listed, but with a research / adjunct / emeritus / clinical title only
                      pending_openalex         (a) only: DBLP has namesakes and none names the school; decided with the
                                               OpenAlex sweep (an open coverage item until then)
                      too_few_school_works     faculty evidence, fewer than SHARE_MIN_N school works and the share
                                               test does not pass (revisit at the next sweep; not open)
                      census_alias             the DBLP person is a census person under another name form
                                               ('Satinder Singh' / 'Satinder Singh Baveja'); recorded for stage 5
            -> hierarchy/<key>/cs-related-review.json {school, rule, reviewed, provisional, decisions: [...]}
            -> census/<key>-additions.json: accepted people of other units (census format; is_pi with pi_basis
               ladder_faculty from the unit listing; added = cs_related_review_<date>)
hand        reviewed/cs-related-hand.json: faculty evidence from a person's own profile page (a unit directory that is a script shell proves nothing):
            [{name, unit, url, sha256, observed, quote, ladder}]. `cs_related_school.py profile <key> "<Name>" <unit> <url>` fetches the page (the live page where
            robots allows, else the latest Wayback capture), requires the name followed by a professor title, and appends the entry; `review` reads the file as
            faculty evidence only when the sha256 is a stored capture whose text holds the quote verbatim. Computing uses the normal share test or the
            existing minimum output of an evidenced, decided DBLP person; undecided namesake counts cannot supply that output.
research/teaching PIs: a source-checked research/teaching appointment can use an explicit
            pi-basis-evidence.json own_group or advises_phd record marked stage2_review=true,
            with unit, role, observed and appointment_rank (research|teaching). Its group/advising
            quote is checked against stored source bytes. Appointment evidence, computing scope,
            and candidate identity remain separate requirements. The appointment hand-review must
            carry the same appointment_rank and unit; the original rank is retained.
candidate dispositions: a hand review may carry candidate_review with source, complete ids,
            decision, why, identity_note and source-bound identity_evidence. Only negative
            rank/status decisions or excluded_scope (R-HIER-05, with separate scope_evidence)
            are supported. Exact source IDs keep homonyms separate; these reviews never admit a PI.
historical appointments: a hand review may carry historical_appointment={start,end}
            with explicit year or month bounds stated in its quote and matching a source-bound
            census override period. The biography observation date is preserved but
            supplies no current listing year. Research/teaching ranks still require the
            separate PI-basis review. Native builders use the reviewed period.
dated officer listings: a hand review may carry dated_listing with the PDF's date
            and literal date quote, physical page, active PROFESSORS/READERS heading,
            full entry name, appointment year and column-definition quote. The saved
            PDF bytes and exact URL are checked. It supplies that calendar year only;
            retrieval is retained separately and no appointment interval is inferred.
usage: cs_related_school.py candidates|units|units-check|review|profile <key> [<Name> <unit> <url>]
units-check exits 0 when units-done.json covers every unit URL of the charter (a unit added since the last `units` run, or no run, exits 1)
"""
import sqlite3
import collections, datetime, gzip, hashlib, json, re, subprocess, sys, zlib
from pathlib import Path

import atlas_paths as P  # noqa: E402
import census_overrides as CO  # noqa: E402
import school_config as S  # noqa: E402
import school_web as W  # noqa: E402
from pi_hierarchy import Name, toks, nick_ok, nosuffix  # noqa: E402
from pihier.names import middle_conflict  # noqa: E402

MIN_DBLP = 5
SHARE_MIN_CS, SHARE_MIN, SHARE_MIN_N = 5, 0.20, 8
TODAY = datetime.date.today().isoformat()
ENGLISH_MONTHS = {name: month for month, name in enumerate((
    'january', 'february', 'march', 'april', 'may', 'june',
    'july', 'august', 'september', 'october', 'november', 'december'), 1)}
ENGLISH_MONTHS.update({name[:3]: month for name, month in list(ENGLISH_MONTHS.items())})
ENGLISH_MONTHS['sept'] = 9
KPROF_T = re.compile(r'(?:조교수|부교수|정교수|석좌교수|(?<![가-힣])교수)')   # Korean ladder titles (KAIST 2026-11-24); 겸임/명예/연구/초빙교수 never match (a Hangul letter precedes 교수)
HANGUL_LETTER = re.compile(r'[\uac00-\ud7af]')
PROF_T = re.compile(r'\b(?:(?:Assistant|Associate|Full|Collegiate|University|Distinguished|Arthur F\. Thurnau)\s+)?Professor\b(?:\s+of\s+[A-Z][\w&,\- ]{2,80})?', re.I)
NOT_LADDER = re.compile(r'emerit|adjunct|status[- ]only|teaching[- ]stream|cross[- ]appointed|visiting|research\s+(?:assistant\s+|associate\s+)?professor|clinical|courtesy|professor\s+of\s+(?:the\s+)?practice|lecturer|postdoc', re.I)


def read(p, default=None):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else default


def clean_dblp(n):
    return re.sub(r'\s+\d{4}$', '', n)


def census_rows(doc):
    """The census rows of a census-faculty.json: {'faculty': [...]} (the stage-2 tools' layout) or a bare list (a composed first-native school such as ZJU).
    A missing file is an empty census, not a crash."""
    if isinstance(doc, dict):
        doc = doc.get('faculty')
    return [x for x in (doc or []) if isinstance(x, dict) and x.get('name')]


def source_exclusions(key):
    """Return exact DBLP PIDs excluded by reviewed, hash-checked student/alumni evidence."""
    doc = read(P.data('cs-related-source-exclusions.json', key), {}) or {}
    if not doc:
        return set()
    assert doc.get('school') == key
    from bs4 import BeautifulSoup
    out = set()
    for row in doc.get('records', []):
        assert row['source'] == 'dblp_affiliation' and row['decision'] == f'exclude_nonfaculty_{key}'
        pid = row['source_id']
        assert pid.startswith('https://dblp.org/pid/') and pid not in out
        ev = row['evidence']
        path = (P.ROOT / ev['raw_path']).resolve()
        assert path.is_relative_to(P.ROOT.resolve())
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == ev['raw_sha256']
        if ev['format'] == 'html':
            soup = BeautifulSoup(raw, 'html.parser')
            body = ' '.join(soup.stripped_strings)
        elif ev['format'] == 'pdf':
            mode = ev.get('pdf_text_mode', 'layout')
            assert mode in ('layout', 'raw')
            body = subprocess.run(['pdftotext', f'-{mode}', str(path), '-'], capture_output=True, text=True, check=True).stdout
        else:
            raise ValueError(f"unsupported source format: {ev['format']}")
        body = ' '.join(body.split())
        assert ev['quotes'] and all(q in body for q in ev['quotes'])
        if key == 'michigan':
            # A common name on an official profile does not bind it to one of
            # several DBLP PIDs. Require the official page to link a homepage
            # that the exact cached DBLP person record also carries.
            homepage = row['source_id_basis']['homepage']
            person = next(p for p in read(P.data('dblp-affiliated.json', key), {})['persons'] if p['pid'] == pid)
            assert row['name'] == clean_dblp(person['names'][0])
            norm = lambda url: url.rstrip('/')
            assert ev['format'] == 'html' and norm(homepage) in {norm(u) for u in person['urls']}
            assert norm(homepage) in {norm(a.get('href')) for a in soup.find_all('a', href=True)}
            for extra in row.get('supporting_evidence') or []:
                source_path = (P.ROOT / extra['raw_path']).resolve()
                assert source_path.is_relative_to(P.ROOT.resolve())
                source_raw = source_path.read_bytes()
                assert hashlib.sha256(source_raw).hexdigest() == extra['raw_sha256']
                if extra['format'] == 'pdf':
                    source_text = subprocess.run(['pdftotext', '-layout', str(source_path), '-'],
                                                 capture_output=True, text=True, check=True).stdout
                elif extra['format'] == 'html':
                    source_text = ' '.join(BeautifulSoup(source_raw, 'html.parser').stripped_strings)
                else:
                    raise ValueError(f"unsupported source format: {extra['format']}")
                assert extra['quotes'] and all(q in source_text for q in extra['quotes'])
        out.add(pid)
    return out


def source_excluded_openalex_ids(key, verified_pids):
    """Only explicitly reviewed author IDs bound to an excluded PID by one ORCID.

    Removing a DBLP student record must not revive that exact identity through
    OpenAlex. A shared name alone cannot suppress an OpenAlex candidate, and a
    mixed-ORCID author record cannot be excluded as one person's identity.
    """
    records = (read(P.data('cs-related-source-exclusions.json', key), {}) or {}).get('records') or []
    rows = [r for r in records if r.get('openalex_identities')]
    if not rows:
        return set()
    persons = {p['pid']: p for p in read(P.data('dblp-affiliated.json', key), {})['persons']}
    with gzip.open(P.data('oa-author-stats.json.gz', key), 'rt') as f:
        authors = json.load(f)['authors']
    out = set()
    for row in rows:
        assert row['source_id'] in verified_pids, 'OpenAlex exclusion needs a source-verified DBLP exclusion'
        person = persons[row['source_id']]
        names = Name([row['name']] + [clean_dblp(n) for n in person['names']])
        for binding in row['openalex_identities']:
            author, orcid = binding['author'], binding['orcid']
            assert re.fullmatch(r'https://openalex.org/A\d+', author), 'invalid reviewed OpenAlex author id'
            assert orcid in person.get('orcid', []), 'OpenAlex exclusion ORCID does not match its DBLP PID'
            stats = authors[author]
            assert set(stats.get('orcids') or {}) == {orcid}, 'OpenAlex exclusion needs one matching ORCID, never a mixed identity'
            assert any(names.match(n) for n in stats['raw']), 'OpenAlex exclusion name conflicts with the DBLP person'
            out.add(author)
    return out


def candidates(key):
    census = census_rows(read(P.data('census-faculty.json', key)))
    cov = {d['code']: d.get('coverage') for d in S.listing_units(S.get(key))}
    out = []
    for x in census:  # (a) ladder in an affiliated department, never ladder in a full-coverage one
        dep_rank = {((s_.get('kind') or '').split(':')[-1], s_.get('rank')) for s_ in x.get('sources') or []}
        if any(cov.get(d) == 'affiliated' and r == 'ladder' for d, r in dep_rank) and not any(cov.get(d) == 'full' and r == 'ladder' for d, r in dep_rank):
            out.append(dict(name=x['name'], aliases=x.get('aliases') or [], source='affiliated_department', departments=x.get('departments') or []))
    names = [Name([x['name']] + list(x.get('aliases') or [])) for x in census]
    pi_names = [Name([x['name']] + list(x.get('aliases') or [])) for x in census if x.get('is_pi')]
    excluded_pids = source_exclusions(key)
    seen_exclusions = set()
    for p in read(P.data('dblp-affiliated.json', key), {}).get('persons', []):
        if p['pid'] in excluded_pids:
            seen_exclusions.add(p['pid'])
            continue
        if p.get('n_window', 0) < MIN_DBLP or p.get('disambiguation'):
            continue
        nm = clean_dblp(p['names'][0])
        if any(N.match(nm) for N in names):
            continue
        out.append(dict(name=nm, aliases=[clean_dblp(n) for n in p['names'][1:]], source='dblp_affiliation', dblp=p['pid'], dblp_window=p['n_window'],
                        affiliations=[a['text'] for a in p['affiliations']], matched_by=p['matched_by']))
    assert seen_exclusions == excluded_pids, 'reviewed DBLP exclusion PID missing from affiliated source inventory'
    excluded_openalex = source_excluded_openalex_ids(key, excluded_pids)
    have = names + [Name([c['name']] + list(c.get('aliases') or [])) for c in out]
    for r in read(P.data('cs-related-candidates-openalex.json', key), []):  # (c)
        if r['author'] in excluded_openalex:
            continue
        if r.get('name_matches_pi') or any(N.match(n) for N in have for n in r['names'][:3]):
            continue
        nm = r['name'] if ',' not in r['name'] else ' '.join(reversed([x.strip() for x in r['name'].split(',', 1)]))
        out.append(dict(name=nm, aliases=[n for n in r['names'] if n != r['name']], source='openalex_rule', openalex=[r['author']], oa_works=r['works'],
                        oa_dblp_works=r['dblp_works'], oa_cs_share=r['cs_share'], oa_years=r['years']))
        have.append(Name([nm] + r['names']))
    # (d) discovery rosters ([cs_related].discovery_units = {CODE = listing format}): a list that names people without proving their rank (KAIST GSDS: most hold their
    # primary appointment in another unit). Each name is a candidate, proven only by a ladder title on a unit page or profile at `review`; nobody is excluded for the missing title.
    import listing_formats as LF
    disc = S.field(S.get(key), 'cs_related.discovery_units', {}) or {}
    if disc:
        cdb = W.con(key)
        for u_ in S.get(key).get('affiliated_units') or []:
            fmt = disc.get(u_['code'])
            if not fmt:
                continue
            for lst in u_.get('listings') or []:
                url_ = lst if lst.startswith('http') else 'https://' + lst
                for e_ in LF.FORMATS[fmt][0](W.live_html(cdb, url_) or ''):
                    nm = e_['name_listed']
                    if any(N.match(nm) for N in names) or any(Name([c['name']] + list(c.get('aliases') or [])).match(nm) for c in out):
                        continue
                    out.append(dict(name=nm, aliases=[], source='unit_roster_discovery', unit=u_['code'], source_url=url_, homepage=e_.get('homepage')))
    # Preserve bibliographic discovery IDs when adding supporting role evidence.
    # A sparse faculty profile is a fallback candidate only after both routes.
    for e in read(P.data('cs-related-hand.json', key), []):
        if not e.get('ladder') or not e.get('name') or e.get('candidate_review'):
            continue
        nm = e['name']
        if any(N.match(nm) for N in pi_names) or any(Name([c['name']] + list(c.get('aliases') or [])).match(nm) for c in out):
            continue
        out.append(dict(name=nm, aliases=[], source='official_profile_ladder', unit=e.get('unit'),
                        source_url=e.get('url'), source_sha256=e.get('sha256')))
    P.data_w('cs-related-candidates.json', key).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps(dict(candidates=len(out), **collections.Counter(c['source'] for c in out))))


def oa_stats(key):
    p = P.data('oa-author-stats.json.gz', key)
    if not p.exists():
        return None
    st = json.load(gzip.open(p, 'rt'))['authors']
    by = collections.defaultdict(set)
    for aid, x in st.items():
        for r in x['raw']:
            t = nosuffix(toks(r))
            if t:
                by[t[-1]].add(aid)
        for o in x.get('orcids') or {}:
            by['orcid:' + o].add(aid)
    return st, by


def strict_name(form, raw):
    """Same family name and the same first spelled-out given name (nicknames allowed); initials never decide."""
    a, b = nosuffix(toks(form)), nosuffix(toks(raw))
    if len(a) < 2 or len(b) < 2 or a[-1] != b[-1]:
        return False
    fa = next((t for t in a[:-1] if len(t) > 1), None); fb = next((t for t in b[:-1] if len(t) > 1), None)
    return bool(fa and fb and nick_ok(fa, fb))


def share_test(S_, names, orcids, first_year, author_ids=()):
    """The computing-share test (module docstring): -> dict(result, ids, n, cs, share, excluded, evidence)."""
    st, by = S_
    ids, excl = {}, []
    for a in author_ids:
        if a in st:
            ids[a] = 'candidate author id'
    for o in orcids:
        for a in by.get('orcid:' + o, ()):
            ids[a] = f'ORCID {o}'
    for fam in {nosuffix(toks(n))[-1] for n in names if len(toks(n)) >= 2}:
        for a in by.get(fam, ()):
            if a in ids:
                continue
            x = st[a]
            if not any(strict_name(f, r) for f in names for r in x['raw']):
                continue
            other = set(x.get('orcids') or {}) - set(orcids)
            if orcids and other:
                excl.append(dict(author=a, why=f'carries another ORCID ({sorted(other)[0]})', n=x['n'])); continue
            if first_year and x['years'] and max(x['years']) < first_year - 1:
                excl.append(dict(author=a, why=f'works end {max(x["years"])}, before the first listing ({first_year})', n=x['n'], raw=list(x['raw'])[:2])); continue
            ids[a] = 'full name: ' + next(r for r in x['raw'] if any(strict_name(f, r) for f in names))
    groups = collections.Counter()
    for a in ids:
        for o in st[a].get('orcids') or {}:
            groups[o] += st[a]['n']
    if not orcids and len(groups) > 1:  # namesakes: keep the ORCID with the most school works (and ids without one)
        keep = groups.most_common(1)[0][0]
        for a in [a for a in ids if (st[a].get('orcids') or {}) and keep not in st[a]['orcids']]:
            excl.append(dict(author=a, why=f'namesake: ORCID {sorted(st[a]["orcids"])[0]}, not the busiest ORCID {keep}', n=st[a]['n'])); del ids[a]
    orcs = collections.Counter(o for a in ids for o in st[a].get('orcids') or {})
    n = sum(st[a]['n'] for a in ids); cs = sum(st[a]['cs'] for a in ids)
    share = cs / n if n else 0.0
    res = 'computing' if cs >= SHARE_MIN_CS and share >= SHARE_MIN else ('not_computing' if n >= SHARE_MIN_N else 'too_few_school_works')
    ev = [dict(author=a, basis=ids[a], works=st[a]['n'], dblp_indexed=st[a]['cs'], years=[st[a]['years'][0], st[a]['years'][-1]] if st[a]['years'] else [],
               names=list(st[a]['raw'])[:3], orcids=sorted(st[a].get('orcids') or {}), venues=list(st[a]['venues'])[:3],
               dblp_examples=st[a].get('dblp_examples', [])[:2], other_examples=st[a].get('other_examples', [])[:2]) for a in sorted(ids, key=lambda a: -st[a]['n'])]
    return dict(result=res, ids=sorted(ids), school_works=n, dblp_indexed=cs, share=round(share, 3), thresholds=dict(dblp_indexed=SHARE_MIN_CS, share=SHARE_MIN, min_works_for_negative=SHARE_MIN_N),
                namesake_orcids=len(orcs) > 1, excluded=excl[:5], authors=ev[:6], source='hierarchy/<key>/oa-author-stats.json.gz (OpenAlex sweep 2026-10-29, papers only)')  # route-ok: a label


PRIORITY_YEARS = ('2026', '2020')   # the current year and 2020 of every unit come first: a faculty list of either year evidences most people (owner decision 2026-11-25)


def unit_fetch_order(plan, first_years=PRIORITY_YEARS):
    """plan: [(unit code, listing url, cdx row)] -> the same triples, the rows of `first_years` first (every unit), then the rest, each group in plan order.
    Only the order changes: every unit and year is still fetched, so recall and `units-done.json` are as before."""
    return [t for t in plan if t[2]['timestamp'][:4] in first_years] + [t for t in plan if t[2]['timestamp'][:4] not in first_years]


def names_professors(tx):
    """True when a unit capture's text looks like a faculty directory: >= 500 characters and at least 3 professor titles, English ('Professor') or Korean (교수, 조교수, 부교수, 정교수;
    KAIST 2026-11-25: Korean directories were all flagged as shells)."""
    tx = tx or ''
    return len(tx) >= 500 and tx.count('Professor') + len(re.findall(r'교수', tx)) >= 3


def units(key):
    cfg = S.get(key); c = W.con(key)
    n = collections.Counter(); per_unit = {}
    plan = []
    for u in cfg.get('affiliated_units') or []:
        for url in u.get('listings') or []:
            host = re.sub(r'^https?://', '', url).split('/')[0]
            if S.host_use(key, host) == 'live':   # the current listing of a live host is a dated capture of its year: no Wayback needed
                lurl = url if url.startswith('http') else 'https://' + url
                res = W.live(c, lurl)
                n['live'] += 1
                if res and res[0] == 200:  # a paged directory live: follow its pages / A-Z letters too (robots and the per-host delay apply in W.live)
                    import listing_formats as LF
                    lh = W.live_html(c, lurl) or ''
                    for _, lu in (LF.page_links(lh, lurl) or LF.letter_links(lh, lurl)).items() if LF.is_paged(lh) else []:
                        if W.live(c, lu):
                            n['live_pages'] += 1
            if PAGER_CHILD.search(url):  # a pager child (/page/N/, ?page=N) is followed from its first page's capture by unit_pages_of, never queried on its own
                continue
            for r in W.cdx_rows(c, re.sub(r'^https?://', '', url), collapse='timestamp:4'):
                plan.append((u['code'], url, r))
    for code, url, r in unit_fetch_order(plan):
        cap, st, sha, b = W.capture(c, r['timestamp'], r['original'], url, code)
        n[f'wayback_{st}'] += 1
        print(json.dumps(dict(unit=code, ts=r['timestamp'], status=st, blocks=len(b), shell=len(b) < 5)), flush=True)
        if st == 200:
            n['paged_pages'] += unit_pages_of(c, cap, r, code, url)
    for u in cfg.get('affiliated_units') or []:
        shells = sorted({ts[:4] for ts, tx in c.execute("select wayback_timestamp, text from captures where department=? and http_status=200", (u['code'],))
                         if not names_professors(tx)})   # a faculty directory names its professors; a capture that does not is a script shell or a nav page
        n['unit_years_without_blocks'] += len(shells)
        per_unit[u['code']] = dict(listings=list(u.get('listings') or []), captures=c.execute("select count(*) from captures where department=? and http_status=200", (u['code'],)).fetchone()[0], shell_years=shells)
        if shells:  # R5 (Georgia Tech friction 18): a capture with almost no text is a script shell and proves nothing, say so
            print(json.dumps(dict(unit=u['code'], shell_years=shells, warning='captures of these years hold < 500 characters or name fewer than 3 professors (script shells or nav pages): they prove nothing')), flush=True)
    P.data_w('units-done.json', key).write_text(json.dumps(dict(school=key, built_at=datetime.datetime.now().isoformat(timespec='seconds'), units=per_unit), indent=1))
    print(json.dumps(dict(n)))


def units_current(key):
    """True when units-done.json exists and names every listing URL of every charter unit (R6: the review must not read a half-run or stale unit capture set)."""
    done = read(P.data('units-done.json', key), None)
    if not done:
        return False
    want = {u['code']: sorted(u.get('listings') or []) for u in S.get(key).get('affiliated_units') or []}
    return all(code in done['units'] and sorted(done['units'][code]['listings']) == ls for code, ls in want.items())


_PAGE_CDX = {}   # (store, page url) -> the page's captures, 2016-2026, one per day: one CDX query per page URL for the whole run


def page_cdx_all_years(c, want):
    """One CDX query per page URL across 2016-2026 (collapse=timestamp:8, the first capture of each day) instead of one uncollapsed query per page URL per year. unit_pages_of
    picks, among the rows of the listing capture's calendar year, the day nearest the listing capture; the first capture of a day is the one the per-year query listed first,
    so the choice is the same (tests/test_unit_pages_of_all_years.py). Measured on KAIST: 64 of its first 80 Wayback operations were per-year pager queries."""
    key = (id(c), want)
    if key not in _PAGE_CDX:
        _PAGE_CDX[key] = W.cdx_rows(c, want, frm='2016', to='2026', collapse='timestamp:8')
    return _PAGE_CDX[key]


def unit_pages_of(c, cap, r, code, url):
    """The other pages of a paged unit directory (`?page=N`, A-Z letter pages; Georgia Tech friction 10/18): each page's capture nearest in time within
    the same calendar year, stored under the unit's code so unit_pages() reads it like the first page. -> pages captured."""
    import listing_formats as LF
    h = W.raw_html(c, cap)
    if not LF.is_paged(h):
        return 0
    links = LF.page_links(h, r['original']) or LF.letter_links(h, r['original'])
    got, ts0 = 0, r['timestamp']
    for _, u in links.items():
        want = re.sub(r'^https?://', '', u)
        rows = [x for x in page_cdx_all_years(c, want) if x['timestamp'].startswith(ts0[:4])]
        if not rows:
            continue
        x = min(rows, key=lambda z: abs(int(z['timestamp'][:8]) - int(ts0[:8])))
        W.capture(c, x['timestamp'], x['original'], url, code)
        got += 1
    return got


PAGER_CHILD = re.compile(r'/page/\d+/?$|[?&]page=\d+(?:&|$)')


def wp_json_people_text(raw):
    """The verification text of a WordPress REST people list (ECE): each record's rendered title ('Yang, Yibin<br> Assistant
    Professor') as one line, markup removed, whitespace collapsed; '' when the body is not that JSON."""
    import html as _h
    try:
        recs = json.loads(raw)
        def mark(r):  # the record's own category classes: an emeritus or cross-appointed person is not a home-unit ladder member
            cl = r.get('class_list') or []
            return (' Emeritus' if 'category-emeritus' in cl else '') + (' (cross-appointed)' if 'category-cross-appointed' in cl else '')
        return ' '.join(' '.join(_h.unescape(re.sub(r'<[^>]+>', ' ', (r.get('title') or {}).get('rendered', ''))).split()) + mark(r) + ' Profile' for r in recs)
    except (ValueError, AttributeError, TypeError):
        return ''


def LF_ntu_text(html):
    import listing_formats as LF
    return LF.ntu_unit_text(html)


def directory_entry_text(html, url, flat):
    """Keep known directory cards apart without changing their source text.

    The separator only terminates a person's evidence window. Every retained
    card text must also occur literally in the original page's extraction.
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    cards = soup.select('.directory-list .item.person, article.profile-card, .profile-teaser, ul.faculty-list > li')
    if not cards:
        return None
    rows = []
    for card in cards:
        text = W.flat(W.extract.blocks(str(card).encode(), 'text/html', url))
        if text and text in flat:
            rows.append(text + ' Profile')
    return ' '.join(rows) if rows else None


def unit_pages(key):
    """(unit code, url, sha256, observed, flat text) of every stored 2016-2026 unit capture and live page."""
    cfg = S.get(key); c = W.con(key)
    codes = {}
    for u in cfg.get('affiliated_units') or []:
        for url in u.get('listings') or []:
            codes[re.sub(r'^(?:https?://)?(?:www\.)?', '', url).split('?')[0].rstrip('/').lower()] = u['code']  # a listing may be an API URL with a query (Toronto ECE wp-json)

    def code_of(k):  # a live page of the listing itself, one of its ?page=N pages or one of its A-Z letter pages
        base = k.split('?')[0].rstrip('/')
        if base in codes:
            return codes[base]
        return next((c_ for lk, c_ in codes.items() if base.startswith(lk + '/') and re.fullmatch(r'[a-z]', base[len(lk) + 1:])), None)
    out = []
    has_raw = any(r[1] == 'raw_zlib' for r in c.execute('pragma table_info(captures)'))   # a fixture store may hold only the text
    for cap, page, dept, ts, st, sha, txt, rawz in c.execute('select capture_url, page_url, department, wayback_timestamp, http_status, sha256, text, ' + ('raw_zlib' if has_raw else 'NULL') + ' from captures'):
        k = re.sub(r'^https?://(www\.)?', '', page or '').rstrip('/').lower()
        if st == 200 and txt and (k in codes or dept in codes.values()):
            y = int(str(ts)[:4])
            if 2016 <= y <= 2026:
                flat_ = ' '.join(txt.split())
                if rawz:
                    flat_ = directory_entry_text(W.body(rawz).decode('utf-8', 'replace'), cap, flat_) or flat_
                if rawz and k.startswith('ntu.edu.sg/'):   # NTU unit pages: the page's own name + title rows (listing_formats.ntu_*), not the 300-characters heuristic
                    nt = LF_ntu_text(W.body(rawz).decode('utf-8', 'replace'))
                    flat_ = nt or flat_
                out.append((codes.get(k, dept), cap, sha, str(ts), flat_))
    for url, at, st, sha, raw in c.execute('select url, fetched_at, status, sha256, raw_zlib from live'):
        k = re.sub(r'^https?://(www\.)?', '', url).rstrip('/').lower()
        if st == 200 and code_of(k):
            import zlib
            if '/wp-json/' in url:
                out.append((code_of(k), url, sha, at[:10].replace('-', ''), wp_json_people_text(zlib.decompress(raw))))
                continue
            nt = LF_ntu_text(zlib.decompress(raw).decode('utf-8', 'replace')) if k.startswith('ntu.edu.sg/') else None
            html = zlib.decompress(raw)
            b = W.extract.blocks(html, 'text/html', url)
            flat_ = W.flat(b)
            out.append((code_of(k), url, sha, at[:10].replace('-', ''), nt or directory_entry_text(html.decode('utf-8', 'replace'), url, flat_) or flat_))
    try:   # a JavaScript-built listing (tools/js_render_capture.py, JS-RENDER.md): the newest ok rendered DOM of a charter listing URL is a unit page like a live one
        import zlib
        newest = {}
        for url, at, st, dsha, dz in c.execute("select url, fetched_at, status, dom_sha256, dom_zlib from js_render where status in ('ok', 'not_settled') order by fetched_at"):
            newest[url] = (at, dsha, dz)
        for url, (at, dsha, dz) in newest.items():
            k = re.sub(r'^https?://(www\.)?', '', url).rstrip('/').lower()
            if code_of(k):
                out = [o for o in out if not (o[1] == url and o[2] != dsha)]   # the live shell of the same URL says nothing
                out.append((code_of(k), url, dsha, at[:10].replace('-', ''), W.flat(W.extract.blocks(zlib.decompress(dz), 'text/html', url))))
    except sqlite3.OperationalError:   # the store has no js_render table
        pass
    return out


ROLE_LEAD = re.compile(r'\s*(?:(?:Interim|Associate|Acting|Vice)\s+)?(?:Chair|Director|Head)\s+of\s+(?:the\s+)?(?:Department|School|Division|Program|Center|Institute)\s+of\s+(?:[A-Z][\w&\'’-]*,?\s+(?:and\s+|&\s+)?)+?(?=(?:Associate\s+|Assistant\s+|Distinguished\s+|Senior\s+)?Professor\b)')
CUT = re.compile(r'Send Email|\bProfile\b|\S+@\S+|Ph\.?\s?D\.?\s+(?:Student|Candidate)|Graduate Student|\(\d{3}\)|\d{3}[-.]\d{3}[-.]\d{4}', re.I)


# words that open a role or unit phrase after a rank, never a person's given name (the next-person rule in faculty_evidence)
ROLE_WORDS = {'graduate', 'undergraduate', 'program', 'director', 'co-director', 'associate', 'assistant', 'chair', 'vice', 'head', 'dean',
              'adjunct', 'affiliate', 'primary', 'joint', 'core', 'emeritus', 'emerita', 'endowed', 'faculty', 'research', 'teaching',
              'department', 'school', 'division', 'college', 'institute', 'center', 'centre', 'computer', 'electrical',
              'information', 'human', 'biomedical', 'industrial', 'mechanical', 'civil', 'applied', 'principal', 'senior', 'founding'}
CONTACT_LEAD = re.compile(r"\s*(?P<phone>\(\d{3}\)\s*\d{3}[-.]\d{4}\s*)?(?P<email>[\w.+-]+@[\w.-]+\.[a-z]{2,}\s*)?(?:[A-Z]{2,5}\s+[A-Z]?\d{1,4}[A-Z]?\s+)?")


def not_ladder_titles(key):
    """The charter's teaching titles plus its `census.rank_words.not_ladder` (titles a school gives non-ladder people that are a real
    rank elsewhere: UW 'Affiliate Assistant Professor' is unpaid outside faculty, Georgia Tech's is a ladder cross-listing; 2026-11-22)."""
    cfg = S.get(key)
    return '|'.join(x for x in (S.field(cfg, 'census.rank_words.teaching'), S.field(cfg, 'census.rank_words.not_ladder')) if x)


TITLE_FIRST_HOSTS = {'btm.kaist.ac.kr'}   # sites whose directory prints the title BEFORE the name ('기술경영학부 | 부교수 권석범(Kwon, Seokbeom)'); host-scoped, no other school's page is read this way
TITLE_FIRST = re.compile(r'\|\s*(?P<t>[가-힣]*교수)\s+(?P<ko>[가-힣]{2,5})\s*\((?P<la>[A-Za-z][A-Za-z ,.\'-]{2,50}?)\)')
TITLE_FIRST_LADDER = {'교수', '부교수', '조교수', '정교수', '석좌교수'}   # 겸임, 명예, 연구, 초빙, 대우 and every other prefixed 교수 are not ladder


def _latin_key(s):
    return ''.join(sorted(re.sub(r'[^a-z ]', '', s.lower().replace('-', '').replace(',', ' ')).split()))


def title_first_evidence(unit, url, sha, obs, flat, names):
    """[(evidence dict)] for a title-before-name directory (btm.kaist.ac.kr): the person's Hangul spelling equals the entry's, or the Latin name in the
    parentheses ('Kwon, Seokbeom') has the same name tokens as one of `names`. The Latin name is returned as `latin_alias` (the page's own rendering)."""
    keys = {_latin_key(n) for n in names if not HANGUL_LETTER.search(n)}
    hangul = {n.replace(' ', '') for n in names if HANGUL_LETTER.search(n)}
    out = []
    for m in TITLE_FIRST.finditer(flat):
        if m.group('ko') in hangul or _latin_key(m.group('la')) in keys:
            out.append(dict(unit=unit, url=url, sha256=sha, observed=obs, quote=' '.join(m.group(0).split()),
                            ladder=m.group('t') in TITLE_FIRST_LADDER, latin_alias=m.group('la').strip()))
    return out


def faculty_evidence(pages, names, teaching_title='', single_person=False):
    """Every (unit, url, sha, observed, quote, ladder) where a page names the person and a professor title follows the
    name directly: the title must start within 60 characters of the name, nothing between them may be a non-ladder
    title, and the segment is cut at the entry's own furniture ('Send Email', 'Profile', an email or phone, 'Ph.D.
    Student'), so the next person's title is never read as this one's (learned 2026-10-29: 'Lauro Ojeda Assistant Research
    Scientist ... Chinedum Okwudire Associate Professor'). A form must end at a name boundary ('Matthew Johnson' is not
    'Matthew Johnson-Roberson')."""
    teaching = re.compile(teaching_title, re.I) if teaching_title else None
    forms = set()
    for n in names:
        t = n.replace(',', '').split()
        if len(t) >= 2:
            forms |= {n, f'{t[-1]}, {" ".join(t[:-1])}', f'{t[0]} {t[-1]}', f'{t[-1]}, {t[0]}'}
    # forms with middle names or initials the page spells and the candidate's name does not ('Karen Feigh' / 'Karen M Feigh', 'Toktay, Beril' /
    # 'Toktay, L. Beril'): regexes, tried after the literal forms (Georgia Tech friction 20)
    kforms = sorted({f for n in names if HANGUL_LETTER.search(n) for f in (n, n.replace(' ', ''))}, key=len, reverse=True)   # a Hangul spelling is matched literally (same string, never a romanization)
    rxs = []
    for n in names:
        t = n.replace(',', '').split()
        given = [x for x in t[:-1] if len(x.strip('.')) >= 3]
        if len(t) >= 2 and given:
            f1, la = re.escape(given[0]), re.escape(t[-1])
            rxs += [rf"{f1}\s+(?:[A-Z][\w.'’-]*\s+){{1,2}}{la}", rf"{la},\s+(?:[A-Z]\.?\s+){{1,2}}{f1}"]
    ev = []
    for unit, url, sha, obs, flat in pages:
        if re.sub(r'^https?://', '', url).split('/')[0].lower() in TITLE_FIRST_HOSTS:
            tf = title_first_evidence(unit, url, sha, obs, flat, names)
            if tf:
                ev.append(tf[0])
                continue
        for f in sorted(forms, key=len, reverse=True) + kforms + rxs:
            hit = None
            korean = f in kforms
            for m in re.finditer(f if f in rxs else re.escape(f), flat):
                nxt = flat[m.end():m.end() + 1]
                if korean and ((nxt and HANGUL_LETTER.match(nxt)) or (m.start() and HANGUL_LETTER.match(flat[m.start() - 1]))):
                    continue   # inside a longer Hangul name
                if nxt and (nxt.isalnum() or nxt in "-'") and not korean:
                    continue
                seg = flat[m.end():m.end() + 260]
                # a directory card that puts the contact block between the name and the unit/title ('Morgansen, Kristi (206) 616-5950
                # morgansn@uw.edu AER 234 Aeronautics & Astronautics Professor', UW facultyfinder 2026-11-22): skip the block, then read as usual
                lead = CONTACT_LEAD.match(seg)
                off = lead.end() if lead and (lead.group('phone') or lead.group('email')) else 0
                seg = seg[off:off + 220]
                lead_role = ROLE_LEAD.match(seg)   # 'Chair of the Department of Biological and Environmental Engineering Professor, ...' (Cornell CEE page, C. Lindsay Anderson)
                if lead_role:
                    seg = seg[lead_role.end():]
                    off += lead_role.end()
                cut = CUT.search(seg)
                seg = seg[:cut.start()] if cut else seg
                pt = KPROF_T.search(seg) if korean else PROF_T.search(seg)
                if not pt or pt.start() > 60:
                    continue
                if korean:   # the title follows the name within 60 characters and no other person's name sits between (a Hangul entry has no 'Prof.' prefix to test)
                    q = flat[m.start():m.end() + off + pt.end()]
                    ev.append(dict(unit=unit, url=url, sha256=sha, observed=obs, quote=q, ladder=True))
                    hit = True
                    break
                # A flat directory can concatenate several people before the next
                # professor title. "Imre Leader Dr Kaisey Mandel ... Professor"
                # describes Mandel, not Leader; a named Dr/Prof before the rank
                # starts a new entry even when the title is within 60 characters.
                if re.search(r'\b(?:Dr|Prof)\.?\s+[A-Z][\w’\'-]+', seg[:pt.start()]):
                    continue
                # A prefixed title belongs to the next person, e.g.
                # "Dr Chao Li Professor Benedikt Loewe". Unlike "Professor of
                # Mathematics", the title is immediately followed by a name.
                after_title = seg[pt.end():]
                # `single_person`: the person's own profile page (`profile`), where no next entry exists and a heading follows
                # the rank ('Gina-Anne Levow (she/her) Professor Contact Information', UW 2026-11-22)
                # A role phrase after the rank is not a name ('John Gennari, PhD Professor Graduate Program Director', UW BIME 2026-11-22)
                nm = re.match(r'\s+([A-Z][\w’\'-]+)\s+[A-Z][\w’\'-]+', after_title)
                if not single_person and pt.group(0).lower() == 'professor' and nm and nm.group(1).lower() not in ROLE_WORDS:
                    continue
                q = flat[m.start():m.end() + off + pt.end()]
                # the rank is read up to the title's own 'Professor': the 'of <unit>' tail can run on into a second
                # appointment ('Associate Professor of Information, School of Information and Research Associate
                # Professor, ICPSR', learned 2026-10-30, Libby Hemphill)
                core = seg[:pt.start() + re.search(r'Professor', seg[pt.start():], re.I).end()]
                _m = re.match(r'[\s,]*(?:Emerit\w+|Adjunct|Affiliate\b|\(?Status[- ]only\)?|\(cross-appointed\)|Teaching[- ]Stream|CLTA)', seg[len(core):], re.I)
                core += _m.group(0) if _m else ''  # 'Professor Emeritus' is emeritus, not ladder (Toronto 2026-11-10)
                hit = dict(unit=unit, url=url, sha256=sha, observed=obs, quote=q,
                           ladder=not NOT_LADDER.search(core) and not (teaching and teaching.search(core)))
                break
            if hit is True:
                break
            if hit:
                ev.append(hit)
                break
    return ev


def census_alias(census, names, dblp=None, openalex=None, oa_map=None):
    """The census person a candidate already is: the same DBLP person id (a direct URL binding of a Han-name roster person,
    tools/dblp_url_binding_school.py), a Name match, or the candidate's tokens are the start of a census
    name ('Satinder Singh' is 'Satinder Singh Baveja')."""
    pids = {d for d in ([dblp] if isinstance(dblp, str) else dblp or []) if d}
    for a in ([openalex] if isinstance(openalex, str) else openalex or []):   # a reviewed OpenAlex binding of a Han census person (D-0010 extension, Q-0354)
        if (oa_map or {}).get(a) in census:
            return oa_map[a]
    for x in census.values():
        if pids and pids & set(x.get('dblp') or []):
            return x['name']
        N = Name([x['name']] + list(x.get('aliases') or []))
        for n in names:
            t = toks(n)
            if N.match(n) or any(len(t) >= 2 and toks(m)[:len(t)] == t for m in [x['name']] + list(x.get('aliases') or [])):
                return x['name']
    return None


def historical_appointment(key, entry):
    """Bind historical role evidence to the explicit period native builders read.

    Observing a biography today does not make its former appointment a current
    listing. Research/teaching roles still need separately checked PI-basis evidence. Both bounds must be stated by this source and independently present
    in the reviewed census override; no interval is inferred from roster years.
    """
    bounds = entry.get('historical_appointment')
    if bounds is None:
        return None
    start, end = (bounds.get(k) for k in ('start', 'end')) if isinstance(bounds, dict) else (None, None)
    if not all(isinstance(v, str) and re.fullmatch(r'\d{4}(?:-\d{2})?', v) for v in (start, end)) or len(start) != len(end):
        raise SystemExit(f"{entry['name']}: historical appointment needs explicit start/end years or months of equal precision")
    precision = 'year' if len(start) == 4 else 'month'
    for label, value in (('start', start), ('end', end)):
        try:
            datetime.date.fromisoformat(value + ('-01-01' if precision == 'year' else '-01'))
        except ValueError as exc:
            raise SystemExit(f"{entry['name']}: historical appointment has an invalid {label} date") from exc
    if not (start <= end and int(start[:4]) <= 2026 and int(end[:4]) >= 2016):
        raise SystemExit(f"{entry['name']}: historical appointment must overlap 2016–2026 in chronological order")
    observed_source = entry.get('observed') or ''
    observed = re.sub(r'[^0-9]', '', observed_source)
    observed_year = observed_source[:4]
    if not re.fullmatch(r'\d{4}', observed_year) or int(end[:4]) > int(observed_year):
        raise SystemExit(f"{entry['name']}: historical appointment cannot end after its source observation")
    if precision == 'month' and (len(observed) < 6 or end.replace('-', '') > observed[:6]):
        raise SystemExit(f"{entry['name']}: historical appointment cannot end after its source observation")
    if not entry.get('ladder', True) and entry.get('appointment_rank') not in ('research', 'teaching'):
        raise SystemExit(f"{entry['name']}: historical non-ladder appointment needs its research/teaching rank")
    for label, value in (('start', start), ('end', end)):
        literal = bounds.get(f'{label}_quote', value)
        # Transcribe explicit numeric or English month/year source dates.
        # Matching only the year would authorize an invented month boundary.
        normalized = literal
        if isinstance(literal, str) and re.fullmatch(r'\d{2}/\d{4}', literal):
            normalized = literal[3:] + '-' + literal[:2]
        named_month = re.fullmatch(r'([A-Za-z]+)\.?\s+(\d{4})', literal) if isinstance(literal, str) else None
        if named_month and named_month[1].lower() in ENGLISH_MONTHS:
            normalized = f'{named_month[2]}-{ENGLISH_MONTHS[named_month[1].lower()]:02d}'
        short_range = re.fullmatch(r'(\d{4})\s*[-–—]\s*(\d{2})', literal) if isinstance(literal, str) else None
        # An abbreviated end year needs its entire range, including this
        # appointment's start. Never expand an isolated number or a century.
        if short_range and label == 'end' and precision == 'year' and short_range[1] == start:
            expanded = start[:2] + short_range[2]
            if expanded >= start:
                normalized = expanded
        boundary = r'\w' if named_month or short_range else r'\d'
        if (not isinstance(literal, str) or normalized != value
                or not re.search(r'(?<!' + boundary + ')' + re.escape(literal) + r'(?!' + boundary + ')', entry['quote'])):
            raise SystemExit(f"{entry['name']}: historical appointment bounds are absent from its source quote")
    periods = (CO.section(key).get(entry['name']) or {}).get('periods') or []
    if not any(p.get('start') == start and p.get('end') == end and p.get('datePrecision') == precision
               and any(all(ev.get(k) == entry[k] for k in ('url', 'sha256', 'quote')) for ev in p.get('evidence') or [])
               for p in periods):
        raise SystemExit(f"{entry['name']}: historical appointment lacks the matching source-bound reviewed census period")
    return dict(start=start, end=end)


def json_strings(value):
    """Yield literal decoded string values without joining unrelated fields."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from json_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from json_strings(child)


def json_pointer(value, pointer):
    """Resolve an RFC 6901 pointer, rejecting invalid escapes and array indices."""
    if not isinstance(pointer, str) or (pointer and not pointer.startswith('/')):
        raise ValueError('invalid JSON pointer')
    if not pointer:
        return value
    for token in pointer[1:].split('/'):
        if re.search(r'~(?![01])', token):
            raise ValueError('invalid JSON pointer escape')
        token = token.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not re.fullmatch(r'0|[1-9][0-9]*', token):
                raise ValueError('invalid JSON array index')
            value = value[int(token)]
        elif isinstance(value, dict):
            value = value[token]
        else:
            raise ValueError('JSON pointer traverses a scalar')
    return value


def dated_listing(entry, pdf):
    """A reviewed officer-table row proves its document's year, not retrieval year.

    The date, appointment-column meaning, active rank heading and full name must
    be literal evidence in the same saved PDF. Mixed-rank pages stay for review.
    This supplies one listing year; it creates no appointment interval.
    """
    proof = entry.get('dated_listing')
    if proof is None:
        return None

    def fail(reason):
        raise SystemExit(f"{entry['name']}: dated listing {reason}")

    if not isinstance(proof, dict) or entry.get('historical_appointment'):
        fail('needs its own dated observation, not an appointment interval')
    try:
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', proof['date']):
            raise ValueError('not an ISO calendar date')
        date = datetime.date.fromisoformat(proof['date'])
        retrieved = datetime.datetime.strptime(re.sub(r'\D', '', entry['observed'])[:8], '%Y%m%d').date()
    except (KeyError, TypeError, ValueError):
        fail('needs valid document and retrieval dates')
    if not 2016 <= date.year <= 2026 or date > retrieved:
        fail('date must be in the window and no later than retrieval')
    flat = ' '.join((pdf or '').split())
    quote = proof.get('date_quote') or ''
    date_words = f'{date.day} {date.strftime("%B")} {date.year}'
    if not quote or quote not in flat or not re.search(r'(?<!\d)' + re.escape(date_words) + r'(?!\d)', quote):
        fail('date is not stated in the saved PDF')
    meaning = ('The mention of a date before a name means that the person named entered in that year '
               'into the office or appointment specified.')
    if proof.get('appointment_column_quote') != meaning or meaning not in flat:
        fail('appointment-column meaning is not source-bound')
    pages = (pdf or '').split('\f')
    page = proof.get('page')
    if type(page) is not int or not 1 <= page <= len(pages):
        fail('needs a valid physical PDF page number')
    text = pages[page - 1]
    headings = {m.group(1).upper() for m in re.finditer(
        r'^\s*((?:(?:EMERITUS|HONORARY)\s+)?(?:PROFESSORS|READERS)|UNIVERSITY (?:SENIOR )?LECTURERS)'
        r'(?:\s*\(continued\))?\s*$', text, re.M | re.I)}
    heading = proof.get('heading')
    if heading not in ('PROFESSORS', 'READERS') or headings != {heading}:
        fail('rank heading is absent, inactive or mixed on the entry page')
    row = ' '.join(entry['quote'].split())
    name = proof.get('entry_name') or ''
    # The register prints knighthood titles inside the literal name column.
    # Remove only that leading title for identity comparison; the source quote
    # and appointment-year binding below still require the entire literal name.
    person_name = re.sub(r'^(?:Sir|Dame)\s+', '', name)
    year = str(proof.get('appointment_year') or '')
    if not row or row not in ' '.join(text.split()):
        fail('entry quote is not on its stated page')
    if (len(toks(person_name)) < 2 or len(toks(person_name)[0]) < 2 or len(toks(person_name)[-1]) < 2
            or name not in row or not Name([entry['name']]).match(person_name)
            or middle_conflict([entry['name']], person_name)):
        fail('full entry name does not bind this candidate')
    if (not re.fullmatch(r'\d{4}', year) or int(year) >= date.year
            or not re.search(r'(?<!\d)' + year + r'\s+' + re.escape(name) + r'(?!\w)', row)):
        fail('needs a source-stated appointment year before the observation year')
    if not entry.get('ladder', True) or NOT_LADDER.search(row):
        fail('does not establish an active ladder appointment')
    return dict(proof)


def faculty_observed(entry):
    """Date of the faculty assertion, distinct from retrieval of an old document."""
    dated = entry.get('dated_listing') or entry.get('dated_roster')
    return dated['date'].replace('-', '') if dated else entry.get('observed') or ''


def dated_source_fields(entry):
    field = 'dated_listing' if entry.get('dated_listing') else 'dated_roster' if entry.get('dated_roster') else None
    return {field: entry[field], 'retrieved_at': entry['observed']} if field else {}


def dated_roster(entry, rows):
    """Bind one reviewed appointment to its original campus/unit/person/title row."""
    from appointment_rosters import regular_professor
    proof = entry['dated_roster']
    if (not isinstance(proof, dict) or proof.get('format') != 'illinois_graybook'
            or entry.get('historical_appointment') or entry.get('dated_listing')):
        raise SystemExit(f"{entry['name']}: dated roster needs a single supported observation")
    required = ('page', 'entry_name', 'title', 'unit', 'college', 'date', 'date_quote', 'employee_class')
    if any(k not in proof for k in required) or type(proof['page']) is not int:
        raise SystemExit(f"{entry['name']}: dated roster lacks a complete row binding")
    matches = [r for r in rows if all(r[k] == proof[p] for k, p in (
        ('page', 'page'), ('name', 'entry_name'), ('title', 'title'), ('unit', 'unit'),
        ('college', 'college'), ('document_date', 'date'), ('date_quote', 'date_quote'),
        ('employee_class', 'employee_class'))) and r['quote'] == ' '.join(entry['quote'].split())]
    if len(matches) != 1:
        raise SystemExit(f"{entry['name']}: dated roster does not bind exactly one original appointment")
    row = matches[0]
    full_name = ' '.join(reversed(row['name'].split(', ', 1))) if ', ' in row['name'] else row['name']
    if not Name([entry['name']]).match(full_name) or middle_conflict([entry['name']], full_name):
        raise SystemExit(f"{entry['name']}: dated roster name conflicts with the candidate")
    retrieved = re.sub(r'\D', '', entry.get('observed') or '')[:8]
    try:
        datetime.datetime.strptime(retrieved, '%Y%m%d')
    except ValueError:
        raise SystemExit(f"{entry['name']}: dated roster needs a valid retrieval date")
    if (not 2016 <= row['year'] <= 2026
            or row['document_date'].replace('-', '') > retrieved):
        raise SystemExit(f"{entry['name']}: dated roster outside the observation window")
    if entry.get('ladder', True) and not regular_professor(row['title']):
        raise SystemExit(f"{entry['name']}: dated roster does not establish a regular professor")
    return dict(proof)


def hand_evidence(key, c=None, *, entries=None, label='cs-related-hand.json'):
    """{normalised name: [evidence]} from reviewed/cs-related-hand.json, each entry verified: its sha256 is a stored capture (or live page) whose text holds the quote."""
    ents = read(P.data('cs-related-hand.json', key), []) if entries is None else entries
    if not ents:
        return {}
    c = c or W.con(key)
    out = {}
    json_by_sha = {}
    pdf_by_sha = {}
    rosters_by_sha = {}
    roster_shas = {e['sha256'] for e in ents if e.get('dated_roster') is not None}
    texts_by_sha = {}  # a catalog PDF can support many reviewed names; extract it once per raw hash
    for e in ents:
        if not all(e.get(k) for k in ('name', 'unit', 'url', 'sha256', 'quote')):
            raise SystemExit(f"{label}: entry without name/unit/url/sha256/quote: {e.get('name')}")
        if e['sha256'] not in texts_by_sha:
            texts = [r[0] for r in c.execute('select text from captures where sha256=?', (e['sha256'],))]
            for url, raw in c.execute('select url, raw_zlib from live where sha256=?', (e['sha256'],)):
                import zlib
                body = zlib.decompress(raw)
                if body.lstrip().startswith((b'{', b'[')):
                    if hashlib.sha256(body).hexdigest() != e['sha256']:
                        raise SystemExit(f"{label}: JSON source hash mismatch for {e['name']}")
                    try:
                        json_by_sha[e['sha256']] = json.loads(body)
                    except (ValueError, UnicodeError) as exc:
                        raise SystemExit(f"{label}: invalid saved JSON for {e['name']}") from exc
                elif body.startswith(b'%PDF-'):
                    # Catalog faculty lists are PDF. The raw bytes and hash are in the same live receipt;
                    # checking binary as HTML silently loses every literal professor-rank quote.
                    import subprocess
                    try:
                        pdf = subprocess.run(['pdftotext', '-raw', '-', '-'], input=body, capture_output=True, timeout=120)
                    except (FileNotFoundError, subprocess.TimeoutExpired):
                        pdf = None
                    if pdf is not None and pdf.returncode == 0:
                        text = pdf.stdout.decode('utf-8', 'replace')
                        texts.append(text)
                        if hashlib.sha256(body).hexdigest() == e['sha256']:
                            pdf_by_sha.setdefault(e['sha256'], {})[url] = text
                            if e['sha256'] in roster_shas:
                                from appointment_rosters import illinois_graybook
                                layout = subprocess.run(['pdftotext', '-layout', '-', '-'], input=body,
                                                        capture_output=True, check=True, timeout=120)
                                rosters_by_sha.setdefault(e['sha256'], {})[url] = illinois_graybook(
                                    layout.stdout.decode('utf-8', 'replace'))
                else:
                    texts.append(W.flat(W.extract.blocks(body, 'text/html', url)))
            try:   # a JavaScript-rendered page (tools/js_render_capture.py): the stored rendered DOM, matched by its dom_sha256
                import zlib
                for url, dz in c.execute('select url, dom_zlib from js_render where dom_sha256=?', (e['sha256'],)):
                    texts.append(W.flat(W.extract.blocks(zlib.decompress(dz), 'text/html', url)))
            except Exception:   # the store has no js_render table
                pass
            texts_by_sha[e['sha256']] = texts
        texts = texts_by_sha[e['sha256']]
        if e['sha256'] in json_by_sha:
            # For JSON, validate original byte-bound values, never a derived capture's narration.
            node = json_by_sha[e['sha256']]
            if 'json_pointer' in e:
                try:
                    node = json_pointer(node, e['json_pointer'])
                except (KeyError, IndexError, ValueError) as exc:
                    raise SystemExit(f"{label}: invalid JSON pointer for {e['name']}") from exc
            texts = list(json_strings(node))
        elif 'json_pointer' in e:
            raise SystemExit(f"{label}: JSON pointer needs saved JSON bytes for {e['name']}")
        if not any(' '.join(t.split()).find(' '.join(e['quote'].split())) >= 0 for t in texts if t):
            raise SystemExit(f"{label}: the quote of {e['name']} is not in the stored page {e['sha256'][:12]} (re-run `profile`)")
        historical = historical_appointment(key, e)
        dated = None
        if e.get('dated_listing') is not None:
            raw = (pdf_by_sha.get(e['sha256']) or {}).get(e['url'])
            if raw is None:
                raise SystemExit(f"{e['name']}: dated listing needs hash-verified PDF bytes at its exact source URL")
            dated = dated_listing(e, raw)
        roster = None
        if e.get('dated_roster') is not None:
            if key != 'uiuc':
                raise SystemExit(f"{e['name']}: Illinois appointment roster does not establish faculty at {key}")
            rows = (rosters_by_sha.get(e['sha256']) or {}).get(e['url'])
            if rows is None:
                raise SystemExit(f"{e['name']}: dated roster needs hash-verified PDF bytes at its exact source URL")
            roster = dated_roster(e, rows)
        out.setdefault(' '.join(toks(e['name'])), []).append(dict(unit=e['unit'], url=e['url'], sha256=e['sha256'], observed=e.get('observed') or '', quote=e['quote'],
                                                                   ladder=bool(e.get('ladder', True)), hand=True,
                                                                   **({'json_pointer': e['json_pointer']} if 'json_pointer' in e else {}),
                                                                   **({'appointment_rank': e['appointment_rank']} if e.get('appointment_rank') else {}),
                                                                   **({'dated_listing': dated} if dated else {}),
                                                                   **({'dated_roster': roster} if roster else {}),
                                                                   **({'historical_appointment': historical} if historical else {})))
    return out


def reviewed_pi_basis(key):
    """Source-checked own-group/advising reviews; never substitute for appointment evidence."""
    entries = [e for e in read(P.data('pi-basis-evidence.json', key), [])
               if e.get('kind') in ('own_group', 'advises_phd') and e.get('stage2_review') is True]
    for e in entries:
        if not e.get('pi') or not e.get('unit') or not e.get('role') or not e.get('observed') or e.get('appointment_rank') not in ('research', 'teaching'):
            raise SystemExit('pi-basis-evidence.json: a stage-2 own-group/advising review needs pi, unit, role, observed and research/teaching appointment_rank')
    hand_evidence(key, entries=[dict(e, name=e['pi'], ladder=False) for e in entries], label='pi-basis-evidence.json')
    out = collections.defaultdict(list)
    for e in entries:
        out[' '.join(toks(e['pi']))].append(e)
    return out


def candidate_identity(candidate):
    """A discovery identity, never a display-name key."""
    source = candidate.get('source')
    ids = [candidate.get('dblp')] if source == 'dblp_affiliation' else candidate.get('openalex') if source == 'openalex_rule' else None
    return (source, tuple(sorted(ids))) if ids and all(isinstance(i, str) and i for i in ids) else None


def reviewed_candidate_dispositions(key, candidates, groups):
    """Validate explicit negative reviews against one exact current candidate."""
    out = {}
    entries = [e for e in (read(P.data('cs-related-hand.json', key), []) or []) if e.get('candidate_review') is not None]
    if not entries:
        return out
    db = W.con(key)
    verified_sources, quote_entries = set(), []

    def fail(name, reason):
        raise SystemExit(f'{name}: candidate_review {reason}')

    def checked(entry, evidence):
        if not isinstance(evidence, dict) or not all(isinstance(evidence.get(k), str) and evidence[k].strip()
                                                   for k in ('url', 'sha256', 'quote', 'observed')):
            fail(entry['name'], 'needs complete saved source evidence')
        url, sha = evidence['url'], evidence['sha256']
        if (url, sha) not in verified_sources:
            raw = db.execute('select status,raw_zlib from live where url=? and sha256=?', (url, sha)).fetchone()
            if raw is None:
                raw = db.execute('select http_status,raw_zlib from captures where capture_url=? and sha256=?', (url, sha)).fetchone()
            if not raw or raw[0] != 200 or not raw[1] or hashlib.sha256(zlib.decompress(raw[1])).hexdigest() != sha:
                fail(entry['name'], 'source URL, successful capture and raw hash must agree')
            verified_sources.add((url, sha))
        ev = {k: evidence[k] for k in ('url', 'sha256', 'quote', 'observed')}
        quote_entries.append(dict(name=entry['name'], unit=entry['unit'], ladder=False, **ev))
        return ev

    for entry in entries:
        proof = entry.get('candidate_review')
        if proof is None:
            continue
        name = entry['name']
        if not isinstance(proof, dict) or proof.get('decision') not in ('excluded_scope', 'research_or_other_rank', 'not_faculty_listed', 'pending_identity_collision', 'pending_source_coverage'):
            fail(name, 'supports only explicit negative decisions or unresolved source/identity holds')
        ids, source = proof.get('ids'), proof.get('source')
        if (source not in ('dblp_affiliation', 'openalex_rule') or not isinstance(ids, list) or not ids
                or not all(isinstance(i, str) and i for i in ids) or len(set(ids)) != len(ids)):
            fail(name, 'needs a source and unique complete candidate IDs')
        selector = source, tuple(sorted(ids))
        matches = [c for c in candidates if candidate_identity(c) == selector and toks(c['name']) == toks(name)]
        if len(matches) != 1:
            fail(name, 'must bind exactly one current candidate by name, source and complete IDs')
        if selector in out:
            fail(name, 'has duplicate or conflicting reviews for one source identity')
        if not all(isinstance(proof.get(k), str) and proof[k].strip() for k in ('why', 'identity_note')):
            fail(name, 'needs the decision and identity reasoning')
        if (not isinstance(entry.get('reviewed_by'), str) or not entry['reviewed_by'].strip()
                or not isinstance(entry.get('reviewed_on'), str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', entry['reviewed_on'])):
            fail(name, 'needs an explicit reviewer and review date')
        try:
            datetime.date.fromisoformat(entry['reviewed_on'])
        except ValueError:
            fail(name, 'needs a valid review calendar date')
        if proof['decision'] not in ('excluded_scope', 'pending_identity_collision', 'pending_source_coverage'):
            if entry.get('ladder') is not False:
                fail(name, 'cannot turn a ladder appointment into a negative rank/status decision')
            if any(g['unit'] == entry['unit'] for g in groups.get(' '.join(toks(name)), [])):
                fail(name, 'rank/status decision conflicts with independent PI-basis evidence')
        elif proof['decision'] == 'excluded_scope' and proof.get('rule') != 'R-HIER-05':
            fail(name, 'scope exclusion must name the existing R-HIER-05 rule')
        role = checked(entry, entry)
        identity = proof.get('identity_evidence')
        if not isinstance(identity, list) or not identity:
            fail(name, 'needs source-bound identity evidence')
        identity = [checked(entry, ev) for ev in identity]
        scope = checked(entry, entry.get('scope_evidence')) if proof['decision'] == 'excluded_scope' else None
        out[selector] = dict(entry=entry, proof=proof, role=role, identity=identity, scope=scope)
    for selector, review in out.items():
        peers = [r for k, r in out.items() if k != selector and toks(r['entry']['name']) == toks(review['entry']['name'])]
        own = {(e['url'], e['sha256'], e['quote']) for e in review['identity']}
        shared = {(e['url'], e['sha256'], e['quote']) for r in peers for e in r['identity']}
        if peers and not own - shared:
            fail(review['entry']['name'], 'homonyms need identity evidence specific to each source ID')
    hand_evidence(key, db, entries=quote_entries, label='candidate_review evidence')
    return out


def profile(key, name, unit, url):
    """Fetch one profile page and record faculty evidence for `name` in reviewed/cs-related-hand.json (see the module doc)."""
    c = W.con(key)
    cands = {' '.join(toks(x['name'])): x for x in read(P.data('cs-related-candidates.json', key), [])}
    names = [name] + list((cands.get(' '.join(toks(name))) or {}).get('aliases') or [])
    cen = P.data('census-faculty.json', key)
    if cen.exists():   # a census person's other spellings (a Hangul alias joined on the school's own profile id) are searched too
        doc_ = json.loads(cen.read_text())
        for x in (doc_['faculty'] if isinstance(doc_, dict) else doc_):
            if name == x['name'] or name in (x.get('aliases') or []):
                names += [n for n in [x['name']] + list(x.get('aliases') or []) if n not in names]
    pages = []
    full = url if url.startswith('http') else 'https://' + url
    host = re.sub(r'^https?://', '', full).split('/')[0]
    if S.host_use(key, host) == 'live':
        res = W.live(c, full)
        if res and res[0] == 200:
            pages.append((unit, full, res[1], datetime.date.today().isoformat().replace('-', ''), W.flat(res[2])))
    if not pages:
        rows = W.cdx_rows(c, re.sub(r'^https?://', '', full), collapse='timestamp:4')
        for r in sorted(rows, key=lambda x: x['timestamp'], reverse=True)[:3]:
            cap, st, sha, b = W.capture(c, r['timestamp'], r['original'], full, unit)
            if st == 200:
                pages.append((unit, cap, sha, r['timestamp'], W.flat(b)))
                break
    teaching = not_ladder_titles(key)
    ev = [e for e in faculty_evidence(pages, names, teaching, single_person=True) if e['ladder']]
    if not ev:
        print(json.dumps(dict(name=name, result='no professor title after the name', pages=len(pages))))
        return 1
    e = ev[0]
    ents = read(P.data('cs-related-hand.json', key), [])
    ents = [x for x in ents if not (x['name'] == name and x['url'] == e['url'])] + [dict(name=name, unit=unit, url=e['url'], sha256=e['sha256'], observed=e['observed'], quote=e['quote'], ladder=True)]
    out = P.data_w('cs-related-hand.json', key); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ents, indent=1, ensure_ascii=False))
    print(json.dumps(dict(name=name, result='recorded', quote=e['quote'], observed=e['observed'])))
    return 0


def units_by_recency(lad, centers):
    """The units whose listings prove a ladder appointment, the HOME last: centers (charter [census].center_units, e.g. the ML Center, a center is not an academic department) first, then the
    other units by the date of their latest evidence, so `departments[-1]` is the most recent academic unit (Georgia Tech owner decision 2026-11-04: the ML Center is `also`, never the home)."""
    latest = {}
    for e in lad:
        latest[e['unit']] = max(latest.get(e['unit'], ''), faculty_observed(e))
    cen = [u for u in latest if u in centers]
    return cen + sorted((u for u in latest if u not in centers), key=lambda u: latest[u])


def review(key):
    if not units_current(key):
        sys.exit(f'review refused: units-done.json is missing or older than the charter\'s [[affiliated_units]]; run `cs_related_school.py units {key}` first (Georgia Tech friction 19)')
    cands = read(P.data('cs-related-candidates.json', key), [])
    dblp = read(P.data('dblp-affiliated.json', key), {}).get('persons', [])
    census = {x['name']: x for x in read(P.data('census-faculty.json', key))['faculty']}
    pages = unit_pages(key)
    ids = read(P.data('dblp-ids.json', key), {})
    SH = oa_stats(key)
    SETTLE = list(S.field(S.get(key), 'cs_related.share_test_settles') or [])
    CENTERS = set(S.field(S.get(key), 'census.center_units') or [])
    NOT_FACULTY = S.field(S.get(key), 'cs_related.not_faculty') or {}   # {name = reason}: owner-decided non-faculty (research engineer, staff) whose listing quote a rule misread
    TEACHING = not_ladder_titles(key)
    searched = sorted({p[0] for p in pages})
    OA_MAP = {a if a.startswith('http') else 'https://openalex.org/' + a: n for n, d in (read(P.data('openalex-identity-review.json', key), {}) or {}).get('decisions', {}).items()
              if d.get('basis') == 'pinyin_unique_openalex' for a in d.get('openalex') or []}
    hand = hand_evidence(key)
    group_reviews = reviewed_pi_basis(key)
    dispositions = reviewed_candidate_dispositions(key, cands, group_reviews)
    dec, adds, n = [], [], collections.Counter()
    seen = set()
    by_display_name = collections.defaultdict(list)
    for c in cands:
        by_display_name[' '.join(toks(c['name']))].append(c)
    for c in cands:
        names = [c['name']] + list(c.get('aliases') or [])
        name_key = ' '.join(toks(c['name']))
        disposition = dispositions.get(candidate_identity(c))
        if disposition:
            e, proof = disposition['entry'], disposition['proof']
            if census_alias(census, names):
                raise SystemExit(f"{c['name']}: candidate_review targets an existing core census identity; reconcile the core PI first")
            review_ids = proof['ids']
            comp = dict(dblp=review_ids, **({'dblp_window': c['dblp_window']} if 'dblp_window' in c else {})) if c['source'] == 'dblp_affiliation' else dict(openalex=review_ids)
            d = proof['decision']
            n[d] += 1
            dec.append(dict(name=c['name'], aliases=c.get('aliases') or [], source=c['source'], decision=d,
                            **({'source_id': review_ids[0]} if len(review_ids) == 1 else {'source_ids': review_ids}),
                            reason=proof['why'], cs_basis=comp,
                            faculty_evidence=[dict(unit=e['unit'], ladder=bool(e.get('ladder')),
                                                   **({'appointment_rank': e['appointment_rank']} if e.get('appointment_rank') else {}),
                                                   **disposition['role'])],
                            evidence=disposition['identity'],
                            **({'scope_evidence': disposition['scope'], 'scope_rule': proof['rule']} if disposition['scope'] else {}),
                            identity_note=proof['identity_note'], reviewed_by=e['reviewed_by'], reviewed_on=e['reviewed_on'],
                            years_listed=[], units_searched=searched))
            continue
        if len(by_display_name[name_key]) > 1:
            if name_key not in seen:
                collisions = by_display_name[name_key]
                dec.append(dict(name=c['name'], aliases=[], source='multiple_candidate_ids', decision='pending_identity_collision',
                                reason='distinct candidate source records have the same display name; resolve each source identity before PI admission',
                                candidate_sources=[dict(source=x['source'], dblp=x.get('dblp'), openalex=x.get('openalex')) for x in collisions],
                                cs_basis={}, faculty_evidence=[], years_listed=[], units_searched=searched))
                n['pending_identity_collision'] += 1
            seen.add(name_key)
            continue
        if name_key in seen:
            n['duplicate_dblp_record'] += 1; continue  # two DBLP records of one name: one decision
        seen.add(name_key)
        al = census_alias(census, names, c.get('dblp'), c.get('openalex'), OA_MAP) if c['source'] not in ('affiliated_department', 'official_profile_ladder') else None
        # a census row whose listing gave no rank ('other': UW's 2016-2024 Allen directory heads every card 'Faculty') and that is no PI does not
        # settle the person: the unit evidence decides, as for a person outside the census (UW 2026-11-22, Emanuel Todorov: AMATH archived listing)
        if al and not census[al].get('is_pi') and census[al].get('rank') == 'other':
            al = None
        if al:
            n['census_alias'] += 1
            dec.append(dict(name=c['name'], aliases=c.get('aliases') or [], source=c['source'], decision='census_alias', census_name=al,
                            reason=f'the census person {al} (a DBLP name form of a listed faculty member)', cs_basis=dict(dblp=[c.get('dblp')])))
            continue
        nf = next((r for n_, r in NOT_FACULTY.items() if ' '.join(toks(n_)) == ' '.join(toks(c['name']))), None)
        if nf:
            n['not_faculty_listed'] += 1
            dec.append(dict(name=c['name'], aliases=c.get('aliases') or [], source=c['source'], decision='not_faculty_listed', reason=f'owner decision (charter [cs_related].not_faculty): {nf}', cs_basis={}, faculty_evidence=[], years_listed=[], units_searched=searched))
            continue
        N = Name(names)
        recs = [p for p in dblp if p['pid'] == c.get('dblp')] if c['source'] == 'dblp_affiliation' else []
        win = max([p.get('n_window', 0) for p in recs] or [0])
        comp = dict(dblp=[p['pid'] for p in recs], dblp_window=win, affiliation_notes=[a['text'] for p in recs for a in p['affiliations']][:4],
                    evidence=[dict(url=p['pid'], source=f'DBLP dump {P.DBLP_DUMP_FILE}', quote=next((a['text'] for a in p['affiliations']), None)) for p in recs][:2])
        undecided = None
        di = ids.get(c['name'])
        # A source-checked individual faculty card can establish the same ladder
        # appointment as a directory row. Its computing evidence must still be
        # a decided, evidenced person record, never a namesake candidate count.
        official_decided = (c['source'] == 'official_profile_ladder' and di and di.get('pid')
                            and di.get('basis') in {'homepage_url', 'school_affiliation', 'school_coauthors', 'unique_name', 'unique_exact_name'}
                            and all(di.get(k) for k in ('url', 'dump', 'sha256', 'quote')))
        if c['source'] == 'affiliated_department' or official_decided:  # the person's own decided DBLP record
            if di and di.get('pid'):
                win = di.get('n_window', 0)
                comp = dict(dblp=[di['pid']], dblp_window=win, dblp_basis=di['basis'],
                            evidence=[dict(url=di['url'], source=f"DBLP dump {di['dump']}", sha256=di['sha256'], quote=di['quote'])])
            elif di and di.get('candidates_max_window', 0) == 0:
                win = 0; comp = dict(dblp=[], dblp_window=0, note=f"{di.get('candidates', 0)} DBLP persons of this name, none with a 2016-2026 record")
            else:
                undecided = ('pending_openalex', f"{(di or {}).get('candidates', '?')} DBLP persons of this name, none names the school: decide with "
                             'the OpenAlex sweep (DBLP-indexed share of the school works)')
        if c['source'] == 'affiliated_department':
            x = census[c['name']]
            src = next(s for s in x['sources'] if s.get('rank') == 'ladder')
            fac = [dict(unit=src['kind'].split(':')[-1], url=src['url'], sha256=src['sha256'], observed=src['observed'], quote=src['quote'], ladder=True)]
        else:
            fac = faculty_evidence(pages, names, TEACHING) + hand.get(' '.join(toks(c['name'])), [])
        lad = [e for e in fac if e['ladder']]
        group_basis = next((e for name in names for e in group_reviews.get(' '.join(toks(name)), [])
                            if any(f['unit'] == e['unit'] and not f['ladder'] and f.get('appointment_rank') == e['appointment_rank'] for f in fac)), None)
        pi_fac = lad or ([f for f in fac if f['unit'] == group_basis['unit'] and not f['ladder'] and f.get('appointment_rank') == group_basis['appointment_rank']] if group_basis else [])
        using_group = not lad and bool(pi_fac)
        basis_label = 'reviewed own-group/advising evidence' if using_group else 'professor rank'
        if using_group:
            comp['pi_basis_review'] = {k: group_basis[k] for k in ('kind', 'url', 'sha256', 'quote', 'unit', 'appointment_rank')}
        sh = None
        if SH and pi_fac:
            x = census.get(c['name']) or {}
            orcids = sorted(set(x.get('orcid') or []) | {o for p in recs for o in p.get('orcids') or []})
            if not orcids and (comp.get('dblp') or []):
                orcids = sorted({o for p in dblp if p['pid'] in comp['dblp'] for o in p.get('orcids') or []})
            fy = min([int(((e.get('historical_appointment') or {}).get('start') or faculty_observed(e))[:4]) for e in fac]
                     + ([min(x['years_listed'])] if x.get('years_listed') else []))
            sh = share_test(SH, names, orcids, fy, c.get('openalex') or [])
            comp['openalex_share'] = sh
        settles = sh and (undecided or c['source'] == 'openalex_rule' or any(N.match(n) for n in SETTLE)
                          or (sh['result'] == 'too_few_school_works') or win < MIN_DBLP)
        if sh and pi_fac and not settles:  # a DBLP-decided acceptance stands; a failing share is recorded for the owner
            if sh['result'] == 'not_computing':
                comp['share_flag'] = 'the computing-share test fails; the DBLP decision stands (owner to decide)'
            sh = None
        if sh and pi_fac:
            why_s = f"{sh['dblp_indexed']} of {sh['school_works']} school works DBLP-indexed (share {sh['share']:.2f}; {len(sh['ids'])} OpenAlex author ids)"
            if sh['result'] == 'computing':
                d = 'accepted'; why = f'faculty ({pi_fac[0]["unit"]} listing, {basis_label}); computing-share test passes: ' + why_s
            elif sh['result'] == 'not_computing':
                d = 'faculty_not_computing'; why = f'faculty ({pi_fac[0]["unit"]}); computing-share test fails: ' + why_s
            elif undecided:
                d = 'too_few_school_works'; why = f'faculty ({pi_fac[0]["unit"]}); fewer than {SHARE_MIN_N} school works and no pass, no decided DBLP record: ' + why_s
            elif win >= MIN_DBLP:  # too few school works to measure: the decided DBLP record stands
                d = 'accepted'; why = f'faculty ({pi_fac[0]["unit"]} listing, {basis_label}) with {win} DBLP records 2016-2026; share test cannot measure (' + why_s + ')'
            else:
                d = 'faculty_not_computing'; why = f'faculty ({pi_fac[0]["unit"]}), {win} DBLP records 2016-2026 (< {MIN_DBLP}); share test cannot measure (' + why_s + ')'
        elif undecided:
            d, why = undecided
        elif using_group and c['source'] == 'openalex_rule':
            d = 'pending_openalex'; why = 'source-verified research/teaching PI basis; computing-share test pending school works'
        elif c['source'] == 'openalex_rule' and fac:
            d = 'research_or_other_rank'; why = 'listed by a searched unit only with a research, adjunct, clinical or emeritus title'
        elif pi_fac and win >= MIN_DBLP:
            record_basis = 'in the decided person record' if comp.get('dblp_basis') else 'naming the school'
            d = 'accepted'; why = f'faculty ({pi_fac[0]["unit"]} listing, {basis_label}) with {win} DBLP records 2016-2026 {record_basis}'
        elif pi_fac:
            d = 'faculty_not_computing'; why = f'faculty ({pi_fac[0]["unit"]}), {win} DBLP records 2016-2026 (< {MIN_DBLP})'
        elif fac:
            d = 'research_or_other_rank'; why = 'listed by a searched unit only with a research, adjunct, clinical or emeritus title'
        else:
            # A missing match proves nothing when even one directory capture is a
            # shell, a year is absent, or a paged listing is incomplete. The unit
            # fetch checks URLs, not source completeness. Require an individual
            # reviewed exclusion before treating absence as a negative decision.
            d = 'pending_source_coverage'; why = f'no faculty evidence in the collected pages of {", ".join(searched)}; directory coverage and pagination require review before exclusion'
        n[d] += 1
        row = dict(name=c['name'], aliases=c.get('aliases') or [], source=c['source'], decision=d, reason=why, cs_basis=comp,
                   faculty_evidence=sorted(fac, key=faculty_observed)[:3] + (sorted(fac, key=faculty_observed)[-1:] if len(fac) > 3 else []),
                   years_listed=sorted({int(faculty_observed(e)[:4]) for e in fac if not e.get('historical_appointment')}), units_searched=searched)
        if not SH:
            row['provisional'] = 'computing share pending the OpenAlex sweep (DBLP-indexed share of school works >= 20%)'
        dec.append(row)
        if d == 'accepted' and c['source'] != 'affiliated_department':
            first, last = pi_fac[0], sorted(pi_fac, key=faculty_observed)[-1]
            basis = group_basis if using_group else first
            basis_role = 'professor title on the unit faculty listing'
            if using_group:
                basis_role = group_basis['role']
            elif basis.get('historical_appointment'):
                basis_role = 'source-stated historical faculty appointment'
            elif basis.get('dated_listing'):
                basis_role = ('Reader' if basis['dated_listing']['heading'] == 'READERS' else 'Professor') + ' on the dated officer listing'
            elif basis.get('dated_roster'):
                basis_role = 'professor title on the dated academic appointment roster'
            adds.append(dict(name=c['name'], aliases=row['aliases'], collection_person_id=f'{key}_fac_' + re.sub(r'[^a-z0-9]+', '-', ' '.join(toks(c['name']))).strip('-'),
                             dblp=comp['dblp'][:1], rank=group_basis['appointment_rank'] if using_group else 'ladder', title_as_listed=last['quote'], departments=units_by_recency(pi_fac, CENTERS),
                             years_listed=row['years_listed'], sources=[dict(url=e['url'], sha256=e['sha256'], quote=e['quote'], kind=f"{'historical_appointment' if e.get('historical_appointment') else 'unit_listing'}:{e['unit']}",
                                                                          observed=faculty_observed(e), **dated_source_fields(e)) for e in sorted(pi_fac, key=faculty_observed)],
                             is_pi=True, pi_basis=dict(kind=group_basis['kind'] if using_group else 'ladder_faculty', url=basis['url'], sha256=basis['sha256'], quote=basis['quote'], observed=faculty_observed(basis),
                                                       role=basis_role,
                                                       **dated_source_fields(basis),
                                                       **({'historical_appointment': basis['historical_appointment']} if basis.get('historical_appointment') else {}),
                                                       cs_related=dict(dblp=comp['dblp'], dblp_window=win, openalex=(comp.get('openalex_share') or {}).get('ids'),
                                                                                 share=(comp.get('openalex_share') or {}).get('share'))),
                             lab_units=[], added=f'cs_related_review_{TODAY.replace("-", "")}'))
    doc = dict(school=key, reviewed=TODAY, rule=__doc__.split('\nusage')[0], min_dblp=MIN_DBLP, share_test=dict(min_dblp_indexed=SHARE_MIN_CS, min_share=SHARE_MIN,
               min_works_for_negative=SHARE_MIN_N, applied=bool(SH)), units_searched=searched, counts=dict(n), decisions=dec)
    P.data_w('cs-related-review.json', key).write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    # rows a reviewer added by hand (`reviewed_by`, e.g. UW 2026-11-22: Allen adjuncts by home-unit rank, departed professors by dated archived
    # profiles whose listing card says only 'Faculty') are not this review's output: carry them over unless the review now adds the same person
    mine = {' '.join(toks(a['name'])) for a in adds}
    kept = [x for x in read(P.data('census-additions.json', key), []) or []
            if isinstance(x.get('reviewed_by'), str) and x['reviewed_by'].strip() and ' '.join(toks(x['name'])) not in mine]
    P.data_w('census-additions.json', key).write_text(json.dumps(adds + kept, indent=1, ensure_ascii=False))
    print(json.dumps(dict(decisions=len(dec), additions=len(adds), hand_rows_kept=len(kept), **n)))


if __name__ == '__main__':
    if sys.argv[1] == 'units-check':
        sys.exit(0 if units_current(sys.argv[2]) else 1)
    if sys.argv[1] == 'profile':
        sys.exit(profile(*sys.argv[2:6]))
    {'candidates': candidates, 'units': units, 'review': review}[sys.argv[1]](sys.argv[2])
