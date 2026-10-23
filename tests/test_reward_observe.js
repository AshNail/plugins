const src = require("./load-script")("reward-observe.js");

function run(url, body, argument) {
  let out = null;
  const logs = [];
  new Function("$request", "$response", "$done", "console", "$argument", src)(
    { url },
    { body: typeof body === "string" ? body : JSON.stringify(body) },
    (v) => { out = v; },
    { log: (...a) => logs.push(a.join(" ")) },
    argument
  );
  return { out, logs };
}

let pass = 0, fail = 0;
function check(name, cond, extra) {
  if (cond) { pass++; console.log("  ok  " + name); }
  else { fail++; console.log("  FAIL " + name + (extra ? " :: " + extra : "")); }
}

function logText(r) {
  return r.logs.join(" | ");
}

function unchanged(r) {
  return r.out && r.out.body === undefined;
}

console.log("\n[1] incentive/config: sources/preload + sensitive filter");
{
  const r = run("https://api.qishui.com/luna/advert/incentive/config", {
    status_code: 10001,
    status_info: "freq limit",
    preload: true,
    advert_sources: [{ rit: 1 }, { rit: 2 }],
    feed_advert_config: { a: 1 },
    expire_time: 123,
    access_token: "SECRET_TOKEN",
    device_id: "SECRET_DEVICE",
    cookie: "SECRET_COOKIE"
  });
  const s = logText(r);
  check("no body rewrite", unchanged(r), JSON.stringify(r.out));
  check("prefix", s.includes("[soda-reward]"), s);
  check("rule id", s.includes("incentive-config"), s);
  check("sources=2", s.includes('"sources":2'), s);
  check("feedConfig=1", s.includes('"feedConfig":1'), s);
  check("preload=true", s.includes('"preload":true'), s);
  check("statusInfo", s.includes('"statusInfo":"freq limit"'), s);
  check("no access token value", !s.includes("SECRET_TOKEN"), s);
  check("no device id value", !s.includes("SECRET_DEVICE"), s);
  check("no cookie value", !s.includes("SECRET_COOKIE"), s);
  check("access_token key filtered", !s.includes("access_token"), s);
  check("device_id key filtered", !s.includes("device_id"), s);
}

console.log("\n[1b] status_info redaction");
{
  const r = run("https://api.qishui.com/luna/advert/incentive/config", {
    status_code: 10002,
    status_info: "denied ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"
  });
  const s = logText(r);
  check("normal text preserved", s.includes("denied"), s);
  check("long token redacted", s.includes("<redacted>") && !s.includes("ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"), s);
}

console.log("\n[2] incentive/config: preload=false");
{
  const r = run("https://api.qishui.com/luna/advert/incentive/config", {
    status_code: 0, preload: false, advert_sources: [], feed_advert_config: {}
  });
  check("no body rewrite", unchanged(r));
  check("preload=false", logText(r).includes('"preload":false'), logText(r));
}

console.log("\n[3] incentive/retrieve: ad_infos_map + ad_infos");
{
  const r = run("https://api.qishui.com/luna/advert/incentive/retrieve", {
    status_code: 0,
    ad_infos_map: { scene_a: { id: 1 }, scene_b: { id: 2 } },
    ad_infos: [{ id: 3 }],
    expire_time: 456
  });
  const s = logText(r);
  check("no body rewrite", unchanged(r));
  check("adInfosMap=2", s.includes('"adInfosMap":2'), s);
  check("adInfos=1", s.includes('"adInfos":1'), s);
}

console.log("\n[4] incentive/done: reward details (real response fields)");
{
  const r = run("https://api.qishui.com/luna/advert/incentive/done", {
    status_code: 0,
    reward_details: { coin: 100 },
    reward_tips: { tip: "x" }
  });
  const s = logText(r);
  check("no body rewrite", unchanged(r));
  check("rewardDetails keys", s.includes('"rewardDetails":{"keys":["coin"]'), s);
  check("rewardTips keys", s.includes('"rewardTips":{"keys":["tip"]'), s);
}

console.log("\n[4b] ads/reward/settle: isValid + playEntitlements");
{
  const r = run("https://api.qishui.com/luna/ads/reward/settle", {
    status_code: 0,
    is_valid: true,
    play_entitlements: {
      expire_at: 1700000000,
      reward_finished_task_info: {
        days_obtained: 2,
        full_day: false,
        all_full: false,
        tasks_finished: 1,
        task_to_full_day: 2
      }
    }
  });
  const s = logText(r);
  check("no body rewrite", unchanged(r));
  check("isValid=true", s.includes('"isValid":true'), s);
  check("playEntitlements keys", s.includes('"playEntitlements":{"keys"'), s);
  check("progress daysObtained=2", s.includes('"daysObtained":2'), s);
  check("progress fullDay=false", s.includes('"fullDay":false'), s);
}

console.log("\n[5] task/view: reward_ads task preserved in log");
{
  const r = run("https://api.qishui.com/luna/treasure/task/view", {
    status_code: 0,
    task_infos: [
      {
        task_key: "reward_ads",
        reward_type: "coin",
        reward_amount: 100,
        reward_max_amount: 300,
        valid_duration: 30,
        can_show: true,
        ad_snap: { rit: 1 },
        stats: { total_times: 3, completed_times: 1, last_rewarded_time: 123 },
        view: { button: { action: "watch_ad" } }
      },
      { task_key: "sign_in", reward_type: "coin", reward_amount: 10 }
    ]
  });
  const s = logText(r);
  check("no body rewrite", unchanged(r));
  check("taskInfos=2", s.includes('"taskInfos":2'), s);
  check("reward_ads task", s.includes('"key":"reward_ads"'), s);
  check("reward amount", s.includes('"amount":100'), s);
  check("reward max", s.includes('"max":300'), s);
  check("valid duration", s.includes('"valid":30'), s);
  check("canShow", s.includes('"show":true'), s);
  check("task total", s.includes('"total":3'), s);
  check("task done", s.includes('"doneTimes":1'), s);
  check("last rewarded", s.includes('"lastReward":123'), s);
  check("adSnap", s.includes('"adSnap":true'), s);
  check("button action", s.includes('"action":"watch_ad"'), s);
  check("sign_in task", s.includes('"key":"sign_in"'), s);
}

console.log("\n[6] ads/config: ad unit + reward config counts");
{
  const r = run("https://api.qishui.com/luna/ads/config", {
    status_code: 0,
    ad_unit_configs: [{ id: 1 }, { id: 2 }, { id: 3 }],
    reward_config: { enable: true },
    splash_config: { enable: true }
  });
  const s = logText(r);
  check("no body rewrite", unchanged(r));
  check("adUnitConfigs=3", s.includes('"adUnitConfigs":3'), s);
  check("rewardConfig=1", s.includes('"rewardConfig":1'), s);
}

console.log("\n[7] ads/retrieve: launch counts");
{
  const r = run("https://api.qishui.com/luna/ads/retrieve", {
    status_code: 0,
    ad_launch: [{ id: 1 }, { id: 2 }],
    ads_blocks: [{ id: 1 }]
  });
  const s = logText(r);
  check("no body rewrite", unchanged(r));
  check("adLaunch=2", s.includes('"adLaunch":2'), s);
  check("adsBlocks=1", s.includes('"adsBlocks":1'), s);
}

console.log("\n[8] reward/receive + validate_reward (real response fields)");
{
  const r1 = run("https://api.qishui.com/luna/ads/reward/receive", {
    status_code: 0,
    play_entitlements: { expire_at: 1700000000 }
  });
  check("receive no body rewrite", unchanged(r1));
  check("receive playEntitlements", logText(r1).includes('"playEntitlements":{"keys"'), logText(r1));

  const r2 = run("https://api.qishui.com/luna/commerce/validate_reward", {
    status_code: 0,
    transaction_success: true,
    subs_info: { plan: "vip" }
  });
  check("validate no body rewrite", unchanged(r2));
  check("transactionSuccess=true", logText(r2).includes('"transactionSuccess":true'), logText(r2));
  check("subsInfo keys", logText(r2).includes('"subsInfo":{"keys":["plan"]'), logText(r2));
}

console.log("\n[9] non-JSON / empty / large body");
{
  const r1 = run("https://api.qishui.com/luna/advert/incentive/config", "not json");
  check("non-JSON no body", unchanged(r1));
  check("non-JSON log", logText(r1).includes("non-JSON"), logText(r1));

  const r2 = run("https://api.qishui.com/luna/advert/incentive/config", "");
  check("empty no body", unchanged(r2));
  check("empty log", logText(r2).includes("empty body"), logText(r2));

  const big = JSON.stringify({ status_code: 0, filler: "x".repeat(300000) });
  const r3 = run("https://api.qishui.com/luna/advert/incentive/config", big);
  check("large no body", unchanged(r3));
  check("large log", logText(r3).includes("body too large"), logText(r3));
}

console.log("\n[10] unmatched URL: silent passthrough");
{
  const r = run("https://api.qishui.com/luna/me/profile", { status_code: 0, data: { name: "x" } });
  check("no body rewrite", unchanged(r));
  check("no logs", r.logs.length === 0, logText(r));
}

console.log("\n[11] input object not mutated");
{
  const body = {
    status_code: 0,
    task_infos: [{ task_key: "reward_ads", reward_amount: 100 }],
    advert_sources: [{ id: 1 }]
  };
  const before = JSON.stringify(body);
  const r = run("https://api.qishui.com/luna/treasure/task/view", body);
  check("no body rewrite", unchanged(r));
  check("object unchanged", JSON.stringify(body) === before, JSON.stringify(body));
}

console.log("\n[12] malformed JSON: passthrough");
{
  const r = run("https://api.qishui.com/luna/advert/incentive/config", "{oops");
  check("no body rewrite", unchanged(r));
  check("parse failed log", logText(r).includes("JSON parse failed"), logText(r));
}

console.log("\n[13] extra task actions: fallback/flip/guide/browse");
{
  const cases = [
    ["fallback-action", "https://api.qishui.com/luna/treasure/task/fallback/do_action"],
    ["flip-card-action", "https://api.qishui.com/luna/treasure/task/flip_card/do_action"],
    ["guide-action", "https://api.qishui.com/luna/treasure/task/guide/do_action"],
    ["browse-mall-action", "https://api.qishui.com/luna/treasure/task/browse_mall/do_action"]
  ];
  for (const [id, url] of cases) {
    const r = run(url, { status_code: 0, data: { ok: true } });
    check(id + " no body rewrite", unchanged(r), JSON.stringify(r.out));
    check(id + " rule id", logText(r).includes(id), logText(r));
  }
}

console.log("\n[14] commerce/v2/upsell: read-only reward entry variables");
{
  const r = run("https://api.qishui.com/luna/commerce/v2/upsell?scene=cold_start", {
    status_code: 0,
    scene_upsells_map: {
      cold_start: {
        candidates: [
          { item_type: "fixed_entrance", fixed_entrance: { coin_widget_data: { capability_level: 1 } } }
        ]
      },
      reward_receive: {},
      cool_down_time_expired: {}
    },
    upells_variables: {
      enable_ads: true,
      enable_coin: true,
      ads_today_task_full: false,
      ads_days_obtained: 2,
      max_release_days: 7,
      reward_tasks_count: 3,
      has_play_entitlement: false,
      can_show_cold_launch_popup_coin: true,
      coin_new_user_first_launch_opt: 1,
      is_vip: true,
      vip_expire_time: 1700000000
    },
    sort_control_unique_names: ["a", "b"],
    popup_config: { a: 1, b: 2 },
    cold_launch_timing: "after_feed",
    access_token: "SECRET_TOKEN",
    user_extra_info: { uid: "SECRET_UID", title: "SENSITIVE_TITLE" }
  });
  const s = logText(r);
  check("no body rewrite", unchanged(r), JSON.stringify(r.out));
  check("rule id", s.includes("upsell-v2"), s);
  check("scenes=3", s.includes('"scenes":3'), s);
  check("scene names", s.includes('"reward_receive"'), s);
  check("fixedEntrances=1", s.includes('"fixedEntrances":1'), s);
  check("coinWidgets=1", s.includes('"coinWidgets":1'), s);
  check("enable_ads", s.includes('"enable_ads":true'), s);
  check("enable_coin", s.includes('"enable_coin":true'), s);
  check("ads_today_task_full", s.includes('"ads_today_task_full":false'), s);
  check("ads_days_obtained", s.includes('"ads_days_obtained":2'), s);
  check("max_release_days", s.includes('"max_release_days":7'), s);
  check("reward_tasks_count", s.includes('"reward_tasks_count":3'), s);
  check("has_play_entitlement", s.includes('"has_play_entitlement":false'), s);
  check("popupConfig=2", s.includes('"popupConfig":2'), s);
  check("no token value", !s.includes("SECRET_TOKEN"), s);
  check("no uid value", !s.includes("SECRET_UID"), s);
  check("no popup copy", !s.includes("SENSITIVE_TITLE"), s);
  check("membership expiry left out", !s.includes("vip_expire_time"), s);
}

console.log("\n[14b] upsell_sort_decision stays unobserved");
{
  const r = run("https://api.qishui.com/luna/commerce/v2/upsell_sort_decision", {
    status_code: 0,
    popup_config: { a: 1 }
  });
  check("no body rewrite", unchanged(r));
  check("no logs", r.logs.length === 0, logText(r));
}

console.log("\n[15] task/page v2（HAR 393 真样本，v2.6.1 补绑）");
{
  const fs = require("fs");
  const page = fs.readFileSync(
    require("path").join(__dirname, "fixtures", "soda_task_page_v2.json"), "utf8"
  );
  const PREFIX = "[soda-reward] task-page ";
  const r = run("https://beta-luna.douyin.com/luna/treasure/task/page/v2", page);
  check("observed (rule fires)", r.logs.length > 0, "no logs");
  const line = r.logs.find((l) => l.indexOf(PREFIX) === 0);
  check("summary line found", !!line, r.logs.join("|").slice(0, 120));
  const s = JSON.parse((line || "").slice(PREFIX.length));
  check("task count >= 10", Array.isArray(s.tasks) && s.tasks.length >= 10,
        s.tasks && s.tasks.length);
  check("status preserved", s.status === 0, s.status);
  check("no body rewrite", unchanged(r));
}

console.log("\n[16] logTaskTitles=开：v2 任务标题随样本带出");
{
  const fs = require("fs");
  const page = fs.readFileSync(
    require("path").join(__dirname, "fixtures", "soda_task_page_v2.json"), "utf8"
  );
  const PREFIX = "[soda-reward] task-page ";
  const r = run("https://api.qishui.com/luna/treasure/task/page/v2", page,
                { logTaskTitles: true });
  const line = r.logs.find((l) => l.indexOf(PREFIX) === 0);
  check("observed via api.qishui host", !!line, r.logs.join("|").slice(0, 120));
  const s = JSON.parse(line.slice(PREFIX.length));
  const titles = (s.tasks || []).map((t) => t.title || "").join("|");
  check("标题含 签到 得金币", /签到/.test(titles), titles);
  check("标题含 看广告 赚金币", /看广告/.test(titles), titles);
  check("标题含 攒时长", /攒时长/.test(titles), titles);
  check("max 24 字截断不失控",
        (s.tasks || []).every((t) => !t.title || t.title.length <= 25), titles);
}

console.log("\n----------------------------------------");
console.log("PASS=" + pass + "  FAIL=" + fail);
process.exit(fail ? 1 : 0);
