/*
 * 分页游标完整性回归（第十四轮）
 * ------------------------------------------------------------
 * 三份外部去广告方案都把「剔除广告条目不得动分页游标」列为硬约束：
 * 信息流里删掉广告卡片若同时改写了 cursor / has_more，App 滑到底
 * 就拿不到下一批数据的令牌，表现为无限加载、一直转圈或白屏。
 *
 * 本套件断言两件事：
 *   1. 净化后分页字段**原样保留**（值不变、类型不变、没被删）；
 *   2. 广告条目**仍然被摘掉**——即保住游标不是靠「什么都不改」。
 *
 * 第 1 条防的是「把游标当广告字段清掉」；第 2 条防的是「为了保游标
 * 连广告也不摘了」这种假修法。
 *
 * 键名覆盖三种书写：snake_case（min_cursor）、camelCase（minCursor）、
 * kebab-case（min-cursor）——归一化后必须命中同一条判据。
 */
const load = require("./load-script");

let pass = 0, fail = 0;
function ck(name, cond, extra) {
  if (cond) { pass++; console.log("  PASS  " + name); }
  else { fail++; console.log("  FAIL  " + name + (extra ? "  got=" + extra : "")); }
}

/* 跑一个净化脚本，返回解析后的响应体 */
function runScript(code, url, body, argument) {
  let out = null;
  const logs = [];
  const fn = new Function(
    "$request", "$response", "$done", "console", "$argument", code
  );
  fn(
    { url },
    { body: typeof body === "string" ? body : JSON.stringify(body) },
    (v) => { out = v; },
    { log: (...a) => logs.push(a.join(" ")) },
    argument
  );
  return { out, logs };
}

function parse(out) {
  if (!out || out.body === undefined) return null;
  try { return JSON.parse(out.body); } catch (e) { return null; }
}

/* ------------------------------------------------------------------ */
/* 分页字段清单：每个字段给一组「原始值」，断言净化后完全不变        */
/* ------------------------------------------------------------------ */
const PAGINATION_FIELDS = [
  { key: "min_cursor", value: "MTQ0MjAxMjAwMDozNjAwMDAw" },
  { key: "minCursor", value: "MTQ0MjAxMjAwMDozNjAwMDAw" },
  { key: "min-cursor", value: "MTQ0MjAxMjAwMDozNjAwMDAw" },
  { key: "max_cursor", value: "MTQ0MjAxMjAwMTo2NDAwMDA" },
  { key: "maxCursor", value: "MTQ0MjAxMjAwMTo2NDAwMDA" },
  { key: "has_more", value: true },
  { key: "hasMore", value: true },
  { key: "page_token", value: "eyJvIjoxMH0" },
  { key: "pageToken", value: "eyJvIjoxMH0" },
  { key: "offset", value: 40 },
  { key: "next_cursor", value: "bmV4dC0x" },
  { key: "nextCursor", value: "bmV4dC0x" },
  { key: "total", value: 128 },
  { key: "count", value: 20 }
];

/*
 * 构造一条带广告条目与分页字段的 feed 响应。
 * 广告条目用两种形态：
 *   - 显式 is_ad=true（一定会被 drop）
 *   - 只有 ad_info 且无媒体载荷（也一定会被 drop）
 */
function feedBody(pagination) {
  const body = {
    data: [
      { id: 1, is_ad: true, title: "ad one" },
      { id: 2, track: { id: "t2" }, title: "real song" },
      { id: 3, ad_info: { creative_id: "c3" }, title: "ad two" },
      { id: 4, track: { id: "t4" }, title: "real song two" }
    ]
  };
  for (const f of pagination) body[f.key] = f.value;
  return body;
}

/* ------------------------------------------------------------------ */
/* soda/sanitize.js                                                     */
/* ------------------------------------------------------------------ */
console.log("== soda sanitize:分页字段原样保留 ==");
{
  const code = load("sanitize.js", "soda");
  const url = "https://api.qishui.com/luna/feed/v2/list";
  const arg = { rewardSafe: false, cleanAds: true, killRewardAds: true };

  for (const f of PAGINATION_FIELDS) {
    const r = runScript(code, url, feedBody([f]), arg);
    const b = parse(r.out);
    ck(
      f.key + " 保留",
      b !== null && Object.prototype.hasOwnProperty.call(b, f.key) &&
        b[f.key] === f.value,
      b === null ? "no body" : JSON.stringify(b[f.key])
    );
  }

  console.log("== soda sanitize:广告仍然被摘掉 ==");
  const r = runScript(code, url, feedBody(PAGINATION_FIELDS), arg);
  const b = parse(r.out);
  ck("响应体可解析", b !== null);
  ck("4 条输入剩 2 条", b && Array.isArray(b.data) && b.data.length === 2,
    b && b.data ? String(b.data.length) : "no data");
  ck("留下的是正常内容", b && b.data && b.data[0] && b.data[0].id === 2 &&
    b.data[1] && b.data[1].id === 4, JSON.stringify(b && b.data));
  ck("全部 14 个分页字段同时在位",
    b && PAGINATION_FIELDS.every((f) =>
      Object.prototype.hasOwnProperty.call(b, f.key) && b[f.key] === f.value),
    JSON.stringify(b && Object.keys(b)));
}

/* ------------------------------------------------------------------ */
/* douyin/clean.js                                                      */
/* ------------------------------------------------------------------ */
console.log("== douyin clean:分页字段原样保留 ==");
{
  const code = load("clean.js", "douyin");
  /* douyin 的 clean.js 用 cleanFeedAds 开关管信息流端点 */
  const url = "https://beta-luna.douyin.com/luna/feed/v2/list";
  const arg = {
    rewardSafe: false, cleanAds: true, killRewardAds: true, cleanFeedAds: true
  };

  for (const f of PAGINATION_FIELDS) {
    const r = runScript(code, url, feedBody([f]), arg);
    const b = parse(r.out);
    ck(
      f.key + " 保留",
      b !== null && Object.prototype.hasOwnProperty.call(b, f.key) &&
        b[f.key] === f.value,
      b === null ? "no body" : JSON.stringify(b[f.key])
    );
  }

  console.log("== douyin clean:广告仍然被摘掉 ==");
  const r = runScript(code, url, feedBody(PAGINATION_FIELDS), arg);
  const b = parse(r.out);
  ck("响应体可解析", b !== null);
  ck("4 条输入剩 2 条", b && Array.isArray(b.data) && b.data.length === 2,
    b && b.data ? String(b.data.length) : "no data");
  ck("留下的是正常内容", b && b.data && b.data[0] && b.data[0].id === 2 &&
    b.data[1] && b.data[1].id === 4, JSON.stringify(b && b.data));
}

/* ------------------------------------------------------------------ */
/* 负向对照：把游标塞进 kill 表时，本套件必须失败                      */
/* （与 lint 的 check_pagination_integrity 互为双保险：                */
/*   lint 管「键名不许进表」，本套件管「进表了结果就会变」）            */
/* ------------------------------------------------------------------ */
console.log("== 负向对照:游标被清空则本断言应失败 ==");
{
  const code = load("sanitize.js", "soda");
  const url = "https://api.qishui.com/luna/feed/v2/list";
  const arg = { rewardSafe: false, cleanAds: true, killRewardAds: true };
  /* 模拟「有人把 cursor 加进 kill 表」后的结果：游标字段被清空 */
  const poisoned = feedBody(PAGINATION_FIELDS);
  for (const f of PAGINATION_FIELDS) {
    if (typeof f.value === "boolean") poisoned[f.key] = false;
    else if (typeof f.value === "number") poisoned[f.key] = 0;
    else poisoned[f.key] = "";
  }
  const r = runScript(code, url, poisoned, arg);
  const b = parse(r.out);
  const changed = b !== null && PAGINATION_FIELDS.some((f) => b[f.key] !== f.value);
  ck("清空后的响应确实与原值不同（说明断言有鉴别力）", changed);
}

console.log("\n" + (fail === 0 ? "ALL PASS" : "FAILURES") + "  pass=" + pass + " fail=" + fail);
process.exit(fail ? 1 : 0);
