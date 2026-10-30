/*
 * SodaClean · App 版本检查静音（Loon http-response 脚本，实验）
 * ----------------------------------------------------------------------------
 * 取证（20.5.0 主二进制，__cstring / Swift 内嵌类型名字符串，按地址序成簇）：
 *   luna/check-update                ← 端点（与 CollectAlbum / check_download 同簇）
 *   STNetProto.CheckUpdateRequest
 *   _TtC10STNetProto18CheckUpdateRequest
 *   嵌套类型名表：CheckUpdateRequest / Scene / Params / CodingKeys /
 *                 CheckUpdateResponseInfo / CheckMediaResult
 *   响应侧字段（同簇紧邻）：media_result / shark_expired_at / has_update
 * 真机佐证（README §10.6）：2026-10-29 的 23 小时日志里 `check-update/` 是
 *   638 条非广告 luna 请求之一——该端点确实在跑，luna 双主机承载。
 *
 * 【不要混淆的同形键（均不是 App 版本检查，绝不绑定）】
 *   check_update_info      gecko bytesync 通道
 *   check_update_result    贴纸/特效平台（/effect/api/panel/*）
 *   force_update           BDPSensitiveWordsService 敏感词库资源
 *   force_update_ts_ms     听歌房（ListenTogether）同步协议字段
 *
 * 设计原则（与 sanitize/settings 同源）：
 *   1. 保留服务端原始包络，只把 has_update 置 false —— 掉「要不要提示更新」
 *      这一分支，不参与任何支付/权益/结算逻辑（该端点是只读查询）
 *   2. 解析失败 / 非 JSON / 解不开的压缩 → 原样放行，最坏情况 = 提示还在
 *   3. CheckUpdateResponseInfo 的完整 Codable 键表静态未挖全：走「能解析才改、
 *      解析不动则放行」的防御式形态，等真实捕获响应后可再收紧
 *   4. 回写 body 时清掉过期的 content-encoding / content-length 头
 *      （与 sanitize.markHeaders 同一理由）
 */

/* ------------------------------------------------------------------ */
/* 开关                                                               */
/* ------------------------------------------------------------------ */
const ENABLED = true;          // false = 完全放行（快速回滚用）
const DRY_RUN = false;         // true = 只打日志不改响应（先观测一轮用）

/* ------------------------------------------------------------------ */
/* 通用工具（与 sanitize.min.js 同一套实现，保证行为一致）               */
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

/* Uint8Array -> UTF-8 字符串（不依赖 TextDecoder） */
function utf8(bytes) {
  var out = "", i = 0, n = bytes.length;
  while (i < n) {
    var b = bytes[i++] & 0xff;
    if (b < 0x80) {
      out += String.fromCharCode(b);
    } else if (b >= 0xc0 && b < 0xe0) {
      out += String.fromCharCode(((b & 0x1f) << 6) | (bytes[i++] & 0x3f));
    } else if (b >= 0xe0 && b < 0xf0) {
      out += String.fromCharCode(((b & 0x0f) << 12) | ((bytes[i++] & 0x3f) << 6) | (bytes[i++] & 0x3f));
    } else {
      var cp = ((b & 0x07) << 18) | ((bytes[i++] & 0x3f) << 12) | ((bytes[i++] & 0x3f) << 6) | (bytes[i++] & 0x3f);
      out += String.fromCodePoint(cp);
    }
  }
  return out;
}

/* 取响应体：JSON 字符串 / Uint8Array / gzip 三形态；
 * 插件 [Rewrite] 已统一 Accept-Encoding: gzip（常开），br 理论上不会再出现，
 * 保留 ceTag 诊断是为了万一服务端无视协商时的可定位性。 */
function readBody(resp) {
  var raw = (resp && resp.body) || "";
  var bytes = null;
  if (typeof Uint8Array !== "undefined" && raw instanceof Uint8Array) {
    bytes = raw;
  } else if (typeof raw === "string" && raw.length > 1 &&
             raw.charCodeAt(0) === 0x1f && raw.charCodeAt(1) === 0x8b) {
    bytes = new Uint8Array(raw.length);
    for (var i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i) & 0xff;
  } else {
    return typeof raw === "string" ? raw : "";
  }
  try {
    if (typeof $utils !== "undefined" && $utils && typeof $utils.ungzip === "function") {
      return utf8($utils.ungzip(bytes));
    }
  } catch (e) {
    console.log("[soda] ungzip failed: " + e);
  }
  return utf8(bytes);
}

function ceTag(resp) {
  try {
    var h = (resp && resp.headers) || {};
    var ce = "";
    for (var k in h) {
      if (String(k).toLowerCase() === "content-encoding") { ce = h[k]; break; }
    }
    ce = String(ce == null ? "" : ce).trim().toLowerCase();
    if (!ce || ce === "gzip" || ce === "x-gzip" || ce === "identity") return "";
    return ";ce=" + ce.replace(/[^a-z0-9,._-]/g, "");
  } catch (e) {
    return "";
  }
}

/*
 * 诊断标记（同 sanitize.markHeaders）：bodyChanged=true 时带回的 body 是
 * 未压缩 UTF-8 字符串，必须删掉旧的 content-encoding / content-length。
 */
function markHeaders(reason, bodyChanged) {
  try {
    var h = Object.assign({}, ($response && $response.headers) || {});
    h["X-Soda-Plugin"] = reason;
    if (bodyChanged) {
      var drop = [];
      for (var k in h) {
        if (!Object.prototype.hasOwnProperty.call(h, k)) continue;
        var lk = String(k).toLowerCase();
        if (lk === "content-encoding" || lk === "content-length") drop.push(k);
      }
      for (var i = 0; i < drop.length; i++) delete h[drop[i]];
    }
    return h;
  } catch (e) {
    return null;
  }
}

/* ------------------------------------------------------------------ */
/* has_update 静音                                                     */
/* ------------------------------------------------------------------ */
/* 归一化键名匹配（小写、去 _ 和 -），这样 has_update / hasUpdate /
 * 有同形后缀变体时也能对齐——但只改这一个键，绝无其它触点。 */
var UPDATE_KEY = "hasupdate";

function normalizeKey(k) {
  return String(k).toLowerCase().replace(/[_-]/g, "");
}

function deepFlip(node, path, log, depth) {
  if (depth > 12 || node === null || node === undefined) return;
  if (Array.isArray(node)) {
    for (var i = 0; i < node.length; i++) {
      deepFlip(node[i], path + "[" + i + "]", log, depth + 1);
    }
    return;
  }
  if (typeof node !== "object") return;
  for (var k of Object.keys(node)) {
    if (normalizeKey(k) === UPDATE_KEY && node[k] !== false) {
      var before = node[k];
      node[k] = false;
      log.push(path + "." + k + " : " + String(before) + " → false");
    }
    deepFlip(node[k], path + "." + k, log, depth + 1);
  }
}

(function main() {
  /* 绑定只透传 ${debugLog}（观测噪声）；enable=${skipUpdateCheck} 已在绑定层生效，
   * 这里保留脚本内的独立保险，与 settings.js 的 ENABLED 同语义。 */
  var pluginArgs = pargs(["debugLog"]);
  var verbose = pflag(pluginArgs, "debugLog", false);
  if (!ENABLED) {
    return $done({ headers: markHeaders("soda-check-update;skip=disabled", false) });
  }
  var url = ($request && $request.url) || "";
  var raw = readBody($response);
  if (verbose) console.log("[soda] check-update verbose on: " + url);

  /* 非 JSON（含 gzip 解不开、空体）原样放行，标记里带上 ce= */
  var head = (typeof raw === "string" ? raw : "").trimStart().slice(0, 1);
  if (head !== "{" && head !== "[") {
    console.log("[soda] check-update non-JSON passthrough: " + url);
    return $done({ headers: markHeaders("soda-check-update;skip=not-json" + ceTag($response), false) });
  }

  var obj;
  try {
    obj = JSON.parse(raw);
  } catch (e) {
    console.log("[soda] check-update JSON parse failed, passthrough: " + url);
    return $done({ headers: markHeaders("soda-check-update;skip=not-json" + ceTag($response), false) });
  }

  var log = [];
  deepFlip(obj, "$", log, 0);

  if (log.length === 0) {
    /* 没 has_update 键（响应形态与静态取证不一致）→ 一个字节都不动 */
    console.log("[soda] check-update no has_update key, untouched: " + url);
    return $done({ headers: markHeaders("soda-check-update;skip=no-key" + ceTag($response), false) });
  }

  if (DRY_RUN) {
    console.log("[soda] check-update DRY_RUN, would change:\n  " + log.join("\n  "));
    return $done({ headers: markHeaders("soda-check-update;dry-run" + ceTag($response), false) });
  }

  console.log("[soda] check-update " + log.length + " change(s)\n  " + log.join("\n  "));
  $done({ body: JSON.stringify(obj), headers: markHeaders("soda-check-update;has_update=false", true) });
})();
