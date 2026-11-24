import hashlib,json,re,subprocess
from pathlib import Path
from bs4 import BeautifulSoup
import atlas_paths as P
RUN=P.SCRATCH/'uiuc-students50-1124';WT=P.ROOT/'worktrees/uiuc-students50-1124';OUT=WT/'reports/uiuc-students50-1124';OUT.mkdir(exist_ok=True,parents=True)
manifest=json.loads((RUN/'sources.json').read_text());dates=[]
for fn in ['extra-source-results.json','navigation-source-results.json','cv-source-results.json']:
 if (RUN/fn).exists():dates.extend(x for x in json.loads((RUN/fn).read_text()) if x.get('body_path'))
records=json.loads(subprocess.check_output(['git','-C',str(WT),'show','8d2cc52ef91111dcaed217c546a3ad016207082d:hierarchy/uiuc/reviewed/few-students-evidence.json'],text=True));new=[];holds={};excluded={}
def src(pi,needle):return next(x for x in manifest[pi]+dates if needle.rstrip('/')in x['url']and x.get('body_path'))
_text_cache={}
def text(s):
 k=(s['body_path'],s['sha256'])
 if k in _text_cache:return _text_cache[k]
 b=Path(s['body_path']).read_bytes();assert hashlib.sha256(b).hexdigest()==s['sha256']
 if b.startswith(b'%PDF'):t=Path(s['text_path']).read_text()
 elif s['url'].endswith(('.js','.json')):t=' '.join(b.decode().split())
 else:
  soup=BeautifulSoup(b,'html.parser')
  for e in soup(['script','style','noscript']):e.decompose()
  t=' '.join(soup.get_text(' ',strip=True).split())
 _text_cache[k]=t
 return t

def section(s,start,end=None):
 t=text(s);a=t.index(start);return t[a:t.index(end,a+len(start))if end else len(t)]
def emit(pi,s,role,name,q,year=None,alumni=False,canonical=None,heading='',note='',**kwargs):
 assert q in text(s),(pi,name,'quote');assert name in q,(pi,name,'name');assert '@'not in q,(pi,name,'contact')
 if heading:assert heading in text(s),(pi,heading)
 row=dict(name=canonical or name,role=role,years=[year,year]if year else ([2026,2026]if not alumni else None),years_basis='Explicit dated source observation; no unproved interval or degree completion inferred.'if year else ('Capture observation only; no earlier membership years inferred.'if not alumni else 'Undated alumni of UIUC-only lab established after2016; exact membership year unresolved.'),alumni=alumni,url=s['url'],observed=s['observed'],sha256=s['sha256'],quote=q,rule='R-STU-01',reviewed_by='codex-uiuc-students50-1124',reviewed=True,auto=False,note=note or 'PI-owned student/advising roster manually reviewed, with school and role scope.')
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
# Both individual CVs explicitly name their own advisees in the joint DASSL lab.
for p,needle,start,end in [('Ram Alagappan','ramalagappan.github.io/pdfs','Student Advising','Service OSDI'),('Aishwarya Ganesan','aishwaryaganesan.github.io/pdf','Graduate Student Advising','Other Mentoring')]:
 cv=src(p,needle);q=section(cv,start,end)
 for n in ['Henry Zhu','Xuhao Luo','Shreesha Bhat','Jiyu Hu','Kiran Hombal','Landon Johnson','Michael Noguera',('Emaan Attique'if p=='Ram Alagappan'else'Emaan Atique')]:
  a=q.index(n);frag=q[a:];stop=re.search(r'(?:Started|since) (?:Fall|Spring) 20\d\d',frag);emit(p,cv,'phd',n,frag[:stop.end()],heading=start,note='PI-specific owned CV explicitly lists this student. Xuhao start2022 in RamCV conflicts withSpring2023 inAishCV/group; capture-year membership only, no earlier year inferred.')
 for n in ['Wenqing Luo','Chaitanya Bhandari','Ramya Bygari','Madhav Jivrajani']:
  a=q.index(n);frag=q[a:a+170];frag=frag[:frag.find('Thesis:')]if'Thesis:'in frag else frag
  year=(2023 if n=='Wenqing Luo'else 2026 if n=='Madhav Jivrajani'else None)if p=='Aishwarya Ganesan'else None
  emit(p,cv,'masters',n,frag.strip(),year,True,heading=start,note='Named graduate advisee. AnticipatedSpring2024 forChaitanya/Ramya is not asserted as completed degree or exact membership year; later owned lab identifies MSthesis alumni.')
 group=src(p,'dassl-uiuc.github.io');q=section(group,'Alumni Madhav','Publications 2026')
 for n in ['Neil Kaushikkar','Shubhi Jain','Abhi Wangoo','Akul Gupta','Amaan Khan','Tony Hong']:
  tail=q[q.index(n):];frag=tail[:tail.index(')')+1];hold(p,group,n,frag,'Shared multi-PI DASSL alumni roster lacks an individual adviser attribution in either reviewed CV. No automatic attribution to both PIs; TonyHong visiting researcher also lacks an explicit student role.')
 excluded[p]=['Individual advising evidence from both CVs supports shared12, not automatic reuse of the collective lab.']
p='Aishwarya Ganesan';cv=src(p,'aishwaryaganesan.github.io/pdf');q=section(cv,'Other Mentoring','Service');hold(p,cv,'Yi Xu',q,'UCSD graduate student mentoring undated; no source establishes whether mentoring continued into PI UIUCappointment after2022.');excluded[p]+=['YifanDai andYienXu: explicitlyUWgraduate mentoring withBourbonOSDI2020, beforeUIUC2022.']
# Ruta's complete available CV includes graduate, undergraduate and high-school research mentoring.
p='Ruta Mehta';cv=src(p,'Ruta-Mehta-CV.pdf');s=src(p,'teaching.html')
for n,y in [('Aniket Murhekar',2025),('Pooja Kulkarni',2025),('Vasileios Livanos',2023),('Rucha Kulkarni',2023),('Shant Boodaghians',2021)]:
 q=section(cv,'• Ph.D. students','• Masters’ students');a=q.index(n);tail=q[a:];end=re.search(r'20\d\d\s*-\s*'+str(y),tail).end();emit(p,cv,'phd',n,tail[:end],y,True,heading='Student Research Advising')
for n,y in [('Aniket Murhekar',2020),('Spencer Gordon',2017)]:
 q=section(cv,'• Masters’ students','• Undergraduate students');a=q.index(n);tail=q[a:];end=re.search(r'20\d\d\s*-\s*'+str(y),tail).end();emit(p,cv,'masters',n,tail[:end],y,True,heading='• Masters’ students')
ug=[('Atharva Naik',None),('Apurv Singhdeo',None),('Yunho Chang',None),('Aditya Arya',2025),('Ayush Chandra',2025),('Anushka Shankaran',2025),('Srikar Pisupati',2025),('Swetha Subbaih Yegappan',2025),('Anh Fung',2025),('Annie Zhang',2024),('Kyra Gunluck',2023),('Arjun Agrawal',2023),('Wenxiao Yang',2023),('Shreya Patil',2021),('Shivam Gupta',2018)]
q=section(cv,'• Undergraduate students','• Highschool students')
for n,y in ug:
 # Keep the entire literal bullet when several students share its explicit date.
 chunks=q.split('– ');frag=next(z for z in chunks if n in z);frag=frag[:frag.index('(')]if '('in frag and n!='Kyra Gunluck'else frag
 if not re.search(r'20\d\d',frag):frag=next(z for z in chunks if n in z)
 frag=frag.split('Worked on')[0].strip();emit(p,cv,'undergraduate',n,frag,y,bool(y),heading='• Undergraduate students (selected)',relationship='membership',note='Named individual research mentee, not a course enrollment. Kyra is Cornell undergraduate research participant; no UIUCdegree asserted.')
q=section(cv,'Maya Vishwanathan','Teaching • CS');emit(p,cv,'student researcher','Maya Vishwanathan',q[:q.index('(')].strip(),2024,True,heading='• Highschool students',relationship='membership',degree_detail='high-school research student',note='Named high-school research mentee who coauthored/presented a paper; not a degree adviser claim.')
excluded[p]=['VishnuNarayanan andBhaskarRayChaudhury: postdocs, not students.','Teaching and committee/service participation are not research mentoring.']
# Forbes's placeholder is a degree role, never a fabricated graduation date.
p='Michael A. Forbes';s=src(p,'miforbes.cs.illinois.edu/');
for n,y in [('Zander Kelley',2023),('Robert Andrews',2024)]:emit(p,s,'phd',n,f'{n} (PhD {y})',y,True,heading='STUDENTS')
emit(p,s,'phd','Andrei Staicu','Andrei Staicu (PhD 20??)',heading='STUDENTS',note='Literal PhD20?? is an unspecified completion date, not a year; capture-year membership only.')
# LPNA explicit degree sections; its mixed former-participant list remains unresolved.
p='Edgar Solomonik';s=src(p,'lpna.cs.illinois.edu/')
many(p,s,'phd','Jack Weinstein|Qizhao Huang|Zhanrui Zhang|Nick Koskelo','PhD students Jack','Master’s students')
many(p,s,'masters','Akhilesh Mocharla','Master’s students','Undergraduate students');many(p,s,'undergraduate','Sreehaas Chinnala','Undergraduate students Sreehaas','Publications Publications')
for n,y in [('Yuchen Pang',2026),('Navjot Singh',2025),('Edward Hutter',2024),('Linjian Ma',2023),('Samah Karim',2022)]:emit(p,s,'phd',n,f'{n} ({y})',y,True,heading='PhD alumni')
for n,y in [('Wentao Yang',2022),('Navjot Singh',2020)]:emit(p,s,'masters',n,f'{n} ({y})',y,True,heading='Master’s theses')
for n,y in [('Yiqing Zhou',2020),('Tianyi Hao',2020),('Youcef Hadjarab',2020),('Zecheng Zhang',2019),('Pavle Simonovic',2018),('Edward Hutter',2017)]:emit(p,s,'undergraduate',n,f'{n} ({y})',y,True,heading='Bachelor’s theses')
q=section(s,'Other past participants','Courses and recorded lectures');names=['Jessica Williams','Sreevardhan Atyam','Aniket Deshpande','Anitej Chanda','Boyang Li','Aarnav Varanasi','Chandani Grover','Bangyan Shi','Aniruddha Sen','Mengyuan (Mina) Sun','Changsheng Chen','Tim Baer','Raul Platero','Dipro Ray','Annika Dugad','Caleb Ju','Yifan Zhang','Zhaoyu Wu','Hung Woei Neoh','Hongru Yang','Yunxin (David) Zhang','Xiaoxiao Wu','Siyuan Zhang','Naijing Zhang','Fan Huang','Eric Song','Ruiqian Yao','Eduardo Yap','Peter Tatkowski','Qile Zhi','Thomas Warther']
for i,n in enumerate(names):
 a=q.index(n);b=q.index(names[i+1],a)if i+1<len(names)else len(q);hold(p,s,n,q[a:b].strip(),'Mixed former graduate/undergraduate researchers and visitors; entry supplies no individual student degree/role. Discipline or dated group participation alone does not establish a student role. Owned CV advising section does not identify a degree/role for these mixed-list participants.')
cv=src(p,'https://solomonik.cs.illinois.edu/cv/Solomonik_CV.pdf')
hold(p,s,'Tobias Wicky','Tobias Wicky (2017)','Owned CV identifies ETHZurich BS2016/MS2017 coadvising from the PI prior ETHperiod. No source explicitly establishes continued UIUC-lab/student episode afterPIjoinedUIUCAugust2016; retain unresolved school scope.')
hold(p,cv,'Tobias Wicky','Tobias Wicky (BS 2016, MS 2017, ETH Zurich, co-advised with Torsten Hoefler)','Explicit ETHdegree context; do not infer a UIUCdegree or continued UIUC-lab episode from completionyear or a generic past-advising entry.')
for row in new:
 if row['pi']!=p:continue
 n=row['name'];role=row['role']
 if n in ['Akhilesh Mocharla','Sreehaas Chinnala']:continue
 if not row['alumni']:cq=section(cv,'Current PhD advisees:','Past Postdoctoral mentees:')
 elif role=='phd':cq=n+' (PhD '+str(row['years'][0])+')'
 elif role=='masters':cq=n+' (MS '+str(row['years'][0])+')'
 elif n=='Edward Hutter':cq='Edward Hutter (DOE CSGF fellow, BS 2017)'
 else:cq=n+' (BS '+str(row['years'][0])+')'
 assert cq in text(cv);row['corroborating_sources']=[dict(url=cv['url'],sha256=cv['sha256'],quote=cq)]
excluded[p]=['MaryamDehghan,TongDing andRaghavendraKanakagiri: postdoctoral researchers.']
# Julia's newer CV supersedes stale group headings and supplies degree/undergraduate dates.
p='Julia Hockenmaier';cv=src(p,'HockenmaierCV.pdf');s=src(p,'hockenmaier.cs.illinois.edu')
for n in ['Jinu Lee','Sewoong Lee','Katya Yegorova','Adam Davies','Ikhyun Cho','Risham Sidhu','Marc Canby','Rajarshi Haldar']:
 q=section(cv,'Student supervision PhD students','MS students');a=q.index(n);tail=q[a:];m=re.search(r'since Fall 20\d\d',tail);emit(p,cv,'phd',n,tail[:m.end()],heading='Student supervision PhD students')
for n,y in [('Prashant Jayannavar',2026),('Anjali Narayan-Chen',2020),('Alice Lai',2018)]:emit(p,cv,'phd',n,f'{n}, PhD Computer Science, {y}',y,True,heading='Student supervision PhD students',note='Explicit dated CVPhDentry; source year retained without inventing a defense date. Anjali2020 supersedes old group page current label.')
for row in new:
 if row['pi']==p and row['name']=='Prashant Jayannavar':
  row.update(alumni=False,years_basis='CV doctoral-student entry dated2026; completion status unresolved, no graduation or defense date inferred.',note='Retain the explicit2026doctoral student observation. The CV does not explicitly state that the degree is completed, and the group roster labels PhDstudent; no completed-degree claim.')
for n,y in [('Amit Athani',2023),('Dhruv Agarwal',2019),('Sidhartha Satapathy',2019),('Sarah Schieferstein',2018),('Mihika Dave',2018),('Chris Cervantes',2017),('Ryan Musa',2016)]:emit(p,cv,'masters',n,f'{n}, MS Computer Science, {y}',y,True,heading='MS students')
for n in ['Zijian Yao','Yongjin Kim','Xiaoyan Wang']:emit(p,cv,'undergraduate',n,f'{n}, Fall 2017',2017,True,heading='Senior theses')
hold(p,s,'Jiacheng (Gary) Lui','Jiacheng (Gary) Lui , BS','Undated undergraduate alumnus; not resolved by CV and PI lab predates2016.')
excluded[p]=['All external andIllinois thesis committees: not advising.','YonatanBisk/MicahHodosh2015,PeterYoung2013 andallpre2016senior theses includingCyrusRashtchian2010: outsidewindow.']
# Veeravalli's newer CV corrects three stale current labels and adds undergraduate projects.
p='Venugopal V. Veeravalli';cv=src(p,'cv_vvv.pdf')
for n in ['Jiawei Li','Argyrios Gerogiannis','Yu-Han Huang']:emit(p,cv,'phd',n,n+'. Currently working on Ph.D. thesis.',heading='Ph.D. Students')
for n,y in [('Adarsh Subramaniam',2025),('Akshayaa Magesh',2024),('Aditya Deshmukh',2023),('Yuchen Liang',2023),('George Rovatsos',2020),('Yuheng Bu',2019),('Meghana Bande',2019),('Jonathan Ligo',2017),('Craig Wilson',2016)]:
 q=section(cv,'Ph.D. Students','M.S. Students');a=q.index(n);tail=q[a:];m=re.search(str(y),tail);emit(p,cv,'phd',n,tail[:m.end()],y,True,heading='Ph.D. Students',note='Newer dated CV supersedes stale website current label; no2026studentepisode asserted for completed degrees.')
for n,y in [('Akshayaa Magesh',2020),('Yuheng Bu',2016),('George Rovatsos',2016)]:
 q=section(cv,'M.S. Students','Undergraduate Research Projects');a=q.index(n);tail=q[a:];m=re.search(str(y),tail);emit(p,cv,'masters',n,tail[:m.end()],y,True,heading='M.S. Students')
q=section(cv,'Undergraduate Research Projects (last ten years)','INVITED TALKS')
for chunk in q.split('◦')[1:]:
 frag=chunk.strip();frag=frag.split('Veeravalli-32')[0].strip();n=frag.split(',')[0]if ','in frag.split('“')[0]else frag.split(' “')[0];n=n.strip();years=re.findall(r'20\d\d',frag);emit(p,cv,'undergraduate',n,frag,int(years[-1]),True,heading='Undergraduate Research Projects (last ten years)',relationship='membership')
excluded[p]=['All postdoctoral associates, includingAdityaDeshmukh post-PhDstage: not student episodes.','Every explicit pre2016 MS/PhDcompletion: outsidewindow.']
# Ghose: explicitly school-scoped CV distinguishes Illinois students from CMU mentoring.
p='Saugata Ghose';cv=src(p,'ghose.cs.illinois.edu/docs');s=src(p,'students.html')
for n in ['Ryan Wong','Yiqiu Sun','Sudhanshu Agarwal','Evie Shen','Arjun Tyagi','Aniket Das','Dylan Meeks']:
 q=section(s,'Current Students Ph.D. Students',"Master's Students");a=q.index(n);frag=q[a:a+130];emit(p,s,'phd',n,frag,heading='Current Students Ph.D. Students')
many(p,s,'masters','Shreya Sharma|Qingyuan Liu',"Master's Students","Bachelor's Students")
many(p,s,'undergraduate','Zoe Kaiser|Karan Annam|Paige Nothelfer|Pranav Mandava|Laasya Aduri|Vallabh Arun',"Bachelor's Students",'Alumni Ph.D. Alumni',relationship='membership')
for n,y,canonical in [('Nabila Tasnim',2026,None),('Dawei Xiong',2026,None),('Vijay Richard Shah',2025,None),('Pratik Rajesh Sampat',2024,None)]:
 q=section(cv,'Graduated Research M.S. Students','Current Research M.S. Students');a=q.index(n);tail=q[a:];m=re.search(str(y),tail);emit(p,cv,'masters',n,tail[:m.end()],y,True,heading='Graduated Research M.S. Students')
q=section(cv,'Illinois Undergraduate Researchers','Illinois Master’s Researchers')
aliases={'Huiyao (Jenny) Liang':'Huiyao (Jenny) Liang','Jiwon (Julie) Lee':'Jiwon (Julie) Lee','Kevin Michael Higgs':'Kevin Michael Higgs'}
for chunk in q.split('»')[1:]:
 frag=chunk.strip();n=frag[:re.search(r'\(20\d\d',frag).start()].strip();year=re.search(r'\(20\d\d.*?\)',frag);quote=frag[:year.end()];yrmatch=re.findall(r'20\d\d',year.group());current='present'in year.group()
 if n=='Karan Amman':
  hold(p,cv,n,quote,'Possible CVtypo for current owned-webKaranAnnam, but surname spelling conflicts. Keep literal web student once; no second Ammanidentity or asserted alias without corroboration.');continue
 # Current PhD/MS identities retain their earlier undergraduate episode only once.
 emit(p,cv,'undergraduate',n,quote,int(yrmatch[-1])if not current else None,not current,heading='Illinois Undergraduate Researchers',relationship='membership')
for n,y in [('Amol Shah',2026),('Vishnu Srinivasan',2022)]:
 q=section(cv,'Illinois Master’s Researchers','Illinois Visiting Researchers');a=q.index(n);tail=q[a:];m=re.search(r'\)',tail);emit(p,cv,'masters',n,tail[:m.end()],y,True,heading='Illinois Master’s Researchers',relationship='membership')
# Explicit current CV nicknames provide safe within-lab aliases without separate people.
for row in new:
 if row['pi']==p and row['name']=='Evie Shen':row.update(name='Yilin (Evie) Shen',aliases=['Evie Shen'],corroborating_sources=[dict(url=cv['url'],sha256=cv['sha256'],quote='Yilin (Evie) Shen, Illinois ECE')],identity_review='Explicit CV nickname supplies full given name within same PI lab; retain owned-web EvieShen literal as alias, no guessed expansion.')
 if row['pi']==p and row['name']=='Dylan Meeks':row['aliases']=['Dylan C. Meeks']
q=section(cv,'Minh Sy Quang Truong','Awards: Apple');hold(p,cv,'Minh Sy Quang Truong',q.strip(),'CMUPhDcoadvising is explicit, but the Illinois episode is explicitly visiting researcher. That own title does not establish visiting-student status underR-STU17/19; hold UIUCstudent admission pending student-role proof.')
q=section(cv,'Illinois Visiting Researchers','CMU Master’s Researchers');a=q.index('Sungjun Cho');frag=q[a:q.index(')',a)+1];emit(p,cv,'visiting','Sungjun Cho',frag,2025,True,heading='Illinois Visiting Researchers',relationship='membership',note='Explicit visiting PhDstudent fromPOSTECH2024–25; visiting membership only, not UIUCdoctoral advising.')
a=q.index('Dylan C. Meeks');frag=q[a:q.index(')',a)+1];emit(p,cv,'visiting','Dylan C. Meeks',frag,2025,True,canonical='Dylan Meeks',heading='Illinois Visiting Researchers',relationship='membership',note='Explicit NSFREU BSstudent fromUTAustin2025; same person now currentIllinoisPhD, not another identity.')
# A distinct MSstage in the mixed historical roster cannot be dated/scoped from a prior CMU UGepisode.
q=section(s,"Non-Thesis Master's Alumni","Bachelor's Alumni");hold(p,s,'Deanyone Su',q,'MSalumni entry withoutcampus/date; CV only establishes a CMUundergraduate2019–21episode for thisname. No UIUCMSepisode inferred.')
excluded[p]=['All CVexplicitCMU-only graduate, undergraduate, intern andmentoring episodes, even2022–23afterPIUIUCmove: not UIUCmembership without continuedepisodeproof.','All postdocs and committee-onlystudents: not students/advising evidence.','MoldirNakibayeva seniorlecturer andArjunTyagi post-baccalaureate visitor episode: no explicit studentrole; retain Arjun currentPhD separately.']
# Vlasov: graduate section is generic; preceding BS/MScredentials do not type current degree.
p='Yurii Vlasov';s=src(p,'integratedneurotech.com/members');al=src(p,'integratedneurotech.com/alumni')
many(p,s,'graduate','Nolan Cummins|Iliana Raquel Minervini Vega|Alex G. Armstrong|Garima Gupta|Miles Guo|Jacky Xiang|Henry Yi|Suyang Zhang','Group members Graduate students','Undergraduate students')
items=[('Akshit Mahajan','masters',2025),('Hrishikesh Thyagarajan Iyer','phd',2025),('Yu Ding','phd',2024),('Weihua Shi','phd',2024),('Christopher Kenji Brenden','phd',2024),('Yan Zhang','phd',2021),('Colin Graber','phd',2021),('Kun Hu','masters',2023),('Prasoon Jha','masters',2020),('Yifei Yan','masters',2019),('Ari Esters','masters',2018),('Oscar Bi','masters',2018)]
q=section(al,'Graduate students','Undergraduate students')
for i,(n,r,y)in enumerate(items):
 a=q.index(n);end=q.index(items[i+1][0],a)if i+1<len(items)else len(q);frag=q[a:end].split('First Job:')[0].split('Job:')[0].strip();emit(p,al,r,n,frag,y,True,heading='Graduate students',relationship='membership')
ug=[('Heeran Yang',2025),('Alexander Lee',2024),('Chengyuan Peng',2025),('Nur Al-Kodmany',2023),('Kathleen Ferreira',2020),('Alyssa Licudine',2020)];q=section(al,'Undergraduate students','Summer interns')
for i,(n,y)in enumerate(ug):
 a=q.index(n);end=q.index(ug[i+1][0],a)if i+1<len(ug)else len(q);frag=q[a:end].split('Job:')[0].strip();emit(p,al,'undergraduate',n,frag,y,True,heading='Undergraduate students',relationship='membership')
q=section(al,'Summer interns','Previous group members at IBM')
for n in ['Xingyu Chen','Yuan Zhu']:
 a=q.index(n);frag=q[a:q.index('2017',a)+4];emit(p,al,'student intern',n,frag,alumni=True,heading='Summer interns',relationship='membership',note='Undated UIUCsummerresearchintern; BS/MSyears are education credentials, not internship dates. UIUCgroup established2016 so episode fallswithin2016–2026; noPhDadvising or exactinternshipyear inferred.')
proof=src(p,'siebelschool');pq=section(proof,'Prior to joining the UIUC in 2016','where he led')
for row in new:
 if row['pi']==p and row['name']in['Xingyu Chen','Yuan Zhu']:
  row['corroborating_sources']=[dict(url=proof['url'],sha256=proof['sha256'],quote=pq)]
excluded[p]=['DrRyanLoh andDrSunghoKim: postdoctoral scientists.','All previousIBMgroupmembers: prior workplace/postdocs, not UIUCstudents.']
# Hsiao-Wecksler: all three dated alumni tables, plus current students; MFA retained literally.
p='Elizabeth T. Hsiao-Wecksler';s=src(p,'/people/');al=next(x for x in dates if x['url']=='https://hdcl.mechanical.illinois.edu/alumni/');raw=Path(al['body_path']).read_bytes();soup=BeautifulSoup(raw,'html.parser')
for n in ['Evelyn Ochoa Arias','Linh Dao','Tim Han','Yixiao Liu','Marshall Tenzer']:
 a=text(s).index(n);frag=text(s)[a:a+150];emit(p,s,'phd',n,frag,heading='Graduate Students')
for n in ['Diane Gonzalez','Aleksandr Kim']:
 a=text(s).index(n);frag=text(s)[a:a+135];emit(p,s,'masters',n,frag,heading='Graduate Students')
many(p,s,'undergraduate','Melissa Fialek|Kaitlyn Jenison|Dominik Kozbiel|Peter Oh|Ivy Yoon','Undergraduate Students','Human Dynamics and Controls Lab 2204',relationship='membership')
for table,role,heading in zip(soup.find_all('table'),['phd','masters','undergraduate'],['PhD Alumni','MS Alumni','Undergraduate Alumni']):
 for tr in table.find_all('tr')[1:]:
  cols=[' '.join(td.get_text(' ',strip=True).split())for td in tr.find_all(['td','th'])]
  if len(cols)<2:continue
  yrs=[int(y)for y in re.findall(r'20\d\d',cols[1])]
  if not yrs or max(yrs)<2016:continue
  literal=cols[0];n=re.split(r' \((?:Manuel|SungWoo|Katie|Joao|William|Girish|Anthropology|Industrial Design|MS Health Technology)',literal)[0];q=' '.join(' '.join(cols).split());assert q in text(al)
  emit(p,al,role,n,q,max(yrs),True,heading=heading,degree_detail='MFA'if 'MFA'in literal else ('MS Health Technology'if 'MS Health Technology'in literal else role),note='Explicit dated alumni/student research table. Anticipated2017 forAlanGaglio is source expectation, not confirmed degree completion; EmilyMatijevich2014–16 retains only in-window2016episode.',relationship='membership'if role=='undergraduate'else 'advising')
  if 'anticipated'in cols[1]:new[-1]['years_basis']='Source expected graduation2017; this is a dated student observation, not a confirmed completion date.'
q=section(al,'Non-Independent Study Undergraduate Alumni','Human Dynamics and Controls Lab 2204');sp=BeautifulSoup(raw,'html.parser');heading=next(h for h in sp.find_all(['h1','h2','h3','h4'])if h.get_text(' ',strip=True)=='Non-Independent Study Undergraduate Alumni');container=heading.find_next('p');names=container.get_text('\n',strip=True).splitlines()if container else []
assert len(names)>30,('non-independent-study roster parsing',names)
for n in names:hold(p,al,n,n,'Undated non-independent-study undergraduate research alumnus; lab predates2016. Dates of another role/person do not date this undergraduate episode.')
excluded[p]=['All explicitly pre2016 PhD/MS/undergraduate episodes outsidewindow.','Post-graduation MDstudies, postdocs or placements do not create new student roles with thisPI.']
# Preserve previous58 reviewed PIgroups, append these ten.
counts={pi:len({x['name']for x in new if x['pi']==pi})for pi in dict.fromkeys(x['pi']for x in new)};assert len(counts)==10,counts
from pihier.links import student_role_ok
baseline=json.loads((RUN/'restored-before-students/students.json').read_text());before={p:sum(student_role_ok(x)for x in baseline.get(p,[]))for p in counts}
for pi in counts:
 assert not any(x['pi']==pi for x in records),pi
 rec=dict(pi=pi,reviewed_on='2026-11-24',review='Full available owned student/current/alumni/advising inventory manually reviewed for2016–2026. Earlier-school-only, staff/postdoc andcommittee-only entries excluded; unresolved school/date/role/identity observations retained separately. Completeness is limited to available reviewed public sources.',students=[{k:v for k,v in x.items()if k!='pi'}for x in new if x['pi']==pi])
 if pi in holds:rec['unresolved_students']=holds[pi]
 records.append(rec)
(WT/'hierarchy/uiuc/reviewed/few-students-evidence.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
review=dict(session='codex-uiuc-students50-1124',date='2026-11-24',counts=counts,before_counts=before,net_new_memberships=sum(counts.values())-sum(before.values()),source_rows=len(new),held_observations=holds,exclusions=excluded,scope='Complete eligible named students in available reviewed public sources,2016–2026; unresolved observations do not establish real-world absence.')
(OUT/'roster-review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n');(OUT/'sources.json').write_text(json.dumps({p:manifest[p]for p in counts},indent=2)+'\n');(OUT/'date-sources.json').write_text(json.dumps(dates,indent=2)+'\n');(RUN/'expected-students.json').write_text(json.dumps({p:sorted({x['name']for x in new if x['pi']==p})for p in counts},indent=2)+'\n');print(counts,'population',sum(counts.values()),'netnew',review['net_new_memberships'],'rows',len(new),'holds',sum(map(len,holds.values())))
