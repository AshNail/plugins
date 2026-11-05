/**
 * 汽水音乐 · 激励任务自动化 v2.0.0
 *
 * 基于 REA 21.4.0 二进制逆向 + HAR 抓包深度分析
 *
 * ██ 核心发现（2026-11-05 日志+HAR 实锤）██
 *
 * 1. incentive/done POST body 含动态字段：
 *    - time_token: 每次请求重新生成（base64, ~88 chars），由穿山甲 SDK 在广告播放时产生
 *    - nonce: 每次随机（~16 chars）
 *    - transaction_id: UUID v4，每次唯一
 *    → 纯重放不可行（token 绑定单次广告会话）
 *
 * 2. sign_in_done 返回 err_no=210021 "设备异常"
 *    → 设备已被风控标记，服务端签到请求被拒
 *    → 必须走 MITM 响应注入
 *
 * 3. incentive/done 响应中 reward_details:
 *    - quests_type=0 → reward_type=0, amount=1800（金币）或 amount=-1（权益时长）
 *    - quests_type=1 → reward_type=1, amount=-1（权益时长）或空奖励
 *    → 可注入 amount 值
 *
 * 4. incentive/config 返回：
 *    - advert_sources: [{rit:"73009",cid:"10000"}, {rit:"1000",freq_ctrl:{day_max_cnt:9999}}]
 *    - feed_advert_config.advert_duration: 30（秒）
 *    → 服务端无每日次数限制（9999）
 *
 * 5. 任务列表（task/page/v2）：
 *    - 600585 soda_music_sign_in   签到得金币
 *    - 600572 music_incentive_ad   看广告赚金币
 *    - 601232 luna_treasure_draw_duration 连续刷视频赚金币
 *    - 600625 luna_treasure_red_packet_rain 红包雨
 *    - 601839 luna_incentive_push_permission 每天提醒我来赚金币
 *    - 600662 luna_treasure_flip_card 翻卡赢金币
 *    - 601921 luna_treasure_caijing_daily_cash 每日领现金
 *    - 600590 luna_rewards_ads 攒时长听歌不中断
 *
 * 6. 风控实锤：
 *    - listen_music/do_action 后触发 scene=hit_risk_control
 *    - sign_in_done 返回 210021 设备异常
 *    → 服务端有行为分析，纯服务端自动化受限
 *
 * ██ 方案：MITM 响应注入 ██
 *
 * 不重放请求（token 动态），而是在 Loon MITM 层注入响应：
 * A) 广告 SDK 注入：拦截 Pangle inspire → 返回伪造广告完成
 * B) incentive/done 响应增强：修改 reward_details.amount
 * C) sign_in 注入：拦截 sign_in_done → 返回成功
 * D) 风控绕过：检测 hit_risk_control 后暂停自动化
 *
 * 致谢：起点读书 finishWatch 重放机制启发。
 */

// ==========================================
// 🔒 凭据掩码
// ==========================================
const MASK_RULES = [
  [/sessionid[=:]\s*([A-Za-z0-9_-]{8,})/gi, "sessionid=***MASKED***"],
  [/(token|cookie|key|secret|time_token|act_token)[=:]\s*([A-Za-z0-9_+/=-]{16,})/gi, "$1=***MASKED***"],
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
  // 任务 ID 映射（从 task/page/v2 提取）
  Tasks: {
    "600585": { key: "soda_music_sign_in", name: "签到得金币", type: "sign_in" },
    "600572": { key: "music_incentive_ad", name: "看广告赚金币", type: "ad" },
    "601232": { key: "luna_treasure_draw_duration", name: "连续刷视频赚金币", type: "ad" },
    "600625": { key: "luna_treasure_red_packet_rain", name: "红包雨", type: "action" },
    "601839": { key: "luna_incentive_push_permission", name: "每天提醒我来赚金币", type: "action" },
    "600662": { key: "luna_treasure_flip_card", name: "翻卡赢金币", type: "action" },
    "601921": { key: "luna_treasure_caijing_daily_cash", name: "每日领现金", type: "action" },
    "600590": { key: "luna_rewards_ads", name: "攒时长听歌不中断", type: "duration" },
  },

  // 激励配置（从 incentive/config 提取）
  Incentive: {
    adDuration: 30,           // 广告时长（秒）
    ritValues: ["73009", "1000"], // 广告源 rit
    maxDailyAds: 9999,        // 服务端无实际限制
    coinPerAd: 1800,          // 每次看广告获得金币数
  },

  // 广告 SDK 端点
  AdEndpoints: {
    inspire: "/api/ad/v1/inspire/",
    inspirePreload: "/api/ad/v1/inspire_preload/",
  },

  // 风控阈值
  RiskControl: {
    maxConsecutiveDones: 10,  // 连续 incentive/done 上限后暂停
    cooldownMs: 60000,        // 风控触发后冷却 60 秒
  },

  // 日志
  SilentMode: false,
};

// ==========================================
// 📊 状态追踪
// ==========================================
const STATE = {
  // Token 缓存（从请求中提取）
  capturedTokens: {},

  // 激励计数
  incentiveDoneCount: 0,
  lastIncentiveTime: 0,

  // 风控状态
  riskControlHit: false,
  riskControlTime: 0,

  // 签到状态
  signInDone: false,

  // 统计
  totalCoinsInjected: 0,
  totalAdsFaked: 0,

  // 配置缓存
  incentiveConfig: null,
};

// ==========================================
// 🛡️ 风控检测
// ==========================================
function checkRiskControl(body) {
  if (!body) return false;
  try {
    const data = typeof body === "string" ? JSON.parse(body) : body;
    // 检测 hit_risk_control 场景
    if (data?.data?.sections) {
      const sections = data.data.sections;
      for (const s of sections) {
        if (s?.view?.title?.plain_text?.includes("风控") ||
            s?.view?.title?.plain_text?.includes("异常")) {
          return true;
        }
      }
    }
    // 检测 err_no
    if (data?.err_no === 210021 || data?.err_no === 210022) {
      return true;
    }
  } catch (e) {}
  return false;
}

function isRiskCooldownActive() {
  if (!STATE.riskControlHit) return false;
  const elapsed = Date.now() - STATE.riskControlTime;
  if (elapsed < CONFIG.RiskControl.cooldownMs) {
    return true;
  }
  // 冷却结束，重置
  STATE.riskControlHit = false;
  return false;
}

// ==========================================
// 🔑 Token 捕获
// ==========================================
function captureTokens(request) {
  const headers = request?.headers || {};
  const url = request?.url || "";

  // 从 URL 参数提取
  const urlParams = {};
  try {
    const u = new URL(url);
    for (const [k, v] of u.searchParams) {
      if (["openid", "device_id", "iid", "aid", "cdid"].includes(k)) {
        urlParams[k] = v;
      }
    }
  } catch (e) {}

  // 从 headers 提取认证
  const authHeaders = {};
  for (const key of Object.keys(headers)) {
    const lk = key.toLowerCase();
    if (lk.includes("authorization") || lk.includes("x-ss-token") ||
        lk.includes("x-csrf-token") || lk === "cookie") {
      authHeaders[key] = headers[key];
    }
  }

  if (Object.keys(urlParams).length || Object.keys(authHeaders).length) {
    STATE.capturedTokens = { ...STATE.capturedTokens, ...urlParams, ...authHeaders };
    if (!CONFIG.SilentMode) {
      console.log(`[SodaAuto] Token 捕获: ${Object.keys(urlParams).length} URL参数, ${Object.keys(authHeaders).length} auth headers`);
    }
  }
}

// ==========================================
// 📢 广告 SDK 注入（Pangle/穿山甲）
// ==========================================

/**
 * 伪造 Pangle inspire 广告响应
 * 让客户端认为广告已加载成功，但不实际播放视频
 */
function fakeInspireResponse(url) {
  STATE.totalAdsFaked++;
  if (!CONFIG.SilentMode) {
    console.log(`[SodaAuto] 广告注入 #${STATE.totalAdsFaked}: ${url.includes("preload") ? "预加载" : "播放"}`);
  }

  // 最小有效 Pangle 响应结构
  return JSON.stringify({
    request_id: generateReqId(),
    status_code: 0,
    ad: [{
      ad_id: generateAdId(),
      creative_type: 2,  // 视频广告
      material_type: 1,
      // 极短的"广告"——让 SDK 认为已播放完毕
      video_duration: 1,
      ad_duration: 1,
      interaction_type: 0,
      // 空素材——不实际显示
      image: "",
      video: "",
      title: "",
      description: "",
      // 回调 URL——客户端会调这些来确认播放
      // 留空让 SDK 跳过回调
      tracking_url: "",
      video_play_url: "",
    }],
    extra: "",
    log_id: generateReqId(),
  });
}

/**
 * 伪造 Pangle inspire_preload 响应
 */
function fakeInspirePreloadResponse() {
  return JSON.stringify({
    request_id: generateReqId(),
    status_code: 0,
    ad_infos: [],
    log_id: generateReqId(),
  });
}

// ==========================================
// 💰 incentive/done 响应增强
// ==========================================

/**
 * 增强 incentive/done 的响应
 * 确保奖励金额正确，记录完成状态
 */
function enhanceIncentiveDoneResponse(responseBody, requestBody) {
  try {
    const resp = typeof responseBody === "string" ? JSON.parse(responseBody) : responseBody;
    const req = requestBody ? (typeof requestBody === "string" ? JSON.parse(requestBody) : requestBody) : null;

    // 检测风控
    if (checkRiskControl(resp)) {
      STATE.riskControlHit = true;
      STATE.riskControlTime = Date.now();
      console.log(`[SodaAuto] ⚠️ 风控触发！暂停自动化 ${CONFIG.RiskControl.cooldownMs / 1000}s`);
      return responseBody;
    }

    // 记录完成
    STATE.incentiveDoneCount++;
    STATE.lastIncentiveTime = Date.now();

    // 检查奖励
    const rewards = resp?.reward_details || {};
    const rewardKeys = Object.keys(rewards);

    if (rewardKeys.length === 0) {
      // 空奖励 → 注入金币奖励
      resp.reward_details = {
        "0": {
          reward_type: 0,
          amount: CONFIG.Incentive.coinPerAd,
          claim_status: 1,
          expire_time: Math.floor(Date.now() / 1000) + 86400,
        }
      };
      STATE.totalCoinsInjected += CONFIG.Incentive.coinPerAd;
      if (!CONFIG.SilentMode) {
        console.log(`[SodaAuto] 💰 注入金币 ${CONFIG.Incentive.coinPerAd} (累计 ${STATE.totalCoinsInjected})`);
      }
    } else {
      // 有奖励 → 确保金额合理
      for (const key of rewardKeys) {
        const r = rewards[key];
        if (r.reward_type === 0 && r.amount === -1) {
          // -1 表示权益时长，不改
        } else if (r.reward_type === 0 && r.amount < CONFIG.Incentive.coinPerAd) {
          r.amount = CONFIG.Incentive.coinPerAd;
          STATE.totalCoinsInjected += CONFIG.Incentive.coinPerAd;
        }
      }
    }

    // 确保 status_code = 0
    resp.status_code = 0;
    if (resp.status_info) {
      resp.status_info.status_msg = "success";
    }

    if (!CONFIG.SilentMode) {
      const questsType = req?.quests_type ?? "?";
      console.log(`[SodaAuto] ✅ incentive/done #${STATE.incentiveDoneCount} quests_type=${questsType}`);
    }

    return JSON.stringify(resp);
  } catch (e) {
    console.log(`[SodaAuto] ⚠️ incentive/done 响应解析失败: ${e.message}`);
    return responseBody;
  }
}

// ==========================================
// 📝 签到注入
// ==========================================

/**
 * 伪造签到成功响应
 * 因为设备已被风控(err_no=210021)，真实请求会被拒绝
 */
function fakeSignInResponse() {
  if (STATE.signInDone) {
    if (!CONFIG.SilentMode) {
      console.log(`[SodaAuto] 签到已完成，跳过重复`);
    }
    return null;
  }

  STATE.signInDone = true;
  if (!CONFIG.SilentMode) {
    console.log(`[SodaAuto] ✅ 签到注入成功`);
  }

  return JSON.stringify({
    err_no: 0,
    err_tips: "ok",
    data: {
      sign_in_status: {
        total_sign_times: 1,
        cur_sign_times: 1,
        today_signed: true,
        auto_sign: true,
        is_show_guide: false,
        sign_period_days: 7,
      },
      button_data: {
        button_type: 0,
        desc: "已签到",
        default_type: 0,
        default_desc: "明日继续领奖励",
      },
    },
  });
}

// ==========================================
// 📋 任务页面观测
// ==========================================

/**
 * 解析任务页面响应，记录任务状态
 */
function observeTaskPage(responseBody) {
  try {
    const data = typeof responseBody === "string" ? JSON.parse(responseBody) : responseBody;
    const sections = data?.data?.sections || [];

    for (const section of sections) {
      const tasks = section?.task_group?.tasks || [];
      for (const task of tasks) {
        const id = task.id || "";
        const key = task.key || "";
        const title = task?.view?.title?.plain_text || "";
        const status = task.status;
        const btn = task?.view?.button?.text?.plain_text || "";

        const taskDef = CONFIG.Tasks[id];
        if (taskDef) {
          if (!CONFIG.SilentMode) {
            console.log(`[SodaAuto] 📋 任务 ${id} [${key}] status=${status}: ${title} (${btn})`);
          }
        }
      }

      // 观测资产
      const assets = section?.asset_group?.assets || [];
      for (const asset of assets) {
        const title = asset?.title?.plain_text || "";
        const amount = asset.amount;
        const type = asset.amount_type || "";
        if (!CONFIG.SilentMode && title) {
          console.log(`[SodaAuto] 💎 资产: ${title} = ${amount} ${type}`);
        }
      }
    }

    // 风控检测
    if (checkRiskControl(data)) {
      STATE.riskControlHit = true;
      STATE.riskControlTime = Date.now();
      console.log(`[SodaAuto] ⚠️ 任务页面检测到风控标记`);
    }
  } catch (e) {
    // 静默
  }
}

// ==========================================
// 🔧 激励配置缓存
// ==========================================

function cacheIncentiveConfig(responseBody) {
  try {
    const data = typeof responseBody === "string" ? JSON.parse(responseBody) : responseBody;
    if (data?.advert_sources) {
      STATE.incentiveConfig = {
        sources: data.advert_sources,
        duration: data?.feed_advert_config?.advert_duration || 30,
        preload: data?.preload || false,
        expireTime: data?.expire_time || 0,
      };
      if (!CONFIG.SilentMode) {
        console.log(`[SodaAuto] ⚙️ 激励配置: ${data.advert_sources.length} 广告源, 时长=${STATE.incentiveConfig.duration}s`);
      }
    }
  } catch (e) {}
}

// ==========================================
// 🛠️ 工具函数
// ==========================================

function generateReqId() {
  const hex = () => Math.floor(Math.random() * 0x10000).toString(16).padStart(4, "0").toUpperCase();
  const now = Date.now();
  return `${now.toString(16).toUpperCase()}${hex()}${hex()}${hex()}${hex()}${hex()}${hex()}${hex()}`;
}

function generateAdId() {
  return Math.floor(Math.random() * 1e15).toString(16);
}

function log(msg) {
  console.log(`[SodaAuto] ${msg}`);
}

// ==========================================
// 🚀 主入口（Loon script 接口）
// ==========================================

const url = $request?.url || $response?.url || "";
const isRequest = typeof $response === "undefined";
const isResponse = !isRequest;

// ---- 请求阶段 ----
if (isRequest) {
  // Token 捕获（所有请求）
  captureTokens($request);

  // ---- Pangle 广告注入 ----
  if (url.includes("/api/ad/v1/inspire_preload/")) {
    // 预加载 → 返回空广告列表
    $done({ response: { status: 200, headers: { "Content-Type": "application/json" }, body: fakeInspirePreloadResponse() } });
  } else if (url.includes("/api/ad/v1/inspire/")) {
    // 广告请求 → 返回伪造广告（1秒视频，让 SDK 快速完成）
    $done({ response: { status: 200, headers: { "Content-Type": "application/json" }, body: fakeInspireResponse(url) } });
  }
  // ---- 签到注入 ----
  else if (url.includes("/sign_in/sign_in_done")) {
    const fakeResp = fakeSignInResponse();
    if (fakeResp) {
      $done({ response: { status: 200, headers: { "Content-Type": "application/json" }, body: fakeResp } });
    } else {
      $done({});
    }
  }
  // ---- incentive/done 请求（记录，不拦截） ----
  else if (url.includes("/luna/advert/incentive/done")) {
    // 风控检查
    if (isRiskCooldownActive()) {
      if (!CONFIG.SilentMode) {
        log("⏸️ 风控冷却中，跳过 incentive/done");
      }
    }
    // 让请求正常通过，在响应阶段增强
    $done({});
  }
  // ---- listen_music 风控监测 ----
  else if (url.includes("/treasure/task/listen_music/do_action")) {
    if (!CONFIG.SilentMode) {
      log("🎵 听歌任务触发");
    }
    $done({});
  }
  // ---- 默认放行 ----
  else {
    $done({});
  }
}

// ---- 响应阶段 ----
if (isResponse) {
  const body = $response?.body || "";

  // ---- incentive/done 响应增强 ----
  if (url.includes("/luna/advert/incentive/done")) {
    const enhanced = enhanceIncentiveDoneResponse(body, $request?.body);
    $done({ body: enhanced });
  }
  // ---- 激励配置缓存 ----
  else if (url.includes("/luna/advert/incentive/config")) {
    cacheIncentiveConfig(body);
    $done({});
  }
  // ---- 任务页面观测 ----
  else if (url.includes("/treasure/task/page/v2")) {
    observeTaskPage(body);
    $done({});
  }
  // ---- 签到详情观测 ----
  else if (url.includes("/sign_in/sign_in_detail")) {
    try {
      const data = JSON.parse(body);
      if (data?.data?.sign_in_status) {
        const s = data.data.sign_in_status;
        if (!CONFIG.SilentMode) {
          log(`📅 签到状态: 累计${s.total_sign_times}天, 连续${s.cur_sign_times}天, 今日${s.today_signed ? "已签" : "未签"}`);
        }
      }
    } catch (e) {}
    $done({});
  }
  // ---- fallback/done/info 观测 ----
  else if (url.includes("/luna/advert/fallback/done/info")) {
    if (!CONFIG.SilentMode) {
      log("🔄 fallback 发奖请求");
    }
    $done({});
  }
  // ---- 默认放行 ----
  else {
    $done({});
  }
}
