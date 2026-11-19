# 中国大陆银行系（六大行 + 信用卡 App + 云闪付）广告移除深度分析与分层落地方案

> **安全边界与双插件分层**：本仓库将银行业规则拆为两个互补插件——
> 1. [`banks.plugin`](../plugins/banks/banks.plugin)（**零证书 / 零 MITM 底座**）：由 `tests/lint-plugins.py` 的 `APP_NO_ENHANCE_SLUGS` 强制锁定禁止任何 MITM 解密，仅运行纯连接层 `[Host]`/`[Rule]`，适合所有不愿开启任何银行域名 CA 解密的用户。
> 2. [`banks-mitm.plugin`](../plugins/banks-mitm/banks-mitm.plugin)（**可选静态 CDN MITM 伴随插件**）：在保证零触碰强 SSL Pinning 核心交易网关（`mlife`/`az1mbasecc`/`intellicc`/`mbmodule-openapi`/`creditcardapp(.bankcomm.com|.bankcomm.cn)`/`wallet.95516.com`/`mbs.boc.cn`/`yunbusiness.ccb.com`/`msmp.abchina.com.cn`/`mobilepaas.abchina.com.cn`/`d.psbc.com`）的前提下，通过原生 `[MITM]` + `[Rewrite]` v2（8 条 `reject_video(200)`/`reject_img(200)`/`reject_dict(200)` + 7 条 `PROTOCOL,QUIC` 回退 + 3 组 `[Argument]` 独立开关）在 Loon 内直接落地掌上生活（含 `.cmbimg.cn` 双生域与 `.mp4/.mov` 视频开屏）、浦大喜奔、工商银行、广发发现精彩（含 `popupads`）的静态/视频广告 CDN 与独立广告接口清理。

---

## 一、核心结论：为何仅靠 `banks.plugin`「掌上生活 / 买单吧」仍显示开屏广告？

如果你已按最佳实践同时启用了 `ads.plugin`（或 `ads-next.plugin`）+ `banks.plugin`（当前含 **7 条生效 `[Host]` + 9 条 `[Rule]`**、**14 条默认关闭的可选遥测/接口候选**），打开 **掌上生活**、**买单吧** 或六大行 App 依然看到开屏广告，这**不是**规则未生效或插件漏写了商业广告联盟域名，而是由国内银行 App 的三重技术现实决定的：

1. **合作品牌不同体于外部广告联盟，广告与核心业务同域混装**：
   受金融监管与安全合规审计约束，六大国有银行手机银行与全国性银行信用卡 App 主启动流程几乎**不接入穿山甲 / 优量汇 / 快手联盟等外部商业广告 SDK**。它们的开屏广告直接由**本行信用卡中心一级 API 网关**下发 JSON 配置，再从**与图标/卡面/UI 共用的静态图床 CDN** 下载图片。在只能看到域名的 DNS/`[Host]` 层，**整域黑洞等于直接切断查账、还款或首页渲染**。
2. **本地沙盒预缓存（Pre-cache）机制**：
   以掌上生活 `preCacheAdvertiseSec` 等接口为例，客户端会在**前一次启动或前后台切换时**预先拉取开屏物料并落盘至 App 沙盒；即使次日网络请求被拦或处于弱网环境，冷启动仍会读取已落盘的本地开屏缓存直接展示。
3. **强制 SSL Pinning（证书绑定）与完整性/越狱检测**：
   掌上生活、买单吧与六大行核心 API 网关普遍启用强 SSL Pinning 或客户端双向校验。任何尝试将 `mlife.cmbchina.com`、`az1mbasecc.bas.cmbchina.com`、`creditcardapp.bankcomm.com` 等网关放入 `[MITM]` `hostname` 的做法，都会触发「网络异常」「设置页打不开」「安全提示」甚至直接闪退；即使在 Android 端使用 Xposed/重打包去 Pinning，也会触发更高等级的反欺诈、设备指纹异常或账号风控。

---

## 二、重点剖析：掌上生活 & 买单吧开屏链路全拆解

### 1. 掌上生活（招商银行信用卡，`cmbchina.com` / `cmbimg.com`）

> 提示：域名映射常见误区——**掌上生活**是招商银行信用卡（`cmbchina.com` / `cmbimg.com`），而 `cmbc.com.cn` 是**中国民生银行**（全民生活），两者毫无关系。

| 主机名 | 观察路径 / 作用 | 所属分类 | DNS 层整域拦截后果 | 本插件处置 |
|---|---|---|---|---|
| `mbads.paas.cmbchina.com` | 招行 PaaS 平台独立广告投放子域（AdRules / HaGeZi PRO / anti-AD 多源收录，0 `@@` 例外） | 独立广告子域 | 无已知核心交易回归 | **默认启用**（`[Host]` + pre-DNS） |
| `mlife.cmbchina.com` | `/ClientFace(Service)?/.../preCacheAdvertiseSec`、`/getAdvertisement.json`、`/preCacheAdvertise.json`（开屏预缓存 + **核心业务 API 网关**） | 同域混装主网关（SSL Pinning） | 账单、额度、活动与登录态全部中断；放进 `[MITM]` 触发「设置页打不开 / 网络异常」 | **红线放行** |
| `az1mbasecc.bas.cmbchina.com` | `/Edge/api/mlife.clientface.clientservice.api.advertiseService/preCacheAdvertiseSec`（新版 Edge 开屏预缓存及基础通信网关） | 同域混装主网关（SSL Pinning） | 中断掌上生活基础通信与初始化链路 | **红线放行** |
| `intellicc.bas.cmbchina.com` | `/Edge/api/mlife.intelli.render.api.render/getDynamicDataSec`（智能动态渲染/楼层数据接口） | 动态渲染共用网关 | 首页与频道楼层卡片空白 | **红线放行** |
| `mbmodule-openapi.paas.cmbchina.com` | 招行 PaaS OpenAPI 核心网关（社区存在 `/graphic/v2/module/graphic` 复写，但同域承载积存金行情 `zBuyPrc`/`zSelPrc` 等核心模块且强 Pinning） | 同域混装强 Pinning 网关 | DNS 黑洞或强制 MITM 会损伤积存金与招行核心服务 | **红线放行** |
| `res.cc.cmbimg.com` / `res.cc.cmbimg.cn` | `/fsp/File/AdPlatformPublic/...`（广告图片及 `.mp4`/`.mov` 视频开屏素材，同时承载 `/fsp/File/...` 业务通用静态资源） | 共享静态/视频 CDN 图床 | 静态资源大面积破图 | **红线放行**（`.com` 可选 `banks-mitm` 先视频 `reject_video(200)` 后图像 `reject_img(200)`） |
| `s3gw.cmbimg.com` / `s3gw.cmbimg.cn` | `/mbappinitads/...`（`.com` 与 `.cn` 双生 S3 对象存储网关，同时托管通用 App 静态资源与初始化包） | 双生共享对象存储网关 | 非广告路径资源同步受影响 | **红线放行**（可选 `banks-mitm` 双线路径拦截） |
| `pic1cdn.cmbchina.com` | `/appinitads/...`（与业务静态图共用招行图片 CDN） | 共享静态图床 | 业务 UI/宣传图裂图 | **红线放行**（可选 `banks-mitm` 路径拦截） |
| `resource.cmbchina.com` | `/fsp/File/ClientFacePublic/...`（客户端公共资源与素材托管） | 共享公共资源 CDN | 客户端 UI/资源异常 | **红线放行** |
| `ccclub.cmbchina.com` | 招商银行信用卡俱乐部/会员中心域 | 卡权益核心业务域 | blackmatrix7 issue #972 实证拦截即破坏招行 App 信用卡核心标签页 | **红线放行** |
| `trip.cmbchina.com` | 招行商旅预订门户（3 源开源黑名单设 `@@` 一方白名单） | 业务门户 | 商旅订票入口异常 | **红线放行** |
| `log.cmbchina.com` | 招行行为日志域名（3 源收录） | 遥测日志 | 低风险，但属 `log` 可观测域名 | **默认关**（`bank_telemetry`） |
| `metric-sz.ccd.cmbchina.com` | 招行卡中心深圳指标遥测（HaGeZi PRO 收录） | 遥测日志 | 不影响主交易，但存在遥测回退风险 | **默认关**（`bank_telemetry`） |
| `site.cc.cmbimg.com` | 掌上生活官方《第三方共享个人信息清单 / AppSDK.html》合规页托管域 | 合规信息发布页 | 合规说明页无法访问 | **红线放行** |

### 2. 买单吧（交通银行信用卡，`bankcomm.com` / `bankcomm.cn`）

> 提示：域名映射常见误区——**买单吧**是交通银行信用卡（`bankcomm.com` / `bankcomm.cn`），而 `spdbccc.com.cn` 是**浦发银行信用卡中心**（浦大喜奔）。另：**买单吧官网《第三方 SDK 目录》实名披露仅接入个推/厂商 Push（交易提醒通道）与神策数据（行为统计，已由 `ads` 默认关 `analytics` `=sensorsdata.cn` 覆盖），未接入穿山甲/优量汇等外部广告联盟——个推（`getui` / `gepush`）不可在全局乱杀**。

| 主机名 | 观察路径 / 作用 | 所属分类 | DNS 层整域拦截后果 | 本插件处置 |
|---|---|---|---|---|
| `ad.bankcomm.com` | 历史保留精确商业广告子域（27 份开源清单 0 命中，随 lint 守卫保留） | 独立广告子域（零副作用） | 无副作用（主流量不经此处） | **默认启用**（`[Host]` + pre-DNS） |
| `creditcardapp.bankcomm.com` / `creditcardapp.bankcomm.cn` | `/mapp/common/queryGuidePageAds.do`、`getPopAds.do`、`.cn` 双线 `/mappweb_interface/common/qryLaunchAds.do` 与 `qryPopAds.do`（开屏/弹窗）及全部移动业务交易请求 | **双线主移动网关**（SSL Pinning） | DNS 黑洞整域 = 买单吧直接无网络；MITM 解密触发证书校验失败 | **红线放行** |
| `creditcard.bankcomm.com` | `/tfimg/public00/M00/...` 与 `/tofimg/...`（广告物料与银行官方公共图片/网页共用 FastDFS 站点） | 共享静态图床与网站 | 首页活动图与共用界面静态文件丢失 | **红线放行** |
| `vads.bankcomm.cn` | 历史文档仅见早期 IPA 分析提及，27 份开源黑名单 0 命中，无现代端内实证抓包 | 未证实历史主机名 | 语义未证，不盲目收入生效层 | **不启用**（`triage_exclude` 记账） |

---

## 三、中国大陆六大国有银行全系矩阵（含配套生活/信用卡 App）

核查工商银行、建设银行、农业银行、中国银行、交通银行、邮储银行六大行官网披露的《第三方 SDK 目录》及 27 份主流开源去广告清单（anti-AD、AdGuard-CN、AdRules、HaGeZi PRO 等）：
- **六大行共同规律**：核心交易端均受监管要求不嵌入穿山甲/优量汇等外部广告联盟 SDK（仅在必要环节接入手机厂商推送、个推/极光及合规地图/风控 SDK，外加经审计的基调听云/博睿/Bugly 等 APM）；
- **开源清单盲区与误杀风险**：`ad.icbc.com.cn`、`ad.boc.cn`、`ad.bankcomm.com`、`ad.psbc.com` 在全部 27 份列表均 **0 命中**，随既有守卫保留零风险规则；而多个含 `ccb`、`abc`、`icbc` 子串的历史收录实为**误杀高危域**或**第三方海外同名公司域名**。

| 银行 | 包含 App | 已启用零风险规则 | 默认关可选组（按需） | 不可黑洞的共享网关 / CDN / 误杀红线（已写入 `protected-roots.json` 与 `banks.json`） |
|---|---|---|---|---|
| **工商银行** | 中国工商银行 / 工银e生活 | `ad.icbc.com.cn` | `TingYun` / `NetworkBench` / `Bonree`（`bank_telemetry`）；Web Qualtrics 问卷弹层由 `ads` 默认关 `analytics`（`=siteintercept.qualtrics.com`）可选承接 | `*.icbc.com.cn`、`*.95588.cn` 整族；`v.icbc.com.cn`（仅 `/userfiles/ADResources/` 等目录为广告）；`elife.icbc.com.cn`；`image2.elife.icbc.com.cn`（`/filepath/elife/` 共享图床）；`pv.elife.icbc.com.cn`（**blackmatrix7 issue 实证拦则破坏工银e生活「爱购8.8」与首页加载**）；`xykpay.3d2.icbc.com.cn`（3D-Secure 验证，2 源 `@@`）；`m.icbc.com.cn`（3 源 `#@`）；`oisc.icbc.com.cn`（**1hosts-lite 误收：实为工商银行境外企业网银系统 OISC 门户**）；Web `@@` 例外含 `/ICBC_ADJS/`、`/Portal_Resources/Common/AdCss/` |
| **建设银行** | 中国建设银行 / 建行生活 | `adv.ccb.com`、`imageadv.ccb.com`（建行 Cookie 政策实证 + 双源 0 `@@`） | `TingYun` / `NetworkBench` / `Bonree`（`bank_telemetry`） | `*.ccb.com`、`*.ccb.com.cn`、`*.95533.cn` 整族；`yunbusiness.ccb.com`（建行生活 `/clp_service/txCtrl` 同域混走开屏 `txcode=A3341A002/A006/A009` 与签到/登录 `A3341A038/autoLogin`，且为代理检测 `skip-proxy` 核心）；`buy.ccb.com`（3 源 `#@` 善融商务）；伪建行误配域：`marketing.ccbtechnology.com`（美商 MSP）、`ss.genesisccb.com`（美商化工）、`smsccb.com`、`tnccb.com` |
| **农业银行** | 中国农业银行 | 无独立可拦广告域 | `firefly.abchina.com.cn`（`/firefly-collection/Collect` 行为采集，收入 `bank_telemetry`） | `*.abchina.com`、`*.abchina.com.cn`、`*.95599.cn` 整族（`95599.cn` 含 3 源 `@@`）；`ad.abchina.com`（4 源 `@@` 白名单）；`www.abchina.com.cn`、`msmp.abchina.com.cn`（风控 `skip-proxy`）与 `mobilepaas.abchina.com.cn`（Alipay mPaaS `/mgw.htm` 核心网关）；`enjoy.cdn-static.abchina.com.cn` 与 `midc.cdn-static.abchina.com.cn`（**`blackmatrix7` AdvertisingLite issue 实证误拦致白屏/缺组件**） |
| **中国银行** | 中国银行（原「缤纷生活」已于 **2026-06-30 24 时**全面停服并迁入中国银行 App） | `ad.boc.cn` | `TingYun` / `NetworkBench` / `Bonree`（`bank_telemetry`） | `*.boc.cn`、`*.bankofchina.com`、`*.95566.cn` 整族；`mbs.boc.cn`（`/ubas-mgateway-static/images/advertType/` 与主交易共用，强 Pinning）；`cdn1.mbs.boc.cn`；`jf365.boc.cn`、`cdn2.jf365.boc.cn`、`mlife.jf365.boc.cn`（积分 365 与原缤纷生活迁入权益域）；适老版本为「岁悦长情版」 |
| **交通银行** | 交通银行 / 买单吧 | `ad.bankcomm.com` | `TingYun` / `NetworkBench` / `Bonree`（`bank_telemetry`） | `*.bankcomm.com`、`*.bankcomm.cn`、`*.95559.com.cn` 整族；`creditcardapp.bankcomm.com` 与 `creditcardapp.bankcomm.cn`（`queryGuidePageAds.do` / `getPopAds.do` / `qryLaunchAds.do` 业务混装）；`creditcard.bankcomm.com`（`/tfimg/public00/M00/` 与 `/tofimg/` 共享图床）；`vads.bankcomm.cn`（未证实暂不启）；`getui` / `gepush` 推送 |
| **邮储银行** | 邮储银行（原「邮储信用卡」已公告于 **2026-11-25 24 时**停服并迁入邮储银行 App） | `ad.psbc.com` | `TingYun` / `NetworkBench` / `Bonree`（`bank_telemetry`） | `*.psbc.com`、`*.psbc.com.cn`、`*.95580.cn` 整族；`login-service.mobile-bank.psbc.com`、`mobile-bank.psbc.com`（登录与 `skip-proxy`）；`d.psbc.com`（实证 `:9091/mcc/resources` 拦截即导致邮储首页与转账异常） |

---

## 四、全国性股份制银行 / 主流城商行信用卡 App 与银联云闪付全系矩阵

除招商（掌上生活）与交通（买单吧）外，对其余全国性股份制银行、2025–2026 关停并转涉事城商行信用卡 App 与云闪付逐一梳理其广告/遥测端点与必须保护的共享网关（同时明确拒绝社区陈旧正则对图标/公共图片目录的误杀：如 `appspace-img/icon/*.png`、`/static/picture/*.jpg`、`/mmc/img/*.jpg`、`group1/M00/*.jpg`、`/commons/uploads/commons/`）：

| App（所属银行） | 已启用 / 可选遥测组覆盖 | 开屏 / 营销同域混装或共享图床红线（禁止整域黑洞） | 端内官方隐私与推荐关闭路径 |
|---|---|---|---|
| **浦发银行 / 浦大喜奔** | **`spdb_ad_optional`**（默认关）：`lban.spdb.com.cn`（`/mspmk-web-component/getAdvList.ah` 与 `prefetchAdvList.ah`，在 `banks-mitm` 默认启用 `reject_dict(200)`）；TalkingData 由 `ads` `analytics` 承接 | `*.spdb.com.cn`、`*.spdbccc.com.cn`、`*.95528.cn`、`per.spdb.com.cn`、`ebank.spdb.com.cn`（个人网银红线，严禁对 `*.spdb.com.cn` 用 `.*adv.*` 泛正则）、`image.spdbccc.com.cn`（共享卡面/活动图床） | 浦发银行主端：`我的 → 设置 → 安全设置 → 其他管理选项 → 个性化推荐` + `设置 → 消息/通知设置` + 切「长辈版」；浦大喜奔：`我的 → 设置 → 用户保护中心 → 个性化推荐设置` |
| **动卡空间**（中信银行） | `bank_telemetry`（按需：TingYun/NetworkBench/Bonree） | `*.ecitic.com`（3 源 `@@\|\|ecitic.com/source/*/pop`）、`*.citicbank.com`、`m.creditcard.ecitic.com`（`/citiccard/mbk/.../appStartAdv`）、`imcs.citicbank.com`、`m.citiccardcdn.citicbank.com`（`/appspace-img/icon/` 为功能图标目录，禁按正则误切） | `首页 → 个人中心 → 设置 → 隐私设置 → 个性化广告推荐` |
| **阳光惠生活**（光大银行） | `bank_telemetry`（按需） | `*.cebbank.com`、`*.cebbank.com.cn`、`*.95595.com`、`yghsh.cebbank.com`、`.static.cebbank.com`（`/static/picture/` 为混装目录，禁整目录切图） | `我的 → 设置 → 隐私管理 → 个性化推荐设置` |
| **发现精彩**（广发银行） | `bank_telemetry`（按需） | `*.cgbchina.com.cn`、`*.95508.com`、`static.95508.com`（`/mmg/images/ads`、`/mmg/ciop/sysabbr/cmep/images/(app)?popupads`、`/icppweb/images/modelMaterial/advertising/`） | `我的 → 设置 → 隐私设置 / 授权管理` |
| **兴业生活**（兴业银行，原名「好兴动」） | `bank_telemetry`（按需） | `*.cib.com.cn`、`*.cibfintech.com`、`*.95561.com`、`images.cib.com.cn`（`/commons/uploads/commons/` 与营销/活动/界面图共用，禁泛切） | `我的 → 设置 → 隐私设置 / 授权管理` |
| **全民生活**（民生银行） | `bank_telemetry`（按需） | `*.cmbc.com.cn`（3 源 `#@` 与 `@@`）、`*.95568.cn`、`rs.creditcard.cmbc.com.cn`（`/mmc/img/` 静态资源） | `我的 → 设置 → 隐私管理 → 个性化推荐设置` |
| **平安口袋银行**（平安银行） | `bank_telemetry`（默认关）：`adcdn.pingan.com`（4 源 `@@`）、`sdc.pingan.com`（3 源 `@@`） | `*.pingan.com`（3 源 `@@\|\|pingan.com^*/rrweb-record-`）、`*.pingan.com.cn`、`*.95511.com`、`iobs.pingan.com.cn`（平安共享对象存储桶） | `我的 → 设置 → 授权管理 → 个性化推荐设置` |
| **华彩生活**（华夏银行） | `bank_telemetry`（按需） | `*.hxb.com.cn`、`*.95577.cn`、`static.creditcard.hxb.com.cn`（`/app/apps/group1/M00/` 共享 FastDFS 集群） | `我的 → 设置 → 隐私设置 / 授权管理` |
| **浙商银行 / 渤海银行 / 恒丰银行**（全 12 家股份制银行收口） | `bank_telemetry`（按需） | `*.czbank.com`（浙商银行 `95527`，无独立信用卡 App）；`*.cbhb.com.cn`（渤海银行 `95541`，**原「渤海银行信用卡」App 已于 2024-12-30 停服迁入主端**）；`*.hfbank.com.cn`（恒丰银行 `95395`，原「恒享生活」等早先停服迁入主端） | 主行 App `我的 → 设置 → 隐私设置 / 个性化推荐` |
| **上海银行 / 上银美好生活** | `bank_telemetry`（按需） | `*.bosc.cn`（客服 `95594`；**「上银美好生活」将于 2026-11-30 24 时全面停服并下架，业务迁入「上海银行」App**） | `我的 → 设置 → 隐私设置 / 授权管理` |
| **北京银行 / 掌上京彩** | `bank_telemetry`（按需） | `*.bankofbeijing.com.cn`（客服 `95526`；北京银行直销银行已于 2025-11-12 停服迁入「京彩生活」，信用卡端「掌上京彩」仍在役；另北京农商行「凤凰信用卡」、江西银行「惠享精彩」等亦已迁入各主行 App） | `我的 → 设置 → 隐私设置 / 个性化推荐` |
| **云闪付**（中国银联） | 默认启用 `ads.cup.com.cn`；**`unionpay_optional`**（默认关）：`ads.95516.com`、`analytics.95516.com`、`analytics.95516.com.wscdns.com`（实证 REJECT 易触发重试风暴、切换版本报错与国补页异常，故默认关） | `*.95516.com`、`*.cup.com.cn`、`*.unionpay.com`、`*.unionpayintl.com`、`wallet.95516.com`（含 `/s/wl/icon/long` 与 `(:10533)?/s/wl/icon/large/1`，强 Pinning 禁 MITM）、`content.95516.com`、`switch.cup.com.cn`、`tysdk.95516.com`、`base.95516.com`、`account.95516.com`、`online.unionpay.com`、`marketing.unionpayintl.com` | `首页右上角 "+" → 切换关爱版`；`我的 → 设置 → 隐私设置 → 个性化推荐设置` + `消息设置`（关营销推送） |

---

## 五、全链路实用落地方案（安全可用，逐层叠加）

### 第 1 层：Loon 主配置协同与代理检测兜底

在主配置安装 `ads.plugin`（或 `ads-next.plugin`）+ `banks.plugin` 后，建议在个人主配置文件确认以下三处（不建议放进任何公共插件以免覆盖全局）：

1. **检查 Wi-Fi 代理残留**：`设置 → 无线局域网 → 当前 Wi-Fi 详情 → HTTP 代理` 保持 `关闭`（历史 `127.0.0.1` 抓包残留会导致部分银行直接弹窗拒服）。
2. **`[General]` DNS 与 `skip-proxy` 合并**（Loon 原生合并列表，**禁止使用 Surge 专用的 `%APPEND%`**）：

```ini
[General]
hijack-dns = *:53
domain-reject-mode = DNS
skip-proxy = 127.0.0.1, 192.168.0.0/16, 10.0.0.0/8, localhost, *.local, www.abchina.com.cn, msmp.abchina.com.cn, mobilepaas.abchina.com.cn, yunbusiness.ccb.com, login-service.mobile-bank.psbc.com, mobile-bank.psbc.com
```

3. **`[Rule]` 顶部按需显式 `DIRECT` 放行银行主族**（注：按规则匹配顺序，放在常规分流之前，仅作核心业务兜底；`banks.plugin` 中的 `adv.ccb.com`、`imageadv.ccb.com`、`mbads.paas.cmbchina.com` 等独立广告子域仍受插件 `[Host]`/`[Rule]` 先行约束）：

```ini
[Rule]
DOMAIN-SUFFIX,icbc.com.cn,DIRECT
DOMAIN-SUFFIX,ccb.com,DIRECT
DOMAIN-SUFFIX,ccb.com.cn,DIRECT
DOMAIN-SUFFIX,abchina.com.cn,DIRECT
DOMAIN-SUFFIX,boc.cn,DIRECT
DOMAIN-SUFFIX,bankcomm.com,DIRECT
DOMAIN-SUFFIX,bankcomm.cn,DIRECT
DOMAIN-SUFFIX,psbc.com,DIRECT
DOMAIN-SUFFIX,psbc.com.cn,DIRECT
DOMAIN-SUFFIX,95516.com,DIRECT
DOMAIN-SUFFIX,cup.com.cn,DIRECT
DOMAIN-SUFFIX,cmbchina.com,DIRECT
DOMAIN-SUFFIX,cmbimg.com,DIRECT
DOMAIN-SUFFIX,cmbimg.cn,DIRECT
DOMAIN-SUFFIX,spdb.com.cn,DIRECT
DOMAIN-SUFFIX,spdbccc.com.cn,DIRECT
DOMAIN-SUFFIX,ecitic.com,DIRECT
DOMAIN-SUFFIX,citicbank.com,DIRECT
DOMAIN-SUFFIX,cebbank.com,DIRECT
DOMAIN-SUFFIX,95508.com,DIRECT
DOMAIN-SUFFIX,cib.com.cn,DIRECT
DOMAIN-SUFFIX,cmbc.com.cn,DIRECT
DOMAIN-SUFFIX,pingan.com,DIRECT
DOMAIN-SUFFIX,hxb.com.cn,DIRECT
DOMAIN-SUFFIX,czbank.com,DIRECT
DOMAIN-SUFFIX,cbhb.com.cn,DIRECT
DOMAIN-SUFFIX,hfbank.com.cn,DIRECT
DOMAIN-SUFFIX,bosc.cn,DIRECT
DOMAIN-SUFFIX,bankofbeijing.com.cn,DIRECT
```

4. **极端代理风控无感方案**：
   - **纯 TUN 模式**：点击 [`loon://proxymode=tun`](loon://proxymode=tun) 切至纯 TUN（不注入系统 `NEProxySettings` HTTP 代理标头）；
   - **快捷指令自动化（针对强检 `NEVPNStatus` 的少数银行）**：在 iOS「快捷指令 → 个人自动化 → App」配置打开对应银行时「立即运行」[`loon://off`](loon://off)，关闭 App 时执行 [`loon://on`](loon://on)。

### 第 2 层：官方适老化版 + 弹窗/营销闭环（六大主力 App 对照）+ URL Scheme 诚实边界

对无法在网络层被强 Pinning 主网关切掉的第一方开屏、弹窗与营销推送，**最安全有效且零风控代价的做法是「官方适老化版本 + 端内隐私/消息全关 + 系统通知/跟踪限制」**，各主力端核验路径如下：

| 目标 App | 开屏网络拦截现状（本仓库） | 官方适老化减浮层路径 | 端内关闭弹窗 / 个性化 / 营销通知路径 |
|---|---|---|---|
| **云闪付** | 零证书 `banks` 启用 `ads.cup.com.cn`；`wallet.95516.com`（含 `/s/wl/icon/long`、`/large/1`）强固定且防切版报错不入 MITM | `首页右上角 "+" → 切换关爱版` | `我的 → 设置 → 隐私设置 → 个性化推荐设置`（关）+ `设置 → 消息设置`（关营销推送） |
| **中国农业银行** | `enjoy`/`midc.cdn-static.abchina.com.cn` 实证拦截致白屏放行；`firefly` 默认关在 `bank_telemetry`；代理风控须加 `skip-proxy` | `我的 → 设置 → 标准版 / 关怀版（大字版）` | ① `我的 → 设置 → 个性化推荐`（关）；② `首页 → 消息 → 右上角设置 → 优惠消息 / 服务通知`（关定向营销弹窗） |
| **掌上生活** | **`banks-mitm` 默认清理** `res.cc.cmbimg.com/AdPlatformPublic/`（视频 `reject_video`+图片 `reject_img`）、`s3gw.cmbimg.com(.cn)/mbappinitads/`、`pic1cdn.cmbchina.com/appinitads/`（装后清缓存）；`mlife`/`mbmodule-openapi/graphic` 强固定放行 | `我的 → 设置 → 大字版 / 关爱版`（或向`小招助理`发「关爱版怎么开」） | `我的 → 设置 → 隐私管理 → 个性化推荐设置`（关）+ `设置 → 消息通知 / 通用设置`（关营销推送） |
| **中国银行**（已合入原缤纷生活） | `banks` 启用 `ad.boc.cn`；`mbs.boc.cn/ubas-mgateway-static/images/advertType/` 与主交易共域强固定禁 MITM | 首页/`我的` 搜索切换 **「岁悦长情版」**（长辈版/关怀版） | `我的 → 右上角设置 → 消息设置`（关**营销优惠消息提醒开关** & **营销服务短信通知开关**）+ `个性化设置`（关） |
| **买单吧** | `banks` 启用 `ad.bankcomm.com`；`creditcardapp.bankcomm.com(.cn)`（`queryGuidePageAds.do`/`qryPopAds.do`）强固定同域混装禁 MITM | `我的 → 设置 → 切换版本 → 关怀版` | `我的 → 消费者权益保护 → 其他授权管理`（关）+ `设置 → 消息设置/通知管理`（关）；营销短信回 `TD` 或致电客服退订 |
| **浦发银行 / 浦大喜奔** | **`banks-mitm` 默认精确 `reject_dict(200)`** 拦截 `lban.spdb.com.cn/mspmk-web-component/(getAdvList|prefetchAdvList).ah`；`per`/`ebank.spdb.com.cn` 红线放行 | 浦发银行：`我的 → 设置 → 应用模式 / 版本切换 → 长辈版` | 浦发银行：`我的 → 设置 → 安全设置 → 其他管理选项 → 个性化推荐` + `消息/通知设置`；浦大喜奔：`用户保护中心 → 个性化推荐设置` |

> **系统级兜底（消除横幅与弹窗干扰）**：iOS 在 `设置 → 通知` 对各银行 App 仅保留交易动账或关闭「允许通知」，在 `设置 → 隐私与安全性 → 跟踪` 关「允许 App 请求跟踪」并限制「粘贴自其他 App」；Android 在「应用管理 → 通知管理」关掉「营销推广类通知」渠道。

- **其他大行与卡端适老化入口补充**：**工商银行**（`幸福生活版`）、**建设银行**（`左上角菜单 → 设置 → 切换到关怀模式`）、**交通银行**（`我的 → 设置 → 版本切换 → 关爱版`）、**邮储银行**（`我的 → 版本切换 / 设置 → 关怀版`）、**招商银行**（`长辈版`）。

- **iOS 快捷指令 URL Scheme 启动与真实冷启边界**（仅收录已核验应用自建 Scheme，已剔除 `wx`/`wb` 微信微博回调协议）：

| App | 已核验 URL Scheme | 实测表现与诚实局限 |
|---|---|---|
| **掌上生活** | `cmblife://` | 现代新版把开屏广告初始化绑定在根启动视图生命周期，**裸 `cmblife://` 无参冷启常不再跳过开屏**；主要对热恢复或带业务参数的深链（`cmblife://{funcName}?...`）有效 |
| **买单吧** | `mdb://` | 同理，现代新版下**裸 `mdb://` 无参冷启往往仍会展示开屏**，建议与「关怀版」及 iOS「限制动作数据」配合使用 |
| **招商银行 / 云闪付** | `cmbchina://` / `cmbmobilebank://`；云闪付 `upwallet://` | 热跳转/特定直达页方便，是否跳过冷启视客户端版本号而定 |
| **全国性信用卡 Scheme** | 浦大喜奔 `spdbccc://`、动卡空间 `citicbankdkkj://`、阳光惠生活 `yghsh://`、发现精彩 `credit://`、兴业 `cibmb://`、民生 `com.cmbc.cn.iphone://`、华夏 `com.hx.hxbank://`、平安口袋 `paesuperbank://` / `paebqw://` | 可用于快速唤起，部分新版仍会补展冷启欢迎页 |
| **六大行（参考 Scheme）** | 工行 `com.icbc.iphoneclient://`、工银e生活 `com.icbc.elife://`、农行 `bankabc://`、中行 `BOCMBCIphone://`、建行 `ccbmobilebank://`、建行生活 `cloudapp://`、交行 `bocom://`、邮储 `psbcmbank://` | 国有大行安全加固后，多数版本外链冷启仍按主启动流程呈现，不承诺跳过开屏 |

> **局限性如实说明**：iOS 通过快捷指令「打开 URL」启动第三方 App 时，系统顶部会短暂弹出「快捷指令」通知或灵动岛提示横幅，属 iOS 系统安全机制限制。

### 第 3 层：防「摇一摇 / 扭一扭」跳转（iOS 27.2+ & Android）

1. **iOS 27.2+（2026-10-27 上线，需中国大陆区 Apple ID）**：
   前往 `设置 → 隐私与安全 → 运动与健身 → 限制动作数据 → 编辑`，勾选 **掌上生活、买单吧、云闪付、六大行** 等 App，系统底层将不再向这些 App 分发加速度计与陀螺仪传感数据，从物理上彻底关闭开屏摇一摇触发跳转。
2. **Android 端注意事项（极重要）**：
   - 六大行与掌上生活（`com.cmbchina.cmblife`）/买单吧（`com.bankcomm.maidanba`）广泛集成梆梆安全等威胁感知框架，主动检索系统的 `AccessibilityService`（反电诈/反远程协助控屏检测）。**切勿对银行 App 长期裸挂无障碍跳广告**；`AIsouler/GKD_subscription` 也已于 2026 年初停止维护（改用社区规则按 `text*="跳过"` / `img_close` 匹配）。
   - **常见误区**：仅在 GKD 内把银行加入「免打扰（DND）名单」**不会**关闭系统的无障碍服务开关，银行侧依然能检测到已激活的无障碍服务列表并弹出安全警告甚至强制退登。
   - **可选方案**：通过 Tasker / MacroDroid 配合 Shizuku，在检测到银行包名进入前台时临时取消 GKD 无障碍授权、退出后恢复；或将银行与信用卡 App 安装进 **Island（Android Work Profile 工作资料）** 隔离，并在系统权限中禁用所有银行 App 的「身体传感器 / 设备动作与方向」权限。

### 第 4 层：个人设备谨慎实验边界（不进公开仓库默认规则）

如果你已在 Loon 安装并完全信任 CA 根证书、希望在 Loon 内直接落地无需手动维护规则的极限降噪，请优先使用仓库配套插件 [`banks-mitm.plugin`](../plugins/banks-mitm/banks-mitm.plugin) 并遵守以下边界：

1. **直接安装可选 MITM 伴随插件 [`banks-mitm.plugin`](../plugins/banks-mitm/banks-mitm.plugin)**：
   - 插件已默认声明以下 7 台非核心主机的 8 条精确路径复写（全带 7 条 `PROTOCOL,QUIC` 回退，并拆为 `cleanCmbSplash` / `cleanSpdbAds` / `cleanBankCdnAds` 三个独立 `[Argument]` 开关）：
     - `res.cc.cmbimg.com`（`/fsp/File/AdPlatformPublic/.*\.(?:mp4|mov)`）→ `reject_video(200)`（**优先命中视频开屏**）
     - `res.cc.cmbimg.com`（`/fsp/File/AdPlatformPublic/`）→ `reject_img(200)`（图片开屏兜底）
     - `s3gw.cmbimg.com` 与双生域 `s3gw.cmbimg.cn`（`/mbappinitads/`）→ `reject_img(200)`
     - `pic1cdn.cmbchina.com`（`/appinitads/`）→ `reject_img(200)`
     - `lban.spdb.com.cn`（`/mspmk-web-component/(getAdvList|prefetchAdvList).ah`）→ `reject_dict(200)`
     - `v.icbc.com.cn`（`/userfiles/(ADResources|Resources/WAP/advertisement)/`）→ `reject_img(200)`
     - `static.95508.com`（`/(mmg/images/ads|mmg/ciop/sysabbr/cmep/images/(app)?popupads|icppweb/images/modelMaterial/advertising)/`）→ `reject_img(200)`
   - 若同时启用了 `banks.plugin`，**请勿取消 `banks.plugin` 中 `# lban.spdb.com.cn = 127.0.0.1` 的注释**（DNS 黑洞会抢在 MITM 前断连）。启用后记得划掉掌上生活后台并清缓存以刷新 `preCacheAdvertiseSec` 本地预缓存。
   - **严禁**将 `mlife.cmbchina.com`、`az1mbasecc.bas.cmbchina.com`、`intellicc.bas.cmbchina.com`、`mbmodule-openapi.paas.cmbchina.com`、`creditcardapp.bankcomm.com`、`creditcardapp.bankcomm.cn`、`mobilepaas.abchina.com.cn` 等强 Pinning 核心网关写入 `[MITM]` `hostname`；若某家银行后续对上述 7 台静态 CDN 开启证书固定导致破图或报错，可在 Loon 关闭对应开关或停用 `banks-mitm.plugin`、仅保留零证书 `banks.plugin`。
2. **`banks.plugin` 默认关分组按需试开**：
   - 未启用 `banks-mitm.plugin` 且在 Loon 请求日志观察到 **浦发 / 浦大喜奔** 命中 `lban.spdb.com.cn`、**农行** 命中 `firefly.abchina.com.cn` 或需试探 `ads.95516.com` 时，在 `banks.plugin` 本地副本**一次仅取消一行注释**，观察 2–3 天确认无重试风暴与按钮卡死。
3. **明确禁止的高风险操作**：
   - **禁止**对银行 App 进行重打包脱壳/Hook 去证书校验；
   - **禁止**在未证实接口语义的银行主域名上使用伪造成功回包（`mock` / 伪报展示计费），既违反金融合规又极易触发账号风控锁定。

---

## 六、延伸阅读与真机核验清单

- 零证书底座插件说明与全量分组：[plugins/banks/README.md](../plugins/banks/README.md)
- 可选 MITM 静态图床与接口伴随插件：[plugins/banks-mitm/README.md](../plugins/banks-mitm/README.md)
- 银行 / 京东 / 淘宝联合配置实操：[banks-jd-taobao-rollout.md](banks-jd-taobao-rollout.md)
- 仓库能力天花板与方法论：[ad-eradication-review.md](ad-eradication-review.md)
- 重装/更新后分段真机检查清单：[device-checklist.md](device-checklist.md)
