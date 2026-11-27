import datetime as dt, json, os, subprocess, time
from pathlib import Path
from zoneinfo import ZoneInfo
import atlas_paths as P
import stage_gate as G
import status_table as T
import pi_states as PS
from pihier.links import student_role_ok
D=Path(__file__).parent
baseline=json.loads((D/'baseline.json').read_text())
KEYS=baseline['school_order']
labels=dict(zip(KEYS,['EPFL','Stanford','CMU','Berkeley','Princeton','MIT','UChicago','JHU','Harvard','Oxford','Toronto','Michigan','U Washington','Tsinghua','Georgia Tech','HKUST','NTU','Cornell','WashU','Cambridge','Virginia Tech','SJTU','Purdue','CUHK','PKU','WHU','ZJU','ETH Zurich','USTC','UMD','UT Austin','UIUC','HIT','NYU','NUS','SEU','KAIST','UESTC','UCSD','Northeastern']))
start=dt.datetime.now(dt.timezone.utc).isoformat()
commit=os.environ.get('CS_ATLAS_SNAPSHOT_COMMIT') or subprocess.check_output(['git','rev-parse','main'],text=True,cwd=P.CODE).strip()
release=T.frozen_release(P.RELEASES)

def sig(p):
 try:
  s=p.stat();return [s.st_mtime_ns,s.st_size]
 except OSError:return None

def ranges(nums):
 if not nums:return '—'
 out=[];first=last=nums[0]
 for n in nums[1:]+[None]:
  if n is not None and n==last+1:last=n;continue
  out.append(str(first) if first==last else f'{first}–{last}')
  first=last=n
 return ', '.join(out)

def measure(key):
 for attempt in range(2):
  t=time.time()
  file_names=['pis.json','students.json','report.json','home-departments-school.json','lab-websites.json','copies.json','census-faculty.json','gap-year-evidence.json']
  paths={n:P.data(n,key) for n in file_names}
  recounts=json.loads((D/'copy-sources.json').read_text())
  if key in recounts:
   prospective=Path(recounts[key]);fresh=json.loads(prospective.read_text());canonical=json.loads(paths['copies.json'].read_text())
   if set(canonical.get('papers',{}))!=set(fresh.get('papers',{})) or canonical.get('summary',{}).get('counted_at','')<fresh.get('summary',{}).get('counted_at',''):paths['copies.json']=prospective
  paths['shared_census_overrides']=P.data('census-overrides.json')
  paths['school_census_overrides']=P.data('census-overrides-school.json',key)
  before={n:sig(p) for n,p in paths.items()}
  pis=G.read(paths['pis.json'],[]);students=G.read(paths['students.json'],{});report=G.read(paths['report.json'],{})
  assert isinstance(pis,list) and len({p['pi'] for p in pis})==len(pis),(key,'PI census')
  n=len(pis);assert n>0
  ns=sum(any(student_role_ok(s) for s in students.get(p['pi'],[])) for p in pis)
  ns_pis=sum(p.get('counts',{}).get('students',0)>0 for p in pis)
  np=sum(p.get('counts',{}).get('labPapers',0)>0 for p in pis)
  gates={}
  for stage in range(10):
   try:gates[str(stage)]=G.evaluate(key,stage)
   except Exception as e:gates[str(stage)]=dict(gate='error',error=repr(e),open=None)
  g3=gates['3'];done=total=None;openpis=[]
  if g3['gate']!='error':
   names=PS.Names(key);excluded=set(PS._build_excluded(key))
   openpis={names.of(i) for i in g3.get('unwaived_items',g3.get('items',[]))};openpis.discard(None);openpis-=excluded
   total=len(names.pis);done=total-len(openpis)
   assert 0<=done<=total
  copies=(G.read(paths['copies.json'],{}) or {}).get('summary')
  changed=[name for name,p in paths.items() if sig(p)!=before[name]]
  if changed and attempt==0:
   print('RETRY_CHANGED',key,changed,flush=True);continue
  assert np==report['counts']['pis_with_lab_papers'],(key,'paper recount mismatch on stable package')
  row=dict(school=key,label=labels[key],pis=n,pis_with_students=ns,pis_with_papers=np,student_percent=100*ns/n,paper_percent=100*np/n,student_rows=sum(sum(student_role_ok(s) for s in students.get(p['pi'],[])) for p in pis),pis_student_count_agrees=ns==ns_pis,stored_pis_with_students=ns_pis,report_pis_with_members=report.get('counts',{}).get('pis_with_students'),built_at=report.get('builtAt'),stage3_done=done,stage3_total=total,stage3_open_pi_names=sorted(openpis),copies=copies,published=key in release['counts'],gates=gates,sources={name:str(p) for name,p in paths.items()},source_signatures=before,inputs_changed_during_read=changed,measured_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),seconds=round(time.time()-t,2))
  return row

def write(rows):
 meta=dict(started_at_utc=start,generated_at_eastern=dt.datetime.now(ZoneInfo('America/New_York')).isoformat(),main_commit=commit,release=release['id'],definition_students='PIs with at least one student-role row under R-STU-34, independently recounted from students.json. Postdocs, staff and untyped non-student members excluded.',definition_completion='Stage3 inventory resolved: unique per-PI unwaived findings attributed with pi_states.Names.of; excluded PIs resolved, school-wide findings remain in gates.',rows=rows)
 (D/'snapshot.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')

rows=[]
for key in [k for k in KEYS if k!='michigan']+['michigan']:
 if key=='michigan':
  audit=Path('/n/fs/resemble/michigan-95-2026-11-26/final-validation.json')
  schema=audit.with_name('final-schema.json')
  for wait_attempt in range(28):
   if audit.exists() and schema.exists():
    a=json.loads(audit.read_text());v=json.loads(schema.read_text())
    assert not a['missing_proposals'] and not a['lost_existing_members'] and not a['lost_lab_papers'] and a['pi_inventory_unchanged']
    assert v['violations']==0
    break
   print('WAIT_MICHIGAN_NATIVE_VALIDATION',wait_attempt,flush=True);time.sleep(45)
  else:raise RuntimeError('Michigan native validation not yet complete; table remains unpublished')
 row=measure(key);rows.append(row);write(rows)
 print(key,row['pis'],f"students={row['pis_with_students']} ({row['student_percent']:.1f}%)",f"papers={row['pis_with_papers']}",f"homes={row['stage3_done']}/{row['stage3_total']}",f"seconds={row['seconds']}",flush=True)
assert len(rows)==40
assert not any(r['inputs_changed_during_read'] for r in rows), 'Concurrent source change; retry the affected row before publishing'
# Re-read package counters for any completed native builds which changed after their row was measured.
changed=[]
for i,row in enumerate(rows):
 if any(sig(Path(row['sources'][n]))!=row['source_signatures'][n] for n in ['pis.json','students.json','report.json','copies.json']):
  rows[i]=measure(row['school']);changed.append(row['school'])
write(rows)
assert not any(r['inputs_changed_during_read'] for r in rows)
import runpy
runpy.run_path(str(D/'render.py'),run_name='__main__')
