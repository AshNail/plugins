/*
 * loon-plugins 共享脚本 · 广告域名拦截（Loon http-request 脚本）
 * ------------------------------------------------------------
 * soda / douyin 共用同一份源码（本文件），家族差异（日志前缀、
 * rewardSafe 默认值）由 src/common/families.json 注入的占位符提供。
 *
 * 用途：让「域名拦截」也能用 [Argument] 开关控制。
 *
 * 为什么不用 [Rule]：
 *   Loon 的 [Rule] 是静态配置，不能按 [Argument] 开关启停。写死会让
 *   rewardSafe（保奖励）模式被广告域名误伤；不写又等于丢掉
 *   「完整域名拦截」这个能力。
 *   这里改用 http-request 脚本 + enable={blockAdDomains}：
 *     - 开关关闭时脚本根本不执行，流量不受影响；
 *     - 开关打开时返回 200 空响应，广告 SDK 拿不到广告；
 *     - rewardSafe=true 时脚本内部直接放行，激励广告照常播放。
 *
 * 已知限制：
 *   1. HTTPS 必须先 MITM 解密才能匹配到域名，所以 [MITM] 里要声明这些域名。
 *   2. 走 HTTP/3(QUIC) 的请求不经过 MITM，可能拦不住；
 *      要 100% 拦截请改用 [Rule] 手动严格模式（见各 family 插件文件注释）。
 *   3. 被拦的域名在 App 侧可能表现为「广告加载失败」，App 自身的补偿逻辑
 *      （例如赠送时长）由 App 决定，插件不伪造任何奖励。
 *
 * 与 ads.plugin 的分层：
 *   下面 5 个域名中的 ad.zijieapi.com / lianmengapi.snssdk.com /
 *   ads5-normal-hl.zijieapi.com 已同时被 ads.plugin 的 [Host] DNS 层拦截；
 *   本脚本是 App 内 MITM 层的兜底与精准控制（ads.plugin 刷奖励时要关）。
 */

/* 被拦截的广告 / 归因域名（与各 family 插件的 [Rule] 严格模式保持一致；lint 会校验四处一致） */
/* ------------------------------------------------------------------ */
/* Loon 插件参数（每个脚本独立内置）                                  */
/* ------------------------------------------------------------------ */
/* 新版 Script 语法（3.5.1(983)+）下 $argument 是对象，键为参数名； */
/* 旧版语法实测不会把开关值传进来，所以这里同时兼容对象 / 位置数组 / */
/* "k=v" 字符串三种形态，开关值也兼容 true / "true" / 1 / "1"。       */
function pargs(keys) {
  var o = {}, r;
  try { r = (typeof $argument === "undefined") ? null : $argument; } catch (e) { r = null; }
  if (r === null || r === undefined) return null;
  var t = Object.prototype.toString.call(r);
  if (t === "[object Object]") {
    for (var k in r) if (Object.prototype.hasOwnProperty.call(r, k)) o[k] = r[k];
    return o;
  }
  if (t === "[object Array]") {
    for (var i = 0; i < r.length && keys && i < keys.length; i++) o[keys[i]] = r[i];
    return o;
  }
  if (typeof r === "string") {
    var p = r.split(/[&;,]/);
    for (var j = 0; j < p.length; j++) {
      var kv = p[j].split("=");
      if (kv.length >= 2) o[kv[0].trim()] = kv.slice(1).join("=");
    }
    return o;
  }
  return null;
}

function pflag(args, name, fallback) {
  if (!args || !(name in args)) return fallback;
  var v = args[name];
  if (v === true || v === "true" || v === 1 || v === "1") return true;
  if (v === false || v === "false" || v === 0 || v === "0") return false;
  return fallback;
}

const BLOCKED_HOSTS = [
  "ad.zijieapi.com",
  "lianmengapi.snssdk.com",
  "ads5-normal-hl.zijieapi.com",
  "zlink.ugsdk.cn",
  "praisewindow.ugsdk.cn"
];

function hostOf(url) {
  const m = String(url || "").match(/^https?:\/\/([^\/:?#]+)/i);
  return m ? String(m[1]).toLowerCase() : "";
}

(function main() {
  try {
    const url = ($request && $request.url) || "";

    const args = pargs(["blockAdDomains", "rewardSafe"]);

    /* 只有明确打开 blockAdDomains 才拦截，避免被误挂到别的规则上 */
    if (!pflag(args, "blockAdDomains", false)) {
      return $done({});
    }

    /* 保奖励模式：激励广告必须能正常加载，直接放行（soda 默认开 / douyin 默认关） */
    if (pflag(args, "rewardSafe", false)) {
      console.log("[douyin-domains] rewardSafe=on, passthrough: " + url);
      return $done({});
    }

    /* 二次确认域名，避免脚本被改挂后误伤其它请求 */
    const host = hostOf(url);
    if (host === "" || BLOCKED_HOSTS.indexOf(host) === -1) {
      return $done({});
    }

    console.log("[douyin-domains] blocked: " + url);
    return $done({
      response: {
        status: 200,
        headers: { "Content-Type": "text/plain; charset=utf-8" },
        body: ""
      }
    });
  } catch (e) {
    console.log("[douyin-domains] error, passthrough: " + e);
    $done({});
  }
})();
