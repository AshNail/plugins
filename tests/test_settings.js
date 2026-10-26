const src = require("./load-script")("settings.js");

function run(body, url) {
  let out = null;
  const logs = [];
  const fn = new Function("$request", "$response", "$done", "console", "$argument", src);
  fn(
    { url: url || "https://conf.qishui.com/service/settings/v3/?device_id=x" },
    { body: body },
    (v) => { out = v; },
    { log: (...a) => logs.push(a.join(" ")) },
    { rewardSafe: false, settingsClean: true }
  );
  return { out, logs };
}

let pass = 0, fail = 0;
function check(name, cond, extra) {
  if (cond) { pass++; console.log("  ok  " + name); }
  else { fail++; console.log("  FAIL " + name + (extra ? " :: " + extra : "")); }
}

function parse(out) {
  if (!out || out.body === undefined) return null;
  try { return JSON.parse(out.body); } catch (e) { return null; }
}

function toggle(code, name) {
  return code
    .replace(`const ${name} = false;`, `const ${name} = true;`)
    .replace(new RegExp(`\\b${name}=!1\\b`), `${name}=!0`);
}

console.log("\n[1] flat dict / object config / JSON string config / scalar");
{
  const body = JSON.stringify({
    commerce_ad_config: { slots: [1, 2], enable: true },
    commerce_ad_feed_config: "{\"enable\":true,\"slots\":[3]}",
    reward_ad_fallback_config: { x: 1 },
    feed_reward_ad_config: "{\"x\":1}",
    splash_ad_early_load_config: { preload: true },
    splash_ad_config: { a: 1 },
    reward_ad_config: { b: 1 },
    feed_ad_config: { c: 1 },
    ad_reward_config: { d: 1 },
    incentive_advert_config: { e: 1 },
    feed_reward_ad_entrance: { f: 1 },
    commerce_libra_ad_config: { g: 1 },
    commerce_common_ad_config: { h: 1 },
    adn_group_config: [{ i: 1 }],
    splash_dsp_config: { j: 1 },
    preload_dsp_config: { k: 1 },
    splash_mannor_config: { l: 1 },
    ad_ignore_player_status_config: { m: 1 },
    switch_show_all_ad: true,
    enable_client_ads_strategy: true,
    preload_feed_ads: true,
    timor_should_enable_ad: true,
    kBasicModeDisableRewardAdEnabled: false,
    splash_ad_switch: true,
    advert_duration: 30,
    reward_details: { coins: 100 },
    hide_skip_ad_entry: false,
    normal_key: "keep"
  });
  const { out, logs } = run(body);
  const j = parse(out);
  check("returns body", !!j, JSON.stringify(out));
  check("object config emptied", JSON.stringify(j.commerce_ad_config) === "{}", JSON.stringify(j.commerce_ad_config));
  check("JSON string config emptied", j.commerce_ad_feed_config === "{}", JSON.stringify(j.commerce_ad_feed_config));
  check("fallback config emptied", JSON.stringify(j.reward_ad_fallback_config) === "{}");
  check("feed reward config emptied", j.feed_reward_ad_config === "{}");
  check("splash config emptied", JSON.stringify(j.splash_ad_early_load_config) === "{}");
  check("splash ad config emptied", JSON.stringify(j.splash_ad_config) === "{}");
  check("reward ad config emptied", JSON.stringify(j.reward_ad_config) === "{}");
  check("feed ad config emptied", JSON.stringify(j.feed_ad_config) === "{}");
  check("ad reward config emptied", JSON.stringify(j.ad_reward_config) === "{}");
  check("incentive advert config emptied", JSON.stringify(j.incentive_advert_config) === "{}");
  check("feed reward ad entrance emptied", JSON.stringify(j.feed_reward_ad_entrance) === "{}");
  const extraConfigs = ["commerce_libra_ad_config", "commerce_common_ad_config",
    "adn_group_config", "splash_dsp_config", "preload_dsp_config",
    "splash_mannor_config", "ad_ignore_player_status_config"];
  check("new ad configs emptied",
    extraConfigs.every((k) => Array.isArray(j[k])
      ? j[k].length === 0
      : JSON.stringify(j[k]) === "{}"),
    JSON.stringify(extraConfigs.map((k) => [k, j[k]])));
  check("switch_show_all_ad untouched by default", j.switch_show_all_ad === true);
  check("client ads strategy false", j.enable_client_ads_strategy === false);
  check("preload feed ads false", j.preload_feed_ads === false);
  check("timor untouched by default", j.timor_should_enable_ad === true, JSON.stringify(j.timor_should_enable_ad));
  check("basic mode disable true", j.kBasicModeDisableRewardAdEnabled === true);
  check("splash switch false", j.splash_ad_switch === false, JSON.stringify(j.splash_ad_switch));
  check("advert_duration untouched", j.advert_duration === 30);
  check("reward_details untouched", j.reward_details.coins === 100);
  check("hide_skip_ad_entry untouched", j.hide_skip_ad_entry === false);
  check("normal key kept", j.normal_key === "keep");
  check("log has changes", logs.join(" ").includes("[soda-settings]"), logs.join(" | "));
}

console.log("\n[2] nested { data: { settings: {...} } }");
{
  const body = JSON.stringify({
    data: {
      settings: {
        commerce_ad_config: "{\"enable\":true}",
        timor_should_enable_ad: "1",
        feed_reward_ad_config: { a: 1 }
      },
      version: 7
    }
  });
  const j = parse(run(body).out);
  check("nested config emptied", j.data.settings.commerce_ad_config === "{}", JSON.stringify(j.data.settings));
  check("nested timor untouched", j.data.settings.timor_should_enable_ad === "1", JSON.stringify(j.data.settings.timor_should_enable_ad));
  check("nested object emptied", JSON.stringify(j.data.settings.feed_reward_ad_config) === "{}");
  check("version kept", j.data.version === 7);
}

console.log("\n[3] key/value array");
{
  const body = JSON.stringify({
    data: [
      { key: "commerce_ad_config", value: "{\"enable\":true}" },
      { key: "timor_should_enable_ad", value: true },
      { key: "kBasicModeDisableRewardAdEnabled", value: 0 },
      { key: "advert_duration", value: 15 }
    ]
  });
  const j = parse(run(body).out);
  const arr = j.data;
  check("array config emptied", arr[0].value === "{}", JSON.stringify(arr[0]));
  check("array timor untouched", arr[1].value === true, JSON.stringify(arr[1]));
  check("array int -> 1", arr[2].value === 1, JSON.stringify(arr[2]));
  check("array duration kept", arr[3].value === 15);
}

console.log("\n[4] double-encoded JSON string");
{
  const inner = JSON.stringify({ commerce_ad_config: { x: 1 }, normal: 1 });
  const body = JSON.stringify(inner);
  const out = run(body).out;
  check("returns string body", typeof out.body === "string", typeof out.body);
  const outer = JSON.parse(out.body);
  check("outer remains string", typeof outer === "string", typeof outer);
  const j = JSON.parse(outer);
  check("inner config emptied", JSON.stringify(j.commerce_ad_config) === "{}");
  check("inner normal kept", j.normal === 1);
}

console.log("\n[5] no ad keys: passthrough");
{
  const body = JSON.stringify({ a: 1, b: { c: 2 } });
  const { out, logs } = run(body);
  check("no body rewrite", out.body === undefined, JSON.stringify(out));
  check("log says no change", logs.join(" ").includes("no ad setting change"), logs.join(" | "));
}

console.log("\n[6] non-JSON: passthrough");
{
  const { out, logs } = run("not json at all");
  check("no body rewrite", out.body === undefined);
  check("log non-JSON", logs.join(" ").includes("non-JSON"), logs.join(" | "));
}

console.log("\n[7] other URL: passthrough");
{
  const { out } = run(JSON.stringify({ commerce_ad_config: { x: 1 } }), "https://api.qishui.com/luna/ads/config");
  check("no body rewrite", out.body === undefined);
}

console.log("\n[8] aggressive off: ad_reward_position_exp untouched");
{
  const body = JSON.stringify({ ad_reward_position_exp: 1 });
  const j = parse(run(body).out);
  check("no body rewrite", j === null, JSON.stringify(j));
}

console.log("\n[9] aggressive on: ad_reward_position_exp -> 0");
{
  const aggressive = toggle(src, "AGGRESSIVE");
  let out = null;
  new Function("$request", "$response", "$done", "console", "$argument", aggressive)(
    { url: "https://conf.qishui.com/service/settings/v3/" },
    { body: JSON.stringify({ ad_reward_position_exp: 1, timor_should_enable_ad: "true", switch_show_all_ad: true }) },
    (v) => { out = v; },
    { log: () => {} },
    { rewardSafe: false, settingsClean: true }
  );
  const j = JSON.parse(out.body);
  check("position exp -> 0", j.ad_reward_position_exp === 0, JSON.stringify(j.ad_reward_position_exp));
  check("timor -> 'false'", j.timor_should_enable_ad === "false", JSON.stringify(j.timor_should_enable_ad));
  check("switch_show_all_ad -> false", j.switch_show_all_ad === false, JSON.stringify(j.switch_show_all_ad));
}

console.log("\n[10] dry run: body untouched");
{
  const dry = toggle(src, "DRY_RUN");
  let out = null;
  const logs = [];
  new Function("$request", "$response", "$done", "console", "$argument", dry)(
    { url: "https://conf.qishui.com/service/settings/v3/" },
    { body: JSON.stringify({ commerce_ad_config: { x: 1 } }) },
    (v) => { out = v; },
    { log: (...a) => logs.push(a.join(" ")) },
    { rewardSafe: false, settingsClean: true }
  );
  check("no body rewrite", out.body === undefined, JSON.stringify(out));
  check("logs change", logs.join(" ").includes("DRY_RUN"), logs.join(" | "));
}

console.log("\n[11] inject missing (opt-in)");
{
  const inject = toggle(src, "INJECT_MISSING");
  let out = null;
  new Function("$request", "$response", "$done", "console", "$argument", inject)(
    { url: "https://conf.qishui.com/service/settings/v3/" },
    { body: JSON.stringify({ normal: 1 }) },
    (v) => { out = v; },
    { log: () => {} },
    { rewardSafe: false, settingsClean: true }
  );
  const j = JSON.parse(out.body);
  check("commerce_ad_config injected", j.commerce_ad_config === "{}", JSON.stringify(j));
  check("feed_reward injected", j.feed_reward_ad_config === "{}");
  check("normal kept", j.normal === 1);

  let out2 = null;
  new Function("$request", "$response", "$done", "console", "$argument", inject)(
    { url: "https://conf.qishui.com/service/settings/v3/" },
    { body: JSON.stringify({ data: { settings: { normal: 2 } } }) },
    (v) => { out2 = v; },
    { log: () => {} },
    { rewardSafe: false, settingsClean: true }
  );
  const j2 = JSON.parse(out2.body);
  check("nested inject into settings", j2.data.settings.commerce_ad_config === "{}", JSON.stringify(j2));
  check("nested normal kept", j2.data.settings.normal === 2);
  check("root not polluted", j2.commerce_ad_config === undefined, JSON.stringify(j2));
}

console.log("\n[12] nested JSON string containing ad keys");
{
  const body = JSON.stringify({
    payload: JSON.stringify({ commerce_ad_config: { enable: true }, x: 1 })
  });
  const j = parse(run(body).out);
  const inner = JSON.parse(j.payload);
  check("inner config emptied", JSON.stringify(inner.commerce_ad_config) === "{}", JSON.stringify(inner));
  check("inner x kept", inner.x === 1);
}

console.log("\n[13] array of settings with normalized key variants");
{
  const body = JSON.stringify({
    settings: [
      { name: "commerce-ad-config", val: "{\"a\":1}" },
      { name: "enable_splash_ad", val: "true" }
    ]
  });
  const j = parse(run(body).out);
  check("dash key emptied", j.settings[0].val === "{}", JSON.stringify(j.settings[0]));
  check("snake enable false", j.settings[1].val === "false", JSON.stringify(j.settings[1]));
}

console.log("\n[14] no mutation of input on parse error inside nested string");
{
  const body = JSON.stringify({ payload: "{bad json", commerce_ad_config: { a: 1 } });
  const j = parse(run(body).out);
  check("bad nested kept", j.payload === "{bad json");
  check("config still emptied", JSON.stringify(j.commerce_ad_config) === "{}");
}

console.log("\n[15] SDK settings hosts (opt-in)");
{
  const body = JSON.stringify({ commerce_ad_config: { a: 1 }, normal: 1 });
  const j1 = parse(run(body, "https://i.snssdk.com/service/settings/v3/?x=1").out);
  check("i.snssdk.com config emptied", JSON.stringify(j1.commerce_ad_config) === "{}", JSON.stringify(j1));
  check("i.snssdk.com normal kept", j1.normal === 1);
  const j2 = parse(run(body, "https://is.snssdk.com/service/settings/v3/?x=1").out);
  check("is.snssdk.com config emptied", JSON.stringify(j2.commerce_ad_config) === "{}", JSON.stringify(j2));
  const r3 = run(body, "https://example.com/service/settings/v3/");
  check("other host passthrough", r3.out && r3.out.body === undefined, JSON.stringify(r3.out));
}

console.log("\n[16] BDADSDK settings shape (is.snssdk.com)");
{
  const body = JSON.stringify({
    settings: {
      adn_group_config: [{ id: 1 }],
      splash_ad_config: { a: 1 },
      normal: "keep"
    },
    ctx_infos: { app_id: 123, device_id: "d" },
    settings_time: 456
  });
  const j = parse(run(body, "https://is.snssdk.com/service/settings/v3/?caller_name=lynx").out);
  check("BDADSDK ad keys emptied",
    j.settings.adn_group_config.length === 0 &&
    JSON.stringify(j.settings.splash_ad_config) === "{}",
    JSON.stringify(j.settings));
  check("BDADSDK normal kept", j.settings.normal === "keep");
  check("BDADSDK ctx/settings_time kept",
    j.ctx_infos.device_id === "d" && j.settings_time === 456,
    JSON.stringify({ ctx_infos: j.ctx_infos, settings_time: j.settings_time }));
}

console.log("\n[17] shake / motion / cache ad configs suppression");
{
  const body = JSON.stringify({
    splash_shake_ad_config: { sensitivity: 10, enable: true },
    shake_ad_config: { motion: "shake" },
    splash_twist_ad_config: { degree: 45 },
    splash_ad_cache_config: { max_age: 3600 },
    enable_splash_shake: true,
    enable_shake_ad: true,
    enable_twist_ad: true,
    shake_ad_switch: true,
    splash_shake_sensitivity: 5,
    splash_cache_enable: true,
    enable_ad_preload: true,
    normal_feature: "active"
  });
  const j = parse(run(body).out);
  check("splash shake ad config emptied", JSON.stringify(j.splash_shake_ad_config) === "{}");
  check("shake ad config emptied", JSON.stringify(j.shake_ad_config) === "{}");
  check("splash twist ad config emptied", JSON.stringify(j.splash_twist_ad_config) === "{}");
  check("splash cache config emptied", JSON.stringify(j.splash_ad_cache_config) === "{}");
  check("enable_splash_shake false", j.enable_splash_shake === false);
  check("enable_shake_ad false", j.enable_shake_ad === false);
  check("enable_twist_ad false", j.enable_twist_ad === false);
  check("shake_ad_switch false", j.shake_ad_switch === false);
  check("splash_shake_sensitivity cleared", j.splash_shake_sensitivity === 0 || j.splash_shake_sensitivity === "");
  check("splash_cache_enable false", j.splash_cache_enable === false);
  check("enable_ad_preload false", j.enable_ad_preload === false);
  check("normal feature preserved", j.normal_feature === "active");
}

console.log("\n" + (fail === 0 ? "ALL PASS" : "FAILURES") + "  pass=" + pass + " fail=" + fail);
process.exit(fail === 0 ? 0 : 1);
