# 米家 · 去广告（小米广告平台层）

> 如实定位:米家 App 首页运营卡片/商城推荐为第一方内嵌(api.io.mi.com 响应体),DNS 不可分。本插件黑洞小米统一广告平台(*.ad.xiaomi.com/o2o/有品推荐)——对 MIUI/澎湃系统投放有效,iOS 米家是否调用该平台未经抓包证实。设备控制/账号/推送域名零接触。零证书。

版本 **1.1.1** ｜ 最低 Loon **3.5.1(983)** ｜ 零证书 · 零 MITM · 零脚本（纯 `[Host]`/`[Rule]`）

## 安装

[![一键导入 mijia.plugin](https://img.shields.io/badge/Loon-导入%E7%B1%B3%E5%AE%B6%20%C2%B7%20%E5%8E%BB%E5%B9%BF%E5%91%8A%EF%BC%88%E5%B0%8F%E7%B1%B3%E5%B9%BF%E5%91%8A%E5%B9%B3%E5%8F%B0%E5%B1%82%EF%BC%89-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fmijia%2Fmijia.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/mijia/mijia.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| 小米统一广告平台 / MSA 投放 | A | 启用 | ad.xiaomi.com 全域成员(api/cdn/sdkconfig/ssp/test/zeus/new.api/diagnosis/track)+ ad1/ad.intl/api.admob + ad.mi.com + o2o.api（新零售广告）——anti-AD 与 edmon1024 小米专项清单一致收录。 |
| MIUI/澎湃系统广告与分析面（默认关，仅小米 Android 设备有感知） | A | 默认关闭 | 覆盖率审计（tools/app-coverage-audit.py）从 hagezi-xiaomi/anti-ad/AdGuard 反查出的小米系统面缺口：adv.sec=安全中心推荐位、activity/hot.browser=浏览器运营/热榜广告位、stat.youpin=有品推荐、stat.pandora=应用商店推荐、tracking.intl/rus=国际版遥测、inf/apm-rum/api.collect/cc/ccc/metok/geofence.sys=系统分析与定位采集、xiaomi-dtv.m.cn.miaozhen=秒针广告测量。对 iPhone/iPad 米家用户零效果；小米手机用户试开。安全组件（auth.be/api.sec/mazu/notify/logupdate 族）刻意不列——防诈与推送通道不许碰。 |
| 小米数据追踪/AB 实验（默认关） | B | 默认关闭 | mistat 与设备端远程配置可能同链——收益=隐私,风险=配置拉取,默认关,抓包确认再开。 |

## 红线与天花板（如实）

- 红线（误伤=掉设备,任何组绝不出现）：api.io.mi.com / app.io.mi.com / center.io.mi.com / token.io.mi.com / ot.io.mi.com / iothub.io.mi.com / account.xiaomi.com 系 / api.xmpush.xiaomi.com 系（营销推送与设备推送同通道,不可选择性拦截）/ miot-spec.org。
- 米家证书固定 + IoT 控制安全 → 明确不做 MITM;首页卡片/有品推荐/场景推荐随主 API 下发,DNS 层无解。
- iOS 预期设低:小米厂商广告 SDK 组主要作用于 Android/MIUI;本插件 iOS 净收益以抓包为准,先给开关不给承诺。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/mijia.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 42 条，[Rule] 0 条。
