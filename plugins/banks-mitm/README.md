# 银行与信用卡 · 静态广告CDN与专域接口净化（可选MITM） v1.1.0

> banks.plugin 配套可选 MITM 增强插件（默认启用 8 条路径级原生 [Rewrite] v2 规则 + 7 条 QUIC 回退，按开关分流控制）：针对招商掌上生活（res.cc.cmbimg.com/fsp/File/AdPlatformPublic/ 视频开屏 reject_video(200) + 静态图 reject_img(200)、s3gw.cmbimg.com 与双生域 s3gw.cmbimg.cn /mbappinitads/、pic1cdn.cmbchina.com/appinitads/）、浦发/浦大喜奔（lban.spdb.com.cn getAdvList/prefetchAdvList.ah reject_dict(200)）、工商银行（v.icbc.com.cn/userfiles/(ADResources|Resources/WAP/advertisement)/ reject_img(200)）与广发发现精彩（static.95508.com ads/popupads/advertising 目录 reject_img(200)）；严格隔离所有强 SSL Pinning 核心交易/支付网关与买单吧双线主网关 creditcardapp.bankcomm.com / creditcardapp.bankcomm.cn 及 mbmodule-openapi.paas.cmbchina.com。需安装并完全信任 Loon CA 证书后启用。

版本 **1.1.0** ｜ 功能基线 Loon **3.5.1(983)**+ （iOS/tvOS 口径；Mac 版是 0.x 独立一条线，插件头不声明门槛）｜ 净化层默认启用（`[Argument]`+`[MITM]`+`[Script]` 三层已在文件里生效，须已装并信任 Loon 证书）· 拦截面 `[Rule]`（本插件无 `[Host]` 黑洞层）

## 安装

[![一键导入 banks-mitm.plugin](https://img.shields.io/badge/Loon-导入%E9%93%B6%E8%A1%8C%E4%B8%8E%E4%BF%A1%E7%94%A8%E5%8D%A1%20%C2%B7%20%E9%9D%99%E6%80%81%E5%B9%BF%E5%91%8ACDN%E4%B8%8E%E4%B8%93%E5%9F%9F%E6%8E%A5%E5%8F%A3%E5%87%80%E5%8C%96%EF%BC%88%E5%8F%AF%E9%80%89MITM%EF%BC%89%20v1.1.0-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fbanks-mitm%2Fbanks-mitm.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/banks-mitm/banks-mitm.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| QUIC 回退（增强层配套） | A | 启用 | 只对 `PROTOCOL,QUIC` 生效：拒的是 HTTP/3 这条通道、不是这台主机，同一主机的 TCP 正文/书架零影响。共 7 条。 |

## 默认启用的 MITM 层（本 App 未做证书固定；必须已装并信任 Loon 证书）

本插件仅针对非核心静态图床 CDN 与独立广告后端启用 Loon 原生 [Rewrite] v2 复写（零 JS 脚本，按 3 个独立 [Argument] 开关分别启停）：① cleanCmbSplash：在掌上生活 AdPlatformPublic 目录按视频开屏（.mp4/.mov -> reject_video(200)）与图片开屏（reject_img(200)）两段有序拦截，并双线拦截 s3gw.cmbimg.com / s3gw.cmbimg.cn 的 mbappinitads/ 与 pic1cdn.cmbchina.com/appinitads/；② cleanSpdbAds：精确拦截浦发/浦大喜奔 lban.spdb.com.cn/mspmk-web-component/(getAdvList|prefetchAdvList).ah 返回 reject_dict(200)；③ cleanBankCdnAds：拦截工商银行 v.icbc.com.cn/userfiles/(ADResources|Resources/WAP/advertisement)/ 与广发发现精彩 static.95508.com 广告及 appPopupAds 目录返回 reject_img(200)。配套 7 条 HTTP/3 (QUIC) 回退规则防止绕过。

- 解密主机（`[MITM] hostname`，7 个，本层已默认生效）：`res.cc.cmbimg.com`, `s3gw.cmbimg.com`, `s3gw.cmbimg.cn`, `pic1cdn.cmbchina.com`, `lban.spdb.com.cn`, `v.icbc.com.cn`, `static.95508.com`
- 配套 QUIC 回退（`AND,((DOMAIN-SUFFIX,<域>),(PROTOCOL,QUIC)),REJECT`，7 条，已生效）：MITM 只解密 TCP，App 走 HTTP/3 时 `URL-REGEX`、`[Rewrite]` 复写与脚本绑定全部静默失效；它拒的是 QUIC 这条通道，同一主机的 TCP 请求零影响。

### 开关（`[Argument]`）

| 开关 | 默认 | 作用 |
|---|---|---|
| `cleanCmbSplash` | true | 双线拦截招商掌上生活静态图床纯广告路径（AdPlatformPublic 含 .mp4/.mov 视频开屏 reject_video(200) 与图片 reject_img(200)、s3gw.cmbimg.com 与 s3gw.cmbimg.cn mbappinitads / pic1cdn appinitads），不碰 mlife / az1mbasecc / intellicc / mbmodule-openapi / ccclub 核心网关。 |
| `cleanSpdbAds` | true | 精确拦截浦发 lban.spdb.com.cn/mspmk-web-component/getAdvList.ah 与 prefetchAdvList.ah，request 阶段返回 reject_dict(200) 空 JSON。 |
| `cleanBankCdnAds` | true | 精确拦截工行 v.icbc.com.cn/userfiles/(ADResources|Resources/WAP/advertisement)/ 与广发发现精彩 static.95508.com 广告/popupads 素材目录，返回 reject_img(200)。 |

### 净化复写（`[Rewrite]`）

| 规则 | 阶段 | 动作 | 开关 | 行为 |
|---|---|---|---|---|
| `kill-cmb-adplatform-video` | request | `reject_video` | `cleanCmbSplash` | 掌上生活 AdPlatformPublic 视频开屏物料优先命中 reject_video(200)，避免把 .mp4/.mov 响应成 GIF |
| `kill-cmb-adplatform` | request | `reject_img` | `cleanCmbSplash` | 掌上生活 AdPlatformPublic 纯广告图片物料目录（非视频物料兜底返回 1px 透明 GIF） |
| `kill-cmb-mbappinitads` | request | `reject_img` | `cleanCmbSplash` | 招行与掌上生活 S3 对象存储 mbappinitads 启动初始化广告目录（.com） |
| `kill-cmb-mbappinitads-cn` | request | `reject_img` | `cleanCmbSplash` | 招行与掌上生活双生域名 s3gw.cmbimg.cn 下的 mbappinitads 启动初始化广告目录 |
| `kill-cmb-pic1cdn-ads` | request | `reject_img` | `cleanCmbSplash` | 招行 pic1cdn 共享图床下的 appinitads 启动广告目录，不碰业务图路径 |
| `kill-spdb-advlist` | request | `reject_dict` | `cleanSpdbAds` | 浦发银行与浦大喜奔客户端开屏及营销广告列表接口（与 banks.plugin 注释态整域候选二选一，路径级更安全） |
| `kill-icbc-adresources` | request | `reject_img` | `cleanBankCdnAds` | 工商银行多媒体域名下的纯广告子目录，不动其余共享业务资源 |
| `kill-cgb-static-ads` | request | `reject_img` | `cleanBankCdnAds` | 广发银行发现精彩共享 CDN 下的 ads、popupads 与 advertising 静态素材子目录 |

> 净化主力放在引擎侧：`reject_*` 与 `response.json.*` 由 Loon 自己解压 `Content-Encoding: gzip`，脚本链不碰压缩体。脚本读响应体必须先 ungzip，而 `$utils.ungzip` 只有 Build ≥ 988 才有——低版本就是静默 passthrough，这正是「净化不生效」的那条链。

> 全层由 `src/apps/banks-mitm.json` 的 `enhance` 整段生成（`tools/build-apps.py`），lint 逐行对账产物——直接改生成物会在下一次构建被覆盖。

前提与步骤：①Loon 装并信任证书（本层已默认解密这些主机） → ②要自动化就把 `[Argument]` 里的对应开关改成 true（默认关的那几个） → ③确认可用：冷启动后看日志里复写装载计数（`Reload rewrites:`）与脚本侧锚点行，再用探针绑定判断复写是否接管（探针消失 = 复写命中）。

> 证书固定红线：银行/微信/米家类 App 做了证书固定，MITM 直接失败甚至触发风控，那些插件不提供本层；本层只对未做证书固定的 App 提供，且每条路径都有下方公开证据。
> 反过来说：本层已经默认写在生效配置里，**证书没装好时这些主机的 TLS 会失败**——不是「没生效」而是「连不上」。装好证书再评估，或直接把 `[MITM]` 那两行注释掉退回零证书形态。

证据：
- https://github.com/AdguardTeam/AdguardFilters
- https://github.com/Cats-Team/AdRules
- https://github.com/blackmatrix7/ios_rule_script
- https://site.cc.cmbimg.com/AgreementManager/agreement/AppSDK.html

## 怎么落实（分层落地与客户端协同）

### 1. 前置条件（必须与底座搭配、且先信任 Loon CA 证书）

- 先启用 `ads.plugin`（或 `ads-next.plugin`）+ 零证书底座 [`banks.plugin`](../banks/README.md)，再启用本插件（`banks-mitm.plugin` 只管 7 台静态 CDN/广告后端的 MITM 路径复写，不重复产出 `[Host]`/`[Rule]` 黑洞）。
- **不要在 `banks.plugin` 中同时取消 `# lban.spdb.com.cn = 127.0.0.1` 的注释**：同一主机若同时被 DNS 黑洞，HTTPS 请求在 DNS 阶段就被掐死，无法进入路径级 `reject_dict(200)`。
- 必须在系统里**安装并完全信任 Loon CA 根证书**（iOS：`设置 → 通用 → 关于本机 → 证书信任设置`）并开启 Loon 全局 MITM 开关；若设备未装证书，**请勿安装本插件**（仅保留 `banks.plugin`）。

### 2. 首次启用与掌上生活预缓存刷新

- 启用本插件并信任 CA 后，**上划彻底杀掉掌上生活 / 浦大喜奔 / 工行 / 发现精彩后台**；如果掌上生活此前通过 `preCacheAdvertiseSec` 已经把开屏图/视频写入本地沙盒，可先清除 App 缓存（或在当期物料过期后观察下一次新开屏）。
- 在 Loon「最近请求」日志中验证：当上述 App 拉取开屏素材时，对应路径命中 `[Rewrite]` 的 `reject_video(200)` / `reject_img(200)` / `reject_dict(200)`，同时账单、还款、转账卡片无白屏、功能图标无裂图或 TLS 握手报错。

### 3. 单家开关回退与能力边界（重要）

- 如果任一银行新版突然对上述 7 台静态 CDN 之一开启证书绑定导致局部图片裂开或弹窗，直接在 Loon 本插件详情页关闭对应开关（`cleanCmbSplash` / `cleanSpdbAds` / `cleanBankCdnAds`）；若仅关闭开关仍因 MITM 握手被拦截（Loon 的 `[MITM] hostname` 只要启用插件即生效），则直接停用本插件，仅保留零证书的 `banks.plugin`。
- 本插件**故意不包含买单吧（`creditcardapp.bankcomm.com` / `creditcardapp.bankcomm.cn`）、六大行强固定交易网关与云闪付核心接口**：买单吧开屏仍需依赖 `banks.plugin` + 官方「关怀版」+ 端内「消费者权益保护 → 其他授权管理」关闭，以及 iOS 27.2+「限制动作数据」（裸 `mdb://` 新版冷启多已不再跳过开屏，见 `docs/banks-creditcard-ad-removal.md`）。

## 红线与天花板（如实）

- 定位边界：本插件是 zero-MITM 底座插件 banks.plugin 的显式可选（opt-in）MITM 配套增强插件——不希望任何银行流量走 CA 解密的用户只装 banks.plugin 即可；仅在确认 Loon 已安装并完全信任根证书、且希望在 Loon 内一键开关静态广告图 CDN 与非核心广告后端路径级清理时，再叠加启用本插件。
- 硬性隔离红线（绝不写入 mitm_hosts，由 tests/lint-plugins.py check_banks_mitm_guard 反向锁死）：mlife.cmbchina.com / az1mbasecc.bas.cmbchina.com / intellicc.bas.cmbchina.com / mbmodule-openapi.paas.cmbchina.com / ccclub.cmbchina.com / trip.cmbchina.com（掌上生活与招行强 Pinning 核心 API、积存金 PaaS 与权益网关，社区实证放入 MITM 易致设置页打不开或网络异常）、creditcardapp.bankcomm.com / creditcardapp.bankcomm.cn / creditcard.bankcomm.com（买单吧双线主网关与通用 FastDFS 图床）、wallet.95516.com / base.95516.com / account.95516.com（云闪付强 Pinning 核心接口）、mbs.boc.cn（中行主网关）、yunbusiness.ccb.com（建行生活核心）、www.abchina.com.cn / msmp.abchina.com.cn / mobilepaas.abchina.com.cn（农行核心、风控与 mPaaS /mgw.htm 网关）、d.psbc.com / login-service.mobile-bank.psbc.com / mobile-bank.psbc.com（邮储核心网关），以及 yghsh.cebbank.com / static.cebbank.com / rs.creditcard.cmbc.com.cn / static.creditcard.hxb.com.cn / images.cib.com.cn / m.citiccardcdn.citicbank.com（业务与功能图标混装共享 CDN）。
- 诚实效果预期（掌上生活 & 买单吧）：① 掌上生活（招商银行信用卡）：本插件只解密静态图床 res.cc.cmbimg.com / s3gw.cmbimg.com / s3gw.cmbimg.cn / pic1cdn.cmbchina.com 的纯广告子目录，并在 AdPlatformPublic 目录按视频（.mp4/.mov -> reject_video(200)）与静态图（reject_img(200)）两段精准有序拦截；由于主 API preCacheAdvertiseSec 会在上一次启动把开屏图预缓存到本地沙盒，安装后需先划掉掌上生活后台并清理缓存（或等待当期预缓存过期）方能观测效果，且开屏容器若展示本地兜底/第一方卡片位属客户端原生限制。② 买单吧（交通银行信用卡）：其开屏接口 queryGuidePageAds.do / getPopAds.do / qryLaunchAds.do / qryPopAds.do 与全部交易共用强 Pinning 双线主网关 creditcardapp.bankcomm.com / creditcardapp.bankcomm.cn，图片走通用 /tfimg/public00/M00/ 与 /tofimg/，Loon 无法在不触碰主网关的前提下安全切除，因此本插件不覆盖买单吧，买单吧仍依赖零证书 banks.plugin + 官方关怀版 + 端内权限关闭 +（带冷启局限说明的）URL Scheme 协同。
- 规则来源可追溯：res.cc.cmbimg.com/fsp/File/AdPlatformPublic/（含 .mp4 视频开屏与图片素材）、s3gw.cmbimg.com/mbappinitads/、s3gw.cmbimg.cn/mbappinitads/ 与 pic1cdn.cmbchina.com/appinitads/ 来自社区实证开屏/初始化广告素材路径；lban.spdb.com.cn/mspmk-web-component/(getAdvList|prefetchAdvList).ah 来自 blackmatrix7/ios_rule_script（使用 reject_dict(200) 比 DNS 黑洞更细粒度且规避误伤其它 web-component）；v.icbc.com.cn/userfiles/(ADResources|Resources/WAP/advertisement)/ 来自 AdGuard-CN 与 AdRules（$domain 过滤路径规则）；static.95508.com/(mmg/images/ads|mmg/ciop/sysabbr/cmep/images/(app)?popupads|icppweb/images/modelMaterial/advertising)/ 来自 blackmatrix7 与 AdRules 公开广发发现精彩纯广告与弹窗素材路径。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/banks-mitm.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 0 条，[Rule] 7 条。
