/*
 * SodaClean · TTKitchen 设置层净化（Loon http-response 脚本，实验）
 * ----------------------------------------------------------------------------
 * 取证（20.5.0 二进制）：
 *   - 设置端点：https://conf.qishui.com/service/settings/v3/
 *     字符串地址 0x10ebe7100；唯一代码引用 0x10692d6ec / 0x10692d6f0
 *   - 调用链：TTKitchenSyncer
 *       -[TTKitchenSyncer synchronizeSettingsWithParameters:disableAutoRequest:
 *          URLString:header:callback:]
 *       -> TTNetworkManager requestForJSONWithResponse:... GET ...
 *   - 响应按 JSON 解析，合并进 TTKitchenManager 的设置字典。
 *
 * 设置键（STABSettingsService 注册表，地址见补充报告）：
 *   commerce_ad_config            0x10e7c6d90  商业化广告配置
 *   commerce_ad_feed_config       0x10e7c6ec0  信息流广告配置
 *   reward_ad_fallback_config     0x10e7c6ff0  兜底广告配置
 *   feed_reward_ad_config         0x10e7f46d0  信息流激励广告配置
 *   splash_ad_early_load_config   0x10e7f0100  开屏广告提前加载配置
 *   ad_webview_sdk_config         0x10e7c6e00  广告 WebView SDK 配置
 *   timor_should_enable_ad        0x10e7fa9d0  是否启用广告
 *   kBasicModeDisableRewardAdEnabled 0x10e7f49c0 基础模式是否禁止激励广告
 *   ad_reward_position_exp        0x10e7f0860  激励广告入口展示
 *
 * 设计原则：
 *   1. 只改设置字典里的广告配置键，不动发奖、时长、风控字段
 *   2. 不注入缺失键（避免模型解析异常）；需要时把 INJECT_MISSING 改 true
 *   3. 兼容五种响应形态：
 *        { "commerce_ad_config": ... }                  扁平字典
 *        { "settings": { ... } } / { "data": { ... } }  嵌套字典
 *        { "data": "[{\"key\":...}]" }                   JSON 字符串
 *        [{ "key": "...", "value": ... }]               key/value 数组
 *        设置值本身是 JSON 字符串                         递归解析后处理
 *   4. 任何异常/非 JSON 一律原样放行
 *
 * 风险：
 *   - conf.qishui.com 若启用证书固定，MITM 会失败；此时只装主插件即可
 *   - 清空广告配置后，App 可能提示「广告能力暂不可用」，这是预期
 *   - AGGRESSIVE=true 会关全局广告开关；若免费畅听依赖广告，可能影响播放，
 *     默认关闭，确认后再开
 */

/* ------------------------------------------------------------------ */
/* 开关                                                               */
/* ------------------------------------------------------------------ */
const ENABLED = true;          // false = 完全放行（只用于快速回滚）
const DRY_RUN = false;         // true = 只打日志，不改响应
const AGGRESSIVE = false;      // true = 关全局广告开关 + 隐藏播放器激励入口
const INJECT_MISSING = false;  // true = 响应里没有广告配置键时补一个空配置

/* ------------------------------------------------------------------ */
/* 键表（归一化：小写、去掉 _ 和 -）                                   */
/* ------------------------------------------------------------------ */
/*
 * 设置层广告配置键。
 * 前 6 个来自 STABSettingsService 注册表；后面几个来自字段描述符 /
 * ADRP+ADD 代码引用，都是广告专用键，命中才清：
 *   splash_ad_config          0x10e7c6280
 *   reward_ad_config          0x10e7c62a0
 *   feed_ad_config            0x10e78a282
 *   ad_reward_config          0x10e7a6388
 *   incentive_advert_config   0x10ec8d5b0
 *   feed_reward_ad_entrance   0x10e7ced30
 *   commerce_libra_ad_config  0x10e7c6200
 *   commerce_common_ad_config 0x10e7c6220
 *   adn_group_config          0x10e7c65c0
 *   splash_dsp_config         0x10e7c6570
 *   preload_dsp_config        0x10e7c6600
 *   splash_mannor_config      0x10e7c6550
 *   ad_ignore_player_status_config 0x10e7c6f00
 * ads_config_expire_time_ms 0x10e7c62c0 是过期时间，不在这里清，避免
 * 把缓存周期改成 0 反而引发更多请求。
 */
const CONFIG_KEYS = new Set([
  "commerceadconfig",
  "commerceadfeedconfig",
  "rewardadfallbackconfig",
  "feedrewardadconfig",
  "splashadearlyloadconfig",
  "adwebviewsdkconfig",
  "splashadconfig",
  "rewardadconfig",
  "feedadconfig",
  "adrewardconfig",
  "incentiveadvertconfig",
  "feedrewardadentrance",
  "commercelibraadconfig",
  "commercecommonadconfig",
  "adngroupconfig",
  "splashdspconfig",
  "preloaddspconfig",
  "splashmannorconfig",
  "adignoreplayerstatusconfig",
  /* 开屏摇一摇/扭一扭/传感器广告与本地素材缓存配置（全方位去广告） */
  "splashshakeadconfig",
  "shakeadconfig",
  "splashtwistadconfig",
  "twistadconfig",
  "motionadconfig",
  "splashadcacheconfig",
  "splashadpreloadconfig",
  /* 拓展多种形态广告配置（插屏/搜索/H5/弹窗/横幅） */
  "h5adconfig",
  "webadconfig",
  "popupadconfig",
  "banneradconfig",
  "interstitialadconfig",
  "searchadconfig"
]);

/* 默认只关“广告功能开关”，不动全局广告 SDK 与时长/发奖 */
const SCALAR_KEYS = new Map([
  ["enablerewardad", "false"],
  ["enablerewardads", "false"],
  ["enableincentivead", "false"],
  ["enablesplashad", "false"],
  ["enablefeedad", "false"],
  ["enablefeedads", "false"],
  ["splashadswitch", "false"],
  ["rewardadswitch", "false"],
  ["feedadswitch", "false"],
  ["feedrewardadswitch", "false"],
  ["incentiveadswitch", "false"],
  ["enableclientadsstrategy", "false"],
  ["preloadfeedads", "false"],
  ["basicmodedisablerewardadenabled", "true"],
  ["kbasicmodedisablerewardadenabled", "true"],
  /* 摇一摇与手势误触开关拦截 */
  ["enablesplashshake", "false"],
  ["enableshakead", "false"],
  ["enableshake", "false"],
  ["enabletwistad", "false"],
  ["enabletwist", "false"],
  ["enablemotionad", "false"],
  ["shakeadswitch", "false"],
  ["twistadswitch", "false"],
  ["splashshakesensitivity", "zero"],
  ["shakesensitivity", "zero"],
  ["splashaccelerationthreshold", "zero"],
  ["splashrotationthreshold", "zero"],
  ["splashcacheenable", "false"],
  ["splashcacheenabled", "false"],
  ["enableadpreload", "false"],
  ["enablesplashadpreload", "false"],
  ["adpreloadenable", "false"],
  /* 插屏/搜索/弹窗/横幅/H5 广告全形态开关 */
  ["enableinterstitialad", "false"],
  ["interstitialadswitch", "false"],
  ["enablesearchad", "false"],
  ["searchadswitch", "false"],
  ["enablepopupad", "false"],
  ["popupadswitch", "false"],
  ["enablebannerad", "false"],
  ["banneradswitch", "false"],
  ["enableh5ad", "false"],
  ["h5adswitch", "false"]
]);

/*
 * 【听抖音】入口开关（hideDouyinEntry）
 * 取证：conf.qishui.com/service/settings/v3/ 真实响应
 *   anchor_luna_to_douyin     = 1   汽水 → 抖音 的“听抖音”入口（锚点）
 *   anchor_luna_to_douyin_mv  = 1   同一入口的 MV 变体
 * 关掉这两个开关 = 汽水里不再出现【听抖音】入口（服务端配置驱动，不是客户端硬编码）
 */
const DOUYIN_ENTRY_KEYS = new Map([
  ["anchorlunatodouyin", "0"],
  ["anchorlunatodouyinmv", "0"]
]);

/* 运行期开关（由 main 设置，walk 读取） */
let hideDouyin = false;
let cleanAdsConfig = false;

/* 仅在 AGGRESSIVE=true 时处理（全局广告开关 / 播放器激励入口） */
const AGGRESSIVE_SCALARS = new Map([
  ["timorshouldenablead", "false"],
  ["adrewardpositionexp", "zero"],
  ["switchshowallad", "false"]
]);

/* ------------------------------------------------------------------ */
/* 工具                                                               */
/* ------------------------------------------------------------------ */
function normalizeKey(k) {
  return String(k).toLowerCase().replace(/[_-]/g, "");
}

function short(v) {
  try {
    const s = JSON.stringify(v);
    if (s === undefined) return "undefined";
    return s.length > 56 ? s.slice(0, 56) + "…" : s;
  } catch (e) {
    return "<unserializable>";
  }
}

function same(a, b) {
  return JSON.stringify(a) === JSON.stringify(b);
}

/*
 * 广告配置键 -> 空值。
 * 保留原值类型，避免 App 的模型解码失败：
 *   对象 -> {}，数组 -> []，JSON 字符串 -> "{}" / "[]"，
 *   布尔 -> false，数字 -> 0，普通字符串 -> ""。
 */
function emptyConfigValue(v) {
  if (Array.isArray(v)) return [];
  if (v && typeof v === "object") return {};

  if (typeof v === "string") {
    const t = v.trim();
    if (t.startsWith("{")) return "{}";
    if (t.startsWith("[")) return "[]";
    if (t === "true") return "false";
    if (t === "false") return "false";
    if (/^-?\d+$/.test(t)) return "0";
    return "";
  }

  if (typeof v === "boolean") return false;
  if (typeof v === "number") return 0;
  return null;
}

/*
 * 开关值 -> 目标值。
 * desired: "true" | "false" | "zero"
 */
function coerceScalar(v, desired) {
  if (typeof v === "boolean") return desired === "true";
  if (typeof v === "number") return desired === "true" ? 1 : 0;

  if (typeof v === "string") {
    const t = v.trim();
    if (/^(true|false)$/i.test(t)) return desired === "true" ? "true" : "false";
    if (/^-?\d+$/.test(t)) return desired === "true" ? "1" : "0";
    if (desired === "zero") return "";
    return desired === "true" ? "true" : "false";
  }

  if (v && typeof v === "object") {
    if (desired === "zero") return {};
    return desired === "true";
  }

  return desired === "true";
}

function looksLikeJsonContainer(s) {
  if (typeof s !== "string") return false;
  const t = s.trim();
  if (!t) return false;
  if (t[0] === "{" && t[t.length - 1] === "}") return true;
  if (t[0] === "[" && t[t.length - 1] === "]") return true;
  return false;
}

/* 兼容 { key: "...", value: ... } 这种数组项 */
function findField(obj, names) {
  for (const k of Object.keys(obj)) {
    if (names.indexOf(normalizeKey(k)) !== -1) return k;
  }
  return null;
}

/*
 * 找设置容器：{settings:{...}} / {data:{settings:{...}}} / {data:{...}} / 根。
 * 仅用于 INJECT_MISSING，不影响正常改写。
 */
function pickSettingsContainer(root) {
  if (!root || typeof root !== "object" || Array.isArray(root)) return root;

  for (const k of Object.keys(root)) {
    const nk = normalizeKey(k);
    if (nk !== "settings" && nk !== "data" && nk !== "result") continue;

    const v = root[k];
    if (!v || typeof v !== "object" || Array.isArray(v)) continue;

    for (const kk of Object.keys(v)) {
      if (normalizeKey(kk) === "settings" &&
          v[kk] && typeof v[kk] === "object" && !Array.isArray(v[kk])) {
        return v[kk];
      }
    }
    return v;
  }

  return root;
}

/* ------------------------------------------------------------------ */
/* 遍历改写                                                           */
/* ------------------------------------------------------------------ */
function walk(node, path, changes, depth) {
  if (depth > 12) return;

  if (Array.isArray(node)) {
    for (let i = 0; i < node.length; i++) {
      walk(node[i], path + "[" + i + "]", changes, depth + 1);
    }
    return;
  }

  if (!node || typeof node !== "object") return;

  /* 形态 4：[{ key: "commerce_ad_config", value: ... }] */
  const keyField = findField(node, ["key", "settingkey", "name"]);
  const valField = findField(node, ["value", "settingvalue", "val"]);
  if (keyField && valField) {
    const nk = normalizeKey(node[keyField]);
    const val = node[valField];

    if (cleanAdsConfig && CONFIG_KEYS.has(nk)) {
      const next = emptyConfigValue(val);
      if (!same(next, val)) {
        changes.push({ path: path + "." + valField, from: short(val), to: short(next) });
        node[valField] = next;
      }
      return;
    }

    if (cleanAdsConfig && (SCALAR_KEYS.has(nk) || (AGGRESSIVE && AGGRESSIVE_SCALARS.has(nk)))) {
      const desired = AGGRESSIVE_SCALARS.has(nk) ? AGGRESSIVE_SCALARS.get(nk) : SCALAR_KEYS.get(nk);
      const next = coerceScalar(val, desired);
      if (!same(next, val)) {
        changes.push({ path: path + "." + valField, from: short(val), to: short(next) });
        node[valField] = next;
      }
      return;
    }

    if (hideDouyin && DOUYIN_ENTRY_KEYS.has(nk)) {
      const next = coerceScalar(val, DOUYIN_ENTRY_KEYS.get(nk));
      if (!same(next, val)) {
        changes.push({ path: path + "." + valField, from: short(val), to: short(next) });
        node[valField] = next;
      }
      return;
    }
  }

  for (const k of Object.keys(node)) {
    const nk = normalizeKey(k);
    const val = node[k];

    /* 1. 广告配置容器 */
    if (cleanAdsConfig && CONFIG_KEYS.has(nk)) {
      const next = emptyConfigValue(val);
      if (!same(next, val)) {
        changes.push({ path: path + "." + k, from: short(val), to: short(next) });
        node[k] = next;
      }
      continue;
    }

    /* 2. 广告开关 */
    if (cleanAdsConfig && (SCALAR_KEYS.has(nk) || (AGGRESSIVE && AGGRESSIVE_SCALARS.has(nk)))) {
      const desired = AGGRESSIVE_SCALARS.has(nk) ? AGGRESSIVE_SCALARS.get(nk) : SCALAR_KEYS.get(nk);
      const next = coerceScalar(val, desired);
      if (!same(next, val)) {
        changes.push({ path: path + "." + k, from: short(val), to: short(next) });
        node[k] = next;
      }
      continue;
    }

    /* 2.1 【听抖音】入口开关 */
    if (hideDouyin && DOUYIN_ENTRY_KEYS.has(nk)) {
      const next = coerceScalar(val, DOUYIN_ENTRY_KEYS.get(nk));
      if (!same(next, val)) {
        changes.push({ path: path + "." + k, from: short(val), to: short(next) });
        node[k] = next;
      }
      continue;
    }

    /* 3. 嵌套 JSON 字符串：解析后继续找广告键 */
    if (looksLikeJsonContainer(val)) {
      let inner;
      try {
        inner = JSON.parse(val);
      } catch (e) {
        continue;
      }
      const before = JSON.stringify(inner);
      const sub = [];
      walk(inner, path + "." + k, sub, depth + 1);
      const after = JSON.stringify(inner);
      if (sub.length && after !== before) {
        node[k] = after;
        changes.push({
          path: path + "." + k,
          from: "JSON string(" + val.length + "B)",
          to: "JSON string(" + after.length + "B)"
        });
      }
      continue;
    }

    /* 4. 普通嵌套 */
    walk(val, path + "." + k, changes, depth + 1);
  }
}

/* ------------------------------------------------------------------ */
/* 主流程                                                             */
/* ------------------------------------------------------------------ */
/* ------------------------------------------------------------------ */
/* 通用工具：插件参数 / 响应体解码 / 诊断标记                          */
/* ------------------------------------------------------------------ */
/* Loon 插件参数：兼容对象 / 位置数组 / "k=v" 字符串三种形态 */
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

/*
 * 取响应体：兼容三种情况
 *   1. 普通 JSON 字符串
 *   2. Uint8Array（binary_body_mode=true）
 *   3. gzip 压缩体（实测抖音/汽水这些接口都是 content-encoding: gzip，
 *      Loon 有时把“未解压的压缩串”交给脚本，此时直接 JSON.parse 会失败）
 * Build ≥ 988 有 $utils.ungzip；没有就原样返回，交给上层判断。
 */
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

/*
 * 诊断标签：把“脚本解不了的压缩”带进标记。
 * 脚本层只有 $utils.ungzip（gzip），br / zstd / deflate 没有解码器；
 * 这些编码下的响应体会以乱码落进“非 JSON”分支，标记带上 ce= 才不会
 * 被误判成“接口本来就不是 JSON”。br 没有魔数，只能靠响应头识别。
 */
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
 * 诊断标记：写进响应头，下一次抓包一眼看出脚本跑到哪一步。
 *
 * bodyChanged=true 表示这次 $done 带回了新的 body，而它是**未压缩的
 * UTF-8 字符串**（readBody 已经 ungzip 过）。原响应头里的
 * content-encoding / content-length 就此过期：
 *   · 留着 content-encoding:gzip → 客户端拿明文按 gzip 解，JSON 解析失败；
 *   · 留着 content-length:191234 → 长度对不上，连接挂住或截断。
 * 删掉这两个头交给 Loon 按实际 body 重算，在「Loon 自己重压」和
 * 「Loon 原样转发」两种实现下都成立。
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

(function main() {
  try {
    if (!ENABLED) {
      console.log("[soda-settings] disabled, passthrough");
      return $done({});
    }

    /*
     * 统一插件开关（两个独立开关，可单独开）：
     *   settingsClean  清空广告配置键（会关掉激励广告入口 → 保奖励模式下不做）
     *   hideDouyinEntry 关掉【听抖音】入口（anchor_luna_to_douyin*，不动广告配置）
     * 保奖励模式只挡“清广告配置”这一步；隐藏【听抖音】不影响发奖链路，可以照常做。
     */
    const pluginArgs = pargs(["settingsClean", "hideDouyinEntry", "rewardSafe"]);
    const wantClean = pflag(pluginArgs, "settingsClean", false);
    const wantDouyin = pflag(pluginArgs, "hideDouyinEntry", false);
    const rewardSafe = pflag(pluginArgs, "rewardSafe", true);
    if (!wantClean && !wantDouyin) {
      console.log("[soda-settings] no switch on, passthrough");
      return $done({ headers: markHeaders("soda-settings;skip=switch-off") });
    }
    if (wantClean && rewardSafe) {
      console.log("[soda-settings] rewardSafe=on, skip ad-config cleanup");
    }
    cleanAdsConfig = wantClean && !rewardSafe;
    hideDouyin = wantDouyin;

    const url = ($request && $request.url) || "";
    const raw = readBody($response);

    const isSettingsHost =
      url.indexOf("conf.qishui.com") !== -1 ||
      url.indexOf("://i.snssdk.com/") !== -1 ||
      url.indexOf("://is.snssdk.com/") !== -1;
    if (!isSettingsHost ||
        url.indexOf("/service/settings/v3") === -1) {
      return $done({});
    }
    if (typeof raw !== "string" || raw.length === 0) {
      return $done({ headers: markHeaders("soda-settings;skip=no-body") });
    }

    const head = raw.trimStart().slice(0, 1);
    if (head !== "{" && head !== "[" && head !== "\"") {
      console.log("[soda-settings] non-JSON body, passthrough (len=" + raw.length + ")");
      return $done({ headers: markHeaders("soda-settings;skip=not-json" + ceTag($response)) });
    }

    let obj;
    try {
      obj = JSON.parse(raw);
    } catch (e) {
      console.log("[soda-settings] JSON parse failed, passthrough");
      return $done({ headers: markHeaders("soda-settings;skip=json-parse" + ceTag($response)) });
    }

    /* 兼容整个响应是 JSON 字符串的情况 */
    let wrapped = false;
    if (typeof obj === "string" && looksLikeJsonContainer(obj)) {
      try {
        obj = JSON.parse(obj);
        wrapped = true;
      } catch (e) {
        return $done({});
      }
    }

    if (!obj || typeof obj !== "object") {
      return $done({});
    }

    const changes = [];
    walk(obj, "$", changes, 0);

    /* 可选：补齐缺失的广告配置键（默认关闭） */
    if (INJECT_MISSING) {
      const target = pickSettingsContainer(obj);
      const injectable = {
        commerceadconfig: "commerce_ad_config",
        commerceadfeedconfig: "commerce_ad_feed_config",
        rewardadfallbackconfig: "reward_ad_fallback_config",
        feedrewardadconfig: "feed_reward_ad_config",
        splashadearlyloadconfig: "splash_ad_early_load_config",
        adwebviewsdkconfig: "ad_webview_sdk_config"
      };

      if (target && typeof target === "object" && !Array.isArray(target)) {
        for (const key of Object.keys(injectable)) {
          const camel = injectable[key];
          const exists = Object.keys(target).some(function (k) {
            return normalizeKey(k) === key;
          });
          if (!exists) {
            target[camel] = "{}";
            changes.push({ path: "<settings>." + camel, from: "<missing>", to: "\"{}\"" });
          }
        }
      }
    }

    if (changes.length === 0) {
      console.log("[soda-settings] hit, no ad setting change");
      return $done({ headers: markHeaders("soda-settings;noop=no-change") });
    }

    const out = JSON.stringify(wrapped ? JSON.stringify(obj) : obj);
    const delta = raw.length - out.length;
    const sizeText = delta >= 0 ? delta + "B smaller" : (-delta) + "B larger";
    console.log(
      "[soda-settings] " + changes.length + " change(s) | " +
      (DRY_RUN ? "DRY_RUN" : sizeText) + "\n  " +
      changes.slice(0, 20).map(function (c) {
        return c.path + " : " + c.from + " -> " + c.to;
      }).join("\n  ")
    );

    if (DRY_RUN) return $done({});
    $done({ body: out, headers: markHeaders("soda-settings;changed=" + changes.length, true) });
  } catch (e) {
    console.log("[soda-settings] error, passthrough: " + e);
    $done({});
  }
})();
