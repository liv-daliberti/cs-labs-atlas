"""Reproduce reviewed Georgia Tech relationships from immutable source captures."""
import hashlib
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup
import atlas_paths as P
import schema_check

SESSION = 'codex-gatech10-20261126'
RUN = P.school_part('gatech', 'work') / 'students15-1126'
OUT = Path(__file__).resolve().parent
WT = OUT.parents[1]
manifest = json.loads((RUN / 'sources.json').read_text())
new = []
sections = []
held = []


def source(url):
    s = manifest[url]
    body = Path(s['body_path']).read_bytes()
    assert s['status'] == 200
    assert hashlib.sha256(body).hexdigest() == s['sha256']
    return s


def visible(s):
    soup = BeautifulSoup(Path(s['body_path']).read_bytes(), 'html.parser')
    for el in soup(['script', 'style', 'noscript']):
        el.decompose()
    return ' '.join(soup.get_text(' ', strip=True).split())


def block(s, start, end):
    t = visible(s)
    a = t.index(start)
    b = t.index(end, a + len(start)) if end else len(t)
    return t[a:b].strip()


def add(pi, s, names, role, quote, *, years=None, alumni=False,
        relationship='membership', host=None, proof=None, basis=None):
    names = names.split('|') if isinstance(names, str) else names
    text = Path(s['body_path']).read_text() if s['url'].endswith('.json') else visible(s)
    assert quote in text
    if host:
        assert host in text
    for name in names:
        assert name in quote
        row = dict(name=name, role=role, relationship=relationship,
                   years=years or [int(s['observed'][:4])] * 2,
                   years_basis=basis or ('explicit source dates' if years else 'capture_date'),
                   alumni=alumni, url=s['url'], sha256=s['sha256'], quote=quote,
                   observed=s['observed'], reviewed=True, reviewed_by=SESSION,
                   auto=False, rule='R-STU-01', batch='gatech-students15-1126',
                   note='Source-stated student role and single-PI group membership; no unobserved enrollment years or degree level inferred.')
        if s.get('capture_url'):
            row['capture_url'] = s['capture_url']
        if host:
            row['host_quote'] = host
        if proof:
            ps, pq = proof
            assert pq in visible(ps)
            row['corroborating_sources'] = [dict(url=ps.get('capture_url') or ps['url'], sha256=ps['sha256'], quote=pq)]
        new.append(dict(pi=pi, **row))
    sections.append(dict(pi=pi, url=s.get('capture_url') or s['url'], sha256=s['sha256'],
                         role=role, relationship=relationship, names=names, alumni=alumni))


p = 'Shreyas Kousik'
s = source('cached-1781')
add(p, s, 'Long Kiu Chung|Wonsuhk Jung|Chuizheng Kong|Dennis Anthony|Dan Choe|Ryota Ozaki|Avi Balakirsky|Sundhar Vinodh Sangeetha', 'phd', block(s, 'Ph.D. Students', 'M.S. Students'))
add(p, s, ['Suvrat Jain'], 'masters', block(s, 'M.S. Students', 'Undergraduate Students'))
add(p, s, 'Advaith Nidumukkala|Karishma Kamalahasan|Andrew Mattei|Benjamin Davis|Pranav Nair|Sheel Shailesh|Nandana Avasarala|Luca Baldelli|Phuoc (Benne) Le|Tianze Qiu|Nandika Kohli|Rowan Holcombe|Krish Kittur|Kirk Siegel|Aydin Kim|Vedanth Iyer|Michael Hakim', 'undergraduate', block(s, 'Undergraduate Students', 'Alumni'))
q = block(s, 'Alumni', 'Visiting Student')
# The source's alumni degree labels date the past membership. Future class years do not.
for match in re.finditer(r'([A-Z][A-Za-z ()\-]+?) \((MS|ME|BS) [A-Z]+ ’(\d{2})[^)]*\)', q):
    name, degree, yy = match[1].strip(), match[2], int(match[3])
    name = re.sub(r'^(Alumni Master’s |Undergraduate )', '', name)
    if yy > 26:
        held.append(dict(pi=p, name=name, reason='Alumni heading but future degree cohort; actual membership year unresolved.'))
        continue
    add(p, s, [name], 'undergraduate' if degree == 'BS' else 'masters', match[0], years=[2000 + yy] * 2, alumni=True)
held.append(dict(pi=p, names=['Justin Hunter', 'Yunho Cho'], reason='Current undergraduate list carries past 2025 degree cohorts; no unsupported 2026 student status assigned. Aishik Dhori is dated from the alumni section instead. External-school visitors excluded.'))

p = 'Christopher J. MacLellan'
s = source('https://tail.cc.gatech.edu/people.html')
home = source('cached-1115')
proof = (home, 'Associate Professor School of Interactive Computing College of Computing Georgia Institute of Technology')
add(p, s, 'Zekun (Anderson) Wang|Qiao Zhang|Momin Siddiqui|Jieyu Zhou|Jennifer Reddig|Glen Smith', 'phd', block(s, 'Zekun (Anderson) Wang', 'Shinhaeng Lee'), proof=proof)
for name, role in [('Shinhaeng Lee', 'undergraduate'), ('Karthik Singaravadivelan', 'undergraduate'), ('Aryan Roy', 'masters'), ('Ananya Bhargava', 'undergraduate'), ('Anant Gupta', 'masters')]:
    cues = {'Shinhaeng Lee': 'Undergraduate Student', 'Karthik Singaravadivelan': 'Undergraduate Researcher', 'Aryan Roy': 'Master’s Student', 'Ananya Bhargava': 'Undergraduate Student', 'Anant Gupta': "Master's Student"}
    add(p, s, [name], role, name + ' ' + cues[name], proof=proof)
held.append(dict(pi=p, section='Past Lab Members / high school / staff', reason='Undated former memberships, Jacob Kim high-school status, scientist and postdoc roles excluded from this degree-student batch.'))

p = 'Helen Xu'
s = source('https://itshelenxu.github.io/teaching/')
for name, role, years, start, end, alumni in [
    ('Yicong (Eddy) Luo', 'phd', [2024, 2026], 'Yicong (Eddy) Luo', 'Zhimeng Gao', False),
    ('Zhimeng Gao', 'phd', [2026, 2026], 'Zhimeng Gao', 'Pablo Raigoza', False),
    ('Pablo Raigoza', 'phd', [2026, 2026], 'Pablo Raigoza', 'M.S.', False),
    ('Kepan Zhang', 'masters', [2024, 2024], 'Kepan Zhang', 'Tiancheng (Alex) Zhao', True),
    ('Tiancheng (Alex) Zhao', 'masters', [2026, 2026], 'Tiancheng (Alex) Zhao', 'Other student advising', True)]:
    add(p, s, [name], role, block(s, start, end), years=years, alumni=alumni, relationship='advising', host='Student advising at Georgia Tech')
held.append(dict(pi=p, section='Other student advising', reason='Explicit Berkeley Lab internships and MIT MEng students are outside Georgia Tech scope.'))

p = 'Cindy Xiong'
s = source('https://cyxiong.com/students/')
home = source('cached-1278')
proof = (home, 'I am an Assistant Professor in the School of Interactive Computing at Georgia Tech.')
add(p, s, ['Kylie Lin'], 'phd', '2026 PhD Student Kylie Lin to intern at Google.', years=[2026, 2026], proof=proof)
add(p, s, ['Minsuk Chang'], 'phd', '2026 PhD Student Minsuk Chang to intern at LG AI Lab.', years=[2026, 2026], proof=proof)
add(p, s, ['Songwen Hu'], 'phd', '2025 PhD Student Songwen Hu received the CoCo Pilot Grant at Georgia Tech, co-advised by Professor Ratan Murty.', years=[2025, 2025], proof=proof)
add(p, s, 'Jangkyu Ju|Mark Volovoi', 'student', block(s, 'Current Students', 'Alum Labbies'), proof=proof)
held.append(dict(pi=p, section='Alum Labbies / UMass achievements', reason='Do not transfer UMass relationships to Georgia Tech; untyped current members retain generic student roles.'))

p = 'Jan van den Brand'
s = source('cached-1185')
for name, year in [('Emile Anand', 2024), ('Albert Weng', 2024), ('Anastasiia Alokhina', 2022), ('Daniel J. Zhang', 2022)]:
    add(p, s, [name], 'student', block(s, 'Students Emile', 'There are currently no open PhD positions'), years=[year, 2026], host='School of Computer Science at Georgia Tech')
held.append(dict(pi=p, reason='Students heading does not state each student degree; no PhD role inferred from recruitment wording.'))

p = 'Anna A. Ivanova'
s = source('cached-1811')
for names, role, start, end in [
    ('Will Decker|Taha Binhuraib|Eyas Ayesh|Ruifeng Yu', 'phd', 'Will Decker', 'Seungmin(Min) Cho'),
    ('Kamya Hari', 'masters', 'Kamya Hari', 'George Flint'),
    ('Sydney Idleburg|Sidarth Krishna|Weichen Huang|Malavika Niverthi|Saanvi Sundaram|Ruthu Raghunath', 'undergraduate', 'Sydney Idleburg', 'Mentors & Collaborators')]:
    add(p, s, names, role, block(s, start, end), host='Principal Investigator Anna (Anya) Ivanova')
for name in ['Caleb McKinney', 'Michael Zhou']:
    add(p, s, [name], 'phd', name + ' (GT) - Part-time PhD, 2025-2025', years=[2025, 2025], alumni=True)
held.append(dict(pi=p, reason='George Flint explicitly UC Berkeley; postdocs/technicians and generic RA alumni without student role, plus MIT mentees and collaborators, excluded.'))

p = 'He Wang'
s = source('cached-634')
home = source('cached-633')
proof = (home, 'I have been away from Georgia Tech since 2024/06.')
for name, year, role in [('Adam Behrendt', 2023, 'phd'), ('Jana Boerger', 2022, 'phd'), ('Sung Woo Kim', 2022, 'phd'), ('Pornpawee Bumpensanti', 2021, 'phd'), ('Yufeng Cao', 2020, 'phd'), ('Adrian Rivera Cardoso', 2019, 'phd'), ('Felipe Simon', 2020, 'masters'), ('Rafael Hanashiro', 2020, 'masters')]:
    text = visible(s)
    a = text.index(name)
    end = text.index(')', a) + 1
    add(p, s, [name], role, text[a:end], years=[year, year], alumni=True, proof=proof)
held.append(dict(pi=p, names=['Yiming Jiang'], reason='Graduation 2025 is after documented June 2024 departure; separate Georgia Tech thesis/advising evidence required. No capture-year enrollment inferred on a page explicitly no longer updated.'))

p = 'Fan Zhang'
s = source('cached-1511')
for names, role, start, end in [
    ('Sungmin Kim|Stephen Yoo|Kai Tan|Hojoon Son|Youndo Do|Michael Doran|Marc Zebrowitz|Jason Reed|Chad Meece', 'phd', 'Ph.D. Sungmin', 'M.S.'),
    ('Spencer Banks|MJay Choi', 'masters', 'M.S.', 'Undergraduate'),
    ('Johan Gouws|Adolfo Ruiz Padron|Lavanya Natarajan|Max Goddard|Winona Wiley|Cheng-Yuan Li|Emma Zoccoli|Richard Hunnewell|Jackson Stahl', 'undergraduate', 'Undergraduate', 'Alumni')]:
    add(p, s, names, role, block(s, start, end), host='Lab Director Dr. Fan Zhang')
held.append(dict(pi=p, section='Alumni', reason='Alumni degree roles and years are unstated; not admitted by the capture date.'))

p = 'Wei Zhu'
s = source('cached-1579')
home = source('https://sites.google.com/view/weizhumath/home')
add(p, s, 'Wenbo Hao|Zhilin (Bill) Li|Fan Liu|Amya Luo|Ziyu Tian|Kaichen Shen', 'phd', block(s, 'Doctoral Students', 'Group Alumni'), proof=(home, 'Georgia Tech School of Mathematics'))
held.append(dict(pi=p, reason='Shaoxuan Chen explicitly UMass; former undergraduates explicitly UMass; postdocs not students.'))

p = 'Rose McCarty'
s = source('https://mccarty.math.gatech.edu/students.shtml')
home = source('https://mccarty.math.gatech.edu/')
for name, year, alumni, start, end in [('Caleb McFarland', 2024, False, 'Caleb McFarland', 'Xiying Du'), ('Xiying Du', 2024, False, 'Xiying Du', 'James Anderson'), ('James Anderson', 2024, True, 'James Anderson', None)]:
    add(p, s, [name], 'phd', block(s, start, end), years=[year, year if alumni else 2026], alumni=alumni, proof=(home, 'I am an Assistant Professor at Georgia Tech'))

p = 'Jennifer Kim'
s = source('cached-1108')
for names, role, start, end in [
    ('Rachel Lowy|Kaely Hall|Seungwan Jin|Hyesoo Park', 'phd', 'PhD students:', 'MS students:'),
    ('Yeonsoo Chang|Ethan Sylvia|Ankith Chandra', 'masters', 'MS students:', 'BS students:'),
    ('Korina Goldsmith|Aakrishtaa Kumar|Tanisha Paryani|Veena Gonugondla', 'undergraduate', 'BS students:', 'Classes')]:
    add(p, s, names, role, block(s, start, end))

p = 'Mohsen Moghaddam'
s = source('cached-1297')
for name, role in [('Akhil Aji', 'phd'), ('Parisa Ghasemi', 'phd'), ('Austin Graves', 'phd'), ('Seok Joon Kim', 'phd'), ('Mahya Qorbani', 'phd'), ('Mahya Qorbani', 'masters'), ('Sandeep John Philip', 'masters'), ('Dante Santaniello', 'masters'), ('Mann Mehta', 'undergraduate'), ('Rohan Mysore', 'undergraduate'), ('Edson Petrini', 'undergraduate'), ('Carson Ray', 'undergraduate'), ('Kuber Sarwal', 'undergraduate')]:
    text = visible(s)
    a = text.index(name)
    # Complete bio is bounded by the next roster heading in the saved HTML.
    soup = BeautifulSoup(Path(s['body_path']).read_bytes(), 'html.parser')
    all_heads = [h.get_text(' ', strip=True) for h in soup.find_all(['h2', 'h3'])]
    next_head = all_heads[all_heads.index(name) + 1]
    q = text[a:text.index(next_head, a + len(name))]
    # All admitted bios explicitly identify GT or its own GT co-advisers; Sakib is held.
    add(p, s, [name], role, q, relationship='advising' if name == 'Mahya Qorbani' else 'membership', host='Principal Investigator Mohsen Moghaddam')
held.append(dict(pi=p, names=['Sakib Reza', 'Yi Jade Han', 'Varun Phadke', 'Chenxi Chelsea Yuan'], reason='Sakib is explicitly co-supervised at Northeastern; former members are undated and/or explicitly Northeastern. Postdocs and collaborators excluded.'))

p = 'Galyna V. Livshyts'
s = source('https://glivshyts6.math.gatech.edu/')
for name, role, years, start, end, alumni in [
    ('Manuel Fernandez V', 'phd', [2022, 2025], 'Manuel Fernandez V', 'Achintya Polavarapu', True),
    ('Achintya Polavarapu', 'phd', [2024, 2026], 'Achintya Polavarapu', 'Masters students:', False),
    ('Rocco Tenaglia', 'masters', [2021, 2022], 'Rocco Tenaglia', 'Undergraduate students:', True),
    ('Neil Patram', 'undergraduate', [2022, 2026], 'Neil Patram', 'Seminars and conferences organized', False)]:
    add(p, s, [name], role, block(s, start, end), years=years, alumni=alumni)
held.append(dict(pi=p, names=['Johaness Hosle'], reason='REU mentorship date is given, but home institution / visiting-student scope is unresolved. Postdocs excluded.'))

p = 'Eunhye Song'
s = source('https://sites.google.com/view/eunhyesongphd/home')
q = block(s, 'PHD/POSTDOCTORAL ADVISEES Current', 'Past * Graduation')
for name, year in [('McLaren Wang', 2025), ('Dongjoon Lee', 2024), ('Jaime Guillermo Gonzalez Hodar', 2022)]:
    add(p, s, [name], 'phd', q, years=[year, 2026], relationship='advising', host='2022-2025 Coca-Cola Foundation Early Career Professor and Assistant Professor, Industrial and Systems Engineering, Georgia Institute of Technology')
held.append(dict(pi=p, section='Past PhD/postdoctoral advisees', reason='Mixed doctoral/postdoc heading with untyped former rows and overlapping Penn State history; no inferred doctoral roles or Georgia Tech degree affiliations.'))

p = 'Yan Wang'
s = source('https://msse.gatech.edu/students.html')
faculty = source('https://msse.gatech.edu/facultyAssociates.html')
proof = (faculty, 'Faculty & Associates Dr. Yan Wang Professor School of Mechanical Engineering')
add(p, s, 'Jungin Kim|Eunsik Choi|Sonia Lemou|Rafael De Farias|Luka Malashkhia', 'phd', block(s, 'Students Jungin Kim', 'Angela Sun'), proof=proof)
add(p, s, ['Angela Sun'], 'undergraduate', block(s, 'Angela Sun', 'Contact Us'), proof=proof)
held.append(dict(pi=p, reason='Ownership checked against Faculty & Associates page: Yan Wang is the sole professor; Yunya Liu is a postdoc and is not added as a student.'))

path = P.reviewed_path('few-students-evidence.json', 'gatech', code=WT)
records = json.loads(path.read_text())
records = [g for g in records if not any(s.get('batch') == 'gatech-students15-1126' for s in g['students'])]
first_ten = {r['pi'] for r in json.loads((WT / 'reports/gatech-students10-1126/additions.json').read_text())}
selected = set(r['pi'] for r in new)
assert len(selected) == 15 and not selected.intersection(first_ten)
assert len({(r['pi'], r['name'], r['role']) for r in new}) == len(new)
baseline = json.loads(P.data('pis.json', 'gatech').read_text())
by_pi = {p['pi']: p for p in baseline}
baseline_path = OUT / 'baseline.json'
baseline_receipt = json.loads(baseline_path.read_text()) if baseline_path.exists() else None
for pi in dict.fromkeys(r['pi'] for r in new):
    original_counts = baseline_receipt['selected'][pi] if baseline_receipt else by_pi[pi]['counts']
    assert original_counts['students'] == 0, pi
    records.append(dict(pi=pi, students=[{k:v for k,v in r.items() if k != 'pi'} for r in new if r['pi'] == pi], note='Source-reviewed additional fifteen-lab batch, gatech-students15-1126.'))
errors = schema_check.validate(records, json.loads((WT / 'schemas/few-students-evidence.schema.json').read_text()))
assert not errors, errors
path.write_text(json.dumps(records, indent=1, ensure_ascii=False) + '\n')
(OUT / 'additions.json').write_text(json.dumps(new, indent=2, ensure_ascii=False) + '\n')
(OUT / 'roster-review.json').write_text(json.dumps(dict(session=SESSION, sections=sections, held=held), indent=2, ensure_ascii=False) + '\n')
used = {r['sha256'] for r in new}
used.update(x['sha256'] for r in new for x in r.get('corroborating_sources', []))
(OUT / 'sources.json').write_text(json.dumps([s for s in manifest.values() if s['sha256'] in used], indent=2) + '\n')
if baseline_receipt is None:
    baseline_path.write_text(json.dumps(dict(pis=len(baseline), zero_student_labs=sum(p['counts']['students'] == 0 for p in baseline), student_memberships=sum(p['counts']['students'] for p in baseline), selected={pi:by_pi[pi]['counts'] for pi in sorted(selected)}), indent=2) + '\n')
pairs = {(r['pi'], r['name']) for r in new}
print(json.dumps(dict(episodes=len(new), relationships=len(pairs), counts={pi:sum(p == pi for p,n in pairs) for pi in sorted(selected)}), indent=2))
