# 真机验证清单（重装/更新后照单走）

> 适用：`soda.plugin`（当前 2.8.5）/ `douyin.plugin`（当前 0.8.5）；`ads.plugin`（当前 2.5.0）见 H 节。
> 构建门槛：soda/douyin 需 Loon 3.5.1(983)+，**gzip 响应清理需 988+**（`$utils.ungzip`），低于 988 只记录状态；ads 需 **3.5.3(1008)+**（`DOMAIN-WILDCARD`）。
> 红线重申：本仓插件**只做净化与观测**——不缩短广告、不加速播放、不改写领奖请求、
> 不做后台自动观看/自动领取。领奖链路（`incentive/done` 等全部 59 头请求）只读不动。

## A. 发布与导入

- [ ] 登录有写权限的 GitHub：`gh auth login --hostname github.com --git-protocol https`
- [ ] `cd loon-plugins && python3 tools/publish.py --with-source --dry-run`（核对将上传清单）
- [ ] `python3 tools/publish.py --with-source --yes` 正式发布（连 src/、docs/、README 一起同步）
- [ ] `python3 tools/check-remote.py` → 期望 `✓ 远端与本地完全一致，Loon 里刷新插件即可生效`
- [ ] Loon：删除本地旧插件 → 添加：
      - `https://raw.githubusercontent.com/AshNail/plugins/main/plugins/soda/soda.plugin`
      - `https://raw.githubusercontent.com/AshNail/plugins/main/plugins/douyin/douyin.plugin`

## B. 首次冒烟（5 分钟）

- [ ] 冷启汽水 ×3：无开屏广告；`blockSplashAd` 日志每次冷启命中（splash/ 与 vN/(ack/)splash/ 全家族）
- [ ] 冷启抖音 ×3（`blockSplashAd=on`）：无开屏广告，日志出现 `[douyin-splash] blocked`；激励广告与发奖链路不受影响
- [ ] 插件设置 `statusNotify=silent` → 点「插件状态自检」不弹通知、结果页仍显示「开关状态」摘要；切回 `notification` → 弹通知且横幅可跳转 App
- [ ] 自检结果页「运行环境」行与实机一致：Loon 版本（建议 988+）、脚本名与执行时间、节点、运行模式；「Loon 能力」行应显示 `gzip 解压 ✅`；若缺行/❌ 说明当前 build 不支持对应能力
- [ ] 抓包看响应头 `X-Soda-Plugin`：正常端点**不应**出现 `ce=`（只写 `skip=not-json` 说明确实不是 JSON）；一旦出现 `ce=br`/`ce=zstd`，说明服务端换了压缩算法、脚本解不了，按 README 把该端点 `Accept-Encoding` 设为 `gzip`
- [ ] 状态看板冲突提醒：临时把 `killRewardAds=on`（或汽水 `rewardSafe+cleanAds`）→ 自检结果页应出现「⚠️ 冲突：」行；改回后消失
- [ ] 首条命中提示：`cleanAds=on` 或 `treasureMinimal=on` + `debugLog=on` → 自检结果页出现「日志会被清理/精简脚本挤掉」提示
- [ ] `hideDouyinTab=on`、`cleanAds=off`：打开福利页只删【听抖音】条目，签到/听歌任务保留（证明独立绑定生效）
- [ ] 打卡副作用：`dailyReminder=on` + `cleanAds=on`（或 `hideDouyinTab=on`）→ 打开一次福利页后 `soda-welfare-seen` / `douyin-welfare-seen` 已写入
- [ ] 打开福利页：任务分区裁剪生效（treasureMinimal / cleanUpsell / cleanActivity）
- [ ] 抖音福利页日志含 `migrate_first_ad : true -> false`；`ad_api_preload.task_ids` 只保留页面任务引用的 id（当前样本 9 -> 4）
- [ ] 抖音商业化接口日志含 `freq_ctrl_cfg : removed 3 entry(ies)`（只删与已删弹窗同名的频控项）
- [ ] （可选，仅全量清理模式 `rewardSafe=off`）汽水 `commerce/v2/upsell` 日志含 `upsell_map : removed N popup(s)`；`sort_control_unique_names` / `cold_launch_timing` 里不再有 `*_ads_*`
- [ ] 播完整一条激励（15s）：日志出现「今日广告 N 次 / 共 M 秒」
- [ ] 复请求头：`X-Soda-Plugin` 含 `skip=incentive`（领奖链路零干预证明）
- [ ] 开关复核：`rewardSafe=on`（关键）；`killRewardAds=off`（`amount=-1` 证据，别开）

## C. 【听抖音】字段抓取（下一版 matcher 精确化的唯一缺口）

- [ ] `logTaskTitles=on` 临时开启 → 打开一次汽水福利页
- [ ] 把含任务标题的日志行**原样**回传（截图或复制）
- [ ] 用日志钉住精确字段 → 改 matcher → 发下一版

## D. 领奖链路复测（纯观测，勿拦截）

- [ ] 完整播一条 15s 激励：领奖面板出现时刻 ≈15.0s（复证 HAR 零死时间）
- [ ] 记录领奖响应 200 与 59 头链仍存在（`x-argus` 等）
- [ ] 全程不做任何拦截/改写

## E. 每日提醒验证（cron + 打卡）

- [ ] `dailyReminder=on`，`reminderCron=30 20 * * *`
- [ ] 当天已打开过福利页（打卡已落）→ 20:30 **不**弹通知
- [ ] 清掉 `soda-welfare-seen`（或 `/douyin-welfare-seen`）→ 20:30 弹通知
- [ ] 有清理脚本胜出时也要打卡：分别用 `cleanAds=on`、`hideDouyinTab=on`、`debugLog=on` 各打开一次福利页，确认 key 仍写入（打卡是胜出脚本的副作用，不依赖独立 welfare-stamp 绑定）
- [ ] 全部清理/隐藏/观测脚本关闭、只留 `dailyReminder=on` → 仍能打卡（welfare-stamp 兜底绑定）
- [ ] 快速验证：临时把 `reminderCron` 改到两分钟后

## F. QUIC / 证书固定旁路判读

v2.8.0 / v0.8.0 起插件自带常开 QUIC 回退（见插件 `[Rule]` 段），所以 F 段不再是“有没有覆盖”，而是“回退的代价能不能接受”。

- [ ] **回退是否发生**：冷启 3 次，Loon 引擎日志真机打印格式为 `REJECT by QUIC Fallback Protection. SNI:<域名>`
      （2026-10-27 取证：同类 `PROTOCOL,QUIC` 规则命中时以此格式打印，早先预期的 `match rule:AND,...` 格式没出现；
      本仓自己的规则当时 0 命中，SNI 需匹配到 `api.qishui.com` / `beta-luna.douyin.com` 才算数）；
      同一时刻脚本日志 `[soda]` / `[douyin-reward]` 应出现，
      说明流量已回到 TCP+TLS 被 MITM 看见。
- [ ] **首屏耗时**：对比删掉 QUIC 回退行前后的冷启时间，超过 ~500ms 或出现“网络异常”提示，就说明该域强依赖 H3
      或存在证书固定——删掉插件 `[Rule]` 里那一行即可单域回滚。
- [ ] **h2 是否友好**：若某次更新后 App 报网络错误，先删 `[MITM]` 的 `h2 = true` 再复测，用于区分
      “h2 兼容问题”与“证书固定”。
- **严谨**：另一台设备开热点 + Wireshark 抓包，冷启并播放广告，观察 UDP:443 占比应接近 0。

## G. 回传材料

1. `check-remote.py` 尾部 `✓` 行
2. 冷启日志 3 段（含 splash 拦截行）
3. C 步任务标题日志行
4. D 步面板时刻截图（含时间戳）
5. E 步两条通知行为截图
6. （做了 F）旁路判定结论一句话

## H. ads.plugin（DNS 层 + DOMAIN-WILDCARD）

- [ ] Loon 版本 ≥ **3.5.3(1008)**；插件页版本为 2.5.0
- [ ] 规则页能看到 30 条 `DOMAIN-WILDCARD,...`；广告子域（如 `ads.example.com`）在日志/DNS 检查里走 127.0.0.1 或 DNS 拒绝
- [ ] 共享主域本身不受通配层影响：`example.com`、`graph.facebook.com`、`doh.dns.apple.com` 正常解析
- [ ] **Mintegral / Rayjump（2.4.0 新增）**：装有 Mintegral 聚合的工具/小游戏类 App，开插件后
      该 App 的广告位应无填充。判读方法：Loon 日志过滤 `rayjump`，应出现
      `net.rayjump.com` / `setting.rayjump.com` / `analytics.rayjump.com` 走 127.0.0.1。
      若日志里一次都没有，说明这个 App 没接 Mintegral（正常），不是规则失效。
- [ ] **Rayjump 的副作用**：`analytics.rayjump.com` 是 Mintegral 的统计通道，拦掉会连它的
      埋点一起断——这正是要的效果，但会让该 App 的「广告收益/填充率」在后台看起来更差，
      不必当故障。
- [ ] 刷奖励前禁用 `ads.plugin`；纯去广告时再启用（与 soda/douyin 的 `rewardSafe` 互斥）
- [ ] 误伤广告左标签业务时，删除对应 `DOMAIN-WILDCARD` 行即可单条回滚，无需卸载插件
- [ ] **不该拦的**：`adtiming.com`、`smaato.com`、`ogury.com` 是官网域，**故意不在清单里**。
      如果你在别处看到有人加，那是猜的——真实请求走 AdTiming 私有端点 / `smaato.net` / `ogury.io`。
- [ ] **4 条 `USER-AGENT` 规则是否真的会命中（第八轮存疑项）**：默认配置下 ads 插件
      没有 `[MITM]` 段，而 UA 是 HTTP 请求头、未解密时看不到，这 4 条很可能命中数为 0。
      判读方法：①日常使用时翻 Loon 请求日志，看有无 `USER-AGENT` 规则的命中记录；
      ②若要确证，临时给 ads.plugin 加 `[MITM] hostname = *`，对比加之前/之后的命中数。
      **从 0 变为 >0 即证明默认配置下不生效**，届时删除或把 UA 特征并入域名层。
      验证前不要因为「写了就以为生效」——它们目前只是成本为零的兜底。
- [ ] **IPv6 / AAAA 旁路（第九轮发现的唯一「有手段未落地」项）**：`[Host]` 里 1301 条黑洞
      **全部只映射 IPv4**（127.0.0.1）。要确认两件事，顺序不能反：
      ① **多行共存**：临时加两条
      `probe.example = 127.0.0.1` 和 `probe.example = ip-mode:ipv4-only`，
      看 `probe.example` 的 A 记录**是否仍是 127.0.0.1**。
      ——如果变成真实 IP，说明 Loon 一个域名只认最后一条，**补 ip-mode 会把黑洞覆盖掉**，
      那样这条旁路只能靠主配置 `ipv6-vif = off`，且必须保持不补。
      ② **旁路是否真存在**：只写 `probe.example = 127.0.0.1` 一条，查它的 AAAA。
      返回空 → 没有旁路，什么都不用做；返回真实 IPv6 → 旁路成立，
      且在①通过的前提下才批量补 `ip-mode:ipv4-only`。
- [ ] **DoQ（UDP 853）是否真的被 `DEST-PORT,853,REJECT` 挡住**：官方 `Rule/port_rule` 页
      没有写 TCP/UDP 限定。判读：找一个能指定 DoQ 的 App/系统「加密 DNS」入口，
      指向 `dns.quad9.net`，看是否解析失败。若仍能解析，
      说明该规则只吃 TCP，确定解法是主配置 `disable-udp-ports = 853`
      （插件 `[General]` 白名单里没有这个键）。
- [ ] **公共解析器 IP 直连组（2.5.0 新增，默认关闭）**：只有当发现某个 App 直连
      `8.8.8.8` / `1.1.1.1` 做 DNS（Loon 日志里目标只有 IP、没有域名）时才需要开。
      开启**前**先确认主配置 `dns-server` / `doh-server` 里没有清单内任何 IP；
      开启**后**确认整网仍可用——误伤的表现是上不了网，不是广告回来。

## I. 真机日志取证（2026-10-27，两份 Loon 引擎日志）

环境：iPhone（iOS 27.2，en_SG）蜂窝 `pdp_ip0`；汽水音乐 Luna 21.4.0（build 100214010）。
样本窗口 16:31–20:01（约 38500 行）与 20:01–20:17（约 79000 行，含大量 fake-IP 噪声）。

- [x] **`[Host]` 黑洞真机确证**：命中格式为 `X Host Map IP:127.0.0.1`（**不是** `Fake IP:127…`，
      也不是 `Reject domain… in DNS phase`）。本窗口黑洞命中：`ads5-normal-hl.zijieapi.com` ×8、
      `dns.weixin.qq.com` ×7、`open.kuaishouzt.com` ×3、`open.kwaizt.com` ×2、
      `httpdns.meituan.com` / `httpdnsmultiapi.meituan.com`（另见 REJECT-DROP）。
      ⚠️ **纠偏**：早先登记的 `Reject domain:app-measurement.com ×145`、`api.mixpanel.com ×63` 等
      **全部不在本仓清单**——是用户主配置自带黑名单的打印，不得记在本插件头上。
- [!] **新发现：防泄漏黑洞与主配置加密 DNS「互害」（本窗口最大命中量）**：
      `dns.alidns.com Host Map` ×3360、`doh.pub` ×2193——主配置用**域名形式** `doq-server = quic://dns.alidns.com:853` /
      `doh-server = https://doh.pub/dns-query` 时，Loon 自身的解析请求同样进 TUN、同样被本插件 `[Host]`
      防泄漏组黑洞，表现为**每秒级重试、整条加密 DNS 链永远不通**。
      **处置（主配置侧，二选一）**：① 把主配置 doh/doq 改成 IP 形式（`https://1.12.12.12/dns-query`、
      `quic://223.5.5.5:853`——本插件自用链就是 IP 形式，不依赖域名）；② 注释掉 ads `[Host]` 里对应行。
      插件默认不动（对国内用户防泄漏仍是净收益），但判读要认这个签名：`Host Map` 高频命中
      `dns.alidns.com`/`doh.pub` = 主配置在打架，不是 App 在绕过。
- [!] **激励分片与 rewardSafe 的互斥真机成立**：`ads5-normal-hl.zijieapi.com` 被 ads `[Host]` 黑洞 ×8，
      同时 soda/douyin `[MITM]` 通配也在匹配它——ads 开着时 DNS 先死，`rewardSafe` 救不了「看广告领奖」类任务
      （攒时长 `ack_time` 不受影响，日志证实正常）。刷激励广告前必须停用 ads.plugin（H 节口径，现已有实锤）。
- [x] **HTTPDNS 防绕过（第八轮 REJECT-DROP）真机确证**：`DOMAIN-KEYWORD,httpdns,REJECT-DROP`
      两个窗口合计 156 次命中，目标 `103.37.152.224` / `203.107.1.1` / `119.29.29.98` /
      `180.76.76.112` 的 :80 直连——App 确实在尝试绕开 TUN DNS，且被掐断。**该组保持默认开启正确。**
- [x] **MITM 通配符真机确证（E10）**：`Match MITM host:ads5-normal-hl.zijieapi.com` ×3——
      `ads?-normal*.zijieapi.com` 一条覆盖真实 Pangle 分片，无需逐分片枚举。
- [x] **解密 hostname 正常**：`api.qishui.com` ×8、`api3-lq/api5-lq.qishui.com` ×11、
      `conf.qishui.com` ×5、`polaris.zijieapi.com`、`zlink.ugsdk.cn`、`beta-luna.douyin.com` 各 1。
- [x] **领奖链路活着**：`luna/treasure/business/ack_time` 每 5~6 分钟规律上报（18:36→18:53 三次），
      两个窗口内**没有任何脚本错误/超时**日志（`debugLog=off` 时脚本静默属预期）。
- [ ] **QUIC 回退本窗口 0 命中（待国内 Wi-Fi 复测）**：`REJECT by QUIC Fallback Protection` 出现 4 次，
      但 SNI 是 `youtubei.googleapis.com`（用户主配置的规则，不在本仓域名清单）；本窗口 `api.qishui.com`
      只有 `protocol:2`（h2），未观测到 QUIC。结论：仓库 17/16 条 QUIC 回退在该网络**没触发也没误伤**；
      F 段「回退是否发生」仍待一个真实走 QUIC 的网络环境复测。
- [!] **新发现：加密 DNS 链在海外蜂窝基本瘫**（ads 插件 `[General]` 的 doh/doh3/doq 均为境内服务）：
      `h3://223.5.5.5` 285 次查询 210 次空回复（74%）、`h3://223.6.6.6` 280/201（72%）、
      `https://223.x` 亦 69~71% 空；`nghttp3 initial write failed / read packets failed` 数百次；
      `1.12.12.12` 被 DNSPod 限流（响应 429 Too Many Requests，Loon 日志的 base64 报文已解码确认）。
      Loon 并行等齐全部服务器（`waiting for remaining responses:9`），空回复不返回结果但**返回慢**。
      **判决：默认配置不动**（目标用户在国内，AliDNS 境内最优）；海外用户按 H 节口径自行替换
      doh-server/doh3-server 为就近 anycast 解析器，或干脆注释掉 doh3 行——插件自用的黑洞/拦截逻辑不依赖它们。
- [ ] 顺带观察：`DNS failed: Invalid packet length:162` ×2（单发噪声，未复现即不处理）。
