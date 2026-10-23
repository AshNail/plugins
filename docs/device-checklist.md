# 真机验证清单（重装/更新后照单走）

> 适用：`soda.plugin`（当前 2.6.1）/ `douyin.plugin`（当前 0.7.0）。
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

- [ ] 冷启汽水 ×3：无开屏广告；`blockSplashAd` 日志每次冷启命中
- [ ] 打开福利页：任务分区裁剪生效（treasureMinimal / cleanUpsell / cleanActivity）
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
- [ ] 快速验证：临时把 `reminderCron` 改到两分钟后

## F. QUIC / 证书固定旁路判读（可选）

- **简易**：看 Loon 日志——若 `ad.zijieapi.com` / `ads5-*` 在拦截名单上仍出现广告素材
  响应或反复超时，说明存在 QUIC 旁路未被覆盖，回报即可。
- **严谨**：另一台设备开热点 + Wireshark 抓包，冷启并播放广告，观察 UDP:443 占比。

## G. 回传材料

1. `check-remote.py` 尾部 `✓` 行
2. 冷启日志 3 段（含 splash 拦截行）
3. C 步任务标题日志行
4. D 步面板时刻截图（含时间戳）
5. E 步两条通知行为截图
6. （做了 F）旁路判定结论一句话
