# 智慧房东 · 去广告

> 智慧房东（uni-app 打包+多广告网络聚合）:穿山甲/优量汇/快手联盟/倍孜黑洞,开屏、插屏、信息流广告位加载失败即本插件生效方式。通通锁控门与个推收租提醒零接触。零证书。

版本 **1.0.1** ｜ 最低 Loon **3.5.1(983)** ｜ 零证书 · 零 MITM · 零脚本（纯 `[Host]`/`[Rule]`）

## 安装

[![一键导入 zhihuifangdong.plugin](https://img.shields.io/badge/Loon-导入%E6%99%BA%E6%85%A7%E6%88%BF%E4%B8%9C%20%C2%B7%20%E5%8E%BB%E5%B9%BF%E5%91%8A-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fzhihuifangdong%2Fzhihuifangdong.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/zhihuifangdong/zhihuifangdong.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| uni-AD/DCloud 与易推 DSP（默认关,需真机抓包） | C | 默认关闭 | ad.dcloud.net.cn/uniad.dcloud.net.cn 为 DCloud uni-AD 公开文档域名,但本 App 真实请求域未经抓包证实;adfunlink/adintl/qttunion 的官网域与投放域未分离——按 AdTiming/Ogury 教训默认关。 |
| 穿山甲 / Pangle（字节跳动）（引用组） | A | 启用 | 看「激励视频/任务」的 App 慎用本组：断它 = 奖励类任务拿不到奖。 共 50 域 / 0 规则。 |
| 腾讯广告 / 优量汇（GDT）（引用组） | A | 启用 | 域名真源见 ads 组/SDK 库 共 10 域 / 0 规则。 |
| 快手联盟 / 快手广告（引用组） | A | 启用 | 域名真源见 ads 组/SDK 库 共 16 域 / 0 规则。 |
| 百度广告 / 百青藤（引用组） | A | 启用 | 域名真源见 ads 组/SDK 库 共 13 域 / 0 规则。 |
| 倍孜广告聚合（Beizi）（引用组） | A | 启用 | 证据同 plugins/ads v2.3.1（TopOn 之外的第三方聚合）。 共 2 域 / 0 规则。 |

## 红线与天花板（如实）

- 红线（业务核心,绝不出现）：*.ttlock.com / servlet.ttlock.com（通通锁=智能门锁控制,拦了门开不了）/ getui / igexin 系（收租提醒推送）。
- 官方隐私政策明列:穿山甲(com.bytedance.sdk.openadsdk)/优量汇(com.qq.e)/快手(com.kwad.sdk)/倍孜(com.beizi.ad)/百度联盟/阿里妈妈/uni-AD/易推DSP——广告网络齐全,DNS 层净收益在 17 个目标 App 里最高。
- App Store 隐私标签含 THIRD_PARTY_ADVERTISING——第三方广告确证存在。
- 本插件 [Host]/[Rule] 全设备生效(Loon 无法按 App 限定):同一 SDK 域跨 App 共享黑洞,'按 App 插件'只是分组开关;配合全局 ads 插件 httpdns 组防绕过。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/zhihuifangdong.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 93 条，[Rule] 0 条。
