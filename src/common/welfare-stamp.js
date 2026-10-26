/*
 * loon-plugins 共享脚本 · 福利页打卡（Loon http-response 脚本）
 * ------------------------------------------------------------
 * soda / douyin 共用同一份源码（本文件），家族差异（日志前缀、
 * 存储键前缀）由 src/common/families.json 注入。
 *
 * 用途：给「每日领取提醒」提供依据——当天是否打开过福利页。
 *
 * 行为：
 *   - 只在 Response Header 阶段执行（requires_body=false），不读、不改响应体；
 *   - 命中 /luna/treasure/task/page 时把今天日期写进 $persistentStore；
 *   - 与 cron 脚本 daily-reminder.js 配对：当天打过卡 → 晚上不提醒；
 *   - enable 跟随 dailyReminder 开关。
 */

var SEEN_KEY = "@@LOG_TAG@@-welfare-seen";

function dayKey() {
  var d = new Date();
  var m = String(d.getMonth() + 1);
  var day = String(d.getDate());
  return d.getFullYear() + "-" + (m.length < 2 ? "0" + m : m) + "-" +
    (day.length < 2 ? "0" + day : day);
}

function debugLog() {
  try {
    var r = (typeof $argument === "undefined") ? null : $argument;
    if (r && typeof r === "object" && r.debugLog === true) console.log("[@@LOG_TAG@@-reminder] debug");
  } catch (e) { /* 参数缺失时静默 */ }
}

try {
  if (typeof $persistentStore !== "undefined" && $persistentStore &&
      typeof $persistentStore.write === "function") {
    $persistentStore.write(dayKey(), SEEN_KEY);
    console.log("[@@LOG_TAG@@-reminder] 已记录今日打开福利页 " + dayKey());
  }
} catch (e) { /* 存储不可用时静默，不影响响应 */ }

debugLog();
$done({});
