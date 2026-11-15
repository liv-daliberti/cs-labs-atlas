"""Official-link records from ALL stored department-listing captures of a school (no network, no archive.org fetch).

lab_websites.enrich_official_links reads only the one listing capture a register row cites. A school whose current listing is JS-built or
Cloudflare-challenged (Michigan CSE/ECE) still has older stored captures of the same listing whose PI cards carry a `Website` anchor. For every register
row that names a website but has no recorded official link, this scans the school's stored listing captures (hierarchy/<school>/raw/school-captures.sqlite,
table captures; page_url on a school-domain host) newest first and, where this PI's own named card holds an anchor to exactly the registered URL
(lab_websites.listing_link_context: never a page-wide match), appends a `department_listing_link` check carrying the capture's sha256, fetch time,
capture URL and the card quote, and sets official_link_status = recorded.

  stored_listing_links.py <school> --src <register.json> --out <register.json> [--report <json>]
"""
import argparse
import json
import re
import sqlite3
import unicodedata
import zlib
from pathlib import Path
from urllib.parse import urlsplit

import atlas_paths as P  # noqa: E402
import lab_websites as LW  # noqa: E402
import school_config as S  # noqa: E402


def domain_of(school):
    return (S.get(school).get('web') or {}).get('domains', [None])[0]


NOT_LISTING = re.compile(r'^(labpage|defense|gap:|profile:|homepage:|student-directory|.*-students$)')   # captures the stage-1 collector tagged by purpose, not as a department listing


def listing_captures(school):
    """[(page_url, capture_url, fetched_at, sha256, wayback_timestamp, html)] newest capture first: HTML people/faculty/directory captures that
    are a department's own listing, either on a host of the charter's departments/affiliated units, or tagged by the stage-1 collector with a
    department code on a school-domain host (never lab pages, homepages, profiles, defenses or student directories). A scheme-less stored
    page_url is read as http."""
    cfg = S.get(school)
    charter_hosts = {urlsplit(u['url']).hostname for u in (cfg.get('departments') or []) + (cfg.get('affiliated_units') or []) if u.get('url')}
    domain = domain_of(school)
    con = sqlite3.connect(f"file:{P.data('school-captures.sqlite', school)}?mode=ro", uri=True)
    out = []
    for page, dept, cap, fetched, sha, ts, blob in con.execute(
            "select page_url, department, capture_url, fetched_at, sha256, wayback_timestamp, raw_zlib from captures "
            "where http_status=200 and raw_zlib is not null and sha256 is not null and content_type like '%html%' order by wayback_timestamp desc"):
        if not re.search(r'/people|/faculty|/directory|/staff', page or ''):
            continue
        host = urlsplit(page if '://' in page else 'http://' + page).hostname or ''
        coded = bool(dept) and not NOT_LISTING.match(dept) and (host == domain or host.endswith('.' + domain))
        if host not in charter_hosts and not coded:
            continue
        try:
            html = zlib.decompress(blob).decode('utf-8', 'replace')
        except zlib.error:
            continue
        out.append((page, cap, fetched, sha, ts, html))
    return out


def well_formed(url):
    """One http(s) scheme and a dotted host: a registered URL such as 'http://http://https://x.github.io/' is a data error to fix first, not a link to certify."""
    p = urlsplit(url or '')
    return p.scheme in ('http', 'https') and '.' in (p.hostname or '') and '://' not in (p.netloc + p.path + p.query)


def scan(doc, caps):
    """Record a department_listing_link check on every website row whose registered URL is linked from that PI's own card in a stored capture."""
    found = {}
    for r in doc['labs']:
        if r.get('coverage') != 'website' or r.get('official_link_status') == 'recorded' or not r.get('url') or not well_formed(r['url']):
            continue
        target = LW.normalized_link(r['url'])
        needle = (target[0].removeprefix('www.') + target[1]).lower()
        surname = r['pi'].split()[-1].lower()
        for page, cap, fetched, sha, ts, html in caps:
            low = html.lower()
            if needle not in low or surname not in low:   # cheap prefilter; the card match below is the check
                continue
            m = LW.listing_link_context(html, page, target, r['pi'])
            if not m:
                continue
            check = dict(source='department_listing_link', url=r['url'], on=page, at=fetched, result='listed', anchor=m[1], linked_url=m[0],
                         source_sha256=sha, source_capture_url=cap, source_quote=m[2][:600], provenance='stored_listing_capture_scan', capture_timestamp=ts)
            r.setdefault('checks', []).append(check)
            r['official_link_status'] = 'recorded'
            r['official_link_evidence'] = [check]
            r['listed_on'] = page
            found[r['pi']] = dict(url=r['url'], on=page, capture=cap, ts=ts)
            break
    return found


def alias_rule(school):
    """The owner-approved host-alias sets of the school (reviewed/host-alias-rule.json), as a list of frozensets; none when the file is absent."""
    path = P.data('host-alias-rule.json', school)
    if not Path(path).exists():
        return []
    return [frozenset(h.lower() for h in group) for group in json.loads(Path(path).read_text()).get('host_alias_sets', [])]


def canon(url, aliases):
    """(alias-set id or host, path without trailing slash, query) so aliased hosts compare equal and nothing else does."""
    p = urlsplit(url if '://' in (url or '') else 'http://' + (url or ''))
    host = (p.hostname or '').lower()
    group = next((i for i, g in enumerate(aliases) if host in g), None)
    return (('alias', group) if group is not None else ('host', host)), p.path.rstrip('/'), p.query


def attach_aliased_captures(doc, rows, aliases):
    """rows: [(page_url, capture_url, fetched_at, sha256, html)] newest first. A website row missing its page capture hash gets one from a stored capture of the
    exact same path under an alias host, when that page names the PI; the capture is recorded as evidence with the alias page it came from."""
    from bs4 import BeautifulSoup
    found = {}
    for r in doc['labs']:
        if 'page_capture_hash_missing' not in (r.get('evidence_gaps') or []) or not r.get('url') or not well_formed(r['url']):
            continue
        want = canon(r['url'], aliases)
        if want[1] in ('', '/'):
            continue
        toks = re.findall(r'[a-z]+', unicodedata.normalize('NFKD', r['pi']).encode('ascii', 'ignore').decode().lower())
        for page, cap, fetched, sha, html in rows:
            if canon(page, aliases) != want:
                continue
            text = ' '.join(BeautifulSoup(html, 'html.parser').get_text(' ', strip=True).split())
            low = text.lower()
            if len(toks) < 2 or toks[0] not in low or toks[-1] not in low:
                continue
            i = low.find(toks[-1])
            r['sha256'], r['capture_fetched_at'] = sha, fetched
            r['evidence'] = dict(url=r['url'], sha256=sha, quote=text[max(0, i - 40):i + 80], capture_url=cap, source='stored_capture_alias', alias_page_url=page)
            r['evidence_gaps'] = [g for g in r['evidence_gaps'] if g != 'page_capture_hash_missing']
            if not r['evidence_gaps']:
                r['coverage'] = 'website'
            found[r['pi']] = dict(url=r['url'], alias_page=page, capture=cap, sha256=sha)
            break
    return found


def stored_pages(school):
    """[(page_url, capture_url, fetched_at, sha256, html)] newest first, every stored HTML 200 capture with a hash (for the alias attach)."""
    con = sqlite3.connect(f"file:{P.data('school-captures.sqlite', school)}?mode=ro", uri=True)
    out = []
    for page, cap, fetched, sha, blob in con.execute(
            "select page_url, capture_url, fetched_at, sha256, raw_zlib from captures where http_status=200 and raw_zlib is not null and sha256 is not null "
            "and content_type like '%html%' order by wayback_timestamp desc"):
        try:
            out.append((page or '', cap, fetched, sha, zlib.decompress(blob).decode('utf-8', 'replace')))
        except zlib.error:
            continue
    return out


def run(school, src, out, report, alias_only=False):
    doc = json.loads(Path(src).read_text())
    found = {}
    aliases = alias_rule(school)
    if aliases:
        found.update({k: dict(v, how='alias_capture') for k, v in attach_aliased_captures(doc, stored_pages(school), aliases).items()})
    if not alias_only:
        found.update(scan(doc, listing_captures(school)))
    Path(out).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
    if report:
        Path(report).write_text(json.dumps(found, indent=1, ensure_ascii=False) + '\n')
    print(len(found), 'rows updated from stored captures (alias attach and official-link records)')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('school')
    ap.add_argument('--src', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--report')
    ap.add_argument('--alias-only', action='store_true', help='only attach alias-host captures; record no official links')
    a = ap.parse_args()
    run(a.school, a.src, a.out, a.report, a.alias_only)


if __name__ == '__main__':
    main()
