# Loon 全功能清单（本仓库视角）

> 依据：官方文档 `https://nsloon.app/docs/`（源仓库 [Loon0x00/LoonManual](https://github.com/Loon0x00/LoonManual) `docs/cn/`，2026-10-27 逐页核对）。
> 图例：✅ 本仓库已在用 / 🟡 建议你在设备侧开启 / ⚪ 进阶可选 / 🔒 需真机取证后启用 / ❌ 不采纳（带理由）。
> 适用版本：主配置按当前 stable 功能描述；标注 build 号的是硬门槛（本仓库统一标注 3.5.1(983)+）。

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
`domain-reject-mode = DNS`（DNS 阶段拒绝，配合 `pre-matching`）、`dns-reject-mode`（让被 DNS 拒的域不再更名重试）。

## 3. DNS 面板与解析（dns.md / hostmap.md）

- ✅ `[Host]` 域名映射（ads 用 127.0.0.1 黑洞）；本仓库构建器速记 `=` → 域 + `*.域`（不是 Loon 语法，由 `tools/build-ads.py` 展开）。
- ✅ IP 形式 DoH（`https://223.5.5.5/dns-query`）——插件 [General]。
- 🔒 `h3://223.5.5.5/dns-query`（DoH3，需看 Loon DNS 页是否生效）、`quic://` DoQ。
- ⚪ DoT 域名形式 `tls://` 与 IP 形式取舍：插件防泄漏名单已拦公共 DoH 入口域名。

## 4. 规则类型全集（rule.md + 7 个细分页）

| 组 | 类型 | 本仓库 |
|---|---|---|
| 域名 | `DOMAIN` `DOMAIN-SUFFIX` `DOMAIN-KEYWORD` | ✅ KEYWORD 兜底；`DOMAIN` 在 soda/douyin 可选组 |
| IP | `IP-CIDR` `IP-CIDR6` `GEOIP` `IP-ASN` | ✅ CIDR 系列（可选网关 IP 组）；❌ GEOIP/IP-ASN 大网段（误伤面大） |
| HTTP | `URL-REGEX` `USER-AGENT` | ✅ 都在用（UA 通配符 `httpdns*`） |
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
- 📈 规则引擎性能（官方实测）：10 万级 DOMAIN 规则 ≤5ms/IP-CIDR6 ≤20ms，LRU 缓存近命中 — **可以放心挂外部规则订阅做增强**：
  🟡 主配置 [Rule] 外挂 `.list`（如 anti-AD / hagezi），`tools/ads-audit.py --sources` 已能评估覆盖互补度。

## 5. 代理与策略组（node.md / policy.md / policygroup.md）

> 仓库不提供节点。以下是你自己主配置里可用的完全面——和本仓库插件**零冲突**（插件只 REJECT 广告域，剩下流量路径原样归你）。

- 协议：Shadowsocks(-R)、VMESS（tcp/ws/http × tls 组合）、VLESS（ws/http × tls）、Trojan（ws/http）、HTTP(S)、**WireGuard**（3.0.4+，含 IPv6）、**Hysteria2**、Custom-by-JS（`custom,...,script-path=...`）。
- 策略组四型：`select`（手动）/ `url-test`（自动最快，`interval`+`tolerance`）/ `fallback`（首个可用）/ `load-balance`（Random/PCC/Round-Robin）。
- 节点直写格式与订阅导入；订阅流量明细读 `Subscription-Userinfo` 头。

## 6. 脚本五型与 API（script.md / script_api.md）

| 类型 | 触发 | 本仓库 |
|---|---|---|
| `http-request` | 请求到达（可改 URL/headers/直接回假响应/指定 node 重发） | ✅ soda/douyin `request … script()` |
| `http-response` | 响应到达（$done 改 body/status/headers） | ✅ 全部净化/改写类脚本 |
| `cron` | 定时（五段 cron；`30 20 * * *` → 6 段可加秒） | ✅ daily-reminder（`reminderCron` 是 [Argument] input） |
| `network-changed` | 网络切换（只执行配置里的第一个） | ⚪ 玩法建议：切网发一条 `$notification` 提示模式状态 |
| `generic` | 手动按钮脚本（`img_url` 配图标） | ✅ soda/douyin `status.min.js` 插件状态自检按钮（一键查打卡与广告统计） |

- ✅ 关键坑已记录：旧语法 `argument=` 不透传开关 → 必须新版 `script("scripts/x.min.js",{${开关}})`，`$argument.<名>` 取值（3.5.1(983)）。
- ✅ 已落地：`$notification.post` attach 对象 `{openUrl: "@@APP_SCHEME@@"}`（通知横幅一键直接跳转打开对应汽水/抖音 App）。
- 🔒 升级点：Rewrite v2 `reject_dict/reject_array` 与 `.mock_file`（后者因外部资源依赖违背自包含不采纳）。

## 7. 插件机制（plugin.md）

- ✅ 元数据齐全并受 lint 校验：soda/douyin 至少 `name/desc/author/version/date`；ads 另含 `homepage/icon/system/loon_version/tag/type`。
- ✅ `[Argument]` 类型 `bool`（开关）与 `input`（cron 文本）。
- 🔒 `[Argument]` `select` 下拉类型（值得验：可把「默认/保奖励/去广告」做成单选预设）。
- ✅ 脚本相对路径绑定（`scripts/*.min.js` 与 `.plugin` 同级——这就是 raw 直链部署无需 Pages 的原因）。

## 8. `[IP Rewrite]`（Build 1007+，插件专属）

- 语法：`目的单 IPv4 = reflect|reject|drop`；**只收单 IPv4**（不收 CIDR/域名/IPv6/参数）；在 [Rule]/Rewrite/脚本之前（TUN 阶段）生效=最快最彻底；**重复声明 IP 会让整个模块失效**；多插件同地址按启用顺序取靠前。
- ✅ 已落地原生编译器支持：`tools/build-ads.py` 支持严格单 IPv4 校验、全局去重锁、保护名单阻断（禁 119.29.29.29）；并在 `src/ads/domains.json` 收录 16 条单 IPv4 HTTPDNS 网关接入点（阿里内地 3 + 海外 8、腾讯 4、百度 1），可选直接 drop。

## 9. 真机取证队列（汇总，按优先级）

1. [x] `[IP Rewrite]` 落地：编译器支持 + 16 条 HTTPDNS 网关单 IPv4 接入点 + build/lint 单 IPv4 去重锁。
2. [x] `[General]` 原生 `doh3-server = h3://223.5.5.5/dns-query,h3://223.6.6.6/dns-query`：支持 HTTP/3 0-RTT 加密 DNS 解析，IP 字面量防自举死锁，构建器与 linter 双重强校验。
3. [x] 第一方上报与打点阻断：Soda 与 Douyin 双插件均实装 DSP 展示上报 Rewrite 阻断（`reject(200)`），配合规则层 `REJECT-DICT` 彻底避免 SDK 重试风暴与本地数据库膨胀。
4. [x] HTTPDNS 关键词规则采用 `REJECT-DROP` 根治秒重试风暴；顺带启用 `$notification` attach openUrl 一键跳转 App。
5. [x] Generic 手动交互按钮落地：`status.min.js` 支持在 Loon 界面一键触发状态健康检查与统计看板。
6. [ ] `[Argument]` `select` 下拉类型应用：探索在大型插件中集成模式预设（如默认/保奖励/强力去广告）。

## 10. 明确不采纳清单（持续维护，带理由）

| 项 | 理由 |
|---|---|
| `FINAL` | 插件 [Rule] 不支持（文档：final 仅主配置兜底） |
| `GEOIP` / `IP-ASN` 大网段 | 广告场景误伤面过大（共享 CDN/服务）；IP 精确打击已够 |
| `mock_file` / `json.jq_file` | 外部资源依赖，违背仓库自包含纪律 |
| `include-tun` / `bypass-tun` / `ipv6-vif`（插件内） | 与拦截目标无关，徒增 TUN 接管面 |
| `hijack-dns` / `domain-reject-mode` / `dns-reject-mode`（插件内） | 插件 [General] 白名单外；放主配置清单（第 2 节） |
| `$config.setSelectPolicy` / `$setRunningModel` | 本仓库插件无策略组场景 |
| `$crypto.aes` / `$utils.gzip` 上行方向 | 现有脚本无加密上行/压缩上行需求 |
| 字节系 HTTPDNS 静态 IP 化 | 火山引擎官方文档：动态接入地址（SDK 定期拉最佳 IP），静态化无意义 |

## 11. 与本仓库的接口速查

| 想做 | 工具 |
|---|---|
| 评估现有拦截覆盖率 | `npm run audit:ads` |
| 重建 ads 插件 | `npm run build:ads`（改 `src/ads/domains.json`，勿手改生成物） |
| 全量门禁 | `npm run check`（build + lint + 44 套件/1268 断言） |
| 远端一致性 | `python3 tools/check-remote.py`（`--list` 看四段清单） |
| 一键发布 | `python3 tools/publish.py --with-source --yes` |
