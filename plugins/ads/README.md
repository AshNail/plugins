# 广告平台拦截器 · All-in-One（单插件）

> **定位**：一个 `ads.plugin` 同时处理 **DNS 广告拦截 + HTTPDNS 防绕过 + 公共 DoH/DoT 防泄漏**。核心路径零证书、零 MITM、零脚本，HTTP/3 同样走 DNS 拦截。
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

要求 **Loon 3.5.1(983)+**（插件头与 `[General]`/`[Rule]` 语法）。安装后建议重连一次 Loon，让 DNS/DoH 配置生效。

### 真机验证清单

| 目标 | 操作 | 通过标准 |
|---|---|---|
| 核心广告拦截 | 找一个确认使用穿山甲/优量汇/快手/AdMob 广告的 App | 禁用插件后先确认广告会展示，再启用后广告消失 |
| HTTPDNS 防绕过 | 抓包或在 Loon 日志里筛 `httpdns`、`httpsdns`、`853` | 几乎无明文 HTTPDNS/DoT 请求；广告域名仍被拦 |
| 公共 DoH/DNS 防泄漏 | 对比插件启用/禁用，看是否还连 Google/Cloudflare/NextDNS 等公共 DoH | 启用时不连被拦的公共 DoH；`doh.dns.apple.com` 正常 |
| 误伤排查 | 某个 App 登录/正常功能异常 | 先禁用插件复现；再按“风险与误伤”表删对应行 |

> **第一优先**：刷奖励前临时禁用本插件，避免激励广告被拦导致奖励失败。

### 从旧版迁移

1. 在 Loon 里删除旧的 `ads-httpdns.plugin`、`ads-measurement.plugin`、`ads-strict.plugin`；仓库里的旧文件也已删除。
2. 重新导入新的 `ads.plugin`。
3. 如果旧版把公共 DoH 段保持注释，新版默认启用公共 DoH 拦截；先看下面的“DNS 防泄漏”与“风险”再决定是否保留。

---

## 一个插件里有什么

| 模块 | 当前内容 | 是否默认生效 |
|---|---|---:|
| `[Host]` 核心广告组 | 14 组、1056 条展开规则：穿山甲、优量汇、快手联盟、百度、阿里妈妈、中国联盟/监测、Google、Meta FAN、TikTok、手机厂商、全球 SDK、交易/SSP/DSP、广告效果监测、零售/CTV/音频、弹窗 | 是 |
| `[Host]` HTTPDNS 组 | 72 条：阿里云、腾讯、百度、字节、快手、B站、网易云音乐、美团、华为、小米、OPPO、vivo、荣耀、YY、讯飞、微博、京东、微信、爱奇艺等 | 是 |
| `[Host]` 公共 DoH 组 | 39 条：Google、Cloudflare/Quad9 各变体、NextDNS、OpenDNS、AdGuard 新旧域、CleanBrowsing、Mullvad、ControlD、Brave、AliDNS、DNSPod、360、dns.sb 等 | 是（见风险表） |
| `[Rule]` | 13 条：`httpdns`/`httpsdns` 关键词 (REJECT-DROP)、UA、IP 字面量 URL-REGEX、埋点上报特征 (REJECT-DICT)、853 端口 | 是 |
| `[General]` | 3 条：公共 DNS + IP 形式 DoH + IP 形式 DoH3 (HTTP/3) | 是 |
| `[Host]` 归因/统计组 | 2 组、72 条展开规则，默认整组注释 | **否** |
| `[Rule]` 可选组 | 28 条默认注释：27 条 HTTPDNS 网关 IP（`IP-CIDR/IP-CIDR6`，阿里内地+海外、腾讯、百度网关）+ `PROTOCOL,STUN,REJECT`（防 WebRTC 泄露；会断语音/视频通话） | **否** |
| `[IP Rewrite]` 可选组 | 16 条单 IPv4 HTTPDNS 网关接入点（Loon Build 1007+ 插件专属，TUN 阶段最快拦截），默认注释 | **否** |
| `[Rewrite]` / `[MITM]` / `[Script]` | 无 | 无证书、无 MITM、无脚本 |

合计：**18 组、1167 条生效 Host、72 条默认注释 Host、13 条生效 Rule、28 条默认注释 Rule、16 条默认注释 IP Rewrite**。

### 归因/统计组（默认关闭）

归因组：AppsFlyer、Adjust、Kochava、Singular、Tenjin、AppMetrica、mParticle、Amplitude、Flurry。
统计组：Google Analytics/Firebase、友盟、CNZZ、TalkingData、GrowingIO、神策、百度统计、Yandex、Pinterest、LinkedIn、Yahoo 等。

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

---

## 覆盖范围

### 核心广告组（14 组 / 1024 条展开）

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

### HTTPDNS / 公共 DoH（111 条展开）

- HTTPDNS/私有 DoH：`*.httpdns.aliyuncs.com`（含阿里《启动接入点》`resolvers-*` 域名兜底）、`httpdns.aliyuncs.com`、`httpdns.qq.com`、`httpdns.baidu.com`、`httpdns.volcengineapi.com`、`httpdns.pro`、`dns.weixin.qq.com`、`dns.jd.com`、`resolver.msg.xiaomi.net` 等 72 条。
- 公共 DoH：`dns.google`（+`dns64.dns.google`/`8888.google`）、`*.cloudflare-dns.com`（覆盖 security/family/dns64 等全部变体）+ `one.one.one.one`、Quad9 全变体（`dns[.9-12].quad9.net`）、`dns[1-3].nextdns.io`、`doh.opendns.com`、AdGuard 新旧域（`=adguard-dns.com` → `adguard-dns.com`+`*.adguard-dns.com` 覆盖 dns/family/unfiltered 变体 + 旧 `dns.adguard.com`）、`doh.cleanbrowsing.org`、Mullvad DoT 族（`dns.mullvad.net`+`*.doh.mullvad.net`）、`freedns.controld.com`、`doh.brave.com`、`dns.alidns.com`、DNSPod（`doh.pub`/`dns.pub`/`dot.pub`/`sm2.doh.pub`）、`doh.360.cn`/`dot.360.cn`、dns.sb（`doh.dns.sb`/`dot.sb`）共 39 条。
- 刻意不拦 `doh.dns.apple.com`，避免影响 iOS/macOS 系统解析。

---

## DNS 防泄漏

### 插件能做到什么

1. **追加公共 DNS 与 IP 形式 DoH**（`[General]`）：`dns-server` 写具体服务器，不写 `system`；`doh-server` 写 IP，避免 Loon 解析 DoH 域名时被本插件的 Host 规则打断。Loon 同时配置常规 DNS 与加密 DNS 时，会优先使用加密 DNS。
2. **封住已知 HTTPDNS/私有 DoH 域名**（`[Host]`）：强制 App 回退到系统 DNS（Loon）。
3. **封住公共 DoH 入口**（`[Host]`）：浏览器/App 的 DoH 解析失败后通常回退系统 DNS，广告域继续被 `[Host]` 拦截。
4. **封住 853 端口**（`[Rule] DEST-PORT,853,REJECT`）：阻断标准 DoT/DoQ，减少 App 自带加密 DNS 绕过。
5. **未知 HTTPDNS 兜底**（`[Rule]`）：`DOMAIN-KEYWORD,httpdns` / `httpsdns`、`USER-AGENT`、IP 字面量 `URL-REGEX`。

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
- 主配置里的 `doh-server` 如果原本是域名形式，比如 `https://doh.pub/dns-query`，请改成 IP 形式，或注释本插件公共 DoH 组里的对应行；否则可能出现“Loon 自己的 DoH 域名被 Host 拦掉”的情况。
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
| 公共 DoH | 1.1.1.1/WARP、Chrome/Firefox 安全 DNS、部分浏览器可能提示 DNS 失败 | 注释公共 DoH 组对应行，或把 Loon 上游改成 IP DoH |
| 853 端口 | 使用标准 DoT/DoQ 的 App 会被断 | 删除 `DEST-PORT,853,REJECT` |
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
2. 读取 `ads.plugin` 中**未注释**的 `[Host]` 规则，计算覆盖率；默认注释的归因/统计组单独标出，`--include-disabled` 才会把它们计入覆盖率；
3. 输出覆盖率、Top 未覆盖候选、已失效/未命中规则、共享主域通配违规；
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
- `rules_disabled`：默认注释的可选 Rule；build 会加 `# `，不参与匹配。
- `groups[].disabled`：Host 组默认注释；归因/统计组用它实现“单文件、默认不生效”。

### 加规则的原则

1. **广告专域才用 `=`（apex + `*.`）**：例如 `=applovin.com`、`=doubleclick.net`。
2. **共享域只写精确子域**：例如 `ad.zijieapi.com`、`gdt.qq.com`、`ads.pinterest.com`；不要写 `*.qq.com`、`*.google.com`。
3. **先有证据再加**：至少一个上游清单或真实抓包/页面请求；不要凭“看起来像广告”整域封。
4. **宁缺毋滥**：拿不准的域名放审计报告里观察，不要直接进核心。
5. **同一条规则只能出现一次**：build 会跨组查重，重复会直接失败。
6. **HTTPDNS 域名是“强制回退”，不是“广告专域”**：加之前确认该 App 有系统 DNS 回退，或接受可能断网。

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

**Q：插件里的 `[Rule]` 禁用插件后还会生效吗？**
`[Rule]` 是插件配置的一部分，禁用插件后不会再从该插件加载；但 Loon 本地规则优先于插件规则。如果你曾把同样的规则手工复制到主配置或本地规则，那部分当然不会随插件撤销。

**Q：装了 `ads.plugin` 后某个 App 白屏/登录失败？**
先禁用 `ads.plugin` 复现；如果恢复，说明该 App 把广告/HTTPDNS 域和核心 API 混在同一个域。把 App 名和抓到的域名发 issue，不要直接整域放开共享主域。

**Q：公共 DoH 拦截后浏览器打不开网页？**
确认 Loon 的 `doh-server` 是 IP 形式，或注释公共 DoH 组里的对应行；`doh.dns.apple.com` 已刻意不拦。若只用 IPv6 或本地 DNS，先测试再启用。

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

- **2.1.4**（2026-10-26）：深化 Loon 现代能力与埋点/遥测拦截。①HTTPDNS 关键词规则采用 `REJECT-DROP`（丢包无回复），防止客户端 SDK 在收到空 200 包后频繁秒级重试造成网络风暴；②新增针对第三方统计与埋点 SDK（如神策）的 `REJECT-DICT` 规则（返回 200 + `{}` 空字典），诱导客户端主动清空本地重试队列（`deleteEvents`），彻底避免本地存储膨胀与无线电唤醒；③提拔纯广告效果监测专域（`coremetrics.com`、`sumome.com`、`insightexpressai.com`、`blueconic.net`、`pixel.watch`）至核心生效层，生效 Host 升至 1155 条、生效 Rule 升至 13 条；④构建工具原生支持 Loon Build 1007+ 插件专属的 `[IP Rewrite]` 语法（单 IPv4 / 严格查重 / 保护名单安全防护），并在可选层收录 16 条单 IPv4 HTTPDNS 网关接入点，可在 TUN 阶段最快阻断。
- **2.1.3**（2026-10-26）：可选 `[Rule]` 组接入 Loon 3.1.7+ 的 `PROTOCOL` 协议规则，新增 `PROTOCOL,STUN,REJECT`（协议级阻断 STUN，防 WebRTC 真实 IP 泄露；会断部分 App 的语音/视频通话，默认注释；主配置更优解 `disable-stun = true`）。默认注释 Rule 合计 27→28 条。功能盘点见 [`docs/loon-feature-checklist.md`](../../docs/loon-feature-checklist.md)。
- **2.1.2**（2026-10-26）：全网取证强化 DNS 层。①公共 DoH 组 16→39 条：补 AdGuard 新域 `dns.adguard-dns.com`（`=adguard-dns.com` 展开覆盖 dns/family/unfiltered 变体——官方文档 DoQ 示例即用此域；旧域 `dns.adguard.com` 保留）、`*.cloudflare-dns.com` 通配 + `one.one.one.one`/`dns.cloudflare.com`、Quad9 全变体、NextDNS DoT 节点 `dns1-3.nextdns.io`、DNSPod `dns.pub`/`dot.pub`/`sm2.doh.pub`、`dot.360.cn`、`dns64.dns.google`/`8888.google`、dns.sb（`doh.dns.sb`/`dot.sb`）、Mullvad DoT 族、ControlD `freedns.controld.com`；来源 curl wiki 公共 DoH 清单、AdGuard DNS KB、DNSPod 官方文档。②HTTPDNS 组补 `*.httpdns.aliyuncs.com`（覆盖阿里《启动接入点》`resolvers-cn/hk/sg/us/de` 域名兜底）。③可选 HTTPDNS 网关 IP 组 5→27 条：新增阿里内地接入点 `203.119.238.240`/`106.11.25.239`/`59.82.99.47` 与 4 个 IPv6 接入点、海外接入点（香港/新加坡/美洲/欧洲 IPv4 ×8 + IPv6 ×6，与阿里云海外 CDN 网段相邻已加风险注释）、腾讯企业版 `43.132.43.43`/`43.132.55.55`；删除笔误 IP `186.76.76.200`（百度官方文档任何版本都只有 `180.76.76.200`），lint 永久锁掉并新增 `119.29.29.29`（本插件 dns-server）禁拦保护；依据阿里云 doc 2868011、腾讯云 doc 379/59133、百度智能云《访问入口》。生效 Host 合计 1135 条（exact 694 / wildcard 441）。
- **2.1.1**（2026-10-26）：继续扩展主流覆盖，三轮合计新增 138 个广告专用域（+250 条展开规则）。①移动 SDK/交易生态 79 个（applvn、inmobicdn、tapjoyads、mobfox/mobclix、adtrue、adspredictiv、adbutler、adsupply、IAS adsafeprotected、AOL adtechus、adsinteractive、adsniper.ru、doubleclick.com、adsense.com 等）；②**开屏专项 32 个**（小红书 `*.ads-splash-*.xhscdn.com` + `splash-online-decision.xiaohongshu.com`、Unity 中国 `splash-ads.unitychina.cn`/`splash-ads.cdn.unity.cn`、vivo `open-ad.vivo.com.cn`、酷狗 `splashimgbssdl.yun.kugou.com`、HKTVmall `ad-splash(.tracking)`、Voodoo `splash-screen(.voodoo-ads.io)`、fancydsp、OpenADX/OpenADS 系、splash 垃圾 DSP）；③**厂商系统开屏与 MSN/Youku 专项 27 个**（小米国际 `ad.intl.xiaomi.com` 一条覆盖 api/zeus/diagnosis/sdkconfig 全系、小米印度 `sdkconfig.ad.india`、vivo `ad.vivo.com.cn`、荣耀 `ads.honor.com`/`ads-adnet-drcn.cloud`、华为中国 `adx-drcn.op.dbankcloud.cn`/`ad-drcn.media.dbankcloud(.ru|.cn)`、三星 `ads.samsung.com`、Realme/欧加 `sales-frontier.com`、当贝开屏 `zndsssp.dangbei.net`、优酷 SSP `yk-ssp.ad.youku.com`/`ad.youku.com`/`adx-open-service.youku.com`/`ad.api.3g.youku.com`、MSN `ads(.eu|1|2).msn.com`、`ads1|ads2.msads.net`、Google `ogads-pa.googleapis.com`/`mail-ads.google.com`、Yahoo `advertising.yahoo.com`、Betfair `ads.betfair.com`、travelaudience、a-ads.com）。④开屏聚合 SDK 与媒体素材专项 16 个（Sigmob `sigmob.cn/sigmob.com`、TopOn/AnyThink `anythinktech.com/toponad.com/toponad.net/selecttopon.com/toponadss.com/toponclick.com`、小米系统推广 `union.mi.com`、网易云开屏素材 `ads.music.126.net`/`admusicpic/iadmusicmat/iadmusicmatvideo.music.126.net`、网易广告 `pg-ad-b1/b2.ws.126.net`/`yt-adp.ws.126.net`、微软 `msads.net`/`msadsscale(.microsoft.com/.azureedge.net)`、`ad.sina.com.cn` 升级为通配覆盖 `img.amp.ad.sina.com.cn`）。⑤聚合/自有 DSP/生态广告专项 17 个（BidMachine `bidmachine.io`、Ogury `cloud.ogury.io`+`dsp-1.ogury.io`、Bidease、Appier RTB `appier.net`/`cr.adsappier.com`、优酷 `adx-core`/`cad`/`ipm.atm`/`apiv4-iyes`/`ad-feedback.youku.com`、美团自有 DSP `impdsp.meituan.com`/`mads.meituan.com`、360 生态 `ad.iot/jia/life/dev.360.cn`）。⑥媒体开屏运营位专项 15 个（神马/UC/夸克 `hc-ssp`/`huichuan(.mc)`/`image-ad`/`video-ad`/`c.sm.cn`/`adtrack` 系、铁路 12306 开屏 `ad.12306.cn`+网宿 CNAME 兜底、酷我 `mobilead.kuwo.cn`、芒果 TV `titan.mgtv.com`、腾讯音乐 TME `tmead(.comm).y.qq.com`）。核心广告组展开规则 679→1024 条，生效 Host 766→1111 条。
- **2.1.0**（2026-10-26）：审计补 23 个广告专用域（AdRoll、Adzerk、Index Exchange/indexww、Ad Alliance、Ad4Game、Admedo、Adcovery、E-Planning、AdScore、Innity、Zucks、Appodeal、BounceAds、PropellerClick、AdXpansion、DoublePimp、HyperBanner 等）；扩展 HTTPDNS IP 字面量 `URL-REGEX`（`/d?`、`/ss?`、`/vN/`、`sign_`）；修正 Facebook 登录说明。生效 Host 合计 766 条。
- **2.0.0**（2026-10-26）：合并为单插件。14 个核心广告组 / 633 条展开 Host；HTTPDNS 71 条；公共 DoH 16 条；生效 Host 合计 720 条；`[Rule]` 11 条 + 5 条默认注释；归因/统计 2 组 / 82 条默认注释；`[General]` 追加 IP 形式 DoH；移除独立 HTTPDNS/measurement/strict 文件与 MITM。
- **1.0.0**（2026-10-23）：旧的四文件版本（核心 / HTTPDNS / measurement / strict）。
