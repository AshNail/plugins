# Instagram · 像素与遥测瘦身

> 如实定位:IG 赞助帖内嵌 feed API(gateway/graph),素材与内容同 fbcdn——App 内广告 DNS 层≈0。黑洞 FB 转化像素、网页播放器 VAST 域与已死徽章服务;不碰 graph/gateway/fbcdn 主域。零证书。

版本 **1.0.0** ｜ 最低 Loon **3.5.1(983)** ｜ 零证书 · 零 MITM · 零脚本（纯 `[Host]`/`[Rule]`）

## 安装

[![一键导入 instagram.plugin](https://img.shields.io/badge/Loon-导入Instagram%20%C2%B7%20%E5%83%8F%E7%B4%A0%E4%B8%8E%E9%81%A5%E6%B5%8B%E7%98%A6%E8%BA%AB-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Finstagram%2Finstagram.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/instagram/instagram.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| FB 像素与专属广告端点（A 级） | A | 启用 | pixel.facebook.com=网页转化像素(Conversions API);an.facebook.com=网页播放器片头广告 VAST 标签;badges.instagram.com=已停用的旧徽章服务。 |
| netseer IP 关联遥测（默认关,纯隐私收益） | B | 默认关闭 | Meta 寄生在 fbcdn 域名空间下的客户端公网 IP 关联/归因遥测（AdguardFilters #217505 / hagezi #3010）——按完整后缀 REJECT 专属子域,绝不升级为整域 fbcdn。间接降低广告定向精度,不减少广告数量。 |
| Meta / Audience Network（FAN）（引用组） | A | 启用 | 域名真源见 ads 组/SDK 库 共 5 域 / 0 规则。 |

## 红线与天花板（如实）

- 红线（绝不进任何组）：gateway.instagram.com / graph.instagram.com / graph.facebook.com / api.facebook.com / edge-mqtt.facebook.com（推送=通知生死线）/ *.fbcdn.net 整域 / *.cdninstagram.com。
- anti-AD 收录 graph.instagram.com 属误杀高危项——本插件明确不采。
- an.facebook.com 是少数「真能少看到广告」的域,但只对网页播放器片头 VAST 生效,IG App 内 Reels 广告不走它——如实,不夸大。
- 本插件 [Host]/[Rule] 全设备生效(Loon 无法按 App 限定):同一 SDK 域跨 App 共享黑洞,'按 App 插件'只是分组开关;配合全局 ads 插件 httpdns 组防绕过。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/instagram.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 8 条，[Rule] 2 条。
