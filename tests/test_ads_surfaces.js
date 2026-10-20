const vm=require('vm');
const code=require('./load-script')('sanitize.js');
function run(url, body){
  let done=null; const logs=[];
  const ctx={$request:{url},$response:{body:JSON.stringify(body)},$done:x=>{done=x},
    console:{log:(...a)=>logs.push(a.join(' '))},JSON,Set,Array,Object,String,Number,Boolean,Math,Error,Date,isFinite};
  vm.runInNewContext(code,ctx,{timeout:3000});
  return {done,logs,out:done&&done.body?JSON.parse(done.body):null};
}
let pass=0,fail=0;
function ck(n,c,e){c?(pass++,console.log('  PASS  '+n)):(fail++,console.log('  FAIL  '+n+(e!==undefined?' got='+JSON.stringify(e):'')))}

console.log('\n== 1. 开屏 ad_launch_list ==');
{
  const r=run('https://api.qishui.com/luna/advert/splash/brand/retrieve',{
    status_code:0,status_info:'',request_id:'r1',
    ad_launch_list:[{launch_id:'1',ad_price:10}],ad_launch:{launch_id:'2'}
  });
  ck('ad_launch_list -> []', Array.isArray(r.out.ad_launch_list)&&r.out.ad_launch_list.length===0, r.out.ad_launch_list);
  ck('ad_launch -> {}', r.out.ad_launch && Object.keys(r.out.ad_launch).length===0, r.out.ad_launch);
  ck('status_code 保留', r.out.status_code===0);
  ck('request_id 保留', r.out.request_id==='r1');
  console.log(r.logs.join('\n'));
}

console.log('\n== 2. 广告位配置 ==');
{
  const r=run('https://api.qishui.com/luna/ads/config',{
    status_code:0,expires_at:1700000000,
    ad_unit_configs:[{slot_id:'1'}],splash_config:{daily_splash_show_limit:3},
    feed_ads_config:{enable:true},reward_config:{reward_duration:30},preload:true
  });
  ck('ad_unit_configs -> []', Array.isArray(r.out.ad_unit_configs)&&r.out.ad_unit_configs.length===0);
  ck('splash_config -> {}', r.out.splash_config && Object.keys(r.out.splash_config).length===0);
  ck('feed_ads_config -> {}', r.out.feed_ads_config && Object.keys(r.out.feed_ads_config).length===0);
  ck('reward_config -> {}', r.out.reward_config && Object.keys(r.out.reward_config).length===0);
  ck('preload -> false', r.out.preload===false, r.out.preload);
  ck('expires_at 延长', r.out.expires_at>1700000000, r.out.expires_at);
  console.log(r.logs.join('\n'));
}

console.log('\n== 3. ads/retrieve 广告对象 ==');
{
  const r=run('https://api.qishui.com/luna/ads/retrieve',{
    status_code:0,slot_id:'s1',
    ad_launch_list:[{launch_id:'1'}],ad_launch:{launch_id:'2'},
    ads_blocks:[{id:'ad1'}],ads_info:{is_ad:true},normal:'keep'
  });
  ck('ad_launch_list -> []', Array.isArray(r.out.ad_launch_list)&&r.out.ad_launch_list.length===0);
  ck('ad_launch -> {}', r.out.ad_launch && Object.keys(r.out.ad_launch).length===0);
  ck('ads_blocks -> []', Array.isArray(r.out.ads_blocks)&&r.out.ads_blocks.length===0);
  ck('ads_info -> {}', r.out.ads_info && Object.keys(r.out.ads_info).length===0);
  ck('普通字段保留', r.out.normal==='keep');
  console.log(r.logs.join('\n'));
}

console.log('\n== 4. 信息流：丢 is_ad，清 ads_blocks ==');
{
  const r=run('https://api.qishui.com/luna/feed/song-tab',{
    status_code:0,
    data:[
      {id:'1',is_ad:true,ad_info:{brand_name:'X'}},
      {id:'2',video:{vid:'v'},ads_blocks:[{id:'ad1'}]},
      {id:'3',track:{id:'s'},ad_info:{foo:'bar'}},
      {id:'4',is_ad:false,video:{vid:'v2'}}
    ]
  });
  const ids=r.out.data.map(x=>x.id);
  ck('is_ad=true 条目被删', ids.join(',')==='2,3,4', ids);
  ck('ads_blocks 被清', Array.isArray(r.out.data[0].ads_blocks)&&r.out.data[0].ads_blocks.length===0);
  ck('有 track 的条目保留', ids.includes('3'));
  ck('ad_info 被清', r.out.data[1].ad_info && Object.keys(r.out.data[1].ad_info).length===0);
  ck('正常条目保留', ids.includes('4'));
  console.log(r.logs.join('\n'));
}

console.log('\n== 5. fastReject：无广告标记直接放行 ==');
{
  const r=run('https://api.qishui.com/luna/feed/song-tab',{
    status_code:0,data:[{id:'1',video:{vid:'v'}}]
  });
  ck('不改 body', r.done && r.done.body===undefined, r.done);
  ck('日志 no ad marker', r.logs.join(' ').includes('no ad marker'), r.logs.join(' '));
}

console.log('\n== 6. is_ad 兼容 1 / "true" ==');
{
  const r=run('https://api.qishui.com/luna/search/track',{
    data:[{id:'1',is_ad:1,ad_info:{}},{id:'2',is_ad:'true'},{id:'3',is_ad:false,video:{}}]
  });
  const ids=r.out.data.map(x=>x.id);
  ck('1/true 被删', ids.join(',')==='3', ids);
}

console.log('\n== 7. upsell card ==');
{
  const r=run('https://api.qishui.com/luna/commerce/v2/upsell',{
    status_code:0,card:{title:'VIP'},countdown:5,upsell_unique_name:'u1'
  });
  ck('card -> {}', r.out.card && Object.keys(r.out.card).length===0);
  ck('upsell_unique_name -> null', r.out.upsell_unique_name===null, r.out.upsell_unique_name);
  ck('countdown 保留', r.out.countdown===5);
}

console.log('\n== 8. 福利任务不受影响 ==');
{
  const r=run('https://api.qishui.com/luna/treasure/task/view',{
    status_code:0,task_infos:[{task_key:'reward_ads'},{task_key:'sign_in'},{task_key:'listen_duration'}]
  });
  const keys=r.out.task_infos.map(x=>x.task_key);
  ck('只摘 reward_ads', keys.join(',')==='sign_in,listen_duration', keys);
}

console.log('\n== 9. ads/retrieve 嵌套 ad config ==');
{
  const r=run('https://api.qishui.com/luna/ads/retrieve',{
    status_code:0,
    adn_group_config:[{id:'g1'}],
    commerce_libra_ad_config:{a:1},
    commerce_common_ad_config:{b:1},
    ad_ignore_player_status_config:{c:1},
    splash_dsp_config:{d:1},
    preload_dsp_config:{e:1},
    splash_mannor_config:{f:1},
    normal:'keep'
  });
  const keys=['adn_group_config','commerce_libra_ad_config','commerce_common_ad_config',
    'ad_ignore_player_status_config','splash_dsp_config','preload_dsp_config','splash_mannor_config'];
  ck('嵌套 ad config 被清',
    keys.every(k=>Array.isArray(r.out[k])?r.out[k].length===0:Object.keys(r.out[k]).length===0),
    JSON.stringify(keys.map(k=>[k,r.out[k]])));
  ck('normal 保留', r.out.normal==='keep');
}

console.log('\n== 10. 兜底广告 / 卡片广告 / 增长入口 ==');
{
  const f=run('https://api.qishui.com/luna/advert/fallback/done/info',{
    status_code:0,
    ad_launch_list:[{launch_id:'f1'}],
    normal:'keep'
  });
  ck('fallback ad_launch_list 被清',
    Array.isArray(f.out.ad_launch_list)&&f.out.ad_launch_list.length===0,
    f.out.ad_launch_list);
  ck('fallback normal 保留', f.out.normal==='keep');

  const c=run('https://api.qishui.com/luna/card',{
    data:[{id:'ad1',is_ad:true,ad_info:{}},{id:'c2',track:{id:'t'}}]
  });
  ck('card 广告条目被删', c.out.data.map(x=>x.id).join(',')==='c2', c.out.data);

  const g=run('https://api.qishui.com/luna/growth/activity_entrance',{
    reward_ad_banner:{id:'r'},
    banner_list:[{banner_type:'ads_banner',id:'a'},{banner_type:'sign_in',id:'s'}],
    normal:'keep'
  });
  ck('growth 广告 banner 被清，正常 banner 保留',
    Object.keys(g.out.reward_ad_banner).length===0 &&
    g.out.banner_list.map(x=>x.banner_type).join(',')==='sign_in',
    {banner:g.out.banner_list,reward:g.out.reward_ad_banner});
}

console.log('\nPASS='+pass+' FAIL='+fail);
process.exit(fail?1:0);
