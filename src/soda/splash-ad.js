/*
 * SodaClean · 开屏广告请求拦截（Loon http-request 脚本）
 * ------------------------------------------------------------
 * 取证（2026-10-20 HAR 384_1792499198027.har，20:27 实测）：
 *   ads5-normal-hl.zijieapi.com/api/ad/splash/luna/v15/      4,721 B  开屏广告配置（CSJ）
 *   ads5-normal-hl.zijieapi.com/api/ad/splash/stock/            42 B  库存查询
 *   ads5-normal-hl.zijieapi.com/api/ad/splash/stat/ack/v1/     125 B  上报
 *   ad.zijieapi.com/api/ad/v1/inspire/                      32,034 B  激励广告（★ 奖励链路，不拦）
 *   ad.zijieapi.com/api/incentive/marketing/done                     激励发奖回调（★ 不拦）
 *
 * 也就是说：开屏广告和激励广告虽然都走穿山甲（CSJ），
 * 但路径/域名是分开的：
 *   开屏端点家族（IPA 内全量核对，2026-10-22）：
 *     /api/ad/splash/{luna,aweme}/v14|v15/   配置（v14/v15、luna/aweme 双族）
 *     /api/ad/splash/stock/realtime/v15/     实时库存
 *     /api/ad/v[0-9]/(ack/)?splash/         v1 库存 + v2 ack（未来路径漂移兜底）
 *     以上全部属于"开屏素材获取与登记"，拦截动作只对该家族返回 {}；
 *   激励 → ad.zijieapi.com/api/ad/v1/inspire/**（奖励要用，绝不能拦）
 *
 * 本脚本只拦开屏那一段，返回空 JSON 让 SDK 拿不到广告；
 * 走 http-request 阶段，请求不会真正发出去。
 * 开关：blockSplashAd（默认关）。
 */

/* ------------------------------------------------------------------ */
/* Loon 插件参数（每个脚本独立内置）                                  */
/* ------------------------------------------------------------------ */
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

(function main() {
  try {
    const url = ($request && $request.url) || "";

    const args = pargs(["blockSplashAd"]);
    if (!pflag(args, "blockSplashAd", false)) {
      return $done({});
    }

    const isSplash =
      /(^|\/\/)[a-z0-9.-]*zijieapi\.com\/api\/ad\/splash\//i.test(url) ||
      /(^|\/\/)[a-z0-9.-]*zijieapi\.com\/api\/ad\/v[0-9]\/(?:ack\/)?splash\//i.test(url);
    if (!isSplash) {
      return $done({});
    }

    console.log("[soda-splash] blocked splash ad request: " + url);
    return $done({
      response: {
        status: 200,
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: "{}"
      }
    });
  } catch (e) {
    console.log("[soda-splash] error, passthrough: " + e);
    $done({});
  }
})();
