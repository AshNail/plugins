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
  const code = loadScript("splash-ad.js", family);
  const fn = new Function("$request", "$done", "console", "$argument", code);
  fn({ url }, (v) => { out = v; }, { log: (...a) => logs.push(a.join(" ")) }, argument);
  return { out, logs };
}

// soda/douyin 共享 src/common/splash-ad.js；两个家族逐套跑，防止
// families.json 的日志前缀展开把某一个家族带偏。
const FAMILIES = ["soda", "douyin"];

const SPLASH = "https://ads5-normal-hl.zijieapi.com/api/ad/splash/luna/v15/?ad_id=1";
const STOCK = "https://ads5-normal-hl.zijieapi.com/api/ad/splash/stock/";
const V2ACK = "https://ad.zijieapi.com/api/ad/v2/ack/splash/collect";
const REWARD = "https://ad.zijieapi.com/api/ad/v1/inspire/?rit=73031";
const PRELOAD = "https://ad.zijieapi.com/api/ad/v1/inspire_preload/";
const DONE = "https://ad.zijieapi.com/api/incentive/marketing/done/";

for (const family of FAMILIES) {
  const TAG = `[${family}-splash]`;
  const API = family === "soda"
    ? "https://api.qishui.com/luna/ads/config"
    : "https://beta-luna.douyin.com/luna/ads/config";

  console.log(`\n===== family: ${family} =====`);

  console.log(`\n== 1. ${family}: blockSplashAd=true：开屏广告请求被拦 ==`);
  {
    const r = runFor(family, SPLASH, { blockSplashAd: true });
    const resp = r.out && r.out.response;
    check(`${family} 返回 200 空 JSON`, !!(resp && resp.status === 200 && resp.body === "{}"),
      JSON.stringify(r.out));
    check(`${family} Content-Type 是 JSON`,
      !!(resp && resp.headers && /application\/json/.test(resp.headers["Content-Type"] || "")),
      JSON.stringify(r.out));
    check(`${family} 日志记录 ${TAG} blocked`,
      r.logs.join(" ").includes(`${TAG} blocked`), r.logs.join(" "));
  }

  console.log(`\n== 2. ${family}: 激励广告与发奖回调绝不拦 ==`);
  {
    const r1 = runFor(family, REWARD, { blockSplashAd: true });
    check(`${family} inspire（激励广告）不拦`, !(r1.out && r1.out.response), JSON.stringify(r1.out));
    const r2 = runFor(family, PRELOAD, { blockSplashAd: true });
    check(`${family} inspire_preload（激励预拉取）不拦`, !(r2.out && r2.out.response), JSON.stringify(r2.out));
    const r3 = runFor(family, DONE, { blockSplashAd: true });
    check(`${family} marketing/done（发奖回调）不拦`, !(r3.out && r3.out.response), JSON.stringify(r3.out));
    const r4 = runFor(family, API, { blockSplashAd: true });
    check(`${family} 广告配置端点不拦`, !(r4.out && r4.out.response), JSON.stringify(r4.out));
  }

  console.log(`\n== 3. ${family}: 开关关闭：全部放行 ==`);
  {
    const r = runFor(family, SPLASH, { blockSplashAd: false });
    check(`${family} 不改写请求`, !(r.out && r.out.response), JSON.stringify(r.out));
    const r2 = runFor(family, SPLASH, {});
    check(`${family} 没有参数也放行`, !(r2.out && r2.out.response), JSON.stringify(r2.out));
  }

  console.log(`\n== 4. ${family}: 其它开屏路径同样拦 ==`);
  {
    const r = runFor(family, STOCK, { blockSplashAd: true });
    check(`${family} splash/stock 也拦`, !!(r.out && r.out.response), JSON.stringify(r.out));
    const r2 = runFor(family, V2ACK, { blockSplashAd: true });
    check(`${family} v2/ack/splash 也拦`, !!(r2.out && r2.out.response), JSON.stringify(r2.out));
  }
}

console.log("\n" + (fail === 0 ? "ALL PASS" : "FAILURES") +
  "  pass=" + pass + " fail=" + fail);
process.exit(fail === 0 ? 0 : 1);
