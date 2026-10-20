const vm = require('vm');
const code = require('./load-script')('sanitize.js');

function run(url, body) {
  let doneArg = null;
  const logs = [];
  const ctx = {
    $argument: {rewardSafe: false, cleanAds: true},
    $request: { url },
    $response: { body: typeof body === 'string' ? body : JSON.stringify(body) },
    $done: (x) => { doneArg = x; },
    console: { log: (...a) => logs.push(a.join(' ')) },
    JSON, Set, Array, Object, String, Number, Boolean, Math, Error, Date, isFinite
  };
  vm.runInNewContext(code, ctx, { timeout: 2000 });
  return { done: doneArg, logs };
}
let pass = 0, fail = 0;
function check(name, cond, extra) {
  if (cond) { pass++; console.log('  PASS  ' + name); }
  else { fail++; console.log('  FAIL  ' + name + (extra ? '  got=' + extra : '')); }
}

const nowS = Math.floor(Date.now()/1000);
const nowMs = Date.now();

console.log('\n== 1. config: 错误码 + 短过期(秒) ==');
{
  const r = run('https://api.qishui.com/luna/advert/incentive/config', {
    status_code: 10001, status_info: 'freq limit',
    advert_sources: [{rit: 1}], feed_advert_config: {enable: true},
    expire_time: nowS + 60, preload: true
  });
  const o = JSON.parse(r.done.body);
  check('status_code -> 0', o.status_code === 0, o.status_code);
  check('status_info -> ""', o.status_info === '', JSON.stringify(o.status_info));
  check('advert_sources -> []', Array.isArray(o.advert_sources) && o.advert_sources.length === 0);
  check('feed_advert_config -> {}', o.feed_advert_config && Object.keys(o.feed_advert_config).length === 0);
  check('preload -> false', o.preload === false, o.preload);
  check('expire_time 延长 >= 6.9d', o.expire_time >= nowS + 6.9*86400, o.expire_time);
  check('expire_time 不是毫秒', o.expire_time < 1e11, o.expire_time);
  console.log(r.logs.join('\n'));
}

console.log('\n== 2. config: 毫秒时间戳 ==');
{
  const r = run('https://api.qishui.com/luna/advert/incentive/config', {
    status_code: 0, status_info: '', advert_sources: [{a:1}], feed_advert_config: {},
    expire_time: nowMs + 60000, preload: false
  });
  const o = JSON.parse(r.done.body);
  check('expire_time 仍为毫秒且延长', o.expire_time > 1e11 && o.expire_time >= nowMs + 6.9*86400*1000, o.expire_time);
}

console.log('\n== 3. retrieve: ad_infos_map + ad_infos ==');
{
  const r = run('https://api.qishui.com/luna/advert/incentive/retrieve', {
    status_code: 0, status_info: '',
    ad_infos_map: {scene_a: {id: 1}}, ad_infos: [{id: 2}],
    expire_time: nowS + 60
  });
  const o = JSON.parse(r.done.body);
  check('ad_infos_map -> {}', o.ad_infos_map && Object.keys(o.ad_infos_map).length === 0);
  check('ad_infos -> []', Array.isArray(o.ad_infos) && o.ad_infos.length === 0);
  check('expire_time 延长', o.expire_time >= nowS + 6.9*86400);
}

console.log('\n== 4. 已是干净状态 -> 不改写 ==');
{
  const r = run('https://api.qishui.com/luna/advert/incentive/config', {
    status_code: 0, status_info: '', advert_sources: [], feed_advert_config: {},
    expire_time: nowS + 30*86400, preload: false
  });
  check('无 body（放行）', !(r.done && r.done.body), JSON.stringify(r.done));
  check('日志 already clean', r.logs.join(' ').includes('already clean'), r.logs.join(' '));
}

console.log('\n== 5. incentive/done 不动 ==');
{
  const body = {status_code:0,status_info:'',reward_details:{coin:100},reward_tips:{t:'x'}};
  const r = run('https://api.qishui.com/luna/advert/incentive/done', body);
  check('无 body（放行）', !(r.done && r.done.body));
}

console.log('\n== 6. TTL 语义（expire_time=300） ==');
{
  const r = run('https://api.qishui.com/luna/advert/incentive/config', {
    status_code: 0, status_info: '', advert_sources: [], feed_advert_config: {},
    expire_time: 300, preload: false
  });
  const o = JSON.parse(r.done.body);
  check('TTL 被拉到 now+7d', o.expire_time >= nowS + 6.9*86400, o.expire_time);
}

console.log('\n== 7. upsell 仍正常 ==');
{
  const r = run('https://api.qishui.com/luna/commerce/upsells', {
    status_code: 0, status_info: '', data: {upsells: [{id:1}], show: true}
  });
  const o = JSON.parse(r.done.body);
  check('upsells -> []', o.data.upsells.length === 0);
  check('show -> false', o.data.show === false);
}

console.log('\n== 8. 畸形 JSON 放行 ==');
{
  const r = run('https://api.qishui.com/luna/advert/incentive/config', '{oops');
  check('无 body', !(r.done && r.done.body));
}

console.log('\n== 9. 非激励端点不误伤 ==');
{
  const r = run('https://api.qishui.com/luna/me/profile', {status_code:0,data:{name:'x',ads:[]}});
  check('无 body', !(r.done && r.done.body));
}

console.log('\n----------------------------------------');
console.log('PASS=' + pass + '  FAIL=' + fail);
process.exit(fail ? 1 : 0);
