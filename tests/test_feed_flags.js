const src = require("./load-script")("sanitize.js");

function run(url, obj) {
  let out = null, logs = [];
  new Function("$request", "$response", "$done", "console", "$argument", src)(
    { url }, { body: JSON.stringify(obj) },
    (v) => { out = v; },
    { log: (...a) => logs.push(a.join(" ")) },
    { rewardSafe: false, cleanAds: true, killRewardAds: true }
  );
  return { out, logs, body: out && out.body ? JSON.parse(out.body) : null };
}

let pass = 0, fail = 0;
function ck(name, cond, extra) {
  if (cond) { pass++; console.log("  PASS  " + name); }
  else { fail++; console.log("  FAIL  " + name + (extra ? " :: " + extra : "")); }
}

const url = "https://api.qishui.com/luna/feed/v2/list";

console.log("== explicit flags ==");
for (const key of ["is_advertisement", "isAdItem", "ad_flag", "adItem", "is_promoted", "is_sponsored", "is_commercial"]) {
  const r = run(url, { data: [{ id: 1, [key]: true, title: "ad" }, { id: 2, title: "ok" }] });
  ck(key + " 条目被删", r.body.data.length === 1 && r.body.data[0].id === 2, JSON.stringify(r.body));
}

console.log("== nested card flag ==");
{
  const r = run(url, {
    data: [
      { id: 1, card: { is_ad: true, title: "ad" }, cover: "x" },
      { id: 2, card: { is_ad: false, title: "ok" } }
    ]
  });
  ck("card.is_ad=true 外层被删", r.body.data.length === 1 && r.body.data[0].id === 2, JSON.stringify(r.body));
}

console.log("== explicit is_ad always drops, even with media ==");
{
  const r = run(url, {
    data: [
      { id: 1, is_ad: true, video: { url: "v" }, title: "ad with media" },
      { id: 2, ad_info: { x: 1 }, track: { id: 3 }, title: "normal with ad_info" }
    ]
  });
  ck("is_ad+media 删除", r.body.data.length === 1 && r.body.data[0].id === 2, JSON.stringify(r.body));
  ck("normal ad_info 被清", r.body.data[0].ad_info && Object.keys(r.body.data[0].ad_info).length === 0, JSON.stringify(r.body.data[0]));
}

console.log("== ads_info alone is kept, field cleared ==");
{
  const r = run(url, {
    data: [{ id: 1, ads_info: { a: 1 }, title: "featured" }]
  });
  ck("条目保留", r.body.data.length === 1, JSON.stringify(r.body));
  ck("ads_info 被清", r.body.data[0].ads_info && Object.keys(r.body.data[0].ads_info).length === 0, JSON.stringify(r.body.data[0]));
}

console.log("== ad_info only is dropped ==");
{
  const r = run(url, { data: [{ id: 1, ad_info: { a: 1 } }, { id: 2, title: "ok" }] });
  ck("纯 ad_info 条目被删", r.body.data.length === 1 && r.body.data[0].id === 2, JSON.stringify(r.body));
}

console.log("== audio_ad & mid_roll_ad containers cleared ==");
{
  const r = run(url, {
    audio_ad: { duration: 15 },
    mid_roll_ad: [{ ad_id: "x" }],
    search_banner: { ad_url: "y" },
    data: [{ id: 1, music: { name: "test" }, title: "song" }]
  });
  ck("audio_ad 被清", r.body.audio_ad && Object.keys(r.body.audio_ad).length === 0, JSON.stringify(r.body.audio_ad));
  ck("mid_roll_ad 被清", Array.isArray(r.body.mid_roll_ad) && r.body.mid_roll_ad.length === 0, JSON.stringify(r.body.mid_roll_ad));
  ck("search_banner 被清", r.body.search_banner && Object.keys(r.body.search_banner).length === 0, JSON.stringify(r.body.search_banner));
  ck("音乐条目保留", r.body.data.length === 1 && r.body.data[0].id === 1);
}

console.log("\n" + (fail === 0 ? "ALL PASS" : "FAILURES") + "  pass=" + pass + " fail=" + fail);
process.exit(fail ? 1 : 0);
