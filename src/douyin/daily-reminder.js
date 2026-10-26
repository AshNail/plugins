/*
 * loon-plugins 共享脚本 · 每日领取提醒（Loon cron 脚本）
 * ------------------------------------------------------------
 * soda / douyin 共用同一份源码（本文件），家族差异（日志前缀、
 * 存储键前缀、通知文案）由 src/common/families.json 注入。
 *
 * 用途：每天定时提醒领奖励——当天打开过福利页就不打扰。
 *
 * 明确不做的事：
 *   - 不代打开 App、不代播放广告、不代点「领取」；
 *   - 不向 incentive/done 等发奖接口发起任何请求
 *     （发奖请求需要 x-argus/x-gorgon/x-ladon/x-medusa 与 bd-ticket-guard
 *      设备级签名，脚本无法生成；自动领取=伪造请求=IVT）；
 *   - 只读 $persistentStore 内本插件自己写的键，不依赖任何接口调用。
 *
 * 配对：welfare-stamp.js 在打开福利页时打当天日期的卡。
 */

var SEEN_KEY = "douyin-welfare-seen";
var STATS_KEY = "douyin-ad-stats";

function dayKey() {
  var d = new Date();
  var m = String(d.getMonth() + 1);
  var day = String(d.getDate());
  return d.getFullYear() + "-" + (m.length < 2 ? "0" + m : m) + "-" +
    (day.length < 2 ? "0" + day : day);
}

function readStats() {
  try {
    if (typeof $persistentStore === "undefined" || !$persistentStore ||
        typeof $persistentStore.read !== "function") return "";
    var raw = $persistentStore.read(STATS_KEY);
    if (!raw) return "";
    var s = JSON.parse(raw);
    if (!s || !s.day) return "";
    return "最近统计（" + s.day + "）：" + s.n + " 次广告 / 共 " + s.s +
      " 秒（约 " + Math.round(s.s / 60) + " 分钟）";
  } catch (e) {
    return "";
  }
}

try {
  var today = dayKey();
  var seen = null;
  try {
    if (typeof $persistentStore !== "undefined" && $persistentStore &&
        typeof $persistentStore.read === "function") {
      seen = $persistentStore.read(SEEN_KEY);
    }
  } catch (e) { /* 存储不可用按未打卡处理 */ }

  if (seen === today) {
    console.log("[douyin-reminder] 今日已打开福利页，不提醒");
  } else {
    var stats = readStats();
    $notification.post(
      "抖音 · 今日奖励待领",
      "今天还没打开福利页",
      "打开抖音福利页完成今天的领取任务（攒时长 / 翻卡 / 签到）。" +
        (stats ? " " + stats : "") +
        "。插件只做提醒，不代看广告、不代领取。",
      ""
    );
    console.log("[douyin-reminder] 已发送提醒（未打卡）");
    try {
      if (typeof $persistentStore !== "undefined" && $persistentStore &&
          typeof $persistentStore.write === "function") {
        $persistentStore.write("", SEEN_KEY);
      }
    } catch (e) { /* 清理失败不影响 */ }
  }
} catch (e) {
  console.log("[douyin-reminder] 异常 " + e);
}

$done({});
