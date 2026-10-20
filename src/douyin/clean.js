/*
 * douyin · 广告配置 / 商业化弹窗 / 演出清理（Loon http-response 脚本）
 * ------------------------------------------------------------
 * 全部字段来自 HAR 实测（381_1792495728793.har、383_1792495850343.har）。
 *
 * 开关分工（务必分清，v0.2.0 起）：
 *   cleanFeedAds   信息流/广告位广告（ads/config、ads/dsp/retrieve）
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
 *    beta-luna.douyin.com/luna/ads/config、/luna/ads/dsp/retrieve
 *      广告容器（cleanFeedAds；本次抓包里服务端本身就返回 {}）
 *
 * 2. 商业化弹窗 / 商城（cleanUpsell）
 *    beta-luna.douyin.com/luna/commerce/v2/upsell
 *      upsell_map{}          93 个弹窗，键名即 unique_name
 *        browse_mall_popup_acc_amount  逛商城赚金币（= 福利页【商城】弹窗）
 *        *ads* / *_ad / ad_*            广告类弹窗（开屏/预览/冷启动/回放…）
 *      sort_control_unique_names[]、cold_launch_timing.upsell_item_unique_names[]
 *        同步清掉被删的 unique_name，否则排序/冷启动仍会引用空弹窗
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
    kill: ["adconfig", "adinfos", "adinfo", "ads", "adsinfo", "adsblocks",
           "addata", "adextra", "adunitconfigs", "adsources"],
    falsy: []
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

  /* 排序列表 / 冷启动列表里的引用也要同步清理 */
  if (Array.isArray(obj.sort_control_unique_names)) {
    obj.sort_control_unique_names = obj.sort_control_unique_names.filter(function (n) {
      return removed.indexOf(n) === -1;
    });
  }
  const clt = obj.cold_launch_timing;
  if (isPlainObject(clt) && Array.isArray(clt.upsell_item_unique_names)) {
    clt.upsell_item_unique_names = clt.upsell_item_unique_names.filter(function (n) {
      return removed.indexOf(n) === -1;
    });
  }
  return true;
}

function handleMusicFestival(obj, log) {
  if (!Array.isArray(obj.detail_list)) return false;
  if (obj.detail_list.length === 0) return false;
  log.push("detail_list : " + obj.detail_list.length + " -> 0 (汽水音乐节/演出)");
  obj.detail_list = [];
  return true;
}

(function main() {
  try {
    const url = ($request && $request.url) || "";
    const args = pargs(["cleanFeedAds", "killRewardAds", "cleanUpsell"]);

    /* 决定这次请求归哪个开关管：没开的开关一律放行 */
    let mode = null;
    if (/\/luna\/advert\/incentive\/(?:config|retrieve)/.test(url)) {
      if (pflag(args, "killRewardAds", false)) mode = "incentive";
    } else if (/\/luna\/ads\/(?:config|dsp\/retrieve)/.test(url)) {
      if (pflag(args, "cleanFeedAds", false)) mode = "feed-ads";
    } else if (/\/luna\/commerce\/v2\/upsell/.test(url)) {
      if (pflag(args, "cleanUpsell", false)) mode = "upsell";
    } else if (/\/luna\/growth\/music_festival\/performance_details/.test(url)) {
      if (pflag(args, "cleanUpsell", false)) mode = "music-festival";
    } else {
      return $done({});
    }
    if (mode === null) {
      console.log("[douyin-clean] switch off, passthrough: " + url);
      return $done({});
    }

    const raw = ($response && $response.body) || "";
    if (typeof raw !== "string" || raw.length === 0) return $done({});
    const head = raw.trimStart().slice(0, 1);
    if (head !== "{" && head !== "[") return $done({});

    let obj;
    try {
      obj = JSON.parse(raw);
    } catch (e) {
      console.log("[douyin-clean] JSON parse failed, passthrough: " + url);
      return $done({});
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
    }

    if (log.length === 0) {
      console.log("[douyin-clean] no change: " + url);
      return $done({});
    }

    console.log("[douyin-clean] " + log.length + " change(s)\n  " + log.join("\n  "));
    $done({ body: JSON.stringify(obj) });
  } catch (e) {
    console.log("[douyin-clean] error, passthrough: " + e);
    $done({});
  }
})();
