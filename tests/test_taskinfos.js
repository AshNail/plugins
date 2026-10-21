const vm=require('vm');
const code=require('./load-script')('sanitize.js');
function run(url, body){
  let done=null; const logs=[];
  const ctx={$request:{url},$response:{body:JSON.stringify(body)},$done:x=>{done=x},
    $argument:{rewardSafe:false,cleanAds:true,killRewardAds:true,hideDouyinTab:false},
    console:{log:(...a)=>logs.push(a.join(' '))},JSON,Set,Array,Object,String,Number,Boolean,Math,Error,Date,isFinite};
  vm.runInNewContext(code,ctx,{timeout:2000});
  return {done,logs};
}
const r=run('https://api.qishui.com/luna/treasure/task/view',{
  status_code:0,
  task_infos:[
    {task_key:'reward_ads',title:'看广告得金币'},
    {task_key:'sign_in',title:'每日签到'},
    {task_key:'listen_duration',title:'听歌任务'},
    {task_key:'browse_mall_task',title:'逛商城'}
  ]
});
const o=JSON.parse(r.done.body);
const keys=o.task_infos.map(t=>t.task_key);
console.log('kept:',keys.join(','));
console.log(r.logs.join('\n'));
if(keys.includes('reward_ads')||keys.length!==3||!keys.includes('sign_in')) process.exit(1);
console.log('PASS');
