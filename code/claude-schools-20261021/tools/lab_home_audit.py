"""Audit every live PI lab plus every row of the PI inventory, without changing inputs.

Writes CSVs, source hashes, and a JSON summary to --out. A recorded assignment is
not a fresh verification of its original web capture. Missing, ambiguous, and
conflicting decisions remain explicit; name-only fuzzy matches are never used.
"""
import argparse
import collections
import csv
import gzip
import datetime as dt
import hashlib
import io
import json
import re
import sqlite3
import zlib
import unicodedata
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit

from bs4 import BeautifulSoup

import atlas_paths as P
import home_department_registry as HOME
import school_config as S


def sequence(doc):
    return doc if isinstance(doc, list) else (doc or {}).get('faculty', [])


def normalize(unit, cfg, aliases=None):
    unit = (aliases or {}).get(unit, unit) or ''
    codes = {r['code']: r['name'] for r in S.listing_units(cfg)}
    unit = codes.get(unit, unit)
    unit = re.sub(r'^Department of\s+', '', unit).strip()
    for canonical, pattern in (S.field(cfg, 'census.home_units') or {}).items():
        if re.search(pattern, unit, re.I):
            return canonical
    return unit


def assess(row, shared, local, cfg, rules):
    issues = []
    if not row:
        return ['missing_home']
    if row.get('status') != 'accepted' or not row.get('home_department'):
        issues.append('held_home')
    if not HOME.valid_evidence(row):
        issues.append('incomplete_evidence')
    if not row.get('home_basis'):
        issues.append('home_basis_unrecorded')
    if row.get('home_basis') == 'primary_unresolved' or row.get('primary_unresolved'):
        issues.append('primary_unresolved')
    aliases = rules.get('aliases') or {}
    norm = lambda u: normalize(u, cfg, aliases)
    if shared and local and shared.get('status') == local.get('status') == 'accepted' \
            and norm(shared.get('home_department')) != norm(local.get('home_department')):
        if not (local.get('home_basis') == 'primary_stated' and HOME.valid_evidence(local)):
            issues.append('shared_local_conflict')
    centers = {norm(c) for c in list(S.field(cfg, 'census.center_units') or []) + list(rules.get('centers') or [])}
    if norm(row.get('home_department')) in centers and not row.get('no_academic_department'):
        issues.append('center_instead_of_department')
    if 'also listed by' in (row.get('note') or '') and not row.get('home_basis'):
        issues.append('multiple_listings_primary_unreviewed')
    return issues


def quote_names_pi(quote, names):
    """Conservative triage: exact full-name or explicit package alias in the quote.

    A failure requires review; it is never treated as proof of a different person.
    """
    def fold(value):
        value = ''.join(c for c in unicodedata.normalize('NFKD', value or '') if not unicodedata.combining(c))
        return ' '.join(''.join(c.casefold() if c.isalnum() else ' ' for c in value).split())
    text = ' ' + fold(quote) + ' '
    variants = {fold(name) for name in names if name}
    for name in names:
        raw = re.findall(r'[^\W_]+', name or '', re.UNICODE)
        words = fold(name).split()
        if len(raw) > 1 and len(raw[0]) > 1 and raw[0].isupper() and any(any(c.islower() for c in w) for w in raw[1:]):
            variants.add(' '.join(words[1:] + words[:1]))
    variants.update(' '.join(t for t in name.split() if not (len(t) == 1 and t.isascii())) for name in list(variants))
    if any(name and ' ' + name + ' ' in text for name in variants):
        return True
    # Engineering directories explicitly print an uppercase family name first.
    # Rotate only that complete name field; never permute arbitrary quote words
    # or substitute initials for a full given name.
    raw_words = re.findall(r'[^\W_]+', quote or '', re.UNICODE)
    words = fold(quote).split()
    if len(raw_words) > 1 and len(raw_words[0]) > 1 and raw_words[0].isupper() and any(any(c.islower() for c in w) for w in raw_words[1:]):
        rotated = words[1:] + words[:1]
        options = {' '.join(rotated), ' '.join(t for t in rotated if not (len(t) == 1 and t.isascii()))}
        return bool(options & variants)
    return False


def homepage_key(url):
    """Normalize presentation differences without dropping identity parameters."""
    url = re.sub(r'^https?://web\.archive\.org/web/\d+(?:id_)?/', '', str(url or ''))
    parsed = urlsplit(url)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.fragment:
        return None
    host = parsed.hostname.lower().removeprefix('www.')
    if parsed.port and parsed.port not in {80, 443}:
        host += ':' + str(parsed.port)
    path = re.sub(r'%7[eE]', '~', parsed.path)
    if host.startswith('faculty.'):
        match = re.fullmatch(r'/([^/.]+)/(?:zh_CN|en)/index\.htm', path)
        if match:
            path = '/' + match[1]
    path = re.sub(r'/index\.(?:html?|php)$', '/', path).rstrip('/') or '/'
    return host, path, urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True)))


def homepage_owners(persons):
    owners = collections.defaultdict(set)
    for person in persons:
        for url in person.get('urls') or []:
            key = homepage_key(url)
            if key:
                owners[key].add(person['pid'])
    return owners


def captured_profile_subject(evidence, school, receipts):
    """Read the subject and its labelled personal links from verified originals.

    Faculty-role evidence is not an identity binding: a record may cite another
    professor's page. The caller must additionally check a person-specific link.
    """
    url, sha = evidence.get('url'), evidence.get('sha256')
    if not url or not re.fullmatch(r'[0-9a-f]{64}', str(sha or '')):
        return dict(verified=False)
    key = (url, sha)
    if key in receipts:
        cached = receipts[key]
        return dict(cached, verified=bool(cached.get('verified_body') and evidence.get('quote')
                                         and evidence['quote'] in cached.get('_text', '')))
    for filename in ('school-captures.sqlite', 'listings-captures.sqlite'):
        path = P.data(filename, school)
        if not path.exists():
            continue
        with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
            for query in ('select http_status,sha256,raw_zlib from captures where capture_url=?',
                          'select status,sha256,raw_zlib from live where url=?'):
                try:
                    row = db.execute(query, (url,)).fetchone()
                except sqlite3.OperationalError:
                    continue
                if not row or row[0] != 200 or row[1] != sha or not row[2]:
                    continue
                try:
                    raw = zlib.decompress(row[2])
                    if hashlib.sha256(raw).hexdigest() != sha:
                        continue
                    body = gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw
                    soup = BeautifulSoup(body, 'html.parser')
                except (ValueError, OSError, zlib.error):
                    continue
                for node in soup(['script', 'style', 'noscript', 'template']):
                    node.decompose()
                flat = lambda node: ' '.join(node.get_text(' ', strip=True).split())
                title = flat(soup.title) if soup.title else ''
                text = flat(soup)
                subjects = re.findall(r'(?:姓名|姓\s*名)\s*[:：]\s*([\u3400-\u9fff·]{2,6})(?=\s|[，,:：;；]|$)', text)
                for piece in re.split(r'[-_|—–]', title):
                    value = ''.join(piece.split())
                    value = re.sub(r'(?:副教授|教授|研究员|院士)(?:个人主页|简介)?$', '', value)
                    generic = re.search(r'大学|科大|学院|学部|系$|科研|师资|导师|教授|主页|首页|简介|新闻|正高|副高', value)
                    if re.fullmatch(r'[\u3400-\u9fff·]{2,6}', value) and not generic:
                        subjects.append(value)
                subjects = {''.join(v.split()) for v in subjects}
                subject = next(iter(subjects)) if len(subjects) == 1 else None
                label = r'(?:个人主页|个人网站|Personal\s+(?:Home\s*Page|Website)|Home\s*Page|ORCID)'
                links = []
                for link in soup.find_all('a', href=True):
                    before = ' '.join(flat(n) if getattr(n, 'name', None) else str(n)
                                      for n in reversed(list(link.previous_siblings)))[-200:]
                    named_link = re.fullmatch(label + r'\s*[:：]?', flat(link), re.I)
                    labelled_value = re.search(label + r'\s*[:：]\s*$', before, re.I)
                    if named_link or labelled_value:
                        target = urljoin(re.sub(r'^https?://web\.archive\.org/web/\d+(?:id_)?/', '', url), link['href'])
                        if homepage_key(target):
                            links.append(target)
                cached = dict(url=url, sha256=sha, capture_file=str(path), title=title, subject=subject,
                              headers=[flat(n) for n in ([soup.title] + list(soup.find_all(['h1', 'h2', 'h3'])))
                                       if n and 1 < len(flat(n)) < 180],
                              personal_links=sorted(set(links)), original_bytes=len(raw), verified_body=True, _text=text)
                receipts[key] = cached
                return dict(cached, verified=bool(evidence.get('quote') and evidence['quote'] in text))
    receipts[key] = dict(url=url, sha256=sha, verified_body=False, error='No hash-matched HTTP-200 original')
    return dict(verified=False)


def accepted_profile_subject(evidence, pi, decisions, profile, persons, owners):
    """Verify declared aliases or unique DBLP homepage links, never role pointers."""
    binding = evidence.get('subject_binding') or {}
    subject = evidence.get('subject_name')
    if (not isinstance(binding, dict) or not subject or not profile.get('verified')
            or binding.get('decision_name') != pi.get('pi')
            or not quote_names_pi(evidence.get('quote'), [subject])):
        return False
    kind = binding.get('kind')
    if kind == 'accepted_reviewed_alias':
        if binding.get('person_id') not in ((pi.get('personIds') or []) + (pi.get('dblp') or [])):
            return False
        key = (evidence.get('url'), evidence.get('sha256'))
        for decision in decisions:
            known = decision.get('dblp') or []
            known = [known] if isinstance(known, str) else known
            known = set(known) | {decision.get('source_id')}
            receipt = decision.get('receipt') or {}
            if (decision.get('decision') == 'accepted' and decision.get('name') == pi.get('pi')
                    and decision.get('cjk_name') == subject and set(pi.get('dblp') or []) & known
                    and key == (receipt.get('url'), receipt.get('sha256'))):
                return True
        return False
    if kind != 'dblp_homepage' or binding.get('person_id') not in (pi.get('dblp') or []):
        return False
    chinese_subject = ''.join(subject.split()) == (profile.get('subject') or '')
    english_subject = (quote_names_pi(subject, [pi.get('pi')])
                       and any(quote_names_pi(h, [subject]) for h in profile.get('headers') or []))
    if not (chinese_subject or english_subject):
        return False
    pid, homepage = binding['person_id'], binding.get('homepage')
    home_key = homepage_key(homepage)
    if not home_key or owners.get(home_key) != {pid}:
        return False
    person = next((p for p in persons if p.get('pid') == pid), None)
    if not person or home_key not in {homepage_key(u) for u in person.get('urls') or []}:
        return False
    if homepage_key(evidence.get('url')) == home_key:
        return True
    return home_key in {homepage_key(u) for u in profile.get('personal_links') or []}


def proposed_from_listing(pi, cfg):
    """Suggest only a single charter department with a same-unit faculty listing.

    Proposals never become reviewed decisions or alter consumer results.
    """
    codes = pi.get('departments') or []
    deps = {d['code']: d['name'] for d in cfg.get('departments') or []}
    if len(codes) != 1 or codes[0] not in deps or pi.get('rank') in ('courtesy', 'affiliated_other_school'):
        return None
    evs = [s for s in pi.get('listings') or [] if s.get('kind') == 'dept_listing:' + codes[0]]
    evs = [s for s in evs if HOME.valid_evidence({'evidence': s})]
    if not evs:
        return None
    ev = max(evs, key=lambda s: (s.get('year') or 0, s.get('url') or ''))
    return dict(home_department=deps[codes[0]], evidence={k: ev[k] for k in ('url', 'sha256', 'quote')},
                basis='single_department_listing_requires_review')


def audit(inventory, out):
    manifest = {}
    profile_receipts = {}

    def read(path, default=None):
        path = Path(path)
        if not path.exists():
            return default
        before = path.stat()
        data = path.read_bytes()
        after = path.stat()
        if (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
            raise RuntimeError(f'input changed while reading: {path}')
        manifest[str(path)] = dict(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
        if path.suffix == '.csv':
            return list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))
        return json.loads(data)

    baseline = read(inventory, [])
    records = {(r['school'], r['pi']): dict(inventory=r, built=None, census=None) for r in baseline}
    shared = read(P.data('home-departments.json'), [])
    schools = sorted(set(r['school'] for r in baseline) | {d.name for d in P.HIERARCHY.iterdir()
                     if d.is_dir() and P.data('pis.json', d.name).exists()})
    results = []
    for school in schools:
        cfg = S.get(school)
        charter = Path(S.__file__).resolve().parents[1] / 'schools' / (school + '.toml')
        if charter.exists():
            b = charter.read_bytes()
            manifest[str(charter)] = dict(sha256=hashlib.sha256(b).hexdigest(), bytes=len(b))
        local = read(P.data('home-departments-school.json', school), [])
        sm = {r['name']: r for r in shared if r.get('school') == school}
        lm = {r['name']: r for r in local}
        merged = {r['name']: r for r in HOME.merge_rows(shared, local, school)}
        rules = read(P.HIERARCHY / school / 'reviewed/home-department-rules.json', {})
        pis = read(P.data('pis.json', school), [])
        for pi in pis:
            records.setdefault((school, pi['pi']), dict(inventory=None, built=None, census=None))['built'] = pi
        overrides = read(P.data('census-overrides-school.json', school), {})
        for filename in ('census-faculty.json', 'census-additions.json'):
            for c in sequence(read(P.data(filename, school), [])):
                if c.get('is_pi') and not (overrides.get(c['name']) or {}).get('exclude'):
                    records.setdefault((school, c['name']), dict(inventory=None, built=None, census=None))['census'] = c
        has_subject_bindings = any(e.get('subject_binding') for row in merged.values()
                                   for e in [row.get('evidence') or {}] + list(row.get('reviewed_home_evidence') or []))
        subject_decisions = (read(P.data('cs-related-review.json', school), {}).get('decisions') or []) if has_subject_bindings else []
        subject_persons = (read(P.data('dblp-affiliated.json', school), {}).get('persons') or []) if has_subject_bindings else []
        subject_owners = homepage_owners(subject_persons)
        for (s, name), item in sorted(records.items()):
            if s != school:
                continue
            r = merged.get(name)
            issues = assess(r, sm.get(name), lm.get(name), cfg, rules)
            pi = item['built'] or {}
            proposal = proposed_from_listing(pi, cfg) if not r else None
            evidence = (r or {}).get('evidence') or {}
            names = [name] + list(pi.get('names') or []) + list((item['census'] or {}).get('aliases') or [])
            sources = [evidence] + list((r or {}).get('reviewed_home_evidence') or [])
            literal_name = any(quote_names_pi(e.get('quote'), names) for e in sources) if r else None
            bindings = [e for e in sources if e.get('subject_binding')]
            checks = [accepted_profile_subject(e, pi, subject_decisions,
                                               captured_profile_subject(e, school, profile_receipts),
                                               subject_persons, subject_owners) for e in bindings]
            bound_name = any(checks)
            if checks and not all(checks):
                issues.append('subject_binding_requires_review')
            named = (literal_name or bound_name) if r else None
            if r and evidence.get('quote') and not named:
                issues.append('evidence_name_requires_review')
            results.append(dict(school=school, pi=name, live_built_lab=bool(item['built']),
                                current_census_pi=bool(item['census']), in_inventory=bool(item['inventory']),
                                inventory_status=(item['inventory'] or {}).get('inventory_status'),
                                home_department=normalize((r or {}).get('home_department'), cfg, rules.get('aliases')) or None,
                                home_department_as_recorded=(r or {}).get('home_department'),
                                home_status=(r or {}).get('status', 'missing'), home_basis=(r or {}).get('home_basis'),
                                primary_resolved=HOME.review(r)['primary_resolved'] and not issues,
                                also=(r or {}).get('also') or [], primary_unresolved=(r or {}).get('primary_unresolved') or [],
                                issues=issues, local_home=(lm.get(name) or {}).get('home_department'),
                                shared_home=(sm.get(name) or {}).get('home_department'),
                                shared_register_missing=name not in sm, evidence_url=evidence.get('url'),
                                evidence_names_pi=named,
                                evidence_subject_match=('literal_name' if literal_name else 'accepted_reviewed_subject' if bound_name else None),
                                evidence_sha256=evidence.get('sha256'), evidence_quote=evidence.get('quote'),
                                proposal=proposal, lab_name=(pi.get('lab') or {}).get('name'),
                                next_action=('Review captured listing proposal' if proposal else
                                             'Resolve appointment or source conflict using official faculty evidence' if issues else
                                             'Recorded assignment available; original capture has not been re-reviewed in this audit')))

    def csv_write(filename, rows):
        with (out / filename).open('w', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=list(results[0]))
            w.writeheader()
            for r in rows:
                w.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in r.items()})

    out.mkdir(parents=True, exist_ok=True)
    csv_write('all-labs-home-departments.csv', results)
    csv_write('home-department-followups.csv', [r for r in results if r['issues']])
    csv_write('uchicago-home-departments.csv', [r for r in results if r['school'] == 'uchicago'])
    counts = lambda rows: dict(records=len(rows), built_labs=sum(r['live_built_lab'] for r in rows),
                              recorded_accepted=sum(r['home_status'] == 'accepted' and bool(r['home_department']) for r in rows),
                              clear_recorded_home=sum(r['primary_resolved'] for r in rows),
                              needs_review=sum(bool(r['issues']) for r in rows),
                              issues=dict(collections.Counter(i for r in rows for i in r['issues'])))
    summary = dict(generated_at=dt.datetime.now(dt.timezone.utc).isoformat(), inventory=str(inventory),
                   definition='Recorded evidence and register consistency audit; not a fresh verification of every original source.',
                   totals=counts(results), live_built=counts([r for r in results if r['live_built_lab']]),
                   schools={s: counts([r for r in results if r['school'] == s]) for s in schools})
    (out / 'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n')
    (out / 'subject-profile-receipts.json').write_text(json.dumps([{k:v for k,v in r.items() if not k.startswith('_')} for r in profile_receipts.values()], indent=2, ensure_ascii=False) + '\n')
    (out / 'input-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, default=P.SCRATCH / 'pi-inventory-review-1117/all-pis-labs.csv')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    audit(args.inventory, args.out)


if __name__ == '__main__':
    main()
