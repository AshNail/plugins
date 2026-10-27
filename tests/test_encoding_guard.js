"use strict";

/*
 * 编码诊断守卫。
 *
 * Loon 脚本层只有 $utils.ungzip（gzip）；br / zstd / deflate 没有解码器，
 * 这些响应体会以乱码落进“非 JSON”分支，看起来和“接口换了形状”一模一样。
 * 这里锁死两件事：
 *   1. 非 gzip 的 content-encoding 必须出现在诊断标记/日志里（ce=br）。
 *   2. gzip / identity / 无头时不许加噪声（不能出现 ce=）。
 *
 * 头名大小写不敏感，逗号列表取原样（gzip, br -> ce=gzip,br）。
 */

const loadScript = require("./load-script");

const SCRIPTS = {
  "soda/sanitize": loadScript("sanitize.js", "soda"),
  "soda/settings": loadScript("settings.js", "soda"),
  "soda/reward-observe": loadScript("reward-observe.js", "soda"),
  "douyin/clean": loadScript("clean.js", "douyin"),
  "douyin/treasure": loadScript("treasure.js", "douyin"),
  "douyin/observe": loadScript("observe.js", "douyin")
};

let pass = 0, fail = 0;
function check(name, cond, extra) {
  if (cond) {
    pass++;
    console.log("  PASS  " + name);
  } else {
    fail++;
    console.log("  FAIL  " + name + (extra ? "  got=" + extra : ""));
  }
}

/* 一段不是 JSON、也不带 gzip 魔数的 body：脚本只能看到乱码 */
const BINARY_BODY = "\u008b\u0000\u00ff\u00fe\u00ab\u00cd";

function runScript(code, opts) {
  let out = null;
  const logs = [];
  const fn = new Function(
    "$request", "$response", "$done", "$argument", "console",
    "$persistentStore", "$notification", code
  );
  fn(
    { url: opts.url },
    { body: opts.body === undefined ? BINARY_BODY : opts.body, headers: opts.headers || {} },
    (v) => { out = v; },
    opts.argument || {},
    { log: (...a) => logs.push(a.join(" ")) },
    undefined,
    { post: () => {} }
  );
  return { out, logs: logs.join("\n") };
}

/*
 * 每个脚本喂一个能走到“非 JSON”分支的 URL 与开关组合。
 * 三组头：br / gzip / 无头，用来同时验“有诊断”和“无噪声”。
 */
const CASES = [
  {
    name: "soda/sanitize",
    key: "soda/sanitize",
    url: "https://api.qishui.com/luna/treasure/task/page/v2",
    argument: { cleanAds: true, rewardSafe: false }
  },
  {
    name: "soda/settings",
    key: "soda/settings",
    url: "https://conf.qishui.com/service/settings/v3/",
    argument: { settingsClean: true, rewardSafe: false }
  },
  {
    name: "soda/reward-observe",
    key: "soda/reward-observe",
    url: "https://api.qishui.com/luna/advert/incentive/config",
    argument: { logTaskTitles: false }
  },
  {
    name: "douyin/clean",
    key: "douyin/clean",
    url: "https://beta-luna.douyin.com/luna/advert/incentive/config",
    argument: { killRewardAds: true }
  },
  {
    name: "douyin/treasure",
    key: "douyin/treasure",
    url: "https://beta-luna.douyin.com/luna/treasure/task/page/v2",
    argument: { treasureMinimal: true }
  },
  {
    name: "douyin/observe",
    key: "douyin/observe",
    url: "https://beta-luna.douyin.com/luna/advert/incentive/config",
    argument: {}
  }
];

function signal(r) {
  const marker = (r.out && r.out.headers && r.out.headers["X-Soda-Plugin"]) || "";
  return marker + "\n" + r.logs;
}

console.log("\n== 1. 非 gzip 编码要留下 ce= 证据 ==");
for (const c of CASES) {
  const r = runScript(SCRIPTS[c.key], {
    url: c.url,
    argument: c.argument,
    headers: { "Content-Encoding": "br" }
  });
  check(c.name + " 标记出 ce=br", /ce=br/.test(signal(r)), signal(r));
}

console.log("\n== 2. gzip / identity / 无头不加噪声 ==");
for (const c of CASES) {
  const gz = runScript(SCRIPTS[c.key], {
    url: c.url, argument: c.argument, headers: { "Content-Encoding": "gzip" }
  });
  check(c.name + " gzip 不写 ce=", !/ce=/.test(signal(gz)), signal(gz));

  const none = runScript(SCRIPTS[c.key], {
    url: c.url, argument: c.argument
  });
  check(c.name + " 无头不写 ce=", !/ce=/.test(signal(none)), signal(none));
}

console.log("\n== 3. 头名大小写与逗号列表 ==");
{
  const lower = runScript(SCRIPTS["soda/sanitize"], {
    url: CASES[0].url,
    argument: CASES[0].argument,
    headers: { "content-encoding": "Brotli" }
  });
  check("小写头名 + 大写值 -> ce=brotli", /ce=brotli/.test(signal(lower)), signal(lower));

  const list = runScript(SCRIPTS["douyin/clean"], {
    url: CASES[3].url,
    argument: CASES[3].argument,
    headers: { "Content-Encoding": "gzip, br" }
  });
  check("逗号列表 -> ce=gzip,br", /ce=gzip,br/.test(signal(list)), signal(list));
}

console.log("\n== 4. 正常 JSON 仍照常处理（诊断不干扰主流程）==");
{
  const ok = runScript(SCRIPTS["douyin/clean"], {
    url: CASES[3].url,
    argument: CASES[3].argument,
    headers: { "Content-Encoding": "gzip" },
    body: JSON.stringify({ status_code: 0, advert_sources: [{ type: 3 }] })
  });
  check("JSON 走完清理并回写 body",
    !!(ok.out && typeof ok.out.body === "string"),
    JSON.stringify(ok.out));
  check("清理后的标记不含 ce=", !/ce=/.test(signal(ok)), signal(ok));
}

console.log("\n== 5. 回写 body 时必须清掉过期的压缩头 ==");
{
  /*
   * readBody 把 gzip 解成了明文字符串，$done 带回去的 body 就是明文。
   * 此时原响应头的 content-encoding:gzip / content-length 已经对不上：
   * 留着 = 客户端拿明文按 gzip 解（JSON 解析失败）或按旧长度截断。
   */
  const gzBody = JSON.stringify({ status_code: 0, advert_sources: [{ type: 3 }] });
  const r = runScript(SCRIPTS["douyin/clean"], {
    url: CASES[3].url,
    argument: CASES[3].argument,
    headers: {
      "Content-Encoding": "gzip",
      "Content-Length": "191234",
      "X-Trace": "keep-me"
    },
    body: gzBody
  });
  const h = (r.out && r.out.headers) || {};
  check("回写 body 时删掉 content-encoding", !("Content-Encoding" in h), JSON.stringify(h));
  check("回写 body 时删掉 content-length", !("Content-Length" in h), JSON.stringify(h));
  check("其它响应头原样保留", h["X-Trace"] === "keep-me", JSON.stringify(h));
  check("诊断头仍在（changed=N）",
    typeof h["X-Soda-Plugin"] === "string" &&
    h["X-Soda-Plugin"].indexOf("changed=") >= 0, h["X-Soda-Plugin"]);
  check("回写的 body 是明文 JSON",
    typeof r.out.body === "string" && r.out.body.charCodeAt(0) === 0x7b,
    String(r.out.body).slice(0, 20));
}

console.log("\n== 6. 只加诊断头（body 没动）时压缩头必须保留 ==");
{
  /*
   * 反向约束：跳过分支只加 X-Soda-Plugin，body 还是原来那份压缩体，
   * 这时候删 content-encoding 反而会把好好的响应弄坏。
   */
  const r = runScript(SCRIPTS["soda/sanitize"], {
    url: CASES[0].url,
    argument: CASES[0].argument,
    headers: { "Content-Encoding": "br", "Content-Length": "10" }
  });
  const h = (r.out && r.out.headers) || {};
  check("跳过分支保留 content-encoding", h["Content-Encoding"] === "br", JSON.stringify(h));
  check("跳过分支保留 content-length", h["Content-Length"] === "10", JSON.stringify(h));
  check("跳过分支不带 body", !("body" in (r.out || {})), JSON.stringify(r.out));
}

console.log("\n" + (fail === 0 ? "ALL PASS" : "FAILURES") +
  "  pass=" + pass + " fail=" + fail);
process.exit(fail === 0 ? 0 : 1);
