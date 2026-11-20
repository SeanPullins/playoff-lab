const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('dist/app.js','utf8').split('function autoPickGames(')[1].split('function renderAutoPick')[0];
const data={games:[{id:'a',week:11,p:.8},{id:'b',week:11,p:.2},{id:'c',week:12,p:.6},{id:'d',week:12,p:.3},{id:'e',week:11,p:.8,done:true}]};
function scenario(scope,week,picks){let applied=null,messages=[];const ctx={data,picks,applyPicks:p=>applied=p,toast:m=>messages.push(m)};vm.createContext(ctx);vm.runInContext('function autoPickGames('+source,ctx);ctx.autoPickGames(scope,week);return {applied:applied&&JSON.parse(JSON.stringify(applied)),messages}}
assert.deepEqual(scenario('week',11,{a:0}).applied,{a:0,b:0});
assert.deepEqual(scenario('season',null,{a:.5}).applied,{a:.5,b:0,c:1,d:0});
assert.deepEqual(scenario('week','12',{}).applied,{c:1,d:0});
assert.equal(scenario('week',11,{a:1,b:0}).applied,null);
assert.equal(scenario('week',18,{}).applied,null);
console.log('Auto-pick tests passed: week scope, season scope, manual picks, ties, finals, no-op.');
