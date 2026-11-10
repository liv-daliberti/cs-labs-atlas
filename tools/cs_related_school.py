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
                      not_faculty_listed       no searched unit lists them as faculty in 2016-2026 and the DBLP record
                                               names the school only as a past or student affiliation (or nothing else
                                               shows a faculty appointment); `units_searched` says where we looked
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
            faculty evidence only when the sha256 is a stored capture whose text holds the quote verbatim. The share test still decides computing.
usage: cs_related_school.py candidates|units|units-check|review|profile <key> [<Name> <unit> <url>]
units-check exits 0 when units-done.json covers every unit URL of the charter (a unit added since the last `units` run, or no run, exits 1)
"""
import collections, datetime, gzip, json, re, sys
from pathlib import Path

import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
import school_web as W  # noqa: E402
from pi_hierarchy import Name, toks, nick_ok, nosuffix  # noqa: E402

MIN_DBLP = 5
SHARE_MIN_CS, SHARE_MIN, SHARE_MIN_N = 5, 0.20, 8
TODAY = datetime.date.today().isoformat()
PROF_T = re.compile(r'\b(?:(?:Assistant|Associate|Full|Collegiate|University|Distinguished|Arthur F\. Thurnau)\s+)?Professor\b(?:\s+of\s+[A-Z][\w&,\- ]{2,80})?', re.I)
NOT_LADDER = re.compile(r'emerit|adjunct|status[- ]only|cross[- ]appointed|visiting|research\s+(?:assistant\s+|associate\s+)?professor|clinical|courtesy|professor\s+of\s+(?:the\s+)?practice|lecturer|postdoc', re.I)


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


def candidates(key):
    census = census_rows(read(P.data('census-faculty.json', key)))
    cov = {d['code']: d.get('coverage') for d in S.get(key).get('departments') or []}
    out = []
    for x in census:  # (a) ladder in an affiliated department, never ladder in a full-coverage one
        dep_rank = {((s_.get('kind') or '').split(':')[-1], s_.get('rank')) for s_ in x.get('sources') or []}
        if any(cov.get(d) == 'affiliated' and r == 'ladder' for d, r in dep_rank) and not any(cov.get(d) == 'full' and r == 'ladder' for d, r in dep_rank):
            out.append(dict(name=x['name'], aliases=x.get('aliases') or [], source='affiliated_department', departments=x.get('departments') or []))
    names = [Name([x['name']] + list(x.get('aliases') or [])) for x in census]
    for p in read(P.data('dblp-affiliated.json', key), {}).get('persons', []):
        if p.get('n_window', 0) < MIN_DBLP or p.get('disambiguation'):
            continue
        nm = clean_dblp(p['names'][0])
        if any(N.match(nm) for N in names):
            continue
        out.append(dict(name=nm, aliases=[clean_dblp(n) for n in p['names'][1:]], source='dblp_affiliation', dblp=p['pid'], dblp_window=p['n_window'],
                        affiliations=[a['text'] for a in p['affiliations']], matched_by=p['matched_by']))
    have = names + [Name([c['name']] + list(c.get('aliases') or [])) for c in out]
    for r in read(P.data('cs-related-candidates-openalex.json', key), []):  # (c)
        if r.get('name_matches_pi') or any(N.match(n) for N in have for n in r['names'][:3]):
            continue
        nm = r['name'] if ',' not in r['name'] else ' '.join(reversed([x.strip() for x in r['name'].split(',', 1)]))
        out.append(dict(name=nm, aliases=[n for n in r['names'] if n != r['name']], source='openalex_rule', openalex=[r['author']], oa_works=r['works'],
                        oa_dblp_works=r['dblp_works'], oa_cs_share=r['cs_share'], oa_years=r['years']))
        have.append(Name([nm] + r['names']))
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


def units(key):
    cfg = S.get(key); c = W.con(key)
    n = collections.Counter(); per_unit = {}
    for u in cfg.get('affiliated_units') or []:
        for url in u.get('listings') or []:
            host = re.sub(r'^https?://', '', url).split('/')[0]
            if S.host_use(key, host) == 'live':
                lurl = url if url.startswith('http') else 'https://' + url
                res = W.live(c, lurl)
                n['live'] += 1
                if res and res[0] == 200:  # a paged directory live: follow its pages / A-Z letters too (robots and the per-host delay apply in W.live)
                    import listing_formats as LF
                    lh = W.live_html(c, lurl) or ''
                    for _, lu in (LF.page_links(lh, lurl) or LF.letter_links(lh, lurl)).items() if LF.is_paged(lh) else []:
                        if W.live(c, lu):
                            n['live_pages'] += 1
            rows = W.cdx_rows(c, re.sub(r'^https?://', '', url), collapse='timestamp:4')
            for r in rows:
                cap, st, sha, b = W.capture(c, r['timestamp'], r['original'], url, u['code'])
                n[f'wayback_{st}'] += 1
                print(json.dumps(dict(unit=u['code'], ts=r['timestamp'], status=st, blocks=len(b), shell=len(b) < 5)), flush=True)
                if st == 200:
                    n['paged_pages'] += unit_pages_of(c, cap, r, u['code'], url)
        shells = sorted({ts[:4] for ts, tx in c.execute("select wayback_timestamp, text from captures where department=? and http_status=200", (u['code'],))
                         if len(tx or '') < 500 or (tx or '').count('Professor') < 3})   # a faculty directory names its professors; a capture that does not is a script shell or a nav page
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
        rows = [x for x in W.cdx_rows(c, want, frm=ts0[:4], to=ts0[:4], collapse=None) if x['timestamp'].startswith(ts0[:4])]
        if not rows:
            continue
        x = min(rows, key=lambda z: abs(int(z['timestamp'][:8]) - int(ts0[:8])))
        W.capture(c, x['timestamp'], x['original'], url, code)
        got += 1
    return got


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
    for cap, page, dept, ts, st, sha, txt in c.execute('select capture_url, page_url, department, wayback_timestamp, http_status, sha256, text from captures'):
        k = re.sub(r'^https?://(www\.)?', '', page or '').rstrip('/').lower()
        if st == 200 and txt and (k in codes or dept in codes.values()):
            y = int(str(ts)[:4])
            if 2016 <= y <= 2026:
                out.append((codes.get(k, dept), cap, sha, str(ts), ' '.join(txt.split())))
    for url, at, st, sha, raw in c.execute('select url, fetched_at, status, sha256, raw_zlib from live'):
        k = re.sub(r'^https?://(www\.)?', '', url).rstrip('/').lower()
        if st == 200 and code_of(k):
            import zlib
            if '/wp-json/' in url:
                out.append((code_of(k), url, sha, at[:10].replace('-', ''), wp_json_people_text(zlib.decompress(raw))))
                continue
            b = W.extract.blocks(zlib.decompress(raw), 'text/html', url)
            out.append((code_of(k), url, sha, at[:10].replace('-', ''), W.flat(b)))
    return out


CUT = re.compile(r'Send Email|\bProfile\b|\S+@\S+|Ph\.?\s?D\.?\s+(?:Student|Candidate)|Graduate Student|\(\d{3}\)|\d{3}[-.]\d{3}[-.]\d{4}', re.I)


def faculty_evidence(pages, names):
    """Every (unit, url, sha, observed, quote, ladder) where a page names the person and a professor title follows the
    name directly: the title must start within 60 characters of the name, nothing between them may be a non-ladder
    title, and the segment is cut at the entry's own furniture ('Send Email', 'Profile', an email or phone, 'Ph.D.
    Student'), so the next person's title is never read as this one's (learned 2026-10-29: 'Lauro Ojeda Assistant Research
    Scientist ... Chinedum Okwudire Associate Professor'). A form must end at a name boundary ('Matthew Johnson' is not
    'Matthew Johnson-Roberson')."""
    forms = set()
    for n in names:
        t = n.replace(',', '').split()
        if len(t) >= 2:
            forms |= {n, f'{t[-1]}, {" ".join(t[:-1])}', f'{t[0]} {t[-1]}', f'{t[-1]}, {t[0]}'}
    # forms with middle names or initials the page spells and the candidate's name does not ('Karen Feigh' / 'Karen M Feigh', 'Toktay, Beril' /
    # 'Toktay, L. Beril'): regexes, tried after the literal forms (Georgia Tech friction 20)
    rxs = []
    for n in names:
        t = n.replace(',', '').split()
        given = [x for x in t[:-1] if len(x.strip('.')) >= 3]
        if len(t) >= 2 and given:
            f1, la = re.escape(given[0]), re.escape(t[-1])
            rxs += [rf"{f1}\s+(?:[A-Z][\w.'’-]*\s+){{1,2}}{la}", rf"{la},\s+(?:[A-Z]\.?\s+){{1,2}}{f1}"]
    ev = []
    for unit, url, sha, obs, flat in pages:
        for f in sorted(forms, key=len, reverse=True) + rxs:
            hit = None
            for m in re.finditer(f if f in rxs else re.escape(f), flat):
                nxt = flat[m.end():m.end() + 1]
                if nxt and (nxt.isalnum() or nxt in "-'"):
                    continue
                seg = flat[m.end():m.end() + 220]
                cut = CUT.search(seg)
                seg = seg[:cut.start()] if cut else seg
                pt = PROF_T.search(seg)
                if not pt or pt.start() > 60:
                    continue
                q = flat[m.start():m.end() + pt.end()]
                # the rank is read up to the title's own 'Professor': the 'of <unit>' tail can run on into a second
                # appointment ('Associate Professor of Information, School of Information and Research Associate
                # Professor, ICPSR', learned 2026-10-30, Libby Hemphill)
                core = seg[:pt.start() + re.search(r'Professor', seg[pt.start():], re.I).end()]
                _m = re.match(r'[\s,]*(?:Emerit\w+|Adjunct|\(?Status[- ]only\)?|\(cross-appointed\))', seg[len(core):], re.I)
                core += _m.group(0) if _m else ''  # 'Professor Emeritus' is emeritus, not ladder (Toronto 2026-11-10)
                hit = dict(unit=unit, url=url, sha256=sha, observed=obs, quote=q, ladder=not NOT_LADDER.search(core))
                break
            if hit:
                ev.append(hit)
                break
    return ev


def census_alias(census, names):
    """The census person a candidate already is: a Name match, or the candidate's tokens are the start of a census
    name ('Satinder Singh' is 'Satinder Singh Baveja')."""
    for x in census.values():
        N = Name([x['name']] + list(x.get('aliases') or []))
        for n in names:
            t = toks(n)
            if N.match(n) or any(len(t) >= 2 and toks(m)[:len(t)] == t for m in [x['name']] + list(x.get('aliases') or [])):
                return x['name']
    return None


def hand_evidence(key, c=None):
    """{normalised name: [evidence]} from reviewed/cs-related-hand.json, each entry verified: its sha256 is a stored capture (or live page) whose text holds the quote."""
    ents = read(P.data('cs-related-hand.json', key), [])
    if not ents:
        return {}
    c = c or W.con(key)
    out = {}
    for e in ents:
        if not all(e.get(k) for k in ('name', 'unit', 'url', 'sha256', 'quote')):
            raise SystemExit(f"cs-related-hand.json: entry without name/unit/url/sha256/quote: {e.get('name')}")
        texts = [r[0] for r in c.execute('select text from captures where sha256=?', (e['sha256'],))]
        for url, raw in c.execute('select url, raw_zlib from live where sha256=?', (e['sha256'],)):
            import zlib
            texts.append(W.flat(W.extract.blocks(zlib.decompress(raw), 'text/html', url)))
        if not any(' '.join(t.split()).find(' '.join(e['quote'].split())) >= 0 for t in texts if t):
            raise SystemExit(f"cs-related-hand.json: the quote of {e['name']} is not in the stored page {e['sha256'][:12]} (re-run `profile`)")
        out.setdefault(' '.join(toks(e['name'])), []).append(dict(unit=e['unit'], url=e['url'], sha256=e['sha256'], observed=e.get('observed') or '', quote=e['quote'],
                                                                   ladder=bool(e.get('ladder', True)), hand=True))
    return out


def profile(key, name, unit, url):
    """Fetch one profile page and record faculty evidence for `name` in reviewed/cs-related-hand.json (see the module doc)."""
    c = W.con(key)
    cands = {' '.join(toks(x['name'])): x for x in read(P.data('cs-related-candidates.json', key), [])}
    names = [name] + list((cands.get(' '.join(toks(name))) or {}).get('aliases') or [])
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
    ev = [e for e in faculty_evidence(pages, names) if e['ladder']]
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
        latest[e['unit']] = max(latest.get(e['unit'], ''), e['observed'])
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
    searched = sorted({p[0] for p in pages})
    hand = hand_evidence(key)
    dec, adds, n = [], [], collections.Counter()
    seen = set()
    for c in cands:
        names = [c['name']] + list(c.get('aliases') or [])
        if ' '.join(toks(c['name'])) in seen:
            n['duplicate_dblp_record'] += 1; continue  # two DBLP records of one name: one decision
        seen.add(' '.join(toks(c['name'])))
        al = census_alias(census, names) if c['source'] != 'affiliated_department' else None
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
        if c['source'] == 'affiliated_department':  # the person's own DBLP record, decided by tools/dblp_ids_school.py
            di = ids.get(c['name'])
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
            fac = faculty_evidence(pages, names) + hand.get(' '.join(toks(c['name'])), [])
        lad = [e for e in fac if e['ladder']]
        sh = None
        if SH and lad:
            x = census.get(c['name']) or {}
            orcids = sorted(set(x.get('orcid') or []) | {o for p in recs for o in p.get('orcids') or []})
            if not orcids and (comp.get('dblp') or []):
                orcids = sorted({o for p in dblp if p['pid'] in comp['dblp'] for o in p.get('orcids') or []})
            fy = min([int(e['observed'][:4]) for e in fac] + ([min(x['years_listed'])] if x.get('years_listed') else []))
            sh = share_test(SH, names, orcids, fy, c.get('openalex') or [])
            comp['openalex_share'] = sh
        settles = sh and (undecided or c['source'] == 'openalex_rule' or any(N.match(n) for n in SETTLE)
                          or (sh['result'] == 'too_few_school_works') or win < MIN_DBLP)
        if sh and lad and not settles:  # a DBLP-decided acceptance stands; a failing share is recorded for the owner
            if sh['result'] == 'not_computing':
                comp['share_flag'] = 'the computing-share test fails; the DBLP decision stands (owner to decide)'
            sh = None
        if sh and lad:
            why_s = f"{sh['dblp_indexed']} of {sh['school_works']} school works DBLP-indexed (share {sh['share']:.2f}; {len(sh['ids'])} OpenAlex author ids)"
            if sh['result'] == 'computing':
                d = 'accepted'; why = f'faculty ({lad[0]["unit"]} listing, professor rank); computing-share test passes: ' + why_s
            elif sh['result'] == 'not_computing':
                d = 'faculty_not_computing'; why = f'faculty ({lad[0]["unit"]}); computing-share test fails: ' + why_s
            elif undecided:
                d = 'too_few_school_works'; why = f'faculty ({lad[0]["unit"]}); fewer than {SHARE_MIN_N} school works and no pass, no decided DBLP record: ' + why_s
            elif win >= MIN_DBLP:  # too few school works to measure: the decided DBLP record stands
                d = 'accepted'; why = f'faculty ({lad[0]["unit"]} listing, professor rank) with {win} DBLP records 2016-2026; share test cannot measure (' + why_s + ')'
            else:
                d = 'faculty_not_computing'; why = f'faculty ({lad[0]["unit"]}), {win} DBLP records 2016-2026 (< {MIN_DBLP}); share test cannot measure (' + why_s + ')'
        elif undecided:
            d, why = undecided
        elif c['source'] == 'openalex_rule' and fac:
            d = 'research_or_other_rank'; why = 'listed by a searched unit only with a research, adjunct, clinical or emeritus title'
        elif lad and win >= MIN_DBLP:
            d = 'accepted'; why = f'faculty ({lad[0]["unit"]} listing, professor rank) with {win} DBLP records 2016-2026 naming the school'
        elif lad:
            d = 'faculty_not_computing'; why = f'faculty ({lad[0]["unit"]}), {win} DBLP records 2016-2026 (< {MIN_DBLP})'
        elif fac:
            d = 'research_or_other_rank'; why = 'listed by a searched unit only with a research, adjunct, clinical or emeritus title'
        else:
            d = 'not_faculty_listed'; why = f'no 2016-2026 faculty listing of the searched units ({", ".join(searched)}) names them with a professor title'
        n[d] += 1
        row = dict(name=c['name'], aliases=c.get('aliases') or [], source=c['source'], decision=d, reason=why, cs_basis=comp,
                   faculty_evidence=sorted(fac, key=lambda e: e['observed'])[:3] + (sorted(fac, key=lambda e: e['observed'])[-1:] if len(fac) > 3 else []),
                   years_listed=sorted({int(e['observed'][:4]) for e in fac}), units_searched=searched)
        if not SH:
            row['provisional'] = 'computing share pending the OpenAlex sweep (DBLP-indexed share of school works >= 20%)'
        dec.append(row)
        if d == 'accepted' and c['source'] != 'affiliated_department':
            first, last = lad[0], sorted(lad, key=lambda e: e['observed'])[-1]
            adds.append(dict(name=c['name'], aliases=row['aliases'], collection_person_id=f'{key}_fac_' + re.sub(r'[^a-z0-9]+', '-', ' '.join(toks(c['name']))).strip('-'),
                             dblp=comp['dblp'][:1], rank='ladder', title_as_listed=last['quote'], departments=units_by_recency(lad, CENTERS),
                             years_listed=row['years_listed'], sources=[dict(url=e['url'], sha256=e['sha256'], quote=e['quote'], kind=f"unit_listing:{e['unit']}",
                                                                          observed=e['observed']) for e in sorted(lad, key=lambda e: e['observed'])],
                             is_pi=True, pi_basis=dict(kind='ladder_faculty', url=first['url'], sha256=first['sha256'], quote=first['quote'], observed=first['observed'],
                                                       role='professor title on the unit faculty listing', cs_related=dict(dblp=comp['dblp'], dblp_window=win, openalex=(comp.get('openalex_share') or {}).get('ids'),
                                                                                 share=(comp.get('openalex_share') or {}).get('share'))),
                             lab_units=[], added=f'cs_related_review_{TODAY.replace("-", "")}'))
    doc = dict(school=key, reviewed=TODAY, rule=__doc__.split('\nusage')[0], min_dblp=MIN_DBLP, share_test=dict(min_dblp_indexed=SHARE_MIN_CS, min_share=SHARE_MIN,
               min_works_for_negative=SHARE_MIN_N, applied=bool(SH)), units_searched=searched, counts=dict(n), decisions=dec)
    P.data_w('cs-related-review.json', key).write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    P.data_w('census-additions.json', key).write_text(json.dumps(adds, indent=1, ensure_ascii=False))
    print(json.dumps(dict(decisions=len(dec), additions=len(adds), **n)))


if __name__ == '__main__':
    if sys.argv[1] == 'units-check':
        sys.exit(0 if units_current(sys.argv[2]) else 1)
    if sys.argv[1] == 'profile':
        sys.exit(profile(*sys.argv[2:6]))
    {'candidates': candidates, 'units': units, 'review': review}[sys.argv[1]](sys.argv[2])
