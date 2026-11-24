"""PhD news and defense pages (UChicago round 2, 2026-11-05): read every defense- or PhD-type page of the department news/event spaces through Wayback
and keep the sentences that name a census PI together with an advising word, for a hand read (a page names the student, the adviser and the year in
its own words; wiring is by hand from the quotes, never from this scan).
Why a new scan: tools/defense_scan.py matched a PI name anywhere on the page, and every page carries the department's sidebar (names of professors in
the news column), so its hits were chrome. Here only sentences of the page BODY count (the text after the page title up to the 'Related' / footer
markers) and the sentence must hold an advising word (advis, supervis, dissertation, thesis, PhD).
Every request goes through listings/scripts/wb.py (host_throttle's shared clock and 429 cooldown). Pages already stored are not fetched again.
usage: defense_pages.py <school> <out.json> [--max N] [--kinds news,events] [--hosts cs,stat,cam]"""
import json
import re
import sys

import atlas_paths as P  # noqa: E402
import school_web as W  # noqa: E402

EV = re.compile(r'defen[cs]e|dissertation|thesis|ph-?d|doctoral|candidacy|proposal|oral-exam', re.I)
NW = re.compile(r'ph-?d|doctoral|dissertation|defend|graduat|alumn|degree|fellow|award|prize|commencement|student|advis', re.I)
ADV = re.compile(r'advis|supervis|dissertation|thesis|ph\.?\s?d|doctoral', re.I)
STOP = re.compile(r'\b(?:Related (?:News|Articles|Stories)|More News|Latest News|Footer|Share this)\b')
HOSTS = {'cs': 'cs.uchicago.edu', 'stat': 'stat.uchicago.edu', 'cam': 'cam.uchicago.edu'}


def body(text):
    """The page's own words: from the first long run after the navigation to the first 'related' marker."""
    m = STOP.search(text)
    return text[:m.start()] if m else text


def main(school, out, mx, kinds, hosts):
    c = W.con(school)
    pis = json.loads(P.data('pis.json', school).read_text())
    forms = []
    for p in pis:
        for n in dict.fromkeys([p['pi']] + list(p.get('names') or [])):
            n = re.sub(r'\s*\([^)]*\)\s*', ' ', n).strip()
            if len(n.split()) >= 2:
                forms.append((p['pi'], n))
    cands = []
    for h in hosts:
        for kind in kinds:
            if kind == 'events' and h == 'stat':
                continue   # stat.uchicago.edu/events/ is robots-disallowed
            rows = W.cdx_rows(c, f'{HOSTS[h]}/{kind}/', exact=False, collapse='urlkey')
            rx = EV if kind == 'events' else NW
            for r in rows:
                u = r['original']
                if re.search(r'\.(jpg|png|gif|css|js|pdf|ics)(\?|$)', u, re.I) or '/embed' in u or u.rstrip('/').endswith(('/news', '/events')):
                    continue
                if rx.search(u):
                    cands.append((r['timestamp'], u))
    print('candidates', len(cands), flush=True)
    res = []
    for ts, u in cands[:mx]:
        cp, st, sha, b = W.capture(c, ts, u, u, 'defense-pages')
        if st != 200:
            continue
        t = W.flat(b)
        t = body(t)
        hits = []
        for sent in re.split(r'(?<=[.!?])\s+', t):
            if not ADV.search(sent):
                continue
            for pi, f in forms:
                if re.search(re.escape(f) + r'(?![\w-])', sent):
                    hits.append(dict(pi=pi, sentence=sent[:400]))
                    break
        if hits:
            res.append(dict(url=u, capture=cp, sha=sha, ts=ts, head=t[:160], hits=hits))
            json.dump(res, open(out, 'w'), indent=1)
    print('pages with hits', len(res), flush=True)


if __name__ == '__main__':
    a = sys.argv[1:]
    mx = int(a[a.index('--max') + 1]) if '--max' in a else 10 ** 6
    kinds = (a[a.index('--kinds') + 1] if '--kinds' in a else 'news,events').split(',')
    hosts = (a[a.index('--hosts') + 1] if '--hosts' in a else 'cs,stat,cam').split(',')
    main(a[0], a[1], mx, kinds, hosts)
