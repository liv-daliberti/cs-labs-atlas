'use strict';
// Counts are sufficient statistics over disjoint work buckets, never sums of lab totals.
const AtlasSizing = (() => {
 function counts(metrics, peerForMember, matches, view, from, to) {
  const selected=new Map(), reference=new Map();
  for(const bucket of metrics.buckets) {
   if(bucket.view!==view && bucket.view!=='combined')continue;
   const peers=new Set(bucket.members.filter(matches).flatMap(peerForMember).filter(Boolean));
   if(!peers.size)continue;
   let value=0,full=0;
   for(const [year,stats] of Object.entries(bucket.years)) {
    if(+year>=2016&&+year<=2026)full+=stats.works;
    if(+year>=from&&+year<=to)value+=stats.works;
   }
   for(const id of peers) {
    if(bucket.view===view)selected.set(id,(selected.get(id)||0)+value);
    if(bucket.view==='combined')reference.set(id,(reference.get(id)||0)+full);
   }
  }
  return {selected,reference};
 }
 function layout(d3, peers) {
  const max=d3.max(peers,p=>p.reference)||0;
  const marker=Math.max(1,Math.sqrt(max)*.025),gap=marker*.35;
  const envelopes=peers.map(p=>({...p,r:Math.max(Math.sqrt(p.reference),marker)+gap})).sort((a,b)=>b.r-a.r||a.id.localeCompare(b.id));
  d3.packSiblings(envelopes);
  const enclosure=envelopes.length?d3.packEnclose(envelopes):{x:0,y:0,r:1};
  const scale=330/(enclosure.r||1);
  return {scale,maxReference:max,points:envelopes.map(p=>({id:p.id,x:350+(p.x-enclosure.x)*scale,y:350+(p.y-enclosure.y)*scale,r:p.count>0?Math.sqrt(p.count)*scale:marker*.75*scale,count:p.count,reference:p.reference,missing:p.count===0}))};
 }
 function niceCount(value) {if(value<1)return 0;const base=10**Math.floor(Math.log10(value)),m=value/base;return (m>=5?5:m>=2?2:1)*base;}
 return {counts,layout,niceCount};
})();
if(typeof module!=='undefined')module.exports=AtlasSizing;
