const load = require("./load-script");
const code = load("settings.js", "soda");

const URL = "https://conf.qishui.com/service/settings/v3/?device_id=x";

function run(body, argument) {
  let out = null;
  const logs = [];
  const fn = new Function(
    "$request", "$response", "$done", "console", "$argument", code
  );
  fn(
    { url: URL },
    { body: typeof body === "string" ? body : JSON.stringify(body) },
    (v) => { out = v; },
    { log: (...a) => logs.push(a.join(" ")) },
    argument
  );
  return { out, logs };
}

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

function parse(out) {
  if (!out || out.body === undefined) return null;
  try { return JSON.parse(out.body); } catch (e) { return null; }
}

function makeSettings() {
  return {
    status_code: 0,
    data: {
      settings: {
        anchor_luna_to_douyin: 1,
        anchor_luna_to_douyin_mv: 1,
        show_douyin_liked_video_switch: false,
        douyin_service_path_migration_switch: { enable: true },
        commerce_ad_config: { splash_ad_config: { allow_splash_ad_scene: 9 } },
        reward_ad_fallback_config: { toast_message: "广告加载失败，先去听歌吧" }
      }
    }
  };
}

console.log("\n== 1. hideDouyinEntry=true：关掉【听抖音】入口 ==");
{
  const r = run(makeSettings(), { hideDouyinEntry: true });
  const o = parse(r.out);
  check("返回了改写后的响应", !!o, JSON.stringify(r.out));
  check("anchor_luna_to_douyin -> 0",
    o && o.data.settings.anchor_luna_to_douyin === 0,
    o ? String(o.data.settings.anchor_luna_to_douyin) : "");
  check("anchor_luna_to_douyin_mv -> 0",
    o && o.data.settings.anchor_luna_to_douyin_mv === 0,
    o ? String(o.data.settings.anchor_luna_to_douyin_mv) : "");
}

console.log("\n== 2. hideDouyinEntry 不动其它设置 ==");
{
  const r = run(makeSettings(), { hideDouyinEntry: true });
  const o = parse(r.out);
  check("广告配置不动（不碰 cleanAds 行为）",
    o && !!o.data.settings.commerce_ad_config.splash_ad_config,
    o ? JSON.stringify(o.data.settings.commerce_ad_config) : "");
  check("迁移开关不动",
    o && o.data.settings.douyin_service_path_migration_switch.enable === true);
  check("分享配置不动", o && o.data.settings.show_douyin_liked_video_switch === false);
}

console.log("\n== 3. hideDouyinEntry + rewardSafe=true：保奖励也能隐藏入口 ==");
{
  const r = run(makeSettings(), { hideDouyinEntry: true, rewardSafe: true });
  const o = parse(r.out);
  check("入口仍然被关掉",
    o && o.data.settings.anchor_luna_to_douyin === 0,
    o ? String(o.data.settings.anchor_luna_to_douyin) : "");
  check("广告配置没被动（保奖励）",
    o && !!o.data.settings.commerce_ad_config.splash_ad_config);
}

console.log("\n== 4. settingsClean + rewardSafe=false：清广告配置 ==");
{
  const r = run(makeSettings(), { settingsClean: true, rewardSafe: false });
  const o = parse(r.out);
  check("commerce_ad_config -> {}",
    o && Object.keys(o.data.settings.commerce_ad_config).length === 0,
    o ? JSON.stringify(o.data.settings.commerce_ad_config) : "");
  check("reward_ad_fallback_config -> {}",
    o && Object.keys(o.data.settings.reward_ad_fallback_config).length === 0);
  check("【听抖音】入口未受影响",
    o && o.data.settings.anchor_luna_to_douyin === 1,
    o ? String(o.data.settings.anchor_luna_to_douyin) : "");
}

console.log("\n== 5. settingsClean + rewardSafe=true：保奖励优先，不清广告配置 ==");
{
  const r = run(makeSettings(), { settingsClean: true, rewardSafe: true });
  check("响应完全不改写（广告配置保持原样）", !(r.out && r.out.body), JSON.stringify(r.out));
  check("日志说明跳过广告配置清理",
    r.logs.join(" ").includes("skip ad-config cleanup"), r.logs.join(" "));
}

console.log("\n== 6. 两个开关都没开：原样放行 ==");
{
  const r = run(makeSettings(), {});
  check("不改写响应", !(r.out && r.out.body), JSON.stringify(r.out));
}

console.log("\n== 7. settingsClean + hideDouyinEntry 同开：一次调用两件事都做 ==");
{
  const r = run(makeSettings(), {
    rewardSafe: false,
    settingsClean: true,
    hideDouyinEntry: true
  });
  const o = parse(r.out);
  check("广告配置被清空",
    o && Object.keys(o.data.settings.commerce_ad_config).length === 0,
    o ? JSON.stringify(o.data.settings.commerce_ad_config) : "");
  check("【听抖音】入口被关掉",
    o && o.data.settings.anchor_luna_to_douyin === 0,
    o ? String(o.data.settings.anchor_luna_to_douyin) : "");
  check("两个开关同开不再互相吞掉", !!o, JSON.stringify(r.out));
}

console.log("\n" + (fail === 0 ? "ALL PASS" : "FAILURES") +
  "  pass=" + pass + " fail=" + fail);
process.exit(fail === 0 ? 0 : 1);
