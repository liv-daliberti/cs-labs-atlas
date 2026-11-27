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
RUN = P.school_part('gatech', 'work') / 'students15d-1126'
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
                   auto=False, rule='R-STU-01', batch='gatech-students15d-1126',
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


for pi,name,role,year,adviser in [
 ('Beki Grinter','Ari Schlesinger','phd',2019,None),
 ('Andrea Thomaz','Tesca Fitzgerald','phd',2017,None),
 ('Lauren G. Wilcox','Matthew Hong','phd',2019,'Lauren Wilcox'),
 ('Yanni Alexander Loukissas','Mohsin Yousufi','phd',2025,'Yanni Loukissas'),
 ('Judith Uchidiuno','Jared Lim','masters',2024,None),
 ('Shaowen Bardzell','Soonho Kwon','phd',2026,None)]:
    award(pi,name,role,year,adviser)

s=source('https://kaishuocheng.github.io/')
q=block(s,'I am a 5th year PhD student','I worked with')+' '+block(s,'Kaishuo Cheng kcheng89','Google Scholar')
# Preserve one contiguous literal quote including name, degree, university, and named co-adviser.
q=block(s,'I am a 5th year PhD student','Google Scholar')
add('Joseph Jaeger',s,'Kaishuo Cheng','phd',q,relationship='advising')

s=source('https://mphute.github.io/')
q=block(s,'Mansi Phute Hi,', 'My research is')
add('Duen Horng "Polo" Chau',s,'Mansi Phute','phd',q,relationship='advising')
s=source('https://alechelbling.com/')
q=block(s,'Alec Helbling Alec Helbling','I work on')
add('Duen Horng "Polo" Chau',s,'Alec Helbling','phd',q,relationship='advising')

s=source('https://calendar.gatech.edu/event/2025/11/12/hotcse-seminar-sebastian-gutierrez-hernandez')
q=block(s,'Bio: Sebastián Gutiérrez Hernández','Sebastián holds')
add('Haomin Zhou',s,'Sebastián Gutiérrez Hernández','phd',q,relationship='advising',years=[2025,2025])
new[-1]['additional_sources']=[dict(url=s['url'],sha256=s['sha256'],quote='Date: Wednesday, Nov. 12, 2025, at 12:00 p.m.')]

s=source('https://barry.ece.gatech.edu/group/hall/shanwei.pdf')
q=block(s,'MULTITRACK DETECTION FOR MAGNETIC RECORDING A Dissertation','Learning without thought')
add('John R Barry',s,'Shanwei Shi','phd',q,relationship='advising',years=[2021,2021],alumni=True)
held.append(dict(pi='John R Barry',reason='Undated research-group page mixes historical people, doctors, and a University of Agder visitor. Only the independently dated 2021 Georgia Tech dissertation with a named adviser is admitted.'))

s=source('https://cgdct.moe/assets/pdf/cv.pdf')
q=block(s,'Stephen Huan','Improve state of the art')
add('Florian Schäfer',s,'Stephen Huan','undergraduate',q,years=[2021,2024],alumni=True)
new[-1]['note']='Explicit undergraduate research placement under Florian Schäfer in the Georgia Tech School of CSE, fall 2021–fall 2024. CMU PhD advisers and Caltech summer research are separate placements, not GT PhD advising.'

s=source('https://pearce.prof/misc/pearce_cv_fall_2024.pdf')
t=visible(s)
owner=t[:t.index('Education')+len('Education')] if 'Education' in t else t[:1200]
# The CV states GT employment from 2019. Use explicit historical start dates;
# Present in an undated CV is never extended to the 2026 capture date.
assert 'Georgia Institute of Technology' in owner
for name,year in [('Hugo Hue',2022),('Amanda Hsu',2021),('Mert Erdemir',2021),('Grant Williams',2020),('Abhishek Bhaskar',2019)]:
    a=t.index(name+':',t.rfind('B.1 Ph.D. Students Supervised'))
    end=t.index('Present',a)+len('Present')
    q=t[a:end]
    add('Paul Pearce',s,name,'phd',q,years=[year,year],relationship='advising',host=owner)
    new[-1]['additional_sources']=[dict(url=s['url'],sha256=s['sha256'],quote='B.1 Ph.D. Students Supervised'),dict(url=s['url'],sha256=s['sha256'],quote=owner)]
    new[-1]['note']='Historical supervision start explicitly stated in the GT faculty CV. Only that year is observed; Present is not extrapolated to retrieval or to the current UCI roster.'
for name,role,start,end,year1,year2 in [
 ('Shaarif Sajid','phd','Shaarif Sajid:','B.2 M.S.',2019,2020),
 ('ChangSeok Oh','masters','ChangSeok Oh:','8. Apurv',2021,2022),
 ('Apurv Singh Gautam','masters','Apurv Singh Gautam:','B.3 Undergraduate',2020,2021),
 ('Wooseok (Luke) Kim','undergraduate','Wooseok (Luke) Kim:','B.4 Thesis',2021,2021)]:
    q=block(s,start,end)
    add('Paul Pearce',s,name,role,q,years=[year1,year2],relationship='advising',alumni=True,host=owner)
    heading={'phd':'B.1 Ph.D. Students Supervised','masters':'B.2 M.S. Projects and Special Problems Students Supervised','undergraduate':'B.3 Undergraduate Students Supervised'}[role]
    new[-1]['additional_sources']=[dict(url=s['url'],sha256=s['sha256'],quote=heading),dict(url=s['url'],sha256=s['sha256'],quote=owner)]
q=block(s,'Shan Chen College of Computing, Advisor: Alexandra Boldyreva, 2019','• Ph.D. Thesis Committee - External')
add('Alexandra Boldyreva',s,'Shan Chen','phd',q,years=[2019,2019],relationship='advising',alumni=True)
new[-1]['additional_sources']=[dict(url=s['url'],sha256=s['sha256'],quote='B.4 Thesis or Dissertation Committees • Ph.D. Thesis Committee - Georgia Tech')]
held.append(dict(pi='Paul Pearce',reason='UCI current roster is not transferred to GT. Historical GT supervision is dated by explicit CV year fields. Committee membership does not imply advising; the separate Shan Chen record names Alexandra Boldyreva as adviser.'))

s=next(source(u) for u in manifest if manifest[u]['body_path'].endswith('cached-1390.html'))
q=block(s,'PhD Students','Undergraduate / Master’s Students')
add('Vladimir Kolesnikov',s,'Sankha Das','phd',q,relationship='advising')

s=source('https://www.pair.toronto.edu/people/')
owner=block(s,'Animesh Garg PAIR Director','Albert Wilcox')
t=visible(s)
# Raw email links are source evidence linking each typed member to GT. Keep the
# exact original HTML attribute as supporting evidence, after checking its card.
from urllib.parse import unquote
soup=BeautifulSoup(Path(s['body_path']).read_bytes(),'html.parser')
for name,role in [('Albert Wilcox','phd'),('Benjamin Joffe','phd'),('Ezra Ameperosa','phd'),('Hrishit Leen','phd'),('Shuxin Cao','phd'),('Walker Byrnes','phd'),('Yogita Choudhary','phd'),('Ethan Villalovoz','masters'),('Varun Giridhar','masters'),('Yixiong Hao','undergraduate')]:
    a=next(a for a in soup.find_all('a',href=lambda h:h and h.startswith('mailto:')) if any(name in p.get_text(' ',strip=True) and len(p.get_text(' ',strip=True))<500 for p in list(a.parents)[:5]))
    email=unquote(a['href']);assert email.endswith('@gatech.edu') or email.endswith('@gtri.gatech.edu'),(name,email)
    card=next(p for p in a.parents if name in p.get_text(' ',strip=True))
    q=' '.join(card.get_text(' ',strip=True).split());assert q in t
    add('Animesh Garg',s,name,role,q,host=owner)
    new[-1]['additional_sources']=[dict(url=s['url'],sha256=s['sha256'],quote=owner),dict(url=s['url'],sha256=s['sha256'],quote=a['href'])]
    new[-1]['note']='Typed current PAIR member, sole director Animesh Garg, with explicit gatech.edu email on the same member card. UofT members are held separately; capture-year observation only.'
for name,role,start,end,years in [
 ('Nhi (Leona) Nguyen','masters','Nhi (Leona) Nguyen','Atharva Mete',[2024,2026]),
 ('Atharva Mete','masters','Atharva Mete','Kourosh Darvish',[2023,2025]),
 ('Ayush Agarwal','undergraduate','Ayush Agarwal','Aditya Bajoria',[2024,2026]),
 ('Aditya Bajoria','undergraduate','Aditya Bajoria','Kunal Aneja',[2024,2026]),
 ('Kunal Aneja','student','Kunal Aneja','Jia Lin (Alan) Yuan',[2022,2026])]:
    add('Animesh Garg',s,name,role,block(s,start,end),host=owner,years=years,alumni=True)
    new[-1]['additional_sources']=[dict(url=s['url'],sha256=s['sha256'],quote=owner)]
    new[-1]['note']='Explicit Georgia Tech institution, degree, and years in the PAIR alumni table. Mixed BSMS degree retained as generic student rather than inventing separate degree periods.'
held.append(dict(pi='Animesh Garg',reason='UofT/Stanford students, postdocs and visitors held. Private-email current members without explicit GT affiliation are held. On-leave GT members remain source-stated members; no attendance inferred.'))

path=P.reviewed_path('few-students-evidence.json','gatech',code=WT)
records=json.loads(path.read_text());records=[g for g in records if not any(s.get('batch')=='gatech-students15d-1126' for s in g['students'])]
prior={r['pi'] for d in ['gatech-students10-1126','gatech-students15-1126','gatech-students15b-1126','gatech-students15c-1126'] for r in json.loads((WT/'reports'/d/'additions.json').read_text())}
selected={r['pi'] for r in new};assert len(selected)==15 and not prior.intersection(selected)
assert len({(r['pi'],r['name'],r['role'],tuple(r['years'])) for r in new})==len(new)
from pihier.links import student_role_ok
baseline=json.loads(P.data('pis.json','gatech').read_text());by_pi={p['pi']:p for p in baseline};ss=json.loads(P.data('students.json','gatech').read_text())
bp=OUT/'baseline.json'
receipt=json.loads(bp.read_text()) if bp.exists() else dict(pis=len(baseline),zero_student_labs=sum(p['counts']['students']==0 for p in baseline),student_memberships=sum(p['counts']['students'] for p in baseline),selected={p:by_pi[p]['counts'] for p in sorted(selected)},existing_students={p:[s for s in ss.get(p,[]) if student_role_ok(s)] for p in sorted(selected)})
for pi in sorted(selected):
    assert receipt['selected'][pi]['students']==0
    old={s['name'] for s in receipt['existing_students'][pi]}
    assert not old.intersection(r['name'] for r in new if r['pi']==pi),pi
    records.append(dict(pi=pi,students=[{k:v for k,v in r.items() if k!='pi'} for r in new if r['pi']==pi],note='Fifteen further source-verified GT student relationship labs, batch gatech-students15d-1126.'))
errs=schema_check.validate(records,json.loads((WT/'schemas/few-students-evidence.schema.json').read_text()));assert not errs,errs
path.write_text(json.dumps(records,indent=1,ensure_ascii=False)+'\n')
(OUT/'additions.json').write_text(json.dumps(new,indent=2,ensure_ascii=False)+'\n')
(OUT/'roster-review.json').write_text(json.dumps(dict(session=SESSION,sections=sections,held=held),indent=2,ensure_ascii=False)+'\n')
used={r['sha256'] for r in new};used.update(x['sha256'] for r in new for x in r.get('corroborating_sources',[]))
(OUT/'sources.json').write_text(json.dumps([s for s in manifest.values() if s['sha256'] in used],indent=2)+'\n')
if not bp.exists():bp.write_text(json.dumps(receipt,indent=2)+'\n')
pairs={(r['pi'],r['name']) for r in new}
print(json.dumps(dict(relationships=len(pairs),episodes=len(new),counts={p:sum(pi==p for pi,n in pairs) for p in sorted(selected)}),indent=2))
