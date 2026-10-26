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

function runStatus(scriptCode, storeData) {
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
    "$done", "$persistentStore", "$notification", "console", scriptCode
  );

  fn((v) => { doneOut = v; }, $persistentStore, $notification, { log: () => {} });

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

console.log(`PASS=${pass} FAIL=${fail}`);
if (fail > 0) process.exit(1);
