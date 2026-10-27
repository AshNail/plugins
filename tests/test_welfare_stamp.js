"use strict";

const loadScript = require("./load-script");
const sodaSanitize = loadScript("sanitize.js", "soda");
const sodaObserve = loadScript("reward-observe.js", "soda");
const sodaReminder = loadScript("daily-reminder.js", "soda");
const douyinTreasure = loadScript("treasure.js", "douyin");
const douyinObserve = loadScript("observe.js", "douyin");
const douyinReminder = loadScript("daily-reminder.js", "douyin");

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

function todayKey() {
  const d = new Date();
  const m = String(d.getMonth() + 1);
  const day = String(d.getDate());
  return d.getFullYear() + "-" + (m.length < 2 ? "0" + m : m) + "-" +
    (day.length < 2 ? "0" + day : day);
}

function makeStore(seed) {
  const data = Object.assign({}, seed || {});
  return {
    data,
    read: (k) => (k in data ? data[k] : ""),
    write: (v, k) => { data[k] = v; return true; },
    remove: (k) => { delete data[k]; return true; }
  };
}

function runScript(code, opts) {
  let out = null;
  let notif = null;
  const logs = [];
  const store = opts.store || makeStore();
  const fn = new Function(
    "$request", "$response", "$done", "$argument", "$persistentStore",
    "$notification", "console", code
  );
  fn(
    { url: opts.url },
    { body: opts.body || JSON.stringify({ status_code: 0 }) },
    (v) => { out = v; },
    opts.argument || {},
    store,
    { post: (...a) => { notif = a; } },
    { log: (...a) => logs.push(a.join(" ")) }
  );
  return { out, notif, logs, store };
}

console.log("\n== 1. douyin treasure 胜出时写打卡 ==");
{
  const store = makeStore();
  runScript(douyinTreasure, {
    url: "https://beta-luna.douyin.com/luna/treasure/task/page/v2",
    argument: { treasureMinimal: true, dailyReminder: true },
    store
  });
  check("douyin-welfare-seen = 今天",
    store.data["douyin-welfare-seen"] === todayKey(),
    JSON.stringify(store.data));
}

console.log("\n== 2. dailyReminder=false 不写打卡 ==");
{
  const store = makeStore();
  runScript(douyinTreasure, {
    url: "https://beta-luna.douyin.com/luna/treasure/task/page/v2",
    argument: { treasureMinimal: true, dailyReminder: false },
    store
  });
  check("store 保持为空", Object.keys(store.data).length === 0, JSON.stringify(store.data));
}

console.log("\n== 3. douyin observe 胜出时写打卡 ==");
{
  const store = makeStore();
  runScript(douyinObserve, {
    url: "https://beta-luna.douyin.com/luna/treasure/task/page/v2",
    argument: { dailyReminder: true },
    body: JSON.stringify({ status_code: 0, task_infos: [] }),
    store
  });
  check("douyin-welfare-seen = 今天",
    store.data["douyin-welfare-seen"] === todayKey(),
    JSON.stringify(store.data));
}

console.log("\n== 4. soda sanitize 胜出时写打卡 ==");
{
  const store = makeStore();
  runScript(sodaSanitize, {
    url: "https://beta-luna.douyin.com/luna/treasure/task/page/v2",
    argument: { rewardSafe: false, cleanAds: true, dailyReminder: true },
    store
  });
  check("soda-welfare-seen = 今天",
    store.data["soda-welfare-seen"] === todayKey(),
    JSON.stringify(store.data));
}

console.log("\n== 5. soda reward-observe 胜出时写打卡 ==");
{
  const store = makeStore();
  runScript(sodaObserve, {
    url: "https://api.qishui.com/luna/treasure/task/page",
    argument: { dailyReminder: true },
    store
  });
  check("soda-welfare-seen = 今天",
    store.data["soda-welfare-seen"] === todayKey(),
    JSON.stringify(store.data));
}

console.log("\n== 6. 打卡写入后，提醒脚本当天不再打扰 ==");
{
  const store = makeStore({ "douyin-welfare-seen": todayKey() });
  const r = runScript(douyinReminder, { url: "", store });
  check("未发送通知", r.notif === null, JSON.stringify(r.notif));
  check("日志说明已打卡", r.logs.join(" ").includes("今日已打开福利页"), r.logs.join(" "));
}

console.log("\n== 7. 未打卡时提醒脚本仍会通知 ==");
{
  const r = runScript(douyinReminder, { url: "", store: makeStore() });
  check("发送了通知", !!r.notif && r.notif[0].includes("抖音"), JSON.stringify(r.notif));
  check("通知未伪造领取", !JSON.stringify(r.notif).includes("自动领取"), JSON.stringify(r.notif));
}

console.log("\n== 8. 端到端：treasure 写入的 store 直接被 reminder 读取 ==");
{
  const store = makeStore();
  runScript(douyinTreasure, {
    url: "https://beta-luna.douyin.com/luna/treasure/task/page/v2",
    argument: { dailyReminder: true },
    store
  });
  const r = runScript(douyinReminder, { url: "", store });
  check("reminder 认到今天的打卡", r.notif === null, JSON.stringify(r.notif));
}

console.log("\n" + (fail === 0 ? "ALL PASS" : "FAILURES") +
  "  pass=" + pass + " fail=" + fail);
process.exit(fail === 0 ? 0 : 1);
