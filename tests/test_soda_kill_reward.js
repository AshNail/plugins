const load = require("./load-script");
const code = load("sanitize.js", "soda");

function run(url, body, argument) {
  let out = null;
  const logs = [];
  const fn = new Function(
    "$request", "$response", "$done", "console", "$argument", code
  );
  fn(
    { url },
    { body: typeof body === "string" ? body : JSON.stringify(body) },
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

function parse(out) {
  if (!out || out.body === undefined) return null;
  try { return JSON.parse(out.body); } catch (e) { return null; }
}

const CONFIG_URL = "https://api.qishui.com/luna/advert/incentive/config";
const RETRIEVE_URL = "https://api.qishui.com/luna/advert/incentive/retrieve";

const CONFIG_BODY = {
  status_code: 0,
  advert_sources: [{ type: 3, rit: "73009", cid: "10000" }],
  feed_advert_config: { advert_duration: 30 },
  preload: true,
  vids: ["18616728", "6840291"],
  expire_time: 1792582120
};

const RETRIEVE_BODY = {
  status_code: 0,
  ad_infos: null,
  ad_infos_map: {
    default: { ad_infos: [{ launch_id: "x.mp4", launch_duration: 30 }] }
  }
};

console.log("\n== 1. 默认（rewardSafe=true）：激励素材不动 ==");
{
  const r = run(CONFIG_URL, CONFIG_BODY, { rewardSafe: true, cleanAds: false });
  check("不改写响应（保住看广告领奖）", !(r.out && r.out.body), JSON.stringify(r.out));
}

console.log("\n== 2. killRewardAds=true：即使保奖励模式也清素材 ==");
{
  const r = run(CONFIG_URL, CONFIG_BODY, { rewardSafe: true, killRewardAds: true });
  const o = parse(r.out);
  check("返回了改写后的响应", !!o, JSON.stringify(r.out));
  check("advert_sources -> []", o && o.advert_sources.length === 0, JSON.stringify(o));
  check("feed_advert_config -> {}", o && Object.keys(o.feed_advert_config).length === 0);
  check("vids -> []（预拉取列表也清）", o && o.vids.length === 0, JSON.stringify(o));
  check("preload -> false", o && o.preload === false);

  const r2 = run(RETRIEVE_URL, RETRIEVE_BODY, { rewardSafe: true, killRewardAds: true });
  const o2 = parse(r2.out);
  check("ad_infos_map -> {}", o2 && Object.keys(o2.ad_infos_map).length === 0, JSON.stringify(o2));
}

console.log("\n== 3. cleanAds=true：只清广告位/信息流，不动激励素材 ==");
{
  const r = run(CONFIG_URL, CONFIG_BODY, { rewardSafe: false, cleanAds: true });
  check("激励素材不受 cleanAds 影响（仍原样）", !(r.out && r.out.body), JSON.stringify(r.out));

  /* 即便误接线（只传 cleanAds），激励素材也不会被清 */
  const rKeep = run(CONFIG_URL, CONFIG_BODY, { rewardSafe: false, cleanAds: true, killRewardAds: false });
  check("只开 cleanAds 时激励素材保持原样", !(rKeep.out && rKeep.out.body), JSON.stringify(rKeep.out));

  /* ads/config 的真实字段：ad_unit_configs / splash_config / preload */
  const feed = {
    status_code: 0,
    ad_unit_configs: { slot: [{ id: 1 }] },
    splash_config: { a: 1 },
    preload: true
  };
  const rAds = run("https://api.qishui.com/luna/ads/config", feed, { rewardSafe: false, cleanAds: true });
  const oAds = parse(rAds.out);
  check("广告位配置被清", oAds && Object.keys(oAds.ad_unit_configs).length === 0, JSON.stringify(oAds));
  check("splash_config 被清", oAds && Object.keys(oAds.splash_config).length === 0, JSON.stringify(oAds));
  check("preload -> false", oAds && oAds.preload === false);
}

console.log("\n" + (fail === 0 ? "ALL PASS" : "FAILURES") +
  "  pass=" + pass + " fail=" + fail);
process.exit(fail === 0 ? 0 : 1);
