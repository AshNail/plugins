# 淘宝 · 去广告（原生规则层）

> 淘宝广告分两层：Alimama/Tanx/Simba/adashx 等独立广告域走 DNS 黑洞；开屏、推荐、活动等广告入口是 acs.m.taobao.com / guide-acs.m.taobao.com 的 mtop 路径，需可选 MITM 后按 URL 精确拒绝。11 条路径来自可莉淘宝插件的 request reject 事实，改写为 Loon 原生 URL-REGEX + REJECT-DICT；不包含上游 JS，交易/登录/支付红线不动。

版本 **1.0.0** ｜ 功能基线 Loon **3.5.1(983)**+ （iOS/tvOS 口径；Mac 版是 0.x 独立一条线，插件头不声明门槛）｜ 零证书 · 纯 `[Host]`/`[Rule]`（另含默认注释的可选 MITM 增强层，见下）

## 安装

[![一键导入 taobao.plugin](https://img.shields.io/badge/Loon-导入%E6%B7%98%E5%AE%9D%20%C2%B7%20%E5%8E%BB%E5%B9%BF%E5%91%8A%EF%BC%88%E5%8E%9F%E7%94%9F%E8%A7%84%E5%88%99%E5%B1%82%EF%BC%89-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Ftaobao%2Ftaobao.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/taobao/taobao.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| 阿里广告/UT 独立端点 | B | 启用 | h-adashx.ut.taobao.com=AdashX 广告/UT 分片；ossgw.alicdn.com=广告素材网关；hudong.alicdn.com=互动广告素材。可莉淘宝原插件默认 REJECT；均为精确广告子域，媒体主域 alicdn.com 不整域。 2026-11-03 App 覆盖率审计补 6 个 ≥3 源 A 候选：atanx.alicdn.com、tns/dsp/tmatch.simba.taobao.com、adashx.m.taobao.com、adashx4yt.m.taobao.com；均为精确广告/交易归因子域。 |
| UT 埋点（默认关） | B | 默认关闭 | ut.taobao.com=阿里 UT 埋点；关闭统计不等于去广告，默认关，需要隐私优先再开。 |
| 淘宝客/联盟归因（默认关） | B | 默认关闭 | tunion-api.m.taobao.com=淘宝联盟 CPS 归因；拦了会影响淘宝客取链/返利，默认关。 |
| 阿里 AMDC HTTPDNS 调度（默认关） | B | 默认关闭 | amdc.m.taobao.com / amdcopen.m.taobao.com=阿里 HTTPDNS 调度；拦后若 App 无回退可能拖慢建连，默认关。 |
| 阿里妈妈 / TanX / 阿里广告监测（引用组） | A | 启用 | 域名真源见 ads 组/SDK 库 共 6 域 / 0 规则。 |

## 可选 MITM 增强层（默认整段注释，不装证书 = 永不生效）

淘宝 iOS 的开屏/推荐/活动广告入口与交易共用 acs.m.taobao.com、guide-acs.m.taobao.com，不能黑洞整域。下列 11 条 URL-REGEX 来自可莉淘宝插件的 request reject 事实，改写为 Loon 原生 REJECT-DICT（200 + 空字典）；广告图片路径用 REJECT-IMG。上游两条 response script（cloudvideo、poplayer 模板）需要 JS，本插件不包含。默认整段注释，装证书后逐条启用，先验搜索/下单/购物车/支付。

- 解密主机（`[MITM] hostname`，4 个）：`acs.m.taobao.com`, `guide-acs.m.taobao.com`, `gw.alicdn.com`, `heic.alicdn.com`
- 配套 QUIC 回退（`AND,((DOMAIN-SUFFIX,<域>),(PROTOCOL,QUIC)),REJECT`，4 条，注释态）：MITM 只解密 TCP，App 走 HTTP/3 时 `URL-REGEX` 会静默失效；启用本层时应连同这些行一起取消注释。
- 路径级规则（`URL-REGEX`，11 条，命中即拦对应广告接口/素材，不影响同域功能请求）：

```text
# URL-REGEX,^https://acs\.m\.taobao\.com/gw/mtop\.fliggy\.crm\.screen\.(?:allresource|predict),REJECT-DICT
# URL-REGEX,^https://acs\.m\.taobao\.com/gw/mtop\.alibaba\.advertisementservice\.getadv,REJECT-DICT
# URL-REGEX,^https://acs\.m\.taobao\.com/gw/mtop\.alimama\.etao\.config\.query/.+?etao_advertise,REJECT-DICT
# URL-REGEX,^https://acs\.m\.taobao\.com/gw/mtop\.alimusic\.common\.mobileservice\.startinit,REJECT-DICT
# URL-REGEX,^https://acs\.m\.taobao\.com/gw/mtop\.etao\.noah\.query/.+tao_splash,REJECT-DICT
# URL-REGEX,^https://acs\.m\.taobao\.com/gw/mtop\.film\.mtopadvertiseapi\.queryadvertise,REJECT-DICT
# URL-REGEX,^https://acs\.m\.taobao\.com/gw/mtop\.o2o\.ad\.gateway\.get,REJECT-DICT
# URL-REGEX,^https://acs\.m\.taobao\.com/gw/mtop\.taobao\.idle\.home\.welcome,REJECT-DICT
# URL-REGEX,^https://acs\.m\.taobao\.com/gw/mtop\.trip\.activity\.querytmsresources,REJECT-DICT
# URL-REGEX,^https://guide-acs\.m\.taobao\.com/gw/mtop\.taobao\.(?:volvo\.secondfloor\.getconfig|wireless\.home\.newface\.awesome\.get),REJECT-DICT
# URL-REGEX,^https://(?:gw|heic)\.alicdn\.com/imgextra/i\d/\d*/.+?-\d-(?:octopus|tps)-(?:1080|1125)-\d{4}\.(?:jpg|png)_(?:1\d{3}|9\d{2})x(?:\d|1\d{3}|9\d{2})q[59]0,REJECT-IMG
```

启用步骤：①Loon 装并信任证书 → ②取消插件内 `[MITM]` 头与 hostname 行注释 → ③取消 `[Rule]` 头、QUIC 回退行与所需规则行的注释（`# [Rule]` 必须一起取消，否则规则会落在上一段的末尾而不生效）。

> 证书固定红线：银行/微信/米家类 App 做了证书固定，MITM 直接失败甚至触发风控，那些插件不提供本层；本层只对未做证书固定的 App 提供，且每条路径都有下方公开证据。

证据：
- https://kelee.one/
- https://github.com/blackmatrix7/ios_rule_script/blob/master/rule/Loon/Advertising/Advertising.list

## 红线与天花板（如实）

- 红线：*.taobao.com / *.tmall.com / *.alicdn.com 整族承载登录、订单、购物车、商品图与播放；本插件只做精确广告子域和广告路径，绝不做 DOMAIN-SUFFIX 整域。
- acs.m.taobao.com 与 guide-acs.m.taobao.com 是 mtop 主网关，交易与广告同域；DNS 层不黑洞它们，只在可选 MITM 层按 11 条广告 API 路径返回 200 空字典。
- 可莉淘宝插件的 11 条 request reject 是原生 reject_dict，本插件改写为 URL-REGEX REJECT-DICT；上游两条 response script（开屏 cloudvideo / poplayer 模板）依赖 JS，本插件不复制、不依赖。
- 证据基线：可莉淘宝插件规则事实 + blackmatrix7 Advertising + anti-AD；淘宝 IPA 10.68.10 的 mtop 广告前缀已在公开主配置有独立证据。路径规则未在 2026-11-03 逐条真机复测，启用后先验搜索、下单、购物车、支付。
- DNS 组默认生效；MITM 增强层默认整段注释，装并信任 Loon 证书后逐条启用。
- 红线补充：h5api.m.taobao.com 是 H5 交易/登录接口；login.taobao.com 是淘宝登录入口；passport.taobao.com 是淘宝账号/通行证；sec.taobao.com 是淘宝风控/安全接口；gw.alicdn.com 是图片/素材 CDN；img.alicdn.com 与 heic.alicdn.com 是商品图 CDN。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/taobao.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 19 条，[Rule] 0 条。
