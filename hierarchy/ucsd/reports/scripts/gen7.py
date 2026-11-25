import sys,json,re,unicodedata,collections
sys.path.insert(0,'/n/fs/resemble/homogenizing-science/worktrees/ucsd/tools')
import school_web as W, atlas_paths as P
key='ucsd'; c=W.con(key)
def norm(s): return re.sub(r'\s+',' ',''.join(ch for ch in unicodedata.normalize('NFKD',s.replace('\xa0',' ')) if not unicodedata.combining(ch)))
cands=json.load(open(P.data('cs-related-candidates.json',key)))
rev=json.load(open(P.data('cs-related-review.json',key)))['decisions']
HOLD={'Zhijian Liu','Duncan Watson-Parris','Meenakshi Khosla'}
acc={x['name'] for x in rev if x['decision']=='accepted'}
todo=[x for x in cands if x['name'] not in acc and x['name'] not in HOLD]
extra=['Shlomo Dubnov','Tamara Smyth','Shahrokh Yadegari','Tom Erbe','Imani Sherman','Sadhika Malladi','Sam Lau','Judith E. Fan','Henry D. I. Abarbanel','Miller S. Puckette']
names={}
for x in todo: names[x['name']]=[x['name']]+list(x.get('aliases') or [])
for n in extra: names.setdefault(n,[n])
def tk(n): return re.sub(r'[^a-z ]','',norm(n).lower().replace('-',' ')).split()
idx=collections.defaultdict(list)
for k,al in names.items():
    for a in al:
        t=tk(a)
        if len(t)>=2: idx[(t[0],t[-1])].append(k)
        if len(t)>=2: idx[(t[0][:1],t[-1])].append(k) if False else None
HEAD=re.compile(r'^(Professors?(?: Emeriti| Emerita| Emeritus)?|Associate Professors?|Assistant Professors?|Professors? of (?:the )?(?:Practice|Teaching)|(?:Senior )?Lecturers?[^,]*|Adjunct [A-Za-z ]+|Research [A-Za-z ]+|Clinical [A-Za-z ]+|[A-Za-z ]*Professors? (?:in|of) [A-Za-z ]+|Affiliated[A-Za-z ]*|Other Faculty[A-Za-z ]*|Faculty Affiliates)$')
LAD={'Professors','Professor','Associate Professors','Assistant Professors'}
hand=json.load(open(P.data('cs-related-hand.json',key)))
have={(e['name'],e['url']) for e in hand}
new=[]; seen=collections.Counter()
for d,url,sha,ts,t in c.execute("select department,capture_url,sha256,wayback_timestamp,text from captures where http_status=200 and department like 'CAT_%'"):
    head=None
    for line in (t or '').split('\n'):
        l=line.strip(); ln=norm(l)
        if not l: continue
        if HEAD.match(ln.strip()): head=ln.strip(); continue
        if head is None or len(l)>140: continue
        nm=ln.split(',')[0]; tt=tk(nm)
        if len(tt)<2: continue
        for k in idx.get((tt[0],tt[-1]),[]):
            role=ln[len(nm):]
            ladder=head in LAD and not re.search(r'Teaching|Lecturer|Research|Adjunct|Emerit|Practice|Visiting|Clinical|Affiliat',role)
            if ladder and (k,url) not in have:
                new.append(dict(name=k,unit=d,url=url,sha256=sha,observed=ts,quote=l.replace('\xa0',' ') if l.replace('\xa0',' ') in (t or '').replace('\xa0',' ') else l,ladder=True,note=f'General Catalog faculty roster, listed under the "{head}" heading'))
                have.add((k,url)); seen[(k,d)]+=1
print(len(new))
for (k,d),n in sorted(seen.items()): print(k,d,n)
json.dump(hand+new,open(P.data_w('cs-related-hand.json',key),'w'),indent=1,ensure_ascii=False)
