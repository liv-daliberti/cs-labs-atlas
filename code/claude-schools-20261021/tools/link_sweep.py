"""Every student x every paper within each PI lab (owner 2026-10-29: "check each student against each paper within a
lab"): an exhaustive, read-only byline match that measures what the builder's student-paper links miss, and re-checks
every existing link.

match     a byline author is the student when the family names agree (either order: 'Wei Zhang' / 'Zhang Wei'; a two-part
          family name may match on either part) and the given names agree: equal, an initial of it, a nickname pair
          (pi_hierarchy.nick_ok), or the same letters without hyphens/spaces ('Yu-Jhe' / 'Yujhe'). Accents, case, 'Last,
          First' and punctuation are normalized.
unique    the byline author matches exactly one student of the lab (two students 'J. Smith' make it ambiguous)
window    the paper's year within [first year - 2, last year + 6] of the student's recorded years (no years: any)
-> hierarchy/link-sweep/<school>.json: per lab the new candidate pairs (unique, in window), the ambiguous and
   out-of-window ones, and the existing links the sweep cannot reproduce (byline lacks the student)
usage: link_sweep.py [school ...]
"""
import collections, gzip, json, re, sys, unicodedata
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from pi_hierarchy import nick_ok, byline_name  # noqa: E402

H = Path(__file__).resolve().parents[1] / 'hierarchy'


def toks(s):
    s = unicodedata.normalize('NFKD', byline_name(s or '')); s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r'\([^)]*\)', ' ', s)
    return [t for t in re.split(r"[^a-z\-]+", s.replace("'", '')) if t and t not in ('jr', 'sr', 'ii', 'iii', 'phd', 'dr')]


def given_ok(a, b):
    a2, b2 = a.replace('-', ''), b.replace('-', '')
    if a2 == b2 or nick_ok(a2, b2):
        return True
    return (len(a2) == 1 and b2.startswith(a2)) or (len(b2) == 1 and a2.startswith(b2))


def forms(t):
    """(family, given) readings of a token list: the last token as family name; for a two-token name also the first
    (East Asian order, 'Zhang Wei'); for a 3+ token name the second-to-last token too (a two-part family name whose
    byline keeps only the first part: 'Bruno Schmitt Antunes' / 'Bruno Schmitt'), and each half of a hyphenated family
    name. Family names are 2+ letters; the given name is always the first token."""
    if len(t) < 2:
        return []
    out = [(t[-1], t[0])]
    if len(t) == 2:
        out.append((t[0], t[1]))
    else:
        out.append((t[-2], t[0]))
    if '-' in t[-1]:
        out += [(p, t[0]) for p in t[-1].split('-')]
    return [(f.replace('-', ''), g) for f, g in out if len(f.replace('-', '')) >= 2]


def byline_forms(t):
    """A byline author's readings: its last token as family name, or for a two-token byline the first (order swap)."""
    if len(t) < 2:
        return []
    out = [(t[-1], t[0])] + ([(t[0], t[1])] if len(t) == 2 else [])
    if '-' in t[-1]:
        out += [(p, t[0]) for p in t[-1].split('-')]
    return [(f.replace('-', ''), g) for f, g in out if len(f.replace('-', '')) >= 2]


def same(st, bt):
    return any(f1 == f2 and given_ok(g1, g2) for f1, g1 in forms(st) for f2, g2 in byline_forms(bt))


def run(school):
    D = H / school
    stu = json.loads((D / 'students.json').read_text())
    lp = collections.defaultdict(list)
    for l in gzip.open(D / 'lab_papers.jsonl.gz', 'rt'):
        r = json.loads(l); lp[r['pi']].append(r)
    have = collections.defaultdict(set)
    for l in gzip.open(D / 'student_papers.jsonl.gz', 'rt'):
        r = json.loads(l); have[(r['pi'], r['student'])].add(r.get('work') or r.get('oa'))
    out, tot = {}, collections.Counter()
    for pi, S in stu.items():
        names = {s['person']: [toks(x) for x in [s['name']] + list(s.get('aliases') or [])] for s in S}
        years = {s['person']: sorted({y for r in s.get('relations') or [] for y in (r.get('years') or []) if isinstance(y, int)}) for s in S}
        new, amb, outw, unrepro = [], [], [], []
        for r in lp.get(pi, []):
            k = r.get('work') or r.get('oa'); y = r.get('year')
            for raw in r.get('byline') or []:
                bt = toks(raw)
                hits = [sid for sid, ns in names.items() if any(same(n, bt) for n in ns if n)]
                if not hits:
                    continue
                if len(hits) > 1:
                    if not any(k in have[(pi, h)] for h in hits):
                        amb.append(dict(paper=k, byline=raw, students=hits)); tot['ambiguous'] += 1
                    continue
                sid = hits[0]
                if k in have[(pi, sid)]:
                    tot['existing_reproduced'] += 1; continue
                ys = years[sid]
                if ys and y and not (ys[0] - 2 <= y <= ys[-1] + 6):
                    outw.append(dict(paper=k, year=y, student=sid, byline=raw, years=[ys[0], ys[-1]])); tot['out_of_window'] += 1
                else:
                    new.append(dict(paper=k, year=y, student=sid, byline=raw)); tot['new_in_window'] += 1
        # existing links the byline does not support
        byl = {(r.get('work') or r.get('oa')): [toks(b) for b in r.get('byline') or []] for r in lp.get(pi, [])}
        for s in S:
            for k in have[(pi, s['person'])]:
                if k in byl and not any(same(n, bt) for n in names[s['person']] if n for bt in byl[k]):
                    unrepro.append(dict(paper=k, student=s['person'], name=s['name'])); tot['existing_not_on_byline'] += 1
        tot['students'] += len(S); tot['students_linked_before'] += sum(bool(have[(pi, s['person'])]) for s in S)
        tot['students_linked_after'] += sum(bool(have[(pi, s['person'])] or any(x['student'] == s['person'] for x in new)) for s in S)
        if new or amb or outw or unrepro:
            out[pi] = dict(new=new, ambiguous=amb, out_of_window=outw, existing_not_on_byline=unrepro)
    tot['links_before'] = sum(len(v) for v in have.values())
    (H / 'link-sweep' / f'{school}.json').write_text(json.dumps(dict(summary=tot, labs=out), indent=1, ensure_ascii=False))
    print(json.dumps(dict(school=school, **tot)), flush=True)


if __name__ == '__main__':
    for s in sys.argv[1:] or ['princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford']:
        run(s)
