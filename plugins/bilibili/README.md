# B 站 · 去广告（仅广告面）

> 只吸收可莉 B 站插件的广告面：开屏、首页信息流、皮肤装备与广告位接口，用 Loon 原生 response.json.jq / URL-REGEX 重写；不包含 VIP 状态、青少年模式、地区 302、核心 api.bilibili.com/biliapi.net/playurl 拒绝，也不复制上游 JS。

版本 **1.0.0** ｜ 功能基线 Loon **3.5.1(983)**+ （iOS/tvOS 口径；Mac 版是 0.x 独立一条线，插件头不声明门槛）｜ 零证书 · 纯 `[Host]`/`[Rule]`（另含默认注释的可选 MITM 增强层，见下）

## 安装

[![一键导入 bilibili.plugin](https://img.shields.io/badge/Loon-导入B%20%E7%AB%99%20%C2%B7%20%E5%8E%BB%E5%B9%BF%E5%91%8A%EF%BC%88%E4%BB%85%E5%B9%BF%E5%91%8A%E9%9D%A2%EF%BC%89-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fbilibili%2Fbilibili.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/bilibili/bilibili.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|

## 可选 MITM 增强层（默认整段注释，不装证书 = 永不生效）

B 站广告面集中在开屏、首页信息流与皮肤装备。下列规则来自可莉 B 站 Pro 的广告部分，改写为 Loon 原生 response.json.jq / URL-REGEX；VIP、青少年、地区和核心播放 API 规则全部不吸收。默认整段注释，启用后先验开屏、首页、动态、播放和登录。

- 解密主机（`[MITM] hostname`，5 个）：`app.bilibili.com`, `api.bilibili.com`, `mobi.bilibili.com`, `api.live.bilibili.com`, `line3-h5-mobile-api.biligame.com`
- 配套 QUIC 回退（`AND,((DOMAIN-SUFFIX,<域>),(PROTOCOL,QUIC)),REJECT`，5 条，注释态）：MITM 只解密 TCP，App 走 HTTP/3 时 `URL-REGEX` 与 `response.json.jq` 都会静默失效；启用本层时应连同这些行一起取消注释。
- 路径级规则（`URL-REGEX`，5 条，命中即拦对应广告接口/素材，不影响同域功能请求）：

```text
# URL-REGEX,^https?://app\.bilibili\.com/x/app/home/splash,REJECT-DICT
# URL-REGEX,^https?://mobi\.bilibili\.com/open/splash,REJECT-DICT
# URL-REGEX,^https?://api\.bilibili\.com/pgc/activity/deliver/material/receive,REJECT-DICT
# URL-REGEX,^https?://line3-h5-mobile-api\.biligame\.com/game/live/large_card_material,REJECT-DICT
# URL-REGEX,^https?://api\.live\.bilibili\.com/xlive/e-commerce-interface/v1/ecommerce-user/get_shopping_info,REJECT-DICT
```

- 响应 JSON 改写（`response.json.jq`，5 条，注释态）：MITM 解密后按公开模块的 jq 只删广告字段/节点、保留 mtop 包络；与 Response Script 二选一（本层不含脚本）。建议逐条启用、真机确认后再加下一条。

```text
# 来源 https://kelee.one/：开屏 show/event_list 清空
# response if ${url} ~= /^https?:\/\/app\.bilibili\.com\/x\/v2\/splash\/(show|event\/list2)\?/ then response.json.jq(`.data |= with_entries(if .key | IN("show", "event_list") then .value = [] else . end)`)
# 来源 https://kelee.one/：开屏列表清空并拉长下一次刷新间隔
# response if ${url} ~= /^https?:\/\/app\.bilibili\.com\/x\/v2\/splash\/list\?/ then response.json.jq(`.data.show = [] | .data.list = [{}] | .data.max_time = 0 | .data.min_interval = 31536000 | .data.pull_interval = 31536000 | .data.keep_ids = []`)
# 来源 https://kelee.one/：首页信息流只保留普通视频卡
# response if ${url} ~= /^https?:\/\/app\.bilibili\.com\/x\/v2\/feed\/index\?/ then response.json.jq(`if .data.items then .data.items |= map(select((.banner_item == null) and (.ad_info == null) and (.card_goto == "av") and (.card_type | IN("small_cover_v2", "large_cover_single_v9", "large_cover_v1")))) end`)
# 来源 https://kelee.one/：story 流删除竖版广告与课程/游戏推广字段
# response if ${url} ~= /^https?:\/\/app\.bilibili\.com\/x\/v2\/feed\/index\/story\?/ then response.json.jq(`if .data.items then .data.items |= map(select((.ad_info == null) and (.card_goto | IN("vertical_ad_av", "vertical_ad_live", "vertical_ad_picture") | not)) | del(.story_cart_icon, .free_flow_toast, .image_infos, .course_info, .game_info)) end`)
# 来源 https://kelee.one/：皮肤接口删除 common_equip 广告装备
# response if ${url} ~= /^https?:\/\/app\.bilibili\.com\/x\/resource\/show\/skin\?/ then response.json.jq(`del(.data.common_equip)`)
```

启用步骤：①Loon 装并信任证书 → ②取消插件内 `[MITM]` 头与 hostname 行注释 → ③取消 `[Rewrite]` 头与所需 `response.json.jq` 行的注释 → ④取消 `[Rule]` 头、QUIC 回退行与所需规则行的注释（`# [Rule]` 必须一起取消，否则规则会落在上一段的末尾而不生效）。

> 证书固定红线：银行/微信/米家类 App 做了证书固定，MITM 直接失败甚至触发风控，那些插件不提供本层；本层只对未做证书固定的 App 提供，且每条路径都有下方公开证据。

证据：
- https://kelee.one/

## 红线与天花板（如实）

- 红线：*.bilibili.com / *.biliapi.com / *.biliapi.net / *.bilivideo.com / *.hdslb.com / *.biligame.com 承载登录、播放、CDN 与游戏；本插件只做广告路径，不黑洞整域。
- 可莉 B 站 Pro 的 VIP 状态、青少年模式、地区 302、核心 API 拒绝全部拒绝吸收；本插件只保留开屏/信息流/皮肤/广告位等广告面。
- 开屏用 response.json.jq 清空 show/event_list/list；信息流用原生 jq 过滤 banner/ad_info/vertical_ad 卡；不复制可莉 bilibili-json.js。
- 证据基线：可莉 B 站 Pro 插件的广告规则事实；未在 2026-11-03 逐条真机复测，启用后先验开屏、首页、动态、播放、登录。
- 没有默认生效的 [Host]/[Rule]；MITM 与 Rewrite 整段默认注释，装证书后逐条启用。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/bilibili.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 0 条，[Rule] 0 条。
