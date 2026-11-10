"""Record a small, source-checked VT Stage 2 review while the annual sweep runs.

These decisions use the existing DBLP threshold and dated official faculty
rank evidence. The complete affiliated-unit review remains a separate job.
"""
import datetime
import hashlib
import json
import re
import sqlite3
import zlib
from pathlib import Path

from bs4 import BeautifulSoup

import cs_related_school as C

ROOT = Path(__file__).resolve().parents[1]
VT = ROOT / 'hierarchy/vt'
HAND_NAMES = (
    'A. Lynn Abbott', 'Angelos Stavrou', 'Binoy Ravindran',
    'Daniel J. Stilwell', 'Haibo Zeng', 'Haining Wang', 'Jeffrey H. Reed',
    'Jianhua Xuan', 'Jih-Sheng Lai', 'Leyla Nazhandali', 'Michael S. Hsiao',
    'Ming Jin', 'Ryan K. Williams', 'Saifur Rahman', 'Steven W. Ellingson',
    'Wenjie Xiong', 'Yang Yi', 'Yulia R. Gel', 'Junghwan Kim',
    'Thinh T. Doan', 'Lisa D. McNair', 'J. Todd Ogle',
)
REGISTRAR_NAMES = (
    'Cameron D. Patterson', 'Christopher W. Zobel', 'Fred C. Lee',
    'Joseph G. Tront', 'Jung-Min Park', 'Patrick Schaumont',
    'Peter M. Athanas', 'Virgilio Centeno', 'Yue Joseph Wang',
    'Zhiwu Xie',
    'Allen B. MacKenzie', 'Dong Sam Ha', 'Stephen G. Eubank',
    'Loren Paul Rees', 'Qiang Li', 'David R. Bevan',
    'T. Charles Clancy', 'A. A. Louis Beex', 'R. Michael Buehrer',
    'Yi Shen', 'Christopher Williams',
    'Montasir M. Abbas', 'John A. Burns', 'Sophia E. Economou',
    'Weiguo Fan', 'Kevin P. Heaslip', 'Yili Hong', 'Michael A. Horning',
    'David B. Knight', 'Zhenyu James Kong', 'Walter C. Lee',
    'Marie C. Paretti', 'Mayuresh Patil', 'Ryan M. Pollyea',
    'Hesham A. Rakha', 'Christian M. Reidys', 'Subhash C. Sarin',
    'Sandeep K. Shukla', 'John E. Taylor', 'Konstantinos P. Triantis',
    'Linda G. Wallace', 'Kevin G. Wang', 'Xiaowei Wu', 'Zheng Xiang',
    'Lizette Zietsman', 'Robert Hildebrand', 'David Higdon',
    'Gretchen L. Matthews', 'Weijun Xie',
)
REGISTRAR_FIRST = {
    'T. Charles Clancy': 'Charles',
    'A. A. Louis Beex': 'Aloysius',
    'R. Michael Buehrer': 'Michael',
}
PROFILE_DBLP_NAMES = (
    'Jeffrey Walling', 'Lingjia Liu', 'Thomas L. Martin',
    'Thomas Hou', 'Sanaz Shafian', 'Scott F. Midkiff',
    'Walid Saad', 'Harpreet S. Dhillon', 'Ruoxi Jia',
)
UNIT_LADDER_NAMES = ('Rolf Müller', 'Suyi Li', 'Tao Lin', 'Xi Chen')
UNIT_OTHER_RANK_NAMES = ('Daniel J. Jakubisin', 'Hanif D. Sherali', 'Yi Shi')
WIRELESS_OTHER_RANK_NAMES = ('Carl B. Dietrich', 'Eric William Burger')
CATALOG_NAMES = {
    'Aaron F. Brantly': 'Aaron Brantly',
    'Dushan Boroyevich': 'Dushan Boroyevich',
    'France Bélanger': 'France Belanger',
    'Janet Abbate': 'Janet Abbate',
}
BOV_LADDER_NAMES = {'Jia-Bin Huang': ('Huang, Jia-Bin', 'Assistant Professor')}
BOV_OTHER_RANK_NAMES = {
    'Amr Hilal': ('Hilal, Amr', 'Professional Lecturer'),
    'Andrea L. Kavanaugh': ('Kavanaugh, Andrea', 'Senior Research Scientist'),
    'Hao Chen': ('Chen, Hao', 'Research Associate'),
    'Jun Wang': ('Wang, Jun', 'Research Assistant Professor'),
    'Junbo Zhao': ('Zhao, Junbo', 'Research Assistant Professor'),
    'Miao Song': ('Song, Miao', 'Research Associate'),
    'Ran Xu': ('Xu, Ran', 'Postdoctoral Associate'),
    'Robert W. McGwier': ('McGwier, Robert', 'Research Professor'),
    'Ruslan Nikolaev': ('Nikolaev, Ruslan', 'Research Assistant Professor'),
    "Timothy J. O'Shea": ("O'Shea, Timothy", 'Research Assistant Professor'),
    'Tingting Jiang': ('Jiang, Tingting', 'Professional Lecturer'),
    'Xiaoguang Wang': ('Wang, Xiaoguang', 'Postdoctoral Associate'),
    'Yao Zhang': ('Zhang, Yao', 'Research Assistant Professor'),
    'Aloizio P. Silva': ('Pereira da Silva, Aloizio', 'Professional Lecturer', '2023-24'),
    'Daniel Sobien': ('Sobien, Daniel', 'Research Associate', '2023-24'),
    'Erin Lanus': ('Lanus, Erin', 'Research Assistant Professor', '2023-24'),
    'Qiang Fan': ('Fan, Qiang', 'Postdoctoral Associate', '2021-22'),
    'Yijun Xu': ('Xu, Yijun', 'Postdoctoral Associate', '2021-22'),
    'Yimin Chen': ('Chen, Yimin', 'Postdoctoral Associate', '2021-22'),
    'Ying Wang': ('Wang, Ying', 'Research Scientist', '2021-22'),
    'Mohamed M. G. Farag': ('Farag, Mohamed', 'Research Associate', '2023-24'),
    'Ashutosh Tiwari': ('Tiwari, Ashutosh', 'Postdoctoral Associate', '2023-24'),
    'Hao Wang': ('Wang, Hao', 'Senior Research Associate', '2016-17'),
    'Manisa Pipattanasomporn': ('Pipattanasomporn, Manisa', 'Research Associate Professor', '2016-17'),
    'Srinivasan Venkatramanan': ('Venkatramanan, Srinivasan', 'Postdoctoral Associate', '2016-17'),
}
BOV_FILES = {
    '2016-17': ('1a06c8b3b2d152adae7c30ed8e6270b74245f94ab6bcd315027089c12943e2db',
                'https://bov.vt.edu/assets/Minutes-November%206-7%2C%202016-78.pdf'),
    '2018-19': ('ee4d8ee9fb8663af0b586be51158f6044c182833055a5ae50309221a87cde3bb',
                'https://bov.vt.edu/assets/Attachment%20OO_Approval%20of%202018-19%20Faculty%20Salary%20Program_June%202019.pdf'),
    '2021-22': ('91c15c7b4717dc4c2bcf77d7ad2c1da4c28f60988b9181a5847959fd175c019e',
                'https://bov.vt.edu/assets/Attachment%20UU_Resolution%20to%20Approve%202021-22%20Faculty%20Salary%20Program.pdf'),
    '2023-24': ('9d1b86a4c16e0cefb8d72456793df938e3d115611959e9c9272f39ec7ceaa8aa',
                'https://www.bov.vt.edu/assets/Minutes-June%205-6%2C%202023-138.pdf'),
}
CNSR_ALUMNI = (
    'Brian Jalaian', 'Ning Wang', 'Ning Zhang',
    'Xu Yuan', 'Yan Huang', 'Yang Xiao', 'Yao Zheng',
)
CNSR_IDENTITY_ANCHORS = {
    'Ning Wang': 'University of South Florida',
    'Ning Zhang': 'Washington University in St. Louis',
    'Xu Yuan': 'University of Toronto',
    'Yang Xiao': 'University of Kentucky',
    'Yao Zheng': 'University of Hawaii',
}


def bov_evidence(name, spelling, rank, year='2018-19'):
    path = ROOT.parent / f'scratch/vt-followthrough-1110/bov-{year}-faculty-salary.pdf'
    sha, url = BOV_FILES[year]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == sha
    import subprocess
    body = subprocess.run(['pdftotext', '-layout', str(path), '-'], capture_output=True, text=True, check=True).stdout
    matches = [line for line in body.splitlines() if re.search(r'\b' + re.escape(spelling) + r'\s+' + re.escape(rank) + r'\b', line, re.I)]
    assert matches, (name, spelling, rank)
    return dict(unit=f'Virginia Tech Board of Visitors {year} faculty salary report',
                url=url,
                sha256=sha, raw_path=str(path.relative_to(ROOT.parent)), observed=year[:4],
                quote=' '.join(matches[0].split()),
                ladder='Professor' in rank and not rank.startswith('Research '), rank=rank)


def catalog_evidence(name, spelling):
    """Verify an exact full-name entry under a professor-rank heading in the official 2023-24 catalog."""
    path = ROOT.parent / 'scratch/vt-followthrough-1110/2023-2024-Graduate-Catalog.pdf'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == '7cb4005807c7305e4665d51badf4de0a74904b4dd13ddf3d5ac65bce8ae63dee'
    import subprocess
    body = subprocess.run(['pdftotext', '-raw', str(path), '-'], capture_output=True, text=True, check=True).stdout
    heading = re.compile(r'(?m)^(Professors|Associate Professors|Assistant Professors):')
    heads = list(heading.finditer(body))
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(body)
        block = body[h.start():min(end, h.start() + 900)]
        match = re.search(r'(?<![\w-])' + re.escape(spelling) + r'\s*;', block, re.I)
        if match:
            quote = ' '.join(block[:match.end()].split())
            assert spelling.casefold() in quote.casefold()
            return dict(unit='Virginia Tech 2023–24 graduate catalog',
                        url='https://www.registrar.vt.edu/content/dam/registrar_vt_edu/archived-catalogs/catalog-2023-2024.pdf',
                        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                        raw_path=str(path.relative_to(ROOT.parent)), observed='2023',
                        quote=quote, ladder=True, rank=h.group(1), catalog_name=spelling)
    raise AssertionError(f'No professor-rank catalog entry for {name} ({spelling})')


def registrar_evidence(name, records):
    first, last = REGISTRAR_FIRST.get(name, name.split()[0]), name.split()[-1]
    # Yue Joseph Wang is printed as WANG, Yue Joseph. All selected names have
    # a unique registrar paragraph starting with surname and spelled given name.
    rx = re.compile(rf'^{re.escape(last)},\s+{re.escape(first)}\b', re.I)
    for year, url, sha, body in sorted(records, reverse=True):
        assert hashlib.sha256(zlib.decompress(body)).hexdigest() == sha
        paragraphs = [' '.join(p.stripped_strings) for p in BeautifulSoup(zlib.decompress(body), 'html.parser').find_all('p')]
        quote = None
        for paragraph in paragraphs:
            if rx.search(paragraph):
                title = re.search(r'\b(?:Professor\b|Prof\.)', paragraph[:160], re.I)
                if title:
                    quote = paragraph[:title.end()]
                    break
        if not quote:
            continue
        assert not C.NOT_LADDER.search(quote)
        assert not re.search(r'\b(?:Research|Emeritus|Adjunct|Clinical|Visiting)\b', quote, re.I)
        return dict(unit='Virginia Tech registrar faculty directory', url=url, sha256=sha,
                    observed=f'{year}0101', quote=quote, ladder=True)
    raise AssertionError(f'no verified registrar professor entry: {name}')


def main():
    candidates = {c['name']: c for c in json.loads((VT / 'derived/cs-related-candidates.json').read_text())}
    hand = C.hand_evidence('vt')  # validates each profile quote against saved capture bytes
    db = sqlite3.connect(ROOT / 'listings/vt/raw/faculty-directory-captures.sqlite')
    records = db.execute('select year,url,sha256,body_zlib from captures').fetchall()
    db_persons = {p['pid']: p for p in json.loads((VT / 'derived/dblp-affiliated.json').read_text())['persons']}
    decisions = []
    for name in HAND_NAMES + REGISTRAR_NAMES:
        c = candidates[name]
        assert c['source'] == 'dblp_affiliation' and c['dblp_window'] >= C.MIN_DBLP
        assert any('Virginia' in a or 'Virginia Polytech' in a for a in c['affiliations'])
        if name in HAND_NAMES:
            receipts = [e for e in hand[' '.join(C.toks(name))] if e['ladder']]
            assert receipts, name
            ev = receipts[0]
        else:
            ev = registrar_evidence(name, records)
        window = c['dblp_window']
        decisions.append(dict(
            name=name, aliases=c.get('aliases') or [], source=c['source'],
            decision='accepted',
            reason=f"faculty ({ev['unit']} professor-rank evidence); {window} DBLP records in 2016–2026 and a Virginia Tech affiliation",
            cs_basis=dict(dblp=[c['dblp']], dblp_window=window,
                          affiliation_notes=c['affiliations'],
                          evidence=[dict(url=c['dblp'], source='DBLP affiliated source inventory', quote=c['affiliations'][0])]),
            faculty_evidence=[ev], years_listed=[int(ev['observed'][:4])],
            units_searched=[ev['unit']],
            provisional='Full affiliated-unit and OpenAlex sweep review pending; no census addition or package admission yet.',
        ))
    # The university's research-lab alumni roster identifies these DBLP
    # candidates as VT doctoral graduates with subsequent appointments away
    # from VT. Keep common-name cases without corroborating affiliation open.
    alumni_path = ROOT.parent / 'scratch/vt-followthrough-1110/identity-sources/cnsr-people.html'
    alumni_raw = alumni_path.read_bytes()
    alumni_sha = 'bd5b4ebb4000ec7d3c8b2de91f6c583bd1ec6259e350ac93e8f1c60c14ea0c4a'
    assert hashlib.sha256(alumni_raw).hexdigest() == alumni_sha
    alumni_text = ' '.join(BeautifulSoup(alumni_raw, 'html.parser').stripped_strings)
    for name in CNSR_ALUMNI:
        c = candidates[name]
        assert c['source'] == 'dblp_affiliation' and c['dblp_window'] >= C.MIN_DBLP
        person = db_persons[c['dblp']]
        assert not person['disambiguation']
        assert any('Virginia Tech' in a or 'Virginia Polytechnic' in a for a in c['affiliations'])
        anchor = CNSR_IDENTITY_ANCHORS.get(name)
        if anchor:
            assert any(anchor in a['text'] for a in person['affiliations']), (name, anchor)
        match = re.search(r'\b' + re.escape(name) + r'\b', alumni_text)
        assert match, name
        window = alumni_text[match.start():match.start() + 300]
        assert re.search(r'Ph\.D\.? in (?:CS|ECE)@VT,', window[:80]), name
        joined = window.find('Joined ')
        assert 0 < joined < 180, name
        quote = window[:joined + 65].strip()
        assert quote in alumni_text
        decisions.append(dict(
            name=name, aliases=c.get('aliases') or [], source=c['source'],
            decision='not_faculty_listed',
            reason='Official Virginia Tech CNSR alumni roster identifies a VT PhD and later external placement; no VT ladder appointment is established in the reviewed sources.',
            cs_basis=dict(dblp=[c['dblp']], dblp_window=c['dblp_window'],
                          affiliation_notes=c['affiliations'], identity_anchor=anchor),
            faculty_evidence=[], status_evidence=[dict(
                url='https://www.cnsr.ictas.vt.edu/people.html',
                sha256=alumni_sha, raw_path=str(alumni_path.relative_to(ROOT.parent)),
                observed='20261110', quote=quote)],
            years_listed=[], units_searched=['CNSR lab alumni roster',
                                              '2016–21 registrar faculty directory',
                                              '2023–24 graduate catalog',
                                              '2026 affiliated-unit listings'],
            provisional='Full affiliated-unit historical listing review pending; revisit if later ladder evidence appears.',
        ))
    pages = C.unit_pages('vt')
    for name in (*UNIT_LADDER_NAMES, *UNIT_OTHER_RANK_NAMES, *WIRELESS_OTHER_RANK_NAMES,
                 *CATALOG_NAMES, *BOV_LADDER_NAMES, *BOV_OTHER_RANK_NAMES):
        c = candidates[name]
        assert c['source'] == 'dblp_affiliation' and c['dblp_window'] >= C.MIN_DBLP
        person = db_persons[c['dblp']]
        assert not person['disambiguation'] and person['n_window'] == c['dblp_window']
        assert ('affiliation_note' in person['matched_by'] or
                any('.vt.edu' in u for u in person['urls']))
        if name in CATALOG_NAMES:
            ev = catalog_evidence(name, CATALOG_NAMES[name])
        elif name in BOV_LADDER_NAMES or name in BOV_OTHER_RANK_NAMES:
            ev = bov_evidence(name, *(BOV_LADDER_NAMES.get(name) or BOV_OTHER_RANK_NAMES[name]))
        elif name in WIRELESS_OTHER_RANK_NAMES:
            from school_web import con, live, flat
            url = 'https://wireless.vt.edu/Directory/faculty.html'
            res = live(con('vt'), url)
            assert res and res[0] == 200
            receipts = C.faculty_evidence([('Wireless', url, res[1], '20261110', flat(res[2]))], [name])
            assert len(receipts) == 1 and not receipts[0]['ladder'], (name, receipts)
            ev = receipts[0]
        else:
            receipts = C.faculty_evidence(pages, [name])
            assert len(receipts) == 1, (name, receipts)
            ev = receipts[0]
            assert ev['ladder'] == (name in UNIT_LADDER_NAMES)
            if name == 'Hanif D. Sherali':
                # The directory says "Professor Emeritus" immediately after the
                # parser's shorter title quote; preserve the full rank phrase.
                unit_page = next(p for p in pages if p[0] == ev['unit'] and p[2] == ev['sha256'])
                assert ev['quote'] + ' Emeritus' in unit_page[4]
                ev = {**ev, 'quote': ev['quote'] + ' Emeritus'}
        accepted = name in (*UNIT_LADDER_NAMES, *CATALOG_NAMES, *BOV_LADDER_NAMES)
        if accepted:
            assert ev['ladder']
        else:
            assert not ev['ladder']
        identity = (f"DBLP official Virginia Tech URL: {next(u for u in person['urls'] if '.vt.edu' in u)}"
                    if not c['affiliations'] else f"DBLP affiliation: {next(a for a in c['affiliations'] if 'Virginia' in a)}")
        decisions.append(dict(
            name=name, aliases=c.get('aliases') or [], source=c['source'],
            decision='accepted' if accepted else 'research_or_other_rank',
            reason=(f"professor-rank faculty ({ev['unit']}); {c['dblp_window']} DBLP records in 2016–2026"
                    if accepted else f"{ev['unit']} lists a non-ladder research or emeritus professor rank; not a ladder PI appointment"),
            cs_basis=dict(dblp=[c['dblp']], dblp_window=c['dblp_window'],
                          affiliation_notes=c['affiliations'], identity_basis=identity,
                          evidence=[dict(url=c['dblp'], source='DBLP affiliated source inventory', quote=identity)]),
            faculty_evidence=[ev], years_listed=[int(ev['observed'][:4])],
            units_searched=[ev['unit']],
            provisional='Full affiliated-unit and OpenAlex sweep review pending; no census addition or package admission yet.',
        ))
    audit = json.loads((ROOT.parent / 'scratch/vt-followthrough-1110/profile-dblp-audit.json').read_text())
    assert audit['school'] == 'vt' and audit['dump'] == C.P.DBLP_DUMP_FILE
    for name in PROFILE_DBLP_NAMES:
        c = candidates[name]
        assert c['source'] == 'official_profile_ladder'
        receipts = [e for e in hand[' '.join(C.toks(name))] if e['ladder']]
        assert receipts, name
        rows = audit['people'][name]
        school = [r for r in rows if any('Virginia Tech' in a or 'Virginia Polytechnic' in a for a in r['affiliations'])]
        if school:
            assert len(school) == 1, name
            record = school[0]
            basis = 'unique DBLP person record with a Virginia Tech affiliation'
        else:
            assert len(rows) == 1, name
            record = rows[0]
            assert any(name.casefold() == re.sub(r'\s+\d{4}$', '', n).casefold() for n in record['names'])
            basis = 'only DBLP person record matching the official profile name'
        assert not record['disambiguation'] and record['n_window'] >= C.MIN_DBLP
        ev = receipts[0]
        decisions.append(dict(
            name=name, aliases=c.get('aliases') or [], source=c['source'], decision='accepted',
            reason=f"faculty ({ev['unit']} professor-rank evidence); {basis}; {record['n_window']} DBLP records in 2016–2026",
            cs_basis=dict(dblp=[record['pid']], dblp_window=record['n_window'],
                          affiliation_notes=record['affiliations'], identity_basis=basis,
                          evidence=[dict(url=record['pid'], source=audit['dump'],
                                         sha256=record['person_record_sha256'], quote=record['names'][0])]),
            faculty_evidence=[ev], years_listed=[int(ev['observed'][:4])],
            units_searched=[ev['unit']],
            provisional='Full affiliated-unit and OpenAlex sweep review pending; no census addition or package admission yet.',
        ))
    # The captured CS profile states a collegiate role, which the VT charter
    # does not count as a ladder PI appointment.
    esakia = candidates['Andrey Esakia']
    esakia_ev = [e for e in hand[' '.join(C.toks('Andrey Esakia'))] if not e['ladder']]
    assert len(esakia_ev) == 1 and 'Collegiate Assistant Professor' in esakia_ev[0]['quote']
    decisions.append(dict(
        name='Andrey Esakia', aliases=esakia.get('aliases') or [], source=esakia['source'],
        decision='research_or_other_rank',
        reason='Saved Virginia Tech CS profile identifies a collegiate assistant professor; this is not a ladder PI role under the VT charter.',
        cs_basis=dict(dblp=[esakia['dblp']], dblp_window=esakia['dblp_window']),
        faculty_evidence=esakia_ev, years_listed=[int(esakia_ev[0]['observed'][:4])],
        units_searched=['Computer Science'],
    ))
    assert len(decisions) == len(HAND_NAMES) + len(REGISTRAR_NAMES) + len(PROFILE_DBLP_NAMES) + len(UNIT_LADDER_NAMES) + len(UNIT_OTHER_RANK_NAMES) + len(WIRELESS_OTHER_RANK_NAMES) + len(CATALOG_NAMES) + len(BOV_LADDER_NAMES) + len(BOV_OTHER_RANK_NAMES) + len(CNSR_ALUMNI) + 1
    assert len({d['name'] for d in decisions}) == len(decisions)
    doc = dict(school='vt', reviewed=datetime.date.today().isoformat(),
               rule='Individual source-checked professor role plus a DBLP Virginia Tech affiliation or unique exact-name person record, with at least five 2016–2026 records. Full unit and paper sweep pending.',
               provisional=True, counts=dict(accepted=sum(d['decision'] == 'accepted' for d in decisions),
                                             research_or_other_rank=sum(d['decision'] == 'research_or_other_rank' for d in decisions),
                                             not_faculty_listed=sum(d['decision'] == 'not_faculty_listed' for d in decisions)), decisions=decisions)
    for path in [VT / 'reviewed/stage2-preliminary-decisions.json', VT / 'reviewed/cs-related-review.json']:
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n')
    print(f'{len(decisions)} source-checked decisions written')


if __name__ == '__main__':
    main()
