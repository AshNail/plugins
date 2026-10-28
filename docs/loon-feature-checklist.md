# Loon 全功能清单（本仓库视角）

> 依据：官方文档 `https://nsloon.app/docs/`（源仓库 [Loon0x00/LoonManual](https://github.com/Loon0x00/LoonManual) `docs/cn/`，2026-10-27 逐页核对）。
> 图例：✅ 本仓库已在用 / 🟡 建议你在设备侧开启 / ⚪ 进阶可选 / 🔒 需真机取证后启用 / ❌ 不采纳（带理由）。
> 适用版本：主配置按当前 stable 功能描述；标注 build 号的是硬门槛（soda/douyin 标注 3.5.1(983)+，gzip 响应解析需 3.5.1(988)+；ads 与全部 App 插件门槛降到 App Store 正式版 **3.5.2(996)**，`DOMAIN-WILDCARD` 仅 TF 3.5.3(1008) 有、改为默认注释层）。

## 1. 导入与快捷指令（docs/cn/scheme.md）

全部 `loon://` scheme 与对应**通用链接**（网页可点，Loon 官方注册了 `www.nsloon.com/openloon/*` 的 Universal Link，AASA 已验证）：

| 用途 | loon:// | 通用链接 |
|---|---|---|
| 开/关 VPN | `loon://on` / `loon://off` | `https://www.nsloon.com/openloon/on`（off 同理） |
| 编辑配置文件 | `loon://editconfig` | `…/openloon/editconfig` |
| 切流量模式 | `loon://flowmodel=direct`（filter / proxy） | `…/openloon/flowmodel=…` |
| 切代理模式 | `loon://proxymode=tun`（mix） | `…/openloon/proxymode=…` |
| 导入订阅/节点/规则/**插件**/图标集/geoip/解析器 | `loon://import?plugin=encode(url)` 等 6 种 | `…/openloon/import?...` |
| 更新全部订阅 | `loon://update?sub=all` | `…/openloon/update?sub=all` |

- ✅ 仓库 README 三个导入按钮用 `openloon/import`（Safari 直接跳 Loon；`loon://` 只作复制备用）。
- 🟡 **iOS 快捷指令**绑定 `loon://off`（一键全关）与 `loon://update?sub=all`（出门前更新）。
- 🟡 `loon://editconfig` 加到主屏：主配置加固改起来快。

## 2. 主配置 `[General]` 全键（docs/cn/general.md）

| 键 | 作用 | 建议 |
|---|---|---|
| `dns-server` | UDP 解析，`system` 表示系统 DNS | ✅ 插件已带（223.5.5.5 等） |
| `doh-server` / `doq-server` / `doh3-server` | DoH / DoQ(默认端口 784, `quic://`) / DoH3(`h3://`) | 🟡 doh 已用；doq/doh3 🔒 见第 10 节 |
| `real-ip` | FakeIP 缓存导致关闭 Loon 后仍打假 IP 的域，返回真 IP | 🟡 `*.apple.com,*.icloud.com` |
| `disable-stun` | 禁 STUN 的 UDP，防 WebRTC 泄露 | 🟡 `true`（比插件 `PROTOCOL,STUN` 规则更稳） |
| `disable-udp-ports` | 禁指定 UDP 端口 | ⚪ 按需（会伤游戏/hole-punching） |
| `force-http-engine-hosts` | 对非 80 端口的裸 TCP-HTTP 强制走引擎解析 | ⚪ 抓包时临时用（配 `:0` 全端口） |
| `bypass-tun` / `skip-proxy` | TUN/HTTP 代理两层各自的直连例外 | 🟡 局域网段 +  printers/nas |
| `ssid-trigger` | 按 WiFi/蜂窝切流量模式（direct/proxy/filter） | ⚪ `"home-wifi":DIRECT,"cellular":PROXY,"default":RULE` |
| `interface-mode` | Auto/Cellular/Performance/Balance 出网接口 | ⚪ 双 WAN 用户 |
| `allow-wifi-access` + `wifi-access-http-port`/`socks5-port` | 局域网代理共享 | ⚪ 给同网段设备 |
| `proxy-test-url` / `internet-test-url` / `test-timeout` / `switch-node-after-failure-times` | 测速与容错 | 🟡 204 系链接，超时 5s |
| `resource-parser` | 订阅解析器（Sub-Store） | ⚪ 有机场订阅时 |
| `geoip-url` | 自定义 mmdb 位置 | ⚪ IP-ASN/GEOIP 用得多时 |
| `ipv6` / `ipv6-vif` | AAAA 查询与 vif 开关 | ❌ 与拦截无关，AAAA 会拉长解析链 |
| `include-tun`（插件） | TUN 模式接管 | ❌ 插件白名单内可声明但与拦截无关 |

🟡 **必开搭档**（DNS 页/常识，与 ads 插件互补，防止规则引擎抢跑）：
`domain-reject-mode = DNS`（DNS 阶段拒绝——**这是 `pre-matching` 在 Loon 里的真正替代物**，且只能在主配置声明）、`dns-reject-mode`（让被 DNS 拒的域不再更名重试）。

## 3. DNS 面板与解析（dns.md / hostmap.md）

- ✅ `[Host]` 域名映射（ads 用 127.0.0.1 黑洞）；本仓库构建器速记 `=` → 域 + `*.域`（不是 Loon 语法，由 `tools/build-ads.py` 展开）。
- ✅ IP 形式 DoH（`https://223.5.5.5/dns-query`）——插件 [General]。**官方 Plugin 文档列明插件 [General] 可用键**：`bypass-tun` / `include-tun` / `skip-proxy` / `real-ip` / `dns-server` / `doh-server` / `doq-server` / `doh3-server` / `ipv6-vif`（第十二轮复核，此前 raw 模板只列 4 键造成歧义）。
- ✅ `h3://223.5.5.5/dns-query`（DoH3）已随 ads v2.7.0 声明；真机在 Loon DNS 页确认显示即生效。
- ⚪ DoT 域名形式 `tls://` 与 IP 形式取舍：插件防泄漏名单已拦公共 DoH 入口域名。

## 4. 规则类型全集（rule.md + 7 个细分页）

| 组 | 类型 | 本仓库 |
|---|---|---|
| 域名 | `DOMAIN` `DOMAIN-SUFFIX` `DOMAIN-KEYWORD` | ✅ KEYWORD 兜底；`DOMAIN` 在 soda/douyin 可选组 |
| 域名通配 | `DOMAIN-WILDCARD`（Build 1008+，glob：`*` 跨点、`?` 单字符、`[0-9]` 字符类） | ⚠️ 收录但**默认注释**（仅 TF 3.5.3 支持，App Store 3.5.2 解析行为未文档化）：ads 30 条广告子域通配层 + 11 条数字分片家族层以 `# DOMAIN-WILDCARD,...` 存在，3.5.3+ 用户取消注释即 DNS 阶段整族拒绝 |
| IP | `IP-CIDR` `IP-CIDR6` `GEOIP` `IP-ASN` | ✅ CIDR 系列（可选网关 IP 组）；❌ GEOIP/IP-ASN 大网段（误伤面大） |
| HTTP | `URL-REGEX` `USER-AGENT` | ⚠️ **写了不等于生效**：`URL-REGEX` 6 条全部锚定 `^http://`（只吃明文）；`USER-AGENT` 4 条写在**没有 `[MITM]` 段**的 ads 插件里，而 UA 是请求头、未解密看不到——能否命中未经验证，已登记 waiver。见 `docs/rule-effectiveness.md` |
| 端口 | `SRC-PORT` `DEST-PORT`（3.1.7+ 支持区间 `80-443`、`>=443`） | ✅ `DEST-PORT,853`（DoT/DoQ 阻断）；区间语法暂无场景 |
| 协议 | `PROTOCOL`（HTTP/HTTPS/TCP/QUIC/STUN/UDP，3.1.7+） | 🟡 `PROTOCOL,STUN,REJECT` 已入可选层 |
| 逻辑 | `AND` / `OR` / `NOT`（3.1.7+；IP 子规则放后面省 DNS） | ❌ 暂无场景 |
| 兜底 | `final,DIRECT`（仅在主配置） | ❌ 插件不能声明 final |

**REJECT 策略变体**（policy.md，一手的「拒绝 API」）：

| 策略 | 回包 | 适用 |
|---|---|---|
| `REJECT` | 404 + 空 body | 默认广告拦截 |
| `REJECT-IMG` | 200 + 1px GIF | `<img>`/开屏图占位（App 需要「图被拒绝」语义时） |
| `REJECT-DICT` | 200 + 空 JSON 对象 `{}` | 上报/埋点接口需要 JSON 才不报错 |
| `REJECT-ARRAY`（文档写作 `REJECT-ARRY`） | 200 + `[]` | 上报接口要数组时 |
| `REJECT-DROP` | 无回包直接丢 | **防重试风暴**（SDK 失败秒重试场景）；官方文档未列 `*-NO-DROP` 变体 |

- ✅ HTTPDNS 关键词规则已换挡至 `REJECT-DROP`，避免客户端在收到 200 空包后频繁秒级重试产生的重试风暴；
- ✅ 通用埋点上报特征规则已接入 `REJECT-DICT`（返回 200 + `{}` 空字典），成功欺骗 SDK 判定数据已落库，触发客户端主动执行 `deleteEvents` 清空本地未上传重试队列，彻底避免本地 SQLite 膨胀与射频高频唤醒；
- ✅ Rewrite v2 侧同步使用 `reject_dict(200)`：soda 开屏品牌上报与 DSP 展示上报、douyin DSP 展示上报都返回 JSON `{}` + `application/json`（`reject(200)` 的空 Body 是 `text/plain`，`reject(200,"{}")` 仍是文本）；规则层 `REJECT-DICT` 与请求层 `reject_dict` 现在一致；
- ✅ **`REJECT-IMG` 规则动作落地（第九轮，meituan v1.2.1 可选增强层）**：`p[0-9].meituan.net` 的广告图路径从 `REJECT`（404 文本）换成 `REJECT-IMG`（200 + 1px GIF 合法图像）——图片加载器拿到可解码图像后不会进入「破损图→重试/占位」分支，是这族请求最贴近语义的拒绝方式。REJECT 五变体现在 3 用（REJECT / REJECT-DICT / REJECT-DROP）+ 1 注释态（REJECT-IMG，需先启用增强层）+ 1 无端点（REJECT-ARRAY），全部纳入覆盖率审计。
- 📈 规则引擎性能（官方实测）：10 万级 DOMAIN 规则 ≤5ms/IP-CIDR6 ≤20ms，LRU 缓存近命中 — **可以放心挂外部规则订阅做增强**：
  🟡 主配置 [Rule] 外挂 `.list`（如 anti-AD / hagezi），`tools/ads-audit.py --sources` 已能评估覆盖互补度。
- ⚠️ **`DOMAIN-WILDCARD` 已收录但默认注释**（语法仅 3.5.3(1008)+，当前只在 TestFlight）：ads 插件带 30 条广告子域通配 + 11 条数字分片家族 glob，v2.7.0 起以 `# DOMAIN-WILDCARD,<glob>,REJECT` 注释行收录——插件头保持 App Store 正式版 3.5.2(996)，不让 TestFlight 版本挡住真实用户；装了 3.5.3 的用户逐行去掉 `# ` 即启用。`*` 跨点语义按广告专用左标签整族拦截动态子域（`ads.*`、`ads-*`、`adserver.*`、`advertising.*`、`advert.*`、`adx-*`、`bannerads.*` 等），弥补 `[Host]` 只能枚举固定域名的缺口。build/lint 双重校验照常在注释层上跑：左标签锚定、只允许 `*`/`?`、拒绝 `*`/`*.com`/`ads*`、不命中 `protected-roots.json`；lint 反向锁死「通配必须保持注释、`#!loon_version` 不得超过正式版 996」。
- ✅ **字符类家族层（第二轮）**：官方规定 `[...]` 是第三类通配符（`node[0-9].example.com`）。ads 插件新增 11 条「数字分片家族」glob，把 `ads3/ads5 × normal/-hl/-lf/-lq/-xh`、`p3/p6/p9-ad-sign.byteimg.com`、`v1/v2/v3-ad.video.yximgs.com`、`pangolin-sdk-toutiao1..5.com`、`dns9..12.quad9.net` 等 **30+ 台已枚举主机折叠成族**，顺带覆盖永远枚举不到的兄弟分片。只放开 `[0-9]`：`[a-z]` / `[!0-9]` 会把匹配扩散到别的品牌主机，而「保护名单不可被通配命中」这条保证必须保住。build 强制「每条家族 glob 至少覆盖 2 台已枚举主机」，凭想象造家族进不来；lint 再用正/反样本锁一次（`ads[0-9]` 命不中 `ads10` / `ads` / `adsxx`）。

## 5. 代理与策略组（node.md / policy.md / policygroup.md）

> 仓库不提供节点。以下是你自己主配置里可用的完全面——和本仓库插件**零冲突**（插件只 REJECT 广告域，剩下流量路径原样归你）。

- 协议：Shadowsocks(-R)、VMESS（tcp/ws/http × tls 组合）、VLESS（ws/http × tls）、Trojan（ws/http）、HTTP(S)、**WireGuard**（3.0.4+，含 IPv6）、**Hysteria2**、Custom-by-JS（`custom,...,script-path=...`）。
- 策略组四型：`select`（手动）/ `url-test`（自动最快，`interval`+`tolerance`）/ `fallback`（首个可用）/ `load-balance`（Random/PCC/Round-Robin）。
- 节点直写格式与订阅导入；订阅流量明细读 `Subscription-Userinfo` 头。

## 6. 脚本五型与 API（script.md / script_api.md）

| 类型 | 触发 | 本仓库 |
|---|---|---|
| `http-request` | 请求到达（可改 URL/headers/直接回假响应/指定 node 重发） | ✅ soda/douyin `request … script()`：广告域名拦截 + 开屏 splash 家族拦截（共享 `src/common/splash-ad.js`） |
| `http-response` | 响应到达（$done 改 body/status/headers） | ✅ 全部净化/改写类脚本 |
| `cron` | 定时（五段 cron；`30 20 * * *` → 6 段可加秒） | ✅ daily-reminder（`reminderCron` 是 [Argument] input） |
| `network-changed` | 网络切换（只执行配置里的第一个） | ⚪ 玩法建议：切网发一条 `$notification` 提示模式状态 |
| `generic` | 手动按钮脚本（`img_url` 配图标） | ✅ soda/douyin `status.min.js` 插件状态自检按钮（打卡 + 广告统计 + 开关看板/冲突提醒 + Loon 环境诊断；全部开关经对象参数透传，`statusNotify` select 可选弹通知/静默） |

- ✅ 关键坑已记录：旧语法 `argument=` 不透传开关 → 必须新版 `script("scripts/x.min.js",{${开关}})`，`$argument.<名>` 取值（3.5.1(983)）。
- ✅ 已落地：`$notification.post` attach 对象 `{openUrl: "@@APP_SCHEME@@"}`（通知横幅一键直接跳转打开对应汽水/抖音 App）。
- ✅ 已落地：Rewrite v2 `reject_dict(200)` 用于上报端点（JSON `{}` + `application/json`）；`reject_array` 暂无数组响应场景。
- ✅ **首条命中治理**：同一请求/响应 Loon 只执行配置顺序里第一条 `enable` 为真的脚本。仓库已据此把 settings 两条绑定的参数对齐、给 `hideDouyinTab` 增加独立绑定、把福利页打卡写成所有胜出脚本的副作用（独立 welfare-stamp 绑定只在全关时兜底）；lint 绑定矩阵用真实 URL 样本锁定“无死绑定、重叠必须等效或允许”，状态看板提示 `debugLog` 被清理脚本抢占。
- ✅ **运行环境诊断**：Generic 状态脚本读取 `$loon`（设备/系统/Loon 版本）、`$script.name/startTime`、`$environment.params.nodeInfo`（兼容文档拼写 `$envirnoment`）与 `$config.getConfig().running_model`，结果页输出「运行环境」行；另用 `$utils.ungzip` 是否存在输出「Loon 能力」行（988+ ✅ / 983–987 ❌）。全部 `typeof` 守卫，旧 build/非节点场景缺失即省略。
- ✅ **脚本安全门禁**：lint 对 `src/*/*.js` 与部署 `.min.js` 强制 `$done()`、禁用 `$httpClient`/`fetch()`/`XMLHttpRequest`/`WebSocket`/`sendBeacon`/`Function(`/`eval(`/`require(`、限制 `$notification.post` 只出现在 status/daily-reminder，并校验部署目录无孤儿脚本——保证脚本不外发响应数据、不执行动态代码。
- ✅ **条件表达式（第二轮核对）**：`request|response if` 支持 `${url}`、`${request.method}`、`${request.header['x']}`、`${response.status}`、`${response.header['x']}` 与 `[Argument]` 参数，操作符只有 `==` / `~=` / `&&` / `||` / `()`；**不支持** `!=`、`!~`、大小比较、Body 内容条件、正则命名捕获。Response 规则必须有「URL Guard 且是必要条件」。
- ⚪ 未用的条件：`${response.status}`（可做「只改 200」的守卫）、`${response.header['Content-Type']}`（可做「只处理 JSON」的守卫）。两条都与脚本内 `readBody` 的 `not-json` 分支重复，且会把「Content-Type 写错但内容是 JSON」的接口静默漏掉，故不采用。
- ⚪ `with debug=${开关}`：Loon 自带的脚本调试开关，可动态引用 `[Argument]`。现在用 `X-*-Plugin` 响应头 + `console.log` 已能定位「跑没跑、跑到哪步」，真机深挖时再挂。
- ⚪ `binary_body_mode`：处理的都是 JSON 文本，不用。
- ✅ `with timeout` / 动态 `timeout=${参数}` / 动态 `cron ${参数}` / `tag` / `img_url` 全部在用。
- ❌ `mock_file` / `.mock_file`：外部资源依赖，违背仓库自包含纪律。

## 7. 插件机制（plugin.md）

- ✅ 元数据齐全并受 lint 校验：soda/douyin 至少 `name/desc/author/version/date`；ads 另含 `homepage/icon/system/loon_version/tag/type`。
- ✅ `[Argument]` 类型 `bool`（开关）、`input`（cron 文本）与 `select`（`statusNotify`：notification/silent，`type=string`；候选值经 `script(...,{${statusNotify}})` 以 String 透传）。
- ✅ 脚本相对路径绑定（`scripts/*.min.js` 与 `.plugin` 同级——这就是 raw 直链部署无需 Pages 的原因）。
- ✅ **`[MITM]` 支持通配（第二轮落地）**：官方文档写明 `hostname` 支持 `*`、`?`，域名前加 `-` 表示排除。soda/douyin 用一条 `ads?-normal*.zijieapi.com` 覆盖 Pangle 全部分片，而 `[Rule]` 的 `DOMAIN-SUFFIX` 不吃通配、只能逐个列 10 条 QUIC 回退——两边各用自己最强的写法，覆盖关系由 lint 校验（`mitm_covers()` 按 glob 匹配）。
- ✅ **App 插件的可选 MITM/URL-REGEX 增强层（第八轮，meituan v1.2.0 / xianyu v1.3.0 / qidian v1.1.0）**：这三个 App 未做证书固定，同域广告接口（`splash.ads`、`argus/api/*/adv/*`、`openscreen?ad` 等）黑洞会伤功能，`URL-REGEX` 路径级 reject 是唯一正解——插件文末整段默认注释（`# [MITM]` + `# hostname = %APPEND% …` + `# URL-REGEX,…,REJECT-DICT`），不装证书永不生效、App Store 3.5.2 导入无障碍。lint 三重锁：固定 App（banks/wechat/mijia/x/instagram）JSON 禁止出现 `enhance`；生成物里 `[MITM]`/`hostname =`/`URL-REGEX` 行必须以 `#` 注释态存在；`enhance.url_regex` 只收 `URL-REGEX` 三段式且动作在白名单。Tier C App（不背单词/软考通/MBA大师/智慧房东）逐家核实**无可引用路径级证据**，宁缺毋滥不加层。

## 8. `[IP Rewrite]`（Build 1007+，插件专属）

- 语法：`目的单 IPv4 = reflect|reject|drop`；**只收单 IPv4**（不收 CIDR/域名/IPv6/参数）；在 [Rule]/Rewrite/脚本之前（TUN 阶段）生效=最快最彻底；**插件内同 IP 按首条生效**，非法条目或重复的 `[IP Rewrite]` 段才会让整段失效；多插件同地址按启用顺序取靠前。
- ✅ 已落地原生编译器支持：`tools/build-ads.py` 支持严格单 IPv4 校验、全局去重锁、保护名单阻断（禁 119.29.29.29）；并在 `src/ads/domains.json` 收录 16 条单 IPv4 HTTPDNS 网关接入点（阿里内地 3 + 海外 8、腾讯 4、百度 1），可选直接 drop。

## 9. 真机取证队列（汇总，按优先级）

1. [x] `[IP Rewrite]` 落地：编译器支持 + 16 条 HTTPDNS 网关单 IPv4 接入点 + build/lint 单 IPv4 去重锁。
2. [x] `[General]` 原生 `doh3-server = h3://223.5.5.5/dns-query,h3://223.6.6.6/dns-query`：支持 HTTP/3 0-RTT 加密 DNS 解析，IP 字面量防自举死锁，构建器与 linter 双重强校验。
3. [x] 第一方上报与打点阻断：Soda 与 Douyin 双插件均实装 DSP 展示上报 Rewrite 阻断（原生 `reject_dict(200)`，JSON `{}` + `application/json`），配合规则层 `REJECT-DICT` 彻底避免 SDK 重试风暴与本地数据库膨胀。
4. [x] HTTPDNS 关键词规则采用 `REJECT-DROP` 根治秒重试风暴；顺带启用 `$notification` attach openUrl 一键跳转 App。
5. [x] Generic 手动交互按钮落地：`status.min.js` 支持在 Loon 界面一键触发状态健康检查与统计看板。
6. [x] `[Argument]` `select` 下拉类型应用：`statusNotify`（notification/silent）控制 Generic 自检按钮的通知行为；大型「模式预设」仍不采纳——`enable=` 与静态 `[Rule]` 无法由 select 推导，预设会与独立开关形成双重事实源。
7. [x] 开屏请求拦截跨家族统一：`splash-ad.js` 迁入 `src/common` 单一来源，douyin 新增 `blockSplashAd`；lint 对两家族做 3 hit / 3 miss 边界锁定（`inspire` / `inspire_preload` / `marketing/done` 绝不拦）。
8. [x] Generic 自检升级为开关看板：全部 `[Argument]` 经对象参数透传，结果页汇总开关并检测冲突（`killRewardAds` / `rewardSafe+cleanAds` / `rewardSafe+settingsClean` / `rewardSafe+blockAdDomains` / `treasureMinimal+killRewardAds`）；lint 锁定绑定必须透传全部开关。
9. [x] 响应脚本首条命中治理：`settingsClean+hideDouyinEntry` 参数对齐、`hideDouyinTab` 独立绑定、打卡副作用内置于 sanitize/reward-observe/treasure/observe、welfare-stamp 仅兜底；lint 新增绑定矩阵（soda 29 样本 / douyin 16 样本）与允许清单，测试新增 `test_welfare_stamp.js` 10 条断言。
10. [x] Generic 状态看板环境诊断：`$loon` / `$script` / `$environment` / `$config.getConfig()` / `$utils.ungzip` 全部接入，结果页与通知显示 Loon 版本、脚本执行时间、节点、运行模式与 gzip 能力；`test_status.js` 扩到 40 条，覆盖完整、拼写兼容、缺失与能力两种状态。
11. [x] 构建门槛对齐：确认 3.5.1(988) 才引入脚本 gzip API；插件保持 983 安装门槛，README/插件描述/真机清单统一注明“gzip 清理需 988+，983–987 只记录状态”。
12. [x] QUIC→TCP 回退落地（v2.8.0 / v0.8.0，常开无开关；v2.8.2 / v0.8.2 扩到全分片族）：soda 17 域、douyin 16 域各写一条 `AND,((DOMAIN-SUFFIX,…),(PROTOCOL,QUIC)),REJECT`；不做全局 `PROTOCOL,QUIC,REJECT`。同时保留 `h2 = true`——**第三轮复核后降级为「未文档化键的零成本冗余」**（官方 MitM 文档只列 `hostname`/`ca-p12`/`ca-passphrase`；HTTP/2 解密是官方产品页宣称的默认能力），不再计入能力点。请求免压缩经真机体积核算后放弃（upsell gzip 后已 183–191 KB）。lint 锁 QUIC 集合、全局 QUIC 禁令、免压缩规则、`h2 = false` 反例与 `families.json` 计数；真机回退耗时与证书固定风险仍按 `docs/device-checklist.md` F 段观察。
13. [x] `DOMAIN-WILDCARD` 广告子域通配层：30 条 glob + 11 条家族 glob；v2.7.0 起因正式版（3.5.2/996）不支持而**默认注释**（TF 3.5.3 用户取消注释启用），插件门槛不再抬到 1008；build 安全校验 + lint 模式/正负样本锁 + 反向锁「通配必须注释、loon_version ≤ 996」全部落地。
14. [x] 编码边界落地（v2.8.1 / v0.8.1）：确认 Loon 脚本层只有 `$utils.ungzip`（gzip），**br / zstd / deflate 无解码器**；br 无魔数（RFC 7932 纯 stream format），只能靠 `content-encoding` 识别。6 个解析 body 的脚本统一加 `ceTag()`，`skip=not-json` / `skip=json-parse` / 两条观察器日志都带 `ce=`；`douyin/observe.js` 非 JSON 时从静默改为打日志。lint 新增 `check_encoding_guard()`（缺 `ceTag()` 或分支漏接即报错），测试新增 `test_encoding_guard.js` 22 条。真遇到 `ce=br` 的正解是把该端点 `Accept-Encoding` **设为** `gzip`（不是删）。
15. [x] **字符类家族层（第二轮，ads v2.3.0）**：`DOMAIN-WILDCARD` 的 `[0-9]` 把 11 个数字分片家族折叠成 glob，覆盖 30+ 台已枚举主机与未枚举的兄弟分片；build 强制「≥2 台已枚举主机」+ lint 正反样本 + 审计工具 glob 计数（`glob 41`）。
16. [x] **Pangle 分片族补全（第二轮，soda v2.8.2 / douyin v0.8.2）**：`[MITM]` 单分片 `ads5-normal-hl` 升级为 `ads?-normal*.zijieapi.com` 一条通配，`[Rule]` 逐个列 10 个分片做 QUIC 回退，`BLOCKED_HOSTS` 支持 `?`/`*`。lint 新增 `mitm_covers()`（按 glob 判断 QUIC 域是否被 MITM 覆盖）与「拦截名单 ↔ `[Script]` 正则」正反样本双向锁。
17. [x] **层序结案 + 原生 Body 改写短路（第二轮）**：官方原文「Rewrite 在规则匹配前执行」；MITM 内部 Rewrite → Script。lint 新增 `REWRITE_BODY_RX`：`response.json.*` / `body.mock` / `body.replace` 命中时同阶段脚本不执行，属文档明写的二选一。
18. [x] **`$notification` clipboard（第二轮）**：状态自检通知点一下就把完整诊断复制进剪贴板。
19. [x] **规则参数对齐（第三轮，修 bug）**：`pre-matching` / `extended-matching` 是 **Surge** 参数，Loon 官方三页规则文档只定义 `no-resolve`（且仅 IP 类用）。已从 72 条规则删除，`RULE_PARAMS` 收缩为 `{no-resolve}`，`DOMAIN-WILDCARD` 生成物改为 `DOMAIN-WILDCARD,<glob>,REJECT`；lint 新增 `SURGE_ONLY_RULE_PARAMS` 拦截回归。想要「DNS 阶段拒绝」的正解是主配置 `domain-reject-mode = DNS`（插件无权声明）。详见 `docs/loon-native-first.md` §10.1。
20. [x] **`[Argument]` schema 校验（第三轮）**：官方只有 `input`/`select`/`switch` 三种控件与 `string`/`number`/`boolean` 三种类型，`integer`/`float`/`bool` 别名不能解析且**不报错**（只会让参数变 `undefined`）。新增 `check_argument_schema()`：控件名、类型名、`switch` 默认值、`select` 候选数（≥2）、`type=number` 可转数字、参数名唯一，覆盖 25 条声明。
21. [x] **`[Host]` 通配 + 固定 IP（已在用，第三轮的判断作废）**：`ads.plugin` 的 `[Host]` 里 456 条 `*.domain = 127.0.0.1` 从早期版本就在跑（`*.pangle.io`、`*.gdt.qq.com`…）。官方 `DNS/hostmap` 左值支持 `*.`，右值语法与是否通配无关，「没找到示例」不等于「不支持」。真机只需确认一个纯通配域名确实解析到 127.0.0.1。

22. [x] **压缩协商降到 gzip（第四轮，soda v2.8.3 / douyin v0.8.3）**：`[Rewrite]` 写 `request.header.set("Accept-Encoding","gzip")`，覆盖 `[MITM]` 全部域名。脚本层只有 `$utils.ungzip`，br/zstd 解不开就是静默失效；降级不是免压缩（只多 10~20%，E2 否决的是删压缩）。lint 新增 `AE_SET_GZIP` 白名单 + 「覆盖每个 `[MITM]` 域名」断言。
23. [x] **回写 body 清压缩头（第四轮，修 bug）**：`markHeaders(reason, bodyChanged)`，`bodyChanged=true` 时删 `content-encoding` / `content-length`。新 body 是明文，旧头指向压缩体：留着 → 客户端按 gzip 解明文或按旧长度截断。只加诊断头的分支不动它们。单测 `test_encoding_guard.js` 双向锁死。
24. [x] **拦截回包形状对齐 `reject_dict`（第四轮）**：`blockAdDomains` 从 `200 + 空 text/plain` 改成 `200 + application/json + {}`，与 `[Rewrite]` 的 `reject_dict(200)` 一致，避免 SDK 走「解析失败→重试」。
25. [x] **`with debug` 接上 `debugLog`（第四轮）**：43 + 14 条 `[Script]` 全部 `debug=${debugLog}`，打开只读日志时同时开 Loon 原生脚本调试。`tag`/`img_url`/`requires_body`/`binary_body_mode` 不接受变量（文档明写）。
26. [x] **参数 schema 单源（E6）**：`src/args/<family>.json`（+ `common.json` 的看板顺序）→ `tools/gen-args.js` 生成三处：插件 `[Argument]` 段、`src/common/status.js` 的 `SWITCH_LABELS`、README 参数表。`--check` 逐字节比对，接入 lint 与 `npm run check:args`（在 build 前跑，避免自动修复掩盖漂移）；lint 里手写的开关名/默认值/generic 透传清单改为从 schema 派生。`[Script]` 的 `${...}` 绑定保留手写（行为接线），继续由 lint 对账。迁移 golden diff：两插件 43 行 `[Argument]` 零差异；`test_args_schema.js` 37 条断言 ×2。
27. [x] **存储作用域（第五轮，修 bug，soda v2.8.4 / douyin v0.8.4）**：官方 Script API 5.3 写明 `$persistentStore.remove()` **不接受参数**，语义是「清空全部脚本的持久化数据」。原来 `adElapsedSeconds()` 里写 `$persistentStore.remove(AD_START_KEY)`，等于每量一次广告时长就把 `welfare-seen` / `ad-stats` / 每日提醒标记一起抹掉，且无任何报错。改成 `write(undefined, AD_START_KEY)`；新增 `tests/test_store_scope.js`（12 断言 ×2，断言「别的键必须还在」）与 lint `SAFE_STORE_WIPE_RX`。
28. [x] **全局直连告警（第五轮）**：`running_model = 0` 时 Loon 不走规则、不进 MITM、不跑脚本，插件完全不生效，但界面只显示「直连」两字。状态页现在点名「运行模式 直连（⚠️ 插件不生效）」并给出处置建议；`"0"` 字符串也覆盖。`test_status.js` 新增 3 条断言。
29. [x] **能力覆盖率可计算（第五轮）**：`tools/loon-coverage.py` 把 117 条能力落成可执行清单，从插件有效行与脚本源码探测真实用法（注释不算），四档分类。`docs/loon-coverage.md` 为生成物；`npm run check:loon` 同时校验「已用仍可探测」「判死没被用回去」「文档不过期」。当前 61 已用 / 27 可用未用 / 28 判死，利用率 69.3%（第九轮把 REJECT 策略变体与 `[IP Rewrite]` 的注释态口径补进表后分母变大，数字低于旧值不是退步，是审计变细）。
30. [x] **广告面覆盖率可计算（第六轮，ads v2.3.1 → 第七轮 ads v2.4.0）**：换轴——分母从「Loon 有多少功能」改成「广告有多少种」。`tools/ad-surface-audit.py` 定义 19 类广告 / 6 族，逐类声明理论可达档与当前档，并从插件与脚本里探测证据；`--check` 拦五种漂移（声明做了探不到、声明没做却探到、当前档高于上限、承诺提档却写「做不到」、距上限停住却不写理由）。生成的 `docs/ad-type-strategy.md` 给出每类的线上特征、可用层与规则思路、覆盖档、局限，以及六种可复制写法。当前 71%（39/55）；零证书方案的天花板是 42%。同轮补 FreeWheel（`fwmrm.net` / `stickyadstv.com`）、Sizmek（`serving-sys.com`）与倍孜（`beizi.biz` / `adn-plus.com.cn`），视频贴片从「无效」提到「弱效」。
31. [x] **第七轮：把「下一步」的假承诺撤回（ads v2.4.0）**。第六轮算出「做完下一步可到 90.9%」，第七轮逐条核对后发现**那个数是假的**：11 条「下一步」里只有 3 条是「零风险加域名」，其余 8 条根本不可达——`[Argument]` 管不到 `[Host]`（所以 attribution 无法开关化）、`URL-REGEX` 在 HTTPS 下要 MITM 才看得到路径（所以 beacon 到不了 full）、「最小合法包络」必须改响应体（所以 adconfig 到不了 full）、私有 JSON 提档 = 多适配一个 App（所以 feed/search/upsell 不是代码问题）。
    - **落实**：补 Mintegral 的真实请求域 `rayjump.com`（+ 通配）、`mtgglobals.com`、`mintegral.net`——此前清单里只有品牌域 `mintegral.com`，而 SDK 的广告请求走 rayjump 系，等于没拦。展开 `[Host]` 1295 → 1301 条。**激励/插屏/Banner 仍停在 `strong`**：补完一家不等于补完一类，长尾聚合（AdTiming/Smaato/Ogury）没有可核实的请求域。
    - **自证**：第一版还加了 `adtiming.com`、`smaato.com`、`ogury.com`，核实后全是官网域（真实请求走 adtiming 私有端点 / `smaato.net` / `ogury.io`），**拦不到广告还会拦官网**，已全删。这和「编造 Surge 参数」「把愿望写成下一步」是同一个形状的错误：**把「看起来应该如此」当成「已验证如此」**。
    - **机制**：每类新增 `blocked` 字段（为什么提不了档）。`--check` 新增两条互斥断言：`next_to > 现状` 时不许写 `blocked`；`现状 < 上限` 且停在原地时必须写。**没有它，删掉一行 `next_to` 就能把「做不到」伪装成「没在做」。**
    - **数字**：70.9%（39/55）——与第六轮同值，但**内容不同**：多了 3 个真实域、13 条 `blocked` 理由、少了 3 个假域。上一版的 90.9% 已撤回。
32. [x] **第八轮：写了 ≠ 生效（第三个分母）**。前两轮分别量化「功能用了多少」与「广告还剩多少」，但两者**只数声明、不检查前提**。新增 `tools/rule-effectiveness.py`：把每条规则的生效前提显式化为 `none`（连接层）/ `plain`（仅明文）/ `mitm`（需解密），并检查插件是否提供了该前提。审计 143 条：前提满足 133、**仅明文 6**、**存疑 4**。
    - **存疑的 4 条**：ads 的 `USER-AGENT,httpdns*,REJECT` 等。ads 插件**没有 `[MITM]` 段**，而 UA 是 HTTP 请求头、未解密时看不到。官方 HTTP 规则页只写「匹配请求 Header 中的 User-Agent」，**未写未解密时是否降级**，因此**不删除**，改为登记 waiver（保留理由 + 存疑点 + 真机证伪方法）。
    - **仅明文 6 条**：ads 的 `URL-REGEX` 全部锚定 `^http://`。技术上有效、不依赖解密，但只吃明文 HTTP，实际命中面很窄——这是一个容易被和「前提满足」混为一谈的夹层。
    - **机制**：`--check` 三条断言——存疑必须登记 waiver、失效 waiver 必须清掉、文档不过期。三条均验过会触发（清空 `WAIVERS` / 塞入不存在 key / 改文档 → 均退出 1），还原归零。与第七轮 `blocked` 断言同源：**允许存疑存在，但禁止存疑沉默。**
    - **顺带确认三条官方机制**：① **Response URL Guard 是强制的**（3.5.1+），条件必须含 `${url}` 且为必要条件，否则整条脚本无效；仓库 47 条 response 绑定全部合规。② **第一条命中即止**，`enable=false` 的规则**不占位**（所以清理组与观测组按开关分层正确，但两者同开时观测组不执行）。③ 仓库已在用 `request.header.set("Accept-Encoding","gzip")` 绕开 br/zstd 无解码器的问题（soda:154 / douyin:143），写法与官方 `request.header.set` 签名一致。
33. [x] **第九轮：拦了 ≠ 拦住（第四个分母，ads v2.5.0）**。前三个分母都默认同一件事：**广告请求会走到规则面前**。新增 `tools/bypass-audit.py` 枚举 17 条旁路，四态 `sealed` / `partial` / `open` / `na`，每条写清「怎么绕 / Loon 的手段 / 为什么停在这 / 真机怎么证伪」。
    - **数字**：已封死 6、部分封死 4、**有手段未落地 1**、无解 6；封死率 54.5%，加权（partial 记 0.5）72.7%。**最重要的一行是「有手段未落地」**——它不是做不到，是还没验证。
    - **唯一未落地项：IPv6 / AAAA 旁路**。`[Host]` 1301 条黑洞**全部只映射 IPv4**。官方 `DNS/hostmap` 支持 `ip-mode:ipv4-only` 右值，但**只给了单独使用的示例**，没给「同一域名同时写 `= 127.0.0.1` 与 `= ip-mode:ipv4-only`」。若 Loon 一个域名只认最后一条，补 ip-mode 会把黑洞覆盖掉——**比不补更糟**，且排查方向会完全错。因此**刻意不落地**，真机两步验证（先验多行共存、再验 AAAA 是否放行）通过后才批量补。
    - **本轮真落地：公共解析器 IP 直连阻断组（默认注释）**。App 直连 `8.8.8.8:443` / `1.1.1.1:853` 时连接层**没有域名**，`[Host]` / `DOMAIN-KEYWORD` / `URL-REGEX` 全废，`DEST-PORT,853` 也只挡端口、挡不住跑在 443 上的 DoH——**唯一还能生效的是 `IP-CIDR`**。补齐 Google / Cloudflare / Quad9 / AdGuard 四家共 16 个官方 IPv4+IPv6（**逐条取自官方页面，不凭印象填**）。默认关闭：用户主配置若拿这些 IP 当 `dns-server`，开启会掐断 Loon 自己的解析链（表现为整网不可用，比广告回来严重得多）。
    - **机制**：`--check` 六条断言，核心是「证据探不到」对 `sealed` 是错误、对 `open` 是**正确**——防止把「没做」伪装成「做了」。lint 新增 `check_bypass_dns_guard()`：本插件自用的 5 个 DNS IP 一旦出现在阻断清单就报错；四家解析器的 16 个 IP 缺一即报错。
    - **三条结论性无解**：主配置规则优先级（本地 > 插件 > 订阅，插件读不到）、`bypass-tun`（插件不该接管 TUN 边界）、证书固定（官方 MitM 页只有 `hostname` / `ca-p12` / `ca-passphrase`，没有 `skip-server-cert-verify`）。这三条写进审计而不是硬做——**知道封不了，也是一种封。**
34. [x] **元数据补齐 `#!openUrl`（第十轮，soda v2.8.5 / douyin v0.8.5 / ads v2.5.0）**：三插件安装详情页「打开链接」直达各自 README（`https://github.com/AshNail/plugins/blob/main/plugins/<family>/README.md`），装完即见使用说明。ads 走生成链：`src/ads/domains.json` 顶层 `openUrl` → `build-ads.py` 渲染 + 继承；lint 把 `openUrl` 列入必带元数据并校验 https；覆盖率工具新增 `m-open-url` 探针（58 已用）。
35. [x] **第十一轮：REJECT 策略变体入审计 + 注释态口径纠偏（meituan v1.2.1 / 覆盖率 v2）**
    - **REJECT-IMG 落地**：meituan 增强层广告图路径（`p[0-9].meituan.net/(bizad|wmbanner|brandCpt)/*.jpg`）由 `REJECT` 改 `REJECT-IMG`——图片加载器收到 200 + 1px GIF 会正常解码，绕开「404 → 破损图 → 重试」分支；REJECT 五变体首次齐进覆盖率表（3 用 + 1 注释态 + 1 无端点）。
    - **`[IP Rewrite]` 口径纠偏**：此前覆盖率标「判死」但第 8 节又写「16 条 HTTPDNS 网关以注释态收录」，两处矛盾。改为「可用未用」并写明唯一落地形态：广告目标 IP 不枚举（死路），HTTPDNS 网关 IP 注释态可选。
    - **数字**：117 条能力，61 已用 / 27 可用未用 / 28 判死，利用率 69.3%。分母变大导致利用率低于上一版，这是审计变细而非能力退步。
36. [x] **第十二轮：覆盖率缺口逐条裁决 + 插件能力面文档核实（mijia v1.1.2 / wechat v1.1.3）**
    - **缺口来自 `docs/app-coverage.md`（非猜测）**：`app-coverage-audit.py --offline` 用缓存的上游清单逐 App 列出「上游有、本地未收」的候选。逐条裁决而非照单全收：
    - **mijia 收 2 条（B 级，2 源）**：`adx.tv.mi.com`（电视端广告交易）、`adv.l7.34.sec.miui.com`（安全中心广告位），进默认关的 `miui_native` 组。注意后者虽在 `sec.miui.com` 族下，但主机名以 `adv.` 开头；同族的鉴权/风控组件（`auth.be`/`api.sec`/`mazu`/`notify`/`logupdate`）此前已裁决排除——反欺诈与推送是红线，不因「同族」而放宽收录，也不因「同族」而连带排除一条真正的广告位主机。
    - **wechat 收 1 条（B 级）**：`*.adinall.com` 营销聚合域进默认关 `watchlist`。具体两主机（`wapx` / `app-tj`）已在 `gdt_new` 组默认生效，通配留待抓包证实轮换子域后再启用——通配一次放太多，误伤时无法定位。
    - **插件能力面官方核实（两个悬而未决的文档疑点）**：① 插件 `[General]` 白名单实测为 `bypass-tun, include-tun, skip-proxy, real-ip, dns-server, doh-server, doq-server, doh3-server, ipv6-vif` 九键——raw 模板只列四键是简写，线上 Plugin 文档才完整；此前对 `doh-server` 是否可用于插件的存疑解除，无需改代码。② 插件 `[Rule]` 策略仅 `DIRECT` / REJECT 族 / `PROXY`，`FINAL` 不支持（与第 10 节既有结论一致）；`REJECT-ARRY` 为官方拼写别名，`REJECT-ARRAY` 亦被接受。
    - **口径**：本轮只增 3 条默认关候选、零默认开启面变化，改动全部经 `build:apps → build:app-readmes → audit:apps:write → lint` 生成链，README 与 `docs/app-coverage.md` 均为生成物、无手写漂移。
37. [x] **第十三轮：缺口审计机械化 + 米家广告基础设施补录（mijia v1.1.3）**
    - **发现**：12 个 App 的 A/B 级上游候选里，唯一还有未裁决项的只有米家（A:35 B:145）。逐条看，其中 5 条是真广告基础设施、其余全是安全/推送/账号云/遥测/业务 API——**缺口数字大，不代表待办多**。
    - **补录 5 条（均 2 源，默认关 `miui_native`）**：`global-ad-extranet-pri-azams.alb.xiaomi.com`、`global-ad-extranet-pri-azpn.alb.xiaomi.com`、`global-ad-intl-pri-alisgp.alb.xiaomi.com`（跨国广告投放 ALB）、`wtradv.market.xiaomi.com`（应用商店推广位）、`xadx.file.market.xiaomi.com`（小米 ADX 素材）。`miui_native` 27 → 32 域。
    - **制度化**：App JSON 新增 `triage_exclude` 裁决台账（11 个族、glob 匹配），审计命中的候选在文档里记「排除·<族>」、**不计入缺口**；未命中的仍显示「缺口」。`--check` 继续盯文档漂移，台账格式错误直接报错。结果：12 个 App 的 A/B 缺口全部归零（米家 141 条裁决排除 + 39 条已收录默认关）。
    - **风险自述**：台账是族级 glob，若未来某条真广告域恰好落在「业务 API」「浏览器」等族内，会被标成排除而不是缺口。缓解：表里仍列出每一行（只是状态不同），且现存的 `adv.*`/`ad.*`/`xadx` 广告位都按条收录、不靠族排除兜底。
    - **验证**：`npm run audit:apps` 12 行 `gaps=0`；`lint` 0 错误；插件/README/覆盖率文档均由生成链重建。
38. [x] **第十四轮：新增第 13 个 App 插件「京东」（jd v1.0.0）**
    - **取证先于规则**：`dsp-x.jd.com/adx/sdk` 是京东官方《京媒 SDK FAQ》写明的正式广告请求地址（`dsp-test-x` 为测试域）；`ccc-x.jd.com/dsp/tp?log=…`、`x.jd.com/dsp/tp?log=…` 是公开可点的广告跳转链——广告交易/点击监测层由官方文档与公开链路双重自证，不靠域名长相猜。
    - **放行比拦截更重要**：AWAvenue-Ads-Rule issue #197 明确 `mapi.m.jd.com`（购物车/订单/搜索必需）、`janapi.jd.com`（App 数据网关）、`img-x.jd.com` 与 `img2.360buyimg.com`（商品详情页图片 CDN）必须 allowlist；`cactus.jd.com/request_algo` 是 h5st 风控签名接口（公开逆向分析）。这些域在上游黑名单里出现 3-4 次也一律不拦——**上游收录数不是误伤豁免证**。
    - **分三层落地**：`jd_ad_exchange` 生效 5 域（dsp-x/ads-union/ccc-x/addata/skdisplay，均 A 级）；`jd_ad_watchlist` 默认关 8 域（x.jd.com 族竞价/曝光/winnotice、sgm-w/jrad/cm 语义待核实）；`jd_telemetry` 默认关 9 域（uranus 埋点、mercury log.gif、knicks 推荐回流、日志族）。零证书；京东含支付/风控，按固定类处理，加入 `APP_NO_ENHANCE_SLUGS` 拒绝 MITM 层。
    - **审计同步**：`app-coverage-audit.py` 增补 `jd` 的 PATTERNS / BRAND_ROOTS / EXCLUDE_ROOTS / ROOT_AD_HINT；`triage_exclude` 台账 5 类（交易风控/推送客服/商品图放行/基础设施/C 级单源）。结果 `jd own=5 A-cand=17 B-cand=13 gaps=0`，全仓 13 个 App 缺口仍为 0。
    - **验证**：`npm run check` 全绿（52 套件 / 1596 断言，lint 0 错误）；`plugins/jd/jd.plugin` 生效 [Host] 5 条、默认关 17 条，README 由生成链产出；`docs/device-checklist.md` J 节升为 13 个并新增京东判读项。
39. [x] **第十五轮：审计分母修复 + 长尾广告域第二批复核 + 京东证据补强（ads v2.7.4 / jd v1.0.1）**
    - **审计源复活**：`adguard-cn` / `adguard-mobile` 原指向已迁移的 `FiltersRegistry` 路径，在线审计一直静默 skip。改用官方 `filters.adtidy.org/extension/chromium/filters/224.txt`（中文）与 `11.txt`（移动广告）后，App 覆盖率审计恢复 14 源分母，13 个 App 仍全部 `gaps=0`。
    - **第二批 33 个 ≥7 源广告专域**：百度点击监测 `ecmb.bdimg.com`；中国媒体 `ykad-data.youku.com`、`de.as.pptv.com`、`adpai.thepaper.cn`；全球交易/SSP 23 个（kiosked/sitemaji/begun/tubemogul/nanigans/inner-active/i-mobile/celtra/brealtime/exponential/iqzone/adhood/adtimaserver/httpool/infolinks/buysellads/presage/disqusads/blogads/biddingx/mixadvert/rotaban/speee-ad）；移动广告网络 5 个（youmi/fiksu/mydas/nend/i2ad）；弹窗 `buzzonclick`。**不补**联盟返利（assoc-amazon）、基础网络（vnet.cn）、分析域（smetrics/nytimes/apple/unity3d）与无品牌语义随机域。生效 Host 1230→1291（exact 798 / wildcard 493），展开 1409。
    - **2.7.3 精确主机收尾**：复核上游语料后再补 5 个有明确广告语义的主机——百度推广入口 `cm.baidu.com`、`entry.baidu.com`；观察者网广告位 `bd1.guancha.cn`（AdGuard 中文 `$domain=m.guancha.cn`）、ZAKER 广告位 `ggs.myzaker.com`、新浪广告脚本 `d2.sina.com.cn`（EasyList China `$object,script`）。均为精确域名，不做根域展开。生效 Host 1291→1296（exact 798→803 / wildcard 493），展开 1414；`zhihuifangdong` 因引用 baidu SDK 组同步 93→96 条黑洞。
    - **2.7.4 第三批 34 个 6 源广告专域**：刷新 10 源清单后从 4933 个 ≥5 源候选中只取语义自证者——33 个交易/SSP/DSP/网络（Dable、Zemanta、Carbon Ads、PageFair、Clickbooth、Demandbase、Adviva、Harren、ClickRev、TrafficShop、TwitTad、Connatix `ck`、Retargeter、JuiceADV、EqAds、PostRelease、Adoric `-om`、MSN RTB `srtb`、The Moneytizer、Fout、Speakol、MicroAd、Greystripe、Optimix、Geniee SSP、StackAdapt、SmartyAds、Dianomi、TripleLift、ValueClick、District M、BidGear、AdButler）+ 弹窗组 PopMyAds。**不补**分析/会话回放、广告验证/反欺诈（拦掉可能放大恶意广告风险）、联盟返利与随机域。生效 Host 1296→1362（exact 837 / wildcard 525），展开 1480；核心广告组 1166→1232。
    - **京东证据补强（v1.0.1）**：`im-x.jd.com/dsp/np?log=` 是公开广告落地链，但多份 wskey 抓取教程显示 `im-x` / `msg.m.jd.com` 同链路携带登录凭证——`im-x` 永久保持默认关，`msg.m.*` 升为「消息/凭证红线」；`sgm-w` 被微信开放平台高风险域名单与 EasyPrivacy 同时收录但语义仍不明确，维持默认关。
    - **文档漂移归零**：`bypass-audit.py` 改为从生成物动态读取生效/注释黑洞数，`plugins/ads/README.md`、`docs/loon-native-first.md` 的硬编码 1301/1218 全部改为当前值或指向生成物；`npm run check` 全绿（52 套件 / 1596 断言，lint 0 错误，五个审计工具全部 `ok`）。
    - **CI 复核**：模拟全新 checkout（无 `.cache`）发现 `app-coverage --offline --check` 会把空源集当成文档 stale；改为「无源可载入时明确 skip、`--write` 仍拒绝覆盖」，本地有缓存时继续严格比对。CI 不再因缺缓存误红，但也不假装跑过覆盖审计。


## 10. 明确不采纳清单（持续维护，带理由）

| 项 | 理由 |
|---|---|
| `FINAL` | 插件 [Rule] 不支持（文档：final 仅主配置兜底） |
| `GEOIP` / `IP-ASN` 大网段 | 广告场景误伤面过大（共享 CDN/服务）；IP 精确打击已够 |
| `mock_file` / `json.jq_file`（**插件内**） | 外部资源依赖，违背仓库自包含纪律。但**主配置里自己写**是另一回事：贴片类可以用 `response.body.mock_file("text","empty.vast",200)` 返回空 VAST，见 `docs/ad-type-strategy.md` 附录 ④ |
| `include-tun` / `bypass-tun` / `ipv6-vif`（插件内） | 与拦截目标无关，徒增 TUN 接管面 |
| `hijack-dns` / `domain-reject-mode` / `dns-reject-mode`（插件内） | 插件 [General] 白名单外；放主配置清单（第 2 节） |
| `$config.setSelectPolicy` / `$setRunningModel` | 本仓库插件无策略组场景 |
| `$persistentStore.remove()` | 官方语义是**清空全部**脚本数据，不接受 key 参数；删单项只能用 `write(undefined, key)` |
| `[IP Rewrite]` | 只接受精确 IPv4、不支持 CIDR/域名；广告目标 IP 随时变，逐条枚举必漏 |
| `#!system_version` | 一个值同时约束 `#!system` 列出的所有平台；ads 声明了 macOS，填 15.0 会把 macOS 14 挡在门外。不填＝全部支持 |
| `$config.getSubPolicies` | 异步读策略组列表，插件不管理节点，读完没有动作可做 |
| `$crypto.aes` / `$utils.gzip` 上行方向 | 现有脚本无加密上行/压缩上行需求 |
| 域名/开屏拦截改用纯 `Rewrite … then reject_dict(200)` | 保留 `http-request` 脚本：需要逐请求日志、`rewardSafe` 分支与跨家族测试（42 + 22 条断言）；原生 Rewrite 无法输出自定义日志，且开关逻辑一旦写进静态行就失去脚本内的二次域名校验 |
| 更多广告响应体改用原生 `[Rewrite]` 拒绝 | 现有净化需要字段级裁剪、开关分支与 `X-Soda-Plugin` 诊断头，静态 Rewrite 只能整包拒绝；唯一适合整包拒绝的纯上报端点（splash/DSP show）已经使用 `reject_dict(200)`。新增静态拒绝必须先有真实 HAR 证明端点不承载奖励语义 |
| 字节系 HTTPDNS 静态 IP 化 | 火山引擎官方文档：动态接入地址（SDK 定期拉最佳 IP），静态化无意义 |
| `response.json.add/delete/replace/jq` 迁移已有净化逻辑 | 文档明写「Response Body Rewrite 命中时 Response Script 不执行」= 与脚本二选一，不是加速；且现有净化是字段级 + 正则 prune + 开关分支，原生 KeyPath 表达不了。lint 已加 `REWRITE_BODY_RX` 拦住「两条都想要」的写法 |
| `response.body.mock` 造「无广告」包络 | 需要完整包络样本，写错就是白屏/NPE；「保留包络、只删字段」这条原则不破 |
| `[Host]` 同一域名同时写 `= 127.0.0.1` 与 `= ip-mode:ipv4-only` | **暂不落地**：官方 `DNS/hostmap` 只给了 `ip-mode:` 单独使用的示例。若 Loon 一个域名只认最后一条，补 ip-mode 会把全部生效黑洞覆盖掉——比不补更糟。真机两步验证（多行共存 → AAAA 是否放行）通过后再批量补，见 `docs/bypass-audit.md` 第 4 节 |
| `reject_img` / `reject_array` / `reject_video` | 图位广告走 `[Host]` 黑洞，到不了 MITM；没有「响应必须是数组」的上报端点；视频素材走 CDN 域名拦截。三者都缺场景，等真机抓到具体端点再说 |
| `[a-z]` / `[!0-9]` 字符类 | 会把匹配扩散到别的品牌主机，让「保护名单不可被通配命中」失效；只放开 `[0-9]` |
| `network-changed` 脚本 | 一次换网会执行**所有**已启用的 Network Changed 脚本，本仓库能做的只有「弹通知」，属纯打扰 |
| `PROCESS-NAME` | 仅 macOS 生效，iOS/tvOS 忽略 |
| `$dns.query` | 会让脚本主动发起 DNS 查询，突破「脚本不外发数据」的安全门禁；且无对应需求 |
| `$persistentStore.remove()` | 清空**全部**脚本的键，会误删其他插件数据 |
| `$done()` 无参（断开连接） | 等价 `REJECT-DROP`，客户端看到的是「连接被掐」，比 `reject_dict` 更容易触发秒级重试 |
| `pre-matching` / `extended-matching`（规则行） | **Surge 参数**，Loon 没有：`pre-matching` 的对应物是主配置 `domain-reject-mode = DNS`，`extended-matching`（SNI 辅助匹配）Loon 默认开启。写进规则要么被忽略、要么让整条规则解析失败 |
| `sub_rule` 订阅规则（远程 `.list`） | 拉取失败没有本地兜底，表现是「广告突然全回来」且用户无感知；拦截规则的可用性应当和插件本体一样可靠 |
| `doq-server`（插件 `[General]` 可声明） | DoQ 只是第四种加密 DNS 传递方式，不增加拦截力；已有 `dns-server` / `doh-server` / `doh3-server` 三条链 |
| `ipv6-vif = off`（插件可声明，1007+） | 关掉的是整个 TUN 的 IPv6，副作用远超广告范围 |

## 11. 与本仓库的接口速查

| 想做 | 工具 |
|---|---|
| 评估现有拦截覆盖率 | `npm run audit:ads` |
| 重建 ads 插件 | `npm run build:ads`（改 `src/ads/domains.json`，勿手改生成物） |
| 全量门禁 | `npm run check`（build + lint + coverage + 52 套件/1596 断言） |
| 远端一致性 | `python3 tools/check-remote.py`（`--list` 看四段清单） |
| 一键发布 | `python3 tools/publish.py --with-source --yes` |
