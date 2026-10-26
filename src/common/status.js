/*
 * loon-plugins 共享脚本 · 插件状态自检（Loon generic 脚本，手动触发）
 * ------------------------------------------------------------
 * soda / douyin 共用同一份源码（本文件），家族差异（应用名、
 * 日志标签、跳转协议）由 src/common/families.json 注入。
 *
 * 用途：
 *   在 Loon 插件列表或脚本列表中点击「插件状态检查」按钮时手动执行，
 *   实时汇总打卡状态、广告统计、App 唤醒入口，无需等待定时任务。
 */

var SEEN_KEY = "@@LOG_TAG@@-welfare-seen";
var STATS_KEY = "@@LOG_TAG@@-ad-stats";

function dayKey() {
  var d = new Date();
  var m = String(d.getMonth() + 1);
  var day = String(d.getDate());
  return d.getFullYear() + "-" + (m.length < 2 ? "0" + m : m) + "-" +
    (day.length < 2 ? "0" + day : day);
}

function readStore(key) {
  try {
    if (typeof $persistentStore !== "undefined" && $persistentStore &&
        typeof $persistentStore.read === "function") {
      return $persistentStore.read(key) || "";
    }
  } catch (e) {}
  return "";
}

(function main() {
  var today = dayKey();
  var seen = readStore(SEEN_KEY);
  var seenToday = (seen === today);

  var statsText = "无广告记录";
  var rawStats = readStore(STATS_KEY);
  if (rawStats) {
    try {
      var s = JSON.parse(rawStats);
      if (s && s.day) {
        statsText = s.day + "：完成 " + s.n + " 次广告（约 " + Math.round(s.s / 60) + " 分钟）";
      }
    } catch (e) {}
  }

  var summary = seenToday ? "今日已打卡" : "今日未打卡";
  var detail = "福利打卡：" + (seenToday ? "✅ 正常（" + seen + "）" : "⚠️ 尚未打卡") + "\n" +
               "广告统计：" + statsText;

  console.log("[@@LOG_TAG@@-status] " + summary + " | " + statsText);

  try {
    if (typeof $notification !== "undefined" && $notification &&
        typeof $notification.post === "function") {
      $notification.post(
        "@@APP_NAME@@ · 状态自检",
        summary,
        detail,
        { "openUrl": "@@APP_SCHEME@@" }
      );
    }
  } catch (e) {}

  $done({
    title: "@@APP_NAME@@ 状态自检",
    summary: summary,
    content: detail
  });
})();
