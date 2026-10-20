/*
 * douyin · 广告域名拦截（Loon http-request 脚本）
 * ------------------------------------------------------------
 * 用途：让「域名拦截」也能用 [Argument] 开关控制。
 *
 * 为什么不用 [Rule]：
 *   Loon 的 [Rule] 是静态配置，不能按插件参数启停。写死会让
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
 *      要 100% 拦截请改用 [Rule] 手动严格模式（见 soda.plugin 注释）。
 *   3. 被拦的域名在 App 侧可能表现为「广告加载失败」，App 自身的补偿逻辑
 *      （例如赠送时长）由 App 决定，插件不伪造任何奖励。
 */

/* 被拦截的广告 / 归因域名（与 soda.plugin 的 [Rule] 严格模式保持一致） */
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

    const args = (typeof $argument === "object" && $argument) ? $argument : null;

    /* 只有明确打开 blockAdDomains 才拦截，避免被误挂到别的规则上 */
    if (!args || args.blockAdDomains !== true) {
      return $done({});
    }

    /* 保奖励模式：激励广告必须能正常加载，直接放行 */
    if (args.rewardSafe === true) {
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
