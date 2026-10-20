const load = require("./load-script");
const code = load("clean.js", "douyin");

function run(url, body) {
  let out = null;
  const logs = [];
  const fn = new Function("$request", "$response", "$done", "console", "$argument", code);
  fn(
    { url },
    { body: typeof body === "string" ? body : JSON.stringify(body) },
    (v) => { out = v; },
    { log: (...a) => logs.push(a.join(" ")) }
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

console.log("\n== 1. incentive/config：清广告源/信息流配置/预拉取 ==");
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
  const r = run("https://beta-luna.douyin.com/luna/advert/incentive/config", body);
  const o = parse(r.out);
  check("advert_sources -> []", o && Array.isArray(o.advert_sources) && o.advert_sources.length === 0,
    JSON.stringify(o));
  check("feed_advert_config -> {}", o && Object.keys(o.feed_advert_config).length === 0,
    JSON.stringify(o));
  check("vids -> []", o && Array.isArray(o.vids) && o.vids.length === 0, JSON.stringify(o));
  check("preload -> false", o && o.preload === false, o && o.preload);
  check("包络保留", o && o.status_code === 0 && o.status_info.status_msg === "success");
}

console.log("\n== 2. incentive/retrieve：清素材表 ==");
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
  const r = run("https://beta-luna.douyin.com/luna/advert/incentive/retrieve", body);
  const o = parse(r.out);
  check("ad_infos_map -> {}", o && Object.keys(o.ad_infos_map).length === 0, JSON.stringify(o));
  check("素材不再下发", o && !JSON.stringify(o).includes("launch_id"));
}

console.log("\n== 3. upsell：删广告弹窗与商城弹窗，保留其它 ==");
{
  const body = {
    status_code: 0,
    upsell_map: {
      browse_mall_popup_acc_amount: { popup: { event: { params: { task_name: "逛商城赚金币" } } } },
      preview_popup_ads: { popup: {} },
      cold_launch_popup_ads_progress: { popup: {} },
      reward_ad_cold_launch_popup: { popup: {} },
      coin_widget: { widget: {} },
      task_page_svip_popup: { popup: {} },
      reward_video_load_fail_compensate: { popup: {} }
    },
    sort_control_unique_names: ["coin_widget", "preview_popup_ads", "browse_mall_popup_acc_amount"],
    cold_launch_timing: {
      upsell_item_unique_names: ["cold_launch_popup_ads_progress", "coin_widget"]
    },
    variables: { ads_days_obtained: "if(...)", is_svip: "..." }
  };
  const r = run("https://beta-luna.douyin.com/luna/commerce/v2/upsell", body);
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
  check("variables 不动", !!o.variables && !!o.variables.ads_days_obtained);
}

console.log("\n== 4. 演出（汽水音乐节）：detail_list 清空 ==");
{
  const body = {
    status_code: 0,
    detail_list: [
      { id: "26", title: "汽水音乐节", performance_stop_name: "常州站", price_desc: "198" }
    ]
  };
  const r = run("https://beta-luna.douyin.com/luna/growth/music_festival/performance_details", body);
  const o = parse(r.out);
  check("detail_list -> []", o && Array.isArray(o.detail_list) && o.detail_list.length === 0,
    JSON.stringify(o));
}

console.log("\n== 5. 未匹配的接口：原样放行 ==");
{
  const r = run("https://beta-luna.douyin.com/luna/treasure/task/box/do_action", { status_code: 0 });
  check("不改写响应", !(r.out && r.out.body), JSON.stringify(r.out));
}

console.log("\n== 6. 非 JSON：原样放行 ==");
{
  const r = run("https://beta-luna.douyin.com/luna/advert/incentive/config", "{oops");
  check("不改写响应", !(r.out && r.out.body), JSON.stringify(r.out));
}

console.log("\n" + (fail === 0 ? "ALL PASS" : "FAILURES") +
  "  pass=" + pass + " fail=" + fail);
process.exit(fail === 0 ? 0 : 1);
