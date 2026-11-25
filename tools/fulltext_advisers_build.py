"""Turn adviser-statement hits (fulltext_advisers.py scan) and WashU ETD committee-chair records into researched-evidence rows.

build  <school> --hits DIR --out FILE      hits -> rows in the thesis-evidence.json shape ([{pi, students:[{name, role, years, url, sha256, quote, note}], notes}])
washu  --etd washu-etd.json --out FILE     tools/washu_etd.py parse output -> hierarchy/washu/reviewed/thesis-committee-chair-evidence.json (a RESEARCHED_FILES file since R-STU-23, 2026-11-08)

Rules: R-STU-01 (quote + hash), R-STU-03 (adviser names: pihier.names.Name + the given-name guard of etd_crawl.given_ok),
R-STU-14 (year = the document's year, inside 2016-2026 and the PI's listed years), R-STU-07 (a PI is never a student record).
Skipped, not guessed: a multi-author document whose quote names no byline author; a statement that says 'former'; an adviser who
matches two PIs; a student who is a PI of the school; a (PI, student) pair the school's package or reviewed evidence already holds.
"""
import argparse
import collections
import glob
import json
import re
import sqlite3
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402
from pihier.names import Name, toks  # noqa: E402

WINDOW = (2016, 2026)
EVIDENCE_FILES = ['few-students-evidence.json', 'undated-capture-evidence.json', 'surname-adviser-evidence.json', 'thesis-evidence.json',
                  'labpage-evidence.json', 'thesis-held-years-evidence.json', 'roster-evidence.json', 'defense-adviser-evidence.json']
BRANCHES = ['gt-students-1107', 'mi-uc-students-1107', 'hjw-students-1107', 'lab-websites']
TITLE = re.compile(r'^(?:prof(?:essor)?\.?|dr\.?)\s+', re.I)


def nt(t):
    t = unicodedata.normalize('NFKD', t or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', t)


def natural(name):
    n = re.sub(r'\s+', ' ', name or '').strip()
    if ',' in n:
        last, _, first = n.partition(',')
        return f'{first.strip()} {last.strip()}'.strip()
    return n


def given_ok(advisor, pi_names):
    t = [x for x in re.sub(r'[^a-z ]', ' ', nt_words(advisor)).split()]
    if len(t) < 2:
        return True
    given = [x for x in t[:-1] if len(x) > 1]
    if not given:
        return True
    mine = {x[:3] for n in pi_names for x in re.sub(r'[^a-z ]', ' ', nt_words(n)).split()[:-1] if len(x) > 1}
    return any(g[:3] in mine for g in given)


def nt_words(t):
    return unicodedata.normalize('NFKD', t or '').encode('ascii', 'ignore').decode().lower()


class School:
    def __init__(self, school):
        self.school = school
        self.pis = json.loads(P.data('pis.json', school).read_text())
        self.names_of = {p['pi']: list(dict.fromkeys([p['pi']] + list(p.get('names') or []))) for p in self.pis}
        self.idx = {p: Name(n) for p, n in self.names_of.items()}
        self.window = {}   # the PI's package periods (start year .. end year, open = 2026): the appointment guard
        for p in self.pis:
            ys = [(int(str(x['start'])[:4]), int(str(x['end'])[:4]) if x.get('end') else 2026) for x in p.get('periods') or [] if x.get('start')]
            if ys:
                self.window[p['pi']] = (min(y[0] for y in ys), max(y[1] for y in ys))
        self.have = self._existing()

    def _existing(self):
        have = set()
        sf = P.data('students.json', self.school)
        if sf.exists():
            for pi, lst in json.loads(sf.read_text()).items():
                for s in lst:
                    have.add((pi, nt(s['name'])))
        rev = Path(P.data('thesis-evidence.json', self.school)).parent
        for fn in EVIDENCE_FILES:
            f = rev / fn
            if f.exists():
                for r in json.loads(f.read_text()):
                    for s in r.get('students', []):
                        have.add((r['pi'], nt(s['name'])))
        for b in BRANCHES:
            for fn in EVIDENCE_FILES:
                rel = f'hierarchy/{self.school}/reviewed/{fn}'
                r = subprocess.run(['git', '-C', str(P.CODE), 'show', f'agent/{b}:{rel}'], capture_output=True)
                if r.returncode == 0:
                    try:
                        for row in json.loads(r.stdout):
                            for s in row.get('students', []):
                                have.add((row['pi'], nt(s['name'])))
                    except ValueError:
                        pass
        return have

    def pi_for(self, adviser):
        """The one PI the adviser string names. A captured string can run on into the next sentence ('Ling Liu. His'), so the
        longest word-prefix of two or more words that names a PI wins."""
        nat = TITLE.sub('', natural(adviser)).rstrip('.')
        words = nat.split()
        for k in range(min(len(words), 4), 1, -1):
            cand = ' '.join(words[:k]).rstrip('.')
            hits = [p for p, nm in self.idx.items() if nm.match(cand) and given_ok(cand, self.names_of[p])]
            if len(hits) == 1:
                return hits[0]
            if len(hits) > 1:
                return 'AMBIGUOUS'
        return None

    def is_pi(self, name):
        return any(nm.match(name) for nm in self.idx.values())

    def in_window(self, pi, year):
        if not year or not (WINDOW[0] <= year <= WINDOW[1]):
            return False
        w = self.window.get(pi)
        return not w or w[0] <= year <= w[1]


def role_of(text):
    t = (text or '').lower()
    if re.search(r'ph\.?\s?d|doctor|dissertation', t):
        return 'phd'
    if re.search(r"master of|master[’']s (?:thesis|degree|student)|\bm\.?s\.? thesis|\bs\.?m\.? thesis", t):
        return 'masters'
    return 'student'


def student_of(hit, byline, adviser_name):
    """The document author the statement is about, or None."""
    quote = hit['quote']
    if len(byline) == 1:
        return byline[0]
    if hit['kind'] in ('advised_by', 'under_sup'):   # the footnote must name exactly one byline author itself
        named = [a for a in byline if toks(a) and re.search(r'\b' + re.escape(toks(a)[-1]) + r'\b', nt_words(quote)) and len(toks(a)[-1]) > 2]
        named = [a for a in named if not Name([adviser_name]).match(a)]
        return named[0] if len(named) == 1 else None
    return None


def title_page_author(school, path, byline, S, adviser):
    """A thesis whose byline lists the author with several others (the adviser, committee): the one non-PI byline author whose full
    name stands in the first three pages (the title page). None when zero or several do."""
    try:
        txt = subprocess.run(['pdftotext', '-f', '1', '-l', '3', '-q', str(Path(P.STORES) / school / path), '-'],
                             capture_output=True, timeout=60).stdout.decode('utf8', 'replace')
    except (subprocess.TimeoutExpired, OSError):
        return None
    flat = nt(txt)
    found = []
    for a in byline:
        t = toks(natural(a))
        if len(t) < 2 or S.is_pi(a) or Name([adviser]).match(a):
            continue
        if nt(' '.join(t)) in flat or nt(' '.join([t[0], t[-1]])) in flat:
            found.append(a)
    return found[0] if len(found) == 1 else None


def build(school, hits_dir):
    S = School(school)
    out = collections.defaultdict(dict)
    c = collections.Counter()
    cat = sqlite3.connect(f"file:{Path(P.STORES) / school / 'catalog.sqlite'}?mode=ro", uri=True)
    for f in sorted(glob.glob(f'{hits_dir}/{school}-*of*.sqlite')):
        db = sqlite3.connect(f'file:{f}?mode=ro', uri=True)
        db.row_factory = sqlite3.Row
        for h in db.execute('select * from hits'):
            h = dict(h)
            c['hits'] += 1
            pi = S.pi_for(h['adviser'])
            if pi is None:
                c['no_pi'] += 1
                continue
            if pi == 'AMBIGUOUS':
                c['ambiguous'] += 1
                continue
            at = h['quote'].find(h['adviser'])
            before = h['quote'][max(0, at - 110):at]
            after_ = h['quote'][at:at + 120]
            if h['kind'] != 'front' and re.search(r"\b(?:not|never|n[’']t)\b[^.]{0,40}\b(?:advis|supervis)|academic|senior thesis|undergrad|bachelor|master|\bM\.?S\.?\b|\bintern\b|summer|co-?op|rotation", before + ' ' + after_[:110], re.I):
                c['not_phd_adviser'] += 1   # 'academic advisor' is program advising (R-STU-02); senior-thesis, master's, intern and negated statements are no PhD adviser
                continue
            if re.search(r'\b(?:former|previous|late)\b', h['quote'][max(0, h['quote'].find(h['adviser']) - 60):h['quote'].find(h['adviser'])], re.I):
                c['former'] += 1
                continue
            byline = json.loads(h['byline'] or '[]')
            if not byline:   # a thesis record: the catalog graph names its student author
                g = cat.execute('select graph_json from works where id=?', (h['work_id'],)).fetchone()
                gj = json.loads(g[0]) if g else {}
                byline = next((v for k, v in gj.items() if k.endswith('_students') and isinstance(v, list)), []) if g else []
                byline = [b for b in byline if not re.search(r'Institute|University|Ph\.? ?D|Thesis', b)]   # a garbled catalog name is no author
            stu = student_of(h, byline, h['adviser'])
            if not stu and (h['pages'] or 0) >= 40 and h['kind'] in ('ack_my', 'ack_my2', 'front') and len(byline) > 1 and h['path'].endswith('.pdf'):
                stu = title_page_author(school, h['path'], byline, S, h['adviser'])
                if stu:
                    c['title_page_author'] += 1
            if not stu:
                c['no_student'] += 1
                continue
            stu = re.sub(r'\s*\([^)]*\)', '', natural(stu)).strip()   # 'Jayson(Jayson R.) Lynch', 'Homberg, Bianca S.'
            if len(toks(stu)) < 2:
                c['name_incomplete'] += 1
                continue
            if S.is_pi(stu):
                c['student_is_pi'] += 1
                continue
            if not S.in_window(pi, h['year']):
                c['outside_window'] += 1
                continue
            if (pi, nt(stu)) in S.have:
                c['already_held'] += 1
                continue
            if nt(stu) in out[pi]:
                c['duplicate'] += 1
                continue
            url = f"https://doi.org/{h['doi']}" if h['doi'] else (h['url'] or '')
            if re.search(r'Signature=|Expires=|X-Amz|/bitstreams/', url):   # a signed, expiring download link is no citation
                land = cat.execute('select landing_url from candidates where work_id=? and landing_url is not null limit 1', (h['work_id'],)).fetchone()
                url = f"https://doi.org/{h['doi']}" if h['doi'] else (land[0] if land and not re.search(r'Signature=|Expires=', land[0]) else '')
            if not url:
                c['no_url'] += 1
                continue
            out[pi][nt(stu)] = dict(
                name=stu, role=role_of(h['quote']), years=[h['year'], h['year']], url=url, sha256=h['sha256'], quote=h['quote'],
                note=f"{school} full text of {h['work_id']} ({h['pages']} pages), {h['kind']} statement; adviser '{h['adviser']}' = {pi}; "
                     f"author of the document is the student (byline {byline}); year = the document's year")
            c['rows'] += 1
    rows = [dict(pi=p, students=sorted(v.values(), key=lambda s: (s['years'][0], s['name'])),
                 notes='Explicit adviser statements in full text already held (tools/fulltext_advisers.py).') for p, v in sorted(out.items())]
    return rows, dict(c)


def washu(etd_json, out):
    S = School('washu')
    out_rows = collections.defaultdict(dict)
    c = collections.Counter()
    for r in json.loads(Path(etd_json).read_text()):
        c['records'] += 1
        year = int(r['year']) if str(r.get('year', '')).isdigit() else None
        if not (r.get('quote_in_text') and r.get('author_in_text')):
            c['quote_not_in_page'] += 1
            continue
        for a in r['chairs']:
            pi = S.pi_for(a)
            if pi in (None, 'AMBIGUOUS'):
                c['no_pi' if pi is None else 'ambiguous'] += 1
                continue
            if not S.in_window(pi, year):
                c['outside_window'] += 1
                continue
            nm = natural(r['author'])
            if role_of(r['degree']) == 'student':   # R-STU-23 (2026-11-09): doctoral and master's records only; honours and other work never counts
                c['not_doctoral_or_masters'] += 1
                continue
            if (pi, nt(nm)) in S.have:
                c['already_held'] += 1
                continue
            out_rows[pi][nt(nm)] = dict(
                name=nm, role=role_of(r['degree']), years=[year, year], url=r['url'], sha256=r['sha256'], quote=(f'Committee Chair {a}' if f'Committee Chair {a}' in r['quote'] else r['quote']),
                note=f"washu repository item page ({r['degree']}; {r['department']}): '{r['title']}'; Committee Chair '{a}' = {pi}. "
                     f"R-STU-23 ({r.get('collection', 'eng_etds')}).")
            c['rows'] += 1
    rows = [dict(pi=p, students=sorted(v.values(), key=lambda s: (s['years'][0], s['name'])),
                 notes='WashU ETD Committee Chair rows (R-STU-23).') for p, v in sorted(out_rows.items())]
    Path(out).write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    return dict(c)


def ecommons(school, etd_json, out):
    """Cornell eCommons PhD dissertation records (tools/cornell_ecommons.py parse) -> researched-evidence rows: the chair (`dc.contributor.chair`, else
    `dc.contributor.advisor`) names the student's adviser when it matches a PI of the school (R-STU-03 names, given-name guard) and the degree year is in
    the PI's package window (R-STU-14). The quote is two verbatim excerpts of the stored API page ('<author> [...] <chair>'). Every row carries the
    discipline for the hand check: a chair name that matches a PI of another field (namesake) shows there."""
    S = School(school)
    out_rows = collections.defaultdict(dict)
    c = collections.Counter()
    for r in json.loads(Path(etd_json).read_text())['rows']:
        c['records'] += 1
        year = r.get('year')
        for a in r['chair']:
            pi = S.pi_for(natural(a))
            if pi in (None, 'AMBIGUOUS'):
                c['no_pi' if pi is None else 'ambiguous'] += 1
                continue
            if not S.in_window(pi, year):
                c['outside_window'] += 1
                continue
            nm = natural(r['author'] or '')
            if not nm or S.is_pi(nm):
                c['author_missing_or_pi'] += 1
                continue
            if (pi, nt(nm)) in S.have:
                c['already_held'] += 1
                continue
            out_rows[pi][nt(nm)] = dict(
                name=nm, role='phd', years=[year, year], url=r['page_url'], sha256=r['page_sha256'], quote=f"{r['author']} [...] {a}",
                note=f"eCommons record {r['url']} ({r['degree']}; {r['discipline']}; issued {year}): '{r['title']}'; {r['chair_field']} '{a}' = {pi}.")
            c['rows'] += 1
    rows = [dict(pi=p, students=sorted(v.values(), key=lambda s: (s['years'][0], s['name'])),
                 notes='Cornell eCommons dissertation chair rows (REST API record pages).') for p, v in sorted(out_rows.items())]
    Path(out).write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    return dict(c)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['build', 'washu', 'ecommons'])
    ap.add_argument('school', nargs='?')
    ap.add_argument('--hits')
    ap.add_argument('--etd')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    if a.cmd == 'washu':
        print(json.dumps(washu(a.etd, a.out)))
    elif a.cmd == 'ecommons':
        print(json.dumps(ecommons(a.school, a.etd, a.out)))
    else:
        rows, cnt = build(a.school, a.hits)
        Path(a.out).write_text(json.dumps(rows, indent=1, ensure_ascii=False))
        print(json.dumps(cnt))
