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
RUN = P.school_part('gatech', 'work') / 'students-under125-1127'
OUT = Path(__file__).resolve().parent
WT = OUT.parents[1]
manifest = json.loads((RUN / 'sources.json').read_text())
new = []
sections = []
held = []


def source(url):
    s = manifest[url] if url in manifest else next(x for x in manifest.values() if x['url'] == url)
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
                   auto=False, rule='R-STU-01', batch='gatech-students-under125-1127',
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


from pihier.names import Name, clean_person_name
from pihier.links import student_role_ok
import collections

# Full names already established by the canonical university census.
canonical=json.loads(P.data('pis.json','gatech').read_text())
by_pi={p['pi']:p for p in canonical}
native=json.loads(P.data('students.json','gatech').read_text())
prior_dirs=['gatech-students10-1126','gatech-students15-1126','gatech-students15b-1126','gatech-students15c-1126','gatech-students15d-1126']
prior_rows=[r for d in prior_dirs for r in json.loads((WT/'reports'/d/'additions.json').read_text())]
known={pi:{clean_person_name(s['name']) for s in ss if student_role_ok(s)} for pi,ss in native.items()}
for row in prior_rows:known.setdefault(row['pi'],set()).add(clean_person_name(row['name']))


def attach_owner(row, s, q):
    assert q in visible(s)
    row.setdefault('additional_sources',[]).append(dict(url=s.get('capture_url') or s['url'],sha256=s['sha256'],quote=q))


def fresh(pi,s,names,role,quote,**kwargs):
    names=names.split('|') if isinstance(names,str) else names
    names=[n for n in names if clean_person_name(n) not in known.get(pi,set())]
    if not names:return
    add(pi,s,names,role,quote,**kwargs)


# Doctoral dissertation table: distinguish it from the separate master's table.
s=source('https://math.gatech.edu/graduate-programs/dissertations')
soup=BeautifulSoup(Path(s['body_path']).read_bytes(),'html.parser')
table=soup.find_all('table')[0]
assert 'Doctoral Dissertations' in visible(s)
doctoral_context=block(s,'Here is the complete list','Doctoral Dissertations')+' Doctoral Dissertations'
assert doctoral_context in visible(s)
math_pis=['Anton Leykin','Yingjie Liu','Rafael de la Llave','Luca Dieci','Haomin Zhou','Sung Ha Kang','Grigoriy Blekherman','Prasad Tetali']
advisor_review=[]
for tr in table.find_all('tr'):
    cells=[' '.join(x.get_text(' ',strip=True).split()) for x in tr.find_all('td')]
    if len(cells)!=4:continue
    date,title,name,advisers=cells
    yr=re.search(r'20\d\d',date)
    if not yr or not 2016<=int(yr[0])<=2026:continue
    if name=='Yiao, Yian':
        held.append(dict(section='Math dissertations',name=name,reason='Possible surname typo; no alias inferred.'))
        continue
    labels=re.split(r'\s+and\s+',advisers)
    for pi in math_pis:
        matches=[a for a in labels if Name(by_pi[pi]['names']).match(a)]
        if not matches:continue
        if clean_person_name(name) in known.get(pi,set()):continue
        q=' '.join(tr.get_text(' ',strip=True).split())
        assert q in visible(s)
        fresh(pi,s,name,'phd',q,years=[int(yr[0])]*2,alumni=True,relationship='advising',basis='explicit doctoral dissertation year and named adviser column')
        row=new[-1]
        attach_owner(row,s,doctoral_context)
        row['note']='Official GT doctoral-dissertation table; original surname-first author string retained exactly. The existing native name cleaner produces the display name. Adviser initials resolve to the canonical Math census name; no unobserved enrollment years inferred.'
        advisor_review.append(dict(pi=pi,source_adviser=advisers,source_name=name,native_name=clean_person_name(name),year=int(yr[0])))
held.append(dict(section='Math dissertations',reason='Only the doctoral table, 2016–2026, and explicit matching adviser initials admitted. Existing Anna Kirkpatrick, Kevin Shu and Yuchen He are not recounted. Blekherman, D. does not match Grigoriy Blekherman; surname-only Dieci/Zhou is not expanded; possible Yiao/Yao typo held.'))

# Graduate and dated alumni cohorts in the sole-PI engineering labs.
s=source('https://epic.gatech.edu/people/')
owner=block(s,'Principal Investigator Dr. Aaron Young','Research Faculty Kinsey')
q=block(s,'Doctoral Students','Masters Students')
phds=['Ethan Schonhaut','Hanjun Kim','Ryan Casey','Siddharth Nathella','Yash Mhaskar','Kyle Kaveny','Matthew Lerner','Hangyeol Song','Ethan Park','Theresa Hardin','John Shim','Sofia Arvelo Rojas','Varshith Sreeramdass','Xinyuan (Caesar) Guo','Vibha Iyer','Krystal Lan','Sean Leapley','Kathleen Ho','Cassidy Schuman','Chase Sun']
fresh('Aaron J Young',s,phds,'phd',q,host=owner)
for row in new[-len(phds):]:attach_owner(row,s,owner)
q=block(s,'Masters Students','Research Teams')
fresh('Aaron J Young',s,'Emily Rice|Summer Sun|Aditya Rao','masters',q,host=owner)
for row in new[-3:]:attach_owner(row,s,owner)
dom=BeautifulSoup(Path(s['body_path']).read_bytes(),'html.parser')
for tb in dom.find_all('table'):
    if not ('Lab Member' in tb.get_text() and 'Degree' in tb.get_text()):continue
    for tr in tb.find_all('tr'):
        cells=[' '.join(c.get_text(' ',strip=True).split()) for c in tr.find_all('td')]
        if len(cells)<3:continue
        name,degree,date=cells[:3]
        yr=re.search(r'20\d\d',date)
        if not name or not yr or not 2016<=int(yr[0])<=2026:continue
        role='phd' if re.search(r'Ph\.?D',degree,re.I) else 'masters' if re.search(r'M\.?S\.?',degree) else None
        if not role:continue
        # Different source-stated degree episodes of the same person are retained.
        if name in known.get('Aaron J Young',set()):continue
        q=' '.join(tr.get_text(' ',strip=True).split())
        add('Aaron J Young',s,[name],role,q,years=[int(yr[0])]*2,alumni=True,host=owner)
        attach_owner(new[-1],s,owner)
held.append(dict(pi='Aaron J Young',reason='Research faculty/postdocs, ambiguous mixed-degree research-team photo captions, and the nameless 2019 alumni row held. Current PhD Chase Sun and the dated 2026 MS completion are two role observations of one person. Co-advising labels do not assign the rest of the shared roster to collaborators.'))

s=source('https://www.epic.gatech.edu/sidd-nathella/')
q=block(s,'Siddharth Nathella Mechanical Engineering PhD Student','He is currently working')
fresh('Lena H. Ting',s,'Siddharth Nathella','phd',q,relationship='advising')

s=source('https://sites.google.com/site/idreemlaboratory/people')
owner='People Principle Investigator Dr. Julie Linsey'
for role,names,start,end in [('phd','Alexander R. Murphy|Morgan Weaver','PhD Students Alexander','Masters Students Timothy'),('masters','Timothy Sawchuk','Masters Students Timothy','Undergraduate Students Danielle'),('undergraduate','Danielle Saracino','Undergraduate Students Danielle','Google Sites Report abuse')]:
    names=names.split('|');fresh('Julie Linsey',s,names,role,block(s,start,end),host=owner)
    for row in new[-len(names):]:attach_owner(row,s,owner)
held.append(dict(pi='Julie Linsey',reason='Undated alumni and duplicated navigation labels held; only typed current degree sections admitted.'))

s=source('https://willperkins.org/perkinsCV.pdf')
q=block(s,'Students supervised','Wei En Tan, University of Birmingham')
owner=visible(s)[:450]
fresh('Will Perkins',s,'Ijay Narang|Denys Slobodianiuk|Aiya Kuchukova|Sam van der Poel|Jade Lintott|Yuzhou Wang','phd',q,relationship='advising',host=owner)
for row in new[-6:]:attach_owner(row,s,owner)
held.append(dict(pi='Will Perkins',reason='Birmingham degrees and UIC/Birmingham postdocs held outside GT degree-student scope.'))

s=source('https://sahinidis.coe.gatech.edu/group')
owner=block(s,'Sahinidis Optimization Group','Main navigation')
q=block(s,'Current Group Members PhD Students','Research collaborators')
fresh('Nikolaos Sahinidis',s,'Selin Bayramoglu|Sourabh Choudhary|Anatoliy Kuznetsov|Yijiang Li|Kaiwen Ma|Donghyun Oh|Owais Sarwar','phd',q,host=owner,proof=(source('cached-1244'),'Sahinidis Optimization Group @ Georgia Tech'))
for row in new[-7:]:attach_owner(row,s,owner)
held.append(dict(pi='Nikolaos Sahinidis',reason='Foreign collaborators and historical Illinois/CMU graduates are not transferred to GT. Explicit current GT group cohort only; George Nemhauser is not assigned the whole roster.'))

s=source('cached-2102')
t=visible(s);owner=t[:t.index('Positions Held')] if 'Positions Held' in t else t[:300]
q=block(s,'Current Ph.D. Students (including co-advisees)','Graduated Ph.D. Students')
fresh('Angelos D Keromytis',s,'Evangelos Froudakis|George Kokolakis|Matthew Pruett|Kevin Sam Tharayil','phd',q,relationship='advising',host=owner)
for row in new[-4:]:attach_owner(row,s,owner)
for name,start,end,years in [('Athanasios Moschos','Athanasios Moschos (Georgia Tech;','Athanasios Avgetidis (Georgia Institute',[2020,2026]),('Athanasios Avgetidis','Athanasios Avgetidis (Georgia Institute','Athanasios Kountouras (Georgia Institute',[2020,2025]),('Athanasios Kountouras','Athanasios Kountouras (Georgia Institute','Marios Pomonis (Columbia',[2018,2023])]:
    q=block(s,start,end)
    fresh('Angelos D Keromytis',s,name,'phd',q,years=years,alumni=True,relationship='advising',host=owner)
    attach_owner(new[-1],s,owner)
    attach_owner(new[-1],s,'Graduated Ph.D. Students')
    if name!='Athanasios Moschos':
        fresh('Manos Antonakakis',s,name,'phd',q,years=years,alumni=True,relationship='advising')
        attach_owner(new[-1],s,'Graduated Ph.D. Students')
held.append(dict(pi='Angelos D Keromytis',reason='Only institution-labelled GT doctoral records admitted. Columbia students, postdocs and research scientists held. Explicit October 2026 graduation of Moschos in the dated faculty CV is used instead of extrapolating an undated candidate bio. George/Georgios Kokolakis alias is not invented.'))

s=source('https://mooney.gatech.edu/security/people/')
owner=block(s,'People People Professor Vincent J. Mooney','Graduate Students')
proof=source('https://mooney.gatech.edu/')
fresh('Vincent J Mooney',s,['Allahverdi, Arman','Ahmad, Kareem'],'student',block(s,'Graduate Students','Alumni Ph.D.'),host=owner,proof=(proof,'Vincent John Mooney III Associate Professor School of Electrical and Computer Engineering Adjunct Associate Professor School of Computer Science Georgia Institute of Technology'))
for row in new[-2:]:attach_owner(row,s,owner)
for name,year in [('Boyapati, Vishnu',2023),('Vunnam, Yathiendra',2023),('Ksiksi, Assil',2018)]:
    q=block(s,'M.S. Name Year Graduated','Parham, Nicholas')
    fresh('Vincent J Mooney',s,name,'masters',q,years=[year,year],alumni=True,host=owner)
    attach_owner(new[-1],s,owner)
held.append(dict(pi='Vincent J Mooney',reason='Current Graduate Students remain generic student rather than guessed PhD. Undated doctoral alumni, pre-window degrees and IIIT-Hyderabad degrees held.'))

s=source('https://aimrl.gatech.edu/leegroup.html')
owner='Faculty Professor Kok-Meng Lee'
q=block(s,'Alumni [ Ph.D. ]','Jungyoul Lim, 2014')
fresh('Kok-Meng Lee',s,'Min Li|Chun-Yeon Lin','phd',q,years=[2017,2017],alumni=True,host=owner)
for row in new[-2:]:attach_owner(row,s,owner)
held.append(dict(pi='Kok-Meng Lee',reason='Only dated 2017 doctoral alumni admitted. Undated members, pre-2016 degrees and explicitly foreign-university co-advised doctorates held.'))

s=source('https://naveenak.org/d3lab/')
owner=block(s,'The D3 Lab is a research group led by','We study and shape')
for name,role,start,end in [('Ananya Kasi','phd','Ananya Kasi','Roshini Deva'),('Roshini Deva','phd','Roshini Deva','Reeda Shimaz Huda'),('Reeda Shimaz Huda','phd','Reeda Shimaz Huda','Anoosha Thumma'),('Anoosha Thumma','masters','Anoosha Thumma','Work with us')]:
    fresh('Naveena Karusala',s,name,role,block(s,start,end),host=owner)
    attach_owner(new[-1],s,owner)

# Add a second independently supported relationship to one-student labs.
s=source('https://deep-inder.github.io/')
q=block(s,'Deep Inder Mohan Deep Inder Mohan About','Email GitHub')
for pi in ['Alexandra Boldyreva','Joseph Jaeger']:fresh(pi,s,'Deep Inder Mohan','phd',q,relationship='advising')
s=source('https://kaishuocheng.github.io/')
q=block(s,'I am a 5th year PhD student','Google Scholar')
fresh('Alexandra Boldyreva',s,'Kaishuo Cheng','phd',q,relationship='advising')

s=source('https://boladjivinny.github.io/')
q=block(s,'Vinny Adjibi | Georgia Institute','I also work closely')
fresh('Fabian Monrose',s,'Vinny Adjibi','phd',q,relationship='advising')
held.append(dict(pi='Fabian Monrose',reason='Vinny names Fabian as adviser. Working closely with Michael Bailey is not relabelled advising or membership in Bailey\'s lab.'))

s=source('cached-989')
q=block(s,'Ph.D. Students','Postdoc Kihyuk')
owner='Jing Li - Professor People'
fresh('Jing Li',s,'Dohyun Ku|Rui Qi Chen|Yeonju Lee|Reinaldo Mock|Jung Hun Phee','phd',q,host=owner)
for row in new[-5:]:attach_owner(row,s,owner)
held.append(dict(pi='Jing Li',reason='ISyE Jing Li group, not an ECE homonym. Undated alumni, postdocs and existing Hairong Wang not recounted.'))

s=source('https://barry.ece.gatech.edu/group/hall/')
t=visible(s)
for name in ['Elnaz Banan Sadeghian']:
    a=t.find(name)
    assert a>=0,name
    rest=t[a:];date=re.search(r'Ph\.D\.,?\s*(?:[A-Za-z]+\s+)?(20\d\d)',rest)
    assert date,(name,rest[:250])
    if not 2016<=int(date[1])<=2026:continue
    q=rest[:date.end()]
    fresh('John R Barry',s,name,'phd',q,years=[int(date[1])]*2,alumni=True,host='Past Members of the Communication Theory Research Group')
    attach_owner(new[-1],source('https://barry.ece.gatech.edu/'),'John R. Barry Professor School of ECE Georgia Institute of Technology')
award('Eric Gilbert','Eshwar Chandrasekharan','phd',2019)

s=source('https://zackory.com/')
q=block(s,'Zackory Erickson Zackory Erickson','News Raj Reddy')
pdf=source('https://zackory.com/assets/Zackory_Erickson_CV.pdf')
# Degree date comes from the same person's CV, not the retrieval year.
pt=visible(pdf); a=pt.index('Education Ph.D., Robotics');pq=pt[a:a+600]
assert '2016–2021' in pq and 'Advisor: Charles C. Kemp' in pq
fresh('Charles C. Kemp',s,'Zackory Erickson','phd',q,years=[2021,2021],alumni=True,relationship='advising',proof=(pdf,pq))
held.append(dict(pi='Charles C. Kemp',reason='Zackory explicitly names Charlie Kemp for his GT PhD; 2021 completion dated by own CV. Current CMU affiliation is not turned into current GT enrollment.'))

# Independent, explicit faculty-owned roster corroborates the Sasha/Alexandra
# name form; the canonical census identity itself is not changed.
bs=source('cached-377')
bq=visible(bs)
for row in new:
    if row['pi']=='Alexandra Boldyreva':
        attach_owner(row,bs,bq)

# Prepare a reviewable package only when BOTH user constraints are satisfied.
selected={r['pi'] for r in new}
pairs={(r['pi'],clean_person_name(r['name'])) for r in new}
assert len({(r['pi'],clean_person_name(r['name']),r['role'],tuple(r['years'])) for r in new})==len(new)
for pi,name in pairs:assert name not in known.get(pi,set()),(pi,name)
projected={pi:{clean_person_name(s['name']) for s in ss if student_role_ok(s)} for pi,ss in native.items()}
for row in prior_rows+new:projected.setdefault(row['pi'],set()).add(clean_person_name(row['name']))
zeros=sum(not projected.get(pi,set()) for pi in by_pi)
ones=sum(len(projected.get(pi,set()))==1 for pi in by_pi)
assert zeros<125 and ones<=60,(zeros,ones)
new_empty={pi for pi in selected if by_pi[pi]['counts']['students']==0 and pi not in {r['pi']for r in prior_rows}}
assert len(new_empty)==13 and all(len(projected[pi])>=2 for pi in new_empty)
assert all(by_pi[pi]['counts']['students']<=1 for pi in selected)
path=P.reviewed_path('few-students-evidence.json','gatech',code=WT)
records=json.loads(path.read_text())
records=[g for g in records if not any(s.get('batch')=='gatech-students-under125-1127' for s in g['students'])]
for pi in sorted(selected):
    records.append(dict(pi=pi,students=[{k:v for k,v in r.items()if k!='pi'}for r in new if r['pi']==pi],note='Source-verified under-125-zero-lab batch; combined native package must keep one-student labs at or below 60.'))
errs=schema_check.validate(records,json.loads((WT/'schemas/few-students-evidence.schema.json').read_text()));assert not errs,errs
path.write_text(json.dumps(records,indent=1,ensure_ascii=False)+'\n')
(OUT/'additions.json').write_text(json.dumps(new,indent=2,ensure_ascii=False)+'\n')
receipt=dict(pis=len(canonical),zero_student_labs=sum(p['counts']['students']==0 for p in canonical),one_student_labs=sum(p['counts']['students']==1 for p in canonical),student_memberships=sum(p['counts']['students']for p in canonical),selected={pi:by_pi[pi]['counts']for pi in sorted(selected)},existing_students={pi:[s for s in native.get(pi,[])if student_role_ok(s)]for pi in selected})
bp=OUT/'baseline.json'
if not bp.exists():bp.write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n')
used={r['sha256']for r in new}
used.update(s['sha256']for r in new for key in ['additional_sources','corroborating_sources']for s in r.get(key,[]))
(OUT/'sources.json').write_text(json.dumps([s for s in manifest.values()if s['sha256']in used],indent=2)+'\n')
(OUT/'roster-review.json').write_text(json.dumps(dict(session=SESSION,sections=sections,held=held,math_adviser_resolution=advisor_review),indent=2,ensure_ascii=False)+'\n')
summary=dict(new_relationships=len(pairs),new_episodes=len(new),labs_enriched=len(selected),new_zero_labs_covered=len(new_empty),projected_zero_labs=zeros,projected_one_labs=ones,projected_memberships=sum(len(projected.get(pi,set()))for pi in by_pi),counts=dict(sorted(collections.Counter(pi for pi,name in pairs).items())))
(OUT/'projection.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(summary,indent=2,ensure_ascii=False))
