import sys,json,re
sys.path.insert(0,'/n/fs/resemble/homogenizing-science/worktrees/ucsd/tools')
import school_web as W, atlas_paths as P
key='ucsd'; c=W.con(key)
cands=json.load(open(P.data('cs-related-candidates.json',key)))
byname={x['name']:x for x in cands}
def cap(dept,year):
    r=c.execute("select capture_url,sha256,wayback_timestamp,text from captures where department=? and http_status=200 and wayback_timestamp like ? order by wayback_timestamp desc limit 1",(dept,year+'%')).fetchone(); return r
def flat(t): return ' '.join(t.split())
specs=[('Scott Makeig','SCCN','2026',r'Scott Makeig Research Scientist & Director','Research Scientist, not a faculty appointment'),
('Arnaud Delorme','SCCN','2026',r'Arnaud Delorme Research Scientist','Research Scientist, not a faculty appointment'),
('Masaki Nakanishi','SCCN','2026',None,'SCCN member listed without a faculty title'),
('Ying Choon Wu','SCCN','2026',r'Ying Wu','SCCN Project Scientist'),
('Michael J. Pazzani','HDSI','2022',r'Michael Pazzani Distinguished Researcher','Distinguished Researcher at HDSI, not a faculty appointment'),
('Yuri Bazilevs','SE','2021',r'Adjunct Bazilevs, Yuri','listed under the Adjunct heading of the Structural Engineering directory')]
ents=[]
for name,dept,yr,rx,why in specs:
    x=byname.get(name)
    if not x: print('no cand',name); continue
    r=cap(dept,yr)
    if not r: print('no cap',name); continue
    url,sha,ts,t=r; f=flat(t)
    if rx is None:
        pn=name.split(); m=re.search(re.escape(pn[0])+r'\s+'+re.escape(pn[-1])+r'[^|]{0,60}',f)
    else: m=re.search(rx.replace(r'\ ',r'\s+') if False else rx,f)
    if not m: print('no quote',name,dept,yr); continue
    q=m.group(0)
    src=x['source']; ids=[x['dblp']] if src=='dblp_affiliation' else x['openalex']
    ev=dict(url=url,sha256=sha,quote=q,observed=ts)
    ents.append(dict(name=name,unit=dept,ladder=False,reviewed_by='claude-ucsd-1124',reviewed_on='2026-11-25',**ev,
      candidate_review=dict(decision='research_or_other_rank',source=src,ids=ids,why=why+' (D-0009: faculty status needs a professor-rank appointment).',
        identity_note='The unit directory entry and the discovery record name the same person at UC San Diego; no namesake at UCSD appears in the captured directory.',identity_evidence=[dict(ev)])))
    print('ok',name,'|',q)
hand=json.load(open(P.data('cs-related-hand.json',key)))
hand=[e for e in hand if e.get('candidate_review') is None]
new=json.load(open('/tmp/claude-363432/gen2-new.json'))
have={(e['name'],e['url']) for e in hand}
hand+= [e for e in new if (e['name'],e['url']) not in have]
hand+=ents
json.dump(hand,open(P.data_w('cs-related-hand.json',key),'w'),indent=1,ensure_ascii=False)
print(len(hand))
