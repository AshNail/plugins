# 哔哩哔哩 · 去广告与精简

> 哔哩哔哩 iOS/iPadOS：遥测上报（dataflow/data/tracker）+ HTTPDNS 解析防劫持域（httpdns.bilivideo.com）走 [Host] 127.0.0.1 零证书黑洞；同域开屏（含品牌/活动开屏）、导航栏、首页推荐流、视频详情页播放下相关推荐广告与搜索广场广告默认启用 Loon 原生 [Rewrite] v2 引擎复写（cleanAds / slimNav 开关默认开，零 JS 脚本）；核心登录/视频播放/直播/图床严格设防红线。前置：同域复写层需已安装并信任 Loon 证书。

版本 **1.2.1** ｜ 功能基线 Loon **3.5.1(983)**+ （iOS/tvOS 口径；Mac 版是 0.x 独立一条线，插件头不声明门槛）｜ 净化层默认启用（`[Argument]`+`[MITM]`+`[Script]` 三层已在文件里生效，须已装并信任 Loon 证书）· 拦截面 `[Host]`/`[Rule]`

## 安装

[![一键导入 bilibili.plugin](https://img.shields.io/badge/Loon-导入%E5%93%94%E5%93%A9%E5%93%94%E5%93%A9%20%C2%B7%20%E5%8E%BB%E5%B9%BF%E5%91%8A%E4%B8%8E%E7%B2%BE%E7%AE%80-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fbilibili%2Fbilibili.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/bilibili/bilibili.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| 哔哩哔哩自建遥测 / 播放器埋点 / HTTPDNS 接口 | A | 启用 | dataflow.biliapi.com（4源，官方移动端数据流/遥测）、httpdns.bilivideo.com（3源，HTTPDNS 解析端点）、data.bilibili.com（2源，数据埋点上报）、tracker.chat.bilibili.com（1源，聊天/直播埋点）、ali-web-player-tracker.biliapi.net（1源，阿里播放器埋点）、hw-v2-web-player-tracker.biliapi.net（1源，华为播放器埋点）。DNS 映射 127.0.0.1 阻断。 |
| QUIC 回退（增强层配套） | A | 启用 | 只对 `PROTOCOL,QUIC` 生效：拒的是 HTTP/3 这条通道、不是这台主机，同一主机的 TCP 正文/书架零影响。共 1 条。 |

## 默认启用的 MITM 层（本 App 未做证书固定；必须已装并信任 Loon 证书）

哔哩哔哩 iOS 的开屏广告、导航栏推广、首页推荐流广告卡片、视频详情页下推荐广告位与核心业务 API 共用 app.bilibili.com，不可 DNS 黑洞整域。本层默认启用 Loon 原生 [Rewrite] v2 引擎复写（由 cleanAds 与 slimNav 开关控制，零 JS 脚本）：① 开屏接口 x/v2/splash/(list|show|brand/list|event/list2) 在 request 阶段直接 reject_dict(200) 终止；② 首页推荐流过滤商业广告卡片（cm_v1/cm_v2/cm_double_v9/ad_av/ad_web_s）与游戏卡片；③ 视频详情页 x/v2/view 剔除播放下方商业组件（cm_config/cms/cm_ipad）及推荐列表广告项；④ 搜索广场过滤热搜中的推广与游戏；⑤ 顶部与底部导航栏过滤会员购/发布与游戏中心。

- 解密主机（`[MITM] hostname`，1 个，本层已默认生效）：`app.bilibili.com`
- 配套 QUIC 回退（`AND,((DOMAIN-SUFFIX,<域>),(PROTOCOL,QUIC)),REJECT`，1 条，已生效）：MITM 只解密 TCP，App 走 HTTP/3 时 `URL-REGEX`、`[Rewrite]` 复写与脚本绑定全部静默失效；它拒的是 QUIC 这条通道，同一主机的 TCP 请求零影响。

### 开关（`[Argument]`）

| 开关 | 默认 | 作用 |
|---|---|---|
| `cleanAds` | true | 启用 Loon 原生 [Rewrite] v2 引擎复写：开屏 splash/(list|show|brand/list|event/list2) 请求直接 reject_dict(200) 终止；推荐信息流过滤商业广告卡片（cm_v1/cm_v2/cm_double_v9/ad_av/ad_web_s）与推广游戏；视频详情页剔除播放下方广告组件与相关推荐广告；搜索广场过滤游戏与广告推广。需已安装并信任 Loon 证书。 |
| `slimNav` | true | 过滤底部导航栏「会员购/发布」与顶部导航栏「游戏中心」。 |

### 净化复写（`[Rewrite]`）

| 规则 | 阶段 | 动作 | 开关 | 行为 |
|---|---|---|---|---|
| `kill-splash` | request | `reject_dict` | `cleanAds` | 开屏广告列表、展示及品牌/活动开屏接口直接返回 200 + 空字典 |
| `kill-top-activity` | request | `reject_dict` | `slimNav` | 首页右上角活动推广挂件直接返回 200 + 空字典 |
| `clean-feed-index` | response | `response.json.jq` | `cleanAds` | 推荐信息流：按前缀通杀商业广告卡片（cm_*/ad_*）、ad_info 节点、推广游戏与横幅广告 |
| `clean-feed-story` | response | `response.json.jq` | `cleanAds` | 竖屏 Story 短视频流：剔除穿插的 ad_info / ad_* 广告视频 |
| `clean-view-relates` | response | `response.json.jq` | `cleanAds` | 视频详情页：剔除播放下方商业推广配置（cm_config/cms/cm_ipad）及关联推荐中的广告卡片 |
| `clean-search-square` | response | `response.json.jq` | `cleanAds` | 搜索广场：过滤热搜词中的游戏与广告推广 |
| `clean-nav-tab` | response | `response.json.jq` | `slimNav` | 导航栏精简：过滤底栏会员购/发布与顶栏游戏中心 |

> 净化主力放在引擎侧：`reject_*` 与 `response.json.*` 由 Loon 自己解压 `Content-Encoding: gzip`，脚本链不碰压缩体。脚本读响应体必须先 ungzip，而 `$utils.ungzip` 只有 Build ≥ 988 才有——低版本就是静默 passthrough，这正是「净化不生效」的那条链。

> 全层由 `src/apps/bilibili.json` 的 `enhance` 整段生成（`tools/build-apps.py`），lint 逐行对账产物——直接改生成物会在下一次构建被覆盖。

前提与步骤：①Loon 装并信任证书（本层已默认解密这些主机） → ②要自动化就把 `[Argument]` 里的对应开关改成 true（默认关的那几个） → ③确认可用：冷启动后看日志里复写装载计数（`Reload rewrites:`）与脚本侧锚点行，再用探针绑定判断复写是否接管（探针消失 = 复写命中）。

> 证书固定红线：银行/微信/米家类 App 做了证书固定，MITM 直接失败甚至触发风控，那些插件不提供本层；本层只对未做证书固定的 App 提供，且每条路径都有下方公开证据。
> 反过来说：本层已经默认写在生效配置里，**证书没装好时这些主机的 TLS 会失败**——不是「没生效」而是「连不上」。装好证书再评估，或直接把 `[MITM]` 那两行注释掉退回零证书形态。

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
- 能力天花板与原生设计：dataflow.biliapi.com、data.bilibili.com、tracker.chat.bilibili.com、ali-web-player-tracker.biliapi.net、hw-v2-web-player-tracker.biliapi.net、httpdns.bilivideo.com 六个自建遥测与 HTTPDNS 域走 [Host] 127.0.0.1 零证书黑洞；开屏与信息流商业广告位走 Loon 原生 [Rewrite] v2（reject_dict(200) + response.json.jq），零 JS 脚本。
- v1.2.0 升级 Loon 原生 [Rewrite] v2 引擎复写层（enhance.active=true）：通过 [Argument] 的 cleanAds（开屏/推荐流/播放页去广告）与 slimNav（导航栏精简）两个开关驱动 5 条原生复写规则 + app.bilibili.com 的 QUIC 回退——补齐 splash/(brand/list|event/list2) 品牌与活动开屏终止、首页推荐流 cm_v1/ad_av/ad_web_s 商业卡片过滤，以及 x/v2/view 视频详情页播放下方商业组件（cm_config/cms/cm_ipad）与相关推荐广告位过滤。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/bilibili.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 6 条，[Rule] 1 条。
