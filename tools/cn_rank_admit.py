"""Rank-sourced PI admission for Han-name schools whose listings print only "教师" (HIT, SEU; process v4, owner 2026-11-18).

A listing proves an appointment but NOT a rank. This tool admits a person as a PI only from a rank source: the official department
list of doctoral supervisors (博士生导师), fetched live with the project fetcher (robots honoured, no redirects, stored in the school's
capture store with its sha256). Adjunct (兼职) supervisors are never admitted. Names on the list that the census does not hold
become census additions with the list as their dated listing; names the census holds get a `pi-basis-evidence.json` record
(kind advises_phd). A person that cannot be told apart from a same-name census row (two rows with the name) is held, never guessed.

Identity anchor (never a name match): the official homepage the list links for the person, when the DBLP dump's person record lists
that same URL (`dblp_school_homepages.py` cache). Exactly one non-disambiguation record, else no anchor (the PI stays held).

  cn_rank_admit.py <key> fetch                 fetch and store the rank pages (live, robots honoured)
  cn_rank_admit.py <key> plan                  print the plan (counts, held names), write nothing
  cn_rank_admit.py <key> write --dblp CACHE    write reviewed/pi-basis-evidence.json, census-additions.json, census-overrides-school.json
"""
import datetime
import gzip
import html
import json
import re
import sys
import zlib
from pathlib import Path

import atlas_paths as P  # noqa: E402
import census_overrides as CO  # noqa: E402
import school_web as W  # noqa: E402

CSR_URL = 'https://raw.githubusercontent.com/emeryberger/CSrankings/5319eddd1e27048c22751de68bb5344a25d7b091/csrankings.csv'   # stored in the school's capture store (live table) with its sha256
WHO = 'claude-ns-a-1118'
TODAY = datetime.date.today().isoformat()

SOURCES = {
    'hit': [dict(url='https://cs.hit.edu.cn/22195/list.htm', unit='CS', kind='td',
                 sections={'计算机科学与技术学科': True, '软件工程学科': True, '网络空间安全学科': True, '兼职博导': False})],
    'seu': [dict(url='https://cs.seu.edu.cn/dsxx/list.htm', unit='CS', kind='ry-xm',
                 sections={'博士生导师': True, '硕士生导师': False})],
}


def ivpn(u):
    """A WebVPN-encoded link (homepage-hit-edu-cn.ivpn.hit.edu.cn:1080/x, '-s' = https, '--' = a literal hyphen) -> the real URL."""
    m = re.match(r'(https?)://([a-z0-9-]+)\.ivpn\.hit\.edu\.cn(?::\d+)?(/.*)?$', u or '')
    if not m:
        return u
    host, https = m.group(2), False
    if host.endswith('-s'):
        host, https = host[:-2], True
    host = host.replace('--', '\0').replace('-', '.').replace('\0', '-')
    return ('https://' if https else 'http://') + host + (m.group(3) or '')


def _aliases(d):
    """Latin name forms of the bound DBLP person: the record's own names, else the CSRankings row's name (homonym number dropped)."""
    if d.get('names'):
        return list(dict.fromkeys(re.sub(r'\s\d{4}$', '', n) for n in d['names']))
    return [re.sub(r'\s\d{4}$', '', d['quote'].split(',')[0])]


def nurl(u):
    u = re.sub(r'^https?://(?:www\.)?', '', (u or '').strip().lower()).split('#')[0].split('?')[0].rstrip('/')
    return re.sub(r'/index\.(?:html?|jsp)$', '', u)


def plain(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s))).strip()


def name_key(s):
    return re.sub(r'[\s　 ]+', '', html.unescape(s))


def stored(c, url):
    r = c.execute('select status, sha256, raw_zlib from live where url=?', (url,)).fetchone()
    if not r or r[0] != 200:
        raise SystemExit(f'{url}: not stored with status 200 (run fetch)')
    return r[1], zlib.decompress(r[2]).decode('utf-8', 'replace')


def parse(src, body):
    """[{section, include, name, key, href, adjunct}] in page order."""
    heads = []
    for sec in src['sections']:
        m = re.search(r'<h2[^>]*>\s*' + re.escape(sec) + r'\s*</h2>', body)
        i = m.start() if m else body.find(sec)
        if i < 0:
            raise SystemExit(f"section {sec!r} not on {src['url']}")
        # the section heading is the LAST occurrence before its first name, so take the first occurrence after the usage comment
        heads.append((i, sec))
    heads.sort()
    out = []
    for n, (i, sec) in enumerate(heads):
        seg = body[i:heads[n + 1][0] if n + 1 < len(heads) else len(body)]
        cells = re.findall(r'<td[^>]*>(.*?)</td>', seg, re.S) if src['kind'] == 'td' else re.findall(r'<p class="ry-xm[^"]*">(.*?)</p>', seg, re.S)
        for cell in cells:
            t = plain(cell)
            if not t or t == sec:
                continue
            a = re.search(r'href="([^"]+)"', cell)
            adj = '兼职' in t
            nm = re.sub(r'\(?兼职\)?', '', t)
            out.append(dict(section=sec, include=src['sections'][sec] and not adj, name=nm.strip(), key=name_key(nm), href=ivpn(html.unescape(a.group(1))) if a else None,
                            adjunct=adj or not src['sections'][sec]))
    return out


def flat_of(c, url):
    sha, body = stored(c, url)
    return sha, W.flat(W.extract.blocks(body.encode(), 'text/html', url))


def quote_for(flat, ent, prev):
    """A verbatim quote of the page's text: the previous name and this one as printed (spaces inside a two-character name kept)."""
    def rx(s):
        return r'\s*'.join(re.escape(ch) for ch in name_key(s))
    pat = (rx(prev) + r'\s+' if prev else '') + rx(ent['name'])
    m = re.search(pat, flat) or re.search(rx(ent['name']), flat)   # the list order is not always the text order: the name alone as a fallback
    return m.group(0) if m else None


def fetch(key):
    c = W.con(key)
    for src in SOURCES[key]:
        res = W.live(c, src['url'])
        print(src['url'], 'blocked/robots' if res is None else res[0])


def census_index(key):
    fac = json.loads(P.data('census-faculty.json', key).read_text())['faculty']
    by = {}
    for x in fac:
        by.setdefault(name_key(re.sub(r'\s*\[.*\]$', '', x['name'])), []).append(x)
    return fac, by


def run(key, write=False, dblp_cache=None, csr=None, recall=None):
    c = W.con(key)
    fac, by = census_index(key)
    ents, srcs = [], {}
    for src in SOURCES[key]:
        sha, flat = flat_of(c, src['url'])
        srcs[src['url']] = (sha, flat, src['unit'])
        prev = None
        for e in parse(src, stored(c, src['url'])[1]):
            e.update(url=src['url'], sha=sha, unit=src['unit'])
            e['quote'] = quote_for(flat, e, prev) if e['include'] else None
            prev = e['name']
            ents.append(e)
    inc, seen = [], {}
    for e in ents:   # one person under several discipline headings of the same list (same name, same link) counts once
        if not e['include']:
            continue
        k_ = (e['key'], nurl(e['href']) if e['href'] else None)
        if k_[1] and k_ in seen:
            seen[k_]['sections'].append(e['section'])
            continue
        e['sections'] = [e['section']]
        seen[k_] = e
        inc.append(e)
    dup_keys = {k for k in {e['key'] for e in inc} if sum(1 for e in inc if e['key'] == k) > 1}
    dblp = {}
    if dblp_cache:
        for p in json.load(gzip.open(dblp_cache, 'rt', encoding='utf-8'))['persons']:
            for u in p['urls']:
                dblp.setdefault(nurl(u), []).append(p)
    csr_home, pid_of = {}, {}
    if csr and recall:   # CSRankings row whose own homepage equals the official-list homepage (a URL binding, never a name match); pid from the recall record of that homepage
        import csv
        import hashlib
        csr_sha = hashlib.sha256(Path(csr).read_bytes()).hexdigest()
        for r in csv.DictReader(open(csr, encoding='utf-8')):
            if r['homepage']:
                csr_home.setdefault(nurl(r['homepage']), []).append(r)
        for cnd in json.load(open(recall))['candidates'].get(key, []):
            for h in cnd.get('home') or []:
                if 'csr' in cnd.get('srcs', []) and len(cnd.get('dblp') or []) == 1:
                    pid_of.setdefault(nurl(h), set()).add('https://dblp.org/pid/' + cnd['dblp'][0])
    csr_name, pinyin_count, full, csr_rows = {}, {}, {}, {}   # D-0004 (owner 2026-11-18): CSRankings entry + a UNIQUE full-name match in the official roster, medium confidence
    if csr and recall:
        from pypinyin import lazy_pinyin
        for rows_ in csr_home.values():
            for r in rows_:
                csr_rows.setdefault(r['name'], r)
        for cnd in json.load(open(recall))['candidates'].get(key, []):
            if 'csr' in cnd.get('srcs', []) and len(cnd.get('dblp') or []) == 1:
                for nm in cnd.get('names') or []:
                    if re.fullmatch(r"[A-Za-z' .-]+", nm) and len(nm.split()) >= 2:
                        t = [x.lower() for x in re.findall(r"[A-Za-z']+", re.sub(r'\s\d{4}$', '', nm))]
                        for kk in {''.join(t), ''.join(reversed(t))}:
                            full.setdefault(kk, set()).add((nm, cnd['dblp'][0]))
        han_all = [x['name'] for x in fac] + [z['name'] for z in ents]
        for hn in han_all:
            k_ = name_key(hn)
            if re.fullmatch(r'[\u4e00-\u9fff]{2,4}', k_):
                py = ''.join(lazy_pinyin(k_)).lower()
                pinyin_count[py] = pinyin_count.get(py, set()) | {k_}
        csr_name = {py: next(iter(v)) for py, v in full.items() if len(v) == 1 and len(pinyin_count.get(py, ())) == 1}
    plan = dict(basis=[], additions=[], held=[], identity=[])
    for e in inc:
        rows = by.get(e['key'], [])
        why, hp = None, (nurl(e['href']) if e['href'] else None)
        e['census'] = None
        if e['quote'] is None:
            why = 'quote not found verbatim in the stored page'
        elif e['key'] in dup_keys or len(rows) > 1:   # a shared name binds to a census row by its homepage only
            cand = [r for r in rows if hp and nurl(r.get('profile_url')) == hp]
            if len(cand) == 1 and sum(1 for z in inc if z['key'] == e['key'] and z['href'] and nurl(z['href']) == hp) == 1:
                e['census'] = cand[0]
            else:
                why = 'same name on the supervisor list or in the census more than once, and no profile URL equals the list link'
        elif len(rows) == 1:
            e['census'] = rows[0]
        if why:
            plan['held'].append(dict(name=e['name'], why=why))
            e['skip'] = True
            continue
        e['skip'] = False
        (plan['basis'] if e['census'] else plan['additions']).append(e['name'])
        recs = [p for p in dblp.get(nurl(e['href']), []) if not p['disambiguation']] if e['href'] else []
        pids = sorted({p['pid'] for p in recs})
        e['dblp'] = recs[0] if len(pids) == 1 else None
        e['csr'] = None
        if not e['dblp'] and hp and len(csr_home.get(hp, [])) >= 1 and len(pid_of.get(hp, ())) == 1:
            row = csr_home[hp][0]
            e['csr'] = dict(pid=next(iter(pid_of[hp])), sha256=csr_sha, quote=f"{row['name']},{row['affiliation']},{row['homepage']}")
        e['csrname'] = None
        if not e['dblp'] and not e['csr'] and e['key'] not in dup_keys and len(by.get(e['key'], [])) <= 1 and re.fullmatch(r'[\u4e00-\u9fff]{2,4}', e['key']):
            from pypinyin import lazy_pinyin
            py = ''.join(lazy_pinyin(e['key'])).lower()
            if py in csr_name and csr_name[py] == e['key']:
                nm_, pid_ = next(iter(full[py]))
                row_ = csr_rows.get(nm_) or next((r for r in csr_rows.values() if r['name'] == re.sub(r'\s\d{4}$', '', nm_)), None)
                if row_:
                    e['csrname'] = dict(pid='https://dblp.org/pid/' + pid_, sha256=csr_sha, quote=f"{row_['name']},{row_['affiliation']},{row_['homepage']}", pinyin=py, csr_name=nm_)
        if e['dblp'] or e['csr'] or e['csrname']:
            plan['identity'].append(e['name'])
    print(json.dumps(dict(listed=len(ents), included=len(inc), basis_records=len(plan['basis']), additions=len(plan['additions']), held=len(plan['held']),
                          dblp_anchored=len(plan['identity']), csrname_candidates=len(csr_name), csrname_matched=sum(1 for z in inc if z.get('csrname')), held_detail=plan['held'][:30]), ensure_ascii=False))
    if not write:
        return plan, ents
    rev = dict(reviewed_by=WHO, reviewed_on=TODAY)
    ov_path = P.data_w('census-overrides-school.json', key)
    ov = json.loads(ov_path.read_text()) if ov_path.exists() else {}
    basis, adds = [], []
    import stage_gate as G
    for e in inc:
        if e['skip']:
            continue
        sha, flat, unit = srcs[e['url']]
        role = f"doctoral supervisor (博士生导师), {' / '.join(e['sections'])}" if key == 'hit' else '博士生导师 (doctoral supervisor)'
        why = ('The official department list of doctoral supervisors (博士生导师) names this person under its doctoral-supervisor heading, not as an adjunct (兼职). '
               'It supports the PI role (advises PhD students) and a 2026 appointment only; the printed list gives no rank, no earlier appointment year and no identity.')
        x = e['census']
        name = x['name'] if x else e['name']
        ev = dict(url=e['url'], sha256=sha, quote=e['quote'], observed=TODAY, role=role)
        if x:
            basis.append(dict(pi=name, kind='advises_phd', **ev, subject_evidence=dict(url=e['url'], sha256=sha, quote=e['quote']), **rev, why=why))
        else:
            slug = re.sub(r'[^a-z0-9]+', '-', e['key'].lower()) if e['key'].isascii() else 'u' + __import__('hashlib').sha1(e['key'].encode()).hexdigest()[:16]
            adds.append(dict(name=e['name'], aliases=_aliases(e.get('dblp') or e.get('csr') or e.get('csrname')) if (e.get('dblp') or e.get('csr') or e.get('csrname')) else [], collection_person_id=f'{key}_fac_{slug}', dblp=[(e.get('dblp') or e.get('csr') or e.get('csrname'))['pid']] if (e.get('dblp') or e.get('csr') or e.get('csrname')) else [], rank='other',
                             title_as_listed='博士生导师', departments=[unit], listed_in=[unit], years_listed=[int(TODAY[:4])], ranks_by_year={TODAY[:4]: ['other']},
                             sources=[dict(url=e['url'], sha256=sha, quote=e['quote'], kind=f'dept_supervisor_list:{unit}', observed=TODAY, rank_as_listed='博士生导师', rank='other')],
                             profile_url=e['href'], is_pi=True, pi_basis=dict(kind='advises_phd', **ev), lab_units=[], added='cn_rank_admit_' + TODAY.replace('-', '')))
        if e.get('csrname') and not e.get('csr') and not e.get('dblp'):
            d = e['csrname']
            o = ov.setdefault(name, {})
            o.update(no_identity=False, dblp=[d['pid']], aliases=_aliases(d), alias_evidence='the Latin name form of the identity-bound DBLP person (identity_resolution evidence); lets the builder keep the DBLP id past its Han-vs-Latin name-conflict check', **rev,
                     identity_resolution=dict(decision='csrankings_unique_fullname_roster', confidence='medium', reviewed=TODAY,
                                              basis='Owner ruling D-0004 (2026-11-18): a CSRankings entry plus a UNIQUE full-name match in the official roster. The pinyin of the roster name equals the CSRankings name (either order); exactly one roster/census Han name has that pinyin and exactly one CSRankings entry of the school has it; the entry maps to one DBLP person. Same-name collisions are held. Medium confidence; covered by the 50-row identity audit.',
                                              evidence=[dict(url=e['url'], sha256=sha, quote=e['quote']), dict(url=CSR_URL, sha256=d['sha256'], quote=d['quote'], pinyin=d['pinyin']), dict(url=d['pid'], note='DBLP person of the CSRankings row (scratch/pi-recall-1118/recall.json)')]))
        elif e.get('csr'):
            d = e['csr']
            o = ov.setdefault(name, {})
            o.update(no_identity=False, dblp=[d['pid']], aliases=_aliases(d), alias_evidence='the Latin name form of the identity-bound DBLP person (identity_resolution evidence); lets the builder keep the DBLP id past its Han-vs-Latin name-conflict check', **rev,
                     identity_resolution=dict(decision='csrankings_homepage_url_binding', reviewed=TODAY,
                                              basis='The official department supervisor list links a homepage URL that is also the homepage of one CSRankings row (commit 5319eddd csrankings.csv); that row maps to one DBLP person. A URL equality, not a name match.',
                                              evidence=[dict(url=e['url'], sha256=sha, quote=e['quote'], homepage=e['href']),
                                                        dict(url=CSR_URL, sha256=d['sha256'], quote=d['quote']), dict(url=d['pid'], note='DBLP person of the CSRankings row (scratch/pi-recall-1118/recall.json)')]))
        elif e.get('dblp'):
            d = e['dblp']
            o = ov.setdefault(name, {})
            o.update(no_identity=False, dblp=[d['pid']], aliases=_aliases(d), alias_evidence='the Latin name form of the identity-bound DBLP person (identity_resolution evidence); lets the builder keep the DBLP id past its Han-vs-Latin name-conflict check', **rev,
                     identity_resolution=dict(decision='verified_source_owned_dblp', reviewed=TODAY,
                                              basis='The official department supervisor list links the homepage that DBLP lists as this person\'s own <url>; exactly one non-disambiguation DBLP record lists it. No name matching.',
                                              evidence=[dict(url=e['url'], sha256=sha, quote=e['quote'], homepage=e['href']),
                                                        dict(url=d['pid'], sha256=d['sha256'], quote=next((u for u in d['urls'] if nurl(u) == nurl(e['href'])), e['href']))]))
        if x:  # years between the first and last listing that no capture covers: reviewed as unproven (R-PAP-01), so the window is the listed years
            gaps = [y for y in G.span_gaps(x) if y not in G.proven_years(key, name)]
            if gaps:
                o = ov.setdefault(name, {})
                o.update(unproven_years=gaps, why_unproven=(
                    f"Years {gaps[0]}-{gaps[-1]} have no stored department listing: the stage-1 capture plan (listings/{key}/raw/captures.sqlite plan) records the slots tried, "
                    'each with its Wayback and live attempts, and no accepted capture covers them. They prove nothing for or against an appointment (R-PAP-01); no papers are placed in them.'),
                    **rev)
    out_b = P.data_w('pi-basis-evidence.json', key)
    old = json.loads(out_b.read_text()) if out_b.exists() else []
    keep = [r for r in old if r['pi'] not in {b['pi'] for b in basis}]
    out_b.write_text(json.dumps(keep + basis, indent=1, ensure_ascii=False) + '\n')
    out_a = P.data_w('census-additions.json', key)
    old = json.loads(out_a.read_text()) if out_a.exists() else []
    keep = [r for r in old if r['name'] not in {a['name'] for a in adds}]
    out_a.write_text(json.dumps(keep + adds, indent=1, ensure_ascii=False) + '\n')
    ov_path.write_text(json.dumps(ov, indent=1, ensure_ascii=False) + '\n')
    CO.section(key)
    print(json.dumps(dict(wrote=dict(basis=len(basis), additions=len(adds), overrides=len(ov)))))
    return plan, ents


if __name__ == '__main__':
    k, cmd = sys.argv[1], sys.argv[2]
    if cmd == 'fetch':
        fetch(k)
    else:
        cache = sys.argv[sys.argv.index('--dblp') + 1] if '--dblp' in sys.argv else None
        a = sys.argv
        run(k, write=cmd == 'write', dblp_cache=cache, csr=a[a.index('--csr') + 1] if '--csr' in a else None, recall=a[a.index('--recall') + 1] if '--recall' in a else None)
