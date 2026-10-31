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
 *     - 开关打开时回 200 + application/json + {}（与 [Rewrite] 的
 *       reject_dict(200) 同形状），广告 SDK 拿不到广告也不会去重试；
 *     - 激励广告路径（inspire / inspire_preload / marketing/done）
 *       永远放行：这几条是发奖链路，拦掉只会让奖励失败，不属于“去广告”。
 *       即使 rewardSafe=false、blockAdDomains=true，也绝不拦。
 *       allowlist 覆盖所有被拦主机，防止服务端把激励请求切到 lianmengapi
 *       等兄弟域后又被误杀。
 *
 * 已知限制：
 *   1. HTTPS 必须先 MITM 解密才能匹配到域名，所以 [MITM] 里要声明这些域名。
 *   2. HTTP/3(QUIC) 不经过 MITM。v2.8.0 起插件用常开的 [Rule]
 *      AND+PROTOCOL,QUIC 把 [MITM] 域强制回退到 TCP，所以这条不再需要用户处理；
 *      如果哪天删了那些回退规则，本脚本会重新出现“部分请求看不见”的情况。
 *   3. 被拦的域名在 App 侧可能表现为「广告加载失败」，App 自身的补偿逻辑
 *      （例如赠送时长）由 App 决定，插件不伪造任何奖励。
 *   4. 全局 DNS 黑洞（例如 ads.plugin 里的 Host 映射）发生在脚本之前，
 *      本脚本无法挽救；启用本插件保奖励模式前，先把 ad.zijieapi.com
 *      从其它广告插件的 Host/REJECT 名单里移出。
 *
 * 与 ads.plugin 的分层：
 *   lianmengapi.snssdk.com 与 ads?-normal*.zijieapi.com（Pangle 分片族）
 *   同时被 ads.plugin 的 [Host] DNS 层 + DOMAIN-WILDCARD 家族层拦截；
 *   ad.zijieapi.com 自 2026-10-31 起已从 ads.plugin 移出，由本脚本按
 *   路径区分激励与非激励流量。ads.plugin 仍是独立 DNS 兜底层，两者可共存。
 */

/* 被拦截的广告 / 归因域名（lint 会校验：本数组 = [Script] 正则 = [MITM] 超集） */
/* ad.zijieapi.com 同时承载激励广告与发奖回调，不能整域拦；下面按路径放行。 */
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

/* 被拦截的广告 / 归因域名（lint 会校验：本数组 = [Script] 正则 = [MITM] 超集）
   条目可以是精确域名，也可以是 glob：`?` 恰好一个字符、`*` 任意字符。
   分片族用 glob 表达：Pangle 按服务端下发在 ads3/ads5 × 区域后缀之间切换，
   逐个枚举必然漏掉没见过的分片，一条 `ads?-normal*.zijieapi.com` 全收。 */
const BLOCKED_HOSTS = [
  "ad.zijieapi.com",
  "lianmengapi.snssdk.com",
  "ads?-normal*.zijieapi.com",
  "zlink.ugsdk.cn",
  "praisewindow.ugsdk.cn"
];

/* glob → RegExp：只把 `*`/`?` 当通配，其余字符按字面量转义。 */
const BLOCKED_RX = BLOCKED_HOSTS.map(function (pattern) {
  var src = "";
  for (var i = 0; i < pattern.length; i++) {
    var c = pattern.charAt(i);
    if (c === "*") src += ".*";
    else if (c === "?") src += ".";
    else src += /[a-z0-9.-]/.test(c) ? c : "\\" + c;
  }
  return new RegExp("^" + src + "$");
});

function hostBlocked(host) {
  for (var i = 0; i < BLOCKED_RX.length; i++) {
    if (BLOCKED_RX[i].test(host)) return true;
  }
  return false;
}

function hostOf(url) {
  const m = String(url || "").match(/^https?:\/\/([^/:?#]+)/i);
  return m ? String(m[1]).toLowerCase() : "";
}

/* 激励链路只认这三条路径（穿山甲 inspire / 预拉取 / 发奖回调）。
   路径匹配与主机无关：服务端换兄弟域时分片规则仍会命中，但发奖不会断。 */
const REWARD_PATH_RX =
  /^\/api\/(?:ad\/v1\/inspire(?:_preload)?|incentive\/marketing\/done)(?:\/|$|\?)/i;

function pathOf(url) {
  const m = String(url || "").match(/^https?:\/\/[^/]+(\/[^?#]*)?/i);
  return m && m[1] ? m[1] : "/";
}

function isRewardRequest(url) {
  return REWARD_PATH_RX.test(pathOf(url));
}

(function main() {
  try {
    const url = ($request && $request.url) || "";

    const args = pargs(["blockAdDomains"]);

    /* 只有明确打开 blockAdDomains 才拦截，避免被误挂到别的规则上 */
    if (!pflag(args, "blockAdDomains", false)) {
      return $done({});
    }

    /* 激励广告/发奖回调永远放行：拦截它们只会让奖励失败，不是去广告。 */
    if (isRewardRequest(url)) {
      console.log("[@@LOG_TAG@@-domains] keep reward ad, passthrough: " + url);
      return $done({});
    }

    /* 二次确认域名，避免脚本被改挂后误伤其它请求 */
    const host = hostOf(url);
    if (host === "" || !hostBlocked(host)) {
      return $done({});
    }

    console.log("[@@LOG_TAG@@-domains] blocked: " + url);
    /* 回包形状与 [Rewrite] 的 reject_dict(200) 对齐：200 + application/json + {}。
       文档明确「reject(200,"{}") 返回普通文本；需要 JSON Content-Type 时用
       reject_dict」。广告 SDK 一律按 JSON 解析，空 text/plain 会落进
       "解析失败 → 重试" 分支，等于把一次拦截变成一次重试风暴。 */
    return $done({
      response: {
        status: 200,
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: "{}"
      }
    });
  } catch (e) {
    console.log("[@@LOG_TAG@@-domains] error, passthrough: " + e);
    $done({});
  }
})();
