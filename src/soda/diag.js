/*
 * 汽水音乐 · 响应诊断脚本（Loon）
 * ------------------------------------------------------------
 * 作用：
 *   1. 把命中接口的 URL / 状态码 / 响应体写进 Loon 日志
 *   2. 对 JSON 响应额外输出"结构摘要"（键名 + 类型），便于快速找开关
 *   3. 不改写任何响应，纯观察
 *
 * 用法：
 *   安装插件后打开 Loon → 日志，搜索 [soda-diag]
 *   触发对应页面（福利页 / 开屏 / 金币任务），即可看到响应
 *
 * 注意：
 *   - 部分接口是 protobuf / 二进制，脚本会标记为 non-text 并跳过
 *   - 输出做了截断，避免日志爆炸
 *   - 稳定后请在 .plugin 里注释掉 [Script] 段
 */

const MAX_RAW = 4000;   // 原始响应最多打印多少字符
const MAX_KEYS = 40;    // 每个对象最多列出多少键

function safeJson(text) {
  try {
    return JSON.parse(text);
  } catch (e) {
    return null;
  }
}

// 生成结构摘要：{ key: "string(12)" | "array[3]" | "object" | ... }
function shapeOf(v, depth) {
  if (depth > 4) return "...";
  if (v === null) return "null";
  if (Array.isArray(v)) {
    if (v.length === 0) return "array[0]";
    return "array[" + v.length + "](" + shapeOf(v[0], depth + 1) + ")";
  }
  const t = typeof v;
  if (t === "object") {
    const keys = Object.keys(v);
    const parts = [];
    for (let i = 0; i < keys.length && i < MAX_KEYS; i++) {
      const k = keys[i];
      parts.push(k + ":" + shapeOf(v[k], depth + 1));
    }
    if (keys.length > MAX_KEYS) parts.push("...+" + (keys.length - MAX_KEYS));
    return "{" + parts.join(", ") + "}";
  }
  if (t === "string") {
    const s = v.length > 24 ? v.slice(0, 24) + "…" : v;
    return "string(" + v.length + ")=\"" + s + "\"";
  }
  return t + "(" + String(v) + ")";
}

const url = ($request && $request.url) || "";
const method = ($request && $request.method) || "";
const status = ($response && $response.status) || 0;
const raw = ($response && $response.body) || "";

let body = raw;
if (typeof body !== "string") {
  // 某些实现下 body 可能是 Uint8Array
  try {
    body = String.fromCharCode.apply(null, body);
  } catch (e) {
    body = "";
  }
}

const isText = /^[\x09\x0a\x0d\x20-\x7e\u00a0-\uffff]*$/.test(body.slice(0, 400));

console.log("\n[soda-diag] " + method + " " + status + " " + url);

if (!isText) {
  console.log("[soda-diag] non-text body, length=" + body.length + " (可能是 protobuf/压缩体，跳过)");
} else {
  const json = safeJson(body);
  if (json) {
    console.log("[soda-diag] JSON shape: " + shapeOf(json, 0));
    const pretty = JSON.stringify(json, null, 2);
    console.log(
      "[soda-diag] body:\n" +
        (pretty.length > MAX_RAW ? pretty.slice(0, MAX_RAW) + "\n...[truncated]" : pretty)
    );
  } else {
    console.log(
      "[soda-diag] text body:\n" +
        (body.length > MAX_RAW ? body.slice(0, MAX_RAW) + "\n...[truncated]" : body)
    );
  }
}

// 原样放行，不做任何修改
$done({});
