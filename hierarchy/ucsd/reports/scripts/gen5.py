import sys,json,datetime
sys.path.insert(0,'/n/fs/resemble/homogenizing-science/worktrees/ucsd/tools')
import school_web as W, atlas_paths as P
c=W.con('ucsd'); u='https://physics.ucsd.edu/people/faculty'
r=W.live(c,u); f=W.flat(r[2]); q='Frank Wuerthwein Professor'; assert q in f
hand=json.load(open(P.data('cs-related-hand.json','ucsd')))
hand.append(dict(name='Frank Würthwein',unit='PHYS',url=u,sha256=r[1],observed=datetime.date.today().isoformat().replace('-',''),quote=q,ladder=True))
json.dump(hand,open(P.data_w('cs-related-hand.json','ucsd'),'w'),indent=1,ensure_ascii=False)
