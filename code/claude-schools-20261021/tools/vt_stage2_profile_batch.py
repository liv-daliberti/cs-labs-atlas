"""Reconcile 50 VT Stage 2 leads against saved official profiles and the local DBLP dump.

The decisions remain provisional until the full OpenAlex sweep and affiliated-unit
review. In particular, a below-threshold DBLP result may change after the
OpenAlex computing-share test.
"""
import collections
import hashlib
import json
import re
import unicodedata
import zlib
from pathlib import Path

from bs4 import BeautifulSoup

import atlas_paths as P
import school_web as W


BRANCH = Path(__file__).resolve().parents[1]
MAIN = P.CODE
VT = BRANCH / 'hierarchy/vt/reviewed'
STUDENTS = MAIN.parent / 'scratch/vt-followthrough-1110/identity-sources/lei-zhang-sanghani.html'
DBLP_TITLES = MAIN.parent / 'scratch/vt-followthrough-1110/sanghani-dblp-title-audit.json'
DBLP_AUDIT = MAIN.parent / 'scratch/vt-followthrough-1110/profile-dblp-audit.json'
PROFESSOR_ACCEPT = (
    'Paul Benjamin Lowry', 'Alan J. Michaels', 'Ali Mehrizi-Sani', 'Chen-Ching Liu',
    'Khai D. T. Ngo', 'Lamine M. Mili', 'Linbo Shao', 'Liyan Zhu', 'Luiz A. DaSilva',
    'Minseong Park', 'Rolando Burgos', 'Rose Qingyang Hu', 'Yaling Yang',
    'Yizheng Zhu', 'Zhangyu Guan', 'Edwin Barnes', 'Yongfa You',
)
PROFESSOR_BELOW_DBLP = (
    'Ahmad Safaai-Jazi', 'Amer Zayegh', 'Christina DiMarino', 'Francis Hou',
    'J. Michael Ruohoniemi', 'Joseph B.H. Baker', 'Majid Manteghi', 'Mantu K. Hudait',
    'Marius K. Orlowski', 'Mark Limes', 'Masoud Agah', 'Wayne A. Scales',
    'Xiaoting Jia', 'David McCall',
)
STUDENT_PERSONAL_SITES = {
    'Yi Fang': ('https://yifang99.github.io/',
                'advised by Dr. Xuan Wang'),
    'You Lu': ('https://yolu1055.github.io/',
               'advised by Professor Bert Huang'),
}


def norm(value):
    return ''.join(ch for ch in unicodedata.normalize('NFKD', re.sub(r'\s+\d{4}$', '', value)).lower() if ch.isalnum())


def saved_page(db, url, expected_sha=None):
    row = db.execute('select status, sha256, raw_zlib, content_type, fetched_at from live where url=?', (url,)).fetchone()
    assert row and row[0] == 200 and row[2], url
    raw = zlib.decompress(row[2])
    assert hashlib.sha256(raw).hexdigest() == row[1], url
    if expected_sha:
        assert row[1] == expected_sha, url
    return row[1], W.flat(W.extract.blocks(raw, row[3], url)), row[4][:10]


def main():
    assert hashlib.sha256(DBLP_TITLES.read_bytes()).hexdigest() == '3ec39ea3ae545b204ca0d15c5b46da9a2edb56a61ea6b1d2d1aa6981583b4b72'
    assert hashlib.sha256(DBLP_AUDIT.read_bytes()).hexdigest() == '7c52175b5c0f0f729578d9fd56b1b565aa452a76beb450e0f911f414dbbe2247'
    candidates = {x['name']: x for x in json.loads((MAIN / 'hierarchy/vt/derived/cs-related-candidates.json').read_text())}
    affiliated = {p['pid']: p for p in json.loads((MAIN / 'hierarchy/vt/derived/dblp-affiliated.json').read_text())['persons']}
    audit = json.loads(DBLP_TITLES.read_text())
    assert audit['dump'] == 'dblp-2026-09-01.xml.gz'
    profiles = json.loads(DBLP_AUDIT.read_text())
    assert profiles['school'] == 'vt' and profiles['dump'] == audit['dump']
    hand = {x['name']: x for x in json.loads((VT / 'cs-related-hand.json').read_text())}
    doc = json.loads((VT / 'cs-related-review.json').read_text())
    decisions = {d['name']: d for d in doc['decisions']}
    db = W.con('vt')
    nav_raw = STUDENTS.read_bytes()
    assert hashlib.sha256(nav_raw).hexdigest() == 'b2e15d9dde7d1773401acbf3bac233afbd3121126bee2137c9c42154fa595933'
    nav = BeautifulSoup(nav_raw, 'html.parser')
    added = collections.Counter()

    for name, record in audit['people'].items():
        assert name not in decisions
        candidate = candidates[name]
        assert candidate['source'] == 'dblp_affiliation' and candidate['dblp'] == record['pid']
        assert affiliated[record['pid']]['n_window'] >= 5
        urls = [a['href'] for a in nav.find_all('a', href=True)
                if a.get_text(' ', strip=True) == name and '/people/students/' in a['href']]
        if name == 'Wei Wang':
            assert urls[0].endswith('/wei-wang-2.html') and len(set(urls)) == 2
        else:
            assert len(set(urls)) == 1, name
        url = urls[0]
        sha, body, at = saved_page(db, url)
        titles = re.findall(r'General Item (.*?) Date: [A-Z][a-z]{2} \d{1,2}, \d{4}', body)
        matches = [(title, pub['title']) for title in titles for pub in record['pubs']
                   if norm(title) == norm(pub['title'])]
        personal = None
        if name in STUDENT_PERSONAL_SITES:
            personal_url, personal_quote = STUDENT_PERSONAL_SITES[name]
            assert personal_url in affiliated[record['pid']]['urls'], name
            personal_sha, personal_body, personal_at = saved_page(db, personal_url)
            assert name in personal_body and 'Virginia Tech' in personal_body and personal_quote in personal_body
            assert personal_quote.split('by ')[-1].replace('Dr. ', '').replace('Professor ', '') in body, name
            personal = dict(url=personal_url, sha256=personal_sha, observed=personal_at,
                            quote=personal_quote, identity_basis='DBLP-linked personal site names the same VT adviser')
        if not matches and not personal:
            continue  # source name alone does not bind this DBLP PID
        assert 'Tags Alumni ' + name in body or 'Tags Student ' + name in body, name
        title, dblp_title = matches[0] if matches else (None, None)
        tag = 'Alumni' if 'Tags Alumni ' + name in body else 'Student'
        decisions[name] = dict(
            name=name, aliases=candidate.get('aliases') or [], source=candidate['source'],
            decision='not_faculty_listed',
            reason=f'VT Sanghani profile identifies this person as {tag.lower()}; the {"page-listed publication" if matches else "DBLP-linked personal site and adviser"} binds the candidate DBLP PID. No VT professor appointment is established by these reviewed sources.',
            cs_basis=dict(dblp=[record['pid']], dblp_window=candidate['dblp_window'],
                          matched_title=dblp_title, dump=audit['dump']),
            faculty_evidence=[], status_evidence=[dict(url=url, sha256=sha, observed=at,
                quote=f'Tags {tag} {name}', matched_publication_title=title)] + ([personal] if personal else []),
            years_listed=[], units_searched=['Sanghani Center individual student profile'],
            provisional='Historical affiliated-unit review remains pending; reconsider if a dated VT faculty appointment appears.',
        )
        added['student_alumni'] += 1

    for name in PROFESSOR_ACCEPT + PROFESSOR_BELOW_DBLP:
        assert name not in decisions
        candidate = candidates[name]
        assert candidate['source'] == 'official_profile_ladder'
        sha, body, at = saved_page(db, candidate['source_url'], candidate['source_sha256'])
        role = hand[name]
        assert role['ladder'] and role['sha256'] == sha and role['quote'] in body, name
        rows = profiles['people'].get(name, [])
        valid = [r for r in rows if not r['disambiguation'] and r['n_window'] >= 5
                 and any(norm(n) == norm(name) for n in r['names'])]
        if name in PROFESSOR_ACCEPT:
            assert len(valid) == 1, name
            person = valid[0]
            assert person['person_record_sha256'] and person['n_window'] >= 5
            decision = 'accepted'
            reason = f"VT {role['unit']} professor-rank profile and one exact-name DBLP person with {person['n_window']} records in 2016–2026"
            basis = dict(dblp=[person['pid']], dblp_window=person['n_window'],
                         person_record_sha256=person['person_record_sha256'], identity_basis='unique exact-name, non-disambiguation DBLP record', dump=audit['dump'])
        else:
            assert not any(r['n_window'] >= 5 and not r['disambiguation'] for r in rows), name
            decision = 'faculty_not_computing'
            reason = 'VT professor-rank profile; local DBLP name audit has no non-disambiguation person with five records in 2016–2026. OpenAlex computing-share check is pending.'
            basis = dict(dblp=[], dblp_window=max((r['n_window'] for r in rows if not r['disambiguation']), default=0),
                         searched_person_records=len(rows), dump=audit['dump'])
        decisions[name] = dict(
            name=name, aliases=candidate.get('aliases') or [], source=candidate['source'],
            decision=decision, reason=reason, cs_basis=basis,
            faculty_evidence=[dict(unit=role['unit'], url=candidate['source_url'], sha256=sha,
                                   observed=at.replace('-', ''), quote=role['quote'], ladder=True)],
            years_listed=[int(at[:4])], units_searched=[role['unit']],
            provisional='Computing-share and full affiliated-unit period review pending; no lab or paper package admitted.',
        )
        added[decision] += 1

    assert added == {'student_alumni': 19, 'accepted': 17, 'faculty_not_computing': 14}, added
    assert len(decisions) == 177
    doc['reviewed'] = '2026-11-10'
    doc['rule'] = 'Source-checked preliminary VT decisions; the full 2016–2026 OpenAlex and affiliated-unit reviews may revise these results.'
    doc['provisional'] = True
    doc['counts'] = dict(collections.Counter(d['decision'] for d in decisions.values()))
    doc['decisions'] = list(decisions.values())
    for path in (VT / 'cs-related-review.json', VT / 'stage2-preliminary-decisions.json'):
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'added': dict(added), 'decisions': len(decisions), 'remaining_candidates': 325 - len(decisions),
                      'stage2_gate_open_including_sweep': 325 - len(decisions) + 1}))


if __name__ == '__main__':
    main()
