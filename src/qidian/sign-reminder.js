/*
 * qidian · 每日签到提醒（Loon cron 脚本 · 零 MITM · 零证书）
 * ------------------------------------------------------------
 * 机制依据（QDReader 5.9.468 主二进制 REA，2026-10-30）：
 *   - 签到通道 /argus/api/v1/checkin/{clientcheckin,autocheckin,videocheckin}
 *     全部要求 App 进程内 encryptSign 的请求签名；脚本层没有这个输入。
 *   - 「会员自动签到」是 App 自带特权：签到面板数据模型 QDCheckInInfoModelV2
 *     携带 btnMemberAutoCheckInTxt（会员自动签到按钮文案），签到成功侧挂
 *     QDMemberAutoCheckInSuccessNotification，调用链 autoCheckInRequestWithAutoCheckInCallBack:，
 *     端点 /argus/api/v1/checkin/autocheckin——服务端按会员身份放行。
 *     会员请在 App 内开启，那是合法形态的「自动签到」，不需要外部伪造。
 *   - App 也自带本地签到提醒（QDSignNotificationManager / bookshelf_sign_notification）。
 *
 * 本脚本只做一件事：cron 时间到 → 发一条本地通知，点通知按 openUrl 直达
 * App 内签到路由，人手完成真实签到。不发起任何网络请求、不代打卡、不代领取。
 */

var OPEN_URL = "QDReader://usercenter/sign";

try {
  if (typeof $notification !== "undefined" && $notification &&
      typeof $notification.post === "function") {
    $notification.post(
      "起点读书 · 今日签到",
      "连续签到别断（补签卡 / 连续奖励都看它）",
      "点这条通知直达起点签到页，在 App 内手动完成今日签到。" +
        "插件只提醒不代签——签到请求由 App 自身签名发起，外部伪造等于领取 IVT。" +
        "（会员可在签到面板开启自带「会员自动签到」）",
      { "openUrl": OPEN_URL }
    );
    console.log("[qd-sign-reminder] 提醒已发送");
  }
} catch (e) {
  console.log("[qd-sign-reminder] 异常 " + e);
}

$done({});
