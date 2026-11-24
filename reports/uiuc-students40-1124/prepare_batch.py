import hashlib,json,re,subprocess
from pathlib import Path
from bs4 import BeautifulSoup
import atlas_paths as P
RUN=P.SCRATCH/'uiuc-students40-1124';WT=P.ROOT/'worktrees/uiuc-students40-1124';OUT=WT/'reports/uiuc-students40-1124';OUT.mkdir(exist_ok=True,parents=True)
manifest=json.loads((RUN/'sources.json').read_text());dates=[]
for fn in ['extra-source-results.json','navigation-source-results.json','cv-source-results.json']:
 if (RUN/fn).exists():dates.extend(x for x in json.loads((RUN/fn).read_text()) if x.get('body_path'))
records=json.loads(subprocess.check_output(['git','-C',str(WT),'show','bf572a6d3e1fa09b38ed2720356d13ec7b02c819:hierarchy/uiuc/reviewed/few-students-evidence.json'],text=True));new=[];holds={};excluded={}
def src(pi,needle):return next(x for x in manifest[pi]+dates if needle.rstrip('/')in x['url']and x.get('body_path'))
def text(s):
 b=Path(s['body_path']).read_bytes();assert hashlib.sha256(b).hexdigest()==s['sha256']
 if b.startswith(b'%PDF'):return Path(s['text_path']).read_text()
 if s['url'].endswith(('.js','.json')):return ' '.join(b.decode().split())
 soup=BeautifulSoup(b,'html.parser')
 for e in soup(['script','style','noscript']):e.decompose()
 return ' '.join(soup.get_text(' ',strip=True).split())
def section(s,start,end=None):
 t=text(s);a=t.index(start);return t[a:t.index(end,a+len(start))if end else len(t)]
def emit(pi,s,role,name,q,year=None,alumni=False,canonical=None,heading='',note='',**kwargs):
 assert q in text(s),(pi,name,'quote');assert name in q,(pi,name,'name');assert '@'not in q,(pi,name,'contact')
 if heading:assert heading in text(s),(pi,heading)
 row=dict(name=canonical or name,role=role,years=[year,year]if year else ([2026,2026]if not alumni else None),years_basis='Explicit dated source observation; no unproved interval or degree completion inferred.'if year else ('Capture observation only; no earlier membership years inferred.'if not alumni else 'Undated alumni of UIUC-only lab established after2016; exact membership year unresolved.'),alumni=alumni,url=s['url'],observed=s['observed'],sha256=s['sha256'],quote=q,rule='R-STU-01',reviewed_by='codex-uiuc-students30-1124',reviewed=True,auto=False,note=note or 'PI-owned student/advising roster manually reviewed, with school and role scope.')
 if heading:row['host_quote']=heading
 if canonical and canonical!=name:row['aliases']=[name]
 row.update(kwargs);new.append(dict(pi=pi,**row))
def many(pi,s,role,names,start,end,year=None,alumni=False,**kwargs):
 q=section(s,start,end)
 for name in names.split('|'):
  i=q.index(name);tail=q[i:i+170];stop=tail.find('@')
  if stop>=0:tail=tail[:max(0,tail.rfind(' ',0,stop))]
  emit(pi,s,role,name,tail,year,alumni,heading=start,**kwargs)
def hold(pi,s,name,q,reason):
 assert name in q and q in text(s),(pi,name)
 holds.setdefault(pi,[]).append(dict(name=name,url=s['url'],sha256=s['sha256'],quote=q,status='unresolved',captured=s['observed'],reason=reason))
# Eric: generic graduate roles remain generic; named PhD defense supplies the exception.
p='Eric Chitambar';s=src(p,'current-members');home=src(p,'quantum-entangled.ece.illinois.edu');many(p,s,'graduate','Max Gold|Sarah Hagen|Samihr Hermes|Anna Honeycutt|Chloe Kim|Selina Nie|Shuen Wu|Mingze Xu','Graduate Students','Group Alumni')
q=section(home,'Congrats to (Dr.) Xinan Chen','Congrats to Sarah');q=q[:q.index('Xinan was')];emit(p,home,'phd','Xinan Chen',q,2026,True)
q=section(home,'Xinan was one of','It’s been');emit(p,home,'undergraduate','Xinan Chen',section(home,'Congrats to (Dr.) Xinan Chen','Congrats to Sarah')[:section(home,'Congrats to (Dr.) Xinan Chen','Congrats to Sarah').index('It’s been')],alumni=True,note='Explicit UIUC undergraduate episode after PIjoinedUIUC2018; exactyearunknown.')
for n,y in [('Louis Schatzki',2025),('Ian George',2024),('Yujie Zhang',2024),('Brian Doolittle',2023)]:emit(p,s,'phd',n,f'{n} (PhD, {y})',y,True,heading='Group Alumni')
for n,y in [('Kaiyuan Ji',2021),('Senrui Chen',2019)]:emit(p,s,'undergraduate',n,f'{n} (Undergraduate, {y})',y,True,heading='Group Alumni')
for n,q in [('Daniel Dilley','Daniel Dilley (PhD, 2019)'),('Alvin Gonzales','Alvin Gonzales (MS, 2018)')]:hold(p,s,n,q,'PI moved from SIU to UIUC2018; this alumni degree entry alone does not establish a UIUC advising or membership episode.')
q=section(home,'Quantum Channel Masking','Structure Theorem');hold(p,home,'Hailey Murray',q,'News published2025 calls her former REU student but supplies no participation date or campus; possible previous-school episode remains unresolved.')
excluded[p]=['All postdocs and visiting postdoc Hanwool Lee: nonstudents.']
# Dallesasse: complete four current and20 explicitly dated alumni.
p='John M. Dallesasse';s=src(p,'/people/');
for n,r,q in [('Anik Mazumder','phd','Anik Mazumder (Ph.D Student )'),('Emily Becher','phd','Emily Becher (Ph.D Student )'),('Jason Flanagan','phd','Jason Flanagan (Ph.D. Student )'),('Gabriel Inojosa','masters','Gabriel Inojosa (M.S. Student )')]:emit(p,s,r,n,q,heading='Graduate Research Members')
alumni=[('Leah Espenhahn','phd',2026),('Robert Kaufman','phd',2025),('Kevin Pikul','phd',2025),('Collin Roy','undergraduate',2024),('Jake Cheng','undergraduate',2024),('Raman Kumar','phd',2023),('Nithiyassri Vivagandan','undergraduate',2023),('Patrick Su','phd',2022),('Mark Kraman','masters',2022),('John Anthony Carlson II','phd',2021),('Maanav Ganjoo','masters',2021),('Fu-Chen (Alex) Hsiao','phd',2020),('Coleman Williams','undergraduate',2019),('Shuang Chen','undergraduate',2019),('Kanuo Chen','phd',2017),('Saoud (Sam) AEA Almulla','masters',2017),('Thomas R. O’Brien Jr.','phd',2017),('Brittany Joy','undergraduate',2017),('Ben Kesler','phd',2017),('Guan-Lin Su','phd',2016)]
for n,r,y in alumni:
 q=section(s,n);q=q[:q.index(']')+1];emit(p,s,r,n,q,y,True,heading='Alumni Group Members')
# Chekuri: explicit advisees and individually dated thesis/research students.
p='Chandra Chekuri';s=src(p,'chekuri.cs');q=section(s,'Student Advising','Professional Activities')
for n,r in [('Weihao Zhu','phd'),('Ethan Luo','masters'),('Annie Zeng','phd')]:many(p,s,r,n,'Student Advising','ElFarouk Harb')
for n,r,y in [('ElFarouk Harb','phd',2026),('Rhea Jain','phd',2026),('Tanvi Bajpai','phd',2025),('Shiliang Zuo','phd',2025),('Junkai Song','student intern',2023),('Vasilis Livanos','phd',2023),('Manuel Torres','phd',2023),('Binghui (Alan) Cheng','undergraduate',2021),('Shovik Guha','undergraduate',2019),('Kent Quanrud','phd',2019),('Xilin Yu','masters',2019),('Vivek Madan','phd',2018),('Shalmoli Gupta','phd',2018),('Chao Xu','phd',2018),('Mark Idleman','masters',2017),('Shweta Patwa','masters',2017),('Sanchit Kalhan','undergraduate',2016)]:
 tail=q[q.index(n):];m=re.search(str(y)+r'\.?',tail);frag=tail[:m.end()];emit(p,s,r,n,frag,y,True,heading='Student Advising',relationship='membership'if n in ['Xilin Yu','Junkai Song']else 'advising',note='Explicit student-advising roster; XilinYu thesis adviser is TandyWarnow, so only research membership asserted.'if n=='Xilin Yu'else 'Explicit dated student advising/research entry; senior thesis indicates undergraduate research.')
emit(p,s,'undergraduate','Annie Zeng','Annie Zeng : Senior thesis , Dec 2025',2025,True,heading='Student Advising')
excluded[p]=['All degree/thesis completions2013orolder and BellLabsinterns: prewindow/prior-school.']
# Sayan: own roster plus CV, never committee members.
p='Sayan Mitra';s=src(p,'group.html');cv=src(p,'cvnoref.pdf')
many(p,s,'phd','Yan Miao|Chenxi Ji|Ege Yuceel|Noah Giles|Abhishek Pai','current members','undergraduate researchers')
many(p,s,'masters','Teodor Dimitrov Tchalakov|Krishna Dubey|Hanna Chen|Rishav Kumar','current members','undergraduate researchers')
for n,y in [('Yangge Li',2026),('Kristina Miller',2024),('Dawei Sun',2023),('Chiao Hsieh',2023),('Hussein Sibai',2021),('Ritwika Ghosh',2020),('Chuchu Fan',2019),('Zhenqi Huang',2016)]:
 tail=section(s,'phd alumni','ms alumni');a=tail.index(n);frag=tail[a:tail.index(')',a)+1];emit(p,s,'phd',n,frag,y,True,heading='phd alumni')
for n,y in [('Jai Anchalia',2026),('Douglas Belgorod',2026),('James Menezes',2026),('Will Shen',2026),('Alex Yuan',2026),('Ye Liu',2025),('Daniel Zhuang',2025),('Akul Datta',2025),('Benjamin C. Yang',2024),('Katherine Braught',2024),('Hongyi Li',2023),('Sumedh Raghoji',2023),('Haoqing (Steven) Zhu',2023),('Minghao Jiang',2021),('Tianqi (Ted) Liu',2020),('Matthew Potok',2018),('Bolun Qi',2018),('Nicole Chan',2018),('Yixiao Lin',2016)]:
 tail=section(s,'ms alumni','undergraduate alumni');a=tail.index(n);b=tail.index(')',a+len(n))+1;emit(p,s,'masters',n,tail[a:b],y,True,heading='ms alumni')
for n,y in [('Robert Azarcon',2025),('Yugal Kithany',2025),('Pranav Rajkumar',2025),('Eeshan Rajesh Zele',2025),('Jeeva Sundaram Murugan',2024),('Yubin Koh',2023),('Yixuan Jia',2023),('Keyi Shen',2023),('Rahul Kajjam',2023),('Daniel Wu',2022),('Yifeng Ni',2021),('Arnab Datta',2021),('Qichao Gao',2020),('Hebron Taylor',2020),('Rong Zhou Li',2019),('Peter Du',2018),('Yu Meng',2016)]:
 tail=section(s,'undergraduate alumni','Illinois faculty collaborators');a=tail.index(n);b=tail.index(')',a)+1;emit(p,s,'undergraduate',n,tail[a:b],y,True,heading='undergraduate alumni',relationship='membership')
# CV prose is flattened text from saved PDF, no headers/contact details in admitted quote fragments.
for n,r,y in [('Navid Mokhlesi','masters',2021),('Shuting Li','masters',2018),('Peter Leung','undergraduate',2020),('Aarushi Sharma','undergraduate',2024),('Nitish Bhupathi Raju','undergraduate',2024),('Zixin Mao','undergraduate',2023),('Liyi Sun','undergraduate',2016)]:
 t=text(cv);a=t.rfind(n);tail=t[a:];b=tail.index(')',tail.index(str(y)))+1;emit(p,cv,r,n,tail[:b],y,True,heading='Undergraduate'if r=='undergraduate'else 'Masters',relationship='membership',note='Named student/advising CV entry. NavidMokhlesi did not finish: membership only, no earned degree claimed.')
for n,y in [('Ege Yuceel',2026),('Yan Miao',2024),('Yangge Li',2021),('Kristina Miller',2021),('Hussein Sibai',2017),('Chuchu Fan',2016),('Ritwika Ghosh',2017)]:
 t=text(cv);a=t.rfind(n);tail=t[a:];b=tail.index(')',tail.index(str(y)))+1;emit(p,cv,'masters',n,tail[:b],y,True,heading='Masters',relationship='membership',note='Explicit master thesis/advising episode; tentatively dates are source observations, not degree completion claims.')
for n,y in [('Krishna Dubey',2025),('Shuting Li',2016),('Bolun Qi',2016)]:
 t=section(cv,'Undergraduate','Doctoral 1.');a=t.index(n);tail=t[a:];b=tail.index(')',tail.index(str(y)))+1;emit(p,cv,'undergraduate',n,tail[:b],y,True,heading='Undergraduate',relationship='membership')
for n in ['Daniel Hernandez','Marvin Hernandez','Berk Cagilci','Shuchen Song']:hold(p,s,n,n,'Undated undergraduate alumnus; roster and reviewedCV do not place research membership inside2016–2026.')
excluded[p]=['All doctoral/habilitation committees: no advising claim.','All expressly pre2016 degree/thesis episodes, including BereniceCarrascoCabreraMS2011.']
# Wenjuan: dates on current students; alumni remain separately unresolved.
p='Wenjuan Zhu';s=src(p,'/people');many(p,s,'graduate','Xiaotong Xu|Isaac Mark Wolstenholme|Junhao lin|Ye Lin','Graduate Student Xiaotong','Alumni')
for n in ['Jialun Liu','Hojoon Ryu','Zijing Zhao','Ankit Sharma','Wui Chung Yap','Zihan Yao','Yueming Yan','Hanwool Lee','Stasiu Chyczewski']:hold(p,s,n,n,'Student role explicit, but undated alumni of UIUClab founded2014; no dated membership/degree evidence in reviewed roster. Publication coauthorship is not membership evidence.')
excluded[p]=['KaiXu: postdoctoral fellow, not student.']
# Yang: graduate section retains literal roles, staff/research faculty excluded.
p='Yang Liu';s=src(p,'people.html');many(p,s,'graduate','Yaxin Yang|Chaojie Zhang|Dimitrios Gotsis|Shuyuan Zhang|Shengwei Chen','Graduate Students Yaxin','Contact Information');many(p,s,'masters','Shengjie Ma|Vidhi Parmar','Graduate Students Yaxin','Contact Information')
excluded[p]=['HongqiangMa: research assistant professor.','Phuong(Hong)Nguyen: research scientist.','ShengweiChen MechanicalEngineering is a discipline, not an asserted MEdegree; degree unspecified.']
# Brian: all dated alumni in window and sole current student, five undated held.
p='Brian Bailey';s=src(p,'people/index.html');emit(p,s,'phd','Wendy Shi','Wendy Shi (PhD)',heading='Students Wendy Shi')
for n,r,y in [('Emily Hastings','phd',2023),('Gina Do','phd',2023),('Patrick Crain','phd',2022),('Sneha Krishna Kumaran','phd',2022),('Jaewook Lee','undergraduate',2022),('Simran Desai','undergraduate',2022),('Melissa Cheng','undergraduate',2022),('Yu-Chun (Grace) Yen','phd',2021),('Yu (Wayne) Wu','phd',2020),('Helen Wauck','phd',2020),('Mia Schoening','masters',2020),('Albatool A. Alamri','masters',2018),('Robert Deloatch','phd',2017),('Farnaz Jahanbakhsh','masters',2017),('Antoine Dejong','masters',2017),('Kirill Mangutov','masters',2016),('Dharthi Nagaraj Kashyap','masters',2016)]:
 degree={'phd':'PhD','masters':'MS','undergraduate':'BS'}[r];emit(p,s,r,n,f'{n} ({degree}, {y})',y,True,heading='Alumni Emily Hastings')
for n in ['Arjun Venkataswamy','Jesse Krantzler','Caryn Leppert','Aarti Israni','Christina Poon']:hold(p,s,n,n+' (undergraduate research)','Undated research alumnus of long-running UIUClab; source does not establish a2016–2026episode.')
excluded[p]=['All expressly dated degree completions2015orolder.']
# Sarah: consume the owned data array as JSON, never execute downloaded JavaScript.
p='Sarah Gimbert Sterman';s=src(p,'shared/js/people.js');raw=Path(s['body_path']).read_text();data=json.JSONDecoder().raw_decode(raw,raw.index('['))[0]
for member in data:
 n=member['name'];r=member['role']
 if r=='PI':continue
 pat=re.compile(r'\{\s*"name":\s*'+re.escape(json.dumps(n))+r'.*?\}',re.S);obj=pat.search(raw).group();q=' '.join(obj.split());role='phd'if 'PhD'in r else ('undergraduate'if r=='Undergraduate'else ('masters'if r in ['MS','MCS']else 'student alumnus'))
 emit(p,s,role,n,q,alumni=not member['current'],heading='window.people =',relationship='membership',degree_detail=r,note='Owned PICL lab data rendered by script_people.js. UIUClab began2023; undated alumni therefore insidewindow. ICAN is a program, not an inferred mastersdegree.')
cv=src(p,'sterman_cv.pdf')
for literal,canonical in [('David Zhou','David Zhou'),('Mingyan Claire Tian','Claire Tian'),('James Eschrich','James Eschrich'),('William Goss','William Goss'),('Matt Makila','Matt Makila'),('Angela Bi','Angela Bi'),('Melina O’Dell',"Melina O'Dell"),('Hannah Kim','Hannah Kim')]:
 q=section(cv,'Current Students: PhD:','Undergraduate:');emit(p,cv,'phd',literal,q,canonical=canonical,heading='RESEARCH MENTORSHIP')
q=section(cv,'ICAN:','Undergraduate:');emit(p,cv,'student alumnus','Hannah Kim',q,alumni=True,heading='RESEARCH MENTORSHIP',degree_detail='ICAN',relationship='membership',note='Named ICAN mentoring episode, not a mastersdegree; same currentPhDstudent identity within thislab. PIownedCV statesPICLfounded2023.')
proof=src(p,'KCunningham_CV_online.pdf');pq=section(proof,'RESEARCH MENTORSHIP:','Masters students:')
for n in ['Arif Demirtas','Jina Hur']:
 q=section(cv,'Mentorship: PhD:','MS/MCS:');emit(p,cv,'phd',n,q,alumni=True,heading='RESEARCH MENTORSHIP',relationship='membership',corroborating_sources=[dict(url=proof['url'],sha256=proof['sha256'],quote=pq)],note='SarahCV explicitPhDmentee. Same individual as MehmetArifDemirtas orJinyoung(Jina)Hur in ownedKatieCV withPhDenrollmentFall2023; episode cannotpredateUIUC2023. No cross-labcollectionidentity reused and no current2026status or exactmentorshipyear inferred.');new[-1].update(alumni=False,years=None,years_basis='Undated PhDmentorship after independentlydocumented UIUCPhDenrollmentFall2023; exactmentoringyear unresolved.')
for n in ['Carl Guo','Parisa Rabbani','Yasmin Isa']:
 q=section(cv,'Mentorship: PhD:','MS/MCS:');hold(p,cv,n,q,'Explicit PhD mentorship but undated and not campus-scoped; PI also mentored during prior BerkeleyPhD. No UIUCepisode inferred solely from name coincidence with other labs.')
for n in ['Gabe Wozniak','Kieu-Vi O’Brien','Jessie Mindel','Angel Ibarra','Michelle Gantos','Ryan Qiao','Alyse Jones','Junghyun Choy','Debbie Yuen','Resham Khanna','Shayna Kothari','Tiffany Chien','Weiwei Zhang','Vivian Liu','Evey Huang']:
 q=section(cv,'Undergraduate: Gabe Wozniak','PROFESSIONAL EXPERIENCE');hold(p,cv,n,q,'Undated undergraduate mentorship includes possible Berkeley/Stanford period; no explicit UIUCmembership episode.')
excluded[p]=['AyseHunt,MengkeWu,WendyShi: PhDcommittees only, notadvising.','Class teaching/outreach participants not individually named research mentees.']
# Deming: full current rows, dated UIUC graduates, and newer owned CV.
p='Deming Chen';s=src(p,'people.html');cv=src(p,'DemingChen_CV.pdf')
t=section(s,'Graduate Students','Researchers at Illinois ARCS')
for m in re.finditer(r'([^()]+?) \((Ph\.D\.[^)]*|M\.S\.[^)]*)\)',t[len('Graduate Students '):]):
 n=m[1].strip();r='phd'if m[2].startswith('Ph')else 'masters'
 # Names with parenthesized nicknames are handled explicitly below.
 if n in ['Huang','Wan','Yuan','Yingbing','Lily','Neo'] or any(z in n for z in ['(Wendy)','(Jiaxin)','(Zehua)']):continue
 emit(p,s,r,n,m[0].strip(),heading='Graduate Students')
for n in ['Yingbing (Wendy) Huang','Lily (Jiaxin) Wan','Neo (Zehua) Yuan']:
 a=t.index(n);tail=t[a:];b=tail.index(')',len(n))+1;emit(p,s,'phd',n,tail[:b],heading='Graduate Students')
many(p,s,'undergraduate','Tyler Bruce Andreas|Ali Asghar|Jintong Doris Hou|Olivia Kapusniak|Satyam Raj|Eric Shim|Cher Rui Tan','Undergraduate Researchers','Alumni from UIUC',relationship='membership')
# Explicit dated alumni avoid capturing placement prose as a person name.
for role,degree,items in [('phd','Ph.D.',[(2017,'Sven Choden Konigsmark|Keith Campbell'),(2018,'Chen-Hsuan Lin'),(2019,'Di He|Yi Liang'),(2021,'Ashutosh Dhar|Sitao Huang'),(2022,'Xinheng Liu|Xiaofan Zhang'),(2023,'Anand Ramachandran|Wei Zuo'),(2024,'Yuhong Li'),(2025,'Hanchen Ye')]),('masters','M.S.',[(2016,'Warren Kemmerer|Yan Yan|Zelei Sun'),(2017,'Daniel Chen|Gowthami Manikandan|Chuanhao Zhuge'),(2018,'Zhangqi Xu|Huiren Li'),(2019,'Kenny Umenthum|Jong Bin Lim|Dae Hee Kim'),(2020,'Xingkai Zhou|Qin Li|Zhijie Jin|Yujia Qiu'),(2021,'Jack Li|Mang Yu'),(2022,'Paul Reckamp|Vibhakar Vemulapati'),(2023,'Curtis Yu|Yizhen Lu|Meghna Mandava|Sean Amin Farhat-Sabet'),(2024,'William Kozlowski')])]:
 for year,names in items:
  for n in names.split('|'):
   q=n+', '+degree+(', 'if n!='William Kozlowski'else ' ')+str(year);emit(p,s,role,n,q,year,True,heading='Alumni from UIUC')
t=section(cv,'Current Graduate Students:','Current Researchers/Collaborators')
for chunk in t.split('•')[1:]:
 q=chunk.strip();q=re.sub(r' \d+$','',q)
 n=q[:q.rfind(' (')];role='phd'if 'Ph.D.'in q else 'masters';emit(p,cv,role,n,q,heading='Current Graduate Students:')
t=section(cv,'Current Undergraduate Researchers:','Alumni from UIUC:')
for chunk in t.split('•')[1:]:
 n=chunk.strip();emit(p,cv,'undergraduate',n,n,heading='Current Undergraduate Researchers:',relationship='membership')
for n,y in [('Sanjana Pingali',2025),('Bill Dai',2025),('Soyeon Lee',2025),('Nuoyan Wang',2026),('Michael Gamota',2026),('Alyssa Huang',2026)]:emit(p,cv,'masters',n,f'{n}, M.S. {y}',y,True,heading='M.S. Graduates')
for source,heading,end in [(s,'Undergraduate Researchers:','Alumni from Illinois ARCS'),(cv,'Undergraduate Researcher Alumni:','Alumni from Illinois ARCS')]:
 t=section(source,heading,end);tail=t[len(heading):].split('etc.')[0].strip().rstrip(',');names=tail.split(', ')
 for n in names:
  if n and n!='many of them later joined either top graduate schools (such as MIT':hold(p,source,n,n,'Undated undergraduate research episode; no membership year inferred from later degree, placement or publication. This is an unresolved episode, even when another degree episode for same person is accepted.')
excluded[p]=['All UIUCpostdocs and SingaporeARCS/ADSCstaff/researchers/postdocs: nonstudent roles.','All explicit pre2016 degree episodes.','ExpectedFall2026 degrees are not asserted complete; currentPhDsource retained.']
# A newer CV supersedes the old HTML's current MS heading for known2025graduates.
for row in new:
 if row['pi']=='Deming Chen' and row['name']in['Bill Dai','Sanjana Pingali','Soyeon Lee'] and row['url'].endswith('people.html'):
  row.update(years=[2025,2025],alumni=True,years_basis='Newer owned CV explicitly records MSgraduation2025; old HTMLcurrentheading is stale, not2026membership.',corroborating_sources=[dict(url=cv['url'],sha256=cv['sha256'],quote=row['name']+', M.S. 2025')],note='Retain old roster evidence, but supersede its stale currentMSlabel with the newer explicitlydated MS2025source; no2026studentepisode asserted.')
# Abigail: preserve individual mentoring roles; committee-only names never advisees.
p='Abigail Wooldridge';cv=src(p,'A-Wooldridge-CV');s=src(p,'people-2');al=src(p,'lab-alumni')
for n in ['Kaitlin Skurnak','Gavin Bourgeois','Mojgan Zoaktafi']:
 q=f'{n}, PhD Advisee and Research Assistant, 2024 – Present';emit(p,cv,'phd',n,q,heading='Graduate Student Mentoring')
emit(p,cv,'phd','Kaitlyn Hale-Lopez','Kaitlyn Hale-Lopez, PhD Advisee and Research Assistant, 2020 – 2024',2024,True,heading='Graduate Student Mentoring')
for n,y,start in [('Anya Knecht',2024,2023),('Irem Yuceel',2023,2022),('Angela Chan',2023,2022),('Emma Mayes',2022,2021)]:
 q=f'{n}, Master’s Advisee'+(''if n=='Anya Knecht'else ' and Research Assistant')+f', {start} – {y}';emit(p,cv,'masters',n,q,y,True,heading='Master’s Thesis Advisees:')
for n,y,q in [('Huanyu Sui',2025,'Huanyu Sui, Spring 2025'),('Carolina Carvalho Manhães Leite',2024,'Carolina Carvalho Manhães Leite, Advisee and Research Assistant, 2020 – 2024'),('Mar Gonzalez Calvo',2022,'Mar Gonzalez Calvo, Spring 2022'),('Deelaka Bandara',2022,'Deelaka Bandara, Spring 2022'),('Ruixuan Gong',2021,'Ruixuan Gong, Fall 2021')]:emit(p,cv,'masters',n,q,y,True,heading='Master’s Project Advisees:',relationship='membership',note='Explicit master project mentoring. Carolina pausedPhDin2024withMS; noPhDcompletion claimed. Exchange student Mar is research membership, noUIUCdegree asserted.')
emit(p,cv,'phd','Carolina Carvalho Manhães Leite','Carolina Carvalho Manhães Leite, Advisee and Research Assistant, 2020 – 2024',2024,True,heading='Master’s Project Advisees:',relationship='membership',corroborating_sources=[dict(url=cv['url'],sha256=cv['sha256'],quote='was one of my PhD advisees and decided in 2024 to interrupt her PhD studies and graduate with a master’s degree.')],note='Explicit interrupted PhDstudent episode, not PhDdegree completion.')
for n,y,q in [('Ryan Santens',2022,'Ryan Santens, Research Assistant, 2021 – 2022'),('Talia Scheck-Long',2021,'Talia Scheck-Long, Research Assistant, 2020 – 2021'),('Amrutha Kumaran',2021,'Amrutha Kumaran, MS in Health Technology Capstone, 2020-2021'),('Rory (Alina) Lusebrink',2021,'Rory (Alina) Lusebrink, Research Assistant, 2020 – 2021'),('Brittany (Sondria) Cottrell',2021,'Brittany (Sondria) Cottrell, Research Assistant, 2020 – 2021'),('Widya Ramadhani',2021,'Widya Ramadhani, Research Assistant, 2019 – 2021'),('Emily Heuck',2021,'Emily Heuck, Research Assistant, 2019 – 2021'),('Jyotika Roychowdhury',2019,'Jyotika Roychowdhury, Research Assistant, 2019'),('Sadia Ashrafi',2019,'Sadia Ashrafi, Research Assistant, 2019')]:emit(p,cv,'masters'if n=='Amrutha Kumaran'else 'graduate',n,q,y,True,heading='Graduate Student Mentoring',relationship='membership',note='Other subsection inside GraduateStudentMentoring supports student researchmembership, no doctorate inferred from later alumni credentials.')
for n,y,q in [('Audrey Freeman',2024,'Audrey Freeman, Undergraduate Research Assistant, 2023 – 2024'),('Madelyn Saenz',2024,'Madelyn Saenz, Undergraduate Research Assistant, 2022 – 2024'),('Irem Yuceel',2022,'Irem Yuceel, Undergraduate Research Assistant, 2021 – 2022'),('Kristen Whalen',2022,'Kristen Whalen, Bachelor of Arts Thesis Advisee, 2021 – 2022'),('Gary Angdoko',2021,'Gary Angdoko, Undergraduate Research Assistant, 2021'),('Mia Spiwak',2021,'Mia Spiwak, Undergraduate Research Assistant, 2019 – 2021'),('John Morgan',2020,'John Morgan, Undergraduate Research Assistant, 2019 – 2020'),('Anthony Composto',None,'Anthony Composto, Undergraduate Research Assistant, 2019 – Present'),('Ashley Mitchel',None,'Ashley Mitchel, Undergraduate Research Assistant, 2019 – Present'),('Ariel Alexander',2020,'Ariel Alexander, Undergraduate Research Assistant, 2019 – 2020'),('Maya Burgard',2020,'Maya Burgard, Undergraduate Research Assistant, 2018 – 2020'),('Maddie L. Kaufman',2019,'Maddie L. Kaufman, Undergraduate Research Assistant, 2019'),('RuthAnn Haefli',2019,'RuthAnn Haefli, Undergraduate Research Assistant, 2018 – 2019')]:emit(p,cv,'undergraduate',n,q,y,True,heading='Undergraduate Student Mentoring',relationship='membership')
for n in ['Kathleen Willoughby','Paty Cintora']:hold(p,al,n,n,'Alumni list gives credentials without lab role; PI CV does not identify a student episode. A degree credential alone does not distinguish former student from staff.')
for n in ['Bat-Zion Hose','Megan Salwei','Jordan Ramsey','Janette Garcia','Katherine Schroeer']:excluded.setdefault(p,[]).append(n+': preceding Wisconsin period or preUIUC2018 episode without a proven continuedUIUCepisode.')
excluded[p]+=['All qualifying/dissertation/thesis committees/external examinations: not advising.','PostdocsHannaApsley/ChihabNadri andvisitorKatharinaWenderott: nonstudents.']
# Preserve earlier groups byte-for-byte as JSON values; append the next ten only.
counts={pi:len({x['name']for x in new if x['pi']==pi})for pi in dict.fromkeys(x['pi']for x in new)}
assert len(counts)==10,counts
for pi in counts:
 rec=next((x for x in records if x['pi']==pi),None)
 if rec is None:rec=dict(pi=pi,students=[]);records.append(rec)
 assert not rec['students'],pi
 rec.update(reviewed_on='2026-11-24',review='Complete available owned student/current/alumni/advising source inventory manually reviewed for2016–2026. Explicitly unresolved role/date/campus observations retained separately; no unlisted real-world completeness claim.',students=[{k:v for k,v in x.items()if k!='pi'}for x in new if x['pi']==pi])
 if pi in holds:rec['unresolved_students']=holds[pi]
(WT/'hierarchy/uiuc/reviewed/few-students-evidence.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
review=dict(session='codex-uiuc-students30-1124',date='2026-11-24',counts=counts,source_rows=len(new),held_observations=holds,exclusions=excluded,scope='All eligible students in reviewed available public sources, with unresolved date/role/campus observations separately retained; no claim that unlisted real-world students are absent.')
review['net_new_memberships']=sum(counts.values());review['before_counts']={pi:0 for pi in counts}
(OUT/'roster-review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n');(OUT/'sources.json').write_text(json.dumps({p:manifest[p]for p in counts},indent=2)+'\n');(OUT/'date-sources.json').write_text(json.dumps(dates,indent=2)+'\n');(RUN/'expected-students.json').write_text(json.dumps({p:sorted({x['name']for x in new if x['pi']==p})for p in counts},indent=2)+'\n');print(counts,'total',sum(counts.values()),'rows',len(new),'holds',sum(map(len,holds.values())))
