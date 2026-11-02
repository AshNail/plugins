# Loon 高级功能矩阵（Mac 0.5.0(1011)）

> 本页记录 Loon Mac「配置 → 高级功能」及相邻模块的逐项结论。
> 原则：默认只开有明确收益且可回滚的项；会改局域网、泄露真实 IP、降低稳定性的项保持关闭，
> 写明开启条件和回滚方式。2026-11-01 在 Mac 实机核对。

## 1. 当前生效配置

| 区域 | 功能 | 当前值 | 结论 |
|---|---|---|---|
| 网络 | IP 栈 | 仅 IPv4 · IPv6 关闭 | 保留。当前网络/节点以 IPv4 为主，v4-only 避免 AAAA/Fake-IP 分流异常；IPv6-only 节点时再开 |
| 网络 | 网络接口 | 自动 | 保留 |
| 网络 | GeoIP / ASN 数据库 | 自定义数据库，自动更新 | 保留；更新失败时用内置库回退 |
| 路由 | 不作为默认路由 | 关 | 保留。TUN 需要默认路由；开启会让 Loon 只接管显式规则流量 |
| 路由 | 绕过路由 / 绕过代理 | 各 22 项 | 保留。私网、保留地址、本机回环不进 TUN/HTTP 代理 |
| 路由 | 路由系统服务 | 已禁用 | 保留。避免 APNs/系统服务被规则误伤 |
| 连接 | 策略切换时关闭连接 | 关 | 保留。开=切节点时断旧连接，防旧策略残留但会中断下载/通话 |
| 连接 | 域名 REJECT | DNS · Loopback IP | 保留。广告在 DNS 阶段拒绝，Host 黑洞返回回环 |
| 连接 | SNI 辅助规则匹配 | 开 | 保留。Host 为 IP 时用 TLS SNI 命中域名规则，提升广告/分流覆盖 |
| 解析 | 延迟测试 | 超时 5 秒 | 保留。3 秒更快但慢节点误判率上升 |
| 解析 | 真实 IP | 36 项 | 保留。銀行/支付/APNs/iCloud/STUN 等需要真实地址 |
| 解析 | DNS 劫持 | `*:53` | 保留。所有 53 端口查询交给 Loon |
| 传输 | UDP | 允许 STUN · REJECT 回落 | 已对齐：允许 STUN（通话），节点不支持 UDP 时 REJECT 而不是直连泄露 |
| 传输 | TLS 指纹 | OpenSSL 默认 | 保留。Chrome/Safari 指纹仅在遇到 TLS 指纹风控时再换，换后需回归银行/支付 |
| 网关 | 启用网关 / DHCP | 关 | 保留关闭。需要 Mac 有线以太网 + 局域网共享；当前无线环境无法启动 |
| 网关 | 随 Loon 启动 | 关 | 已关闭。防止以后插入网线自动改写局域网网关/DHCP |
| 系统 | 登录时启动 Loon | 关 | 可选。需要开机即代理时再开；不影响当前运行 |
| 系统 | 系统代理 | 开（Loon 默认） | 保留开启。TUN + 系统代理同时工作，覆盖只认系统代理的 App；若遇到重复代理/端口冲突再关 |
| 日志 | 自动删除日志 | 7 天 | 保留。排障时临时调 debug，结束恢复 info |
| 通知 | 节点异常 / 策略匹配异常 / 脚本事件 | 开 | 保留。网关/DHCP 未启用时可关掉对应通知减少噪音 |

## 2. 已做的高级调整

1. **STUN 放行**：移除 `PROTOCOL,STUN,REJECT` 与 `DEST-PORT,3478,REJECT`。
   实测 Google STUN `19302` 收到真实响应；`udp-fallback-mode=REJECT` 仍在，
   节点不支持 UDP 时不会回落 DIRECT。代价是 WebRTC/STUN 可探测公网出口；
   需要更严格隐私时加回两条即可（会断语音/视频）。
2. **SNI 辅助规则匹配**：保持开启。它是 Host 为 IP 时仍能命中域名规则的关键，
   对 IP 直连广告和分流都有收益。
3. **网关随 Loon 启动关闭**：网关功能本身保持关闭；当前没有有线接口，
   `网关启动失败：未检测到可用的以太网连接`。等接入有线并确实需要 Mac 做局域网网关时，
   再开「启用网关」和 DHCP，先确认不会与主路由 DHCP 冲突。
4. **插件版本兼容**：见 §3，Mac 0.x 的插件版本元数据问题已用本机缓存兼容层解决。
5. **中银积分365 放行**：`jf365.boc.cn` 是中国银行官方积分查询/兑换商城，旧 ads
   清单误收。已从 ads 数据移除并加负向门禁；主配置 `[Host]` 对其显式 DoH 解析，
   兼容尚未更新的旧插件。实测解析到真实 IP，HTTPS 200。
6. **Mac 插件收敛到 39 个**：移除 soda、douyin、BiliBili ADBlock（macOS 无对应
   App 或作者明确不支持），Loon 插件页不再出现「不支持的操作系统」；
   公开配置仍保留 42 个供 iOS/iPad/TV，`make-private-config.py --platform macos`
   可复现。`--platform tvos` 仍是 3 个零 MITM 插件。
7. **插件新版 Rewrite/Script 已生效**：Mac 0.5.0(1011) 实测插件缓存里的
   `request if ${url} ... then reject(...)` 会执行。kelee 淘宝
   `mtop.taobao.idle.home.welcome` 返回合成 404、`film.life.popup.get` 返回
   合成 200 `{}`，同域对照路径真实 200；MITM 280 / Rewrite 282 / Script 250
   均由仪表确认加载。早先 Mac 1009 的插件新 Rewrite 不执行问题在 1011 已修复。
8. **IPA 广告端点跨端补齐**：IPA 审计里的 8 个域名
   （`api-adservices.apple.com`、`mtadservice.com`、`vads.bankcomm.cn`、
   `adashx.m.taobao.com`、`s-adashx.ut.taobao.com`、`ads.m.taobao.com`、
   `simba.taobao.com`、`topshow.taobao.com`）此前只在 Mac 私有增量里，
   现已进公开主配置，iOS/iPad/TV 不依赖 kelee 下载也能拦住。
   JD/Taobao 的路径级 Rewrite 仍留在 Mac 私有档：它们需要新增
   `api.m.jd.com` / `acs.m.taobao.com` MITM，证书固定风险未在真机证伪，
   不贸然扩大公开解密面。

## 3. Mac 0.x 插件版本兼容

现象：Loon for Mac 显示 `0.5.0(1011)`，插件声明 `#!loon_version=3.5.1(983)` /
`3.5.2(996)`，Loon 用展示版本 `0.5.0` 与 `3.x` 比较，把几乎所有插件标成
「Loon 的版本过旧，插件功能受限」。构建号 1011 实际高于 iOS 3.5.2(996)，
且插件功能已实测可运行，这是版本比较的误报。

处理（只改本机插件缓存头，不改插件逻辑/远端/CA/订阅，自动备份）：

```bash
python3 tools/mac-plugin-compat.py --apply
```

- 默认 dry-run；`--apply` 把缓存头写成当前 Mac 版本 `0.5.0(1011)`。
- 只处理声明支持 macOS 且要求构建号 ≤ 1011 的插件；更高要求会 SKIP。
- 备份在 `~/Loon-backups/<时间>/plugin-caches/`。
- 执行后重启 Loon；外部资源页的「Loon 版本过旧」应消失。
- 执行过「更新全部外部资源」后，远端头会恢复，重新跑一次即可。
- `soda` / `douyin` 仍显示「不支持的操作系统」：它们只声明 iOS/iPadOS，
  macOS 没有对应 App，这是正确的平台限制，不是版本问题。

## 4. Script 验证限制（2026-11-01）

- 插件新版 **Rewrite** 已实测执行（淘宝 idle 合成 404 / film popup 合成 200）。
- Script 绑定已计入仪表（Script 250），但受控的主配置 response Script 测试
  （本地文件路径、本地 HTTP、404 与 200 响应各一次）都没有改写 body；
  kelee 的远程脚本 CDN 当前 403，无法用其做独立对照。
- 因此当前只能确认“Script 绑定被加载”，不能确认 Mac 0.5.0(1011) 主配置
  response Script 的最终执行。下一步应使用可公开访问的远程脚本 + Loon 脚本日志
  复核；在结论出来前不要把 Script 当作已验证的覆盖层。

## 5. 不默认开启及原因

| 功能 | 不默认开启的原因 |
|---|---|
| 网关 / DHCP | 需要有线以太网；会改局域网 DHCP/网关，和主路由冲突时影响全家设备 |
| 系统代理 | 当前保持 Loon 默认开启；若只想 TUN 可关，出现重复代理/端口冲突时优先关它 |
| 不作为默认路由 | 会让大量流量绕过 Loon，去广告/分流失效 |
| 策略切换时关闭连接 | 切节点会断下载/通话；隐私要求极高时再开 |
| IPv6 | 当前节点/网络以 IPv4 为主；开 IPv6 需重新验证 AAAA、Fake-IP 和 UDP |
| TLS 指纹改 Chrome/Safari | 可能触发银行/支付风控；无 TLS 风控证据前保持 OpenSSL 默认 |
| DoH3 / DoQ | 历史日志 DoH3 1043 次失败、DoQ 5236/5239 失败；保持关闭，DoH 兜底 |
| 登录自启 | 可用但不是代理正确性的必要条件；需要常驻再开 |
