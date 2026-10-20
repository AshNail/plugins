const code = require("./load-script")("block-domains.js");

function run(url, argument) {
  let out = null;
  const logs = [];
  const fn = new Function(
    "$request", "$done", "console", "$argument", code
  );
  fn(
    { url },
    (v) => { out = v; },
    { log: (...a) => logs.push(a.join(" ")) },
    argument
  );
  return { out, logs };
}

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

const AD_URL = "https://ad.zijieapi.com/feed?slot=reward";

console.log("\n== 1. blockAdDomains=true + rewardSafe=false：拦截广告域名 ==");
{
  const r = run(AD_URL, { rewardSafe: false, blockAdDomains: true });
  const resp = r.out && r.out.response;
  check("返回 200 空响应", !!(resp && resp.status === 200), JSON.stringify(r.out));
  check("body 为空", !!(resp && resp.body === ""), JSON.stringify(r.out));
  check("日志记录 blocked",
    r.logs.join(" ").includes("[soda-domains] blocked"),
    r.logs.join(" "));
}

console.log("\n== 2. rewardSafe=true：放行，激励广告照常 ==");
{
  const r = run(AD_URL, { rewardSafe: true, blockAdDomains: true });
  check("不返回 response", !(r.out && r.out.response), JSON.stringify(r.out));
  check("日志记录 passthrough",
    r.logs.join(" ").includes("rewardSafe=on"),
    r.logs.join(" "));
}

console.log("\n== 3. 没有 $argument（独立调用）：放行 ==");
{
  const r = run(AD_URL);
  check("不返回 response", !(r.out && r.out.response), JSON.stringify(r.out));
}

console.log("\n== 4. 其它域名不受影响（脚本只匹配广告域名）==");
{
  const r = run("https://api.qishui.com/luna/treasure/task/view", {
    rewardSafe: false,
    blockAdDomains: true
  });
  check("API 域名不拦截", !(r.out && r.out.response), JSON.stringify(r.out));
}

console.log("\n" + (fail === 0 ? "ALL PASS" : "FAILURES") +
  "  pass=" + pass + " fail=" + fail);
process.exit(fail === 0 ? 0 : 1);
