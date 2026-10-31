"""Identity: is the authorship that matches the PI's name the PI? The anchors (the PI's DBLP person page from the cached
lists and the DBLP dump, the DBLP-verified collection works, the PI's institutional and lab publication lists, reviewed
OpenAlex ids, ORCIDs, advisees as co-authors) and the authorships of the sweep and of pi-works.sqlite matched to PIs.
R-PAP-04 (the order of identities), R-PAP-05 (the DBLP dump), R-PAP-06 (mixed ids), R-PAP-07 (initials), R-PAP-24 (page 1
for DBLP-anchored works)."""
import collections, gzip, html, json, re, sqlite3, zlib

import atlas_paths as P  # every path in one place
from .common import DBLP, NOT_PAPERS, ndoi, norm_title, read, sweep_works
from .names import Name, all_initials, byline_name, clean_person_name, full_pair, name_conflict, nosuffix, toks

DUMP_PERSONS = None  # hierarchy/dblp-dump-persons.json.gz, read once per process


def apply_cached_lists(pis, pubs, dblp_doi, dblp_title, n):
    """R-PAP-05 with the pre-protocol schools' cached DBLP publication lists (`pubs`: key -> record with authors {pid:
    name}): a census DBLP id whose names never carry the PI's name is dropped; a PI without one takes the one DBLP person
    of exactly that name; every record of the PI's ids anchors by DOI and title."""
    by_dname = collections.defaultdict(set)  # a PI without a census DBLP id: the one DBLP person of exactly that name, if unique
    for rec in pubs.values():
        for q, dn in (rec.get('authors') or {}).items():
            if not re.search(r'\d{4}$', dn or ''):
                by_dname[' '.join(toks(dn))].add(q)
    dname = collections.defaultdict(set)
    for rec in pubs.values():
        for q, dn in (rec.get('authors') or {}).items():
            dname[q].add(re.sub(r'\s+\d{4}$', '', dn or ''))
    n['dblp_ids_dropped_name_mismatch'] = 0
    for p in pis:  # a census DBLP id whose person never carries the PI's name is someone else's (e.g. 'Jun Zhu' for Jun-Yan Zhu)
        keep = [q for q in p['dblp'] if q not in dname or any(not name_conflict(p['names'], dn) for dn in dname[q])]
        if len(keep) < len(p['dblp']):
            n['dblp_ids_dropped_name_mismatch'] += len(p['dblp']) - len(keep); p['dblpDropped'] = sorted(set(p['dblp']) - set(keep)); p['dblp'] = keep
    for p in pis:
        if not p['dblp']:
            c_ = {q for n_ in p['names'] for q in by_dname.get(' '.join(toks(n_)), set())}
            if len(c_) == 1:
                p['dblp'] = sorted(c_); p['dblpBasis'] = 'unique DBLP person of that exact name among the cached publication co-authors'
    owner = collections.defaultdict(list)
    for p in pis:
        for q in p['dblp']:
            owner[q].append(p['pi'])
    for rec in pubs.values():
        for q in rec.get('authors') or {}:
            for pi in owner.get(q, []):
                if rec.get('doi'):
                    dblp_doi[pi].add(ndoi(rec['doi']))
                dblp_title[pi][norm_title(rec.get('title', '').rstrip('.'))] = rec.get('year')


def apply_dump(pis, dump, dblp_doi, dblp_title, n):
    """R-PAP-05 with DBLP's own dump (`dump`: hierarchy/dblp-dump-persons.json.gz, {persons, by_name}): name conflicts
    drop an id, a PI still without one takes the unique person of exactly that name (no disambiguation record), every
    record anchors by DOI and title, and the person's ORCIDs join the PI's."""
    DP, DN = dump['persons'], dump['by_name']
    for p in pis:
        keep = [q for q in p['dblp'] if q not in DP or any(not name_conflict(p['names'], re.sub(r'\s+\d{4}$', '', dn)) for dn in DP[q]['names'])]
        if len(keep) < len(p['dblp']):
            n['dblp_ids_dropped_name_mismatch'] += len(p['dblp']) - len(keep)
            p['dblpDropped'] = sorted(set(p.get('dblpDropped') or []) | (set(p['dblp']) - set(keep))); p['dblp'] = keep
        if not p['dblp']:
            c_ = {q for n_ in p['names'] for q in DN.get(' '.join(toks(n_)), [])}
            if len(c_) == 1 and not any(DP[q].get('disambiguation') for q in c_):
                p['dblp'] = sorted(c_); p['dblpBasis'] = 'unique DBLP person of that exact name in the DBLP dump'; n['dblp_ids_from_dump_name'] += 1
        for q in p['dblp']:
            rec_ = DP.get(q)
            if not rec_:
                continue
            k0 = len(dblp_title[p['pi']])
            for r_ in rec_['pubs']:
                for d_ in r_.get('dois') or []:
                    dblp_doi[p['pi']].add(ndoi(d_))
                t_ = norm_title(html.unescape(r_.get('title') or '').rstrip('.'))
                if t_:
                    dblp_title[p['pi']].setdefault(t_, r_.get('year'))
            n['dblp_dump_titles_added'] += len(dblp_title[p['pi']]) - k0
            new_orcid = [o_ for o_ in rec_.get('orcid') or [] if o_ not in p['orcid']]
            if new_orcid:
                p['orcid'] = list(p['orcid']) + new_orcid; p['orcidFromDblp'] = new_orcid; n['pis_orcid_from_dblp'] += 1


def anchors(ctx):
    """The identity anchors of every PI: verified collection works, DBLP DOIs and titles, the PI's own and lab
    publication lists, the lab's advisee names."""
    HERE, school, pis, pls, stu, n = ctx.here, ctx.school, ctx.pis, ctx.pls, ctx.stu, ctx.n
    # identity anchors: the PI's own DBLP publication list, the PI's DBLP-verified collection works, a stated advisee as co-author
    verified = {p['pi']: {l['work'] for i in p['personIds'] for l in pls[i] if l.get('status') == 'verified' and l.get('role', 'author') == 'author'} for p in pis}
    dblp_doi, dblp_title = collections.defaultdict(set), collections.defaultdict(dict)
    dp = P.archive_sweep(DBLP.get(school, '')) / 'raw/dblp_pubs.json.gz'
    if P.data('dblp_pubs.json.gz', school, root=HERE).exists():  # Princeton: converted from the lab records' cached DBLP answers
        dp = P.data('dblp_pubs.json.gz', school, root=HERE)
    if dp.exists() and dp.name == 'dblp_pubs.json.gz' and (DBLP.get(school) or 'hierarchy' in str(dp)):
        pubs = read(dp)['pubs']
        apply_cached_lists(pis, pubs, dblp_doi, dblp_title, n)
    # the PI's full DBLP person page from DBLP's own dump (tools/dblp_dump_persons.py -> hierarchy/dblp-dump-persons.json.gz;
    # 2026-10-29): the cached lists above hold only what the census queries returned, so a PI found as a co-author there
    # (Song Mei: 13 of 96 records) or added to the census later had a partial or empty list. Every record of the PI's
    # DBLP person anchors identity by DOI or title, as the cached lists do; a PI still without a DBLP id takes the one
    # person record of exactly that name in the dump when no other record carries the name (no homonyms); a census id
    # whose dump names never carry the PI's name is dropped as with the cached lists. ORCIDs on the person record (DBLP's
    # curated person links) join the PI's ORCIDs.
    dd_f = P.data('dblp-dump-persons.json.gz', root=HERE)
    if dd_f.exists():
        global DUMP_PERSONS
        if DUMP_PERSONS is None:
            DUMP_PERSONS = read(dd_f)
        apply_dump(pis, DUMP_PERSONS, dblp_doi, dblp_title, n)
    n['pis_with_dblp_list'] = sum(bool(dblp_title[p['pi']]) for p in pis)
    own_list = collections.defaultdict(dict)  # the PI's own institutional publication list (hierarchy/<school>/pi-publication-lists.json)
    pl_f = P.data('pi-publication-lists.json', school, root=HERE)
    for pi_, rows_ in (read(pl_f) if pl_f.exists() else {}).items():
        for r_ in rows_:
            own_list[pi_][norm_title(r_['title'])] = r_.get('year')
    n['pis_with_own_publication_list'] = sum(bool(own_list[p['pi']]) for p in pis)
    lab_page = collections.defaultdict(list)  # the lab's own publications page (labpage-pubs.jsonl.gz): citation strings, title inside
    lp_f = P.data('labpage-pubs.jsonl.gz', school, root=HERE)
    for line in (gzip.open(lp_f, 'rt') if lp_f.exists() else []):
        r_ = json.loads(line)
        if r_.get('sha256') and r_.get('quote'):
            lab_page[r_['pi']].append((norm_title(r_.get('title')), r_.get('year')))
    n['pis_with_lab_publication_page'] = sum(bool(lab_page[p['pi']]) for p in pis)
    advisee_names = {p['pi']: [Name([s_['name']]) for s_ in stu[p['pi']].values()] for p in pis}
    adv_full = {p['pi']: {fp_ for s_ in stu[p['pi']].values() for nm_ in [s_['name']] + list(s_.get('aliases') or []) for fp_ in [full_pair(clean_person_name(nm_))] if fp_} for p in pis}
    ctx.verified, ctx.dblp_doi, ctx.dblp_title, ctx.own_list, ctx.lab_page = verified, dblp_doi, dblp_title, own_list, lab_page
    ctx.advisee_names, ctx.adv_full = advisee_names, adv_full


def authorship_identity(ctx, pi, w, a, cw):
    """R-PAP-04, R-PAP-07: the identity that makes authorship `a` of work `w` (collection work `cw`) the PI's, in order,
    or None. An id reviewed as someone else's (or another PI's reviewed id) is never the PI."""
    blocked, reviewed_oa, orcids, verified = ctx.blocked, ctx.reviewed_oa, ctx.orcids, ctx.verified
    dblp_doi, dblp_title, own_list, lab_page = ctx.dblp_doi, ctx.dblp_title, ctx.own_list, ctx.lab_page
    advisee_names, pid0 = ctx.advisee_names, ctx.pid0
    if (a.get('author') or {}).get('id') in blocked[pi]:
        return None
    if (a.get('author') or {}).get('id') in reviewed_oa[pi]:
        return 'reviewed_openalex_author_id'
    if re.sub(r'^https?://orcid\.org/', '', (a.get('author') or {}).get('orcid') or '') in orcids[pi]:
        return 'pi_orcid'
    if cw and cw in verified[pi]:
        return 'dblp_verified_collection_work'
    if ndoi(w.get('doi')) in dblp_doi[pi]:
        return 'dblp_person_page_doi'
    y = dblp_title[pi].get(norm_title(w.get('title')))
    if y is not None and (not y or not w.get('publication_year') or abs(int(y) - w['publication_year']) <= 1):
        return 'dblp_person_page_title'
    y = own_list[pi].get(norm_title(w.get('title')), -1)
    if y != -1 and (not y or not w.get('publication_year') or abs(int(y) - w['publication_year']) <= 1):
        return 'pi_institutional_publication_list'
    t_ = norm_title(w.get('title'))
    if len(t_) >= 30 and any(t_ in c_ and (not y_ or not w.get('publication_year') or abs(int(y_) - w['publication_year']) <= 1) for c_, y_ in lab_page[pi]):
        return 'lab_publication_page'  # the title inside a citation the PI's lab lists (title, authors, venue run together)
    others = [(x.get('raw_author_name') or (x.get('author') or {}).get('display_name') or '') for x in w.get('authorships') or [] if x is not a]
    # two initials prove nothing (2026-10-29: 'M. Wang' with 'J. Zhang' on EAST plasma papers made a Hefei M. Wang
    # Mengdi Wang's, and 'Y. L. Chen' with 'H. Hu' a Nanjing Y. L. Chen Yuxin Chen's): the PI or the advisee must be
    # written with a full given name
    def full(x):
        t_ = nosuffix(toks(byline_name(x)))
        return len(t_) >= 2 and len(t_[0]) > 1
    pi_raw = a.get('raw_author_name') or (a.get('author') or {}).get('display_name') or ''
    # ... unless the initials spell every given name of a PI with two or more ('M.T. Islam' is Md Tauhidul Islam;
    # 'Y. L. Chen' is still not Yuxin Chen, 'M. Wang' still not Mengdi Wang) (2026-10-29, owner: best judgement)
    pi_full = full(pi_raw) or all_initials(pid0[pi].get('names') or [pi], pi_raw)
    if any(an.match(o) and (pi_full or full(o)) for an in advisee_names[pi] for o in others):
        return 'advisee_coauthor'
    return None


def id_sets(ctx):
    """Per PI: reviewed OpenAlex ids, ORCIDs, blocked ids (reviewed as not the PI, unless mixed; and every other PI's
    reviewed id, 2026-10-28) and mixed ids (R-PAP-06)."""
    pis, n = ctx.pis, ctx.n
    reviewed_oa = {p['pi']: set(p.get('reviewedOpenAlex') or []) for p in pis}
    orcids = {p['pi']: set(p.get('orcid') or []) for p in pis}
    blocked = {p['pi']: set(p.get('notOpenAlex') or []) - set(p.get('mixedOpenAlex') or []) for p in pis}
    mixed = {p['pi']: set(p.get('mixedOpenAlex') or []) for p in pis}
    # another PI's reviewed author id is never this PI's (2026-10-28: S. Simon Wong's advisees co-wrote with H.-S. Philip
    # Wong, so the advisee rule anchored Philip Wong's reviewed id to Simon Wong through the 'S.' in 'H.-S.')
    all_reviewed = collections.Counter(a for s_ in reviewed_oa.values() for a in s_)
    for p in pis:
        blocked[p['pi']] |= {a for a in all_reviewed if a not in reviewed_oa[p['pi']]}
    n['other_pi_reviewed_ids_blocked'] = sum(len(v) for v in blocked.values())
    ctx.reviewed_oa, ctx.orcids, ctx.blocked, ctx.mixed = reviewed_oa, orcids, blocked, mixed


def hits(ctx):
    """The authorships matched to PIs: sweep works with an authorship matching the PI's name (with its identity), surname
    hits under an anchored or reviewed id, and the PI's own works outside the sweep (pi-works.sqlite) under an anchored or
    reviewed id or tied by page 1 (R-PAP-24). Anchored author ids are counted on the way."""
    HERE, school, pis, n, nm, by_sur, cwork = ctx.here, ctx.school, ctx.pis, ctx.n, ctx.nm, ctx.by_sur, ctx.cwork

    def identity_of(pi, w, a, cw):
        return authorship_identity(ctx, pi, w, a, cw)
    surname_only = []
    anchored = collections.defaultdict(collections.Counter)
    via_advisee = collections.defaultdict(collections.Counter)  # an author id on 2+ works the PI wrote with their own advisees anchors too
    id_sets(ctx)
    reviewed_oa, blocked, mixed = ctx.reviewed_oa, ctx.blocked, ctx.mixed
    hits = []  # (pi, oa work, authorship, collection work, identity)
    for w in sweep_works(school, HERE):
        if w.get('type') in NOT_PAPERS:  # datasets, peer reviews, errata, supplements: not papers
            continue
        cw = None; done = set()
        for a in w.get('authorships') or []:
            raw = a.get('raw_author_name') or (a.get('author') or {}).get('display_name') or ''
            t = nosuffix(toks(raw))  # "John Fisher III" is looked up under Fisher
            if len(t) < 2:
                continue
            for pi in sorted(set(by_sur.get(t[-1], []) + by_sur.get(''.join(t[1:]), []) + by_sur.get(t[0], []))):  # sorted: hit order
                if pi in done:
                    continue
                if not nm[pi].match(raw):
                    if (a.get('author') or {}).get('id'):  # "Zhiwei Steven Wu" for Steven Wu: decided once the PI's ids are anchored
                        surname_only.append((pi, w, a))
                    continue
                if cw is None:
                    cw = cwork(w) or ''
                done.add(pi)
                ident = identity_of(pi, w, a, cw)
                if (a.get('author') or {}).get('id') in mixed[pi]:
                    pass  # a mixed record never anchors
                elif ident and ident != 'advisee_coauthor' and (a.get('author') or {}).get('id'):
                    anchored[pi][a['author']['id']] += 1
                elif ident == 'advisee_coauthor' and (a.get('author') or {}).get('id'):
                    via_advisee[pi][a['author']['id']] += 1
                hits.append((pi, w, a, cw or None, ident, None))
    for pi, c in via_advisee.items():
        for aid, k in c.items():
            if k >= 2:
                anchored[pi][aid] += 0.5  # weaker than a DBLP- or review-anchored id; recorded apart in the identity label
    n['sweep_name_hits'] = len(hits)
    seen_pw = {(h[0], h[1]['id']) for h in hits}
    for pi, w, a in surname_only:  # the same surname under an author id anchored (or reviewed) for this PI
        aid = a['author']['id']
        if (pi, w['id']) in seen_pw or aid in blocked[pi] or not (anchored[pi].get(aid, 0) >= 1 or aid in reviewed_oa[pi]):
            continue
        seen_pw.add((pi, w['id'])); hits.append((pi, w, a, cwork(w) or None, 'reviewed_openalex_author_id' if aid in reviewed_oa[pi] else 'anchored_author_id', None))
        n['surname_only_hits_by_anchored_id'] += 1
    # the PI's own works outside the sweep (hierarchy/<school>/pi-works.sqlite, tools/pi_fulltext_affiliation.py): an
    # authorship with no recorded institution whose page 1 ties the school to the PI, and works over the sweep's author cap
    pw = P.data('pi-works.sqlite', school, root=HERE)
    tied, from_pw, page_read = {}, set(), {}
    if pw.exists():
        con = sqlite3.connect(f'file:{pw}?mode=ro', uri=True)
        tied = {r[0]: dict(json.loads(r[1]), url=r[2], pdf_sha256=r[3]) for r in con.execute('select work, quote, url, pdf_sha256 from pages where school_named=1')}
        page_read = {r[0]: (r[1], r[2], r[3]) for r in con.execute('select work, status, page1, url from pages')}  # R3: every page-1 read
        in_sweep = {h[1]['id'] for h in hits}
        owner = collections.defaultdict(list)
        for p in pis:
            for a_ in set(anchored[p['pi']]) | reviewed_oa[p['pi']]:
                owner[a_].append(p['pi'])
        k0 = len(hits)
        for (b_,) in con.execute('select body from works'):
            w = json.loads(zlib.decompress(b_))
            if w['id'] in in_sweep or w.get('type') in NOT_PAPERS:
                continue
            for a in w.get('authorships') or []:
                aid = (a.get('author') or {}).get('id')
                for pi in owner.get(aid, []):
                    raw = a.get('raw_author_name') or (a.get('author') or {}).get('display_name') or ''
                    if aid in blocked[pi] or not nm[pi].match(raw):
                        continue
                    ident = 'reviewed_openalex_author_id' if aid in reviewed_oa[pi] else ('anchored_author_id' if anchored[pi][aid] >= 1 else 'advisee_anchored_author_id')
                    hits.append((pi, w, a, cwork(w), ident, tied.get(w['id']))); from_pw.add((pi, w['id']))
            # R8 (R-PAP-24, 2026-10-29, owner: accuracy sample): a work whose page 1 ties the school to the PI by name, at an
            # authorship with no institution, under an author id that is not (yet) anchored, is the PI's when the PI's own
            # DBLP person page (or another non-advisee identity) names it: Jacob Fox's JCTB 2025 paper
            if w['id'] in tied:
                for a in w.get('authorships') or []:
                    raw = a.get('raw_author_name') or (a.get('author') or {}).get('display_name') or ''
                    t = nosuffix(toks(raw)); aid = (a.get('author') or {}).get('id')
                    if len(t) < 2 or a.get('institutions') or a.get('raw_affiliation_strings'):
                        continue
                    for pi in sorted(set(by_sur.get(t[-1], []))):
                        if (pi, w['id']) in from_pw or aid in blocked[pi] or not nm[pi].match(raw) \
                                or toks(pi)[-1] not in toks(' '.join(tied[w['id']].get('quotes') or [])):
                            continue
                        cw_ = cwork(w); ident = identity_of(pi, w, a, cw_)
                        if ident and ident != 'advisee_coauthor':
                            hits.append((pi, w, a, cw_, ident, tied[w['id']])); from_pw.add((pi, w['id'])); n['pi_work_page1_dblp_hits'] += 1
        n['pi_work_list_hits'] = len(hits) - k0
    ctx.hits, ctx.anchored, ctx.tied, ctx.from_pw, ctx.page_read = hits, anchored, tied, from_pw, page_read
