# 银行 App 聚合 · 遥测瘦身 v1.3.1

> 覆盖掌上生活/买单吧/浦发银行(含浦大喜奔)/云闪付/中国银行/农行掌银:中国大陆六大国有银行(工行/建行/农行/中行/交行/邮储)与招行/浦发/云闪付自建商业广告专域精准拦截(新增建行 imageadv.ccb.com, 剔除美商误配 ccbtechnology 与银联国际卡权益门户 unionpayintl);登录/支付/付款码/动账提醒零接触红线;内置 SSL Pinning 纯连接层零证书零 MITM。

版本 **1.3.7** ｜ 功能基线 Loon **3.5.1(983)**+ （iOS/tvOS 口径；Mac 版是 0.x 独立一条线，插件头不声明门槛）｜ 零证书 · 零 MITM · 零脚本（纯 `[Host]`/`[Rule]`）

## 安装

[![一键导入 banks.plugin](https://img.shields.io/badge/Loon-导入%E9%93%B6%E8%A1%8C%20App%20%E8%81%9A%E5%90%88%20%C2%B7%20%E9%81%A5%E6%B5%8B%E7%98%A6%E8%BA%AB%20v1.3.1-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fbanks%2Fbanks.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/banks/banks.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| 已证实的自建/自营广告端点 | A | 启用 | 六大国有银行(工行/建行/农行/中行/交行/邮储)+招行+云闪付自建广告投放与视觉营销域名。2026-11-18 补建行官网 Cookie 政策实证且 1hosts-lite/HaGeZi PRO 双收的 imageadv.ccb.com；剔除误配美商 MSP 的 marketing.ccbtechnology.com 与银联国际卡权益门户 marketing.unionpayintl.com；注：ad.icbc/boc/bankcomm/psbc 在 25 源开源黑名单 0 命中，按既有守卫保留零风险精确子域。 |
| 穿山甲企业内网解析域 | A | 启用 | *.alliance.com.corpqueue.net=穿山甲 SDK 内置企业内网主机名(私有 TLD 防劫持),外部网络只产生 DNS 探测噪音,黑洞零副作用;对装了穿山甲的 App 普遍有效。 |
| 云闪付 ads/analytics 主接口（默认关） | B | 默认关闭 | ads.95516.com + analytics.95516.com + analytics.95516.com.wscdns.com（网宿 CDN CNAME 别名）=云闪付开屏推广与分析；部分设备实证 REJECT 后触发重试风暴，默认关。 |
| 银行日志上报单源候选（默认关） | B | 默认关闭 | 银行日志/指标/灰度/APM 监测端点：log.cmbchina.com（招行日志，3 源）、metric-sz.ccd.cmbchina.com（招行卡中心深圳指标，HaGeZi PRO 收录）、sdc.pingan.com 与 adcdn.pingan.com（平安，存在多源 @@ 例外）、beacon.tingyun.com / wkrd.tingyun.com / api.networkbench.com / dc1.networkbench.com（基调听云 APM）及 oneupload.bonree.com（博睿 APM），均默认关。 |
| pre-DNS 双栈防旁路 | A | 启用 | 由生效 `[Host]` 精确派生 `DOMAIN-SUFFIX`/`DOMAIN` REJECT，在 DNS 解析前同步阻断 IPv4 与 IPv6/AAAA，防止单装插件时 AAAA 旁路。共 7 条。 |

## 怎么落实（分层落地与客户端协同）

### 1. Loon 主配置协同与代理检测防闪退

- 插件搭配：安装 `ads.plugin`（或 `ads-next.plugin`，二选一）+ `banks.plugin`；主配置 `[General]` 加入 `hijack-dns = *:53` 与 `domain-reject-mode = DNS`。本插件严格保持零 MITM（`enhance: null`），切勿手动将任何银行/银联域名写入 `[MITM]` `hostname`。
- 排查 Wi-Fi 代理残留：iOS 前往 `设置 → 无线局域网 → 当前 Wi-Fi 详情 → HTTP 代理`，确认处于 `关闭`（避免 Charles/抓包遗留的 `127.0.0.1` 触发银行检测）。
- 主配置 `skip-proxy` 直连豁免：若农行/建行/邮储/工行提示「检测到代理」，在主配置 `[General]` 的 `skip-proxy` 用英文逗号追加 `www.abchina.com.cn, msmp.abchina.com.cn, yunbusiness.ccb.com, login-service.mobile-bank.psbc.com, mobile-bank.psbc.com`（Loon 会原生合并列表，**禁写 Surge 的 `%APPEND%`**；本插件不擅自改写用户全局 `skip-proxy`）。
- 主配置 `[Rule]` 顶部按需显式直连：`DOMAIN-SUFFIX,icbc.com.cn,DIRECT`、`DOMAIN-SUFFIX,ccb.com,DIRECT`、`DOMAIN-SUFFIX,abchina.com.cn,DIRECT`、`DOMAIN-SUFFIX,boc.cn,DIRECT`、`DOMAIN-SUFFIX,bankcomm.com,DIRECT`、`DOMAIN-SUFFIX,psbc.com,DIRECT`、`DOMAIN-SUFFIX,95516.com,DIRECT`。
- 仍触发风控弹窗时的两种无感兜底：① 将 Loon 切换为纯 TUN（点击 `loon://proxymode=tun`，避免向系统注入 `NEProxySettings` HTTP 代理标记）；② 对强检 `NEVPNStatus` 的银行，在 iOS「快捷指令 → 个人自动化 → App」配置打开对应银行 App 时「立即运行」`loon://off`、关闭时自动执行 `loon://on`。（说明：`DOMAIN,msmp.abchina.com.cn,REJECT` 属社区风控偏方而非去广告，存在阻断农行安全监测的风险，本插件红线维持放行。）

### 2. 六大行 + 信用卡 + 云闪付 客户端内官方降噪开关（必做）

- **工商银行 / 工银e生活**：`我的 → 设置 → 个性化设置 → 个性化推荐`（关闭）。
- **建设银行 / 建行生活**：`我的 → 设置 → 隐私管理 → 个性化推荐管理`（关闭个性化内容推荐与个性化广告推荐）。
- **中国银行**（原「缤纷生活」App 已于 2026 年 6 月 30 日 24 时全面停服并迁入「中国银行」App）：`我的 → 设置 → 个性化设置`（或在隐私与安全内隐私管理入口关闭个性化推荐）。
- **农业银行 / 交通银行（含买单吧） / 邮储银行**：各行 `我的 → 设置 → 隐私设置 / 个性化推荐` 关闭（买单吧：`我的 → 消费者权益保护 → 其他授权管理`；邮储亦可致电 `95580` 转人工申请关闭个性化推荐）。
- **招商银行 / 掌上生活 / 浦大喜奔 / 云闪付**：招行 `我的 → 设置 → 安全中心 → 设备管理 → 允许个性化推荐` 关闭；掌上生活 `我的 → 设置 → 隐私管理 → 个性化推荐设置` 关闭；浦大喜奔 `我的 → 设置 → 用户保护中心 → 个性化推荐设置` 关闭；云闪付 `我的 → 设置 → 隐私设置 → 个性化推荐设置` 关闭。

### 3. Android 无障碍（GKD）风控与 iOS 传感器防摇一摇

- **Android 慎用无障碍跳开屏**：六大行普遍检索系统已启用的 `AccessibilityService`（反电诈与防远控校验）。仅在 GKD 内把银行加入免打扰（DND）名单**不会**移除系统无障碍服务列表，仍可能触发风险警告或强退；可行方案是在 MacroDroid/Tasker 配合 Shizuku 于银行前台时自动暂停无障碍服务，或将银行 App 放入 **Island（工作资料）** 沙箱隔离运行。
- **iOS 摇一摇防误触**：升级至 **iOS 27.2+**（2026-10-27 上线，需登录中国大陆 Apple ID）可在 `设置 → 隐私与安全 → 运动与健身 → 限制动作数据 → 编辑` 中勾选易乱跳 App，从系统底层切断传感器触发跳转。

### 4. 默认关闭组试开与回滚

- `unionpay_optional`（`ads.95516.com` / `analytics.95516.com.wscdns.com`）与 `bank_telemetry`（`metric-sz.ccd.cmbchina.com` 及 `TingYun` / `NetworkBench` / `Bonree` 遥测端）：仅当 Loon 请求日志确认对应域实际发起且有降噪需求时再逐行取消注释；出现按钮卡死、重试风暴或转账校验异常时立即恢复注释。

## 红线与天花板（如实）

- 域名映射纠错（防后续维护者凭品牌名加规则,均为 A 级官方验证）：掌上生活=招商信用卡,域在 cmbchina.com/cmbimg.com——cmbc.com.cn 是民生银行!;买单吧=交通信用卡,域在 bankcomm.com——spdbccc.com.cn 是浦发信用卡中心(浦大喜奔)!;adspdbl.com 是 Triplelift 系停放域、iabchina.cn 是 IAB 行业组织,都与浦发/农行无关。
- 红线（绝不出现）：各银行主域整族（*.cmbchina.com/*.bankcomm.com/*.spdb.com.cn/*.95528.cn/*.spdbccc.com.cn/*.95516.com/*.cup.com.cn/*.boc.cn/*.abchina.com 的 DOMAIN-SUFFIX 级操作）/ wap.cmpassport.com+e.189.cn+ms.zzx9.cn(一键登录) / getui+gepush(买单吧与中行的唯一自建推送,杀了=交易提醒消失) / wallet.95516.com+mobilepaybeta.95516.com(付款码/HCE) / cfca.com.cn(数字证书扫码付) / cmbc.maam.cc(招行行内嵌优量汇测试域,黑洞会触发招行侧异常)。
- App 内正确开关:个性化推荐/商业推送在各银行隐私设置页可关(云闪付隐私政策明列路径),网络层拦不到第一方运营位是物理限制,不是规则没生效。
- 网上流传的『银行广告域名清单』几乎全不可用——本插件有效规则 4 条,是四大公开列表(anti-AD 11 万域/AdGuard-CN/AW/bm7 Advertising)+官方 SDK 目录交叉验证后的真实上限。
- 第二轮全网取证复检(2026-10-28)：CT 枚举六大行域空间无独立 ads/stat/log 前缀投放子域;明确禁加——hotpatch.cup.com.cn(云闪付热修复通道,与 ads.95516.com 同 IP 段群)/market.cmbchina.com(招行连隐私政策都托管在此,典型运营混装)/mbs.boc.cn(中行主接口,开屏广告是其 /advertType/ 路径,MITM 不可行则 DNS 无解)/pic1cdn.cmbchina.com(业务图混装);track.bankcomm.com 仅存在性证据(C 级,隐私政策未列广告 SDK),不采。
- 2026-11-18 深度取证纠偏与六大行主域加固：① 误杀与误配剔除——marketing.ccbtechnology.com 实为美国威斯康星州 IT 服务商 CCB Technology（ccbtechnology.com），因主机名含 ccb 子串被上游黑名单误收入并错标为建行域，与中国建设银行无关；marketing.unionpayintl.com（/offer-promote/）为银联国际官方跨境卡权益/U·Plan 优惠报名门户（AdRules 与 EasyPrivacy 双向设 @@ 一方白名单），同 jf365.boc.cn 属用户权益业务域，整域屏蔽必伤优惠报名。② 新增实证广告子域与六大行全族红线——imageadv.ccb.com 由建行官网 Cookie 政策明确与 adv.ccb.com 并列承载广告/定向视觉资源，且获 1hosts-lite + HaGeZi PRO 双源 0 @@ 收录；六大行主域红线补全：*.icbc.com.cn / *.ccb.com / *.ccb.com.cn / *.abchina.com.cn / *.psbc.com / *.unionpayintl.com / *.pingan.com 绝不做整族拦截；精确业务/安全/权益红线主机：v.icbc.com.cn（工行官网共享多媒体主机，仅 /userfiles/ADResources/ 为广告目录，零 MITM 下不可切）、cdn2.jf365.boc.cn / jf365.boc.cn（中行积分 365 商城及 CDN）、ad.abchina.com（4 家清单 @@ 白名单放行）、msmp.abchina.com.cn（农行移动安全监控与代理风控通道，飞客/NodeSeek 实证开代理触发弹窗强退，属安全风控域非商业广告）、tysdk.95516.com（银联统一 SDK 接口，1hosts-lite 单源，误拦可能影响嵌入式支付校验）、oisc.icbc.com.cn（仅 1hosts-lite 单源，工行内部 APM/运维监测，不默认拦截）。③ 可选遥测与 CNAME 补齐：metric-sz.ccd.cmbchina.com（招行卡中心深圳指标遥测，HaGeZi PRO 收录）并入默认关 bank_telemetry；analytics.95516.com.wscdns.com（analytics.95516.com 网宿 CDN CNAME 别名，adblockfilters + HaGeZi PRO 双源）并入默认关 unionpay_optional。④ 诚实边界与原守卫说明：ad.icbc.com.cn / ad.boc.cn / ad.bankcomm.com / ad.psbc.com 在 25 源开源黑名单中均 0 命中（六大行手机银行不接入穿山甲/优量汇等外部广告联盟，开屏/弹窗均由证书固定或国密 SM2/SM3/SM4 主接口直接下发，网络零 MITM 存在物理天花板），随既有 lint 守卫保留精确低风险子域并纠偏原 95528.cn（浦发银行，非农行）注释笔误。
- 2026-11-18 第二轮附属生活/信用卡端复核与伪建行名录排除：① 核查六大行附属生活/信用卡 App（工银e生活 / 建行生活 / 缤纷生活 / 买单吧 / 邮储信用卡）合规披露：主流程同样不接入穿山甲/优量汇/快手商业广告联盟，维持零证书连接层边界；② 云闪付强证书固定核心业务域补入红线：content.95516.com（银联活动/优惠券/卡面内容分发域，整域黑洞会导致优惠活动与卡面加载失败）、switch.cup.com.cn（银联支付路由调度后端，拦则影响交易调度）；③ 25 源全网名称模糊误配排查排除：ss.genesisccb.com 实为美国得州特种化工企业 Genesis Custom Chemical Blending（genesisccb.com），smsccb.com 与 tnccb.com 为垃圾/钓鱼威胁清单域，三者均非中国建设银行域。
- 2026-11-18 第三轮六大行 SDK 隐私披露与生活端实证误杀排查：核查工商银行/建设银行/农业银行/中国银行/交通银行（买单吧）/邮储银行《第三方SDK目录》（梆梆加固、同盾/顶象风控、高德/百度地图、个推及手机厂商 Push 均非商业广告联盟）；补入 blackmatrix7 AdvertisingLite issue 实证的工银e生活红线域 pv.elife.icbc.com.cn（/OFSTPV/utm.gif 上报端点，拦截会引发工银e生活「爱购8.8」及首页模块加载报错或异常，永不拦截）。
- 2026-11-18 第四轮 3D-Secure 支付网关 / @@ 白名单与听云博睿 APM 收敛：① 扫描 25 源全部 @@ 例外并结合 UnionPay_remove_ads_with_ssl_unpinning.js 补入 4 项红线：xykpay.3d2.icbc.com.cn（工行信用卡 3D-Secure /acs-auth-web/js/fingerprint2.min.js 支付验证，2 源设 @@ 白名单）、trip.cmbchina.com（招行商旅门户，3 源设 @@ 白名单）、base.95516.com 与 account.95516.com（云闪付强 SSL Pinning 核心界面接口，非去校验修改版启用 MITM 即断）；② 针对六大行官方《第三方SDK目录》实名披露的基调听云/博睿 APM 上报端，将 beacon.tingyun.com（4 源 0 @@）、wkrd.tingyun.com（3 源 0 @@）、api.networkbench.com / dc1.networkbench.com 及 oneupload.bonree.com 收录至默认关 bank_telemetry（同步于 ads 默认关 analytics 收 =networkbench.com），不误触 tingyun.com 门户且避免同步依赖引发偶发加载卡顿。
- 2026-11-18 第五轮真机落地与代理检测红线核实：① 核查中国银行公告：原信用卡「缤纷生活」App 已于 2026 年 6 月 30 日 24 时全面停服，服务整合迁入「中国银行」App（积分 365 域 jf365.boc.cn 等仍维持红线）；② 按社区 skip-proxy 实证与支付主链路补入 5 项红线永不拦截：www.abchina.com.cn（农行主域与 skip-proxy 核心）、yunbusiness.ccb.com（建行生活与 skip-proxy 核心）、login-service.mobile-bank.psbc.com 与 mobile-bank.psbc.com（邮储手机银行登录与 skip-proxy 核心）、wallet.95516.com（云闪付支付与卡包核心链路）；③ 完整 Loon 主配置 skip-proxy（原生自动合并、禁写 %APPEND%）、纯 TUN / 快捷指令 loon://off 与 loon://on 自动化、六大行+信用卡+云闪付端内隐私关闭路径、Android 无障碍/GKD 反诈风控规避及 iOS 27.2+ 限制动作数据方案生成至 plugins/banks/README.md。
- 2026-11-18 第六轮子门户反隐藏规则核查与官方《第三方SDK目录》合规交叉复检：① 逐行复核 25 源原始规则排查银行扩张域：剔除并锁定 buy.ccb.com（建行善融商务，25 源仅在 adguard-cn/adrules/easylist-cn 含 #@ 样式反隐藏例外）与 m.icbc.com.cn（工行手机网页版银行入口，仅 adguard-mobile 含首页 CSS 元素选择器）进红线与台账排除，防止误作 DNS 广告黑洞；② 核查六大行官网《第三方SDK目录》及开源 UnionPay_remove_ads 证据：各大行核心交易端均受监管禁止接入第三方商业广告联盟 SDK，推送转向手机厂商系统通道并辅以个推/极光，APM 仅含经安全审计的基调听云/博睿/Bugly 等，而云闪付 UnionPay_remove_ads 所涉 wallet.95516.com/s/wl/icon/long 需去 SSL Pinning 方能介入、维持红线天花板；全链路汇总部署指引同步落盘至 docs/banks-jd-taobao-rollout.md。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/banks.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 19 条，[Rule] 9 条。
