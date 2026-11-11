/*
 * qidian mainPage 只留激励任务 · v4.2.0 双向回归
 * ------------------------------------------------------------
 * 用户 2026-11-10 20:25 提供二次抓包的 mainPage 原始响应并裁决：只保留激励任务
 * （常驻 + 限时），其余全部剔除。本套件把这条裁决钉在四处：
 *
 *   1. 源 src/apps/qidian.json 与发布插件 plugins/qidian/qidian.plugin 逐字对账
 *      （防「源写了、产物没写对」的假覆盖）；
 *   2. 白名单分类守卫：keep_whitelist ∪ delete 名单必须恰好等于真机样本的全部
 *      Data 键。服务端以后新增 Data 键，样本一更新这里就红，禁止静默漏网；
 *   3. 双向断言：12 个推广/奖励/布局键确实消失，同时 4 个激励模块与 7 个身份
 *      标量逐字原样、顶层包络不动。只测「广告没了」会把「整个响应清空」也放过；
 *   4. jq_equivalent 用 /usr/bin/jq 实跑，输出必须与运行时那条
 *      response.json.delete 完全等价；7 类异常输入不得让整次净化失败。
 *
 * 取舍：运行态用官方 response.json.delete（HAR 466 实证命中并改包），不用 jq
 * 白名单——Loon 内置 jq 对 with_entries / |= 的支持尚未真机回抓验证。
 * jq_equivalent 保留等价写法，作为真机确认后可切换的严格白名单运行态。
 */
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const ROOT = path.resolve(__dirname, "..");
const cfg = JSON.parse(fs.readFileSync(path.join(ROOT, "src", "apps", "qidian.json"), "utf8"));
const plugin = fs.readFileSync(path.join(ROOT, "plugins", "qidian", "qidian.plugin"), "utf8");
const sample = JSON.parse(fs.readFileSync(
  path.join(__dirname, "fixtures", "qidian_mainpage_limited.json"), "utf8"));
const capture = JSON.parse(fs.readFileSync(
  path.join(__dirname, "fixtures", "qidian_mainpage_20261110.json"), "utf8"));

let pass = 0, fail = 0;
function check(name, cond, extra) {
  if (cond) { pass++; console.log("  ok  " + name); }
  else { fail++; console.log("  FAIL " + name + (extra ? " :: " + extra : "")); }
}
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const keys = o => Object.keys(o).sort();

// 用户裁决的独立声明（故意不复用源里的数组，两边对账才有鉴别力）
const INCENTIVE = ["DailyBenefitModule", "VideoRewardTab", "ReadingPageTaskModule", "SurpriseBenefit"];
const SCALARS = ["Guid", "EncryptedGuid", "NickName", "Avatar",
  "AutoJumpSignDetailForHM", "DiffAmount", "NineReward"];
const MUST_DROP = ["MoreRewardTab", "PrivilegedTaskModule", "TaskShowData"];

const rules = cfg.enhance.rewrite;
const mainRules = rules.filter(r => r.endpoint === "video/adv/mainPage");
const rule = mainRules[0] || {};
const pluginRules = plugin.split("\n").filter(
  l => l.startsWith("response if ") && l.includes("mainPage"));
const deleteMatch = /response\.json\.delete\((\[.*\])\)/.exec(rule.action || "");
const dropPaths = deleteMatch ? JSON.parse(deleteMatch[1]) : [];
const dropKeys = dropPaths.map(k => k.replace(/^Data\./, ""));
const keep = rule.keep_whitelist || [];

// 按 Loon response.json.delete 的点分路径语义就地删键；路径中途不是对象就跳过。
function applyDelete(payload, paths) {
  const out = JSON.parse(JSON.stringify(payload));
  for (const key of paths) {
    const parts = key.split(".");
    let cur = out;
    for (let i = 0; i < parts.length - 1; i++) {
      if (!cur || typeof cur !== "object" || Array.isArray(cur)) { cur = null; break; }
      cur = cur[parts[i]];
    }
    if (cur && typeof cur === "object" && !Array.isArray(cur)) delete cur[parts[parts.length - 1]];
  }
  return out;
}

function runJq(expr, value) {
  try {
    return { rc: 0, out: execFileSync("/usr/bin/jq", ["-c", expr],
      { input: JSON.stringify(value), encoding: "utf8", stdio: ["pipe", "pipe", "pipe"] }) };
  } catch (e) {
    return { rc: 1, out: String((e.stderr || "").toString()).slice(0, 160) };
  }
}

const after = applyDelete(sample, dropPaths);

console.log("\n[1] 源与发布产物逐字对账（防假覆盖）");
check("源里恰好 1 条 mainPage 复写规则", mainRules.length === 1, String(mainRules.length));
check("发布插件里恰好 1 条 mainPage response 规则", pluginRules.length === 1, String(pluginRules.length));
check("生成行带 ${url} ~= URL Guard", pluginRules.length === 1 && pluginRules[0].includes("${url} ~="),
  (pluginRules[0] || "").slice(0, 120));
check("生成行 then 之后的动作与源 action 逐字一致",
  pluginRules.length === 1 && pluginRules[0].endsWith("then " + rule.action),
  (pluginRules[0] || "").slice(-160));
check("生成行不是整包 reject_dict / reject（保住任务与身份字段）",
  pluginRules.length === 1 && !/reject_dict|reject\(200/.test(pluginRules[0]));

console.log("\n[2] 规则形状与 URL 边界");
check("stage 是 response", rule.stage === "response", rule.stage);
check("endpoint 是 video/adv/mainPage", rule.endpoint === "video/adv/mainPage", rule.endpoint);
check("动作是 response.json.delete 批量 12 键，且全部是 Data. 点分路径",
  dropPaths.length === 12 && dropPaths.every(k => /^Data\.[A-Za-z][A-Za-z0-9]*$/.test(k)),
  JSON.stringify(dropPaths));
check("规则无 gate（与其余 15 条一致，净化常开）", rule.gate === undefined, String(rule.gate));
const rx = new RegExp(rule.url);
const good = [
  "https://h5.if.qidian.com/argus/api/v2/video/adv/mainPage",
  "https://h5.if.qidian.com/argus/api/v2/video/adv/mainPage?source=welfare",
  "https://magev6.if.qidian.com/argus/api/v3/video/adv/mainPage",
];
const bad = [
  "https://h5.if.qidian.com/argus/api/v2/video/adv/mainPageDialog",
  "https://h5.if.qidian.com/argus/api/v2/video/adv/finishWatch",
  "https://h5.if.qidian.com/argus/api/v2/video/adv/reportDialog",
];
check("URL 正则命中 h5/magev6、v2/v3、带 query 三个正例", good.every(u => rx.test(u)),
  good.filter(u => !rx.test(u)).join(","));
check("URL 正则不误伤 mainPageDialog / finishWatch / reportDialog",
  bad.every(u => !rx.test(u)), bad.filter(u => rx.test(u)).join(","));

console.log("\n[3] 白名单分类守卫（服务端新增 Data 键必须报红）");
check("keep_whitelist 恰好 11 键", keep.length === 11, String(keep.length));
check("keep 含 4 个广告激励模块（常驻 2 + 限时 2）", INCENTIVE.every(k => keep.includes(k)),
  JSON.stringify(INCENTIVE.filter(k => !keep.includes(k))));
check("keep 含 7 个身份/账户标量", SCALARS.every(k => keep.includes(k)) &&
  keep.filter(k => !INCENTIVE.includes(k)).length === 7, JSON.stringify(keep.filter(k => !INCENTIVE.includes(k))));
check("drop 含 MoreRewardTab / PrivilegedTaskModule / TaskShowData",
  MUST_DROP.every(k => dropKeys.includes(k)), JSON.stringify(MUST_DROP.filter(k => !dropKeys.includes(k))));
check("keep ∪ drop 恰好等于真机样本的全部 23 个 Data 键（无遗漏）",
  eq([...new Set([...keep, ...dropKeys])].sort(), keys(sample.Data)),
  JSON.stringify(keys(sample.Data).filter(k => !keep.includes(k) && !dropKeys.includes(k))));
check("keep ∩ drop 为空", keep.every(k => !dropKeys.includes(k)));
check("二次抓包证据的 data_keys 与真机样本逐键一致",
  eq([...capture.data_keys].sort(), keys(sample.Data)));
check("二次抓包证据的 task_counts 与真机样本一致",
  capture.task_counts["DailyBenefitModule.TaskList"] === sample.Data.DailyBenefitModule.TaskList.length &&
  capture.task_counts["VideoRewardTab.TaskList"] === sample.Data.VideoRewardTab.TaskList.length &&
  capture.task_counts["ReadingPageTaskModule.TaskList"] === sample.Data.ReadingPageTaskModule.TaskList.length &&
  capture.task_counts["MoreRewardTab.TaskList"] === sample.Data.MoreRewardTab.TaskList.length &&
  capture.task_counts["RedeemGifts"] === sample.Data.RedeemGifts.length,
  JSON.stringify(capture.task_counts));
check("二次抓包证据的 keep/drop 与源规则一致",
  eq([...capture.keep_incentive, ...capture.keep_render_scalars].sort(), [...keep].sort()) &&
  eq([...capture.drop].sort(), [...dropKeys].sort()));

console.log("\n[4] 双向断言：12 键删净 + 业务字段原样");
check("净化后 Data 恰好 11 键", keys(after.Data).length === 11, JSON.stringify(keys(after.Data)));
check("12 个非激励键全部消失", dropKeys.every(k => after.Data[k] === undefined),
  JSON.stringify(dropKeys.filter(k => after.Data[k] !== undefined)));
check("4 个激励模块对象与原文全等（不是只留空壳）",
  INCENTIVE.every(k => eq(after.Data[k], sample.Data[k])),
  JSON.stringify(INCENTIVE.filter(k => !eq(after.Data[k], sample.Data[k]))));
check("任务条数 9 / 3 / 6 原样",
  after.Data.DailyBenefitModule.TaskList.length === 9 &&
  after.Data.VideoRewardTab.TaskList.length === 3 &&
  after.Data.ReadingPageTaskModule.TaskList.length === 6);
check("限时任务 TaskId / Total / TaskType 原样",
  eq(after.Data.ReadingPageTaskModule.TaskList.map(t => [t.TaskId, t.Total, t.TaskType]),
    sample.Data.ReadingPageTaskModule.TaskList.map(t => [t.TaskId, t.Total, t.TaskType])) &&
  after.Data.ReadingPageTaskModule.TaskType === 300);
check("常驻激励 AdPositionCode 原样",
  eq(after.Data.DailyBenefitModule.TaskList.map(t => t.AdPositionCode),
    sample.Data.DailyBenefitModule.TaskList.map(t => t.AdPositionCode)));
check("SurpriseBenefit 的 Title / Desc / TaskId 原样",
  eq(after.Data.SurpriseBenefit, sample.Data.SurpriseBenefit));
check("7 个身份/账户标量原样（白屏防线）", SCALARS.every(k => after.Data[k] === sample.Data[k]),
  JSON.stringify(SCALARS.filter(k => after.Data[k] !== sample.Data[k])));
check("顶层 Result / Message / Data 包络原样，不是把整个响应清空",
  after.Result === sample.Result && after.Message === sample.Message &&
  after.Data !== undefined && typeof after.Data === "object" && !Array.isArray(after.Data));
check("4 个激励模块的 TaskList / 内容均非空（防「留了键但内容被清空」）",
  after.Data.DailyBenefitModule.TaskList.length > 0 &&
  after.Data.VideoRewardTab.TaskList.length > 0 &&
  after.Data.ReadingPageTaskModule.TaskList.length > 0 &&
  typeof after.Data.SurpriseBenefit.Title === "string" && after.Data.SurpriseBenefit.Title.length > 0);

console.log("\n[5] jq 白名单等价性与异常输入");
const jq = runJq(rule.jq_equivalent, sample);
check("jq_equivalent 在 /usr/bin/jq 实跑成功且与运行时 delete 输出全等",
  jq.rc === 0 && eq(JSON.parse(jq.out), after), jq.rc ? jq.out : "");
const abnormal = [
  [1, 2, 3], null, { Result: 0 }, { Data: [1, 2] },
  { Data: "x" }, { Data: null }, { Data: { Guid: 7 } },
];
abnormal.forEach((v, i) => {
  const r = runJq(rule.jq_equivalent, v);
  check("异常样本 #" + (i + 1) + " 不抛错且原样放行",
    r.rc === 0 && eq(JSON.parse(r.out), v), r.rc ? r.out : r.out.slice(0, 80));
});

console.log("\n[6] 反向证伪：断言必须有鉴别力");
const weakened = applyDelete(sample, dropPaths.filter(k => k !== "Data.MoreRewardTab"));
check("故意漏删 MoreRewardTab 时净化结果确实会多出该键（删除断言不是恒真）",
  weakened.Data.MoreRewardTab !== undefined && !eq(weakened, after));
const widened = rule.jq_equivalent.replace('"SurpriseBenefit"', '"SurpriseBenefit", "MoreRewardTab"');
const wj = runJq(widened, sample);
check("故意把 MoreRewardTab 加进 jq 白名单时输出确实变化（白名单断言不是恒真）",
  wj.rc === 0 && !eq(JSON.parse(wj.out), after) && JSON.parse(wj.out).Data.MoreRewardTab !== undefined,
  wj.rc ? wj.out : "");

console.log("\n[7] 证据与同 URL 脚本互斥");
const ev = rule.evidence || {};
check("evidence.kind = field-present（本轮规则尚未真机回抓，不冒充 effective）",
  ev.kind === "field-present", String(ev.kind));
check("evidence.har / url_hits 与 HAR 466 的 1 条 mainPage URL 相符",
  ev.har === "466_1794290256836.har" && ev.url_hits === 1, JSON.stringify(ev));
check("device_check 写明白屏回滚、新增键处理、_loon.rewrite 取证",
  /白屏/.test(ev.device_check || "") && /回滚/.test(ev.device_check || "") &&
  /_loon\.rewrite/.test(ev.device_check || ""));
check("proof 指向二次抓包登记与完整真机样本",
  /qidian_mainpage_20261110\.json/.test(ev.proof || "") &&
  /qidian_mainpage_limited\.json/.test(ev.proof || ""));
const deep = cfg.enhance.bindings.find(b => b.id === "engine-deep-clean");
check("engine-deep-clean 标 probe=true 且 pattern 覆盖 mainPage（复写命中即抑制脚本）",
  !!deep && deep.probe === true && /mainPage/.test(deep.pattern || ""),
  JSON.stringify(deep && { probe: deep.probe, pattern: (deep.pattern || "").slice(0, 80) }));

console.log("\nPASS=" + pass + " FAIL=" + fail);
process.exit(fail ? 1 : 0);
