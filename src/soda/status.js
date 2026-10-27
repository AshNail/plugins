/*
 * loon-plugins 共享脚本 · 插件状态自检（Loon generic 脚本，手动触发）
 * ------------------------------------------------------------
 * soda / douyin 共用同一份源码（本文件），家族差异（应用名、
 * 日志标签、跳转协议）由 src/common/families.json 注入。
 *
 * 用途：
 *   在 Loon 插件列表或脚本列表中点击「插件状态检查」按钮时手动执行，
 *   实时汇总打卡状态、广告统计、App 唤醒入口，无需等待定时任务。
 *   通知模式由 [Argument] statusNotify 的 select 控制：
 *   notification 弹通知并带 openUrl，silent 只写日志与结果页。
 */

var SEEN_KEY = "soda-welfare-seen";
var STATS_KEY = "soda-ad-stats";

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

/*
 * Generic 绑定把全部开关透传进来；结果页与通知里给出一份
 * 「当前开关摘要 + 冲突提醒」。标签只覆盖两家族真实存在的开关，
 * 不认识的键自动忽略。
 */
var SWITCH_LABELS = [
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
  ["logTaskTitles", "日志带标题"]
];

function readArgs() {
  var r;
  try { r = (typeof $argument === "undefined") ? null : $argument; } catch (e) { r = null; }
  if (!r) return {};
  if (typeof r === "string") {
    var o = {};
    var parts = r.split(/[&;,]/);
    for (var i = 0; i < parts.length; i++) {
      var kv = parts[i].split("=");
      if (kv.length >= 2) o[kv[0].trim()] = kv.slice(1).join("=");
    }
    return o;
  }
  if (typeof r === "object") return r;
  return {};
}

function isOn(v) {
  return v === true || v === "true" || v === 1 || v === "1";
}

function switchSummary(args) {
  var on = [];
  for (var i = 0; i < SWITCH_LABELS.length; i++) {
    if (isOn(args[SWITCH_LABELS[i][0]])) on.push(SWITCH_LABELS[i][1]);
  }
  if (isOn(args.dailyReminder)) {
    on.push("每日提醒" + (args.reminderCron ? "(" + args.reminderCron + ")" : ""));
  }
  return on.join("、") || "全部默认";
}

function switchWarnings(args) {
  var out = [];
  if (isOn(args.killRewardAds)) {
    out.push("⚠️ 冲突：killRewardAds —— 激励广告完全不发，相关奖励会失效");
  }
  if (isOn(args.rewardSafe) && isOn(args.cleanAds)) {
    out.push("⚠️ 冲突：rewardSafe+cleanAds —— 脚本只保护非开屏端点，建议只开一种");
  }
  if (isOn(args.rewardSafe) && isOn(args.settingsClean)) {
    out.push("⚠️ 冲突：rewardSafe+settingsClean —— 设置层清理会被放行");
  }
  if (isOn(args.rewardSafe) && isOn(args.blockAdDomains)) {
    out.push("⚠️ 冲突：rewardSafe+blockAdDomains —— 域名拦截会被放行");
  }
  if (isOn(args.treasureMinimal) && isOn(args.killRewardAds)) {
    out.push("⚠️ 冲突：treasureMinimal+killRewardAds —— 福利页只剩攒时长，但激励已断");
  }
  return out;
}

/*
 * statusNotify 是 [Argument] select，"notification"（默认）弹通知，
 * "silent" 只写日志和 $done 结果页。兼容字符串参数与对象参数两种
 * 传递形态，缺省时保持旧行为。
 */
function notifyEnabled() {
  try {
    return readArgs().statusNotify !== "silent";
  } catch (e) {
    return true;
  }
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

  var args = readArgs();
  var switches = switchSummary(args);
  var warns = switchWarnings(args);

  var summary = seenToday ? "今日已打卡" : "今日未打卡";
  var detail = "福利打卡：" + (seenToday ? "✅ 正常（" + seen + "）" : "⚠️ 尚未打卡") + "\n" +
               "广告统计：" + statsText + "\n" +
               "开关状态：" + switches;
  for (var w = 0; w < warns.length; w++) detail += "\n" + warns[w];

  console.log("[soda-status] " + summary + " | " + statsText + " | " + switches);

  try {
    if (notifyEnabled() && typeof $notification !== "undefined" && $notification &&
        typeof $notification.post === "function") {
      $notification.post(
        "汽水音乐 · 状态自检",
        summary,
        detail,
        { "openUrl": "qishui://" }
      );
    }
  } catch (e) {}

  $done({
    title: "汽水音乐 状态自检",
    summary: summary,
    content: detail
  });
})();
