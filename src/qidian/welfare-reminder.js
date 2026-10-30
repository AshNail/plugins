/*
 * qidian · 每日任务/福利提醒（Loon cron 脚本 · 零 MITM · 零证书）
 * ------------------------------------------------------------
 * 机制依据（QDReader 5.9.468 主二进制 REA，2026-10-30）：
 *   - 领取层全部是风险 charger 端点：
 *     /argus/api/v1/readtime/{daymission,score,pk-reward}/pickup/risk、
 *     /v2/freshman/task/rewardFreshmanTask、/v4/recharge/task/{take,list}；
 *     服务端按 readingtaskprocessreport / calendarreport 记账的真实阅读与
 *     观看会话结算（时长户头在服务端：/v2/readtime/readpage 等）。
 *   - 领取动作没有「网络层可替跑」的合法路径：真实路径必须由人在 App 内走完，
 *     外部伪造领取事件 = IVT（插件不做）。
 *
 * 本脚本只做一件事：cron 时间到 → 发一条本地通知，点通知按 openUrl 直达
 * App 内任务/福利中心路由，提醒白天攒下的真实阅读/观看可以领了。
 * 不发起任何网络请求、不代打开 App、不代点「领取」。
 */

var OPEN_URL = "QDReader://usercenter/task";

try {
  if (typeof $notification !== "undefined" && $notification &&
      typeof $notification.post === "function") {
    $notification.post(
      "起点读书 · 任务/福利中心",
      "今天的阅读/观看任务可领",
      "点这条通知直达任务中心，确认真实完成的阅读时长与任务后自行领取。" +
        "领取接口（/pickup/risk）按服务端账本校验，插件只提醒不代领。",
      { "openUrl": OPEN_URL }
    );
    console.log("[qd-welfare-reminder] 提醒已发送");
  }
} catch (e) {
  console.log("[qd-welfare-reminder] 异常 " + e);
}

$done({});
