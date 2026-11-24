"""Bind distinctive VT census PIs to source-backed local DBLP person records."""

import hashlib
import json
from datetime import datetime, timezone

import atlas_paths as P


# Explicit reviewed identities. Broad common-name matches remain open.
PIDS = {
    'Osman Balci': '23/385',
    'Christopher L. Barrett': '75/3334',
    'Ing-Ray Chen': 'c/IngRayChen',
    'Lenwood S. Heath': 'h/LenwoodSHeath',
    'Wenjing Lou': '73/3673',
    'Godmar Back': '47/2634',
    'Denis Gracanin': 'g/DenisGracanin',
    'Chang-Tien Lu': '08/4367',
    'Eli Tilevich': '00/869',
    'Anil Vullikanti': '89/7912',
    'Daphne Yao': 'y/DanfengYao',
    'Sharath Raghvendra': '149/2582',
    'Naren Ramakrishnan': 'r/NarenRamakrishnan',
    'Nicholas F. Polys': '92/1766',
    'Shaddi Hasan': '47/11303',
    'Murat Kantarcioglu': '36/195',
    'Ryan P. McMahan': '35/6470',
    'Sam H. Noh': '81/970',
    'Yang Cao': '25/7045-1',
    'Liqing Zhang': '20/4627-2',
    'Na Meng': '60/6376',
    'Xun (Steve) Jian': '130/7707-2',
    'Bo Ji': '67/8454-1',
    'Tijay Chung': '90/8396',
    'Peng Gao': '29/5999-8',
    'Sang Won Lee': '01/4601-2',
    'Chris Thomas': '21/4235-4',
    'Dan Williams': '96/2005',
    'Dawei Zhou': '39/3130-3',
    'Yan Chen': '88/2827-33',
    'Alberto Cano': '62/8229-1',
    'Doug Bowman': '40/1426',
    'Kirk Cameron': '56/3019',
    'Stephen Edwards': '34/4539',
    'Edward Fox': 'f/EdwardAFox',
    'Dennis Kafura': '71/6910',
    'Madhav Marathe': '52/991',
    'T. M. Murali': '76/2280',
    'Chris North': '58/4516',
    'Cliff Shaffer': 's/CliffordAShaffer',
    'Deborah Tatar': '18/1023',
    'Layne Watson': 'w/LayneTWatson',
    'Ali Butt': 'b/AliRazaButt',
    'Chandan Reddy': '42/1341',
    'Christine Julien': 'j/ChristineJulien',
    'Gang Wang': '71/4292-11',
}

ALIASES = {
    'Yang Cao': 'Yang Cao 0001',
    'Liqing Zhang': 'Liqing Zhang 0002',
    'Na Meng': 'Na Meng 0001',
    'Xun (Steve) Jian': 'Xun Steve Jian',
    'Bo Ji': 'Bo Ji 0001',
    'Tijay Chung': 'Taejoong (Tijay) Chung',
    'Peng Gao': 'Peng Gao 0008',
    'Sang Won Lee': 'Sang Won Lee 0002',
    'Chris Thomas': 'Chris Thomas 0004',
    'Dan Williams': 'Dan Williams 0001',
    'Dawei Zhou': 'Dawei Zhou 0003',
    'Yan Chen': 'Yan Chen 0033',
    'Alberto Cano': 'Alberto Cano 0001',
    'Doug Bowman': 'Doug A. Bowman',
    'Kirk Cameron': 'Kirk W. Cameron',
    'Stephen Edwards': 'Stephen H. Edwards',
    'Edward Fox': 'Edward A. Fox',
    'Dennis Kafura': 'Dennis G. Kafura',
    'Madhav Marathe': 'Madhav V. Marathe',
    'T. M. Murali': 'T. M. Murali 0001',
    'Chris North': 'Chris North 0001',
    'Cliff Shaffer': 'Cliff A. Shaffer',
    'Deborah Tatar': 'Deborah G. Tatar',
    'Layne Watson': 'Layne T. Watson',
    'Ali Butt': 'Ali Raza Butt',
    'Chandan Reddy': 'Chandan K. Reddy',
    'Christine Julien': 'Christine Julien 0001',
    'Gang Wang': 'Gang Wang 0011',
}


def main():
    source = P.data('dblp-affiliated.json', 'vt')
    raw = source.read_bytes()
    people = json.loads(raw)['persons']
    by_pid = {person['pid']: person for person in people}
    census = {person['name'] for person in json.loads(P.data('census-faculty.json', 'vt').read_text())['faculty']}
    path = P.data('census-overrides-school.json', 'vt')
    overrides = json.loads(path.read_text())
    receipts = []
    for name, suffix in PIDS.items():
        pid = 'https://dblp.org/pid/' + suffix
        person = by_pid[pid]
        assert name in census, name
        assert not person['disambiguation'] and person['n_window'] > 0, name
        assert any('virginia tech' in a['text'].lower() or 'virginia polytechnic' in a['text'].lower()
                   for a in person['affiliations']) or any('vt.edu' in u for u in person['urls']), name
        assert (name in person['names'] or ALIASES.get(name) in person['names'] or
                (name == 'Daphne Yao' and 'Danfeng (Daphne) Yao' in person['names'])), name
        current = overrides.setdefault(name, {})
        assert not current.get('dblp') or current['dblp'] == [pid], name
        current['dblp'] = [pid]
        current['why_dblp'] = ('Exact named DBLP person with VT affiliation or VT faculty-page URL '
                               'in the locally indexed September 2026 DBLP dump; publication count in '
                               '2016–2026 is positive. This anchors identity, not paper admission.')
        current['dblp_evidence'] = [dict(
            source='hierarchy/vt/derived/dblp-affiliated.json',
            source_sha256=hashlib.sha256(raw).hexdigest(), pid=pid,
            names=person['names'], affiliations=person['affiliations'], urls=person['urls'],
            works_2016_2026=person['n_window'],
        )]
        receipts.append(dict(name=name, pid=pid, works_2016_2026=person['n_window']))
    path.write_text(json.dumps(overrides, indent=1, ensure_ascii=False) + '\n')
    out = path.parent / 'stage5-identity-review.json'
    out.write_text(json.dumps(dict(
        school='vt', reviewed_at=datetime.now(timezone.utc).isoformat(),
        source='hierarchy/vt/derived/dblp-affiliated.json',
        source_sha256=hashlib.sha256(raw).hexdigest(),
        rule='distinctive exact-name VT-affiliated DBLP person; no ambiguous names',
        anchors=receipts,
    ), indent=2) + '\n')
    print(json.dumps({'bound': len(receipts)}))


if __name__ == '__main__':
    main()
