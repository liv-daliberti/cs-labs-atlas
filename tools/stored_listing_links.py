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


def run(school, src, out, report):
    doc = json.loads(Path(src).read_text())
    found = scan(doc, listing_captures(school))
    Path(out).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
    if report:
        Path(report).write_text(json.dumps(found, indent=1, ensure_ascii=False) + '\n')
    print(len(found), 'official links recorded from stored listing captures')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('school')
    ap.add_argument('--src', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--report')
    a = ap.parse_args()
    run(a.school, a.src, a.out, a.report)


if __name__ == '__main__':
    main()
