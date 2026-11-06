/**
 * 起点读书 · 看书激励助手 v3.5.0
 *
 * 核心功能（看书+激励）：
 *
 * 【自动化层】
 *   Token 窃取：App 打开时自动捕获 auth headers(getlogininfo/getconf/checkin)
 *   自动签到：cron 每天 POST /argus/api/v2/checkin/checkin + 抽奖
 *   激励任务重放：拦截 finishWatch，重放 9/9 和 3/3
 *   自动领奖：拦截 receiveTaskReward + 尝试 6 个领奖端点
 *
 * 【响应净化层】（v3.4.0 起本层是**回退层**：同 URL 的 [Rewrite] 引擎复写默认生效并抑制本脚本）
 *   getconf 净化：30 项字段覆写 + 10 项字段删除（关广告/追踪/弹窗）
 *   开屏广告：清空 getsplashscreen 返回
 *   发现页：白名单过滤（保留书单/专栏/IP 专区）
 *   书架：悬浮广告/置顶运营位清空
 *   福利中心：mainPage/mainPageDialog 净化
 *   账户页：营销模块删除
 *   每日导读：Items 清空
 *   广告列表：getadvlist/getadvlistbatch 已由复写整条终止
 *   阅读积分：readpage 时长改满值 + 任务标记完成（v3.4.0 起挂 autoTask，不随净化默认开）
 *   弹窗/红点：popup/batchget、reddot/getdot 清空
 *   新手引导：freshman 系列清空
 *   章末模块：showChapterEndModule 清空
 *   青少年配置：young/getconf 清空
 *
 * 【广告 SDK 层】
 *   视频秒播：patch 时长字段为 1 秒
 *
 * 致谢：3kaiu 起点全能助手 Pro 的方案。
 */

// ==========================================
// 🔒 凭据掩码
// ==========================================
/** @type {Array<[RegExp, string]>} */
const MASK_RULES = [
  [/cmfuToken[=:]\s*([A-Za-z0-9_-]{8,})/gi, "cmfuToken=***MASKED***"],
  [/(token|cookie|key|secret)[=:]\s*([A-Za-z0-9_+/=-]{16,})/gi, "$1=***MASKED***"],
];

function maskSecrets(str) {
  if (typeof str !== "string") return str;
  let out = str;
  for (const [re, rep] of MASK_RULES) out = out.replace(re, rep);
  return out;
}

// ==========================================
// ⚙️ 配置
// ==========================================
const CONFIG = {
  // 激励任务映射
  TaskMapping: {
    "1218712929269776384": { name: "激励视频", count: 9 },
    "1218712929269776388": { name: "福利任务", count: 3 },
  },

  // 可自动领取的奖励端点
  RewardEndpoints: [
    { path: "/argus/api/v1/video/adv/receiveTaskReward", name: "视频任务奖励" },
    { path: "/argus/api/v3/freshman/autoreceive", name: "新用户自动领取" },
    { path: "/argus/api/v1/ontimeredpacket/receivetaskrpaward", name: "定时红包" },
    { path: "/argus/api/v1/ploy/receiverewardsatisfy", name: "奖励满足" },
    { path: "/argus/api/v1/dialog/receivetask", name: "对话框任务" },
    { path: "/argus/api/v1/dialog/takereward", name: "对话框奖励" },
  ],

  // getconf 字段覆写（关广告/追踪/弹窗）
  ClientConfigOverrides: {
    "PangleEnable": "0",                    // 穿山甲广告
    "DisableQidianBurryReport": "1",        // 埋点上报
    "DisableNewabInBI": "1",                // BI 分析
    "SplashScreenInterval": "0",            // 开屏间隔
    "SplashScreenRoundCount": "0",          // 开屏轮次
    "BusinessSplashCoolDownTime": "99999",  // 商业开屏冷却
    "PushDialogFrequency": "0",             // 推送弹窗频率
    "EnableMonitorLog": "0",                // 监控日志
    "EnableBeaconFullBurry": "0",           // Beacon 全量埋点
    "ReloadExposureEnabled": "false",       // 曝光重载
    "QDABRegularReportTimeSpan": "999999",  // AB 测试上报
    "QDABReportMinThreshold": "999999",     // AB 测试阈值
    "RankBuryPoint": "0",                   // 排行埋点
    "CheckInPushSwitchReport": "0",         // 签到推送上报
    "WolfEye": 0,                           // 狼眼监控
    "MainTabActivityRunning": 0,            // 主 Tab 活动
    "DailyReadRecReasonSwitch": 0,          // 每日阅读推荐
    "DailyRecommendGray": 0,                // 每日推荐灰度
    "EnableShareChapterPloy": 0,            // 分享章节策略
    "EnableChapterAdvanceGuide": 0,         // 章节提前引导
    "AddBookShelfNoticeFrequency": "999999",// 加书架通知
    "BookShelfPushNoticeFrequency": "999999",// 书架推送通知
    "UGCPushNoticeFrequency": "999999",     // UGC 推送通知
    "NotificationPageBackPushNoticeFrequency": "999999",
    "ActivityPageBackPushNoticeFrequency": "999999",
    "InAppPushLimitMinutes": "999999",      // 应用内推送限制
    "PushNoticeFrequency": "-1",            // 推送通知频率
    "AegisSignOn": 0,                       // 安全盾签到
    "EnableFockRetryStrategy": 0,           // Fock 重试策略
    "EnableSearchUser": "1",                // 允许搜索用户
  },

  // getconf 整段删除的 key
  DeleteKeys: [
    "ActivityIcon", "ActivityPopup", "LuckBag",
    "BookShelfBottomIcons", "ClassicBookInfo", "ClientLocalNotify2",
    "PushDialogScenes", "RewardSatisfyDialog", "FansClubPropInfo",
    "AdVideoPositionConfig", "GDT",
  ],

  // 直接 404 拒绝的纯广告端点（保留核心阅读相关）
  RejectPaths: [
    "push/getdialog",
    "booksearch/hotWords", "maintain/playstrip", "young/getconf",
    "followsubscribe/showChapterEndModule", "freshman/bookshelfbtn",
    "freshman/freshmanGuidePopup",
    "message/getpushedmessagelist", "dailyrecommend/recommendBook",
    "bookshelf/getTopOperation",
    "popup/batchget", "ploy/getactivitylist",
    "message/pullOperationPush", "message/pullSocialPush",
    "video/adv/reportDialog", "interaction/getclassicbookinfo",
    "bookshelf/getad", "client/iosad",
  ],

  // 发现页保留白名单（核心阅读内容）
  DiscoverKeepKeys: [
    "NEW_ZHUANQU",    // IP 专区
    "NEW_ZHUANLAN",   // 专栏
    "NEW_SHUDAN",     // 书单
  ],

  // 账户页删除营销模块
  AccountPageDelKeys: ["BenefitButtonList"],

  // 广告白名单（保留激励相关广告位）
  AdWhitelist: ["reward", "video", "normaltask", "limitegg", "redpocket"],

  // 视频秒播时长
  VideoSkipSeconds: 1,
  AdDurationKeys: ["video_duration", "video_timelife", "duration", "play_time", "total_time", "show_time", "max_time", "stay", "display_time"],
  RewardTimeKeys: ["rewardTime", "appearanceTime", "minVideoTime", "videoTime"],

  // 阅读积分满值（秒/天）
  ReadTimeFull: 7200,

  SilentMode: false,
  CheckinRetry: 2,
  CheckinTimeout: 10000,
  ReplayTimeout: 15000,
};

// ==========================================
// 🪵 debugLog 开关（顶层作用域：所有 handler 共用）
// ==========================================
// 必须放顶层：handleClientConfig / handleAccountPage / doSignIn / doLottery 等
// 顶层函数会调用它；放在主 IIFE 里时这些调用会解析成未定义变量，真机表现为
// ReferenceError → 兜底空 $done() → getconf/账户页净化与签到/抽奖静默失效。
const DEBUG = (() => {
  try { return String($argument?.debugLog || "false") === "true"; } catch (e) { return false; }
})();

function debugLog(msg) {
  if (DEBUG) console.log("[起点全能助手] [DEBUG] " + msg);
}

// ==========================================
// 📌 锚定日志（v3.3.0 方向 A 试验期**常开**，不受 debugLog 门禁）
// ==========================================
// 目的只有一个：把「执行面」的事实钉进真机日志，供后续优化对账，判读口径：
//   · 有 anchor phase=response 行        ⇒ 这条 URL 的 [Script] 绑定被调用了
//   · 同 URL 有 [Rewrite] 规则却仍有此行 ⇒ 官方互斥没生效，或复写正则没命中
//   · 此行消失                            ⇒ 复写命中并接管（净化改由引擎做）
//   · enc=gzip + parsed=0                 ⇒ 脚本拿到原始压缩体，本侧净化必然 passthrough
//   · ungzip=missing                      ⇒ Build < 988，没有 $utils.ungzip
// 净化确认稳定生效后本段降回 debugLog 门禁（整段可一次 revert）。
const ANCHOR_BUILD = "3.5.0";

function anchor(msg) {
  try { console.log("[起点锚点] b=" + ANCHOR_BUILD + " " + msg); } catch (e) {}
}

function anchorEnv() {
  let ungzip = "missing";
  try {
    if (typeof $utils !== "undefined" && typeof $utils.ungzip === "function") ungzip = "present";
  } catch (e) {}
  return "ungzip=" + ungzip + " debug=" + DEBUG;
}

// 只记长度与压缩特征，绝不把 body 写进日志（含用户凭据与书籍正文）。
function bodyShape(body) {
  if (body === null || body === undefined) return "none";
  if (typeof body === "string") {
    return "str:" + body.length +
      (body.length > 1 && body.charCodeAt(0) === 0x1f && body.charCodeAt(1) === 0x8b ? " gzip" : "");
  }
  if (typeof Uint8Array !== "undefined" && body instanceof Uint8Array) {
    return "u8:" + body.length + (body[0] === 0x1f && body[1] === 0x8b ? " gzip" : "");
  }
  if (typeof ArrayBuffer !== "undefined" && body instanceof ArrayBuffer) {
    return "ab:" + body.byteLength +
      (new Uint8Array(body).length > 1 && new Uint8Array(body)[0] === 0x1f ? " gzip?" : "");
  }
  return typeof body;
}

function pickHeader(headers, name) {
  if (!headers) return "";
  const want = String(name).toLowerCase();
  for (const k of Object.keys(headers)) {
    if (String(k).toLowerCase() === want) return String(headers[k] || "");
  }
  return "";
}

function anchorBody(response) {
  if (!response) return "";
  return " body=[" + bodyShape(response.body) + "] enc=" +
    (pickHeader(response.headers, "content-encoding") || "-");
}

// ==========================================
// 🚀 主入口
// ==========================================
// eslint-disable-next-line @typescript-eslint/no-unused-expressions
!(async () => {
  const E = new Env("起点全能助手");

  // Cron 模式：无 $request → 定时任务
  if (typeof $request === "undefined") {
    let tk = "";
    try { tk = ($persistentStore.read("Qidian_Headers") || "").length ? "set" : "none"; } catch (e) { tk = "err"; }
    anchor("phase=timer " + anchorEnv() + " token=" + tk);
    await runCronTasks(E);
    E.done();
    return;
  }

  const { url, method } = $request;
  anchor("phase=" + (typeof $response === "undefined" ? "request" : "response") +
    " " + method + " " + url.replace(/^https?:\/\/[^/]+/, "").slice(0, 90) +
    " " + anchorEnv() + anchorBody($response));
  debugLog("请求: " + method + " " + url.substring(0, 120));

  // ── A. Token 窃取（response 阶段） ──
  if (url.includes("/user/getlogininfo") && typeof $response !== "undefined") {
    captureToken(E, "getlogininfo");
    E.done();
    return;
  }

  // ── B. Token 窃取（request 阶段，补充源） ──
  if ((url.includes("/client/getconf") || url.includes("/checkin/")) &&
      url.includes("magev6") && typeof $response === "undefined") {
    captureToken(E, "request");
    E.done();
    return;
  }

  // ── C. getconf 响应净化 ──
  if (url.includes("/client/getconf") && typeof $response !== "undefined") {
    debugLog("处理 getconf 响应净化");
    handleClientConfig(E, $response);
    return;
  }

  // ── D. finishWatch 重放 ──
  if (url.includes("/video/adv/finishWatch") && method === "POST" &&
      typeof $response === "undefined") {
    debugLog("拦截 finishWatch 请求,准备重放");
    await handleReplay(E, $request);
    return;
  }

  // ── E. receiveTaskReward 拦截 ──
  if (url.includes("/video/adv/receiveTaskReward") && method === "POST" &&
      typeof $response === "undefined") {
    handleRewardReceive(E, $request);
    return;
  }

  // ── F. 广告 SDK 秒播（视频时长 patch） ──
  if (url.includes(".mp4") && (url.includes("gdtimg.com") || url.includes("gtimg.cn"))) {
    handleVideoReplace(E);
    return;
  }

  // ── G. 广告 SDK 秒播（响应 patch） ──
  if ((url.includes("/gdt_inner_view") || url.includes("/get_ads")) &&
      typeof $response !== "undefined") {
    handleAdSkip(E, $response);
    return;
  }

  // 解析 URL
  let urlObj;
  try { urlObj = new URL(url); } catch (e) { E.done(); return; }
  const path = urlObj.pathname;

  // ── H. 直接拒绝纯广告端点 ──
  if (typeof $response === "undefined" && CONFIG.RejectPaths.some(p => path.includes(p))) {
    E.done({ status: 404 });
    return;
  }

  // ── I. 响应净化（v3.3.0 起为**回退层**：同 URL 的 [Rewrite] 复写命中时官方会抑制本脚本，
  //     所以这一段还能跑到，就说明对应复写规则没命中或本就没有复写覆盖）──
  if (typeof $response !== "undefined") {
    // 开屏广告
    if (path.includes("getsplashscreen")) { debugLog("处理开屏广告"); handleSplashScreen(E, $response); return; }
    // Deeplink 广告
    if (path.includes("deeplink/geturl")) { debugLog("处理 Deeplink 广告"); handleDeeplink(E, $response); return; }
    // 每日导读
    if (path.includes("dailyrecommend")) { debugLog("处理每日导读"); handleDailyRec(E, $response); return; }
    // 账户页
    if (path.includes("getaccountpage")) { debugLog("处理账户页净化"); handleAccountPage(E, $response); return; }
    // 广告列表
    if (path.includes("adv/getadvlistbatch")) { debugLog("处理广告列表"); handleAdListBatch(E, url, $response); return; }
    // 直接击杀广告
    if (CONFIG.RejectPaths.some(p => path.includes(p)) && !CONFIG.AdWhitelist.some(k => url.includes(k))) {
      debugLog("直接击杀广告: " + path); handleDirectAdKill(E, url, $response); return;
    }
    // 福利中心主页
    if (path.includes("video/adv/mainPage") && !path.includes("Dialog")) {
      debugLog("处理福利中心主页"); handleMainPage(E, $response); return;
    }
    // 发现页
    if (path.includes("getsimplediscover")) { debugLog("处理发现页"); handleDiscover(E, $response); return; }
    // 书架悬浮广告
    if (path.includes("getHoverAdv")) { debugLog("处理书架悬浮广告"); handleHoverAdv(E, $response); return; }
    // 每日阅读积分
    if (path.includes("readtime/readpage")) { debugLog("处理每日阅读积分"); handleReadTime(E, $response); return; }
    // 净化规则
    if (matchCleanRule(path)) { debugLog("匹配净化规则: " + path); handleClean(E, path, $response); return; }
    anchor("js-sanitize=none path=" + path.slice(0, 80) + "（该 URL 没有被任何脚本处置认领）");
  }

  E.done();
})().catch(e => {
  try { new Env("起点全能助手").log("异常: " + e); } catch (_) {}
  try { $done(); } catch (_) {}
});

// ==========================================
// 🔑 Token 捕获
// ==========================================
function captureToken(E, source) {
  try {
    const headers = (typeof $request !== "undefined" && $request.headers) ? $request.headers : null;
    if (!headers) { return; }
    const hasToken = Object.keys(headers).some(k => /cookie|authorization|cmfutoken/i.test(k));
    if (!hasToken) { return; }
    $persistentStore.write(JSON.stringify(headers), "Qidian_Headers");
    E.log("Token 已捕获 (via " + source + ")");
  } catch (e) {
    E.log("Token 捕获失败: " + e);
  }
}

// ==========================================
// 📺 finishWatch 重放
// ==========================================
async function handleReplay(E, request) {
  const body = request.body || "";
  const matchedId = Object.keys(CONFIG.TaskMapping).find(id => body.includes(id));
  if (!matchedId) { E.done(); return; }

  const task = CONFIG.TaskMapping[matchedId];
  const replayCount = task.count - 1;
  if (replayCount <= 0) { E.done(); return; }

  E.log("识别任务: " + task.name + ", 重放 " + replayCount + " 次");
  const headers = normalizeHeaders(request.headers || {});

  const tasks = [];
  for (let i = 0; i < replayCount; i++) {
    tasks.push((async () => {
      await E.wait((i + 1) * 2000);
      const t0 = Date.now();
      try {
        const res = await E.fetch({
          url: request.url, method: "POST", headers: headers, body: body,
          timeout: CONFIG.ReplayTimeout,
        });
        const ms = Date.now() - t0;
        const code = res ? res.statusCode : "ERR";
        E.log("[重放 " + (i + 1) + "/" + replayCount + "] " + task.name + " HTTP " + code + " " + ms + "ms");
        return { ok: res && res.statusCode === 200, code: code };
      } catch (err) {
        E.log("[重放 " + (i + 1) + "/" + replayCount + "] " + task.name + " 异常: " + String(err).slice(0, 80));
        return { ok: false, code: "EXC" };
      }
    })());
  }

  const results = await Promise.allSettled(tasks);
  const settled = results.map(r => r.status === "fulfilled" ? r.value : { ok: false, code: "REJ" });
  const ok = settled.filter(x => x.ok).length;
  const expired = settled.some(x => x.code === 401 || x.code === 403);
  const total = replayCount + 1;
  const summary = task.name + ": " + (ok + 1) + "/" + total + (expired ? " (Cookie 可能过期)" : "");

  if (!CONFIG.SilentMode) { await E.notify("起点助手", "", summary); }
  else { E.log("[静默] " + summary); }

  E.done();
}

// ==========================================
// 🎁 领奖处理
// ==========================================
function handleRewardReceive(E, request) {
  const endpoint = CONFIG.RewardEndpoints.find(ep => request.url.includes(ep.path));
  if (!endpoint) { E.done(); return; }

  E.log("拦截领奖请求: " + endpoint.name);
  const rewardData = {
    url: request.url,
    headers: normalizeHeaders(request.headers || {}),
    body: request.body || "",
    timestamp: Date.now(),
  };
  $persistentStore.write(JSON.stringify(rewardData), "Qidian_LastRewardRequest");
  E.log("已保存领奖请求");
  E.done();
}

async function autoReceiveRewards(E, headers) {
  E.log("开始自动领奖...");
  let received = 0;

  // 重放上次的领奖请求
  const lastRewardStr = $persistentStore.read("Qidian_LastRewardRequest");
  if (lastRewardStr) {
    try {
      const lastReward = JSON.parse(lastRewardStr);
      if (Date.now() - lastReward.timestamp < 86400000) {
        const res = await E.fetch({
          url: lastReward.url, method: "POST",
          headers: normalizeHeaders(headers), body: lastReward.body,
          timeout: CONFIG.CheckinTimeout,
        });
        if (res && res.statusCode === 200) {
          const obj = safeJsonParse(res.body);
          if (obj && obj.Result === 0) { E.log("领奖成功"); received++; }
        }
      }
    } catch (e) { E.log("领奖重放异常: " + e); }
  }

  // 尝试调用各领奖端点
  for (const endpoint of CONFIG.RewardEndpoints) {
    try {
      const baseUrl = endpoint.path.includes("freshman") ? "https://h5.if.qidian.com" : "https://magev6.if.qidian.com";
      const res = await E.fetch({
        url: baseUrl + endpoint.path, method: "POST",
        headers: normalizeHeaders(headers), body: "",
        timeout: CONFIG.CheckinTimeout,
      });
      if (res && res.statusCode === 200) {
        const obj = safeJsonParse(res.body);
        if (obj && obj.Result === 0) { E.log(endpoint.name + " 领取成功"); received++; }
      }
    } catch (e) { E.log(endpoint.name + " 异常: " + e); }
  }

  if (received > 0) E.log("自动领奖完成，成功 " + received + " 项");
  return received;
}

// ==========================================
// 🔧 响应处理工具函数
// ==========================================
/**
 * 构建响应头，删除 content-encoding 和 content-length
 * 添加 X-Qidian-Plugin 标记用于诊断
 */
function respondHeaders(tag) {
  const h = Object.assign({}, (typeof $response !== "undefined" && $response.headers) || {});
  h["X-Qidian-Plugin"] = tag || "qidian-sanitize";
  
  // 删除 content-encoding 和 content-length
  const drop = [];
  for (const k of Object.keys(h)) {
    const lk = String(k).toLowerCase();
    if (lk === "content-encoding" || lk === "content-length") drop.push(k);
  }
  for (const k of drop) delete h[k];
  
  return h;
}

/**
 * 返回修改后的 JSON 响应
 * 自动处理响应头，确保客户端能正确解析
 */
function respondJson(E, obj, tag) {
  E.done({ 
    body: JSON.stringify(obj), 
    headers: respondHeaders(tag) 
  });
}

// ==========================================
// 🔧 响应净化
// ==========================================
function handleClientConfig(E, response) {
  const obj = safeJsonParse(response.body);
  if (!obj) {
    anchor("getconf parsed=0 reason=parse-fail" + anchorBody(response));
    E.done();
    return;
  }
  if (!obj.Data) {
    anchor("getconf parsed=1 reason=no-Data result=" + obj.Result);
    E.done();
    return;
  }

  const changes = [];
  for (const [k, v] of Object.entries(CONFIG.ClientConfigOverrides)) {
    if (obj.Data[k] !== v) changes.push(k + "=" + v);
    obj.Data[k] = v;
  }
  CONFIG.DeleteKeys.forEach(k => {
    if (obj.Data[k] !== undefined) { changes.push("delete:" + k); delete obj.Data[k]; }
  });
  obj.Data.NewFeedsDiscover = 0;
  if (obj.Data.CloudSetting && obj.Data.CloudSetting.TeenShowFreq) {
    obj.Data.CloudSetting.TeenShowFreq = "0";
  }

  anchor("getconf parsed=1 changes=" + changes.length + "（此行出现=复写未接管 getconf，脚本仍在净化）");
  debugLog("getconf 净化: " + changes.length + " 项变更 [" + changes.slice(0, 5).join(", ") + (changes.length > 5 ? "..." : "") + "]");
  respondJson(E, obj, "qidian-sanitize");
}

function handleSplashScreen(E, response) {
  debugLog("handleSplashScreen 开始执行");
  const obj = safeJsonParse(response.body);
  if (!obj) {
    debugLog("handleSplashScreen: JSON 解析失败");
    E.done();
    return;
  }
  if (obj.Data && Array.isArray(obj.Data.List)) {
    debugLog("handleSplashScreen: 清空 List, 原长度: " + obj.Data.List.length);
    obj.Data.List = [];
  }
  respondJson(E, obj, "qidian-sanitize");
}

function handleDeeplink(E, response) {
  const obj = safeJsonParse(response.body);
  if (!obj) { E.done(); return; }
  if (obj.Data) obj.Data = {};
  respondJson(E, obj, "qidian-sanitize");
}

function handleDailyRec(E, response) {
  const obj = safeJsonParse(response.body);
  if (!obj) { E.done(); return; }
  if (obj.Data && obj.Data.Items) obj.Data.Items = [];
  respondJson(E, obj, "qidian-sanitize");
}

function handleAccountPage(E, response) {
  const obj = safeJsonParse(response.body);
  if (!obj) { E.done(); return; }
  if (obj.Data) {
    const deleted = [];
    CONFIG.AccountPageDelKeys.forEach(k => {
      if (obj.Data[k] !== undefined) { deleted.push(k); delete obj.Data[k]; }
    });
    if (deleted.length > 0) debugLog("账户页删除: " + deleted.join(", "));
  }
  respondJson(E, obj, "qidian-sanitize");
}

function handleAdListBatch(E, url, response) {
  if (CONFIG.AdWhitelist.some(kw => url.includes(kw))) { E.done(); return; }
  const obj = safeJsonParse(response.body);
  if (!obj) { E.done(); return; }
  if (obj.Data) obj.Data = Array.isArray(obj.Data) ? [] : {};
  respondJson(E, obj, "qidian-sanitize");
}

function handleDirectAdKill(E, url, response) {
  if (CONFIG.AdWhitelist.some(kw => url.includes(kw))) { E.done(); return; }
  const obj = safeJsonParse(response.body);
  if (!obj) { E.done(); return; }
  if (obj.Data) obj.Data = Array.isArray(obj.Data) ? [] : {};
  E.log("广告已秒杀");
  respondJson(E, obj, "qidian-sanitize");
}

function handleMainPage(E, response) {
  const obj = safeJsonParse(response.body);
  if (!obj || !obj.Data) { E.done(); return; }
  const data = obj.Data;
  if (data.DailyBenefitModule) data.DailyBenefitModule.RotateText = [];
  const REMOVE_KEYS = [
    "MemberExclusiveTaskModule", "PrivilegedTaskModule", "MoreRewardTab",
    "SurpriseBenefit", "LastRewardItems", "IndexBannerTabs",
    "BaizeModule", "TaskShowData", "UserRewardModule", "PopFrequency",
  ];
  REMOVE_KEYS.forEach(k => { delete data[k]; });
  E.log("福利中心净化完成");
  respondJson(E, obj, "qidian-sanitize");
}

function handleDiscover(E, response) {
  const obj = safeJsonParse(response.body);
  if (!obj || !obj.Data || !Array.isArray(obj.Data.Items)) { E.done(); return; }
  obj.Data.Items = obj.Data.Items.filter(item => CONFIG.DiscoverKeepKeys.includes(item.KeyName));
  E.log("发现页过滤完成，保留 " + obj.Data.Items.length + " 项");
  respondJson(E, obj, "qidian-sanitize");
}

function handleHoverAdv(E, response) {
  const obj = safeJsonParse(response.body);
  if (!obj) { E.done(); return; }
  if (!obj.Data) obj.Data = {};
  obj.Data.ItemList = [];
  E.log("书架悬浮广告已清空");
  respondJson(E, obj, "qidian-sanitize");
}

function handleReadTime(E, response) {
  const obj = safeJsonParse(response.body);
  if (!obj || !obj.Data) { E.done(); return; }
  const data = obj.Data;
  if (data.ReadInfo) data.ReadInfo.TodayReadTime = CONFIG.ReadTimeFull;
  if (data.TaskModule && Array.isArray(data.TaskModule.TaskList)) {
    data.TaskModule.TaskList.forEach(t => { t.Status = 2; });
  }
  E.log("每日阅读积分已满");
  respondJson(E, obj, "qidian-sanitize");
}

function handleVideoReplace(E) {
  // 1 秒黑屏 MP4 (H.264 320x240, 655 bytes)
  const MP4_B64 = "AAAAFGZ0eXBpc29tAAAAAWlzb20AAAJKbW9vdgAAAGhtdmhkAAAAAAAAAAAAAAAAAAAD6AAAA+gAAQAAAQAAAAAAAAAAAAAAAAEAAAABAAAAAQAAAAEAAAABAAAAAQAAAAEAAAABAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB2nRyYWsAAABcdGtoZAAAAAcAAAAAAAAAAAAAAAEAAAAAAAAD6AAAAAAAAAAAAAAAAAEAAAAAAQAAAAEAAAABAAAAAQAAAAEAAAABAAAAAQAAAAEAAAABAAABQAAAAPAAAAAAAXZtZGlhAAAAIG1kaGQAAAAAAAAAAAAAAAAAAAPoAAAD6FXEAAAAAAAtaGRscgAAAAAAAAAAdmlkZQAAAAAAAAAAAAAAAFZpZGVvSGFuZGxlcgAAAAEhbWluZgAAABR2bWhkAAAAAAAAAAAAAAAAAAAAKGRpbmYAAAAgZHJlZgAAAAAAAAABAAAAEHVybCAAAAAAAAAAAQAAAN1zdGJsAAAAdXN0c2QAAAAAAAAAAQAAAGVhdmMxAAAAAAAAAAEAAAAAAAAAAAAAAAABQADwAEgAAABIAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFwFCAB7/4QAIQgAeq0B4FgABAAQ4gAAAAAAAGHN0dHMAAAAAAAAAAQAAAAEAAAPoAAAAHHN0c2MAAAAAAAAAAQAAAAEAAAABAAAAAQAAABhzdHN6AAAAAAAAAAAAAAABAAAAKQAAABRzdGNvAAAAAAAAAAEAAAJmAAAAMW1kYXQAAAABZ0IAHqtAeBYAAAABaM44gAAAAAFliIQAR//89S5qCCNTGQASiA==";
  try {
    const mp4 = Uint8Array.from(atob(MP4_B64), c => c.charCodeAt(0));
    E.done({ body: mp4.buffer, headers: { "Content-Type": "video/mp4" } });
  } catch (e) { E.done(); }
}

function handleAdSkip(E, response) {
  const obj = safeJsonParse(response.body);
  if (obj) {
    patchDurationFields(obj, CONFIG.AdDurationKeys, CONFIG.VideoSkipSeconds);
    respondJson(E, obj, "qidian-sanitize");
    return;
  }
  let body = String(response.body || "");
  const s = CONFIG.VideoSkipSeconds;
  body = body
    .replace(/"video_duration":\s*\d+/g, '"video_duration":' + s)
    .replace(/"video_timelife":\s*\d+/g, '"video_timelife":' + s)
    .replace(/"duration":\s*\d+/g, '"duration":' + s)
    .replace(/"play_time":\s*\d+/g, '"play_time":' + s)
    .replace(/"total_time":\s*\d+/g, '"total_time":' + s)
    .replace(/"show_time":\s*\d+/g, '"show_time":' + s)
    .replace(/"max_time":\s*\d+/g, '"max_time":' + s);
  E.done({ body });
}

const CLEAN_RULES = {
  "video/adv/mainPageDialog": ["Data"],
  "reddot/getdot": ["Data"],
  "checkin/checkinexchangepage": ["Data.Goods"],
};

function matchCleanRule(path) {
  return Object.keys(CLEAN_RULES).some(k => path.includes(k));
}

function getCleanRules(path) {
  for (const [k, rules] of Object.entries(CLEAN_RULES)) {
    if (path.includes(k)) return rules;
  }
  return null;
}

function handleClean(E, path, response) {
  let obj = safeJsonParse(response.body);
  if (!obj) { E.done(); return; }
  const rules = getCleanRules(path);
  if (rules) rules.forEach(r => applyCleanRule(obj, r.split(".")));
  E.log("净化完成: " + path.split("/").pop());
  respondJson(E, obj, "qidian-sanitize");
}

function parseSelector(segment) {
  const match = /^([^[\]]+)(?:\[([^=\]]+)=([^\]]+)\])?$/.exec(segment);
  if (!match) return { key: segment };
  return { key: match[1], filterKey: match[2], filterValue: match[3] };
}

function applyCleanRule(target, segments, index = 0) {
  if (!target || index >= segments.length) return;
  const { key, filterKey, filterValue } = parseSelector(segments[index]);
  const current = target[key];
  if (current == null) return;
  if (index === segments.length - 1) {
    if (filterKey && Array.isArray(current)) {
      target[key] = current.filter(item => String(item?.[filterKey]) !== filterValue);
      return;
    }
    delete target[key];
    return;
  }
  if (filterKey && Array.isArray(current)) {
    current.filter(item => String(item?.[filterKey]) === filterValue)
           .forEach(item => applyCleanRule(item, segments, index + 1));
    return;
  }
  applyCleanRule(current, segments, index + 1);
}

function patchDurationFields(value, keys, nextValue) {
  if (!value || typeof value !== "object") return;
  if (Array.isArray(value)) {
    value.forEach(item => patchDurationFields(item, keys, nextValue));
    return;
  }
  if (value.name && CONFIG.RewardTimeKeys.includes(value.name) && Array.isArray(value.data)) {
    value.data.forEach(d => {
      if (d && d.data && d.data.int_val !== undefined) d.data.int_val = String(nextValue);
    });
  }
  for (const [key, item] of Object.entries(value)) {
    if (keys.includes(key)) {
      if (typeof item === "number") { value[key] = nextValue; continue; }
      if (typeof item === "string" && !isNaN(Number(item))) { value[key] = String(nextValue); continue; }
    }
    patchDurationFields(item, keys, nextValue);
  }
}

// ==========================================
// ⏰ Cron 定时任务
// ==========================================
async function runCronTasks(E) {
  E.log("开始执行定时任务...");

  const headersStr = $persistentStore.read("Qidian_Headers");
  if (!headersStr) {
    E.log("未找到 Token，请先打开起点 App");
    if (!CONFIG.SilentMode) E.notify("起点助手", "未找到 Token", "请打开起点 App 触发 Token 捕获");
    return;
  }

  let headers;
  try { headers = JSON.parse(headersStr); } catch (e) { E.log("Token 解析失败: " + e); return; }

  // 1. 签到
  const signResult = await doCheckin(E, headers);
  if (signResult === "expired") return;

  // 2. 抽奖
  if (signResult === "ok") await doLottery(E, headers);

  // 3. 自动领奖
  await autoReceiveRewards(E, headers);
}

async function doCheckin(E, headers) {
  debugLog("开始签到...");
  for (let i = 0; i < CONFIG.CheckinRetry; i++) {
    try {
      const res = await E.fetch({
        url: "https://magev6.if.qidian.com/argus/api/v2/checkin/checkin",
        method: "POST", headers: normalizeHeaders(headers), body: "",
        timeout: CONFIG.CheckinTimeout,
      });

      if (res && res.statusCode === 200) {
        const obj = safeJsonParse(res.body);
        if (obj && obj.Result === 0) {
          const msg = obj.Message || "签到成功";
          debugLog("签到成功: " + msg);
          if (!CONFIG.SilentMode) E.notify("起点助手", "签到成功", msg);
          else E.log("[静默] 签到成功: " + msg);
          return "ok";
        }
        if (obj && obj.Result === -452000) {
          const msg = obj.Message || "今日已签到";
          debugLog("今日已签到: " + msg);
          if (!CONFIG.SilentMode) E.notify("起点助手", "今日已签到", msg);
          else E.log("[静默] 今日已签到: " + msg);
          return "ok";
        }
        const msg = obj ? JSON.stringify(obj).slice(0, 200) : "未知错误";
        debugLog("签到异常: " + msg);
        if (!CONFIG.SilentMode) E.notify("起点助手", "签到异常", msg);
        return "failed";
      }

      const code = res ? res.statusCode : 0;
      if (code === 401 || code === 403) {
        debugLog("Cookie 过期: HTTP " + code);
        if (!CONFIG.SilentMode) E.notify("起点助手", "Cookie 过期", "请打开起点 App 触发 Token 刷新");
        return "expired";
      }

      debugLog("签到 HTTP " + code + ", 重试 " + (i + 1) + "/" + CONFIG.CheckinRetry);
      E.log("签到 HTTP " + code + ", 重试 " + (i + 1) + "/" + CONFIG.CheckinRetry);
      if (i < CONFIG.CheckinRetry - 1) await E.wait(1500);
    } catch (e) {
      debugLog("签到异常: " + e);
      E.log("签到异常: " + e);
      if (i < CONFIG.CheckinRetry - 1) await E.wait(1500);
    }
  }

  if (!CONFIG.SilentMode) E.notify("起点助手", "签到失败", "重试 " + CONFIG.CheckinRetry + " 次后仍失败");
  return "failed";
}

async function doLottery(E, headers) {
  debugLog("开始抽奖...");
  try {
    const res = await E.fetch({
      url: "https://magev6.if.qidian.com/argus/api/v1/checkin/checkinlottery",
      method: "POST", headers: normalizeHeaders(headers), body: "",
      timeout: CONFIG.CheckinTimeout,
    });
    if (res && res.statusCode === 200) {
      const obj = safeJsonParse(res.body);
      if (obj && obj.Result === 0) {
        const award = (obj.Data && obj.Data.AwardName) || "成功";
        debugLog("抽奖成功: " + award);
        E.log("抽奖: " + award);
        if (!CONFIG.SilentMode) E.notify("起点助手", "抽奖", award);
        return;
      }
      const msg = (obj && obj.Message) || "无奖励";
      debugLog("抽奖: " + msg);
      E.log("抽奖: " + msg);
    } else {
      debugLog("抽奖 HTTP " + (res ? res.statusCode : "无响应"));
    }
  } catch (e) {
    debugLog("抽奖异常: " + e);
    E.log("抽奖异常: " + e);
  }
}

// ==========================================
// 🔧 工具函数
// ==========================================
function normalizeHeaders(headers) {
  const h = Object.assign({}, headers);
  delete h["Content-Length"];
  delete h["content-length"];
  return h;
}

function safeJsonParse(body) {
  if (body === null || body === undefined) return null;
  if (typeof body === "object" && !(body instanceof Uint8Array) && !(body instanceof ArrayBuffer)) return body; // 已经是对象，直接返回
  
  // 处理字符串
  if (typeof body === "string") {
    // 检测 gzip 魔数 (1f 8b)
    if (body.length >= 2 && body.charCodeAt(0) === 0x1f && body.charCodeAt(1) === 0x8b) {
      if (typeof $utils === "undefined" || typeof $utils.ungzip !== "function") {
        anchor("gzip str len=" + body.length + " ungzip=missing ⇒ 本侧净化必然 passthrough");
        return null;
      }
      try {
        const obj = JSON.parse($utils.ungzip(body));
        anchor("gzip str len=" + body.length + " ungzip=ok");
        return obj;
      } catch (e) {
        anchor("gzip str len=" + body.length + " ungzip=fail " + String((e && e.message) || e).slice(0, 60));
      }
      return null;
    }
    
    try { return JSON.parse(body); } catch (e) { 
      console.log("[起点全能助手] [DEBUG] JSON 解析失败: " + String((e && e.message) || e).slice(0, 60) + ", len=" + body.length);
      return null; 
    }
  }
  
  // 处理 Uint8Array / ArrayBuffer
  if (body instanceof Uint8Array || body instanceof ArrayBuffer) {
    const bytes = body instanceof Uint8Array ? body : new Uint8Array(body);
    anchor("binary " + (body instanceof Uint8Array ? "u8" : "ab") + " len=" + bytes.length);
    // 检测 gzip
    if (bytes.length >= 2 && bytes[0] === 0x1f && bytes[1] === 0x8b) {
      try {
        if (typeof $utils !== "undefined" && $utils.ungzip) {
          const decompressed = $utils.ungzip(body);
          return JSON.parse(decompressed);
        }
        anchor("binary gzip ungzip=missing ⇒ 本侧净化必然 passthrough");
      } catch (e) {
        anchor("binary gzip ungzip=fail " + String((e && e.message) || e).slice(0, 60));
      }
    }
    // 尝试直接转字符串
    try {
      if (typeof globalThis.TextDecoder !== "undefined") {
        const str = new globalThis.TextDecoder().decode(bytes);
        return JSON.parse(str);
      }
    } catch (e) {
      anchor("binary textDecode=fail " + String((e && e.message) || e).slice(0, 60));
    }
  }
  
  return null;
}

// ==========================================
// 🌍 Env 兼容层 (Loon)
// ==========================================
function Env(name) {
  this.name = name;
  this.log = function () {
    var args = Array.prototype.slice.call(arguments);
    console.log("[" + this.name + "] " + args.join(" "));
  };
  this.wait = function (ms) { return new Promise(function (r) { setTimeout(r, ms); }); };
  this.done = function (o) { try { $done(o || {}); } catch (e) {} };
  this.fetch = function (opts) {
    return new Promise(function (resolve, reject) {
      var m = (opts.method || "GET").toLowerCase();
      $httpClient[m](opts, function (err, resp, body) {
        if (err) { reject(err); return; }
        resp.body = body;
        if (resp.statusCode === undefined) {
          resp.statusCode = resp.status !== undefined ? resp.status : 200;
        }
        resolve(resp);
      });
    });
  };
  this.notify = function (title, subtitle, body) {
    title = maskSecrets(title);
    subtitle = maskSecrets(subtitle);
    body = maskSecrets(body);
    try { $notification.post(title, subtitle, body); } catch (e) {}
  };
}
