"use strict";

/*
 * src/args/*.json 是插件参数、状态看板标签、README 参数表的唯一事实源。
 * 本测试锁定：schema 自身语义、三处生成物无漂移、共享开关跨家族一致。
 */

const fs = require("fs");
const path = require("path");
const args = require("../tools/gen-args");

const ROOT = path.resolve(__dirname, "..");

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
function read(rel) {
  return fs.readFileSync(path.join(ROOT, rel), "utf8");
}

let schemas = null;
let loadError = "";
try {
  schemas = args.loadSchemas();
} catch (error) {
  loadError = error.message;
}
check("schema loads without validation errors", schemas !== null, loadError);

if (schemas) {
  const families = schemas.families;
  check("schema declares soda + douyin", Object.keys(families).sort().join(",") === "douyin,soda",
    Object.keys(families).join(","));

  // ---- 1. 标签顺序与内容 ----
  const expectedLabels = [
    ["rewardSafe", "保奖励"],
    ["splashClean", "清开屏"],
    ["cleanAds", "去广告"],
    ["cleanFeedAds", "清信息流广告"],
    ["killRewardAds", "断激励"],
    ["blockAdDomains", "域名拦截"],
    ["blockSplashAd", "开屏请求拦截"],
    ["settingsClean", "设置层清理"],
    ["hideDouyinEntry", "隐藏听抖音入口"],
    ["hideDouyinTab", "隐藏听抖音条目"],
    ["treasureMinimal", "福利页精简"],
    ["cleanUpsell", "弹窗/演出清理"],
    ["cleanActivity", "活动入口清理"],
    ["debugLog", "只读日志"],
    ["logTaskTitles", "日志带标题"],
    ["dailyReminder", "每日提醒"],
    ["skipUpdateCheck", "版本检查静音"]
  ];
  const labels = args.labelEntries(schemas);
  check("SWITCH_LABELS order/content is pinned", JSON.stringify(labels) === JSON.stringify(expectedLabels),
    JSON.stringify(labels));

  // ---- 2. 关键默认值 ----
  const pinned = {
    soda: {
      rewardSafe: true,
      splashClean: true,
      cleanAds: false,
      killRewardAds: false,
      blockAdDomains: false,
      settingsClean: false,
      dailyReminder: false,
      skipUpdateCheck: false,
      blockSplashAd: true,
      statusNotify: "notification"
    },
    douyin: {
      treasureMinimal: true,
      cleanFeedAds: false,
      killRewardAds: false,
      cleanUpsell: false,
      cleanActivity: false,
      blockAdDomains: false,
      blockSplashAd: true,
      dailyReminder: false,
      statusNotify: "notification"
    }
  };
  for (const family of ["soda", "douyin"]) {
    const byName = new Map(families[family].switches.map((item) => [item.name, item]));
    for (const name of Object.keys(pinned[family])) {
      check(`${family}: ${name} default is pinned`, byName.get(name) &&
        byName.get(name).default === pinned[family][name],
        byName.get(name) && byName.get(name).default);
    }
    check(`${family}: reminder cron default`,
      byName.get("reminderCron") && byName.get("reminderCron").default === "30 20 * * *");
    check(`${family}: statusNotify select values`,
      byName.get("statusNotify") &&
      JSON.stringify(byName.get("statusNotify").values) === '["notification","silent"]');
  }

  // ---- 3. 共享开关跨家族语义一致 ----
  const soda = new Map(families.soda.switches.map((item) => [item.name, item]));
  const douyin = new Map(families.douyin.switches.map((item) => [item.name, item]));
  let sharedMismatch = "";
  for (const [name, item] of soda) {
    if (!douyin.has(name)) continue;
    const other = douyin.get(name);
    const same = item.type === other.type &&
      JSON.stringify(item.default) === JSON.stringify(other.default) &&
      item.label === other.label;
    if (!same) sharedMismatch += `${name}:${item.type}/${item.default}/${item.label}!=` +
      `${other.type}/${other.default}/${other.label};`;
  }
  check("shared switches agree across families", !sharedMismatch, sharedMismatch);

  // ---- 4. 生成物逐字节一致 ----
  let changes = [];
  let planError = "";
  try {
    changes = args.plan(schemas).filter((entry) => entry.changed);
  } catch (error) {
    planError = error.message;
  }
  check("generated regions exist", !planError, planError);
  check("generated regions are drift-free", changes.length === 0,
    changes.map((entry) => entry.file + " @ " + entry.diff).join(" | "));

  for (const family of Object.keys(families).sort()) {
    const schema = families[family];
    const plugin = read(`plugins/${family}/${family}.plugin`);
    const readme = read(`plugins/${family}/README.md`);
    check(`${family}: plugin [Argument] matches schema`,
      plugin.includes(args.renderArgumentBlock(schema)));
    check(`${family}: README table matches schema`,
      readme.includes(args.renderReadmeBlock(schema)));
    check(`${family}: plugin markers appear once`,
      plugin.split(`GENERATED ARGUMENTS from src/args/${family}.json`).length - 1 === 1);
  }
  check("SWITCH_LABELS matches schema",
    read("src/common/status.js").includes(args.renderLabelsBlock(schemas)));

  // ---- 5. 每个声明参数至少被一条绑定引用 ----
  for (const family of Object.keys(families).sort()) {
    const plugin = read(`plugins/${family}/${family}.plugin`);
    const referenced = new Set(
      [...plugin.matchAll(/\$\{([A-Za-z_]\w*)\}/g)].map((match) => match[1])
    );
    const orphan = families[family].switches
      .map((item) => item.name)
      .filter((name) => !referenced.has(name));
    check(`${family}: every declared argument is referenced`, orphan.length === 0,
      orphan.join(","));
  }

  // ---- 6. schema 自校验拒绝坏输入（生成器验证器本身） ----
  const bad = {
    family: "bad",
    app: "bad",
    switches: [
      { name: "x", type: "switch", default: "yes", tag: "a", desc: "b", label: "c", readme: "d" }
    ]
  };
  const badErrors = args.validateFamily(bad, path.join(ROOT, "src", "args", "bad.json"));
  check("schema validator rejects a non-boolean switch default",
    badErrors.some((line) => /switch default must be true or false/.test(line)),
    badErrors.join(" | "));
}

console.log(`PASS=${pass} FAIL=${fail}`);
if (fail > 0) process.exit(1);
