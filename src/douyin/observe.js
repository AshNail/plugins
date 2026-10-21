/*
 * douyin · 激励链路只读观测（Loon http-response 脚本）
 * ------------------------------------------------------------
 * 只写日志，不改写响应。用于回答：
 *   - 福利页现在到底下发了哪些分区/任务
 *   - 广告素材的时长、交互、组件参数是什么
 *   - 激励广告源、频控、预拉取配置
 *   - 商业化弹窗里有哪些广告/商城入口
 *   - 发奖接口返回了什么
 *
 * 隐私：不打印 token / sign / device_id / 用户 id / 素材完整 URL；
 * 按钮 schema 里的 luckydog_task_token 会被抹掉。
 */

function maskUrl(u) {
  return String(u || "")
    .replace(/(luckydog_task_token=)[^&]*/g, "$1***")
    .replace(/([?&](token|sign|device_id|iid|cdid|openid)=)[^&]*/g, "$1***")
    .slice(0, 220);
}

function short(v, n) {
  const s = String(v === undefined || v === null ? "" : v);
  return s.length > n ? s.slice(0, n) + "…" : s;
}

function isPlainObject(v) {
  return !!v && typeof v === "object" && !Array.isArray(v);
}

function plainText(v) {
  if (typeof v === "string") return v;
  if (isPlainObject(v)) {
    if (typeof v.plain_text === "string") return v.plain_text;
    if (isPlainObject(v.text)) return plainText(v.text);
  }
  return "";
}

function observeTreasure(obj) {
  const data = obj && obj.data;
  if (!isPlainObject(data) || !Array.isArray(data.sections)) return;
  const lines = [];
  for (const section of data.sections) {
    if (!isPlainObject(section)) continue;
    const group = section.task_group || section.widget_task_group;
    const tasks = isPlainObject(group) && Array.isArray(group.tasks) ? group.tasks : [];
    lines.push("section " + section.key + " : " + tasks.length + " task(s)");
    for (const task of tasks) {
      if (!isPlainObject(task)) continue;
      const view = isPlainObject(task.view) ? task.view : {};
      const button = isPlainObject(view.button) ? view.button : {};
      lines.push(
        "  - " + task.key + " id=" + task.id +
        " type=" + (task.type || "-") +
        " status=" + task.status +
        " can_show=" + task.can_show +
        " title=" + short(plainText(view.title), 24) +
        " btn=" + short(plainText(button.text), 12)
      );
      if (button.schema) lines.push("      schema: " + maskUrl(button.schema));
      if (isPlainObject(task.stats)) {
        const st = task.stats;
        lines.push(
          "      stats: total=" + (st.total_times === undefined ? "-" : st.total_times) +
          " done=" + (st.completed_times === undefined ? "-" : st.completed_times) +
          " last_rewarded=" + (st.last_rewarded_time === undefined ? "-" : st.last_rewarded_time)
        );
      }
    }
  }
  const cfg = isPlainObject(data.config) ? data.config : null;
  if (cfg && isPlainObject(cfg.ad_api_preload)) {
    const ids = Array.isArray(cfg.ad_api_preload.task_ids) ? cfg.ad_api_preload.task_ids : [];
    lines.push("ad_api_preload: preload=" + cfg.ad_api_preload.preload +
      " task_ids=" + ids.join(","));
  }
  console.log("[douyin-reward] treasure page\n  " + lines.join("\n  "));
}

function observeIncentiveConfig(obj) {
  const sources = Array.isArray(obj.advert_sources) ? obj.advert_sources : [];
  const lines = [];
  for (const s of sources) {
    if (!isPlainObject(s)) continue;
    lines.push("source type=" + s.type + " rit=" + s.rit + " cid=" + s.cid +
      (isPlainObject(s.freq_ctrl)
        ? " freq_ctrl=" + JSON.stringify(s.freq_ctrl)
        : ""));
  }
  const feed = isPlainObject(obj.feed_advert_config) ? obj.feed_advert_config : {};
  lines.push("feed_advert_config: " + JSON.stringify(feed));
  lines.push("preload=" + obj.preload + " vids=" +
    (Array.isArray(obj.vids) ? obj.vids.length : 0));
  console.log("[douyin-reward] incentive/config\n  " + lines.join("\n  "));
}

function observeIncentiveRetrieve(obj) {
  const map = isPlainObject(obj.ad_infos_map) ? obj.ad_infos_map : {};
  const lines = [];
  for (const slot of Object.keys(map)) {
    const group = map[slot];
    const list = isPlainObject(group) && Array.isArray(group.ad_infos) ? group.ad_infos : [];
    lines.push("slot " + slot + " : " + list.length + " creative(s)");
    for (const info of list) {
      if (!isPlainObject(info)) continue;
      const ci = isPlainObject(info.creative_info) ? info.creative_info : {};
      const vl = Array.isArray(ci.video_list) ? ci.video_list : [];
      lines.push(
        "  - launch_duration=" + info.launch_duration +
        " launch_period=" + info.launch_period +
        " interaction=" + JSON.stringify(info.interaction_info || {}) +
        " component=" + JSON.stringify(info.component || {}) +
        " videos=" + vl.length
      );
    }
  }
  console.log("[douyin-reward] incentive/retrieve\n  " + lines.join("\n  "));
}

function observeUpsell(obj) {
  const map = isPlainObject(obj.upsell_map) ? obj.upsell_map : {};
  const names = Object.keys(map);
  const adNames = names.filter(function (n) { return /ads|_ad$|^ad_/.test(n); });
  const mallNames = names.filter(function (n) { return n.indexOf("mall") !== -1; });
  const lines = [];
  lines.push("upsell_map: " + names.length + " popup(s)");
  lines.push("ad popups: " + (adNames.length ? adNames.join(",") : "-"));
  lines.push("mall popups: " + (mallNames.length ? mallNames.join(",") : "-"));
  const vars = isPlainObject(obj.variables) ? obj.variables : {};
  const adsVars = Object.keys(vars).filter(function (k) { return k.indexOf("ads") === 0; });
  lines.push("ads_* variables: " + (adsVars.length ? adsVars.join(",") : "-"));
  console.log("[douyin-reward] upsell\n  " + lines.join("\n  "));
}

function observeIncentiveDone(obj) {
  const details = isPlainObject(obj.reward_details) ? obj.reward_details : {};
  const lines = [];
  for (const k of Object.keys(details)) {
    const d = isPlainObject(details[k]) ? details[k] : {};
    lines.push("reward[" + k + "]: type=" + d.reward_type + " amount=" + d.amount +
      " claim_status=" + d.claim_status);
  }
  console.log("[douyin-reward] incentive/done\n  " + (lines.join("\n  ") || "-"));
}

/* 兜底凭证：只打印字段名，不打印 time_token / nonce 的值 */
function observeFallback(obj) {
  const raw = obj.post_done_extra;
  let keys = "-";
  if (typeof raw === "string") {
    try {
      keys = Object.keys(JSON.parse(raw)).join(",");
    } catch (e) {
      keys = "(not json)";
    }
  } else if (isPlainObject(raw)) {
    keys = Object.keys(raw).join(",");
  }
  console.log("[douyin-reward] fallback/done/info : post_done_extra keys = " + keys);
}

/* 信息流/广告位广告容器计数 */
function observeFeedAds(obj) {
  const lines = [];
  const containers = ["ads", "ads_info", "adsInfo", "ad_infos", "ad_infos_map",
                      "ad_info", "ad_data", "adConfig", "ad_unit_configs"];
  for (const key of containers) {
    const v = obj[key];
    if (v === undefined || v === null) continue;
    lines.push(key + " = " + (Array.isArray(v) ? "[" + v.length + "]" :
      isPlainObject(v) ? "{" + Object.keys(v).length + "}" : typeof v));
  }
  console.log("[douyin-reward] feed ads config\n  " + (lines.join("\n  ") || "-"));
}

/*
 * 穿山甲（CSJ）广告平台：广告配置 + 领奖回调
 * 取证 2026-10-20 HAR 384：
 *   ad.zijieapi.com/api/ad/v1/inspire/            广告配置（effective_play_time 等）
 *   ad.zijieapi.com/api/incentive/marketing/done   领奖回调（2026-10-20 实测返回 403 设备异常）
 *   ads5-normal-hl.zijieapi.com/api/ad/splash/luna/v15/  开屏广告配置
 */
function observeAdPlatform(obj, url) {
  const lines = [];
  if (/\/api\/incentive\/marketing\/done/.test(url)) {
    const code = obj.code === undefined ? obj.status_code : obj.code;
    const msg = obj.msg || obj.message || obj.err_tips || obj.status_msg || "";
    lines.push("marketing/done -> code=" + code + " msg=" + msg);
    const toast = obj.data && obj.data.toast ? obj.data.toast : "";
    if (toast) lines.push("  toast: " + toast);
    console.log("[douyin-reward] 广告平台领奖回调\n  " + lines.join("\n  "));
    return;
  }
  if (/\/api\/ad\/splash\//.test(url)) {
    lines.push("开屏广告配置(CSJ) keys: " + Object.keys(obj).slice(0, 12).join(","));
    console.log("[douyin-reward] 开屏广告请求\n  " + lines.join("\n  "));
    return;
  }
  const items = Array.isArray(obj.ad_item) ? obj.ad_item : [];
  lines.push("ad_item: " + items.length);
  for (const item of items) {
    if (!item || typeof item !== "object") continue;
    const ad = isPlainObject(item.ad_data) ? item.ad_data : {};
    lines.push("  ad_id=" + ad.ad_id + " source_type=" + ad.ad_source_type +
      " effective_play_time=" + ad.effective_play_time +
      " is_hide_time_stamp=" + ad.is_hide_time_stamp +
      " display_after=" + ad.display_after +
      " ad_coin_cool_sec=" + ad.ad_coin_cool_sec +
      " button_text=" + ad.button_text +
      " expire_timestamp=" + ad.expire_timestamp);
  }
  console.log("[douyin-reward] 广告平台广告配置\n  " + lines.join("\n  "));
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
      return $done({});
    }

    if (/\/luna\/treasure\/task\/page\/v2/.test(url)) observeTreasure(obj);
    else if (/\/luna\/advert\/incentive\/config/.test(url)) observeIncentiveConfig(obj);
    else if (/\/luna\/advert\/incentive\/retrieve/.test(url)) observeIncentiveRetrieve(obj);
    else if (/\/luna\/advert\/incentive\/done/.test(url)) observeIncentiveDone(obj);
    else if (/\/luna\/advert\/fallback\/done\/info/.test(url)) observeFallback(obj);
    else if (/\/luna\/ads\/(?:config|dsp\/retrieve)/.test(url)) observeFeedAds(obj);
    else if (/\/luna\/commerce\/v2\/upsell/.test(url)) observeUpsell(obj);
    else if (/zijieapi\.com\/(?:api\/ad\/|api\/incentive\/marketing\/done)/.test(url)) {
      observeAdPlatform(obj, url);
    } else return $done({});

    $done({});
  } catch (e) {
    console.log("[douyin-reward] error: " + e);
    $done({});
  }
})();
