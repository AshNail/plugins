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
 * 页面级广告开关同步收紧：migrate_first_ad 置 false，
 * ad_api_preload.task_ids 只留“仍在页面里的任务”引用的 id，
 * 一条不剩时 preload 也关掉，避免后台还在预拉被删任务的广告。
 *
 * 说明：这是“少看广告入口”的纯客户端裁剪，不改任何发奖字段，
 * 也不伪造领奖；被删掉的任务本来就要靠看广告/跨端跳转才能完成。
 */

const KEEP_SECTIONS = ["duration_task_section"];
const KEEP_TASKS = ["luna_rewards_ads"];

function isPlainObject(v) {
  return !!v && typeof v === "object" && !Array.isArray(v);
}

/*
 * 只保留仍在页面里的任务自己引用的预拉取 id：
 *   task.id / task.ad_snap.task_id / discrepancy_data.*.base_ad_diversion.id
 * 被裁掉的分区任务、以及页面快照里不存在的 id 一并丢弃；
 * 一条不剩时关掉 preload。保留下来的 luna_rewards_ads 若命中列表则不受影响。
 */
function collectRetainedTaskIds(sections, ids) {
  for (const section of sections) {
    if (!isPlainObject(section)) continue;
    const groups = [section.task_group, section.widget_task_group];
    for (const group of groups) {
      if (!isPlainObject(group) || !Array.isArray(group.tasks)) continue;
      for (const task of group.tasks) {
        if (!isPlainObject(task)) continue;
        if (task.id !== undefined && task.id !== null && task.id !== "") {
          ids[String(task.id)] = true;
        }
        if (isPlainObject(task.ad_snap) && task.ad_snap.task_id !== undefined) {
          ids[String(task.ad_snap.task_id)] = true;
        }
        const dd = task.discrepancy_data;
        if (!isPlainObject(dd)) continue;
        for (const k of Object.keys(dd)) {
          const sub = dd[k];
          if (isPlainObject(sub) && isPlainObject(sub.base_ad_diversion) &&
              sub.base_ad_diversion.id !== undefined) {
            ids[String(sub.base_ad_diversion.id)] = true;
          }
        }
      }
    }
  }
}

function pruneAdConfig(cfg, sections, log) {
  if (!isPlainObject(cfg)) return;

  if (cfg.migrate_first_ad === true) {
    cfg.migrate_first_ad = false;
    log.push("config.migrate_first_ad : true -> false");
  }

  const pre = cfg.ad_api_preload;
  if (!isPlainObject(pre) || !Array.isArray(pre.task_ids)) return;

  const ids = {};
  collectRetainedTaskIds(sections, ids);
  const kept = pre.task_ids.filter(function (id) {
    return ids[String(id)] === true;
  });
  if (kept.length !== pre.task_ids.length) {
    log.push("config.ad_api_preload.task_ids : " +
      pre.task_ids.length + " -> " + kept.length);
    pre.task_ids = kept;
  }
  if (pre.preload === true && pre.task_ids.length === 0) {
    pre.preload = false;
    log.push("config.ad_api_preload.preload : true -> false");
  }
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

  pruneAdConfig(data.config, kept, log);

  return true;
}

/* ------------------------------------------------------------------ */
/* 通用工具：插件参数 / 响应体解码 / 诊断标记                          */
/* ------------------------------------------------------------------ */
/* Loon 插件参数：兼容对象 / 位置数组 / "k=v" 字符串三种形态 */
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

/* Uint8Array -> UTF-8 字符串（不依赖 TextDecoder） */
function utf8(bytes) {
  var out = "", i = 0, n = bytes.length;
  while (i < n) {
    var b = bytes[i++] & 0xff;
    if (b < 0x80) {
      out += String.fromCharCode(b);
    } else if (b >= 0xc0 && b < 0xe0) {
      out += String.fromCharCode(((b & 0x1f) << 6) | (bytes[i++] & 0x3f));
    } else if (b >= 0xe0 && b < 0xf0) {
      out += String.fromCharCode(((b & 0x0f) << 12) | ((bytes[i++] & 0x3f) << 6) | (bytes[i++] & 0x3f));
    } else {
      var cp = ((b & 0x07) << 18) | ((bytes[i++] & 0x3f) << 12) | ((bytes[i++] & 0x3f) << 6) | (bytes[i++] & 0x3f);
      out += String.fromCodePoint(cp);
    }
  }
  return out;
}

/*
 * 取响应体：兼容三种情况
 *   1. 普通 JSON 字符串
 *   2. Uint8Array（binary_body_mode=true）
 *   3. gzip 压缩体（实测抖音/汽水这些接口都是 content-encoding: gzip，
 *      Loon 有时把“未解压的压缩串”交给脚本，此时直接 JSON.parse 会失败）
 * Build ≥ 988 有 $utils.ungzip；没有就原样返回，交给上层判断。
 */
function readBody(resp) {
  var raw = (resp && resp.body) || "";
  var bytes = null;
  if (typeof Uint8Array !== "undefined" && raw instanceof Uint8Array) {
    bytes = raw;
  } else if (typeof raw === "string" && raw.length > 1 &&
             raw.charCodeAt(0) === 0x1f && raw.charCodeAt(1) === 0x8b) {
    bytes = new Uint8Array(raw.length);
    for (var i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i) & 0xff;
  } else {
    return typeof raw === "string" ? raw : "";
  }
  try {
    if (typeof $utils !== "undefined" && $utils && typeof $utils.ungzip === "function") {
      return utf8($utils.ungzip(bytes));
    }
  } catch (e) {
    console.log("[douyin-treasure] ungzip failed: " + e);
  }
  return utf8(bytes);
}

/* 诊断标记：写进响应头，下一次抓包一眼看出脚本跑到哪一步 */
function markHeaders(reason) {
  try {
    var h = Object.assign({}, ($response && $response.headers) || {});
    h["X-Soda-Plugin"] = reason;
    return h;
  } catch (e) {
    return null;
  }
}

/* 福利页打卡：精简脚本默认胜出，若还等独立的 stamp 绑定就永远轮不到 */
function stampWelfare(args) {
  if (!pflag(args, "dailyReminder", false)) return;
  try {
    if (typeof $persistentStore === "undefined" || !$persistentStore ||
        typeof $persistentStore.write !== "function") return;
    var d = new Date();
    var m = String(d.getMonth() + 1);
    var day = String(d.getDate());
    var key = d.getFullYear() + "-" + (m.length < 2 ? "0" + m : m) + "-" +
      (day.length < 2 ? "0" + day : day);
    $persistentStore.write(key, "douyin-welfare-seen");
    console.log("[douyin-treasure] welfare stamp " + key);
  } catch (e) { /* 存储不可用不影响响应 */ }
}

(function main() {
  try {
    const url = ($request && $request.url) || "";
    if (!/\/luna\/treasure\/task\/page\/v[0-9]+/.test(url)) return $done({});

    const args = pargs(["treasureMinimal", "dailyReminder"]);
    stampWelfare(args);
    if (!pflag(args, "treasureMinimal", true)) {
      console.log("[douyin-treasure] treasureMinimal=off, passthrough: " + url);
      return $done({ headers: markHeaders("douyin-treasure;skip=switch-off") });
    }

    const raw = readBody($response);
    if (typeof raw !== "string" || raw.length === 0) {
      return $done({ headers: markHeaders("douyin-treasure;skip=no-body") });
    }
    const head = raw.trimStart().slice(0, 1);
    if (head !== "{" && head !== "[") {
      return $done({ headers: markHeaders("douyin-treasure;skip=not-json") });
    }

    let obj;
    try {
      obj = JSON.parse(raw);
    } catch (e) {
      console.log("[douyin-treasure] JSON parse failed, passthrough: " + url);
      return $done({ headers: markHeaders("douyin-treasure;skip=json-parse") });
    }

    const log = [];
    if (!pruneTreasure(obj, log)) {
      console.log("[douyin-treasure] unexpected shape, passthrough: " + url);
      return $done({ headers: markHeaders("douyin-treasure;skip=shape") });
    }

    if (log.length === 0) {
      console.log("[douyin-treasure] already minimal");
      return $done({ headers: markHeaders("douyin-treasure;noop=already-minimal") });
    }

    console.log(
      "[douyin-treasure] pruned " + log.length + " change(s)\n  " + log.join("\n  ")
    );
    $done({ body: JSON.stringify(obj), headers: markHeaders("douyin-treasure;pruned=" + log.length) });
  } catch (e) {
    console.log("[douyin-treasure] error, passthrough: " + e);
    $done({});
  }
})();
