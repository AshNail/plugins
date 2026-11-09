# 淘宝 · 去广告（原生复写层）

> 淘宝广告分两层：Alimama/Tanx/Simba/adashx 等独立广告域走 DNS 黑洞；开屏、推荐、活动等广告入口是 acs.m.taobao.com / guide-acs.m.taobao.com 的 mtop 路径，默认启用 Loon 原生 [Rewrite] v2 引擎复写（cleanAds 开关默认开）——10 条广告 mtop 路径在 request 阶段 reject_dict(200) 终止，开屏大图路径用 reject_img(200) 返回 1px 透明图；不包含上游 JS，交易/登录/支付红线不动。前置：同域复写层需已安装并信任 Loon 证书。

版本 **1.2.4** ｜ 功能基线 Loon **3.5.1(983)**+ （iOS/tvOS 口径；Mac 版是 0.x 独立一条线，插件头不声明门槛）｜ 净化层默认启用（`[Argument]`+`[MITM]`+`[Script]` 三层已在文件里生效，须已装并信任 Loon 证书）· 拦截面 `[Host]`/`[Rule]`

## 安装

[![一键导入 taobao.plugin](https://img.shields.io/badge/Loon-导入%E6%B7%98%E5%AE%9D%20%C2%B7%20%E5%8E%BB%E5%B9%BF%E5%91%8A%EF%BC%88%E5%8E%9F%E7%94%9F%E5%A4%8D%E5%86%99%E5%B1%82%EF%BC%89-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Ftaobao%2Ftaobao.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/taobao/taobao.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| 阿里广告/UT 独立端点 | B | 启用 | h-adashx.ut.taobao.com=AdashX 广告/UT 分片；ossgw.alicdn.com=广告素材网关；hudong.alicdn.com=互动广告素材；adashx4yt.m.taobao.com=优土侧 AdashX 分片；dsp/tmatch/stat/srd.simba.taobao.com=Simba 直通车竞价、定向与曝光统计子域（其余 atanx、tns.simba、adashx.m、wcp、audid-api、poplayer、rtb.julang 已由上方 sdks:["alimama"] 统一注入，此处不重复声明）。均为精确广告子域，媒体主域 alicdn.com 不整域。 |
| UT 埋点（默认关） | B | 默认关闭 | ut.taobao.com / umengacs.m.taobao.com / umengjmacs.m.taobao.com / abtest.alibaba.com=阿里 UT/友盟埋点与 AB 实验分流；关闭统计不等于去广告，默认关，需要隐私优先再开。 |
| 淘宝客/联盟归因（默认关） | B | 默认关闭 | tunion-api.m.taobao.com=淘宝联盟 CPS 归因；拦了会影响淘宝客取链/返利，默认关。 |
| 阿里 AMDC HTTPDNS 调度（默认关） | B | 默认关闭 | amdc.m.taobao.com / amdcopen.m.taobao.com=阿里 HTTPDNS 调度；拦后若 App 无回退可能拖慢建连，默认关。 |
| 阿里妈妈直通车点击跳转/外链（默认关） | B | 默认关闭 | mclick.simba.taobao.com / redirect.simba.taobao.com / textlink.simba.taobao.com / click.mz.simba.taobao.com / click.tz.simba.taobao.com=阿里妈妈直通车推广商品点击跳转与追踪；拦截后在搜索列表点带「广告」标的商品会打不开，默认关，需彻底绝育推广点击再开。 |
| 阿里妈妈 / TanX / 阿里广告监测（引用组） | A | 启用 | 域名真源见 ads 组/SDK 库 共 17 域 / 0 规则。 |
| QUIC 回退（增强层配套） | A | 启用 | 只对 `PROTOCOL,QUIC` 生效：拒的是 HTTP/3 这条通道、不是这台主机，同一主机的 TCP 正文/书架零影响。共 4 条。 |

## 默认启用的 MITM 层（本 App 未做证书固定；必须已装并信任 Loon 证书）

淘宝 iOS 的开屏/推荐/活动广告入口与交易共用 acs.m.taobao.com、guide-acs.m.taobao.com，不能黑洞整域。本层默认启用 Loon 原生 [Rewrite] v2 引擎复写（由 cleanAds 开关控制，零 JS 脚本）：10 条广告 mtop 路径在 request 阶段直接 reject_dict(200) 返回空字典；开屏全屏广告图路径用 reject_img(200) 返回 1px 透明 GIF。

- 解密主机（`[MITM] hostname`，4 个，本层已默认生效）：`acs.m.taobao.com`, `guide-acs.m.taobao.com`, `gw.alicdn.com`, `heic.alicdn.com`
- 配套 QUIC 回退（`AND,((DOMAIN-SUFFIX,<域>),(PROTOCOL,QUIC)),REJECT`，4 条，已生效）：MITM 只解密 TCP，App 走 HTTP/3 时 `URL-REGEX`、`[Rewrite]` 复写与脚本绑定全部静默失效；它拒的是 QUIC 这条通道，同一主机的 TCP 请求零影响。

### 开关（`[Argument]`）

| 开关 | 默认 | 作用 |
|---|---|---|
| `cleanAds` | true | 启用 Loon 原生 [Rewrite] v2 引擎复写：acs.m.taobao.com / guide-acs.m.taobao.com 的 10 条广告 mtop 路径在 request 阶段直接 reject_dict(200) 终止；gw/heic.alicdn.com 开屏推广大图路径用 reject_img(200) 返回 1px 透明图。需已安装并信任 Loon 证书。 |

### 净化复写（`[Rewrite]`）

| 规则 | 阶段 | 动作 | 开关 | 行为 |
|---|---|---|---|---|
| `kill-fliggy-screen` | request | `reject_dict` | `cleanAds` | 飞猪频道弹屏与营销资源拉取 |
| `kill-alibaba-getadv` | request | `reject_dict` | `cleanAds` | 阿里通用广告服务拉取接口 |
| `kill-etao-advertise` | request | `reject_dict` | `cleanAds` | 阿里妈妈一淘广告配置拉取 |
| `kill-alimusic-startinit` | request | `reject_dict` | `cleanAds` | 启动初始化营销配置接口 |
| `kill-tao-splash` | request | `reject_dict` | `cleanAds` | 淘宝 noah 开屏广告查询接口 |
| `kill-film-advertise` | request | `reject_dict` | `cleanAds` | 淘票票/影视模块广告查询接口 |
| `kill-o2o-ad` | request | `reject_dict` | `cleanAds` | 本地生活 O2O 广告网关拉取接口 |
| `kill-idle-welcome` | request | `reject_dict` | `cleanAds` | 闲置频道欢迎弹窗营销接口 |
| `kill-trip-tms` | request | `reject_dict` | `cleanAds` | 出行活动 TMS 营销资源查询接口 |
| `kill-guide-secondfloor` | request | `reject_dict` | `cleanAds` | 首页二楼活动配置与开屏引导拉取 |
| `kill-splash-img` | request | `reject_img` | `cleanAds` | 淘宝开屏全屏尺寸（1080/1125）octopus/tps 推广图返回 200 + 1px 透明 GIF |

> 净化主力放在引擎侧：`reject_*` 与 `response.json.*` 由 Loon 自己解压 `Content-Encoding: gzip`，脚本链不碰压缩体。脚本读响应体必须先 ungzip，而 `$utils.ungzip` 只有 Build ≥ 988 才有——低版本就是静默 passthrough，这正是「净化不生效」的那条链。

> 全层由 `src/apps/taobao.json` 的 `enhance` 整段生成（`tools/build-apps.py`），lint 逐行对账产物——直接改生成物会在下一次构建被覆盖。

前提与步骤：①Loon 装并信任证书（本层已默认解密这些主机） → ②要自动化就把 `[Argument]` 里的对应开关改成 true（默认关的那几个） → ③确认可用：冷启动后看日志里复写装载计数（`Reload rewrites:`）与脚本侧锚点行，再用探针绑定判断复写是否接管（探针消失 = 复写命中）。

> 证书固定红线：银行/微信/米家类 App 做了证书固定，MITM 直接失败甚至触发风控，那些插件不提供本层；本层只对未做证书固定的 App 提供，且每条路径都有下方公开证据。
> 反过来说：本层已经默认写在生效配置里，**证书没装好时这些主机的 TLS 会失败**——不是「没生效」而是「连不上」。装好证书再评估，或直接把 `[MITM]` 那两行注释掉退回零证书形态。

证据：
- https://kelee.one/
- https://github.com/blackmatrix7/ios_rule_script/blob/master/rule/Loon/Advertising/Advertising.list

## 红线与天花板（如实）

- 红线：*.taobao.com / *.tmall.com / *.alicdn.com 整族承载登录、订单、购物车、商品图与播放；本插件只做精确广告子域和广告路径，绝不做 DOMAIN-SUFFIX 整域。
- acs.m.taobao.com 与 guide-acs.m.taobao.com 是 mtop 主网关，交易与广告同域；DNS 层不黑洞它们，只在 MITM + [Rewrite] v2 层按 10 条广告 API 路径返回 200 空字典。
- v1.2.0 启用 Loon 原生 [Rewrite] v2 引擎复写层（enhance.active=true）：通过 [Argument] cleanAds 开关（默认开）驱动 10 条 reject_dict(200) + 1 条 reject_img(200) 规则及 4 台解密主机的 QUIC 回退，解决注释态增强层在订阅插件下无法直接开启的问题。
- 证据基线：可莉淘宝插件规则事实 + blackmatrix7 Advertising + anti-AD；淘宝 IPA 10.68.10 的 mtop 广告前缀已在公开主配置有独立证据。
- 红线补充：h5api.m.taobao.com 是 H5 交易/登录接口；login.taobao.com 是淘宝登录入口；passport.taobao.com 是淘宝账号/通行证；sec.taobao.com 是淘宝风控/安全接口；gw.alicdn.com 是图片/素材 CDN；img.alicdn.com 与 heic.alicdn.com 是商品图 CDN。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/taobao.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 37 条，[Rule] 4 条。
