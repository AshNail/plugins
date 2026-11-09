# 网易云音乐 · 净化（规则层）

从 `ios151/NeteasemusicAd` 的 `wyy.sgmodule` 中吸纳**规则与 Map Local 端点事实**，
转换为 Loon 原生规则；**不包含上游 `wyyad.js`**（无许可证，且本机无网易云 App）。

## 导入

[一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fnetease%2Fnetease.plugin)

## 内容（v1.1.0）

- `[Argument]`：
  - `cleanAds`（默认开启）：控制全部广告/推广请求短路与 9 条响应侧 `jq` 字段剥离。
  - `slimUI`（默认关闭）：按需隐藏侧边栏小程序、云贝入口、商城入口与红点。
- `[Host]`：自包含 8 个网易云专属 HTTPDNS（`httpdns.music.163.com`、`music.httpdns.c.163.com`、`httpdns.n.netease.com`、`httpdns-sdk.n.netease.com`）与独立广告素材 CDN（`iadmat*.nosdn.127.net`、`iadmusicmat*.music.126.net`）黑洞，不依赖外部插件即可防绕过且不触碰音频流媒体与封面图 CDN。
- `[Rule]`：`AND,((DOMAIN-SUFFIX,music.163.com),(PROTOCOL,QUIC)),REJECT` 强制 HTTP/3 回落 TCP，保障 MITM 生效。
- `[Rewrite]`：
  - 请求阶段：6 条广告/推广 `reject_dict(200)`（`cleanAds` 控制）+ 3 条界面精简 `reject_dict(200)`（`slimUI` 控制）；**已剔除上游误伤「我的收藏歌手」（`user/sub/artist`）与手动检查更新（`ios/version`）的两个端点**；`/api/ad` 收紧尾边界避免前缀误伤。
  - 响应阶段：9 条原生 `response.json.jq`，对首页、发现、我的、收银台、评论区、`/batch`、`v1/user/info`、推荐页、关注推荐递归删除广告与曝光监控字段；零第三方 JS。
- `[MITM]`：`%APPEND% music.163.com, interface.music.163.com, interface?.music.163.com, ipv4.music.163.com, ipv6.music.163.com`（覆盖 `interface0..9` 全分片及 IPv4/IPv6 入口，不覆盖主配置其它 MITM 域名）。

## 边界

- 只做空响应与广告字段清理；上游 JS 的 Tab 名称自定义未复制。
- 需要 Loon 3.5.1(983)+；HTTPS 改写需要 MITM 证书。
- Mac 0.5.0(1011) 实测 response 阶段 jq 未执行，请求阶段规则正常；需 iOS/iPad/tvOS 验证。
- 原始模块版权归 ios151/NeteasemusicAd；本文件只包含规则事实与原创配置。

## 验证

- `https://interface.music.163.com/eapi/ad` → 200 `{}`
- `/wapi/search/default`、`/xeapi/mlivestream/entrance/playpage` → 200 `{}`
- 对照路径与 `music.163.com` 正常。
- 9 条 jq 已用合成响应验证；真机启用后确认首页/发现/评论无广告字段且业务 JSON 合法。
