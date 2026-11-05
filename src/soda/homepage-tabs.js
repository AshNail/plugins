/*
 * SodaClean · 底部 Tab 栏模块过滤（Loon http-response 脚本）
 * ----------------------------------------------------------------------------
 * 取证（21.4.0 / build 100214010 主二进制 REA 逆向）：
 *   - 底部 Tab 由服务端 `/aweme/homepage/combine/` 动态下发（BDPTabBarConfig、
 *     IESECTabKitBottomTabComponent、BNRootPresenter、_finalTabList）。
 *   - Tab 标识符（主二进制字符串）：listen_douyin（听抖音）、song_tab（推荐）、
 *     live（直播）、video（视频）、discover（发现）、mine（我的）等。
 *   - 每个 Tab 对应的 feed 接口：luna/feed/song-tab、luna/feed/listen-video-tab、
 *     luna/feed/live-tab、luna/feed/video-tab；Tab schema：luna://luna.com/song_tab。
 *   - 响应容器字段：bottom_tab_data / bottom_tab / homepage_tabs / tab_list /
 *     tab_data / tab_info / tab_config / main_tab。
 *
 * 两个开关：
 *   hideDouyinTab  只移除【听抖音】（listen_douyin 家族）。
 *   listenOnly     纯听歌模式：移除所有与听歌无关的模块 Tab（听抖音、直播、
 *                  视频、朋友/社区、创作、AI 聊天、消息/IM、一起听、娱乐）。
 *                  保留推荐（song_tab/default_recommend）、发现、我的、音乐。
 *
 * 三重匹配，避免误删：
 *   1) ID：tab_id / tab_name / tab_type / tab_key / key（归一化后比对）
 *   2) schema：schema / scheme / url / link 中包含被禁 schema 片段
 *   3) 标题：tab_title / title / name / text / view.title.plain_text
 * 保护：条目或标题命中 奖励/金币/领奖/reward/incentive/coin 时永不删除，
 *       确保激励获取奖励的链路完整。
 *
 * 失败即放行：非 JSON、结构不认识、没有命中，一律不改响应。
 */

const ENABLED = true;
const DRY_RUN = false;
const VERBOSE = true;

/* ---------------- 被禁 Tab ID（归一化：小写、去 _ - 空格） ---------------- */
const DOUYIN_IDS = [
  "listen_douyin", "listen_video", "listen_video_tab", "listen_video_tab_module",
  "listen_video", "douyin_music", "douyin_tab"
];

const NON_MUSIC_IDS = DOUYIN_IDS.concat([
  /* 直播 */
  "live", "live_tab", "live_tab_play", "livelist", "live_room",
  /* 视频（非纯听歌） */
  "video", "video_tab", "video_playlist", "personal_video_tab",
  /* 朋友 / 社交 / 社区 */
  "friend", "friend_tab", "friends", "social", "community", "community_tab", "square",
  /* 创作工具 */
  "creation", "creation_tools", "creation_tab", "create", "creator",
  /* AI 聊天助手 */
  "chat", "chat_tab", "chat_agent", "chatbot", "ai_chat", "ai_chatbot", "aichat",
  /* 即时通讯 / 消息 */
  "message", "msg", "msg_tab", "message_tab", "im", "im_tab", "notice_tab",
  /* 一起听 */
  "listen_together", "listen_together_tab", "together", "together_listen",
  /* 娱乐 / 演出 / 明星 / 长内容 */
  "entertainment", "entertainment_tab", "show", "star", "movie", "tv", "concert",
  "novel", "book", "comic", "cartoon", "podcast", "radio", "game", "game_tab"
]);

/* schema 里出现这些片段视为非听歌 Tab */
const BLOCK_SCHEMA_PARTS = [
  "listen_douyin", "listen_video_tab", "listen-video-tab",
  "live-tab", "live_tab", "live/",
  "video-tab", "video_tab", "/video_playlist",
  "community", "friend", "social", "creation", "chat_agent", "chatbot",
  "message", "msg_tab", "listen_together", "entertainment"
];

/* hideDouyinTab 模式只认听抖音相关的 schema 片段 */
const DOUYIN_SCHEMA_PARTS = ["listen_douyin", "listen_video_tab", "listen-video-tab"];

/* 标题命中这些词视为非听歌 Tab（只在标题字段里找，不扫正文） */
const BLOCK_TITLE_RE = /听抖音|直播|朋友|社区|创作|AI\s*聊天|聊天助手|一起听|娱乐|广场|明星|演出|电影|电视剧|小说|漫画|游戏|消息/i;

/* hideDouyinTab 模式只认听抖音标题 */
const DOUYIN_TITLE_RE = /听抖音/i;

/* 奖励保护：命中这些词的条目永不删除 */
const KEEP_REWARD_RE = /奖励|金币|领奖|提现|reward|incentive|coin|treasure/i;

/* 可能承载 Tab 列表的字段（归一化后匹配） */
const TAB_CONTAINER_FIELDS = new Set([
  "bottomtabdata", "bottomtab", "bottomtabs", "homepagetabs", "hometabs",
  "tablist", "tabdata", "tabinfo", "tabinfos", "tabconfig", "tabs",
  "maintabs", "maintab", "mainpage", "tabbar", "tabbarconfig",
  "topttabs", "toptab", "toptabs", "lefttabs", "xtab", "xtabs"
]);

function normalize(v) {
  return String(v).toLowerCase().replace(/[_\-.\s]/g, "");
}

function normSet(list) {
  const s = new Set();
  for (const x of list) s.add(normalize(x));
  return s;
}

const DOUYIN_SET = normSet(DOUYIN_IDS);
const NON_MUSIC_SET = normSet(NON_MUSIC_IDS);

/* ---------------- 工具 ---------------- */
function textOf(v) {
  if (typeof v === "string") return v;
  if (v && typeof v === "object") {
    if (typeof v.plain_text === "string") return v.plain_text;
    if (typeof v.text === "string") return v.text;
  }
  return "";
}

function hasReward(item) {
  if (!item || typeof item !== "object") return false;
  for (const k of Object.keys(item)) {
    const nk = normalize(k);
    // 奖励相关键名
    if (nk.indexOf("reward") !== -1 || nk.indexOf("incentive") !== -1 ||
        nk.indexOf("coin") !== -1 || nk.indexOf("treasure") !== -1) {
      return true;
    }
    const v = item[k];
    if (typeof v === "string" && KEEP_REWARD_RE.test(v)) return true;
  }
  // 标题字段里的奖励词
  const title = textOf(item.tab_title) || textOf(item.title) || textOf(item.name);
  return KEEP_REWARD_RE.test(title);
}

function tabIds(item) {
  const out = [];
  const fields = ["tab_id", "tabId", "tab_name", "tabName", "tab_type", "tabType",
                  "tab_key", "tabKey", "key", "id"];
  for (const f of fields) {
    const v = item[f];
    if (typeof v === "string" && v) out.push(v);
  }
  return out;
}

function schemas(item) {
  const out = [];
  const fields = ["schema", "scheme", "url", "link", "action", "tab_schema", "tabSchema"];
  for (const f of fields) {
    const v = item[f];
    if (typeof v === "string" && v) out.push(v);
  }
  return out;
}

function titles(item) {
  const out = [];
  for (const f of ["tab_title", "tabTitle", "title", "name", "text", "display_name"]) {
    const t = textOf(item[f]);
    if (t) out.push(t);
  }
  if (item.view && typeof item.view === "object") {
    const t = textOf(item.view.title);
    if (t) out.push(t);
  }
  return out;
}

/* 判断一个条目是否是被禁 Tab。listenOnly=true 用全量黑名单，否则只用听抖音。 */
function isBlockedTab(item, listenOnly) {
  if (!item || typeof item !== "object" || Array.isArray(item)) return false;
  if (hasReward(item)) return false; // 奖励条目永久保护

  const idSet = listenOnly ? NON_MUSIC_SET : DOUYIN_SET;

  for (const id of tabIds(item)) {
    if (idSet.has(normalize(id))) return true;
  }

  const schemaParts = listenOnly ? BLOCK_SCHEMA_PARTS : DOUYIN_SCHEMA_PARTS;
  for (const s of schemas(item)) {
    const low = s.toLowerCase();
    for (const part of schemaParts) {
      if (low.indexOf(part) !== -1) return true;
    }
  }

  const titleRe = listenOnly ? BLOCK_TITLE_RE : DOUYIN_TITLE_RE;
  for (const t of titles(item)) {
    if (titleRe.test(t)) return true;
  }

  return false;
}

/* 只对“Tab 容器数组”做过滤，避免误伤普通数组 */
function filterTabsArray(arr, listenOnly, log, path) {
  const kept = [];
  let dropped = 0;
  for (let i = 0; i < arr.length; i++) {
    const item = arr[i];
    if (isBlockedTab(item, listenOnly)) {
      dropped++;
      if (VERBOSE) {
        const id = tabIds(item)[0] || titles(item)[0] || "unknown";
        log.push(path + "[" + i + "] : removed " + id);
      }
      continue;
    }
    kept.push(item);
  }
  if (dropped > 0) {
    arr.length = 0;
    for (const item of kept) arr.push(item);
  }
  return dropped;
}

function walk(node, listenOnly, log, path, depth) {
  if (depth > 14 || node === null || node === undefined) return;

  if (Array.isArray(node)) {
    for (let i = 0; i < node.length; i++) {
      walk(node[i], listenOnly, log, path + "[" + i + "]", depth + 1);
    }
    return;
  }
  if (typeof node !== "object") return;

  for (const key of Object.keys(node)) {
    const nk = normalize(key);
    const v = node[key];

    if (TAB_CONTAINER_FIELDS.has(nk) && Array.isArray(v)) {
      filterTabsArray(v, listenOnly, log, path + "." + key);
    }

    // 递归（过滤后继续下钻）
    walk(node[key], listenOnly, log, path + "." + key, depth + 1);
  }
}

/* ---------------- 主逻辑 ---------------- */
(function main() {
  if (!ENABLED || (!$argument.hideDouyinTab && !$argument.listenOnly)) {
    $done({});
    return;
  }

  const listenOnly = !!$argument.listenOnly;
  const raw = $response.body;
  const url = $request.url;

  if ($argument.debugLog) {
    console.log("[soda-trace] RESP homepage-tabs url=" + url +
      " len=" + (raw && raw.length) + " mode=" +
      (listenOnly ? "listenOnly" : "hideDouyinTab"));
  }

  if (!raw || typeof raw !== "string" || raw.length === 0) {
    $done({});
    return;
  }

  // 快速预检：没有 Tab 相关字样直接放行，避免无谓 JSON.parse
  const fastCheck = /(?:"[a-z_-]*tab[a-z_-]*"\s*:)|listen[-_]douyin|listen[-_]video[-_]tab/i;
  if (!fastCheck.test(raw)) {
    if (VERBOSE) console.log("[soda] homepage-tabs: no tab config, passthrough: " + url);
    $done({});
    return;
  }

  let obj;
  try {
    obj = JSON.parse(raw);
  } catch (e) {
    console.log("[soda] homepage-tabs: JSON parse failed, passthrough: " + url);
    $done({});
    return;
  }

  const log = [];
  walk(obj, listenOnly, log, "$", 0);

  if (log.length === 0) {
    if (VERBOSE) console.log("[soda] homepage-tabs: no blocked tab found, passthrough: " + url);
    $done({});
    return;
  }

  console.log("[soda] homepage-tabs (" + (listenOnly ? "listenOnly" : "hideDouyinTab") +
    "): removed " + log.length + " tab(s)\n  " + log.join("\n  "));

  if (DRY_RUN) {
    console.log("[soda] homepage-tabs: DRY_RUN, passthrough");
    $done({});
    return;
  }

  const headers = $response.headers || {};
  headers["X-Soda-Plugin"] = "homepage-tabs";
  $done({ body: JSON.stringify(obj), headers: headers });
})();
