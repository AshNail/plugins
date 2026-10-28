# MBA大师 · 去广告

> MBA大师（mbajm）开屏走穿山甲,课程列表插屏走优量汇;讲义/题库内嵌不可分。看广告领课程依赖这些 SDK——启用即断。零证书。

版本 **1.0.0** ｜ 最低 Loon **3.5.1(983)** ｜ 零证书 · 零 MITM · 零脚本（纯 `[Host]`/`[Rule]`）

## 安装

[![一键导入 mba-dashi.plugin](https://img.shields.io/badge/Loon-导入MBA%E5%A4%A7%E5%B8%88%20%C2%B7%20%E5%8E%BB%E5%B9%BF%E5%91%8A-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fmba-dashi%2Fmba-dashi.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/mba-dashi/mba-dashi.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| 穿山甲 / Pangle（字节跳动）（引用组） | A | 启用 | 看「激励视频/任务」的 App 慎用本组：断它 = 奖励类任务拿不到奖。 共 50 域 / 0 规则。 |
| 腾讯广告 / 优量汇（GDT）（引用组） | A | 启用 | 域名真源见 ads 组/SDK 库 共 10 域 / 0 规则。 |

## 红线与天花板（如实）

- 红线：www.mbajm.com / m.mbajm.com / file.mbajm.com / video.mbajm.com 全是讲义、课程、视频链路,绝不碰。
- 两家 SDK（穿山甲/优量汇）由官方隐私政策确认;域名映射为行业标准基建（B 级）。
- 本插件 [Host]/[Rule] 全设备生效(Loon 无法按 App 限定):同一 SDK 域跨 App 共享黑洞,'按 App 插件'只是分组开关;配合全局 ads 插件 httpdns 组防绕过。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/mba-dashi.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 60 条，[Rule] 0 条。
