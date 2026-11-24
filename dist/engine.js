/* Playoff Lab 2.0 — deterministic seeded Monte Carlo and NFL-style selection. */
const GROUPS={AFC:{East:['BUF','MIA','NE','NYJ'],North:['BAL','CIN','CLE','PIT'],South:['HOU','IND','JAX','TEN'],West:['DEN','KC','LAC','LV']},NFC:{East:['DAL','NYG','PHI','WSH'],North:['CHI','DET','GB','MIN'],South:['ATL','CAR','NO','TB'],West:['ARI','LAR','SF','SEA']}};
const TEAMS=Object.values(GROUPS).flatMap(c=>Object.values(c).flat()),IX=Object.fromEntries(TEAMS.map((t,i)=>[t,i]));const CONF=[],DIV=[];Object.entries(GROUPS).forEach(([c,ds])=>Object.entries(ds).forEach(([d,ts])=>ts.forEach(t=>{CONF[IX[t]]=c;DIV[IX[t]]=c+d})));
const rate=(w,n)=>n?w/n:0;
function selectBest(candidates,ctx,isDiv=false){
 let pool=candidates.slice();const {w,n,hh,hn,dw,dn,cw,cn,pf,pa,cpf,cpa,schedule,beaten,noise}=ctx;
 const pct=t=>rate(w[t],n[t]);let max=Math.max(...pool.map(pct));pool=pool.filter(t=>Math.abs(pct(t)-max)<1e-9);if(pool.length===1)return pool[0];
 const sov=t=>rate(beaten[t].reduce((s,o)=>s+w[o],0),beaten[t].reduce((s,o)=>s+n[o],0));const sos=t=>rate(schedule[t].reduce((s,o)=>s+w[o],0),schedule[t].reduce((s,o)=>s+n[o],0));
 const ranking=(t,subset,scored,allowed)=>subset.filter(x=>scored[x]>scored[t]).length+subset.filter(x=>allowed[x]<allowed[t]).length;
 function reduce(values){let m=Math.max(...values);let kept=pool.filter((_,i)=>Math.abs(values[i]-m)<1e-9);if(kept.length<pool.length){pool=kept;return true}return false}
 // Restart after narrowing the set, as NFL multi-club procedures require.
 for(let restart=0;restart<32;restart++){
  const others=t=>pool.filter(x=>x!==t),allPlayed=pool.every(t=>others(t).every(o=>hn[t*32+o]>0));
  let hhValues;
  if(isDiv||pool.length===2)hhValues=allPlayed?pool.map(t=>rate(others(t).reduce((s,o)=>s+hh[t*32+o],0),others(t).reduce((s,o)=>s+hn[t*32+o],0))):null;
  else {const sweeper=pool.find(t=>others(t).every(o=>hn[t*32+o]>0&&hh[t*32+o]===hn[t*32+o]));if(sweeper!==undefined)return sweeper;const swept=pool.filter(t=>others(t).every(o=>hn[t*32+o]>0&&hh[t*32+o]===0));if(swept.length&&swept.length<pool.length){pool=pool.filter(t=>!swept.includes(t));continue}}
  const common=[...new Set(schedule[pool[0]])].filter(o=>pool.every(t=>schedule[t].includes(o)));const commonValid=pool.every(t=>common.reduce((s,o)=>s+hn[t*32+o],0)>=(isDiv?1:4));const commonRate=t=>rate(common.reduce((s,o)=>s+hh[t*32+o],0),common.reduce((s,o)=>s+hn[t*32+o],0));
  const criteria=[];if(hhValues)criteria.push(hhValues);if(isDiv){criteria.push(pool.map(t=>rate(dw[t],dn[t])));if(commonValid)criteria.push(pool.map(commonRate));criteria.push(pool.map(t=>rate(cw[t],cn[t])))}else{criteria.push(pool.map(t=>rate(cw[t],cn[t])));if(commonValid)criteria.push(pool.map(commonRate))}
  criteria.push(pool.map(sov),pool.map(sos),pool.map(t=>-ranking(t,TEAMS.map((_,i)=>i).filter(i=>CONF[i]===CONF[t]),pf,pa)),pool.map(t=>-ranking(t,TEAMS.map((_,i)=>i),pf,pa)));
  if(isDiv)criteria.push(pool.map(t=>common.reduce((s,o)=>s+ctx.net[t*32+o],0)));else criteria.push(pool.map(t=>cpf[t]-cpa[t]));
  criteria.push(pool.map(t=>pf[t]-pa[t]));let narrowed=false;for(let vals of criteria){if(reduce(vals)){narrowed=true;break}}if(pool.length===1)return pool[0];if(!narrowed)break;
 }
 // Net touchdowns unavailable: seeded draw only after all implemented score criteria.
 ctx.fallbacks++;return pool.reduce((a,b)=>noise[a]>noise[b]?a:b);
}
function qualify(ctx){let selected=[],division=[],byes=[],seeds=Array(32).fill(0);
 for(const [conf,ds] of Object.entries(GROUPS)){let leaders=Object.values(ds).map(ts=>selectBest(ts.map(t=>IX[t]),ctx,true));division.push(...leaders);let ordered=[];while(leaders.length){let t=selectBest(leaders,ctx,false);ordered.push(t);leaders=leaders.filter(x=>x!==t)}byes.push(ordered[0]);let remaining=TEAMS.map((_,i)=>i).filter(t=>CONF[t]===conf&&!ordered.includes(t));for(let k=0;k<3;k++){let reps=Object.values(ds).map(ts=>remaining.filter(t=>ts.includes(TEAMS[t]))).filter(ts=>ts.length).map(ts=>selectBest(ts,ctx,true));let t=selectBest(reps,ctx,false);ordered.push(t);remaining=remaining.filter(x=>x!==t)}ordered.forEach((t,i)=>seeds[t]=i+1);selected.push(...ordered)}return {selected,division,byes,seeds}}
// A logistic margin with scale 7.2 has about a 13-point standard deviation.
function sampleMargin(homeChance, outcome, quantile) {
 if (outcome === .5) return 0;
 const winnerChance = outcome === 1 ? homeChance : 1 - homeChance;
 // Inverse CDF of the winner's margin conditional on a positive margin.
 const points = 7.2 * Math.log1p(quantile / ((1 - winnerChance) * (1 - quantile)));
 return (outcome === 1 ? 1 : -1) * Math.max(1, Math.round(points));
}
function simulate(data,picks={},N=10000,focus='CLE',seed=14721){
 let state=seed>>>0;const random=()=>{state=(Math.imul(state,1664525)+1013904223)>>>0;return state/4294967296};const normal=()=>Math.sqrt(-2*Math.log(Math.max(1e-9,random())))*Math.cos(2*Math.PI*random());
 const gs=data.games.map(g=>({...g,hi:IX[g.h],ai:IX[g.a]})),future=gs.filter(g=>!g.done),schedule=TEAMS.map((_,i)=>gs.filter(g=>g.hi===i||g.ai===i).map(g=>g.hi===i?g.ai:g.hi));
 const base=TEAMS.map(()=>({w:0,l:0,t:0}));gs.filter(g=>g.done).forEach(g=>{if(g.hs===g.as_){base[g.hi].t++;base[g.ai].t++}else{base[g.hs>g.as_?g.hi:g.ai].w++;base[g.hs>g.as_?g.ai:g.hi].l++}});
 const out=TEAMS.map(()=>({play:0,division:0,bye:0,wins:0,seeds:Array(8).fill(0),records:Array(18).fill(0),noTieRecords:Array(18).fill(0),noTiePlayoffs:Array(18).fill(0)})),impact=future.map(()=>({counts:[0,0,0],qualified:[0,0,0]}));let fallbacks=0;
 for(let s=0;s<N;s++){
  let ctx={w:Array(32).fill(0),n:Array(32).fill(0),hh:new Float32Array(1024),hn:new Uint8Array(1024),dw:Array(32).fill(0),dn:Array(32).fill(0),cw:Array(32).fill(0),cn:Array(32).fill(0),pf:Array(32).fill(0),pa:Array(32).fill(0),cpf:Array(32).fill(0),cpa:Array(32).fill(0),net:new Int16Array(1024),beaten:TEAMS.map(()=>[]),schedule,noise:TEAMS.map(()=>random()),fallbacks:0};let outcomes=[],tieCounts=Array(32).fill(0);
  for(let g of gs){let hs=g.hs,as=g.as_;if(!g.done){let u=random(),marginQuantile=random(),totalNoise=normal();let v=picks[g.id];if(v===undefined)v=u<.004?.5:((u-.004)/.996<g.p?1:0);outcomes.push(v===0?0:v===.5?1:2);let margin=sampleMargin(g.p,v,marginQuantile);let total=Math.max(Math.abs(margin)+6,Math.round(44+10*totalNoise));as=Math.max(0,Math.round((total-margin)/2));hs=as+margin;}
   let h=g.hi,a=g.ai,v=hs>as?1:hs<as?0:.5;if(v===.5){tieCounts[h]++;tieCounts[a]++}ctx.w[h]+=v;ctx.w[a]+=1-v;ctx.n[h]++;ctx.n[a]++;ctx.hh[h*32+a]+=v;ctx.hh[a*32+h]+=1-v;ctx.hn[h*32+a]++;ctx.hn[a*32+h]++;ctx.pf[h]+=hs;ctx.pa[h]+=as;ctx.pf[a]+=as;ctx.pa[a]+=hs;ctx.net[h*32+a]+=hs-as;ctx.net[a*32+h]+=as-hs;
   if(CONF[h]===CONF[a]){ctx.cw[h]+=v;ctx.cw[a]+=1-v;ctx.cn[h]++;ctx.cn[a]++;ctx.cpf[h]+=hs;ctx.cpa[h]+=as;ctx.cpf[a]+=as;ctx.cpa[a]+=hs}if(DIV[h]===DIV[a]){ctx.dw[h]+=v;ctx.dw[a]+=1-v;ctx.dn[h]++;ctx.dn[a]++}if(v===1)ctx.beaten[h].push(a);if(v===0)ctx.beaten[a].push(h)
  }
  let q=qualify(ctx);q.selected.forEach(t=>out[t].play++);q.division.forEach(t=>out[t].division++);q.byes.forEach(t=>out[t].bye++);out.forEach((r,i)=>{const wins=ctx.w[i]-tieCounts[i]/2;r.wins+=wins;r.seeds[q.seeds[i]]++;r.records[wins]++;if(!tieCounts[i]){r.noTieRecords[ctx.w[i]]++;if(q.seeds[i])r.noTiePlayoffs[ctx.w[i]]++}});let qualified=q.selected.includes(IX[focus]);outcomes.forEach((v,i)=>{impact[i].counts[v]++;if(qualified)impact[i].qualified[v]++});fallbacks+=ctx.fallbacks;
 }
 return {N,focus,base:Object.fromEntries(TEAMS.map((t,i)=>[t,base[i]])),result:Object.fromEntries(TEAMS.map((t,i)=>[t,out[i]])),impact:Object.fromEntries(future.map((g,i)=>[g.id,impact[i]])),fallbacks};
}
if(typeof self!=='undefined'&&typeof document==='undefined')onmessage=e=>{try{postMessage({...simulate(e.data.data,e.data.picks,e.data.N,e.data.focus),version:e.data.version,kind:e.data.kind})}catch(err){postMessage({error:err.message,version:e.data.version})}};
if(typeof module!=='undefined')module.exports={sampleMargin,simulate,selectBest,qualify,GROUPS,TEAMS,IX};
