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
    kill: ["advertSources", "feedAdvertConfig", "vids"],
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
           "splash", "brand", "ads", "splashActiveData", "jumpBtnInfo",
           "shakeInfo", "twistInfo", "motionInfo", "interactionInfo", "splashCache"],
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
           "splashMannorConfig", "adIgnorePlayerStatusConfig",
           "shakeInfo", "twistInfo", "motionInfo", "interactionInfo", "splashCache"],
    killArrayData: true,
    forceOk: true
  },
  {
    id: "upsell",
    match: /\/luna\/commerce\/(?:upsells|v2\/upsell(?:_sort_decision)?)/,
    /*
     * 取证：v1 响应字段 card / countdown / upsell_unique_name
     *（字段描述符 0x1147cb278）；v2 真响应改用 upsell_map{} 承载弹窗，
     * 由 cleanUpsellMap() 精确处理（见下方函数注释）。
     * extraReject 让只带 upsell_map 的响应也能进入 JSON 处理，
     * 否则大响应预检可能直接放行。
     */
    kill: ["upsells", "upsellList", "upsellUniqueName", "card",
           "items", "popups", "list"],
    falsy: ["show", "isShow", "visible", "enable", "enabled"],
    killArrayData: true,
    extraReject: /"upsell_map"\s*:/
  },
  {
    id: "feed-ads",
    match: /\/luna\/(?:(?:v2\/)?feed\/|playlist\/(?:feed\/|detail|related_media|search)|search\/track|search-block|search-categories|media\/(?:assistant\/)?related|video_playlist\/detail|me\/discover|discover\/mix|featured-content\/list|card)/,
    /*
     * 信息流广告：ads_blocks / ads_info / is_ad=true。
     * fastReject 先做字符串预检，避免对体积大的 feed 响应做无谓 JSON.parse。
     */
    kill: ["adsBlocks", "adsInfo", "adInfo", "adData", "adExtra",
           "videoEndAd", "feedAds", "feedRewardAdEntrance",
           "audioAd", "midRollAd", "midRollAds", "pauseAd",
           "recommendAd", "searchBanner", "sponsorCard", "commercialNotice",
           "promotedTrack", "promotedSong"],
    prune: [
      { key: "bannerList", match: /ad[_-]?reward|reward[_-]?ad|ads_banner|ad_snap|incentive[_-]?ad|看视频|看广告/i }
    ],
    dropAdItems: true
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
  },
  {
    id: "task-page",
    match: /\/luna\/treasure\/task\/page\/v[0-9]+/,
    /*
     * v2.6.1 · sections 形态（task/page/v2，HAR 393 真样本实证）：
     * data.sections[].task_group.tasks —— 结构化摘广告任务
     * （music_incentive_ad / polaris_incentive_ad_v3 家族 / 标题广告词），
     * 签到、翻卡、攒时长、逛街等正常任务保留（它们的 ad_token/ad_snap
     * 只是观测归因，不作为判别依据）。banner 广告位照旧清。
     * 页面级广告开关（migrate_first_ad / ad_api_preload）在
     * pruneTaskAdPreload() 里按“仍保留的任务”精确收紧。
     */
    kill: ["adsBanner", "rewardAdBanner", "rewardAdBannerExtra",
           "popupShowAd", "actionPopupShowAd"],
    falsy: ["migrateFirstAd"],
    prune: [
      { key: "tasks", match: /ad[_-]?reward|reward[_-]?ads?|incentive[_-]?ad|watch[_-]?(?:video|ad)|commerce[_-]?ad|ad[_-]?(?:snap|task)|看广告|看视频|广告/i },
      { key: "taskInfos", match: /ad[_-]?reward|reward[_-]?ads?|incentive[_-]?ad|watch[_-]?(?:video|ad)|commerce[_-]?ad|ad[_-]?(?:snap|task)|看广告|看视频|广告/i },
      { key: "bannerList", match: /ad[_-]?reward|reward[_-]?ad|ads_banner|ad_snap|incentive[_-]?ad|看视频|看广告/i }
    ],
    extraReject: /"sections"\s*:/
  }
];

/*
 * 大响应预检（fastReject）由规则本身生成，而不是手写：
 * 只要 JSON 里出现任一 kill/falsy/prune 键（同时兼容 camelCase 与
 * snake_case），就进入 JSON.parse 精细处理；没有就直接放行。
 * 手写正则很容易漏键（例如 upsell 的 upsells/show 被漏掉），
 * 这里从规则表派生，新增规则时自动同步。
 */
function escapeRe(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function markerForKeys(keys) {
  const parts = [];
  for (const key of keys) {
    const tokens = String(key)
      .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
      .toLowerCase()
      .split(/[^a-z0-9]+/)
      .filter(Boolean);
    if (tokens.length === 0) continue;
    parts.push('"' + tokens.map(escapeRe).join("[_-]?") + '"\\s*:');
  }
  return parts;
}

/* 信息流条目显式广告标记（dropAdItems 的价值级判据） */
const AD_ITEM_MARKER =
  '"(?:is[_-]?(?:ad|advert|advertisement|ad[_-]?item|promoted|sponsored|commercial)|ad[_-]?(?:flag|item))"\\s*:\\s*(?:true|1|"1"|"true")';

for (const rule of RULES) {
  const keys = (rule.kill || []).concat(rule.falsy || []);
  for (const p of rule.prune || []) keys.push(p.key);

  const parts = markerForKeys(keys);
  if (rule.dropAdItems) parts.push(AD_ITEM_MARKER);
  if (rule.extraReject) parts.push(rule.extraReject.source);
  if (rule.killArrayData) {
    parts.push('"data"\\s*:\\s*\\[');
    parts.push("^\\s*\\[");
  }
  rule.fastReject = new RegExp(parts.join("|"), "i");
}

/* ------------------------------------------------------------------ */
/* 工具                                                               */
/* ------------------------------------------------------------------ */
function normalizeKey(k) {
  return String(k).toLowerCase().replace(/[_-]/g, "");
}

function isPlainObject(v) {
  return !!v && typeof v === "object" && !Array.isArray(v);
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

/*
 * 只在“标题类字段”里找“抖音”，避免把正文里提到抖音的正常条目误删。
 * 真实福利页任务的标题在 view.title.plain_text（抖音/汽水同一套 luna 结构）。
 */
function isDouyinEntry(item) {
  if (typeof item === "string") return item.indexOf(DOUYIN_KEYWORD) !== -1;
  if (!item || typeof item !== "object") return false;

  const titleLike = ["title", "sub_title", "subtitle", "name", "text", "plain_text",
                     "desc", "display_name", "button_text", "tab_name"];
  for (const f of titleLike) {
    const v = item[f];
    if (typeof v === "string" && v.indexOf(DOUYIN_KEYWORD) !== -1) return true;
    if (v && typeof v === "object" && typeof v.plain_text === "string" &&
        v.plain_text.indexOf(DOUYIN_KEYWORD) !== -1) return true;
  }
  if (item.view && typeof item.view === "object") {
    const vt = item.view.title;
    if (vt && typeof vt === "object" && typeof vt.plain_text === "string" &&
        vt.plain_text.indexOf(DOUYIN_KEYWORD) !== -1) return true;
  }
  return false;
}

function dropDouyinItems(node, log, path, depth) {
  if (depth > 14 || node === null || node === undefined) return;

  if (Array.isArray(node)) {
    const kept = [];
    let dropped = 0;
    for (const item of node) {
      if (isDouyinEntry(item)) {
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
  $done({ body: JSON.stringify(obj), headers: markHeaders("soda-sanitize;hide-douyin", true) });
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
           nn === "isaditem" || nn === "aditem" || nn === "adflag" ||
           nn === "ispromoted" || nn === "promoted" ||
           nn === "issponsored" || nn === "sponsored" ||
           nn === "iscommercial" || nn === "commercialad") &&
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
         nk === "isaditem" || nk === "aditem" || nk === "adflag" ||
         nk === "ispromoted" || nk === "promoted" ||
         nk === "issponsored" || nk === "sponsored" ||
         nk === "iscommercial" || nk === "commercialad") &&
        isAdFlag(v)) {
      return true;
    }
    if (nk === "adinfo" || nk === "addata" || nk === "adextra" ||
        nk === "commercialdata" || nk === "promoteddata") {
      hasAd = true;
    }
    if (nk === "video" || nk === "liveroom" || nk === "media" ||
        nk === "track" || nk === "song" || nk === "aweme" ||
        nk === "roomdata" || nk === "audio" || nk === "music" ||
        nk === "artist" || nk === "album") {
      hasMedia = true;
    }
  }

  if (!hasAd && hasNestedAdFlag(o)) hasAd = true;
  return hasAd && !hasMedia;
}

/*
 * 【循环八/C 步 · 任务对象结构化判别（true样本 = HAR 393 task/page/v2）】
 * ------------------------------------------------------------
 * v1 时代的整条 stringify 匹配（extra.ad_task_id / ad_snap 一并命中）
 * 在 v2 sections 形态下会误删带广告归因的**正常任务**（签到/翻卡都带
 * ad_token/ad_snap）。v2.6.1 起对 tasks / taskInfos 容器改判别依据：
 *   1) item.key 在显式广告任务键名单（music_incentive_ad，样本实证）；
 *   2) item.type 命中 incentive_ad 家族（样本实证 polaris_incentive_ad_v3）；
 *   3) task 标题（view.title.plain_text / title）命中广告关键词。
 * 领奖/发奖字段零接触；luna_rewards_ads（攒时长）仍在保留名单。
 */
const AD_TASK_KEYS = new Set(["music_incentive_ad"]);
const AD_TASK_TYPE = /incentive[_-]?ad/i;
const AD_TASK_TITLE = /看广告|看视频|广告/i;
/* 仅判别 key/task_key 标识串（绝不 stringify 任务体——防 extra.ad_token 误杀）。
 * 家族刻意收窄：裸 /incentive/ 会误杀 luna_incentive_push_permission（打卡提醒，
 * 393 样本实证是正常福利）；/reward[_-]?ads?/ 对 luna_rewards_ads（攒时长）无命中。 */
const AD_TASK_KEY_RE = /ad[_-]?reward|reward[_-]?ads?|incentive[_-]?ad|watch[_-]?(?:video|ad)|commerce[_-]?ad|ad[_-]?(?:snap|task)/i;

function taskTitleOf(item) {
  if (item && item.view && item.view.title) {
    const t = item.view.title;
    if (typeof t === "string") return t;
    if (t && typeof t.plain_text === "string") return t.plain_text;
  }
  if (item && typeof item.title === "string") return item.title;
  return "";
}

function isAdTaskEntry(item) {
  if (!item || typeof item !== "object" || Array.isArray(item)) return false;
  var key = (typeof item.key === "string" && item.key) ||
    (typeof item.task_key === "string" && item.task_key) || "";
  if (key && AD_TASK_KEYS.has(key)) return true;
  if (key && AD_TASK_KEY_RE.test(key)) return true;
  if (typeof item.type === "string" && AD_TASK_TYPE.test(item.type)) return true;
  return AD_TASK_TITLE.test(taskTitleOf(item));
}

/*
 * 【页面级广告预拉取收紧（真样本 = config.ad_api_preload）】
 * ------------------------------------------------------------
 * 只保留“仍留在 sections 里的任务”自己引用的 task_id：
 *   task.id / task.ad_snap.task_id / discrepancy_data.*.base_ad_diversion.id
 * 被摘掉的广告任务和页面快照里不存在的预拉取 id 全部丢弃；
 * 一条不剩时把 preload 也关掉。保留的任务若仍需看广告，其 id 会留下，
 * 不会被误伤。migrate_first_ad 由规则 falsy 置 false。
 */
function collectRetainedTaskIds(sections, ids) {
  for (const section of sections) {
    if (!isPlainObject(section)) continue;
    const groups = [section.task_group, section.widget_task_group];
    for (const group of groups) {
      if (!isPlainObject(group) || !Array.isArray(group.tasks)) continue;
      for (const task of group.tasks) {
        if (!isPlainObject(task)) continue;
        if (task.id !== undefined && task.id !== null && task.id !== "") {
          ids[String(task.id)] = true;
        }
        if (isPlainObject(task.ad_snap) && task.ad_snap.task_id !== undefined) {
          ids[String(task.ad_snap.task_id)] = true;
        }
        const dd = task.discrepancy_data;
        if (!isPlainObject(dd)) continue;
        for (const k of Object.keys(dd)) {
          const sub = dd[k];
          if (isPlainObject(sub) && isPlainObject(sub.base_ad_diversion) &&
              sub.base_ad_diversion.id !== undefined) {
            ids[String(sub.base_ad_diversion.id)] = true;
          }
        }
      }
    }
  }
}

function pruneTaskAdPreload(obj, log) {
  const data = isPlainObject(obj) && isPlainObject(obj.data) ? obj.data : null;
  if (!data) return;

  const cfg = data.config;
  const sections = Array.isArray(data.sections) ? data.sections : [];

  const pre = isPlainObject(cfg) && isPlainObject(cfg.ad_api_preload)
    ? cfg.ad_api_preload : null;
  if (!pre) return;

  if (Array.isArray(pre.task_ids)) {
    const ids = {};
    collectRetainedTaskIds(sections, ids);
    const kept = pre.task_ids.filter(function (id) {
      return ids[String(id)] === true;
    });
    if (kept.length !== pre.task_ids.length) {
      log.push("config.ad_api_preload.task_ids : " +
        pre.task_ids.length + " -> " + kept.length);
      pre.task_ids = kept;
    }
  }
  if (pre.preload === true && Array.isArray(pre.task_ids) && pre.task_ids.length === 0) {
    pre.preload = false;
    log.push("config.ad_api_preload.preload : true -> false");
  }
}

/*
 * 【v2 商业化弹窗精确清理（真样本 = beta-luna commerce/v2/upsell）】
 * ------------------------------------------------------------
 * 93 个弹窗的 HAR 实证：v2 用 upsell_map{} 承载弹窗实体，v1 的
 * card / upsells / upsell_unique_name 已不存在。只删广告/商城命名的实体
 *（ad_incentive_backup_card、*_ads_*、*_reward_ad_*、browse_mall_*），
 * 奖励/发奖/兜底弹窗（reward_*、feed_*_reward_popup、coin_widget）保留。
 * 同时同步三处引用，避免“实体删了但还会被调度”：
 *   freq_ctrl_cfg.freq_ctrl_map / sort_control_unique_names /
 *   cold_launch_timing.upsell_item_unique_names
 * 共享频控键（background_voice_prompt）与非弹窗键（widget_ad）不动。
 */
const AD_UPSELL_RE = /(^|_)ads?(_|$)/;
const MALL_UPSELLS = ["browse_mall_popup_acc_amount"];

function isHiddenUpsellName(name) {
  if (typeof name !== "string") return false;
  return AD_UPSELL_RE.test(name) || MALL_UPSELLS.indexOf(name) !== -1;
}

function cleanUpsellMap(obj, log) {
  const map = obj.upsell_map;
  if (!isPlainObject(map)) return;

  const removed = [];
  for (const name of Object.keys(map)) {
    if (!isHiddenUpsellName(name)) continue;
    delete map[name];
    removed.push(name);
  }
  if (removed.length === 0) return;

  log.push("upsell_map : removed " + removed.length + " popup(s) -> " +
    removed.slice(0, 8).join(", ") + (removed.length > 8 ? " ..." : ""));

  /* 只删与已删弹窗同名的频控项：共享键与非弹窗键必须保留 */
  const freqCfg = obj.freq_ctrl_cfg;
  if (isPlainObject(freqCfg) && isPlainObject(freqCfg.freq_ctrl_map)) {
    const fmap = freqCfg.freq_ctrl_map;
    const dropped = [];
    for (const name of Object.keys(fmap)) {
      if (removed.indexOf(name) === -1) continue;
      delete fmap[name];
      dropped.push(name);
    }
    if (dropped.length > 0) {
      log.push("freq_ctrl_cfg : removed " + dropped.length + " entry(ies) -> " +
        dropped.slice(0, 6).join(", ") + (dropped.length > 6 ? " ..." : ""));
    }
  }

  /*
   * 列表里可能有“只登记、没有实体”的广告弹窗（cold_launch_popup_ads_text），
   * 因此按名字判据全量过滤，而不是只删 removed 里的条目。
   */
  if (Array.isArray(obj.sort_control_unique_names)) {
    const before = obj.sort_control_unique_names.length;
    obj.sort_control_unique_names = obj.sort_control_unique_names.filter(function (n) {
      return !isHiddenUpsellName(n);
    });
    if (obj.sort_control_unique_names.length !== before) {
      log.push("sort_control_unique_names : " + before + " -> " +
        obj.sort_control_unique_names.length + " item(s)");
    }
  }
  const clt = obj.cold_launch_timing;
  if (isPlainObject(clt) && Array.isArray(clt.upsell_item_unique_names)) {
    const before = clt.upsell_item_unique_names.length;
    clt.upsell_item_unique_names = clt.upsell_item_unique_names.filter(function (n) {
      return !isHiddenUpsellName(n);
    });
    if (clt.upsell_item_unique_names.length !== before) {
      log.push("cold_launch_timing : " + before + " -> " +
        clt.upsell_item_unique_names.length + " item(s)");
    }
  }
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
        const structured = (nk === "tasks" || nk === "taskinfos");
        const kept = val.filter(function (item) {
          if (structured) return !isAdTaskEntry(item);
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

/*
 * 福利页打卡：Loon 对同一响应只执行第一条命中的脚本，独立的
 * welfare-stamp 绑定会被清理/观测脚本遮蔽。这里让任何胜出的脚本
 * 在 dailyReminder=true 时顺手写下当天日期，独立绑定只作全关兜底。
 */
function stampWelfare(args) {
  if (!pflag(args, "dailyReminder", false)) return;
  try {
    if (typeof $persistentStore === "undefined" || !$persistentStore ||
        typeof $persistentStore.write !== "function") return;
    var d = new Date();
    var m = String(d.getMonth() + 1);
    var day = String(d.getDate());
    var key = d.getFullYear() + "-" + (m.length < 2 ? "0" + m : m) + "-" +
      (day.length < 2 ? "0" + day : day);
    $persistentStore.write(key, "soda-welfare-seen");
    console.log("[soda] welfare stamp " + key);
  } catch (e) { /* 存储不可用不影响响应 */ }
}

(function main() {
  try {
    const url = ($request && $request.url) || "";
    const raw = readBody($response);

    /*
     * 统一插件开关：保奖励模式优先。
     * rewardSafe=true 时只允许开屏品牌广告继续处理，其他端点直接放行；
     * 唯一例外：hideDouyinTab=true 且是福利页端点时，只做“听抖音”过滤，
     * 不做任何广告裁剪，避免影响奖励任务。
     * 独立主插件没有 $argument，行为保持不变。
     */
    const pluginArgs = pargs([
      "rewardSafe", "cleanAds", "killRewardAds", "hideDouyinTab", "dailyReminder"
    ]);
    const rewardSafe = pflag(pluginArgs, "rewardSafe", true);
    /* 显式打开“断激励广告”时不再受保奖励模式保护（用户主动选择：广告完全不发） */
    const killReward = pflag(pluginArgs, "killRewardAds", false);
    const hideDouyin = pflag(pluginArgs, "hideDouyinTab", false);
    const cleanAds = pflag(pluginArgs, "cleanAds", false);
    const isSplash = /\/luna\/advert\/splash\/brand\/retrieve/.test(url);
    const isTreasure = /\/luna\/(?:treasure|growth)\//.test(url);

    if (/\/luna\/treasure\/task\/page/.test(url)) stampWelfare(pluginArgs);

    if (rewardSafe && !killReward && !isSplash) {
      if (!(hideDouyin && isTreasure)) {
        console.log("[soda] rewardSafe=on, non-splash passthrough: " + url);
        return $done({ headers: markHeaders("soda-sanitize;skip=reward-safe") });
      }
      /* 保奖励 + 隐藏听抖音：只删抖音条目，其余原样返回 */
      return douyinOnly(raw, url);
    }

    /* hideDouyinTab 独立开关：cleanAds 关着时只删抖音条目，不做广告裁剪 */
    if (hideDouyin && !cleanAds && !killReward && isTreasure) {
      return douyinOnly(raw, url);
    }

    if (typeof raw !== "string" || raw.length === 0) {
      return $done({ headers: markHeaders("soda-sanitize;skip=no-body") });
    }

    const head = raw.trimStart().slice(0, 1);
    if (head !== "{" && head !== "[") {
      // 非 JSON（protobuf / 压缩体 / 空体），不动
      return $done({ headers: markHeaders("soda-sanitize;skip=not-json" + ceTag($response)) });
    }

    const rule = RULES.find(function (r) { return r.match.test(url); });
    if (!rule) return $done({ headers: markHeaders("soda-sanitize;skip=no-rule") });

    /*
     * 激励素材（advert/incentive/config|retrieve）只有显式打开 killRewardAds 才清：
     * 清掉它 = 广告完全不发 = 领奖变 amount=-1（2026-10-21 实测）。
     * 没有参数时（独立调用）保持旧行为照常清理。
     */
    if ((rule.id === "incentive-config" || rule.id === "incentive-retrieve") &&
        pluginArgs && !killReward) {
      return $done({ headers: markHeaders("soda-sanitize;skip=reward-ads-kept") });
    }

    /* 大响应预检：没有广告标记就直接放行，避免无谓 JSON.parse */
    if (rule.fastReject && !rule.fastReject.test(raw)) {
      console.log("[soda] " + rule.id + " hit, no ad marker");
      return $done({ headers: markHeaders("soda-sanitize;noop=no-marker") });
    }

    let obj;
    try {
      obj = JSON.parse(raw);
    } catch (e) {
      console.log("[soda] JSON parse failed, passthrough: " + url);
      return $done({ headers: markHeaders("soda-sanitize;skip=json-parse" + ceTag($response)) });
    }

    rule._kill = new Set((rule.kill || []).map(normalizeKey));
    rule._falsy = new Set((rule.falsy || []).map(normalizeKey));
    rule._prune = (rule.prune || []).map(function (p) {
      return { key: normalizeKey(p.key), match: p.match };
    });

    const log = [];
    const before = JSON.stringify(obj);
    rewrite(obj, rule, "$", log, 0);
    if (rule.id === "upsell") cleanUpsellMap(obj, log);
    if (rule.id === "task-page") pruneTaskAdPreload(obj, log);
    if (rule.dropAdItems) dropAdItems(obj, log, "$", 0);
    if (hideDouyin && isTreasure) dropDouyinItems(obj, log, "$", 0);

    if (log.length === 0) {
      console.log("[soda] " + rule.id + " hit, already clean");
      return $done({ headers: markHeaders("soda-sanitize;noop=already-clean") });
    }

    const out = JSON.stringify(obj);
    console.log(
      "[soda] " + rule.id + " | " + log.length + " change(s) | " +
      (DRY_RUN ? "DRY_RUN" : (before.length - out.length) + "B smaller") + "\n  " +
      log.join("\n  ")
    );

    if (DRY_RUN) {
      return $done({ headers: markHeaders("soda-sanitize;dry-run") });
    }

    $done({ body: out, headers: markHeaders("soda-sanitize;changed=" + log.length, true) });
  } catch (e) {
    console.log("[soda] error, passthrough: " + e);
    $done({});
  }
})();
