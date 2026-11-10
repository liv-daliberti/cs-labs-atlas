"""Add a source-checked VT Stage 2 batch from repository and person records.

These are provisional candidate decisions, not admissions.  The later complete
affiliate-unit review and OpenAlex sweep may change them.
"""
import collections
import hashlib
import json
import sys
import unicodedata
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import school_web as W  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
MAIN = Path('/n/fs/resemble/homogenizing-science/code')
SCRATCH = MAIN.parent / 'scratch/vt-followthrough-1110'
VT = ROOT / 'hierarchy/vt/reviewed'
HASHES = {
    'repo_candidate_audit.jsonl': 'fad19a5cf8ecb129c1111469ed659ca2ae0697c35af69484e5986ed7f10cdda1',
    'dblp-candidate-theses.json': 'c53c1f51afa9901824f6f2485d547d05dc989819260a2bda366c31bd7449bd31',
    'dblp-candidate-pubs.json': '6f45bd233b3f635de02632209daa835dd0d634724f63e7019e2bcf6bb8224b3d',
}
PAPER_BOUND = {
    'Anirban Mukhopadhyay': ('Scaling Up Complex Sensemaking', 'OSINT Research Studios:'),
    'Dian Chen': ('Trustworthy AI for Smart Systems:', 'Ethical AI for Healthcare Systems:'),
    'Guannan Liu': ('Investigating Security Threats of Resource Mismanagement', 'Dial "N" for NXDomain:'),
    'Lifeng Zhou': ('Parsimonious, Risk-Aware, and Resilient', 'Spatial Temporal Graph Neural Networks'),
    'Xu Shi': ('Bayesian Modeling for Isoform Identification', 'mAPC-GibbsOS:'),
    'Jianan Bai': ('Random Access Control In Massive Cellular', 'Resource Allocation for D2D Cellular Networks'),
    'Xuan Zhang': ('Product Defect Discovery and Summarization', 'Identifying Product Defects from User Complaints:'),
    'Xiao Wang': ('Computational Modeling for Differential Analysis', 'BADGE:'),
    'He Li': ('Privacy and Authentication in Emerging', 'Cumulative Message Authentication Codes'),
}
PERSON_ROLES = {
    'Bo Shen': ('https://boshen0.github.io/', 'I obtained my Ph.D. in the Industrial and Systems Engineering at Virginia Tech.', 'not_faculty_listed'),
    'Feiyu Lu': ('https://ericlu25.github.io/', 'I obtained my Ph.D. degree at Virginia Tech in May 2023', 'not_faculty_listed'),
    'John M. Carroll': ('https://jcarroll.ist.psu.edu/', 'Until August 2003, I was a professor in Computer Science at Virginia Tech.', 'not_faculty_listed'),
    'Pedro Soto': ('https://pedrojuansoto.github.io/', 'Applied Mathematics Postdoc @ VTech', 'research_or_other_rank'),
    'Po-Heng Chou': ('https://homepage.citi.sinica.edu.tw/pages/bonezhou/vita_en.html', 'Postdoctoral Visiting Fellow hosted by Prof. Walid Saad', 'research_or_other_rank'),
    'Xiaodong Yu': ('https://xiaodong-yu.github.io/', 'I got my Ph.D. degree in Computer Science from Virginia Tech.', 'not_faculty_listed'),
}
PROFESSORS = {
    'Edward Valeev': ('https://dblp.org/pid/46/2149', 'Edward F. Valeev'),
    'Rachel (Ryan) M. Gerdes': ('https://dblp.org/pid/73/1832', 'Ryan M. Gerdes'),
    'Thidapat (Tam) Chantem': ('https://dblp.org/pid/59/2918', 'Thidapat Chantem'),
    'Ting-Chung (T.-C) Poon': ('https://dblp.org/pid/01/8294', 'Ting-Chung Poon'),
}


def norm(value):
    return ''.join(ch for ch in unicodedata.normalize('NFKD', value).lower() if ch.isalnum())


def saved(db, url, expected=None):
    row = db.execute('select status,sha256,raw_zlib,content_type,fetched_at from live where url=?', (url,)).fetchone()
    assert row and row[0] == 200 and row[2], url
    raw = zlib.decompress(row[2])
    assert hashlib.sha256(raw).hexdigest() == row[1], url
    if expected:
        assert row[1] == expected, url
    return raw, row[1], W.flat(W.extract.blocks(raw, row[3], url)), row[4][:10]


def repo_items(db, receipt):
    raw, sha, _, at = saved(db, receipt['url'], receipt['sha256'])
    data = json.loads(raw)
    assert data['query'] == '"' + receipt['name'] + '"'
    items = []
    for obj in data['_embedded']['searchResult']['_embedded']['objects']:
        item = obj.get('_embedded', {}).get('indexableObject') or {}
        meta = item.get('metadata') or {}
        vals = lambda key: [v['value'] for v in meta.get(key, []) if v.get('value')]
        authors = vals('dc.contributor.author')
        name = receipt['name']
        first, last = name.split()[0], name.split()[-1]
        if not any(name.casefold() in a.casefold() or a.casefold() == (last + ', ' + first).casefold() for a in authors):
            continue
        items.append(dict(title=item['name'], type=vals('dc.type'), authors=authors,
                          handle=item.get('handle'), uuid=item.get('uuid'), date=vals('dc.date.issued')[:1]))
    return items, sha, at


def one(items, prefix, thesis=None):
    rows = [x for x in items if x['title'].casefold().startswith(prefix.casefold())]
    if thesis is not None:
        rows = [x for x in rows if any(t in ' '.join(x['type']).lower() for t in ('dissertation', 'thesis')) == thesis]
    assert len(rows) == 1, (prefix, rows)
    return rows[0]


def item_receipt(item, query, sha, at):
    return dict(url=f"https://vtechworks.lib.vt.edu/items/{item['uuid']}",
                repository_query=query, query_sha256=sha, observed=at,
                quote=f"{'; '.join(item['authors'][:8])} — {item['title']} ({', '.join(item['type'])})",
                title=item['title'], handle=item['handle'])


def main():
    for file, sha in HASHES.items():
        assert hashlib.sha256((SCRATCH / file).read_bytes()).hexdigest() == sha, file
    repo = {x['name']: x for x in map(json.loads, (SCRATCH / 'repo_candidate_audit.jsonl').read_text().splitlines())}
    theses = json.loads((SCRATCH / 'dblp-candidate-theses.json').read_text())
    pubs = json.loads((SCRATCH / 'dblp-candidate-pubs.json').read_text())
    candidates = {x['name']: x for x in json.loads((MAIN / 'hierarchy/vt/derived/cs-related-candidates.json').read_text())}
    affiliated = {x['pid']: x for x in json.loads((MAIN / 'hierarchy/vt/derived/dblp-affiliated.json').read_text())['persons']}
    hand = {x['name']: x for x in json.loads((VT / 'cs-related-hand.json').read_text())}
    profiles = json.loads((SCRATCH / 'profile-dblp-audit.json').read_text())['people']
    doc = json.loads((VT / 'cs-related-review.json').read_text())
    decisions = {x['name']: x for x in doc['decisions']}
    assert len(decisions) == 177
    db = W.con('vt')
    added = collections.Counter()

    # The local DBLP dump includes the identical thesis under the exact author
    # string assigned to this candidate PID.  This binds the repository student.
    for name, receipt in repo.items():
        if name in decisions or name not in theses:
            continue
        candidate = candidates[name]
        if candidate['source'] != 'dblp_affiliation':
            continue
        items, sha, at = repo_items(db, receipt)
        matches = [(item, t) for item in items for t in theses[name]
                   if norm(item['title']) == norm(t['title'])
                   and any(k in ' '.join(item['type']).lower() for k in ('dissertation', 'thesis'))]
        if not matches:
            continue
        assert len(matches) == 1, name
        item, thesis = matches[0]
        assert item['authors'] and name.split()[-1].casefold() in item['authors'][0].casefold(), name
        assert thesis['year'] <= 2026 and thesis['type'] in ('phdthesis', 'mastersthesis')
        decisions[name] = dict(name=name, aliases=candidate.get('aliases') or [], source=candidate['source'],
            decision='not_faculty_listed',
            reason='VT repository identifies this DBLP person as a thesis author; the exact thesis title also occurs under the candidate person in the September 2026 DBLP dump. No VT professor appointment is established by the reviewed sources.',
            cs_basis=dict(dblp=[candidate['dblp']], dblp_window=candidate['dblp_window'],
                          matched_dblp_thesis_title=thesis['title'], dblp_key=thesis['key'], dump='dblp-2026-09-01.xml.gz',
                          dblp_audit_sha256=HASHES['dblp-candidate-theses.json']),
            faculty_evidence=[], status_evidence=[item_receipt(item, receipt['url'], sha, at)],
            years_listed=[], units_searched=['VT CS dated census and saved official faculty profiles'],
            provisional='Later VT professor appointment and affiliate-unit period review remain possible; no package admitted.')
        added['exact_thesis'] += 1

    # For theses missing from DBLP, require an exact non-thesis publication title
    # on the same VT repository author search and on the candidate DBLP person.
    for name, (thesis_prefix, paper_prefix) in PAPER_BOUND.items():
        assert name not in decisions
        candidate = candidates[name]
        assert candidate['source'] == 'dblp_affiliation'
        receipt = repo[name]
        items, sha, at = repo_items(db, receipt)
        thesis = one(items, thesis_prefix, thesis=True)
        paper = one(items, paper_prefix, thesis=False)
        dblp_papers = [p for p in pubs[name] if p['type'] not in ('phdthesis', 'mastersthesis')
                       and norm(p['title']) == norm(paper['title'])]
        assert dblp_papers, (name, paper['title'])
        assert candidate['dblp'] in affiliated
        decisions[name] = dict(name=name, aliases=candidate.get('aliases') or [], source=candidate['source'],
            decision='not_faculty_listed',
            reason='VT repository records this person as a thesis author. An exact non-thesis publication title appears on the same repository author search and the candidate DBLP person, binding the identity; the full affiliated faculty review is pending.',
            cs_basis=dict(dblp=[candidate['dblp']], dblp_window=candidate['dblp_window'],
                          matched_publication_title=paper['title'], dblp_key=dblp_papers[0]['key'],
                          dump='dblp-2026-09-01.xml.gz', dblp_audit_sha256=HASHES['dblp-candidate-pubs.json']),
            faculty_evidence=[], status_evidence=[item_receipt(thesis, receipt['url'], sha, at),
                                                    item_receipt(paper, receipt['url'], sha, at)],
            years_listed=[], units_searched=['VT CS dated census and saved official faculty profiles'],
            provisional='Thesis and paper identity bound; later VT professor appointment remains open to the affiliate-unit period review.')
        added['paper_bound_thesis'] += 1

    # The person's own DBLP-linked page explicitly states the VT degree or
    # non-ladder role, or dates the VT professorship outside the study window.
    for name, (url, quote, decision) in PERSON_ROLES.items():
        assert name not in decisions
        candidate = candidates[name]
        assert candidate['source'] == 'dblp_affiliation' and url in affiliated[candidate['dblp']]['urls']
        _, sha, body, at = saved(db, url)
        assert quote in body and (name in body or name.split()[-1] in body), name
        decisions[name] = dict(name=name, aliases=candidate.get('aliases') or [], source=candidate['source'],
            decision=decision, reason=f'DBLP-linked person page documents the VT degree, past appointment, or non-ladder role: {quote}',
            cs_basis=dict(dblp=[candidate['dblp']], dblp_window=candidate['dblp_window'],
                          identity_basis='DBLP-linked person page', dump='dblp-2026-09-01.xml.gz'),
            faculty_evidence=[], status_evidence=[dict(url=url, sha256=sha, observed=at, quote=quote)],
            years_listed=[], units_searched=['VT CS dated census and saved official faculty profiles'],
            provisional='Full VT affiliate-unit and period review pending; no package admitted.')
        added['person_role'] += 1

    # The four profile-person matches have corroborating full-name or alias
    # evidence.  Reject partial middle-name and unrelated-name DBLP matches.
    for name, (pid, printed) in PROFESSORS.items():
        assert name not in decisions
        candidate = candidates[name]
        role = hand[name]
        assert candidate['source'] == 'official_profile_ladder' and role['ladder']
        _, sha, body, at = saved(db, candidate['source_url'], candidate['source_sha256'])
        assert sha == role['sha256'] and role['quote'] in body and name in body, name
        person = [p for p in profiles[name] if p['pid'] == pid]
        assert len(person) == 1 and person[0]['n_window'] >= 5 and printed in person[0]['names'], name
        if name == 'Edward Valeev':
            assert 'Edward F. Valeev' in body and 'Theory & Computation' in body
        decisions[name] = dict(name=name, aliases=candidate.get('aliases') or [], source=candidate['source'],
            decision='accepted', reason='Official VT professor-rank profile and a corroborated DBLP person with at least five 2016–2026 computing records.',
            cs_basis=dict(dblp=[pid], dblp_window=person[0]['n_window'],
                          person_record_sha256=person[0]['person_record_sha256'],
                          identity_basis=f'profile name or explicit alias matches {printed}', dump='dblp-2026-09-01.xml.gz'),
            faculty_evidence=[dict(unit=role['unit'], url=candidate['source_url'], sha256=sha,
                                   observed=at.replace('-', ''), quote=role['quote'], ladder=True)],
            years_listed=[int(at[:4])], units_searched=[role['unit']],
            provisional='OpenAlex computing share and full affiliate-unit period review pending; no package admitted.')
        added['official_professor'] += 1

    # Three dated histories settle a current/previous-role ambiguity.  The
    # sources are institutional pages captured with the project web client.
    histories = (
        ('Chao Wang', 'https://ece.vt.edu/news/articles/2011/Chao-Wang-joins-ECE1636660229624.html',
         'Chao Wang has joined the ECE faculty as an assistant professor', 'accepted'),
        ('Yilu Liu', 'https://eecs.utk.edu/people/yilu-liu/',
         'She joined UT in August 2009 from Virginia Tech.', 'not_faculty_listed'),
        ('Hengyong Yu', 'https://sites.uml.edu/hengyong-yu/',
         'From November 2006 to May 2010, he was a Research Scientist', 'research_or_other_rank'),
    )
    for name, url, quote, decision in histories:
        assert name not in decisions
        candidate = candidates[name]
        assert candidate['source'] == 'dblp_affiliation'
        _, sha, body, at = saved(db, url)
        assert quote in body and name in body, name
        if name == 'Chao Wang':
            # The university's dated registrar directory confirms the role
            # persisted into the first year of the 2016–2026 window.
            import sqlite3
            con = sqlite3.connect(MAIN / 'listings/vt/raw/faculty-directory-captures.sqlite')
            from bs4 import BeautifulSoup
            rows = con.execute('select url,sha256,body_zlib from captures where year=2016').fetchall()
            hit = [(u,s) for u,s,b in rows if hashlib.sha256(zlib.decompress(b)).hexdigest() == s
                   and 'WANG, Chao (2011) Assistant Prof. of Electrical and Computer Engineering'
                   in ' '.join(BeautifulSoup(zlib.decompress(b), 'html.parser').stripped_strings)]
            assert len(hit) == 1, hit
            faculty = [dict(unit='Electrical and Computer Engineering', url=url, sha256=sha,
                            observed=at.replace('-', ''), quote=quote, ladder=True),
                       dict(unit='VT registrar faculty directory', url=hit[0][0], sha256=hit[0][1],
                            observed='20160101', quote='WANG, Chao (2011) Assistant Prof. of Electrical and Computer Engineering', ladder=True)]
        else:
            faculty = []
        decisions[name] = dict(name=name, aliases=candidate.get('aliases') or [], source=candidate['source'],
            decision=decision, reason=f'Institutional biography dates the VT appointment or departure: {quote}',
            cs_basis=dict(dblp=[candidate['dblp']], dblp_window=candidate['dblp_window'],
                          affiliation_notes=candidate['affiliations'], dump='dblp-2026-09-01.xml.gz'),
            faculty_evidence=faculty, status_evidence=[dict(url=url, sha256=sha, observed=at, quote=quote)],
            years_listed=[2016] if name == 'Chao Wang' else [],
            units_searched=['VT registrar 2016–17 and institutional biography'] if name == 'Chao Wang' else ['VT CS dated census and institutional biography'],
            provisional='Full affiliate-unit and OpenAlex sweep review pending; no package admitted.')
        added['dated_history'] += 1

    assert added == {'exact_thesis': 29, 'paper_bound_thesis': 9, 'person_role': 6,
                     'official_professor': 4, 'dated_history': 3}, added
    assert len(decisions) == 228
    doc['reviewed'] = '2026-11-10'
    doc['provisional'] = True
    doc['rule'] = 'Source-checked preliminary VT decisions; full 2016–2026 OpenAlex and affiliated-unit reviews may revise results.'
    doc['counts'] = dict(collections.Counter(x['decision'] for x in decisions.values()))
    doc['decisions'] = list(decisions.values())
    for path in (VT / 'cs-related-review.json', VT / 'stage2-preliminary-decisions.json'):
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'added': dict(added), 'decisions': len(decisions), 'undecided': 325-len(decisions),
                      'expected_open_with_sweep': 325-len(decisions)+1}))


if __name__ == '__main__':
    main()
