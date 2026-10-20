/*
 * douyin · 广告配置 / 商业化弹窗 / 演出清理（Loon http-response 脚本）
 * ------------------------------------------------------------
 * 全部字段来自 HAR 实测（381_1792495728793.har、383_1792495850343.har）。
 *
 * 1. 激励广告配置
 *    beta-luna.douyin.com/luna/advert/incentive/config
 *      advert_sources[]      广告源（type 3 rit 73009 cid 10000 / type 5 rit 1000）
 *      feed_advert_config    信息流广告配置（advert_duration=30 / forbid_first_slide）
 *      vids[]                预拉取视频 id 列表
 *      preload               是否预拉取
 *    beta-luna.douyin.com/luna/advert/incentive/retrieve
 *      ad_infos_map          素材表（每条含 launch_duration=30 / video_list / component.countdown）
 *      ad_infos[]
 *    beta-luna.douyin.com/luna/ads/config、/luna/ads/dsp/retrieve
 *      广告容器（无样本，按常见键名保守清理）
 *
 * 2. 商业化弹窗 / 商城
 *    beta-luna.douyin.com/luna/commerce/v2/upsell
 *      upsell_map{}          93 个弹窗，键名即 unique_name
 *        browse_mall_popup_acc_amount  逛商城赚金币（= 福利页【商城】弹窗）
 *        *ads* / *_ad / ad_*            广告类弹窗（开屏/预览/冷启动/回放…）
 *      sort_control_unique_names[]、cold_launch_timing.upsell_item_unique_names[]
 *        同步清掉被删的 unique_name，否则排序/冷启动仍会引用空弹窗
 *      variables{}           入口资格变量，保持原样（不改发奖/资格判断）
 *
 * 3. 演出（汽水音乐节）
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

    if (/\/luna\/advert\/incentive\/config/.test(url)) {
      killContainers(obj, KILL_CONTAINERS["incentive-config"], log, "$", 0);
    } else if (/\/luna\/advert\/incentive\/retrieve/.test(url)) {
      killContainers(obj, KILL_CONTAINERS["incentive-retrieve"], log, "$", 0);
    } else if (/\/luna\/ads\/(?:config|dsp\/retrieve)/.test(url)) {
      killContainers(obj, KILL_CONTAINERS["ads-config"], log, "$", 0);
    } else if (/\/luna\/commerce\/v2\/upsell/.test(url)) {
      handleUpsell(obj, log);
    } else if (/\/luna\/growth\/music_festival\/performance_details/.test(url)) {
      handleMusicFestival(obj, log);
    } else {
      return $done({});
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
