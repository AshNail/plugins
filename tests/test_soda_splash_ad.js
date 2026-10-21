const load = require("./load-script");
const code = load("splash-ad.js", "soda");

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

const SPLASH = "https://ads5-normal-hl.zijieapi.com/api/ad/splash/luna/v15/?ad_id=1";
const STOCK = "https://ads5-normal-hl.zijieapi.com/api/ad/splash/stock/";
const REWARD = "https://ad.zijieapi.com/api/ad/v1/inspire/?rit=73031";
const DONE = "https://ad.zijieapi.com/api/incentive/marketing/done/";
const API = "https://api.qishui.com/luna/ads/config";

console.log("\n== 1. blockSplashAd=true：开屏广告请求被拦 ==");
{
  const r = run(SPLASH, { blockSplashAd: true });
  const resp = r.out && r.out.response;
  check("返回 200 空 JSON", !!(resp && resp.status === 200 && resp.body === "{}"),
    JSON.stringify(r.out));
  check("日志记录 blocked",
    r.logs.join(" ").includes("[soda-splash] blocked"), r.logs.join(" "));
}

console.log("\n== 2. 激励广告与发奖回调绝不拦 ==");
{
  const r1 = run(REWARD, { blockSplashAd: true });
  check("inspire（激励广告）不拦", !(r1.out && r1.out.response), JSON.stringify(r1.out));
  const r2 = run(DONE, { blockSplashAd: true });
  check("marketing/done（发奖回调）不拦", !(r2.out && r2.out.response), JSON.stringify(r2.out));
  const r3 = run(API, { blockSplashAd: true });
  check("汽水广告配置不拦", !(r3.out && r3.out.response), JSON.stringify(r3.out));
}

console.log("\n== 3. 开关关闭：全部放行 ==");
{
  const r = run(SPLASH, { blockSplashAd: false });
  check("不改写请求", !(r.out && r.out.response), JSON.stringify(r.out));
  const r2 = run(SPLASH, {});
  check("没有参数也放行", !(r2.out && r2.out.response), JSON.stringify(r2.out));
}

console.log("\n== 4. 其它开屏路径同样拦 ==");
{
  const r = run(STOCK, { blockSplashAd: true });
  check("splash/stock 也拦", !!(r.out && r.out.response), JSON.stringify(r.out));
}

console.log("\n" + (fail === 0 ? "ALL PASS" : "FAILURES") +
  "  pass=" + pass + " fail=" + fail);
process.exit(fail === 0 ? 0 : 1);
