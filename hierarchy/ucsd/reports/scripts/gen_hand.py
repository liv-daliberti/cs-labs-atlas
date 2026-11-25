import sys,json,re,datetime,unicodedata
sys.path.insert(0,'/n/fs/resemble/homogenizing-science/worktrees/ucsd/tools')
import school_web as W, school_config as S, cs_related_school as C, atlas_paths as P
key='ucsd'; c=W.con(key); cfg=S.get(key)
cands=json.load(open(P.data('cs-related-candidates.json',key)))
rev=json.load(open(P.data('cs-related-review.json',key)))['decisions']
acc={x['name'] for x in rev if x['decision']=='accepted'}
HOLD={'Zhijian Liu','Duncan Watson-Parris','Meenakshi Khosla'}
todo=[x for x in cands if x['name'] not in acc and x['name'] not in HOLD]
teaching=C.not_ladder_titles(key)
hand=json.load(open(P.data('cs-related-hand.json',key))) if P.data('cs-related-hand.json',key).exists() else []
hand=[e for e in hand if e['unit']!='MATH' and not (e['name'] in HOLD and e['url'].rstrip('/').endswith('/faculty'))]
have={(e['name'],e['url']) for e in hand}
new=[]
def norm(s): return ''.join(ch for ch in unicodedata.normalize('NFKD',s) if not unicodedata.combining(ch))
# 1. live unit pages
today=datetime.date.today().isoformat().replace('-','')
for u in cfg['affiliated_units']:
    for l in u.get('listings') or []:
        url=l if l.startswith('http') else 'https://'+l
        host=re.sub(r'^https?://','',url).split('/')[0]
        if S.host_use(key,host)!='live': continue
        r=W.live(c,url)
        if not r or r[0]!=200: continue
        flat=W.flat(r[2]); pages=[(u['code'],url,r[1],today,flat)]
        for x in todo:
            names=[x['name']]+list(x.get('aliases') or [])
            ev=[e for e in C.faculty_evidence(pages,names,teaching) if e['ladder']]
            if not ev and u['code']=='MATH':   # title-first layout: 'Professor Lutz Warnke AP&M'
                for n in names:
                    t=n.split(); 
                    if len(t)<2: continue
                    m=re.search(r'((?:Associate |Assistant |Distinguished )?Professor)\s+'+re.escape(t[0])+r'\s+(?:[A-Z][\w.\'-]*\s+)?'+re.escape(t[-1])+r'\b',flat)
                    if m: ev=[dict(unit='MATH',url=url,sha256=r[1],observed=today,quote=m.group(0),ladder=True)]; break
            if ev:
                e=ev[0]
                if (x['name'],e['url']) not in have: new.append(dict(name=x['name'],unit=u['code'],url=e['url'],sha256=e['sha256'],observed=e['observed'],quote=e['quote'],ladder=True)); have.add((x['name'],e['url']))
# 2. MATH faculty-page captures 2016-2021 (title-less directory: the Faculty page lists the department's faculty)
for url,sha,ts,txt in c.execute("select capture_url,sha256,wayback_timestamp,text from captures where department='MATH' and http_status=200 and text like '%Total%' and text like '%AP&M%'"):
    t=norm(txt)
    for x in todo:
        for n in [x['name']]+list(x.get('aliases') or []):
            p=norm(n).split()
            if len(p)<2: continue
            m=re.search(re.escape(p[-1])+r',\s+'+re.escape(p[0])+r'(?:[ \t]+(?!Graduate\b)[A-Z][\w.\'-]*)?(?=\s|$)',t)
            if m:
                q=m.group(0)
                if q in txt and (x['name'],url) not in have:
                    new.append(dict(name=x['name'],unit='MATH',url=url,sha256=sha,observed=ts,quote=q,ladder=True,note='MATH Faculty page directory (Total Faculty list); the page prints no titles and does not mark lecturers; the Faculty page (not Emeriti/Visitors/Staff) is read as ladder for the capture year'))
                    have.add((x['name'],url))
                break
print(len(new)); 
for e in new: print(e['name'],e['unit'],e['observed'][:8],e['quote'])
json.dump(hand+new,open(P.data_w('cs-related-hand.json',key),'w'),indent=1,ensure_ascii=False)
