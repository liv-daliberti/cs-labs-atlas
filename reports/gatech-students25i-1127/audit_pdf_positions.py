import re,json,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
import atlas_paths as P
report=Path(__file__).resolve().parent;run=P.school_part('gatech','work')/'students25i-1127'
entries=[dict(e,pdf_page=e['source_pdf_page'])for e in json.loads((report/'reviewed-entries.json').read_text())if e.get('source_pdf_page')];sources={s['sha256']:s for s in json.loads((report/'sources.json').read_text())}
xmls={h:ET.fromstring(re.sub(rb'[\x00-\x08\x0b\x0c\x0e-\x1f]',b'',subprocess.check_output(['pdftotext','-bbox-layout',s['body_path'],'-'],stderr=subprocess.DEVNULL)))for h,s in sources.items()if h in {e['sha256']for e in entries}}
checks=[]
for e in entries:
 pages=xmls[e['sha256']].findall('.//{*}page');p=pages[e['pdf_page']-1]
 lines=[dict(text=' '.join(w.text or '' for w in l.findall('{*}word')),x=float(l.attrib['xMin']),y=float(l.attrib['yMin']),ymax=float(l.attrib['yMax']))for l in p.findall('.//{*}line')]
 names=[l for l in lines if l['text'].removesuffix(' +')==e['name']]
 if len(names)!=1:print('NAME',e['name'],[l['text']for l in lines if e['name'].split()[-1]in l['text']]);continue
 n=names[0];below=sorted([l for l in lines if abs(l['x']-n['x'])<2 and l['y']>n['y']+2 and l['y']-n['ymax']<45],key=lambda l:l['y'])
 if not below or not below[0]['text'].startswith(('Advisor:','Advisors:')):print('ADVISER',e['name'],n,below);continue
 checks.append(dict(sha256=e['sha256'],pi=e['pi'],name=e['name'],pdf_page=e['pdf_page'],name_position=n,following_column_lines=below,result='named adviser directly below candidate in same PDF column'))
print('geometric source checks',len(checks),'/',len(entries))
(run/'pdf-position-audit.json').write_text(json.dumps(checks,indent=2,ensure_ascii=False)+'\n')
assert len(checks)==len(entries)
