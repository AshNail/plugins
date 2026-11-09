/*
 * 第三轮回归：净化链「不误伤业务」的双向断言 + jq 类型收窄实证
 * ----------------------------------------------------------------------------
 * 每一组都同时断言两件事：广告/弹窗仍然被删、业务字段原样保留。
 * 只测「广告没了」是单向的——把整个响应清空也能过，那正是本轮要防的 bug。
 *
 * 覆盖的 5 个实质问题：
 *   1. 发奖兜底接口 advert/fallback/done/info 不得 forceOk、不得碰
 *      post_done_extra 里的 req_id/time_token/nonce，也不得清 rewardConfig/
 *      adExtra/data（soda 与 douyin 两侧都要）。
 *   2. upsell v1/v2 分开：v1 要有路径边界（upsells_config 不能被误命中），
 *      v2 只删 upsell_map 实体，业务 data/items/show 必须原样。
 *   3. 传感器阈值（Sensitivity / Threshold）方向不明，不许置 0；
 *      只关语义明确的 enable* 开关。
 *   4. Bilibili / Zhihu 的 response.json.jq 必须扛得住异常条目
 *      （target 是字符串/数组、card_goto 是数字），不能整次净化失败。
 *      用真实 jq 引擎跑，不是「看表达式像不像有守卫」。
 *   5. 抖音只真正支持 v2 upsell；v1 路由不该挂空转处理器（假覆盖）。
 */
"use strict";

const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");
const load = require("./load-script");

const ROOT = path.resolve(__dirname, "..");
const sodaSanitize = load("sanitize.js");
const sodaSettings = load("settings.js");
const douyinClean = load("clean.js", "douyin");

let pass = 0, fail = 0;
function check(name, cond, extra) {
  if (cond) {
    pass++;
    console.log("  PASS  " + name);
  } else {
    fail++;
    console.log("  FAIL  " + name + (extra !== undefined ? "  got=" + JSON.stringify(extra) : ""));
  }
}
function eq(a, b) { return JSON.stringify(a) === JSON.stringify(b); }
function parse(out) {
  if (!out || out.body === undefined) return null;
  try { return JSON.parse(out.body); } catch (e) { return null; }
}

function runner(code, defaultUrl) {
  return function (body, argument, url) {
    let out = null;
    const logs = [];
    const fn = new Function(
      "$request", "$response", "$done", "console", "$argument", code
    );
    fn(
      { url: url || defaultUrl },
      { body: typeof body === "string" ? body : JSON.stringify(body) },
      (v) => { out = v; },
      { log: (...a) => logs.push(a.join(" ")) },
      argument
    );
    return { out, logs };
  };
}

const SODA_CLEAN = { rewardSafe: false, cleanAds: true, killRewardAds: false, hideDouyinTab: false };
const runSoda = runner(sodaSanitize, "https://api.qishui.com/luna/ads/retrieve");
const runSettings = runner(sodaSettings, "https://conf.qishui.com/service/settings/v3/");
const DOUYIN_ARGS = {
  cleanFeedAds: true, killRewardAds: false, cleanUpsell: true,
  cleanActivity: false, debugLog: false, blockSplashAd: true
};
const runDouyin = runner(douyinClean, "https://beta-luna.douyin.com/luna/ads/retrieve");

const FALLBACK_URL = "https://api.qishui.com/luna/advert/fallback/done/info";
const FALLBACK_DOUYIN_URL = "https://beta-luna.douyin.com/luna/advert/fallback/done/info";
function fallbackBody() {
  return {
    status_code: 1001,
    status_info: "服务端拒绝",
    reward_details: { amount: 5, coin: 3 },
    reward_tips: "本期奖励已发放",
    post_done_extra: { req_id: "R-1", time_token: "T-1", nonce: "N-1" },
    rewardConfig: { keep: "yes" },
    adExtra: { keep: "yes" },
    data: [{ id: 1 }, { id: 2 }],
    ad_launch_list: [{ id: "ad-1" }],
    ads_blocks: [{ id: "ad-2" }]
  };
}

/* ---------------------------------------------------------------- */
console.log("\n== 1. soda · 发奖兜底接口：不伪造成功、不碰凭证 ==");
{
  const raw = fallbackBody();
  const o = parse(runSoda(raw, SODA_CLEAN, FALLBACK_URL).out);
  check("命中并改写响应", !!o, o);
  check("服务端错误码 1001 保留（不 forceOk）", o && o.status_code === 1001, o && o.status_code);
  check("服务端错误文案保留（不 forceOk）", o && o.status_info === "服务端拒绝", o && o.status_info);
  check("post_done_extra 三凭证原样",
    o && eq(o.post_done_extra, raw.post_done_extra), o && o.post_done_extra);
  check("reward_details 原样", o && eq(o.reward_details, raw.reward_details), o && o.reward_details);
  check("reward_tips 原样", o && o.reward_tips === raw.reward_tips, o && o.reward_tips);
  check("rewardConfig 原样", o && eq(o.rewardConfig, raw.rewardConfig), o && o.rewardConfig);
  check("adExtra 原样", o && eq(o.adExtra, raw.adExtra), o && o.adExtra);
  check("业务 data 数组 2 条原样", o && eq(o.data, raw.data), o && o.data);
  check("广告素材 ad_launch_list 已清", o && eq(o.ad_launch_list, []), o && o.ad_launch_list);
  check("广告块 ads_blocks 已清", o && eq(o.ads_blocks, []), o && o.ads_blocks);
}

/* ---------------------------------------------------------------- */
console.log("\n== 2. soda · upsell v1 路径边界 ==");
{
  const body = { status_code: 0, upsells: [{ id: 1 }], card: { a: 1 }, show: true };
  const cfg = runSoda(body, SODA_CLEAN,
    "https://api.qishui.com/luna/commerce/upsells_config");
  check("upsells_config 不命中 v1 规则（不改写）", !(cfg.out && cfg.out.body), cfg.out);
  const v1 = parse(runSoda(body, SODA_CLEAN,
    "https://api.qishui.com/luna/commerce/upsells").out);
  check("真正的 v1 端点被处理", !!v1, v1);
  check("v1 upsells 已清", v1 && eq(v1.upsells, []), v1 && v1.upsells);
  check("v1 card 已清", v1 && eq(v1.card, {}), v1 && v1.card);
  check("v1 show 已关", v1 && v1.show === false, v1 && v1.show);
}

/* ---------------------------------------------------------------- */
console.log("\n== 3. soda · upsell v2 只删实体，业务数组必须原样 ==");
{
  const body = {
    status_code: 0,
    data: [{ id: 1 }, { id: 2 }],
    items: [{ id: 3 }],
    show: true,
    upsell_map: { ads_foo: { a: 1 }, reward_x: { b: 2 } },
    sort_control_unique_names: ["ads_foo", "reward_x"],
    cold_launch_timing: { upsell_item_unique_names: ["ads_foo", "reward_x"] },
    freq_ctrl_cfg: { freq_ctrl_map: { ads_foo: {}, reward_x: {}, widget_ad: {} } },
    variables: { qualify: 1 }
  };
  const o = parse(runSoda(body, SODA_CLEAN,
    "https://api.qishui.com/luna/commerce/v2/upsell").out);
  check("命中并改写响应", !!o, o);
  check("业务 data 2 条原样（旧规则会整体清空）", o && eq(o.data, body.data), o && o.data);
  check("业务 items 1 条原样", o && eq(o.items, body.items), o && o.items);
  check("业务 show 保持 true（不走 v1 泛化清理）", o && o.show === true, o && o.show);
  check("variables 原样", o && eq(o.variables, body.variables), o && o.variables);
  check("广告弹窗 ads_foo 已删", o && !o.upsell_map.ads_foo, o && o.upsell_map);
  check("奖励弹窗 reward_x 保留", o && !!o.upsell_map.reward_x, o && o.upsell_map);
  check("sort 同步只留 reward_x",
    o && eq(o.sort_control_unique_names, ["reward_x"]), o && o.sort_control_unique_names);
  check("冷启动列表同步只留 reward_x",
    o && eq(o.cold_launch_timing.upsell_item_unique_names, ["reward_x"]),
    o && o.cold_launch_timing);
  check("频控共享键 widget_ad 保留",
    o && !!o.freq_ctrl_cfg.freq_ctrl_map.widget_ad, o && o.freq_ctrl_cfg);
}

/* ---------------------------------------------------------------- */
const THRESHOLDS = {
  splashShakeSensitivity: 3,
  shakeSensitivity: 5,
  splashAccelerationThreshold: 9,
  splashRotationThreshold: 7
};
function checkThresholds(label, o, raw) {
  for (const k of Object.keys(THRESHOLDS)) {
    check(label + " " + k + " 保持原值 " + THRESHOLDS[k],
      o && o[k] === raw[k], o && o[k]);
  }
}

console.log("\n== 4. soda sanitize · 方向不明的传感器阈值不许置 0 ==");
{
  const body = Object.assign({}, THRESHOLDS, {
    enableSplashShake: true,
    ad_launch_list: [{ id: "ad-1" }]
  });
  const o = parse(runSoda(body, SODA_CLEAN,
    "https://api.qishui.com/luna/advert/splash/brand/retrieve").out);
  check("命中并改写响应", !!o, o);
  checkThresholds("开屏响应", o, body);
  check("语义明确的开关 enableSplashShake 仍被关掉",
    o && o.enableSplashShake === false, o && o.enableSplashShake);
  check("广告素材 ad_launch_list 已清", o && eq(o.ad_launch_list, []), o && o.ad_launch_list);
}

console.log("\n== 5. soda settings · 阈值键不进改写表 ==");
{
  const body = { data: { settings: Object.assign({}, THRESHOLDS, {
    enableSplashShake: true,
    anchor_luna_to_douyin: 1
  }) } };
  const args = { settingsClean: true, hideDouyinEntry: false, rewardSafe: false, debugLog: false };
  const o = parse(runSettings(body, args).out);
  const s = o && o.data && o.data.settings;
  check("命中并改写设置响应", !!s, o);
  checkThresholds("设置表", s, body.data.settings);
  check("语义明确的开关 enableSplashShake 仍被关掉",
    s && s.enableSplashShake === false, s && s.enableSplashShake);
  check("hideDouyinEntry 关着时入口开关不动",
    s && s.anchor_luna_to_douyin === 1, s && s.anchor_luna_to_douyin);
}

/* ---------------------------------------------------------------- */
console.log("\n== 6. douyin · 发奖兜底接口走专用规则（不是泛化 ads-config）==");
{
  const raw = fallbackBody();
  const o = parse(runDouyin(raw, DOUYIN_ARGS, FALLBACK_DOUYIN_URL).out);
  check("命中并改写响应", !!o, o);
  check("服务端错误码 1001 保留", o && o.status_code === 1001, o && o.status_code);
  check("服务端错误文案保留", o && o.status_info === "服务端拒绝", o && o.status_info);
  check("post_done_extra 三凭证原样",
    o && eq(o.post_done_extra, raw.post_done_extra), o && o.post_done_extra);
  check("reward_details 原样", o && eq(o.reward_details, raw.reward_details), o && o.reward_details);
  check("rewardConfig 原样（泛化规则会清掉）",
    o && eq(o.rewardConfig, raw.rewardConfig), o && o.rewardConfig);
  check("adExtra 原样（泛化规则会清掉）",
    o && eq(o.adExtra, raw.adExtra), o && o.adExtra);
  check("业务 data 2 条原样", o && eq(o.data, raw.data), o && o.data);
  check("广告素材 ad_launch_list 已清", o && eq(o.ad_launch_list, []), o && o.ad_launch_list);
  check("广告块 ads_blocks 已清", o && eq(o.ads_blocks, []), o && o.ads_blocks);
}

console.log("\n== 7. douyin · 传感器阈值不许置 0 ==");
{
  const body = Object.assign({}, THRESHOLDS, {
    enableSplashShake: true,
    reward_details: { amount: 5 },
    ad_launch_list: [{ id: "ad-1" }]
  });
  const o = parse(runDouyin(body, DOUYIN_ARGS,
    "https://beta-luna.douyin.com/luna/advert/splash/brand/retrieve").out);
  check("命中并改写响应", !!o, o);
  checkThresholds("开屏品牌响应", o, body);
  check("语义明确的开关 enableSplashShake 仍被关掉",
    o && o.enableSplashShake === false, o && o.enableSplashShake);
  check("reward_details 原样", o && eq(o.reward_details, body.reward_details), o && o.reward_details);
  check("广告素材 ad_launch_list 已清", o && eq(o.ad_launch_list, []), o && o.ad_launch_list);
}

console.log("\n== 8. douyin · v1 upsell 不挂空转路由（假覆盖）==");
{
  const body = { upsell_map: { ads_foo: { a: 1 }, reward_x: { b: 2 } } };
  const r = runDouyin(body, DOUYIN_ARGS,
    "https://beta-luna.douyin.com/luna/commerce/upsells");
  check("v1 请求放行，不假装处理", !(r.out && r.out.body), r.out);
  const v2 = parse(runDouyin(body, DOUYIN_ARGS,
    "https://beta-luna.douyin.com/luna/commerce/v2/upsell").out);
  check("v2 端点仍然真实净化", !!v2 && !v2.upsell_map.ads_foo, v2);
  check("v2 奖励弹窗保留", !!v2 && !!v2.upsell_map.reward_x, v2);
  /* 运行时断言抓不到「路由绑了但处理器空转」——因为空转也是不改写响应。
   * 所以对源码与插件接线各加一条静态断言，回潮时测试自己就会红。 */
  const cleanSrc = fs.readFileSync(path.join(ROOT, "src/douyin/clean.js"), "utf8")
    .replace(/\/\*[\s\S]*?\*\//g, " ");
  check("源码 upsell 路由不含 v1 的 upsells",
    !/commerce.{0,80}upsells/.test(cleanSrc));
  const pluginSrc = fs.readFileSync(path.join(ROOT, "plugins/douyin/douyin.plugin"), "utf8");
  check("插件 [Script] 接线不含 v1 的 upsells",
    !pluginSrc.split("\n").some((l) =>
      !l.trim().startsWith("#") && l.includes("commerce") &&
      l.includes("script(") && l.includes("upsells")));
}

/* ---------------------------------------------------------------- */
console.log("\n== 9. Bilibili / Zhihu · jq 类型收窄（真实 jq 引擎）==");
{
  function exprs(rel) {
    const d = JSON.parse(fs.readFileSync(path.join(ROOT, rel), "utf8"));
    const out = {};
    for (const r of (d.enhance && d.enhance.rewrite) || []) {
      const m = /response\.json\.jq\("(.*)"\)/.exec(r.action || "");
      if (m) out[r.id] = m[1].replace(/\\"/g, '"');
    }
    return out;
  }
  const E = Object.assign({},
    exprs("src/apps/zhihu.json"),
    exprs("src/apps/bilibili.json"));

  function jqRun(expr, obj) {
    try {
      const out = execFileSync("jq", ["-c", expr], {
        input: JSON.stringify(obj), encoding: "utf8"
      }).trim();
      return { ok: true, data: JSON.parse(out) };
    } catch (e) {
      return { ok: false, err: String(e.stderr || e.message).split("\n")[0] };
    }
  }
  function leftCount(id, data) {
    const d = data && data.data;
    if (Array.isArray(d)) return d.length;
    if (d && Array.isArray(d.items)) return d.items.length;
    return -1;
  }
  const cases = [
    ["zhihu 正常：广告删、业务留", "clean-topstory-recommend",
      { data: [{ type: "answer", target: { type: "answer" } },
               { type: "feed_advert" },
               { type: "answer", target: { type: "advert" } }] }, 1],
    ["zhihu target 是字符串：整次净化不失败", "clean-topstory-recommend",
      { data: [{ type: "answer", target: "oops" },
               { type: "answer", target: { type: "answer" } }] }, 2],
    ["zhihu target 是数组：整次净化不失败", "clean-topstory-recommend",
      { data: [{ type: "answer", target: [1, 2] },
               { type: "answer", target: { type: "answer" } }] }, 2],
    ["zhihu moments target 是数字：不失败", "clean-moments-feed",
      { data: [{ type: "answer", target: 7 }, { type: "feed_advert" }] }, 1],
    ["bili card_goto 是数字：整次净化不失败", "clean-feed-index",
      { data: { items: [{ card_goto: 123 }, { card_goto: "av", card_type: "normal" }] } }, 2],
    ["bili card_type 是数组：整次净化不失败", "clean-feed-index",
      { data: { items: [{ card_goto: "av", card_type: [1] }, { card_goto: "av" }] } }, 2],
    ["bili 正常：广告删、业务留", "clean-feed-index",
      { data: { items: [{ card_goto: "ad_web_s" }, { card_type: "cm_v1" },
                        { card_goto: "av", card_type: "normal" }] } }, 1],
    ["bili story card_goto 是数字：不失败", "clean-feed-story",
      { data: { items: [{ card_goto: 9 }, { card_goto: "av" }] } }, 2],
    ["bili story 正常：广告删", "clean-feed-story",
      { data: { items: [{ card_goto: "ad_web_s" }, { card_goto: "av" }] } }, 1]
  ];
  for (const [name, id, obj, want] of cases) {
    check("jq 表达式存在：" + id, !!E[id], Object.keys(E));
    const r = E[id] ? jqRun(E[id], obj) : { ok: false, err: "missing expr" };
    check(name + "（rc=0）", r.ok, r.err);
    check(name + "（剩 " + want + " 条）",
      r.ok && leftCount(id, r.data) === want,
      r.ok ? leftCount(id, r.data) : r.err);
  }
}

console.log("\n" + (fail === 0 ? "ALL PASS" : "FAILURES") +
  "  pass=" + pass + " fail=" + fail);
process.exit(fail === 0 ? 0 : 1);
