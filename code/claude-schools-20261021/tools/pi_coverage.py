"""Per-PI coverage ledger and gate items (owner directive 2026-11-12: "every PI has students; every lab has appropriate lab papers
(tied to the PI) with appropriate student-PI connections").

The stage gates ask school-level questions (precision, recall of a sample, a Z share of PIs without students). This tool asks the owner's
question PI by PI: for each PI of the built package, in each of three dimensions, is there evidence ('present'), a researched reason
('reason') or nothing ('gap')?

  students      graduate-level student rows (PhD / master's / alumni / unspecified-student) that qualify as evidence
  lab_papers    lab_papers.jsonl.gz rows of the PI inside the appointment window
  links         student_papers.jsonl.gz rows of the PI: distinct students linked to a paper of the PI

REPORT-ONLY by default. stage_gate.g5 / g6 call gate_items(key, part); those items are the only thing that can fail a stage, and the bars
are the ONE constant RATCHET_LEVEL below (level 0 = report-only, no school fails, level 3 = the long-term target). Nothing
here writes a reviewed input, relabels a row or touches the recall gate (tools/student_recall.py keeps its own thresholds and record).

Honesty rules baked in
  * 'reason' needs a researched, non-boilerplate reason with >= MIN_SOURCES sources: lab-coverage-reasons.json (students / papers, the
    student_recall.researched_reason standard) or census-overrides no_papers / no_identity text that is individual (a text shared by >= BOILER_REPEAT
    PIs after the name is removed is boilerplate) and names >= MIN_SOURCES distinct sources (URLs / sha256 prefixes) or carries a structured evidence list.
  * a student row from a thesis-only or profile-only source counts only when it is DATED (a year); undated names stay excluded (the strict rule).
  * a reviewed no_identity hold is a 'reason' only if it passes the test above; the Han-name schools' shared-sentence holds do not.

usage: pi_coverage.py report <school|all> [--out DIR] [--json]      write the ledger CSV + JSON of the school(s), print the count table
       pi_coverage.py gaps <school|all> [--out DIR]                 write per-school gap CSVs per dimension, sorted by what would unlock them
       pi_coverage.py gate <school|all> [--level N]                 the gate items at a ratchet level (default RATCHET_LEVEL)
       pi_coverage.py summary [--level N]                           markdown tables: counts by state per school and dimension, gate verdict per level
"""
import argparse
import collections
import csv
import gzip
import json
import re
import sys
from pathlib import Path

import atlas_paths as P  # noqa: E402
import census_overrides as CO  # noqa: E402
import student_recall as R  # noqa: E402  (read-only helpers: role/source classes, researched_reason)

SCHOOLS = ('mit', 'tsinghua', 'stanford', 'berkeley', 'sjtu', 'hkust', 'princeton', 'cmu', 'zju', 'ntu')

# ---- THE BARS: every number the PI-coverage gate uses lives here (owner sets RATCHET_LEVEL) -------------------------------------------------
# GAP SHARE bars: the largest share of a school's PIs that may be in 'gap' in a dimension (the rest are present or have a researched reason).
RATCHET_LEVELS = (
    dict(lab_papers=1.00, students=1.00, links=1.00),   # level 0: REPORT-ONLY, no school can fail (today's worst: ZJU 93% / 97% / 100%); the gate line still carries the counts
    dict(lab_papers=0.50, students=0.60, links=0.80),   # level 1: the Han-name schools must have shipped real identities / rosters for about half their PIs
    dict(lab_papers=0.20, students=0.25, links=0.40),   # level 2
    dict(lab_papers=0.05, students=0.05, links=0.15),   # level 3: the long-term target (owner may tighten toward 2% / 5%)
)
RATCHET_LEVEL = 1   # owner 2026-11-17 (D-0001, Q-0125-0127): level 1 now, target level 3


def bars(level=None):
    return dict(RATCHET_LEVELS[RATCHET_LEVEL if level is None else level])


# EVIDENCE thresholds (per PI)
ACTIVE_FROM_YEAR = 2025        # a PI whose appointment reaches this year is active
STUDENTS_MIN_ACTIVE = 3        # graduate-level student rows an active PI needs
STUDENTS_MIN_INACTIVE = 1      # a PI who left or retired before ACTIVE_FROM_YEAR needs at least one (alumni)
LABP_MIN = 3                   # lab papers inside the appointment (any PI with an appointment of >= 1 year)
LABP_PER_YEAR = 0.5            # ... and at least this many papers per appointment year (capped at LABP_YEAR_CAP years, rounded up)
LABP_YEAR_CAP = 6
LINKS_MIN = 2                  # distinct students linked to a paper of the PI (or all of them when the PI has fewer qualifying students)
MIN_SOURCES = R.MIN_SOURCES_FOR_REASON
BOILER_REPEAT = 3              # an override reason text shared (name removed) by this many PIs is boilerplate
WINDOW_DEFAULT = (2016, 2026)
GRAD_ROLES = ('phd', 'masters', 'alumni', 'student_unspecified')

URL_RE = re.compile(r'https?://[^\s,;)\]"\']+')
SHA_RE = re.compile(r'sha256[: ]+([0-9a-f]{12,64})|\b[0-9a-f]{40,64}\b')


# ---- data -------------------------------------------------------------------------------------------------------------------------------------
def _read(p, default=None):
    return R._read(p, default)


def _pis(key):
    d = _read(P.data('pis.json', key), [])
    return d if isinstance(d, list) else d.get('pis', [])


def _rows_by_pi(path):
    out = collections.defaultdict(list)
    p = Path(path)
    if p.exists():
        with gzip.open(p, 'rt') as f:
            for line in f:
                r = json.loads(line)
                out[r.get('pi')].append(r)
    return out


def appointment_years(p, window):
    """The years the PI's appointment covers inside the window: union of reviewed periods (dates), else first..last listing year."""
    lo, hi = window
    ys = set()
    for per in p.get('periods') or []:
        s, e = str(per.get('start') or '')[:4], str(per.get('end') or '')[:4]
        if s.isdigit():
            ys.update(range(int(s), (int(e) if e.isdigit() else hi) + 1))
    if not ys:
        ly = sorted({int(x['year']) for x in (p.get('listings') or []) if isinstance(x.get('year'), int)} |
                    {int(x['year']) for x in (p.get('listingsAfterMove') or []) if isinstance(x, dict) and isinstance(x.get('year'), int)})
        if ly:
            ys = set(range(ly[0], ly[-1] + 1))
    return sorted(y for y in ys if lo <= y <= hi)


def norm_reason(text, names):
    t = str(text or '')
    for n in sorted(names, key=len, reverse=True):
        if n:
            t = t.replace(n, '<PI>')
    t = re.sub(r'\d+', '#', t)
    return re.sub(r'\s+', ' ', t).strip().lower()   # the WHOLE text: a shared prefix with a PI-specific tail is not boilerplate


def count_sources(text, structured=None):
    s = set(URL_RE.findall(str(text or ''))) | {m.group(0)[:16] for m in SHA_RE.finditer(str(text or ''))}
    return max(len(s), len(structured or []))


def _override_texts(ov):
    """{pi: [(kind, text, structured_sources)]} from census-overrides: no_identity+why_no_identity, no_papers+why_no_papers."""
    out = collections.defaultdict(list)
    for name, o in ov.items():
        if o.get('no_identity') and o.get('why_no_identity'):
            out[name].append(('no_identity', o['why_no_identity'], o.get('no_identity_sources') or o.get('why_no_identity_sources')))
        if o.get('no_papers') and o.get('why_no_papers'):
            out[name].append(('no_papers', o['why_no_papers'], o.get('no_papers_sources')))
    return out


class School:
    """All the inputs of one school, read once."""

    def __init__(self, key):
        self.key = key
        self.pis = _pis(key)
        self.students = R._students(key)
        self.reasons = R._reasons(key)
        self.overrides = CO.section(key)
        self.lab = _rows_by_pi(P.data('lab_papers.jsonl.gz', key))
        self.links = _rows_by_pi(P.data('student_papers.jsonl.gz', key))
        w = _read(P.data('lab-websites.json', key), {}) or {}
        self.websites = {r['pi']: r for r in w.get('labs', [])}
        try:
            import school_config as S
            self.window = tuple(S.get(key).get('window') or WINDOW_DEFAULT)
        except Exception:
            self.window = WINDOW_DEFAULT
        texts = _override_texts(self.overrides)
        self.override_texts = texts
        names = {p['pi']: set([p['pi']] + list(p.get('names') or [])) for p in self.pis}
        self.repeat = collections.Counter(norm_reason(t, names.get(n, {n})) for n, xs in texts.items() for _, t, _ in xs)
        self.names = names
        self.few = {x.get('pi'): x for x in (_read(P.data('few-students-evidence.json', key), []) or []) if isinstance(x, dict)}


# ---- classification ---------------------------------------------------------------------------------------------------------------------------
def website_class(w):
    """no_website | host_off_limits | site_dead | website_found | none (no register row)."""
    if not w:
        return 'unregistered'
    rc = w.get('reason_code') or ''
    if rc in ('host_blocked_by_robots', 'host_challenge_no_wayback'):
        return 'host_off_limits'
    if rc in ('site_dead_no_wayback',):
        return 'site_dead'
    if w.get('status', '').startswith('reviewed_live') or w.get('status') == 'found' or w.get('coverage') == 'website':
        return 'website_found'
    return 'no_website'


def student_facts(rows):
    cls = collections.Counter()
    qual = cur = alum = phd = cur_phd = dated = thesis_profile_undated = withheld = 0
    for r in rows:
        rc = R.role_class(r)
        cls[rc] += 1
        if rc not in GRAD_ROLES:
            continue
        y = R.max_year(r)
        src = R.source_class(r)
        weak = bool(src) and src <= {'thesis', 'profile'}
        if y is None and (weak or not src):
            thesis_profile_undated += 1   # strict rule: undated names from thesis/profile-only sources do not count
            continue
        qual += 1
        dated += y is not None
        phd += rc == 'phd'
        is_alum = rc == 'alumni' or (y is not None and y < R.CURRENT_FROM_YEAR)
        alum += is_alum
        cur += not is_alum
        cur_phd += (not is_alum) and rc == 'phd'
        withheld += R.withheld(r)
    return dict(rows=len(rows), qualifying=qual, current=cur, alumni=alum, phd=phd, current_phd=cur_phd, dated=dated,
                excluded_undated_weak=thesis_profile_undated, role_mix=dict(cls))


def reason_ok(S, pi, kinds):
    """The researched reason a PI may carry for a dimension, or None. kinds: ('students',) / ('papers',) / ('links',)."""
    for k in kinds:
        s = (S.reasons.get(pi) or {}).get(k) or {}
        why = str(s.get('why') or '')
        if s and why and not why.startswith(R.BOILERPLATE) and len(s.get('sources_checked') or []) >= MIN_SOURCES:
            return dict(source='lab-coverage-reasons', kind=k, code=s.get('code'), why=why[:300])
    return None


def identity_reason(S, pi, kinds=('no_papers', 'no_identity')):
    """(reason|None, boilerplate_flag) from census-overrides texts: individual and >= MIN_SOURCES sources."""
    boiler = False
    for kind, text, struct in S.override_texts.get(pi, []):
        if kind not in kinds:
            continue
        shared = S.repeat[norm_reason(text, S.names.get(pi, {pi}))] >= BOILER_REPEAT
        if shared:
            boiler = True
            continue
        if count_sources(text, struct) >= MIN_SOURCES:
            return dict(source='census-overrides', kind=kind, why=str(text)[:300]), boiler
        boiler = boiler or kind == 'no_identity'
    return None, boiler


def build_row(S, p):
    pi = p['pi']
    window = S.window
    appt = appointment_years(p, window)
    active = bool(appt) and appt[-1] >= ACTIVE_FROM_YEAR
    anchors = [k for k, v in (('dblp', p.get('dblp')), ('orcid', p.get('orcid')), ('openalex', p.get('reviewedOpenAlex'))) if v]
    hold = (p.get('identityHold') or {}).get('status')
    ov = S.overrides.get(pi) or {}
    row = dict(school=S.key, pi=pi, depts='|'.join(p.get('departments') or []), rank=p.get('rank'), title=p.get('title'),
               appt_from=appt[0] if appt else None, appt_to=appt[-1] if appt else None, appt_years=len(appt), active=active)
    # ---- identity
    row.update(anchors='+'.join(anchors) or None, oa_author_ids=len(p.get('oaAuthorIds') or []), identity_hold=hold,
               no_identity=bool(ov.get('no_identity') or hold == 'reviewed_no_identity'))
    # ---- lab papers
    lp = S.lab.get(pi, [])
    in_appt = [r for r in lp if r.get('year') in set(appt)] if appt else lp
    years_with = sorted({r['year'] for r in lp if isinstance(r.get('year'), int)})
    cov = sorted({r['year'] for r in in_appt if isinstance(r.get('year'), int)})
    need = max(LABP_MIN, -(-int(LABP_PER_YEAR * 2 * min(len(appt), LABP_YEAR_CAP)) // 2)) if appt else LABP_MIN
    row.update(lab_papers=len(lp), lab_papers_in_appointment=len(in_appt), lab_years=len(cov), lab_years_first=cov[0] if cov else None,
               lab_years_last=cov[-1] if cov else None, lab_papers_needed=need)
    # ---- students
    sf = student_facts(S.students.get(pi, []))
    row.update(student_rows=sf['rows'], students_qualifying=sf['qualifying'], students_current=sf['current'], students_alumni=sf['alumni'],
               students_phd=sf['phd'], students_current_phd=sf['current_phd'], students_dated=sf['dated'],
               students_excluded_undated_weak=sf['excluded_undated_weak'])
    need_s = STUDENTS_MIN_ACTIVE if active else STUDENTS_MIN_INACTIVE
    row['students_needed'] = need_s
    # ---- links
    ln = S.links.get(pi, [])
    linked = {r.get('student') for r in ln if r.get('student')}
    row.update(link_rows=len(ln), links_students=len(linked), links_works=len({r.get('oa') or r.get('work') for r in ln}),
               links_verified=sum(1 for r in ln if r.get('status') == 'verified'),
               links_needed=min(LINKS_MIN, sf['qualifying']) if sf['qualifying'] else LINKS_MIN)
    # ---- website
    w = S.websites.get(pi)
    wc = website_class(w)
    row.update(website=wc, website_kind=(w or {}).get('kind'), website_reason_code=(w or {}).get('reason_code'), website_url=(w or {}).get('url'))

    # ---- states
    idr, idr_boiler = identity_reason(S, pi)
    pr = reason_ok(S, pi, ('papers',)) or idr
    row['identity_status'] = ('anchored_yields' if anchors and lp else 'anchored_zero_papers' if anchors else
                              'hold_researched' if idr and idr['kind'] == 'no_identity' else
                              'hold_boilerplate' if row['no_identity'] else 'no_anchor')
    # lab papers
    if len(in_appt) >= need:
        row['lab_state'], row['lab_cause'], row['lab_reason'] = 'present', None, None
    elif pr:
        row['lab_state'], row['lab_cause'], row['lab_reason'] = 'reason', pr.get('code') or pr['kind'], pr['why']
    else:
        row['lab_state'] = 'gap'
        row['lab_reason'] = None
        if not anchors and not p.get('oaAuthorIds'):
            row['lab_cause'] = 'no_identity_anchor_boilerplate_hold' if idr_boiler or row['no_identity'] else 'no_identity_anchor'
        elif lp and not in_appt:
            row['lab_cause'] = 'papers_outside_appointment'
        elif not lp and appt and appt[0] >= ACTIVE_FROM_YEAR:
            row['lab_cause'] = 'appointment_window_too_new'
        elif not lp:
            row['lab_cause'] = 'anchor_yields_0_papers'
        else:
            row['lab_cause'] = 'thin_lab_papers'
    # students
    sr = reason_ok(S, pi, ('students',))
    if sf['qualifying'] >= need_s:
        row['students_state'], row['students_cause'], row['students_reason'] = 'present', None, None
    elif sr:
        row['students_state'], row['students_cause'], row['students_reason'] = 'reason', sr.get('code') or sr['kind'], sr['why']
    else:
        row['students_state'] = 'gap'
        row['students_reason'] = None
        weak = sf['excluded_undated_weak'] and not sf['qualifying']
        boiler = str(((S.reasons.get(pi) or {}).get('students') or {}).get('why') or '').startswith(R.BOILERPLATE)
        if sf['qualifying']:
            c = 'thin_students'
        elif weak:
            c = 'only_undated_thesis_or_profile_rows'
        elif wc == 'host_off_limits':
            c = 'website_host_off_limits'
        elif wc in ('no_website', 'unregistered', 'site_dead'):
            c = 'no_website' if wc != 'site_dead' else 'website_dead'
        elif wc == 'website_found':
            c = 'website_without_members'
        else:
            c = 'no_student_evidence'
        row['students_cause'] = ('boilerplate_reason_' + c) if boiler else c
    # links
    lr = reason_ok(S, pi, ('links',))
    if row['links_students'] >= row['links_needed'] and sf['qualifying']:
        row['links_state'], row['links_cause'], row['links_reason'] = 'present', None, None
    elif lr:
        row['links_state'], row['links_cause'], row['links_reason'] = 'reason', lr.get('code') or lr['kind'], lr['why']
    elif row['students_state'] == 'reason' and not sf['qualifying']:
        row['links_state'], row['links_cause'], row['links_reason'] = 'reason', 'inherits_students_reason', row['students_reason']
    else:
        row['links_state'] = 'gap'
        row['links_reason'] = None
        if not sf['qualifying']:
            row['links_cause'] = 'no_students'
        elif row['lab_state'] != 'present' and not lp:
            row['links_cause'] = 'no_lab_papers'
        elif row['link_rows']:
            row['links_cause'] = 'thin_links'
        else:
            row['links_cause'] = 'students_without_paper_links'
    return row


def ledger(key):
    S = School(key)
    return [build_row(S, p) for p in S.pis]


DIMS = (('lab_papers', 'lab'), ('students', 'students'), ('links', 'links'))
CAUSE_ORDER = {   # what would unlock the PI soonest first (low = cheaper); the gaps CSVs sort by this
    'lab': ['appointment_window_too_new', 'papers_outside_appointment', 'thin_lab_papers', 'anchor_yields_0_papers', 'no_identity_anchor',
            'no_identity_anchor_boilerplate_hold'],
    'students': ['thin_students', 'website_without_members', 'only_undated_thesis_or_profile_rows', 'no_student_evidence', 'no_website',
                 'website_dead', 'website_host_off_limits'],
    'links': ['thin_links', 'students_without_paper_links', 'no_lab_papers', 'no_students'],
}


def cause_rank(dim, cause):
    base = (cause or '').replace('boilerplate_reason_', '')
    order = CAUSE_ORDER[dim]
    return (order.index(base) if base in order else len(order)) + (0.5 if (cause or '').startswith('boilerplate_reason_') else 0)


def counts(rows):
    out = {}
    for dim, pre in DIMS:
        c = collections.Counter(r[pre + '_state'] for r in rows)
        out[dim] = {s: c.get(s, 0) for s in ('present', 'reason', 'gap')}
        out[dim]['causes'] = dict(collections.Counter(r[pre + '_cause'] for r in rows if r[pre + '_state'] == 'gap').most_common())
    return out


# ---- gate -------------------------------------------------------------------------------------------------------------------------------------
GATE_PARTS = {'papers': ('lab_papers',), 'students': ('students', 'links')}   # stage 5 -> papers; stage 6 -> students + links
_CACHE = {}


def _counts_cached(key):
    if key not in _CACHE:
        _CACHE[key] = (counts(ledger(key)), len(_pis(key)))
    return _CACHE[key]


def ratchet_text(level=None):
    """'level 0 of 3: gap share <= 100% lab papers, ...; next level 1: ...' (the last level says it is the target)."""
    lv = RATCHET_LEVEL if level is None else level

    def fmt(b):
        return ', '.join(f'{d} <= {b[d]:.0%}' for d in b)
    out = f'ratchet level {lv} of {len(RATCHET_LEVELS) - 1}: gap share {fmt(RATCHET_LEVELS[lv])}'
    return out + (f'; next level {lv + 1}: {fmt(RATCHET_LEVELS[lv + 1])}' if lv + 1 < len(RATCHET_LEVELS) else '; this is the long-term target level')


def stage_summary(key):
    """One line: gap counts per dimension."""
    c, n = _counts_cached(key)
    return f'{key}: {n} PIs; gap ' + ', '.join(f'{d} {c[d]["gap"]}' for d, _ in DIMS) + ' (reason ' + ', '.join(f'{d} {c[d]["reason"]}' for d, _ in DIMS) + ')'


def gate_items(key, part, level=None):
    """Gate findings of one part ('papers' for stage 5, 'students' for stage 6) at a ratchet level; [] without a built package."""
    if not _pis(key):
        return []
    c, n = _counts_cached(key)
    b = bars(level)
    items = []
    for dim in GATE_PARTS[part]:
        gap = c[dim]['gap']
        if n and gap / n > b[dim]:
            top = ', '.join(f'{k} {v}' for k, v in list(c[dim]['causes'].items())[:3])
            items.append(f'PI coverage {dim}: {gap} of {n} PIs ({gap / n:.0%}) have neither evidence nor a researched reason (> {b[dim]:.0%}; ratchet level '
                         f'{RATCHET_LEVEL if level is None else level} of {len(RATCHET_LEVELS) - 1}); top causes: {top}. {ratchet_text(level)}; all dimensions: {stage_summary(key)}. Ledger: pi_coverage.py report {key}')
    return items


def gate_counts(key):
    if not _pis(key):
        return {}
    c, n = _counts_cached(key)
    return {f'pi_cov_{d}_gap': c[d]['gap'] for d, _ in DIMS}


# ---- output -----------------------------------------------------------------------------------------------------------------------------------
def default_out():
    return Path(P.ROOT) / 'scratch' / 'pi-coverage-1112'


COLS = ['school', 'pi', 'depts', 'rank', 'title', 'active', 'appt_from', 'appt_to', 'appt_years',
        'anchors', 'oa_author_ids', 'identity_hold', 'identity_status',
        'student_rows', 'students_qualifying', 'students_current', 'students_alumni', 'students_phd', 'students_current_phd', 'students_dated',
        'students_excluded_undated_weak', 'students_needed', 'students_state', 'students_cause', 'students_reason',
        'lab_papers', 'lab_papers_in_appointment', 'lab_years', 'lab_years_first', 'lab_years_last', 'lab_papers_needed', 'lab_state', 'lab_cause', 'lab_reason',
        'link_rows', 'links_students', 'links_works', 'links_verified', 'links_needed', 'links_state', 'links_cause', 'links_reason',
        'website', 'website_kind', 'website_reason_code', 'website_url']


def write_ledger(key, out):
    rows = ledger(key)
    d = Path(out) / 'ledger'
    d.mkdir(parents=True, exist_ok=True)
    with open(d / f'{key}-pi-coverage.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, COLS, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)
    (d / f'{key}-pi-coverage.json').write_text(json.dumps(dict(school=key, window=School(key).window, thresholds=thresholds(), counts=counts(rows),
                                                              rows=rows), ensure_ascii=False, indent=1))
    return rows


def write_gaps(key, out):
    rows = ledger(key)
    d = Path(out) / 'gaps'
    d.mkdir(parents=True, exist_ok=True)
    for dim, pre in DIMS:
        gaps = sorted((r for r in rows if r[pre + '_state'] == 'gap'), key=lambda r: (cause_rank(pre, r[pre + '_cause']), r['pi']))
        with open(d / f'{key}-{dim}-gaps.csv', 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['school', 'pi', 'cause', 'active', 'appt_from', 'appt_to', 'anchors', 'identity_status', 'students_qualifying', 'lab_papers_in_appointment',
                        'links_students', 'website', 'website_reason_code', 'website_url'])
            for r in gaps:
                w.writerow([key, r['pi'], r[pre + '_cause'], r['active'], r['appt_from'], r['appt_to'], r['anchors'], r['identity_status'], r['students_qualifying'],
                            r['lab_papers_in_appointment'], r['links_students'], r['website'], r['website_reason_code'], r['website_url']])
    return rows


def thresholds():
    return dict(active_from_year=ACTIVE_FROM_YEAR, students_min_active=STUDENTS_MIN_ACTIVE, students_min_inactive=STUDENTS_MIN_INACTIVE,
                lab_papers_min=LABP_MIN, lab_papers_per_year=LABP_PER_YEAR, lab_year_cap=LABP_YEAR_CAP, links_min=LINKS_MIN, min_sources=MIN_SOURCES,
                boiler_repeat=BOILER_REPEAT, ratchet_level=RATCHET_LEVEL, bars=bars())


def table(keys):
    lines = ['| school | PIs | dimension | present | reason | gap | gap share |', '|---|---|---|---|---|---|---|']
    for k in keys:
        c, n = _counts_cached(k)
        for dim, _ in DIMS:
            x = c[dim]
            lines.append(f'| {k} | {n} | {dim} | {x["present"]} | {x["reason"]} | {x["gap"]} | {x["gap"] / n:.0%} |')
    return '\n'.join(lines)


def verdicts(keys, level):
    lines = ['| school | ' + ' | '.join(d for d, _ in DIMS) + ' |', '|---|---|---|---|']
    for k in keys:
        c, n = _counts_cached(k)
        b = bars(level)
        lines.append(f'| {k} | ' + ' | '.join(('FAIL ' if c[d]['gap'] / n > b[d] else 'ok ') + f'{c[d]["gap"] / n:.0%}/{b[d]:.0%}' for d, _ in DIMS) + ' |')
    return '\n'.join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('cmd', choices=['report', 'gaps', 'gate', 'summary'])
    ap.add_argument('school', nargs='?', default='all')
    ap.add_argument('--out')
    ap.add_argument('--level', type=int)
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    keys = list(SCHOOLS) if a.school == 'all' else [a.school]
    out = a.out or default_out()
    if a.cmd == 'summary':
        print(table(keys))
        for lv in range(len(RATCHET_LEVELS)):
            print(f'\nlevel {lv}: bars {RATCHET_LEVELS[lv]}\n' + verdicts(keys, lv))
        return 0
    rc = 0
    for k in keys:
        if a.cmd == 'report':
            write_ledger(k, out)
        elif a.cmd == 'gaps':
            write_gaps(k, out)
        elif a.cmd == 'gate':
            for part in GATE_PARTS:
                for it in gate_items(k, part, a.level):
                    print(f'{k}: {it}')
                    rc = 1
            continue
        c, n = _counts_cached(k)
        if not a.json:
            print('STAGE SUMMARY ' + stage_summary(k) + '; ' + ratchet_text())
        print(json.dumps(dict(school=k, pis=n, **{d: {s: c[d][s] for s in ('present', 'reason', 'gap')} for d, _ in DIMS}), ensure_ascii=False) if a.json
              else f'{k}: {n} PIs ' + '; '.join(f'{d} present {c[d]["present"]} reason {c[d]["reason"]} gap {c[d]["gap"]}' for d, _ in DIMS))
    return rc


if __name__ == '__main__':
    sys.exit(main())
