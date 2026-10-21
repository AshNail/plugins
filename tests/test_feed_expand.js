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

console.log('\n== me/discover: is_ad ==');
{
  const r=run('https://api.qishui.com/luna/me/discover',{
    data:[{id:'1',is_ad:true,ad_info:{}},{id:'2',video:{vid:'v'}}]
  });
  ck('广告条目被删', r.out.data.map(x=>x.id).join(',')==='2', r.out.data);
}

console.log('\n== playlist/detail: ads_blocks ==');
{
  const r=run('https://api.qishui.com/luna/playlist/detail',{
    status_code:0,playlist:{id:'p1'},ads_blocks:[{id:'ad1'}]
  });
  ck('ads_blocks 被清', Array.isArray(r.out.ads_blocks)&&r.out.ads_blocks.length===0);
  ck('playlist 保留', r.out.playlist.id==='p1');
}

console.log('\n== feed: video_end_ad / feed_ads / banner_list ==');
{
  const r=run('https://api.qishui.com/luna/feed/song-tab',{
    status_code:0,
    video_end_ad:{id:'end'},
    feed_ads:[{id:'f1'}],
    feed_reward_ad_entrance:{id:'ent'},
    banner_list:[{banner_type:'reward_ad'},{banner_type:'vip'}],
    data:[{id:'1',video:{vid:'v'}}]
  });
  ck('video_end_ad 被清', Object.keys(r.out.video_end_ad).length===0);
  ck('feed_ads 被清', Array.isArray(r.out.feed_ads)&&r.out.feed_ads.length===0);
  ck('feed_reward_ad_entrance 被清', Object.keys(r.out.feed_reward_ad_entrance).length===0);
  ck('广告 banner 被删', r.out.banner_list.map(x=>x.banner_type).join(',')==='vip', r.out.banner_list);
}

console.log('\n== featured-content: ads_info ==');
{
  const r=run('https://api.qishui.com/luna/featured-content/list',{
    data:[{id:'1',ads_info:{ad_id:'a'}},{id:'2',title:'keep'}]
  });
  ck('ads_info 被清', Object.keys(r.out.data[0].ads_info).length===0);
  ck('正常条目保留', r.out.data[1].title==='keep');
}

console.log('\n== playlist/related_media: ads_blocks ==');
{
  const r=run('https://api.qishui.com/luna/playlist/related_media',{
    media_list:[{id:'m1',ads_blocks:[{id:'ad'}]}]
  });
  ck('ads_blocks 被清', Array.isArray(r.out.media_list[0].ads_blocks)&&r.out.media_list[0].ads_blocks.length===0);
}

console.log('\n== discover/mix 与 playlist/search 仍生效 ==');
{
  const r1=run('https://api.qishui.com/luna/discover/mix',{
    data:[{id:'1',is_ad:true},{id:'2',title:'keep'}]
  });
  ck('discover/mix 广告条目被删', r1.out.data.map(x=>x.id).join(',')==='2', r1.out.data);

  const r2=run('https://api.qishui.com/luna/playlist/search',{
    data:[{id:'1',ads_blocks:[{id:'ad'}]},{id:'2',title:'keep'}]
  });
  ck('playlist/search ads_blocks 被清', Array.isArray(r2.out.data[0].ads_blocks)&&r2.out.data[0].ads_blocks.length===0, r2.out.data[0]);
}

console.log('\n== 非目标端点不碰 ==');
{
  const r=run('https://api.qishui.com/luna/me/playlist',{
    ads_blocks:[{id:'ad1'}],data:[{id:'1',is_ad:true}]
  });
  ck('未改写', r.done && r.done.body===undefined, r.done);
}

console.log('\n== search-block: 只有 banner_list 也要解析 ==');
{
  const r=run('https://api.qishui.com/luna/search-block',{
    banner_list:[{banner_type:'reward_ad',id:'a'},{banner_type:'vip',id:'b'}],
    normal:'keep'
  });
  ck('search-block 广告 banner 被删',
    r.out.banner_list.map(x=>x.banner_type).join(',')==='vip',
    r.out.banner_list);
  ck('search-block normal 保留', r.out.normal==='keep');
}

console.log('\n== search/track 仍生效 ==');
{
  const r=run('https://api.qishui.com/luna/search/track',{
    data:[{id:'1',is_ad:true},{id:'2',title:'keep'}]
  });
  ck('广告条目被删', r.out.data.map(x=>x.id).join(',')==='2');
}

console.log('\nPASS='+pass+' FAIL='+fail);
process.exit(fail?1:0);
