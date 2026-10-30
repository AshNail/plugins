# Loon 最大化配置（去广告优先）

> 目标不是「把所有开关都打开」，而是**让官方 26 个正文页的能力面都有归属**：
> 该默认开的默认开，该按需开的给出可复制模板，该判死的写清为什么，
> 平台不支持的明确标不适用。关键计数（台账五态、默认配置项、文档链接声明）
> 都由仓库脚本复算，而不是散文里的估计。

## 0. 先给结论

1. **去广告的主战场不在主配置，而在插件层**。`ads.plugin` 已经用 `[Host]`/`[Rule]`/`[General]`
   承担 DNS 黑洞、HTTPDNS 防绕过和公共 DoH 防泄漏；soda/douyin/13 个 App 插件承担
   MITM 后的路径级与字段级清理。主配置要做的，是**给这些插件创造不互相打架的前置条件**。
2. **本方案的主配置只加 10 个安全且必要的键**：IP 形式加密 DNS、53 端口劫持、
   DNS 阶段拒绝、`prefer-v4`、`real-ip`、私网绕过、853 端口阻断、`FINAL,DIRECT`。
   其余 General 键与主配置能力按需开启，默认注释。
3. **域名形式 `doh-server`/`doq-server` 是当前最大的自伤点**。2026-10-29 的 23 小时真机日志里，
   ads 插件的 28,547 次 `Host Map IP:127.0.0.1` 有 28,312 次（99.2%）打在 Loon 自己的
   加密 DNS 上；证据、计数与处置见 [`plugins/ads/README.md`](../plugins/ads/README.md) 的
   2.8.0 变更记录与 [`docs/loon-native-first.md`](loon-native-first.md) §9.15。因此本方案
   的 DoH/DoH3/DoQ 上游**一律要求 IP 形式**，并由 `tools/check-loon-config.py` 永久锁死。
4. **「100% 利用率」的诚实定义**：
   - 插件面：175 条能力，69 已用 / 40 可用未用 / 50 判死 / 12 不适用 / 4 未文档化，
     利用率 63.3%，见 [`docs/loon-coverage.md`](loon-coverage.md)。
   - 插件面之外：本文第 5 节 53 条台账（主配置/分发/插件专属），**53/53 有状态**。
   - 两张表视角不同、存在重叠；不把 175 和 53 相加冒充「228 项全部开启」。
     真正的目标是「零项无归属」，不是「所有开关都 ON」。
5. **规则与 Host 的底层语义单独立册**：官方 18 类规则、8 类 Host Map、ASN/GEOIP/CIDR
   的分工，以及 9 处官方未定义的规则/Host 交互，见
   [`docs/loon-routing-host-asn.md`](loon-routing-host-asn.md)。它是本台账已有条目的展开，
   不是第二套能力计数；`npm run check:config` 会逐类核对那两张矩阵是否齐全、分流配方
   是否恰好一条 `FINAL`，并拒绝括号不平衡的逻辑规则与 Host Map 非法右值。

### 0.1 三分钟上手

1. 把 [`examples/loon.conf`](../examples/loon.conf) 的 `[General]` 与 `[Rule]` **合并**进现有主配置
   （不要整份替换；没有代理需求就保留 `FINAL,DIRECT`）。
2. 用根 README 的按钮安装 `ads.plugin`；刷激励广告时停用它，避免奖励任务被 DNS 层拦死。
3. 需要证书级清理时再装 soda/douyin 或对应 App 插件；**一个 App 只装一个**，
   银行/微信/米家/京东/X/Instagram 不提供 MITM 层。

## 1. 底层：Loon 到底按什么顺序处理一个请求

理解顺序，才能知道每条规则该写在哪一层。

| 阶段 | 发生什么 | 官方依据 | 插件能不能做 |
|---|---|---|---|
| DNS | 先查 `[Host]`；未命中则并发查询已配置的 DoU/DoH/DoQ/DoH3；命中缓存直接用；加密 DNS 失败默认回落普通 DNS | DNS 页、Host Map 页 | 能（插件 `[General]` 白名单含 dns/doh/doq/doh3） |
| 域名拒绝 | `domain-reject-mode = DNS` 时，域名类 REJECT 在 DNS 阶段用 `dns-reject-mode` 指定应答（回环/空/NXDOMAIN） | 通用配置页 | 不能（插件白名单没有这两键） |
| MITM | 仅对 `[MITM] hostname` 命中的 HTTPS 解密；证书固定、mmtls 等仍看不见 | MitM 页 | 能，但公开插件不塞私钥 |
| Rewrite（request） | 在请求发出前改 URL/Header/Body；**在规则匹配前执行** | Rewrite v2 页 | 能 |
| Script（request） | 在请求发出前执行；Request Body Rewrite 或 Mock 命中时不再执行 Request Script | Script v2 页 | 能 |
| Rule | 域名规则先于 IP 规则；同来源按配置顺序；本地 > 插件 > 订阅；全部未命中走 `FINAL` | 规则页 | 能，但插件 `[Rule]` 不支持 `FINAL` |
| Policy / Node | 规则选中策略，策略决定最终节点 | 策略页、策略组页 | 不能（插件不建节点/组） |
| Rewrite / Script（response） | 收到响应头后执行；Response Body Rewrite 命中时不再执行 Response Script | Rewrite v2 页、Script v2 页 | 能 |

以上页面均来自官方文档站 <https://nsloon.app/docs/>；本仓库的 26 页清单与
拉丁 token 词表由 `npm run check:tokens` 双向自证，不是凭记忆列的。

三条对去广告最关键的推论：

- **DNS 层最便宜**：一次 `[Host]` 黑洞就能让请求根本不出网；但它只看得见域名，
  看不见 IP 直连和路径。
- **MITM 层最锋利也最贵**：能看路径和 JSON，但需要证书、会被证书固定挡住，
  还会把 QUIC 流量漏掉——所以 soda/douyin 用 `[Rule] PROTOCOL,QUIC,REJECT`
  把自家域名的 QUIC 逼回 TCP。
- **Rewrite 与 Script 是互斥关系，不是叠加关系**：请求体或响应体被 Rewrite 命中后，
  同阶段脚本不执行。不要把「字段级脚本」和「同 URL 的 JSON Rewrite」同时打开。

## 2. 基线配置：直接可合并的主配置

下面这份配置是 `examples/loon.conf` 的逐字副本，由
`tools/check-loon-config.py` 双向校验；改一处必须同时改另一边。

使用方式：**合并，不要整份替换**。它刻意不含节点、订阅和证书私钥，
`FINAL,DIRECT` 会让没有代理需求的设备直接以「去广告 + 直连」运行；
如果你已有 `[Proxy]`/`[Proxy Group]`，保留它们并把 `FINAL` 改成你的策略组。

<!-- base-config:start -->
```ini
# ============================================================================
# Loon 主配置 · 去广告优先（direct-only 基线）
# ----------------------------------------------------------------------------
# 用法：把需要的段落合并进你现有主配置，不要整份替换——这份文件刻意不含
# 节点、订阅、证书私钥，也不替你决定 [Proxy]/[Proxy Group]/FINAL 的代理策略。
# 语法来源：Loon 官方 26 个正文页；[Plugin] 行格式来自 Loon 官方 example.conf，
# 不在 26 页手册内，因此下面保持注释，默认用 URL Scheme/UI 安装插件。
# 目标：把「插件管不到、只能主配置做」的去广告前置条件全部配齐；
# 插件层见 plugins/ads/ads.plugin 与各 App 插件 README。
# ============================================================================

[General]
# --- DNS：加密优先，全部 IP 形式 -------------------------------------------
# 域名形式 doh-server/doq-server 会被 ads 插件的 [Host] 一起黑洞（2026-10-29
# 真机日志：28,547 次 Host Map 中 28,312 次是 Loon 自己的加密 DNS，占 99.2%）。
# 因此这里只写 IP 形式；Loon 会并发查询并采用最先返回的结果。
dns-server = 223.5.5.5,119.29.29.29,180.184.1.1
doh-server = https://223.5.5.5/dns-query,https://223.6.6.6/dns-query,https://1.12.12.12/dns-query
doh3-server = h3://223.5.5.5/dns-query,h3://223.6.6.6/dns-query
# DoQ 默认关闭：同窗口 5,239 次 DoQ 建立尝试中 5,236 次失败。
# 需要时改成 IP 形式再打开（官方 DNS 页写默认 853，通用配置页写 784，以服务端为准）：
# doq-server = quic://223.5.5.5:853

# --- DNS 防绕过：劫持 53 端口 + DNS 阶段拒绝 -------------------------------
# *:53 = 所有目标的 53 端口。局域网/公司 DNS 已在 bypass-tun 中绕过，不会进来。
hijack-dns = *:53
# 域名拒绝在 DNS 阶段完成，返回回环 IP，与 ads 插件的 127.0.0.1 黑洞语义一致。
domain-reject-mode = DNS
dns-reject-mode = LOOPBACKIP

# --- IP 栈：先 A 后 AAAA ----------------------------------------------------
# prefer-v4 不拒绝 IPv6；要彻底封死 AAAA 旁路可改 v4-only（IPv6-only 网络会断）。
ip-mode = prefer-v4
# ip-mode = v4-only

# --- 让 iCloud 等系统服务拿真实 IP，避免 Fake IP 被系统缓存 -----------------
# 不要顺手写 *.apple.com：它会连带放行 ca.iadsdk.apple.com 这类广告主机，
# 而 [Host] 与 real-ip 的先后顺序官方未定义。
real-ip = *.icloud.com

# --- 本地与私网绕过 TUN / HTTP Proxy ---------------------------------------
# 官方 example.conf 的私网全集 + localhost/*.local；局域网 DNS 因此不会被劫持。
bypass-tun = 10.0.0.0/8,100.64.0.0/10,127.0.0.0/8,169.254.0.0/16,172.16.0.0/12,192.0.0.0/24,192.0.2.0/24,192.88.99.0/24,192.168.0.0/16,198.18.0.0/15,198.51.100.0/24,203.0.113.0/24,224.0.0.0/4,255.255.255.255/32,localhost,*.local
skip-proxy = 10.0.0.0/8,127.0.0.0/8,172.16.0.0/12,192.168.0.0/16,localhost,*.local

# --- 以下全部按需开启，默认注释 ---------------------------------------------
# 禁止 443/80 走 UDP，QUIC 会回退 TCP；不会回退的业务会断，全局生效。
# disable-udp-ports = 443,80
# STUN 防 WebRTC IP 泄漏；会断部分语音/视频通话。
# disable-stun = true
# 节点不支持 UDP 时的兜底；REJECT 会断掉所有 UDP 业务，确认节点能力后再开。
# udp-fallback-mode = REJECT
# 把 Loon 变成局域网代理入口：扩大监听面，按需开启。
# allow-wifi-access = true
# wifi-access-http-port = 8899
# wifi-access-socks5-port = 8898
# 只有配置了节点/策略组才有意义。
# proxy-test-url = http://cp.cloudflare.com/generate_204
# internet-test-url = http://wifi.vivo.com.cn/generate_204
# test-timeout = 5
# 订阅需要格式转换时才需要；脚本是远程依赖，默认不引入。
# resource-parser = https://example.com/parser.js
# 按 Wi-Fi/蜂窝切换运行模式；PROXY 需要你已有名为 PROXY 的策略组。
# ssid-trigger = "loon-wifi5g":DIRECT,"cellular":PROXY,"default":RULE
# interface-mode = auto
# 仅 Loon Build 1007+（当前 App Store 3.5.2(996) 不识别：include-tun）。
# include-tun = 10.7.0.1/32
# ipv6-vif = auto
# 只有换数据库源时才需要；默认用 Loon 内置库。
# geoip-url = https://example.com/Country.mmdb
# ipasn-url = https://example.com/GeoLite2-ASN.mmdb

[Host]
# ads 插件已提供广告/HTTPDNS/公共 DoH 的黑洞，这里不要重复。
# 以下是官方支持、但当前去广告基线不需要的 Host Map 形态；
# 保留为语法模板，启用前把 example.com 换成你的真实域名。
# 固定 IPv4 / IPv6
# example.com = 192.0.2.10
# *.example.com = 192.0.2.10
# 域名别名
# cdn.example.com = origin.example.com
# 按域指定 DNS
# *.example.com = server:https://223.5.5.5/dns-query
# 按 SSID 指定 DNS
# ssid:Office-WiFi = server:system
# 按域指定 IP 栈
# example.com = ip-mode:prefer-v4
# IP 到 IP
# 198.51.100.10 = 192.0.2.20
# 代理内继续使用映射
# proxy-origin.example.com = 192.0.2.30,use-in-proxy=true

[Rule]
# 853 = 标准 DoT/DoQ。与 ads 插件同义：未装插件时也封住 App 自带加密 DNS。
# Loon 自己的 DoQ 不受该规则影响（2026-10-29 日志：规则在跑，DoQ 仍在重试）。
DEST-PORT,853,REJECT
# 可选：STUN 协议级拒绝；会断语音/视频通话。
# PROTOCOL,STUN,REJECT
# 可选：Loon 3.5.3(1008)+ 的动态广告子域；App Store 3.5.2 保持注释。
# DOMAIN-WILDCARD,ads.*,REJECT
# 其他规则形态模板（启用前确认策略名/网段/正则）：
# DOMAIN,example.com,DIRECT
# DOMAIN-SUFFIX,example.com,DIRECT
# DOMAIN-KEYWORD,example,DIRECT
# URL-REGEX,^http://example\.com,DIRECT
# USER-AGENT,Example*,DIRECT
# IP-CIDR,198.51.100.0/24,DIRECT,no-resolve
# IP-CIDR6,2001:db8::/32,DIRECT,no-resolve
# GEOIP,CN,DIRECT
# IP-ASN,4134,DIRECT,no-resolve
# AND,((DOMAIN-SUFFIX,example.com),(DEST-PORT,443)),DIRECT
# OR,((DOMAIN-SUFFIX,example.com),(DOMAIN-SUFFIX,example.org)),DIRECT
# NOT,((DOMAIN-SUFFIX,example.com)),DIRECT
# SRC-PORT,443,DIRECT
# 远程规则订阅（每行一个 URL + 策略）：
# https://example.com/rules.list,DIRECT
# 其他都未命中时直连；有代理时改成你的策略组名。
FINAL,DIRECT

# ============================================================================
# 可选段：按需取消注释。默认保持注释，避免把未验证的写法变成默认值。
# ============================================================================
# [MITM]
# hostname = example.com, *.example.org, -private.example.org
# 证书用 Loon 内置 CA 生成，不要把 ca-p12/ca-passphrase 写进公开配置。
#
# [Rewrite]
# request if ${url} ~= /^https:\/\/example\.com/ then request.header.set("X-Loon", "true")
#
# [Script]
# generic then script("scripts/loon-doctor.js") with tag="Loon Doctor"
#
# [Plugin]
# 官方 example.conf 的旧写法：URL,tag=...,enable=true。不在 26 页手册内，
# 真机确认可用前建议用 README 里的 URL Scheme/UI 安装。
# https://raw.githubusercontent.com/AshNail/plugins/main/plugins/ads/ads.plugin,tag=ads,enable=true
```
<!-- base-config:end -->

### 2.1 这 10 个默认键分别在做什么

| 键 | 作用 | 为什么默认开 | 风险/边界 |
|---|---|---|---|
| `dns-server` + `doh-server` + `doh3-server` | 具体 IP 的 DoU + DoH + DoH3，加密优先、并发取最快 | 不写 `system`，避免系统 DNS 把广告域解析回真实 IP；IP 形式避免被自己的 `[Host]` 黑洞 | 换网络后某个 IP 不可达时，Loon 会回落普通 DNS；可自行增删服务器 |
| `hijack-dns = *:53` | 劫持所有目标的 53 端口 UDP DNS，返回 Fake IP | 把 App 写死的 `8.8.8.8`/`114.114.114.114` 拉回 Loon；与 `bypass-tun` 配合，局域网 DNS 不受影响 | 公司/校园 DNS 若不在私网段，需在 `bypass-tun` 里补网段 |
| `domain-reject-mode = DNS` + `dns-reject-mode = LOOPBACKIP` | 域名类 REJECT 在 DNS 阶段返回回环 IP | 与 ads 插件的 `127.0.0.1` 黑洞语义一致；请求不出网 | 官方说明 HTTP Proxy/TUN 下仍可能有一部分请求走到转发阶段，所以插件层继续保留 `[Rule] REJECT` |
| `ip-mode = prefer-v4` | 有 A 用 A，没有 A 再用 AAAA | 不拒绝 IPv6，兼容 IPv6-only 网络；同时优先走 ads 插件能封的 IPv4 路径 | 不是 AAAA 的彻底封口；要彻底封口见 §3.4 的 `v4-only` |
| `real-ip = *.icloud.com` | 指定域名返回真实 IP，不用 Fake IP | iCloud 等系统服务会缓存 Fake IP，排除后减少「Loon 关了还连不上」 | 不要顺手写 `*.apple.com`：会连带放行 `ca.iadsdk.apple.com` 这类广告主机 |
| `bypass-tun` + `skip-proxy` | 私网、链路本地、`localhost`、`*.local` 绕过 TUN/HTTP Proxy | 局域网设备、路由器管理页、AirPlay/mDNS 不被代理；局域网 DNS 也不会被 `hijack-dns` 抓走 | 网段清单来自官方 example.conf；自定义内网段请自行补 |
| `DEST-PORT,853,REJECT` | 拒绝标准 DoT/DoQ 端口 | 封住 App 自带加密 DNS；与 ads 插件同义，未装插件时也生效 | 企业内网若用 853 做合法 DoT，需加例外；Loon 自己的 DoQ 不受该规则影响（真机日志已证） |
| `FINAL,DIRECT` | 未命中任何规则时直连 | 去广告基线不依赖代理；有节点时改成你的策略组 | 整份配置不含节点，导入后就是直连模式 |

### 2.2 为什么这里不重复 ads 插件的广告域名

`ads.plugin` 已经用 1,466 条生效 `[Host]`（exact + wildcard）覆盖广告专域、
HTTPDNS/私有 DoH、海外公共 DoH；主配置再写一遍只会制造两份会漂移的清单。
**本地规则优先于插件规则**，所以主配置只写「插件写不了」或「必须比插件更早」的项：

- 插件 `[General]` 白名单没有 `hijack-dns`、`domain-reject-mode`、`dns-reject-mode`、
  `disable-stun`、`disable-udp-ports`、`udp-fallback-mode`、`ip-mode`、`ssid-trigger`、
  `interface-mode`、`allow-wifi-access`、测速/数据库 URL——这些只能主配置做。
- 插件 `[Rule]` 不支持 `FINAL`，也不适合替用户决定 `FINAL` 走哪。
- 插件不应该替用户建节点、策略组、订阅。

## 3. 可选层：把剩下的主配置能力放回它们该在的场景

以下全部默认注释。开之前先读「代价」，不要因为「利用率高」就开。

### 3.1 节点、策略组、订阅（需要服务商）

官方 26 页只定义了节点协议/参数和策略组类型，**没有给 `[Proxy Group]` 的行语法**；
官方 `example.conf` 里有可用写法，但那是 2021 年的示例。最稳的做法仍然是
在 Loon UI 里建组，然后只把节点/订阅写进配置。下面只作语法参考：

```text
[Proxy]
# 节点名称 = 协议,服务器,端口,必填参数,可选参数
# 密码/路径含逗号时用双引号包住整个值
HK-01 = Shadowsocks,node.example.com,443,aes-128-gcm,"password",udp=true,fast-open=true,server-dns="223.5.5.5,https://223.5.5.5/dns-query"

[Proxy Group]
# 官方 example.conf 的写法：组名 = 类型,成员...,参数 = 值
PROXY = select,HK-01,DIRECT
Auto = url-test,HK-01,url = http://cp.cloudflare.com/generate_204,interval = 600,tolerance = 50
Fallback = fallback,HK-01,DIRECT,url = http://cp.cloudflare.com/generate_204,interval = 600,max-timeout = 3000
LB = load-balance,HK-01,DIRECT,url = http://cp.cloudflare.com/generate_204,interval = 600,algorithm = pcc,max-timeout = 3000
# example.conf 另有「按 Wi-Fi 选策略」的 ssid 组（正文未文档化，台账记 ⚪）：
# SSID = ssid, default = PROXY, cellular = DIRECT, "Office-WiFi" = DIRECT

[Remote Proxy]
# 订阅别名 = URL,参数...
MySub = https://example.com/subscription,enabled=true,udp=default,block-quic=default,fast-open=default,server-dns="223.5.5.5,https://223.5.5.5/dns-query"
```

要点：

- 官方节点协议共 12 类：Shadowsocks、ShadowsocksR、HTTP、HTTPS、SOCKS5、VMess、
  VLESS、Trojan、WireGuard、Hysteria2、AnyTLS、Custom by JavaScript。具体参数见
  官方 Node 页；不要从品牌名猜参数。
- 通用参数 `server-dns`/`ip-mode` 只影响**解析节点服务器域名**，不会替换全局 DNS。
  用 `server-dns` 后查询失败不会回落到 SSID/全局 DNS。
- 订阅可以整段下发 `[DNS]`/`[Host]`/`[Proxy]`；订阅 Host Map **优先于主配置**。
  这是排障顺序：插件 `[Host]` 某天不生效，先查订阅 Host Map，再怀疑正则。
- `skip-cert-verify=true` 会关闭证书校验，只应在你完全信任节点时使用；
  能用 `tls-cert-sha256`/`tls-pubkey-sha256` 固定指纹就不要关校验。
- 节点通用参数（官方 Node 页）：`server-dns`、`ip-mode`、`fast-open`、`udp`、
  `block-quic`、`skip-cert-verify`、`sni`、`tls-profile`、`tls-cert-sha256`、
  `tls-pubkey-sha256`。`udp=false` / `block-quic=true` 丢的是节点侧 UDP/QUIC，
  不是广告拦截开关；不要为了「多用一个参数」去关它们。
- 官方策略组页只列 `select`/`url-test`/`fallback`/`load-balance`；`example.conf`
  另有 `ssid` 组（按 Wi-Fi 选策略），正文未文档化，台账记 `⚪`，不建议作为默认。

### 3.2 局域网代理

```ini
# 把 Loon 变成局域网 HTTP/SOCKS5 代理入口
# allow-wifi-access = true
# wifi-access-http-port = 8899
# wifi-access-socks5-port = 8898
```

代价：扩大监听面；同网段设备都能用你的代理。只在需要时开，并给端口设一个
不冲突的值。与去广告无直接关系，属于「全功能」而非「必需」。

### 3.3 QUIC / STUN / UDP 兜底

```ini
# 全局把 QUIC 逼回 TCP：MITM 只能看见 TCP，开了脚本才能处理 QUIC 流量
# disable-udp-ports = 443,80
# 禁止 STUN，减少 WebRTC 真实 IP 泄漏；会断部分语音/视频通话
# disable-stun = true
# 节点不支持 UDP 时的兜底；REJECT 会断掉所有 UDP 业务
# udp-fallback-mode = REJECT
```

- soda/douyin 已经对**自家域名**写了 `PROTOCOL,QUIC,REJECT`，不需要全局开
  `disable-udp-ports`；全局开会波及所有 App 的 QUIC 业务。
- `PROTOCOL,STUN,REJECT` 与 `disable-stun = true` 二选一：前者是规则层，
  后者是主配置层；插件里只有前者可选（ads 可选组默认注释）。
- `udp-fallback-mode = REJECT` 只在「节点不支持 UDP」时有意义；直连基线用不到。

### 3.4 AAAA / IPv6 / include-tun

```ini
# 彻底不查 AAAA，并拒绝 IPv6 连接；IPv6-only 网络不要开
# ip-mode = v4-only
# 关闭 TUN 的 IPv6 地址（off/auto/always）
# ipv6-vif = off
# 让指定 IPv4 网段进入 TUN（Build 1007+；App Store 3.5.2(996) 不识别）
# include-tun = 10.7.0.1/32
```

`ip-mode = v4-only` 是当前唯一能彻底封死「AAAA 旁路」的主配置开关：
ads 插件的 `[Host]` 只映射 IPv4，`prefer-v4` 仍可能让 IPv6 路径漏过去。
但它会拒绝所有 IPv6 连接，属于全局取舍；先确认你的网络与常用 App 不依赖 IPv6。
`include-tun` 是 Build 1007+ 的主配置能力；`ipv6-vif` 在主配置长期可用，
只有「插件声明 off」需要 Build 1007+。两者都不进面向 3.5.2 的默认基线。

### 3.5 DoQ

```ini
# DoQ 默认关闭：2026-10-29 日志里 5,239 次建立尝试、5,236 次失败
# doq-server = quic://223.5.5.5:853
```

官方两页对默认端口的写法不一致：DNS 页写 853，通用配置页写 784。
以服务商实际端口为准；IP 形式是硬要求（域名形式会被 ads 插件黑洞）。

### 3.6 MITM 与主配置级 Rewrite / Script

插件自带 `[MITM]`（soda/douyin 及各 App 插件的可选增强层），主配置通常不需要再写。
只有当你确实要在主配置里做全局改写/脚本时，才加：

```ini
# [MITM]
# hostname = example.com, *.example.org, -private.example.org
# 证书用 Loon 内置 CA 生成；不要把 ca-p12/ca-passphrase 写进公开配置
#
# [Rewrite]
# request if ${url} ~= /^https:\/\/example\.com/ then request.header.set("X-Loon", "true")
#
# [Script]
# generic then script("scripts/loon-doctor.js") with tag="Loon Doctor", img_url="stethoscope"
```

边界：

- `[MITM]` 只对 HTTP/HTTPS 生效；证书固定的银行/微信/米家/京东/X/Instagram
  不要试图 MITM，插件层也明确不提供这些 App 的 MITM。
- 主配置 Rewrite 对**所有 App** 生效，写错一条会影响全机；能用插件做就别放主配置。
- 主配置 Script 的路径解析/远程加载依赖运行时；本仓库不把远程脚本作为默认值。
- `ca-p12`/`ca-passphrase` 是私钥与口令，公开配置一律不写；本仓库 lint 会拦。

### 3.7 `[Plugin]` 列表：官方示例有、26 页手册没有

官方 `example.conf` 里有 `[Plugin]` 段，行格式是 `URL,tag=...,enable=true`；
官方 Plugin 页只在讲 IP Rewrite 优先级时提到「顺序以主配置 `[Plugin]` 列表为准」，
没有给行语法。它可能随版本变化，所以本方案**默认用 README 里的 URL Scheme/UI 安装**，
`[Plugin]` 只作可选写法：

```text
[Plugin]
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/ads/ads.plugin,tag=ads,enable=true
```

真机确认你的 Loon 版本认这个段之后再启用；不认时它不会报错，只会静默不加载——
这正是「未文档化语法不能做默认值」的原因。

### 3.8 URL Scheme：快捷控制与导入

官方 Scheme 页定义的快捷操作：

| 操作 | URL |
|---|---|
| 开启/关闭 VPN | `loon://on` / `loon://off` |
| 编辑配置 | `loon://editconfig` |
| 全局直连/分流/全局代理 | `loon://flowmodel=direct` / `=filter` / `=proxy` |
| TUN Only / HTTP Proxy & TUN | `loon://proxymode=tun` / `=mix` |
| 更新所有订阅 | `loon://update?sub=all` |

导入资源共 7 类：`sub`、`nodelist`、`rules`、`plugin`、`iconset`、`geoip`、`parser`，
地址必须先 URL 编码；网页里打不开 `loon://` 时换成
`https://www.nsloon.com/openloon/` 同路径。本仓库 README 的导入按钮已按这套语法校验。

## 4. 与仓库插件的编排

| 层 | 插件 | 装不装 | 证书 | 与其它插件的关系 |
|---|---|---|---|---|
| DNS 底座 | [`ads`](../plugins/ads/README.md) | **默认装** | 不需要 | 与 soda/douyin 的激励广告互斥；刷奖励时禁用 |
| MITM 脚本 | [`soda`](../plugins/soda/README.md) / [`douyin`](../plugins/douyin/README.md) | 按需 | 需要 Loon 内置 CA | 与 ads 同时装时，ads 的 `[Host]` 先生效，脚本收不到这些广告域；两者只开一个 |
| App 专属 | [`meituan`](../plugins/meituan/README.md)、[`xianyu`](../plugins/xianyu/README.md)、[`qidian`](../plugins/qidian/README.md) 等 13 个 | 按 App 装 | 默认不需要；3 个带可选 MITM 增强层 | 一个 App 只装一个插件；域重叠是按 App 开关的分组语义 |
| 银行合集 | [`banks`](../plugins/banks/README.md) | 按需 | 不需要 | 6 款银行 App 合一个插件；证书固定/支付风控红线不提供 MITM |

编排顺序（按 Loon 的实际优先级，不是按安装顺序）：

1. **本地配置 > 插件 > 订阅**。所以主配置的 `DEST-PORT,853` 会先于插件同义规则执行；
   订阅里的 Host Map 会盖掉主配置——这是订阅优先于主配置的唯一例外，排障时先查它。
2. **ads 先于 App 插件生效**：ads 的 `[Host]` 在 DNS 阶段把广告域打到回环，
   App 插件的 MITM 脚本根本看不到这些请求。想让脚本处理某个域，就不要在 ads 里拦它，
   或者只开 App 插件、关 ads。
3. **soda/douyin 的传输层常开**：`[Rule] PROTOCOL,QUIC,REJECT` 把自家域名逼回 TCP，
   `[MITM]` 才能解密。它们不拦业务流量，只保证脚本看得见流量。
4. **证书固定 App 不 MITM**：银行/微信/米家/京东/X/Instagram 的插件只做 `[Host]`/`[Rule]`，
   这是能力边界，不是遗漏。

### 4.1 三档组合：按场景选，不按「全开」选

| 档位 | 组合 | 代价 | 适合 |
|---|---|---|---|
| A. 直连去广告（默认） | `examples/loon.conf` 原样 + `ads.plugin`；`FINAL,DIRECT`；DNS 全部 IP 形式 | 没有代理能力；853 端口与域名形式加密 DNS 被拒 | 只想干净上网、不需要节点的设备 |
| B. 代理 + 去广告 | A + `[Proxy]`/`[Proxy Group]`/`[Remote Proxy]`；`FINAL` 改成策略组；节点 `server-dns` 也用 IP 形式 | 策略组与节点由服务商决定；测速/订阅参数需自己维护 | 已有节点、希望分流与去广告共存 |
| C. 最大隔离（按需） | B + `ip-mode = v4-only` + `disable-stun = true` + `disable-udp-ports = 443`（或 `udp-fallback-mode = REJECT`） | 会断 IPv6-only 网络、部分语音/视频通话与 QUIC 业务；只适合能接受副作用的设备 | 安全优先、愿意逐项真机验证的用户 |

三档都必须保留 §2 的 DNS 基线。C 档不是「更高级」：它把更多全局连通性
拿来做交换，只有在你能逐项验证「断的是广告而不是业务」时才值得开。

## 5. 全量台账

两张表合起来覆盖官方 26 页：

- 插件面 175 条：见 [`docs/loon-coverage.md`](loon-coverage.md)，按「已用 / 可用未用 /
  判死 / 不适用 / 未文档化」五档，每条都有探测证据。
- 插件面之外 53 条（主配置/分发/插件专属）：下表。`✅` = 已用/默认开启，`🟡` = 按需模板（默认注释），
  `❌` = 判死/不采纳，`—` = 平台不适用，`⚪` = 官方 26 页查不到。
- 重叠项（9 个共享 `[General]` 键、`[MITM]`、`[IP Rewrite]`、旧版语法）在两张表里
  各自标注，不做「175+53=228 项全部开启」的虚假加法。

<!-- ledger:start -->
| # | 能力 | 归属 | 状态 | 说明 |
|---:|---|---|---|---|
| 1 | `include-tun` | 主配置 | 🟡 | Build 1007+；3.5.2(996) 不识别，默认注释 |
| 2 | `bypass-tun` | 共享 | ✅ | 私网/本地绕过 TUN，官方 example.conf 网段全集 |
| 3 | `skip-proxy` | 共享 | ✅ | 私网/本地绕过 HTTP Proxy |
| 4 | `dns-server` | 共享 | ✅ | 具体 IP 的 DoU，不写 `system` |
| 5 | `doh-server` | 共享 | ✅ | IP 形式 DoH，避免被 ads `[Host]` 黑洞 |
| 6 | `doq-server` | 共享 | 🟡 | 默认关；日志里 5,236/5,239 次失败 |
| 7 | `doh3-server` | 共享 | ✅ | IP 形式 DoH3 |
| 8 | `hijack-dns` | 主配置 | ✅ | 劫持 53 端口 UDP DNS，返回 Fake IP |
| 9 | `ip-mode` | 主配置 | ✅ | 基线 `prefer-v4`；`v4-only` 放可选层 |
| 10 | `ipv6-vif` | 共享 | 🟡 | 默认不写；需要时 off/auto/always |
| 11 | `allow-wifi-access` | 主配置 | 🟡 | 局域网代理入口，默认关 |
| 12 | `wifi-access-http-port` | 主配置 | 🟡 | 与 allow-wifi-access 成对 |
| 13 | `wifi-access-socks5-port` | 主配置 | 🟡 | 与 allow-wifi-access 成对 |
| 14 | `proxy-test-url` | 主配置 | 🟡 | 有节点/策略组才有意义 |
| 15 | `internet-test-url` | 主配置 | 🟡 | 默认值够用；可换直连可达 URL |
| 16 | `test-timeout` | 主配置 | 🟡 | 有测速需求再调 |
| 17 | `resource-parser` | 主配置 | 🟡 | 订阅格式转换时才需要 |
| 18 | `ssid-trigger` | 主配置 | 🟡 | 按 Wi-Fi/蜂窝切换模式 |
| 19 | `interface-mode` | 主配置 | 🟡 | auto/cellular/performance/balance |
| 20 | `real-ip` | 共享 | ✅ | 仅 `*.icloud.com`，避免 Fake IP 缓存 |
| 21 | `disable-udp-ports` | 主配置 | 🟡 | 全局 QUIC→TCP，影响面大 |
| 22 | `disable-stun` | 主配置 | 🟡 | 防 WebRTC 泄漏，会断通话 |
| 23 | `udp-fallback-mode` | 主配置 | 🟡 | 节点不支持 UDP 时的兜底 |
| 24 | `geoip-url` | 主配置 | 🟡 | 换 GeoIP 库才需要 |
| 25 | `ipasn-url` | 主配置 | 🟡 | 换 ASN 库才需要 |
| 26 | `domain-reject-mode` | 主配置 | ✅ | `DNS`，域名拒绝在 DNS 阶段完成 |
| 27 | `dns-reject-mode` | 主配置 | ✅ | `LOOPBACKIP`，与 127.0.0.1 黑洞一致 |
| 28 | `ipv6`（已弃用） | 主配置 | ❌ | 3.2.3(754) 起由 `ip-mode` 替代 |
| 29 | `switch-node-after-failure-times` | 主配置 | ❌ | Loon 已自动检测节点可用性 |
| 30 | `force-http-engine-hosts` | 主配置 | ❌ | 3.2.3(787) 起弃用 |
| 31 | `skip-first-packet` | 主配置 | ❌ | 3.5.0(968) 起由 Loon 自动识别 |
| 32 | `FINAL` | 主配置 | ✅ | 插件 `[Rule]` 不支持；基线 `DIRECT` |
| 33 | `PROCESS-NAME` | 主配置 | — | 仅 macOS 生效；iOS/tvOS 忽略 |
| 34 | `[Proxy]` 12 类协议 + 10 个通用参数 | 主配置 | 🟡 | 需服务商；参数清单与模板见 §3.1 |
| 35 | `select` 策略组 | 主配置 | 🟡 | 需节点；建议 UI 建组 |
| 36 | `url-test` 策略组 | 主配置 | 🟡 | `url`/`interval`/`tolerance` |
| 37 | `fallback` 策略组 | 主配置 | 🟡 | `url`/`interval`/`max-timeout` |
| 38 | `load-balance` 策略组 | 主配置 | 🟡 | `Random`/`PCC`/`Round-Robin` |
| 39 | `[Remote Proxy]` 订阅 | 主配置 | 🟡 | 12 个参数；可下发 `[DNS]`/`[Host]`/`[Proxy]` |
| 40 | 订阅规则（远程 `[Rule]` URL） | 主配置 | 🟡 | 官方 Rule/sub_rule 页有 URL 行写法；`[Remote Rule]` 段头与 `policy=/enabled=` 仅 example.conf，默认不引入远程列表 |
| 41 | `[Remote Rewrite]` | 主配置 | ⚪ | 仅官方 example.conf；26 页正文查不到，远程复写有供应链风险 |
| 42 | `[Remote Script]` | 主配置 | 🟡 | 官方 Script v2 页明列入适用来源；远程脚本有供应链风险，本方案默认只写本地脚本 |
| 43 | `[Remote Filter]` | 主配置 | ⚪ | 节点筛选功能在 Node/nodefilter 页以 UI 形式文档化，但 `[Remote Filter]` 段语法仅 example.conf |
| 44 | `[Plugin]` 列表 | 主配置 | 🟡 | Plugin 页只说明主配置 `[Plugin]` 列表决定插件顺序，行语法仅 example.conf；默认走 URL Scheme/UI |
| 45 | URL Scheme 控制 | 分发 | ✅ | on/off/editconfig/flowmodel/proxymode/update |
| 46 | URL Scheme 导入 7 类 | 分发 | ✅ | sub/nodelist/rules/plugin/iconset/geoip/parser |
| 47 | `[MITM] hostname` | 共享 | ✅ | 插件已用；支持 `*`/`?`/`-排除` |
| 48 | `[MITM] ca-p12`/`ca-passphrase` | 主配置 | ❌ | 公开配置不塞私钥/口令 |
| 49 | 旧版 Rewrite 语法 | 主配置 | ❌ | 官方定位「仅维护旧配置」，本仓全用 v2 |
| 50 | 旧版 Script 语法 | 主配置 | ❌ | 3.5.1(983) 起统一为 v2，不混用两套口径 |
| 51 | `[IP Rewrite]` | 插件 | 🟡 | 仅插件、Build 1007+；ads 默认注释 |
| 52 | `ssid` 策略组 | 主配置 | ⚪ | 仅官方 example.conf；策略组页只列 select/url-test/fallback/load-balance；按 Wi-Fi 选策略，与 `ssid-trigger` 切运行模式不同 |
| 53 | `[MITM] enable` | 主配置 | ⚪ | 仅官方 example.conf；MitM 页三参数表无此键；本方案不依赖，插件 lint 也不允许 |
<!-- ledger:end -->

<!-- ledger-count: 53 -->
<!-- ledger-counts: 14/27/7/1/4 -->

台账里最值得注意的不是「还有多少没开」，而是 4 条 `⚪`：
`[Remote Rewrite]`、`[Remote Filter]`、`ssid` 策略组与 `[MITM] enable` 只在官方
`example.conf` 出现，不在 26 页正文（节点筛选功能本身在 Node/nodefilter 页以 UI 形式文档化）。
另外三条曾疑似「未文档化」的经复核改判：`[Remote Script]` 在 Script v2 页明列为主配置来源；
远程规则在 Rule/sub_rule 页有 URL 行写法；`[Plugin]` 段在 Plugin 页被引用（但行语法仍未文档化）。
它们可能是历史写法、可能随版本失效；本方案不把它们作为默认值，也不假装它们「已支持」。

所以「100%」在本表里指 **53/53 有归属**，而不是 53 个开关全开：
27 条按需项多数需要节点、订阅或特定网络环境，7 条判死，1 条平台不适用，
4 条未文档化；默认开启率低是设计结果，不是未完成项。

## 6. 验证、判读与回滚

### 6.1 配置生效的日志签名

| 现象 | 说明 | 处置 |
|---|---|---|
| `Host Map IP:127.0.0.1` 高频出现，且主机是 `dns.alidns.com`/`doh.pub` | Loon 自己的加密 DNS 被 ads `[Host]` 黑洞 | 把主配置 DoH/DoQ 改 IP 形式；本方案已默认 IP 形式 |
| `Search rule by host` 里看不到 `doh.pub`/`dns.alidns.com` | Loon 自己的 DNS 查询可能不走 `[Rule]` | 不要把「封 Loon 自身 DoH」寄托在规则层 |
| `NGQUIC-CLOSE host=127.0.0.1` 高频 | DoQ 连接被本机回环关闭 | 同上；先查 `doq-server` 是否域名形式 |
| `[Rule]` 命中但请求仍出网 | 规则可能只在转发阶段生效，或域名已被订阅 Host Map 改解析 | 查 `domain-reject-mode`、订阅 Host Map、插件优先级 |
| MITM 脚本不执行 | 站点未被 `[MITM] hostname` 覆盖、QUIC 未回退、或证书未信任 | 查 hostname、`PROTOCOL,QUIC`、Loon 内置 CA 信任状态 |
| Rewrite 改了但脚本没跑 | 同阶段 Body Rewrite/Mock 命中会禁用 Script | 二选一，不要叠加 |

### 6.2 三步验证

1. **DNS**：装 ads 后访问一个已知广告域，确认日志出现 `Host Map IP:127.0.0.1`；
   再查 `dns.alidns.com`/`doh.pub` 是否**不再**出现在该日志里。
2. **规则**：在 Loon 请求记录里看 `DEST-PORT,853` 是否命中；用 `nslookup -port=853`
   或一个 DoT 客户端验证连接被拒。
3. **MITM（仅 soda/douyin/可选增强层）**：信任证书后打开目标 App，确认脚本日志出现
   自己的 tag；若没有，先查 QUIC 是否已回退、hostname 是否覆盖当前 API 域。

### 6.3 回滚

- 主配置：删除/注释本方案新增的 `[General]` 行与 `[Rule]` 行，恢复原 `FINAL`；
  Loon 重新加载配置即生效。
- 插件：在 Loon 插件页停用对应插件；`[Host]`/`[Rule]` 随插件停用一起撤销。
- MITM：停用插件里的 `[MITM]`/`[Rewrite]`/`[Script]` 段，或在 Loon 设置里撤销证书信任。
- 不要用「删配置重装」当回滚：先注释单行，才能定位是哪一条生效/失效。

## 7. 边界

- **不做广告欺诈**：不缩短广告时长、不伪造完成回调、不重复领奖、不提前调用发奖接口、
  不绕过服务端风控。`ads.plugin` 会同时拦掉激励广告，这是「去广告」与「保奖励」的
  固有权衡，不是 bug。
- **不 MITM 证书固定 App**：银行/微信/米家/京东/X/Instagram 的插件只做 DNS/规则层。
- **不在公开配置里放私钥**：`ca-p12`/`ca-passphrase` 一律不进仓库、不进示例。
- **不把未验证写法做默认值**：`[Plugin]`、`[Remote Rule]` 等只在官方 example.conf
  出现的写法，默认注释并标注取证状态；真机确认后再升级为默认。
- **不追求「全部开关 ON」**：`v4-only`、`disable-stun`、`disable-udp-ports`、
  `udp-fallback-mode=REJECT` 都会改变全局连通性；最大化利用率的正确形态是
  「每一项都有归属，默认值只开安全且普适的」。
