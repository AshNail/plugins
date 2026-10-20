const vm=require('vm');
const code=require('./load-script')('request.js');
function run(url, body){
  let done=null; const logs=[];
  const ctx={$request:{url,body:typeof body==='string'?body:JSON.stringify(body)},$done:x=>{done=x},
    console:{log:(...a)=>logs.push(a.join(' '))},JSON,Set,Array,Object,String,Number,Boolean,Math,Error,Date};
  vm.runInNewContext(code,ctx,{timeout:2000});
  return {done,logs};
}
let pass=0,fail=0;
function ck(n,c,e){c?(pass++,console.log('  PASS  '+n)):(fail++,console.log('  FAIL  '+n+(e?' got='+e:'')))}

console.log('\n== 1. preload true -> false ==');
{
  const r=run('https://api.qishui.com/luna/advert/incentive/config',{
    preload:true, advert_sources:[{rit:1}], advert_duration:30, cid:'x'
  });
  const o=JSON.parse(r.done.body);
  ck('preload=false', o.preload===false, o.preload);
  ck('advert_duration 未动', o.advert_duration===30, o.advert_duration);
  ck('advert_sources 未动', Array.isArray(o.advert_sources)&&o.advert_sources.length===1);
  console.log(r.logs.join('\n'));
}

console.log('\n== 2. preload 1 -> 0 ==');
{
  const r=run('https://api.qishui.com/luna/advert/incentive/config',{preload:1,advert_duration:15});
  const o=JSON.parse(r.done.body);
  ck('preload=0', o.preload===0, o.preload);
}

console.log('\n== 3. 嵌套 preload ==');
{
  const r=run('https://api.qishui.com/luna/advert/incentive/config',{data:{preload:true,advert_duration:30}});
  const o=JSON.parse(r.done.body);
  ck('嵌套 preload=false', o.data.preload===false, o.data.preload);
}

console.log('\n== 4. 非 JSON 放行 ==');
{
  const r=run('https://api.qishui.com/luna/advert/incentive/config','\x08\x96\x01');
  ck('无 body', !(r.done&&r.done.body));
}

console.log('\n== 5. 非目标 URL 放行 ==');
{
  const r=run('https://api.qishui.com/luna/treasure/task/view',{preload:true});
  ck('无 body', !(r.done&&r.done.body));
}

console.log('\n== 6. 已经 off -> 放行 ==');
{
  const r=run('https://api.qishui.com/luna/advert/incentive/config',{preload:false});
  ck('无 body', !(r.done&&r.done.body));
  ck('日志 already off', r.logs.join(' ').includes('already off'), r.logs.join(' '));
}

console.log('\n== 7. ads/config preload ==');
{
  const r=run('https://api.qishui.com/luna/ads/config',{
    preload:true,ad_unit_configs:[{slot_id:'1'}],advert_duration:30
  });
  const o=JSON.parse(r.done.body);
  ck('ads/config preload=false', o.preload===false, o.preload);
  ck('ad_unit_configs 未动', Array.isArray(o.ad_unit_configs)&&o.ad_unit_configs.length===1);
  ck('advert_duration 未动', o.advert_duration===30, o.advert_duration);
}

console.log('\nPASS='+pass+' FAIL='+fail);
process.exit(fail?1:0);
