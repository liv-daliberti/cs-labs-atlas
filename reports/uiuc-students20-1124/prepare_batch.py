import hashlib,json,subprocess
from pathlib import Path
from bs4 import BeautifulSoup
import atlas_paths as P
RUN=P.SCRATCH/'uiuc-students20-1124';WT=P.ROOT/'worktrees/uiuc-students20-1124';OUT=WT/'reports/uiuc-students20-1124';OUT.mkdir(parents=True,exist_ok=True)
manifest=json.loads((RUN/'sources.json').read_text());dates=json.loads((RUN/'date-source-results.json').read_text())+json.loads((RUN/'extra-source-results.json').read_text()); records=json.loads(subprocess.check_output(['git','-C',str(WT),'show','8214a140a2a9364fd498fc7ac5c850ce9b56d298:hierarchy/uiuc/reviewed/few-students-evidence.json'],text=True));new=[];reviews=[]
def src(pi,needle):return next(x for x in manifest[pi]+dates if needle in x['url'])
def text(s):
 b=Path(s['body_path']).read_bytes();assert hashlib.sha256(b).hexdigest()==s['sha256']
 if b.startswith(b'%PDF'):return Path(s['text_path']).read_text()
 soup=BeautifulSoup(b,'html.parser')
 for e in soup(['script','style','noscript']):e.decompose()
 return ' '.join(soup.get_text(' ',strip=True).split())
def block(s,start,end):
 t=text(s);a=t.index(start);b=t.index(end,a+len(start)) if end else len(t);return t[a:b].strip()
def add(pi,s,role,names,start,end,alumni=False,year=None,note='',proof=None):
 q=block(s,start,end)
 for name in names.split('|'):
  assert name in q,(pi,name,q)
  row=dict(name=name,role=role,years=[year,year] if year else ([2026,2026] if not alumni else None),years_basis='explicit dated source' if year else ('capture observation only; no earlier membership years inferred' if not alumni else 'undated UIUC lab alumni; membership year unresolved; UIUC-only lab and PI education/appointment place possible membership wholly in 2016–2026'),alumni=alumni,section=start,url=s['url'],observed=s['observed'],sha256=s['sha256'],quote=q,rule='R-STU-01',reviewed_by='codex-uiuc-students20-1124',reviewed=True,auto=False,note=note or 'Whole owned roster manually reviewed, with degree headings and campus scope; source membership is not inferred from coauthorship.')
  if proof:
   ps,pq=proof;assert pq in text(ps);row['corroborating_sources']=[dict(url=ps['url'],sha256=ps['sha256'],quote=pq)]
  new.append(dict(pi=pi,**row))
 reviews.append(dict(pi=pi,url=s['url'],sha256=s['sha256'],section=start,role=role,names=names.split('|'),alumni=alumni))
p='Bin Hu';s=src(p,'people.html');add(p,s,'phd','Xingang Guo|Zichen Wang|Yicheng He','Phd Students','Master Students');add(p,s,'masters','Po-Jen Ko|Zhuoer Zhang','Master Students','Alumni');prof=src(p,'siebelschool');add(p,s,'alumnus','Aaron Joseph Havens|Usman Ahmed Syed|Darioush Keivan Esfahani','Alumni',None,alumni=True,proof=(prof,'Education Ph.D. in Aerospace Engineering and Mechanics, University of Minnesota, 2016'))
p='Francis Yan';s=src(p,'/students');cv=src(p,'fyy-cv.pdf');proof=(cv,block(cv,'Former students at UIUC','Former students at Microsoft Research'));add(p,s,'phd','Eric Xiang Gao|Zhan Jin|Han-Ting Liang|Seoyul Oh|Yinjie Zhao','Ph.D. students','Master’s students');add(p,s,'masters','Nikhil Chandrasekar|Chris Chen|Chan Ju (Martin) Chong|Keyuan Hu|Xiayang Jin|Will Kung|Yu-An (Ann) Lai|Ang Li|Tianyi Zhong','Master’s students','Undergraduate students');add(p,s,'undergraduate','Yiqi Mei','Undergraduate students','Alumni');add(p,s,'visiting','Yuxuan Tang','Yuxuan Tang','Alumni');add(p,s,'masters','Anya Gill|Jiajun Ruan','Alumni (with publications','Luke Hsiao',alumni=True,proof=proof);add(p,s,'undergraduate','Luke Hsiao|Ian Zhang|William Zheng','Luke Hsiao','Microsoft Research Redmond',alumni=True,proof=proof);add(p,s,'visiting','Kai Luo|Yikai Zheng','Luke Hsiao','Microsoft Research Redmond',alumni=True,proof=proof)
p='Radhika Mittal';s=src(p,'radhikam.web');
for nm,yr in [('Yongzhou Chen',2025),('Ammar Tahir',2026)]:add(p,s,'phd',nm,'Students PhD students','MS students',alumni=True,year=yr)
add(p,s,'phd','Sachin Ashok|Taimoor Tariq|Talha Waheed|Eashan Gupta','Students PhD students','MS students')
for nm,yr in [('Aditi Partap',2021),('Ruihao Yao',2022),('Eashan Gupta',2023),('Ananya Kommalapati',2026)]:add(p,s,'masters',nm,'MS students','If you are interested',alumni=True,year=yr)
p='Shenlong Wang';s=src(p,'illinois.edu/');old=src(p,'group.html');cv=src(p,'Fall2025.pdf');proof=(cv,block(cv,'Employment','Research Scientist'));add(p,s,'phd','Tianhang Cheng|Hanxiao Jiang|Chih-Hao Lin|Jing Wen|Hongchi Xia|Albert J. Zhai|Hao-Yu Hsu|Quincy Yu|Yuqun Wu|Gloria Wang','Group Members','Past members:');add(p,s,'masters','Henry Che','Group Members','Past members:');add(p,s,'visiting','Jingxuan Zhang','Group Members','Past members:');add(p,old,'phd','Shaowei Liu|Vlas Zyrianov|Yuan Shen','PhD Students:','PhD Mentees:',alumni=True,proof=proof);add(p,old,'phd','Jason Ren|Joao Marcos Correia Marques|Jae Yong Lee','PhD Mentees:','Master Students:',alumni=True,proof=proof);add(p,old,'masters','Jason Mei|Xiyue Zhu|Bhargav Chandaka|Max Hsu|David Yao|Haozhe Chen|Tianhang Cheng','Master Students:','Visiting Students:',alumni=True,proof=proof);add(p,old,'visiting','Zhi-Hao Lin|Yuefan Wu|Zeyuan Chen|Qianfan Chen|Ziyu Zhu|Xiaoxue Chen|Boyuan Chen|Hongchi Xia|Li Yuan','Visiting Students:','Undergraduate Students:',alumni=True,proof=proof);add(p,old,'undergraduate','Sydney Yu|Ryan Wolf|Niviru Wijayaratne|Bhargav Chandaka','Undergraduate Students:','Interns and Mentees before Joining UIUC:',alumni=True,proof=proof)
p='Jugal Garg';s=src(p,'jugal.ise');add(p,s,'phd','Eklavya Sharma|John Qin|Yuang (Eric) Shen','PhD Students','Pooja Kulkarni');
for nm,yr in [('Pooja Kulkarni',2025),('Aniket Murhekar',2025),('Setareh Taki',2022),('Peter McGlaughlin',2021),('Timothy Murray',2020)]:add(p,s,'phd',nm,'PhD Students','Selected Publications',alumni=True,year=yr)
p='Yupeng Zhang';s=src(p,'student.html');cv=src(p,'zhangyp.web.illinois.edu/CV.pdf');proof=(cv,block(cv,'Professional University of Illinois','Texas A&M University'));add(p,s,'phd','Pariya Akhiani|Tianyu Zhang|Yupeng Ouyang|Zhongjing Wei|Tianyi Liu','PhD Students','Alumni');add(p,s,'phd','Zhiyong Fang|Wenxuan Wu','Alumni','Mentoring',alumni=True,year=2025,proof=proof);add(p,s,'student','Ruofan Xu','Ruofan Xu','Master Students',alumni=True,year=2024);add(p,cv,'masters','Taoran Li','– Taoran Li (Fall 2024)','Undergraduate Students',alumni=True,year=2024)
for nm,yr in [('Tianyu Zhang',2024),('Shen Dong',2024),('Qi Wu',2024),('Yupeng Ouyang',2024),('Daniel Vilardell',2023)]:add(p,s,'undergraduate',nm,'Undergraduate Students','Hanson Yu',alumni=True,year=yr,proof=proof)
p='Bhaskar Ray Chaudhury';s=src(p,'bhaskarraychaudhury.com/');add(p,s,'phd','Jiaxin Song|Yuanchen Tang','PhD Students','Recent News')
p='Minjia Zhang';s=src(p,'supercomputing-system-ai-lab.github.io/');proof=(s,'[1/16/2024] Minjia officially joined UIUC!');add(p,s,'phd','Xinyu Lian|Haochen Shen|Ahan Gupta|Jiahuan Yu|Hsu-Tzu Ting|Zheng Wang|Haoyang Zhang|Chenghao Mo|Zixian Wang','Xinyu Lian Ph.D Student','Jiankun Wang MS Student');add(p,s,'masters','Jiankun Wang|Kaidi Fu|Wangjia Zhan|Banghao Chi|Aditi Ahuja|Chengyi Wang','Jiankun Wang MS Student','Alumi');add(p,s,'masters','Akshat Sharma|Xiao Wang|Neel Dani|Jianping Li|Yueming Yuan|Zelei Shao|Hongbo Zheng|Kartik Ramesh|Mingtao Hu','Alumi','Yiming Gong',alumni=True,proof=proof);add(p,s,'undergraduate','Yiming Gong','Yiming Gong','Interns (over 6 months)',alumni=True,proof=proof)
add(p,s,'intern','Zheng Wang|Mengjue Tan|Yuyi Ao|Banghao Chi|Beichen Huang|Shihan Lin|Tong Wei|Xingru Lu|Eddie Gao|Wendi Wang|Hangliang Ding|Lemin Zhang|Wangjia Zhan|Chengyi Wang','Interns (over 6 months)','Past Interns and Advised Students',alumni=True,year=2024)
add(p,s,'intern','Prajwal Hegde|Jacob Xianyu','Interns (over 6 months)','Past Interns and Advised Students',alumni=True,year=2025);add(p,s,'intern','Hoa La','Interns (over 6 months)','Past Interns and Advised Students',note='Source states Summer2024 open interval; use current capture observation only, not an invented end of internship.')
p='Koustuv Saha';s=src(p,'oncare.cs.illinois.edu/people/');cv=src(p,'KoustuvSahaCV.pdf');proof=(cv,'Advising and Mentorship At UIUC 2023– PhD Advisees.')
# One paragraph per member: role and campus context come from the whole owned roster.
soup=BeautifulSoup(Path(s['body_path']).read_bytes(),'html.parser')
for par in soup.find_all('p'):
 strong=par.find('strong');h=par.find_previous('h2')
 if not strong or not h or h.get_text(strip=True) not in ['Current Students','Alumni']:continue
 name=strong.get_text(' ',strip=True);q=' '.join(par.get_text(' ',strip=True).split())
 if name=='Yunhao Yuan':continue  # Explicit visiting researcher, not visiting student.
 role='phd' if 'PhD' in q else ('masters' if 'MS' in q else 'undergraduate')
 add(p,s,role,name,q,None,alumni=h.get_text(strip=True)=='Alumni',proof=proof)
 # Narrow each record to its actual card; the full section was reviewed separately.
 new[-1]['quote']=q;new[-1]['relationship']='membership'
 if name in ['Yuqi Liu','Jash Rajesh Parekh','Niharika Bhattacharjee']:
  alt='undergraduate' if role!='undergraduate' else 'masters';row=dict(new[-1]);row['role']=alt;new.append(row)
for nm,yr in [('Shreya Haran',2025),('Samiha Thatikonda',2025),('Jake Crawmer',2024),('Michelle Hernandez',2024),('Urvi Banerjee',2026),('Shouhan Kar',2026)]:
 add(p,cv,'student',nm,'2023— High School Students.','2023— Other Student',alumni=True,year=yr);new[-1].update(relationship='membership',role_detail='high_school',note='Explicit high-school research student named in UIUC mentoring section; student lab membership only, no faculty advising claim.')
# Prior UIUC degree episodes explicitly documented in the CV, on existing roster identities.
for nm,role,yr,start,end in [('Veda Duddu','masters',2026,'Graduate Students.','Undergraduate Students.'),('Yueshen Li','masters',2026,'Graduate Students.','Undergraduate Students.'),('Soorya Shimgekar','masters',2024,'Graduate Students.','Undergraduate Students.'),('Melissa Shi','undergraduate',2025,'Undergraduate Students.','High School Students.'),('Andy Mao','undergraduate',2025,'Undergraduate Students.','High School Students.')]:add(p,cv,role,nm,start,end,alumni=True,year=yr)
p='Shenlong Wang';cv=src(p,'Fall2025.pdf')
for nm,yr in [('Runzhao Huang',2024),('Naina Singh',2024),('Anna Shukhter',2024),('Ansh Sharma',2024),('Albert Xiao',2024),('Praneet Rathi',2024),('Rohit Kundu',2024),('Emily Chen',2023)]:add(p,cv,'undergraduate',nm,'Current and Past Student Interns since joining UIUC:','Past Interns/Residents before joining UIUC:',alumni=True,year=yr)
add(p,cv,'student','Michael Meng','Current and Past Student Interns since joining UIUC:','Past Interns/Residents before joining UIUC:',alumni=True,year=2024);new[-1].update(relationship='membership',role_detail='high_school_intern')
for nm,yr in [('Gloria Wang',2023),('Henry Che',2023),('Hongchi Xia',2024),('Tianhang Cheng',2023),('Xiyue Zhu',2023),('Boyuan Chen',2024),('Zeyuan Chen',2022)]:add(p,cv,'undergraduate',nm,'Current and Past Student Interns since joining UIUC:','Past Interns/Residents before joining UIUC:',alumni=True,year=yr);new[-1]['relationship']='membership'
for nm,yr in [('Shaowei Liu',2021),('Yuan Shen',2021),('Vlas Zyrianov',2021),('Zhi-Hao Lin',2022),('Jing Wen',2022),('Albert Zhai',2022),('Hanxiao Jiang',2023),('Hongchi Xia',2024),('Tianhang Cheng',2024)]:
 add(p,cv,'phd',nm,'Mentorship • Current Students:','• Current and Past Student Interns')
 new[-1].update(years=[yr,None],years_basis='Literal CV start–present interval retained with open end; no capture-year endpoint inferred')
 if nm=='Albert Zhai':new[-1].update(name='Albert J. Zhai',aliases=['Albert Zhai'],identity_review='Same unique Albert Zhai in PI-owned PhD roster and CV, with optional middle initial in current roster.')
# Resolve surname/given-name order with the student's own named PI and ZJU education.
identity=json.loads((RUN/'identity-source-results.json').read_text());dates.extend(identity);own=next(x for x in identity if 'y-u-a-n-l-i' in x['url'])
add(p,cv,'visiting','Yuan Li','Current and Past Student Interns since joining UIUC:','Past Interns/Residents before joining UIUC:',alumni=True,year=2022)
new[-1].update(name='Li Yuan',aliases=['Yuan Li'],identity_review='Chinese surname/given-name order reversal on PI alumni page versus CV. Both name token pair, BS atZJU, UIUC studentintern context; own YuanLi page confirms ZJU BEng2023, laterZJU masters, and undergraduate internship advised byShenlongWang atUIUC. Future degree destinations on olderPIsources differ; do not infer PhDdegreeatZJU.',relationship='membership')
new[-1]['corroborating_sources']=[dict(url=own['url'],sha256=own['sha256'],quote=block(own,'My name is Yuan Li','My research interests'))]
p='Elahe Soltanaghai';rendered=json.loads((RUN/'render-source-results.json').read_text())[0];dates.append(rendered);s=rendered;old=src(p,'elahe.web.illinois.edu/');add(p,s,'phd','Saif Ur Rahman|Mingyue Tang|Luke Jacobs|Parham Chavoshian|Anton Dmitriev|Rafid Umayer Murshed|Soham Chakraborty','Team Elahé Soltanaghai','Alumni');add(p,s,'masters','Ansley Tsai|Qinglin (Gloria) Ge','Team Elahé Soltanaghai','Alumni')
soup=BeautifulSoup(Path(s['body_path']).read_bytes(),'html.parser')
for box in soup.select('div.MuiBox-root.css-hpgf8j'):
 ps=box.find_all('p',recursive=False)
 if len(ps)!=2:continue
 name=ps[0].get_text(' ',strip=True);desc=ps[1].get_text(' ',strip=True);q=' '.join(box.get_text(' ',strip=True).split());role='student' if 'high school' in desc.lower() else ('undergraduate' if 'BS ' in desc or 'Undergrad' in desc else 'masters')
 add(p,s,role,name,q,None,alumni=True);new[-1]['quote']=q;new[-1]['relationship']='membership';new[-1]['years_basis']='undated alumni in explicitly UIUC-only iSENS lab; exact years unresolved; corroborated by lab news announcing newPhD and professor award2022';new[-1]['years']=None
 if role=='student':new[-1]['role_detail']='high_school_intern'
# A still-listed undergraduate omitted from rendered alumni/current cards.
add(p,old,'undergraduate','Alex Shaffer','Undergraduate Students:','High School Students:')
add(p,old,'undergraduate','Ansley Tsai','Undergraduate Students:','High School Students:',alumni=True);new[-1]['note']='Earlier undergraduate role and rendered currentMS role retained separately; no enrollment date inferred.'
add(p,old,'undergraduate','Sam Hurh','Undergraduate Students:','High School Students:',alumni=True);new[-1].update(name='Samuel Hurh',aliases=['Sam Hurh'],identity_review='Same owned iSENS roster; conventional Sam/Samuel given-name expansion, identical rare surname; old undergraduate/new MCS episodes retained on one person.')
for row in new:
 if row['pi']==p and row['name']=='Ed Wolsky':row['aliases']=['Ed Wolski']
 if row['pi']==p and row['name']=='Navid Tajkhorshid':row['aliases']=['Navid Tajkhoeshid']
# Internship source retains the literal open end rather than inventing an observation in2026.
for row in new:
 if row['pi']=='Minjia Zhang' and row['name']=='Hoa La':row.update(years=[2024,None],years_basis='literal Summer2024 open interval; only documented start, no end year inferred')
for pi in dict.fromkeys(x['pi'] for x in new):
 rec=next((x for x in records if x['pi']==pi),None)
 if rec is None:rec=dict(pi=pi,students=[]);records.append(rec)
 assert not rec['students'],(pi,'unexpected existing rows; merge manually')
 rec.update(reviewed_on='2026-11-24',review='Full available owned current/alumni rosters, linkedCVs and renderediSENS reviewed, codex-uiuc-students20-1124. Includes all supported student roles and separately dated prior degree episodes. Excludes prior-school-only mentoring, nonstudents, unsupported collaborator-only cases. Undated alumni retain unresolved years, not capture-year enrollment.')
 rec['students']=[{k:v for k,v in x.items() if k!='pi'} for x in new if x['pi']==pi]
(WT/'hierarchy/uiuc/reviewed/few-students-evidence.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
counts={pi:len({x['name'] for x in new if x['pi']==pi}) for pi in dict.fromkeys(x['pi'] for x in new)}
exclusions={'Francis Yan':['Whole Microsoft Research Redmond former-student section: prior institution, not UIUC'],'Shenlong Wang':['Interns and Mentees before Joining UIUC: explicit prior institution'],'Jugal Garg':['Vishnu V. Narayan: postdoc','Bhaskar Ray Chaudhury: postdoc'],'Yupeng Zhang':['Fatima Elsheimy MS2021–22: TexasA&M beforeUIUC','Hanson Yu2022,Yinuo Zhang2020,Weijie Wang2020,Sibo Min/Yuno Min2020,Sixing Zheng/Skyler Zheng2019: TexasA&M beforeUIUC','Jiaheng Zhang/Tiancheng Xie2018–23: UC Berkeleymentoring, noUIUCepisode established'],'Minjia Zhang':['Whole Past Interns and Advised Students (before joining UIUC): prior Microsoft Research'],'Koustuv Saha':['Yunhao Yuan: visiting researcher, degree alone does not establish visitingstudent role','Other Student Mentorship/Collaborations Han Zhang,Sidharth Kaliappan,Himanshu Rathi,Sukriti Bhardwaj: ambiguous mentoring vs collaboration; no explicit lab membership or named advising established','PhD committees: not adviser evidence','At Microsoft Research and At Georgia Tech sections: prior institutions'],'Elahe Soltanaghai':['Elahé Soltanaghai: PI','Milo Alipurr: labpet, not student']}
(OUT/'roster-review.json').write_text(json.dumps(dict(session='codex-uiuc-students20-1124',date='2026-11-24',scope='Complete eligible named students in reviewed available current/alumni sources,2016–2026, including CV and JavaScript roster. Does not assert completeness for unlisted people or shorter internships the source omits.',sections=reviews,counts=counts,source_rows=len(new),exclusions=exclusions,identity_reviews={'Shenlong Wang':{'Yuan Li / Li Yuan':'Chinese name-order variant supported by own named UIUC mentor + ZJU education; older future-degree plans not promoted as degrees','Zhi-Hao Lin / Chih-Hao Lin':'Distinct individuals with distinct personalpage URLs; kept separate','Albert Zhai / Albert J. Zhai':'Optional middle initial, same unique PI-owned PhD roster'},'Elahe Soltanaghai':{'Sam Hurh / Samuel Hurh':'Conventional given-name expansion in samePIownedlab; retain undergraduate andMCS sourceepisodes, oneperson','Ed Wolski / Ed Wolsky':'SamePIownedlab MS roster, finalvowelvariant; canonical renderedspelling','Navid Tajkhoeshid / Navid Tajkhorshid':'SamePIownedlab undergraduate roster, internalvoweltypo; canonicalrenderedspelling'},'Koustuv Saha':{'Aryan Kapadia / Aryan Ramchandra Kapadia':'Shorter currentlabname; do not add CV fullername as anotherstudent','Ross Kimme / Ross Kimne':'Prefer latestpeoplepagelinkedrosskimme.com; no duplicateCVtypo','Souradeep Pal / Souradeep Pal':'Same name; no duplicate'}}),ensure_ascii=False,indent=2)+'\n')
# Keep the finite ten-PI inventory plus each fetched/rendered source used in this review.
m={k:v for k,v in manifest.items() if k in counts}
for pi,needle in [('Minjia Zhang','supercomputing-system-ai'),('Koustuv Saha','oncare.cs.illinois.edu/people/'),('Elahe Soltanaghai','https://isens.cs.illinois.edu/')]:m[pi].extend([x for x in dates if needle in x['url']])
(OUT/'sources.json').write_text(json.dumps(m,indent=2)+'\n');(OUT/'date-sources.json').write_text(json.dumps(dates,indent=2)+'\n')
(RUN/'expected-students.json').write_text(json.dumps({pi:sorted({x['name'] for x in new if x['pi']==pi}) for pi in counts},indent=2)+'\n')
print('Student-lab pairs:',sum(counts.values()),'source rows:',len(new));print(counts)
