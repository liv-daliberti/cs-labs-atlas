"""Students of a school's PIs from Wikidata's doctoral-student (P185) statements (owner 2026-11-04, "look for other ways to fill").

Robots: www.wikidata.org/robots.txt disallows /w/ and /api/ and query.wikidata.org disallows /sparql for every crawler, so neither the
action API nor the query service is used. The one allowed path is /wiki/Special:EntityData/<Q>.json (no rule names ClaudeBot or
anthropic-ai); one request per second, a descriptive User-Agent, responses cached gzip under var/cache/wikidata.
Route: PI -> its DBLP person records -> the wikidata.org/entity/Q urls DBLP lists -> the Q's JSON (label must equal the PI's name) -> P185 values ->
each student's JSON: the student counts only if its own record names the school (P69 educated at, P108 employer, P1344... via the institution's label
holding the school's name) AND names this PI as doctoral advisor (P184) or the PI's P185 lists it (both sides recorded; either alone is enough, the quote says which).
Years come from the school-matched P69 start/end qualifiers (P580/P582); without a year the row is skipped (recorded in `checked`).
The appointment window applies: nothing ending before the PI's first listing at the school.
-> reviewed/wikidata-evidence.json {rows, checked, counts} (rows have the cv-evidence shape; labpage_students_school.extract merges them).
usage: wikidata_students.py <school> [--all] [--count-only]   (default: only PIs without students / with a sources_exhausted reason; --all: every PI)
"""
import gzip, json, re, sys, time, unicodedata, urllib.request, hashlib, datetime
from pathlib import Path

import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
import periods_school as PS  # noqa: E402

UA = 'cs-atlas-research/1.0 (academic study of research labs; polite 1 req/s; contact via project repository)'
CACHE = P.CACHE / 'wikidata'
ENT = 'https://www.wikidata.org/wiki/Special:EntityData/%s.json'
_last = [0.0]


def fold(s):
    s = unicodedata.normalize('NFKD', s or '')
    return re.sub(r'[^a-z ]+', ' ', ''.join(c for c in s if not unicodedata.combining(c)).lower()).split()


def entity(q):
    """(entity dict or None, observed YYYYMMDD, sha256)"""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (q + '.json.gz')
    if f.exists():
        raw = gzip.open(f).read()
        meta = json.loads(raw)
        return meta['entity'], meta['observed'], meta['sha256']
    wait = 1.0 - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    body, ent = b'', None
    for attempt in range(3):
        try:
            req = urllib.request.Request(ENT % q, headers={'User-Agent': UA, 'Accept': 'application/json'})
            body = urllib.request.urlopen(req, timeout=30).read()
            ent = json.loads(body)['entities'].get(q)
            break
        except Exception as e:  # noqa: BLE001
            if getattr(e, 'code', None) == 404:
                break
            time.sleep(5 * (attempt + 1))
    _last[0] = time.time()
    meta = dict(entity=ent, observed=datetime.date.today().strftime('%Y%m%d'), sha256=hashlib.sha256(body).hexdigest())
    with gzip.open(f, 'wt') as g:
        json.dump(meta, g)
    return ent, meta['observed'], meta['sha256']


def label(ent):
    return ((ent or {}).get('labels', {}).get('en') or {}).get('value') or ''


def ids(ent, prop):
    out = []
    for c in (ent or {}).get('claims', {}).get(prop, []):
        v = (c.get('mainsnak', {}).get('datavalue') or {}).get('value')
        if isinstance(v, dict) and v.get('id'):
            out.append((v['id'], c.get('qualifiers') or {}))
    return out


def year_of(q, prop):
    for s in q.get(prop, []):
        t = ((s.get('datavalue') or {}).get('value') or {}).get('time')
        if t:
            return int(t[1:5])
    return None


def school_names(key):
    cfg = S.get(key)
    return [n.lower() for n in {cfg.get('name'), cfg.get('short')} if n]


def school_stays(ent, names):
    """[(institution label, start, end)] of the school-matched P69 (educated at) / P108 (employer) statements."""
    out = []
    for prop in ('P69', 'P108'):
        for qid, q in ids(ent, prop):
            e, _, _ = entity(qid)
            lb = label(e).lower()
            if lb and any(lb == n or lb.startswith(n) for n in names):
                out.append((label(e), year_of(q, 'P580'), year_of(q, 'P582'), prop))
    return out


def pi_qids(key):
    """PI name -> (first listed year, [Q ids from the PI's DBLP person records])."""
    pis = {p['pi']: p for p in json.load(open(P.data('pis.json', key)))}
    dp = {}
    for f in (P.data('dblp-dump-persons.json.gz'), P.data('dblp-dump-persons-school.json.gz', key)):
        if f.exists():
            dp.update(json.load(gzip.open(f, 'rt'))['persons'])
    first = {t['name']: t['first'] for t in PS.targets(key)}
    out = {}
    for nm, p in pis.items():
        qs = []
        for pid in p.get('dblp') or []:
            for u in (dp.get(pid) or {}).get('urls') or []:
                m = re.search(r'wikidata\.org/entity/(Q\d+)', u)
                if m:
                    qs.append(m.group(1))
        out[nm] = (first.get(nm, 2016), list(dict.fromkeys(qs)))
    return out


def run(key, everyone=False, count_only=False):
    names = school_names(key)
    cov = P.data('lab-coverage-reasons.json', key)
    reasons = json.load(open(cov)) if Path(cov).exists() else {}
    have = set()
    sf = P.data('labpage-evidence.json', key)
    if sf.exists():
        have = {e['pi'] for e in json.load(open(sf)) if e.get('students')}
    rows, checked = [], {}
    pq = pi_qids(key)
    for pi, (first, qs) in pq.items():
        if not everyone and (pi in have and (reasons.get(pi, {}).get('students') or {}).get('code') != 'sources_exhausted'):
            continue
        checked[pi] = dict(qids=qs, pi_label_match=[], students_listed=0, skipped_no_year=0, skipped_other_school=0, rows=0)
        for q in qs:
            ent, obs, sha = entity(q)
            if not ent or fold(label(ent)) != fold(pi) and not {' '.join(fold(a['value'])) for a in (ent.get('aliases', {}).get('en') or [])} & {' '.join(fold(pi))}:
                continue
            checked[pi]['pi_label_match'].append(q)
            for sq, _ in ids(ent, 'P185'):
                checked[pi]['students_listed'] += 1
                se, sobs, ssha = entity(sq)
                stays = school_stays(se, names)
                if not stays:
                    checked[pi]['skipped_other_school'] += 1
                    continue
                adv = [a for a, _ in ids(se, 'P184')]
                yrs = [y for st in stays for y in st[1:3] if y]
                if not yrs:
                    checked[pi]['skipped_no_year'] += 1
                    continue
                lo, hi = (min(yrs), max(yrs)) if len(yrs) > 1 else (None, yrs[0])
                if (hi and hi < max(first, 2016)) or (lo and lo < first):
                    continue
                nm = label(se)
                side = 'both sides' if q in adv else 'the PI record lists the student (P185); the student record names no advisor'
                quote = (f'Wikidata {q} "{label(ent)}" doctoral student (P185): {sq} "{nm}"; {sq} {stays[0][3]} {stays[0][0]} '
                         f'{lo or ""}-{hi or ""}; student record P184 advisor ids: {", ".join(adv) or "none"} ({side})')
                rows.append(dict(student=nm, pi=pi, years=[lo, hi], role='phd', url=ENT % sq, capture_url=ENT % sq, sha256=ssha, quote=quote[:400],
                                 directory_evidence=[dict(url=ENT % sq, observed=sobs, directory='Wikidata', heading='P185/P184')],
                                 section='Wikidata doctoral student (P185)', years_basis='wikidata_qualifiers'))
                checked[pi]['rows'] += 1
    counts = dict(pis_checked=len(checked), pis_with_qid=sum(1 for v in checked.values() if v['qids']),
                  pis_label_matched=sum(1 for v in checked.values() if v['pi_label_match']), rows=len(rows),
                  pis_with_rows=len({r['pi'] for r in rows}), students_listed=sum(v['students_listed'] for v in checked.values()))
    if not count_only:
        P.data_w('wikidata-evidence.json', key).write_text(json.dumps(dict(rows=rows, checked=checked, counts=counts), indent=1, ensure_ascii=False))
    print(json.dumps(dict(school=key, **counts)))
    return counts


if __name__ == '__main__':
    run(sys.argv[1], '--all' in sys.argv, '--count-only' in sys.argv)
