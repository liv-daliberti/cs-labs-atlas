"""Where the missing lab-paper copies are (2026-11-04): per school and ledger reason, and the two big groups
(publisher_only_closed, landing_page_without_pdf) by publisher, venue and the host of the attempted URLs; the
open-proceedings venues (CVF, PMLR, NeurIPS, ACL, USENIX, ...) and the open-archive DOI prefixes (Zenodo, OSF, ...)
by reason. Read-only: it reads hierarchy/<school>/derived/unavailable.jsonl.gz (the unavailability ledger,
docs/UNAVAILABLE.md) and writes nothing unless --json is given.
usage: missing_breakdown.py [--schools a,b,...] [--top 30] [--json out.json]
"""
import argparse, gzip, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import atlas_paths as P  # noqa: E402

SCHOOLS = ['berkeley', 'cmu', 'epfl', 'mit', 'michigan', 'princeton', 'stanford']
BIG = ('publisher_only_closed', 'landing_page_without_pdf')
VENUES = {
    'CVF (CVPR/ICCV/WACV)': r'computer vision and pattern|international conference on computer vision|winter conference on applications|CVPR|ICCV|WACV',
    'PMLR (ICML/AISTATS/COLT/CoRL)': r'international conference on machine learning|artificial intelligence and statistics|conference on learning theory|robot learning|ICML|AISTATS|\bCOLT\b|proceedings of machine learning',
    'NeurIPS': r'neural information processing|NeurIPS|NIPS', 'ICLR': r'learning representations|ICLR',
    'ACL Anthology': r'computational linguistics|empirical methods in natural|\bACL\b|EMNLP|NAACL|CoNLL',
    'USENIX': r'usenix|OSDI|NSDI|operating systems design|networked systems design', 'AAAI': r'AAAI|association for the advancement of artificial',
    'IJCAI': r'IJCAI|joint conference on artificial intelligence', 'JMLR/TMLR': r'journal of machine learning research|transactions on machine learning research',
    'LIPIcs': r'leibniz|lipics|dagstuhl', 'VLDB': r'very large data|VLDB', 'SIGPLAN': r'POPL|PLDI|OOPSLA|principles of programming|programming language design',
    'HICSS': r'HICSS|system sciences'}
PREFIXES = {'10.5281': 'Zenodo', '10.31234': 'PsyArXiv', '10.31219': 'OSF Preprints', '10.31235': 'SocArXiv', '10.35542': 'EdArXiv', '10.17605': 'OSF',
            '10.1101': 'bioRxiv/medRxiv', '10.21203': 'Research Square', '10.48550': 'arXiv', '10.2139': 'SSRN', '10.1184': 'CMU KiltHub',
            '10.24251': 'HICSS (ScholarSpace)', '10.4230': 'LIPIcs'}


def load(schools):
    for s in schools:
        f = P.HIERARCHY / s / 'derived' / 'unavailable.jsonl.gz'
        if not f.exists():
            continue
        with gzip.open(f, 'rt') as fh:
            for line in fh:
                r = json.loads(line); r['school'] = s
                yield r


def breakdown(recs, top):
    by = defaultdict(Counter); out = {}
    for r in recs:
        by[r['reason_code']][r['school']] += 1
    out['reason_by_school'] = {k: dict(v) for k, v in by.items()}
    for rc in BIG:
        sub = [r for r in recs if r['reason_code'] == rc]
        hosts = Counter()
        for r in sub:
            hs = {urlsplit(a.get('url', '')).netloc for a in r.get('attempts') or []}
            hosts.update(hs or {'(no attempt)'})
        out[rc] = dict(n=len(sub), publisher=Counter(r['publisher'] for r in sub).most_common(top),
                       venue=Counter((r['venue'] or '(none)')[:60] for r in sub).most_common(top), attempt_host=hosts.most_common(top))
    ven = defaultdict(Counter)
    for r in recs:
        v = r.get('venue') or ''
        for k, p in VENUES.items():
            if re.search(p, v, re.I):
                ven[k][r['reason_code']] += 1
    out['open_venues'] = {k: dict(v) for k, v in ven.items()}
    pre = defaultdict(Counter)
    for r in recs:
        p = (r.get('doi') or '').lower().split('/')[0]
        if p in PREFIXES:
            pre[PREFIXES[p]][r['reason_code']] += 1
    out['open_archive_prefixes'] = {k: dict(v) for k, v in pre.items()}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--schools', default=','.join(SCHOOLS)); ap.add_argument('--top', type=int, default=30); ap.add_argument('--json')
    a = ap.parse_args()
    schools = a.schools.split(',')
    recs = list(load(schools))
    out = breakdown(recs, a.top)
    reasons = sorted(out['reason_by_school'], key=lambda k: -sum(out['reason_by_school'][k].values()))
    print('| reason | ' + ' | '.join(schools) + ' | total |\n|' + '---|' * (len(schools) + 2))
    for k in reasons:
        row = [out['reason_by_school'][k].get(s, 0) for s in schools]
        print(f'| {k} | ' + ' | '.join(map(str, row)) + f' | {sum(row)} |')
    for rc in BIG:
        d = out[rc]
        print(f'\n## {rc}: {d["n"]}')
        for key in ('publisher', 'venue', 'attempt_host'):
            print(f'{key}:', '; '.join(f'{k} {n}' for k, n in d[key]))
    for key in ('open_venues', 'open_archive_prefixes'):
        print(f'\n## {key}')
        for k, v in sorted(out[key].items(), key=lambda kv: -sum(kv[1].values())):
            print(f'{k}: {sum(v.values())}  ' + ', '.join(f'{r} {n}' for r, n in sorted(v.items(), key=lambda x: -x[1])[:4]))
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
