const load = require("./load-script");
const code = load("homepage-tabs.js", "soda");

const URL = "https://api.qishui.com/aweme/homepage/combine/?device_id=x";

function run(body, argument) {
  let out = null;
  const logs = [];
  const fn = new Function(
    "$request", "$response", "$done", "console", "$argument", code
  );
  fn(
    { url: URL },
    { body: typeof body === "string" ? body : JSON.stringify(body), headers: {} },
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

function ids(list) {
  return list.map((t) => t.tab_id || t.id).join(",");
}

function makeHomepageResponse() {
  return {
    status_code: 0,
    data: {
      bottom_tab_data: {
        tab_list: [
          { tab_id: "default_recommend", tab_name: "song_tab", tab_title: "推荐", schema: "luna://luna.com/song_tab" },
          { tab_id: "listen_douyin", tab_name: "listen_video_tab", tab_title: "听抖音", schema: "luna://luna.com/listen_video_tab" },
          { tab_id: "live", tab_name: "live_tab", tab_title: "直播", schema: "luna://luna.com/live_tab" },
          { tab_id: "video", tab_name: "video_tab", tab_title: "视频", schema: "luna://luna.com/video_tab" },
          { tab_id: "friend", tab_name: "friend_tab", tab_title: "朋友" },
          { tab_id: "community", tab_name: "community", tab_title: "社区" },
          { tab_id: "creation", tab_name: "creation_tools", tab_title: "创作" },
          { tab_id: "chat", tab_name: "chat_agent", tab_title: "AI 聊天" },
          { tab_id: "message", tab_name: "message_tab", tab_title: "消息" },
          { tab_id: "listen_together", tab_name: "listen_together", tab_title: "一起听" },
          { tab_id: "discover", tab_name: "discover_tab", tab_title: "发现" },
          { tab_id: "mine", tab_name: "me_tab", tab_title: "我的" }
        ]
      },
      other_data: { some_config: "keep_me" }
    }
  };
}

console.log("\n== 1. listenOnly=true：只留听歌相关 Tab ==");
{
  const r = run(makeHomepageResponse(), { listenOnly: true });
  const o = parse(r.out);
  const list = o && o.data.bottom_tab_data.tab_list;
  check("返回改写后的响应", !!o, JSON.stringify(r.out));
  check("推荐保留", list && list.some((t) => t.tab_id === "default_recommend"));
  check("发现保留", list && list.some((t) => t.tab_id === "discover"));
  check("我的保留", list && list.some((t) => t.tab_id === "mine"));
  check("听抖音移除", list && !list.some((t) => t.tab_id === "listen_douyin"));
  check("直播移除", list && !list.some((t) => t.tab_id === "live"));
  check("视频移除", list && !list.some((t) => t.tab_id === "video"));
  check("朋友移除", list && !list.some((t) => t.tab_id === "friend"));
  check("社区移除", list && !list.some((t) => t.tab_id === "community"));
  check("创作移除", list && !list.some((t) => t.tab_id === "creation"));
  check("AI 聊天移除", list && !list.some((t) => t.tab_id === "chat"));
  check("消息移除", list && !list.some((t) => t.tab_id === "message"));
  check("一起听移除", list && !list.some((t) => t.tab_id === "listen_together"));
  check("最终只剩 3 个 Tab", list && list.length === 3, list ? ids(list) : "");
  check("其它数据不受影响", o && o.data.other_data.some_config === "keep_me");
}

console.log("\n== 2. hideDouyinTab=true：只移除听抖音 ==");
{
  const r = run(makeHomepageResponse(), { hideDouyinTab: true });
  const o = parse(r.out);
  const list = o && o.data.bottom_tab_data.tab_list;
  check("听抖音移除", list && !list.some((t) => t.tab_id === "listen_douyin"));
  check("直播保留（hideDouyinTab 不动其它）", list && list.some((t) => t.tab_id === "live"));
  check("视频保留", list && list.some((t) => t.tab_id === "video"));
  check("最终剩 11 个 Tab", list && list.length === 11, list ? String(list.length) : "");
}

console.log("\n== 3. 两个开关都没开：原样放行 ==");
{
  const r = run(makeHomepageResponse(), {});
  check("不改写响应", !(r.out && r.out.body), JSON.stringify(r.out));
}

console.log("\n== 4. 没有可移除的 Tab：原样放行 ==");
{
  const body = {
    status_code: 0,
    data: { bottom_tab_data: { tab_list: [
      { tab_id: "default_recommend", tab_title: "推荐" },
      { tab_id: "mine", tab_title: "我的" }
    ] } }
  };
  const r = run(body, { listenOnly: true });
  check("不改写响应", !(r.out && r.out.body), JSON.stringify(r.out));
}

console.log("\n== 5. 奖励条目永久保护（即使标题含禁词） ==");
{
  const body = {
    status_code: 0,
    data: { tab_list: [
      { tab_id: "listen_douyin", tab_title: "听抖音领金币", reward: true },
      { tab_id: "live", tab_title: "直播奖励", incentive: "coin" },
      { tab_id: "video", tab_title: "视频" }
    ] }
  };
  const r = run(body, { listenOnly: true });
  const o = parse(r.out);
  const list = o && o.data.tab_list;
  check("带 reward 的听抖音条目保留", list && list.some((t) => t.tab_id === "listen_douyin"));
  check("带 incentive 的直播条目保留", list && list.some((t) => t.tab_id === "live"));
  check("普通视频条目仍移除", list && !list.some((t) => t.tab_id === "video"));
}

console.log("\n== 6. 深层嵌套 + schema 匹配 ==");
{
  const body = {
    status_code: 0,
    data: { page_config: { homepage_tabs: [
      { id: "song_tab", title: "推荐", schema: "luna://luna.com/song_tab" },
      { id: "tab_x", title: "神秘", schema: "luna://luna.com/listen-video-tab/module" },
      { id: "tab_y", title: "神秘2", schema: "luna://luna.com/live-tab" }
    ] } }
  };
  const r = run(body, { listenOnly: true });
  const o = parse(r.out);
  const list = o && o.data.page_config.homepage_tabs;
  check("schema 命中 listen-video-tab 被移除", list && !list.some((t) => t.id === "tab_x"));
  check("schema 命中 live-tab 被移除", list && !list.some((t) => t.id === "tab_y"));
  check("song_tab 保留", list && list.some((t) => t.id === "song_tab"));
}

console.log("\n== 7. 非 JSON / 空响应：原样放行 ==");
{
  check("非 JSON 放行", !(run("not json", { listenOnly: true }).out || {}).body);
  check("空响应放行", !(run("", { listenOnly: true }).out || {}).body);
}

console.log("\n" + (fail === 0 ? "ALL PASS" : "FAILURES") +
  "  pass=" + pass + " fail=" + fail);
process.exit(fail === 0 ? 0 : 1);
