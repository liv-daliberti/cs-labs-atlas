"""Group attributes for the heterogeneity analysis: one row per (paper, lab) of the strict membership (pandas; CPU only).

reads   <snapshot>/release/hierarchy/<school>/{lab_papers.jsonl.gz, pis.json, students.json, student_papers.jsonl.gz}, universe/oa_extra.sqlite (source name),
        <results>/work/panel.parquet (OpenAlex topic), code hierarchy/reviewed/cs-venues.json, <results>/heterogeneity/work/pi_career.jsonl (study_hetero_authors.py),
        scratch/cs-rankings/gras-2025-cse-top300.tsv (GRAS 2025 CS&E rank bands)
writes  <results>/heterogeneity/work/hetero_papers.parquet, venue_map.csv (every reviewed venue and its area), school_tiers.csv, pi_attr.csv
Four characteristics (definitions fixed before any outcome was read; see HETEROGENEITY.md):
  career   years from the PI's first publication to 2022 (the year before post): early < 10, mid 10-20, senior > 20 (primary); alternatives in CAREER_ALT.
  led      pi_led: the PI is first (or sole) author; student_led: first author is a student of that lab (students.json roster / student_papers); other.
  field    theory / systems / ml_ai / other, venue first, OpenAlex topic fallback (study_hetero_fields.py).
  gras     GRAS 2025 CS&E band of the school: top10, r11_50, r51_300 (the 12 schools have ranks 1-8, 19, 21, 51-75, 51-75, 76-100, 151-200, 201-300).
"""
import argparse
import gzip
import json
import re
import sqlite3
import unicodedata

import numpy as np
import pandas as pd

import study_common as C
import study_hetero_fields as HF

REF_YEAR = 2022                                  # career age is measured at the last pre year, so a PI's tier never moves with the outcome year
CAREER_CUTS = (10, 20)                           # primary: early < 10 <= mid <= 20 < senior
CAREER_ALT = {'cut_8_18': (8, 18), 'cut_12_22': (12, 22), 'cut_10_25': (10, 25), 'cut_7_15': (7, 15)}
APPT_CUTS = (5, 15)                              # years since the earliest evidenced appointment start, at 2022: new < 5 <= mid <= 15 < long
STUDENT_ROLE = re.compile(r'phd|student|master|undergrad|visiting|doctoral|alumn', re.I)
ROUND1_SEED = 20261108                           # field hand check, round 1 (30 papers; found the failure modes the final field rules fix; labels kept in field_handcheck_round1.csv)
HANDCHECK_SEED = 20261109                        # round 2 on the final rules (numpy default_rng; 30 field papers, 20 led papers)
GRAS_FILE = 'gras-2025-cse-top300.tsv'
GRAS_NAMES = {'princeton': 'Princeton University', 'cmu': 'Carnegie Mellon University', 'epfl': 'Swiss Federal Institute of Technology Lausanne',
              'mit': 'Massachusetts Institute of Technology', 'berkeley': 'University of California, Berkeley', 'stanford': 'Stanford University',
              'michigan': 'University of Michigan, Ann Arbor', 'uchicago': 'University of Chicago', 'gatech': 'Georgia Institute of Technology',
              'harvard': 'Harvard University', 'jhu': 'Johns Hopkins University', 'washu': 'Washington University in St Louis'}


def name_tokens(s):
    s = unicodedata.normalize('NFKD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    return [t for t in re.sub(r'[^a-z0-9 ]', ' ', s.replace('-', ' ')).split() if t]


def same_person(a, b):
    """Name match inside one lab: same surname (last token) and compatible given name (same initial; full given names must be equal or one a prefix of the other)."""
    a, b = name_tokens(a), name_tokens(b)
    if len(a) < 2 or len(b) < 2 or a[-1] != b[-1] or a[0][0] != b[0][0]:
        return False
    if len(a[0]) > 1 and len(b[0]) > 1:
        return a[0] == b[0] or a[0].startswith(b[0]) or b[0].startswith(a[0])
    return True


def led_class(position, byline, pi_names, student_names):
    """pi_led / student_led / other from the PI's author position, the byline list, the PI's names and the lab's student names."""
    first = byline[0] if byline else None
    if position == 'first' or (position is None and first and any(same_person(first, n) for n in pi_names)):
        return 'pi_led'
    if first and any(same_person(first, n) for n in student_names):
        return 'student_led'
    return 'other'


def gras_bands(scratch_tsv):
    """{school: (rank_text, lower bound, band)} from the GRAS 2025 CS&E top-300 file."""
    ranks = {}
    for line in scratch_tsv.read_text().splitlines()[1:]:
        r, name, _ = (line.split('\t') + ['', '', ''])[:3]
        ranks[name] = r
    out = {}
    for s, nm in GRAS_NAMES.items():
        r = ranks[nm]
        lo = int(r.split('-')[0])
        out[s] = (r, lo, 'top10' if lo <= 10 else 'r11_50' if lo <= 50 else 'r51_300')
    return out


def career_first_year(years, min_works=1):
    """First year with a cumulative count of at least min_works works (years: {year: count})."""
    cum = 0
    for y in sorted(int(k) for k in years):
        cum += years[str(y)] if str(y) in years else years[y]
        if cum >= min_works:
            return y
    return None


def tier(age, cuts):
    if age is None or pd.isna(age):
        return None
    return 'early' if age < cuts[0] else ('mid' if age <= cuts[1] else 'senior')


def appt_start(periods):
    ys = [int(str(p.get('start'))[:4]) for p in periods or [] if str(p.get('start') or '')[:4].isdigit()]
    return min(ys) if ys else None


def handcheck_samples(d, hdir, seed=HANDCHECK_SEED):
    """Stratified random samples for the analyst's hand check: 30 papers for the field map (7/8/8/7 theory/systems/ml_ai/other), 20 for the led split (7/7/6).
    Written once; an existing sample file is never overwritten so the hand labels stay attached to the same rows."""
    rng = np.random.default_rng(seed)
    for name, col, plan in (('field', 'field', {'theory': 7, 'systems': 8, 'ml_ai': 8, 'other': 7}), ('led', 'led', {'pi_led': 7, 'student_led': 7, 'other': 6})):
        f = hdir / f'{name}_handcheck_sample.csv'
        if f.exists():
            continue
        parts = []
        for g, n in plan.items():
            pool = d[d[col] == g].drop_duplicates('k').sort_values('k')
            parts.append(pool.iloc[rng.choice(len(pool), n, replace=False)])
        cols = ['k', 'school', 'pi', 'year', col, 'field_source', 'venue', 'title', 'first_author', 'pi_position']
        pd.concat(parts)[cols].rename(columns={col: 'assigned'}).to_csv(f, index=False)


def build(snap, out, code_root, scratch):
    hdir = out / 'heterogeneity' / 'work'
    hdir.mkdir(parents=True, exist_ok=True)
    venues = json.loads((code_root / 'hierarchy' / 'reviewed' / 'cs-venues.json').read_text())
    cs = {HF.norm_venue(v['name']) for v in venues}
    pd.DataFrame([dict(name=v['name'], lab_papers=v['lab_papers'], area=HF.venue_area(v['name'])) for v in venues]).to_csv(hdir / 'venue_map.csv', index=False)
    pan = pd.read_parquet(out / 'work' / 'panel.parquet', columns=['k', 'topic_name', 'topic_sub', 'topic_field']).drop_duplicates('k').set_index('k')
    db = sqlite3.connect(f'file:{snap / "universe" / "oa_extra.sqlite"}?mode=ro', uri=True)
    src = dict(db.execute('select id, source_name from works where source_name is not null'))
    db.close()
    career = {}
    cf = hdir / 'pi_career.jsonl'
    if cf.exists():
        for r in map(json.loads, cf.read_text().splitlines()):
            career[(r['school'], r['pi'])] = r
    gr = gras_bands(scratch / 'cs-rankings' / GRAS_FILE)
    rows, pirows = [], []
    for s in C.SCHOOLS:
        hd = snap / 'release' / 'hierarchy' / s
        pis = {q['pi']: q for q in json.loads((hd / 'pis.json').read_text())}
        stu = {}
        for pi, lst in json.loads((hd / 'students.json').read_text()).items():
            stu.setdefault(pi, set()).update(x['name'] for x in lst if x.get('name') and STUDENT_ROLE.search(' '.join(x.get('roles') or [])))
        for line in gzip.open(hd / 'student_papers.jsonl.gz', 'rt'):
            r = json.loads(line)
            stu.setdefault(r['pi'], set()).update(x for x in (r.get('name'), r.get('byline')) if x)
        for pi, q in pis.items():
            c = career.get((s, pi))
            fy1 = career_first_year(c['years'], 1) if c and c['years'] else None
            fy2 = career_first_year(c['years'], 2) if c and c['years'] else None
            pirows.append(dict(school=s, pi=pi, lab_id=q.get('labId') or f'atl:l:{s}:{pi}', first_pub_any=fy1, first_pub_2plus=fy2, appt_start=appt_start(q.get('periods')),
                               n_students=len(stu.get(pi, ())), author_ids=(c or {}).get('n_ids'), career_basis=(c or {}).get('basis')))
        for line in gzip.open(hd / 'lab_papers.jsonl.gz', 'rt'):
            r = json.loads(line)
            y = r.get('year')
            if not y or not C.FIRST <= y <= C.LAST:
                continue
            k = C.oa_short(r.get('oa')) or r.get('atlasWorkId')
            if not k:
                continue
            q = pis.get(r['pi'], {})
            names = set(q.get('names') or []) | {r['pi']}
            led = led_class((r.get('authorship') or {}).get('position'), r.get('byline'), names, stu.get(r['pi'], set()))
            tn = pan['topic_name'].get(k) if k in pan.index else None
            ts = pan['topic_sub'].get(k) if k in pan.index else None
            tf = pan['topic_field'].get(k) if k in pan.index else None
            field, alt, fsrc = HF.classify([r.get('venue'), src.get(k)], cs, tn, ts, tf)
            rows.append((k, s, q.get('labId') or f'atl:l:{s}:{r["pi"]}', r['pi'], int(y), led, field, alt, fsrc, r.get('venue') or src.get(k), r.get('title') or '',
                         (r.get('byline') or [''])[0], (r.get('authorship') or {}).get('position')))
    d = pd.DataFrame(rows, columns=['k', 'school', 'lab_id', 'pi', 'year', 'led', 'field', 'field_alt', 'field_source', 'venue', 'title', 'first_author', 'pi_position'])
    d = d.drop_duplicates(['k', 'lab_id'])
    pa = pd.DataFrame(pirows)
    pa['age_any'] = REF_YEAR - pa['first_pub_any']
    pa['age_2plus'] = REF_YEAR - pa['first_pub_2plus']
    pa['appt_years'] = REF_YEAR - pa['appt_start']
    pa['career'] = pa['age_any'].map(lambda a: tier(a, CAREER_CUTS))
    for nm, cuts in CAREER_ALT.items():
        pa['career_' + nm] = pa['age_any'].map(lambda a, cuts=cuts: tier(a, cuts))
    pa['career_2plus'] = pa['age_2plus'].map(lambda a: tier(a, CAREER_CUTS))
    pa['career_appt'] = pa['appt_years'].map(lambda a: None if pd.isna(a) else ('early' if a < APPT_CUTS[0] else ('mid' if a <= APPT_CUTS[1] else 'senior')))
    d = d.merge(pa.drop(columns=['pi', 'school']), on='lab_id', how='left')
    d['gras'] = d['school'].map({s: v[2] for s, v in gr.items()})
    pa.to_csv(hdir / 'pi_attr.csv', index=False)
    pd.DataFrame([dict(school=s, gras_rank=v[0], gras_band=v[2], partial=s in C.PARTIAL) for s, v in gr.items()]).to_csv(hdir / 'school_tiers.csv', index=False)
    d.to_parquet(hdir / 'hetero_papers.parquet')
    handcheck_samples(d, hdir.parent)
    return d, pa


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', default='2026-11-08')
    a = ap.parse_args()
    from pathlib import Path
    d, pa = build(C.snapshot_dir(a.id), C.results_dir(a.id), Path(C.P.CODE), Path(C.P.SCRATCH))
    print(json.dumps({'rows': len(d), 'papers': int(d.k.nunique()), 'led': d.led.value_counts().to_dict(), 'field': d.field.value_counts().to_dict(),
                      'field_source': d.field_source.value_counts().to_dict(), 'career': pa.career.value_counts(dropna=False).to_dict()}))
