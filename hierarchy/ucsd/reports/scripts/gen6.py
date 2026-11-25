import sys,json,re
sys.path.insert(0,'/n/fs/resemble/homogenizing-science/worktrees/ucsd/tools')
import school_web as W, atlas_paths as P
key='ucsd'; c=W.con(key)
cands={x['name']:x for x in json.load(open(P.data('cs-related-candidates.json',key)))}
url,sha,ts,t=c.execute("select capture_url,sha256,wayback_timestamp,text from captures where department='SCCN' and wayback_timestamp like '2026%' order by wayback_timestamp desc limit 1").fetchone()
f=' '.join(t.split())
specs=[('Dung Truong',r'Dung Truong 2018 Michael Vu','listed in the SCCN former-members list (2018) with no faculty title'),
('Alejandro Ojeda',r'Alejandro Ojeda Gonzalez Position Programmer Analyst','SCCN programmer/analyst, not a faculty appointment'),
('Jörn Anemüller',r'J\S+rn Anem\S+ller Position Visiting Postdoctoral Fellow','SCCN visiting postdoctoral fellow, not a faculty appointment')]
hand=json.load(open(P.data('cs-related-hand.json',key)))
hand=[e for e in hand if not (e['name']=='Lily Weng')]
# Tsui-Wei Weng: the candidate's page name is 'Lily Weng' (HDSI profile)
w=[e for e in json.load(open(P.data('cs-related-hand.json',key))) if e['name']=='Lily Weng']
for e in w: hand.append(dict(e,name='Tsui-Wei Weng'))
have={(e['name'],e.get('candidate_review') is not None) for e in hand}
for name,rx,why in specs:
    x=cands.get(name)
    if not x: print('no cand',name); continue
    m=re.search(rx,f)
    if not m: print('no quote',name); continue
    q=m.group(0); src=x['source']; ids=[x['dblp']] if src=='dblp_affiliation' else x['openalex']
    ev=dict(url=url,sha256=sha,quote=q,observed=ts)
    hand.append(dict(name=name,unit='SCCN',ladder=False,reviewed_by='claude-ucsd-1124',reviewed_on='2026-11-25',**ev,
      candidate_review=dict(decision='research_or_other_rank',source=src,ids=ids,why=why+' (D-0009).',identity_note='The SCCN member list entry and the OpenAlex author record name the same person with SCCN/UC San Diego works.',identity_evidence=[dict(ev)])))
    print('ok',name)
json.dump(hand,open(P.data_w('cs-related-hand.json',key),'w'),indent=1,ensure_ascii=False)
