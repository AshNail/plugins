const vm = require('vm');
const code = require('./load-script')('sanitize.js');

function run(url, body) {
  let doneArg = null; const logs = [];
  const ctx = {
    $request: { url },
    $response: { body: typeof body === 'string' ? body : JSON.stringify(body) },
    $done: (x) => { doneArg = x; },
    console: { log: (...a) => logs.push(a.join(' ')) },
    JSON, Set, Array, Object, String, Number, Boolean, Math, Error, Date, isFinite
  };
  vm.runInNewContext(code, ctx, { timeout: 2000 });
  return { done: doneArg, logs };
}
let pass=0, fail=0;
function check(n,c,e){ if(c){pass++;console.log('  PASS  '+n)}else{fail++;console.log('  FAIL  '+n+(e?'  got='+e:''))} }

console.log('\n== 1. 福利入口：只摘 incentive 标签 ==');
{
  const r = run('https://api.qishui.com/luna/treasure/entrance/config', {
    status_code: 0,
    labels: [
      { id: 'luna_treasure_guide_incentive_ad', text: '看视频领福利' },
      { id: 'sign_in', text: '签到' },
      { id: 'listen', text: '听歌任务' }
    ]
  });
  const o = JSON.parse(r.done.body);
  check('只剩 2 个标签', o.labels.length === 2, JSON.stringify(o.labels));
  check('签到保留', o.labels.some(x => x.id === 'sign_in'));
  check('听歌保留', o.labels.some(x => x.id === 'listen'));
  check('incentive 被摘', !o.labels.some(x => /incentive/.test(x.id)));
  console.log(r.logs.join('\n'));
}

console.log('\n== 2. 任务列表：只摘 reward_ads ==');
{
  const r = run('https://api.qishui.com/luna/treasure/task/view', {
    status_code: 0,
    data: { tasks: [
      { task_key: 'reward_ads', title: '看广告得金币' },
      { task_key: 'sign_in', title: '每日签到' },
      { task_key: 'listen_duration', title: '听歌 15 分钟' },
      { task_key: 'share', title: '分享单曲' }
    ]}
  });
  const o = JSON.parse(r.done.body);
  const keys = o.data.tasks.map(t => t.task_key);
  check('reward_ads 被摘', !keys.includes('reward_ads'), keys.join(','));
  check('sign_in 保留', keys.includes('sign_in'));
  check('listen_duration 保留', keys.includes('listen_duration'));
  check('share 保留', keys.includes('share'));
  console.log(r.logs.join('\n'));
}

console.log('\n== 3. task/view data 直接是数组 ==');
{
  const r = run('https://api.qishui.com/luna/treasure/task/view', {
    status_code: 0,
    data: [
      { task_key: 'reward_ad', title: '看视频免费畅听' },
      { task_key: 'browse_mall', title: '逛商城' }
    ]
  });
  const o = JSON.parse(r.done.body);
  check('只留 browse_mall', o.data.length === 1 && o.data[0].task_key === 'browse_mall', JSON.stringify(o.data));
}

console.log('\n== 4. 没有广告任务 -> 放行 ==');
{
  const r = run('https://api.qishui.com/luna/treasure/task/view', {
    status_code: 0, data: { tasks: [{ task_key: 'sign_in' }, { task_key: 'share' }] }
  });
  check('无 body', !(r.done && r.done.body));
  check('日志 clean', r.logs.join(' ').includes('already clean'), r.logs.join(' '));
}

console.log('\n== 5. 激励配置仍正常 ==');
{
  const r = run('https://api.qishui.com/luna/advert/incentive/config', {
    status_code: 0, status_info: '', advert_sources: [{rit:1}], feed_advert_config: {},
    expire_time: Math.floor(Date.now()/1000)+60, preload: true
  });
  const o = JSON.parse(r.done.body);
  check('advert_sources -> []', o.advert_sources.length === 0);
  check('preload -> false', o.preload === false);
}

console.log('\n----------------------------------------');
console.log('PASS='+pass+'  FAIL='+fail);
process.exit(fail?1:0);
