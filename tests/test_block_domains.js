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

  console.log(`\n== 1. ${family}: blockAdDomains=true：拦截非激励广告域名 ==`);
  {
    const r = runFor(family, AD_URL, { blockAdDomains: true });
    const resp = r.out && r.out.response;
    check(`${family} 返回 200 响应`, !!(resp && resp.status === 200), JSON.stringify(r.out));
    /* 与 [Rewrite] 的 reject_dict(200) 同形状：JSON {} + application/json。
       空 text/plain 会让按 JSON 解析的 SDK 走“解析失败→重试”。 */
    check(`${family} body 是 JSON {}`, !!(resp && resp.body === "{}"), JSON.stringify(r.out));
    check(`${family} Content-Type 是 application/json`,
      !!(resp && resp.headers &&
        String(resp.headers["Content-Type"] || "").startsWith("application/json")),
      JSON.stringify(r.out));
    check(`${family} 日志记录 ${TAG} blocked`,
      r.logs.join(" ").includes(`${TAG} blocked`),
      r.logs.join(" "));
  }

  console.log(`\n== 2. ${family}: 激励链路永远放行（与 rewardSafe 无关）==`);
  {
    const rewardPaths = [
      "https://ad.zijieapi.com/api/ad/v1/inspire/?ad_from=coin",
      "https://ad.zijieapi.com/api/ad/v1/inspire_preload/?is_preload=1",
      "https://ad.zijieapi.com/api/incentive/marketing/done/"
    ];
    for (const url of rewardPaths) {
      for (const args of [{ blockAdDomains: true }, { rewardSafe: true, blockAdDomains: true }]) {
        const r = runFor(family, url, args);
        check(`${family} 放行 ${url.slice(8, 60)} (${JSON.stringify(args)})`,
          !(r.out && r.out.response), JSON.stringify(r.out));
        check(`${family} 日志记录 keep reward`,
          r.logs.join(" ").includes("keep reward ad"), r.logs.join(" "));
      }
    }
    const lookalike = runFor(family, "https://ad.zijieapi.com/api/ad/v1/inspirex/", { blockAdDomains: true });
    check(`${family} 不放行仿冒路径 inspirex`, !!(lookalike.out && lookalike.out.response),
      JSON.stringify(lookalike.out));
    const splash = runFor(family, "https://ad.zijieapi.com/api/ad/v1/splash/stock/", { blockAdDomains: true });
    check(`${family} 继续拦截开屏素材路径`, !!(splash.out && splash.out.response),
      JSON.stringify(splash.out));
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

  console.log(`\n== 5. ${family}: 广告域名（含 Pangle 分片族 glob）全部命中 ==`);
  {
    const hits = [
      "ad.zijieapi.com",
      "lianmengapi.snssdk.com",
      "ads3-normal-hl.zijieapi.com",
      "ads5-normal-hl.zijieapi.com",
      "ads3-normal.zijieapi.com",
      // 枚举名单里没有的兄弟分片：靠 BLOCKED_HOSTS 的 glob 命中，
      // 这样服务端换分片（ads7/ads9、-lf/-lq）不会漏。
      "ads7-normal-xh.zijieapi.com",
      "ads9-normal.zijieapi.com",
      "zlink.ugsdk.cn",
      "praisewindow.ugsdk.cn"
    ];
    for (const host of hits) {
      const r = runFor(family, `https://${host}/x`, { rewardSafe: false, blockAdDomains: true });
      const ok = !!(r.out && r.out.response && r.out.response.status === 200);
      check(`${family} 拦截 ${host}`, ok, JSON.stringify(r.out));
    }
    const misses = [
      "ads-normal-hl.zijieapi.com",                    // 分片位必须是数字
      "ads5-normal-hl.zijieapi.com.evil.example",       // 后缀伪装
      "notad.zijieapi.com"                              // 非广告主机
    ];
    for (const host of misses) {
      const r = runFor(family, `https://${host}/x`, { rewardSafe: false, blockAdDomains: true });
      check(`${family} 不误伤 ${host}`, !(r.out && r.out.response), JSON.stringify(r.out));
    }
  }

  console.log(`\n== 6. ${family}: 只开 blockAdDomains（无 rewardSafe 参数）→ 两家族一致拦截非激励路径 ==`);
  {
    const r = runFor(family, AD_URL, { blockAdDomains: true });
    const resp = r.out && r.out.response;
    check(`${family} 非激励路径被拦截`, !!(resp && resp.status === 200), JSON.stringify(r.out));
    check(`${family} 日志记录 blocked`, r.logs.join(" ").includes(`${TAG} blocked`), r.logs.join(" "));
    const reward = runFor(family, "https://ad.zijieapi.com/api/ad/v1/inspire/", { blockAdDomains: true });
    check(`${family} 激励路径仍放行`, !(reward.out && reward.out.response), JSON.stringify(reward.out));
  }
}

console.log("\n" + (fail === 0 ? "ALL PASS" : "FAILURES") +
  "  pass=" + pass + " fail=" + fail);
process.exit(fail === 0 ? 0 : 1);
