# 哔哩哔哩 · 去广告与精简

> 哔哩哔哩 iOS/iPadOS：遥测上报（dataflow/data/tracker）+ HTTPDNS 解析防劫持域（httpdns.bilivideo.com）走 [Host] 127.0.0.1 零证书黑洞；开屏/导航栏/首页推荐流广告走可选增强层（原生 response.json.jq 置空与过滤卡片，零 JS 脚本）；核心登录/视频播放/直播/图床严格设防红线。

版本 **1.0.0** ｜ 功能基线 Loon **3.5.1(983)**+ （iOS/tvOS 口径；Mac 版是 0.x 独立一条线，插件头不声明门槛）｜ 零证书 · 纯 `[Host]`/`[Rule]`（另含默认注释的可选 MITM 增强层，见下）

## 安装

[![一键导入 bilibili.plugin](https://img.shields.io/badge/Loon-导入%E5%93%94%E5%93%A9%E5%93%94%E5%93%A9%20%C2%B7%20%E5%8E%BB%E5%B9%BF%E5%91%8A%E4%B8%8E%E7%B2%BE%E7%AE%80-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fbilibili%2Fbilibili.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/bilibili/bilibili.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| 哔哩哔哩自建遥测 / 播放器埋点 / HTTPDNS 接口 | A | 启用 | dataflow.biliapi.com（4源，官方移动端数据流/遥测）、httpdns.bilivideo.com（3源，HTTPDNS 解析端点）、data.bilibili.com（2源，数据埋点上报）、tracker.chat.bilibili.com（1源，聊天/直播埋点）、ali-web-player-tracker.biliapi.net（1源，阿里播放器埋点）、hw-v2-web-player-tracker.biliapi.net（1源，华为播放器埋点）。DNS 映射 127.0.0.1 阻断。 |

## 可选 MITM 增强层（默认整段注释，不装证书 = 永不生效）

哔哩哔哩 iOS 的开屏广告、导航栏推广、首页推荐流广告卡片与核心业务 API 共用 app.bilibili.com，不可 DNS 黑洞整域。下列 4 条 response.json.jq 采用 Loon 原生 jq：①开屏配置 data.show 置空；②顶部与底部导航栏过滤会员购与游戏中心；③首页推荐流过滤商业广告卡片（cm_v2/cm_double_v9）与游戏卡片；④搜索广场过滤推广与游戏。另附 1 条可选 REJECT-DICT（splash 接口直接返回空字典）。整段默认注释，启用需安装证书。

- 解密主机（`[MITM] hostname`，1 个，注释态，取消注释才解密）：`app.bilibili.com`
- 配套 QUIC 回退（`AND,((DOMAIN-SUFFIX,<域>),(PROTOCOL,QUIC)),REJECT`，1 条，注释态）：MITM 只解密 TCP，App 走 HTTP/3 时 `URL-REGEX` 与 `response.json.jq` 都会静默失效；启用本层时应连同这些行一起取消注释。
- 路径级规则（`URL-REGEX`，1 条，命中即拦对应广告接口/素材，不影响同域功能请求）：

```text
# URL-REGEX,^https://app\.bilibili\.com/x/v2/splash/(list|show)(\?.*)?$,REJECT-DICT
```

- 响应 JSON 改写（`response.json.jq`，4 条，注释态）：MITM 解密后按公开模块的 jq 只删广告字段/节点、保留 mtop 包络；与 Response Script 二选一（本层不含脚本）。建议逐条启用、真机确认后再加下一条。

```text
# 来源 https://github.com/app2smile/rules/blob/master/plugin/bilibili.plugin：开屏广告：置空 data.show 广告配置
# response if ${url} ~= /^https?:\/\/app\.bilibili\.com\/x\/v2\/splash\/(list|show)(\?.*)?$/ then response.json.jq(`if (.data.show? != null) then .data.show = null else . end`)
# 来源 https://github.com/app2smile/rules/blob/master/plugin/bilibili.plugin：导航栏精简：过滤底栏会员购/发布与顶栏游戏中心
# response if ${url} ~= /^https?:\/\/app\.bilibili\.com\/x\/resource\/show\/tab\/v\d+(\?.*)?$/ then response.json.jq(`(if (.data.bottom? != null) then .data.bottom |= map(select(.name != "会员购" and .tab_id != "会员购Bottom" and .name != "发布")) else . end) | (if (.data.top? != null) then .data.top |= map(select(.name != "游戏中心")) else . end)`)
# 来源 https://github.com/app2smile/rules/blob/master/plugin/bilibili.plugin：推荐信息流：过滤商业广告卡片与推广游戏
# response if ${url} ~= /^https?:\/\/app\.bilibili\.com\/x\/v2\/feed\/index(\?.*)?$/ then response.json.jq(`if (.data.items? != null) then .data.items |= map(select(.card_type != "cm_v2" and .card_type != "cm_double_v9" and .card_goto != "game" and (.banner_item? == null or (.banner_item | all(.type != "ad"))))) else . end`)
# 来源 https://github.com/app2smile/rules/blob/master/plugin/bilibili.plugin：搜索广场：过滤热搜词中的游戏与广告推广
# response if ${url} ~= /^https?:\/\/app\.bilibili\.com\/x\/v2\/search\/square(\?.*)?$/ then response.json.jq(`if (.data? != null) then .data |= map(select(.type != "game" and .type != "ad")) else . end`)
```

启用步骤：①Loon 装并信任证书 → ②取消插件内 `[MITM]` 头与 hostname 行注释 → ③取消 `[Rewrite]` 头与所需 `response.json.jq` 行的注释 → ④取消 `[Rule]` 头、QUIC 回退行与所需规则行的注释（`# [Rule]` 必须一起取消，否则规则会落在上一段的末尾而不生效）。

> 证书固定红线：银行/微信/米家类 App 做了证书固定，MITM 直接失败甚至触发风控，那些插件不提供本层；本层只对未做证书固定的 App 提供，且每条路径都有下方公开证据。

证据：
- https://github.com/app2smile/rules/blob/master/plugin/bilibili.plugin
- https://github.com/ddgksf2013/ddgksf2013
- https://github.com/limbopro/Adblock4limbo/blob/main/Bilibili.conf

## 红线与天花板（如实）

- 红线（绝不进任何拦截组）：passport.bilibili.com 账号与安全登录网关 / api.bilibili.com 核心业务 API，视频/播放/稿件接口 / app.bilibili.com 移动端核心业务接口，启动/信息流/导航 / live.bilibili.com 直播核心业务 / message.bilibili.com 私信与消息通知长连接通道。
- 哔哩哔哩主站业务共享根域 *.bilibili.com，禁止整域通配。
- 哔哩哔哩移动 API 业务共享根域 *.biliapi.net，禁止整域通配。
- 哔哩哔哩开放平台业务共享根域 *.biliapi.com，禁止整域通配。
- 哔哩哔哩流媒体 CDN 业务共享根域 *.bilivideo.com，禁止整域通配。
- 哔哩哔哩静态图片与封面共享根域 *.hdslb.com，禁止整域通配。
- 能力天花板与原生设计：dataflow.biliapi.com、data.bilibili.com、tracker.chat.bilibili.com、ali-web-player-tracker.biliapi.net、hw-v2-web-player-tracker.biliapi.net、httpdns.bilivideo.com 六个自建遥测与 HTTPDNS 域走 [Host] 127.0.0.1 零证书黑洞；开屏与信息流商业广告位走可选增强层 Loon 原生 response.json.jq，零 JS 脚本。
- 证据：app2smile/rules、ddgksf2013、Adblock4limbo 公开规则库的 Bilibili 广告处置逻辑。本插件不搬运远程 JS，采用 Loon 原生 response.json.jq 与 REJECT-DICT 重写实现等价效果。整段默认注释，安装证书后按需启用。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/bilibili.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 6 条，[Rule] 0 条。
