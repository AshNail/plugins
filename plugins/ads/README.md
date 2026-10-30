# 广告平台拦截器 · All-in-One（单插件）

> **定位**：一个 `ads.plugin` 同时处理 **DNS 广告拦截 + 广告子域通配 + HTTPDNS 防绕过 + 公共 DoH/DoT 防泄漏**。核心路径零证书、零 MITM、零脚本，HTTP/3 同样走 DNS 拦截。
>
> **和旧版的关系**：旧的 `ads-httpdns.plugin`、`ads-measurement.plugin`、`ads-strict.plugin` 已合并/移除。现在只需要安装这一个文件；不要再同时安装旧文件，否则 Host/Rule 会重复。
>
> **和其他去广告插件的关系**：soda/douyin 等 App 专用插件负责共享域、响应体和 UI；本插件负责广告平台域、HTTPDNS 与公共 DoH 的统一底层拦截。

---

## 和 soda / douyin 的冲突（先读）

`soda.plugin` / `douyin.plugin` 默认 `rewardSafe=true`，靠穿山甲/优量汇/快手联盟的激励广告领奖励。`ads.plugin` 会在 DNS 阶段把这些广告域打到 `127.0.0.1`，**激励广告加载不出来，奖励任务会失败**。

- **刷奖励**：不要装 `ads.plugin`，或临时在 Loon 里禁用；soda/douyin 保持 `rewardSafe=true`。
- **纯去广告**：装 `ads.plugin`；soda/douyin 里把 `rewardSafe` 设为 `false`，它们的 `blockAdDomains` 也就冗余了。
- **两个都装时**：`[Host]` 先生效，soda/douyin 的广告域名脚本收不到请求；它们的 `[MITM]` 仍只解密自己的 API 域，不会额外放大风险。

---

## 安装

[![一键导入 ads.plugin](https://img.shields.io/badge/Loon-导入广告拦截器-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fads%2Fads.plugin)

直链地址（单文件；`[Script]` 相对路径脚本以插件 URL 为基准同目录解析）：

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/ads/ads.plugin
```

Loon 导入链接：

```text
loon://import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fads%2Fads.plugin
```

要求 **Loon 3.5.2(996)+**（当前 App Store 正式版）。插件头 `#!loon_version=3.5.2(996)` 与正式版对齐，**所有真实用户都能直接导入**——不再用 TestFlight 的 3.5.3 卡门槛。核心 `[Host]` 黑洞、`[Rule]` HTTPDNS/端口、`[General]` DoH/DoT 在 3.5.2 完整生效。`DOMAIN-WILDCARD` 通配/家族层（Loon 3.5.3(1008)+，目前仅 TestFlight）默认以注释行收录：App Store 用户保持注释即可（对应的具体广告/DoH 域已由 `[Host]` 逐条覆盖），装了 3.5.3+ 的用户逐行去掉行首 `# ` 即启用整族拦截。安装后建议重连一次 Loon，让 DNS/DoH 配置生效。

### 真机验证清单

| 目标 | 操作 | 通过标准 |
|---|---|---|
| 核心广告拦截 | 找一个确认使用穿山甲/优量汇/快手/AdMob 广告的 App | 禁用插件后先确认广告会展示，再启用后广告消失 |
| HTTPDNS 防绕过 | 抓包或在 Loon 日志里筛 `httpdns`、`httpsdns`、`853` | 几乎无明文 HTTPDNS/DoT 请求；广告域名仍被拦 |
| 广告子域通配（仅 3.5.3+ 取消注释后） | 在 Loon 日志/DNS 检查里访问 `<广告左标签>.任意域名`（如 `ads.example.com`） | 走 127.0.0.1 或 DNS 拒绝；`example.com`、`adsl.example.com` 正常；3.5.2 未取消注释时本项不适用 |
| 公共 DoH/DNS 防泄漏 | 对比插件启用/禁用，看是否还连 Google/Cloudflare/NextDNS 等公共 DoH | 启用时不连被拦的公共 DoH；`doh.dns.apple.com` 正常 |
| 误伤排查 | 某个 App 登录/正常功能异常 | 先禁用插件复现；再按“风险与误伤”表删对应行 |

> **第一优先**：刷奖励前临时禁用本插件，避免激励广告被拦导致奖励失败。

### 从旧版迁移

1. 在 Loon 里删除旧的 `ads-httpdns.plugin`、`ads-measurement.plugin`、`ads-strict.plugin`；仓库里的旧文件也已删除。
2. 重新导入新的 `ads.plugin`。
3. 新版默认只启用海外公共 DoH；阿里云、DNSPod、360 这 9 条国内入口改为默认注释，先看下面的“DNS 防泄漏”与“风险”再决定是否开启。

---

## 一个插件里有什么

| 模块 | 当前内容 | 是否默认生效 |
|---|---|---:|
| `[Host]` 核心广告组 | 14 组、1347 条展开规则：穿山甲、优量汇、快手联盟、百度、阿里妈妈、中国联盟/监测、Google、Meta FAN、TikTok、手机厂商、全球 SDK、交易/SSP/DSP、广告效果监测、零售/CTV/音频、弹窗 | 是 |
| `[Host]` HTTPDNS 组 | 71 条：阿里云、腾讯、百度、字节、快手、B站、网易云音乐、美团、华为、小米、OPPO、vivo、荣耀、YY、讯飞、微博、微信、爱奇艺等 | 是 |
| `[Host]` 公共 DoH 组 | 48 条：Google、Cloudflare/Quad9 各变体、NextDNS、OpenDNS、AdGuard 新旧域、CleanBrowsing、Mullvad、ControlD、Brave、dns.sb、Applied Privacy、LibreDNS、FFMUC、Digitale Gesellschaft、Hostux、SecuredNS、Crypto.sx、DNSForge、Kommespaeter 等海外厂商 | 是（见风险表） |
| `[Rule]` | 13 条：`httpdns`/`httpsdns` 关键词 (REJECT-DROP)、UA、IP 字面量 URL-REGEX、埋点上报特征 (REJECT-DICT)、853 端口 | 是 |
| `[Rule]` DOMAIN-WILDCARD 通配/家族层 | 41 条 glob（30 广告左标签 + 11 数字分片家族：`ads.*`、`adserver.*`、`ads[0-9]-normal*.zijieapi.com` 等）：按广告专用左标签拦截任意层级子域，弥补 `[Host]` 无法表达动态子域；规则行不带参数 | **否**（需 Loon 3.5.3(1008)+，当前仅 TF；默认注释，`[Host]` 已逐条覆盖这批域，取消注释只是把同族动态子域也一并拒绝） |
| `[General]` | 3 条：公共 DNS + IP 形式 DoH + IP 形式 DoH3 (HTTP/3) | 是 |
| `[Host]` 默认注释组 | 4 组、131 条展开规则，默认整组注释（归因、统计、国内公共 DoH，以及命中按 App 插件红线的候选） | **否** |
| `[Rule]` 可选组 | 44 条默认注释：27 条 HTTPDNS 网关 IP（`IP-CIDR/IP-CIDR6`，阿里内地+海外、腾讯、百度网关）+ 16 条公共 DNS 解析器 IP 直连阻断（Google/Cloudflare/Quad9/AdGuard 的 IPv4+IPv6，封 DNS 旁路）+ `PROTOCOL,STUN,REJECT`（防 WebRTC 泄露；会断语音/视频通话） | **否** |
| `[IP Rewrite]` 可选组 | 16 条单 IPv4 HTTPDNS 网关接入点（Loon Build 1007+ 插件专属，TUN 阶段最快拦截），默认注释 | **否** |
| `[Rewrite]` / `[MITM]` / `[Script]` | 无 | 无证书、无 MITM、无脚本 |

合计：**20 组、1466 条生效 Host（exact 891 / wildcard 575）、131 条默认注释 Host、13 条生效 Rule（HTTPDNS/端口/UA）、41 条默认注释 DOMAIN-WILDCARD glob（30 通配 + 11 家族，需 3.5.3+）、44 条默认注释可选 Rule（HTTPDNS 网关 IP + 公共 DNS 直连 IP + STUN）、16 条默认注释 IP Rewrite**。

### 默认注释组（可选开启）

- 国内公共 DoH 组：`dns.alidns.com`、`doh.aliyun.com`、`dot.alidns.com`（阿里云）、`doh.pub`、`dns.pub`、`dot.pub`、`sm2.doh.pub`（DNSPod）、`doh.360.cn`、`dot.360.cn`（360），共 9 条。**不能默认拦**：国内 Loon 主配置常用域名形式 `doh-server` / `doq-server`，`[Host]` 会把 Loon 自己的加密 DNS 一起打到 `127.0.0.1`（真机证据见下）。开启前把主配置 dns/doh/doq 全改成 IP 形式。
- 归因组：AppsFlyer、Adjust、Kochava、Singular、Tenjin、AppMetrica、mParticle、Amplitude、Flurry。
- 统计组：Google Analytics/Firebase、友盟、CNZZ、TalkingData、GrowingIO、神策、百度统计、Yandex、Pinterest、LinkedIn、Yahoo 等。
- 红线冲突候选组：`dns.jd.com`（京东自建 HTTPDNS）与 `=union.jd.com`（京东联盟 CPS 站，展开含 `*.union.jd.com`）。这两条不进默认生效组的原因是 `src/apps/jd.json` 的「红线（绝不进任何拦截组）」原文逐字写着它们，而 `tools/build-ads.py` 会拒绝任何默认生效条目命中任一 App 声明的红线（判定见 `tools/redlines.py`）。两面理由都留着：拦 `dns.jd.com` 可防京东绕过 Loon 直接解析广告域（成熟清单的常规做法），但没有真机取证证明它无回退时会断解析；拦 `union.jd.com` 去不掉 App 内广告，只会断联盟取链后台。

默认注释的原因：安装归因、渠道 ROI、Firebase/GA 报表、友盟/TalkingData 统计会失效。需要时二选一：

- 在 `src/ads/domains.json` 把对应组的 `"disabled": true` 改成 `false`，再运行 `python3 tools/build-ads.py`；
- 或直接在本地的 `ads.plugin` 里取消这些行行首的 `# `（下次构建会覆盖，长期维护建议改 JSON）。

`branch.io`、`jpush.cn`、`getui.com` 是深度链接/推送基础设施，明确不拦。

---

## 工作机制

```text
App 请求 ad.example.com
        │
        ▼
Loon DNS（[Host] ad.example.com = 127.0.0.1）
        │
        ▼
连接 127.0.0.1:443 → 本机没有监听 → 快速失败
```

- **DNS 阶段生效**：不需要证书、不需要 MITM，TLS 握手都不会发生。
- **HTTP/3 也覆盖**：QUIC 连接同样拿到 `127.0.0.1`；不会像 MITM 域名脚本那样漏掉 QUIC。
- **共享主域不整域封**：`qq.com`、`baidu.com`、`google.com`、`facebook.com`、`snssdk.com`、`zijieapi.com`、`kuaishou.com`、`unity3d.com`、`amazon.com` 等只列广告专用子域。保护名单在 `src/ads/protected-roots.json`，build 和 lint 都会强制检查。
- **单插件、静态配置**：`[Host]`、`[Rule]`、`[General]` 不支持 `${argument}` 条件绑定；不要期待像 soda 那样在 Loon 界面里用开关逐组控制。需要关闭某组时，删对应行或改 JSON 后重新构建。

### `=` 规则简写

`src/ads/domains.json` 里：

```json
"=doubleclick.net"
```

生成：

```ini
doubleclick.net = 127.0.0.1
*.doubleclick.net = 127.0.0.1
```

Loon 的 `*.example.com` 不保证覆盖 apex，所以广告专域统一写两行；共享域只允许精确广告子域。

### DOMAIN-WILDCARD 通配层（默认注释，3.5.3+ 取消注释启用）

`[Host]` 只能枚举已知域名，广告 SDK 常用的随机/多级子域（`ads-xxx.example.com`、`adserver.foo.bar`）枚举不到。插件在 `[Rule]` 里收录 30 条通配 + 11 条数字分片家族 glob。该规则类型仅 Loon 3.5.3(1008)+ 提供（当前只在 TestFlight），App Store 正式版 3.5.2(996) 遇到未知规则类型的行为官方未文档化，所以两层**默认以 `# ` 注释收录**——3.5.2 用户保持注释、其余全部层照常生效；3.5.3+ 用户逐行去掉行首 `# ` 即启用：

```ini
# DOMAIN-WILDCARD,ads.*,REJECT
# DOMAIN-WILDCARD,adserver.*,REJECT
```

| glob | 命中示例 | 刻意不命中 |
|---|---|---|
| `ads.*` | `ads.example.com`、`ads.a.b.example.net` | `example.com`、`adsl.example.com` |
| `ads-*` | `ads-tracker.example.com` | `ads.example.com`（无连字符） |
| `adserver.*` / `adserver-*` | `adserver.example.com`、`adserver-eu.example.net` | `example.com` |
| `adserve.*` / `adserv.*` / `adserv-*` | `adserve.example.com`、`adserv-fra1.example.com` | `advertisement.example.com` |
| `adserving.*` / `adserving-*` / `adservice.*` / `adservices.*` / `adsystem.*` | 对应前缀的任意子域 | 普通业务域 |
| `advertising.*` / `advertising-*` | `advertising.example.com`、`advertising-api.example.com` | `advertise.example.com`（业务站） |
| `advert.*` / `adverts.*` / `advertiser.*` | `advert.example.com`、`advertiser.example.net` | `advertisement.example.com` |
| `adtech.*` / `adtech-*` / `adclick.*` | 对应前缀的任意子域 | 普通业务域 |
| `adnetwork.*` / `adnetwork-*` / `adx.*` / `adx-*` / `adtrack.*` / `adtrack-*` | 对应前缀的任意子域 | 普通业务域 |
| `adunit.*` / `bannerads.*` / `sponsorads.*` / `ad-exchange.*` | 对应前缀的任意子域 | `banner.example.com`、`adunit2.example.com` |

- Loon 的 `*` **跨点匹配**：`ads.*` 同时覆盖 `ads.a.com` 与 `ads.a.b.com`，它不是 `*.ads.com`。
- 每条 glob 在 build 与 lint 阶段都用 `protected-roots.json` 校验，确保不命中保护名单里的共享主域；lint 还用正/负样本锁死语义，禁止改成 `*`、`*.com`、`ads*` 这类宽泛模式。
- 规则行**不带参数**。Loon 的规则参数只有 `no-resolve` 一个（IP 类用）；`pre-matching` / `extended-matching` 是 **Surge** 的写法，Loon 里没有——「DNS 阶段拒绝」由主配置 `domain-reject-mode = DNS` 控制（插件无法声明），「SNI 辅助匹配」Loon 默认开启。想要 DNS 阶段就拒绝，把那一行加进主配置（见“主配置加固”）。
- 误伤时删除对应 `DOMAIN-WILDCARD` 行，或从 `src/ads/domains.json` 的 `domain_wildcards` 删除后重新 build；只影响这一条 glob，不影响 `[Host]`。

#### 数字分片家族层（11 条，第二轮）

左标签锚定的 glob 覆盖不到 `ads1/ads3/ads5` 这类**编号分片**。Loon 3.5.3(1008) 起 `DOMAIN-WILDCARD` 还支持第三类通配符 `[...]`（官方示例 `node[0-9].example.com`），于是可以把「同一家族、只换了数字」的主机折叠成一条：

```ini
DOMAIN-WILDCARD,ads[0-9]-normal*.zijieapi.com,REJECT
DOMAIN-WILDCARD,p[0-9]-ad-sign.byteimg.com,REJECT
```

| 家族 glob | 覆盖的已枚举主机 | 理由 |
|---|---|---|
| `ads[0-9]-normal*.zijieapi.com` | `ads3/ads5 × normal、-hl、-lf、-lq、-xh`（10 台） | 穿山甲按地区/线路下发分片，只列见过的那台必漏 |
| `p[0-9]-ad-sign.byteimg.com` | `p3/p6/p9` | 广告素材签名，编号分片 |
| `v[0-9]-ad.video.yximgs.com` | `v1/v2/v3` | 快手广告视频 |
| `pangolin-sdk-toutiao[0-9].com` | `toutiao1..5` | 穿山甲 SDK 接入点 |
| `ads[0-9].msn.com` / `ads[0-9]-adnow.com` | `ads1/2`、`ads1/3/5` | 海外广告网 |
| `ads-splash-i[0-9].xhscdn.com` / `ads-splash-v[0-9].xhscdn.com` | `i1/i2`、`v1/v2` | 小红书开屏 |
| `pg-ad-b[0-9].ws.126.net` | `b1/b2` | 网易广告位 |
| `dns[0-9]*.quad9.net` / `dns[0-9]*.nextdns.io` | `dns9..12`、`dns1..3` | 公共 DoH 入口，防泄漏 |

- **只放开 `[0-9]`**：`[a-z]` 或 `[!0-9]` 会把匹配扩散到别的品牌主机，让「保护名单不可被通配命中」这条保证失效。build 里除 `[0-9]` 以外的字符类直接报错。
- **每条家族 glob 必须「赢得位置」**：build 会数它覆盖了多少台 `[Host]` 里**已经存在**的主机，少于 2 台就拒绝构建——这挡住了「凭想象造家族」。
- **语义边界同样是锁死的**：lint 用 `ADS_FAMILY_MUST_MISS` 验证 `ads[0-9]-normal*.zijieapi.com` 不会命中 `ads-normal-hl`（少一位）、`ads10-normal-hl`（两位）、`adsxx-normal-hl`（非数字），也不会命中 `…zijieapi.com.evil.example`（后缀伪装）。
- 审计工具把这一层计入覆盖率（`glob 41`），并继续检查保护名单违规（当前 0 条）。

---

## 覆盖范围

### 核心广告组（14 组 / 1347 条展开）

| 组 | 代表 |
|---|---|
| 穿山甲 / Pangle | `ad.zijieapi.com`、`pangolin.snssdk.com`、`*.pangle.io`、`*.pglstatp-toutiao.com` |
| 腾讯广告 / 优量汇 | `*.gdt.qq.com`、`*.gdtimg.com`、`*.e.qq.com`、`*.l.qq.com` |
| 快手联盟 | `*.adkwai.com`、`*.adukwai.com`、`*.open.kwaizt.com`、`*.e.kuaishou.com` |
| 百度 / 百青藤 | `*.mobads.baidu.com`、`*.pos.baidu.com`、`cpro.baidustatic.com` |
| 阿里妈妈 / TanX | `*.tanx.com`、`*.alimama.com`、`*.mmstat.com` |
| 中国联盟/媒体/监测 | `*.miaozhen.com`、`*.admaster.com.cn`、`*.mediav.com`、`*.adsame.com`、`union.360.cn`、`ads.sohu.com` |
| Google Ads | `*.doubleclick.net`、`*.googlesyndication.com`、`*.admob.com`、`imasdk.googleapis.com` |
| Meta / FAN | `*.an.facebook.com`、`*.b-graph.facebook.com`、`pixel.facebook.com` |
| TikTok Ads | `ads.tiktok.com`、`business-api.tiktok.com`、`analytics.tiktok.com` |
| 全球移动广告 SDK | AppLovin、Unity Ads、ironSource、Mintegral、Vungle、AdColony、Chartboost、InMobi、Tapjoy、Smaato、PubNative、Moloco、Liftoff、Start.io、Digital Turbine、Fyber、adjoe、BIGO Ads |
| 广告交易/SSP/DSP/验证 | Xandr、Trade Desk、Criteo、Taboola、Outbrain、PubMatic、Magnite、OpenX、Index Exchange、Amazon Ads、IAS、DoubleVerify、Moat、Pixalate 等 |
| 零售/CTV/音频/社交 | eBay、Uber、Walmart Connect、Roundel、Kroger、Instacart、Samsung Ads、LG Ads、Roku、Vistar、Place Exchange、Broadsign、Triton、AdsWizz、Spotify、SoundCloud、Snap、Pinterest、Reddit、LinkedIn、X、Yahoo、Microsoft、Apple、Yandex |
| 手机厂商广告 SDK | 小米、华为、OPPO/HeyTap、vivo（Android；iOS 不受影响） |
| 弹窗/Popunder | PropellerAds、PopAds、PopCash、ExoClick、JuicyAds、TrafficJunky、Adsterra、HilltopAds、Clickadu、SpyLog 等 |

### HTTPDNS / 公共 DoH（119 条展开）

- HTTPDNS/私有 DoH：`*.httpdns.aliyuncs.com`（含阿里《启动接入点》`resolvers-*` 域名兜底）、`httpdns.aliyuncs.com`、`httpdns.qq.com`、`httpdns.baidu.com`、`httpdns.volcengineapi.com`、`httpdns.pro`、`dns.weixin.qq.com` 等 71 条。`dns.jd.com` 与 `resolver.msg.xiaomi.net` 不在这里——它们分别是 `src/apps/jd.json`（京东自建 HTTPDNS）与 `src/apps/mijia.json`（MIUI 推送/消息解析）声明的红线域，见上面「默认注释组（可选开启）」。
- 公共 DoH：`dns.google`（+`dns64.dns.google`/`8888.google`）、`*.cloudflare-dns.com`（覆盖 security/family/dns64 等全部变体）+ `one.one.one.one` + `1dot1dot1dot1.cloudflare-dns.com`、Quad9 全变体（`dns[.9-12].quad9.net`+`dot.quad9.net`）、`dns[1-3].nextdns.io`+`doh.nextdns.io`、`doh.opendns.com`、AdGuard 新旧域（`=adguard-dns.com` → `adguard-dns.com`+`*.adguard-dns.com` 覆盖 dns/family/unfiltered 变体 + 旧 `dns.adguard.com`）、`doh.cleanbrowsing.org`、Mullvad DoT 族（`dns.mullvad.net`+`*.doh.mullvad.net`+`dot.mullvad.net`）、ControlD（`freedns.controld.com`+`dns.controld.com`+`doh.controld.com`）、`doh.brave.com`、dns.sb（`doh.dns.sb`/`dot.sb`）、Applied Privacy、LibreDNS、FFMUC、Digitale Gesellschaft、Hostux、SecuredNS、Crypto.sx、DNSForge、Kommespaeter 共 48 条。阿里云/DNSPod/360 的国内入口见「默认注释组」——它们默认生效会把 Loon 自己的 DoH 打到 127.0.0.1。
- 刻意不拦 `doh.dns.apple.com`，避免影响 iOS/macOS 系统解析。

### 广告子域通配层（30 条 + 11 条家族层）

`ads.*`、`ads-*`、`adserver.*`、`adserver-*`、`adserve.*`、`adserv.*`、`adserv-*`、`adserving.*`、`adserving-*`、`adservice.*`、`adservices.*`、`adsystem.*`、`advertising.*`、`advertising-*`、`advert.*`、`adverts.*`、`advertiser.*`、`adtech.*`、`adtech-*`、`adclick.*`、`adnetwork.*`、`adnetwork-*`、`adx.*`、`adx-*`、`adtrack.*`、`adtrack-*`、`adunit.*`、`bannerads.*`、`sponsorads.*`、`ad-exchange.*`。

前 30 条按“广告专用左标签”覆盖任意层级子域，后 11 条按数字分片折叠家族（见上），与 `[Host]` 的精确/通配条目互补：`[Host]` 管已知平台域，通配层管动态/随机广告子域。离线审计（默认 10 个上游源、41.6 万去重域名）显示，该层额外命中约 3,300 个此前未覆盖的广告域名；其中第二轮的 14 条 hyphen/长前缀变体（`adx-*`、`advert.*`、`advertising-*`、`bannerads.*` 等）新增 135 个。

这一层唯一的已知红线重叠：`ads.*` 会连微信要求必须放行的 `ads.privacy.qq.com`（广点通隐私/合规入口）一起命中。Loon 的 DOMAIN-WILDCARD 没有例外语法，所以取舍写进数据里由 `tools/build-ads.py` 复算：命中集与 `redline_overlap` 认罪清单必须逐条相等，漏一条或多一条都构建失败，生成的插件注释里也会把这条重叠打在段首。开启本层前先删掉 `ads.*`，或接受微信 SDK 的异常风险。

---

## DNS 防泄漏

### 插件能做到什么

1. **追加公共 DNS 与 IP 形式 DoH**（`[General]`）：`dns-server` 写具体服务器，不写 `system`；`doh-server` 写 IP，避免 Loon 解析 DoH 域名时被本插件的 Host 规则打断。Loon 同时配置常规 DNS 与加密 DNS 时，会优先使用加密 DNS。
   **真机取证（2026-10-27，海外蜂窝）**：本插件默认的 AliDNS 系 `doh/doh3` 在境外空回复率 69~74%、
   `1.12.12.12` 被限流 429——境内用户保持默认即可；境外使用建议把 `doh-server` / `doh3-server`
   换成就近解析器或直接注释掉（拦截逻辑不依赖加密 DNS，见 `docs/device-checklist.md` I 节）。
2. **封住已知 HTTPDNS/私有 DoH 域名**（`[Host]`）：强制 App 回退到系统 DNS（Loon）。
3. **封住公共 DoH 入口**（`[Host]`）：浏览器/App 的 DoH 解析失败后通常回退系统 DNS，广告域继续被 `[Host]` 拦截。
4. **封住 853 端口**（`[Rule] DEST-PORT,853,REJECT`）：阻断标准 DoT/DoQ，减少 App 自带加密 DNS 绕过。
5. **未知 HTTPDNS 兜底**（`[Rule]`）：`DOMAIN-KEYWORD,httpdns` / `httpsdns`、IP 字面量 `URL-REGEX`（6 条均锚定 `^http://`，只吃明文）、`USER-AGENT` 4 条。**注意**：本插件没有 `[MITM]` 段，而 UA 是 HTTP 请求头、未解密时看不到，这 4 条能否命中**未经验证**——保留是因为成本为零（不解密就不会误伤），验证方法见 `docs/rule-effectiveness.md` 第 3 节。
6. **动态广告子域**（`[Rule] DOMAIN-WILDCARD`）：`ads.*`、`adserver.*`、`adx-*`、`advert.*` 等 30 条前缀 glob 在 DNS 阶段拒绝任意层级子域，弥补 `[Host]` 只能枚举已知域名的缺口。
7. **可选：公共解析器 IP 直连阻断**（`[Rule]` 默认注释组，2.5.0 起）：上面 2–4 全都在跟「域名」打交道。
   但 App 若**直连 `8.8.8.8:443` / `1.1.1.1:853`**，连接层根本没有域名——`[Host]`、
   `DOMAIN-KEYWORD`、`URL-REGEX` 全部失效，`DEST-PORT,853` 也只挡端口、挡不住跑在 443 上的 DoH。
   这时唯一还能生效的是 `IP-CIDR` / `IP-CIDR6`（只看 IP，不需要域名也不需要解密），
   组里收录 Google / Cloudflare / Quad9 / AdGuard 四家共 16 个官方 IPv4 + IPv6。
   **默认关闭**：若你的主配置拿清单内任一 IP 当 `dns-server` / `doh-server`，
   开启会掐断 Loon 自己的解析链——表现是**整网不可用**，比广告回来严重得多。
   开启前逐条核对主配置；本插件自用的 5 个 DNS 刻意不在清单内，lint 会拦住误加。

### 插件不能做到什么（重要）

Loon **插件**的 `[General]` 只支持白名单键：`bypass-tun`、`include-tun`、`skip-proxy`、`real-ip`、`dns-server`、`doh-server`、`doq-server`、`doh3-server`、`ipv6-vif`。因此插件**不能**设置：

- `hijack-dns`
- `domain-reject-mode`
- `dns-reject-mode`
- `disable-stun`

这些键即使写进插件也不会生效。插件也无法删除主配置里的 `system` DNS，无法拦截“未知 IP 的 53/853 明文 DNS”，无法处理 App 把广告域写死成 IP 的情况；系统级加密 DNS 描述文件、iCloud Private Relay 或其他 VPN 也可能绕过 Loon，需要手动移除/关闭。**完整的 DNS 防泄漏必须在主配置里加下面这段。**

### 主配置加固片段

把以下内容合并到 Loon 主配置的 `[General]`（不要替换你已有的节点/规则/证书配置）：

```ini
[General]
# 1. 劫持局域网/系统发往任意目标的 53 端口 DNS，返回 Fake IP
hijack-dns = *:53

# 2. 常规 DNS：不要写 system，避免继续走运营商 DNS
dns-server = 223.5.5.5,119.29.29.29,180.184.1.1

# 3. DoH 用 IP 形式，避免 Loon 解析 DoH 域名时被本插件的 [Host] 打断
doh-server = https://223.5.5.5/dns-query,https://223.6.6.6/dns-query,https://1.12.12.12/dns-query

# 4. 让域名规则在 DNS 阶段直接拒绝，而不是等 TCP/HTTP
domain-reject-mode = DNS
dns-reject-mode = LOOPBACKIP

# 可选：减少 WebRTC/STUN 暴露；可能影响语音/视频通话，按需开启
# disable-stun = true
```

说明：

- `hijack-dns = *:53` 会影响所有直连的 53 端口查询；公司/校园/局域网 DNS 用户先加 `skip-proxy`/`bypass-tun` 例外，或把 `*:53` 换成具体网段。
- 主配置里的 `doh-server` / `doq-server` 如果原本是域名形式，比如 `https://doh.pub/dns-query`、`quic://dns.alidns.com:853`：本插件默认只拦海外公共 DoH，这 9 条国内入口已默认注释，**不会**再互害；但如果你手动开启「国内公共 DoH」组，必须先把主配置改成 IP 形式（例如 `https://223.5.5.5/dns-query`、`quic://223.5.5.5:853`），否则 Loon 自己的 DoH 域名会被插件 `[Host]` 打到 127.0.0.1。
  **真机实锤（2026-10-27）**：主配置 `doq-server = quic://dns.alidns.com:853` 与域名形式 doh.pub 被本插件黑洞
  共 5553 次（`dns.alidns.com Host Map IP:127.0.0.1` ×3360、`doh.pub` ×2193）——整条加密 DNS 链每秒重试每秒失败。
  **2026-10-29 的 23 小时窗口放大到 5 倍**：17073 + 11239 = 28,312 次，
  占当窗口全部 28,547 次黑洞的 99.2%，并连带 5,239 次 DoQ 建立尝试（其中 5,236 次连接失败）、两条上游共 10,389 次 DoH 连接失败与 9,389 次 `NGQUIC-CLOSE host=127.0.0.1`（6,576@443 + 2,813@853）。
  因此 **2.8.0 起这 9 条国内入口改为默认注释**；证据与判读见 `docs/device-checklist.md` I / I2 节。
- 这些参数无法由插件替你设置；本插件只负责 `[Host]`/`[Rule]` 层与追加 DNS。
- 修改后重连 Loon，并在 DNS 检查工具里确认解析不再走运营商 DNS。

---

## 风险与边界

### 会断掉的功能

| 功能 | 影响 | 处理 |
|---|---|---|
| 激励广告/看广告领奖励 | 穿山甲、优量汇、快手联盟广告加载失败，奖励任务失败 | 刷奖励时禁用 `ads.plugin`，或不要装 |
| 安装归因/渠道 ROI | 只有手动启用归因组后才断 AppsFlyer/Adjust 等上报 | 保持默认注释，或删对应组 |
| Firebase/GA/友盟统计 | 只有手动启用统计组后才断报表 | 保持默认注释，或删对应组 |
| App 内置 HTTPDNS | 极少数 App 没有 DNS 回退会断网 | 删 HTTPDNS 组里对应行 |
| 公共 DoH | 海外 48 条默认拦：1.1.1.1/WARP、Chrome/Firefox 安全 DNS、部分浏览器可能提示 DNS 失败；国内 9 条已默认注释，开启后若主配置仍用域名形式 DoH 会废掉 Loon 自己的加密 DNS | 注释公共 DoH 组对应行，或把 Loon 上游改成 IP DoH；国内组开启前必须先改主配置 |
| 853 端口 | 使用标准 DoT/DoQ 的 App 会被断 | 删除 `DEST-PORT,853,REJECT` |
| 广告子域通配层 | 若某业务把 `ads.`、`adx.`、`advertising.` 等左标签用于非广告服务，会被整族拒绝 | 删除对应 `DOMAIN-WILDCARD` 行；glob 只锚定左标签，不会命中共享主域本身 |
| Facebook 登录/Graph API | `graph.facebook.com` / `www.facebook.com` 不拦；但 `b-graph.facebook.com` 等广告测量子域在核心组，Facebook App 登录可能受影响 | 删除 Meta 组里 `b-graph.facebook.com` 两行 |
| Android 厂商广告 | 小米/华为/OPPO/vivo 广告 SDK 被拦；系统更新/云服务一般不受影响 | 删 OEM 组对应行 |
| 部分 App 的“看广告解锁” | 广告不可用，解锁流程卡住 | 临时禁用插件 |

### 明确不拦

- **`branch.io`**：深度链接/邀请/分享基础设施，拦了会断核心功能。
- **`jpush.cn` / `getui.com`**：推送基础设施，不是广告；拦了会丢推送。
- **`is.snssdk.com`**：头条搜索、豆包输入法共用，刻意排除。
- **`graph.facebook.com` / `www.facebook.com`**：承载 Facebook 登录、Graph API 和网页；DNS 整域封禁会断登录。单插件不包含 MITM 路径级增强，因此 FAN 在这些共享域上的广告不会被 DNS 层拦截。注意 `b-graph.facebook.com` 等广告测量子域仍在核心组，若 Facebook App 登录异常，删 Meta 组对应行。
- **YouTube / Twitch / Spotify / Netflix 等内容级广告**：广告和内容走同一批共享域/CDN，DNS 层无法区分。
- **第一方广告**：广告由 App 自己的业务 API 返回（例如 `api.example.com/feed` 里夹广告），DNS 层看不到；只能在 App 专用插件里改响应体。
- **`qq.com` / `baidu.com` / `google.com` / `facebook.com` / `snssdk.com` / `zijieapi.com` / `pstatp.com` / `kuaishou.com` / `yximgs.com` / `unity3d.com` / `amazon.com` 等共享主域**：整域封禁会打断登录、内容、支付、更新等核心功能；只允许精确广告子域。
- **中国六大银行核心与认证域名**（工行 `icbc.com.cn`、建行 `ccb.com`、农行 `abchina.com`、中行 `boc.cn`、交行 `bankcomm.com`、邮储 `psbc.com`）：
  - **金融交易与资金安全第一**：严禁对银行主域使用通配符阻断，严禁对银行域名开启 MITM（六大行具备严格的 SSL Pinning 证书绑定与国密 SM2/SM3/SM4 校验，解密会导致客户端网络报错或触发风控）；
  - **`ad.abchina.com` 明确不拦**：经 EasyList China 与 AdRules 实证取证，该子域承载农行安全认证与核心脚本，误封会导致页面与登录损坏；
  - **精准定向**：银行广告仅阻断已验证的独立广告/营销资产子域（`adv.ccb.com`、`ad.icbc.com.cn`、`ad.boc.cn`、`jf365.boc.cn`、`ad.bankcomm.com`、`ad.psbc.com`），六大行主域已纳入 `protected-roots.json` 强锁保护。

### 为什么没有 MITM / Rewrite / 脚本

本插件的核心目标是“所有去广告插件的底层依赖”。依赖层必须确定性、零证书、零 JS、禁用即撤销。`[Host]` 全部满足；脚本会引入 `requires_body`、超时、JSON 解析、MITM 证书等失败面。Meta FAN 在共享域上的路径级拦截需要 MITM，证书固定风险高，单插件默认不做；需要时请自行维护一个本地严格增强，不要把它混进核心。

### 为什么没有 `[Argument]` 开关

Loon 的 `[Argument]` 只会绑定到 `[Script]` / `[Rewrite]`，**不能条件控制 `[Host]`、`[General]`、`[Rule]`**。给 Host 组加一个假开关只会让用户误以为生效。当前控制方式：

- 整插件安装/禁用；
- 归因/统计组改 `disabled` 后重新 build；
- 某条规则误伤时删对应行；
- 需要更细的开关时，把对应规则放到你自己的本地 Rule/Host 配置里。

---

## 维护与审计

数据源只有两个：

```text
src/ads/domains.json          # 元数据 + [General] + [Rule] + 分组 Host
src/ads/protected-roots.json  # 共享主域保护名单
```

生成与检查：

```bash
python3 tools/build-ads.py            # 重新生成 plugins/ads/ads.plugin
python3 tools/build-ads.py --check    # CI 用：生成物是否与 JSON 一致
python3 tools/build-ads.py --stats    # 看 General/Rule/组/规则计数
```

上游覆盖率审计：

```bash
python3 tools/ads-audit.py --top 40
python3 tools/ads-audit.py --sources anti-ad,hagezi-pro,adguard-dns,easylist-cn --top 60
python3 tools/ads-audit.py --offline --include-disabled --top 60
```

审计工具会：

1. 拉取上游清单（带缓存，默认缓存在 `.cache/ads-audit/`）；
2. 读取 `ads.plugin` 中**未注释**的 `[Host]` 规则和生效的 `[Rule] DOMAIN-WILDCARD` glob，计算覆盖率；默认注释的归因/统计组与可选 glob 单独标出，`--include-disabled` 才会把它们计入覆盖率；
3. 输出覆盖率、Top 未覆盖候选、已失效/未命中规则、共享主域通配/glob 违规；
4. 只读，不自动改插件；人工确认后把候选写进 `src/ads/domains.json`，再 build。
5. **不要被 0.x% 吓到**：项目按“广告平台专域/HTTPDNS 入口”收紧清单，不是照抄上游人海清单；覆盖低不等于失效。

日常改动流程：

```bash
# 1. 改 src/ads/domains.json
# 2. 重新生成
npm run build:ads
# 3. 结构检查 + 测试
npm run lint
npm test
```

### JSON 字段

- `general`：`[General]` 原样行；build 只允许 Loon 插件白名单键，`dns-server` 禁止 `system`，`doh-server` 强制 IP 形式。
- `rules`：`[Rule]` 原样行；build/lint 只允许 REJECT 系列策略。
- `domain_wildcards`：左标签锚定的 `DOMAIN-WILDCARD` glob；build 生成**注释行** `# DOMAIN-WILDCARD,<glob>,REJECT`（3.5.3+ 才支持，默认注释以免挡住正式版），校验左标签锚定、不允许字符集、不命中 `protected-roots.json`。
- `family_wildcards`：数字分片家族 glob（含 `[0-9]`）；build 额外要求「至少覆盖 2 台 `[Host]` 已枚举主机」、首标签 3+ 字面量、只允许 `[0-9]`、不命中保护名单；同样默认注释输出。
- `rules_disabled`：默认注释的可选 Rule；build 会加 `# `，不参与匹配。
- `groups[].disabled`：Host 组默认注释；归因/统计组用它实现“单文件、默认不生效”。

### 加规则的原则

1. **广告专域才用 `=`（apex + `*.`）**：例如 `=applovin.com`、`=doubleclick.net`。
2. **共享域只写精确子域**：例如 `ad.zijieapi.com`、`gdt.qq.com`、`ads.pinterest.com`；不要写 `*.qq.com`、`*.google.com`。
3. **先有证据再加**：至少一个上游清单或真实抓包/页面请求；不要凭“看起来像广告”整域封。
4. **宁缺毋滥**：拿不准的域名放审计报告里观察，不要直接进核心。
5. **同一条规则只能出现一次**：build 会跨组查重，重复会直接失败。
6. **HTTPDNS 域名是“强制回退”，不是“广告专域”**：加之前确认该 App 有系统 DNS 回退，或接受可能断网。
7. **DOMAIN-WILDCARD 只允许“广告专用左标签 + 显式 glob”**：例如 `ads.*`、`adserver-*`；不能写 `*`、`*.com`、`ads*`。build/lint 会校验左标签锚定、`*`/`?` 语义与保护名单，宽泛 glob 直接构建失败。

### 上游参考

审计/研究阶段参考过以下公开清单（各清单版权与许可见其仓库，本仓库只保留人工复核后的广告专用域名，不做整表搬运）：

- [anti-AD](https://github.com/privacy-protection-tools/anti-AD)
- [Hagezi DNS blocklists](https://github.com/hagezi/dns-blocklists)
- [AdGuard DNS filter](https://github.com/AdguardTeam/AdguardFilters)
- [EasyList / EasyList China](https://easylist.to/)
- [StevenBlack/hosts](https://github.com/StevenBlack/hosts)
- [Peter Lowe's Ad and tracking server list](https://pgl.yoyo.org/adservers/)
- [AdAway](https://github.com/AdAway/adaway.github.io)
- [AWAvenue](https://github.com/TG-Twilight/AWAvenue-Ads-Rule)
- [AdRules](https://github.com/Loyalsoldier/surge-rules)

---

## 常见问题

**Q：为什么映射到 `127.0.0.1`，不是 `0.0.0.0` 或 `198.18.x.x`？**
`127.0.0.1` 在 Loon 的 TUN、HTTP 代理、直连三种模式下都能快速失败；`0.0.0.0` 在 iOS 上语义不稳定，`198.18.x.x` 在没有 `[IP Rewrite]` 时会尝试出网，可能变成超时。

**Q：为什么不用 `[IP Rewrite] ... = reject`？**
`[IP Rewrite]` 只在 TUN 模式稳定生效；`[Host]` 到 `127.0.0.1` 不依赖 TUN，兼容性更好。若你只用 TUN，可以自行在本地配置里把 `127.0.0.1` 的连接 RST，但不要写进共享插件（会影响其他人的 localhost 服务）。

**Q：为什么 `[Host]` 要写 apex 和 `*.` 两行？**
Loon 的 `*.example.com` 不保证匹配 `example.com`；广告专域通常两者都要，所以 `=` 简写展开成两行。

**Q：为什么不用 `[Host]` 的 `*.example.com` 代替 `DOMAIN-WILDCARD`？**
`[Host]` 只能表达“某个具体域名的子域”；`ads.*` 要表达的是“左标签为 ads 的任意域名（任意 TLD、任意层级）”，只有 `DOMAIN-WILDCARD` 的跨点 `*` 能做到。它需要 Loon 3.5.3(1008)+，而当前 App Store 正式版是 3.5.2(996)——所以插件头保持 **3.5.2(996)**、通配层默认注释：不让 TestFlight 版本挡住真实用户，装了 3.5.3+ 的用户取消注释即得整族拦截。

**Q：DOMAIN-WILDCARD 会不会误伤共享主域？**
不会命中保护名单本身：30 条 glob 都以广告专用左标签开头，build/lint 用 `protected-roots.json` 校验；lint 还有正/负样本（如 `ads.*` 不命中 `example.com`、`adsl.example.com`）。若某业务确实把 `ads.` 左标签用于非广告服务，删对应一行即可。

**Q：插件里的 `[Rule]` 禁用插件后还会生效吗？**
`[Rule]` 是插件配置的一部分，禁用插件后不会再从该插件加载；但 Loon 本地规则优先于插件规则。如果你曾把同样的规则手工复制到主配置或本地规则，那部分当然不会随插件撤销。

**Q：装了 `ads.plugin` 后某个 App 白屏/登录失败？**
先禁用 `ads.plugin` 复现；如果恢复，说明该 App 把广告/HTTPDNS 域和核心 API 混在同一个域。把 App 名和抓到的域名发 issue，不要直接整域放开共享主域。

**Q：公共 DoH 拦截后浏览器打不开网页？**
先确认是不是 Loon 自己的 DoH 在打架：日志里出现 `dns.alidns.com` / `doh.pub` 的高频 `Host Map IP:127.0.0.1`，说明主配置用了域名形式 DoH/DoQ。国内 9 条自 2.8.0 起已默认注释；若你手动开了「国内公共 DoH」组，把主配置改成 IP 形式或重新注释该组。`doh.dns.apple.com` 始终不拦。若只用 IPv6 或本地 DNS，先测试再启用。

**Q：为什么 HTTPDNS 组会拦到非广告 App？**
HTTPDNS 是“绕过系统 DNS 的通道”，不是广告域本身。我们拦它让 App 回退到 Loon DNS，从而让广告 Host 生效；代价是极少数没有回退的 App 可能断网。删对应行即可。

**Q：能不能只拦广告、保留激励广告？**
不能按 App 区分——同一个穿山甲/优量汇域名既服务激励广告也服务普通广告。要保留激励广告，只能不装 `ads.plugin`，或在刷奖励时临时禁用。

**Q：为什么归因/统计不默认启用？**
它们会断安装归因、渠道 ROI 和报表，但不影响广告展示拦截。默认注释，避免“装个去广告插件把统计打挂”；需要时按上面的方法开启。

**Q：能不能把 FAN 的 `graph.facebook.com` 也加进 Host？**
不要。它会断 Facebook 登录/Graph API。共享域路径级拦截需要 MITM，单插件为了零证书不提供；自行维护严格增强时也要先测试证书固定。

---

## 版本

- **2.8.0**（2026-10-30）：**公共 DoH 防泄漏改成「海外默认拦、国内默认注释」——插件第一次主动撤回自伤默认**。2026-10-29 的 23 小时真机日志里，主配置 `doq-server = quic://dns.alidns.com:853` + `doh-server = https://doh.pub/dns-query`，本插件 `[Host]` 把这两个域名一起黑洞：`dns.alidns.com` 17,073 次 + `doh.pub` 11,239 次 = **28,312 次，占当窗口全部 28,547 次 Host Map 的 99.2%**，并连带 5,239 次 `quic://dns.alidns.com:853` 建立尝试（5,236 次连接失败）、两条上游共 10,389 次 DoH 连接失败、9,389 次 `NGQUIC-CLOSE`（6,576@443 + 2,813@853）。插件读不到主配置，无法只拦 App 而放过 Loon 自身；在国内用户常配的域名形式加密 DNS 下，默认拦等于把用户的解析链打瘫。处置：阿里云/DNSPod/360 共 9 条移入新组 `doh_public_cn` 默认注释，海外 48 条仍默认生效。生效 Host 1475→1466（exact 900→891 / wildcard 575）、默认注释 122→131、组 19→20；公共 DoH 组 57→48。`tests/lint-plugins.py` 新增自伤门禁：这 9 条只要出现在生效 Host、缺少注释形态，或 `doh_public_cn` 不等于这 9 条，`npm run check` 立即失败。开启本组前必须把主配置 dns/doh/doq 全改 IP 形式（上方「DNS 防泄漏」段给出可复制配置）。
- **2.7.8**（2026-10-29）：**把「App 红线」从散文变成数据，红线数据立刻反咬本插件两口**。`src/apps/*.json` 新增 `redlines` 字段（99 条，覆盖 13 个 App；每条带 `kind`/`quote`/`why`，`quote` 必须是同一文件 comment 里的原文片段且域名是独立 token——凭品牌名造域进不了名单）。判定与名单住在 `tools/redlines.py`，`tools/build-ads.py` 与 `tools/build-apps.py` 共用：**任何默认生效的拦截条目命中任一 App 红线即构建失败**（注释掉的组不参与，红线只管默认就会生效的东西）。门禁首跑抓到两处自相矛盾：ads 在 httpdns 组默认黑洞 `dns.jd.com`、在 cn_union 组默认黑洞 `=union.jd.com`，而 `src/apps/jd.json` 的「红线（绝不进任何拦截组）」原文逐字写着它们——两条移入新组「与按 App 插件红线冲突的候选」（默认注释，两面理由都印在组注释里）。再加 `redline_overlap` 认罪层：通配 `ads.*` 会命中微信要求放行的 `ads.privacy.qq.com`，DOMAIN-WILDCARD 没有例外语法，于是命中集与认罪清单必须逐条相等，漏报或多报都构建失败，插件里也会把这条取舍打在段首注释。生效 Host 1479→1476（exact 901 / wildcard 575）、默认注释 118→121、展开 1597 不变；核心广告组 1349→1347、HTTPDNS 组 73→72。
- **2.7.7**（2026-10-28）：**按公开资料补 23 个小米/MIUI/MiTV 与 OPPO/荣耀广告主机**。前 20 个小米主机不在 14 份通用广告清单里，由公开 `xiaomi-dns-blocklist`、`hagezi-xiaomi` 与 MiTV 去开机广告教程逐条列出：`ad1.xiaomi.com`、`ad.mi.com`、`ad.cdn.pandora.xiaomi.com`（电视广告 CDN）、`ad.quickapp.hybrid.xiaomi.com`、`adv.sec.miui.com`/`adv.sec.intl.miui.com`（含 `*.` 子域）、`api.admob.xiaomi.com`、`ads.xiaomi.com`（含 `*.`）、`adx.tv.mi.com`/`staging-adx.tv.mi.com`（MiTV 广告交易）、`ad.miui.com`、`ad.eu/rus/india.xiaomi.com`、`adv.l7.34.sec.miui.com`、`global-ad-extranet-pri-azams/azpn.alb.xiaomi.com`、`global-ad-intl-pri-alisgp.alb.xiaomi.com`、`wtradv.market.xiaomi.com`、`xadx.file.market.xiaomi.com`（hagezi-xiaomi 通配收录的系统广告位/商店推广/ADX 素材/跨国投放 ALB）；再补 3 个单源但语义明确的厂商主机：`adx-in.ads.heytapmobile.com`（realme/OPPO 印度广告交易）、`ads-drcn.platform.hihonorcloud.com` 与 `metrics-ad-drcn.dt.hihonorcloud.com`（荣耀广告平台/测量）；另补中国程序化广告平台聚告 AdinALL（`adinall.com`，公开官网与第三方共享清单可核实）。生效 Host 1441→1479（exact 903 / wildcard 576），展开 1597；核心广告组 1311→1349。
- **2.7.6**（2026-10-28）：**补 14 个 4–7 源、公开身份可核实的广告专域**。TenMax 台湾 RTB/原生广告网络（`tenmax.io`，7 源）；Bid Run 程序化平台（`bid.run`，BuiltWith 收录）；Geniee SSP 五域（`genieessp.jp`/`genieesspv.jp`/`gsspat.jp`/`gsspcln.jp`/`gssprt.jp`，同为日本 Geniee 广告投放链路）；Speee 广告投放（`speee-ad.jp`，日本站点外部送信政策里的 `click.speee-ad.jp`/`uzou.speee-ad.jp`）；EuroAds 丹麦联盟（`euroads.dk`）；WebAds 欧洲媒体网络（`webads.eu`）；SelectMedia 视频 SSP（`selectmedia.asia`）；Seznam SSP（`ssp.seznam.cz`）；TargetADS 广告验证（`targetads.io`，VK Ads 审计像素）；中国 50bang 广告/流量联盟（`50bang.org`，上游列出 `union2`/`guess` 广告子域）。**跳过**：`hottraffic.nl`、`mediatraffic.com.ua`、`pabidding.io`（公开身份未能核实，不靠命中数硬收）、`pebfvv.icu`（随机域，生命周期不确定）。生效 Host 1413→1441（exact 879 / wildcard 562），展开 1559；核心广告组 1283→1311。全部未逐域抓包，异常时按行删除。
- **2.7.5**（2026-10-28）：**再补 28 个 6 源广告专域**。从刷新后的候选中继续筛语义自证者：22 个交易/SSP/DSP/视频/header bidding 域（vidcpm、knorex、m32.media、hueadsxml、media6degrees、tribalfusion、simpli.fi、fastclick、ncaudienceexchange、lucidmedia、jumptap、tradeadexchange、industrybrains、pointroll、vdopia、venturead、creativecdn/RTB House、blogherads、webads.co.nz、pushnami、retagro、h-bid）+ 5 个共享根精确主机（`bat.bing.net` Bing Ads UET、`pix.revjet.com`、`beap-bc`/`ganon`/`3p-udc.yahoo.com` Yahoo 广告交换与数据）+ 弹窗组 ExoClick 投放域 `magsrv.com`。**跳过** `ns1p.net`（无语义）、`adlog.com.com`（无上下文）、`gmads.net`（带 `sat1.de` 白名单例外）。生效 Host 1362→1413（exact 865 / wildcard 548），展开 1531；核心广告组 1232→1283。
- **2.7.4**（2026-10-28）：**刷新上游后补 34 个 6 源广告专域**。重跑 10 源审计，从 4933 个 ≥5 源未覆盖候选中只取语义自证的广告交易/网络：Dable、Zemanta/Outbrain、Carbon Ads、PageFair、Clickbooth、Demandbase（`company-target.com`）、Adviva、Harren Media、ClickRev、TrafficShop、TwitTad、Connatix（`ck` 精确主机）、Retargeter、JuiceADV、EqAds、PostRelease、Adoric（`-om` 投放域）、MSN RTB（`srtb` 精确主机）、The Moneytizer、Fout、Speakol、MicroAd、Greystripe、Optimix、Geniee SSP（`gmossp-sp.jp`）、StackAdapt、SmartyAds、Dianomi、TripleLift（`3lift.com`）、ValueClick、District M、BidGear、AdButler（`servedbyadbutler.com`），弹窗组补 PopMyAds。**不补**分析/会话回放（hotjar/sessioncam/quantummetric/siteimprove）、广告验证与反欺诈（confiant/titanhq/fpjs，拦掉反而放大恶意广告风险）、联盟返利（zanox/vcommission）与 6 源随机域（`4jnzhl0d0.com` 等）。生效 Host 1296→1362（exact 837 / wildcard 525），展开 1480；新增项未逐域抓包，异常时按行删除。
- **2.7.3**（2026-10-28）：**收掉 5 个「7 源但名字不自证」的精确主机**。逐条回到缓存清单看上下文，而不是只看命中数：`bd1.guancha.cn` 在 AdGuard 中文列表里带 `$domain=m.guancha.cn`（只在观察者网 m 站加载的广告脚本）；`ggs.myzaker.com` 是 ZAKER 的广告服务器；`d2.sina.com.cn` 被 EasyList China 标为 `$object,script`（新浪广告脚本/对象）；`cm.baidu.com` 与 `entry.baidu.com` 紧邻 `cpro/cbjs/eclick` 等百度广告域，后者在 EasyList China 精确到 `/rp/home?` 推广入口。5 条全部按精确主机收录（不升通配），生效 Host 1291→1296（exact 803 / wildcard 493），展开 1414。`zhihuifangdong` 因引用 baidu SDK 组同步 +2（94→96 条黑洞）。**仍不补** `kw0xlh4wig.com`（无语义随机域）、`assoc-amazon.com`（联盟返利）、`vnet.cn`（基础网络）与 `smetrics.*` 等分析域。
- **2.7.2**（2026-10-28）：**修复两个审计源的 404，并按完整 12 源分母再补 33 个长尾广告专域**。①`adguard-cn` / `adguard-mobile` 原来指向已迁移的 `FiltersRegistry` 路径、在线审计直接 skip；改用官方 `filters.adtidy.org` 的 224（中文）/ 11（移动广告）完整列表后，App 覆盖率审计恢复 14 源分母（13 个 App 仍为 0 缺口）。②从恢复后的 12 源分母里补 33 个 ≥7 源广告专域：百度 `ecmb.bdimg.com`（点击监测）；中国媒体 `ykad-data.youku.com`、`de.as.pptv.com`、`adpai.thepaper.cn`；全球交易/SSP `kiosked`、`sitemaji`、`begun`、`tubemogul`、`nanigans`、`inner-active`、`i-mobile`、`celtra`、`brealtime`、`exponential`、`iqzone`、`adhood`、`adtimaserver`、`httpool`、`infolinks`、`buysellads`、`presage`、`disqusads`、`blogads`、`biddingx`、`mixadvert`、`rotaban`、`speee-ad.akamaized.net`；移动广告网络 `youmi`、`fiksu`、`mydas`、`nend`、`i2ad`；弹窗 `buzzonclick`。③**刻意不补**：`assoc-amazon.com`（联盟返利）、`vnet.cn`（基础网络）、`smetrics.*` / `nytimes` / `apple` / `unity3d` 分析域（归统计组）、`nextacdn.top` / `kw0xlh4wig.com` 等无品牌语义随机域。④生效 Host 1230→1291（exact 798 / wildcard 493），展开 1409；新增项未逐域抓包，异常时按行删除。
- **2.7.1**（2026-10-28）：**按上游清单做一次长尾补洞**（13 个 App 同轮刷新后仍为 0 缺口）。重跑 `tools/ads-audit.py --refresh` 后，从 1861 条未覆盖的广告 token 候选中人工筛出 11 个语义自证、≥5 源收录的广告专用域：中国媒体/SSP/OEM 侧补 `ad-api.cnblogs.com`、`abroad-ad.kingsoft-office-service.com`（WPS）、`dsp.ali213.net`、`pg-ad-b1.nosdn.127.net`、`static-ssp.yidianzixun.com`、`ssp.21ic.com`、`ad.cctv.com`、`ad.gmw.cn`、`bdapi-ads.realmemobile.com`、`bdapi-in-ads.realmemobile.com`，全球侧补 `ad.daum.net`（Kakao/Daum）。**不补** `prebid.org`（行业组织）、`clickdensity.com`/`clicktracks.com`（统计）等只是名字像广告的域；新增项未逐域抓包，异常时按行删除即可。审计工具同轮修了下载重试：上游 adrules 截断响应不再让整次审计崩掉（3 次重试后仍失败才报错）。
- **2.7.0**（2026-10-28）：**把导入门槛降回 App Store 正式版，不再用 TestFlight 版本挡真实用户**。此前插件头 `#!loon_version=3.5.3(1008)`（为加载 `DOMAIN-WILDCARD` 抬高），而当前 App Store 正式版是 **3.5.2(996)**、3.5.3 build 1007–1011 只在 TestFlight——正式版用户点导入会直接被挡在门外。①插件头降为 **`3.5.2(996)`**：核心 `[Host]` 黑洞、`[Rule]` HTTPDNS/端口/UA、`[General]` DoH/DoT 在 3.5.2 全量生效，人人可导。②`DOMAIN-WILDCARD` 通配层（30）+ 数字分片家族层（11）改为**默认注释行**收录（`# DOMAIN-WILDCARD,<glob>,REJECT`）：3.5.2 用户保持注释即可（这批左标签的已知具体广告/DoH 域已由 `[Host]` 逐条覆盖），装了 3.5.3+ 的用户逐行去掉 `# ` 即启用整族动态子域拦截。③build/lint/coverage 三处联动：`tools/build-ads.py` 去掉「有 glob 就要求 build≥1008」硬门槛、通配一律加 `#`；`tests/lint-plugins.py` 反向锁定「`DOMAIN-WILDCARD` 必须保持注释、`#!loon_version` 不得超过正式版 996」，App 插件同锁；`tools/loon-coverage.py` 把 r-wildcard 期望降为 `open`（注释层不计入生效能力）。④App 插件生成链 `tools/build-apps.py` 明确禁用 `DOMAIN-WILDCARD`（app 插件永远走 `[Host] '*.'` 黑洞），并加正式版 build 上限校验。

- **2.6.0**（2026-10-27）：**用真机日志做反向缺口审计**（第五个分母：设备真实访问过、但不在清单的域名）。两份 iPhone 日志（约 4.5 分钟 × 9 万行 + 3.5 小时）里 878 个去重域名逐一与本仓插件清单（含 `*.` 通配语义）交叉比对，按「归因核实 + 真机请求实锤」补 30 条：**analytics 组（默认注释）+27**——`app-analytics-services.com`（GA 别称，Netify 核实）、`mixpanel.com`、腾讯 Beacon/APM（`rmonitor.qq.com`/`h.trace.qq.com`/`unitelogreport.reader.qq.com`）、美团 `dreport`/`wreport`、JPush 统计族、BOSS 直聘 APM、Firebase logging/crashlytics、微信 `badjs`、起点 `upush`；**httpdns 组（常开）+1**——`amdc.alipay.com.cn`（阿里系调度绕路，真机 ×4）；**retail_ctv_audio（常开）+2**——`ads-api.x.com`（X 广告接口）、`ca.iadsdk.apple.com`（补齐清单内 `iadsdk.apple.com` 的已观测子域）。字节系遥测（`mon`/`log`/`abtest`/`mssdk`/`pitaya`）**刻意不加**：与领奖风控/远程配置同源，误伤代价大于收益。顺带取证两处：`Host Map IP:127.0.0.1` 才是黑洞命中的日志格式（此前误把主配置黑名单的 `Reject domain` 记在本插件头上）；主配置若用域名形式 doh/doq，会与防泄漏组互害（本窗口 `dns.alidns.com` 被黑洞 3360 次），处置见 [`docs/device-checklist.md`](../../docs/device-checklist.md) I 节。
- **2.5.0**（2026-10-27）：换第四个分母——从「规则有没有生效」到「**路径有没有封死**」，新增 `tools/bypass-audit.py` 与 [`docs/bypass-audit.md`](../../docs/bypass-audit.md)。①**枚举 17 条旁路**（App 可以绕开整个插件的路），四态 `sealed` / `partial` / `open` / `na`，每条写清「怎么绕 / Loon 的手段 / 为什么停在这 / 真机怎么证伪」。当前已封死 6、部分封死 4、**有手段未落地 1**、无解 6。②**唯一「有手段未落地」是 IPv6 / AAAA 旁路**：`[Host]` 1301 条黑洞全部只映射 IPv4，官方 `DNS/hostmap` 支持 `ip-mode:v4-only`，但只给了单独使用的示例——若 Loon 一个域名只认最后一条，补 ip-mode 会把黑洞**覆盖掉**，比不补更糟。因此**刻意不落地**，等真机两步验证（先验多行共存、再验 AAAA 是否放行）通过后再批量补。③**本轮真落地：公共解析器 IP 直连阻断组（默认注释）**，补 Google / Cloudflare / Quad9 / AdGuard 四家共 16 个官方 IPv4 + IPv6，**逐条取自官方页面不凭印象**。④lint 新增 `check_bypass_dns_guard()`：本插件自用的 5 个 DNS IP 出现即报错，四家 16 个 IP 缺一即报错。⑤三条结论性无解写进审计（主配置规则优先级 本地>插件>订阅、`bypass-tun`、证书固定）——**知道封不了，也是一种封**。（**第十八轮更正**：本条原文把取值写成 `ipv4-only`/`ipv4-preferred`——那是别的实现的命名。官方 `DNS/hostmap` 与「通用配置」的值表是 `v4-only`/`dual`/`prefer-v4`/`prefer-v6`/`v6-only`；照非法值做真机探针，Loon 会直接忽略该行，A 记录「看起来仍生效」纯属假阳性。已全文改为 `ip-mode:v4-only`，并由 `tests/lint-plugins.py` 的 `check_ip_mode_values()` 永久锁死右值。）
- **2.4.0**（2026-10-27）：补上 Mintegral 的真实请求域，并撤回上一版「下一步」里做不到的部分。①**Mintegral 此前只拦了品牌域**：清单里只有 `mintegral.com`，而 SDK 的广告请求与统计实际走 `net.rayjump.com` / `setting.rayjump.com` / `analytics.rayjump.com` / `cdn-adn-https.rayjump.com`（Mobvista 旗下 Rayjump 基础设施）。新增 `rayjump.com`（精确 + `*.` 通配）、`mtgglobals.com`、`mintegral.net`，展开 `[Host]` 1295 → 1301 条。**激励 / 插屏 / Banner 仍停在 `strong`，没有升 `full`**——补完一家不等于补完一类。②**删掉三个自己猜错的域**：初版还加了 `adtiming.com`、`smaato.com`、`ogury.com`，核实后全是官网域（真实请求走 AdTiming 的私有端点、`smaato.net`、`ogury.io`），加进去拦不到广告还会拦官网。这正是本插件一直在防的错：从品牌名推域名。③**撤回 90.9% 的假承诺**：上一版把 11 条「下一步」算成可达 90.9%，逐条核对后只有 3 条是「零风险加域名」；其余撞在机制上——`[Argument]` 只作用于 `[Script]`/`[Rewrite]` 的 `enable`，管不到 `[Host]` 与静态 `[Rule]`；`URL-REGEX` 在 HTTPS 下要 MITM 才取得到路径；「最小合法包络」必须改响应体；私有 JSON 提档 = 多适配一个 App。④**每类新增 `blocked` 字段**记录「为什么提不了档」，`--check` 增加两条互斥断言（承诺提档时不许写 `blocked`，距上限停住时必须写）。当前 70.9%（39/55），待做增分 0，结构性停住 13 类。
- **2.3.1**（2026-10-27）：按「广告类型」补齐两个结构性缺口，并把这件事变成可回归的审计。①**视频贴片/大屏（VAST/VMAP）**：新增 FreeWheel 系 `fwmrm.net`（含 `*.v.fwmrm.net` 二级子域）与 `stickyadstv.com`，以及 Sizmek `serving-sys.com`——这三家是 CTV 与长视频前贴/中贴的广告决策服务器，拦掉后播放器走「无广告」分支，而不再反复拉清单。②**国内聚合**：新增倍孜 `beizi.biz` / `adn-plus.com.cn`（TopOn 之外的第三方聚合，2024 后在中长尾 App 里占比上升）。③新增 **`tools/ad-surface-audit.py`**：把 19 类广告按「可切断点」分成 6 族，逐类声明理论可达档与当前档，并从插件/脚本里**探测证据**；`--check` 会在「声明做了但探不到」「声明没做却探到了」「当前档高于上限」三种情况下失败。生成的 [`docs/ad-type-strategy.md`](../../docs/ad-type-strategy.md) 给出每类的特征、规则思路、覆盖与局限，以及零证书方案 44% 的天花板。当前覆盖率 71%，落地「下一步」后 91%；零证书方案的天花板是 42%。④顺带确认 `[Host]` 官方支持 `*.` 通配（hostmap 文档示例 `*.testflight.apple.com`），`*.v.fwmrm.net` 这类二级通配因此可以显式写。生效 Host 1295 条、生效 Rule 54 条。
- **2.3.0**（2026-10-27）：把 `DOMAIN-WILDCARD` 的第三类通配符 `[0-9]` 用起来，新增「数字分片家族层」11 条。①左标签 glob 覆盖不到 `ads1/ads3/ads5` 这类编号分片，字符类可以：`ads[0-9]-normal*.zijieapi.com` 一条覆盖 `ads3/ads5 × normal、-hl、-lf、-lq、-xh` 全部 10 台，并把 Pangle 未来新增的分片一起收进来。同类还有 `p[0-9]-ad-sign.byteimg.com`、`v[0-9]-ad.video.yximgs.com`、`pangolin-sdk-toutiao[0-9].com`、`ads[0-9].msn.com`、`ads[0-9]-adnow.com`、`ads-splash-i/v[0-9].xhscdn.com`、`pg-ad-b[0-9].ws.126.net`、`dns[0-9]*.quad9.net`、`dns[0-9]*.nextdns.io`，合计 11 条 glob、覆盖 30+ 台已枚举主机。②build 新增 `family_wildcards` 校验：只允许 `[0-9]`（`[a-z]`/`[!0-9]` 会让保护名单失效）、首标签 3+ 字面量、不命中 `protected-roots.json`，并且**必须覆盖 2 台以上 `[Host]` 已枚举主机**——凭想象造家族进不来。③lint 永久锁定 11 条模式 + 每条声明覆盖的主机 + 反样本（`ads-normal-hl`、`ads10-normal-hl`、`adsxx-normal-hl`、后缀伪装 `…zijieapi.com.evil.example`），并验证 `[0-9]` 之外的字符类直接报错。④审计工具与 build 的 glob 翻译同步支持字符类，覆盖率 7,589→7,592 域（`glob 41`）。⑤**删掉一条编造的参数**：规则行的 `pre-matching` / `extended-matching` 是 Surge 的写法，Loon 官方三页规则文档只定义 `no-resolve`（仅 IP 类用），72 条规则全部清掉，生成物改为 `DOMAIN-WILDCARD,<glob>,REJECT`；想要「DNS 阶段拒绝」的正解是主配置 `domain-reject-mode = DNS`（插件无权声明）。lint 新增 `SURGE_ONLY_RULE_PARAMS` 防回归。
- **2.2.0**（2026-10-27）：把 Loon 3.5.3(1008) 的 `DOMAIN-WILDCARD` 真正用于覆盖层。①首轮新增 16 条生效 `[Rule]` glob（`ads.*`、`ads-*`、`adserver.*`、`adserver-*`、`adserve.*`、`adserv.*`、`adserving.*`、`adservice.*`、`adservices.*`、`adsystem.*`、`advertising.*`、`adtech.*`、`adclick.*`、`adnetwork.*`、`adx.*`、`adtrack.*`），按广告专用左标签在 DNS 阶段拦截任意层级子域；随后按缓存上游清单再补 14 条 hyphen/长前缀变体（`adx-*`、`advert.*`、`adverts.*`、`advertising-*`、`advertiser.*`、`adserv-*`、`adserving-*`、`adtech-*`、`adnetwork-*`、`adtrack-*`、`adunit.*`、`bannerads.*`、`sponsorads.*`、`ad-exchange.*`），共 30 条生效 glob，第二轮新增 135 个高置信广告域（保护名单命中全部为广告子域）。默认 10 个上游源的离线审计覆盖 4,279→7,589 个域名（1.03%→1.82%）。②build 新增 glob 安全校验：左标签锚定（3+ 字符 + `.`/`-`）、只允许 `*`/`?`、拒绝 `*`/`*.com`/`ads*` 等宽泛模式、不命中保护名单、与 `#!loon_version` Build ≥1008 联动。③lint 永久锁定 30 条模式、正/负样本与 `ads.*` 不命中 `example.com`/`adsl.example.com`、`advert.*` 不命中 `advertise.example.com`；审计工具把生效 glob 计入覆盖率并检查保护名单违规。④插件最低版本从 3.5.1(983) 提高到 **3.5.3(1008)**。
- **2.1.5**（2026-10-27）：补充广告/测量专域与公共加密 DNS 入口。①核心层新增 `advertnative.com`、`ntvk1.ru`、`lentainform.com`、`valueclickmedia.com`、`medleyads.com`、`bluecava.com`、`voicefive.com` 与零售 CTV 测量域 `events.brightline.tv`，生效 Host 1167→1200 条（exact 744 / wildcard 456）；②公共 DoH/DoT 组 39→57 条，补 NextDNS、ControlD、Quad9、Cloudflare DoT、Mullvad、AliDNS，以及 Applied Privacy、LibreDNS、FFMUC、Digitale Gesellschaft、Hostux、SecuredNS、Crypto.sx、DNSForge、Kommespaeter，堵住更多 App 自带加密解析绕过；③可选统计组新增 `cetrk.com`、`wizaly.com`、`stat.pl`、`soicos.com`、`stats.wp.com`、`nr-data.net`、`annoyingacoustics.com`、`sanalytics.disneyplus.com`，默认注释后展开 72→86 条；④lint 增加上述核心域与公共 DoH 的永久回归锁，防止后续误删。
- **2.1.4**（2026-10-26）：深化 Loon 现代能力与埋点/遥测拦截。①HTTPDNS 关键词规则采用 `REJECT-DROP`（丢包无回复），防止客户端 SDK 在收到空 200 包后频繁秒级重试造成网络风暴；②新增针对第三方统计与埋点 SDK（如神策）的 `REJECT-DICT` 规则（返回 200 + `{}` 空字典），诱导客户端主动清空本地重试队列（`deleteEvents`），彻底避免本地存储膨胀与无线电唤醒；③提拔纯广告效果监测专域（`coremetrics.com`、`sumome.com`、`insightexpressai.com`、`blueconic.net`、`pixel.watch`）至核心生效层，生效 Host 升至 1155 条、生效 Rule 升至 13 条；④构建工具原生支持 Loon Build 1007+ 插件专属的 `[IP Rewrite]` 语法（单 IPv4 / 严格查重 / 保护名单安全防护），并在可选层收录 16 条单 IPv4 HTTPDNS 网关接入点，可在 TUN 阶段最快阻断。
- **2.1.3**（2026-10-26）：可选 `[Rule]` 组接入 Loon 3.1.7+ 的 `PROTOCOL` 协议规则，新增 `PROTOCOL,STUN,REJECT`（协议级阻断 STUN，防 WebRTC 真实 IP 泄露；会断部分 App 的语音/视频通话，默认注释；主配置更优解 `disable-stun = true`）。默认注释 Rule 合计 27→28 条。功能盘点见 [`docs/loon-feature-checklist.md`](../../docs/loon-feature-checklist.md)。
- **2.1.2**（2026-10-26）：全网取证强化 DNS 层。①公共 DoH 组 16→39 条：补 AdGuard 新域 `dns.adguard-dns.com`（`=adguard-dns.com` 展开覆盖 dns/family/unfiltered 变体——官方文档 DoQ 示例即用此域；旧域 `dns.adguard.com` 保留）、`*.cloudflare-dns.com` 通配 + `one.one.one.one`/`dns.cloudflare.com`、Quad9 全变体、NextDNS DoT 节点 `dns1-3.nextdns.io`、DNSPod `dns.pub`/`dot.pub`/`sm2.doh.pub`、`dot.360.cn`、`dns64.dns.google`/`8888.google`、dns.sb（`doh.dns.sb`/`dot.sb`）、Mullvad DoT 族、ControlD `freedns.controld.com`；来源 curl wiki 公共 DoH 清单、AdGuard DNS KB、DNSPod 官方文档。②HTTPDNS 组补 `*.httpdns.aliyuncs.com`（覆盖阿里《启动接入点》`resolvers-cn/hk/sg/us/de` 域名兜底）。③可选 HTTPDNS 网关 IP 组 5→27 条：新增阿里内地接入点 `203.119.238.240`/`106.11.25.239`/`59.82.99.47` 与 4 个 IPv6 接入点、海外接入点（香港/新加坡/美洲/欧洲 IPv4 ×8 + IPv6 ×6，与阿里云海外 CDN 网段相邻已加风险注释）、腾讯企业版 `43.132.43.43`/`43.132.55.55`；删除笔误 IP `186.76.76.200`（百度官方文档任何版本都只有 `180.76.76.200`），lint 永久锁掉并新增 `119.29.29.29`（本插件 dns-server）禁拦保护；依据阿里云 doc 2868011、腾讯云 doc 379/59133、百度智能云《访问入口》。生效 Host 合计 1135 条（exact 694 / wildcard 441）。
- **2.1.1**（2026-10-26）：继续扩展主流覆盖，三轮合计新增 138 个广告专用域（+250 条展开规则）。①移动 SDK/交易生态 79 个（applvn、inmobicdn、tapjoyads、mobfox/mobclix、adtrue、adspredictiv、adbutler、adsupply、IAS adsafeprotected、AOL adtechus、adsinteractive、adsniper.ru、doubleclick.com、adsense.com 等）；②**开屏专项 32 个**（小红书 `*.ads-splash-*.xhscdn.com` + `splash-online-decision.xiaohongshu.com`、Unity 中国 `splash-ads.unitychina.cn`/`splash-ads.cdn.unity.cn`、vivo `open-ad.vivo.com.cn`、酷狗 `splashimgbssdl.yun.kugou.com`、HKTVmall `ad-splash(.tracking)`、Voodoo `splash-screen(.voodoo-ads.io)`、fancydsp、OpenADX/OpenADS 系、splash 垃圾 DSP）；③**厂商系统开屏与 MSN/Youku 专项 27 个**（小米国际 `ad.intl.xiaomi.com` 一条覆盖 api/zeus/diagnosis/sdkconfig 全系、小米印度 `sdkconfig.ad.india`、vivo `ad.vivo.com.cn`、荣耀 `ads.honor.com`/`ads-adnet-drcn.cloud`、华为中国 `adx-drcn.op.dbankcloud.cn`/`ad-drcn.media.dbankcloud(.ru|.cn)`、三星 `ads.samsung.com`、Realme/欧加 `sales-frontier.com`、当贝开屏 `zndsssp.dangbei.net`、优酷 SSP `yk-ssp.ad.youku.com`/`ad.youku.com`/`adx-open-service.youku.com`/`ad.api.3g.youku.com`、MSN `ads(.eu|1|2).msn.com`、`ads1|ads2.msads.net`、Google `ogads-pa.googleapis.com`/`mail-ads.google.com`、Yahoo `advertising.yahoo.com`、Betfair `ads.betfair.com`、travelaudience、a-ads.com）。④开屏聚合 SDK 与媒体素材专项 16 个（Sigmob `sigmob.cn/sigmob.com`、TopOn/AnyThink `anythinktech.com/toponad.com/toponad.net/selecttopon.com/toponadss.com/toponclick.com`、小米系统推广 `union.mi.com`、网易云开屏素材 `ads.music.126.net`/`admusicpic/iadmusicmat/iadmusicmatvideo.music.126.net`、网易广告 `pg-ad-b1/b2.ws.126.net`/`yt-adp.ws.126.net`、微软 `msads.net`/`msadsscale(.microsoft.com/.azureedge.net)`、`ad.sina.com.cn` 升级为通配覆盖 `img.amp.ad.sina.com.cn`）。⑤聚合/自有 DSP/生态广告专项 17 个（BidMachine `bidmachine.io`、Ogury `cloud.ogury.io`+`dsp-1.ogury.io`、Bidease、Appier RTB `appier.net`/`cr.adsappier.com`、优酷 `adx-core`/`cad`/`ipm.atm`/`apiv4-iyes`/`ad-feedback.youku.com`、美团自有 DSP `impdsp.meituan.com`/`mads.meituan.com`、360 生态 `ad.iot/jia/life/dev.360.cn`）。⑥媒体开屏运营位专项 15 个（神马/UC/夸克 `hc-ssp`/`huichuan(.mc)`/`image-ad`/`video-ad`/`c.sm.cn`/`adtrack` 系、铁路 12306 开屏 `ad.12306.cn`+网宿 CNAME 兜底、酷我 `mobilead.kuwo.cn`、芒果 TV `titan.mgtv.com`、腾讯音乐 TME `tmead(.comm).y.qq.com`）。核心广告组展开规则 679→1024 条，生效 Host 766→1111 条。
- **2.1.0**（2026-10-26）：审计补 23 个广告专用域（AdRoll、Adzerk、Index Exchange/indexww、Ad Alliance、Ad4Game、Admedo、Adcovery、E-Planning、AdScore、Innity、Zucks、Appodeal、BounceAds、PropellerClick、AdXpansion、DoublePimp、HyperBanner 等）；扩展 HTTPDNS IP 字面量 `URL-REGEX`（`/d?`、`/ss?`、`/vN/`、`sign_`）；修正 Facebook 登录说明。生效 Host 合计 766 条。
- **2.0.0**（2026-10-26）：合并为单插件。14 个核心广告组 / 633 条展开 Host；HTTPDNS 71 条；公共 DoH 16 条；生效 Host 合计 720 条；`[Rule]` 11 条 + 5 条默认注释；归因/统计 2 组 / 82 条默认注释；`[General]` 追加 IP 形式 DoH；移除独立 HTTPDNS/measurement/strict 文件与 MITM。
- **1.0.0**（2026-10-23）：旧的四文件版本（核心 / HTTPDNS / measurement / strict）。
