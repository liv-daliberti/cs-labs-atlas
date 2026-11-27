"""Reproduce reviewed Georgia Tech relationships from immutable source captures."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

from bs4 import BeautifulSoup
import atlas_paths as P
import schema_check

SESSION = 'codex-gatech15c-schema-20261126'
RUN = P.school_part('gatech', 'work') / 'students15c-1126'
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
    if Path(s['body_path']).read_bytes().startswith(b'%PDF'):
        return ' '.join(subprocess.check_output(['pdftotext', '-layout', s['body_path'], '-']).decode().split())
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
                   auto=False, rule='R-STU-01', batch='gatech-students15c-1126',
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


# Each observation is placed by the university's award-year heading, not the retrieval date.
foley_source = source('https://research.gatech.edu/ipat/foley-endowment')
foley_dom = BeautifulSoup(Path(foley_source['body_path']).read_bytes(), 'html.parser')
context = block(foley_source, 'Funds from the Foley Endowment', 'Foley Scholars 2026')

def award(pi, name, role, year, adviser=None):
    adviser = adviser or pi
    candidates = []
    for node in foley_dom.find_all(string=lambda value: value and name in value):
        paragraph = node.find_parent('p')
        heading_node = node.find_previous(['h2', 'h3', 'h4'])
        if not paragraph or not heading_node:
            continue
        heading = heading_node.get_text(' ', strip=True)
        if re.fullmatch(r'20\d\d', heading):
            heading = heading_node.find_previous('h2').get_text(' ', strip=True)
        dated = re.search(r'20\d\d', heading)
        text = ' '.join(paragraph.get_text(' ', strip=True).split())
        if dated and int(dated[0]) == year and adviser in text[text.index(name):]:
            candidates.append(dict(year=year, heading=heading, text=text))
    if role == 'masters':
        candidates.sort(key=lambda r: 'MASTER' not in r['heading'].upper())
    assert candidates, (pi, name, year)
    record = candidates[0]
    q = record['text'][record['text'].index(name):]
    pos = q.index(adviser) + len(adviser)
    ending = re.search(r'(?<![A-Z])\.(?=\s|$)', q[pos:])
    q = q[:pos + ending.end()] if ending else q
    degree = re.compile(r'Ph\.?D\.?|Ph\.D\.|doctoral', re.I) if role == 'phd' else re.compile(r'master|M\.S\.|\bMS\b', re.I)
    if role == 'phd' and not degree.search(q):
        tail = record['text'][record['text'].index(name):]
        cue = degree.search(tail)
        assert cue, (name, 'doctoral role needs a source cue')
        ending = re.search(r'(?<![A-Z])\.(?=\s|$)', tail[cue.end():])
        q = tail[:cue.end() + ending.end()] if ending else tail
    if role in ('phd', 'masters'):
        assert degree.search(q) or (role == 'masters' and 'MASTER' in record['heading'].upper()), (name, role, q)
    from pihier.students import Name
    assert Name([pi]).match(adviser), (pi, adviser)
    assert re.search(r'advis(?:or|er|ed|ory)', q[:pos], re.I), (pi, name)
    assert adviser in q and q in visible(foley_source)
    add(pi, foley_source, [name], role, q, years=[year, year], relationship='advising', basis='dated university award entry; named adviser')
    row = new[-1]
    row['date_quote'] = record['heading']
    row['additional_sources'] = [dict(url=foley_source['url'],sha256=foley_source['sha256'],quote=context), dict(url=foley_source['url'],sha256=foley_source['sha256'],quote=record['heading'])]
    row['note'] = 'University award-year observation with an explicitly named adviser. No current enrollment, advising start year, or unobserved intervening years inferred. Generic student role retained when the entry does not state a degree.'
    assert record['heading'] in visible(foley_source)

for name, role, year in [('Vedant Das Swain','phd',2022),('Vedant Das Swain','masters',2017),('Anandghan Waghmare','masters',2017),('Yunnuo Cheng','masters',2016),('Sarthak Ghosh','masters',2016),('Yuhui Zhao','masters',2019),('Nivedita Arora','student',2021),('Mehrab Bin Morshed','student',2021),('Ali Mirzazadeh','student',2021),('Tingyu Cheng','student',2022)]:
    award('Gregory Abowd',name,role,year)
for name, role, year in [('Charles Ramey','phd',2024),('Ceara Byrne','phd',2019),('Yuhui Zhao','masters',2019),('Nivedita Arora','student',2021),('Ali Mirzazadeh','student',2021),('Georgianna Lin','student',2020),('Max Zuo','masters',2022)]:
    award('Thad Starner',name,role,year)
for name, role, year, adviser in [('Mohit Chandra','phd',2026,None),('Shravika Mittal','phd',2025,None),('Jiawei Zhou','phd',2024,'Munmun DeChoudhury'),('Sachin Pendse','phd',2023,None),('Koustuv Saha','student',2020,None),('Sindhu Kiranmai Ernala','student',2020,None),('Stevie Chancellor','phd',2016,None),('Vedant Das Swain','phd',2022,'Munmun DeChoudhury')]:
    award('Munmun De Choudhury',name,role,year,adviser)
for name,role,year,adviser in [('Niharika Mathur','phd',2025,None),('Maia Jacobs','phd',2016,'Beth Mynatt'),('Aditi Dhar','masters',2016,'Beth Mynatt')]:
    award('Elizabeth Mynatt',name,role,year,adviser)
for name,role,year,adviser in [('Charles Ramey','phd',2024,None),('Arianna Mastali','masters',2023,None),('Ceara Byrne','phd',2019,None),('Josh Terry','masters',2021,'Melody Moore Jackson')]:
    award('Melody Jackson',name,role,year,adviser)
for name,role,year in [('Ari Schlesinger','phd',2019),('Fereshteh Shahmiri','phd',2021)]:
    award('Keith Edwards',name,role,year)
for name,role,year,adviser in [('Mariam Asad','phd',2016,'Chris Le Dantec'),('Eric Corbett','phd',2019,None),('Alyssa Rumsey','phd',2021,None),('Adriana Alvarado Garcia','student',2021,None)]:
    award('Christopher Le Dantec',name,role,year,adviser)
for name,role,year,adviser in [('Amy Zhenlu Chen','phd',2026,None),('Umme Ammara','masters',2025,None),('Grace Barkhuff','masters',2021,'Mike Best')]:
    award('Michael Best',name,role,year,adviser)
for name,role,year,adviser in [('Mansi Saini','masters',2026,'Andrea Parker'),('Jordan Brown','masters',2024,'Andrea Parker'),('Vanessa Oguamanam','phd',2024,'Andrea Parker'),('Yixuan (Janice) Zhang','phd',2022,None),('Xiao Luo','masters',2022,None)]:
    award('Andrea Grimes Parker',name,role,year,adviser)
for name,role,year in [('Grace Barkhuff','phd',2026),('Grace Barkhuff','masters',2021),('Beatriz Palacios Abad','phd',2024),('Daniel Schiff','student',2020),('Emma Logevall','masters',2019)]:
    award('Ellen Zegura',name,role,year)
for name,role,year in [('Mansi Saini','masters',2026),('Duri Long','student',2020)]:
    award('Brian Magerko',name,role,year)
for name,role,year in [('Miranda Parker','phd',2017),('Kantwon Lamount Rogers','masters',2017)]:
    award('Mark Guzdial',name,role,year)
award('Anne Sullivan','Alexandra Teixeira Riggs','phd',2024)
held.append(dict(section='Foley award archive',reason='Only dated in-window entries with named advisers admitted. Repeated annual observations are not counted as new people. Clint Zeagler is existing Charles Clinton Zeagler; Michaelanne Dye is already recorded under Amy Bruckman. Misspelled duplicate names, pre-2016 entries, and unselected advisers are held. Generic graduate-student roles are not relabeled PhD.'))

p='Sara Fridovich-Keil'
s=source('https://voilalab.github.io/team/')
owner=block(s,'Sara Fridovich-Keil Sutterfield','Members Kent')
for name,role,start,end in [
 ('Namhoon Kim','phd','Namhoon Kim','Ben Burns'),
 ('Ben Burns','phd','Ben Burns','Jihoon Hong'),
 ('Jihoon Hong','phd','Jihoon Hong','Alireza Kheirandish'),
 ('Alireza Kheirandish','phd','Alireza Kheirandish','Quang Nguyen'),
 ('Quang Nguyen','phd','Quang Nguyen','Julia Nakhleh'),
 ('Sungwon Jeong','masters','Sungwon Jeong','Merve Kocabas'),
 ('Ayush Shah','undergraduate','Ayush Shah','MS alumni')]:
    add(p,s,[name],role,block(s,start,end),host=owner)
    new[-1]['additional_sources']=[dict(url=s['url'],sha256=s['sha256'],quote=owner)]
for name in ['Sarvesh Sundaram','Aditya Pandey']:
    add(p,s,[name],'masters',block(s,'MS alumni Sarvesh','About Machine Learning Center'),years=[2025,2026],alumni=True,host=owner)
held.append(dict(pi=p,names=['Kent Gauen','Julia Nakhleh','Merve Kocabas'],reason='Postdoc excluded; visiting students explicitly advised at UW-Madison and Tübingen are held outside GT degree-student scope.'))
add('Glen Chou',s,['Jihoon Hong'],'phd',block(s,'Jihoon Hong','Alireza Kheirandish'),relationship='advising',host=owner)
held.append(dict(pi='Glen Chou',reason='Own lab page lists only Future student placeholders; no people inferred. Jihoon Hong is admitted by the separately named co-adviser field on the university-affiliated VOILA roster.'))

path=P.reviewed_path('few-students-evidence.json','gatech',code=WT)
records=json.loads(path.read_text());records=[g for g in records if not any(s.get('batch')=='gatech-students15c-1126' for s in g['students'])]
prior={r['pi'] for d in ['gatech-students10-1126','gatech-students15-1126','gatech-students15b-1126'] for r in json.loads((WT/'reports'/d/'additions.json').read_text())}
selected={r['pi'] for r in new};assert len(selected)==15 and not prior.intersection(selected)
assert len({(r['pi'],r['name'],r['role'],tuple(r['years'])) for r in new})==len(new)
from pihier.links import student_role_ok
baseline=json.loads(P.data('pis.json','gatech').read_text());by_pi={p['pi']:p for p in baseline};ss=json.loads(P.data('students.json','gatech').read_text())
bp=OUT/'baseline.json'
receipt=json.loads(bp.read_text()) if bp.exists() else dict(pis=len(baseline),zero_student_labs=sum(p['counts']['students']==0 for p in baseline),student_memberships=sum(p['counts']['students'] for p in baseline),selected={p:by_pi[p]['counts'] for p in sorted(selected)},existing_students={p:[s for s in ss.get(p,[]) if student_role_ok(s)] for p in sorted(selected)})
for pi in sorted(selected):
    assert receipt['selected'][pi]['students']<=1
    old={s['name'] for s in receipt['existing_students'][pi]}
    assert not old.intersection(r['name'] for r in new if r['pi']==pi),pi
    records.append(dict(pi=pi,students=[{k:v for k,v in r.items() if k!='pi'} for r in new if r['pi']==pi],note='Fifteen further source-verified GT student relationship labs, batch gatech-students15c-1126.'))
errs=schema_check.validate(records,json.loads((WT/'schemas/few-students-evidence.schema.json').read_text()));assert not errs,errs
path.write_text(json.dumps(records,indent=1,ensure_ascii=False)+'\n')
(OUT/'additions.json').write_text(json.dumps(new,indent=2,ensure_ascii=False)+'\n')
(OUT/'roster-review.json').write_text(json.dumps(dict(session=SESSION,sections=sections,held=held),indent=2,ensure_ascii=False)+'\n')
used={r['sha256'] for r in new};used.update(x['sha256'] for r in new for x in r.get('corroborating_sources',[]))
(OUT/'sources.json').write_text(json.dumps([s for s in manifest.values() if s['sha256'] in used],indent=2)+'\n')
if not bp.exists():bp.write_text(json.dumps(receipt,indent=2)+'\n')
pairs={(r['pi'],r['name']) for r in new}
print(json.dumps(dict(relationships=len(pairs),episodes=len(new),counts={p:sum(pi==p for pi,n in pairs) for p in sorted(selected)}),indent=2))
