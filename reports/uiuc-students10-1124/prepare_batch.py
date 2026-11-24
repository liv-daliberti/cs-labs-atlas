import hashlib,json,re,shutil
from pathlib import Path
from bs4 import BeautifulSoup
import atlas_paths as P
RUN=P.SCRATCH/'uiuc-students10-1124';WT=P.ROOT/'worktrees/uiuc-students10-1124';OUT=WT/'reports/uiuc-students10-1124';OUT.mkdir(parents=True,exist_ok=True)
manifest=json.loads((RUN/'sources.json').read_text());dates=json.loads((RUN/'date-source-results.json').read_text()); records=json.loads((P.CODE/'hierarchy/uiuc/reviewed/few-students-evidence.json').read_text());new=[];reviews=[]
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
  row=dict(name=name,role=role,years=[year,year] if year else ([2026,2026] if not alumni else None),years_basis='explicit dated source' if year else ('capture observation only; no earlier membership years inferred' if not alumni else 'undated UIUC lab alumni; membership year unresolved; UIUC-only lab and PI education/appointment place possible membership wholly in 2016–2026'),alumni=alumni,section=start,url=s['url'],observed=s['observed'],sha256=s['sha256'],quote=q,rule='R-STU-01',reviewed_by='codex-uiuc-students10-1124',reviewed=True,auto=False,note=note or 'Whole owned roster manually reviewed, with degree headings and campus scope; source membership is not inferred from coauthorship.')
  if proof:
   ps,pq=proof;assert pq in text(ps);row['corroborating_sources']=[dict(url=ps['url'],sha256=ps['sha256'],quote=pq)]
  new.append(dict(pi=pi,**row))
 reviews.append(dict(pi=pi,url=s['url'],sha256=s['sha256'],section=start,role=role,names=names.split('|'),alumni=alumni))
p='Hao Peng';s=src(p,'/group/');add(p,s,'phd','Deema Alnuhait|Dylan Zhang|Lifan Yuan|Minyang Tian|Sagnik Mukherjee|Shivam Agarwal|Xinxi Lyu|Yufeng Du','PhD students','Masters students');add(p,s,'masters','Haojin Wang|Jingwen Gu|Lai Jiang','Masters students','Undergrad students');add(p,s,'undergraduate','An Yan|Chinmay Rawat|Haoming Wen|Pavan Jayasinha|Yufan Zhang|Yuyang Wu','Undergrad students','Last updated')
p='Yuxiong Wang';s=src(p,'yxw.cs.illinois.edu/');add(p,s,'phd','Garvita Allabadi|Liuyu Bian|Shengcao Cao|Junkun Chen|Jiahua Dong|Ji Li|Yunze Man|Ziqi Pang|Michal Shlapentokh-Rothman|Kai Yan|Qianlan Yang|Sirui Xu|Zheyu Zhang','Students PhD Students','Recent Publications')
p='Katie Driggs-Campbell';s=src(p,'/people/');cv=src(p,'2025_krdc_cv.pdf');proof=(cv,block(cv,'Academic Appointments','Postdoctoral Research Scholar'))
add(p,s,'phd','Ye-Ji Mun|Neeloy Chakraborty|Kaiwen Hong|Andre Schreiber|Ananya Yammanuru|Fatemeh Cheraghi|Maria Lusardi|John Pohovey|Shaoting Peng','PhD Students','MS Students');add(p,s,'masters','Joshua Cox|Will Chen|Jiaming Xu|Jimmy Fang','MS Students','Alumni')
add(p,s,'phd','Haonan Chen|Jacob Wagner|Marty Purushottam|Zhe Huang|Aamir Hasan|Peixin Chang|Pulkit Katdare|Tianchen Ji|Shuijing Liu|Peter Du','Alumni Alum Program','©',alumni=True,proof=proof)
add(p,s,'masters','Janelle Domantay|Yiyang Xu|Yixuan Wang|Xiang Li|Yiqing Xie|Eric Liang|Zhenyi Tang|Ke (Richard) Xu|James Keiller','Alumni Alum Program','©',alumni=True,proof=proof)
# Explicit thesis lists extend the lab people page; committee-only names are excluded.
for name,yr in [('Surya Murthy',2023),('Yilong Niu',2023),('Justin Lin',2023),('Zhaoxu Deng',2021),('Kazuki Shin',2021),('Abhi Kamboj',2021),('Rui Liu',2020),('Shanduojiao Jiang',2020),('Xinyi Guo',2020)]:add(p,cv,'undergraduate',name,'Undergraduate Theses','Doctoral Dissertation Committees',alumni=True,year=yr)
# Preserve earlier degree episodes of current students without inventing PhD start years.
for name in ['Andre Schreiber','Neeloy Chakraborty']:add(p,cv,'masters',name,'Masters Theses','Undergraduate Theses',year=2023)
add(p,cv,'undergraduate','Neeloy Chakraborty','Undergraduate Theses','Doctoral Dissertation Committees',year=2021)
p='Jiaqi Ma';s=src(p,'jiaqima.github.io');add(p,s,'phd','Junwei Deng|Pingbang Hu|Shixuan Liu|Yiwen Tu|Weiyi Wang','People PhD Students','MS Students');add(p,s,'masters','Xirui Jiang|Dan Lee','MS Students (thesis-based)','Teaching')
p='Ning Luo';s=src(p,'students.html');add(p,s,'phd','Gefei Tan|Chentian Wu','Students Gefei Tan','Can Liu');add(p,s,'masters','Can Liu','Can Liu , MS','Siqi Li');add(p,s,'undergraduate','Siqi Li','Siqi Li','Alumni');add(p,s,'masters','Joy Wan','Fall 2025 - Fall 2026','Publication:',alumni=True,year=2026);add(p,s,'masters','Hengyu Liu','Fall 2024 - Fall 2025','Publication:',alumni=True,year=2025);add(p,s,'visiting','Zhaoxiang Liu','Summer 2025, Visiting student, Zhaoxiang Liu','Publication:',alumni=True,year=2025);add(p,s,'visiting','Can Liu','Summer 2025, Visiting student, Can Liu','Publication:',alumni=True,year=2025);add(p,s,'visiting','Sijia Xie','Summer 2025, Visiting student, Sijia Xie','Former Mentees',alumni=True,year=2025)
p='Fernando Granha Jeronimo';s=src(p,'granha.github.io/');add(p,s,'phd','Lenny Liu|William Gay|Ricardo Garcia|Abhi Shukul','PhD Students','Research archive')
p='Dakshita Khurana';s=src(p,'/group');add(p,s,'phd','James Hulett|Kabir Tomer|Tzu-Hsiang (Jimmy) Huang|Hoaxing Jin','PhD Students','Former PhD Students');add(p,s,'phd','Ruta Jawale|Amit Agarwal','Former PhD Students','In loving memory',alumni=True,year=2025);add(p,s,'phd','Nishant Kumar','Former PhD Students','Former Postdocs',alumni=True,year=2022,note='Named under Former PhD Students; memorial date proves presence by2022, not a graduation date.');add(p,s,'masters','Andrew Liu','Former M.S. Student','Amit, me,',alumni=True,year=2022)
p='Makrand Sinha';s=src(p,'makrandsinha');add(p,s,'phd','Qizhao Huang|Ricardo Garcia|William Gay|Abhi Shukul','Advising','Alexandra Levinshteyn');add(p,s,'undergraduate','Alexandra Levinshteyn','Alexandra Levinshteyn','Arjun Aggarwal',alumni=True,year=2026);add(p,s,'undergraduate','Arjun Aggarwal','Arjun Aggarwal','Mehrdad Tahmasbi',alumni=True,year=2025)
p='Gagandeep Singh';s=src(p,'/students/');cv=src(p,'ggndpsngh.github.io/cv/');proof=(cv,block(cv,'Education','Publications'))
add(p,s,'phd','Qiuhan Gu|Jasper Lee|Nalin Wadhwa|Shaurya Gomber|Debangshu Banerjee|Jason Vega|Isha Chaudhary|Avaljot Singh|Calvin Xu','Students PhD','Master Dushyant');add(p,s,'masters','Dushyant Bharadwaj|David Shu Cheung','Master Dushyant','Undergrad');add(p,s,'undergraduate','Anay Joshi|Prineet Parhar|Brian Kim|Kavya Sachdeva|Nischay Singh|Yuxuan Wan','Undergrad','Alumni');add(p,s,'phd','Yinglun Xu','Alumni Yinglun Xu','Shubham Ugare',alumni=True,year=2026);add(p,s,'phd','Shubham Ugare','Shubham Ugare','Xinyi Wei',alumni=True,year=2025,note='Source degree interval begins2020; retain only explicit2025 completion observation without claiming PI lab membership in2020.');add(p,s,'masters','Xinyi Wei','Xinyi Wei','Tarun Suresh',alumni=True,proof=proof);add(p,s,'undergraduate','Tarun Suresh|Vedaant V Jain|Jehyeok Yeon|Rohan Gumaste|Hangoo Kang|Siyuan Brant Qian|Nancy Jia|Seung Hoon Choi|Pranshu Chaturvedi|Rem Yang|Robert Nagel','Tarun Suresh','Sitemap',alumni=True,proof=proof)
p='Yingying Li';s=src(p,'/people');prof=src(p,'ece.illinois.edu/about');proof=(prof,'Yingying Li Assistant Professor, Industrial and Enterprise Systems Engineering, starting Fall 2023')
add(p,s,'phd','Haonan Xu|Ziyao Guo|Yulun Wu|Ghazal Hassani|Haori Lu|Shengkang Gao','Ph.D. Students','Undergraduate Students');add(p,s,'undergraduate','Alexandra Li','Undergraduate Students','Former Students');add(p,s,'phd','Negin Musavi','Former Students','Christopher William Taylor',alumni=True,proof=proof);add(p,s,'undergraduate','Christopher William Taylor|William Deng','Christopher William Taylor','Jing Yu',alumni=True,proof=proof);add(p,s,'masters','Jesse Wei|Dhritiman Roy|Vansh Porwal','Jesse Wei','Angelina Jane McKenna',alumni=True,proof=proof);add(p,s,'undergraduate','Angelina Jane McKenna','Angelina Jane McKenna','Google Sites',alumni=True,proof=proof)
p='Ning Luo';cv=src(p,'CV_Ning');add(p,cv,'masters','Siheng Pan','Masters: Siheng Pan','Undergraduates:');add(p,cv,'phd','Can Liu','Mentorship PhDs:','Masters:')
p='Dakshita Khurana';cv=src(p,'cv--26.pdf');add(p,cv,'undergraduate','Alexandra Levinshteyn','Undergrad ⋄ Alexandra','⋄ Devin Akman');add(p,cv,'undergraduate','Devin Akman','⋄ Devin Akman','⋄ Kabir Tomer',alumni=True,year=2020);add(p,cv,'undergraduate','Olivia Figueira','⋄ Olivia Figueira','Teaching Fall 2026',alumni=True,year=2020);add(p,cv,'undergraduate','Kabir Tomer','⋄ Kabir Tomer, Summer intern','⋄ Olivia Figueira',year=2020)
for name,yr in [('Nishant Kumar',2022),('Ruta Jawale',2022),('Amit Agarwal',2021)]:add(p,cv,'masters',name,'MS ⋄ Nishant Kumar','Undergrad',alumni=True,year=yr)
for pi in dict.fromkeys(x['pi'] for x in new):
 rec=next((x for x in records if x['pi']==pi),None)
 if rec is None:rec=dict(pi=pi,students=[]);records.append(rec)
 assert not rec['students'],(pi,'unexpected existing rows; merge manually')
 rec.update(reviewed_on='2026-11-24',review='Full available owned current/alumni roster and linked CV review, codex-uiuc-students10-1124. Includes all supported student roles; explicit prior-school mentees, faculty, postdocs and visiting scholars excluded. Dates reflect stated episodes or current capture only; undated alumni retain unresolved membership years.')
 rec['students']=[{k:v for k,v in x.items() if k!='pi'} for x in new if x['pi']==pi]
(WT/'hierarchy/uiuc/reviewed/few-students-evidence.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
(OUT/'roster-review.json').write_text(json.dumps(dict(session='codex-uiuc-students10-1124',date='2026-11-24',scope='Complete eligible students in reviewed available sources,2016–2026; not an assertion about unlisted people.',sections=reviews,counts={pi:len({x['name'] for x in new if x['pi']==pi}) for pi in dict.fromkeys(x['pi'] for x in new)},exclusions={'Katie Driggs-Campbell':['Mahsa Golchoubian: visiting scholar','D. Livingston McPherson: postdoc','Junyi Geng: postdoc','Tan Chen: postdoc (CV)','Doctoral Dissertation Committees: other named thesis advisers, not advising evidence'],'Ning Luo':['Former Mentees: prior Northwestern/Yale/Xiamen mentoring'],'Dakshita Khurana':['Mehrdad Tahmasbi: postdoc','Naresh Goud Boddu: postdoc'],'Makrand Sinha':['Mehrdad Tahmasbi: postdoc'],'Yingying Li':['Jing Yu: Caltech mentoring','Runyu Zhang: Harvard mentoring','Xin Chen: Harvard mentoring'],'Fernando Granha Jeronimo':["Avi Wigderson’s: extractor false person from PI own prior-postdoc bio"]}),ensure_ascii=False,indent=2)+'\n')
shutil.copy2(RUN/'sources.json',OUT/'sources.json');shutil.copy2(RUN/'date-source-results.json',OUT/'date-sources.json')
print('Pairs',sum(len({x['name'] for x in new if x['pi']==pi}) for pi in dict.fromkeys(x['pi'] for x in new)),'source rows',len(new));print(json.loads((OUT/'roster-review.json').read_text())['counts'])
