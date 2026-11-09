# 真机验证清单（重装/更新后照单走）

> 适用：`soda.plugin`（当前 3.2.0）/ `douyin.plugin`（当前 0.9.0）；`ads.plugin`（当前 2.8.10）见 H 节。
> 构建门槛：soda/douyin 需 Loon 3.5.1(983)+，**gzip 响应清理需 988+**（`$utils.ungzip`），低于 988 只记录状态；ads 与全部 App 插件**不再声明 `#!loon_version`**（`#!system` 覆盖 macOS，Loon for Mac 的营销版本号是独立一条线 `0.5.0(1011)`，iOS 口径门槛在 Mac 上语义未定），功能基线仍是 App Store 正式版 **3.5.2(996)**；`DOMAIN-WILDCARD` 仅 TF 3.5.3(1008)+ 有，保持默认注释层。
> 红线重申：净化/观测层默认生效、零改写；自动化层（签到 / 激励任务重放 / 自动领取 / 广告秒播，
> 3kaiu 方案）是独立显式开关，默认值见各插件 `[Argument]`，开启前先读插件 README 的副作用说明。
> 支付、账号安全与推送链路一律零接触。

## A. 发布与导入

- [ ] 登录有写权限的 GitHub：`gh auth login --hostname github.com --git-protocol https`
- [ ] `cd loon-plugins && python3 tools/publish.py --with-source --dry-run`（核对将上传清单）
- [ ] `python3 tools/publish.py --with-source --yes` 正式发布（连 src/、docs/、README 一起同步）
- [ ] `python3 tools/check-remote.py` → 期望 `✓ 远端与本地完全一致，Loon 里刷新插件即可生效`
- [ ] Loon：删除本地旧插件 → 添加：
      - `https://raw.githubusercontent.com/AshNail/plugins/main/plugins/soda/soda.plugin`
      - `https://raw.githubusercontent.com/AshNail/plugins/main/plugins/douyin/douyin.plugin`
- [ ] **排障首查项（本轮文档对差新增）**：某条 `[Host]` 黑洞不生效时，先看订阅是否下发 `[Host]` / `[DNS]` 段——官方《节点订阅》页明写「订阅 Host Map 加载后合并到当前 Host Map，并**优先于主配置**」。顺序口径：Rewrite/规则是「本地 > 插件 > 订阅」，Host Map 里订阅压过主配置，插件 [Host] 与订阅 Host Map 的相对顺序**官方未写**，遇到同名映射冲突属未定义行为，只能真机证实（先换订阅、再怀疑正则）。
- [x] **主配置通配 Host 压过插件精确黑洞（2026-11-01 macOS 实测）**：主配置写 `*.qq.com = server:119.29.29.29` 等 17 条 `server:` 通配映射时，插件里的 `wxa.wxs.qq.com = 127.0.0.1` 不生效——`curl` 仍拿到真实服务器 302/404/403；删除这 17 条后，同一批主机全部变成 5s 超时黑洞，`wxsnsdy.wxs.qq.com` 直接 `127.0.0.1`。结论：**Host 不是「越精确越优先」**，主配置宽通配会赢；主配置 `[Host]` 应保持精简，指定解析器用 DoH 形态并只写单域，不要写宽带 `server:` 通配。
- [x] **Remote Rule 镜像全 404（2026-11-01 实测）**：`ws.wenn.in/main/Mirror/rules/loon-{China,Global,Advertising,Privacy,Hijacking,Epic}.list` 六条全部 404。已改为 blackmatrix7 上游 `raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Loon/<类>/<类>.list`，策略与 tag 不变；重启后六份 `.lsr` 重新下载（China 2056 / Global 6218 / Advertising 26870 / Privacy 821 / Hijacking 6734 / Epic 588 字节），DNS 与广告回归正常。从旧 `.lcf` 备份重建配置时注意同步替换这些死 URL。
- [x] **红线域全量抽测 0 误杀（2026-11-01 实测）**：对 `src/apps/*.json` 的 111 个红线域逐个 `dig`，修复前有 5 个解析到 `127.0.0.1`：`ads.privacy.qq.com`（微信广点通合规入口）、`dns.jd.com` / `janapi.jd.com`（京东 HTTPDNS/数据网关）、`resolver.msg.xiaomi.net`（米家推送/解析）、`fockrt.yuewen.com`（阅文 fock 文件服务）。公开配置和 Mac 私有配置都加了 local `DIRECT` 精确放行，并删掉 `fockrt` 自相矛盾的 REJECT；修复后 111/111 无 DNS 黑洞，5 个域 HTTPS 均返回真实响应（404/200/401）。广告与正常域回归通过。
- [x] **银行规则误杀清理（2026-11-01 实测）**：公开配置原有 10 条无 banks 插件证据的 REJECT，其中 `creditcard.bankcomm.com`（交行信用卡主站）、`switch.cup.com.cn`（银联支付切换）、`cdn1.mbs.boc.cn`（中行移动银行 CDN）、`ads.95516.com`（插件明确默认关，重试风暴）等可能直接断业务。已全部移除，银行广告只保留 banks 插件证实的 `mbads.paas.cmbchina.com`、`ads.cup.com.cn`、`alliance.com.corpqueue.net` 三条。公开规则 497→487，Mac 私有 535→525。
- [x] **中银积分365 误杀修复（2026-11-01）**：`jf365.boc.cn` 是官方积分查询/兑换商城（中行公告明确），旧 ads 数据误收。已从 ads cn_union 移除、lint 加负向门禁，ads 升到 2.8.5；公开/私有主配置 `[Host]` 增加显式 DoH 解析，兼容旧插件。实测真实 IP、HTTPS 200。
- [x] **Fallback 空组修复（2026-11-01）**：策略页曾显示 `Fallback · 暂无可用子策略`，而 Final/Streaming/AI/Developer/Gaming/Social 都把 Fallback 作为可选子策略；已补入订阅节点组 `东京`。重启后策略页显示 10 组 / 31 节点，Fallback 选中 `hy2-main-JP`，无空组。
- [x] **规则集合核对（2026-11-01）**：规则页显示 8 个集合 / 521 条规则；国内域名 DIRECT、国际域名 Proxy、广告域名 REJECT、隐私保护 REJECT、反劫持 REJECT、Epic Games Proxy，兜底 Final。6 条 Remote Rule 均已加载，不再有 404 空订阅。
- [x] **STUN 放行（2026-11-01 实测）**：Mac 私有配置曾有 `DOMAIN-KEYWORD,stun,REJECT` 排在具体 STUN 放行规则之前，已删除；进一步移除 `PROTOCOL,STUN,REJECT` 与 `DEST-PORT,3478,REJECT` 后，Google STUN 收到真实响应（WhatsApp 3478 仍受网络/节点限制）。已对齐 Loon UI 的「允许 STUN」，公开与私有配置都放行 STUN，保留 DoT/DoQ 端口阻断和 `udp-fallback-mode=REJECT` 防直连泄漏；需要更严格 WebRTC 隐私时再加回这两条，代价是语音/视频通话。

- [ ] **⚪ `#!version` / `#!openUrl` 取证（第二十轮登记的两个未文档化头字段）**：官方 Plugin 页把插件信息字段列成一张明确的表，共 11 个（`name` `desc` `author` `homepage` `icon` `system` `system_version` `loon_version` `date` `tag` `type`），**没有 `#!version`，也没有 `#!openUrl`**（`openUrl` 只是 `$notification.post(..., attach)` 的字段）。我们 16 个插件都带着这两行，取证两条：
      ① 看 Loon 插件卡片/详情页是否显示 `#!version` 的值（本仓库当前 `ads=2.8.23`、`soda=3.3.2`、`douyin=0.9.1`，与 `#!date` 不同，一眼可辨）——显示＝Loon 认它，把 `tools/loon-coverage.py` 的 `m-version` 升回 `used`；不显示＝纯社区惯例，可以删（不影响任何拦截行为，但按纪律先登记再动手）；
      ② 在插件列表点该插件的「打开/详情」入口，看是否跳到 `#!openUrl` 指向的 README——跳转成立则 `m-open-url` 升回 `used` 并保留；不成立则删掉该行（`#!homepage` 已指向仓库主页，功能不缺失）。
      两处结论都拿到后，同步改 `tools/loon-token-audit.py` 的 `UNDOCUMENTED` 例外表与 `tools/loon-coverage.py` 的期望档；只改文档不改工具会被 `--check` 拦下。

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
- [ ] **固定证书止损判据（2026-11-05 20:25:48 已取证，逐台数三个计数）**：
      `SNI`（`Find a tls connection from tun. sni:<host>. alpn:`）/ `Match`
      （`Match MITM host:`，两种形态 `host(host)` 与 `IP(host)`，括号里都是 SNI）/
      `fail`（`H2 MITM TLS handshake failed`，签名 `ssl/tls alert certificate unknown`、
      err 167773206、`0A000416`）。三者**相等**就是固定证书，不是「静默不生效」：
      `polaris.zijieapi.com` 26/26/26、`aweme.snssdk.com` 8/8/8、`zlink.ugsdk.cn` 6/6/6、
      `ads5-normal-gl2.zijieapi.com` 5/5/5。同窗口只有 `gspe1-ssl.ls.apple.com` 与
      `configuration.ls.apple.com` 解密成功且零失败 → Loon CA 已被系统信任，
      「用户没装证书」这条排除。`ads5-normal-gl2` 的 Match 是靠
      `[MITM]` 的 `ads?-normal*.zijieapi.com` **通配**命中的 → 「MITM hostname 不支持通配」这条也排除。
      后果与纪律：这三台（polaris 属抖音侧、aweme 属汽水侧）的连接是我们掐断的，
      落在它们身上的响应改写一律只许说「已注册、固定证书未解除前不生效」，
      不许说「已净化 / 已拦截 / 已签到」；`docs/rule-effectiveness.md` 里它们的审计状态不变是**应该的**——
      那个工具只审 `[Rule]`/`[Host]` 的形状与红线，没有 TLS 语义，固定证书的判定只活在
      插件注释、两份 README 和本条里。止损动作（默认不执行）：从 `[MITM]` hostname 删掉这些主机，
      `[Rule]` 对应 QUIC 回退行与只命中它们的绑定一起注释；汽水的 `sign_in_done` / `sign_in_detail`
      两行不必整行注释，保留 `api.qishui.com` / `beta-luna.douyin.com` 两条腿即可。
- [ ] **零流量不等于结论**：同窗口 `beta-luna.douyin.com` / `ad.zijieapi.com` /
      `lianmengapi.snssdk.com` / `praisewindow.ugsdk.cn` / `api.qishui.com` / `conf.qishui.com`
      一次 SNI 都没有。三个方向都不许推：不是「已生效」，不是「被固定」，也不能反过来当成
      「插件没用」——福利/激励链路恰好全在这些主机上，所以这一轮日志**无法**给自动化定性，
      要复测就得真的把 App 的福利页点开（F 段第一条的冷启 3 次不够）。
- [ ] **⚪ 未文档化 token 取证（第十九轮登记的两个，见 `docs/loon-coverage.md` 传输层）**：
      `h2 = true` 与 `hostname` 行首的 `%APPEND%` 在官方 26 个正文页里**一个都查不到**
      （`MitM` 页参数表只有 `hostname` / `ca-p12` / `ca-passphrase`）。它们仍留在 soda/douyin 的生效行里，
      但已从「已用」口径摘出——因为**我们不知道 Loon 认不认**。三条取证：
      ① **未知键会不会让整段失效**：临时在主配置 `[MITM]` 写一行 `zzz = true`，
          再看插件的 `hostname` 域名是否仍被解密（脚本日志 `[soda]` 出现＝仍在解密）。
          若整段被丢弃，说明 Loon 对未知键的处理不是「忽略该行」，`h2 = true` 必须立刻删除；
      ② **`%APPEND%` 到底追加了什么**：先在主配置 `[MITM]` 留一个用户自己的域名 `mine.example.com`，
          导入 soda 后访问它——仍能解密＝追加语义成立（`%APPEND%` 有用，删掉会覆盖用户名单）；
          不能解密＝插件的 `hostname` 本来就是合并生效、`%APPEND%` 只是死 token（可删，但要另测一版对照）；
      ③ **`h2` 有没有实际作用**：删掉 `h2 = true` 复测一次冷启，脚本日志与拦截条数不变＝它确实只是保险。
      三条结论写回本文件与 `tools/loon-coverage.py` 的 `why`；取证前**不改这两行插件写法**（两种猜测的后果都不确定）。
- **严谨**：另一台设备开热点 + Wireshark 抓包，冷启并播放广告，观察 UDP:443 占比应接近 0。

## G. 回传材料

1. `check-remote.py` 尾部 `✓` 行
2. 冷启日志 3 段（含 splash 拦截行）
3. C 步任务标题日志行
4. D 步面板时刻截图（含时间戳）
5. E 步两条通知行为截图
6. （做了 F）旁路判定结论一句话

## H. ads.plugin（DNS 层 + DOMAIN-WILDCARD 默认注释层）

- [ ] Loon 版本 ≥ **3.5.2(996)**（App Store 正式版即可导入）；插件页版本为 2.8.6
      （此前 2.6.0 把门槛抬到 3.5.3(1008) 会挡住正式版用户；2.7.0 已降回正式版，
      `DOMAIN-WILDCARD` 通配/家族两层改为**默认注释**，正式版用户保持注释、其余全量生效。）
- [ ] 规则页看不到生效的国内公共 DoH/DoT：`dns.alidns.com`、`doh.pub`、`doh.360.cn` 等 9 条整组为 `# ` 注释，
      默认只生效海外 48 条。**主配置用域名形式 `doh-server`/`doq-server` 时不要开启本组**——那会把
      Loon 自己的解析打到 127.0.0.1（签名：`dns.alidns.com Host Map IP:127.0.0.1` 高频出现，见 I/I2 节）。
      确需开启：先把主配置 dns/doh/doq 全改 IP 形式，再逐行去掉行首 `# `。
- [ ] 规则页默认看不到生效的 `DOMAIN-WILDCARD,...`（都是 `# ` 注释行）；广告子域拦截由 `[Host]` 逐条承担
- [ ] **仅 3.5.3+（TestFlight build 1008–1011）用户**：逐行去掉通配层行首 `# ` 后，再验通配层独立取证
      （与 [Host] 区分开）：挑一个**只命中 glob、不在 [Host] 清单**的域，
      Safari 访问 `http://ads.loon-wildcard-probe.com/`，日志应出现
      `Search rule by host:ads.loon-wildcard-probe.com` 且策略判为 REJECT——这才证明
      DOMAIN-WILDCARD 在**插件 [Rule]** 里生效（官方 domain_rule 页只写 build 1008+，未明示插件可用性；
      未取消注释、或 3.5.2 正式版上此项不适用，那些域仍在 [Host] DNS 阶段被黑洞）。
- [ ] 共享主域本身不受通配层影响：`example.com`、`graph.facebook.com`、`doh.dns.apple.com` 正常解析
- [ ] **Mintegral / Rayjump（2.4.0 新增）**：装有 Mintegral 聚合的工具/小游戏类 App，开插件后
      该 App 的广告位应无填充。判读方法：Loon 日志过滤 `rayjump`，应出现
      `net.rayjump.com` / `setting.rayjump.com` / `analytics.rayjump.com` 走 127.0.0.1。
      若日志里一次都没有，说明这个 App 没接 Mintegral（正常），不是规则失效。
- [ ] **Rayjump 的副作用**：`analytics.rayjump.com` 是 Mintegral 的统计通道，拦掉会连它的
      埋点一起断——这正是要的效果，但会让该 App 的「广告收益/填充率」在后台看起来更差，
      不必当故障。
- [ ] 刷穿山甲奖励前确认 `ad.zijieapi.com` 不在任何广告插件的 Host 黑洞里（ads.plugin 2.8.4 起已移除）；刷优量汇/快手奖励仍需临时禁用 `ads.plugin`
- [ ] 误伤广告左标签业务时，删除对应 `DOMAIN-WILDCARD` 行即可单条回滚，无需卸载插件
- [ ] **不该拦的**：`adtiming.com`、`smaato.com`、`ogury.com` 是官网域，**故意不在清单里**。
      如果你在别处看到有人加，那是猜的——真实请求走 AdTiming 私有端点 / `smaato.net` / `ogury.io`。
- [ ] **4 条 `USER-AGENT` 规则是否真的会命中（第八轮存疑项）**：默认配置下 ads 插件
      没有 `[MITM]` 段，而 UA 是 HTTP 请求头、未解密时看不到，这 4 条很可能命中数为 0。
      判读方法：①日常使用时翻 Loon 请求日志，看有无 `USER-AGENT` 规则的命中记录；
      ②若要确证，临时给 ads.plugin 加 `[MITM] hostname = *`，对比加之前/之后的命中数。
      **从 0 变为 >0 即证明默认配置下不生效**，届时删除或把 UA 特征并入域名层。
      验证前不要因为「写了就以为生效」——它们目前只是成本为零的兜底。
- [ ] **IPv6 / AAAA 旁路（第九轮发现的唯一「有手段未落地」项）**：`[Host]` 里全部生效黑洞
      **全部只映射 IPv4**（127.0.0.1）。要确认两件事，顺序不能反：
      ① **多行共存**：临时加两条
      `probe.example = 127.0.0.1` 和 `probe.example = ip-mode:v4-only`，
      看 `probe.example` 的 A 记录**是否仍是 127.0.0.1**。
      ——如果变成真实 IP，说明 Loon 一个域名只认最后一条，**补 ip-mode 会把黑洞覆盖掉**，
      那样这条旁路只能靠主配置 `ipv6-vif = off`，且必须保持不补。
      ② **旁路是否真存在**：只写 `probe.example = 127.0.0.1` 一条，查它的 AAAA。
      返回空 → 没有旁路，什么都不用做；返回真实 IPv6 → 旁路成立，
      且在①通过的前提下才批量补 `ip-mode:v4-only`。
      ③ **若①失败（一个域名只认最后一条）**：不再碰 `[Host]`，改给同一域名补一条
      `DOMAIN-SUFFIX,probe.example,REJECT`，看 v4/v6 是否都拒。域名规则在解析前命中、
      不看地址族，这是唯一不依赖未知语义就能落地的封法。
      **取证前提（第十八轮更正）**：官方 `ip-mode` 取值只有 `v4-only`/`dual`/`prefer-v4`/
      `prefer-v6`/`v6-only`；本仓库旧版写的 `ipv4-only`/`ipv4-preferred`/`ipv6-preferred` 是错的，
      非法行会被 Loon 直接忽略——照旧写法测出的「A 记录仍生效」属**假阳性**，
      会让人误判成「多行不共存」。已在 `docs/loon-native-first.md` §15.2 与 `tools/bypass-audit.py` 更正。
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
      **2.8.0 起插件侧已默认处置**：阿里云/DNSPod/360 共 9 条国内公共 DoH/DoT 移入 `doh_public_cn`
      默认注释组，域名形式主配置不再被本插件黑洞；车主配置保持域名形式也能正常解析。
      判读要认这个签名：`Host Map` 高频命中 `dns.alidns.com`/`doh.pub` = 本插件旧版本或手动开组，不是 App 在绕过。
      **2026-10-29 的 23 小时窗口升至 17073 + 11239（见 I2）**——这正是 2.8.0 撤回默认的原因。
- [!] **激励与广告域的按路径拆分（2026-10-31 修正）**：`ads5-normal-hl.zijieapi.com` 等开屏/信息流分片仍被 ads `[Host]` 黑洞；
      `ad.zijieapi.com` 已移出全局黑洞，由 soda/douyin 的 `blockAdDomains` 按路径放行 `inspire / inspire_preload / marketing_done`。
      若抓包里这些路径仍是 status 0，先查是否还有别的广告插件在 Host/DNS 层拦 `ad.zijieapi.com`。
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
      只有 `protocol:2`（h2），未观测到 QUIC。结论：仓库当时的 18/16 条 QUIC 回退（汽水侧 v3.2.0 起增至 25 条）在该网络**没触发也没误伤**；
      F 段「回退是否发生」仍待一个真实走 QUIC 的网络环境复测。
- [!] **新发现：加密 DNS 链在海外蜂窝基本瘫**（ads 插件 `[General]` 的 doh/doh3/doq 均为境内服务）：
      `h3://223.5.5.5` 285 次查询 210 次空回复（74%）、`h3://223.6.6.6` 280/201（72%）、
      `https://223.x` 亦 69~71% 空；`nghttp3 initial write failed / read packets failed` 数百次；
      `1.12.12.12` 被 DNSPod 限流（响应 429 Too Many Requests，Loon 日志的 base64 报文已解码确认）。
      Loon 并行等齐全部服务器（`waiting for remaining responses:9`），空回复不返回结果但**返回慢**。
      **判决：默认配置不动**（目标用户在国内，AliDNS 境内最优）；海外用户按 H 节口径自行替换
      doh-server/doh3-server 为就近 anycast 解析器，或干脆注释掉 doh3 行——插件自用的黑洞/拦截逻辑不依赖它们。
- [ ] 顺带观察：`DNS failed: Invalid packet length:162` ×2（单发噪声，未复现即不处理）。

## I2. 真机日志取证（2026-10-29，23 小时 / 113 MB）

环境：同一台 iPhone（iOS 27.2，en_SG），Luna 21.4.0（build 100214010）。
样本：`2026-10-29 10:39:55.log`，1,538,207 行 / 113 MB，覆盖 10-29 10:39 → 10-30 09:37。

- [x] **luna 主机已搬去 beta-luna**：按 `Search rule by host:` 统计，两主机共 886 条请求，
      其中 luna 787 条——`beta-luna.douyin.com/luna/*` 784 条、`api.qishui.com/luna/*` 3 条
      （全是不承载广告的 `commerce/ecommerce/order_list`）；另有 99 条非 luna 请求。
      soda 2.8.5 的 34 条 api 单主机 luna 绑定在这 784 条上命中 0，整版只靠两条 beta-only
      task/page 绑定命中 1 条——这是 v2.8.6 双主机绑定的直接证据
      （修复后同一份日志回放 149/787；剩余 638 条 luna 请求是 `me/`、`media-stats/`、`comments/` 等非广告面，故意不绑）。
- [!] **同宿主跨插件竞争**：787 条 luna 请求里有 43 条同时命中 douyin 插件的响应绑定；
      Loon 对同一响应只跑第一条命中的脚本。**同时装两个插件时，清理开关只开在一个插件里**
      （详见 `plugins/soda/README.md` 10.6 节）。
- [x] **DoH 互害放大**：28,547 次 `Host Map IP:127.0.0.1`，涉及 13 个主机；
      `dns.alidns.com` 17073 次 + `doh.pub` 11239 次 = 28,312 次（99.2%）。
      连带两条上游共 10,389 次 DoH 连接失败、5,239 次 DoQ 建立尝试（5,236 次失败）与
      9,389 次 `NGQUIC-CLOSE host=127.0.0.1`（6,576@443 + 2,813@853）。
      处置：2.8.0 已把 9 条国内公共 DoH/DoT 默认注释，主配置保持域名形式也不会再被黑洞；
      若手动开启 `doh_public_cn` 组，必须先按 I 节把主配置的 DoH/DoQ 全改 IP 形式。
- [x] **QUIC 噪声**：9,389 次 `NGQUIC-CLOSE host=127.0.0.1`（6,576@443 + 2,813@853），
      是被黑洞 DoH/DoT 走 QUIC 时的必然结果，不是插件规则误伤。
- [x] **HTTPDNS 防绕过**：`DOMAIN-KEYWORD,httpdns,REJECT-DROP` 110 次命中，该组保持默认开启。
- [x] **红线零误伤**：13 个被黑洞主机对 137 个受保护主域（103 手写 + 34 由 App 红线派生）0 命中；
      110 条 App 红线没有一条被 DNS 黑洞碰到。
- [x] **Pangle 分片**：`ads5-normal-hl.zijieapi.com` ×12、`ad.zijieapi.com` ×2 被黑洞；
      与 soda/douyin `splash-ad` 的请求层拦截互补（一个挡 DNS，一个挡请求）。
- [!] **起点可选层判读**：`magev6.if.qidian.com` 出现 `Match MITM host:` 20 次但 0 条拦截——
      那是 v3.1.0 的注释基线形态；**v3.2.0 起 `[MITM]`+`[Script]`+`[Argument]` 已默认生效**，
      解密≠拦截这条判读仍然成立（路径级 `URL-REGEX` 那一层按纪律保持注释态，条数见 J2 节）。
- [!] **别把主配置记在插件头上**：`api3-lq.qishui.com` / `api5-lq.qishui.com` 各 73/74 次 MITM，
      但那一版 soda 插件没声明这两个主机，也没有对应的 `Search rule by host:`——
      那是用户主配置自己的 MITM 名单，不参与本清单判读。**v3.2.0 起 soda 已把这 7 台
      分片（api3/api5 × hl/lf/lq + conf5-lf）写进 `[MITM]`**，所以今后判读要先对 `#!version`：
      插件自己声明了的解密面才归本仓解释，没声明的一律算主配置。
- [x] **汽水 API 分片取证通道（v3.3.1 撤出，结案）**：`api3/api5 × hl/lf/lq` 与 `conf5-lf` 这 7 台曾进 soda 的 `[MITM]`（v3.2.0~v3.3.0）。2026-11-06 16:21:50 日志（Loon 3.5.3(1014)）回答了原清单的三个问题：① `Match MITM host:api5-lf.qishui.com` 等行出现、解密面确实铺开；③ **`certificate unknown` 出现了**——`api5-lf` 186 次、`api3-lf` 30 次、`conf5-lf` 5 次、其余各 2 次，7 台共约 227 次握手 100% 失败，= 证书固定，汽水 App 因此「全部提示网络错误」。原清单「两份日志零次」的推断是幸存者偏差（那时这些主机没进 hostname，根本没发生过解密）。**处置已按本条预案执行**：7 台从 `[MITM]`、QUIC 回退（25→18 条）与 `Accept-Encoding` 降级一并退出，lint 的 `QUIC_HOSTS` 同步去掉。**复测**：升级到 3.3.1 后打开汽水，搜索/播放/换歌应不再弹网络错误；日志里 `qishui.com` 不应再出现 `Match MITM` 与 `H2 MITM TLS handshake failed`（`api.qishui.com`/`beta-luna.douyin.com` 除外）。重新纳入的前置条件：先证明固定已绕开。
- [x] **有意的数据缺口**：638 条非广告 luna 请求未绑定；没有“全 luna 都处理”的假宣告。

## J. 19 个 App 专属插件（2026-10-28 起，源 `src/apps/`）

- [ ] 逐个导入 `plugins/<slug>/<slug>.plugin`，装后完全退出并重开目标 App。
- [ ] **生效判读**：日志里命中域应显示 `Host Map IP:127.0.0.1`（插件 [Host] 的特征字样，区别于主配置的 `Reject domain ... in DNS phase`）。
- [ ] **wechat**：朋友圈/视频号广告位应「素材空白、占位保留」；`wxsnsdy*`/`wxsnsad` 出现在日志即素材黑洞命中。微信收发、支付、公众号文章正常。
- [ ] **meituan**：开插件跑一遍下单+支付+地图+直播——`appsec-mobile`/`api-unionid`/`api-map`/`shark`/`ddplus` 不应出现在任何拦截日志；若 `impdsp`/`mads` 有命中且交易无恙，B 组（waimai_ad/d_meituan_net）可逐条试开。
- [ ] **banks**：六行各开一次 App，重点验云闪付支付与招商账单——`ads.cup.com.cn` 命中后银联主链路（`wallet.95516.com`）必须无恙；unionpay_optional 组只在无转账需求时试开（重试风暴风险见插件注释）。
- [ ] **zhihuifangdong**：门锁操作（ttlock）与推送（getui）无恙；开屏/插屏广告加载失败即 pangle/gdt 组命中。
- [ ] **mijia**：设备控制（`api.io.mi.com` 系、`*xmpush*` 推送、`resolver.msg.xiaomi.net` 解析、`*.micloud.*`/`app.chat.xiaomi.net` 云与对话、`api.sec.miui.com`/`data.sec.intl.miui.com`/`avlyun`/`avast` 安全族）必须无恙——这些是本插件 `redlines` 逐条登记的域，绝不出现在拦截日志。
- [ ] **jd**：`dsp-x`/`ads-union`/`ccc-x` 命中即广告交易层生效；商品图（`360buyimg`/`img-x`）不得白图，下单/搜索签名（h5st）/登录/客服/推送必须无恙。首页/信息流广告不保证消失（素材与商品同 API 同图床）；`jd_ad_watchlist` 与 `jd_telemetry` 默认关，先在日志确认域名再试开。
- [ ] **zhihu**：开插件验证知乎自建遥测/分析（`zhihu-web-analytics`/`sugar`/`crash2`/`udd1i5`）命中 `127.0.0.1` 零证书黑洞；热榜、推荐、关注信息流正常，问答、文章、个人页无白屏；`passport.zhihu.com` 登录与 `lc-push.zhihu.com` 推送无恙。可选增强层（12 条 REJECT-DICT）在导入证书并取消注释后，信息流与回答页穿插广告静默绝育（返回 200 + 空字典），搜索预置词清空。
- [ ] **bilibili**：开插件验证哔哩哔哩遥测/播放器埋点/HTTPDNS（`dataflow.biliapi.com`/`data.bilibili.com`/`tracker.chat.bilibili.com` 系 / `httpdns.bilivideo.com`）命中 `127.0.0.1` 零证书黑洞；登录（`passport.bilibili.com`）、视频播放、直播、私信长连接正常；首页信息流广告、开屏、搜索推广正常消失后功能无恙。可选增强层（4 条 `response.json.jq` + 1 条可选 `REJECT-DICT`）在导入证书并取消注释后生效：开屏配置 `data.show` 置空、首页推荐流过滤商业卡片（cm_v2/cm_double_v9）。
- [ ] **amap**：开插件验证高德地图自建日志遥测/阿里 UT 埋点（`logs.amap.com`/`dualstack-logs.amap.com`/`amap-aos-info-nogw.amap.com`/`adashx.ut.amap.com` 系）与商业广告域（`optimus-ads.amap.com`）命中 `127.0.0.1` 零证书黑洞；逆地理编码（`apsrgeo.amap.com`）、基站定位（`cgicol.amap.com`）、路线规划主网关（`restapi.amap.com`）与轨迹服务（`ts.amap.com`）正常无恙，地图定位、搜索与导航正常。可选增强层（7 条 URL-REGEX）在导入证书并取消注释后生效：开屏 alimama 广告、首页推荐流、路线规划下方推广卡片与订单页面推广信息绝育。
- [ ] **qqnews**：开插件验证腾讯新闻开屏与各频道列表无广告；`news.ssp.qq.com`（开屏/配置主网关）与 `r.inews.qq.com`（要闻/频道/专题业务 API）内容加载正常，新闻正文与评论无恙。可选增强层（2 条 response.json.jq）在导入证书并取消注释后，列表 `adList` 置空，专题 `widget_list` 过滤广告 widget。
- [ ] 红线交叉验证（ads × `jd`/`mijia`）：`src/apps/*.json` 的 `redlines` 把 `dns.jd.com`（京东自建 HTTPDNS）、`union.jd.com`（京东联盟站）与 `resolver.msg.xiaomi.net`（小米推送/米家解析通道，出处是 `mijia.json` 台账「推送/云红线」的 `resolver.msg.*`，不在 `comment` 里）划为绝不进拦截组，`tools/build-ads.py` 因此拒绝把它们放进任何默认生效组，三者现在只存在于 ads 的「与按 App 插件红线冲突的候选」注释组。取证两步：①同时导入 ads + `jd` + `mijia`，确认日志里**没有**这几条的 `Host Map IP:127.0.0.1`，京东搜索/下单/图片正常、米家设备控制与消息推送正常；②逐行取消 `# ` 打开它们后重开这两个 App，观察是否出现「转圈/搜索无结果/白图/设备离线/收不到推送」——若一切正常，说明它们确实回退系统 DNS，可把对应条目挪回默认生效组并同步改该 App 的红线与本清单（挪回去要先删红线，门禁会当场拒绝无红线的激活）。没做完这两步之前，别凭「成熟清单也拦」推断无副作用。
- [ ] **qidian/xianyu/x/instagram**：预期收益低（内联广告），判读以「遥测域消失 + 业务无恙」为准，不以「广告消失」为准。
- [ ] **bubei-danci** 不背单词：本插件**没有广告 SDK 组**——官方 SDK 目录 `https://learnywhere.cn/lexis/sdklist` 里没有穿山甲/优量汇/快手/百青藤，变现是酷币与会员内购，所以这里的「去广告」实际是去跟踪。判读：`ns.360wgjs.com`（站外埋点，anti-AD/PiT 等三家清单收录）从日志消失；学习链路 `learnywhere.cn`（API + 例句音频）、`bbdc.cn`、声通评测 `isuntone` 必须无恙。**`umeng` 组默认关**：`umeng.com` 整域拦会把统计 + U-Push + 一键登录一起断（签到提醒、号码认证同断），只在「不在乎推送、只要隐私」时开。
- [ ] **youtube**：可选 MITM 启用后，推荐/播放 JSON 中广告字段应消失；视频播放、登录、缩略图正常；`googlevideo.com` 不得被 DNS 黑洞或请求拒绝。Mac 当前不执行 response jq，需 iOS/iPad/TV 验证。
- [ ] **taobao**：DNS 组应命中 h-adashx/ossgw/hudong 等精确广告域；可选 MITM 的 11 条 URL-REGEX 启用后，搜索、下单、购物车、支付必须无恙，`acs.m.taobao.com` 与 `guide-acs.m.taobao.com` 不得被 DNS 黑洞；广告图片路径应返回 1px 图。
- [ ] **mba-dashi** MBA大师：开屏走穿山甲、课程列表插屏走优量汇（两家 SDK 由官方隐私政策确认）。判读：冷启开屏广告加载失败、课程列表插屏消失即 pangle/gdt 组命中；红线 `www/m/file/video.mbajm.com` 全是讲义、课程、视频链路，绝不允许出现在拦截日志。**代价**：App 内「看广告领课程」依赖这些 SDK——启用即断该活动，属预期而非故障。
- [ ] **ruankao-tong** 软考通：同为 pangle + gdt（`ixinz` 系）。判读：开屏与课程列表插屏加载失败即命中；红线 `www.ixinz.com` 与 `*.s2.ixinz.com` 是课程/题库内容分发域，不得出现在日志。官方隐私政策只给 SDK 包名不给域名，域名按两家 SDK 公开集成文档补齐（B 级）；题库内容与广告同源不可分，「看广告解锁真题」启用即断。崩溃上报（`shenzhou` / `crash.ixinz`）为第一方自建、网络层无从区分，故不列。
- [ ] **以上两款共有的口径**：`mba-dashi` / `ruankao-tong` 的 `[Host]`/`[Rule]` 是全设备生效（Loon 无法按 App 限定），同一 SDK 域跨 App 共享黑洞——「按 App 插件」只是分组开关；测试时若别的 App 也报广告加载失败，那是同一批域在起作用，不是插件写错。配合全局 ads 插件的 httpdns 组防绕过。
- [ ] 默认关的组（watchlist/telemetry/amdc/waimai_ad/d_meituan_net/unionpay_optional/jd_ad_watchlist/jd_telemetry 等）试开前，先在日志确认对应域真实出现——没出现就开了也没有收益。

### J2. MITM 增强层（meituan/xianyu 文末整段默认注释；qidian 自 v3.2.0 起默认启用）

不装证书 = 本层永不生效，上面各项判读不变；启用与否、启用几条完全自愿，随时可回滚（重新注释即回到原状）。

- [ ] **前置**：Loon → 证书管理 → 生成/安装 CA → iOS 设置里「通用→关于→证书信任设置」打开完全信任；无证书时取消注释也无效，先装证书再改规则。
- [!] **qidian（v3.6.1 形态）**：`[Argument]` + `[MITM]` + `[Rewrite]` + `[Script]` 四层已**默认写进生效配置**——不再需要取消 `[MITM]` 注释，`hostname = %APPEND% magev6.if.qidian.com, mage.if.qidian.com, h5.if.qidian.com` 直接生效；`[Rewrite]` 只留 17 条 request 阶段 `reject_dict(200)`（不碰响应体），10 条脚本绑定由 `[Argument]` 控制（净化 `QDREADER_CLEAN_ENABLE=true` 默认开、自动化六开关默认开；Token/Cookie 捕获由独立开关 `QDREADER_COOKIE_ENABLE=true` 门控）。限时激励任务（mainPage 的 `ReadingPageTaskModule`，TaskType 300/「【限时】广告·加点！」）不再剪枝：当轮 TaskId/Total 写入持久化键 `Qidian_LimitedTasks`，看播 `finishWatch` 命中后由引擎按 Total-1 次重放自动完成（脚本日志 `识别任务: 限时激励:… , 重放 N 次`）。v3.3.0/v3.4.0 那 14 条 `response.json.*` 复写在 v3.5.0 整层撤回：2026-11-06 14:34 日志里命中复写的 47 条请求挂起中位 20s、最长 75.7s，15 条以 `kCFStreamErrorDomainSSL Code=6` 断连收场，而未命中的 165 条全部 0s 完成。**所以判读前置换成了证书**：Loon 没装/没完全信任 CA 时，这三台主机不是「没生效」而是 TLS 直接失败——起点打不开就是这条，先装证书再评估。「起点 Pro」克隆件已随 v3.6.0 退役删除，本仓不再分发，不再有双开问题。验证（对着 v3.5.0 的四个回归点逐条打勾）：①**我的页**必须出内容，不再「网络错误」；②底部 tab 必须是 3 个，「发现」不再回来（`NewFeedsDiscover=0` 走脚本侧 getconf 覆写）；③福利页的**限时福利(`SurpriseBenefit`)必须保留**；VideoRewardTab 的正常激励（完成 N 个广告任务得奖励/白泽装扮）与 `ReadingPageTaskModule` 的 6 条「【限时】广告·加点！」也全部保留（v3.6.1 起不再剪任务条目，自动完成走 finishWatch 重放）；④冷启动开屏广告秒过、书架悬浮广告/每日推荐位消失、我的页内测推广与书架置顶推广消失；正文阅读、评论、支付必须无恙（**听书不在「必须无恙」名单里**——owner 口径 2026-11-06「打死吧，我不需要听书」，`audio_tts` 组 9 条 `[Host]` 默认生效把播放链断在 DNS 阶段，日志里看到它们 REJECT 是预期，要恢复听书注释这 9 条即可）。若条目还在，把 `QDREADER_DEBUG` 打开抓一条 `福利中心 removed=[…] kept=[…] 任务条目=N [paths]` 锚点回来——那两类条目是按标题关键词剪的，锚点会报出实际字段路径。路径级 `URL-REGEX`（12 条）仍按仓库纪律保持注释态——正文与广告位同主机，**解密不等于拦截**；要额外拦路径才取消注释并移进上方已生效的 `[Rule]` 段（配套 3 条 QUIC 回退已生效）。
- [ ] **meituan**：MITM 主机 9 个（`wmapi/apimobile/p?.meituan.net/flowplus/img/feedguess/mt-personalcenter/assistify/mop`），响应 jq 8 条（tab/推荐流/我的页/搜索词/AI skills/购物车 banner/启动图），默认全注释、逐条启用。验证：开屏广告消失、启动不再拉 `openscreen?ad/startpicture`；广告图路径命中后应看到 1px 图（`REJECT-IMG` 200 + GIF，不是 404）且商品图正常；下单、支付、地图、外卖全程无恙——任何一步异常即整段回滚（该 App 交易链路敏感，红线高于收益）。
- [ ] **xianyu**：本层有三块——`# [MITM]`（2 主机）、`# [Rewrite]`（15 条 `response.json.jq`）、`# [Rule]`（2 条 QUIC 回退 + 2 条 `URL-REGEX`，拦 `splash.ads`/`idle.ad.expose`）。建议顺序：先只开 `[MITM]` + QUIC + 两条 `URL-REGEX`，验证开屏广告消失且发布、下单、聊天、扫一扫无恙；再开 `[Rewrite]` 里**一条** `group.myself.banner`（`.data.bannerList = []`，最保守），确认群聊页 banner 消失、消息列表正常、响应仍是合法 JSON；第二步试 `item.recommend`（只删 mamaAD）与三条占位规则（`user.strategy.list` / `search.shade` / `search.activate`）；最后再试「只留 item/业务分区」的激进规则：`home.nextfresh`、`search.search`、`local.home`、`search.discover`、`item.buy.feeds`、`item.recommend.list`，以及最激进的 `user.page.my.adapter`（我的页面只留 head/user/trade 分区）。任一规则导致白屏/接口报错，只重新注释该行即可回滚；整体异常（登录转圈、全局接口报错）则整段恢复注释。**若 jq 规则全无效果，先怀疑 Loon 没执行 jq（响应压缩/内容类型不满足），不要改正则硬试**——mtop 网关被解密本身就改变连接形态，本层对该 App 定位是「实验」。
- [ ] **共同回滚判据**：银行/支付/门锁等红线域绝不允许进 `[MITM]` hostname；增强层启用后若 App 报「网络异常/证书错误」，说明该 App 实际做了固定或检测，接受现实、整段恢复注释（插件注释已声明此可能）。

## K. MITM 名单收敛与插件 `[General]` DNS（2026-11-02 macOS 实测）

- [x] **主配置与插件 `hostname` 是合并生效**：主配置只写少量主机时，插件声明的 `music.163.com` 仍被解密（TLS 签发者为 Loon CA）；未列入任何名单的 `example.com` 返回真实 Cloudflare 证书。判据用 `openssl s_client` 看 issuer，不要看 `curl` 的 HTTP 状态（被解密与否都可能 200）。
- [x] **主配置独有主机要逐条找消费方**：从 `[Plugin]` 的启用 URL 算 MD5 映射到 `remotePlugin/<md5>.lpx`，解析每个插件 `[MITM] hostname`（去 `%APPEND%`、跳过 `-` 排除）取并集；主配置里不被并集覆盖、且插件 Rewrite/Script/Rule 文本与主配置 `[Rewrite]/[Script]` 都不引用的主机，才可判孤儿。示例：私有 Mac 配置 50 个正包含 → 18 个（32 个孤儿删除），61 个排除项全部保留；`ad.zijieapi.com`、`beta-api.m.jd.com` 因主配置 Rewrite 命中而保留。
- [x] **证书验证**：重启隧道后对每个删除项跑 `echo | openssl s_client -connect <host>:443 -servername <host> 2>/dev/null | openssl x509 -noout -issuer`；真实 CA＝已退出解密，`O=Loon`＝仍在名单（检查插件是否声明或配置未重载）。
- [x] **macOS 重启隧道**：Loon for Mac 不注册 `loon://` scheme，退出 App 也不会重启网络扩展；用 `scutil --nc stop "Loon for Mac"` → `scutil --nc start "Loon for Mac"` 才会重载 `Loon.lcf` 与插件缓存。改动前备份 `Loon.lcf`，回滚即恢复备份后再重启 VPN。
- [x] **插件 `[General]` 会追加 DNS**：启用插件的 `dns-server` / `doh-server` / `doh3-server` 是追加而非替换。实测 All-in-One 追加了 `h3://223.5.5.5`、`h3://223.6.6.6` 与 `1.12.12.12`，会在主配置已清理 DoH3 后重新引入；排障时先 grep 插件缓存的 `[General]`，再怀疑主配置。若删除缓存里的这些行，先备份 `.lpx`；「更新全部外部资源」会恢复远端版本。
- [x] **不要用 UI 的 MITM 计数判断主机数**：清理后 TLS issuer 已按主机变化，但首页「MITM 228」计数未同步；以证书签发者与插件缓存名单为准。
- [x] **只读审计工具**：`python3 tools/mac-mitm-audit.py` 列出主配置独有 MITM 主机及插件缓存/主配置消费证据，`--json` 可机器读取。候选判断是启发式的（如 `(?:beta-)?api.m.jd.com` 这类可选前缀正则），删除前仍要按上一条做证书验证。

## L. 分流结构审计（2026-11-03 macOS 实测）

- [x] **只读工具**：`python3 tools/mac-routing-audit.py` 检查本地 `[Rule]` 的 FINAL 位置、重复行、端口/协议规则是否落在 IP 规则之后、域名是否被更早的宽规则遮蔽、策略组是否未定义；`--json` 机器可读，`--check` 有发现时 exit 1。
- [x] **现网结果**：Mac 私有配置 540 条本地规则 / 10 个策略组；FINAL 唯一且在末条，0 重复、0 端口/IP 倒序、0 域名遮蔽、0 未定义策略。公开配置 511 条同样全绿。
- [x] **远程规则**：6 条 `[Remote Rule]` 分别绑 DIRECT / Proxy / REJECT；工具只汇总 policy，不打印远程 URL。
- [x] **边界**：该工具只做结构检查，不判断业务策略是否最优；`url-test` 只测延迟，不能发现“延迟低但吞吐崩”的节点（2026-11-03 实测：唯一存活 HY2 节点 189ms，但 Cloudflare 下载仅 4–7 KB/s；两条 VLESS 均 Timeout）。节点吞吐问题应更新订阅/换线路，不要改规则顺序。
- [x] **远程规则集红线审计**：`python3 tools/remote-rules-audit.py` 拉取 blackmatrix7 的 Advertising / Privacy / Hijacking 三套 REJECT 规则，对照 122 条 App 红线并检查本地 DIRECT 覆盖。当前 Advertising 有 3 条京东红线关键词（kepler.jd.com / mapi.m.jd.com / policy.jd.com），均由本地精确 DIRECT 规则覆盖；实测 HTTPS 返回真实 302/403/404。远程清单更新后必须重跑，出现无本地覆盖的红线命中时工具 exit 1，不要删除本地覆盖行。

- [!] **起点 v3.5.2 判死（2026-11-06 20:02 日志）**：v3.5.2 那句「force-gzip 后 Loon HTTP 引擎会解压成 UTF-8 字符串再交脚本」是没成立的前提。20:02:17.log 里 18 条 `[Rewrite]` 全在 request 阶段命中（id 28 = 那条 `Accept-Encoding` 复写，343 次；id 29–45 = 17 条 reject），响应侧 `起点getconf净化 match=6 / Trigger=6`、`起点深度净化 match=39 / Trigger=38` —— 脚本跑了、没挂流（全日志 0 次 75.00s、仅 2 次 Force closed），而真机 UI 仍报「没净化」。机制见 `tests/test_qidian_sanitize.js` 头部登记的 16:21:50 日志：不带 `binary_body_mode` 时 gzip 体是 UTF-8 硬解的乱码串，`1f 8b` 检测失效、`JSON.parse` 必抛、`safeJsonParse` 返回 null ⇒ 全端点 passthrough。
- [!] **起点日志判读口径修正（2026-11-06 21:05 日志，v3.5.3 上线后第一份）**：这份日志把「能证明的」和「结构上证明不了的」划清了。能证明：传输层彻底不挂（0 次 75.00s、1 次 Force closed、57 次 `Transform to http1.1` 全部正常释放）、`[Rewrite]` 层活着（id:28 命中 191 次、id 29–45 的 17 条 reject 命中 54 次）、净化绑定在跑（`起点getconf净化` match=4/Trigger=4/Finished=4，`起点深度净化` 29/27，MITM 命中 magev6/h5 8 次）。证明不了：**整份日志 0 条 `[起点锚点]`，而 24 个插件的脚本 console 输出同样 0 条** —— Loon 只在绑定 `with debug=true` 时才把脚本 console 落主日志，我们写的是 `debug=${debugLog}` 且默认 false，所以「看不到 changes=N」既不是失败证据也不是成功证据，v3.5.2/v3.5.3 两条判死里凡是靠日志锚点说话的部分都降回「靠 UI + 机制推定」。顺带作废一条本轮读出来的假信号：`Trigger→Finished` 的 0ms vs 999ms 二态**不是**脚本工作量——同一端点（`reddot/getdot?positionMark=BOTTOM_TAB`）两种值都出现，且 999ms 严格贴着 1s，是 Loon 异步 `$done` 的刷写节拍；主日志里的脚本时长没有判读价值。
- [!] **起点 v3.5.4 判死（2026-11-06 21:35 日志，v3.5.4 上线后第一份）**：本轮押的两件事一件成立、一件推翻。成立：净化绑定确实在跑——按 (conn,req) 归并后 `起点深度净化` match=20/Trigger=19/Finished=19、`起点getconf净化` 2/2/2、`起点Token捕获` 4/4/4，全日志 0 次 75.00s，装载行 `Load 1974 rules. 257 scripts. 106 rewrites.` 与 21:05 那份逐字相同；`X-Qidian-Plugin` 头部也仍是唯一不依赖 console 的自证面。推翻：**「绑定带 `debug=true` 就能把脚本 console 落主日志」不成立** —— 两条净化绑定的 `debug` 本轮已常开，主日志仍 0 条 `[起点锚点]`（七份日志 10:19/10:54/13:09/14:15/20:02/21:05/21:35 全为 0）。官方 Script API 的口径是 `console.log` 「向**当前脚本日志**写入一条记录」：主日志（能导出的这份）结构性不含脚本 stdout，锚点只能在 App 内的脚本日志页看，21:05 那条「Loon 只在绑定带 debug 时才落主日志」的推定作废。连带作废的还有 v3.5.1/v3.5.3 那句「回字符串会被 Loon 静默丢弃」：手册明写 `$done().body` 接受字符串**或** `Uint8Array`，且「修改响应 Body 后 Loon 会根据传输协议处理 Content-Length、Transfer-Encoding 和 Content-Encoding 等相关 Header」——`respondJson` 的形态镜像保留（对两种头语义都无害），但它不再是「唯一可能生效的写法」。同一份日志还做了竞争排除：全日志 `http-response script:` 只有起点自家三个 tag，且起点流量只命中 id 28–45（request 阶段），所以「同一响应最多选择一条 Response Script」与「Response Body Rewrite 命中时 Response Script 不执行」这两条短路在本机都不适用。
      · 第一优先看 HAR（或任一代理检视器）里净化端点的响应头：有 `X-Qidian-Plugin: qidian-sanitize;b=3.5.4;in=u8` ⇒ 脚本走到了 respondJson，且 Loon 给的是字节；`in=str` ⇒ binary_body_mode 没生效；**整个头没有** ⇒ safeJsonParse 仍返回 null，净化没跑到底；
      · 脚本锚点 `[起点锚点] b=… changes=N` 只在 **App 内脚本日志页**（Loon → 日志/脚本日志，绑定带 debug 才留）可见，导出主日志里永远搜不到；判 changes=N 请用 App 内脚本日志，别再用主日志判；
      · 若看到 `body=[str:…]` + `json parse=ok str len=…` ⇒ 这次上游没压，净化同样生效，不必切路线 B；
      · 若还是 `json parse=fail str` ⇒ 回滚单位＝删这两条的 `binary_body_mode=true`（v3.5.3 那一行），改走路线 B：把 `force-gzip` 复写的值改成 `identity`（放弃压缩，soda 侧实测明文膨胀 5~10 倍，起点这几个接口体量小可接受）；
      · 取证期结束后回滚单位＝删这两条的 `debug=true` 键（脚本侧 anchor 段与 `X-Qidian-Plugin` 头可留，前者体量小、后者本来就一直在）；
      · UI 口径不变：发现页顶栏 3 个 tab、我的页功能区 5 项且无营销卡、福利页只剩激励任务与限时福利。
- [!] **起点 v3.5.5 判成一半（2026-11-06 22:06 日志，32 秒冷启动）**：tag 指纹立刻见效——主日志出现 `match http-response script:起点深度净化v355`×17 / Trigger=16 / Finished=16、`起点getconf净化v355` 2/2/2、`起点每日阅读积分` 2/2/2、`起点Token捕获` 4/4/4，`id:28` 命中 110 次、id 29–45 命中 31 次、0 次 75.00s。于是**「设备装的是哪一版」第一次可机读，且答案是「远端最新版确实装上了」**——日志里没有 per-plugin 版本行（`Load plugin:起点读书 · 看书激励助手` 只有名字，`pluginHashes=24` 只有数量），此前「没更新」和「更新了但看不到」不可区分，现在排除了前者。锚点仍 0 条，与 console 判死一致。同一份日志也确认主日志**结构上给不出送达形态**：全文 0 次提到 `content-encoding`/`gzip`，没有任何一行会打印脚本改的 body 或 headers，所以 identity 改写有没有生效只能问设备本身——这就是 v3.5.6 把证据改从通知出口的原因。下面这条复测的判读顺序仍然适用（把 tag 名换成当前 build 后缀）。
- [ ] **起点 v3.5.5 复测（build 号进 tag + 过期压缩头就地改写；净化字段规则本身经 HAR 核对无误）**：本机 10:28 的 69MB HAR（`440_1793932089145.har`，Loon 存的是已解压 base64 明文，直接 `json.loads` 即可）逐字段对过净化规则——`getaccountpage` 的 `FunctionButtonList` 13 项 `PositionMark` 与保留白名单 5 项逐字命中、`BenefitButtonList` 6 项（福利中心/活动中心/我的阅历/卡牌广场/周边商城/游戏中心）与 9 个删除键全对得上，`getconf` 168 个 `Data` 键里 `PangleEnable/ActivityIcon/ActivityPopup/LuckBag/ClassicBookInfo/ClientLocalNotify2/PushDialogScenes/RewardSatisfyDialog/FansClubPropInfo/AdVideoPositionConfig/GDT` 确实存在 ⇒ **规则内容不是短板**。本轮两处改动：① `respondHeaders` 对过期的 `content-encoding`/`content-length` 改为**就地改写原键名**（`identity` + 新体字节数），不再 `delete`——手册没保证 Loon 对脚本给的 headers 是替换还是合并，合并语义下删键＝不改，原始 `Content-Encoding: gzip` 会套在明文新体上，App inflate 失败后静默回落本地缓存（起点把 `getaccountpage/reddot/getdot` 明确列进 `CacheIsolationPathList`），这正是「脚本跑了、字段改了、UI 一动不动」的形状；原键不存在时绝不发明新头。② `getconf-clean`/`deep-clean` 的 tag 变成 `起点getconf净化v355`/`起点深度净化v355`（tag 是字面量、且会原样出现在主日志的 match/Trigger/Finished 行里）——三版 Load 计数完全不变、日志也没有任何 per-plugin 版本行（只有 `remoteHashes=7 pluginHashes=24` 这种数量），「没更新」与「更新了但看不到」此前在日志上不可区分。判读顺序：
      · **先看主日志有没有 `script:起点深度净化v355`**：还是旧名 ⇒ 插件根本没更新（重新导入 + 详情页刷新外部脚本缓存），后面全部作废；
      · 再看 HAR（或任一代理检视器）里净化端点响应头：`X-Qidian-Plugin: qidian-sanitize;b=3.5.5;in=u8` ⇒ 脚本走到了 `respondJson` 且拿到字节；`in=str` ⇒ `binary_body_mode` 没给字节；**整个头没有** ⇒ `safeJsonParse` 仍返回 null；
      · 同一个响应里 `Content-Encoding` 若还是 `gzip`（而 body 已是明文 JSON）⇒ 就是「Loon 合并头」这条洞，本轮改写正是为了堵它，此时 UI 应开始变化；
      · 同一个头的 `;n=<N>` 就是本次字段变更条数（getconf/账户页/福利页三处上报），HAR 里直接读；App 内脚本日志页的 `changes=N` 是同一件事的另一份抄本，主日志结构上没有；
      · 若 tag 已是 v355、头部 `in=u8`、`Content-Encoding: identity` 三样齐了 UI 却还是老样子 ⇒ 传输与解析两条线都判死，剩下的只有 App 侧缓存/CDN 回源，改走「冷启动 + 卸载重装后首启」再判，或按缺口扩面（下条）；
      · ~~已登记但**本轮没动**的净化面缺口~~ **22:15 结案：这几条不是缺口，扩面是错的**（10:28 HAR 逐端点看体）：`widget/getContent` 只有 `Data.CheckInInfo`（签到组件：`HasCheckInToday/BreakDays/ShowText/ActionUrl`），删掉就是打掉签到入口本身；`bookshelf/getHighLevelBookReadInfo` 这份 HAR 里 `Result:-301 未登录`、连 `Data` 都没有；`widget/daily/rec` 是每日荐书正文（`DailyReadingUnionPage` + `Day/Month` 阅读时长）；`client/ostar` 的 `Data` 是一段 84B 加密位（`{"code":0,"data":"KlR0TnGOrnxDl4eae4SWYw=="}`），没有可剥字段；`v3/client/r1` 的 `Data:0`。可莉 `QiDian_remove_ads.lpx` 同样没碰 `widget/*` 与这几条——三家公开规则 + 本机 HAR 都对齐了 ⇒ 起点在这些路径上没有营销面。**唯一还挂着的一条**：`checkin/simpleinfo`（10:28 那份 HAR 里没有它的样本，所以既不能定罪也不能洗白，等有体量的 HAR 再说）；
      · 回滚单位：`respondHeaders` 的 `write()` 两行 + 两处 tag 的 `v355` 后缀。UI 口径不变：发现页顶栏 3 个 tab、我的页功能区 5 项且无营销卡、福利页只剩激励任务与限时福利。
- [!] **起点 v3.5.6 复测（取证出口换成锁屏通知）**：净化逻辑与规则内容一行未动，只加一个出口——`respondJson` 在回写前调 `forensicNotice()`：插件的「调试模式」(`debugLog`) 开着、且本次净化有变更计数（getconf / 账户页 / 福利页三处上报）时，用 `$notification.post` 把 `b=<build> in=<形态> n=<条数>` 直接推到锁屏，标题带端点路径，`$persistentStore` 记上次时间做 **15s 节流**（一次冷启动最多一两条）；透传路径（`safeJsonParse` 返回 null ⇒ 没走到 `respondJson`）一律不推。这样不用 HAR、不用翻 App 内脚本日志：**打开插件的「是否开启调试模式」，用一遍起点，看锁屏/通知中心**。判读三分叉：
      · 通知出现且 `n>0`，UI 却还是老样子 ⇒ 脚本确实改到了字段、Loon 也确实回了包，剩下的只有 App 侧（本地缓存 `CacheIsolationPathList` / CDN 回源），按「卸载重装后首启」再判一次；
      · 通知出现且 `n=0` ⇒ 解析成功但当前规则没有可改字段（版本漂移的第一信号），下一步是按 HAR 抓一份真实 `getconf`/`getaccountpage` 对键名，而不是继续动传输层；
      · tag 已是 `v356`、调试模式开着、`起点深度净化v356` 在日志里 match/Trigger/Finished 齐全，却一条通知都没有 ⇒ 三处 `respondJson` 一个都没走到，即 `safeJsonParse` 仍返回 null，直接切路线 B：把 `force-gzip` 复写的值改成 `identity`（放弃压缩，起点这几个接口体量小，明文膨胀可接受）；
      · 完全没有通知且通知权限没给 ⇒ 这条通道失效，退回 HAR 判读（头部 `X-Qidian-Plugin: ...;b=3.5.6;in=...;n=...`）。
      回滚单位 = 删 `forensicNotice()` 函数与 `respondJson` 里那一行调用（`n` 计数与头部 `;n=` 可留）。
- [x] **起点 v3.5.6 判读（2026-11-06 22:15 日志，33 秒）＋「广告拒绝层」第一次实证生效**：① 版号对上了——`起点深度净化v356` match=19/Trigger=19/Finished=19（**四份日志里第一次一条不漏**，21:05 是 29/27、22:06 是 17/16）、`起点getconf净化v356` 2/2/2、`起点每日阅读积分` 2/2/2、`起点Token捕获` 4/4/4，`id:28` 命中 121 次、id 29–45 命中 36 次、0 次 75.00s、锚点仍 0 条（与 console 判死一致）。通知通道在导出日志里天然不可见（全日志只有 1 行 `Schedule task notification`，脚本侧 `$notification.post` 不落任何行），所以 v3.5.6 那一刀只能由设备回答：调试模式开没开、锁屏有没有「起点净化取证」那条。② **新读出一条能单独定罪/定量的机制**：正常流在 request 读完后必打 `[H2Tunnel-c/r](n) Request ended before remote selected. ruleSearchs:8 state:67 cacheBody:0 url:…`（这行就是此前的 URL 普查依据，80 条起点流量全出自它），而**被 request 阶段 `reject_dict(200)` 终止的流永远走不到这行**——按 (conn,req) 归并后，36 条命中 id 29–45 的流里 0 条有 URL 行、0 条 `Create h2 remote socket`、0 条 `start submit h2 request`、0 条响应头行、0 条 script 行：终止发生在选远端之前，广告请求根本没出本机。反证同样干净：全日志 204 条 URL 行、50 个唯一 URL，**没有一条**落在 17 个 reject 路径上（`getsplashscreen/getTopOperation/bookshelf/getad/iosad/playstrip/push/getdialog/hotWords/showChapterEndModule/young/getconf/freshman*/recommendBook/getclassicbookinfo/getactivitylist/popup/batchget/message 三条/adv/getadvlist*/getfloatcard`）。⇒ 「拒绝层未验证」这个挂了三轮的判定作废，**[Rewrite] 层 request 拒绝实证生效**；「日志给不出哪些端点被拒」由这组双向对账补上（能定量、能证伪，只是给不出被拒 URL 的明文名单）。③ 上一轮登记的「净化面缺口」按 HAR 逐端点看完体量后判定**不是缺口**（详见 v3.5.5 复测那条的划线条目），扩面是错的方向；剩下唯一未定性的是 `checkin/simpleinfo`（HAR 无样本）。至此传输、装载、版本、解析前提、拒绝层五件事全部排干，净化面剩下的唯一未知只有一个：**真机 UI 到底变了没有**。
- [!] **设备答复回来了，v3.5.6 判死（2026-11-06 追问，owner 现场）**：「调试模式打开了，通知一条都没有，广告也没去掉」。按我自己上一轮写的三分叉，这一支的结论是**三处 `respondJson` 一次都没走到**，也就是 `safeJsonParse` 返回 null——断点在响应体解析链，不在传输层、不在规则内容、不在插件装载。于是上一句「唯一未知」也要修正：UI 只是**第一项被排除**，因为这条通知通道当时**只在成功侧推**（`if (!DEBUG || BODY_OUT.n < 0) return;`），「解析失败」与「解析成功但没字段可改」在设备上同形，零通知并不能区分「脚本没被调到」和「调到了但解析崩了」。同轮作废一条更早的口径：**`Finished execute` 齐全不能证明脚本内部没抛异常**——v3.5.2 那次 TDZ ReferenceError 正是从 catch 里空 `$done()` 走掉、日志照样打 Finished，所以 19/19/19 从来不是「解析成功」的证据。
- [ ] **起点 v3.5.7 复测（路线 B：identity + 失败侧也推）**：两处改动，都不动净化字段规则。① `[Rewrite]` 的 `force-gzip` 改名 `force-identity`，复写值换成 `Accept-Encoding: identity`。依据是本机 16:21 日志已经证明「写 gzip 上游就真回 gzip」⇒ 上游照客户端声明走，那写 identity 就拿到明文，`binary_body_mode` / `$utils.ungzip` / 手写 UTF-8 解码这三层真机未确认的前提直接从主路上摘掉（gzip 分支与 `binary_body_mode` 留作「CDN 无视 identity」的兜底）；identity 同样消掉脚本解不动的 br/zstd，且比 gzip 更彻底。代价是这几个 Argus 接口明文膨胀 5~10 倍，单机可接受。② `forensicNotice()` 换成 `forensicReport(kind, detail)`：**ok 与 fail 各占一个 15s 节流键**，失败侧把「字符串体 parse 失败 / ungzip 抛错 / ungzip 缺失 / 不认的 object 形态 / 明文与 gzip 字节体 parse 失败（附首段 24 字符）」原样推到锁屏。③ `safeJsonParse` 的对象早退收紧：原先「不是 Uint8Array/ArrayBuffer 的对象」一律当已解析 JSON 原样返回，运行时桥接来的二进制包装一旦 `instanceof` 认不出，下游就是 `obj.Data === undefined` 的静默透传、或被 stringify 成 `{"0":31,…}` 的坏包；现在只认数组与朴素对象，其余判失败并报出去。tag → `v357`。判读三分叉（这次互斥且各自可行动）：
      · **两条通知都没有** ⇒ 脚本根本没被调到（绑定 URL 正则或 MITM 命中问题），下一步查 `match http-response script:起点深度净化v361` 是否还在；
      · **只有 fail** ⇒ 明文也没解动，`detail` 直接指名是 parse、ungzip 还是形态不认，按那条继续收；
      · **有 ok 且 `n>0` 而 UI 仍不动** ⇒ 净化链完整、Loon 确实回了包，剩下的只有 App 侧（`CacheIsolationPathList` 本地缓存 / CDN 回源），按「卸载重装后首启」再判一次；
      · 通知权限没给 ⇒ 这条通道失效，退回 HAR 看 `X-Qidian-Plugin: ...;b=3.5.7;in=...;n=...` 与响应头 `Content-Encoding`。
      回滚单位：`force-identity` 那一行的值换回 `gzip`（一行）+ `forensicReport` 的 fail 侧调用（`tools/build-apps.py` 的 `REWRITE_REQ_HEADER_RE` 已放开 identity，属长期合法形，不随回滚撤回）。UI 口径不变：发现页顶栏 3 个 tab、我的页功能区 5 项且无营销卡、福利页只剩激励任务与限时福利。
