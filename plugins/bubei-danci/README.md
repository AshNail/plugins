# 不背单词 · 跟踪瘦身

> 如实结论:不背单词官方 SDK 目录(learnywhere.cn/lexis/sdklist 渲染取证)没有任何广告联盟——变现是酷币/会员内购,「去广告」对这个 App 实际=去跟踪。本插件只裁埋点组,友盟推送系默认关(拦了断签到提醒)。零证书。

版本 **1.0.1** ｜ 最低 Loon **3.5.1(983)** ｜ 零证书 · 零 MITM · 零脚本（纯 `[Host]`/`[Rule]`）

## 安装

[![一键导入 bubei-danci.plugin](https://img.shields.io/badge/Loon-导入%E4%B8%8D%E8%83%8C%E5%8D%95%E8%AF%8D%20%C2%B7%20%E8%B7%9F%E8%B8%AA%E7%98%A6%E8%BA%AB-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fbubei-danci%2Fbubei-danci.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/bubei-danci/bubei-danci.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| 站外埋点 | B | 启用 | ns.360wgjs.com 收录于 anti-AD/PiT 等三家列表;拦后无功能损失。 |
| 友盟统计/超链（默认关——会连 U-Push 一起断） | B | 默认关闭 | umeng.com 族是它的统计+推送+一键登录底座:DOMAIN-SUFFIX 整域拦=签到提醒与号码认证同断。只在「不在乎推送、只要隐私」时开。 |

## 红线与天花板（如实）

- 官方 SDK 目录全列:支付宝/微信 OpenSDK/友盟全家桶(统计/U-Push/分享/APM/U-Link 超链/一键登录+三大运营商通道/Agoo 长连接)/华为联运/各家推送/声通评测/爱加密/岳鹰 Crash——无穿山甲/优量汇/快手/百青藤。此前按「小厂爱用联盟」假设给本 App 配 SDK 组是错的,已撤回。
- 红线：learnywhere.cn 整主域(API+例句音频)/bbdc.cn/声通 isuntone/Agoo(阿里共享域不碰)/爱加密(拦可能被识别异常环境)/友盟一键登录通道(cmpassport/wosms/e189)。
- U-Link「智能超链」=营销归因(拉新转化),属跟踪面不属广告面;黑名单站外收录,拦了不影响学习功能。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/bubei-danci.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 1 条，[Rule] 1 条。
