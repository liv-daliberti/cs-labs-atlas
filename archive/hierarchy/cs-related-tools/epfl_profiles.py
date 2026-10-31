"""EPFL: fetch live people.epfl.ch profiles (?lang=en) of the CS-related review's candidates into the review store."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import cscap
cscap.use('epfl')
for slug in sys.argv[1:]:
    u = f'https://people.epfl.ch/{slug}?lang=en'
    r = cscap.fetch(u)
    t = r['text']
    i = t.find('Position'); 
    print(json.dumps(dict(slug=slug, status=r['status'], err=r['error'], n=len(t), head=t[:160])), flush=True)
