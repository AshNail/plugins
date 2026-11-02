# 网易云音乐 · 净化（规则层）

从 `ios151/NeteasemusicAd` 的 `wyy.sgmodule` 中吸纳**规则与 Map Local 端点事实**，
转换为 Loon 原生规则；**不包含上游 `wyyad.js`**（无许可证，且本机无网易云 App）。

## 导入

[一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fnetease%2Fnetease.plugin)

## 内容

- 域名：由 ads 插件与公开主配置覆盖；插件只保留 MITM/Rewrite。
- `[Rewrite]`：7 条 request 阶段 `reject_dict(200)`，对应上游 Map Local 的空 JSON
  端点（广告、免流推广、Tab 框架、搜索默认词、资源曝光、直播入口、商店配置等）。
- 响应阶段：9 条原生 `response.json.jq`，对首页、发现、我的、收银台、评论区、
  `/batch`、`v1/user/info`、推荐页、关注推荐删除广告字段；不复制上游 JS。
- `[MITM]`：`music.163.com`、`interface[3/9].music.163.com`、`ipv4.music.163.com`。

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
