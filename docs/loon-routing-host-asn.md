# Loon 分流、Host 与 ASN 底层手册

> 这份手册只回答三个问题：一条请求在匹配规则前**被谁改写过地址**、规则引擎**按什么顺序比较**、
> 以及为什么同样写 `IP-ASN` 有时命中有时不命中。所有语法都能在官方 26 个正文页里找到出处；
> 官方没有写死的交互，统一放在 §7，不拿来当默认值。
>
> 本文的规则矩阵、Host 矩阵与分流模板由 `npm run check:config` 逐条解析；
> 规则类型数 / Host 映射类型数由 `<!-- routing-counts -->` 与检查器里的类型集合双向核对。

## 0. 先给结论

1. **规则不是一张平铺列表**。官方顺序是：域名规则先匹配；域名未命中才解析 DNS 并匹配 IP 规则；
   其他规则按配置顺序；同一来源内越靠前越优先；来源之间是本地 > 插件 > 订阅；最后才走 `FINAL`。
   所以一条 `IP-ASN`/`GEOIP` 规则**不能覆盖**已经命中的域名规则。
2. **Host Map 发生在规则之前**。它能把域名改成固定 IP、别名、指定 DNS 或指定 IP 栈；
   订阅下发的 Host Map 会合并并**优先于主配置**。规则看到的地址，可能已经不是 App 以为的那个。
3. **ASN 是 IP 规则，不是域名规则**。域名请求要匹配 `IP-ASN`/`GEOIP`，必须让 Loon 先解析 DNS；
   只有纯 IP 目标才适合加 `no-resolve`。广告拦截应继续用域名/Host 层，ASN 用于**分流路径**。
4. **全部规则类型和 Host 映射类型都有归属**：18 种规则类型（含 `FINAL`）与 8 种 Host Map 形态
   在 §3、§5 的矩阵里逐条出现，并由 `tools/check-loon-config.py` 校验；
   它们是既有台账的拆解，不是把能力总数再乘一遍。
5. **默认值仍然克制**：本文给的是语法与排序手册，可合并基线仍是
   [`examples/loon.conf`](../examples/loon.conf)；不会因为「利用率」把
   `PROCESS-NAME`、`DOMAIN-WILDCARD`、ASN 大网段全部打开。

## 1. 证据、目标版本与本文边界

- 规则语义来自官方正文页：`Rule` 与 9 个子页（domain/http/ip/logic/port/process/protocol/sub/final）、
  `DNS`、`DNS/hostmap`、`Node/subscription`、`General`、`Plugin`、`Script/script_api`。
- 目标仍是 App Store 的 Loon 3.5.2(996)：正文里标了更高 Build 的语法会单独注明，
  不会混进默认配置。当前基线的逐字副本见 [`docs/loon-max-config.md`](loon-max-config.md)。
- 本文只讨论**分流与地址映射**；MITM/Rewrite/Script 的请求改写顺序见
  [`docs/loon-max-config.md`](loon-max-config.md) §1。
- 广告侧的取舍见 [`plugins/ads/README.md`](../plugins/ads/README.md)：
  去广告用域名级 `[Host]`/`[Rule]`，不用 ASN/GEOIP 大网段。

## 2. 匹配前，地址已经被谁改过

### 2.0 在地址被改写之前：TUN 入口与 IP Rewrite

规则引擎并不是最早的裁决者。官方顺序是：

1. **系统路由先决定流量是否进入 TUN**。`bypass-tun` 让指定 IP 段/域名绕过 TUN；
   `include-tun`（Build 1007+）把指定 IPv4 网段拉进来。两者冲突时：网络地址和掩码完全相同，
   `include-tun` 优先；掩码不同，范围更小的路由优先；来自主配置还是插件不影响这个判定。
2. **进入 TUN 后，`[IP Rewrite]` 先于常规处理**。它只允许在插件中声明（主配置不支持），
   Build 1007+，按精确目的 IPv4 匹配，动作只有 `reflect`/`reject`/`drop`。命中后不再进入
   规则匹配、策略、HTTP Rewrite、脚本或 MitM，也不走代理、不转发出网。同一插件同地址取第一条；
   多个插件同地址取靠前的启用插件，顺序以主配置 `[Plugin]` 列表为准。
3. 只有没被 IP Rewrite 截走的流量，才进入下面的地址改写与第 3 节的规则匹配。

```text
# 插件内语法（官方示例；不是本仓库基线）
[IP Rewrite]
10.7.0.1 = reflect
10.7.0.2 = reject
10.7.0.3 = drop
```

对去广告的含义：`[IP Rewrite]` 是最早、最硬的拒绝层，但只能写精确 IPv4，广告端点又经常换 IP；
仓库因此不拿它枚举广告网段。它适合「已经拿到确切目的 IP、且必须在规则前截断」的场景，
不是域名拦截的替代品。

规则比较的是「当前目标地址」。在它之前，至少有六种机制会改变这个地址：

| 机制 | 官方行为 | 对规则的影响 |
|---|---|---|
| `[Host]` 固定 IP | 域名直接映射到 IPv4/IPv6，不再走普通 DNS | IP 规则看到映射后的 IP；广告域映射到回环后，IP 规则看到的是回环地址 |
| `[Host]` 域名别名 | 域名映射到另一个域名 | 最终解析取决于目标域名；**域名规则看到哪个名字官方未明说**，不要用别名做规则分流 |
| `[Host] server:` | 为域名/SSID 指定 DNS（`system`、IP 或 DoH/DoQ/DoH3 URL） | 解析结果来自指定 DNS；普通域名查询失败后是否回落官方未逐条说明，订阅节点解析的六层顺序见 §5.2 |
| `hijack-dns` | 劫持 UDP DNS 并返回 Fake IP（3.2.5(789)+） | 域名请求会拿到 Fake IP；**Fake IP 与 IP 规则如何交互官方未展开**，不要让 IP 规则承担域名分流的主判据 |
| `real-ip` | 指定域名返回真实 IP，不使用 Fake IP | 这些域名的 IP 规则看到真实地址；与 `[Host]` 的先后顺序官方未定义 |
| 普通 DNS / `ip-mode` | 按 `v4-only`/`dual`/`prefer-v4`/`prefer-v6`/`v6-only` 选 A/AAAA | 决定 IP 规则看到的是 IPv4 还是 IPv6 地址 |

官方匹配顺序可以写成四步：

1. 目标是域名时，先匹配**域名规则**（`DOMAIN*`；HTTP 规则只在 HTTP/HTTPS 上可见）。
2. 域名规则未命中，才解析 DNS 并匹配 **IP 规则**（`IP-CIDR`/`IP-CIDR6`/`GEOIP`/`IP-ASN`）。
3. 其他规则（端口、协议、进程、逻辑规则）按配置顺序匹配，越靠前优先级越高。
4. 全部未命中，使用 `FINAL`。

两条来源优先级必须同时记住：

- **同一来源内**：按配置顺序，没有「越精确越优先」的加分。
- **跨来源**：本地规则 > 插件规则 > 订阅规则。主配置里的一条 `DIRECT` 可以压过插件的 `REJECT`；
  订阅规则也压不过插件。

> 官方原文只写了「其他规则按配置顺序」，没有展开「其他规则」与 IP 规则交错时的精确相位。
> 需要跨类优先级时，用逻辑规则把条件写在一起，或在请求详情里复核，不要靠猜。

## 3. 18 种规则类型：语义、代价与版本门

### 3.1 逐类语义

| 类型 | 匹配对象 | 关键约束 | 官方代价/规模 | 放置建议 |
|---|---|---|---|---|
| `DOMAIN` | 完整域名 | 精确匹配；不触发 DNS | 20 万条 1 ms 内 | 已知主机名，优先 |
| `DOMAIN-SUFFIX` | 域名后缀 | `apple.com` 匹配 `icloud.apple.com`、`www.apple.com`，不匹配 `app-apple.com` | 20 万条 1 ms 内 | 域名族首选 |
| `DOMAIN-KEYWORD` | 域名中的关键词 | 随规则数与表达式变慢 | 官方明确会变慢 | 只在后缀写不出来时用 |
| `DOMAIN-WILDCARD` | 完整域名的 Glob | `*`/`?`/`[...]`；`*` 可跨 `.`；Build 1008+ | 5 万条约 0.031 ms 平均 | 当前 3.5.2(996) 不启用 |
| `URL-REGEX` | 请求 URL | **仅 HTTP/HTTPS**；正则复杂度影响耗时 | 随规则数/复杂度变慢 | 路径级清理，插件已用 |
| `USER-AGENT` | 请求 UA | **仅 HTTP/HTTPS**；通配符匹配 | 随规则数/复杂度变慢 | 粗粒度分流，别做广告主判据 |
| `IP-CIDR` | IPv4 网段 | 域名请求会先解析；纯 IP 目标建议 `no-resolve` | 10 万条 1 ms 内 | 精确端点/内网 |
| `IP-CIDR6` | IPv6 网段 | 同上；只接受 IPv6 | 4 千条 1–2 ms | IPv6 精确端点 |
| `GEOIP` | IP 的国家/地区 | 数据来自 MMDB；`geoip-url` 可换库 | 官方称受数量影响较小 | 国家级兜底 |
| `IP-ASN` | IP 所属 ASN | 域名请求会先解析；纯 IP 目标建议 `no-resolve` | 5 千条 1 ms 内 | 运营商/网络路径分流 |
| `SRC-PORT` | 源端口 | 单端口、闭区间、`>=`；3.1.7+ | 受数量影响较小 | 特殊入站/本机服务 |
| `DEST-PORT` | 目标端口 | 单端口、闭区间、`>=`；3.1.7+ | 受数量影响较小 | 封 DoT/特殊端口 |
| `PROTOCOL` | 协议类型 | `HTTP`/`HTTPS`/`TCP`/`QUIC`/`STUN`/`UDP`；3.1.7+ | 受数量影响较小 | 逼回 TCP、拒绝 STUN |
| `PROCESS-NAME` | 可执行文件名/路径 | **仅 macOS**；iOS/tvOS 忽略；含进程条件的整条逻辑规则也忽略 | 官方未给性能表 | 桌面端分流，不进移动默认 |
| `AND` | 所有子规则同时满足 | 3.1.7+；子规则写成 `((...),(...))` | 取决于子规则 | 域名 + 端口/地区组合 |
| `OR` | 任一子规则满足 | 3.1.7+；同上 | 取决于子规则 | 多域名/多条件合并 |
| `NOT` | 唯一子规则不满足 | 3.1.7+；只能一个子规则，可嵌套 | 取决于子规则 | 排除特定组合 |
| `FINAL` | 全部未命中 | 仅主配置；本仓库要求唯一且最后一条 | 不适用 | 兜底策略 |

`DOMAIN-WILDCARD` 的 Glob 细节（Build 1008+）：`*` 匹配零个或多个字符，并且可以跨越 `.`；
`.` 本身是普通字符，所以 `*.example.com` 能匹配 `a.example.com` 和 `a.b.example.com`，
但**不匹配裸 `example.com`**。`?` 恰好匹配一个字符；`[...]` 支持集合与范围，
`[!abc]`/`[^abc]` 表示排除。匹配不区分大小写。

`PROCESS-NAME` 有三种表达式形态：不以 `/` 开头按可执行文件名匹配（不区分大小写，支持通配）；
以 `/` 开头且不以 `/` 结尾按完整路径匹配（区分大小写，`*` 可跨越 `/`）；以 `/` 开头并以 `/`
结尾按目录前缀匹配。表达式含逗号时用双引号包围。仅 macOS 生效，iOS/tvOS 会忽略整条含进程条件的逻辑规则。

### 3.2 语法矩阵（逐条校验，不是推荐全部启用）

<!-- rule-matrix:start -->
```ini
[Rule]
# 域名类：不解析 DNS
DOMAIN,google.com,DIRECT
DOMAIN-SUFFIX,apple.com,DIRECT
DOMAIN-KEYWORD,apple,DIRECT
# Build 1008+；当前 3.5.2(996) 待支持
DOMAIN-WILDCARD,*.example.com,DIRECT
# HTTP/HTTPS 专用
URL-REGEX,^http://google\.com,DIRECT
USER-AGENT,Apple*,DIRECT
# IP 类：域名请求会先解析；纯 IP 目标加 no-resolve
IP-CIDR,118.89.204.198/32,DIRECT,no-resolve
IP-CIDR6,2402:4e00:1200:ed00:0:9089:6dac:96b6/128,DIRECT,no-resolve
GEOIP,CN,DIRECT
IP-ASN,4134,DIRECT,no-resolve
# 端口/协议：3.1.7+
SRC-PORT,443,DIRECT
DEST-PORT,80-443,DIRECT
DEST-PORT,>=443,DIRECT
PROTOCOL,STUN,REJECT
# 进程：仅 macOS；iOS/tvOS 整条忽略
PROCESS-NAME,curl,DIRECT
# 逻辑：子规则双括号；NOT 只能一个子规则
AND,((DOMAIN-SUFFIX,example.com),(DEST-PORT,443),(GEOIP,CN)),DIRECT
OR,((DOMAIN-SUFFIX,example.com),(DOMAIN-SUFFIX,example.org)),DIRECT
NOT,((AND,((DOMAIN-SUFFIX,example.com),(DEST-PORT,443)))),DIRECT
# 兜底：主配置最后一条
FINAL,DIRECT
```
<!-- rule-matrix:end -->

<!-- routing-counts: 18/8 -->

### 3.3 官方性能数字怎么读

`Rule` 页的真机数据（iPhone 15 Pro、Loon 3.2.0(712)）：

- `DOMAIN`/`DOMAIN-SUFFIX`：20 万条，1 ms 内；
- `IP-CIDR`：10 万条，1 ms 内；
- `IP-CIDR6`：4 千条，1–2 ms；
- `IP-ASN`：5 千条，1 ms 内；
- `GEOIP`、端口、协议规则：官方称受数量影响较小；
- `DOMAIN-WILDCARD`：5 万条，平均 0.031 ms、P95 0.061 ms、P99 0.110 ms
  （iPhone Air、iOS 27.0.1、Loon 3.5.3(1008)，Build 1008+）；
- `DOMAIN-KEYWORD`、`USER-AGENT`、`URL-REGEX`：随规则数量和表达式复杂度增加，官方建议优先用前一类。

这组数字的用途不是「把规则写满」，而是**排序依据**：能用后缀/网段解决的，不要升级成关键词/正则；
能把域名条件放前面的，不要让 IP 子规则先触发 DNS。

## 4. 排序与组合的 12 条硬规则

1. **域名规则先于 IP 规则**。域名规则命中后，IP 规则不再参与；`IP-ASN`/`GEOIP` 不能推翻它。
2. **同来源内按配置顺序**，没有「更精确优先」。需要例外就把例外写得**更靠前**。
3. **本地 > 插件 > 订阅**。主配置的 `DIRECT` 能压过插件 `REJECT`；插件压过订阅。
4. **`no-resolve` 只给纯 IP 目标**。它表示「只匹配目标地址已经是 IP 的请求，不为域名做 DNS」；
   给域名做 ASN/GEOIP/CIDR 分流时不要加，否则永远不命中域名请求。
5. **逻辑规则里 IP 子规则放后面**。官方原话：同时包含域名和 IP 子规则时，建议把 IP 规则放后面，
   减少不必要的 DNS 查询。
6. **`NOT` 只能一个子规则**，但子规则本身可以是嵌套的 `AND`/`OR`。
7. **端口/协议规则是 3.1.7+**；要和域名同时满足，就用逻辑规则组合，不要写成两条指望它们「与」。
8. **HTTP 规则看不见 QUIC**。`URL-REGEX`/`USER-AGENT` 只匹配 HTTP/HTTPS；要处理 QUIC，
   先按域名把 QUIC 逼回 TCP（插件里的 `PROTOCOL,QUIC,REJECT`），或接受这层盲区。
9. **进程规则只在 macOS 桌面场景有意义**：`PROCESS-NAME` 仅 macOS 生效；
   iOS/tvOS 会忽略它，含进程条件的整条逻辑规则也会被忽略。
10. **插件规则只能用 `DIRECT`/`REJECT` 系列/`PROXY`**；未写策略默认 `DIRECT`；
    `PROXY` 表示由用户选择策略组。插件不能写 `FINAL`，也不能引用自定义组名。
11. **`FINAL` 按定义兜底，本仓库要求唯一且放在最后一条**；它只属于主配置——插件规则策略白名单里没有它，写了无效。
12. **远程规则每行是 URL + 策略**；来源优先级仍是本地 > 插件 > 订阅。官方没有定义拉取失败时的行为，
    所以本仓库不把远程规则作为默认（见 [`docs/loon-max-config.md`](loon-max-config.md) 台账第 40 行）。

### 4.1 最常见的 8 个「写了但不命中」

| 写法/现象 | 根因 | 修正 |
|---|---|---|
| `IP-ASN,4134,DIRECT,no-resolve` 想命中域名请求 | `no-resolve` 只匹配已经是 IP 的目标 | 去掉 `no-resolve`，或改用域名规则 |
| 域名规则写了 `DIRECT`，ASN 规则仍想把它拉去代理 | 域名规则先匹配，IP 规则不再参与 | 把域名例外写得更靠前，或用逻辑规则 |
| 插件 `FINAL,PROXY` 不生效 | 插件规则策略白名单没有 `FINAL` | `FINAL` 只写主配置 |
| 插件规则引用自定义组名不生效 | 插件只能用 `DIRECT`/`REJECT` 系列/`PROXY` | 主配置建组，插件只写 `PROXY` |
| `URL-REGEX` 对 QUIC 流量不命中 | HTTP 规则只匹配 HTTP/HTTPS | 先按域名拒绝 QUIC，或接受盲区 |
| iOS 上 `PROCESS-NAME` 不生效 | 进程规则仅 macOS；整条逻辑规则被忽略 | 移动端不要用进程条件 |
| `DOMAIN-WILDCARD` 不生效 | 需要 Build 1008+；3.5.2(996) 不支持 | 用 `DOMAIN-SUFFIX`/`DOMAIN-KEYWORD` |
| `AND,((A),(B)),DIRECT` 不按预期组合 | 子规则列表必须写成双括号，官方形态是 `AND,((...),(...)),DIRECT` | 用本文矩阵的形态 |

## 5. Host Map：8 种映射与订阅 DNS 顺序

### 5.1 8 种官方形态

| 形态 | 官方例子 | 作用 |
|---|---|---|
| 域名 → IPv4 | `example.com = 192.0.2.10` | 固定 IPv4 |
| 域名 → IPv6 | `example.com = 2001:db8::10` | 固定 IPv6 |
| 域名别名 | `example.com = example.com.cn` | 域名映射到另一个域名 |
| 域名 → 指定 DNS | `*.testflight.apple.com = server:8.8.4.4` | 该域走指定 DNS；`system` 表示系统 DNS，也接受 DoH/DoQ/DoH3 URL |
| SSID → 指定 DNS | `ssid:Office-WiFi = server:system` | 按当前 Wi-Fi 选 DNS |
| 域名 → IP 栈 | `example.com = ip-mode:v4-only` | 该域使用指定 A/AAAA 策略 |
| IP → IP | `198.51.100.10 = 192.0.2.20` | 固定 IP 到 IP（常见于节点地址） |
| 代理内继续映射 | `proxy-origin.example.com = 192.0.2.30,use-in-proxy=true` | 映射在代理内继续生效 |

<!-- host-matrix:start -->
```ini
[Host]
example.com = 192.0.2.10
example.com = 2001:db8::10
example.com = example.com.cn
*.example.com = server:8.8.4.4
*.example.com = server:https://223.5.5.5/dns-query
*.example.com = server:quic://223.5.5.5
*.example.com = server:h3://223.5.5.5/dns-query
ssid:Office-WiFi = server:system
example.com = ip-mode:prefer-v4
198.51.100.10 = 192.0.2.20
proxy-origin.example.com = 192.0.2.30,use-in-proxy=true
```
<!-- host-matrix:end -->

> 上面的 `example.com` 重复出现是**语法矩阵**，不是一份可直接使用的 Host 表；
> 真实配置里同一域名只保留你确实需要的那一条。

### 5.2 订阅 Host Map 与节点 DNS

- 订阅文件可以整段下发 `[DNS]`/`[Host]`/`[Proxy]`；订阅 Host Map 会合并到当前 Host Map，
  并**优先于主配置**。排查「插件 Host 不生效」时，先看订阅是否覆盖了同名域。
- 订阅 Host Map 的域名键支持 `*` 和 `?` 通配符（`Node/subscription` 页）。
- 解析订阅节点的服务器域名时，官方给出的选择顺序是：
  1. 订阅文件 `[Host]` 的固定 IP/别名/指定 DNS/IP 栈；
  2. 主配置 `[Host]`；
  3. 主配置 `[Remote Proxy]` 为订阅手动设置的 `server-dns`；
  4. 订阅节点行里的 `server-dns`；
  5. 订阅文件 `[DNS]`；
  6. 当前 SSID DNS 和全局 DNS。
- 第 3、4 层的 `server-dns` 都要求 Loon 3.5.2(996) 及以上，正好是当前目标版本；
  更低版本只能用订阅 `[DNS]` 或 Host 映射。
- **一旦命中指定的节点 DNS，查询失败不会继续回落到下一层**。所以节点 DNS 写错时，
  表现为「节点全部超时」，而不是「自动回到全局 DNS」。

### 5.3 与去广告的直接关系

- 广告域在 `[Host]` 被映射到 `127.0.0.1` 后，后续 IP 规则看到的是回环地址；
  这时再去写 `IP-CIDR,127.0.0.0/8,...` 既没有必要，也容易误伤本机服务。
- 不要把 Loon 自己的全局 DoH/DoQ 域名写进 Host 黑洞：2026-10-29 的 23 小时日志里，
  99.2% 的 `Host Map IP:127.0.0.1` 打在 `dns.alidns.com`/`doh.pub` 上，属于插件把宿主 DNS 打死。
  证据与处置见 [`plugins/ads/README.md`](../plugins/ads/README.md) 2.8.0 与
  [`docs/loon-native-first.md`](loon-native-first.md) §9.15。
- `real-ip` 只给确实需要真实 IP 的系统服务（如 `*.icloud.com`）；不要顺手写 `*.apple.com`，
  否则会连带放行 `ca.iadsdk.apple.com` 这类广告主机。`real-ip` 与 `[Host]` 的先后官方未定义，
  同一域名不要同时依赖两者。

## 6. ASN、GEOIP 与 CIDR：怎么选

### 6.1 `IP-ASN` 的两种用法

```text
# 纯 IP 目标：加 no-resolve，避免为域名做无谓 DNS
IP-ASN,4134,DIRECT,no-resolve

# 域名目标：不加 no-resolve，让 Loon 先解析，再按 ASN 匹配
IP-ASN,4134,PROXY
```

`4134` 是官方 `Rule/ip_rule` 页的示例值；**本文不替它背书为某家运营商**。
把它替换成你用 `$utils.ipasn` 查到的实际 ASN。ASN 是 IP 所属网络/运营商的标识，
不是内容归属；共享 CDN/云厂商的 IP 可能服务很多不相关站点。

### 6.2 数据源与脚本接口

- `ipasn-url`：自定义 ASN 数据库下载地址，适用于 Loon 3.2.3(754) 及以上；只在主配置，
  插件 `[General]` 白名单没有它。
- `geoip-url`：自定义 GeoIP 数据库下载地址；同样只在主配置。
- 官方 Script API 提供两个同步查询（使用本地 ASN 数据库）：
  - `$utils.ipasn(ip)` → IP 对应的 ASN；
  - `$utils.ipaso(ip)` → IP 对应的自治系统组织名称。
- 两个接口和 `ipasn-url` 是否读同一份自定义库，官方没有明说；换库后要用脚本实测确认。

### 6.3 三种「按地址分流」的取舍

| 维度 | `IP-CIDR` | `GEOIP` | `IP-ASN` |
|---|---|---|---|
| 粒度 | 网段 | 国家/地区 | 网络/运营商 |
| 输入 | IP | IP | IP |
| 域名请求 | 先解析 DNS | 先解析 DNS | 先解析 DNS |
| 纯 IP 目标 | 可加 `no-resolve` | 可加 `no-resolve` | 可加 `no-resolve` |
| 数据源 | 规则自带 | 内置 MMDB；`geoip-url` 可换 | 内置 ASN 库；`ipasn-url` 可换 |
| 适合 | 精确端点、内网 | 「中国 IP 直连」这类国家级兜底 | 「某个网络单独走一条策略」 |
| 广告拦截 | 只适合有日志证据的精确端点 | 误伤面大，不用于广告 | 误伤面大，不用于广告 |
| 官方性能 | 10 万条 1 ms 内 | 受数量影响较小 | 5 千条 1 ms 内 |

### 6.4 一个可复制的分流骨架

<!-- routing-recipe:start -->
```ini
[Rule]
# 域名规则先判：明确的服务直连，后面的 IP 规则不能覆盖它
DOMAIN-SUFFIX,example.cn,DIRECT
# 域名未命中 → Loon 解析 DNS → 先匹配更具体的 ASN
IP-ASN,4134,PROXY
# 再按国家兜底
GEOIP,CN,DIRECT
# 其余走代理；PROXY 需替换成你已有的策略组名
FINAL,PROXY
```
<!-- routing-recipe:end -->

这段骨架演示的是**顺序**，不是推荐策略：

- `example.cn` 命中域名规则后，`IP-ASN`/`GEOIP` 都不会再评估；
- 其他域名解析后先看 ASN，再按国家兜底；
- 最后才 `FINAL`。如果你的 `FINAL` 是直连，把 `PROXY` 换回 `DIRECT` 即可。

同一顺序已经落成可导入的 `examples/loon-routing.conf`（direct-only 实验配置）：
它把所有策略写成 `DIRECT`，只用于在 Loon 日志里观察「域名 → 解析 → ASN → GEOIP → FINAL」
的命中顺序；`IP-ASN` 故意不带 `no-resolve`，否则域名请求永远不会命中这条演示规则。
日常配置仍以 `examples/loon.conf` 为准。

### 6.5 为什么不拿 ASN 去广告

ASN/GEOIP 描述的是**网络归属**，不是「这条请求是不是广告」。广告素材、统计、登录、支付可能共用
同一个云厂商或 CDN 的 ASN；按 ASN 拒绝会把正常业务一起打掉。仓库的广告插件因此坚持：

- 域名级 `[Host]`/`[Rule]` 黑洞；
- 有日志证据的精确 IP 端点；
- 不用大网段 GEOIP/IP-ASN 做广告拦截（见 `docs/loon-feature-checklist.md`
  「明确不采纳清单」中的 `GEOIP / IP-ASN 大网段` 一行）。

## 7. 官方没有写死的 9 处规则/Host 交互

这些不是「我觉得」，而是官方 26 页正文没有给出确定语义。本文不依赖它们做默认值：

1. 同一 Host 表里**精确键与通配键**谁优先；
2. 同一域名多行 Host 映射谁覆盖谁；
3. `[Host]` 与 `real-ip` 的先后；
4. 一行 Host 同时写固定 IP 和 `ip-mode:` 是否合法、谁生效（官方示例只单独使用）；
5. 域名别名后，域名规则看到的是原域名还是别名目标；
6. `hijack-dns` 返回的 Fake IP 与 IP 规则如何交互；
7. `use-in-proxy=true` 与别名/`server:` 组合时的行为（官方只给了固定 IP 示例）；
8. `DOMAIN-SUFFIX,apple.com` 是否匹配裸 `apple.com`（官方只列了子域例子）；
9. 「其他规则」与 IP 规则交错时的精确相位（官方只写「按配置顺序」）。

另有一处官方**文档自身不一致**：`DNS` 页注释写 DoQ 默认端口 853，示例却用 `:784`；
`General` 页写默认 784。需要 DoQ 时显式写端口，不要依赖默认值。

## 8. 排障：先问「哪一层没命中」

| 症状 | 先查什么 | 判读 |
|---|---|---|
| 域名规则命中，但最终仍走错策略 | 来源优先级 | 本地 > 插件 > 订阅；订阅 Host Map 还可能改了地址 |
| `IP-ASN`/`GEOIP` 对域名完全不命中 | 是否写了 `no-resolve` | 写了就只匹配纯 IP；去掉再试 |
| 域名规则没命中，IP 规则命中了 | 域名是否被 Host 改写成固定 IP/别名 | Host 先于规则；看请求详情里的实际目标 |
| 广告域已 REJECT，App 仍加载广告 | QUIC / 缓存 / 未知新域 | MITM 层需先逼回 TCP；DNS 缓存可能未过期；插件未覆盖的新域需补证据 |
| 插件 `[Host]` 不生效 | 订阅 Host Map | 订阅 Host Map 优先于主配置 |
| 节点域名解析失败 | 订阅/节点 `server-dns` | 命中指定 DNS 后失败不会回落下一层 |
| iOS 上进程规则没反应 | 平台 | `PROCESS-NAME` 仅 macOS；整条逻辑规则被忽略 |
| `DOMAIN-WILDCARD` 不生效 | Build | 需要 1008+；3.5.2(996) 不支持 |
| `FINAL` 不生效 | 位置/数量 | 只能一条、必须最后、只在主配置 |

请求详情里可以直接看到规则命中与耗时（官方 `Rule` 页说明缓存命中耗时接近 0 ms，
实际耗时会受设备状态与并发影响）。排障时先看「命中哪条」，再看「地址从哪来」，
最后才怀疑策略组/节点。

## 9. 与现有台账的关系

- 18 种规则类型和 8 种 Host 映射是**既有能力的拆解**，不是新增 26 条能力：
  它们分别落在 `docs/loon-max-config.md` 台账的 `FINAL`、`PROCESS-NAME`、`[Host]` 相关行、
  `ipasn-url`、远程规则等条目里。
- `npm run check:config` 现在同时校验：
  - `examples/loon.conf` 与 `docs/loon-max-config.md` 的基线围栏逐字一致；
  - 本文的规则矩阵覆盖全部 18 种规则类型；
  - 本文的 Host 矩阵覆盖全部 8 种 Host 映射类型；
  - 分流模板的 `FINAL` 唯一且最后；
  - `examples/loon-routing.conf` 的规则顺序（域名 → ASN → GEOIP → 端口 → `FINAL`）、
    `IP-ASN` 不带 `no-resolve`、`FINAL` 唯一且最后；
  - `routing-counts: 18/8` 与检查器类型集合一致。
- `npm run check:tokens` 继续要求矩阵里的每个语法 token 能在官方正文里查到；
  本轮把官方 `Node/subscription` 页补进 Host 词表，`use-in-proxy` 不再是「查不到的词」。

## 10. 边界

- **不做广告欺诈**：不缩短广告时长、不伪造完成回调、不重复领奖、不提前调用发奖接口、
  不绕过服务端风控。
- **不 MITM 证书固定 App**：银行/微信/米家/京东/X/Instagram 的插件只做 DNS/规则层。
- **不在公开配置里放私钥**：`ca-p12`/`ca-passphrase` 一律不进仓库、不进示例。
- **不把未验证写法做默认值**：本文 §7 的 9 件事没有被官方写死，就不写进基线。
- **不追求「全部开关 ON」**：ASN/GEOIP 用于分流，不用于广告；`PROCESS-NAME` 不进移动默认；
  `DOMAIN-WILDCARD` 等 Build 1008+ 能力不在 3.5.2 基线上假装可用。
