/*
 * 存储作用域测试：删一个键 ≠ 清空整个存储
 *
 * 背景（官方 Script API 5.3）：`$persistentStore.remove()` 不接受参数，
 * 语义是「清空通过脚本存储 API 保存的全部数据」。传 key 进去不会只删那个键。
 *
 * 这个测试盯的是「量完一次广告时长，把其它脚本的状态一起抹掉」这类事故：
 * 只断言「目标键没了」是不够的——必须同时断言「别的键还在」。
 */

const load = require("./load-script");

let pass = 0, fail = 0;
function check(name, cond, extra) {
  if (cond) { pass++; console.log("  ok  " + name); }
  else { fail++; console.log("  FAIL " + name + (extra ? " :: " + extra : "")); }
}

const CASES = [
  {
    family: "soda",
    file: "reward-observe.js",
    url: "https://api.qishui.com/luna/advert/incentive/done",
    body: { reward_details: { r1: { amount: 1, claim_status: 2 } } },
    startKey: "soda-ad-start",
    statsKey: "soda-ad-stats",
    otherKey: "soda-welfare-seen"
  },
  {
    family: "douyin",
    file: "observe.js",
    url: "https://ad.zijieapi.com/api/incentive/marketing/done",
    body: { code: 0, msg: "ok" },
    startKey: "douyin-ad-start",
    statsKey: "douyin-ad-stats",
    otherKey: "douyin-welfare-seen"
  }
];

function runCase(c) {
  const src = load(c.file, c.family);

  const data = {};
  const calls = [];
  data[c.startKey] = String(Date.now() - 30000); // 30 秒前点了广告
  data[c.otherKey] = "2026-10-27";               // 当天已打卡
  data[c.statsKey] = JSON.stringify({ day: "2026-10-27", n: 2, s: 90 });

  const store = {
    read(key) { return Object.prototype.hasOwnProperty.call(data, key) ? data[key] : ""; },
    write(value, key) {
      calls.push(["write", value, key]);
      if (value === undefined || value === null) { delete data[key]; }
      else { data[key] = String(value); }
      return true;
    },
    remove() {
      calls.push(["remove"]);
      // 官方的 remove 会带走全部数据，这里如实模拟
      Object.keys(data).forEach((k) => delete data[k]);
    }
  };

  let out = null;
  const logs = [];
  new Function(
    "$request", "$response", "$done", "console", "$argument", "$persistentStore", src
  )(
    { url: c.url, method: "POST" },
    { status: 200, body: JSON.stringify(c.body) },
    (v) => { out = v; },
    { log: (...a) => logs.push(a.join(" ")) },
    null,
    store
  );
  return { data, calls, logs, out };
}

for (const c of CASES) {
  console.log(`\n[${c.family}] 量完广告时长后，其它脚本的键必须还在`);
  const r = runCase(c);

  check("没有调用 $persistentStore.remove()",
    !r.calls.some((x) => x[0] === "remove"),
    JSON.stringify(r.calls.filter((x) => x[0] === "remove")));

  check("开始时间键被删掉",
    !Object.prototype.hasOwnProperty.call(r.data, c.startKey),
    JSON.stringify(Object.keys(r.data)));

  check("打卡状态键仍在（这是事故现场）",
    r.data[c.otherKey] === "2026-10-27",
    JSON.stringify(r.data));

  check("统计键仍在",
    Object.prototype.hasOwnProperty.call(r.data, c.statsKey),
    JSON.stringify(Object.keys(r.data)));

  check("删除走的是 write(undefined, key)",
    r.calls.some((x) => x[0] === "write" && x[1] === undefined && x[2] === c.startKey),
    JSON.stringify(r.calls));

  check("日志里带出耗时秒数",
    r.logs.join(" ").includes("秒"),
    r.logs.join(" | ").slice(0, 200));
}

console.log("\n" + (fail === 0 ? "ALL PASS" : "FAILURES") +
  ` pass=${pass} fail=${fail}`);
process.exit(fail === 0 ? 0 : 1);
