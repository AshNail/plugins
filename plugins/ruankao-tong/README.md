# 软考通 · 去广告

> 软考通（ixinz 系）开屏/课程列表插屏走穿山甲+优量汇;题库内容与广告同源不可分。看广告解锁真题依赖这些 SDK——启用即断。零证书。

版本 **1.0.1** ｜ 最低 Loon **3.5.1(983)** ｜ 零证书 · 零 MITM · 零脚本（纯 `[Host]`/`[Rule]`）

## 安装

[![一键导入 ruankao-tong.plugin](https://img.shields.io/badge/Loon-导入%E8%BD%AF%E8%80%83%E9%80%9A%20%C2%B7%20%E5%8E%BB%E5%B9%BF%E5%91%8A-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fruankao-tong%2Fruankao-tong.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/ruankao-tong/ruankao-tong.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| 穿山甲 / Pangle（字节跳动）（引用组） | A | 启用 | 看「激励视频/任务」的 App 慎用本组：断它 = 奖励类任务拿不到奖。 共 50 域 / 0 规则。 |
| 腾讯广告 / 优量汇（GDT）（引用组） | A | 启用 | 域名真源见 ads 组/SDK 库 共 10 域 / 0 规则。 |

## 红线与天花板（如实）

- 红线：www.ixinz.com 与 *.s2.ixinz.com 是课程/题库内容分发域,绝不碰。
- 隐私政策只给 SDK 包名（com.bytedance.sdk.openadsdk / com.qq.e.union）不给域名——域名由两家 SDK 公开集成文档补齐（B 级,但为行业标准基建）。
- 崩溃 SDK（shenzhou / crash.ixinz）第一方自建,网络层无从区分,不列。
- 本插件 [Host]/[Rule] 全设备生效(Loon 无法按 App 限定):同一 SDK 域跨 App 共享黑洞,'按 App 插件'只是分组开关;配合全局 ads 插件 httpdns 组防绕过。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/ruankao-tong.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 60 条，[Rule] 0 条。
