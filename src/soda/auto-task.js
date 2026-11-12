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
// 💎 本地权益注入（commerce_info 响应增强）
// ==========================================

/**
 * 注入 commerce_info 响应，解锁本地权益：
 * - 音质：lossless/spatial 从 svip 改为 free
 * - 会员：注入 membership_detail_map_v2 让 is_vip/is_svip/is_free_vip 全部 true
 * - 播放：延长 play_track.expire_time
 * - 下载：增加 download.quota
 * - 激励：标记任务完成
 *
 * 关键发现（HAR 实锤）：
 * upsell/variables 里的 is_vip/is_svip/is_free_vip/is_membership 全部从
 * commerce_info.membership.membership_detail_map_v2 计算。
 * quality_list 里 lossless/spatial 的 stage="svip" → 改为 "free" 即解锁。
 */
function injectCommerceInfo(responseBody) {
  try {
    const resp = typeof responseBody === "string" ? JSON.parse(responseBody) : responseBody;
    if (!resp || resp.status_code !== 0) return responseBody;

    const FAR_FUTURE = 4070908800; // 2099-01-01 00:00:00 UTC
    const changes = [];

    console.log(`[SodaAuto] 💎 commerce_info 响应 intercepted`);

    // 1. 音质权益解锁
    if (resp.benefit_base?.quality?.quality_list) {
      resp.benefit_base.quality.quality_list.forEach(q => {
        if (q.key === "lossless" || q.key === "spatial" || q.key === "hi_res") {
          if (q.stage !== "free") {
            changes.push(`quality.${q.key}:${q.stage}→free`);
            q.stage = "free";
          }
          q.expire_time = FAR_FUTURE;
        }
      });
      // 也更新 benefit_quality_map
      const bqm = resp.benefit_base.quality.benefit_quality_map || {};
      for (const key of Object.keys(bqm)) {
        if (key.includes("lossless") || key.includes("spatial") || key.includes("highest")) {
          bqm[key].end_time = FAR_FUTURE;
        }
      }
      resp.benefit_base.quality.max_level = 4; // 最高音质
    }

    // 2. 播放权益延长
    if (resp.benefit_base?.play_track) {
      resp.benefit_base.play_track.expire_time = FAR_FUTURE;
      changes.push("play_track.expire_time→2099");
    }

    // 3. 下载配额
    if (resp.benefit_base?.download) {
      resp.benefit_base.download.quota = 9999;
      changes.push("download.quota→9999");
    }

    // 4. 会员状态注入
    if (!resp.membership) resp.membership = {};
    resp.membership.expire_time = FAR_FUTURE;
    resp.membership.expire_time_max = FAR_FUTURE;
    resp.membership.membership_detail_map_v2 = {
      vip: {
        start_time: 0,
        expire_time: FAR_FUTURE,
        membership_type: "vip",
        is_valid: true,
      },
      svip: {
        start_time: 0,
        expire_time: FAR_FUTURE,
        membership_type: "svip",
        is_valid: true,
      },
      free_vip: {
        start_time: 0,
        expire_time: FAR_FUTURE,
        membership_type: "free_vip",
        is_valid: true,
      },
    };
    changes.push("membership→VIP/SVIP/FreeVIP");

    // 5. 激励任务标记完成
    if (resp.incentive) {
      if (resp.incentive.tasks && Array.isArray(resp.incentive.tasks)) {
        resp.incentive.tasks.forEach(task => {
          task.is_completed = true;
          if (task.stages && Array.isArray(task.stages)) {
            task.stages.forEach(stage => {
              stage.is_completed = true;
              if (stage.rewards && Array.isArray(stage.rewards)) {
                stage.rewards.forEach(reward => {
                  reward.claim_status = 1; // 已领取
                });
              }
            });
          }
        });
        changes.push(`incentive.tasks→completed(${resp.incentive.tasks.length})`);
      }
      // 播放权益
      if (resp.incentive.expire_time) {
        resp.incentive.expire_time = FAR_FUTURE;
      }
    }

    // 6. 播放权益（play_entitlements）
    if (resp.play_entitlements) {
      resp.play_entitlements.expire_at = FAR_FUTURE;
      if (resp.play_entitlements.reward_finished_task_info) {
        resp.play_entitlements.reward_finished_task_info.all_full = true;
        resp.play_entitlements.reward_finished_task_info.full_day = true;
      }
      changes.push("play_entitlements→unlocked");
    }

    // 7. 活动免费 VIP
    if (resp.activity_free_vip) {
      resp.activity_free_vip.end_date = "2099-01-01";
      resp.activity_free_vip.applied_cnt = 1;
      changes.push("activity_free_vip→extended");
    }

    // 8. 交易信息 - 标记有付费订单（防止弹窗提示开通）
    if (resp.trade) {
      resp.trade.has_paid_order = true;
      changes.push("trade.has_paid_order→true");
    }

    if (changes.length > 0) {
      console.log(`[SodaAuto] 💎 权益注入: ${changes.join(", ")}`);
    }

    return JSON.stringify(resp);
  } catch (e) {
    console.log(`[SodaAuto] ⚠️ commerce_info 注入失败: ${e.message}`);
    return responseBody;
  }
}

// ==========================================
// 🚫 Upsell 弹窗清空
// ==========================================

/**
 * 清空 upsell 响应中的弹窗和营销内容
 * 保留奖励相关字段（variables 里的权益表达式需要保留）
 */
function cleanUpsell(responseBody) {
  try {
    const resp = typeof responseBody === "string" ? JSON.parse(responseBody) : responseBody;
    if (!resp || resp.status_code !== 0) return responseBody;

    const changes = [];
    console.log(`[SodaAuto] 🚫 upsell 响应 intercepted`);

    // 清空弹窗配置
    if (resp.popup_config) {
      resp.popup_config.popup_frequency_control = { group_gap: 999999, time_interval: 999999 };
      changes.push("popup_config→disabled");
    }

    // 清空 scene_upsells_map 里的广告/营销弹窗
    const sceneMap = resp.scene_upsells_map || resp.sceneUpsellsMap || {};
    for (const scene of Object.keys(sceneMap)) {
      const candidates = sceneMap[scene]?.candidates || [];
      const before = candidates.length;
      let kept = null;
      for (let i = 0; i < before; i++) {
        const c = candidates[i];
        const name = c?.unique_name || c?.uniqueName || "";
        let retain = true;
        if (name.includes("reward") || name.includes("coin") || name.includes("treasure")) {
          retain = true;
        } else if (name.includes("ads") || name.includes("popup") || name.includes("commerce")) {
          retain = false;
        }
        if (!retain) {
          if (kept === null) kept = candidates.slice(0, i);
        } else if (kept !== null) {
          kept.push(c);
        }
      }
      if (kept !== null) {
        sceneMap[scene].candidates = kept;
        changes.push(`scene.${scene}:${before}→${kept.length}`);
      }
    }

    // 修改 variables 里的倒计时表达式，让权益永不过期
    if (resp.variables) {
      // 让 ad_reward_benefit_countdown 返回一个很大的值
      if (resp.variables.ad_reward_benefit_countdown) {
        resp.variables.ad_reward_benefit_countdown = "999999999999";
        changes.push("variables.countdown→extended");
      }
    }

    if (changes.length > 0) {
      console.log(`[SodaAuto] 🚫 Upsell清理: ${changes.join(", ")}`);
    }

    return JSON.stringify(resp);
  } catch (e) {
    console.log(`[SodaAuto] ⚠️ upsell 清理失败: ${e.message}`);
    return responseBody;
  }
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

function log(msg) {
  console.log(`[SodaAuto] ${msg}`);
}

const UTF8_DECODER = typeof TextDecoder !== "undefined" ? new TextDecoder("utf-8") : null;

function utf8(bytes) {
  if (UTF8_DECODER) {
    try {
      return UTF8_DECODER.decode(bytes);
    } catch (_) {}
  }
  let out = "", i = 0, n = bytes.length;
  while (i < n) {
    const b = bytes[i++] & 0xff;
    if (b < 0x80) {
      out += String.fromCharCode(b);
    } else if (b >= 0xc0 && b < 0xe0) {
      out += String.fromCharCode(((b & 0x1f) << 6) | (bytes[i++] & 0x3f));
    } else if (b >= 0xe0 && b < 0xf0) {
      out += String.fromCharCode(((b & 0x0f) << 12) | ((bytes[i++] & 0x3f) << 6) | (bytes[i++] & 0x3f));
    } else {
      const cp = ((b & 0x07) << 18) | ((bytes[i++] & 0x3f) << 12) | ((bytes[i++] & 0x3f) << 6) | (bytes[i++] & 0x3f);
      out += String.fromCodePoint(cp);
    }
  }
  return out;
}

function readBody(resp) {
  const raw = (resp && (resp.rawBytes !== undefined ? resp.rawBytes : resp.body)) || "";
  let bytes = null;
  if (typeof Uint8Array !== "undefined" && raw instanceof Uint8Array) {
    bytes = raw;
  } else if (ArrayBuffer.isView && ArrayBuffer.isView(raw)) {
    bytes = new Uint8Array(raw.buffer, raw.byteOffset, raw.byteLength);
  } else if (typeof ArrayBuffer !== "undefined" && raw instanceof ArrayBuffer) {
    bytes = new Uint8Array(raw);
  } else if (Array.isArray(raw)) {
    bytes = new Uint8Array(raw);
  } else if (typeof raw === "string" && raw.length > 1 &&
             raw.charCodeAt(0) === 0x1f && raw.charCodeAt(1) === 0x8b) {
    bytes = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i) & 0xff;
  } else {
    return typeof raw === "string" ? raw : "";
  }
  if (bytes.length > 1 && bytes[0] === 0x1f && bytes[1] === 0x8b) {
    try {
      if (typeof $utils !== "undefined" && $utils && typeof $utils.ungzip === "function") {
        const u = $utils.ungzip(bytes);
        if (typeof u === "string") return u;
        if (u && typeof u.length === "number") return utf8(u);
      }
    } catch (e) {
      log(`ungzip failed: ${e}`);
    }
  }
  return utf8(bytes);
}

function cleanResponseHeaders(headers) {
  try {
    const h = Object.assign({}, headers || {});
    for (const k of Object.keys(h)) {
      const lk = String(k).toLowerCase();
      if (lk === "content-encoding" || lk === "content-length") {
        delete h[k];
      }
    }
    return h;
  } catch (e) {
    return undefined;
  }
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

  // ---- Pangle 广告注入（已禁用 - 会导致网络错误） ----
  // 伪造的响应格式与真实 SDK 不兼容，导致 App 报网络错误
  // 广告拦截改由 [Host] 层的域名黑名单处理

  // ---- 签到注入（已禁用 - 需要更复杂的实现） ----
  // 简单的响应替换不足以绕过服务端校验

  // ---- 默认放行 ----
  $done({});
}

// ---- 响应阶段 ----
if (isResponse) {
  if (url.indexOf("/luna/") === -1) {
    $done({});
  } else {
    const body = readBody($response);

  // ---- incentive/done 响应观测（只记录，不修改） ----
  if (/\/+luna\/advert\/incentive\/done/.test(url)) {
    try {
      const data = typeof body === "string" ? JSON.parse(body) : body;
      if (data?.reward_details) {
        log(`📊 incentive/done: ${JSON.stringify(data.reward_details).substring(0, 100)}`);
      }
    } catch (e) {}
    $done({});
  }
  // ---- 激励配置观测 ----
  else if (/\/+luna\/advert\/incentive\/config/.test(url)) {
    cacheIncentiveConfig(body);
    $done({});
  }
  // ---- 💎 本地权益注入（commerce_info） ----
  else if (/\/+luna\/commerce\/v2\/commerce_info/.test(url)) {
    const injected = injectCommerceInfo(body);
    if (injected !== body) {
      $done({ body: injected, headers: cleanResponseHeaders($response?.headers) });
    } else {
      $done({});
    }
  }
  // ---- 🚫 Upsell 弹窗清空 ----
  else if (/\/+luna\/commerce\/v2\/upsell/.test(url) && !url.includes("sort_decision")) {
    const cleaned = cleanUpsell(body);
    if (cleaned !== body) {
      $done({ body: cleaned, headers: cleanResponseHeaders($response?.headers) });
    } else {
      $done({});
    }
  }
  // ---- 任务页面观测 ----
  else if (/\/+luna\/treasure\/task\/page\/v[0-9]+/.test(url)) {
    observeTaskPage(body);
    $done({});
  }
  // ---- 默认放行 ----
  else {
    $done({});
  }
  }
}
