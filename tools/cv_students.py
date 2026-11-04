"""Students named in a PI's own CV (HTML, or a PDF read through pdftotext from its Wayback capture): protocol stage 6, owner dive 2026-11-04.

For each PI of the school without students (or every PI with --all) the CV links found on the PI's stored pages (anchor text or file name: CV, vita,
curriculum vitae, resume) are fetched (live where the charter allows the host, else the Wayback capture nearest the present; a PDF of a host whose
robots.txt bars PDFs, Booth's, is never fetched). A section whose heading names advised students ('Ph.D. students advised', 'Doctoral students',
'Students supervised', 'Advisees', 'Graduate students', 'Current students', 'Former students', 'Ph.D. dissertations supervised' ...) is read to the next
heading; every item with a plausible person name and a year (or a 'current' heading) becomes a relation: role phd, years [None, year] for a degree year,
[year, None] for 'current'; a year before the PI's first listing at the school is dropped (appointment window). The quote is the heading through the
name, verbatim from the CV text. -> hierarchy/<key>/reviewed/cv-evidence.json {rows, checked}; labpage_students_school.extract merges the rows.
usage: cv_students.py <key> [--all]
"""
import collections, html as H, json, re, subprocess, sys, tempfile, urllib.parse as U, zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hierarchy' / 'labpage-tools-epfl-berkeley'))
import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
import school_web as W  # noqa: E402
import periods_school as PS  # noqa: E402
import student_decisions as SD  # noqa: E402
import lpdom  # noqa: E402

ANCHOR = re.compile(r'<a\b[^>]*?href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.S | re.I)
CVWORD = re.compile(r'(\bcv\b|curriculum vita|\bvita\b|resum)', re.I)
NOISE_URL = re.compile(r'(/curriculum\b|#|resume-review|core-curriculum|/blog/|/mba/|/programs/|mailto:|linkedin)', re.I)
HEAD = re.compile(r'(ph\.?\s?d\.?\s*(?:students?|advis\w*|dissertations?|theses|thesis|committees?)|doctoral\s*(?:students?|advis\w*|dissertations?|theses|committees?)|'
                  r'students?\s*(?:supervised|advised|mentored)|advisees|(?:current|former|past|graduate)\s*students?|student\s*advising|graduate\s*advising|'
                  r'advising|supervision|mentoring|dissertations?\s*supervised)', re.I)
STOP = re.compile(r'^\W*(teaching|service|publications?|awards?|honors?|grants?|funding|talks?|invited|professional|education|employment|appointments?|'
                  r'research|selected|software|patents?|editorial|memberships?|references|courses?|conferences?|journal)\b', re.I)
YEAR = re.compile(r'(?<!\d)((?:19|20)\d\d)(?!\d)')


def cv_urls(c, urls):
    out = collections.OrderedDict()
    for u in urls:
        pages = [(cap, W.body(raw).decode('utf8', 'replace')) for cap, raw in c.execute('select capture_url, raw_zlib from captures where http_status=200 and page_url=?', (u,))]
        pages += [(u, zlib.decompress(raw).decode('utf8', 'replace')) for (raw,) in c.execute('select raw_zlib from live where status=200 and url=?', (u,))]
        for cap, h in pages:
            for m in ANCHOR.finditer(h):
                t = ' '.join(H.unescape(re.sub(r'<[^>]+>', ' ', m.group(2))).split())
                href = m.group(1)
                if CVWORD.search(t[:40]) or re.search(r'(^|/)(cv|vita|resume|curriculum[-_]?vita\w*)[^/]*\.(pdf|html?)$', href, re.I):
                    full = re.sub(r'^https://web\.archive\.org/web/\d+(?:id_)?/', '', U.urljoin(u, href))
                    if not NOISE_URL.search(full):
                        out[full] = t[:30]
    return out


def cv_text(c, key, url):
    """(text, capture date or 'live', note) of one CV URL; text None when it cannot be read under the rules."""
    host = re.sub(r'^https?://', '', url).split('/')[0].lower()
    pdf = url.lower().split('?')[0].endswith('.pdf')
    if pdf and 'chicagobooth.edu' in host:
        return None, None, 'Booth robots.txt disallows /*.pdf: not fetched'
    if not pdf and S.host_use(key, host) == 'live' and host not in W._blocked:
        res = W.live(c, url)
        if res and res[0] == 200:
            row = c.execute('select raw_zlib, fetched_at from live where url=?', (url,)).fetchone()
            b = W.extract.blocks(zlib.decompress(row[0]), 'text/html', url)
            return W.flat(b), row[1][:10].replace('-', ''), 'live'
    rows = W.cdx_rows(c, re.sub(r'^https?://', '', url), frm='2016', to='2026', collapse='timestamp:6')
    if not rows:
        return None, None, 'no Wayback capture'
    r = max(rows, key=lambda x: x['timestamp'])
    cap, st, sha, b = W.capture(c, r['timestamp'], r['original'], url, 'cv')
    if st != 200:
        return None, None, f'capture status {st}'
    if pdf:
        raw = c.execute('select raw_zlib from captures where capture_url=?', (cap,)).fetchone()[0]
        with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
            f.write(W.body(raw)); f.flush()
            t = subprocess.run(['pdftotext', '-layout', f.name, '-'], capture_output=True, text=True).stdout
        return t, r['timestamp'][:8], 'wayback pdf'
    return W.flat(b), r['timestamp'][:8], 'wayback'


def parse(text, first_year):
    """[(name, years, heading, quote)] from advising sections of a CV text (lines)."""
    lines = [' '.join(x.split()) for x in text.replace('\x0c', '\n').split('\n')]
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        if ln and len(ln) <= 70 and HEAD.search(ln) and not STOP.match(ln):
            cur = bool(re.search(r'current|present', ln, re.I)); body = []
            j = i + 1
            while j < len(lines) and not (lines[j] and len(lines[j]) <= 50 and STOP.match(lines[j])) and j - i < 80:
                body.append(lines[j]); j += 1
            blob = ' '.join(x for x in body if x)
            for item in re.split(r'[;•]|\s{2,}|(?<=\))\s*,\s*', blob):
                m = re.match(r"^\W*([A-Z][\w.'’-]+(?: [A-Z][\w.'’-]+){1,3})\b", item.strip())
                if not m:
                    continue
                nm = m.group(1)
                if not (lpdom.looks_like_name(nm) and lpdom.plausible_person(nm)):
                    continue
                ys = [int(y) for y in YEAR.findall(item)]
                if ys:
                    yrs = [None, max(ys)] if len(ys) == 1 and not cur else [min(ys), max(ys)]
                elif cur:
                    yrs = [None, None]
                else:
                    continue
                if (yrs[1] and yrs[1] < max(first_year, 2016)) or (yrs[0] and yrs[0] < first_year):
                    continue   # appointment window: nothing that starts before the PI's first listing at the school (an earlier institution's students)
                q = ln + ' ' + blob[:blob.find(nm) + len(nm)][-300:]
                out.append((nm, yrs, ln, q.strip()))
            i = j
        else:
            i += 1
    return out


def main(key, everyone=False):
    c = W.con(key)
    tg = {t['name']: t for t in PS.targets(key)}
    cov = P.data('lab-coverage-reasons.json', key)
    reasons = json.loads(Path(cov).read_text()) if Path(cov).exists() else {}
    pis = list(tg) if everyone else [pi for pi, v in reasons.items() if (v.get('students') or {}).get('code') == 'sources_exhausted']
    dec = SD.load(key)
    rows, checked = [], {}
    for pi in pis:
        t = tg.get(pi)
        if not t:
            continue
        checked[pi] = []
        for url, label in list(cv_urls(c, t['urls']).items())[:4]:
            text, when, note = cv_text(c, key, url)
            ent = dict(url=url, label=label, capture=when, note=note, advising_items=0)
            if text:
                for nm, yrs, head, q in parse(text, t['first']):
                    if SD.excluded(dec, pi, nm):
                        continue
                    flat = ' '.join(text.split())
                    if q not in flat and q.replace('  ', ' ') not in flat:
                        q = head + ' ' + nm   # a quote the layout split: the heading and the name, each verbatim
                    rows.append(dict(student=nm, pi=pi, years=yrs, url=url, capture_url=url, sha256=None, quote=q[:400],
                                     directory_evidence=[dict(url=url, observed=when, directory='CV', heading=head)], section='CV: ' + head, years_basis='cv_years'))
                    ent['advising_items'] += 1
            checked[pi].append(ent)
    f = P.data_w('cv-evidence.json', key)
    f.write_text(json.dumps(dict(rows=rows, checked=checked), indent=1, ensure_ascii=False))
    print(json.dumps(dict(pis=len(pis), with_cv_url=sum(1 for v in checked.values() if v), rows=len(rows), students=len({(r['pi'], r['student']) for r in rows}))))


if __name__ == '__main__':
    main(sys.argv[1], '--all' in sys.argv)
