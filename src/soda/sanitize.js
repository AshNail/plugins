/*
 * SodaClean · 精准裁剪（Loon http-response 脚本）
 * ------------------------------------------------------------
 * 设计原则：
 *   1. 保留服务端原始包络（status_code / status_info / expire_time ...）
 *   2. 只清空"广告/弹窗容器"字段，不破坏解码
 *   3. 同时兼容 snake_case 与 camelCase（按归一化键名匹配）
 *   4. 失败即放行：任何异常都不改响应
 *   5. 可 DRY_RUN：只打日志，不改写
 *
 * 取证依据（20.5.0 二进制）：
 *   GetIncentiveAdvertConfigResponse: statusCode/statusInfo/advertSources/feedAdvertConfig/expireTime/preload
 *   IncentiveRetrieveResponse:        statusCode/statusInfo/adInfosMap/expireTime  (+ ad_infos)
 *   IncentiveDoneResponseInfo:        statusCode/statusInfo/rewardDetails/rewardTips   ← 不碰
 *   线上 JSON 键名（二进制中的唯一 snake_case 串）：
 *     advert_sources / feed_advert_config / ad_infos_map / ad_infos / reward_details / reward_tips
 *   缓存键：incentive_advert_config_key、incentive_adinfo_cache_key
 *   过期控制：IncentiveServiceManager.incentiveExpireTimer / incentiveCacheExpires
 */

/* ------------------------------------------------------------------ */
/* 开关                                                               */
/* ------------------------------------------------------------------ */
const VERBOSE = true;          // 打印每条改写记录
const DRY_RUN = false;         // true = 只记录不修改（首次上线建议先开）

const FORCE_OK = true;         // 激励类端点：status_code → 0，避免错误提示/重试
const EXTEND_EXPIRY = true;    // 把 expire_time 至少延长到 N 天后（自适应秒/毫秒）
const EXTEND_DAYS = 7;         // 延长天数；调小可缩短"关插件后仍无广告"的尾巴

/* ------------------------------------------------------------------ */
/* 规则表：按 URL 片段匹配，只处理该端点的响应                          */
/* ------------------------------------------------------------------ */
const RULES = [
  {
    id: "incentive-config",
    match: /\/luna\/advert\/incentive\/config/,
    kill: ["advertSources", "feedAdvertConfig"],
    falsy: ["preload"],
    forceOk: true,
    extendExpiry: true
  },
  {
    id: "incentive-retrieve",
    match: /\/luna\/advert\/incentive\/retrieve/,
    kill: ["adInfosMap", "adInfos"],
    forceOk: true,
    extendExpiry: true
  },
  {
    id: "splash-brand",
    match: /\/luna\/advert\/splash\/brand\/retrieve/,
    /*
     * 取证：SplashAdSourceBrand.lastSelectedAdLaunch /
     * lastSelectedUnifiedAdLaunch；响应字段 ad_launch_list
     *（字段描述符 0x1147cbcd8）。
     */
    kill: ["adLaunchList", "adLaunch", "adLaunches", "adInfo", "adInfos",
           "splash", "brand", "ads", "splashActiveData", "jumpBtnInfo"],
    killArrayData: true,
    forceOk: true
  },
  {
    id: "ads-config",
    match: /\/luna\/ads\/config/,
    /*
     * 取证：响应字段 expires_at + ad_unit_configs / splash_config /
     * feed_ads_config / reward_config（字段描述符 0x1147cfb80）。
     */
    kill: ["adUnitConfigs", "splashConfig", "feedAdsConfig", "rewardConfig",
           "searchBanner", "feedWidget",
           "commerceLibraAdConfig", "commerceCommonAdConfig",
           "adnGroupConfig", "splashDspConfig", "preloadDspConfig",
           "splashMannorConfig", "adIgnorePlayerStatusConfig"],
    falsy: ["preload", "enableAds", "enableAd"],
    extendExpiry: true
  },
  {
    id: "ads",
    match: /\/luna\/(?:ads\/(?:config|retrieve|dsp\/retrieve)|advert\/fallback\/done\/info)/,
    /*
     * 取证：luna/ads/retrieve 的广告对象用 ad_launch / ad_launch_list；
     * 信息流广告块用 ads_blocks / ads_info（0x1147cde48、0x1147ce218）。
     */
    kill: ["adLaunchList", "adLaunch", "adLaunches", "adInfo", "adInfos",
           "ads", "adList", "advertSources", "banners", "sources",
           "adsBlocks", "adsInfo", "adUnitConfigs", "splashConfig",
           "feedAdsConfig", "rewardConfig",
           "commerceLibraAdConfig", "commerceCommonAdConfig",
           "adnGroupConfig", "splashDspConfig", "preloadDspConfig",
           "splashMannorConfig", "adIgnorePlayerStatusConfig"],
    killArrayData: true,
    forceOk: true
  },
  {
    id: "upsell",
    match: /\/luna\/commerce\/(?:upsells|v2\/upsell(?:_sort_decision)?)/,
    /*
     * 取证：upsell 响应字段 card / countdown / upsell_unique_name
     *（字段描述符 0x1147cb278）。
     */
    kill: ["upsells", "upsellList", "upsellUniqueName", "card",
           "items", "popups", "list"],
    falsy: ["show", "isShow", "visible", "enable", "enabled"],
    killArrayData: true
  },
  {
    id: "feed-ads",
    match: /\/luna\/(?:(?:v2\/)?feed\/|playlist\/(?:feed\/|detail|related_media|search)|search\/track|search-block|search-categories|media\/(?:assistant\/)?related|video_playlist\/detail|me\/discover|discover\/mix|featured-content\/list|card)/,
    /*
     * 信息流广告：ads_blocks / ads_info / is_ad=true。
     * fastReject 先做字符串预检，避免对体积大的 feed 响应做无谓 JSON.parse。
     */
    kill: ["adsBlocks", "adsInfo", "adInfo", "adData", "adExtra",
           "videoEndAd", "feedAds", "feedRewardAdEntrance"],
    prune: [
      { key: "bannerList", match: /ad[_-]?reward|reward[_-]?ad|ads_banner|ad_snap|incentive[_-]?ad|看视频|看广告/i }
    ],
    dropAdItems: true,
    fastReject: /ads_blocks|ads_info|ad_info|ad_data|ad_extra|video_end_ad|feed_ads|feed_reward_ad_entrance|banner_list|"bannerList"\s*:|"is_ad"\s*:|"isAd"\s*:|"is_advert"\s*:|"isAdvert"\s*:|"is_advertisement"\s*:|"isAdvertisement"\s*:|"is_ad_item"\s*:|"isAdItem"\s*:|"ad_item"\s*:|"adItem"\s*:|"ad_flag"\s*:|"adFlag"\s*:/
  },
  {
    id: "treasure-entrance",
    match: /\/luna\/(?:treasure\/entrance\/config|growth\/activity_entrance)/,
    /*
     * 只摘掉"看视频/激励"标签与广告 banner，保留签到、听歌、金币、
     * VIP/宝藏等正常入口。
     * 取证：0x10ec5b362 起 reward_ad / reward_ad_banner / ads_banner /
     * ad_snap；0x10ec5cb60 起 popup_show_ad / action_popup_show_ad。
     */
    kill: ["rewardAdBanner", "rewardAdBannerExtra", "adsBanner", "adSnap",
           "rewardAd", "popupShowAd", "actionPopupShowAd", "popupGainAdEnt"],
    prune: [
      { key: "labels", match: /ad[_-]?reward|incentive[_-]?ad|reward[_-]?ads?|watch[_-]?video|看视频|看广告/i },
      /* 金币挂件的广告态：widgetAdReward / reward_ads_cold_start */
      { key: "coinWidgetStateList", match: /widgetad|ad[_-]?reward|reward[_-]?ad|incentive[_-]?ad|watch[_-]?(?:video|ad)|看视频|看广告/i },
      /* 福利页 banner 列表：只摘广告 banner，VIP/宝藏 banner 保留 */
      { key: "bannerList", match: /ad[_-]?reward|reward[_-]?ad|ads_banner|ad_snap|incentive[_-]?ad|看视频|看广告/i }
    ]
  },
  {
    id: "treasure-task-view",
    match: /\/luna\/treasure\/task\/view/,
    /*
     * 只摘掉 reward_ads（看广告得金币/畅听）任务，
     * 保留 sign_in、listen_duration、share、browse_mall、flip_card、guide。
     * task/view 也可能带 banner/popup 配置，一并清理广告项。
     */
    kill: ["rewardAdBanner", "rewardAdBannerExtra", "adsBanner", "adSnap",
           "rewardAd", "popupShowAd", "actionPopupShowAd", "popupGainAdEnt",
           "commerceAdTask"],
    prune: [
      { key: "taskInfos", match: /ad[_-]?reward|reward[_-]?ads?|incentive|watch[_-]?(?:video|ad)|commerce[_-]?ad|ad[_-]?(?:snap|task)|看视频|看广告|广告/i },
      { key: "tasks", match: /ad[_-]?reward|reward[_-]?ads?|incentive|watch[_-]?(?:video|ad)|commerce[_-]?ad|ad[_-]?(?:snap|task)|看视频|看广告|广告/i },
      { key: "taskList", match: /ad[_-]?reward|reward[_-]?ads?|incentive|watch[_-]?(?:video|ad)|commerce[_-]?ad|ad[_-]?(?:snap|task)|看视频|看广告|广告/i },
      { key: "list", match: /ad[_-]?reward|reward[_-]?ads?|incentive|watch[_-]?(?:video|ad)|commerce[_-]?ad|ad[_-]?(?:snap|task)|看视频|看广告|广告/i },
      { key: "data", match: /ad[_-]?reward|reward[_-]?ads?|incentive|watch[_-]?(?:video|ad)|commerce[_-]?ad|ad[_-]?(?:snap|task)|看视频|看广告|广告/i },
      { key: "bannerList", match: /ad[_-]?reward|reward[_-]?ad|ads_banner|ad_snap|incentive[_-]?ad|看视频|看广告/i }
    ]
  }
];

/* ------------------------------------------------------------------ */
/* 工具                                                               */
/* ------------------------------------------------------------------ */
function normalizeKey(k) {
  return String(k).toLowerCase().replace(/[_-]/g, "");
}

function emptyLike(v) {
  if (Array.isArray(v)) return [];
  if (v && typeof v === "object") return {};
  return null;
}

function isAlreadyEmpty(v) {
  if (Array.isArray(v)) return v.length === 0;
  if (v && typeof v === "object") return Object.keys(v).length === 0;
  return v === null || v === undefined;
}

function short(v) {
  try {
    const s = JSON.stringify(v);
    return s === undefined ? "undefined" : s.length > 48 ? s.slice(0, 48) + "…" : s;
  } catch (e) {
    return "<unserializable>";
  }
}

function safeString(v) {
  try {
    return JSON.stringify(v) || "";
  } catch (e) {
    return "";
  }
}

/*
 * 【听抖音】条目过滤（可选开关 hideDouyinTab）
 * ------------------------------------------------------------
 * 福利页的“听抖音”是一个 tab/任务条目，默认保留（属于正常福利任务）。
 * 打开开关后，只删除“数组里带‘抖音’字样的条目”，
 * 不动签到 / 听歌 / 分享 / 金币 / 逛商城 / 翻牌 / 引导等其它任务。
 * 说明：具体字段（tab 列表 / task_infos / entrance 列表）要等真实 HAR
 * 确认后收紧范围；这里先按“内容含抖音的数组元素”处理，最坏情况是
 * 多删一两个跨端推广条目，不会动到发奖字段。
 */
const DOUYIN_KEYWORD = "抖音";

function dropDouyinItems(node, log, path, depth) {
  if (depth > 14 || node === null || node === undefined) return;

  if (Array.isArray(node)) {
    const kept = [];
    let dropped = 0;
    for (const item of node) {
      if (safeString(item).indexOf(DOUYIN_KEYWORD) !== -1) {
        dropped++;
        continue;
      }
      kept.push(item);
    }
    if (dropped > 0) {
      node.length = 0;
      for (const item of kept) node.push(item);
      log.push(path + " : dropped " + dropped + " 抖音 item(s)");
    }
    for (let i = 0; i < node.length; i++) {
      dropDouyinItems(node[i], log, path + "[" + i + "]", depth + 1);
    }
    return;
  }

  if (typeof node !== "object") return;
  for (const k of Object.keys(node)) {
    dropDouyinItems(node[k], log, path + "." + k, depth + 1);
  }
}

/*
 * 保奖励模式下的“只删听抖音”通道：
 * 不做任何广告裁剪，只移除带“抖音”的数组条目。
 */
function douyinOnly(raw, url) {
  if (typeof raw !== "string" || raw.length === 0) return $done({});
  const head = raw.trimStart().slice(0, 1);
  if (head !== "{" && head !== "[") return $done({});

  let obj;
  try {
    obj = JSON.parse(raw);
  } catch (e) {
    console.log("[soda] JSON parse failed (douyin-only), passthrough: " + url);
    return $done({});
  }

  const log = [];
  dropDouyinItems(obj, log, "$", 0);
  if (log.length === 0) {
    console.log("[soda] hideDouyinTab=on, no 抖音 item found: " + url);
    return $done({});
  }

  console.log(
    "[soda] hideDouyinTab=on | " + log.length + " change(s)\n  " + log.join("\n  ")
  );
  $done({ body: JSON.stringify(obj) });
}

/*
 * 纯广告条目判定：
 *   1. 显式 is_ad / is_advert / is_advertisement / is_ad_item / ad_flag = true
 *   2. 只有 ad_info / ads_info / ad_data / ads_blocks，且没有任何媒体载荷
 *   3. card / ad_info 等嵌套对象里带 is_ad=true，且外层没有媒体载荷
 * 保守策略：正常内容即使带 ad_info，只要还有媒体字段就不删。
 */
function isAdFlag(v) {
  return v === true || v === 1 || v === "1" || v === "true";
}

function hasNestedAdFlag(o) {
  for (const k of Object.keys(o)) {
    const nk = normalizeKey(k);
    if (nk !== "card" && nk !== "adinfo" && nk !== "adsinfo" &&
        nk !== "addata" && nk !== "adsdata" &&
        nk !== "adblock" && nk !== "adsblock") {
      continue;
    }
    const v = o[k];
    if (!v || typeof v !== "object" || Array.isArray(v)) continue;
    for (const kk of Object.keys(v)) {
      const nn = normalizeKey(kk);
      if ((nn === "isad" || nn === "isadvert" || nn === "isadvertisement" ||
           nn === "isaditem" || nn === "aditem" || nn === "adflag") &&
          isAdFlag(v[kk])) {
        return true;
      }
    }
  }
  return false;
}

function isAdItem(o) {
  let hasAd = false;
  let hasMedia = false;

  for (const k of Object.keys(o)) {
    const nk = normalizeKey(k);
    const v = o[k];

    if ((nk === "isad" || nk === "isadvert" || nk === "isadvertisement" ||
         nk === "isaditem" || nk === "aditem" || nk === "adflag") &&
        isAdFlag(v)) {
      return true;
    }
    if (nk === "adinfo" || nk === "addata") {
      hasAd = true;
    }
    if (nk === "video" || nk === "liveroom" || nk === "media" ||
        nk === "track" || nk === "song" || nk === "aweme" ||
        nk === "roomdata") {
      hasMedia = true;
    }
  }

  if (!hasAd && hasNestedAdFlag(o)) hasAd = true;
  return hasAd && !hasMedia;
}

function dropAdItems(node, log, path, depth) {
  if (depth > 14) return;

  if (Array.isArray(node)) {
    const kept = [];
    for (let i = 0; i < node.length; i++) {
      const item = node[i];
      if (item && typeof item === "object" && !Array.isArray(item) && isAdItem(item)) {
        log.push(path + "[" + i + "] : dropped ad item");
        continue;
      }
      kept.push(item);
      dropAdItems(item, log, path + "[" + i + "]", depth + 1);
    }
    if (kept.length !== node.length) {
      node.length = 0;
      for (let i = 0; i < kept.length; i++) node.push(kept[i]);
    }
    return;
  }

  if (!node || typeof node !== "object") return;
  for (const k of Object.keys(node)) {
    dropAdItems(node[k], log, path + "." + k, depth + 1);
  }
}

/*
 * 把 expire_time 延长到 now + N 天。
 * 自适应两种语义：
 *   - 绝对时间戳（秒 ~1e9 / 毫秒 ~1e12）
 *   - TTL（秒 ~1e3 / 毫秒 ~1e6）
 * 两种情况下都用同一公式落到"至少 N 天后"，不会缩短原值。
 */
function extendExpiryValue(v, nowMs) {
  if (typeof v !== "number" || !isFinite(v) || v <= 0) return null;

  const looksMs = v > 1e11;
  const now = looksMs ? nowMs : Math.floor(nowMs / 1000);
  const delta = looksMs ? EXTEND_DAYS * 86400 * 1000 : EXTEND_DAYS * 86400;
  const target = now + delta;

  if (v >= target) return null;
  return { value: target, unit: looksMs ? "ms" : "s" };
}

/* ------------------------------------------------------------------ */
/* 遍历改写                                                           */
/* ------------------------------------------------------------------ */
function rewrite(node, rule, path, log, depth) {
  if (depth > 14) return;

  if (Array.isArray(node)) {
    if (rule.killArrayData && depth === 0) {
      log.push("$ (root array) -> []");
      return;
    }
    for (let i = 0; i < node.length; i++) {
      rewrite(node[i], rule, path + "[" + i + "]", log, depth + 1);
    }
    return;
  }
  if (!node || typeof node !== "object") return;

  const killSet = rule._kill;
  const falsySet = rule._falsy;
  const pruneList = rule._prune || [];
  const nowMs = Date.now();

  for (const k of Object.keys(node)) {
    const nk = normalizeKey(k);
    const val = node[k];

    /* 0. 按条目过滤数组：只摘掉广告任务/广告标签 */
    if (pruneList.length && Array.isArray(val)) {
      let hit = false;
      for (const p of pruneList) {
        if (nk !== p.key) continue;
        hit = true;
        const kept = val.filter(function (item) {
          return !p.match.test(safeString(item));
        });
        if (kept.length !== val.length) {
          if (VERBOSE) {
            log.push(path + "." + k + " : dropped " +
              (val.length - kept.length) + "/" + val.length + " ad item(s)");
          }
          node[k] = kept;
        }
        break;
      }
      if (hit) continue;
    }

    /* 1. 清空广告容器 */
    if (killSet.has(nk)) {
      if (isAlreadyEmpty(val)) continue;
      const after = emptyLike(val);
      if (VERBOSE) log.push(path + "." + k + " : " + short(val) + " -> " + short(after));
      node[k] = after;
      continue;
    }

    /* 2. 关闭开关（布尔 true / 数字非 0） */
    if (falsySet.has(nk)) {
      if (val === true) {
        if (VERBOSE) log.push(path + "." + k + " : true -> false");
        node[k] = false;
        continue;
      }
      if (typeof val === "number" && val !== 0) {
        if (VERBOSE) log.push(path + "." + k + " : " + val + " -> 0");
        node[k] = 0;
        continue;
      }
    }

    /* 3. 归零错误码（仅激励类端点，仅顶层包络） */
    if (rule.forceOk && depth === 0) {
      if (nk === "statuscode" && typeof val === "number" && val !== 0) {
        if (VERBOSE) log.push(path + "." + k + " : " + val + " -> 0");
        node[k] = 0;
        continue;
      }
      if (nk === "statusinfo" && typeof val === "string" && val !== "") {
        if (VERBOSE) log.push(path + "." + k + " : " + short(val) + " -> \"\"");
        node[k] = "";
        continue;
      }
    }

    /* 4. 延长配置缓存（仅顶层，避免动到嵌套 adInfo 的过期时间） */
    if (rule.extendExpiry && depth === 0 &&
        (nk === "expiretime" || nk === "expiresat")) {
      const ext = extendExpiryValue(val, nowMs);
      if (ext) {
        if (VERBOSE) log.push(path + "." + k + " : " + val + " -> " + ext.value + " (" + ext.unit + ", +" + EXTEND_DAYS + "d)");
        node[k] = ext.value;
        continue;
      }
    }

    /* 5. data 是数组且规则允许：整体清空 */
    if (rule.killArrayData && nk === "data" && Array.isArray(val)) {
      if (VERBOSE) log.push(path + "." + k + " : " + short(val) + " -> []");
      node[k] = [];
      continue;
    }

    rewrite(val, rule, path + "." + k, log, depth + 1);
  }
}

/* ------------------------------------------------------------------ */
/* 主流程                                                             */
/* ------------------------------------------------------------------ */
(function main() {
  try {
    const url = ($request && $request.url) || "";
    const raw = ($response && $response.body) || "";

    /*
     * 统一插件开关：保奖励模式优先。
     * rewardSafe=true 时只允许开屏品牌广告继续处理，其他端点直接放行；
     * 唯一例外：hideDouyinTab=true 且是福利页端点时，只做“听抖音”过滤，
     * 不做任何广告裁剪，避免影响奖励任务。
     * 独立主插件没有 $argument，行为保持不变。
     */
    const pluginArgs =
      (typeof $argument === "object" && $argument) ? $argument : null;
    const rewardSafe = !!(pluginArgs && pluginArgs.rewardSafe === true);
    const hideDouyin = !!(pluginArgs && pluginArgs.hideDouyinTab === true);
    const isSplash = /\/luna\/advert\/splash\/brand\/retrieve/.test(url);
    const isTreasure = /\/luna\/(?:treasure|growth)\//.test(url);

    if (rewardSafe && !isSplash) {
      if (!(hideDouyin && isTreasure)) {
        console.log("[soda] rewardSafe=on, non-splash passthrough: " + url);
        return $done({});
      }
      /* 保奖励 + 隐藏听抖音：只删抖音条目，其余原样返回 */
      return douyinOnly(raw, url);
    }

    if (typeof raw !== "string" || raw.length === 0) {
      return $done({});
    }

    const head = raw.trimStart().slice(0, 1);
    if (head !== "{" && head !== "[") {
      // 非 JSON（protobuf / 压缩体 / 空体），不动
      return $done({});
    }

    const rule = RULES.find(function (r) { return r.match.test(url); });
    if (!rule) return $done({});

    /* 大响应预检：没有广告标记就直接放行，避免无谓 JSON.parse */
    if (rule.fastReject && !rule.fastReject.test(raw)) {
      console.log("[soda] " + rule.id + " hit, no ad marker");
      return $done({});
    }

    let obj;
    try {
      obj = JSON.parse(raw);
    } catch (e) {
      console.log("[soda] JSON parse failed, passthrough: " + url);
      return $done({});
    }

    rule._kill = new Set((rule.kill || []).map(normalizeKey));
    rule._falsy = new Set((rule.falsy || []).map(normalizeKey));
    rule._prune = (rule.prune || []).map(function (p) {
      return { key: normalizeKey(p.key), match: p.match };
    });

    const log = [];
    const before = JSON.stringify(obj);
    rewrite(obj, rule, "$", log, 0);
    if (rule.dropAdItems) dropAdItems(obj, log, "$", 0);
    if (hideDouyin && isTreasure) dropDouyinItems(obj, log, "$", 0);

    if (log.length === 0) {
      console.log("[soda] " + rule.id + " hit, already clean");
      return $done({});
    }

    const out = JSON.stringify(obj);
    console.log(
      "[soda] " + rule.id + " | " + log.length + " change(s) | " +
      (DRY_RUN ? "DRY_RUN" : (before.length - out.length) + "B smaller") + "\n  " +
      log.join("\n  ")
    );

    if (DRY_RUN) {
      return $done({});
    }

    $done({ body: out });
  } catch (e) {
    console.log("[soda] error, passthrough: " + e);
    $done({});
  }
})();
