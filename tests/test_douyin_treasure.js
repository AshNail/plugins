const load = require("./load-script");
const code = load("treasure.js", "douyin");

const TREASURE_URL = "https://beta-luna.douyin.com/luna/treasure/task/page/v2";

function makePage() {
  return {
    status_code: 0,
    status_info: { now: 1792495764, status_msg: "success" },
    data: {
      sections: [
        {
          key: "asset_section",
          type: 1,
          view: { title: { type: 1, plain_text: "我的资产" } },
          asset_group: { assets: [{ title: { plain_text: "金币" }, amount: 209 }] }
        },
        {
          key: "duration_task_section",
          type: 2,
          task_group: {
            tasks: [
              {
                id: "600590",
                key: "luna_rewards_ads",
                type: "",
                status: 1,
                can_show: true,
                view: {
                  title: { type: 1, plain_text: "攒时长 听歌不中断" },
                  button: {
                    text: { type: 1, plain_text: "领时长" },
                    action: "redirect",
                    schema:
                      "sslocal://luckydog/activity_task?luckydog_task_type=luna_watch_ads_settle_vip" +
                      "&luckydog_task_token=SECRET&extra={\"ad_type\":\"ads_get_duration\"}"
                  }
                },
                stats: {}
              }
            ]
          }
        },
        {
          key: "gold_task_section",
          type: 2,
          view: { title: { type: 1, plain_text: "做任务 赚金币" } },
          task_group: {
            tasks: [
              { id: "600585", key: "soda_music_sign_in", status: 1, can_show: true,
                view: { title: { plain_text: "签到得金币" } } },
              { id: "601013", key: "luna_treasure_shop", status: 1, can_show: true,
                view: { title: { plain_text: "逛街赚金币" } } },
              { id: "600572", key: "music_incentive_ad", status: 1, can_show: true,
                view: { title: { plain_text: "看广告赚金币" } } },
              { id: "600662", key: "luna_treasure_flip_card", status: 1, can_show: true,
                view: { title: { plain_text: "翻卡赢金币" } } },
              { id: "600625", key: "luna_treasure_red_packet_rain", status: 5, can_show: true,
                view: { title: { plain_text: "红包雨" } } }
            ]
          }
        },
        {
          key: "widget_task_section",
          type: 3,
          widget_task_group: {
            tasks: [
              { id: "600607", key: "music_ug_treasure", status: 1, can_show: true,
                view: { title: { plain_text: "开宝箱得金币" } } }
            ]
          }
        }
      ],
      feedback_schema: { reward_feedback_popup: { title: { plain_text: "恭喜累计获得奖励" } } },
      strategy: { style: { ui_theme: "green" } },
      namespace: "luna_incentive",
      config: {
        migrate_first_ad: true,
        ad_api_preload: {
          preload: true,
          task_ids: ["600607", "600585", "600625", "601039", "600662", "600572"]
        }
      }
    }
  };
}

function run(body, argument, url) {
  let out = null;
  const logs = [];
  const fn = new Function("$request", "$response", "$done", "console", "$argument", code);
  fn(
    { url: url || TREASURE_URL },
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

console.log("\n== 1. treasureMinimal=true：只留攒时长模块 ==");
{
  const r = run(makePage(), { treasureMinimal: true });
  const o = parse(r.out);
  check("有返回体", !!o, JSON.stringify(r.out));
  check("只剩 1 个分区", o && o.data.sections.length === 1, JSON.stringify(o && o.data.sections));
  check("分区是 duration_task_section",
    o && o.data.sections[0].key === "duration_task_section");
  check("只剩 1 个任务",
    o && o.data.sections[0].task_group.tasks.length === 1);
  check("任务是 luna_rewards_ads",
    o && o.data.sections[0].task_group.tasks[0].key === "luna_rewards_ads");
  check("攒时长标题保留",
    o && o.data.sections[0].task_group.tasks[0].view.title.plain_text === "攒时长 听歌不中断");
  check("按钮 schema 保留",
    o && /luna_watch_ads_settle_vip/.test(
      o.data.sections[0].task_group.tasks[0].view.button.schema));
}

console.log("\n== 2. 我的资产/签到/商城/看广告/翻卡/红包雨/开宝箱 都被移除 ==");
{
  const r = run(makePage(), { treasureMinimal: true });
  const o = parse(r.out);
  const s = JSON.stringify(o);
  check("没有 asset_section", s.indexOf("asset_section") === -1);
  check("没有 gold_task_section", s.indexOf("gold_task_section") === -1);
  check("没有 widget_task_section", s.indexOf("widget_task_section") === -1);
  check("没有签到任务", s.indexOf("soda_music_sign_in") === -1);
  check("没有商城任务", s.indexOf("luna_treasure_shop") === -1);
  check("没有看广告任务", s.indexOf("music_incentive_ad") === -1);
  check("没有翻卡任务", s.indexOf("luna_treasure_flip_card") === -1);
  check("没有红包雨任务", s.indexOf("luna_treasure_red_packet_rain") === -1);
  check("没有开宝箱任务", s.indexOf("music_ug_treasure") === -1);
}

console.log("\n== 3. 广告预拉取 id 清空 ==");
{
  const r = run(makePage(), { treasureMinimal: true });
  const o = parse(r.out);
  check("task_ids -> []",
    o && Array.isArray(o.data.config.ad_api_preload.task_ids) &&
    o.data.config.ad_api_preload.task_ids.length === 0,
    JSON.stringify(o && o.data.config));
}

console.log("\n== 4. treasureMinimal=false：原样放行 ==");
{
  const r = run(makePage(), { treasureMinimal: false });
  check("不改写响应", !(r.out && r.out.body), JSON.stringify(r.out));
  check("日志说明 passthrough",
    r.logs.join(" ").includes("treasureMinimal=off"), r.logs.join(" "));
}

console.log("\n== 5. 没有 $argument：按插件默认（treasureMinimal=true）执行 ==");
{
  const r = run(makePage());
  const o = parse(r.out);
  check("仍然精简（默认开）", o && o.data.sections.length === 1, JSON.stringify(o));
}

console.log("\n== 5b. 参数以数组/字符串形式传入也能识别 ==");
{
  const r1 = run(makePage(), [true]);
  const o1 = parse(r1.out);
  check("数组形式 -> 精简生效", o1 && o1.data.sections.length === 1, JSON.stringify(o1));
  const r2 = run(makePage(), "treasureMinimal=true");
  const o2 = parse(r2.out);
  check("字符串形式 -> 精简生效", o2 && o2.data.sections.length === 1, JSON.stringify(o2));
}

console.log("\n== 6. 非福利页接口：原样放行 ==");
{
  const r = run({ status_code: 0 }, { treasureMinimal: true },
    "https://beta-luna.douyin.com/luna/treasure/task/box/do_action");
  check("不改写响应", !(r.out && r.out.body), JSON.stringify(r.out));
}

console.log("\n== 7. 非 JSON：原样放行 ==");
{
  const r = run("{oops", { treasureMinimal: true });
  check("不改写响应", !(r.out && r.out.body), JSON.stringify(r.out));
}

console.log("\n== 8. 真实抓包样本（tests/fixtures/douyin_treasure_page.json）==");
{
  const real = require("./fixtures/douyin_treasure_page.json");
  const before = real.data.sections.length;
  const r = run(real, { treasureMinimal: true });
  const o = parse(r.out);
  check("真实响应有 " + before + " 个分区", before === 4, String(before));
  check("真实响应精简为 1 个分区", o && o.data.sections.length === 1,
    o ? JSON.stringify(o.data.sections.map((s) => s.key)) : JSON.stringify(r.out));
  check("保留的是攒时长分区",
    o && o.data.sections[0].key === "duration_task_section");
  check("保留的任务是 luna_rewards_ads",
    o && o.data.sections[0].task_group.tasks.length === 1 &&
    o.data.sections[0].task_group.tasks[0].key === "luna_rewards_ads",
    o ? JSON.stringify(o.data.sections[0].task_group.tasks.map((t) => t.key)) : "");
  check("广告预拉取 id 清空",
    o && Array.isArray(o.data.config.ad_api_preload.task_ids) &&
    o.data.config.ad_api_preload.task_ids.length === 0,
    o ? JSON.stringify(o.data.config.ad_api_preload) : "");
}

console.log("\n" + (fail === 0 ? "ALL PASS" : "FAILURES") +
  "  pass=" + pass + " fail=" + fail);
process.exit(fail === 0 ? 0 : 1);
