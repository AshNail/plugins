/*
 * SodaClean · 激励链路观测（只读，不改响应）
 * ------------------------------------------------------------
 * 用途：
 *   在 Loon 里确认“激励广告到底有没有下发、奖励任务还在不在、
 *   发奖接口返回了什么”。它只写日志，永远不修改响应体。
 *
 * 端点：
 *   incentive/config、incentive/retrieve、incentive/done
 *   ads/config、ads/retrieve、ads/dsp/retrieve
 *   ads/reward/receive、ads/reward/settle
 *   commerce/validate_reward
 *   treasure/task/view、treasure/entrance/config
 *   treasure/task/reward_ads/do_action
 *   treasure/task/fallback/do_action
 *   treasure/task/flip_card/do_action
 *   treasure/task/guide/do_action
 *   treasure/task/browse_mall/do_action
 *   growth/activity_entrance、growth/activity/finish
 *   advert/fallback/done/info
 *   commerce/v2/upsell（只读奖励入口变量）
 *
 * 日志前缀：[soda-reward]
 *
 * 隐私：
 *   - 只打印结构、计数、白名单字段；
 *   - 不打印 token / cookie / session / device_id / 用户 ID；
 *   - 不打印广告素材 URL、跳转链接、完整任务文案。
 *
 * 注意：
 *   - 这是观测插件，不是“跳过广告”插件；
 *   - 它不会缩短广告、伪造回调或直接发奖；
 *   - 大响应（> 256KB）只打印长度，不解析，避免拖慢广告加载。
 */

const PREFIX = "[soda-reward]";
const MAX_BODY = 262144;       // 256KB，超过只记录长度
const MAX_NODES = 2500;        // 遍历节点上限，避免大 JSON 卡顿
const MAX_TASKS = 12;
const MAX_LOG = 1600;

const RULES = [
  { id: "incentive-config", match: /\/luna\/advert\/incentive\/config/ },
  { id: "incentive-retrieve", match: /\/luna\/advert\/incentive\/retrieve/ },
  { id: "incentive-done", match: /\/luna\/advert\/incentive\/done/ },
  { id: "ads-config", match: /\/luna\/ads\/config/ },
  { id: "ads-retrieve", match: /\/luna\/ads\/retrieve/ },
  { id: "ads-dsp-retrieve", match: /\/luna\/ads\/dsp\/retrieve/ },
  { id: "reward-receive", match: /\/luna\/ads\/reward\/receive/ },
  { id: "reward-settle", match: /\/luna\/ads\/reward\/settle/ },
  { id: "validate-reward", match: /\/luna\/commerce\/validate_reward/ },
  { id: "task-view", match: /\/luna\/treasure\/task\/view/ },
  { id: "task-page", match: /\/luna\/treasure\/task\/page\/v[0-9]+/ },
  { id: "treasure-entrance", match: /\/luna\/treasure\/entrance\/config/ },
  { id: "reward-ads-action", match: /\/luna\/treasure\/task\/reward_ads\/do_action/ },
  { id: "fallback-action", match: /\/luna\/treasure\/task\/fallback\/do_action/ },
  { id: "flip-card-action", match: /\/luna\/treasure\/task\/flip_card\/do_action/ },
  { id: "guide-action", match: /\/luna\/treasure\/task\/guide\/do_action/ },
  { id: "browse-mall-action", match: /\/luna\/treasure\/task\/browse_mall\/do_action/ },
  { id: "growth-entrance", match: /\/luna\/growth\/activity_entrance/ },
  { id: "growth-finish", match: /\/luna\/growth\/activity\/finish/ },
  { id: "fallback-done", match: /\/luna\/advert\/fallback\/done\/info/ },
  { id: "upsell-v2", match: /\/luna\/commerce\/v2\/upsell(?:\?|$)/ }
];

/* 白名单字段：只观察这些，避免把任意对象都打进日志 */
const FIELD_MAP = {
  advertsources: "sources",
  feedadvertconfig: "feedConfig",
  adinfosmap: "adInfosMap",
  adinfos: "adInfos",
  adunitconfigs: "adUnitConfigs",
  rewardconfig: "rewardConfig",
  taskinfos: "taskInfos",
  tasklist: "taskList",
  tasks: "tasks",
  bannerlist: "bannerList",
  adlaunchlist: "adLaunchList",
  adlaunch: "adLaunch",
  adsblocks: "adsBlocks",
  adsinfo: "adsInfo",
  rewards: "rewards",
  playentitlements: "playEntitlements",
  rewarddetails: "rewardDetails",
  rewardtips: "rewardTips",
  dailyrewardcontents: "dailyRewardContents",
  rewardcontent: "rewardContent",
  rewardamount: "rewardAmount",
  rewardmaxamount: "rewardMaxAmount",
  rewardtype: "rewardType",
  validduration: "validDuration",
  effectiveplaytime: "effectivePlayTime",
  freqperday: "freqPerDay",
  rewarddurationtype: "rewardDurationType",
  launchduration: "launchDuration",
  queststype: "questsType",
  compensate: "compensate",
  isvalid: "isValid",
  transactionsuccess: "transactionSuccess",
  subsinfo: "subsInfo",
  preload: "preload",
  canshow: "canShow",
  rewardfinishedtaskinfo: "rewardFinishedTaskInfo",
  daysobtained: "daysObtained",
  fullday: "fullDay",
  allfull: "allFull",
  tasksfinished: "tasksFinished",
  tasktofullday: "taskToFullDay",
  maxreleasedays: "maxReleaseDays",
  rewardadvancereleasedays: "rewardAdvanceReleaseDays",
  expiretime: "expireTime",
  cooldownendtime: "cooldownEndTime"
};

const REWARD_FIELDS = [
  "rewardDetails", "rewardTips", "isValid", "transactionSuccess",
  "subsInfo", "playEntitlements", "compensate", "launchDuration",
  "questsType", "rewardAmount", "rewardMaxAmount", "rewardType",
  "validDuration", "effectivePlayTime", "rewardContent",
  "dailyRewardContents", "freqPerDay", "rewardDurationType",
  "rewardFinishedTaskInfo", "maxReleaseDays", "rewardAdvanceReleaseDays",
  "expireTime", "cooldownEndTime"
];

const PROGRESS_FIELDS = [
  "daysObtained", "fullDay", "allFull", "tasksFinished", "taskToFullDay"
];

const SENSITIVE_KEY = /^(?:access[_-]?token|refresh[_-]?token|token|authorization|cookie|set-cookie|session|session[_-]?id|user[_-]?id|uid|device[_-]?id|sign|signature|secret|secret[_-]?key|api[_-]?key)$/i;

function normalizeKey(k) {
  return String(k).toLowerCase().replace(/[_-]/g, "");
}

function isObject(v) {
  return v !== null && typeof v === "object" && !Array.isArray(v);
}

function sizeOf(v) {
  if (Array.isArray(v)) return v.length;
  if (isObject(v)) return Object.keys(v).length;
  return v === undefined ? 0 : 1;
}

function scalar(v) {
  if (v === null || v === undefined) return String(v);
  if (typeof v === "number" || typeof v === "boolean") return v;
  if (typeof v === "string") return v.length > 64 ? v.slice(0, 64) + "…" : v;
  if (Array.isArray(v)) return "array[" + v.length + "]";
  return "object{" + Object.keys(v).length + "}";
}

function safeText(v) {
  if (typeof v !== "string") return scalar(v);
  let s = v.length > 80 ? v.slice(0, 80) + "…" : v;
  return s.replace(/[A-Za-z0-9_-]{24,}/g, "<redacted>");
}

function keysOf(v, limit) {
  if (!isObject(v)) return [];
  return Object.keys(v)
    .filter(function (k) { return !SENSITIVE_KEY.test(k); })
    .slice(0, limit || 20);
}

function addField(out, obj, names, label) {
  for (let i = 0; i < names.length; i++) {
    if (Object.prototype.hasOwnProperty.call(obj, names[i])) {
      out[label] = scalar(obj[names[i]]);
      return;
    }
  }
}

function taskSummary(obj) {
  const out = {};
  addField(out, obj, ["task_key", "taskKey"], "key");
  if (out.key === undefined) addField(out, obj, ["key"], "key");
  if (out.key === undefined) addField(out, obj, ["id"], "id");
  addField(out, obj, ["task_type", "taskType"], "type");
  addField(out, obj, ["reward_type", "rewardType"], "reward");
  addField(out, obj, ["reward_amount", "rewardAmount"], "amount");
  addField(out, obj, ["reward_max_amount", "rewardMaxAmount"], "max");
  addField(out, obj, ["valid_duration", "validDuration"], "valid");
  addField(out, obj, ["can_show", "canShow"], "show");
  addField(out, obj, ["status", "task_status", "taskStatus"], "status");
  addField(out, obj, ["completed", "is_completed", "isCompleted"], "done");

  const stats = obj.stats;
  if (isObject(stats)) {
    addField(out, stats, ["total_times", "totalTimes"], "total");
    addField(out, stats, ["completed_times", "completedTimes"], "doneTimes");
    addField(out, stats, ["last_rewarded_time", "lastRewardedTime"], "lastReward");
  }

  const view = obj.view;
  if (isObject(view) && isObject(view.button)) {
    addField(out, view.button, ["action"], "action");
  }

  /*
   * 任务标题：默认不打（避免把文案写进日志），
   * 打开 logTaskTitles 才带出来 —— 用来定位福利页里的【听抖音】等入口。
   */
  if (LOG_TASK_TITLES) {
    const title = taskTitle(obj);
    if (title) out.title = title;
  }

  if (obj.ad_snap || obj.adSnap) out.adSnap = true;
  return Object.keys(out).length ? out : null;
}

/* 任务标题：从 title / view.title / name 里取纯文本，截断 24 字 */
function taskTitle(obj) {
  const cands = [obj.title, obj.name, obj.text, obj.desc];
  if (isObject(obj.view)) {
    cands.push(obj.view.title, obj.view.subtitle, obj.view.sub_title);
  }
  for (let i = 0; i < cands.length; i++) {
    const v = cands[i];
    let s = null;
    if (typeof v === "string") s = v;
    else if (isObject(v)) {
      if (typeof v.plain_text === "string") s = v.plain_text;
      else if (typeof v.text === "string") s = v.text;
    }
    if (s) return s.length > 24 ? s.slice(0, 24) + "…" : s;
  }
  return null;
}

function hasTaskKey(obj) {
  if (Object.prototype.hasOwnProperty.call(obj, "task_key") ||
      Object.prototype.hasOwnProperty.call(obj, "taskKey") ||
      Object.prototype.hasOwnProperty.call(obj, "task_id") ||
      Object.prototype.hasOwnProperty.call(obj, "taskId")) {
    return true;
  }
  /*
   * 抖音/汽水新版福利页的任务对象用 key + id（没有 task_key），
   * 例如 {"id":"600585","key":"soda_music_sign_in","view":{...},"stats":{...}}。
   * 只有同时出现 id 与 view/stats/rewards 时才算任务，避免把普通字典误判。
   */
  if (Object.prototype.hasOwnProperty.call(obj, "key") &&
      Object.prototype.hasOwnProperty.call(obj, "id")) {
    return isObject(obj.view) || isObject(obj.stats) || Array.isArray(obj.rewards);
  }
  return false;
}

/*
 * 一次遍历收集：
 *   - 白名单字段的计数
 *   - 任务对象摘要
 * 不修改任何节点，不写回响应。
 */
function scan(node, depth, acc) {
  if (depth > 8 || !node || typeof node !== "object") return;
  if (acc.nodes++ > MAX_NODES) return;

  if (Array.isArray(node)) {
    const n = Math.min(node.length, 60);
    for (let i = 0; i < n; i++) scan(node[i], depth + 1, acc);
    return;
  }

  if (hasTaskKey(node) && acc.tasks.length < MAX_TASKS) {
    if (acc.taskSeen.indexOf(node) === -1) {
      acc.taskSeen.push(node);
      const t = taskSummary(node);
      if (t) acc.tasks.push(t);
    }
  }

  const keys = Object.keys(node);
  for (let i = 0; i < keys.length; i++) {
    const k = keys[i];
    const v = node[k];
    const bucket = FIELD_MAP[normalizeKey(k)];
    if (bucket) {
      if (!acc.fields[bucket]) acc.fields[bucket] = [];
      if (acc.fields[bucket].length < 6) {
        acc.fields[bucket].push(v);
      }
    }
    scan(v, depth + 1, acc);
  }
}

function countOf(acc, name) {
  const arr = acc.fields[name];
  if (!arr || arr.length === 0) return undefined;
  let best = 0;
  for (let i = 0; i < arr.length; i++) {
    const n = sizeOf(arr[i]);
    if (n > best) best = n;
  }
  return best;
}

function firstOf(acc, name) {
  const arr = acc.fields[name];
  return arr && arr.length ? arr[0] : undefined;
}

function rewardSummary(acc) {
  const out = {};
  for (let i = 0; i < REWARD_FIELDS.length; i++) {
    const name = REWARD_FIELDS[i];
    const v = firstOf(acc, name);
    if (v === undefined) continue;
    if (isObject(v)) {
      out[name] = { keys: keysOf(v, 8), count: Object.keys(v).length };
    } else if (Array.isArray(v)) {
      out[name] = { count: v.length, sample: v.length ? scalar(v[0]) : null };
    } else {
      out[name] = scalar(v);
    }
  }
  return out;
}

function progressSummary(acc) {
  const out = {};
  for (let i = 0; i < PROGRESS_FIELDS.length; i++) {
    const name = PROGRESS_FIELDS[i];
    const v = firstOf(acc, name);
    if (v !== undefined) out[name] = scalar(v);
  }
  return out;
}

/*
 * upsell v2：只读奖励入口资格。
 * 不输出弹窗标题/正文/图片/跳转链接，也不输出会员到期时间。
 */
const UPSELL_VARIABLES = [
  "enable_ads", "enable_coin", "ads_today_task_full", "ads_days_obtained",
  "max_release_days", "reward_tasks_count", "has_play_entitlement",
  "can_show_cold_launch_popup_coin", "coin_new_user_first_launch_opt"
];

function pickField(obj, names) {
  if (!isObject(obj)) return undefined;
  for (let i = 0; i < names.length; i++) {
    if (Object.prototype.hasOwnProperty.call(obj, names[i])) return obj[names[i]];
  }
  return undefined;
}

function countKey(node, wanted, depth, acc) {
  if (depth > 10 || node === null || typeof node !== "object") return;
  if (acc.nodes++ > 2000) return;
  if (Array.isArray(node)) {
    const n = Math.min(node.length, 80);
    for (let i = 0; i < n; i++) countKey(node[i], wanted, depth + 1, acc);
    return;
  }
  const keys = Object.keys(node);
  for (let i = 0; i < keys.length; i++) {
    const k = keys[i];
    if (normalizeKey(k) === wanted) acc.n++;
    countKey(node[k], wanted, depth + 1, acc);
  }
}

function upsellSummary(obj) {
  if (!isObject(obj)) return null;
  const out = {};

  /* 二进制原样拼写是 upellsVariables（少一个 s），同时兼容正确拼写 */
  const vars = pickField(obj, [
    "upells_variables", "upellsVariables", "upsell_variables", "upsellVariables"
  ]);
  if (isObject(vars)) {
    for (let i = 0; i < UPSELL_VARIABLES.length; i++) {
      const name = UPSELL_VARIABLES[i];
      if (Object.prototype.hasOwnProperty.call(vars, name)) {
        out[name] = scalar(vars[name]);
      }
    }
  }

  const scenes = pickField(obj, ["scene_upsells_map", "sceneUpsellsMap"]);
  if (isObject(scenes)) {
    const names = Object.keys(scenes);
    out.scenes = names.length;
    if (names.length) {
      out.sceneNames = names.slice(0, 8).map(function (n) { return safeText(n); });
    }
  } else if (Array.isArray(scenes)) {
    out.scenes = scenes.length;
  }

  /* 金币挂件的直接宿主：UpsellItem.fixedEntrance.coinWidgetData */
  if (scenes !== undefined) {
    const fe = { n: 0, nodes: 0 };
    const cw = { n: 0, nodes: 0 };
    countKey(scenes, "fixedentrance", 0, fe);
    countKey(scenes, "coinwidgetdata", 0, cw);
    if (fe.n) out.fixedEntrances = fe.n;
    if (cw.n) out.coinWidgets = cw.n;
  }

  const sortNames = pickField(obj, ["sort_control_unique_names", "sortControlUniqueNames"]);
  if (Array.isArray(sortNames)) out.sortNames = sortNames.length;
  else if (isObject(sortNames)) out.sortNames = Object.keys(sortNames).length;
  else if (sortNames !== undefined) out.sortNames = scalar(sortNames);

  const popup = pickField(obj, ["popup_config", "popupConfig"]);
  if (popup !== undefined) out.popupConfig = sizeOf(popup);

  const cold = pickField(obj, ["cold_launch_timing", "coldLaunchTiming"]);
  if (cold !== undefined) out.coldLaunchTiming = scalar(cold);

  return Object.keys(out).length ? out : null;
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

/* 广告耗时实测：记下广告下发时刻，到发奖时算差值 */
/* 今日广告耗时统计：$persistentStore 累计“今天看了几个广告、共多少秒” */
const AD_STATS_KEY = "soda-ad-stats";

function todayKey() {
  const d = new Date();
  const m = String(d.getMonth() + 1);
  const day = String(d.getDate());
  return d.getFullYear() + "-" + (m.length < 2 ? "0" + m : m) + "-" + (day.length < 2 ? "0" + day : day);
}

/* 福利页打卡：观测脚本在同一响应上胜出时也要留下“今天来过”的凭证 */
function stampWelfare(args) {
  if (!pflag(args, "dailyReminder", false)) return;
  try {
    if (typeof $persistentStore === "undefined" || !$persistentStore ||
        typeof $persistentStore.write !== "function") return;
    const key = todayKey();
    $persistentStore.write(key, "soda-welfare-seen");
    console.log(PREFIX + " welfare stamp " + key);
  } catch (e) { /* 存储不可用不影响响应 */ }
}

function recordAdSeconds(seconds) {
  if (seconds < 0) return null;
  try {
    if (typeof $persistentStore === "undefined" || !$persistentStore ||
        typeof $persistentStore.read !== "function") return null;
    const day = todayKey();
    let stats = null;
    const raw = $persistentStore.read(AD_STATS_KEY);
    if (raw) {
      try { stats = JSON.parse(raw); } catch (e) { stats = null; }
    }
    if (!stats || stats.day !== day) stats = { day: day, n: 0, s: 0 };
    stats.n += 1;
    stats.s += seconds;
    if (typeof $persistentStore.write === "function") {
      $persistentStore.write(JSON.stringify(stats), AD_STATS_KEY);
    }
    return stats;
  } catch (e) {
    return null;
  }
}

const AD_START_KEY = "soda-ad-start";

function rememberAdStart() {
  try {
    if (typeof $persistentStore !== "undefined" && $persistentStore &&
        typeof $persistentStore.write === "function") {
      $persistentStore.write(String(Date.now()), AD_START_KEY);
    }
  } catch (e) { /* 存储不可用就跳过测量 */ }
}

function adElapsedSeconds() {
  try {
    if (typeof $persistentStore === "undefined" || !$persistentStore ||
        typeof $persistentStore.read !== "function") return -1;
    const raw = $persistentStore.read(AD_START_KEY);
    if (!raw) return -1;
    const start = parseInt(raw, 10);
    if (!start) return -1;
    /*
     * 只清这一个键：官方 API 文档 5.3 写明 `$persistentStore.remove()` **不接受参数**，
     * 作用是「清空通过脚本存储 API 保存的全部数据」。传进去的 key 会被忽略，
     * 于是每量一次广告时长，就把 welfare-seen / ad-stats / 每日提醒等其它键一起抹了。
     * 删单个键的唯一写法是 `write(undefined, key)`（官方 5.1）。
     */
    if (typeof $persistentStore.write === "function") {
      $persistentStore.write(undefined, AD_START_KEY);
    }
    return Math.round((Date.now() - start) / 1000);
  } catch (e) {
    return -1;
  }
}

/* 开关：logTaskTitles 由 [Argument] 传入，默认关 */
let LOG_TASK_TITLES = false;

(function main() {
  try {
    const url = ($request && $request.url) || "";
    const args = pargs(["logTaskTitles", "dailyReminder"]);
    LOG_TASK_TITLES = pflag(args, "logTaskTitles", false);
    if (/\/luna\/treasure\/task\/page/.test(url)) stampWelfare(args);

    const rule = RULES.find(function (r) { return r.match.test(url); });
    if (!rule) return $done({});

    const path = url.replace(/^https?:\/\/[^/]+/, "").split("?")[0];
    let raw = readBody($response);

    if (/\/advert\/incentive\/retrieve/.test(url)) rememberAdStart();

    if (typeof raw !== "string" || raw.length === 0) {
      console.log(PREFIX + " " + rule.id + " empty body");
      return $done({});
    }

    if (raw.length > MAX_BODY) {
      console.log(PREFIX + " " + rule.id + " body too large len=" + raw.length);
      return $done({});
    }

    const head = raw.trimStart().slice(0, 1);
    if (head !== "{" && head !== "[") {
      console.log(PREFIX + " " + rule.id + " non-JSON len=" + raw.length + ceTag($response));
      return $done({});
    }

    let obj;
    try {
      obj = JSON.parse(raw);
    } catch (e) {
      console.log(PREFIX + " " + rule.id + " JSON parse failed len=" + raw.length + ceTag($response));
      return $done({});
    }

    const acc = { nodes: 0, fields: {}, tasks: [], taskSeen: [] };
    scan(obj, 0, acc);

    let status;
    let statusInfo;
    if (isObject(obj)) {
      if (Object.prototype.hasOwnProperty.call(obj, "status_code")) status = obj.status_code;
      else if (Object.prototype.hasOwnProperty.call(obj, "statusCode")) status = obj.statusCode;
      if (Object.prototype.hasOwnProperty.call(obj, "status_info")) statusInfo = obj.status_info;
      else if (Object.prototype.hasOwnProperty.call(obj, "statusInfo")) statusInfo = obj.statusInfo;
    }

    const counts = {};
    const countNames = [
      "sources", "feedConfig", "adInfosMap", "adInfos", "adUnitConfigs",
      "rewardConfig", "taskInfos", "taskList", "bannerList", "adLaunchList",
      "adLaunch", "adsBlocks", "adsInfo", "rewards", "playEntitlements"
    ];
    for (let i = 0; i < countNames.length; i++) {
      const n = countOf(acc, countNames[i]);
      if (n !== undefined) counts[countNames[i]] = n;
    }

    /* 发奖结果：amount=-1 表示这笔没发出来（广告没播/被风控） */
    if (/\/advert\/incentive\/done/.test(url)) {
      const details = obj && obj.reward_details ? obj.reward_details : null;
      const parts = [];
      if (details && typeof details === "object") {
        for (const k of Object.keys(details)) {
          const d = details[k] || {};
          parts.push("amount=" + d.amount + " claim=" + d.claim_status +
            (d.expire_time ? " expire=" + d.expire_time : ""));
        }
      }
      const elapsed = adElapsedSeconds();
      const stats = elapsed >= 0 ? recordAdSeconds(elapsed) : null;
      console.log(PREFIX + " 发奖结果 " + (parts.join(" | ") || "-") +
        (elapsed >= 0 ? " | 广告请求->发奖 " + elapsed + " 秒" : "") +
        (stats ? " | 今日广告 " + stats.n + " 次 / 共 " + stats.s + " 秒" : ""));
    }

    const summary = {
      path: path,
      status: status,
      statusInfo: statusInfo === undefined ? undefined : safeText(statusInfo),
      keys: isObject(obj) ? keysOf(obj, 20) : (Array.isArray(obj) ? "array[" + obj.length + "]" : typeof obj),
      counts: counts,
      preload: scalar(firstOf(acc, "preload")),
      progress: progressSummary(acc),
      tasks: acc.tasks,
      reward: rewardSummary(acc)
    };

    const upsell = upsellSummary(obj);
    if (upsell) summary.upsell = upsell;

    /* 可选字段为空时删掉，保持日志短 */
    if (summary.status === undefined) delete summary.status;
    if (summary.statusInfo === undefined) delete summary.statusInfo;
    if (summary.preload === "undefined") delete summary.preload;
    if (!summary.tasks.length) delete summary.tasks;
    if (!Object.keys(summary.reward).length) delete summary.reward;
    if (!Object.keys(summary.progress).length) delete summary.progress;
    if (!Object.keys(summary.counts).length) delete summary.counts;

    let line = JSON.stringify(summary);
    if (line.length > MAX_LOG) line = line.slice(0, MAX_LOG) + "…";

    console.log(PREFIX + " " + rule.id + " " + line);
    return $done({});
  } catch (e) {
    console.log(PREFIX + " error, passthrough: " + e);
    $done({});
  }
})();
