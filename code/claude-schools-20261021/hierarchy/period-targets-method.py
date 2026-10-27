import json,sys,collections
def yrs(p):
    Y=set()
    for q in p.get('periods') or []:
        s=int(str(q.get('start') or '1900')[:4]); e=int(str(q.get('end') or q.get('asof') or '2026')[:4])
        Y|={y for y in range(max(s,2016),min(e,2026)+1)}
    Y|={l['year'] for l in p.get('listings') or []}
    return Y
for s in sys.argv[1:]:
    P=json.load(open(f'hierarchy/{s}/pis.json'))
    add={a['name'] for a in json.load(open(f'census/{s}-additions.json')) if 'cs_related' in str(a.get('added'))}
    c=collections.Counter(); low=[]
    for p in P:
        k=len(yrs(p)); grp='csrel' if p['pi'] in add else 'core'
        c[grp,'n']+=1
        if k<=3: c[grp,'<=3yrs']+=1; low.append((p['pi'],k,p['counts']['labPapers']))
    print(s,dict(c)); print('  ',low[:60])
