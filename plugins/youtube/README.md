# YouTube · 广告字段清理（原生复写） v1.2.2

> YouTube 广告跟踪请求直接阻断，首页、搜索与播放器推荐广告字段原生 jq 过滤；不改音视频流，零JS脚本。

版本 **1.2.2** ｜ 功能基线 Loon **3.5.1(983)**+ （iOS/tvOS 口径；Mac 版是 0.x 独立一条线，插件头不声明门槛）｜ 净化层默认启用（`[Argument]`+`[MITM]`+`[Script]` 三层已在文件里生效，须已装并信任 Loon 证书）· 拦截面 `[Host]`/`[Rule]`

## 安装

[![一键导入 youtube.plugin](https://img.shields.io/badge/Loon-导入YouTube%20%C2%B7%20%E5%B9%BF%E5%91%8A%E5%AD%97%E6%AE%B5%E6%B8%85%E7%90%86%EF%BC%88%E5%8E%9F%E7%94%9F%E5%A4%8D%E5%86%99%EF%BC%89%20v1.2.2-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fyoutube%2Fyoutube.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/youtube/youtube.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| YouTube 精确广告子域（DNS 黑洞） | A | 启用 | ad.youtube.com / ads.youtube.com=YouTube 广告投放与营销专用子域（anti-AD / AdGuard / HaGeZi 多源收录），精确黑洞不触碰播放与主站红线。 |
| QUIC 回退（增强层配套） | A | 启用 | 只对 `PROTOCOL,QUIC` 生效：拒的是 HTTP/3 这条通道、不是这台主机，同一主机的 TCP 正文/书架零影响。共 2 条。 |

## 默认启用的 MITM 层（本 App 未做证书固定；必须已装并信任 Loon 证书）

YouTube 的广告元数据与正文共用 youtubei.googleapis.com / www.youtube.com，不可整域黑洞。本层默认启用 Loon 原生 [Rewrite] v2 复写（由 cleanAds 开关控制，零 JS 脚本）：① www.youtube.com 的 pagead/、api/stats/(ads|atr|qoe)、ptracking、error_204 以及 youtubei/v1/log_event 在 request 阶段 reject_dict(200) 直接终止；② youtubei.googleapis.com 响应递归删除 adPlacements / playerAds / adSlots / adBreakHeartbeatParams / adBreakParams，不改播放地址。

- 解密主机（`[MITM] hostname`，2 个，本层已默认生效）：`youtubei.googleapis.com`, `www.youtube.com`
- 配套 QUIC 回退（`AND,((DOMAIN-SUFFIX,<域>),(PROTOCOL,QUIC)),REJECT`，2 条，已生效）：MITM 只解密 TCP，App 走 HTTP/3 时 `URL-REGEX`、`[Rewrite]` 复写与脚本绑定全部静默失效；它拒的是 QUIC 这条通道，同一主机的 TCP 请求零影响。

### 开关（`[Argument]`）

| 开关 | 默认 | 作用 |
|---|---|---|
| `cleanAds` | true | 启用 Loon 原生 [Rewrite] v2 引擎复写：拦截 www.youtube.com 网页广告/统计路径与 youtubei/v1/log_event 事件上报，并递归删除 youtubei.googleapis.com 响应中的广告字段。需已安装并信任 Loon 证书。 |

### 净化复写（`[Rewrite]`）

| 规则 | 阶段 | 动作 | 开关 | 行为 |
|---|---|---|---|---|
| `kill-pagead` | request | `reject_dict` | `cleanAds` | 网页与客户端 pagead/ 加载及广告统计/追踪上报路径直接返回 200 + 空字典 |
| `kill-youtubei-log-event` | request | `reject_dict` | `cleanAds` | YouTube 客户端中插广告点拉取（player/ad_break）及高频遥测/广告归因上报（log_event、att/log）在请求阶段直接返回 200 + 空字典 |
| `clean-youtubei-ads` | response | `response.json.jq` | `cleanAds` | YouTubei 响应（含 Shorts reel_item_watch 与播放中 updated_metadata）递归删除广告字段；不改播放地址 |

> 净化主力放在引擎侧：`reject_*` 与 `response.json.*` 由 Loon 自己解压 `Content-Encoding: gzip`，脚本链不碰压缩体。脚本读响应体必须先 ungzip，而 `$utils.ungzip` 只有 Build ≥ 988 才有——低版本就是静默 passthrough，这正是「净化不生效」的那条链。

> 全层由 `src/apps/youtube.json` 的 `enhance` 整段生成（`tools/build-apps.py`），lint 逐行对账产物——直接改生成物会在下一次构建被覆盖。

前提与步骤：①Loon 装并信任证书（本层已默认解密这些主机） → ②要自动化就把 `[Argument]` 里的对应开关改成 true（默认关的那几个） → ③确认可用：冷启动后看日志里复写装载计数（`Reload rewrites:`）与脚本侧锚点行，再用探针绑定判断复写是否接管（探针消失 = 复写命中）。

> 证书固定红线：银行/微信/米家类 App 做了证书固定，MITM 直接失败甚至触发风控，那些插件不提供本层；本层只对未做证书固定的 App 提供，且每条路径都有下方公开证据。
> 反过来说：本层已经默认写在生效配置里，**证书没装好时这些主机的 TLS 会失败**——不是「没生效」而是「连不上」。装好证书再评估，或直接把 `[MITM]` 那两行注释掉退回零证书形态。

证据：
- https://www.youtube.com/

## 红线与天花板（如实）

- 红线：*.youtube.com / *.googlevideo.com / *.ytimg.com / youtubei.googleapis.com 承载登录、播放、缩略图与 API；本插件只做 youtubei JSON 广告字段清理，不黑洞整域，不改播放地址。
- v1.2.0 启用 Loon 原生 [Rewrite] v2 引擎复写层（enhance.active=true）：通过 [Argument] cleanAds 开关（默认开）驱动 3 条原生复写规则 + 配套 QUIC 回退，并将 youtubei/v1/log_event 高频遥测上报移至 request 阶段直接 reject_dict(200) 阻断出网。
- 可莉 YouTube 插件是纯 response/request 脚本（含上传、Shorts、字幕、日志事件参数）；本插件不复制、不依赖，只实现可由 Loon 原生 [Rewrite] v2 表达的广告路径拦截与字段删除。
- 响应规则只删除 adPlacements/playerAds/adSlots/adBreakHeartbeatParams/adBreakParams；不改播放 URL、不碰 googlevideo 的 initplayback，避免把视频本体拦掉。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/youtube.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 2 条，[Rule] 2 条。
