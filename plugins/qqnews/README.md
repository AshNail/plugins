# 腾讯新闻 · 广告字段清理（原生复写）

> 不搬 app2smile 远程 JS：腾讯新闻 iOS 的开屏/列表/专题广告位走 HTTPS JSON。本插件默认启用 Loon 原生 [Rewrite] v2 引擎复写（cleanAds 开关默认开）——news.ssp.qq.com/app 开屏配置请求在 request 阶段 reject_dict(200) 终止、列表接口 adList 用 response.json.replace 置 null、专题/频道 widget_list 用 response.json.jq 过滤 widget_type=ad_list；零 JS 脚本。前置：需已安装并信任 Loon 证书。

版本 **1.1.2** ｜ 功能基线 Loon **3.5.1(983)**+ （iOS/tvOS 口径；Mac 版是 0.x 独立一条线，插件头不声明门槛）｜ 净化层默认启用（`[Argument]`+`[MITM]`+`[Script]` 三层已在文件里生效，须已装并信任 Loon 证书）· 拦截面 `[Host]`/`[Rule]`

## 安装

[![一键导入 qqnews.plugin](https://img.shields.io/badge/Loon-导入%E8%85%BE%E8%AE%AF%E6%96%B0%E9%97%BB%20%C2%B7%20%E5%B9%BF%E5%91%8A%E5%AD%97%E6%AE%B5%E6%B8%85%E7%90%86%EF%BC%88%E5%8E%9F%E7%94%9F%E5%A4%8D%E5%86%99%EF%BC%89-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fqqnews%2Fqqnews.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/qqnews/qqnews.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| QUIC 回退（增强层配套） | A | 启用 | 只对 `PROTOCOL,QUIC` 生效：拒的是 HTTP/3 这条通道、不是这台主机，同一主机的 TCP 正文/书架零影响。共 2 条。 |

## 默认启用的 MITM 层（本 App 未做证书固定；必须已装并信任 Loon 证书）

腾讯新闻的广告与正文共用 HTTPS JSON（news.ssp.qq.com、r.inews.qq.com），不可 DNS 黑洞。本层默认启用 Loon 原生 [Rewrite] v2 复写（由 cleanAds 开关控制，零 JS 脚本）：① news.ssp.qq.com/app 开屏配置请求在 request 阶段 reject_dict(200) 直接终止；② 列表类接口（开屏/要闻/财经/地方专区）用原生 response.json.replace 将 adList 置为 null；③ 专题详情/频道信息流（gw/page/event_detail、channel_feed）用原生 response.json.jq 过滤 widget_type=ad_list。

- 解密主机（`[MITM] hostname`，2 个，本层已默认生效）：`news.ssp.qq.com`, `r.inews.qq.com`
- 配套 QUIC 回退（`AND,((DOMAIN-SUFFIX,<域>),(PROTOCOL,QUIC)),REJECT`，2 条，已生效）：MITM 只解密 TCP，App 走 HTTP/3 时 `URL-REGEX`、`[Rewrite]` 复写与脚本绑定全部静默失效；它拒的是 QUIC 这条通道，同一主机的 TCP 请求零影响。

### 开关（`[Argument]`）

| 开关 | 默认 | 作用 |
|---|---|---|
| `cleanAds` | true | 启用 Loon 原生 [Rewrite] v2 引擎复写：news.ssp.qq.com/app 开屏配置请求 reject_dict(200) 终止；列表接口 adList 置 null；专题/频道信息流过滤 widget_type 为 ad_list 的广告组件。需已安装并信任 Loon 证书。 |

### 净化复写（`[Rewrite]`）

| 规则 | 阶段 | 动作 | 开关 | 行为 |
|---|---|---|---|---|
| `kill-ssp-app` | request | `reject_dict` | `cleanAds` | 开屏配置接口直接返回 200 + 空字典 |
| `clean-list-adlist` | response | `response.json.replace` | `cleanAds` | 要闻/财经/地方专区/详情关联/视频列表接口：adList 广告数组置 null（原生标量替换，全平台生效） |
| `clean-feed-widget` | response | `response.json.jq` | `cleanAds` | 专题详情/频道信息流：data.widget_list 过滤 widget_type=ad_list 的广告组件 |

> 净化主力放在引擎侧：`reject_*` 与 `response.json.*` 由 Loon 自己解压 `Content-Encoding: gzip`，脚本链不碰压缩体。脚本读响应体必须先 ungzip，而 `$utils.ungzip` 只有 Build ≥ 988 才有——低版本就是静默 passthrough，这正是「净化不生效」的那条链。

> 全层由 `src/apps/qqnews.json` 的 `enhance` 整段生成（`tools/build-apps.py`），lint 逐行对账产物——直接改生成物会在下一次构建被覆盖。

前提与步骤：①Loon 装并信任证书（本层已默认解密这些主机） → ②要自动化就把 `[Argument]` 里的对应开关改成 true（默认关的那几个） → ③确认可用：冷启动后看日志里复写装载计数（`Reload rewrites:`）与脚本侧锚点行，再用探针绑定判断复写是否接管（探针消失 = 复写命中）。

> 证书固定红线：银行/微信/米家类 App 做了证书固定，MITM 直接失败甚至触发风控，那些插件不提供本层；本层只对未做证书固定的 App 提供，且每条路径都有下方公开证据。
> 反过来说：本层已经默认写在生效配置里，**证书没装好时这些主机的 TLS 会失败**——不是「没生效」而是「连不上」。装好证书再评估，或直接把 `[MITM]` 那两行注释掉退回零证书形态。

证据：
- https://github.com/app2smile/rules/blob/master/plugin/qqnews.plugin
- https://github.com/app2smile/rules/blob/master/js/qq-news.js

## 红线与天花板（如实）

- 红线（绝不进任何拦截组）：news.ssp.qq.com 是腾讯新闻开屏页与频道配置接口主机；r.inews.qq.com 是腾讯新闻要闻/频道/专题/评论接口主机，正文与广告同主机——DNS 黑洞整域 = 新闻页白屏重试。本插件不做 [Host] 整域黑洞，只做路径级与字段级 Loon 原生 [Rewrite] v2 清理（需装 Loon 证书）。
- v1.1.0 启用 Loon 原生 [Rewrite] v2 引擎复写层（enhance.active=true）：通过 [Argument] cleanAds 开关（默认开）驱动 3 条原生复写规则 + 配套 QUIC 回退，解决远程订阅插件无法手工取消 # 注释导致 0 生效的问题；列表接口 adList 改用原生 response.json.replace("adList", null)，不依赖 jq 即可在 iOS/macOS 全平台置空。
- 证据：app2smile/rules（MIT License）公开插件 qqnews.plugin + 脚本 js/qq-news.js 的广告处置逻辑（adList→null；widget_list 过滤 widget_type=ad_list），本插件不复制其远程脚本、改用 Loon 原生 [Rewrite] v2（reject_dict / response.json.replace / response.json.jq）实现等价效果。app2smile 标记为「弃用/待验证」的 getTwentyFourHourNews、getQQNewsListItems、gw/event/list 端点一律不收。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/qqnews.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 0 条，[Rule] 2 条。
