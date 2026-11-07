# 美团 · 去广告

> 美团/点评：iOS 官方 SDK 目录实证第三方变现 = Sigmob/ToBid/美数（穿山甲/优量汇仅 Android）+ 自建广告端点 impdsp/mads + 纯遥测家族黑洞；同域开屏接口、共享图床广告目录图片、搜索热词与购物车 Banner 默认启用 Loon 原生 [Rewrite] v2 引擎复写（cleanAds 开关默认开、slimUI 开关默认关，零 JS 脚本）。交易、支付、骑手调度零接触。前置：同域复写层需已安装并信任 Loon 证书。

版本 **1.3.2** ｜ 功能基线 Loon **3.5.1(983)**+ （iOS/tvOS 口径；Mac 版是 0.x 独立一条线，插件头不声明门槛）｜ 净化层默认启用（`[Argument]`+`[MITM]`+`[Script]` 三层已在文件里生效，须已装并信任 Loon 证书）· 拦截面 `[Host]`/`[Rule]`

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
| 美团/点评纯遥测家族（默认关） | A | 默认关闭 | CAT 开源 APM(catfront)、灵犀埋点(lx.meituan.net)、dreport/wreport/hreport/report(BI 集群自证)、analytics.meituan.net、data-sdk-uuid-log/metrics-picture/maplocatesdksnapshot 分片、wx-md/cloudidv/orecct/athena——全部多源收录且与下单支付不同集群,拦掉只丢报表。athena=运营配置中心,拦后营销弹窗从「白屏」变「正常消失」。 |
| d.meituan.net 数据集群已知子域（默认关，验证后可升通配） | B | 默认关闭 | bd0.d 落 data-leopard 集群（CNAME 取证自证上报），S7 用 DOMAIN-SUFFIX,d.meituan.net,REJECT——但整后缀升通配前需实测商品图/地图完整性，这里只列已知子域。 |
| 外卖广告独立子域（默认关，单源收录） | B | 默认关闭 | adgame.waimai.meituan.com=外卖广告小游戏;ad.e.waimai.sankuai.com=外卖广告请求域（CNAME 与业务 e.waimai.sankuai.com 不同集群,证据成立但仅 wool 单源）。抓包命中后升 A。 |
| 优惠券弹窗/红包雨配置网关（默认关） | A | 默认关闭 | catdot/catreport.dianping.com=弹窗配置下发。拦掉=弹窗不弹,但每次请求要多等约 60s 超时——副作用可感知,默认关。 |
| Sigmob（北京创智汇聚）（引用组） | A | 启用 | adservice/dc/track.sigmob.cn；anti-AD/AdGuard/hagezi 多源收录；ads 插件 mobile_sdks 组同源含此域。 共 4 域 / 0 规则。 |
| ToBid 聚合（北京创致 / Sigmob 系）（引用组） | A | 启用 | 美团官方 SDK 目录实证 iOS 在跑的聚合 SDK；n.tobidad.com 为静态端点，同补 tobidad.cn 变体（ads mobile_sdks 同源）。证据：fe-config.meituan.com SDK 目录 + anti-AD/hagezi。 共 4 域 / 0 规则。 |
| 美数 AdMate（北京美数信息）（引用组） | A | 启用 | 美团官方 SDK 目录实证 iOS 第三方变现 SDK；anti-AD 收录。 共 6 域 / 0 规则。 |
| QUIC 回退（增强层配套） | A | 启用 | 只对 `PROTOCOL,QUIC` 生效：拒的是 HTTP/3 这条通道、不是这台主机，同一主机的 TCP 正文/书架零影响。共 8 条。 |

## 默认启用的 MITM 层（本 App 未做证书固定；必须已装并信任 Loon 证书）

美团 iOS 未做证书固定：开屏广告/启动配置走 wmapi.meituan.com 的具体路径（与业务 API 同主机，黑洞整域=废掉点外卖），广告图片走 p[0-9].meituan.net / flowplus.meituan.net / img.meituan.net 共享图床的广告目录段。本层默认启用 Loon 原生 [Rewrite] v2 引擎复写（零 JS 脚本）：cleanAds（默认开）拦截开屏 JSON、用 reject_img(200) 返回 1px GIF 替换广告图片（避免图片加载器进入破损图重试分支）、并用 response.json.jq 清空搜索热词与启动图/购物车 Banner；slimUI（默认关）用于精简底部 Tab 与推荐信息流。

- 解密主机（`[MITM] hostname`，9 个，本层已默认生效）：`wmapi.meituan.com`, `apimobile.meituan.com`, `p?.meituan.net`, `flowplus.meituan.net`, `img.meituan.net`, `feedguess.meituan.com`, `mt-personalcenter.meituan.com`, `assistify.meituan.com`, `mop.meituan.com`
- 配套 QUIC 回退（`AND,((DOMAIN-SUFFIX,<域>),(PROTOCOL,QUIC)),REJECT`，8 条，已生效）：MITM 只解密 TCP，App 走 HTTP/3 时 `URL-REGEX`、`[Rewrite]` 复写与脚本绑定全部静默失效；它拒的是 QUIC 这条通道，同一主机的 TCP 请求零影响。

### 开关（`[Argument]`）

| 开关 | 默认 | 作用 |
|---|---|---|
| `cleanAds` | true | 启用 Loon 原生 [Rewrite] v2 引擎复写：wmapi 开屏接口 reject_dict(200) 终止；共享图床广告目录路径 reject_img(200) 返回 1px GIF；搜索热词、购物车顶部 Banner 与启动图通过 response.json.jq 置空。需已安装并信任 Loon 证书。 |
| `slimUI` | false | 隐藏底部 video/xiaotuan Tab（只留首页与我的）、清空购物车/个人中心推荐流与 AI 技能配置。默认关，按需开启。 |

### 净化复写（`[Rewrite]`）

| 规则 | 阶段 | 动作 | 开关 | 行为 |
|---|---|---|---|---|
| `kill-openscreen` | request | `reject_dict` | `cleanAds` | 美团外卖/主站 openscreen 开屏广告请求返回 200 + 空字典 |
| `kill-startpicture` | request | `reject_dict` | `cleanAds` | wmapi 启动图广告请求返回 200 + 空字典 |
| `kill-loadinfo` | request | `reject_dict` | `cleanAds` | wmapi 启动加载广告信息请求返回 200 + 空字典 |
| `kill-img-p-cdn` | request | `reject_img` | `cleanAds` | p[0-9].meituan.net 共享图床下的 bizad/wmbanner/brandCpt 广告图返回 200 + 1px GIF |
| `kill-img-flowplus` | request | `reject_img` | `cleanAds` | flowplus.meituan.net 玲珑推广素材图返回 200 + 1px GIF |
| `kill-img-brandcpt` | request | `reject_img` | `cleanAds` | img.meituan.net 品牌 CPT 广告图返回 200 + 1px GIF |
| `kill-img-adunion` | request | `reject_img` | `cleanAds` | img.meituan.net 广告联盟/展示广告目录图片返回 200 + 1px GIF |
| `clean-search-defaultword` | response | `response.json.jq` | `cleanAds` | 清空搜索默认词与热词 |
| `clean-search-hotrecommend` | response | `response.json.jq` | `cleanAds` | 去掉搜索热词推荐与 AI 气泡 |
| `clean-cart-banner` | response | `response.json.jq` | `cleanAds` | 清空购物车入口顶部 banner（topBannerArea） |
| `clean-mop-startuppic` | response | `response.json.jq` | `cleanAds` | 清空 mop 启动图（startupPicArea） |
| `slim-indextab` | response | `response.json.jq` | `slimUI` | 隐藏 video/xiaotuan 底部 tab，只保留 homepage/mine |
| `slim-feedguess` | response | `response.json.jq` | `slimUI` | 清空购物车/个人中心推荐流 |
| `slim-usercenter` | response | `response.json.jq` | `slimUI` | 我的页去掉交叉推荐模块 |
| `slim-hornconfig` | response | `response.json.jq` | `slimUI` | 清空 AI 技能配置（data 内嵌 JSON 的 skills 对象） |

> 净化主力放在引擎侧：`reject_*` 与 `response.json.*` 由 Loon 自己解压 `Content-Encoding: gzip`，脚本链不碰压缩体。脚本读响应体必须先 ungzip，而 `$utils.ungzip` 只有 Build ≥ 988 才有——低版本就是静默 passthrough，这正是「净化不生效」的那条链。

> 全层由 `src/apps/meituan.json` 的 `enhance` 整段生成（`tools/build-apps.py`），lint 逐行对账产物——直接改生成物会在下一次构建被覆盖。

- 通配主机（`p?.meituan.net`）无法用 `DOMAIN-SUFFIX` 表达 QUIC 回退，启用该层的这一域时需另行处理。
前提与步骤：①Loon 装并信任证书（本层已默认解密这些主机） → ②要自动化就把 `[Argument]` 里的对应开关改成 true（默认关的那几个） → ③确认可用：冷启动后看日志里复写装载计数（`Reload rewrites:`）与脚本侧锚点行，再用探针绑定判断复写是否接管（探针消失 = 复写命中）。

> 证书固定红线：银行/微信/米家类 App 做了证书固定，MITM 直接失败甚至触发风控，那些插件不提供本层；本层只对未做证书固定的 App 提供，且每条路径都有下方公开证据。
> 反过来说：本层已经默认写在生效配置里，**证书没装好时这些主机的 TLS 会失败**——不是「没生效」而是「连不上」。装好证书再评估，或直接把 `[MITM]` 那两行注释掉退回零证书形态。

证据：
- https://github.com/blackmatrix7/ios_rule_script/blob/master/rewrite/Loon/AllInOne/AllInOne.plugin
- https://github.com/blackmatrix7/ios_rule_script/blob/master/rewrite/Loon/AdvertisingScript/AdvertisingScript.plugin
- https://github.com/fmz200/wool_scripts/blob/main/Surge/module/blockAds.module
- https://t.me/GitCube
- https://t.me/Aa28413761
- https://t.me/Nzmgs
- https://github.com/ZenmoFeiShi/Qx

## 红线与天花板（如实）

- 红线（绝不进任何拦截组）：appsec-mobile.meituan.com（mtgsig 签名+设备指纹上报，拦=触发下单/支付风控，无任何黑名单收录）/ api-unionid.meituan.com（统一账号）/ api-map.meituan.net（地图瓦片）/ shark.dianping.com（Pike 长连通道，核弹模块 S9 也误伤它）/ ddplus(+quic).meituan.net（TitansX/Picasso 动态模板包）/ mrn.meituan.net 与 beauty-*.meituan.net（VOD/直播拉流）/ assistify.meituan.com（零证据，暂判 CORE）/ awp-assets 与 awps-assets（H5 容器与活动混装）/ apimobile.meituan.com / paymp / i.meituan.com。
- 拒收条目（取证否决）：meituan.xn / meituan.yoga / meituangov.cn / meituancdn.cc——AliDNS 无解析或非美团主体，来源可疑，写了也不会命中。
- 能力天花板（如实）：开屏走 wmapi/mapi 主 API 路径与 s3plus 共享存储，首页轮播走 p*.meituan.net / img.meituan.net 共享图床的 /bizad|/wmbanner|/adunion 路径——DNS 层不可分；成熟方案（blackmatrix7/wool）全部用 Map Local/reject-dict 即直接证据。本插件对独立 ADN + impdsp/mads 走 DNS 黑洞，对同域开屏/广告图/热词走 Loon 原生 [Rewrite] v2（reject_dict / reject_img / response.json.jq）。
- iOS 与 Android 差异：官方《接入第三方SDK目录》标注腾讯营销联盟/BeiZi/天璇/快手联盟/酷盈/PolyGamma 仅 Android——本插件 iOS 侧不挂 pangle/gdt/kuaishou 组，避免无收益死规则。
- 只走精确域,不做 DOMAIN-SUFFIX 整域——美团交易规则依赖 *.meituan.com/*.meituan.net 深层子域（含 *.mtgsig 防刷签名路径）。
- 本插件 [Host]/[Rule] 全设备生效(Loon 无法按 App 限定):同一 SDK 域跨 App 共享黑洞,'按 App 插件'只是分组开关;配合全局 ads 插件 httpdns 组防绕过。
- v1.3.0 启用 Loon 原生 [Rewrite] v2 引擎复写层（enhance.active=true）：通过 [Argument] 的 cleanAds（默认开：开屏 reject_dict(200)、4 条共享图床广告目录 reject_img(200)、4 条搜索热词与启动图/Banner jq 置空）与 slimUI（默认关：底部 Tab 与推荐流精简）双开关控制 15 条原生复写规则 + 配套 QUIC 回退。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/meituan.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 43 条，[Rule] 8 条。
