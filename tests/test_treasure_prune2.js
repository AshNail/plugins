const vm=require('vm');
const code=require('./load-script')('sanitize.js');
function run(url, body){
  let done=null; const logs=[];
  const ctx={$request:{url},$response:{body:JSON.stringify(body)},$done:x=>{done=x},
    $argument:{rewardSafe:false,cleanAds:true,killRewardAds:true,hideDouyinTab:false},
    console:{log:(...a)=>logs.push(a.join(' '))},JSON,Set,Array,Object,String,Number,Boolean,Math,Error,Date,isFinite};
  vm.runInNewContext(code,ctx,{timeout:3000});
  return {done,logs,out:done&&done.body?JSON.parse(done.body):null};
}
let pass=0,fail=0;
function ck(n,c,e){c?(pass++,console.log('  PASS  '+n)):(fail++,console.log('  FAIL  '+n+(e!==undefined?' got='+JSON.stringify(e):'')))}

console.log('\n== entrance: 金币挂件广告态 ==');
{
  const r=run('https://api.qishui.com/luna/treasure/entrance/config',{
    status_code:0,
    labels:[{text:'看视频免费畅听'},{text:'每日签到'}],
    coin_widget_state_list:[
      {text_type:'widgetAdReward',jump_uri:'x'},
      {text_type:'widgetSignInWithListenGate',jump_uri:'y'},
      {text_type:'widgetClaimable',jump_uri:'z'}
    ]
  });
  const states=r.out.coin_widget_state_list.map(x=>x.text_type);
  const labels=r.out.labels.map(x=>x.text);
  ck('广告态被删', states.join(',')==='widgetSignInWithListenGate,widgetClaimable', states);
  ck('签到/可领取保留', states.includes('widgetSignInWithListenGate')&&states.includes('widgetClaimable'));
  ck('看视频标签被删', labels.join(',')==='每日签到', labels);
  console.log(r.logs.join('\n'));
}

console.log('\n== task/view: watch_video / incentive ==');
{
  const r=run('https://api.qishui.com/luna/treasure/task/view',{
    status_code:0,
    task_infos:[
      {task_key:'watch_video',title:'看视频领畅听'},
      {task_key:'incentive_ad',title:'激励任务'},
      {task_key:'ad_reward',title:'广告奖励'},
      {task_key:'reward_ad',title:'广告奖励2'},
      {task_key:'commerce_ad_task',title:'商业化广告任务'},
      {task_key:'ad_snap',title:'广告挂件'},
      {task_key:'sign_in',title:'每日签到'},
      {task_key:'listen_duration',title:'听歌任务'},
      {task_key:'share_cnt',title:'分享任务'}
    ]
  });
  const keys=r.out.task_infos.map(x=>x.task_key);
  ck('只留非广告任务', keys.join(',')==='sign_in,listen_duration,share_cnt', keys);
  ck('commerce_ad/ad_snap 任务被删', !keys.includes('commerce_ad_task')&&!keys.includes('ad_snap'), keys);
  console.log(r.logs.join('\n'));
}

console.log('\n== entrance: 广告 banner ==');
{
  const r=run('https://api.qishui.com/luna/treasure/entrance/config',{
    status_code:0,
    banner_list:[
      {banner_type:'reward_ad',image:'a'},
      {banner_type:'ad_reward',image:'a2'},
      {banner_type:'vip',image:'b'},
      {banner_type:'treasure',image:'c'},
      {banner_type:'incentive_center',image:'c2'}
    ],
    reward_ad_banner:{image:'d'},
    ads_banner:{image:'e'},
    ad_snap:{image:'f'},
    vip_banner:{image:'g'},
    free_vip_banner:{image:'h'}
  });
  const types=r.out.banner_list.map(x=>x.banner_type);
  ck('广告 banner 被删', types.join(',')==='vip,treasure,incentive_center', types);
  ck('reward_ad_banner 被清', Object.keys(r.out.reward_ad_banner).length===0);
  ck('ads_banner 被清', Object.keys(r.out.ads_banner).length===0);
  ck('ad_snap 被清', Object.keys(r.out.ad_snap).length===0);
  ck('vip_banner 保留', r.out.vip_banner.image==='g');
  ck('free_vip_banner 保留', r.out.free_vip_banner.image==='h');
  console.log(r.logs.join('\n'));
}

console.log('\n== task/view: banner/popup ==');
{
  const r=run('https://api.qishui.com/luna/treasure/task/view',{
    task_infos:[{task_key:'sign_in'},{task_key:'reward_ads'}],
    banner_list:[{banner_type:'reward_ad'},{banner_type:'vip'}],
    popup_show_ad:{x:1},
    action_popup_show_ad:{x:2},
    popup_gain_ad_ent:{x:3},
    commerce_ad_task:{x:4}
  });
  ck('task 只留签到', r.out.task_infos.map(x=>x.task_key).join(',')==='sign_in');
  ck('banner 只留 vip', r.out.banner_list.map(x=>x.banner_type).join(',')==='vip');
  ck('ad popup 被清', Object.keys(r.out.popup_show_ad).length===0 && Object.keys(r.out.action_popup_show_ad).length===0);
  ck('commerce_ad_task 被清', Object.keys(r.out.commerce_ad_task).length===0);
}

console.log('\nPASS='+pass+' FAIL='+fail);
process.exit(fail?1:0);
