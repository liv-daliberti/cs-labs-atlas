import sys,json,re
sys.path.insert(0,'/n/fs/resemble/homogenizing-science/worktrees/ucsd/tools')
import school_web as W, atlas_paths as P
key='ucsd'; c=W.con(key)
def cap(d): return c.execute("select capture_url,sha256,wayback_timestamp,text from captures where department=? and http_status=200 and wayback_timestamp like '2026%' order by wayback_timestamp desc limit 1",(d,)).fetchone()
specs=[('Jun-Kun Wang','ECE','Jun-Kun Wang Assistant Professor'),('Michael Yip','ECE','Michael Yip Associate Professor'),('Yeshaiahu Fainman','ECE','Y. Shaya Fainman Distinguished Professor'),('Dmitriy Drusvyatskiy','HDSI','Dima Drusvyatskiy Professor')]
hand=json.load(open(P.data('cs-related-hand.json',key)))
have={(e['name'],e['url']) for e in hand}
for name,d,q in specs:
    url,sha,ts,t=cap(d)
    f=' '.join(t.split())
    if q not in f: print('missing',q); continue
    if (name,url) in have: continue
    hand.append(dict(name=name,unit=d,url=url,sha256=sha,observed=ts,quote=q,ladder=True)); print('ok',name)
json.dump(hand,open(P.data_w('cs-related-hand.json',key),'w'),indent=1,ensure_ascii=False)
