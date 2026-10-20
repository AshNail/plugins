const sanitize = require("./load-script")("sanitize.js");
const settings = require("./load-script")("settings.js");

let pass = 0, fail = 0;
function check(name, cond, extra) {
  if (cond) {
    pass++;
    console.log("  PASS  " + name);
  } else {
    fail++;
    console.log("  FAIL  " + name + (extra ? "  got=" + extra : ""));
  }
}

function runSanitize(url, body, argument) {
  let out = null;
  const logs = [];
  const fn = new Function(
    "$request", "$response", "$done", "console", "$argument", sanitize
  );
  fn(
    { url },
    { body: typeof body === "string" ? body : JSON.stringify(body) },
    (v) => { out = v; },
    { log: (...a) => logs.push(a.join(" ")) },
    argument
  );
  return { out, logs };
}

function runSettings(body, argument) {
  let out = null;
  const logs = [];
  const fn = new Function(
    "$request", "$response", "$done", "console", "$argument", settings
  );
  fn(
    { url: "https://conf.qishui.com/service/settings/v3/?device_id=x" },
    { body: typeof body === "string" ? body : JSON.stringify(body) },
    (v) => { out = v; },
    { log: (...a) => logs.push(a.join(" ")) },
    argument
  );
  return { out, logs };
}

function hasBody(result) {
  return !!(result.out && result.out.body);
}

const nowS = Math.floor(Date.now() / 1000);

console.log("\n== 1. rewardSafe=true：非开屏端点直接放行 ==");
{
  const body = {
    status_code: 10001,
    status_info: "freq limit",
    advert_sources: [{ id: 1 }],
    feed_advert_config: { enable: true },
    expire_time: nowS + 60,
    preload: true
  };
  const r = runSanitize(
    "https://api.qishui.com/luna/advert/incentive/config",
    body,
    { rewardSafe: true, cleanAds: true }
  );
  check("incentive/config 不改写", !hasBody(r), JSON.stringify(r.out));
  check("日志说明 rewardSafe", r.logs.join(" ").includes("rewardSafe=on"), r.logs.join(" "));
}

console.log("\n== 2. rewardSafe=true：开屏品牌广告仍然清理 ==");
{
  const body = {
    status_code: 0,
    ad_launch_list: [{ id: 1 }],
    expire_time: nowS + 60
  };
  const r = runSanitize(
    "https://api.qishui.com/luna/advert/splash/brand/retrieve",
    body,
    { rewardSafe: true, cleanAds: true }
  );
  const o = r.out && r.out.body ? JSON.parse(r.out.body) : null;
  check("splash 返回改写后的 body", !!o, JSON.stringify(r.out));
  check("ad_launch_list -> []", o && Array.isArray(o.ad_launch_list) && o.ad_launch_list.length === 0,
    JSON.stringify(o));
}

console.log("\n== 3. rewardSafe=false + cleanAds=true：去广告脚本生效 ==");
{
  const body = {
    status_code: 10001,
    status_info: "freq limit",
    advert_sources: [{ id: 1 }],
    feed_advert_config: { enable: true },
    expire_time: nowS + 60,
    preload: true
  };
  const r = runSanitize(
    "https://api.qishui.com/luna/advert/incentive/config",
    body,
    { rewardSafe: false, cleanAds: true }
  );
  const o = r.out && r.out.body ? JSON.parse(r.out.body) : null;
  check("incentive/config 被清理", !!o, JSON.stringify(r.out));
  check("advert_sources -> []", o && Array.isArray(o.advert_sources) && o.advert_sources.length === 0,
    JSON.stringify(o));
  check("preload -> false", o && o.preload === false, o && o.preload);
}

console.log("\n== 4. 没有 $argument：按保守默认（rewardSafe=true）放行 ==");
{
  const body = {
    status_code: 10001,
    advert_sources: [{ id: 1 }],
    feed_advert_config: { enable: true },
    expire_time: nowS + 60,
    preload: true
  };
  const r = runSanitize(
    "https://api.qishui.com/luna/advert/incentive/config",
    body
  );
  check("无参数时不改写（不误伤奖励链路）", !(r.out && r.out.body), JSON.stringify(r.out));
}

console.log("\n== 5. settings：rewardSafe=true 时放行 ==");
{
  const body = {
    commerce_ad_config: { slots: [1, 2] },
    reward_ad_config: { enable: true },
    normal: "keep"
  };
  const r = runSettings(body, { rewardSafe: true, settingsClean: true });
  check("设置响应不改写", !hasBody(r), JSON.stringify(r.out));
  check("日志说明 rewardSafe", r.logs.join(" ").includes("rewardSafe=on"), r.logs.join(" "));
}

console.log("\n== 6. settings：rewardSafe=false 时正常清理 ==");
{
  const body = {
    commerce_ad_config: { slots: [1, 2] },
    reward_ad_config: { enable: true },
    normal: "keep"
  };
  const r = runSettings(body, { rewardSafe: false, settingsClean: true });
  const o = r.out && r.out.body ? JSON.parse(r.out.body) : null;
  check("设置响应被清理", !!o, JSON.stringify(r.out));
  check("commerce_ad_config -> {}", o && o.commerce_ad_config &&
    Object.keys(o.commerce_ad_config).length === 0, JSON.stringify(o));
  check("正常字段保留", o && o.normal === "keep", JSON.stringify(o));
}

console.log("\n== 7. hideDouyinTab：删除带“抖音”的条目 ==");
{
  const body = {
    status_code: 0,
    rewardAdBanner: { id: 1 },
    task_infos: [
      { task_key: "douyin_listen", title: "听抖音", reward_amount: 50 },
      { task_key: "sign_in", title: "签到", reward_amount: 10 },
      { task_key: "listen_duration", title: "听歌", reward_amount: 20 }
    ]
  };
  const r = runSanitize(
    "https://api.qishui.com/luna/treasure/task/view",
    body,
    { rewardSafe: false, cleanAds: true, hideDouyinTab: true }
  );
  const o = r.out && r.out.body ? JSON.parse(r.out.body) : null;
  check("抖音条目被删除",
    o && Array.isArray(o.task_infos) && o.task_infos.length === 2,
    JSON.stringify(o));
  check("签到/听歌保留",
    o && o.task_infos.every((t) => t.task_key !== "douyin_listen"),
    JSON.stringify(o));
}

console.log("\n== 8. hideDouyinTab 关闭时保留抖音条目 ==");
{
  const body = {
    status_code: 0,
    rewardAdBanner: { id: 1 },
    task_infos: [
      { task_key: "douyin_listen", title: "听抖音" },
      { task_key: "sign_in", title: "签到" }
    ]
  };
  const r = runSanitize(
    "https://api.qishui.com/luna/treasure/task/view",
    body,
    { rewardSafe: false, cleanAds: true, hideDouyinTab: false }
  );
  const o = r.out && r.out.body ? JSON.parse(r.out.body) : null;
  check("抖音条目保留",
    o && Array.isArray(o.task_infos) && o.task_infos.length === 2,
    JSON.stringify(o));
}

console.log("\n== 9. rewardSafe + hideDouyinTab：只删抖音，不动其它任务 ==");
{
  const body = {
    status_code: 0,
    task_infos: [
      { task_key: "douyin_listen", title: "听抖音" },
      { task_key: "reward_ads", title: "看广告得金币" }
    ]
  };
  const r = runSanitize(
    "https://api.qishui.com/luna/treasure/task/view",
    body,
    { rewardSafe: true, cleanAds: true, hideDouyinTab: true }
  );
  const o = r.out && r.out.body ? JSON.parse(r.out.body) : null;
  check("抖音条目被删除",
    o && Array.isArray(o.task_infos) && o.task_infos.length === 1,
    JSON.stringify(o));
  check("看广告任务保留（保奖励不受影响）",
    o && o.task_infos[0] && o.task_infos[0].task_key === "reward_ads",
    JSON.stringify(o));
}

console.log("\n" + (fail === 0 ? "ALL PASS" : "FAILURES") +
  "  pass=" + pass + " fail=" + fail);
process.exit(fail === 0 ? 0 : 1);
