"""Reproduce reviewed Georgia Tech relationships from immutable source captures."""
import hashlib
import json
import subprocess
from pathlib import Path

from bs4 import BeautifulSoup
import atlas_paths as P
import schema_check

SESSION = 'codex-gatech10-20261126'
RUN = P.school_part('gatech', 'work') / 'students15b-1126'
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
                   auto=False, rule='R-STU-01', batch='gatech-students15b-1126',
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


p = 'Joy Arulraj'
s = source('cached-775')
add(p, s, 'Gaurav|Tarkok Kakkar|Shahmeer Ahmad|Weili Shi|Sayan Sinha', 'student', block(s, 'Students Gaurav', 'Graduated Students'), host='Joy Arulraj Associate Professor Georgia Institute of Technology')
held.append(dict(pi=p, reason='Current Students heading is untyped; no inferred PhD roles. Undated graduates held; Qi Zhou already present.'))

p = 'Teodora Baluta'
s = source('cached-1390')
add(p, s, 'Jehad Hussein|Caroline Huang|Kevin Dai|Sankha Das', 'phd', block(s, 'PhD Students Jehad', 'Undergraduate / Master’s Students'))
add(p, s, ['Yash Chauhan'], 'student', block(s, 'Undergraduate / Master’s Students', 'Alumni'))
held.append(dict(pi=p, reason='Zedian Shao already present; mixed undergraduate/Masters heading remains generic; undated alumni and collaborators excluded.'))

p = 'Kexin Rong'
s = source('https://kexinrong.github.io/lab/people/')
add(p, s, 'Jixian Su|Weili Shi|Shahmeer Ahmad|Yujun He', 'phd', block(s, 'PhD students Jixian', 'Master and Undergraduate students'), host='The D2I lab is directed by Dr. Kexin Rong')
add(p, s, 'Penghao Luo|Yash Vinod Totla|Laksh Makhija|Subhajit Bag|Mei Li|Jiayue Sun|Rachel Lee', 'student', block(s, 'Master and Undergraduate students', 'Lab Alumni'))
for name, year in [('Hantian Zhang',2024),('Renzhi Wu',2024),('Peng Li',2023)]:
    t=visible(s);a=t.index(name);b=t.index('Thesis:',a)
    add(p,s,[name],'phd',t[a:b].strip(),years=[year,year],alumni=True)
held.append(dict(pi=p, reason='Undated MS/undergraduate alumni held; mixed current heading retains generic student role.'))

p = 'Wei Xu'
s = source('https://cocoxu.github.io/')
for names, role, start, end in [
 ('Tarek Naous|Jonathan Zheng|Geyang Guo|Duong Minh Le|Ivy He|Junmo Kang','phd','X Lab Tarek','Usneek Singh'),
 ('Usneek Singh|Yiren Wang|Frank Yang|Baixi Jiao|Elene Sturua|Jiayu Liu','masters','Usneek Singh (CS M.S.)','Jiangyue Zhu'),
 ('Jiangyue Zhu','student','Jiangyue Zhu','Victor Gong'),
 ('Victor Gong|Benjamin Mamut|Alexey Plagov|Isha Madanu|James Balak|Sean Connelly|Sergey Sachko|Dieu Anh Truong','undergraduate','Victor Gong','Jiayi Chen')]:
    add(p,s,names,role,block(s,start,end),host='Georgia Institute of Technology')
held.append(dict(pi=p, reason='Columbia visiting student excluded. Alumni spanning former OSU history require individual GT affiliation proof; no inference from degree year. Yao Dou already present.'))

p = 'Steve Mussmann'
s = source('https://steve.mussmann.us/addapt')
add(p,s,'Hangyu Zhou|Anisha Pal','phd',block(s,'Current PhD Students','Current BS & MS Students'))
for names,role in [('Archit Shinde|Diya Kaimal|Naman Talreja|Nash Moore|Neel Bhattacharyya|Suman Krishna|Tony Qin|Yuxuan (Leon) Liang','undergraduate'),('Kabir Kang|Tanmay Chavan|Yukai Ma','masters'),('Yu-An Chen','student')]:
    add(p,s,names,role,block(s,'Current BS & MS Students','Alumni'))
held.append(dict(pi=p, reason='Kangping Hu already present. Undated alumni held; BS/MS dual label remains generic student.'))

p = 'Anqi Wu'
s = source('https://sites.google.com/view/brainml/people')
add(p,s,'Yule Wang|Weihan Li|Feiyang Wu|Jingyang Ke|Eric Su|Jiyi Wang','phd',block(s,'Current Student','Alumni'),host='Principle Investigator Anqi Wu')
held.append(dict(pi=p, reason='Alumni have start dates but no dated membership end/degree dates; not extended to capture year. Chengrui Li already present.'))

p = 'Xiuwei Zhang'
s = source('https://xiuweizhang.wordpress.com/group/')
add(p,s,'Macrina M Lobo|Ziqi Zhang|Yuqi Cheng|Chandra Sekhar Reddy E|Hechen Li|Michael Squires','phd',block(s,'Group members Xiuwei','Yong Li Neo'),host='Xiuwei Zhang Principal Investigator')
add(p,s,'Yong Li Neo|Yuxing Sun','undergraduate',block(s,'Yong Li Neo','Xinhai Pan PhD student graduated'))
add(p,s,['Xinhai Pan'],'phd','Xinhai Pan PhD student graduated in May 2026. Now at Google',years=[2026,2026],alumni=True)
q=block(s,'Alumni Mehak','Like Loading')
items=[('Mehak Bindra','masters',[2024,2025]),('Dongjae Lee','masters',[2025,2025]),('Baran Abbasi','undergraduate',[2025,2025]),('Huaijin (Tony) Tu','undergraduate',[2024,2024]),('Alejandro Danies-Lopez','masters',[2024,2024]),('Mihir Bafna','undergraduate',[2022,2024]),('Anwesha Gorantla','undergraduate',[2022,2022]),('Anwesha Gorantla','undergraduate',[2024,2024]),('Han Bao','undergraduate',[2022,2022]),('Xinye Zhao','masters',[2022,2022]),('Chukang Zhong','masters',[2022,2022]),('Pranav Putta','undergraduate',[2022,2022]),('Sooyoun Oh','phd',[2020,2021]),('Jongseok Han','masters',[2021,2021]),('Paarth Parekh','masters',[2021,2021]),('Chengkai Yang','undergraduate',[2020,2020]),('Rohan Goel','masters',[2020,2020]),('Pranit Kaul','masters',[2020,2020]),('Amir Girgis','undergraduate',[2020,2020])]
for name,role,years in items:add(p,s,[name],role,q,years=years,alumni=True)
held.append(dict(pi=p, reason='High school student excluded. Separate 2022 and 2024 observations for Anwesha Gorantla do not assert continuous membership.'))

p = 'Josiah Hester'
s = source('https://kamoamoa.com/team/')
add(p,s,'John Mamish|Alex Curtiss|Rishabh Goel|Eric Greenlee|Diana Wang|Yingting Gao|Tejonidhi Deshpande|Moeiini ‘Moi’ Reilly|Connor Pan|Rachel Baker-Ramos|Haisley Kim|Jacob Cook|Nikola Maruszewski|Xinye Wang|Yibo Fu|Summit Shrestha|Tristan Daniel','phd',block(s,'PhD Students # John','Master Students # Candace'),host='Josiah Hester is Associate Professor of Interactive Computing and Computer Science at Georgia Tech.')
add(p,s,['Candace Boice'],'masters',block(s,'Master Students # Candace','Honors and Undergraduate Students # Ben'))
add(p,s,'Ben Carter|James Kemerait|Simon Guterman|Diego Shipmon|Omer Inan|Pichaya “Palm” Limprayoon','undergraduate',block(s,'Honors and Undergraduate Students # Ben','Alumni # PhD and Postdoctoral #'))
held.append(dict(pi=p, reason='Christopher Kraemer already present. Staff, postdocs, affiliated researchers, undated alumni and mixed PhD/postdoc alumni excluded.'))

p = 'Wenjing Liao'
s = source('cached-1763')
add(p,s,['Haoran Yan'],'student','Students Haoran Yan, 2025 - now',years=[2025,2026])
for name,year,start,end in [('Alex Havrilla',2021,'Alex Havrilla','Jiahui Cheng'),('Jiahui Cheng',2020,'Jiahui Cheng','Minshuo Chen'),('Minshuo Chen',2018,'Minshuo Chen','Postdoc Alumni')]:
    add(p,s,[name],'phd',block(s,start,end),years=[year,2023 if name=='Minshuo Chen' else 2025],alumni=True)
held.append(dict(pi=p, reason='Haoran current Students heading is untyped in this roster. Biraj Dahal already present; all postdocs excluded.'))

p = 'Juba Ziani'
s = source('https://www.ai4opt.org/about/member-spotlights')
add(p,s,'Diptangshu Sen|Srikanth Avasalara|Samuel Hood','phd','My main role in the Institute is to contribute high-quality research to the “Responsible AI for Decision Making” research thrust, supported by my exceptional Ph.D. students Krishna Acharya, Diptangshu Sen, Srikanth Avasalara, and Samuel Hood.',years=[2025,2025],relationship='advising',host='Juba Ziani Georgia Institute of Technology SPOTLIGHT 2025-05-01')
s=source('cached-1040')
add(p,s,['Amit Saha'],'undergraduate',block(s,'October 2026: Check out our new work led','September 2026:'),years=[2026,2026])
add(p,s,['George Bentley'],'student',block(s,'May 2026: Congratulations to student George','May 2026: Edwige'),years=[2026,2026])
held.append(dict(pi=p, reason='Krishna Acharya already present. Coauthors and external students are not inferred as advisees.'))

p = 'Arthur Delarue'
s = source('https://www.darden.virginia.edu/sites/default/files/inline-files/CV-delarue-20261001.pdf')
for name,years,start,end in [('Kleanthis Karakolios',[2025,2025],'Kleanthis Karakolios, PhD, Machine Learning, Georgia Tech','Puneet S. Bagga, BS'),('Olivia Phillips',[2023,2025],'Olivia Phillips, PhD student in Operations Research, Georgia Tech','Weiqing (Lynn) Xu, PhD student'),('Weiqing (Lynn) Xu',[2023,2025],'Weiqing (Lynn) Xu, PhD student in Operations Research, Georgia Tech','SERVICE INFORMS')]:
    add(p,s,[name],'phd',block(s,start,end),years=years,alumni=True,relationship='advising')
held.append(dict(pi=p, reason='All dates explicitly Georgia Tech in CV, preceding UVA. Puneet S. Bagga already present; MIT student Shriya Karam excluded.'))

p = 'John Stasko'
s = source('cached-204')
items=[('Yu Fu',2025),('Hayeong Song',2024),('Po Ming "Terrance" Law',2021),('John Thompson',2020),('Arjun Srinivasan',2020),('Alex Godwin',2018),('Mengdie Hu',2018),('Ramik Sadana',2017),('Yi Han',2016),('Chad Stolper',2016)]
for name,year in items:
    t=visible(s);a=t.index(name+' ,');b=t.index(', '+str(year),a)+len(', '+str(year))
    add(p,s,[name],'phd','Students Completed PhD '+t[a:b] if t[a:b].startswith('Alex Bendeck') else block(s,'Students Completed PhD','Youn ah Kang'),years=[year,year],alumni=True,relationship='advising')
held.append(dict(pi=p, reason='Pre-2016 graduates excluded. Alex Bendeck is existing Alexander Bendeck; no alias duplicate added.'))

p = 'Ashok Goel'
s = source('https://hcc.cc.gatech.edu/specialization/cogsci')
for name,start,end in [('Sungeun An','Sungeun An Started 2017','Lawrence “Larry” Freil'),('Marissa Gonzales','Marissa Gonzales Started 2016','Lara Martin Started 2015'),('Qiaosi “Chelsea” Wang','Qiaosi “Chelsea” Wang Started 2018',None)]:
    add(p,s,[name],'phd',block(s,start,end),relationship='advising',host='Current Ph.D. students specializing in Cognitive Science')
held.append(dict(pi=p, reason='University HCC directory explicitly states each adviser, avoiding shared DILab inference. Program start dates are not assumed to be advising start dates. Captured directory status only; Karan Taneja already present.'))

p = 'Robert C. Wilson'
s = source('https://psychology.gatech.edu/news/elliot-huang-selected-georgia-techs-representative-usg-academic-recognition-day')
add(p,s,['Elliot Huang'],'undergraduate',block(s,'For Elliot Huang','Georgia Tech Resources'),years=[2026,2026],relationship='advising')
held.append(dict(pi=p, reason='Official dated article identifies undergraduate and mentor/PI explicitly. Other lab names without student/advising evidence excluded.'))

p = 'Alexander Lerch'
s = source('https://musicinformatics.gatech.edu/')
proof=source('https://kwatcharasupat.github.io/')
add(p,s,['Karn Watcharasupat'],'phd',block(s,'Fall 2026 Griffin','Spring 2026 Caleb'),years=[2026,2026],proof=(proof,'I am a PhD student in Music Technology at the Music Informatics Group , Georgia Institute of Technology under Prof Alexander Lerch .'))
held.append(dict(pi=p, reason='Dated group photo supplies membership; personal bio supplies explicit doctoral role and PI. Other photo names are held without independently stated student roles.'))

path = P.reviewed_path('few-students-evidence.json','gatech',code=WT)
records=json.loads(path.read_text())
records=[g for g in records if not any(s.get('batch')=='gatech-students15b-1126' for s in g['students'])]
prior={r['pi'] for d in ['gatech-students10-1126','gatech-students15-1126'] for r in json.loads((WT/'reports'/d/'additions.json').read_text())}
selected={r['pi'] for r in new}
assert len(selected)==15 and not selected.intersection(prior)
assert len({(r['pi'],r['name'],r['role'],tuple(r['years'])) for r in new})==len(new)
baseline=json.loads(P.data('pis.json','gatech').read_text());by_pi={p['pi']:p for p in baseline}
from pihier.links import student_role_ok
ss=json.loads(P.data('students.json','gatech').read_text())
baseline_path=OUT/'baseline.json'
receipt=json.loads(baseline_path.read_text()) if baseline_path.exists() else dict(pis=len(baseline),zero_student_labs=sum(p['counts']['students']==0 for p in baseline),student_memberships=sum(p['counts']['students'] for p in baseline),selected={p:by_pi[p]['counts'] for p in sorted(selected)},existing_students={p:[s for s in ss.get(p,[]) if student_role_ok(s)] for p in sorted(selected)})
for pi in sorted(selected):
    assert receipt['selected'][pi]['students']<=1
    existing={s['name'] for s in receipt['existing_students'][pi]}
    assert not existing.intersection(r['name'] for r in new if r['pi']==pi)
    records.append(dict(pi=pi,students=[{k:v for k,v in r.items() if k!='pi'} for r in new if r['pi']==pi],note='Source-reviewed third batch, fifteen further labs, gatech-students15b-1126.'))
errors=schema_check.validate(records,json.loads((WT/'schemas/few-students-evidence.schema.json').read_text()));assert not errors,errors
path.write_text(json.dumps(records,indent=1,ensure_ascii=False)+'\n')
(OUT/'additions.json').write_text(json.dumps(new,indent=2,ensure_ascii=False)+'\n')
(OUT/'roster-review.json').write_text(json.dumps(dict(session=SESSION,sections=sections,held=held),indent=2,ensure_ascii=False)+'\n')
used={r['sha256'] for r in new};used.update(x['sha256'] for r in new for x in r.get('corroborating_sources',[]))
(OUT/'sources.json').write_text(json.dumps([s for s in manifest.values() if s['sha256'] in used],indent=2)+'\n')
if not baseline_path.exists():baseline_path.write_text(json.dumps(receipt,indent=2)+'\n')
pairs={(r['pi'],r['name']) for r in new}
print(json.dumps(dict(episodes=len(new),relationships=len(pairs),counts={pi:sum(p==pi for p,n in pairs) for pi in sorted(selected)}),indent=2))
