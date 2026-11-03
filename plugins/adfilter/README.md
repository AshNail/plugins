# 广告过滤器 · 原生规则子集

从 fkingikelee/可莉广告过滤器的 82 条 request reject 中筛出的 **API 级广告/推广拦截**，
改写为 Loon 原生 `[Rule]` / `URL-REGEX`，不复制任何 JS。

## 导入

[一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fadfilter%2Fadfilter.plugin)

## 内容

- 默认生效：11 条精确广告域规则（AdNexus、21CN、联通广告、Pixiv 广告等），不碰
  `taobao.com` / `alicdn.com` / `qq.com` 等共享主域。
- 可选：52 条 `URL-REGEX`，覆盖小米金融/MiFit、Pinduoduo 开屏、QWeather、有道、
  Umetrip? 等 App 的广告 API；**默认注释**，需要 MITM 后逐 App 取消注释。
- 明确排除：QQ/微信钱包、`api.m.mi.com` 启动、米家店铺配置、`gw.alicdn.com`
  共享 CDN、淘宝主网关、Umetrip 首页、小米手表健康资源、图片硬编码、未知响应体 mock。

## 启用

1. 只想要 DNS 层：直接导入，默认规则即生效。
2. 要 URL 规则：装并信任 Loon 证书 → 取消 `# [MITM]` 与 `# hostname` 行 →
   再取消需要的 `# URL-REGEX` 行；逐 App 验证，出现白屏/接口报错只回滚对应行。

## 边界

- 不做会员/地区/青少年/支付/鉴权绕过；不复制可莉 JS。
- 规则事实来源：`https://github.com/fkingikelee/fkikelee` 的
  `Remove_ads_by_keli.lpx`；本插件只保留可原生表达的广告 API 与广告域。
