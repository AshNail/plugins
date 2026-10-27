# 真机验证清单（重装/更新后照单走）

> 适用：`soda.plugin`（当前 2.7.1）/ `douyin.plugin`（当前 0.7.9）；`ads.plugin`（当前 2.2.0）见 H 节。
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

- [ ] **回退是否发生**：冷启 3 次，Loon 规则日志里应出现 `AND,((DOMAIN-SUFFIX,api.qishui.com),(PROTOCOL,QUIC)),REJECT`
      （douyin 对应 `beta-luna.douyin.com`）的命中；同一时刻脚本日志 `[soda]` / `[douyin-reward]` 应出现，
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

- [ ] Loon 版本 ≥ **3.5.3(1008)**；插件页版本为 2.2.0
- [ ] 规则页能看到 30 条 `DOMAIN-WILDCARD,...`；广告子域（如 `ads.example.com`）在日志/DNS 检查里走 127.0.0.1 或 DNS 拒绝
- [ ] 共享主域本身不受通配层影响：`example.com`、`graph.facebook.com`、`doh.dns.apple.com` 正常解析
- [ ] 刷奖励前禁用 `ads.plugin`；纯去广告时再启用（与 soda/douyin 的 `rewardSafe` 互斥）
- [ ] 误伤广告左标签业务时，删除对应 `DOMAIN-WILDCARD` 行即可单条回滚，无需卸载插件
