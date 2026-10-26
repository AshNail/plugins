const loadScript = require("./load-script");

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

function runFor(family, url, argument) {
  let out = null;
  const logs = [];
  const code = loadScript("block-domains.js", family);
  const fn = new Function("$request", "$done", "console", "$argument", code);
  fn({ url }, (v) => { out = v; }, { log: (...a) => logs.push(a.join(" ")) }, argument);
  return { out, logs };
}

// soda/douyin 共享 src/common/block-domains.js；两个家族逐套跑，防止
// families.json 的展开（日志前缀 / rewardSafe 默认值）把某一个家族带偏。
const FAMILIES = ["soda", "douyin"];

const AD_URL = "https://ad.zijieapi.com/feed?slot=reward";

for (const family of FAMILIES) {
  const TAG = `[${family}-domains]`;

  console.log(`\n===== family: ${family} =====`);

  console.log(`\n== 1. ${family}: blockAdDomains=true + rewardSafe=false：拦截广告域名 ==`);
  {
    const r = runFor(family, AD_URL, { rewardSafe: false, blockAdDomains: true });
    const resp = r.out && r.out.response;
    check(`${family} 返回 200 空响应`, !!(resp && resp.status === 200), JSON.stringify(r.out));
    check(`${family} body 为空`, !!(resp && resp.body === ""), JSON.stringify(r.out));
    check(`${family} 日志记录 ${TAG} blocked`,
      r.logs.join(" ").includes(`${TAG} blocked`),
      r.logs.join(" "));
  }

  console.log(`\n== 2. ${family}: rewardSafe=true：放行，激励广告照常 ==`);
  {
    const r = runFor(family, AD_URL, { rewardSafe: true, blockAdDomains: true });
    check(`${family} 不返回 response`, !(r.out && r.out.response), JSON.stringify(r.out));
    check(`${family} 日志记录 passthrough`,
      r.logs.join(" ").includes("rewardSafe=on"),
      r.logs.join(" "));
  }

  console.log(`\n== 3. ${family}: 没有 $argument（独立调用）：放行 ==`);
  {
    const r = runFor(family, AD_URL);
    check(`${family} 不返回 response`, !(r.out && r.out.response), JSON.stringify(r.out));
  }

  console.log(`\n== 4. ${family}: 其它域名不受影响（脚本只匹配广告域名）==`);
  {
    const api = family === "soda"
      ? "https://api.qishui.com/luna/treasure/task/view"
      : "https://beta-luna.douyin.com/luna/treasure/task/page/v2";
    const r = runFor(family, api, { rewardSafe: false, blockAdDomains: true });
    check(`${family} API 域名不拦截`, !(r.out && r.out.response), JSON.stringify(r.out));
  }

  console.log(`\n== 5. ${family}: 5 个广告域名全部命中 ==`);
  {
    const hosts = [
      "ad.zijieapi.com",
      "lianmengapi.snssdk.com",
      "ads5-normal-hl.zijieapi.com",
      "zlink.ugsdk.cn",
      "praisewindow.ugsdk.cn"
    ];
    for (const host of hosts) {
      const r = runFor(family, `https://${host}/x`, { rewardSafe: false, blockAdDomains: true });
      const ok = !!(r.out && r.out.response && r.out.response.status === 200);
      check(`${family} 拦截 ${host}`, ok, JSON.stringify(r.out));
    }
  }

  console.log(`\n== 6. ${family}: 只开 blockAdDomains（无 rewardSafe 参数）时按家族默认值分支 ==`);
  {
    // soda 的 families.json 默认 rewardSafe=true（保奖励优先 → 放行）；
    // douyin 默认 false（blockAdDomains 一开就拦）。两家族行为必须不同，
    // 这里的断言把 families.json 的差异锁进测试。
    const r = runFor(family, AD_URL, { blockAdDomains: true });
    if (family === "soda") {
      check("soda 默认 rewardSafe=true → 放行", !(r.out && r.out.response), JSON.stringify(r.out));
      check("soda 日志说明 rewardSafe=on", r.logs.join(" ").includes("rewardSafe=on"), r.logs.join(" "));
    } else {
      const resp = r.out && r.out.response;
      check("douyin 默认 rewardSafe=false → 拦截", !!(resp && resp.status === 200), JSON.stringify(r.out));
      check("douyin 日志记录 blocked", r.logs.join(" ").includes(`${TAG} blocked`), r.logs.join(" "));
    }
  }
}

console.log("\n" + (fail === 0 ? "ALL PASS" : "FAILURES") +
  "  pass=" + pass + " fail=" + fail);
process.exit(fail === 0 ? 0 : 1);
