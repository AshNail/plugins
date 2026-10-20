/*
 * SodaClean · 请求侧减负（Loon http-request 脚本）
 * ------------------------------------------------------------
 * 只做一件事：把激励广告配置 / 广告位配置请求里的 preload 关掉，
 * 让 App 不再主动预加载广告素材。
 *
 * 明确不碰：
 *   - advert_duration（广告时长声明）
 *   - advert_sources / feed_advert_config（广告源协商）
 *   - 任何与发奖、校验相关的字段
 *
 * 失败即放行：非 JSON、解析失败、异常 → 原样发请求。
 */

const VERBOSE = true;

/* ------------------------------------------------------------------ */
/* 工具                                                               */
/* ------------------------------------------------------------------ */
function normalizeKey(k) {
  return String(k).toLowerCase().replace(/[_-]/g, "");
}

function short(v) {
  try {
    const s = JSON.stringify(v);
    return s === undefined ? "undefined" : s.length > 48 ? s.slice(0, 48) + "…" : s;
  } catch (e) {
    return "<unserializable>";
  }
}

/* ------------------------------------------------------------------ */
/* 遍历：只关 preload                                                 */
/* ------------------------------------------------------------------ */
function walk(node, log, depth) {
  if (depth > 10 || !node || typeof node !== "object") return;

  if (Array.isArray(node)) {
    for (let i = 0; i < node.length; i++) walk(node[i], log, depth + 1);
    return;
  }

  for (const k of Object.keys(node)) {
    const nk = normalizeKey(k);
    const val = node[k];

    if (nk === "preload") {
      if (val === true) {
        log.push(k + " : true -> false");
        node[k] = false;
      } else if (typeof val === "number" && val !== 0) {
        log.push(k + " : " + val + " -> 0");
        node[k] = 0;
      }
      continue;
    }

    walk(val, log, depth + 1);
  }
}

/* ------------------------------------------------------------------ */
/* 主流程                                                             */
/* ------------------------------------------------------------------ */
(function main() {
  try {
    const url = ($request && $request.url) || "";
    const raw = ($request && $request.body) || "";

    const isIncentive = /\/luna\/advert\/incentive\/config/.test(url);
    const isAdsConfig = /\/luna\/ads\/config/.test(url);

    if (!isIncentive && !isAdsConfig) {
      return $done({});
    }

    const label = isIncentive ? "incentive-config" : "ads-config";

    if (typeof raw !== "string" || raw.length === 0) {
      return $done({});
    }

    const head = raw.trimStart().slice(0, 1);
    if (head !== "{") {
      // 非 JSON（protobuf / 压缩体），不动
      return $done({});
    }

    let obj;
    try {
      obj = JSON.parse(raw);
    } catch (e) {
      console.log("[soda-req] JSON parse failed, passthrough");
      return $done({});
    }

    const log = [];
    walk(obj, log, 0);

    if (log.length === 0) {
      console.log("[soda-req] " + label + " hit, preload already off");
      return $done({});
    }

    const out = JSON.stringify(obj);
    if (VERBOSE) {
      console.log("[soda-req] " + label + " | " + log.length + " change(s)\n  " + log.join("\n  "));
    }

    $done({ body: out });
  } catch (e) {
    console.log("[soda-req] error, passthrough: " + e);
    $done({});
  }
})();
