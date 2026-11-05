/*
 * douyin · 广告配置 / 商业化弹窗 / 演出清理（Loon http-response 脚本）
 * ------------------------------------------------------------
 * 全部字段来自 HAR 实测（381_1792495728793.har、383_1792495850343.har）。
 *
 * 开关分工（务必分清，v0.2.0 起）：
 *   cleanFeedAds   信息流/广告位广告（ads/config、ads/retrieve、ads/dsp/retrieve）
 *                   —— 不影响激励奖励，可以随便开。
 *   killRewardAds  激励广告素材与预拉取（advert/incentive/config|retrieve）
 *                   —— 开这个等于“广告完全不发”，攒时长/看广告赚金币随之失效。
 *                   抓包实测：广告素材是 30 秒（launch_duration=30），
 *                   config 里 preload=true + vids[]（33 个预拉取 id）是“下一次广告秒开”的关键，
 *                   清掉它会让每次广告都变成“点了才现下载”，反而更慢。
 *   cleanUpsell    商业化弹窗 / 商城 / 演出
 *
 * 1. 激励广告配置（killRewardAds）
 *    beta-luna.douyin.com/luna/advert/incentive/config
 *      advert_sources[]      广告源（type 3 rit 73009 cid 10000 / type 5 rit 1000）
 *      feed_advert_config    信息流广告配置（advert_duration=30 / forbid_first_slide）
 *      vids[]                预拉取视频 id 列表
 *      preload               是否预拉取
 *    beta-luna.douyin.com/luna/advert/incentive/retrieve
 *      ad_infos_map          素材表（每条含 launch_duration=30 / video_list / component.countdown）
 *      ad_infos[]
 *    beta-luna.douyin.com/luna/ads/config、/luna/ads/retrieve、/luna/ads/dsp/retrieve
 *      广告容器（cleanFeedAds；config/dsp 在本次抓包里服务端本身就返回 {}，
 *      retrieve 与汽水共用同一套 ad_launch / ads_blocks / ads_info 字段）
 *
 * 2. 商业化弹窗 / 商城（cleanUpsell）
 *    beta-luna.douyin.com/luna/commerce/v2/upsell
 *      upsell_map{}          93 个弹窗，键名即 unique_name
 *        browse_mall_popup_acc_amount  逛商城赚金币（= 福利页【商城】弹窗）
 *        *ads* / *_ad / ad_*            广告类弹窗（开屏/预览/冷启动/回放…）
 *      sort_control_unique_names[]、cold_launch_timing.upsell_item_unique_names[]
 *        同步清掉被删的 unique_name，否则排序/冷启动仍会引用空弹窗
 *      freq_ctrl_cfg.freq_ctrl_map{}  只删与已删弹窗同名的频控项（共享键保留）
 *      variables{}           入口资格变量，保持原样（不改发奖/资格判断）
 *
 * 3. 演出（汽水音乐节）（cleanUpsell）
 *    beta-luna.douyin.com/luna/growth/music_festival/performance_details
 *      detail_list[]         演出列表（title=汽水音乐节 / performance_stop_name=常州站…）
 *
 * 边界：只删广告与推广入口，不动发奖字段（reward_details / play_entitlements）、
 * 任务进度（stats）与幂等键；不发任何请求、不伪造领奖。
 */

const AD_UPSELL_RE = /(^|_)ads?(_|$)/;
const MALL_UPSELLS = [
  "browse_mall_popup_acc_amount"
];

/* kill/falsy 里的键名都是“归一化后”的形式：小写且去掉 _ 与 - */
const KILL_CONTAINERS = {
  "incentive-config": {
    kill: ["advertsources", "feedadvertconfig", "vids"],
    falsy: ["preload"]
  },
  "incentive-retrieve": {
    kill: ["adinfosmap", "adinfos"],
    falsy: []
  },
  "ads-config": {
    kill: ["adconfig", "adinfos", "adinfo", "ads", "adlist", "adsinfo", "adsblocks",
           "addata", "adextra", "adunitconfigs", "adsources", "adlaunch", "adlaunchlist",
           "adlaunches", "advertsources", "banners", "sources",
           "splashconfig", "feedadsconfig", "rewardconfig",
           "shakeinfo", "twistinfo", "motioninfo", "interactioninfo", "splashcache",
           "splashdspconfig", "preloaddspconfig", "splashmannorconfig", "adignoreplayerstatusconfig",
           "adngroupconfig", "commercelibraadconfig", "commercecommonadconfig",
           "feedrewardadentrance", "searchbanner", "feedwidget",
           "audioad", "midrollad", "pausead", "recommendad", "sponsorcard",
           "commercialnotice", "interstitialad", "popupad", "bannerad"],
    falsy: ["preload", "enableads", "enablead"]
  }
};

function isPlainObject(v) {
  return !!v && typeof v === "object" && !Array.isArray(v);
}

function normalizeKey(k) {
  return String(k).toLowerCase().replace(/[_-]/g, "");
}

function emptyLike(v) {
  if (Array.isArray(v)) return [];
  if (isPlainObject(v)) return {};
  return null;
}

/* 递归清空广告容器（只处理 kill/falsy 名单里的键） */
function killContainers(node, spec, log, path, depth) {
  if (depth > 12 || !node || typeof node !== "object") return;
  if (Array.isArray(node)) {
    for (let i = 0; i < node.length; i++) {
      killContainers(node[i], spec, log, path + "[" + i + "]", depth + 1);
    }
    return;
  }
  for (const k of Object.keys(node)) {
    const nk = normalizeKey(k);
    const val = node[k];
    if (spec.kill.indexOf(nk) !== -1) {
      if (val === null || val === undefined) continue;
      const after = emptyLike(val);
      if (after === null) continue;
      node[k] = after;
      log.push(path + "." + k + " -> " + (Array.isArray(after) ? "[]" : "{}"));
      continue;
    }
    if (spec.falsy.indexOf(nk) !== -1) {
      node[k] = false;
      log.push(path + "." + k + " -> false");
      continue;
    }
    killContainers(val, spec, log, path + "." + k, depth + 1);
  }
}

function handleUpsell(obj, log) {
  const map = obj.upsell_map;
  if (!isPlainObject(map)) return false;

  const removed = [];
  for (const name of Object.keys(map)) {
    if (AD_UPSELL_RE.test(name) || MALL_UPSELLS.indexOf(name) !== -1) {
      delete map[name];
      removed.push(name);
    }
  }
  if (removed.length === 0) return false;

  log.push("upsell_map : removed " + removed.length + " popup(s) -> " +
    removed.slice(0, 8).join(", ") + (removed.length > 8 ? " ..." : ""));

  /*
   * 频控表里与已删弹窗同名的条目一并清掉（例如 preview_popup_ads /
   * background_voice_prompt_ad）。只删同名项：像 background_voice_prompt
   * 这种被普通弹窗共享的频控键，以及 widget_ad 等非 upsell 实体的键必须保留。
   */
  const removedSet = {};
  for (const n of removed) removedSet[n] = true;
  const freqCfg = obj.freq_ctrl_cfg;
  if (isPlainObject(freqCfg) && isPlainObject(freqCfg.freq_ctrl_map)) {
    const fmap = freqCfg.freq_ctrl_map;
    const dropped = [];
    for (const name of Object.keys(fmap)) {
      if (removedSet[name] !== true) continue;
      delete fmap[name];
      dropped.push(name);
    }
    if (dropped.length > 0) {
      log.push("freq_ctrl_cfg : removed " + dropped.length + " entry(ies) -> " +
        dropped.slice(0, 6).join(", ") + (dropped.length > 6 ? " ..." : ""));
    }
  }

  /*
   * 排序列表 / 冷启动列表里的引用也要同步清理。
   * 注意：真实数据里存在“只出现在列表、upsell_map 里没有实体”的广告弹窗
   * （例如 cold_launch_popup_ads_text），所以除了删除已删的实体，
   * 还要把列表里所有广告/商城命名的条目一并去掉，否则冷启动仍会弹广告。
   */
  const dropFromList = function (n) {
    if (removed.indexOf(n) !== -1) return true;
    if (AD_UPSELL_RE.test(n)) return true;
    if (MALL_UPSELLS.indexOf(n) !== -1) return true;
    return false;
  };
  if (Array.isArray(obj.sort_control_unique_names)) {
    obj.sort_control_unique_names = obj.sort_control_unique_names.filter(function (n) {
      return !dropFromList(n);
    });
  }
  const clt = obj.cold_launch_timing;
  if (isPlainObject(clt) && Array.isArray(clt.upsell_item_unique_names)) {
    const before = clt.upsell_item_unique_names.length;
    clt.upsell_item_unique_names = clt.upsell_item_unique_names.filter(function (n) {
      return !dropFromList(n);
    });
    if (clt.upsell_item_unique_names.length !== before) {
      log.push("cold_launch_timing : " + before + " -> " +
        clt.upsell_item_unique_names.length + " item(s)");
    }
  }
  return true;
}

/*
 * 活动入口清理（cleanActivity）
 * 取证：polaris.zijieapi.com/luckycat/activity/settings/get_dynamic_settings/
 *   data.activity_info.music_festival      = 汽水音乐节（= 福利页【演出】）
 *   data.activity_info.music_festival_v2   = 同上的 v2
 *   data.activity_info.douyin_select_*     = 抖音运营活动（选游戏/选作者/开学季/创作者抽奖）
 * 这些是“活动能不能展示”的开关（canshow），置 false 就能让入口不出现，
 * 不动其它活动（用户自己的签到/翻卡/红包雨等不在这个字典里）。
 */
const ACTIVITY_HIDE_RE = /^(?:music_festival(?:_v2)?|douyin_select_)/;

function handleActivity(obj, log) {
  const info = obj && obj.data ? obj.data.activity_info : null;
  if (!isPlainObject(info)) return false;
  const touched = [];
  for (const key of Object.keys(info)) {
    if (!ACTIVITY_HIDE_RE.test(key)) continue;
    const entry = info[key];
    if (!isPlainObject(entry)) continue;
    const common = isPlainObject(entry.activity_common) ? entry.activity_common : null;
    if (!common) continue;
    if (common.canshow === false) continue;
    common.canshow = false;
    if (common.forbid_reason === undefined) common.forbid_reason = 2;
    touched.push(key);
  }
  if (touched.length === 0) return false;
  log.push("activity_info : canshow=false x" + touched.length +
    " (" + touched.slice(0, 6).join(",") + ")");
  return true;
}

function handleMusicFestival(obj, log) {
  if (!Array.isArray(obj.detail_list)) return false;
  if (obj.detail_list.length === 0) return false;
  log.push("detail_list : " + obj.detail_list.length + " -> 0 (汽水音乐节/演出)");
  obj.detail_list = [];
  return true;
}

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
    console.log("[douyin-clean] ungzip failed: " + e);
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
    const url = ($request && $request.url) || "";
    const args = pargs(["cleanFeedAds", "killRewardAds", "cleanUpsell", "cleanActivity"]);

    /* 决定这次请求归哪个开关管：没开的开关一律放行 */
    let mode = null;
    if (/\/luna\/advert\/incentive\/(?:config|retrieve)/.test(url)) {
      if (pflag(args, "killRewardAds", false)) mode = "incentive";
    } else if (/\/luna\/ads\/(?:config|retrieve|dsp\/retrieve)/.test(url)) {
      if (pflag(args, "cleanFeedAds", false)) mode = "feed-ads";
    } else if (/\/luna\/commerce\/v2\/upsell/.test(url)) {
      if (pflag(args, "cleanUpsell", false)) mode = "upsell";
    } else if (/\/luna\/growth\/music_festival\/performance_details/.test(url)) {
      if (pflag(args, "cleanUpsell", false)) mode = "music-festival";
    } else if (/\/luckycat\/activity\/settings\//.test(url)) {
      if (pflag(args, "cleanActivity", false)) mode = "activity";
    } else {
      return $done({});
    }
    if (mode === null) {
      console.log("[douyin-clean] switch off, passthrough: " + url);
      return $done({ headers: markHeaders("douyin-clean;skip=switch-off") });
    }

    const raw = readBody($response);
    if (typeof raw !== "string" || raw.length === 0) {
      return $done({ headers: markHeaders("douyin-clean;skip=no-body") });
    }
    /* 广告位/信息流端点也可能返回大体积响应；没有广告标记就不解析。 */
    if (mode === "feed-ads" &&
        !/ad|splash|feed|reward|search|commercial|interstitial|popup|banner|shake|twist|motion|interaction|audio|midroll|pause|recommend|sponsor|enable/i.test(raw)) {
      return $done({ headers: markHeaders("douyin-clean;noop=no-marker") });
    }
    const head = raw.trimStart().slice(0, 1);
    if (head !== "{" && head !== "[") {
      return $done({ headers: markHeaders("douyin-clean;skip=not-json" + ceTag($response)) });
    }

    let obj;
    try {
      obj = JSON.parse(raw);
    } catch (e) {
      console.log("[douyin-clean] JSON parse failed, passthrough: " + url);
      return $done({ headers: markHeaders("douyin-clean;skip=json-parse" + ceTag($response)) });
    }

    const log = [];

    if (mode === "incentive") {
      if (/\/luna\/advert\/incentive\/config/.test(url)) {
        killContainers(obj, KILL_CONTAINERS["incentive-config"], log, "$", 0);
      } else {
        killContainers(obj, KILL_CONTAINERS["incentive-retrieve"], log, "$", 0);
      }
    } else if (mode === "feed-ads") {
      killContainers(obj, KILL_CONTAINERS["ads-config"], log, "$", 0);
    } else if (mode === "upsell") {
      handleUpsell(obj, log);
    } else if (mode === "music-festival") {
      handleMusicFestival(obj, log);
    } else if (mode === "activity") {
      handleActivity(obj, log);
    }

    if (log.length === 0) {
      console.log("[douyin-clean] no change: " + url);
      return $done({ headers: markHeaders("douyin-clean;noop=no-change") });
    }

    console.log("[douyin-clean] " + log.length + " change(s)\n  " + log.join("\n  "));
    $done({ body: JSON.stringify(obj), headers: markHeaders("douyin-clean;changed=" + log.length, true) });
  } catch (e) {
    console.log("[douyin-clean] error, passthrough: " + e);
    $done({});
  }
})();
