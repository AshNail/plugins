# 腾讯新闻 · 广告字段清理（原生 jq）

> 不搬 app2smile 远程 JS：腾讯新闻 iOS 的开屏/列表/专题广告位走 HTTPS JSON。本插件用 Loon 原生 response.json.jq 双规则清理——列表接口 adList 置空、专题/频道 widget_list 过滤 widget_type=ad_list；零 JS、零默认生效、不装证书永不生效。

版本 **1.0.0** ｜ 功能基线 Loon **3.5.1(983)**+ （iOS/tvOS 口径；Mac 版是 0.x 独立一条线，插件头不声明门槛）｜ 零证书 · 纯 `[Host]`/`[Rule]`（另含默认注释的可选 MITM 增强层，见下）

## 安装

[![一键导入 qqnews.plugin](https://img.shields.io/badge/Loon-导入%E8%85%BE%E8%AE%AF%E6%96%B0%E9%97%BB%20%C2%B7%20%E5%B9%BF%E5%91%8A%E5%AD%97%E6%AE%B5%E6%B8%85%E7%90%86%EF%BC%88%E5%8E%9F%E7%94%9F%20jq%EF%BC%89-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fqqnews%2Fqqnews.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/qqnews/qqnews.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|

## 可选 MITM 增强层（默认整段注释，不装证书 = 永不生效）

腾讯新闻的广告与正文共用 HTTPS JSON（news.ssp.qq.com、r.inews.qq.com），不可 DNS 黑洞。下列 2 条 response.json.jq 采用 Loon 原生 jq：①列表类接口（开屏/要闻/财经/地方专区）adList 广告数组置空；②专题详情/频道信息流（gw/page/event_detail、channel_feed）的 data.widget_list 过滤 widget_type=ad_list。不复制 app2smile 的远程脚本。另附 1 条可选 REJECT-DICT（news.ssp.qq.com/app 整个开屏配置接口返回空字典，比 jq 更激进：未经真机逐端点验证，确认 App 行为正常后再启用）。整段默认注释，启用需安装证书。

- 解密主机（`[MITM] hostname`，2 个，注释态，取消注释才解密）：`news.ssp.qq.com`, `r.inews.qq.com`
- 配套 QUIC 回退（`AND,((DOMAIN-SUFFIX,<域>),(PROTOCOL,QUIC)),REJECT`，2 条，注释态）：MITM 只解密 TCP，App 走 HTTP/3 时 `URL-REGEX` 与 `response.json.jq` 都会静默失效；启用本层时应连同这些行一起取消注释。
- 路径级规则（`URL-REGEX`，1 条，命中即拦对应广告接口/素材，不影响同域功能请求）：

```text
# URL-REGEX,^https://news\.ssp\.qq\.com/app(\?.*)?$,REJECT-DICT
```

- 响应 JSON 改写（`response.json.jq`，2 条，注释态）：MITM 解密后按公开模块的 jq 只删广告字段/节点、保留 mtop 包络；与 Response Script 二选一（本层不含脚本）。建议逐条启用、真机确认后再加下一条。

```text
# 来源 https://github.com/app2smile/rules/blob/master/js/qq-news.js：开屏/要闻/财经/地方专区等列表接口：adList 广告数组置空（app2smile qq-news.js 分支，忽略缺失字段）
# response if ${url} ~= /^https?:\/\/(news\.ssp\.qq\.com\/app|r\.inews\.qq\.com\/(getQQNewsUnreadList|getTagFeedList|news_feed\/hot_module_list))(\?.*)?$/ then response.json.jq(`.adList = null`)
# 来源 https://github.com/app2smile/rules/blob/master/js/qq-news.js：专题详情/频道信息流：data.widget_list 过滤 widget_type=ad_list 的广告 widget（app2smile qq-news.js removeAdList()）
# response if ${url} ~= /^https?:\/\/r\.inews\.qq\.com\/gw\/page\/(event_detail|channel_feed)(\?.*)?$/ then response.json.jq(`if (.data.widget_list? != null) then .data.widget_list |= map(select(.widget_type != "ad_list")) else . end`)
```

启用步骤：①Loon 装并信任证书 → ②取消插件内 `[MITM]` 头与 hostname 行注释 → ③取消 `[Rewrite]` 头与所需 `response.json.jq` 行的注释 → ④取消 `[Rule]` 头、QUIC 回退行与所需规则行的注释（`# [Rule]` 必须一起取消，否则规则会落在上一段的末尾而不生效）。

> 证书固定红线：银行/微信/米家类 App 做了证书固定，MITM 直接失败甚至触发风控，那些插件不提供本层；本层只对未做证书固定的 App 提供，且每条路径都有下方公开证据。

证据：
- https://github.com/app2smile/rules/blob/master/plugin/qqnews.plugin
- https://github.com/app2smile/rules/blob/master/js/qq-news.js

## 红线与天花板（如实）

- 红线（绝不进任何拦截组）：news.ssp.qq.com 是腾讯新闻开屏页与频道配置接口主机；r.inews.qq.com 是腾讯新闻要闻/频道/专题/评论接口主机，正文与广告同主机——DNS 黑洞整域 = 新闻页白屏重试。本插件只做「装证书后按需启用」的 JSON 广告字段清理，默认无任何生效条目。
- 本插件不黑洞任何域；MITM 与 [Rewrite] 整段默认注释，装证书后按需启用。
- 证据：app2smile/rules（MIT License）公开插件 qqnews.plugin + 脚本 js/qq-news.js 的广告处置逻辑（adList→null；widget_list 过滤 widget_type=ad_list），本插件不复制其远程脚本、改用 Loon 原生 response.json.jq 重写实现等价效果。app2smile 标记为「弃用/待验证」的 getTwentyFourHourNews、getQQNewsListItems、gw/event/list 端点一律不收。
- 未在 2026-11-06 用 iOS 真机逐端点验证；Mac 当前不执行 response jq，启用后请先在非主力设备验证。
- 可选 REJECT-DICT 只命中 news.ssp.qq.com/app（app2smile 同路径），返回 200 + {}；与 jq 层二选一即可，不推荐同时启用。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/qqnews.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 0 条，[Rule] 0 条。
