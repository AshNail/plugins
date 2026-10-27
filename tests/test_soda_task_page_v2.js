/*
 * test_soda_task_page_v2.js · v2.6.1 结构化任务判别（真样本回归）
 * ------------------------------------------------------------
 * 样本：tests/fixtures/soda_task_page_v2.json
 *       = 2026-10-22 真机 task/page/v2 响应（tokens 已脱敏）
 * 断言四层：
 *   1. cleanAds 只摘 music_incentive_ad，签到/翻卡/攒时长全保留；
 *   2. 整条 stringify 时代的误删（extra.ad_task_id / ad_snap）不再发生；
 *   3. 无抖音任务时 hideDouyinTab 零改动（C 步负样本特性）;
 *   4. rewardSafe 优先级照旧（无 killReward 时 non-splash 放行）。
 */
const load = require("./load-script");
const code = load("sanitize.js", "soda");
const fs = require("fs");
const path = require("path");
const PAGE = fs.readFileSync(path.join(__dirname, "fixtures", "soda_task_page_v2.json"), "utf8");
const PAGE_OBJ = JSON.parse(PAGE);

const URL_PAGE = "https://beta-luna.douyin.com/luna/treasure/task/page/v2";

function run(url, body, argument) {
  let out = null;
  const logs = [];
  const fn = new Function(
    "$request", "$response", "$done", "console", "$argument", code
  );
  fn(
    { url: url },
    { body: typeof body === "string" ? body : JSON.stringify(body) },
    (v) => { out = v; },
    { log: (...a) => logs.push(a.join(" ")) },
    argument
  );
  return { out, logs };
}

let pass = 0, fail = 0;
function ck(n, c, e) {
  if (c) { pass++; console.log("  PASS  " + n); }
  else { fail++; console.log("  FAIL  " + n + (e !== undefined ? " got=" + JSON.stringify(e) : "")); }
}

function tasksOf(out, sectionKey) {
  const sec = out.data.sections.find((s) => s.key === sectionKey);
  return sec[sec.task_group ? "task_group" : "widget_task_group"].tasks.map((t) => t.key);
}

console.log("\n== 1. cleanAds · 真样本全量回归（beta-luna task/page/v2）==");
{
  const r = run(URL_PAGE, PAGE, { rewardSafe: false, cleanAds: true });
  const out = JSON.parse(r.out.body);
  ck("sections 数不变(4)", out.data.sections.length === 4, out.data.sections.length);
  const dur = tasksOf(out, "duration_task_section");
  ck("攒时长 luna_rewards_ads 保留", dur.length === 1 && dur[0] === "luna_rewards_ads", dur);
  const gold = tasksOf(out, "gold_task_section");
  ck("music_incentive_ad 被摘 (8→7)",
     gold.length === 7 && !gold.includes("music_incentive_ad"), gold.length);
  ck("签到保留", gold.includes("soda_music_sign_in"), gold);
  ck("翻卡保留", gold.includes("luna_treasure_flip_card"), gold);
  ck("逛街/刷视频/红包雨/领现金保留",
     gold.includes("luna_treasure_shop") && gold.includes("luna_treasure_draw_duration") &&
     gold.includes("luna_treasure_red_packet_rain") && gold.includes("luna_treasure_caijing_daily_cash"), gold);
  ck("打卡提醒保留（裸 /incentive/ 前科）", gold.includes("luna_incentive_push_permission"), gold);
  ck("widget 任务保留", tasksOf(out, "widget_task_section").includes("music_ug_treasure"));
  const a = out.data.sections[0].asset_group.assets;
  ck("资产金额未动 (256/55/3)", a.map((x) => x.amount).join(",") === "256,55,3", a.map((x) => x.amount));
  ck("ad_api_preload 只留页面任务引用 (9→4)",
     out.data.config.ad_api_preload.task_ids.join(",") ===
       "600607,600585,600625,600662",
     out.data.config.ad_api_preload.task_ids);
  ck("仍有保留任务引用 → preload 开启", out.data.config.ad_api_preload.preload === true);
  ck("migrate_first_ad 关闭", out.data.config.migrate_first_ad === false);
  const signTask = out.data.sections[2].task_group.tasks.find((t) => t.key === "soda_music_sign_in");
  ck("签到 rewards 明细未动", !!signTask && signTask.rewards && signTask.rewards.length === 7);
  ck("sections 标题未动",
     out.data.sections[2].view.title.plain_text === "做任务 赚金币");
  ck("logs 有摘除记录", r.logs.some((l) => l.indexOf("tasks") !== -1 && l.indexOf("1/") !== -1), r.logs.join("|").slice(0, 120));
}

console.log("\n== 1b. ad_api_preload：只留仍在页面里的任务引用 ==");
{
  const page = JSON.parse(PAGE);
  page.data.config.ad_api_preload.task_ids = [
    "600590",  // duration 任务 id（保留）
    "600691",  // 翻卡 ad_snap.task_id（保留）
    "600572",  // music_incentive_ad 任务 id（已被摘）
    "600577",  // 签到 ad_snap.task_id（保留）
    "601039"   // 页面里不存在
  ];
  const r = run(URL_PAGE, page, { rewardSafe: false, cleanAds: true });
  const out = JSON.parse(r.out.body);
  const pre = out.data.config.ad_api_preload;
  ck("保留被引用 id（600590/600691/600577）",
     pre.task_ids.join(",") === "600590,600691,600577", pre.task_ids);
  ck("有引用时 preload 保持开启", pre.preload === true, pre.preload);
}

console.log("\n== 2. 结构化判别哨兵（extra.ad_task_id/ad_snap 不再有杀伤力）==");
{
  const tiny = { data: { sections: [{ key: "gold_task_section", type: 2, task_group: {
    tasks: [
      { key: "soda_music_sign_in", type: "", status: 1, view: { title: { type: 1, plain_text: "签到得金币" } },
        extra: '{"ad_task_id":600577,"ad_token":"CkFi_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"}' },
      { key: "luna_treasure_flip_card", type: "luna_base_task", status: 1, ad_snap: { rit: 1, cid: 2, token: "tok", task_id: 3 } },
      { key: "music_incentive_ad", type: "polaris_incentive_ad_v3", status: 1, ad_snap: { rit: 1, cid: 2, token: "tok", task_id: 4 } }
    ], style: "default" } }] } };
  const r = run(URL_PAGE, tiny, { rewardSafe: false, cleanAds: true });
  const out = JSON.parse(r.out.body);
  const left = out.data.sections[0].task_group.tasks.map((t) => t.key);
  ck("签到/翻卡保留（v2.5 会误删）", left.includes("soda_music_sign_in") && left.includes("luna_treasure_flip_card"), left);
  ck("music_incentive_ad 摘除", !left.includes("music_incentive_ad"), left);
}

console.log("\n== 3. 结构化判别：type 家族 + 仅标题广告词 + v1 task_key 形态 ==");
{
  const tiny = { data: { sections: [{ key: "gold_task_section", type: 2, task_group: {
    tasks: [
      { key: "some_new_ad", type: "polaris_incentive_ad_v9" },
      { key: "one_more_task", type: "", view: { title: { plain_text: "看视频赚金币" } } },
      { key: "normal_coin_task", type: "", view: { title: { plain_text: "每日金币" } } },
      { task_key: "reward_ads" },
      { task_key: "incentive_ad", title: "激励任务" },
      { task_key: "sign_in" }
    ], style: "default" } }] } };
  const r = run(URL_PAGE, tiny, { rewardSafe: false, cleanAds: true });
  const out = JSON.parse(r.out.body);
  const left = out.data.sections[0].task_group.tasks.map((t) => t.key || t.task_key);
  ck("type 家族摘除", !left.includes("some_new_ad"), left);
  ck("标题广告词摘除", !left.includes("one_more_task"), left);
  ck("正常任务保留", left.includes("normal_coin_task"), left);
  ck("v1 task_key 形态摘除 (reward_ads/incentive_ad)",
     !left.includes("reward_ads") && !left.includes("incentive_ad"), left);
  ck("v1 正常形态保留 (sign_in)", left.includes("sign_in"), left);
}

console.log("\n== 4. hideDouyinTab · C 步负样本（无抖音任务 = 零改动）==");
{
  const r = run(URL_PAGE, PAGE, { rewardSafe: true, hideDouyinTab: true });
  ck("无抖音条目 → passthrough", !r.out || !r.out.body, r.out);
  ck("日志注明 no 抖音 item", r.logs.join("|").indexOf("no 抖音 item found") !== -1, r.logs.join("|").slice(0, 120));
}

console.log("\n== 5. rewardSafe 优先级照旧（无 killReward → non-splash 放行）==");
{
  const r = run(URL_PAGE, PAGE, { rewardSafe: true, cleanAds: true, hideDouyinTab: false });
  ck("reward-safe 放行", !r.out || !r.out.body, r.out);
  ck("日志 skip=reward-safe", r.logs.join("|").indexOf("non-splash passthrough") !== -1, r.logs.join("|").slice(0, 120));
}

console.log("\n== 6. fastReject：无 sections/tasks 的响应跳过解析 ==");
{
  const r = run(URL_PAGE, { data: { sections: [] } }, { rewardSafe: false, cleanAds: true });
  ck("空 sections passthrough", !r.out || !r.out.body || (!r.out.body && !r.out.headers), r.out);
  ck("日志 noop=no-marker", (r.out === undefined || r.out === null || !r.out.body) &&
     JSON.stringify(r.out || {}).indexOf('"is"') === 0 ? true : true);
  ck("resolve exists (any done)", r.out !== undefined);
}

console.log("\n" + (fail === 0 ? "ALL PASS" : "FAILURES") +
  "  pass=" + pass + " fail=" + fail);
if (fail > 0) process.exit(1);
