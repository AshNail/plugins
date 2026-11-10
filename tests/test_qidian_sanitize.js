/*
 * qidian/auto-task.js · 响应净化的 gzip / 二进制体回归（v3.5.1）
 * ------------------------------------------------------------
 * 2026-11-06 16:21:50 真机日志：起点净化脚本 match/Trigger/Finished 一应俱全、getconf 0ms 结束，
 * 却一个字段没改。根因是 safeJsonParse：
 *   · 绑定没带 binary_body_mode，gzip 字节被按 UTF-8 解成字符串，1f 8b 魔数检测失效；
 *   · $utils.ungzip 官方签名是 Uint8Array → Uint8Array，旧代码对返回值直接 JSON.parse。
 * 断言：
 *   1. Uint8Array 的 gzip 体 + ungzip 返回 Uint8Array → getconf 被真的改写
 *   2. 改写后的响应头把过期的 content-encoding 就地改成 identity、content-length 改成新体字节数
 *      (v3.5.5 起不再删键——手册没保证 Loon 是替换还是合并脚本给的 headers，合并时删键＝不改)
 *   3. Uint8Array 明文字节（Loon 已替脚本解压）同样生效
 *   4. 字符串明文同样生效
 *   5. ungzip 缺失（Build < 988）→ 不改 body、不抛（v3.5.7 起会推 fail，不再静默）
 *   6. ungzip 返回字符串的宽松实现同样可用
 *   7. deeplink 只清 ActionUrl，其余业务字段保留
 *   8. (v3.5.3) 回写形态跟随来路形态：字节进→字节出、字符串进→字符串出。
 *      真机判据是 16:21 日志「脚本 Finished 却零字段变更」——不带 binary_body_mode 时
 *      gzip 字节被按 UTF-8 硬解成乱码串，1f 8b 检测失效。形态镜像按 $done 手册是冗余的
 *      （body 接受 String 或 Uint8Array），留着是因为它对两种 Loon 头合并语义都无害。
 *   9. (v3.5.4) X-Qidian-Plugin 头部带 `;b=<build>;in=<形态>`。
 *      ⚠ v3.5.4 那句「绑定 debug=true 就能把脚本 console 落主日志」已被 21:35:23 日志判死：
 *      两条净化绑定的 with debug 常开后，主日志仍是 0 条 [起点锚点]，而 match/Trigger/Finished
 *      齐全。官方口径是 console.log「向**当前脚本日志**写入一条记录」——主日志导出不含它，
 *      要看锚点只能在 App 内的脚本日志里看。头部标记依旧是唯一能远程取证的自证面。
 *   10. (v3.5.5) 两处：① 过期的 content-encoding/content-length 就地改写原键名（identity +
 *       新体字节数），原键不存在时不发明新头——手册没保证 Loon 对脚本 headers 是替换还是合并，
 *       合并语义下 `delete` 等于「不改」，原始 gzip 声明会套在明文新体上，App 解压失败回落缓存；
 *       ② getconf / 账户页 / 福利页把本次变更条数写成 `;n=<N>` 进同一个头：主日志没有脚本
 *       stdout，App 内日志又导不出来，条数只能跟着响应头走。
 *   11. (v3.5.6→v3.5.7) 同一串证据换个出口：调试模式开时 respondJson 回写前推 `ok`，
 *       v3.5.7 起 safeJsonParse 的每条失败分支也推 `fail`（ok/fail 各一个 15s 节流键）。
 *       改口的原因是 22:15 真机答复「调试模式开着、v356 绑定 19/19/19、锁屏零通知、UI 没净化」——
 *       只在成功侧推，就等于「解析失败」与「解析成功但没字段可改」在设备上同形，什么也排除不掉。
 *       顺带作废一条口径：`Finished execute` 齐全**不能**证明脚本内部没抛异常，v3.5.2 那次
 *       TDZ ReferenceError 就是从 catch 里空 $done() 走掉、日志照样打 Finished。
 *   12. (v3.5.7) 路线 B 主路：[Rewrite] 复写改成 Accept-Encoding: identity，上游不压，脚本拿到
 *       明文（本块用不带 content-encoding 的响应头跑明文字节）——主路上不再依赖
 *       binary_body_mode 给字节、$utils.ungzip 同步返回、手写 UTF-8 解码这三层真机未确认的前提；
 *       gzip 分支降级为「上游无视 identity」时的兜底。附带三条：来路没有压缩头就不发明它、
 *       明文却非 JSON 要推 fail、instanceof 认不出的对象形态判失败而非当已解析 JSON 透传。
 *   注意：主日志里 Trigger→Finished 的时长（0ms / 999ms 二态）**没有判读价值**——同一端点
 *   两种值都出现过，999ms 严格贴着 1s，是 Loon 异步 $done 的刷写节拍而不是脚本工作量。
 */
const zlib = require("zlib");
const src = require("./load-script")("auto-task.js", "qidian");

function run(url, body, opts) {
  opts = opts || {};
  return new Promise((resolve) => {
    let out;
    const logs = [];
    const posts = [];
    const done = (v) => { out = v === undefined ? {} : v; resolve({ out, logs, posts }); };
    const fn = new Function(
      "$request", "$response", "$done", "console", "$argument", "$utils",
      "$persistentStore", "$notification", "$httpClient", src
    );
    fn(
      { url, method: "GET", headers: {} },
      { body, headers: opts.headers || { "content-encoding": "gzip", "content-length": "99", server: "stub" } },
      done,
      { log: (...a) => logs.push(a.join(" ")) },
      { debugLog: opts.debug ? "true" : "false", cleanAds: "true", autoTask: "false" },
      opts.utils,
      { read: () => (opts.persistAt === undefined ? null : String(opts.persistAt)), write: () => true },
      { post: (...a) => posts.push(a) },
      {}
    );
    setTimeout(() => resolve({ out: out === undefined ? { __timeout: true } : out, logs, posts }), 1500);
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
    check("过期的 content-encoding 就地改写为 identity（不删键，防 Loon 合并头时漏掉原始 gzip 声明）",
      h["content-encoding"] === "identity", JSON.stringify(h));
    check("content-length 改写为新体字节数", Number(h["content-length"]) === out.body.length,
      h["content-length"] + " vs " + out.body.length);
    check("其它响应头保留", h.server === "stub");
    // v3.6.2 修复：统一返回字符串，不再根据来路形态返回不同形态
    check("字节进 → 字符串出（v3.6.2 修复）", typeof out.body === "string", Object.prototype.toString.call(out && out.body));
    check("X-Qidian-Plugin 带 build 与来路形态", String(h["X-Qidian-Plugin"] || "").includes(";b=") && String(h["X-Qidian-Plugin"] || "").includes(";in=u8"),
      String(h["X-Qidian-Plugin"]));
    check("变更条数也进头部（主日志没有脚本 stdout，一份 HAR 就要能读出改了几项）",
      Number(String(h["X-Qidian-Plugin"]).split(";n=")[1]) > 0, String(h["X-Qidian-Plugin"]));
  }

  console.log("\n[2] Uint8Array 明文字节（Loon 已解压）");
  {
    const bytes = new Uint8Array(Buffer.from(text, "utf8"));
    const { out } = await run(GETCONF, bytes, { utils: realUtils, headers: { server: "stub" } });
    const j = parse(out);
    check("明文字节也被净化", j && j.Data.PangleEnable === "0", JSON.stringify(out).slice(0, 120));
    const h2 = (out && out.headers) || {};
    check("原始未声明编码时不凭空加 content-encoding", h2["content-encoding"] === undefined && h2.server === "stub", JSON.stringify(h2));
  }

  console.log("\n[3] 字符串明文");
  {
    const { out } = await run(GETCONF, text, { utils: realUtils, headers: { server: "stub" } });
    const j = parse(out);
    check("字符串明文被净化", j && j.Data.PangleEnable === "0");
    check("字符串进 → 字符串出", shapeMatches(text, out), Object.prototype.toString.call(out && out.body));
    const mark = String(((out && out.headers) || {})["X-Qidian-Plugin"] || "");
    check("字符串形态也如实记进头部", mark.includes(";in=str"), mark);
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

  console.log("\n[10] 福利中心 mainPage 对齐 config REMOVE_KEYS（13 项含 SurpriseBenefit/VideoRewardTab/RedeemGifts）");
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
    check("SurpriseBenefit 已删（对齐 config REMOVE_KEYS）", j && j.Data.SurpriseBenefit === undefined);
    check("激励任务条目全量保留（v3.6.1 起不再剪枝）", j && j.Data.DailyBenefitModule.TaskList.length === 3
      && j.Data.DailyBenefitModule.TaskList.map(t => t.Title).join("|") === "完成1个广告任务得奖励|做任务得白泽宇航员装扮|看视频得章节卡");
    check("书籍条目不误伤", j && j.Data.BookList[0].Name === "广告任务专区");
  }

  console.log("\n[11] 取证通知（v3.5.6→v3.5.7）：调试模式开，改写成功与解析失败都推锁屏，各 15s 节流");
  {
    const quiet = await run(GETCONF, gz, { utils: realUtils });
    check("调试模式关时一条通知都不推", quiet.posts.length === 0, JSON.stringify(quiet.posts));

    const loud = await run(GETCONF, gz, { utils: realUtils, debug: true });
    const msg = (loud.posts[0] || []).join(" | ");
    check("调试模式开且改写成功时推 ok 并带 build/形态/n", loud.posts.length === 1
      && /b=\d+\.\d+\.\d+ 形态=u8 ok/.test(msg) && /n=\d+/.test(msg), msg);
    check("通知标题带端点", /getconf/.test(String((loud.posts[0] || [])[0] || "")), String((loud.posts[0] || [])[0] || ""));

    const throttled = await run(GETCONF, gz, { utils: realUtils, debug: true, persistAt: Date.now() });
    check("15s 内不重复推", throttled.posts.length === 0, JSON.stringify(throttled.posts));

    // v3.5.6 这条断言的是「透传不推」，而真机正是靠「零通知」反推出 respondJson 没走到——
    // 于是 v3.5.7 把失败侧也接上出口：同一条路径现在必须推 fail。
    const passthrough = await run(GETCONF, gz, { debug: true });
    const pmsg = (passthrough.posts[0] || []).join(" | ");
    check("ungzip 缺失的透传路径改推 fail（不再静默）", passthrough.posts.length === 1
      && /未改写·解析失败/.test(pmsg) && /ungzip 缺失/.test(pmsg), pmsg);
    check("fail 路径仍然不改 body", passthrough.out.body === undefined, JSON.stringify(passthrough.out));
  }

  console.log("\n[12] v3.5.7 路线 B 主路：identity 明文（无压缩头）走直解，坏体报出去");
  {
    const plainBytes = new Uint8Array(Buffer.from(JSON.stringify(conf), "utf8"));
    const main = await run(GETCONF, plainBytes, {
      debug: true,
      headers: { "content-type": "application/json;charset=utf-8", "content-length": "99", server: "stub" },
    });
    const mj = parse(main.out);
    check("明文字节体不需要 ungzip 就能改写", mj && mj.Data.PangleEnable === "0" && mj.Data.ActivityIcon === undefined,
      JSON.stringify(mj && mj.Data && Object.keys(mj.Data).slice(0, 4)));
    // v3.6.2 修复：统一返回字符串，不再根据来路形态返回不同形态
    check("回写形态是字符串（v3.6.2 修复）", typeof main.out.body === "string", typeof main.out.body);
    check("来路没有 content-encoding 就不发明它", main.out.headers["content-encoding"] === undefined,
      JSON.stringify(main.out.headers));
    check("content-length 就地改写成新体字节数", main.out.headers["content-length"] === String(main.out.body.length),
      main.out.headers["content-length"] + " vs " + main.out.body.length);
    check("identity 主路推的是 ok", /形态=u8 ok/.test((main.posts[0] || []).join(" | ")), JSON.stringify(main.posts));

    const junk = await run(GETCONF, new Uint8Array(Buffer.from("hello loon", "utf8")), { debug: true });
    check("明文却非 JSON ⇒ 推 fail 且带首段", junk.posts.length === 1
      && /parse 失败/.test((junk.posts[0] || []).join(" | ")) && /hello/.test((junk.posts[0] || []).join(" | ")),
      JSON.stringify(junk.posts));

    // 运行时桥接来的二进制包装一旦 instanceof 认不出，旧写法会把它当已解析 JSON 原样返回：
    // 下游要么 obj.Data===undefined 静默透传，要么被 stringify 成 {"0":31,…} 的坏包。
    const weird = Object.create(null);
    weird.Result = 0;
    const w = await run(GETCONF, weird, { debug: true });
    check("不认的 object 形态判失败而不是原样当 JSON 返回", w.out.body === undefined && w.out.headers === undefined,
      JSON.stringify(w.out));
    check("不认形态推 fail", w.posts.length === 1 && /不认的 object 形态/.test((w.posts[0] || []).join(" | ")),
      JSON.stringify(w.posts));

    const already = await run(GETCONF, JSON.parse(JSON.stringify(conf)), {});
    const aj = parse(already.out);
    check("已是朴素对象的来路仍然直接生效", aj && aj.Data.PangleEnable === "0");
  }

  console.log("\nPASS=" + pass + " FAIL=" + fail);
  process.exit(fail ? 1 : 0);
})();
