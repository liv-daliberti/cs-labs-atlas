"""Targeted, resumable student-source discovery; proposals only, never reviewed inputs.

Run through the isolated labpage_students_school.py entry point:
  ... sources SCHOOL --seeds sources.json --out DIR [--hierarchy H] [--max-fetches 40 | --offline]

Seeds are a JSON list with url and kind (defense_index, defense, gatsby_team, lab_people).
Defense indexes follow only same-host dissertation/PhD defense links and pagination on
the exact index path. Gatsby page-data is the public data used by the site's team tabs;
categories and biographies are retained for review, not treated as individual advising.
Every successful page remains in school_web's hashed capture store. No Wayback requests,
search endpoints, APIs requiring credentials, or automatic acceptance are performed.
"""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import re
import urllib.parse as U
import zlib
from pathlib import Path

from bs4 import BeautifulSoup

import atlas_paths as P
import school_web as W
from pihier.names import Name

DEFENSE = re.compile(r'(?:ph\.?\s*d\.?\s*)?(?:dissertation\s+)?defen[cs]e\s*[-–—:]\s*(.+)', re.I)
ADVISER = re.compile(r'\b(?:co[- ]?)?advis[oe]rs?\b', re.I)


def tidy(s):
    return ' '.join(s.split())


def index_links(body, url):
    """Do not turn a department index into an unrestricted university crawl."""
    origin = U.urlsplit(url)
    out = {}
    for a in BeautifulSoup(body, 'lxml').select('a[href]'):
        target, _ = U.urldefrag(U.urljoin(url, a['href']))
        parsed = U.urlsplit(target)
        if parsed.scheme != 'https' or parsed.netloc != origin.netloc:
            continue
        if parsed.path == origin.path and re.fullmatch(r'page=\d+', parsed.query):
            out[target] = 'defense_index'
        elif re.search(r'/event/\d{4}/\d{2}/\d{2}/', parsed.path) and 'defense' in parsed.path.lower():
            out[target] = 'defense'
    return [{'url': u, 'kind': kind} for u, kind in out.items()]


def defense_rows(body, url, sha, pis, today):
    """Explicit adviser labels only: committee membership/chair alone is insufficient."""
    soup = BeautifulSoup(body, 'lxml')
    heading = soup.find('h1')
    title = tidy(heading.get_text(' ', strip=True)) if heading else ''
    match = DEFENSE.fullmatch(title.replace('Ph.D. ', '', 1))
    date_match = re.search(r'/event/(\d{4})/(\d{2})/(\d{2})/', U.urlsplit(url).path)
    if not match or not date_match:
        return [], 'unrecognized_title_or_date'
    try:
        date = dt.date(*map(int, date_match.groups()))
    except ValueError:
        return [], 'invalid_date'
    if date > today:
        return [], 'future_announcement'
    if not 2016 <= date.year <= 2026:
        return [], 'outside_window'
    name = match.group(1).strip()
    lines = [tidy(s) for s in soup.get_text('\n', strip=True).splitlines() if tidy(s)]
    advisors = []
    for i, line in enumerate(lines):
        m = ADVISER.search(line)
        if not m:
            continue
        # ECE: 'Dr. Name, ECE, Chair, Advisor'; also 'Advisor: Dr. Name'.
        prefix, suffix = line[:m.start()].strip(' :,;-'), line[m.end():].strip(' :,;-')
        separate = not prefix and not suffix and i + 1 < len(lines)
        if separate:
            suffix = lines[i + 1]
        raw_name = suffix if not prefix else prefix.split(',')[0]
        raw_name = re.sub(r'^(?:Dr\.?|Prof\.?|Professor)\s+', '', raw_name).strip()
        hits = [p['pi'] for p in pis if Name(p.get('names') or [p['pi']]).match(raw_name)]
        if len(hits) == 1:
            quote = line + ' ' + suffix if separate else line
            advisors.append((hits[0], quote))
    rows = []
    for pi, quote in dict(advisors).items():
        rows.append(dict(pi=pi, name=name, role='phd', years=[date.year, date.year],
                         years_basis='dated_defense_announcement', url=url, sha256=sha,
                         quote=title, host_quote=quote,
                         note='Explicit adviser on a defense announcement; no claim that the degree was awarded.',
                         review_status='unreviewed'))
    return rows, 'explicit_adviser' if rows else 'no_unique_explicit_adviser'


def rich_text(node):
    if isinstance(node, list):
        return ' '.join(rich_text(x) for x in node)
    if not isinstance(node, dict):
        return ''
    return node.get('value', '') if node.get('nodeType') == 'text' else rich_text(node.get('content', []))


def gatsby_rows(body, url, sha):
    """Read hidden tabs without turning faculty, visitors or affiliates into advisees."""
    data = json.loads(body)
    contents = data['result']['data']['contentfulKLabPage']['kLabContents']
    rows = []
    for i, person in enumerate(contents):
        categories = person.get('personCategory') or []
        if person.get('__typename') != 'ContentfulPersonItem' or not {'Students', 'Alumni'} & set(categories):
            continue
        bio = json.loads((person.get('biography') or {}).get('raw') or '{}')
        rows.append(dict(name=person['name'].strip(), categories=categories, biography=tidy(rich_text(bio)),
                         website=person.get('website'), url=url, sha256=sha,
                         source_pointer=f'/result/data/contentfulKLabPage/kLabContents/{i}',
                         review_status='unreviewed; membership, role, dates and adviser require review'))
    return rows


def collect(school, seeds, out, hierarchy, max_fetches=40, offline=False):
    c = W.con(school)
    pis = json.loads(P.hfile(hierarchy, 'pis.json', school).read_text())
    out.mkdir(parents=True, exist_ok=True)
    pending = list(seeds)
    seen, stopped, receipts, proposals = set(), set(), [], []
    fetched = 0
    today = dt.datetime.now(dt.timezone.utc).date()
    while pending:
        seed = pending.pop(0)
        url, kind = seed['url'], seed['kind']
        if url in seen:
            continue
        seen.add(url)
        parsed = U.urlsplit(url)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError(f'Invalid public HTTPS seed: {url}')
        if parsed.hostname == 'web.archive.org':
            raise ValueError('This collector uses live sources only.')
        if kind not in ('defense_index', 'defense', 'gatsby_team', 'lab_people'):
            raise ValueError(f'Unknown source kind: {kind}')
        row = c.execute('select status, sha256, raw_zlib, fetched_at from live where url=?', (url,)).fetchone()
        if row is None:
            if offline or fetched >= max_fetches or parsed.hostname in stopped:
                receipts.append(dict(url=url, kind=kind, result='pending'))
                continue
            # Serialize this pipeline's runs per host; school_web enforces robots and crawl delay.
            lock_dir = P.LOCKS / 'student-sources'
            lock_dir.mkdir(parents=True, exist_ok=True)
            lock = lock_dir / (hashlib.sha256(parsed.hostname.encode()).hexdigest() + '.lock')
            with lock.open('w') as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                result = W.live(c, url)
            fetched += 1
            if result is None:
                receipts.append(dict(url=url, kind=kind, result='robots_or_host_blocked'))
                continue
            row = c.execute('select status, sha256, raw_zlib, fetched_at from live where url=?', (url,)).fetchone()
        status, sha, compressed, at = row
        receipt = dict(url=url, kind=kind, status=status, sha256=sha, captured_at=at)
        receipts.append(receipt)
        if status != 200 or not compressed:
            receipt['result'] = 'http_or_capture_failure'
            if status in (403, 429, 999):
                stopped.add(parsed.hostname)
            continue
        body = zlib.decompress(compressed)
        if hashlib.sha256(body).hexdigest() != sha:
            raise ValueError(f'Capture hash mismatch: {url}')
        if kind == 'defense_index':
            children = index_links(body, url)
            pending.extend(children)
            receipt.update(result='index_parsed', discovered=len(children))
        elif kind == 'defense':
            rows, result = defense_rows(body, url, sha, pis, today)
            proposals.extend(rows)
            receipt.update(result=result, proposals=len(rows))
        elif kind == 'gatsby_team':
            try:
                rows = gatsby_rows(body, url, sha)
            except (ValueError, KeyError, TypeError) as e:
                receipt.update(result='unrecognized_roster_format', detail=str(e)[:200])
            else:
                proposals.extend(rows)
                receipt.update(result='tabbed_roster_parsed', proposals=len(rows))
        else:
            receipt['result'] = 'captured_for_manual_roster_review'
    result = dict(school=school, generated_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                  status='proposals_only', network_attempts=fetched, sources=receipts, proposals=proposals)
    dest = out / f'{school}-sources.json'
    tmp = dest.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    tmp.replace(dest)
    print(json.dumps(dict(school=school, network_attempts=fetched, sources=len(receipts), proposals=len(proposals), output=str(dest))))
    return result


def main(school, argv):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seeds', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--hierarchy', type=Path, default=P.HIERARCHY)
    p.add_argument('--max-fetches', type=int, default=40)
    p.add_argument('--offline', action='store_true')
    a = p.parse_args(argv)
    if a.max_fetches < 0:
        p.error('--max-fetches must be nonnegative')
    return collect(school, json.loads(a.seeds.read_text()), a.out, a.hierarchy, a.max_fetches, a.offline)
