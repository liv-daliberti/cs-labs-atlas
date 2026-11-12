"""HKUST CSE 'Graduate Placements' page as a dated student-adviser source (rule R-STU-26, owner question queued 2026-11-13).

https://cse.hkust.edu.hk/pg/ourgraduates/ (the department's own page; robots.txt allows it) lists selected PhD graduates, one card each:
    <name> / <job> / <employer> / <place> / 'PhD <year>' / 'Supervised by <PI>[ and <PI>]'
A card is a dated student-adviser pair: the student took the PhD at HKUST CSE in <year> under the named supervisor(s). Used like the R-STU-24/25 thesis and
profile supervisor records (the shape of thesis-evidence.json; years [year, year], role phd, R-LNK-06 widens the paper window).

Admitted card: degree PhD, year 2016-2026, a supervisor that is exactly one CSE PI by the build's full-name rule (pihier.names.Name, spelled-out given name;
a name two PIs share is dropped). Co-supervised cards ('X and Y') give a row for every named supervisor that matches a PI (the PI is a named co-supervisor).
'Dr. Lin GU' style titles are stripped; a supervisor who is no HKUST CSE PI is skipped. The quote is the card's own text, verbatim in the page's flattened text.

usage: hkust_cse_graduates.py evidence --html FILE --url URL --sha SHA --pis pis.json [--out FILE]
"""
import argparse
import html as H
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pihier.names import Name  # noqa: E402

WINDOW = (2016, 2026)
RULE = 'R-STU-26'
CARD = re.compile(r'<a class="card news-card graduate-card".*?</a>', re.S)
TITLE = re.compile(r'^(?:Dr|Prof|Professor)\.?\s+', re.I)


def _p(card, cls):
    m = re.search(r'class="%s"[^>]*>(.*?)</p>' % cls, card, re.S)
    return re.sub(r'\s+', ' ', H.unescape(re.sub(r'<!--.*?-->|<[^>]+>', ' ', m.group(1) if m else ''))).strip()


def parse_cards(raw_html):
    """-> [dict(name, info1, deg, year, supervisors[], text)] for every graduate card of the page."""
    out = []
    for card in CARD.findall(raw_html):
        name, info1, info2 = _p(card, 'people-name'), _p(card, 'people-info1'), _p(card, 'people-info2')
        m = re.match(r'(PhD|MPhil|MSc|MEng)\s+(\d{4})\s+Supervised by (.+)$', info2)
        if not (name and m):
            continue
        sups = [TITLE.sub('', s).strip() for s in re.split(r'\s+and\s+', m.group(3))]
        out.append(dict(name=name, info1=info1, deg=m.group(1), year=int(m.group(2)), supervisors=sups, text=f'{name} {info1} {info2}'))
    return out


def flat_text(raw_html):
    t = re.sub(r'(?is)<(script|style)\b.*?</\1>', ' ', raw_html)
    return re.sub(r'\s+', ' ', H.unescape(re.sub(r'<!--.*?-->|<[^>]+>', ' ', t))).strip()


def evidence(raw_html, url, sha, pis):
    """-> (rows [{pi, students:[...], notes}], counts, skipped). `pis` is the school's pis.json list; only PIs with a CSE department are matched."""
    cse = [p for p in pis if 'CSE' in (p.get('departments') or [])]
    idx = {p['pi']: Name(list(dict.fromkeys([p['pi']] + list(p.get('names') or [])))) for p in cse}
    flat = flat_text(raw_html)
    counts = dict(cards=0, not_phd=0, outside_window=0, no_pi=0, ambiguous=0, quote_missing=0, rows=0)
    by, skipped = {}, []
    for c in parse_cards(raw_html):
        counts['cards'] += 1
        if c['deg'] != 'PhD':
            counts['not_phd'] += 1
            continue
        if not WINDOW[0] <= c['year'] <= WINDOW[1]:
            counts['outside_window'] += 1
            continue
        if c['text'] not in flat:
            counts['quote_missing'] += 1
            skipped.append(dict(name=c['name'], why='card text not in flattened page'))
            continue
        hit = False
        for s in c['supervisors']:
            ps = [p for p, nm in idx.items() if nm.match(s)]
            if len(ps) > 1:
                counts['ambiguous'] += 1
                skipped.append(dict(name=c['name'], supervisor=s, why='ambiguous', pis=ps))
                continue
            if not ps:
                continue
            hit = True
            co = f" (co-supervised with {', '.join(x for x in c['supervisors'] if x != s)})" if len(c['supervisors']) > 1 else ''
            by.setdefault(ps[0], []).append(dict(name=c['name'], role='phd', years=[c['year'], c['year']], url=url, sha256=sha,
                                                  quote=c['text'], note=f"HKUST CSE Graduate Placements card: PhD {c['year']}, supervised by {s}{co}. {RULE}"))
            counts['rows'] += 1
        if not hit:
            counts['no_pi'] += 1
    rows = [dict(pi=p, students=v, notes='HKUST CSE Graduate Placements page (tools/hkust_cse_graduates.py, R-STU-26).') for p, v in sorted(by.items())]
    return rows, counts, skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['evidence'])
    ap.add_argument('--html', required=True)
    ap.add_argument('--url', required=True)
    ap.add_argument('--sha', required=True)
    ap.add_argument('--pis', required=True)
    ap.add_argument('--out')
    a = ap.parse_args()
    rows, counts, skipped = evidence(Path(a.html).read_text(errors='replace'), a.url, a.sha, json.load(open(a.pis)))
    print(json.dumps(counts))
    if a.out:
        Path(a.out).write_text(json.dumps(rows, ensure_ascii=False, indent=1) + '\n')


if __name__ == '__main__':
    main()
