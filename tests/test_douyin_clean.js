const load = require("./load-script");
const code = load("clean.js", "douyin");

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

const INCENTIVE_CONFIG = "https://beta-luna.douyin.com/luna/advert/incentive/config";
const INCENTIVE_RETRIEVE = "https://beta-luna.douyin.com/luna/advert/incentive/retrieve";
const FEED_ADS = "https://beta-luna.douyin.com/luna/ads/dsp/retrieve";
const FEED_ADS_RETRIEVE = "https://beta-luna.douyin.com/luna/ads/retrieve";
const UPSELL = "https://beta-luna.douyin.com/luna/commerce/v2/upsell";
const FESTIVAL = "https://beta-luna.douyin.com/luna/growth/music_festival/performance_details";

console.log("\n== 1. killRewardAds：清广告源/信息流配置/预拉取 ==");
{
  const body = {
    status_code: 0,
    advert_sources: [{ type: 3, rit: "73009", cid: "10000" }],
    expire_time: 1792582120,
    preload: true,
    feed_advert_config: { advert_duration: 30, forbid_first_slide: true },
    vids: ["18616728", "6840291"],
    status_info: { now: 1792495720, status_msg: "success" }
  };
  const r = run(INCENTIVE_CONFIG, body, { killRewardAds: true });
  const o = parse(r.out);
  check("advert_sources -> []", o && Array.isArray(o.advert_sources) && o.advert_sources.length === 0,
    JSON.stringify(o));
  check("feed_advert_config -> {}", o && Object.keys(o.feed_advert_config).length === 0,
    JSON.stringify(o));
  check("vids -> []", o && Array.isArray(o.vids) && o.vids.length === 0, JSON.stringify(o));
  check("preload -> false", o && o.preload === false, o && o.preload);
  check("包络保留", o && o.status_code === 0 && o.status_info.status_msg === "success");
}

console.log("\n== 2. killRewardAds：清素材表 ==");
{
  const body = {
    status_code: 0,
    ad_infos: null,
    ad_infos_map: {
      default: {
        ad_infos: [
          {
            launch_id: "x.mp4",
            launch_duration: 30,
            creative_info: { video_list: [{ url: "http://p6-luna.douyinpic.com/x.mp4" }] },
            component: { card: { upsell_unique_name: "ad_incentive_backup_card" } }
          }
        ]
      }
    }
  };
  const r = run(INCENTIVE_RETRIEVE, body, { killRewardAds: true });
  const o = parse(r.out);
  check("ad_infos_map -> {}", o && Object.keys(o.ad_infos_map).length === 0, JSON.stringify(o));
  check("素材不再下发", o && !JSON.stringify(o).includes("launch_id"));
}

console.log("\n== 3. 只开 cleanFeedAds：激励广告素材/预拉取必须原样保留 ==");
{
  const config = {
    status_code: 0,
    preload: true,
    feed_advert_config: { advert_duration: 30 },
    vids: ["18616728", "6840291"],
    advert_sources: [{ type: 3, rit: "73009" }]
  };
  const r = run(INCENTIVE_CONFIG, config, { cleanFeedAds: true });
  check("不改写激励广告配置", !(r.out && r.out.body), JSON.stringify(r.out));
  check("日志说明开关未开",
    r.logs.join(" ").includes("switch off"), r.logs.join(" "));

  const material = {
    status_code: 0,
    ad_infos_map: { default: { ad_infos: [{ launch_id: "x.mp4", launch_duration: 30 }] } }
  };
  const r2 = run(INCENTIVE_RETRIEVE, material, { cleanFeedAds: true });
  check("不改写激励广告素材", !(r2.out && r2.out.body), JSON.stringify(r2.out));
}

console.log("\n== 4. cleanFeedAds：清信息流广告容器 ==");
{
  const body = {
    status_code: 0,
    ads: [{ id: 1 }],
    ads_info: { a: 1 },
    ad_infos: [{ id: 2 }],
    ad_unit_configs: { x: 1 },
    splash_dsp_config: { rit: "123" },
    enable_ads: true
  };
  const r = run(FEED_ADS, body, { cleanFeedAds: true });
  const o = parse(r.out);
  check("ads -> []", o && Array.isArray(o.ads) && o.ads.length === 0, JSON.stringify(o));
  check("ads_info -> {}", o && Object.keys(o.ads_info).length === 0, JSON.stringify(o));
  check("ad_infos -> []", o && Array.isArray(o.ad_infos) && o.ad_infos.length === 0);
  check("ad_unit_configs -> {}", o && Object.keys(o.ad_unit_configs).length === 0);
  check("splash_dsp_config -> {}", o && Object.keys(o.splash_dsp_config).length === 0);
  check("enable_ads -> false", o && o.enable_ads === false);
}

console.log("\n== 4b. cleanFeedAds：ads/retrieve 清广告对象与配置 ==");
{
  const body = {
    status_code: 0,
    ad_launch: { id: "launch" },
    ad_launch_list: [{ id: "launch-list" }],
    ads_blocks: [{ id: 1 }],
    ads_info: { a: 1 },
    ad_unit_configs: { x: 1 },
    splash_config: { rit: "splash" },
    feed_ads_config: { enable: true },
    reward_config: { rit: "reward" },
    data: { title: "normal-feed" }
  };
  const r = run(FEED_ADS_RETRIEVE, body, { cleanFeedAds: true });
  const o = parse(r.out);
  check("ads/retrieve: ad_launch -> {}", o && Object.keys(o.ad_launch).length === 0,
    JSON.stringify(o));
  check("ads/retrieve: ad_launch_list -> []",
    o && Array.isArray(o.ad_launch_list) && o.ad_launch_list.length === 0);
  check("ads/retrieve: ads_blocks -> []",
    o && Array.isArray(o.ads_blocks) && o.ads_blocks.length === 0);
  check("ads/retrieve: ads_info -> {}", o && Object.keys(o.ads_info).length === 0);
  check("ads/retrieve: ad_unit_configs -> {}", o && Object.keys(o.ad_unit_configs).length === 0);
  check("ads/retrieve: splash_config -> {}", o && Object.keys(o.splash_config).length === 0);
  check("ads/retrieve: feed_ads_config -> {}", o && Object.keys(o.feed_ads_config).length === 0);
  check("ads/retrieve: reward_config -> {}", o && Object.keys(o.reward_config).length === 0);
  check("ads/retrieve: 非广告字段保留", o && o.data && o.data.title === "normal-feed");
}

console.log("\n== 5. cleanUpsell：删广告弹窗与商城弹窗，保留其它 ==");
{
  const body = {
    status_code: 0,
    upsell_map: {
      browse_mall_popup_acc_amount: { popup: { event: { params: { task_name: "逛商城赚金币" } } } },
      preview_popup_ads: { popup: {} },
      cold_launch_popup_ads_progress: { popup: {} },
      reward_ad_cold_launch_popup: { popup: {} },
      background_voice_prompt_ad: { popup: {} },
      coin_widget: { widget: {} },
      task_page_svip_popup: { popup: {} },
      reward_video_load_fail_compensate: { popup: {} }
    },
    sort_control_unique_names: ["coin_widget", "preview_popup_ads", "browse_mall_popup_acc_amount"],
    cold_launch_timing: {
      upsell_item_unique_names: ["cold_launch_popup_ads_progress", "coin_widget"]
    },
    freq_ctrl_cfg: {
      freq_ctrl_map: {
        preview_popup_ads: { day_max_cnt: 1 },
        background_voice_prompt_ad: { day_max_cnt: 2 },
        background_voice_prompt: { day_max_cnt: 2 },
        widget_ad: { day_max_cnt: 1 },
        coin_widget: { day_max_cnt: 1 }
      }
    },
    variables: { ads_days_obtained: "if(...)", is_svip: "..." }
  };
  const r = run(UPSELL, body, { cleanUpsell: true });
  const o = parse(r.out);
  const names = Object.keys(o.upsell_map);
  check("商城弹窗被删", names.indexOf("browse_mall_popup_acc_amount") === -1, names.join(","));
  check("广告弹窗被删", names.indexOf("preview_popup_ads") === -1, names.join(","));
  check("冷启动广告弹窗被删", names.indexOf("cold_launch_popup_ads_progress") === -1);
  check("激励冷启动弹窗被删", names.indexOf("reward_ad_cold_launch_popup") === -1);
  check("金币挂件保留", names.indexOf("coin_widget") !== -1, names.join(","));
  check("领奖弹窗保留", names.indexOf("task_page_svip_popup") !== -1, names.join(","));
  check("广告失败兜底保留", names.indexOf("reward_video_load_fail_compensate") !== -1);
  check("排序列表同步清理",
    o.sort_control_unique_names.indexOf("preview_popup_ads") === -1 &&
    o.sort_control_unique_names.indexOf("browse_mall_popup_acc_amount") === -1,
    JSON.stringify(o.sort_control_unique_names));
  check("冷启动列表同步清理",
    o.cold_launch_timing.upsell_item_unique_names.indexOf("cold_launch_popup_ads_progress") === -1);
  const freq = o.freq_ctrl_cfg.freq_ctrl_map;
  check("同名频控项清理 (preview_popup_ads)",
    !("preview_popup_ads" in freq), Object.keys(freq).join(","));
  check("同名频控项清理 (background_voice_prompt_ad)",
    !("background_voice_prompt_ad" in freq), Object.keys(freq).join(","));
  check("共享频控键保留 (background_voice_prompt)",
    "background_voice_prompt" in freq, Object.keys(freq).join(","));
  check("非 upsell 广告频控键保留 (widget_ad)", "widget_ad" in freq, Object.keys(freq).join(","));
  check("普通弹窗频控键保留 (coin_widget)", "coin_widget" in freq, Object.keys(freq).join(","));
  check("variables 不动", !!o.variables && !!o.variables.ads_days_obtained);
}

console.log("\n== 6. cleanUpsell：演出（汽水音乐节）detail_list 清空 ==");
{
  const body = {
    status_code: 0,
    detail_list: [
      { id: "26", title: "汽水音乐节", performance_stop_name: "常州站", price_desc: "198" }
    ]
  };
  const r = run(FESTIVAL, body, { cleanUpsell: true });
  const o = parse(r.out);
  check("detail_list -> []", o && Array.isArray(o.detail_list) && o.detail_list.length === 0,
    JSON.stringify(o));
}

console.log("\n== 7. 开关全关：原样放行 ==");
{
  const r = run(INCENTIVE_CONFIG, { status_code: 0, preload: true }, {});
  check("不改写响应", !(r.out && r.out.body), JSON.stringify(r.out));
}

console.log("\n== 8. 未匹配的接口：原样放行 ==");
{
  const r = run("https://beta-luna.douyin.com/luna/treasure/task/box/do_action",
    { status_code: 0 }, { cleanUpsell: true, cleanFeedAds: true, killRewardAds: true });
  check("不改写响应", !(r.out && r.out.body), JSON.stringify(r.out));
}

console.log("\n== 9. 非 JSON：原样放行 ==");
{
  const r = run(INCENTIVE_CONFIG, "{oops", { killRewardAds: true });
  check("不改写响应", !(r.out && r.out.body), JSON.stringify(r.out));
}

console.log("\n" + (fail === 0 ? "ALL PASS" : "FAILURES") +
  "  pass=" + pass + " fail=" + fail);
process.exit(fail === 0 ? 0 : 1);
