# 闲鱼 · 去广告（原生复写层）

> 闲鱼广告 100% 内嵌 goofish mtop 主网关（splash.ads / nextfresh bizType / item.recommend bizType=mamaAD 均为同域 API 名）。DNS 层阻断阿里广告 SDK 端点 iyes.youku.com 与淘宝客 Tunion 归因接口；同域 mtop 广告默认启用 Loon 原生 [Rewrite] v2 引擎复写（cleanAds 开关默认开、cleanFeed 激进精简开关默认关，零 JS 脚本）。前置：同域复写层需已安装并信任 Loon 证书。

版本 **1.6.2** ｜ 功能基线 Loon **3.5.1(983)**+ （iOS/tvOS 口径；Mac 版是 0.x 独立一条线，插件头不声明门槛）｜ 净化层默认启用（`[Argument]`+`[MITM]`+`[Script]` 三层已在文件里生效，须已装并信任 Loon 证书）· 拦截面 `[Host]`/`[Rule]`

## 安装

[![一键导入 xianyu.plugin](https://img.shields.io/badge/Loon-导入%E9%97%B2%E9%B1%BC%20%C2%B7%20%E5%8E%BB%E5%B9%BF%E5%91%8A%EF%BC%88%E5%8E%9F%E7%94%9F%E5%A4%8D%E5%86%99%E5%B1%82%EF%BC%89-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fxianyu%2Fxianyu.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/xianyu/xianyu.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| 阿里广告 SDK 端点（闲鱼净化模块唯一 REJECT 域） | A | 启用 | iyes.youku.com=阿里广告 SDK 端点（apiv4-iyes 为其分片,整域+通配）;anti-AD/AdGuard/hagezi/wool XianYu 模块四源收录。 |
| 淘宝客/阿里妈妈 API 端点 | B | 启用 | tunion-api.m.taobao.com=淘宝联盟(Tunion) CPS 广告归因接口,taobao.com 是共享主域、全局 ads 插件的 =alimama.com 整域黑洞罩不到它,故在此精确单列;afpapi.alimama.com 已由 ads 插件 alibaba 组整域覆盖,此处只作按 App 开关的完整起见。DoH 实测 afpapi CNAME 终结于 adsz.wagbridge.tanx.alimama.com(Tanx=阿里妈妈 AdX)。 |
| 淘宝系 AMDC HTTPDNS 调度（默认关） | B | 默认关闭 | amdc.m/amdcopen.m.taobao.com=阿里 HTTPDNS 调度;闲鱼净化脚本专改 /amdc/mobileDispatch。拦=广告域解析绕过消失,但阿里系 App 若无回退逻辑可能拖慢建连——默认关,验证后再开。 |
| 阿里妈妈 / TanX / 阿里广告监测（引用组） | A | 启用 | 域名真源见 ads 组/SDK 库 共 16 域 / 0 规则。 |
| QUIC 回退（增强层配套） | A | 启用 | 只对 `PROTOCOL,QUIC` 生效：拒的是 HTTP/3 这条通道、不是这台主机，同一主机的 TCP 正文/书架零影响。共 2 条。 |

## 默认启用的 MITM 层（本 App 未做证书固定；必须已装并信任 Loon 证书）

闲鱼 iOS 未做证书固定：开屏/曝光计数是 mtop 主网关 acs.m.goofish.com / g-acs.m.goofish.com 的路径名（splash.ads / idle.ad.expose），信息流广告则在同域 API 的 JSON 字段里（nextfresh 分区 / item.recommend 的 bizType=mamaAD）。黑洞整网关=废掉 App，本层默认启用 Loon 原生 [Rewrite] v2 引擎复写（零 JS 脚本）：cleanAds（默认开）拦截纯广告路径并剥离 mamaAD 卡片、悬浮球、搜索暗词与各处 Banner；cleanFeed（默认关）提供激进的信息流仅留商品与我的页精简。

- 解密主机（`[MITM] hostname`，2 个，本层已默认生效）：`acs.m.goofish.com`, `g-acs.m.goofish.com`
- 配套 QUIC 回退（`AND,((DOMAIN-SUFFIX,<域>),(PROTOCOL,QUIC)),REJECT`，2 条，已生效）：MITM 只解密 TCP，App 走 HTTP/3 时 `URL-REGEX`、`[Rewrite]` 复写与脚本绑定全部静默失效；它拒的是 QUIC 这条通道，同一主机的 TCP 请求零影响。

### 开关（`[Argument]`）

| 开关 | 默认 | 作用 |
|---|---|---|
| `cleanAds` | true | 启用 Loon 原生 [Rewrite] v2 引擎复写：splash.ads、idle.idleadv、idle.ad.expose 等 7 个广告/模块端点在 request 阶段 reject_dict(200) 终止；商品推荐 mamaAD 卡片、悬浮球、搜索预填词、顶部省钱 Tab、群聊/圈子 Banner 通过 response.json.jq 精准剥离。需已安装并信任 Loon 证书。 |
| `cleanFeed` | false | 首页 nextfresh / 本地信息流 / 搜索结果只留 item、删除搜索发现页与我的页底部商品推荐、精简我的页分区。因过滤粒度较激进默认关，按需开启。 |

### 净化复写（`[Rewrite]`）

| 规则 | 阶段 | 动作 | 开关 | 行为 |
|---|---|---|---|---|
| `kill-splash-ads` | request | `reject_dict` | `cleanAds` | 闲鱼开屏广告 mtop 请求直接返回 200 + 空字典 |
| `kill-idleadv-restore` | request | `reject_dict` | `cleanAds` | 闲鱼切回前台/场景恢复开屏与弹层广告请求（mtop.idle.idleadv.scene.restore 等）直接返回 200 + 空字典 |
| `kill-ad-expose` | request | `reject_dict` | `cleanAds` | 闲鱼广告曝光计数上报接口直接返回 200 + 空字典 |
| `kill-whale-modulet` | request | `reject_dict` | `cleanAds` | 首页顶部营销模块（home.whale.modulet）直接返回 200 + 空字典 |
| `kill-resell-recommend` | request | `reject_dict` | `cleanAds` | 「这些宝贝超好卖」推广模块直接返回 200 + 空字典 |
| `kill-topic-banner` | request | `reject_dict` | `cleanAds` | 我的页话题横幅（topic.banner）直接返回 200 + 空字典 |
| `kill-coin-nextfresh` | request | `reject_dict` | `cleanAds` | 闲鱼币推荐信息流（idle.coin.nextfresh）直接返回 200 + 空字典 |
| `clean-item-recommend` | response | `response.json.jq` | `cleanAds` | 商品底部推荐：只删 bizType=mamaAD 的阿里妈妈广告卡片 |
| `clean-strategy-list` | response | `response.json.jq` | `cleanAds` | 首页右下角悬浮球：留一个空 strategy 占位 |
| `clean-search-shade` | response | `response.json.jq` | `cleanAds` | 搜索框预填/热词：留一个空占位 |
| `clean-search-activate` | response | `response.json.jq` | `cleanAds` | 搜索页「猜你可能找」推广卡片清空 |
| `clean-circle-savemoney` | response | `response.json.jq` | `cleanAds` | 首页顶部 Tab：去掉 saveMoney 省钱推广位 |
| `clean-group-banner` | response | `response.json.jq` | `cleanAds` | 群聊/消息页 banner 位清空 |
| `clean-circle-banner` | response | `response.json.jq` | `cleanAds` | 圈子页 banner 位清空 |
| `clean-playboy-recommend` | response | `response.json.jq` | `cleanAds` | 消息页推荐位清空 |
| `slim-home-nextfresh` | response | `response.json.jq` | `cleanFeed` | 首页信息流：顶部只留首项、分区只留 item |
| `slim-search-result` | response | `response.json.jq` | `cleanFeed` | 搜索结果信息流：只留 item 结果 |
| `slim-local-home` | response | `response.json.jq` | `cleanFeed` | 本地信息流：分区只留 item |
| `slim-search-discover` | response | `response.json.delete` | `cleanFeed` | 搜索发现页：原生点分路径删除 data.resultList |
| `slim-my-adapter` | response | `response.json.jq` | `cleanFeed` | 我的页面：清空 ability 并只留 head/user/trade 分区 |
| `slim-buy-feeds` | response | `response.json.delete` | `cleanFeed` | 我的页面底部商品推荐：原生点分路径删除 data.sections |
| `slim-recommend-list` | response | `response.json.jq` | `cleanFeed` | 商品推荐列表：整列清空 cardList |

> 净化主力放在引擎侧：`reject_*` 与 `response.json.*` 由 Loon 自己解压 `Content-Encoding: gzip`，脚本链不碰压缩体。脚本读响应体必须先 ungzip，而 `$utils.ungzip` 只有 Build ≥ 988 才有——低版本就是静默 passthrough，这正是「净化不生效」的那条链。

> 全层由 `src/apps/xianyu.json` 的 `enhance` 整段生成（`tools/build-apps.py`），lint 逐行对账产物——直接改生成物会在下一次构建被覆盖。

前提与步骤：①Loon 装并信任证书（本层已默认解密这些主机） → ②要自动化就把 `[Argument]` 里的对应开关改成 true（默认关的那几个） → ③确认可用：冷启动后看日志里复写装载计数（`Reload rewrites:`）与脚本侧锚点行，再用探针绑定判断复写是否接管（探针消失 = 复写命中）。

> 证书固定红线：银行/微信/米家类 App 做了证书固定，MITM 直接失败甚至触发风控，那些插件不提供本层；本层只对未做证书固定的 App 提供，且每条路径都有下方公开证据。
> 反过来说：本层已经默认写在生效配置里，**证书没装好时这些主机的 TLS 会失败**——不是「没生效」而是「连不上」。装好证书再评估，或直接把 `[MITM]` 那两行注释掉退回零证书形态。

证据：
- https://github.com/ddgksf2013/Rewrite/blob/master/AdBlock/GoofishAds.conf
- https://github.com/fmz200/wool_scripts/blob/main/Surge/module/blockAds.module
- https://t.me/GitCube
- https://t.me/Aa28413761

## 红线与天花板（如实）

- 红线：*.goofish.com / *.idlefish.com / mtop 网关域（g-acs.m.goofish.com→alibabacorp mtop ingress）全部是核心功能;acs.m.goofish.com 出现在个别模块的 REJECT 里是错误规则,打死整个 App——拒收。
- 取证否决：m.goofish.com / awl.goofish.com 实测 NXDOMAIN（不存在）;xianyu.mobi 与 blackmatrix7 的 16 个乱码域是淘宝短链跳转服务（cname.tb.cn），拦=断分享链接;cdn.ynuf.aliapp.org=阿里无线安全 UMID 指纹,禁拦。
- 证据基线：闲鱼全部广告面在同域 API 名上——开屏 mtop.taobao.idlecommerce.splash.ads、切回前台场景恢复开屏 mtop.idle.idleadv.scene.restore、信息流 nextfresh bizType、底部推荐 bizType==mamaAD（字段名直接点名阿里妈妈）;素材共用 *.alicdn.com 共享 CDN。第三方列表 goofish 域零命中。
- 本插件 [Host]/[Rule] 全设备生效(Loon 无法按 App 限定):同一 SDK 域跨 App 共享黑洞,'按 App 插件'只是分组开关;配合全局 ads 插件 httpdns 组防绕过。
- 第二轮取证复检(2026-10-28)：mma.alimama.com 实测 NXDOMAIN(网传『阿里妈妈端点』不存在,禁凭品牌造域);开屏素材无 alicdn 之外的独立 CDN(墨鱼 GoofishAds.conf 亦无单独素材域);h-adashx.ut.taobao.com=阿里 UT/AdashX 埋点,全阿里系 App 共享,属全局 ads 插件的决策面,不进本按 App 插件。
- v1.6.1 启用 Loon 原生 [Rewrite] v2 引擎复写层（enhance.active=true）：通过 [Argument] 的 cleanAds（默认开：7 条开屏/场景恢复/曝光/推广模块 request reject_dict(200) + 8 条商品推荐 mamaAD / 悬浮球 / 搜索暗词 / 省钱 Tab / 群聊圈子 Banner jq 剥离）与 cleanFeed（默认关：7 条激进信息流/我的页精简，其中 search.discover 与 item.buy.feeds 升级为原生 response.json.delete）双开关控制 22 条原生复写规则 + 配套 QUIC 回退。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/xianyu.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 22 条，[Rule] 2 条。
