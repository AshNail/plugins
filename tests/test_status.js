"use strict";

const loadScript = require("./load-script");
const sodaStatus = loadScript("status.js", "soda");
const douyinStatus = loadScript("status.js", "douyin");

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

function runStatus(scriptCode, storeData, argument) {
  let doneOut = null;
  let notifOut = null;
  const store = Object.assign({}, storeData || {});

  const $persistentStore = {
    read: (k) => store[k] || "",
    write: (v, k) => { store[k] = v; return true; }
  };

  const $notification = {
    post: (title, subtitle, body, attach) => {
      notifOut = { title, subtitle, body, attach };
    }
  };

  const fn = new Function(
    "$done", "$persistentStore", "$notification", "$argument", "console", scriptCode
  );

  fn((v) => { doneOut = v; }, $persistentStore, $notification, argument,
    { log: () => {} });

  return { doneOut, notifOut };
}

function todayKey() {
  const d = new Date();
  const m = String(d.getMonth() + 1);
  const day = String(d.getDate());
  return d.getFullYear() + "-" + (m.length < 2 ? "0" + m : m) + "-" +
    (day.length < 2 ? "0" + day : day);
}

// 1. Soda 未打卡测试
{
  const res = runStatus(sodaStatus, {});
  check("soda: doneOut has title", res.doneOut && res.doneOut.title.includes("汽水音乐"));
  check("soda: doneOut has summary '未打卡'", res.doneOut && res.doneOut.summary.includes("未打卡"));
  check("soda: notifOut posted", res.notifOut && res.notifOut.title.includes("汽水音乐"));
  check("soda: notif attach openUrl is qishui://", res.notifOut && res.notifOut.attach && res.notifOut.attach.openUrl === "qishui://");
}

// 2. Soda 今日已打卡 + 广告统计
{
  const store = {
    "soda-welfare-seen": todayKey(),
    "soda-ad-stats": JSON.stringify({ day: todayKey(), n: 5, s: 150 })
  };
  const res = runStatus(sodaStatus, store);
  check("soda: doneOut marked seen today", res.doneOut && res.doneOut.summary.includes("已打卡"));
  check("soda: content includes stats", res.doneOut && res.doneOut.content.includes("完成 5 次广告"));
}

// 3. Douyin 未打卡与 openUrl 检查
{
  const res = runStatus(douyinStatus, {});
  check("douyin: doneOut has title", res.doneOut && res.doneOut.title.includes("抖音"));
  check("douyin: doneOut has summary '未打卡'", res.doneOut && res.doneOut.summary.includes("未打卡"));
  check("douyin: notif attach openUrl is snssdk1128://", res.notifOut && res.notifOut.attach && res.notifOut.attach.openUrl === "snssdk1128://");
}

// 4. statusNotify select：silent 只写结果页，不弹通知
{
  const res = runStatus(sodaStatus, {}, { statusNotify: "silent" });
  check("soda: silent 不弹通知", res.notifOut === null, JSON.stringify(res.notifOut));
  check("soda: silent 仍返回结果页", res.doneOut && res.doneOut.title.includes("汽水音乐"));
  const def = runStatus(sodaStatus, {}, { statusNotify: "notification" });
  check("soda: notification 弹通知", def.notifOut && def.notifOut.title.includes("汽水音乐"));
}

// 5. 状态看板：soda 默认开关摘要
{
  const args = {
    statusNotify: "silent", rewardSafe: true, splashClean: true, cleanAds: false,
    killRewardAds: false, blockAdDomains: false, blockSplashAd: false,
    settingsClean: false, hideDouyinEntry: false, hideDouyinTab: false,
    debugLog: false, logTaskTitles: false, dailyReminder: false,
    reminderCron: "30 20 * * *"
  };
  const res = runStatus(sodaStatus, {}, args);
  const body = res.doneOut.content;
  check("soda: 结果页有开关状态行", body.includes("开关状态："), body);
  check("soda: 摘要含保奖励", body.includes("保奖励"), body);
  check("soda: 摘要含清开屏", body.includes("清开屏"), body);
  check("soda: 默认组合无冲突警告", !body.includes("冲突："), body);
}

// 6. 状态看板：soda 冲突组合逐条提醒
{
  const args = {
    statusNotify: "notification", rewardSafe: true, splashClean: true, cleanAds: true,
    killRewardAds: true, blockAdDomains: true, blockSplashAd: true,
    settingsClean: true, hideDouyinEntry: false, hideDouyinTab: false,
    debugLog: true, logTaskTitles: true, dailyReminder: true,
    reminderCron: "5 9 * * *"
  };
  const res = runStatus(sodaStatus, {}, args);
  const body = res.doneOut.content;
  check("soda: 提醒 killRewardAds", body.includes("killRewardAds ——"), body);
  check("soda: 提醒 rewardSafe+cleanAds", body.includes("rewardSafe+cleanAds"), body);
  check("soda: 提醒 rewardSafe+settingsClean", body.includes("rewardSafe+settingsClean"), body);
  check("soda: 提醒 rewardSafe+blockAdDomains", body.includes("rewardSafe+blockAdDomains"), body);
  check("soda: 摘要含每日提醒时间", body.includes("每日提醒(5 9 * * *)"), body);
  check("soda: 通知正文也带冲突提醒", res.notifOut && res.notifOut.body.includes("冲突："),
    JSON.stringify(res.notifOut));
}

// 7. 状态看板：douyin 摘要与攒时长冲突
{
  const args = {
    statusNotify: "silent", treasureMinimal: true, cleanFeedAds: true,
    killRewardAds: true, cleanUpsell: false, cleanActivity: true,
    blockAdDomains: false, blockSplashAd: true, debugLog: true,
    dailyReminder: false, reminderCron: "30 20 * * *"
  };
  const res = runStatus(douyinStatus, {}, args);
  const body = res.doneOut.content;
  check("douyin: 摘要含福利页精简", body.includes("福利页精简"), body);
  check("douyin: 摘要含清信息流广告", body.includes("清信息流广告"), body);
  check("douyin: 摘要含开屏请求拦截", body.includes("开屏请求拦截"), body);
  check("douyin: 摘要含只读日志", body.includes("只读日志"), body);
  check("douyin: 提醒 killRewardAds", body.includes("killRewardAds ——"), body);
  check("douyin: 提醒 treasureMinimal+killRewardAds",
    body.includes("treasureMinimal+killRewardAds"), body);
  check("douyin: silent 不弹通知", res.notifOut === null, JSON.stringify(res.notifOut));
}

console.log(`PASS=${pass} FAIL=${fail}`);
if (fail > 0) process.exit(1);
