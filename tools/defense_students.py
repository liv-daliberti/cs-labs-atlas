"""Students from PhD-defense announcements (R-STU-23, proposed 2026-11-07): an announcement that names the candidate and marks a PI 'Advisor'.

Source: fulltext-push/defense_crawl.py (Georgia Tech's Mercury feed, hg.gatech.edu; the listing's title and date, the event page's text and sha256).
An event page counts for a PI only when
  1. the listing title names the candidate ('PhD Defense by <name>', 'Ph.D. Dissertation Defense - <name>', 'Dissertation Defense: <name>');
  2. the page text names the PI right next to an adviser cue: '<name> (Advisor)', '<name>, <unit>, Chair, Advisor', '<name> (co-advisor)' or
     'Advisor: <names>' (a committee member, reader, chair without the cue, 'faculty host' or 'collaborator' is not an adviser);
  3. the name is the PI's by the build's full-name rule (pihier.names.Name) and its given name is spelled out (etd_crawl.given_ok: a namesake
     such as 'Wang, C.-K. Chris' is not Kai Wang); a name two PIs share is ambiguous and dropped;
  4. the announcement year (the listing date, or a full date in the text) is inside the PI's listed years at the school and 2016-2026.
Row (reviewed/defense-evidence.json, the shape of thesis-evidence.json): role phd, years [y, y] (the defense year, R-LNK-06 widens the link window),
quote = the listing title | the page's own words from the adviser entry (verbatim), url, sha256 of the fetched bytes. A student the candidate
has no other record of is a new student of the lab; co-advised candidates are rows under every PI marked.

usage: defense_students.py evidence <school> [--out FILE]      (default: print the counts)
       defense_students.py sample <school> --seed N --n 30      (the rows to hand-check, with their full page text)
"""
import json
import random
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'fulltext-push'))
import atlas_paths as P  # noqa: E402
import etd_crawl as E  # noqa: E402
import ftp_common as F  # noqa: E402
from pihier.names import Name  # noqa: E402

WINDOW = (2016, 2026)
TITLE_RXS = [re.compile(r'(?i)^\s*(?:ph\.?\s?d\.?|doctoral)\s*(?:dissertation\s*)?(?:thesis\s*)?(?:defense|defence|proposal(?:\s+oral\s+exam)?|oral\s+exam)?\s*(?:by|[-–—:|])\s*(?P<n>.+?)\s*$'),
             re.compile(r'(?i)^\s*(?:dissertation|thesis)\s*(?:defense|defence)\s*(?:by|[-–—:|])\s*(?P<n>.+?)\s*$')]
PREFIX = r'(?:Dr|Prof|Professor|Mr|Ms|Mrs|Assoc|Assistant|Associate)\.?'
ADV = r'(?:co-?\s?|thesis\s+|dissertation\s+|primary\s+|research\s+)?advis[eo]r'
NAME = r"(?:[A-Z][\w'’\-]*\.?|[A-Z]\.)(?:\s+(?:[A-Z][\w'’\-]*\.?|de|van|von|der|di|da|la|le|del|bin|al)){1,3}"
NAME_RX = re.compile(r"(?:[A-Z][\w'’\-]*\.?)(?:\s+(?:[A-Z][\w'’\-]*\.?|de|van|von|der|di|da|la|le|del|bin|al)){1,4}", re.U)
STOP_FIRST = {'committee', 'members', 'member', 'chair', 'co-chair', 'advisor', 'advisors', 'co-advisor', 'thesis', 'reading', 'dissertation', 'research',
              'primary', 'and', 'the', 'with', 'by', 'faculty', 'host', 'school', 'georgia', 'tech', 'institute', 'department', 'professor'}
UNIT_WORDS = re.compile(r'(?i)\b(school|department|college|institute|university|laboratory|center|centre|engineering|science|sciences|georgia|tech|chair|co-chair|'
                        r'professor|emeritus|ece|isye|cs|ic|ml|mse|chbe|bme|ae|me|cee|math|physics|chemistry|biology|gtri|hsoe)\b')
# 'Advisor: Dr. X and Dr. Y' : names after the cue
BEFORE_RX = re.compile(r'(?i:(?:' + ADV + r')s?(?:\(s\))?)\s*[:\-–—]\s*(?P<list>[^;|]{3,160}?)(?=\s*(?:Committee|Co-?advis|Reader|Member|Abstract|Title|Date|Time|Location|$|;|\|))')
CUE = re.compile(r'(?i)\b' + ADV + r's?\b')


def clean_name(n):
    n = re.sub(r'^\s*(?:Mr|Ms|Mrs|Dr|Prof)\.?\s+', '', n.strip())
    n = re.sub(r'\s+', ' ', n).strip(' .,;:|')
    if n.isupper() or n.islower():
        n = n.title()
    return n


def candidate_name(title):
    for rx in TITLE_RXS:
        m = rx.match(title or '')
        if m:
            n = clean_name(m.group('n'))
            if 2 <= len(n.split()) <= 5 and not re.search(r'(?i)\b(defense|dissertation|committee|room|zoom)\b', n):
                return n
    return None


def trim_name(raw):
    """The person's name from a run of capitalised words: after the last title prefix, leading cue/unit words dropped."""
    toks = raw.split()
    for k in range(len(toks) - 1, -1, -1):
        if re.fullmatch(PREFIX, toks[k]):
            toks = toks[k + 1:]
            break
    while toks and toks[0].rstrip('.:,').lower() in STOP_FIRST:
        toks = toks[1:]
    return clean_name(' '.join(toks)) if len(toks) >= 2 else None


def entry_tail_has_cue(tail):
    """tail = the text right after a name: the cue must come in this entry ('(Advisor)', ', ECE, Chair, Advisor', ' - co-advisor')."""
    tail = tail.lstrip()
    if tail.startswith('('):
        close = tail.find(')')
        inner = tail[1:close if close > 0 else 60]
        return bool(CUE.search(inner)) and not re.search(r'(?i)\b(committee|reader|host|collaborat)\b', inner)
    cut = re.search(r'\b' + PREFIX + r'\s|;|\bCommittee\b|\bAbstract\b', tail)
    tail = tail[:cut.start()] if cut else tail[:100]
    segs = re.split(r',|\s[-–—]\s', tail)
    for seg in segs[:4]:
        seg = seg.strip(' .:')
        if not seg:
            continue
        if CUE.search(seg):
            return not re.search(r'(?i)\b(committee|reader|host|collaborat)\b', seg)
        if NAME_RX.fullmatch(seg) and not UNIT_WORDS.search(seg):
            return False        # the next person: this entry had no cue
    return False


def advisor_mentions(text):
    """-> [(advisor name, start, end)] the page names with an adviser cue on that entry."""
    out = []
    for m in NAME_RX.finditer(text):
        if not entry_tail_has_cue(text[m.end():m.end() + 130]):
            continue
        n = trim_name(m.group(0))
        if n:
            out.append((n, m.start(), m.end()))
    for m in BEFORE_RX.finditer(text):
        for part in re.split(r'\s+and\s+|\s*&\s*|,\s*(?=(?:' + PREFIX + r'|[A-Z]))', m.group('list')):
            part = re.sub(r'\(.*?\)', '', part).strip()
            mm = NAME_RX.match(part)
            n = trim_name(mm.group(0)) if mm else None
            if n:
                out.append((n, m.start('list'), m.end('list')))
    seen, res = set(), []
    for n, s_, e_ in out:
        if n.lower() not in seen:
            seen.add(n.lower())
            res.append((n, s_, e_))
    return res


def defense_year(listed, text):
    m = re.search(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+(20\d\d)\b', text)
    return int(m.group(1)) if m else int(listed[:4])


def connect_ro():
    from defense_crawl import db_path
    return sqlite3.connect(f'file:{db_path()}?mode=ro', uri=True)


def build(school, pis, pi_window=None):
    """-> (rows in thesis-evidence.json shape, counts, detail rows for sampling)."""
    idx = {p['pi']: Name(list(dict.fromkeys([p['pi']] + list(p.get('names') or [])))) for p in pis}
    names_of = {p['pi']: list(dict.fromkeys([p['pi']] + list(p.get('names') or []))) for p in pis}
    c = connect_ro()
    counts = dict(pages=0, no_candidate=0, no_advisor_cue=0, outside_window=0, no_pi=0, ambiguous=0, outside_pi_appointment=0, rows=0, duplicate=0)
    out, detail, seen = {}, [], {}
    for url, sha, text, listed, ltitle in c.execute(
            'SELECT p.url, p.sha256, p.text, q.listed, q.title FROM pages p JOIN queue q ON q.url = p.url ORDER BY q.listed, p.url'):
        counts['pages'] += 1
        cand = candidate_name(ltitle)
        if not cand:
            counts['no_candidate'] += 1
            continue
        ms = advisor_mentions(text)
        if not ms:
            counts['no_advisor_cue'] += 1
            continue
        year = defense_year(listed, text)
        if not (WINDOW[0] <= year <= WINDOW[1]):
            counts['outside_window'] += 1
            continue
        hit_any = False
        for adv, s, e in ms:
            pi_hits = [p for p, nm in idx.items() if nm.match(adv) and E.given_ok(adv, names_of[p])]
            if len(pi_hits) > 1:
                counts['ambiguous'] += 1
                continue
            for p in pi_hits:
                hit_any = True
                if pi_window and p in pi_window and not (pi_window[p][0] <= year <= pi_window[p][1]):
                    counts['outside_pi_appointment'] += 1
                    continue
                key = (p, F.nt(cand))
                if key in seen:   # the proposal and the defense of one candidate: one row, the years span both announcements
                    counts['duplicate'] += 1
                    r = seen[key]
                    r['years'] = [min(r['years'][0], year), max(r['years'][1], year)]
                    continue
                lo = max(0, s - 40)
                frag = text[lo:e + 20].strip()
                frag = frag[frag.find(' ') + 1:] if lo > 0 and ' ' in frag[:40] else frag
                quote = f'{ltitle} | {frag}'
                row = dict(name=cand, role='phd', years=[year, year], url=url, sha256=sha, quote=quote,
                           note=f"hg.gatech.edu PhD announcement listed {listed} ({'proposal' if re.search('(?i)proposal', ltitle) else 'defense'}): adviser '{adv}' = {p} (R-STU-23, defense_students.py)")
                seen[key] = row
                out.setdefault(p, []).append(row)
                detail.append(dict(pi=p, student=cand, url=url, listed=listed, year=year, quote=quote, text=text))
                counts['rows'] += 1
        if not hit_any:
            counts['no_pi'] += 1
    rows = [dict(pi=p, students=sorted(v, key=lambda s: (s['years'][0], s['name'])),
                 notes='PhD-defense announcements (hg.gatech.edu, fulltext-push/defense_crawl.py): the listing title names the candidate, the page marks the PI Advisor (R-STU-23).')
            for p, v in sorted(out.items())]
    return rows, counts, detail


def main(argv):
    cmd, school = argv[0], argv[1]
    pis = json.loads(P.data('pis.json', school).read_text())
    import periods_school as PS
    pw = {t['name']: (t['first'], max(t['years'] or [2026])) for t in PS.targets(school)}
    rows, counts, detail = build(school, pis, pw)
    if cmd == 'evidence':
        if '--out' in argv:
            Path(argv[argv.index('--out') + 1]).write_text(json.dumps(rows, indent=1, ensure_ascii=False))
        print(json.dumps(dict(counts, pis=len(rows))))
    elif cmd == 'sample':
        seed = int(argv[argv.index('--seed') + 1])
        n = int(argv[argv.index('--n') + 1]) if '--n' in argv else 30
        pick = random.Random(seed).sample(detail, min(n, len(detail)))
        print(json.dumps(pick, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main(sys.argv[1:])
