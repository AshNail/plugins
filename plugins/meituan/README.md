# 美团 · 去广告

> 美团/点评：iOS 官方 SDK 目录实证第三方变现 = Sigmob/ToBid/美数（穿山甲/优量汇仅 Android）+ 自建广告端点 impdsp/mads + 纯遥测家族黑洞。首页轮播/信息流/开屏素材与业务同域同 CDN——DNS 层收益约 25-35%，其余是「加载失败留白」。交易、支付、骑手调度零接触。零证书。

版本 **1.2.0** ｜ 最低 Loon **3.5.1(983)** ｜ 零证书 · 纯 `[Host]`/`[Rule]`（另含默认注释的可选 MITM 增强层，见下）

## 安装

[![一键导入 meituan.plugin](https://img.shields.io/badge/Loon-导入%E7%BE%8E%E5%9B%A2%20%C2%B7%20%E5%8E%BB%E5%B9%BF%E5%91%8A-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fmeituan%2Fmeituan.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/meituan/meituan.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| 美团自建广告端点（曝光/竞价/聚合入口） | A | 启用 | impdsp.meituan.com=自营展示广告 DSP 曝光/点击链路（wpt-giant 自建集群，anti-AD/AdGuard/hagezi 三源+issue #9926 归类 Ads）;mads.meituan.com=移动广告聚合入口。与 ads 插件同域规则重叠属有意（按 App 开关语义）。 |
| 开屏素材 CDN（专用子域） | A | 启用 | pd0-cdn-mcdn.m.meituan.net=开屏素材专用 mcdn(反黑名单收录);s3plus-pre=预发遥测端,生产不调用,黑洞零风险。开屏主路径(wmapi startpicture/s3plus brandcpt)同域不可分,预期只削掉 mcdn 分发的部分。 |
| 美团/点评纯遥测家族（默认关） | A | 默认关闭 | CAT 开源 APM(catfront)、dreport/wreport/hreport/report(BI 集群自证)、analytics.meituan.net、data-sdk-uuid-log/metrics-picture/maplocatesdksnapshot 分片、wx-md/cloudidv/orecct/athena——全部多源收录且与下单支付不同集群,拦掉只丢报表。athena=运营配置中心,拦后营销弹窗从「白屏」变「正常消失」。 |
| d.meituan.net 数据集群已知子域（默认关，验证后可升通配） | B | 默认关闭 | bd0.d 落 data-leopard 集群（CNAME 取证自证上报），S7 用 DOMAIN-SUFFIX,d.meituan.net,REJECT——但整后缀升通配前需实测商品图/地图完整性，这里只列已知子域。 |
| 外卖广告独立子域（默认关，单源收录） | B | 默认关闭 | adgame.waimai.meituan.com=外卖广告小游戏;ad.e.waimai.sankuai.com=外卖广告请求域（CNAME 与业务 e.waimai.sankuai.com 不同集群,证据成立但仅 wool 单源）。抓包命中后升 A。 |
| 优惠券弹窗/红包雨配置网关（默认关） | A | 默认关闭 | catdot/catreport.dianping.com=弹窗配置下发。拦掉=弹窗不弹,但每次请求要多等约 60s 超时——副作用可感知,默认关。 |
| Sigmob（北京创智汇聚）（引用组） | A | 启用 | adservice/dc/track.sigmob.cn；anti-AD/AdGuard/hagezi 多源收录；ads 插件 mobile_sdks 组同源含此域。 共 4 域 / 0 规则。 |
| ToBid 聚合（北京创致 / Sigmob 系）（引用组） | A | 启用 | 美团官方 SDK 目录实证 iOS 在跑的聚合 SDK；n.tobidad.com 为静态端点。证据：fe-config.meituan.com SDK 目录 + anti-AD/hagezi。 共 2 域 / 0 规则。 |
| 美数 AdMate（北京美数信息）（引用组） | A | 启用 | 美团官方 SDK 目录实证 iOS 第三方变现 SDK；anti-AD 收录。 共 4 域 / 0 规则。 |

## 可选 MITM 增强层（默认整段注释，不装证书 = 永不生效）

美团 iOS 未做证书固定：开屏广告/启动配置走 wmapi.meituan.com 的具体路径（与业务 API 同主机，黑洞整域=废掉点外卖），正解是 MITM 后按路径 reject。下列规则来自 blackmatrix7 AllInOne/AdvertisingScript 与 fmz200 blockAds 公开模块（reject 语义），默认整段注释、装证书后按需启用。素材图 p[0-9].meituan.net 与商品图共用 CDN，只按广告路径段拦，不整域拦。

- 解密主机（`[MITM] hostname`，3 个）：`wmapi.meituan.com`, `apimobile.meituan.com`, `p?.meituan.net`
- 路径级规则（`URL-REGEX`，4 条，命中即拦对应广告接口/素材，不影响同域功能请求）：

```text
# URL-REGEX,^https?://wmapi\.meituan\.com/api/v[0-9]/openscreen\?ad,REJECT-DICT
# URL-REGEX,^https?://wmapi\.meituan\.com/api/v[0-9]/startpicture,REJECT-DICT
# URL-REGEX,^https?://wmapi\.meituan\.com/api/v[0-9]/loadInfo\?,REJECT-DICT
# URL-REGEX,^https?://p[0-9]\.meituan\.net/(bizad|wmbanner|brandCpt)/[a-zA-Z0-9]+\.jpg,REJECT
```

启用步骤：①Loon 装并信任证书 → ②取消插件内 `[MITM]` 头与 hostname 行注释 → ③按需取消规则行注释。

> 证书固定红线：银行/微信/米家类 App 做了证书固定，MITM 直接失败甚至触发风控，那些插件不提供本层；本层只对未做证书固定的 App 提供，且每条路径都有下方公开证据。

证据：
- https://github.com/blackmatrix7/ios_rule_script/blob/master/rewrite/Loon/AllInOne/AllInOne.plugin
- https://github.com/blackmatrix7/ios_rule_script/blob/master/rewrite/Loon/AdvertisingScript/AdvertisingScript.plugin
- https://github.com/fmz200/wool_scripts/blob/main/Surge/module/blockAds.module

## 红线与天花板（如实）

- 红线（绝不进任何拦截组）：appsec-mobile.meituan.com（mtgsig 签名+设备指纹上报，拦=触发下单/支付风控，无任何黑名单收录）/ api-unionid.meituan.com（统一账号）/ api-map.meituan.net（地图瓦片）/ shark.dianping.com（Pike 长连通道，核弹模块 S9 也误伤它）/ ddplus(+quic).meituan.net（TitansX/Picasso 动态模板包）/ mrn.meituan.net 与 beauty-*.meituan.net（VOD/直播拉流）/ assistify.meituan.com（零证据，暂判 CORE）/ awp-assets 与 awps-assets（H5 容器与活动混装）/ apimobile.meituan.com / paymp / i.meituan.com。
- 拒收条目（取证否决）：meituan.xn / meituan.yoga / meituangov.cn / meituancdn.cc——AliDNS 无解析或非美团主体，来源可疑，写了也不会命中。
- 能力天花板（如实）：开屏走 wmapi/mapi 主 API 路径与 s3plus 共享存储，首页轮播走 p*.meituan.net / img.meituan.net 共享图床的 /bizad|/wmbanner|/adunion 路径——DNS 层不可分；成熟方案（blackmatrix7/wool）全部用 Map Local/reject-dict 即直接证据。可 DNS 切断的只有第三方 ADN + impdsp/mads + 遥测。
- iOS 与 Android 差异：官方《接入第三方SDK目录》标注腾讯营销联盟/BeiZi/天璇/快手联盟/酷盈/PolyGamma 仅 Android——本插件 iOS 侧不挂 pangle/gdt/kuaishou 组，避免无收益死规则。
- 只走精确域,不做 DOMAIN-SUFFIX 整域——美团交易规则依赖 *.meituan.com/*.meituan.net 深层子域（含 *.mtgsig 防刷签名路径）。
- 本插件 [Host]/[Rule] 全设备生效(Loon 无法按 App 限定):同一 SDK 域跨 App 共享黑洞,'按 App 插件'只是分组开关;配合全局 ads 插件 httpdns 组防绕过。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/meituan.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 36 条，[Rule] 0 条。
