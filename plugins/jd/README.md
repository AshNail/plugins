# 京东 · 去广告（自建广告交易层） v1.0.3

> 京东自建广告交易、京媒联盟与点击监测域 DNS 黑洞拦截；交易支付与风控绝对放行。零证书。

版本 **1.0.9** ｜ 功能基线 Loon **3.5.1(983)**+ （iOS/tvOS 口径；Mac 版是 0.x 独立一条线，插件头不声明门槛）｜ 零证书 · 零 MITM · 零脚本（纯 `[Host]`/`[Rule]`）

## 安装

[![一键导入 jd.plugin](https://img.shields.io/badge/Loon-导入%E4%BA%AC%E4%B8%9C%20%C2%B7%20%E5%8E%BB%E5%B9%BF%E5%91%8A%EF%BC%88%E8%87%AA%E5%BB%BA%E5%B9%BF%E5%91%8A%E4%BA%A4%E6%98%93%E5%B1%82%EF%BC%89%20v1.0.3-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fjd%2Fjd.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/jd/jd.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| 京东自建广告交易与点击监测（生效） | A | 启用 | dsp-x=京媒 SDK 广告请求（官方 FAQ 写明 /adx/sdk）、ads-union=京东联盟广告投放、ccc-x=广告点击监测、addata=广告数据、skdisplay=展示广告。五域均 ≥3 家上游清单收录，且语义由官方文档或公开广告点击链自证。 |
| 竞价/曝光/点击监测与语义待核实广告域（默认关） | B | 默认关闭 | x.jd.com 族（x/im-x/u-x/u.x/wn.x/bdsp.x）是广告竞价、DSP、曝光与 winnotice 监测；ads.union.jd.com / nfa.jd.com / c-nfa.jd.com 为前端广告位与联盟投放接口（25 源达 2~3 源 0 @@）；ad.3.cn 虽达 3 源但 adguard-cn/adrules/easylist-cn 存在 3 条 @@ 例外（/ads/mgets?$domain=jd.com），绝不默认生效；cm/cc.m/jrad/sgm-w 语义待真机逐域核实。全组默认关，先在日志确认域名真实出现、再逐条试开。 |
| 埋点/日志/推荐回流（默认关，隐私收益） | A | 默认关闭 | uranus/mercury/knicks/mllog/xlog/log/jcm/hermes/orbit/mars/anti-sdk-report/ex.m/jra/dsap/cltm/sgm-m/stat.m/firevent/du/atom-log.3.cn/log-h5.imdada.cn/clk-m.joybuy.com/h5log.joybuy.com=行为埋点、性能日志、秒送/国际端点击回流与推广事件上报，均默认关（不影响购物交易前提下提供隐私开关）。 |
| pre-DNS 双栈防旁路 | A | 启用 | 由生效 `[Host]` 精确派生 `DOMAIN-SUFFIX`/`DOMAIN` REJECT，在 DNS 解析前同步阻断 IPv4 与 IPv6/AAAA，防止单装插件时 AAAA 旁路。共 5 条。 |

## 怎么落实（分层落地与客户端协同）

### 1. Loon 分层组合与 HTTPDNS 硬编码 IP 旁路封堵

- 插件搭配：安装 `ads.plugin`（或 `ads-next.plugin`，二者互斥请只开其一）+ `jd.plugin`；并在主配置 `[General]` 加入 `hijack-dns = *:53` 与 `domain-reject-mode = DNS`（Loon 插件白名单不含这两键）。
- 保持零 MITM 边界：京东 13/14+ 对 `api.m.jd.com` 实施 `CertificatePinner` + `TrustManager` + `h5st` 强签名，非越狱/非 Root 环境不要强行对 `api.m.jd.com` 开 MITM，否则必现网络报错或风控。
- 封堵 HTTPDNS 硬编码直连：京东冷启可通过硬编码 IP 绕开域名黑洞直连 `dns.jd.com`。在启用上述主配置 DNS 加固后，按需在 `ads.plugin` 中取消默认注释的可选规则 `IP-CIDR,101.124.19.122/32,REJECT,no-resolve` 与 `IP-CIDR6,2402:db40:5100:1011::5/128,REJECT,no-resolve` 注释（同时保持 `dns.jd.com` 域名红线不黑洞，确保正常降级回退）。

### 2. 默认关闭组按日志按需试开

- `jd_ad_watchlist`（含 `ads.union.jd.com`、`nfa.jd.com`、`bdsp.x.jd.com` 及含 3 份 `@@` 例外的 `ad.3.cn`）与 `jd_telemetry`（`stat.m.jd.com`、`firevent.jd.com`、`atom-log.3.cn`、`log-h5.imdada.cn`、`clk-m.joybuy.com` 等）默认保持关闭。
- 试开方法：先在 Loon 请求日志核对具体命中域，再逐行取消注释；回归验收必测搜索、商品详情图（`360buyimg`/`img-x` 无白图）、下单结算（`cactus.jd.com` / `cactus.joybuy.com`）与物流跟踪（`wl.jd.com`）。

### 3. 客户端官方降噪 + 系统级掐断「摇一摇」开屏

- **京东 App 内设置**：`我的 → 右上角设置 → 通用设置 → 隐私设置 → 推荐管理 → 关闭个性化推荐`（同时在消息通知管理中关闭营销活动推送）。
- **iOS 27.2+ 彻底防摇一摇跳转（2026-10-27 上线，需中国大陆 Apple ID）**：`设置 → 隐私与安全 → 运动与健身 → 限制动作数据 → 编辑 → 勾选 京东`（从系统底层切断开屏期加速度计与陀螺仪权限，即使主接口下发静态开屏图也不再晃动误跳）。
- **Android 传感器禁止 + GKD 跳开屏**：系统设置搜索 `设备动作与方向` / `身体传感器`，将 **京东** 设为 `禁止`（或 `仅开屏时拒绝`）；开屏倒计时「跳过」按钮可由 GKD 订阅自动点击（电商 App 通常不因无障碍服务触发银行级拒服，若个人同时使用六大行仍建议按 `banks` 插件指引隔离无障碍）。

## 红线与天花板（如实）

- 红线（绝不进任何拦截组）：mapi.m.jd.com / api.m.jd.com（移动 API 网关）、janapi.jd.com（App 数据请求网关）、cactus.jd.com（h5st 风控签名 /request_algo，拦=下单/搜索签名失败）、passport.jd.com（登录）、jpushjd.m.jd.com（推送）、msg.m.jd.com（消息/登录凭证，wskey 抓取教程显示与 im-x 同链路）、chat1.jd.com（客服）、dns.jd.com / blackhole.m.jd.com / h5speed.m.jd.com / gia(s).jd.com（解析/监控/加速）、kepler.jd.com（开普勒 H5 容器）、dgstatic.jd.com（静态资源）、wl.jd.com（物流）、policy.jd.com（规则页）、cps.360buy.com（联盟 CPS 结算）、jrclick.jd.com（金融业务点击）、union.jd.com（联盟站）。
- 商品图 CDN 必须放行：360buyimg.com / img2.360buyimg.com / img-x.jd.com——AWAvenue-Ads-Rule issue #197 明确把 img2/img-x 标为商品详情页图片必需并加 allowlist；黑洞会白图。
- 证据：dsp-x.jd.com/adx/sdk 是京东官方《京媒 SDK FAQ》写明的正式广告请求地址；ccc-x.jd.com/dsp/tp?log=… 、x.jd.com/dsp/tp?log=… 与 im-x.jd.com/dsp/np?log=… 是公开可见的广告点击/落地链；mapi/janapi/img2/img-x 的红线结论见 AWAvenue issue #197 与 h5st 逆向公开分析。
- 能力天花板（如实）：京东 App 的开屏/信息流广告素材由主 API 下发并复用商品图 CDN，DNS 层无法按域剥离；可切断的是广告交易与点击/曝光监测域名、埋点日志域名，收益以抓包为准，不承诺「广告全消失」。
- 证书与 MITM：京东含支付/风控（h5st）且本插件未做抓包取证，按证书固定类 App 处理，不提供可选 MITM 增强层；需要路径级去广告请另用主配置，并自行承担风控风险。
- 第三方 ADN 未取证：京东 iOS 是否调用穿山甲/优量汇/快手等外部变现 SDK 没有可引用的官方 SDK 目录证据，本插件不挂 SDK 组；若真机抓包发现，直接开 ads.plugin 对应组即可。
- 频道情报核对（2026-10-30）：「广告必须死」公开频道（GitCube / Aa28413761）给出 m.360buyimg.com/mobilecms/s1125x2436_jfs* 开屏图 REJECT-IMG 方案，需 MITM 图片 CDN；京东属证书固定类 App、本插件红线零证书（lint APP_NO_ENHANCE_SLUGS 锁定），故拒收。频道清单中的 janapi/dns.jd.com 也命中本插件明文红线，同样拒收。确需路径级开屏去图只能在主配置自行 MITM，并自担 h5st 风控风险。
- 本插件 [Host]/[Rule] 全设备生效（Loon 无法按 App 限定）：同一广告/埋点域跨 App 共享黑洞，'按 App 插件'只是分组开关；与全局 ads 插件配合使用。
- 2026-11-18 25 源全网复核与 HTTPDNS 旁路勘察：① 纠偏原 triage_exclude「C 级单源不收」分类：25 源交叉显示 ads.union.jd.com（3 源，0 @@，京东联盟投放，与已生效 ads-union.jd.com 并列）、nfa.jd.com（3 源，0 @@，loadFa.action 前端广告组件加载与反作弊）、c-nfa.jd.com（2 源，0 @@）、bdsp.x.jd.com（2 源，0 @@，Bidding DSP 竞价投放，与 dsp-x.jd.com 同属 .x.jd.com 族）、u.x.jd.com（2 源，0 @@，与 u-x.jd.com 同族）实已达 B 级多源，迁入默认关 jd_ad_watchlist；stat.m.jd.com / firevent.jd.com / du.jd.com（均 2 源，0 @@）迁入默认关 jd_telemetry；② jzt.jd.com 实为京准通商家投放平台后台（2 源），按业务后台口径保留排除；blackhole-m.m.jd.com（1 源，与红线 blackhole.m 同族风控/日志）与 ddms.jd.com（1 源，分布式设备运维）按 C 级单源保留排除；③ 记录 HTTPDNS 接入点情报：dns.jd.com 常见 IPv4 节点为 101.124.19.122，因高版本京东 api.m.jd.com 强证书固定与 h5st（cactus.jd.com）强校验，dns.jd.com 仍列红线且维持零证书边界。
- 2026-11-18 第二轮 .3.cn 域族与双栈 HTTPDNS 深挖：① 将 .3.cn 盲区纳入覆盖审计后证实：atom-log.3.cn 获 4 源（adguard-dns/adrules/anti-ad/easyprivacy）0 @@ 收录，属行为日志上报域，迁入默认关 jd_telemetry；ad.3.cn 虽达 3 源但 adguard-cn/adrules/easylist-cn 三方均设 @@||ad.3.cn/ads/mgets?$domain=jd.com 放行旧模块/TV 展示，绝不默认生效，仅收于默认关 jd_ad_watchlist 并标注 3 条 @@ 风险；② 3.cn 整族（*.3.cn 不整域）、p.3.cn（商品实时定价接口）、c0.3.cn（商品库存接口）、jstatic.3.cn（AdRules 设 @@ 白名单）写入红线与台账排除，防误伤交易价库与页面静态资源；③ 补齐 dns.jd.com 双栈 HTTPDNS 接入点 101.124.19.122（IPv4）与 2402:db40:5100:1011::5（IPv6）情报，对应 IP-CIDR/IP-CIDR6 与 IP Rewrite 仅作为默认注释防旁路可选项录于 ads.plugin。
- 2026-11-18 第三轮关联子生态与协议边界深挖：① 纳入京东秒送/达达快送 imdada.cn 与京东国际 joybuy.com 25 源全网交叉验证：log-h5.imdada.cn（4 源 0 @@，京东秒送 H5 行为日志）、clk-m.joybuy.com（5 源 0 @@）、h5log.joybuy.com（5 源 0 @@）收入默认关 jd_telemetry；joybuy.com / imdada.cn 整族与 cactus.joybuy.com（5 源，h5st 风控签名镜像，同 cactus.jd.com 拦=下单失败）写入红线与台账排除；② 复核京东 13/14+ 客户端协议边界：api.m.jd.com 的 functionId=start / home_launchConfig / hotWords 虽在早期 QX/Loon 重写流行，但现代版本叠加 OkHttp CertificatePinner + 自定义 TrustManager 强证书固定与 HTTPDNS 直连，非 Root/Frida 环境开启 MITM 会直接报网络错误，故 jd.plugin 维持零证书边界；③ 补充实证为什么 3.cn 根域必列红线：AdRules/EasyPrivacy 仅拦截 ||3.cn/cesu/r? 路径级测速上报，3.cn 根域直接承载商品口令短链（https://3.cn/xxx），绝不做根域黑洞。
- 2026-11-18 第四轮真机落地与系统级摇一摇协同固化：在 plugins/jd/README.md 补齐从 Loon 主配置 hijack-dns/domain-reject-mode、ads/ads-next 可选双栈 HTTPDNS IP（101.124.19.122/32 与 2402:db40:5100:1011::5/128）启用时机、App 内隐私推荐关闭到 iOS 27.2+「限制动作数据」与 Android 传感器禁止 + GKD 跳开屏的完整执行路径。
- 2026-11-18 第五轮京东全资 1 号店子生态补全：扩展审计纳入 yhd.com 族并锁定 yhd.com（1 号店全族不整域黑洞）红线；将 anti-ad + yhosts 0 @@ 共识的 api.dsp.yhd.com 并入默认关 jd_ad_watchlist，click.yhd.com 与 tracker.yhd.com 并入默认关 jd_telemetry（同步合入 ads 默认关组）。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/jd.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 45 条，[Rule] 5 条。
