/*
 * soda · commerce/v2/upsell 的 upsell_map 精确清理
 * 真样本：tests/fixtures/douyin_upsell.json（beta-luna 2026-10-20 HAR，93 个弹窗）
 * 与 douyin.plugin 共用同一套 luna commerce 响应结构。
 */
const load = require("./load-script");
const code = load("sanitize.js");

const UPSELL = "https://api.qishui.com/luna/commerce/v2/upsell";
const CLEAN = { rewardSafe: false, cleanAds: true, killRewardAds: false, hideDouyinTab: false };

function run(body, argument, url) {
  let out = null;
  const logs = [];
  const fn = new Function(
    "$request", "$response", "$done", "console", "$argument", code
  );
  fn(
    { url: url || UPSELL },
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

const real = require("./fixtures/douyin_upsell.json");
const REAL_NAMES = Object.keys(real.upsell_map);

const SHOULD_REMOVE = [
  "ad_incentive_backup_card",
  "ads_close_persuade_vip_popup",
  "background_to_front_popup_ads",
  "background_voice_prompt_ad",
  "browse_mall_popup_acc_amount",
  "cold_launch_popup_ads_future",
  "cold_launch_popup_ads_progress",
  "freevip_close_persuade_ads_popup",
  "high_value_preview_popup_ads_block",
  "high_value_preview_popup_ads_nonblock",
  "me_tab_reward_ad_banner",
  "preview_popup_ads",
  "preview_popup_downgrade_snackbar_ads",
  "preview_snackbar_ads_block",
  "preview_snackbar_ads_nonblock",
  "reward_ad_cold_launch_popup",
  "rewind_previous_preview_popup_ads",
  "vip_close_persuade_ads_popup"
];

const MUST_KEEP = [
  "reward_video_load_fail_compensate",
  "reward_video_load_fail_retry",
  "reward_task_dialog_active",
  "reward_task_dialog_passive",
  "reward_cool_down_popup",
  "feed_listen_music_reward_popup",
  "feed_treasure_box_reward_popup",
  "treasure_guide_reward_acc_popup",
  "task_page_svip_popup",
  "coin_widget",
  "treasure_svip_withdraw_banner"
];

console.log("\n== 1. 真实 upsell 样本（93 个弹窗）==");
{
  check("样本弹窗数 = 93", REAL_NAMES.length === 93, String(REAL_NAMES.length));
  const r = run(real, CLEAN);
  const o = parse(r.out);
  check("返回了改写后的响应", !!o, JSON.stringify(r.out));
  const names = o ? Object.keys(o.upsell_map) : [];
  check("弹窗数从 93 降到 " + (93 - SHOULD_REMOVE.length),
    names.length === 93 - SHOULD_REMOVE.length, String(names.length));
  check("status_code 保留", o && o.status_code === 0, o && o.status_code);
}

console.log("\n== 2. 广告类 + 商城弹窗被删 ==");
{
  const o = parse(run(real, CLEAN).out);
  const names = o ? Object.keys(o.upsell_map) : [];
  for (const n of SHOULD_REMOVE) {
    check("已删 " + n, names.indexOf(n) === -1);
  }
}

console.log("\n== 3. 奖励/发奖/福利页入口弹窗保留 ==");
{
  const o = parse(run(real, CLEAN).out);
  const names = o ? Object.keys(o.upsell_map) : [];
  for (const n of MUST_KEEP) {
    check("保留 " + n, names.indexOf(n) !== -1, names.slice(0, 10).join(","));
  }
}

console.log("\n== 4. variables / libra_params_map 不动 ==");
{
  const o = parse(run(real, CLEAN).out);
  check("variables 值不变",
    o && JSON.stringify(o.variables) === JSON.stringify(real.variables));
  check("libra_params_map 不动",
    o && JSON.stringify(o.libra_params_map) === JSON.stringify(real.libra_params_map));
}

console.log("\n== 5. 排序 / 冷启动引用同步清理 ==");
{
  const o = parse(run(real, CLEAN).out);
  const sort = (o && o.sort_control_unique_names) || [];
  const cold = (o && o.cold_launch_timing &&
    o.cold_launch_timing.upsell_item_unique_names) || [];
  check("sort 只剩非广告条目", sort.length === 6, String(sort.length));
  check("sort 无广告/商城条目",
    sort.every((n) => n.indexOf("_ads_") === -1 && n.indexOf("_ad_") === -1 &&
      n !== "browse_mall_popup_acc_amount"),
    JSON.stringify(sort));
  check("冷启动只剩非广告条目", cold.length === 20, String(cold.length));
  check("冷启动里的广告弹窗（只出现在列表）也被清掉",
    cold.indexOf("cold_launch_popup_ads_text") === -1, JSON.stringify(cold));
  check("VIP 弹窗引用保留",
    sort.indexOf("cold_launch_popup_vip") !== -1 &&
    sort.indexOf("preview_popup_vip") !== -1, JSON.stringify(sort));
}

console.log("\n== 6. 频控表只删同名项 ==");
{
  const o = parse(run(real, CLEAN).out);
  const fmap = (o && o.freq_ctrl_cfg && o.freq_ctrl_cfg.freq_ctrl_map) || {};
  const names = Object.keys(fmap);
  check("频控表 82 -> 79", names.length === 79, String(names.length));
  check("ads_close_persuade_vip_popup 频控已删",
    names.indexOf("ads_close_persuade_vip_popup") === -1);
  check("background_voice_prompt_ad 频控已删",
    names.indexOf("background_voice_prompt_ad") === -1);
  check("vip_close_persuade_ads_popup 频控已删",
    names.indexOf("vip_close_persuade_ads_popup") === -1);
  check("共享键 background_voice_prompt 保留",
    names.indexOf("background_voice_prompt") !== -1);
  check("非弹窗键 widget_ad 保留", names.indexOf("widget_ad") !== -1);
  check("奖励弹窗频控 coin_guided_login_popup 保留",
    names.indexOf("coin_guided_login_popup") !== -1);
}

console.log("\n== 7. 只有 upsell_map 的响应也能命中（fastReject 标记）==");
{
  const body = {
    status_code: 0,
    upsell_map: { ads_foo: { a: 1 }, reward_x: { b: 2 } },
    sort_control_unique_names: ["ads_foo", "reward_x"],
    cold_launch_timing: { upsell_item_unique_names: ["ads_foo", "reward_x"] },
    freq_ctrl_cfg: { freq_ctrl_map: { ads_foo: { day_max_cnt: 1 }, reward_x: { day_max_cnt: 1 } } }
  };
  const r = run(body, CLEAN);
  const o = parse(r.out);
  check("处理了响应", !!o, JSON.stringify(r.out));
  check("ads_foo 实体已删", o && !o.upsell_map.ads_foo);
  check("reward_x 实体保留", o && !!o.upsell_map.reward_x);
  check("sort 只剩 reward_x",
    o && JSON.stringify(o.sort_control_unique_names) === '["reward_x"]');
  check("冷启动只剩 reward_x",
    o && JSON.stringify(o.cold_launch_timing.upsell_item_unique_names) === '["reward_x"]');
  check("频控只剩 reward_x",
    o && JSON.stringify(Object.keys(o.freq_ctrl_cfg.freq_ctrl_map)) === '["reward_x"]');
}

console.log("\n== 8. 没有广告弹窗：不写 body ==");
{
  const r = run({
    status_code: 0,
    upsell_map: { reward_x: { b: 2 } },
    sort_control_unique_names: ["reward_x"]
  }, CLEAN);
  check("不改写响应", !(r.out && r.out.body), JSON.stringify(r.out));
}

console.log("\n== 9. rewardSafe=true：upsell 放行 ==");
{
  const r = run(real, { rewardSafe: true, cleanAds: true });
  check("不改写响应", !(r.out && r.out.body), JSON.stringify(r.out));
  check("标记 reward-safe",
    !!(r.out && r.out.headers && /reward-safe/.test(r.out.headers["X-Soda-Plugin"] || "")),
    JSON.stringify(r.out));
}

console.log("\n" + (fail === 0 ? "ALL PASS" : "FAILURES") +
  "  pass=" + pass + " fail=" + fail);
process.exit(fail === 0 ? 0 : 1);
