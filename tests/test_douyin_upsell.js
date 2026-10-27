const load = require("./load-script");
const code = load("clean.js", "douyin");

const UPSELL = "https://beta-luna.douyin.com/luna/commerce/v2/upsell";

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

/* 规则应当删掉的（广告类 + 商城） */
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

/* 必须保留的（奖励/发奖/福利页入口/兜底补偿） */
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
  const r = run(real, { cleanUpsell: true });
  const o = parse(r.out);
  check("返回了改写后的响应", !!o, JSON.stringify(r.out));
  const names = Object.keys(o.upsell_map);
  check("弹窗数从 93 降到 " + (93 - SHOULD_REMOVE.length),
    names.length === 93 - SHOULD_REMOVE.length, String(names.length));
}

console.log("\n== 2. 广告类 + 商城弹窗被删 ==");
{
  const o = parse(run(real, { cleanUpsell: true }).out);
  const names = Object.keys(o.upsell_map);
  for (const n of SHOULD_REMOVE) {
    check("已删 " + n, names.indexOf(n) === -1);
  }
}

console.log("\n== 3. 奖励/发奖/福利页入口弹窗保留 ==");
{
  const o = parse(run(real, { cleanUpsell: true }).out);
  const names = Object.keys(o.upsell_map);
  for (const n of MUST_KEEP) {
    check("保留 " + n, names.indexOf(n) !== -1, names.slice(0, 10).join(","));
  }
}

console.log("\n== 4. variables / libra_params_map 不动 ==");
{
  const o = parse(run(real, { cleanUpsell: true }).out);
  check("variables 条数不变", Object.keys(o.variables).length === Object.keys(real.variables).length,
    String(Object.keys(o.variables).length));
  check("variables 值不变",
    JSON.stringify(o.variables) === JSON.stringify(real.variables));
  check("libra_params_map 不动",
    JSON.stringify(o.libra_params_map) === JSON.stringify(real.libra_params_map));
}

console.log("\n== 5. 排序/冷启动引用同步清理 ==");
{
  const o = parse(run(real, { cleanUpsell: true }).out);
  const removed = SHOULD_REMOVE;
  for (const n of removed) {
    if ((o.sort_control_unique_names || []).indexOf(n) !== -1) {
      check("sort 列表已清 " + n, false);
    }
    if ((o.cold_launch_timing.upsell_item_unique_names || []).indexOf(n) !== -1) {
      check("冷启动列表已清 " + n, false);
    }
  }
  const AD = /(^|_)ads?(_|$)/;
  const MALL = ["browse_mall_popup_acc_amount"];
  check("sort 列表无广告/商城条目",
    (o.sort_control_unique_names || []).every(
      (n) => !AD.test(n) && MALL.indexOf(n) === -1),
    JSON.stringify(o.sort_control_unique_names));
  check("冷启动列表无广告/商城条目",
    (o.cold_launch_timing.upsell_item_unique_names || []).every(
      (n) => !AD.test(n) && MALL.indexOf(n) === -1),
    JSON.stringify(o.cold_launch_timing.upsell_item_unique_names));
  check("冷启动里的广告弹窗（只出现在列表）也被清掉",
    (o.cold_launch_timing.upsell_item_unique_names || []).indexOf(
      "cold_launch_popup_ads_text") === -1,
    JSON.stringify(o.cold_launch_timing.upsell_item_unique_names));
}

console.log("\n== 5b. 频控表：只删与已删弹窗同名的条目 ==");
{
  const o = parse(run(real, { cleanUpsell: true }).out);
  const before = real.freq_ctrl_cfg.freq_ctrl_map;
  const freq = o.freq_ctrl_cfg.freq_ctrl_map;
  check("freq 条数 82 -> 79",
    Object.keys(before).length === 82 && Object.keys(freq).length === 79,
    String(Object.keys(freq).length));
  for (const n of ["ads_close_persuade_vip_popup", "background_voice_prompt_ad",
                   "vip_close_persuade_ads_popup"]) {
    check("已删同名频控 " + n, !(n in freq));
  }
  check("共享频控键 background_voice_prompt 保留", "background_voice_prompt" in freq);
  check("非 upsell 实体的 widget_ad 保留", "widget_ad" in freq);
  check("排序列表内普通弹窗频控保留", "coin_guided_login_popup" in freq);
}

console.log("\n== 6. cleanUpsell 关闭：原样放行 ==");
{
  const r = run(real, { cleanUpsell: false });
  check("不改写响应", !(r.out && r.out.body), JSON.stringify(r.out));
}

console.log("\n" + (fail === 0 ? "ALL PASS" : "FAILURES") +
  "  pass=" + pass + " fail=" + fail);
process.exit(fail === 0 ? 0 : 1);
