# 起点读书 · 去广告

> 起点读书:官方 SDK 清单声明穿山甲+腾讯七巧板(优量汇系)——两组装备黑洞 + 起点自有广告统计端点(adstat.qidian.com/adsite.yuewen.com,官方政策自证)。Argus 广告位(magev6.if.qidian.com/adv)与章节内容同域,零 MITM 不可分。看「福利中心」视频领章节卡依赖 SDK,启用即断。零证书。

版本 **1.0.0** ｜ 最低 Loon **3.5.1(983)** ｜ 零证书 · 零 MITM · 零脚本（纯 `[Host]`/`[Rule]`）

## 安装

[![一键导入 qidian.plugin](https://img.shields.io/badge/Loon-导入%E8%B5%B7%E7%82%B9%E8%AF%BB%E4%B9%A6%20%C2%B7%20%E5%8E%BB%E5%B9%BF%E5%91%8A-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fqidian%2Fqidian.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/qidian/qidian.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| 起点/阅文自有广告与统计端点 | A | 启用 | adsite.yuewen.com=官方隐私政策自证「收集设备信息用于广告展示」；adstat.qidian.com=起点 2.5.0 后自有广告统计。qidianad.com=阅文自有广告域(anti-AD 收录,名称+清单双证)。 |
| 起点自家埋点（B 级,默认关） | B | 默认关闭 | tongji/dwtrack.qidian.com=站内统计(anti-AD 收录,拦了只断自家分析);o.if.qidian.com=anti-AD 独家拦但 if 命名空间同时承载内容 API,有误伤可能——先真机测试;qdp.qidian.com=起点推送,拦了断通知。log.1ting.com=听书线日志,无清单背书。 |
| 穿山甲 / Pangle（字节跳动）（引用组） | A | 启用 | 看「激励视频/任务」的 App 慎用本组：断它 = 奖励类任务拿不到奖。 共 50 域 / 0 规则。 |
| 腾讯广告 / 优量汇（GDT）（引用组） | A | 启用 | 域名真源见 ads 组/SDK 库 共 10 域 / 0 规则。 |

## 红线与天花板（如实）

- 官方声明源:acts.qidian.com/pact/sdk_table.html 列穿山甲(北京巨量引擎)+七巧板通用 SDK(深圳腾讯,程序化广告推送/监测/归因)+腾讯灯塔/Ostar 画像;未声明快手/百青藤/倍孜——未声明的联盟一律不加(纪律同 ads v2.4.0)。
- 红线（绝不进任何拦截组）：magev6.if.qidian.com（Argus 主 API:章节目录/书架与广告位 adv 同域同主机——黑洞=起点废掉）/ druid.if.qidian.com（章节目录）/ h5.if.qidian.com / cococdn.qidian.com / bookcover.yuewen.com / *.qidianalipay.com（广告图床与书城、充值共用）。
- adv/getadvlistbatch 路径证据:Yu9191 Rewrite 以 reject-200 拦此路径——路径级拦截需 MITM,超出本插件约束;DNS 层能切的是联盟填充那部分(开屏/插屏/横幅约一半,估计)。
- 本插件 [Host]/[Rule] 全设备生效(Loon 无法按 App 限定):同一 SDK 域跨 App 共享黑洞,'按 App' 只是分组开关。配合全局 ads 插件的 httpdns 组使用,否则黑洞可被 HTTPDNS 绕过。
- 本插件 [Host]/[Rule] 全设备生效(Loon 无法按 App 限定):同一 SDK 域跨 App 共享黑洞,'按 App 插件'只是分组开关;配合全局 ads 插件 httpdns 组防绕过。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/qidian.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 67 条，[Rule] 1 条。
