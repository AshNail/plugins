# YouTube · 广告字段清理（原生 jq）

> 不复制可莉 YouTube 脚本：对 youtubei.googleapis.com 的 browse/next/player/search 等 JSON 响应，用 Loon 原生 response.json.jq 递归删除 adPlacements/playerAds/adSlots 等广告字段；不改播放地址、不碰 googlevideo 传输、不做上传/Shorts 功能开关。

版本 **1.0.0** ｜ 功能基线 Loon **3.5.1(983)**+ （iOS/tvOS 口径；Mac 版是 0.x 独立一条线，插件头不声明门槛）｜ 零证书 · 纯 `[Host]`/`[Rule]`（另含默认注释的可选 MITM 增强层，见下）

## 安装

[![一键导入 youtube.plugin](https://img.shields.io/badge/Loon-导入YouTube%20%C2%B7%20%E5%B9%BF%E5%91%8A%E5%AD%97%E6%AE%B5%E6%B8%85%E7%90%86%EF%BC%88%E5%8E%9F%E7%94%9F%20jq%EF%BC%89-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fyoutube%2Fyoutube.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/youtube/youtube.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|

## 可选 MITM 增强层（默认整段注释，不装证书 = 永不生效）

只做 YouTubei JSON 的广告字段删除：递归删除 adPlacements / playerAds / adSlots / adBreakHeartbeatParams / adBreakParams。不复制可莉脚本，不处理 googlevideo initplayback、上传、Shorts、字幕或日志事件参数。默认整段注释，先在非主力设备验证。

- 解密主机（`[MITM] hostname`，2 个）：`youtubei.googleapis.com`, `www.youtube.com`
- 配套 QUIC 回退（`AND,((DOMAIN-SUFFIX,<域>),(PROTOCOL,QUIC)),REJECT`，2 条，注释态）：MITM 只解密 TCP，App 走 HTTP/3 时 `URL-REGEX` 与 `response.json.jq` 都会静默失效；启用本层时应连同这些行一起取消注释。
- 路径级规则（`URL-REGEX`，1 条，命中即拦对应广告接口/素材，不影响同域功能请求）：

```text
# URL-REGEX,^https?://www\.youtube\.com/(?:pagead/|api/stats/ads),REJECT
```

- 响应 JSON 改写（`response.json.jq`，1 条，注释态）：MITM 解密后按公开模块的 jq 只删广告字段/节点、保留 mtop 包络；与 Response Script 二选一（本层不含脚本）。建议逐条启用、真机确认后再加下一条。

```text
# 来源 https://www.youtube.com/：YouTubei 响应递归删除广告字段；不改播放地址
# response if ${url} ~= /^https?:\/\/youtubei\.googleapis\.com\/youtubei\/v1\/(browse|next|player|search|reel\/reel_watch_sequence|guide|account\/get_setting|get_watch|log_event|config)(\?.*)?$/ then response.json.jq(`walk(if type == "object" then del(.adPlacements, .playerAds, .adSlots, .adBreakHeartbeatParams, .adBreakParams) else . end)`)
```

启用步骤：①Loon 装并信任证书 → ②取消插件内 `[MITM]` 头与 hostname 行注释 → ③取消 `[Rewrite]` 头与所需 `response.json.jq` 行的注释 → ④取消 `[Rule]` 头、QUIC 回退行与所需规则行的注释（`# [Rule]` 必须一起取消，否则规则会落在上一段的末尾而不生效）。

> 证书固定红线：银行/微信/米家类 App 做了证书固定，MITM 直接失败甚至触发风控，那些插件不提供本层；本层只对未做证书固定的 App 提供，且每条路径都有下方公开证据。

证据：
- https://www.youtube.com/

## 红线与天花板（如实）

- 红线：*.youtube.com / *.googlevideo.com / *.ytimg.com / youtubei.googleapis.com 承载登录、播放、缩略图与 API；本插件只做 youtubei JSON 广告字段清理，不黑洞整域，不改播放地址。
- 可莉 YouTube 插件是纯 response/request 脚本（含上传、Shorts、字幕、日志事件参数）；本插件不复制、不依赖，只实现可由 Loon 原生 jq 表达的广告字段删除。
- 响应规则只删除 adPlacements/playerAds/adSlots/adBreakHeartbeatParams/adBreakParams；不改播放 URL、不碰 googlevideo 的 initplayback，避免把视频本体拦掉。
- 证据基线：YouTubei 公开响应中的广告字段名；未在 2026-11-03 用 iOS/TV 真机逐端点验证，Mac 当前不执行 response jq，启用后先在非主力设备验证。
- 没有默认生效的 [Host]/[Rule]；MITM 与 Rewrite 整段默认注释，装证书后按需启用。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/youtube.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 0 条，[Rule] 0 条。
