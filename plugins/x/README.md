# X · 广告像素与遥测瘦身

> 如实定位:X 时间线推广推文与正常内容同 API 同 CDN(pbs/video.twimg.com),DNS 层 App 内广告减少≈0。本插件黑洞广告像素/嵌入 syndication/广告后台域——隐私收益真实,广告数量不变。零证书。

版本 **1.0.0** ｜ 最低 Loon **3.5.1(983)** ｜ 零证书 · 零 MITM · 零脚本（纯 `[Host]`/`[Rule]`）

## 安装

[![一键导入 x.plugin](https://img.shields.io/badge/Loon-导入X%20%C2%B7%20%E5%B9%BF%E5%91%8A%E5%83%8F%E7%B4%A0%E4%B8%8E%E9%81%A5%E6%B5%8B%E7%98%A6%E8%BA%AB-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fx%2Fx.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/x/x.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| 广告像素与嵌入（A 级,黑洞无损） | A | 启用 | ads-twitter.com/static=网页端转化像素;syndication/p/urls.api=第三方站点嵌入推文组件,X App 不用。 |
| 广告后台与客户端遥测（默认关） | B | 默认关闭 | ads*.twitter/x.com=广告管理控制台后端（黑洞不影响时间线广告,只断广告主后台）;analytics/scribe=统计与日志。不用广告主后台可开。 |

## 红线与天花板（如实）

- 红线（绝不进任何组）：t.co / *.twimg.com / api.twitter.com / x.com / twitter.com / api-stream.twitter.com——全部核心。
- AdGuard 官方口径:Twitter/X 广告与内容同服务器,DNS 拦截无法阻止,只能靠浏览器内容规则（MITM 层）——超出本插件约束。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/x.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 9 条，[Rule] 1 条。
