/*
 * check-update.js · App 版本检查静音
 * ------------------------------------------------------------
 * 断言目标（与 sanitize 同一套 fenix 风格）：
 *   1. 只把 has_update（归一化）置 false，包络与其它字段零接触
 *   2. 无 has_update 键 → body 一个字节不动（skip=no-key）
 *   3. 非 JSON / 解析失败 → 原样放行（skip=not-json）
 *   4. gzip 形态：$utils.ungzip 解出 JSON 后同样生效
 *   5. 回写时删除过期的 content-encoding / content-length，其它头保留
 *   6. 诊断标记 X-Soda-Plugin 每个分支都在
 */
const src = require("./load-script")("check-update.js");

function run(body, opts) {
  opts = opts || {};
  let out = null;
  const logs = [];
  const utils = opts.ungzip
    ? { ungzip: () => opts.ungzip }
    : undefined;
  const fn = new Function(
    "$request", "$response", "$done", "console", "$argument", "$utils", src
  );
  fn(
    { url: opts.url || "https://beta-luna.douyin.com/luna/check-update" },
    { body: body, headers: opts.headers || { server: "stub", "content-length": "123" } },
    (v) => { out = v; },
    { log: (...a) => logs.push(a.join(" ")) },
    opts.argument !== undefined ? opts.argument : { debugLog: false },
    utils
  );
  return { out, logs };
}

let pass = 0, fail = 0;
function check(name, cond, extra) {
  if (cond) { pass++; console.log("  ok  " + name); }
  else { fail++; console.log("  FAIL " + name + (extra ? " :: " + extra : "")); }
}

function parse(out) {
  if (!out || out.body === undefined) return null;
  try { return JSON.parse(out.body); } catch (e) { return null; }
}

function marker(out) {
  if (!out || !out.headers) return "";
  return out.headers["X-Soda-Plugin"] || "";
}

console.log("\n[1] has_update 置 false / 深层嵌套 / 包络保留");
{
  const body = JSON.stringify({
    status_code: 0,
    status_info: "",
    has_update: true,
    data: { has_update: 1, media_result: { keep: "me" } }
  });
  const { out, logs } = run(body);
  const j = parse(out);
  check("returns body", !!j, JSON.stringify(out));
  check("top has_update=false", j.has_update === false, JSON.stringify(j));
  check("nested has_update=false", j.data.has_update === false);
  check("envelope untouched", j.status_code === 0 && j.status_info === "");
  check("media_result untouched", j.data.media_result.keep === "me");
  check("marker present", marker(out).indexOf("has_update=false") !== -1, marker(out));
  check("stale headers dropped",
    out.headers["content-length"] === undefined, JSON.stringify(out.headers));
  check("other headers kept", out.headers.server === "stub");
  check("log records change", logs.join(" ").indexOf("has_update") !== -1, logs.join(" | "));
}

console.log("\n[2] 同形键不误伤 / 无键放行");
{
  const body = JSON.stringify({
    check_update_info: { x: 1 },      // gecko bytesync 键（不应动）
    force_update_ts_ms: 42,           // 听歌房键（不应动）
    data: { version: "1.2.3" }        // 无 has_update → 不动
  });
  const { out } = run(body);
  /* 不带 body 的 $done = Loon 原样透传原始响应体 */
  check("no-key passthrough emits no body", out.body === undefined, JSON.stringify(out));
  check("no-key marker", marker(out).indexOf("skip=no-key") !== -1, marker(out));

  /* 改写路径下同形键必须原样保留 */
  const { out: rewritten } = run(JSON.stringify({
    check_update_info: { x: 1 },
    force_update_ts_ms: 42,
    data: { has_update: true }
  }));
  const j = parse(rewritten);
  check("same-shape keys untouched", j.check_update_info.x === 1 && j.force_update_ts_ms === 42,
    JSON.stringify(j));
  check("target flag still muted", j.data.has_update === false, JSON.stringify(j));
}

console.log("\n[3] 非 JSON / 解析失败放行");
{
  const { out } = run("this is not json at all");
  check("not-json no body", !out || out.body === undefined, JSON.stringify(out));
  check("not-json marker", marker(out).indexOf("skip=not-json") !== -1, marker(out));

  const { out: out2 } = run("{\"status_code\":0,");
  check("broken-json no body", !out2 || out2.body === undefined);
  check("broken-json marker", marker(out2).indexOf("skip=not-json") !== -1);
}

console.log("\n[4] gzip 形态 + boolean/string 值全量覆盖");
{
  const { out } = run("\u001f\u008bFAKEGZIP", {
    ungzip: new Uint8Array(Buffer.from(
      JSON.stringify({ data: { has_update: "true", hasUpdate: 1 } }), "utf8"))
  });
  const j = parse(out);
  check("ungzip path parsed", !!j, JSON.stringify(out));
  check("string true -> false", j.data.has_update === false);
  check("camelCase variant caught", j.data.hasUpdate === false);
  const { out: keep } = run(JSON.stringify({ data: { has_update: false } }));
  check("already false left alone",
    keep.body === JSON.stringify({ data: { has_update: false } }) || marker(keep).indexOf("no-key") !== -1,
    JSON.stringify(keep));
}

console.log("\n[5] DRY_RUN / ENABLED 快速回滚常量不进产物逻辑");
{
  check("source keeps ENABLED const", /\bENABLED\s*=/.test(src));
  check("source keeps DRY_RUN const", /\bDRY_RUN\s*=/.test(src));
}

console.log(`\nPASS=${pass} FAIL=${fail}`);
if (fail > 0) { console.log("FAILURES"); process.exit(1); }
console.log("ALL PASS");
