"""Per-person website register: PI home / profile pages and student home pages, with where each URL was found.

Offline consolidation of pages the pipeline already captured (no network, no student or membership changes).
One row per (person, url); a person with no URL gets one row with url null and a specific reason.

  person_websites.py build <school>... [--out FILE]    -> reviewed/person-websites.json
  person_websites.py summary <school>...
  person_websites.py sample <school> [--seed N] [--n 30]    rows for the hand-check

kind        pi_home | pi_profile | group | student_home   (a lab's own site is in lab-websites.json; a PI's lab or home page is
            repeated here as pi_home / group so every PI has all three kinds in one file)
found_from  {kind: official_page|own_page, url, sha256, capture_url?, anchor?}: the page that links the URL. A URL counts only
            when an official page, or the person's own page, links it (a name pattern is never a source).
fetched     true only when a stored capture of the URL itself exists (sha256, status, fetched_at); otherwise false with a reason
            ('queued: ...' when the host can be read, 'host not fetchable (robots/login)' for Google Scholar, LinkedIn, X ...).
"""
import argparse
import html.parser
import json
import random
import re
import sqlite3
import sys
import unicodedata
import zlib
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import atlas_paths as P
from lab_websites import capture_stores

NOT_FETCHABLE = re.compile(r'(?:^|\.)(?:scholar\.google\.[a-z.]+|linkedin\.com|twitter\.com|x\.com|facebook\.com|instagram\.com|'
                           r'researchgate\.net|academia\.edu|orcid\.org|dblp\.org|mathgenealogy\.org|genealogy\.math\.ndsu\.nodak\.edu|'
                           r'academictree\.org|semanticscholar\.org)$', re.I)
NOT_A_SITE = re.compile(r'(?:^|\.)(?:github\.com|gitlab\.com|dl\.acm\.org|ieeexplore\.ieee\.org|arxiv\.org|doi\.org|youtube\.com|'
                        r'openreview\.net|wikipedia\.org|mailto|medium\.com|bsky\.app|mastodon\.[a-z.]+)$', re.I)
BANNED = re.compile(r'(?:^|\.)(?:deepblue\.lib\.umich\.edu|news\.umich\.edu|record\.umich\.edu)$', re.I)
REPOSITORY = re.compile(r'(?:repository|smartech|dspace|dissertations|proquest|etd|scholarworks|knowledge\.library|deepblue|'
                        r'escholarship|dataspace|digitalcommons|openscholar)', re.I)
WAYBACK = re.compile(r'^https?://web\.archive\.org/web/\d+[a-z_]*/(https?://.+)$', re.I)


def fold(s):
    s = unicodedata.normalize('NFKD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r'[^a-z0-9 ]+', ' ', s)


def name_key(s):
    t = fold(s).split()
    return (t[0], t[-1]) if len(t) >= 2 else None


def original(url):
    m = WAYBACK.match(url or '')
    return m.group(1) if m else url


class Anchors(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self._href, self._text, self._base = [], None, [], None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'base' and a.get('href'):
            self._base = a['href']
        if tag == 'a' and a.get('href'):
            self._href, self._text = a['href'], []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == 'a' and self._href is not None:
            self.links.append((self._href, ' '.join(''.join(self._text).split())))
            self._href = None


def page_anchors(raw, base):
    p = Anchors()
    try:
        p.feed(raw.decode('utf-8', 'replace'))
    except Exception:
        return []
    base = urljoin(base, p._base) if p._base else base
    out = []
    for h, t in p.links:
        try:
            out.append((urljoin(base, h), t))
        except ValueError:
            continue
    return out


def read_json(path, default=None):
    path = Path(path)
    return json.loads(path.read_text()) if path.exists() else default


def captures(school, fetched_store=False):
    """Every stored 200 HTML capture of the lab-page stores: (url, capture_url, sha256, fetched_at, bytes)."""
    seen = set()
    for path in capture_stores(school):
        if path.name.startswith('captures-') != fetched_store:
            continue
        con = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
        for url, cap, sha, at, blob in con.execute(
                "select url, capture_url, sha256, fetched_at, content from captures where status=200 and content is not null"):
            if 'robots.txt' in url or '/cdx/search' in url or (url, sha) in seen:
                continue
            seen.add((url, sha))
            try:
                raw = zlib.decompress(blob)
            except zlib.error:
                raw = blob
            yield url, cap, sha, at, raw


def home_row(person, lab, kind, url, found_from, cap=None, reason=None, role='pi'):
    host = urlsplit(url).hostname or ''
    row = dict(person=person, role=role, lab=lab, kind=kind, url=url, found_from=found_from)
    stored = (cap or {}).get(url)
    if BANNED.search(host):
        row.update(fetched=False, fetch_reason='host not used (owner-banned source)')
    elif NOT_FETCHABLE.search(host):
        row.update(fetched=False, fetch_reason='host not fetchable (robots/login)')
    elif stored:
        row.update(fetched=True, fetched_at=stored['at'], status=200, sha256=stored['sha256'])
    else:
        row.update(fetched=False, fetch_reason='queued: not fetched in this pass; read live where robots allows, else Wayback only')
    if reason:
        row['reason'] = reason
    return row


def build(school, labs_path=None):
    pis = read_json(P.data('pis.json', school), [])
    students = read_json(P.data('students.json', school), {})
    labs = {r['pi']: r for r in (read_json(labs_path or P.data('lab-websites.json', school), {}) or {}).get('labs', [])}
    cap_urls, pages = {}, []
    for url, cap, sha, at, raw in captures(school):
        cap_urls[url] = dict(sha256=sha, at=at)
        if cap:
            cap_urls.setdefault(original(cap), dict(sha256=sha, at=at))
        pages.append((url, cap, sha, at, raw))
    for url, cap, sha, at, raw in captures(school, fetched_store=True):   # pages person_fetch.py read live: fetch evidence only
        cap_urls[url] = dict(sha256=sha, at=at)
    rows = []
    # PIs: home page / lab group (from the lab register), official profile (school_profile check), reasons otherwise
    for p in pis:
        pi = p['pi']
        r = labs.get(pi) or {}
        profile = next((c for c in r.get('checks') or [] if c.get('source') == 'school_profile'
                        and c.get('result') in ('ok', 'ok_wayback') and c.get('url') and c.get('sha256')), None)
        if profile:
            lst = p.get('listings') or [{}]
            lst = ([x for x in lst if urlsplit(original(x.get('url') or '')).hostname == urlsplit(profile['url']).hostname] or lst)
            rows.append(dict(person=pi, role='pi', lab=pi, kind='pi_profile', url=profile['url'],
                             found_from=(dict(kind='official_page', url=lst[-1].get('url'), sha256=lst[-1].get('sha256'))
                                         if lst[-1].get('url') and lst[-1].get('sha256') else
                                         dict(kind='official_page', url=profile['url'], sha256=profile['sha256'],
                                              note='school profile cited by the PI evidence; no listing record')),
                             fetched=True, fetched_at=profile['at'], status=200, sha256=profile['sha256']))
        else:
            rows.append(dict(person=pi, role='pi', lab=pi, kind='pi_profile', url=None,
                             reason='no official faculty profile page found among the department listing links or the cached profile search'
                                    if r else 'no lab-websites record for this PI'))
        if r.get('url') and r.get('coverage') == 'website':
            official = (r.get('official_link_evidence') or [None])[0]
            if official:
                on = official.get('on')
                sha = official.get('source_sha256') or next((c.get('sha256') for c in r.get('checks') or []
                                                             if c.get('url') == on and c.get('sha256')), None) \
                    or (cap_urls.get(on) or {}).get('sha256')
                ff = dict(kind='official_page', url=on, sha256=sha,
                          anchor=official.get('anchor'), via=official.get('source'))
            else:
                src = next((c for c in r.get('checks') or [] if c.get('source') == (r.get('found_via') or '').replace('orcid_researcher_url', 'orcid_researcher_urls')
                            and c.get('result') == 'listed'), {})
                ff = dict(kind='discovery', url=r.get('listed_on') or src.get('url') or r['url'],
                          sha256=src.get('sha256') or (None if (r.get('listed_on') or src.get('url')) else r.get('sha256')),
                          via=r.get('found_via'),
                          note='listed on the PI\'s DBLP person record / ORCID researcher URLs (the dump, never dblp.org); the page was '
                               'captured and names the PI (url is the page itself when no linking record survives); '
                               'no official school page link recorded yet')
            kind = 'group' if r.get('kind') == 'lab_site' else 'pi_home'
            row = home_row(pi, pi, kind, r['url'], ff, cap_urls)
            if r.get('sha256') and not row['fetched'] and not NOT_FETCHABLE.search(urlsplit(r['url']).hostname or ''):
                row.update(fetched=True, status=200, sha256=r['sha256'], fetched_at=r.get('checked_at'))
                row.pop('fetch_reason', None)
            rows.append(row)
        else:
            rows.append(dict(person=pi, role='pi', lab=pi, kind='pi_home', url=None,
                             reason=(r.get('reason') or 'no lab-websites record for this PI')))
    # Students: anchors on stored lab pages whose text is the student's name, else the student's own page in a relation source
    by_key = {}
    for pi, lst in students.items():
        for s in lst:
            k = name_key(s['name'])
            if k:
                by_key.setdefault(k, []).append((pi, s))
    found = {}
    for url, cap, sha, at, raw in pages:
        base = original(cap) if cap else url
        host = urlsplit(base).hostname or ''
        if BANNED.search(host):
            continue
        for href, text in page_anchors(raw, base):
            k = name_key(text)
            if not k or k not in by_key or len(fold(text).split()) > 4:
                continue
            h = urlsplit(href)
            if h.scheme not in ('http', 'https') or NOT_A_SITE.search(h.hostname or '') or h.hostname == host:
                continue
            for pi, s in by_key[k]:
                if fold(s['name']).split()[0] != fold(text).split()[0]:
                    continue
                found.setdefault((pi, s['person'], href), dict(
                    s=s, pi=pi, ff=dict(kind='official_page' if host.endswith(('.edu', '.org')) else 'lab_page', url=base,
                                        sha256=sha, capture_url=cap, anchor=text)))
    for (pi, pid, href), v in found.items():
        rows.append(home_row(v['s']['name'], pi, 'student_home', href, v['ff'], cap_urls, role='student') | dict(person_id=pid))
    have = {(pi, pid) for (pi, pid, _h) in found}
    for pi, lst in students.items():
        for s in lst:
            if (pi, s['person']) in have:
                continue
            own = None
            toks = fold(s['name']).split()
            for rel in s.get('relations') or []:
                for src in rel.get('sources') or []:
                    u = src.get('url') or ''
                    h = urlsplit(u).hostname or ''
                    if (not u or REPOSITORY.search(h) or NOT_A_SITE.search(h) or NOT_FETCHABLE.search(h) or BANNED.search(h)
                            or WAYBACK.match(u) or h.endswith('gatech.edu') and 'faculty' in u):
                        continue
                    q = fold(src.get('quote'))
                    if toks and toks[0] in q and toks[-1] in q and len(re.findall(r'\bi am\b|\bmy (?:advisor|adviser)\b|\bmy research\b', q)):
                        own = (u, src)
                        break
                if own:
                    break
            if own:
                u, src = own
                rows.append(home_row(s['name'], pi, 'student_home', u, dict(kind='own_page', url=u, sha256=src.get('sha256')),
                                     cap_urls, role='student') | dict(person_id=s['person']))
            else:
                rows.append(dict(person=s['name'], person_id=s['person'], role='student', lab=pi, kind='student_home', url=None,
                                 reason='student listed without a link on any stored official or lab page; no page found linking to them '
                                        '(searched: stored lab people/alumni pages and the student\'s relation sources; no name-pattern guesses)'))
    annotate(rows, school, labs_path)
    return dict(school=school, tool='tools/person_websites.py', source='lab-websites.json, labpage-audit-captures.sqlite, students.json',
                review_status='automatic', rows=rows)


FOUND_KINDS = (('dblp_person_url', 'dblp_homepage'), ('orcid', 'orcid'), ('prior_labpage_pass', 'prior_pass'))


def found_kind(row):
    ff = row.get('found_from') or {}
    if ff.get('kind') == 'discovery':
        via = ff.get('via') or ''
        return next((k for prefix, k in FOUND_KINDS if via.startswith(prefix)), 'prior_pass')
    return ff.get('kind') or 'official_page'


def annotate(rows, school, near=None):
    """found_from_kind for every URL row; verified = the fetched page names the person (first and last name). Fetch results
    from tools/person_fetch.py that were not a 200 give the unfetched row its specific reason."""
    from person_fetch import DIR, names_person
    shas = {r['sha256'] for r in rows if r.get('url') and r.get('sha256')}
    text = {}
    for path in capture_stores(school):
        con = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
        for sha in list(shas - set(text)):
            row = con.execute("select content from captures where sha256=? and content is not null limit 1", (sha,)).fetchone()
            if row:
                try:
                    text[sha] = zlib.decompress(row[0])
                except zlib.error:
                    text[sha] = row[0]
    failed, got = {}, {}
    res_path = DIR / f'fetched-{school}.jsonl'
    if res_path.exists():
        for line in res_path.open():
            x = json.loads(line)   # the latest line per URL counts (a redirect re-fetch follows the first attempt)
            got[x['url']] = x
        failed = {u: x for u, x in got.items() if x.get('status') != 200}
        sha_needed = {x['sha256'] for u, x in got.items() if x.get('status') == 200 and x.get('sha256')} - set(text)
        for path in capture_stores(school):
            if not sha_needed:
                break
            con = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
            for sha in list(sha_needed):
                row = con.execute("select content from captures where sha256=? and content is not null limit 1", (sha,)).fetchone()
                if row:
                    try:
                        text[sha] = zlib.decompress(row[0])
                    except zlib.error:
                        text[sha] = row[0]
                    sha_needed.discard(sha)
    from lab_websites import website_review
    from person_fetch import last_name_on_page, plausible_owner
    review = website_review(school, near)
    for r in rows:
        if not r.get('url'):
            continue
        rv = review.get((r['person'], r['url']))
        x = got.get(r['url'])
        if x and x.get('status') == 200 and not r.get('fetched') and x.get('sha256'):
            r.update(fetched=True, status=200, sha256=x['sha256'], fetched_at=x['at'])
            r.pop('fetch_reason', None)
            if x.get('redirect_hops'):
                r['redirected_to'] = x['final_url']
        r['found_from_kind'] = found_kind(r)
        body = text.get(r.get('sha256')) if r.get('fetched') else None
        if rv and rv['decision'] == 'verified':
            r['verified'], r['verified_by'], r['verification_reason'] = True, 'hand_review', rv['reason']
            continue
        if rv and rv['decision'] == 'rejected':
            r.update(rejected_url=r['url'], url=None, fetched=False, reason=rv['reason'] + ' (hand review): ' + r['url'] + ' rejected as not this person\'s website')
            for k in ('status', 'sha256', 'fetched_at', 'fetch_reason', 'found_from_kind', 'verified', 'redirected_to'):
                r.pop(k, None)
            continue
        if rv and rv['decision'] == 'unresolved':
            r['verified'], r['unverified_reason'] = False, rv['reason']
            continue
        if body is not None:
            r['verified'], q = names_person(body, r['person'])
            if q:
                r['verification_quote'] = q
            if not r['verified']:
                if r['role'] == 'student' and not last_name_on_page(body, r['person']) and not plausible_owner(r.get('redirected_to') or r['url'], r['person']):
                    # clear mismatch: the page does not name the person and the address does not either. Never shown as the person's site.
                    r.update(rejected_url=r['url'], url=None, fetched=False,
                             reason=f"fetched page does not name {r['person']} (no surname on the page, none in the address): "
                                    f"{r['url']} rejected as not this person's website")
                    for k in ('status', 'sha256', 'fetched_at', 'fetch_reason', 'found_from_kind', 'verified', 'redirected_to'):
                        r.pop(k, None)
                    continue
                r['unverified_reason'] = 'fetched page does not carry the full name' + (' (surname present)' if last_name_on_page(body, r['person']) else ' (address names the person)')
        else:
            r['verified'] = False
            r['unverified_reason'] = r.get('fetch_reason') or 'page not fetched'
        if x and not r.get('fetched'):
            err = x.get('error') or f"HTTP {x.get('status')}"
            if any(k in err for k in ('robots', 'off-limits')):
                r['fetch_reason'] = f'not fetched: robots.txt disallows it, or the host names an AI agent or is a banned source ({err})'
            elif any(k in err for k in ('challenge', 'host-challenged', 'previous-host-refusal', 'wayback-only', '403', '429')):
                r['fetch_reason'] = f'read via Wayback only (shared low lane): {err}'
            else:
                r['fetch_reason'] = f'live fetch failed: {err}'
            r['fetch_attempted_at'] = x['at']
            r['unverified_reason'] = r['fetch_reason']


def counts(doc):
    out = dict(rows=len(doc['rows']))
    for role in ('pi', 'student'):
        for kind in sorted({r['kind'] for r in doc['rows'] if r['role'] == role}):
            sel = [r for r in doc['rows'] if r['role'] == role and r['kind'] == kind]
            out[f'{role}:{kind}'] = dict(url=sum(1 for r in sel if r['url']), reason=sum(1 for r in sel if not r['url']),
                                         not_fetchable=sum(1 for r in sel if r['url'] and not r['fetched'] and 'not fetchable' in r.get('fetch_reason', '')),
                                         queued=sum(1 for r in sel if r['url'] and not r['fetched'] and r.get('fetch_reason', '').startswith('queued')),
                                         fetched=sum(1 for r in sel if r['url'] and r['fetched']),
                                         verified=sum(1 for r in sel if r.get('verified')),
                                         official=sum(1 for r in sel if r['url'] and r.get('found_from_kind') == 'official_page'),
                                         non_official=sum(1 for r in sel if r['url'] and r.get('found_from_kind') != 'official_page'))
    return out


def gate(doc):
    """Rows the register may not hold: a URL without provenance, or a missing URL without a reason."""
    bad = []
    for r in doc['rows']:
        if r['url']:
            ff = r.get('found_from') or {}
            if not ff.get('url') or not (ff.get('sha256') or ff.get('kind') == 'discovery'):
                bad.append(f"{r['person']} {r['kind']} {r['url']}: found_from url/sha256 missing")
            if not r['fetched'] and not r.get('fetch_reason'):
                bad.append(f"{r['person']} {r['url']}: unfetched without a reason")
        elif not r.get('reason'):
            bad.append(f"{r['person']} {r['kind']}: no URL and no reason")
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('cmd', choices=['build', 'summary', 'sample', 'queue'])
    ap.add_argument('schools', nargs='+')
    ap.add_argument('--out')
    ap.add_argument('--labs', help='lab-websites.json to read (default: the data path)')
    ap.add_argument('--seed', type=int, default=20261108)
    ap.add_argument('--n', type=int, default=30)
    a = ap.parse_args()
    rc = 0
    for s in a.schools:
        doc = build(s, a.labs)
        bad = gate(doc)
        rc |= bool(bad)
        if a.cmd == 'build':
            out = Path(a.out) if a.out else P.data_w('person-websites.json', s)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
        if a.cmd == 'queue':
            from person_fetch import DIR
            labs = read_json(a.labs or P.data('lab-websites.json', s), {})['labs']
            DIR.mkdir(parents=True, exist_ok=True)
            with open(DIR / f'queue-{s}.jsonl', 'w') as f:
                for r in doc['rows']:
                    if r['url'] and not r['fetched'] and r.get('fetch_reason', '').startswith('queued'):
                        mode = 'wayback_only' if s == 'uchicago' and (urlsplit(r['url']).hostname or '').endswith('uchicago.edu') else 'live_if_robots_else_wayback'
                        f.write(json.dumps(dict(url=r['url'], person=r['person'], role=r['role'], kind=r['kind'], lab=r['lab'], mode=mode)) + '\n')
                for r in labs:
                    if r.get('coverage') == 'pending' and r.get('url'):
                        f.write(json.dumps(dict(url=r['url'], person=r['pi'], role='pi', kind='lab_pending', lab=r['pi'], gaps=r.get('evidence_gaps'),
                                                mode='live_if_robots_else_wayback')) + '\n')
        if a.cmd == 'sample':
            pool = [r for r in doc['rows'] if r['url']]
            for r in random.Random(a.seed).sample(pool, min(a.n, len(pool))):
                print(json.dumps(r, ensure_ascii=False))
        else:
            print(s, json.dumps(counts(doc)), 'gate_problems', len(bad))
        for b in bad[:5]:
            print('  !', b, file=sys.stderr)
    return rc


if __name__ == '__main__':
    sys.exit(main())
