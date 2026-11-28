import csv,json,os
from pathlib import Path
D=Path(os.environ.get('ATLAS_PROGRESS_OUT_DIR', str(Path(__file__).parent)))
x=json.loads((D/'snapshot.json').read_text())
rows=x['rows']
assert len(rows)==40
website_path=Path(__file__).with_name('website-publication.json')
if website_path.exists():
 website=json.loads(website_path.read_text())
 assert set(website['schools'])=={r['school'] for r in rows}
 x['website_publication']=website
 for r in rows:r['published']=r['school'] in website['schools']
 (D/'snapshot.json').write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
weights={'students':30,'papers':20,'homes_websites':20,'gates':20,'copies':10}

def ranges(nums):
 if not nums:return '—'
 out=[];first=last=nums[0]
 for n in nums[1:]+[None]:
  if n is not None and n==last+1:last=n;continue
  out.append(str(first) if first==last else f'{first}–{last}')
  first=last=n
 return ', '.join(out)

for r in rows:
 cp=r['copies'];home=None if not r['stage3_total'] else r['stage3_done']/r['stage3_total']
 copy=None if not cp or cp.get('local_share') is None else cp.get('local',0)/cp['lab_papers'] if cp['lab_papers'] else 0
 components=dict(students=r['student_percent']/100,papers=r['paper_percent']/100,homes_websites=home,gates=sum(g['gate'] in ('pass','waived') for g in r['gates'].values())/10,copies=copy)
 missing=[k for k,v in components.items() if v is None]
 if any(g['gate']=='error' for g in r['gates'].values()):missing.append('gate_errors')
 r['score_components']=components
 r['completion_score']=sum(weights[k]*v for k,v in components.items() if v is not None)
 r['unmeasured_components']=missing
 r['score_provisional']=bool(missing)
 r['completion_score_max']=r['completion_score']+sum(weights[k] for k,v in components.items() if v is None)+2*sum(g['gate']=='error' for g in r['gates'].values())
 assert 0<=r['completion_score']<=r['completion_score_max']<=100.0000001
rows.sort(key=lambda r:(-r['completion_score'],-r['score_components']['gates'],-r['student_percent'],-(r['score_components']['homes_websites'] or 0),r['label']))
table=[]
for i,r in enumerate(rows,1):
 r['rank']=i
 gs=r['gates'];done,total=r['stage3_done'],r['stage3_total'];cp=r['copies']
 passed=ranges([int(s) for s,g in gs.items() if g['gate']=='pass'])
 failing=', '.join(f"{s} ({len(g.get('unwaived_items',g.get('items',[]))):,})" for s,g in gs.items() if g['gate']=='fail') or '—'
 errors=[s for s,g in gs.items() if g['gate']=='error']
 if errors:failing+='; errors: '+ranges(list(map(int,errors)))
 waived=[s for s,g in gs.items() if g['gate']=='waived']
 if waived:failing+='; waived: '+','.join(waived)
 table.append({'#':i,'School':r['label'],'Score':f"{r['completion_score']:.1f}"+('*' if r['score_provisional'] else ''),'PIs':r['pis'],'PIs w/ students':f"{r['student_percent']:.1f}%",'PIs w/ papers':f"{r['paper_percent']:.1f}%",'Lab homes & websites (PIs done)':f'{round(100*done/total)}% ({done}/{total})' if total else 'Error','Copies':f"{round(cp['local_share']*100)}%" if cp and cp.get('local_share') is not None else 'unmeasured','Live':'✅' if r['published'] else '—','Gates passed':passed,'Gates failing (open items)':failing})
x['rows']=rows
x['ranking_formula']={'weights_percent':weights,'formula':'30*student_fraction +20*paper_fraction +20*home_website_fraction +20*(resolved_gates_0_to_9/10) +10*local_copy_fraction','gates_resolved':'pass or valid owner-approved waiver','missing_policy':'Unavailable components receive no verified completion credit. Their factual columns remain Error/unmeasured. Provisional scores are marked with an asterisk; upper bound is retained per row.','tie_break':'Unrounded score, then resolved-gate share, student share, home/website share, school label.'}
x.pop('score_note',None)
(D/'snapshot-ranked.json').write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
with (D/'table.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(table[0]),lineterminator='\n');w.writeheader();w.writerows(table)
lines=['| '+' | '.join(table[0])+' |','| '+' | '.join(['---']*len(table[0]))+' |']+['| '+' | '.join(map(str,r.values()))+' |' for r in table]
(D/'table.txt').write_text('\n'.join(lines)+'\n')
live_note=(f"Live means provisionally visible on {website['public_url']} (verified baseline `{website['publication']}`; all schools retained in this refresh). Formal research-release inclusion is recorded separately in snapshot-ranked.json." if x.get('website_publication') else f"Live indicates formal research release inclusion in `{x['release']}`.")
intro=['# All-school progress refresh','',f"Measured {x['started_at_utc']} through {x['generated_at_eastern']}. Code: `{x['main_commit']}`. {live_note}",'']
notes=['','Score = 30 × student share + 20 × paper share + 20 × resolved home/website share + 20 × resolved gate share + 10 × local-copy share. Shares are fractions from zero to one; gates are stages 0–9.','','Student coverage counts explicit student-role memberships under R-STU-34. Lab homes and websites use the stage-3 process inventory, which can differ from the native PI census; resolved outcomes do not necessarily mean a working lab website. Open school-wide audit findings remain in the gates column.','','Copies are freshly recounted against each current unique-paper inventory using the native copy-quality and identity checks. Shared catalog and copy-counter files are untouched. Measurement times and source paths are recorded per school in snapshot-ranked.json. A local copy is not by itself a publicly hosted website reader.','','An asterisk marks a provisional score with an unreadable component; no completion credit is inferred from an unavailable measurement.']
(D/'table.md').write_text('\n'.join(intro+lines+notes)+'\n')
validation=dict(rows=len(rows),ranked_by_current_score=True,prior_scores_and_ranks_unused=True,all_pis_counted=True,all_student_percentages_recounted=True,all_rows_stable_during_read=not any(r['inputs_changed_during_read'] for r in rows),package_student_count_disagreements=[r['school'] for r in rows if not r['pis_student_count_agrees']],provisional_scores={r['school']:{'score':r['completion_score'],'maximum':r['completion_score_max'],'unknown':r['unmeasured_components']} for r in rows if r['score_provisional']},gate_errors={r['school']:{s:g['error'] for s,g in r['gates'].items() if g['gate']=='error'} for r in rows if any(g['gate']=='error' for g in r['gates'].values())})
assert validation['all_rows_stable_during_read']
(D/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
print('DONE',json.dumps(validation),flush=True)
