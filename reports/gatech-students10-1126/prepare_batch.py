"""Reproduce reviewed Georgia Tech relationships from immutable source captures."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup
import atlas_paths as P
import schema_check

SESSION = 'codex-gatech10-20261126'
RUN = P.school_part('gatech', 'work') / 'students10-1126'
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
                   auto=False, rule='R-STU-01', batch='gatech-students10-1126',
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


p = 'Alberto Dainotti'
s = source('https://www.cc.gatech.edu/~adainotti6/')
q = block(s, 'PhD Students and PostDocs', 'Former:')
add(p, s, 'Iliana Xygkou|Olivier Bemba|Philip Lengyel|Weili Wu|Zahra Yazdani|Zhiyi Chen', 'phd', q,
    host='Director of the Internet Intelligence Lab Georgia Tech')
held.append(dict(pi=p, section='Former', reason='Former roster explicitly describes UC San Diego students/postdocs; not Georgia Tech relationships.'))

p = 'Ashwin Pananjady'
s = source('https://sites.gatech.edu/ashwin-pananjady/group/')
add(p, s, 'Tianjiao Li|Mengqi Lou|Sheng Zhang', 'phd', block(s, 'phd students', 'postdocs'),
    relationship='advising', host='I am fortunate to advise and learn from those listed below.')
held.append(dict(pi=p, names=['Jingyan Wang'], reason='Postdoctoral role, outside requested student population.'))

p = 'Alexander T Adams'
s = source('https://www.uncommonsenselabs.com/people')
add(p, s, 'Adam Cherepon|Rishabh Goel|Sheraz Hassan|Kefan Song|Sixuan Wu|Dario Liu|Alexander Ford|Jung-Hyun Bae|Xinye Wang|Yibo Fu|Rizky Ilhamsyah|Zach Deak|Unnathi Annapurna', 'phd', block(s, 'Ph.D. Students', 'Affiliated PhD Students'))
add(p, s, 'Samuel Wilcox|Yingting Gao', 'phd', block(s, 'Affiliated PhD Students', 'Collaborators'))
add(p, s, 'Payne Gumbrill|Sidney Wise|Amelia Jemal|Bingshao Kang|Miranda Dominguez|Jenson Huang|Rutuja Shendage|Priyanshu Mehta|Mei Wan|Tanya Punater|Albert Kuo|Janvi Shah|Allen Gao|Riley Liu|Isaac Kaufman|Hudson Etkin|Shivani Sridharan|Anne Youn', 'student', block(s, 'Masters & Undergraduate', 'Alumni (MS and Undergrads)'))
held.append(dict(pi=p, section='Alumni (MS and Undergrads)', reason='Undated past memberships; no capture-year enrollment assigned. Collaborators are not student rows.'))

p = 'Brendan Saltaformaggio'
s = source('https://cyfi.ece.gatech.edu/people/')
for names, role, start, end in [
    ('David Oygenblik|Yizhi Huang|Filippos Sofias|Neil Van Eikema Hommes|Kian Esmaeili', 'phd', 'David Oygenblik', 'Min Ho Lee'),
    ('Min Ho Lee|Tang-Wei Wang', 'masters', 'Min Ho Lee', 'Teja Akella'),
    ('Teja Akella|Tanmay Gupta|Andrew Son', 'undergraduate', 'Teja Akella', 'CyFI Lab Alumni')]:
    add(p, s, names, role, block(s, start, end), host='People Professor Brendan Saltaformaggio')
# Every dated PhD/MS/BS alumni entry is a degree episode; employer labels are excluded.
soup = BeautifulSoup(Path(s['body_path']).read_bytes(), 'html.parser')
heads = soup.find_all('h2')
for h in heads:
    if h.find(['h2', 'h3']):
        continue
    value = ' '.join(h.get_text(' ', strip=True).split())
    match = re.match(r'(.+?) (PhD|MS|BS) (?:ECE|CS|Cybersecurity) (20\d\d)\b', value)
    if match:
        name = match[1]
        year = int(match[3])
        assert 2016 <= year <= 2026
        quote = match[0]
        add(p, s, [name], {'PhD': 'phd', 'MS': 'masters', 'BS': 'undergraduate'}[match[2]], quote,
            years=[year, year], alumni=True, host='People Professor Brendan Saltaformaggio')
held.append(dict(pi=p, section='Postdoc', reason='Current and former postdocs excluded from student recovery.'))

p = 'Danfei Xu'
s = source('https://rl2.cc.gatech.edu/members.json')
home = source('https://rl2.cc.gatech.edu/')
data = json.loads(Path(s['body_path']).read_text())['members']
assert [x['name'] for x in data['faculty']] == [p]
for category, role in [('phd_students', 'phd'), ('masters_students', 'masters'), ('undergrad_students', 'undergraduate')]:
    for member in data[category]:
        raw = Path(s['body_path']).read_text()
        start = raw.index('"name": ' + json.dumps(member['name']))
        end = raw.index(',', raw.index('"role":', start))
        quote = raw[start:end]
        add(p, s, [member['name']], role, quote,
            host='"name": "Danfei Xu",\n          "role": "Lab Director"',
            proof=(home, 'Georgia Institute of Technology'))
held.append(dict(pi=p, section='alumni.json / robots', reason='Undated alumni need membership dates; seven robot equipment entries are not people. Co-advisers are retained literally without adding other labs to this batch.'))

p = 'Daniel Genkin'
s = source('https://architecture.fail/')
add(p, s, 'Nicolas Berrios|Jalen Chuang|Chengsong Diao|Walter Wang', 'student', block(s, 'Students Nicolas Berrios', 'Alumni'), host='People Faculty Daniel Genkin genkin@gatech.edu')
held.append(dict(pi=p, section='Alumni', reason='Undated alumni and mixed past-institution context held. Generic student heading does not establish a PhD degree.'))

p = 'Divya Mahajan'
s = source('https://www.divyamahajan.com/students')
home = source('https://www.divyamahajan.com/')
add(p, s, 'Kunal Jain|Junkyum Kim|Seokjin Go|Irene Wang', 'phd', block(s, 'Current Students', 'Graduated Students'),
    proof=(home, 'Georgia Tech'))
held.append(dict(pi=p, section='Graduated Students / Visiting Students', reason='Graduated students are undated; visitors have explicit other-school affiliations. No current-year enrollment inferred for alumni.'))

p = 'Kartik Goyal'
s = source('https://kartikgo.github.io/')
for names, role, start, end in [
    ('Tomohiro Sawada|Nghia (Max) Le|Ruyuan Zuo', 'phd', 'Ph.D. Students :', "Masters' Students :"),
    ('Jakob Bjorner|Yunxiang Yan|Myungjin Shin|Kunal Daga', 'masters', "Masters' Students :", 'Undergraduate Students :'),
    ('Oleksandr Lavreniuk|Saniya Srivastava', 'undergraduate', 'Undergraduate Students :', 'Past students :')]:
    add(p, s, names, role, block(s, start, end), relationship='advising', host='Advising')
held.append(dict(pi=p, section='Past students', reason='Past memberships have no dates; degree of Huopu Zhang is unstated.'))

p = 'B. Aditya Prakash'
s = source('https://web.archive.org/web/20251021194511id_/https://faculty.cc.gatech.edu/~badityap/index.html')
add(p, s, 'Arjun Chodhury|Shangqing Xu|Haoxin Liu|Zhiyuan Zhao|Harshavardhan Kamarthi', 'phd', block(s, 'PhD Students Arjun', 'Dr. Jiaming Cui'),
    host='Georgia Institute of Technology', basis='Wayback observation year 2025; retrieved from immutable local capture in 2026')
held.append(dict(pi=p, section='Dr. alumni / MS, Undergraduate and High-school Students', reason='Undated alumni, prior Virginia Tech appointments and ambiguous current/past school scope held. Only five plainly active doctoral entries in the dated 2025 snapshot are admitted.'))

p = 'Suguman Bansal'
s = source('https://suguman.github.io/group/')
home = source('https://suguman.github.io/')
proof = (home, 'Assistant Professor, School of Computer Science, Georgia Institute of Technology')
for name, role, start, end, years, alumni in [
    ('Vignesh Subramanian', 'phd', '**Vignesh Subramanian**', '**Lu-Chin Chang**', [2023, 2026], False),
    ('Lu-Chin Chang', 'phd', '**Lu-Chin Chang**', '**Sankar Gopalkrishna**', [2026, 2026], False),
    ('Sankar Gopalkrishna', 'masters', '**Sankar Gopalkrishna**', '**Krishaang Gupta**', [2026, 2026], False),
    ('Krishaang Gupta', 'masters', '**Krishaang Gupta**', 'alumni', [2026, 2026], False),
    ('Amogh Palasamudram', 'masters', '**Amogh Palasamudram**', '**Ramneet Singh**', [2025, 2026], True),
    ('Yash Kankariya', 'undergraduate', '**Yash Kankariya**', '**Gaurav Mahala**', [2023, 2023], True),
    ('Kaushik Arcot', 'masters', '**Kaushik Arcot**', '**Siddharth Meenachi Sundaram**', [2024, 2024], True),
    ('Siddharth Meenachi Sundaram', 'masters', '**Siddharth Meenachi Sundaram**', '**Aryan Saboo**', [2024, 2024], True),
    ('Aryan Saboo', 'undergraduate', '**Aryan Saboo**', '© Copyright', [2025, 2026], True)]:
    add(p, s, [name], role, block(s, start, end), years=years, alumni=alumni, proof=proof)
held.append(dict(pi=p, names=['Ramneet Singh', 'Gaurav Mahala'], reason='Explicit IIT Delhi / IIT Bombay student affiliations excluded from Georgia Tech school population.'))

path = P.reviewed_path('few-students-evidence.json', 'gatech', code=WT)
records = json.loads(path.read_text())
records = [g for g in records if not any(s.get('batch') == 'gatech-students10-1126' for s in g['students'])]
baseline = json.loads(P.data('pis.json', 'gatech').read_text())
by_pi = {p['pi']: p for p in baseline}
for pi in dict.fromkeys(r['pi'] for r in new):
    assert by_pi[pi]['counts']['students'] == 0, pi
    rows = [{k: v for k, v in r.items() if k != 'pi'} for r in new if r['pi'] == pi]
    records.append(dict(pi=pi, students=rows, note='Source-reviewed batch gatech-students10-1126; explicit membership preserves role without asserting personal advising.'))
errors = schema_check.validate(records, json.loads((WT / 'schemas/few-students-evidence.schema.json').read_text()))
assert not errors, errors
assert len({r['pi'] for r in new}) == 10
assert len({(r['pi'], r['name']) for r in new}) == len(new)
path.write_text(json.dumps(records, indent=1, ensure_ascii=False) + '\n')
(OUT / 'additions.json').write_text(json.dumps(new, indent=2, ensure_ascii=False) + '\n')
(OUT / 'roster-review.json').write_text(json.dumps(dict(session=SESSION, sections=sections, held=held), indent=2, ensure_ascii=False) + '\n')
used = {r['sha256'] for r in new}
used.update(x['sha256'] for r in new for x in r.get('corroborating_sources', []))
(OUT / 'sources.json').write_text(json.dumps([s for s in manifest.values() if s['sha256'] in used], indent=2) + '\n')
(OUT / 'baseline.json').write_text(json.dumps(dict(pis=len(baseline), zero_student_labs=sum(p['counts']['students'] == 0 for p in baseline),
    student_memberships=sum(p['counts']['students'] for p in baseline), selected={pi: by_pi[pi]['counts'] for pi in dict.fromkeys(r['pi'] for r in new)}), indent=2) + '\n')
print(json.dumps(dict(rows=len(new), counts=Counter(r['pi'] for r in new)), indent=2))
