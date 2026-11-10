/*
 * qidian/auto-task.js + scripts/Qidian.js · mainPage 限时激励任务（v3.6.1）
 * ------------------------------------------------------------
 * 真机 mainPage 响应（tests/fixtures/qidian_mainpage_limited.json）里：
 *   · ReadingPageTaskModule 有 6 条「【限时】广告·加点！」(TaskType 300, Total=3)
 *   · VideoRewardTab 有 3 条正常激励任务（完成 N 个广告任务得奖励）
 * 用户裁决：不要过滤掉；有的话参考正常激励自动完成。实现分三段：
 *   1. handleMainPage 不再调用 pruneAdTaskItems，两个模块的任务条目全量保留；
 *   2. 限时任务的当轮 TaskId/Total 写入 Qidian_LimitedTasks；
 *   3. 引擎 wrapper 的动态映射让 finishWatch 命中名单后按 Total-1 重放
 *      （与 config TaskMapping 的 count-1 同口径），响应侧不改完成态。
 * 本套件对 src 与 dist 两套 auto-task 各跑一遍；引擎段始终读 plugins/qidian/scripts/Qidian.js。
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const assert = require("assert");
const src = require("./load-script")("auto-task.js", "qidian");

const ROOT = path.resolve(__dirname, "..");
const FIXTURE = JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", "qidian_mainpage_limited.json"), "utf8"));
const MAINPAGE_URL = "https://magev6.if.qidian.com/argus/api/v2/video/adv/mainPage";
const ENGINE = fs.readFileSync(path.join(ROOT, "plugins", "qidian", "scripts", "Qidian.js"), "utf8");

function runSanitizer(body) {
  return new Promise((resolve) => {
    let out;
    const logs = [];
    const writes = [];
    const done = (v) => {
      out = v === undefined ? {} : v;
      resolve({ out, logs, writes });
    };
    const fn = new Function(
      "$request", "$response", "$done", "console", "$argument", "$utils",
      "$persistentStore", "$notification", "$httpClient", src
    );
    fn(
      { url: MAINPAGE_URL, method: "GET", headers: {} },
      { body: JSON.stringify(body), headers: {} },
      done,
      { log: (...a) => logs.push(a.join(" ")) },
      { QDREADER_DEBUG: "true", QDREADER_CLEAN_ENABLE: "true", QDREADER_EXTRA_ADV_JOB_ENABLE: "true" },
      undefined,
      {
        read: () => null,
        write: (v, k) => { writes.push({ k, v }); return true; },
      },
      { post: () => {} },
      {}
    );
    setTimeout(() => resolve({ out: out === undefined ? { __timeout: true } : out, logs, writes }), 2000);
  });
}

function runEngine(body, store, opts) {
  opts = opts || {};
  return new Promise((resolve) => {
    const calls = [];
    const notifications = [];
    let out;
    const realSetTimeout = global.setTimeout;
    global.setTimeout = (fn, ms, ...args) => {
      if (ms && ms > 100) { fn(...args); return 0; }
      return realSetTimeout(fn, ms, ...args);
    };
    try {
      new Function(
        "$request", "$response", "$done", "$argument", "$persistentStore",
        "$notification", "$httpClient", "$loon", "console", ENGINE
      )(
        { method: "POST", url: MAINPAGE_URL.replace(/mainPage$/, "finishWatch"), headers: {}, body: JSON.stringify(body) },
        undefined,
        (o) => { out = o; },
        {},
        {
          read: (k) => (Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null),
          write: () => true,
        },
        { post: (...a) => notifications.push(a) },
        {
          post: (o, cb) => {
            calls.push(o);
            cb(null, { status: 200, headers: {} }, JSON.stringify({ Result: 0 }));
          },
        },
        {},
        { log: () => {} }
      );
    } catch (e) {
      global.setTimeout = realSetTimeout;
      resolve({ calls, notifications, out, error: String(e) });
      return;
    }
    realSetTimeout(() => {
      global.setTimeout = realSetTimeout;
      resolve({ calls, notifications, out });
    }, opts.waitMs || 400);
  });
}

let pass = 0, fail = 0;
function check(name, cond, extra) {
  if (cond) { pass++; console.log("  ok  " + name); }
  else { fail++; console.log("  FAIL " + name + (extra ? " :: " + extra : "")); }
}

(async () => {
  {
    let output;
    const diagnostic = [];
    const url = "https://h5.if.qidian.com/argus/api/v2/video/adv/mainPage?source=welfare";
    const plugin = fs.readFileSync(path.join(ROOT, "plugins/qidian/qidian.plugin"), "utf8");
    const mitm = plugin.split("\n").find(line => line.startsWith("hostname = "));
    assert(mitm, "发布插件必须声明 MITM 域名");
    const hosts = mitm.split("=")[1].split(",").map(host => host.trim());
    assert.deepStrictEqual(hosts, ["h5.if.qidian.com", "magev6.if.qidian.com"]);
    const deepBinding = plugin.split("\n").find(line => line.startsWith("http-response ") && line.includes("tag=深度净化"));
    assert(deepBinding && !new RegExp(deepBinding.split(" ")[1]).test(url));
    const binding = plugin.split("\n").find(line => line.startsWith("http-response ") && line.includes("tag=起点mainPage诊断D2"));
    assert(binding && new RegExp(binding.split(" ")[1]).test(url));
    assert(binding.includes("script-path=https://raw.githubusercontent.com/AshNail/plugins/164082796f54c4afc63c1def711da918882de21a/plugins/qidian/scripts/Qidian.js"));
    assert.strictEqual(require("crypto").createHash("sha256").update(ENGINE).digest("hex"),
      "eac473815fcab7553d9b01343272a2527adc61db1aaacd669d2572fb8897cbba",
      "回归测试必须运行固定 URL 对应的实际脚本");
    const context = {
      $request: { url, method: "GET" },
      $response: { body: JSON.stringify(FIXTURE) },
      $done: value => { output = value; },
      $persistentStore: { read: () => null, write: () => true },
      $notification: { post: (...args) => diagnostic.push(args.join("\n")) },
      console: { log: () => {} },
    };
    vm.runInNewContext(ENGINE, context);
    assert.strictEqual(diagnostic.length, 2);
    assert(diagnostic[0].includes("已进入 QD-MP-D2"));
    assert(/entry.*URL=undefined/.test(diagnostic[0]));
    assert(diagnostic[1].includes("handler\nparse ok\nclean"));
    assert(diagnostic[1].includes("done body=string:"));
    assert(!diagnostic.join("\n").includes("source=welfare"));
    assert(output && typeof output.body === "string", "发布引擎在无 URL 全局环境中必须回写 mainPage");
    const data = JSON.parse(output.body).Data;
    const expected = JSON.parse(JSON.stringify(FIXTURE));
    if (expected.Data.DailyBenefitModule) expected.Data.DailyBenefitModule.RotateText = [];
    for (const key of ["MemberExclusiveTaskModule", "PrivilegedTaskModule", "MoreRewardTab",
      "SurpriseBenefit", "LastRewardItems", "IndexBannerTabs", "BaizeModule",
      "TaskShowData", "UserRewardModule", "PopFrequency"]) delete expected.Data[key];
    assert.deepStrictEqual(JSON.parse(output.body), expected);
    assert.strictEqual(data.ReadingPageTaskModule.TaskList.length, 6);
    for (const [body, expectedStage] of [["not-json", "parse failed"], ["{}", "parse no-Data"]]) {
      diagnostic.length = 0;
      vm.runInNewContext(ENGINE, { ...context, $response: { body } });
      assert.strictEqual(diagnostic.length, 2);
      assert(diagnostic[1].includes(expectedStage));
      assert(diagnostic[1].includes("done passthrough"));
    }
    diagnostic.length = 0;
    const brokenResponse = {};
    let reads = 0;
    Object.defineProperty(brokenResponse, "body", { get() {
      if (++reads > 1) throw new TypeError("diagnostic-test");
      return "{}";
    } });
    vm.runInNewContext(ENGINE, { ...context, $response: brokenResponse });
    assert.strictEqual(diagnostic.length, 2);
    assert(diagnostic[1].includes("error"));
    assert(diagnostic[1].includes("done passthrough"));
    check("发布绑定与无 URL 全局环境下 mainPage 回写回归", true);
  }
  console.log("\n[1] mainPage 净化：限时任务与正常激励全量保留，TaskId/Total 落盘");
  let r = await runSanitizer(FIXTURE);
  const j = r.out && r.out.body ? JSON.parse(r.out.body) : null;
  check("响应可解析", !!j && !!j.Data);
  check("ReadingPageTaskModule 保留 6 条", !!j && j.Data.ReadingPageTaskModule
    && j.Data.ReadingPageTaskModule.TaskList.length === 6);
  check("限时任务标题未被改写", !!j && j.Data.ReadingPageTaskModule.TaskList.every(
    (t) => t.Title === "【限时】广告·加点！"));
  check("VideoRewardTab 已删（对齐 config REMOVE_KEYS）", !!j && j.Data.VideoRewardTab === undefined);

  const write = r.writes.find((w) => w.k === "Qidian_LimitedTasks");
  const stored = write ? JSON.parse(write.v) : null;
  check("写入 Qidian_LimitedTasks", !!stored && Array.isArray(stored));
  check("落盘 6 个限时 TaskId", !!stored && stored.length === 6);
  check("落盘 Total 与响应一致", !!stored && stored.every((t) => t.total === 3));
  check("落盘 TaskId 与响应一致", !!stored && j
    && stored.map((t) => t.id).join(",") === j.Data.ReadingPageTaskModule.TaskList.map((t) => t.TaskId).join(","));
  check("锚点报告限时任务条数", r.logs.join("\n").includes("限时任务=6"), r.logs.join("\n").slice(-120));

  console.log("\n[2] 引擎 finishWatch：名单命中按 Total-1 重放，未知 taskId 不放行");
  const limitedStore = {
    Qidian_LimitedTasks: JSON.stringify([
      { id: "1283964019879641088", total: 3, title: "【限时】广告·加点！" },
    ]),
  };
  let e = await runEngine({ taskId: "1283964019879641088" }, limitedStore);
  check("限时任务重放 Total-1=2 次", e.calls.length === 2, String(e.calls.length));
  check("重放 body 带原 TaskId", e.calls.every((c) => String(c.body).includes("1283964019879641088")));
  check("通知摘要标记限时激励", JSON.stringify(e.notifications).includes("限时激励"));

  e = await runEngine({ taskId: "9999999" }, {});
  check("未知 taskId 不重放（config 原语义）", e.calls.length === 0, String(e.calls.length));

  e = await runEngine({ taskId: "1218712929269776384" }, {});
  check("正常激励静态映射仍生效（9 次 -> 重放 8 次）", e.calls.length === 8, String(e.calls.length));

  console.log("\nPASS=" + pass + " FAIL=" + fail);
  process.exit(fail ? 1 : 0);
})();
