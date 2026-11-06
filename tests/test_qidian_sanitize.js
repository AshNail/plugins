/*
 * qidian/auto-task.js · 响应净化的 gzip / 二进制体回归（v3.5.1）
 * ------------------------------------------------------------
 * 2026-11-06 16:21:50 真机日志：起点净化脚本 match/Trigger/Finished 一应俱全、getconf 0ms 结束，
 * 却一个字段没改。根因是 safeJsonParse：
 *   · 绑定没带 binary_body_mode，gzip 字节被按 UTF-8 解成字符串，1f 8b 魔数检测失效；
 *   · $utils.ungzip 官方签名是 Uint8Array → Uint8Array，旧代码对返回值直接 JSON.parse。
 * 断言：
 *   1. Uint8Array 的 gzip 体 + ungzip 返回 Uint8Array → getconf 被真的改写
 *   2. 改写后的响应头删掉过期的 content-encoding / content-length
 *   3. Uint8Array 明文字节（Loon 已替脚本解压）同样生效
 *   4. 字符串明文同样生效
 *   5. ungzip 缺失（Build < 988）→ 静默透传，不抛、不改 body
 *   6. ungzip 返回字符串的宽松实现同样可用
 *   7. deeplink 只清 ActionUrl，其余业务字段保留
 *   8. (v3.5.3) 回写形态跟随来路形态：字节进→字节出、字符串进→字符串出。
 *      真机判据是 16:21 日志「脚本 Finished 却零字段变更」——Loon 不替脚本解压 gzip，
 *      不带 binary_body_mode 时 $response.body 是 UTF-8 硬解的乱码串；而 v3.5.1 开了
 *      binary_body_mode 却回字符串，被 Loon 丢弃。两头必须同时成立，缺一个都是透传。
 */
const zlib = require("zlib");
const src = require("./load-script")("auto-task.js", "qidian");

function run(url, body, opts) {
  opts = opts || {};
  return new Promise((resolve) => {
    let out;
    const logs = [];
    const done = (v) => { out = v === undefined ? {} : v; resolve({ out, logs }); };
    const fn = new Function(
      "$request", "$response", "$done", "console", "$argument", "$utils",
      "$persistentStore", "$notification", "$httpClient", src
    );
    fn(
      { url, method: "GET", headers: {} },
      { body, headers: opts.headers || { "content-encoding": "gzip", "content-length": "99", server: "stub" } },
      done,
      { log: (...a) => logs.push(a.join(" ")) },
      { debugLog: "false", cleanAds: "true", autoTask: "false" },
      opts.utils,
      { read: () => null, write: () => true },
      { post: () => {} },
      {}
    );
    setTimeout(() => resolve({ out: out === undefined ? { __timeout: true } : out, logs }), 1500);
  });
}

let pass = 0, fail = 0;
function check(name, cond, extra) {
  if (cond) { pass++; console.log("  ok  " + name); }
  else { fail++; console.log("  FAIL " + name + (extra ? " :: " + extra : "")); }
}

const GETCONF = "https://magev6.if.qidian.com/argus/api/v1/client/getconf";
const conf = {
  Result: 0,
  Data: {
    PangleEnable: "1",
    SplashScreenInterval: 30,
    ActivityIcon: { a: 1 },
    GDT: { b: 2 },
    NewFeedsDiscover: 1,
    KeepMe: "yes",
    CloudSetting: { TeenShowFreq: "3" },
  },
};
const text = JSON.stringify(conf);
const gz = new Uint8Array(zlib.gzipSync(Buffer.from(text, "utf8")));
const realUtils = {
  ungzip: (bytes) => new Uint8Array(zlib.gunzipSync(Buffer.from(bytes))),
};

function parse(out) {
  if (!out || out.body === undefined) return null;
  const raw = out.body instanceof Uint8Array
    ? Buffer.from(out.body).toString("utf8")
    : out.body instanceof ArrayBuffer
      ? Buffer.from(new Uint8Array(out.body)).toString("utf8")
      : out.body;
  try { return JSON.parse(raw); } catch (e) { return null; }
}

// v3.5.3 契约：进字节必须回字节。binary_body_mode 下回字符串会被 Loon 静默丢弃
// （v3.5.1 就是这样「脚本跑完、字段没改」），所以这条断言挂了就是回归。
function shapeMatches(bodyIn, out) {
  const inBytes = bodyIn instanceof Uint8Array || bodyIn instanceof ArrayBuffer;
  const outBytes = out && (out.body instanceof Uint8Array || out.body instanceof ArrayBuffer);
  return inBytes === !!outBytes;
}

(async () => {
  console.log("\n[1] gzip 字节体 + ungzip→Uint8Array");
  {
    const { out } = await run(GETCONF, gz, { utils: realUtils });
    const j = parse(out);
    check("getconf 返回了改写后的 body", !!j, JSON.stringify(out).slice(0, 120));
    check("PangleEnable 被覆写为 0", j && j.Data.PangleEnable === "0", j && JSON.stringify(j.Data));
    check("ActivityIcon / GDT 被删除", j && j.Data.ActivityIcon === undefined && j.Data.GDT === undefined);
    check("NewFeedsDiscover 置 0", j && j.Data.NewFeedsDiscover === 0);
    check("TeenShowFreq 置 \"0\"", j && j.Data.CloudSetting.TeenShowFreq === "0");
    check("非广告字段保留", j && j.Data.KeepMe === "yes");
    const h = (out && out.headers) || {};
    check("过期的 content-encoding / content-length 已删",
      h["content-encoding"] === undefined && h["content-length"] === undefined, JSON.stringify(h));
    check("其它响应头保留", h.server === "stub");
    check("字节进 → 字节出（binary_body_mode 契约）", shapeMatches(gz, out), Object.prototype.toString.call(out && out.body));
  }

  console.log("\n[2] Uint8Array 明文字节（Loon 已解压）");
  {
    const bytes = new Uint8Array(Buffer.from(text, "utf8"));
    const { out } = await run(GETCONF, bytes, { utils: realUtils, headers: { server: "stub" } });
    const j = parse(out);
    check("明文字节也被净化", j && j.Data.PangleEnable === "0", JSON.stringify(out).slice(0, 120));
  }

  console.log("\n[3] 字符串明文");
  {
    const { out } = await run(GETCONF, text, { utils: realUtils, headers: { server: "stub" } });
    const j = parse(out);
    check("字符串明文被净化", j && j.Data.PangleEnable === "0");
    check("字符串进 → 字符串出", shapeMatches(text, out), Object.prototype.toString.call(out && out.body));
  }

  console.log("\n[4] ungzip 缺失（Build < 988）→ 静默透传");
  {
    const { out } = await run(GETCONF, gz, { utils: undefined });
    check("不抛、不带改写 body", out && out.body === undefined && !out.__timeout, JSON.stringify(out).slice(0, 120));
  }

  console.log("\n[5] ungzip 返回字符串的宽松实现");
  {
    const loose = { ungzip: (b) => zlib.gunzipSync(Buffer.from(b)).toString("utf8") };
    const { out } = await run(GETCONF, gz, { utils: loose });
    const j = parse(out);
    check("返回字符串同样可用", j && j.Data.PangleEnable === "0");
  }

  console.log("\n[6] deeplink 只清 ActionUrl");
  {
    const body = JSON.stringify({ Result: 0, Data: { ActionUrl: "QDReader://x", Keep: 7 } });
    const g = new Uint8Array(zlib.gzipSync(Buffer.from(body, "utf8")));
    const { out } = await run("https://magev6.if.qidian.com/argus/api/v3/deeplink/geturl", g, { utils: realUtils });
    const j = parse(out);
    check("ActionUrl 被清空", j && j.Data.ActionUrl === "", JSON.stringify(j));
    check("其余业务字段保留", j && j.Data.Keep === 7);
  }

  console.log("\n[7] CLEAN_RULES TDZ 回归（reddot/getdot · mainPageDialog · checkinexchangepage）");
  {
    const reddotBody = JSON.stringify({ Result: 0, Data: { Dots: [1, 2] } });
    const { out: r1 } = await run("https://magev6.if.qidian.com/argus/api/v1/reddot/getdot", reddotBody, { utils: realUtils });
    const j1 = parse(r1);
    check("reddot/getdot 不触发 TDZ 异常且成功删除 Data", j1 && j1.Data === undefined && j1.Result === 0, JSON.stringify(r1));

    const exchBody = JSON.stringify({ Result: 0, Data: { Goods: [{ id: 1 }], Balance: 100 } });
    const { out: r2 } = await run("https://h5.if.qidian.com/argus/api/v3/checkin/checkinexchangepage", exchBody, { utils: realUtils });
    const j2 = parse(r2);
    check("checkinexchangepage 删除 Data.Goods 并保留 Balance", j2 && j2.Data && j2.Data.Goods === undefined && j2.Data.Balance === 100, JSON.stringify(r2));
  }

  console.log("\n[8] 发现页 getsimplediscover 双族白名单（NEW_* 宫格 + DISCOVER_* 顶栏 tab）");
  {
    const discBody = JSON.stringify({
      Result: 0,
      Data: {
        Items: [
          { KeyName: "NEW_ZHUANQU" },
          { KeyName: "NEW_ZHUANLAN" },
          { KeyName: "NEW_SHUDAN" },
          { KeyName: "NEW_YOUXI" },
          { KeyName: "DISCOVER_TUIJIAN" },
          { KeyName: "DISCOVER_ZHUANLAN" },
          { KeyName: "DISCOVER_SHUDAN" },
          { KeyName: "DISCOVER_SHUTIE" },
          { KeyName: "DISCOVER_CAIDAN" },
        ],
      },
    });
    const { out } = await run("https://magev6.if.qidian.com/argus/api/v1/user/getsimplediscover", discBody, { utils: realUtils });
    const j = parse(out);
    const keys = j && j.Data && j.Data.Items ? j.Data.Items.map(i => i.KeyName) : [];
    check("发现页保留 6 项（3 宫格 + 3 顶栏 tab）", keys.length === 6 && keys.includes("DISCOVER_TUIJIAN") && !keys.includes("DISCOVER_SHUTIE"), JSON.stringify(keys));
  }

  console.log("\n[9] 账户页 getaccountpage 9 键删除 + FunctionButtonList 13→5 + FreshManGuideSwitch=0");
  {
    const accBody = JSON.stringify({
      Result: 0,
      Data: {
        BenefitButtonList: [1],
        ActiveActionUrl: "x",
        DianNiangUrl: "x",
        DianNiangWorldImage: "x",
        DianNiangWorldSwitch: 1,
        SchoolImage: "x",
        SchoolText: "x",
        SchoolUrl: "x",
        PursueBookCard: {},
        FreshManGuideSwitch: 1,
        FunctionButtonList: [
          { PositionMark: "mypagenew_WOFABUDE" },
          { PositionMark: "mypagenew_GUANZHUSHOUCANG" },
          { PositionMark: "mypagenew_WODEQUANDING" },
          { PositionMark: "mypagenew_LIULANJILU" },
          { PositionMark: "mypagenew_WODEDINGZHI" },
          { PositionMark: "mypagenew_VIPCENTER" },
          { PositionMark: "mypagenew_GAMECENTER" },
        ],
        UserBasicInfo: { NickName: "reader" },
      },
    });
    const { out } = await run("https://magev6.if.qidian.com/argus/api/v3/user/getaccountpage", accBody, { utils: realUtils });
    const j = parse(out);
    check("9 个营销键全部删除", j && j.Data.BenefitButtonList === undefined && j.Data.PursueBookCard === undefined && j.Data.DianNiangWorldSwitch === undefined);
    check("FunctionButtonList 过滤保留 5 项", j && Array.isArray(j.Data.FunctionButtonList) && j.Data.FunctionButtonList.length === 5);
    check("FreshManGuideSwitch 置为数值 0", j && j.Data.FreshManGuideSwitch === 0);
    check("UserBasicInfo 保留", j && j.Data.UserBasicInfo && j.Data.UserBasicInfo.NickName === "reader");
  }

  console.log("\n[10] 福利中心 mainPage 删 ActivityCenterModule/CharityModule、保 SurpriseBenefit、剪任务条目");
  {
    const mainBody = JSON.stringify({
      Result: 0,
      Data: {
        SurpriseBenefit: { Title: "限时福利" },
        ActivityCenterModule: { a: 1 },
        CharityModule: { b: 2 },
        MemberExclusiveTaskModule: { c: 3 },
        DailyBenefitModule: {
          RotateText: ["x"],
          TaskList: [
            { Title: "完成1个广告任务得奖励" },
            { Title: "做任务得白泽宇航员装扮" },
            { Title: "看视频得章节卡" },
          ],
        },
        BookList: [{ Name: "广告任务专区" }],
      },
    });
    const { out } = await run("https://h5.if.qidian.com/argus/api/v2/video/adv/mainPage", mainBody, { utils: realUtils });
    const j = parse(out);
    check("ActivityCenterModule 与 CharityModule 已删", j && j.Data.ActivityCenterModule === undefined && j.Data.CharityModule === undefined);
    check("SurpriseBenefit 限时福利保留", j && j.Data.SurpriseBenefit && j.Data.SurpriseBenefit.Title === "限时福利");
    check("广告任务/白泽装扮条目被剪除且正常任务保留", j && j.Data.DailyBenefitModule.TaskList.length === 1 && j.Data.DailyBenefitModule.TaskList[0].Title === "看视频得章节卡");
    check("书籍条目不误伤", j && j.Data.BookList[0].Name === "广告任务专区");
  }

  console.log("\nPASS=" + pass + " FAIL=" + fail);
  process.exit(fail ? 1 : 0);
})();
