import sys,json,re,unicodedata
sys.path.insert(0,'/n/fs/resemble/homogenizing-science/worktrees/ucsd/tools')
import school_web as W, atlas_paths as P
key='ucsd'; c=W.con(key)
cands=json.load(open(P.data('cs-related-candidates.json',key)))
rev=json.load(open(P.data('cs-related-review.json',key)))['decisions']
done={x['name'] for x in rev if x['decision'] in('accepted',)}
HOLD={'Zhijian Liu','Duncan Watson-Parris','Meenakshi Khosla'}
todo=[x for x in cands if x['name'] not in done and x['name'] not in HOLD]
hand=json.load(open(P.data('cs-related-hand.json',key)))
have={(e['name'],e['url']) for e in hand}
def norm(s): return ''.join(ch for ch in unicodedata.normalize('NFKD',s) if not unicodedata.combining(ch))
caps=sorted(c.execute("select department,capture_url,sha256,wayback_timestamp,text from captures where http_status=200 and department!='ucsd' and department!='MATH'"),key=lambda r:r[3])
latest={}
for d,u,s,ts,t in caps: latest[(d,u[:0],ts[:4])]=(d,u,s,ts,t)   # per unit-year keep last
rows=[v for v in latest.values()]
new=[]
TITLE=re.compile(r'^[\s|,]{0,6}((?:Assistant |Associate |Distinguished |Full )?Professor)(?! of the Practice)(?!\s+(?:Emerit|of Teaching|Teaching))')
for x in todo:
    for d,u,s,ts,t in rows:
        tn=norm(t); best=None
        for n in [x['name']]+list(x.get('aliases') or []):
            p=norm(n).split()
            if len(p)<2: continue
            for m in re.finditer(re.escape(p[0])+r'\s+(?:[A-Z][\w.\'-]*\s+)?'+re.escape(p[-1])+r'(?![\w-])',tn):
                tail=tn[m.end():m.end()+40]
                mt=TITLE.match(tail.replace('\n',' '))
                if mt: best=tn[m.start():m.end()+mt.end()]; break
            if best: break
        if best and best in t and (x['name'],u) not in have:
            new.append(dict(name=x['name'],unit=d,url=u,sha256=s,observed=ts,quote=' '.join(best.split()),ladder=True)); have.add((x['name'],u))
seen={}
for e in new: seen.setdefault((e['name'],e['unit']),[]).append(e['observed'][:4])
for k,v in sorted(seen.items()): print(k,v[:3],'...',len(v))
json.dump(new,open('/tmp/claude-363432/gen2-new.json','w'))
