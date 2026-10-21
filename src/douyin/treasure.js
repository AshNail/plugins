/*
 * douyin · 福利页精简（Loon http-response 脚本）
 * ------------------------------------------------------------
 * 目标接口：https://beta-luna.douyin.com/luna/treasure/task/page/v2
 *
 * 实测结构（HAR: 381_1792495728793.har / 383_1792495850343.har）：
 *   data.sections[]            页面分区
 *     key = asset_section       我的资产（余额/提现）
 *     key = duration_task_section  攒时长 听歌不中断
 *           task_group.tasks[0].key = luna_rewards_ads
 *           按钮 schema = sslocal://luckydog/activity_task
 *                        ?luckydog_task_type=luna_watch_ads_settle_vip
 *                        &extra={"ad_type":"ads_get_duration", ...}
 *           → 该模块本质是“看广告结算 VIP 时长”，所以清广告会破坏它
 *     key = gold_task_section   做任务 赚金币
 *           soda_music_sign_in(签到得金币) / luna_treasure_shop(逛街赚金币=商城)
 *           music_incentive_ad(看广告赚金币) / luna_treasure_draw_duration(连续刷视频)
 *           luna_incentive_push_permission / luna_treasure_flip_card(翻卡赢金币)
 *           luna_treasure_red_packet_rain(红包雨)
 *     key = widget_task_section  开宝箱得金币（music_ug_treasure）
 *   data.config.ad_api_preload.task_ids  预拉取广告的 task_id 列表（9 个）
 *   data.feedback_schema         领奖反馈弹窗（保留）
 *
 * 精简策略：只保留【攒时长 听歌不中断】一个分区 + 它的那一个任务，
 * 其余分区（我的资产/做任务赚金币/开宝箱）整体移除；
 * 被移除任务的广告预拉取 id 一并清空，避免后台还在预拉广告。
 *
 * 说明：这是“少看广告入口”的纯客户端裁剪，不改任何发奖字段，
 * 也不伪造领奖；被删掉的任务本来就要靠看广告/跨端跳转才能完成。
 */

const KEEP_SECTIONS = ["duration_task_section"];
/* ------------------------------------------------------------------ */
/* Loon 插件参数（每个脚本独立内置）                                  */
/* ------------------------------------------------------------------ */
/* 新版 Script 语法（3.5.1(983)+）下 $argument 是对象，键为参数名； */
/* 旧版语法实测不会把开关值传进来，所以这里同时兼容对象 / 位置数组 / */
/* "k=v" 字符串三种形态，开关值也兼容 true / "true" / 1 / "1"。       */
function pargs(keys) {
  var o = {}, r;
  try { r = (typeof $argument === "undefined") ? null : $argument; } catch (e) { r = null; }
  if (r === null || r === undefined) return null;
  var t = Object.prototype.toString.call(r);
  if (t === "[object Object]") {
    for (var k in r) if (Object.prototype.hasOwnProperty.call(r, k)) o[k] = r[k];
    return o;
  }
  if (t === "[object Array]") {
    for (var i = 0; i < r.length && keys && i < keys.length; i++) o[keys[i]] = r[i];
    return o;
  }
  if (typeof r === "string") {
    var p = r.split(/[&;,]/);
    for (var j = 0; j < p.length; j++) {
      var kv = p[j].split("=");
      if (kv.length >= 2) o[kv[0].trim()] = kv.slice(1).join("=");
    }
    return o;
  }
  return null;
}

function pflag(args, name, fallback) {
  if (!args || !(name in args)) return fallback;
  var v = args[name];
  if (v === true || v === "true" || v === 1 || v === "1") return true;
  if (v === false || v === "false" || v === 0 || v === "0") return false;
  return fallback;
}

const KEEP_TASKS = ["luna_rewards_ads"];

function isPlainObject(v) {
  return !!v && typeof v === "object" && !Array.isArray(v);
}

function pruneTreasure(obj, log) {
  const data = obj && obj.data;
  if (!isPlainObject(data)) return false;

  const sections = data.sections;
  if (!Array.isArray(sections)) return false;

  const kept = [];
  for (const section of sections) {
    if (!isPlainObject(section) || KEEP_SECTIONS.indexOf(section.key) === -1) {
      log.push("drop section " + (section && section.key));
      continue;
    }
    const group = section.task_group || section.widget_task_group;
    if (isPlainObject(group) && Array.isArray(group.tasks)) {
      const tasks = group.tasks.filter(function (task) {
        return isPlainObject(task) && KEEP_TASKS.indexOf(task.key) !== -1;
      });
      if (tasks.length !== group.tasks.length) {
        log.push(
          section.key + " : kept " + tasks.length + "/" + group.tasks.length + " task(s)"
        );
      }
      group.tasks = tasks;
    }
    kept.push(section);
  }
  data.sections = kept;

  const cfg = data.config;
  if (isPlainObject(cfg) && isPlainObject(cfg.ad_api_preload) &&
      Array.isArray(cfg.ad_api_preload.task_ids)) {
    if (cfg.ad_api_preload.task_ids.length > 0) {
      log.push(
        "config.ad_api_preload.task_ids : " +
        cfg.ad_api_preload.task_ids.length + " -> 0"
      );
    }
    cfg.ad_api_preload.task_ids = [];
  }

  return true;
}

(function main() {
  try {
    const url = ($request && $request.url) || "";
    if (!/\/luna\/treasure\/task\/page\/v2/.test(url)) return $done({});

    const args = pargs(["treasureMinimal"]);
    if (!pflag(args, "treasureMinimal", true)) {
      console.log("[douyin-treasure] treasureMinimal=off, passthrough: " + url);
      return $done({});
    }

    const raw = ($response && $response.body) || "";
    if (typeof raw !== "string" || raw.length === 0) return $done({});
    const head = raw.trimStart().slice(0, 1);
    if (head !== "{" && head !== "[") return $done({});

    let obj;
    try {
      obj = JSON.parse(raw);
    } catch (e) {
      console.log("[douyin-treasure] JSON parse failed, passthrough: " + url);
      return $done({});
    }

    const log = [];
    if (!pruneTreasure(obj, log)) {
      console.log("[douyin-treasure] unexpected shape, passthrough: " + url);
      return $done({});
    }

    if (log.length === 0) {
      console.log("[douyin-treasure] already minimal");
      return $done({});
    }

    console.log(
      "[douyin-treasure] pruned " + log.length + " change(s)\n  " + log.join("\n  ")
    );
    $done({ body: JSON.stringify(obj) });
  } catch (e) {
    console.log("[douyin-treasure] error, passthrough: " + e);
    $done({});
  }
})();
