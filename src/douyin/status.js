/*
 * loon-plugins 共享脚本 · 插件状态自检（Loon generic 脚本，手动触发）
 * ------------------------------------------------------------
 * soda / douyin 共用同一份源码（本文件），家族差异（应用名、
 * 日志标签、跳转协议）由 src/common/families.json 注入。
 *
 * 用途：
 *   在 Loon 插件列表或脚本列表中点击「插件状态检查」按钮时手动执行，
 *   实时汇总打卡状态、广告统计、App 唤醒入口，无需等待定时任务。
 *   同时输出 Loon 运行环境（$loon / $script / $environment /
 *   $config.getConfig()），方便判断脚本是否运行在预期版本与模式下。
 *   通知模式由 [Argument] statusNotify 的 select 控制：
 *   notification 弹通知并带 openUrl，silent 只写日志与结果页。
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
/* >>> GENERATED SWITCH_LABELS from src/args/*.json -- do not edit (npm run build:args) */
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
  ["logTaskTitles", "日志带标题"],
  ["dailyReminder", "每日提醒"],
  ["skipUpdateCheck", "版本检查静音"],
];
/* <<< GENERATED SWITCH_LABELS */

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
    var key = SWITCH_LABELS[i][0];
    if (!isOn(args[key])) continue;
    var label = SWITCH_LABELS[i][1];
    /* 每日提醒带上当前 cron，省得再去插件参数里翻。 */
    if (key === "dailyReminder" && args.reminderCron) {
      label += "(" + args.reminderCron + ")";
    }
    on.push(label);
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
  /* Loon 同一响应只跑第一条命中的脚本：清理/隐藏会抢占只读日志 */
  if (isOn(args.cleanAds) && isOn(args.debugLog)) {
    out.push("ℹ️ 提示：cleanAds+debugLog —— 被清理的端点会挤掉只读日志");
  }
  if (isOn(args.treasureMinimal) && isOn(args.debugLog)) {
    out.push("ℹ️ 提示：treasureMinimal+debugLog —— 福利页日志会被精简脚本挤掉");
  }
  if (isOn(args.hideDouyinTab) && isOn(args.debugLog)) {
    out.push("ℹ️ 提示：hideDouyinTab+debugLog —— 福利页日志会被隐藏脚本挤掉");
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

/* envLine() 顺手记下运行模式，给下面的「模式告警」用 */
var RUNNING_MODEL = null;

function envText(v) {
  if (typeof v === "string") return v;
  try { return JSON.stringify(v); } catch (e) { return String(v); }
}

/*
 * Loon 环境诊断：$loon / $script / $environment / $config.getConfig()
 * 在旧 build 或测试环境里可能缺失，逐项 typeof 守卫；缺失项直接跳过。
 */
function envLine() {
  var bits = [];
  try {
    if (typeof $loon !== "undefined" && $loon) bits.push(envText($loon));
  } catch (e) {}
  try {
    if (typeof $script !== "undefined" && $script && $script.name) {
      var name = String($script.name);
      if ($script.startTime) name += " @ " + String($script.startTime);
      bits.push("脚本 " + name);
    }
  } catch (e) {}
  try {
    var environment = null;
    if (typeof $environment !== "undefined" && $environment) {
      environment = $environment;
    } else if (typeof $envirnoment !== "undefined" && $envirnoment) {
      environment = $envirnoment;
    }
    if (environment && environment.params && environment.params.nodeInfo) {
      bits.push("节点 " + envText(environment.params.nodeInfo));
    }
  } catch (e) {}
  try {
    if (typeof $config !== "undefined" && $config &&
        typeof $config.getConfig === "function") {
      var raw = $config.getConfig();
      var cfg = typeof raw === "string" ? JSON.parse(raw) : raw;
      if (cfg && typeof cfg.running_model !== "undefined") {
        var models = ["直连", "分流", "全局代理"];
        var idx = Number(cfg.running_model);
        RUNNING_MODEL = idx;
        /*
         * 0 = 全局直连。这种模式下 Loon 不执行规则、不进 [MITM]、不跑脚本，
         * 插件等于没装——而界面上只会显示「直连」两个字，用户不会知道
         * 自己刚装的去广告插件一个动作都没执行。这里必须点名。
         */
        bits.push("运行模式 " + (models[idx] || ("#" + cfg.running_model)) +
          (idx === 0 ? "（⚠️ 插件不生效）" : ""));
      }
    }
  } catch (e) {}
  return bits.join(" · ");
}

/* gzip 响应清理的分水岭：$utils.ungzip 自 Loon 3.5.1(988) 提供。 */
function capabilityLine() {
  var ok = false;
  try {
    ok = typeof $utils !== "undefined" && $utils &&
      typeof $utils.ungzip === "function";
  } catch (e) {}
  return "gzip 解压 " + (ok ? "✅" : "❌（需 Loon 3.5.1(988)+）");
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
  var env = envLine();
  if (RUNNING_MODEL === 0) {
    warns.unshift(
      "⚠️ 当前是「全局直连」：Loon 不执行规则、不解密、不跑脚本，" +
      "本插件所有功能都不会生效。改成「分流」或「全局代理」后再看。"
    );
  }

  var summary = seenToday ? "今日已打卡" : "今日未打卡";
  var detail = "福利打卡：" + (seenToday ? "✅ 正常（" + seen + "）" : "⚠️ 尚未打卡") + "\n" +
               "广告统计：" + statsText + "\n" +
               "开关状态：" + switches;
  if (env) detail += "\n运行环境：" + env;
  detail += "\nLoon 能力：" + capabilityLine();
  detail += "\n静态层：QUIC 回退 16 域 · h2 · 压缩→gzip（常开）";
  for (var w = 0; w < warns.length; w++) detail += "\n" + warns[w];

  console.log("[douyin-status] " + summary + " | " + statsText + " | " + switches +
    (env ? " | env=" + env : ""));

  try {
    if (notifyEnabled() && typeof $notification !== "undefined" && $notification &&
        typeof $notification.post === "function") {
      $notification.post(
        "抖音 · 状态自检",
        summary,
        detail,
        /* 点通知：打开 App + 把同一份诊断复制到剪贴板（直接粘进 issue 即可） */
        { "openUrl": "snssdk1128://", "clipboard": detail }
      );
    }
  } catch (e) {}

  $done({
    title: "抖音 状态自检",
    summary: summary,
    content: detail
  });
})();
