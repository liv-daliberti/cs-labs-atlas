import hashlib,json,re,subprocess
from pathlib import Path
from bs4 import BeautifulSoup
import atlas_paths as P
RUN=P.SCRATCH/'uiuc-students30-1124';WT=P.ROOT/'worktrees/uiuc-students30-1124';OUT=WT/'reports/uiuc-students30-1124';OUT.mkdir(parents=True,exist_ok=True)
manifest=json.loads((RUN/'sources.json').read_text());dates=[]
for fn in ['extra-source-results.json','linked-source-results.json','cv-source-results.json','navigation-source-results.json','render-source-results.json','team-source-results.json']:
 if (RUN/fn).exists():dates.extend(x for x in json.loads((RUN/fn).read_text()) if x.get('body_path'))
records=json.loads(subprocess.check_output(['git','-C',str(WT),'show','eafc863aec2241862875a528ab0b03b9e381a259:hierarchy/uiuc/reviewed/few-students-evidence.json'],text=True));new=[];reviews=[]
def src(pi,needle):return next(x for x in manifest[pi]+dates if needle.rstrip('/') in x['url'] and x.get('body_path'))
def text(s):
 b=Path(s['body_path']).read_bytes();assert hashlib.sha256(b).hexdigest()==s['sha256']
 if b.startswith(b'%PDF'):return Path(s['text_path']).read_text()
 if s['url'].endswith(('.js','.json')):return ' '.join(b.decode('utf-8').split())
 soup=BeautifulSoup(b,'html.parser')
 for e in soup(['script','style','noscript']):e.decompose()
 return ' '.join(soup.get_text(' ',strip=True).split())
def block(s,start,end):
 t=text(s);a=t.index(start);b=t.index(end,a+len(start)) if end else len(t);return t[a:b].strip()
def add(pi,s,role,names,start,end,alumni=False,year=None,note='',proof=None):
 q=block(s,start,end)
 for name in names.split('|'):
  assert name in q,(pi,name,q)
  row=dict(name=name,role=role,years=[year,year] if year else ([2026,2026] if not alumni else None),years_basis='explicit dated source' if year else ('capture observation only; no earlier membership years inferred' if not alumni else 'undated UIUC lab alumni; membership year unresolved; UIUC-only lab and PI education/appointment place possible membership wholly in 2016–2026'),alumni=alumni,section=start,url=s['url'],observed=s['observed'],sha256=s['sha256'],quote=q,rule='R-STU-01',reviewed_by='codex-uiuc-students30-1124',reviewed=True,auto=False,note=note or 'Whole owned roster manually reviewed, with degree headings and campus scope; source membership is not inferred from coauthorship.')
  if proof:
   ps,pq=proof;assert pq in text(ps);row['corroborating_sources']=[dict(url=ps['url'],sha256=ps['sha256'],quote=pq)]
  new.append(dict(pi=pi,**row))
 reviews.append(dict(pi=pi,url=s['url'],sha256=s['sha256'],section=start,role=role,names=names.split('|'),alumni=alumni))
p='Yunzong Xu';s=src(p,'yunzongxu.github.io/');add(p,s,'phd','Hao Liang|Boxuan Zhou|Anthony Pineci|Cheng Tang|Shunri Zheng','Doctoral Thesis Research Advising','Undergraduate Research Advising',note='Current doctoral advisees observed2026. HaoLiang statedadvisingstart2023 predatesPIUIUC2024; noUIUC2023episodeinferred.');add(p,s,'undergraduate','Qiushi Han','Undergraduate Research Advising','Zhangyi Liu',alumni=True,year=2025);add(p,s,'undergraduate','Zhangyi Liu','Zhangyi Liu','Besides,',alumni=True,year=2026)
p='Abdussalam Alawini';s=src(p,'alawini.web.illinois.edu/');add(p,s,'phd','Abdulrahman Alrabah','Current Students:','Undergraduate Students:');add(p,s,'masters','Xing Gao','Current Students:','Undergraduate Students:');add(p,s,'undergraduate','Nikhil Khandekar|Rishabh Jain|Tom Reichel','Undergraduate Students:','Past Graduate Students:');proof=(s,block(s,'Biography','Current Students:'));add(p,s,'phd','Fareedah Alsaad|Sophia Yang','Past Graduate Students:','Undergraduate Students:',alumni=True,proof=proof);add(p,s,'masters','Matthew C Weston|Abdulrahman Alrabah','Past Graduate Students:','Undergraduate Students:',alumni=True,proof=proof);q=block(s,'Past Graduate Students:','1 + Undergraduate');q=q[q.index('Undergraduate Students:'):]
add(p,s,'undergraduate','Mei Chen|Ridha Alkhabaz|Rohit Narayanan',q,None,alumni=True,proof=proof)
for row in new:
 if row['pi']==p and row['name']in['Mei Chen','Ridha Alkhabaz','Rohit Narayanan']:row['quote']=q
p='Huy T. Tran';s=src(p,'/team');cv=src(p,'huy-cv.pdf');add(p,s,'phd','Jaye Heglund|Rupal Nigam|Miki Yuasa|Niket Parikh|MJ (Minjae) Cho|Rio Futagawa','Graduate Students','Alumni');add(p,s,'masters','Miki Yuasa','Miki Yuasa Miki is','Visit Miki Yuasa')
for nm,yr in [('Karl Thompson',2019),('Keshav Chandramouleeswaran',2018),('Neale Van Stralen',2020),('Walker Dimon',2022)]:add(p,s,'masters',nm,'Alumni','Email us',alumni=True,year=yr)
add(p,cv,'phd','H. Osooli','Student Advising Graduate Students','Alumni');new[-1].update(years=[2024,None],years_basis='literal CV PhD2024 open end',source_record_key='huy-tran:cv-graduate:h-osooli',note='CV supplies initial only; source-scoped identity, no borrowed full name.')
add(p,cv,'masters','J. Heglund','Alumni W. Dimon','Undergraduate Students through Research Programs',alumni=True,year=2020);new[-1].update(name='Jaye Heglund',aliases=['J. Heglund'],identity_review='Same rare surname and initial in same PI-owned currentPhD/datedMS roster, with MS placement atUIUC asPhDstudent.')
for nm,yr in [('A. Rihani',2021),('A. Arora',2023),('L. Lalumandier',2022),('B. Cadee',2022),('V. Thatte',2022),('P. Baffoe',2022),('O. Upalekar',2022),('S. Vazhathodiyil',2024),('S. Bangaru',2020),('S. Sharma',2020),('A. Jain',2019),('A. Sehgal',2020),('J. Xue',2019),('D. Mulye',2019),('D. Yang',2019)]:
 add(p,cv,'undergraduate',nm,'Undergraduate Students through Research Programs','Doctoral Committees',alumni=True,year=yr)
 new[-1].update(relationship='membership',source_record_key='huy-tran:cv-undergraduate:'+nm.lower().replace(' ','').replace('.',''),note='Named undergraduate research participant in PI-owned CV; preserve literal initials, with source-scoped identity. Class enrollment alone is not the basis; the CV identifies individual research-program advisees.')
p='Halil Kilicoglu';s=src(p,'/lab');cv=src(p,'kilicoglu-cv.pdf')
# Dated advisor fields supersede stale current-student headings; no future graduation dates invented.
for nm,yr in [('Linh Hoang',2022),('Janina Sarol',2025),('Yingjun Guan',2023),('Lan Jiang',2026),('Morgan Lundy',2022),('Haoyang Liu',2022)]:add(p,cv,'phd',nm,'Doctoral Students, advisor','Doctoral Students, committee member',alumni=True,year=yr)
add(p,s,'phd','Mengfei Lan|Shufan Ming|Gibong Hong|Evan Guerra|Joe Menke|Yikun Han|Shiwei Liu','members of the scienceNLP lab','© Copyright')
add(p,cv,'phd','Joe D Menke','Doctoral Students, advisor','Doctoral Students, committee member');new[-1].update(name='Joe Menke',aliases=['Joe D Menke'],identity_review='Same unique Menke PhD in PI-owned lab and CV; optional middle initial D.')
for nm,yr in [('Lan Li',2020),('Nadine Veasley',2023),('Jerome You',2024)]:add(p,cv,'phd',nm,'Doctoral Students, project supervisor','Master’s Students, project supervisor',alumni=True,year=yr);new[-1]['relationship']='membership'
for nm,yr in [('Gaozheng Liu',2019),('Aditya Chanodia',2020),('Sahil Wadhwa',2020),('Mengfei Lan',2020),('Yasaswi Boyapati',2021),('Isaac Joy',2021),('Brian Rao',2022),('Veronica Hindle',2024),('Shruthan Radhakrishna',2024),('Degaulle Dai',2023),('Sree Kodimela',2023),('Arjun Kumaran',2024),('Jainam Rajput',2025),('Shiwei Liu',2025),('Deekshita Karingula',2025),('Sylvey Lin',2025),('Jyot Buch',2026),('Aditya Ponnudurai',2026),('Atharva Satishrao Chaudhari',2026),('Aniket Tathe',2026),('Sagar Jha',2026)]:
 add(p,cv,'masters',nm,'Master’s Students, project supervisor','Undergraduate Students, project supervisor',alumni=True,year=yr);new[-1]['relationship']='membership'
for nm,yr in [('Shinka Mori',2020),('Mandy Cheng',2021),('Eugene Gurevich',2023),('Zoe Tsokolas',2023),('Sunny Lee',2023),('Jackson Song',2025),('Youbeen Oh',2025),('Sirapop (Mig) Umnakkittikul',2025),('Shawn Huang',2026)]:
 add(p,cv,'undergraduate',nm,'Undergraduate Students, project supervisor','SERVICE',alumni=True,year=yr);new[-1]['relationship']='membership'
p='Karthekeyan Chandrasekaran';s=src(p,'karthik.ise.illinois.edu/');add(p,s,'phd','Weihao Zhu','PhD Advisees','Shubhang Kulkarni')
for nm,yr in [('Shubhang Kulkarni',2025),('Calvin Beideman',2023),('Weihang Wang',2023),('Chao Xu',2018)]:add(p,s,'phd',nm,'PhD Advisees','Masters Advisees',alumni=True,year=yr)
for nm,yr in [('Sahand Mozaffari',2021),('Ali Bibak',2020),('Victor Sui',2020)]:add(p,s,'masters',nm,'Masters Advisees','Undergrad Advisees',alumni=True,year=yr)
for nm,yr in [('Richard Bi',2025),('Soham Joshi',2025),('Aditya Pillai',2020),('Jingwen Jiang',2016)]:add(p,s,'undergraduate',nm,'Undergrad Advisees','Publications',alumni=True,year=yr)
p='Richard Y. Zhang';s=src(p,'ryz.ece.illinois.edu/');cv=src(p,'ryz_cv.pdf');add(p,s,'phd','Hong-Ming Chiu|Iven Guzel|Jing-Teng (Jeter) Hwang|Haoruo Zhang','I am advising PhD students','Alumni from my group');add(p,s,'undergraduate','Kevin Wu','I am advising PhD students','Alumni from my group');add(p,s,'phd','Gavin (Jialun) Zhang','Alumni from my group','In Fall 2026',alumni=True,year=2024);add(p,s,'masters','June Hou','Alumni from my group','In Fall 2026',alumni=True,year=2025);add(p,cv,'undergraduate','Jose Maria Sunyer Nestares','Undergraduate Thesis Advising','Teaching',alumni=True,year=2020)
p='Jian Huang';s=src(p,'platformxlab.github.io');add(p,s,'phd','Benjamin Reidys|Yuqi Xue|Shaobo Li|Yiqi Liu|Eric Zhou|Daixuan Li|Noelle Crawford|Yikang Yue|Max Bromberg|Anna Li|Jefferson Zhang|Ingi Helgason','Team Group Members','Jerry Wu');add(p,s,'masters','Jerry Wu|Kevin Chen|Rudra Thakkar|Nikita Vasilyev|Pilar Luiz','Jerry Wu MS Student','Alumni Graduated Students');add(p,s,'phd','Jinghan Sun','Alumni Graduated Students','Michael Wang',alumni=True,year=2025)
for nm,yr in [('Michael Wang',2026),('Yuan Xu',2025),('Xiaohao (David) Wang',2019),('Chance C. Coats',2019),('Yue Leng',2019)]:add(p,s,'masters',nm,'Alumni Graduated Students','Illinois PlatformX Expanding',alumni=True,year=yr)
add(p,s,'masters','Ziyan Feng','Alumni Graduated Students','Illinois PlatformX Expanding',alumni=True,year=2019);new[-1]['degree_detail']='ME'
p='Svetlana Lazebnik';s=src(p,'slazebni.cs.illinois.edu/');cv=src(p,'lana_cv.pdf');add(p,s,'phd','Dwip Dalal|Chang Liu','Ph.D. Students','Former Ph.D. Students');add(p,cv,'phd','Jay Mahajan','Mentoring Ph.D. Advisees','M.S. Advisees')
for nm,yr in [('Shivansh Patel',2026),('Aiyu Cui',2024),('Viraj Shah',2024),('Daniel McKee',2023),('Unnat Jain',2022),('Arun Mallya',2018),('Liwei Wang',2018),('Bryan Plummer',2018)]:add(p,s,'phd',nm,'Former Ph.D. Students','Former Postdocs',alumni=True,year=yr)
for nm,yr in [('Asher Mai',2025),('Nidhish Kamath',2024),('Shrey Sarswat',2024),('Nan Liu',2023),('Nikash Walia',2023),('Zitong Zhan',2023),('Xiaodan Du',2020),('Shubham Jain',2019),('Medhini Narasimhan',2019),('Jing Huang',2018),('Victor Ge',2018),('Hsiao-Ching Chang',2018),('Manav Kedia',2017)]:add(p,cv,'masters',nm,'M.S. Advisees','Ph.D. Committees',alumni=True,year=yr)
add(p,cv,'masters','Unnat Jain','Mentoring Ph.D. Advisees','M.S. Advisees',alumni=True,year=2018)
p='Katie Cunningham';s=src(p,'trailslab.web.illinois.edu/team/');cv=src(p,'KCunningham_CV_online.pdf');add(p,s,'phd','Mehmet Arif Demirtaş|Jinyoung (Jina) Hur|Joslyn Orgill|Yoshee Jain','Group Members','© 2024')
for row in new:
 if row['pi']==p and row['name']=='Jinyoung (Jina) Hur':row.update(name='Jinyoung Hur',aliases=['Jinyoung (Jina) Hur'])
 if row['pi']==p and row['name']=='Mehmet Arif Demirtaş':row['aliases']=['Mehmet Arif Demirtas']
for nm,yr in [('Salma El Otmani',2025),('Hongxuan Chen',2023)]:add(p,cv,'phd',nm,'RESEARCH MENTORSHIP:','Masters students:',alumni=True,year=yr);new[-1]['relationship']='membership'
add(p,cv,'masters','Zepei Li|Ang Li','Masters students:','Undergraduates:',alumni=True,year=2023)
for nm,yr in [('Aditi Shukla',2025),('Claire Zheng',2024),('Yoshee Jain',2023),('Jumee “Emily” Park',2025),('Nicole Hu',2024),('Jonathan Zhang',2023),('Anushree Berlia',2022)]:
 add(p,cv,'undergraduate',nm,'Undergraduates:','Alex Chen',alumni=True,year=yr);new[-1]['relationship']='membership'
# First-party roster JSON is the source loaded by PLAN content.js/getTeam() and displayed by index.js/buildTeamCard().
p='Ismini Lourentzou';s=src(p,'assets/data/team.json');raw=Path(s['body_path']).read_text();data=json.loads(raw);decoder=json.JSONDecoder();literal={}
for match in re.finditer(r'\{',raw):
 try:obj,end=decoder.raw_decode(raw,match.start())
 except json.JSONDecodeError:continue
 if isinstance(obj,dict)and'name'in obj and'role'in obj:literal[obj['name']]=raw[match.start():end]
plan_holds=[]
for member in data['members']:
 name=member['name'];group=member['group'];bio=member.get('bio','')
 if group=='pi':continue
 objraw=literal[name];a=objraw.index('"group"');b=objraw.index('"avatar"');q=' '.join(objraw[a:b].strip().rstrip(',').split());bioq=' '.join(objraw[objraw.index('"bio"'):objraw.rfind('}')].strip().split())
 if group=='alumni' and 'Virginia Tech'in bio:
  plan_holds.append(dict(name=name,reason='Former VirginiaTech student; no source here establishes continued advising or membership during the PI UIUC appointment. Retain unresolved school scope, not an admittedUIUC identity.',url=s['url'],sha256=s['sha256'],quote=bioq,status='unresolved',source_record_id=member['id'],captured=s['observed'],section='PLAN roster alumni'))
  continue
 role='undergraduate'if 'Undergraduate'in ' '.join(member.get('title',[]))else'phd'
 alumni=group=='alumni';yr=2026 if name=='Muntasir Wahed'else None
 add(p,s,role,name,q,None,alumni=alumni,year=yr)
 row=new[-1];row.update(quote=q,relationship='membership',corroborating_sources=[dict(url=s['url'],sha256=s['sha256'],quote=bioq)],source='reviewed_owned_structured_roster')
 if name=='Eman Abdelrahman':row['note']='Explicit current member in PI-owned UIUC PLAN roster; PhD enrollment is VirginiaTech, not UIUC. Research membership only, as with cross-school co-supervision; no UIUC degree asserted.'
 if name=='Xinzhuo Li':row['note']='Internal group key says masters, but role,title and biography all explicitly say PhD. Use explicit degree role, not display category.'
 if alumni and yr is None:row['years_basis']='Undated explicitlyUIUC undergraduate alumnus of PLANafterPIjoinedUIUC2024; exactmembershipyear unresolved.'
# Corroborate Janina's completion with separately dated home news; preserve the CV's stated advising interval as source text.
for row in new:
 if row['pi']=='Halil Kilicoglu'and row['name']=='Janina Sarol':
  home=src('Halil Kilicoglu','kilicogluh.github.io/');hq=block(home,'Nov 15, 2025','selected publications');row['corroborating_sources']=[dict(url=home['url'],sha256=home['sha256'],quote=hq)];row['years_basis']='Home news explicitly records PhD defense November2025; CV advising interval through2026 is not a graduation date.'
# Save all original reviewed groups unchanged, and add these ten reviewed source groups.
counts={pi:len({x['name']for x in new if x['pi']==pi})for pi in dict.fromkeys(x['pi']for x in new)}
baseline=json.loads((RUN/'restored-before-students/students.json').read_text())
from pihier.links import student_role_ok
before_counts={pi:sum(student_role_ok(x)for x in baseline[pi])for pi in counts}
for pi in counts:
 rec=next((x for x in records if x['pi']==pi),None)
 if rec is None:rec=dict(pi=pi,students=[]);records.append(rec)
 assert not rec['students'],(pi,'merge pre-existing manual evidence explicitly')
 rec.update(reviewed_on='2026-11-24',review='Full available owned current/alumni rosters, research-mentoring CV sections and linked PLAN structuredroster reviewed, codex-uiuc-students30-1124. Currentstudentandearlierdegreeepisodescountonceperpersonandlab; prior-school-only, committee-only andnonstudentcases excluded or held with reasons. Source-only initials retain isolatedsource-recordkeys; no guessedfullnames.')
 rec['students']=[{k:v for k,v in x.items()if k!='pi'}for x in new if x['pi']==pi]
 if pi=='Ismini Lourentzou':rec['unresolved_students']=plan_holds
(WT/'hierarchy/uiuc/reviewed/few-students-evidence.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
exclusions={'Yunzong Xu':['Teddy bears: not people'],'Huy T. Tran':['Neale Van Stralen research-engineer2020–22 episode: not student; MS2018–20 retained','All Doctoral Committees: other named advisers, not advising evidence'],'Halil Kilicoglu':['All Doctoral Students committee-member and external-examiner sections: no advising claim','Arif Canakoglu,Shabnam Tafreshi,Tung Tran: NationalLibraryofMedicine mentoring beforeUIUC','Wren Rudolph,Tory Yeonas: NLMundergraduate mentoring beforeUIUC'],'Svetlana Lazebnik':['Yunchao Gong PhD2014UNC andJoseph TighePhD2013UNC: prior school/prewindow','Cecilia MauceriMS2015,Mariyam KhalidMS2014 andallUNCMSalumni: before2016','Arun MallyaMS2014: prewindowMSstage notadmitted, PhD2018retained','All PhD committees and postdocs: not studentadvising'],'Katie Cunningham':['Alex Chen,Sid Runwal Winter2022 andallolder Northwestern/Michigan/GeorgiaTech mentorship: beforeUIUCJuly2022'],'Richard Y. Zhang':['Yubo Zhuang: committee only; named other advisers','Unrelated /faculty/zhangyp profile: YupengZhang, notRichard']}
review=dict(session='codex-uiuc-students30-1124',date='2026-11-24',scope='Complete eligible named students in available reviewed current/alumni/researchmentoring sources,2016–2026. FormerVirginiaTech alumni withoutanexplicitUIUCepisode held separately. Does not prove unlistedreal-world completeness.',sections=reviews,counts=counts,before_counts=before_counts,net_new_memberships=sum(counts.values())-sum(before_counts.values()),source_rows=len(new),exclusions=exclusions,held_roster_observations=plan_holds,identity_reviews={'Halil Kilicoglu':{'Joe Menke / Joe D Menke':'Same uniquePhD in ownlab/CV, optional middle initial'},'Huy T. Tran':{'J. Heglund / Jaye Heglund':'Same rare surname/initial, CVMSplacementasUIUCPhD andowncurrentPhDroster','Initial-only research participants':'Literal source names andstable isolatedsource-recordkeys; no full identity or namesake collection records borrowed'},'Katie Cunningham':{'Mehmet Arif Demirtaş / Mehmet Arif Demirtas':'Diacriticvariant in sameownlab andCV, samePhDcohort','Jinyoung (Jina) Hur / Jinyoung Hur':'Explicit nickname inownteam, sameCVPhDcohort'},'Richard Y. Zhang':{'June Hou':'Existingnativeidentity preserved; CVChunYing(June)Hou literalnickname corroborates MS2025. FuturePhDdestination is not PIPhDadvising.'}})
(OUT/'roster-review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
m={pi:[x for x in manifest[pi]if not(pi=='Richard Y. Zhang'and'/faculty/zhangyp'in x['url'])]for pi in counts}
extra_bindings={'Ismini Lourentzou':['plan-lab.github.io'],'Katie Cunningham':['kicunningham.com/public/','trailslab.web.illinois.edu/'],'Halil Kilicoglu':['kilicogluh.github.io/'],'Huy T. Tran':['huy-cv.pdf'],'Richard Y. Zhang':['ryz_cv.pdf'],'Svetlana Lazebnik':['lana_cv.pdf'],'Jian Huang':['platformxlab.github.io']}
for pi,needles in extra_bindings.items():
 for source in dates:
  if any(needle in source['url']for needle in needles)and not any(x['url']==source['url']and x['sha256']==source['sha256']for x in m[pi]):m[pi].append(source)
(OUT/'sources.json').write_text(json.dumps(m,indent=2)+'\n');(OUT/'date-sources.json').write_text(json.dumps(dates,indent=2)+'\n')
(RUN/'expected-students.json').write_text(json.dumps({pi:sorted({x['name']for x in new if x['pi']==pi})for pi in counts},indent=2)+'\n')
print('Complete labpopulations',counts,'total',sum(counts.values()),'netnew',review['net_new_memberships'],'rows',len(new),'heldVT',len(plan_holds))
