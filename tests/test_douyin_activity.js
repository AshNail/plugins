const load = require("./load-script");
const code = load("clean.js", "douyin");

const URL = "https://polaris.zijieapi.com/luckycat/activity/settings/get_dynamic_settings/?ver=60";

function run(body, argument, url) {
  let out = null;
  const logs = [];
  const fn = new Function(
    "$request", "$response", "$done", "console", "$argument", code
  );
  fn(
    { url: url || URL },
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

const real = require("./fixtures/douyin_activity_settings.json");
const INFO = real.data.activity_info;

console.log("\n== 1. 真实活动配置样本（181 个活动）==");
{
  check("样本活动数 = 181", Object.keys(INFO).length === 181, String(Object.keys(INFO).length));
  check("样本里有音乐节入口", !!INFO.music_festival);
  check("样本里有音乐节 v2", !!INFO.music_festival_v2);
  check("样本里有抖音运营活动", !!INFO.douyin_select_game_sjz);
}

console.log("\n== 2. 真实样本：这些活动本来就 canshow=false（区域未开） ==");
{
  const r = run(real, { cleanActivity: true });
  check("无需改动（原样放行）", !(r.out && r.out.body), JSON.stringify(r.out));
  let on = 0;
  for (const k of Object.keys(INFO)) {
    if (!/^(music_festival|douyin_select_)/.test(k)) continue;
    if (INFO[k].activity_common.canshow === true) on++;
  }
  check("样本里没有 canshow=true 的目标活动", on === 0, String(on));
}

console.log("\n== 2b. 模拟 canshow=true：应被置为 false ==");
{
  const body = {
    data: {
      activity_info: {
        music_festival: { activity_common: { canshow: true, forbid_reason: 0, time_table: null } },
        music_festival_v2: { activity_common: { canshow: true } },
        douyin_select_game_sjz: { activity_common: { canshow: true } },
        douyin_select_author_election: { activity_common: { canshow: true } },
        sign_in_activity: { activity_common: { canshow: true } },
        treasure_flip_card: { activity_common: { canshow: true } }
      }
    }
  };
  const o = parse(run(body, { cleanActivity: true }).out);
  check("返回了改写后的响应", !!o, JSON.stringify(run(body, { cleanActivity: true }).out));
  const info = o.data.activity_info;
  check("music_festival canshow=false", info.music_festival.activity_common.canshow === false);
  check("music_festival_v2 canshow=false", info.music_festival_v2.activity_common.canshow === false);
  check("douyin_select_game_sjz canshow=false", info.douyin_select_game_sjz.activity_common.canshow === false);
  check("douyin_select_author_election canshow=false",
    info.douyin_select_author_election.activity_common.canshow === false);
  check("其它活动（签到）不受影响", info.sign_in_activity.activity_common.canshow === true);
  check("其它活动（翻卡）不受影响", info.treasure_flip_card.activity_common.canshow === true);
  check("已有 forbid_reason 保持不变",
    info.music_festival.activity_common.forbid_reason === 0,
    String(info.music_festival.activity_common.forbid_reason));
  check("缺失 forbid_reason 时补 2",
    info.music_festival_v2.activity_common.forbid_reason === 2,
    String(info.music_festival_v2.activity_common.forbid_reason));
}

console.log("\n== 3. 真实样本：非目标活动完全不动 ==");
{
  const o = parse(run(real, { cleanActivity: true }).out);
  if (o) {
    const info = o.data.activity_info;
    let changed = 0;
    for (const k of Object.keys(INFO)) {
      if (/^(music_festival|douyin_select_)/.test(k)) continue;
      if (JSON.stringify(INFO[k]) !== JSON.stringify(info[k])) changed++;
    }
    check("非目标活动内容未变", changed === 0, String(changed));
    check("活动数量未变",
      Object.keys(info).length === Object.keys(INFO).length,
      Object.keys(info).length + " vs " + Object.keys(INFO).length);
  } else {
    check("真实样本原样放行（本来就都是 canshow=false）", true);
  }
}

console.log("\n== 4. cleanActivity 关闭：原样放行 ==");
{
  const r = run(real, { cleanActivity: false });
  check("不改写响应", !(r.out && r.out.body), JSON.stringify(r.out));
}

console.log("\n== 5. 已经 canshow=false 的条目不重复处理 ==");
{
  const body = {
    data: {
      activity_info: {
        music_festival: { activity_common: { canshow: false, forbid_reason: 5 } }
      }
    }
  };
  const r = run(body, { cleanActivity: true });
  const o = parse(r.out);
  check("未被改动（仍无 body）", !(r.out && r.out.body), JSON.stringify(r.out));
  check("forbid_reason 保持原值",
    o === null || o.data.activity_info.music_festival.activity_common.forbid_reason === 5);
}

console.log("\n" + (fail === 0 ? "ALL PASS" : "FAILURES") +
  "  pass=" + pass + " fail=" + fail);
process.exit(fail === 0 ? 0 : 1);
