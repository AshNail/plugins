/*
 * qidian/auto-task.js · 响应净化的 gzip / 二进制体回归（v3.5.1）
 * ------------------------------------------------------------
 * 2026-11-06 16:21:50 真机日志：起点净化脚本 match/Trigger/Finished 一应俱全、getconf 0ms 结束，
 * 却一个字段没改。根因是 safeJsonParse：
 *   · 绑定没带 binary_body_mode，gzip 字节被按 UTF-8 解成字符串，1f 8b 魔数检测失效；
 *   · $utils.ungzip 官方签名是 Uint8Array → Uint8Array，旧代码对返回值直接 JSON.parse。
 * 断言：
 *   1. Uint8Array 的 gzip 体 + ungzip 返回 Uint8Array → getconf 被真的改写
 *   2. 改写后的响应头删掉过期的 content-encoding / content-length
 *   3. Uint8Array 明文字节（Loon 已替脚本解压）同样生效
 *   4. 字符串明文同样生效
 *   5. ungzip 缺失（Build < 988）→ 静默透传，不抛、不改 body
 *   6. ungzip 返回字符串的宽松实现同样可用
 *   7. deeplink 只清 ActionUrl，其余业务字段保留
 */
const zlib = require("zlib");
const src = require("./load-script")("auto-task.js", "qidian");

function run(url, body, opts) {
  opts = opts || {};
  return new Promise((resolve) => {
    let out;
    const logs = [];
    const done = (v) => { out = v === undefined ? {} : v; resolve({ out, logs }); };
    const fn = new Function(
      "$request", "$response", "$done", "console", "$argument", "$utils",
      "$persistentStore", "$notification", "$httpClient", src
    );
    fn(
      { url, method: "GET", headers: {} },
      { body, headers: opts.headers || { "content-encoding": "gzip", "content-length": "99", server: "stub" } },
      done,
      { log: (...a) => logs.push(a.join(" ")) },
      { debugLog: "false", cleanAds: "true", autoTask: "false" },
      opts.utils,
      { read: () => null, write: () => true },
      { post: () => {} },
      {}
    );
    setTimeout(() => resolve({ out: out === undefined ? { __timeout: true } : out, logs }), 1500);
  });
}

let pass = 0, fail = 0;
function check(name, cond, extra) {
  if (cond) { pass++; console.log("  ok  " + name); }
  else { fail++; console.log("  FAIL " + name + (extra ? " :: " + extra : "")); }
}

const GETCONF = "https://magev6.if.qidian.com/argus/api/v1/client/getconf";
const conf = {
  Result: 0,
  Data: {
    PangleEnable: "1",
    SplashScreenInterval: 30,
    ActivityIcon: { a: 1 },
    GDT: { b: 2 },
    NewFeedsDiscover: 1,
    KeepMe: "yes",
    CloudSetting: { TeenShowFreq: "3" },
  },
};
const text = JSON.stringify(conf);
const gz = new Uint8Array(zlib.gzipSync(Buffer.from(text, "utf8")));
const realUtils = {
  ungzip: (bytes) => new Uint8Array(zlib.gunzipSync(Buffer.from(bytes))),
};

function parse(out) {
  if (!out || out.body === undefined) return null;
  try { return JSON.parse(out.body); } catch (e) { return null; }
}

(async () => {
  console.log("\n[1] gzip 字节体 + ungzip→Uint8Array");
  {
    const { out } = await run(GETCONF, gz, { utils: realUtils });
    const j = parse(out);
    check("getconf 返回了改写后的 body", !!j, JSON.stringify(out).slice(0, 120));
    check("PangleEnable 被覆写为 0", j && j.Data.PangleEnable === "0", j && JSON.stringify(j.Data));
    check("ActivityIcon / GDT 被删除", j && j.Data.ActivityIcon === undefined && j.Data.GDT === undefined);
    check("NewFeedsDiscover 置 0", j && j.Data.NewFeedsDiscover === 0);
    check("TeenShowFreq 置 \"0\"", j && j.Data.CloudSetting.TeenShowFreq === "0");
    check("非广告字段保留", j && j.Data.KeepMe === "yes");
    const h = (out && out.headers) || {};
    check("过期的 content-encoding / content-length 已删",
      h["content-encoding"] === undefined && h["content-length"] === undefined, JSON.stringify(h));
    check("其它响应头保留", h.server === "stub");
  }

  console.log("\n[2] Uint8Array 明文字节（Loon 已解压）");
  {
    const bytes = new Uint8Array(Buffer.from(text, "utf8"));
    const { out } = await run(GETCONF, bytes, { utils: realUtils, headers: { server: "stub" } });
    const j = parse(out);
    check("明文字节也被净化", j && j.Data.PangleEnable === "0", JSON.stringify(out).slice(0, 120));
  }

  console.log("\n[3] 字符串明文");
  {
    const { out } = await run(GETCONF, text, { utils: realUtils, headers: { server: "stub" } });
    const j = parse(out);
    check("字符串明文被净化", j && j.Data.PangleEnable === "0");
  }

  console.log("\n[4] ungzip 缺失（Build < 988）→ 静默透传");
  {
    const { out } = await run(GETCONF, gz, { utils: undefined });
    check("不抛、不带改写 body", out && out.body === undefined && !out.__timeout, JSON.stringify(out).slice(0, 120));
  }

  console.log("\n[5] ungzip 返回字符串的宽松实现");
  {
    const loose = { ungzip: (b) => zlib.gunzipSync(Buffer.from(b)).toString("utf8") };
    const { out } = await run(GETCONF, gz, { utils: loose });
    const j = parse(out);
    check("返回字符串同样可用", j && j.Data.PangleEnable === "0");
  }

  console.log("\n[6] deeplink 只清 ActionUrl");
  {
    const body = JSON.stringify({ Result: 0, Data: { ActionUrl: "QDReader://x", Keep: 7 } });
    const g = new Uint8Array(zlib.gzipSync(Buffer.from(body, "utf8")));
    const { out } = await run("https://magev6.if.qidian.com/argus/api/v3/deeplink/geturl", g, { utils: realUtils });
    const j = parse(out);
    check("ActionUrl 被清空", j && j.Data.ActionUrl === "", JSON.stringify(j));
    check("其余业务字段保留", j && j.Data.Keep === 7);
  }

  console.log("\nPASS=" + pass + " FAIL=" + fail);
  process.exit(fail ? 1 : 0);
})();
