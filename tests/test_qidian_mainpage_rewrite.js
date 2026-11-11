/*
 * qidian mainPage 只留激励任务 · v4.2.1 双向回归
 * ------------------------------------------------------------
 * 用户 2026-11-10 20:25 裁决：mainPage 只保留激励任务（常驻 + 限时）。
 * 用户 2026-11-11 13:23 追加裁决：SurpriseBenefit 整模块与 VideoRewardTab
 * 内两条单次激励条目（T2024010102 订阅券 / T2023111401 白泽装扮）一并剔除。
 * 本套件把裁决钉在七处：
 *
 *   1. 源 src/apps/qidian.json 与发布插件 plugins/qidian/qidian.plugin 逐字对账
 *      （防「源写了、产物没写对」的假覆盖）；
 *   2. 白名单分类守卫：keep_whitelist ∪ delete 名单必须恰好等于真机样本的全部
 *      Data 键。服务端以后新增 Data 键，样本一更新这里就红，禁止静默漏网；
 *   3. 双向断言：13 个非激励键确实消失，同时 3 个激励模块与 7 个身份标量
 *      逐字原样、顶层包络不动、VideoRewardTab 只剩 1 条且与原文全等；
 *   4. 两条规则按官方同侧顺序语义串联（先整键 delete、后条目 jq 过滤），
 *      组合输出必须与手工基准完全等价；
 *   5. jq 表达式用 /usr/bin/jq 实跑对账；异常输入不得让整次净化失败；
 *   6. 反向证伪：断言必须有鉴别力（漏删键 / 漏删条目都要能测出来）；
 *   7. 证据与同 URL 脚本互斥登记。
 *
 * 取舍：整键删除走官方 response.json.delete（HAR 466 实证命中并改包）；
 * 条目级过滤 delete 做不到，走 response.json.jq（clean-mainpage-videoreward-filter，
 * |= / map(select) 尚未真机回抓，回滚单位=删那一条规则）。
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
const INCENTIVE = ["DailyBenefitModule", "VideoRewardTab", "ReadingPageTaskModule"];
const SCALARS = ["Guid", "EncryptedGuid", "NickName", "Avatar",
  "AutoJumpSignDetailForHM", "DiffAmount", "NineReward"];
const MUST_DROP = ["MoreRewardTab", "PrivilegedTaskModule", "TaskShowData", "SurpriseBenefit"];
const DROP_RAWIDS = ["T2024010102", "T2023111401"];
const KEEP_TASKID = "1218712929269776388"; // T2024010101「完成3个广告任务得奖励」

const rules = cfg.enhance.rewrite;
const mainRules = rules.filter(r => r.endpoint === "video/adv/mainPage");
const rule = mainRules.find(r => r.id === "clean-mainpage-incentive-only") || {};
const filterRule = mainRules.find(r => r.id === "clean-mainpage-videoreward-filter") || {};
const pluginRules = plugin.split("\n").filter(
  l => l.startsWith("response if ") && l.includes("mainPage"));
const deleteMatch = /response\.json\.delete\((\[.*\])\)/.exec(rule.action || "");
const dropPaths = deleteMatch ? JSON.parse(deleteMatch[1]) : [];
const dropKeys = dropPaths.map(k => k.replace(/^Data\./, ""));
const keep = rule.keep_whitelist || [];
const filterRawIds = filterRule.filter_rawids || [];

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

// 从 filter 规则的 action 提取 jq 表达式（剥壳 + 反转义）
const filterJqMatch = /^response\.json\.jq\("(.*)"\)$/.exec(filterRule.action || "");
const filterExpr = filterJqMatch ? filterJqMatch[1].replace(/\\"/g, '"') : "";

// 手工基准：删 13 键 + TaskList 剔除 2 条
function manualBaseline() {
  const out = applyDelete(sample, dropPaths);
  out.Data.VideoRewardTab.TaskList = out.Data.VideoRewardTab.TaskList.filter(
    t => !(t && typeof t === "object" && DROP_RAWIDS.includes(t.TaskRawId)));
  return out;
}

// 组合运行：先 delete（等价 jq 模拟），后条目过滤——对应 Loon 同侧顺序语义
function combinedRun(src) {
  const delExpr = 'if type == "object" and (.Data | type) == "object" then del(' +
    dropKeys.map(k => ".Data." + k).join(", ") + ') else . end';
  const step1 = runJq(delExpr, src);
  if (step1.rc !== 0) return { rc: 1, out: step1.out };
  const step2 = runJq(filterExpr, JSON.parse(step1.out));
  return step2;
}

const after = manualBaseline();

console.log("\n[1] 源与发布产物逐字对账（防假覆盖）");
check("源里恰好 2 条 mainPage 复写规则（delete + jq filter）", mainRules.length === 2,
  String(mainRules.length));
check("发布插件里恰好 2 条 mainPage response 规则", pluginRules.length === 2,
  String(pluginRules.length));
check("两条生成行都带 ${url} ~= URL Guard",
  pluginRules.length === 2 && pluginRules.every(l => l.includes("${url} ~=")),
  (pluginRules[0] || "").slice(0, 120));
check("delete 生成行动作与源 action 逐字一致",
  pluginRules.some(l => l.endsWith("then " + rule.action)),
  (pluginRules.find(l => l.includes("response.json.delete")) || "").slice(-160));
check("jq 过滤生成行动作与源 action 逐字一致",
  pluginRules.some(l => l.endsWith("then " + filterRule.action)),
  (pluginRules.find(l => l.includes("response.json.jq")) || "").slice(-160));
check("生成行不是整包 reject_dict / reject（保住任务与身份字段）",
  pluginRules.every(l => !/reject_dict|reject\(200/.test(l)));

console.log("\n[2] 规则形状与 URL 边界");
check("delete 规则 stage/endpoint 正确",
  rule.stage === "response" && rule.endpoint === "video/adv/mainPage");
check("filter 规则 stage/endpoint/URL 与 delete 规则一致（同侧串联前提）",
  filterRule.stage === "response" && filterRule.endpoint === rule.endpoint &&
  filterRule.url === rule.url);
check("delete 动作批量 13 键，且全部是 Data. 点分路径",
  dropPaths.length === 13 && dropPaths.every(k => /^Data\.[A-Za-z][A-Za-z0-9]*$/.test(k)),
  JSON.stringify(dropPaths));
check("filter 规则声明 filter_rawids = T2024010102 / T2023111401",
  eq([...filterRawIds].sort(), [...DROP_RAWIDS].sort()), JSON.stringify(filterRawIds));
check("filter jq 表达式按 TaskRawId 匹配且含逐层类型守卫",
  filterExpr.includes('TaskRawId') && !filterExpr.includes('TaskId') &&
  filterExpr.includes('"T2024010102"') && filterExpr.includes('"T2023111401"') &&
  filterExpr.includes('if type == "object"') &&
  filterExpr.includes('(.Data | type) == "object"') &&
  filterExpr.includes('(.Data.VideoRewardTab | type) == "object"') &&
  filterExpr.includes('(.Data.VideoRewardTab.TaskList | type) == "array"') &&
  filterExpr.includes('if type == "string"'),
  filterExpr.slice(0, 120));
check("两条规则都无 gate（净化常开）",
  rule.gate === undefined && filterRule.gate === undefined);
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
check("keep_whitelist 恰好 10 键", keep.length === 10, String(keep.length));
check("keep 含 3 个广告激励模块", INCENTIVE.every(k => keep.includes(k)),
  JSON.stringify(INCENTIVE.filter(k => !keep.includes(k))));
check("keep 含 7 个身份/账户标量", SCALARS.every(k => keep.includes(k)) &&
  keep.filter(k => !INCENTIVE.includes(k)).length === 7, JSON.stringify(keep.filter(k => !INCENTIVE.includes(k))));
check("drop 含 MoreRewardTab / PrivilegedTaskModule / TaskShowData / SurpriseBenefit",
  MUST_DROP.every(k => dropKeys.includes(k)), JSON.stringify(MUST_DROP.filter(k => !dropKeys.includes(k))));
check("keep ∪ drop 恰好等于真机样本的全部 23 个 Data 键（无遗漏）",
  eq([...new Set([...keep, ...dropKeys])].sort(), keys(sample.Data)),
  JSON.stringify(keys(sample.Data).filter(k => !keep.includes(k) && !dropKeys.includes(k))));
check("keep ∩ drop 为空", keep.every(k => !dropKeys.includes(k)));
check("二次抓包证据的 data_keys 与真机样本逐键一致",
  eq([...capture.data_keys].sort(), keys(sample.Data)));
check("二次抓包证据的 keep/drop 与源规则一致（含 2026-11-11 追加裁决）",
  eq([...capture.keep_incentive, ...capture.keep_render_scalars].sort(), [...keep].sort()) &&
  eq([...capture.drop].sort(), [...dropKeys].sort()));
check("证据登记的条目级剔除与 filter_rawids 一致",
  eq(capture.drop_task_items["VideoRewardTab.TaskList"].map(t => t.TaskRawId).sort(), [...DROP_RAWIDS].sort()));
check("证据登记的条目级保留与样本 T2024010101 一致",
  capture.keep_task_items["VideoRewardTab.TaskList"].length === 1 &&
  capture.keep_task_items["VideoRewardTab.TaskList"][0].TaskId === KEEP_TASKID);

console.log("\n[4] 双向断言：13 键删净 + 条目过滤 + 业务字段原样");
check("净化后 Data 恰好 10 键", keys(after.Data).length === 10, JSON.stringify(keys(after.Data)));
check("13 个非激励键全部消失（含 SurpriseBenefit）",
  dropKeys.every(k => after.Data[k] === undefined),
  JSON.stringify(dropKeys.filter(k => after.Data[k] !== undefined)));
check("3 个激励模块对象与原文全等或按裁决过滤",
  eq(after.Data.DailyBenefitModule, sample.Data.DailyBenefitModule) &&
  eq(after.Data.ReadingPageTaskModule, sample.Data.ReadingPageTaskModule) &&
  typeof after.Data.VideoRewardTab === "object");
check("DailyBenefit / ReadingPageTask 的 TaskList 9 / 6 条原样",
  after.Data.DailyBenefitModule.TaskList.length === 9 &&
  after.Data.ReadingPageTaskModule.TaskList.length === 6);
check("VideoRewardTab.TaskList 只剩 1 条",
  after.Data.VideoRewardTab.TaskList.length === 1,
  JSON.stringify(after.Data.VideoRewardTab.TaskList.map(t => t.TaskRawId)));
check("保留条目是 T2024010101「完成3个广告任务得奖励」且与原文全等",
  after.Data.VideoRewardTab.TaskList[0].TaskRawId === "T2024010101" &&
  after.Data.VideoRewardTab.TaskList[0].TaskId === KEEP_TASKID &&
  eq(after.Data.VideoRewardTab.TaskList[0],
    sample.Data.VideoRewardTab.TaskList.find(t => t.TaskId === KEEP_TASKID)));
check("被剔除两条的 TaskId 不在净化结果里",
  after.Data.VideoRewardTab.TaskList.every(t =>
    t.TaskId !== "1218712929269776389" && t.TaskId !== "1218712929269776387"));
check("VideoRewardTab 模块级字段（Title/CurrentTime/ExpireTime）原样",
  after.Data.VideoRewardTab.Title === sample.Data.VideoRewardTab.Title &&
  after.Data.VideoRewardTab.CurrentTime === sample.Data.VideoRewardTab.CurrentTime &&
  after.Data.VideoRewardTab.ExpireTime === sample.Data.VideoRewardTab.ExpireTime);
check("限时任务 TaskId / Total / TaskType 原样",
  eq(after.Data.ReadingPageTaskModule.TaskList.map(t => [t.TaskId, t.Total, t.TaskType]),
    sample.Data.ReadingPageTaskModule.TaskList.map(t => [t.TaskId, t.Total, t.TaskType])) &&
  after.Data.ReadingPageTaskModule.TaskType === 300);
check("常驻激励 AdPositionCode 原样",
  eq(after.Data.DailyBenefitModule.TaskList.map(t => t.AdPositionCode),
    sample.Data.DailyBenefitModule.TaskList.map(t => t.AdPositionCode)));
check("7 个身份/账户标量原样（白屏防线）", SCALARS.every(k => after.Data[k] === sample.Data[k]),
  JSON.stringify(SCALARS.filter(k => after.Data[k] !== sample.Data[k])));
check("顶层 Result / Message / Data 包络原样，不是把整个响应清空",
  after.Result === sample.Result && after.Message === sample.Message &&
  after.Data !== undefined && typeof after.Data === "object" && !Array.isArray(after.Data));
check("3 个激励模块内容均非空（防「留了键但内容被清空」）",
  after.Data.DailyBenefitModule.TaskList.length > 0 &&
  after.Data.VideoRewardTab.TaskList.length > 0 &&
  after.Data.ReadingPageTaskModule.TaskList.length > 0);

console.log("\n[5] jq 等价性与异常输入");
const jqKeep = runJq(rule.jq_equivalent, sample);
const afterKeysOnly = applyDelete(sample, dropPaths);
check("jq_equivalent 实跑成功且与整键 delete 输出全等",
  jqKeep.rc === 0 && eq(JSON.parse(jqKeep.out), afterKeysOnly), jqKeep.rc ? jqKeep.out : "");
const combined = combinedRun(sample);
check("delete + jq 过滤的组合输出与手工基准完全等价（官方同侧顺序语义）",
  combined.rc === 0 && eq(JSON.parse(combined.out), after), combined.rc ? combined.out : "");
const abnormalKeys = [
  [1, 2, 3], null, { Result: 0 }, { Data: [1, 2] },
  { Data: "x" }, { Data: null }, { Data: { Guid: 7 } },
];
abnormalKeys.forEach((v, i) => {
  const r = runJq(rule.jq_equivalent, v);
  check("整键白名单异常样本 #" + (i + 1) + " 不抛错且原样放行",
    r.rc === 0 && eq(JSON.parse(r.out), v), r.rc ? r.out : r.out.slice(0, 80));
});
const abnormalFilter = [
  [1, 2, 3], null, { Result: 0 },
  { Data: { VideoRewardTab: { TaskList: "x" } } },
  { Data: { VideoRewardTab: 5 } },
  { Data: { VideoRewardTab: { TaskList: [{ TaskRawId: 123 }, { x: 1 }] } } },
];
abnormalFilter.forEach((v, i) => {
  const r = runJq(filterExpr, v);
  check("条目过滤异常样本 #" + (i + 1) + " 不抛错且原样放行",
    r.rc === 0 && eq(JSON.parse(r.out), v), r.rc ? r.out : r.out.slice(0, 80));
});
const mixedList = { Data: { VideoRewardTab: { TaskList: [
  { TaskRawId: 123 }, { TaskRawId: "T2024010102" }, { x: 1 },
] } } };
const mixedRun = runJq(filterExpr, mixedList);
check("混合条目样本：目标条目被删、异常条目保留（宁可漏删不误删）",
  mixedRun.rc === 0 && eq(JSON.parse(mixedRun.out).Data.VideoRewardTab.TaskList,
    [{ TaskRawId: 123 }, { x: 1 }]), mixedRun.rc ? mixedRun.out : "");

console.log("\n[6] 反向证伪：断言必须有鉴别力");
const weakened = applyDelete(sample, dropPaths.filter(k => k !== "Data.MoreRewardTab"));
check("故意漏删 MoreRewardTab 时净化结果确实会多出该键（删除断言不是恒真）",
  weakened.Data.MoreRewardTab !== undefined && !eq(weakened, afterKeysOnly));
const widened = rule.jq_equivalent.replace('"ReadingPageTaskModule"', '"ReadingPageTaskModule", "MoreRewardTab"');
const wj = runJq(widened, sample);
check("故意把 MoreRewardTab 加进 jq 白名单时输出确实变化（白名单断言不是恒真）",
  wj.rc === 0 && !eq(JSON.parse(wj.out), afterKeysOnly) && JSON.parse(wj.out).Data.MoreRewardTab !== undefined,
  wj.rc ? wj.out : "");
const leakFilter = filterExpr.replace('. != "T2024010102" and ', "");
const lf = runJq(leakFilter, sample);
check("故意让条目过滤漏删 T2024010102 时 TaskList 确实多出该条（条目断言不是恒真）",
  lf.rc === 0 && JSON.parse(lf.out).Data.VideoRewardTab.TaskList.length === 2 &&
  JSON.parse(lf.out).Data.VideoRewardTab.TaskList.some(t => t.TaskRawId === "T2024010102"),
  lf.rc ? lf.out : "");

console.log("\n[7] 证据与同 URL 脚本互斥");
const ev = rule.evidence || {};
const fev = filterRule.evidence || {};
check("两条规则 evidence.kind = field-present（尚未真机回抓，不冒充 effective）",
  ev.kind === "field-present" && fev.kind === "field-present",
  JSON.stringify([ev.kind, fev.kind]));
check("两条规则 evidence.har / url_hits 与 HAR 466 的 1 条 mainPage URL 相符",
  ev.har === "466_1794290256836.har" && ev.url_hits === 1 &&
  fev.har === "466_1794290256836.har" && fev.url_hits === 1);
check("delete 规则 device_check 写明白屏回滚、新增键处理、_loon.rewrite 取证",
  /白屏/.test(ev.device_check || "") && /回滚/.test(ev.device_check || "") &&
  /_loon\.rewrite/.test(ev.device_check || ""));
check("filter 规则 device_check 写明 jq 失效回滚单位与 _loonOriginal 对照",
  /回滚/.test(fev.device_check || "") && /_loonOriginal/.test(fev.device_check || "") &&
  /TaskList/.test(fev.device_check || ""));
const deep = cfg.enhance.bindings.find(b => b.id === "engine-deep-clean");
check("engine-deep-clean 标 probe=true 且 pattern 覆盖 mainPage（复写命中即抑制脚本）",
  !!deep && deep.probe === true && /mainPage/.test(deep.pattern || ""),
  JSON.stringify(deep && { probe: deep.probe, pattern: (deep.pattern || "").slice(0, 80) }));

console.log("\nPASS=" + pass + " FAIL=" + fail);
process.exit(fail ? 1 : 0);
