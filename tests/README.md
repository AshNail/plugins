# SodaClean 测试

这些是**脚本层**回归测试：用 Node `vm` 加载 `src/soda/*.js`（或 terser 实际压缩版 `plugins/soda/scripts/*.min.js`），构造响应体，检查字段是否按规则裁剪。压缩版不是只改后缀：会去掉空白/注释并混淆变量名；`src/` 里保留完整原始代码。

## 运行

```bash
cd /path/to/loon-plugins
npm ci
npm run build       # 先生成 plugins/soda/scripts/*.min.js
npm run check       # build + lint + 源码/压缩版测试
```

单独跑：

```bash
npm run test:src    # 只测 src/soda/*.js
npm run test:dist   # 只测 plugins/soda/scripts/*.min.js
npm test            # 源码 + 压缩版都跑
npm run lint        # 插件结构、正则、脚本引用、脚本安全边界、压缩脚本语法
npm run coverage    # Loon 能力覆盖/利用率（155 条能力，探测真实用法）
npm run coverage:write  # 重新生成 docs/loon-coverage.md
```

`run-all.py` 默认对源码和压缩版各跑一遍；`SODA_SCRIPT_SET=src|dist`（或 `SCRIPT_SET`）由 `tests/load-script.js` 读取，`loadScript(name, family)` 可以加载不同插件族。`lint-plugins.py` 检查每个 App 唯一部署插件（`soda.plugin`、`douyin.plugin`）的 section、域名、Rewrite/Script 行数、正则编译、脚本引用（新版 `script("...")` 与旧 `script-path=`）是否指向存在的 `.min.js`、源码是否存在、压缩脚本能否通过 `node --check`，并确认压缩脚本确实比源码小且行数不超过 5 行。它还会验证：插件没有启用的静态 `[Rule]` 域名、每条脚本都带 `enable=${开关}`、开关默认值正确、`[MITM]` 覆盖 API/设置/广告域名、关键端点能被脚本正则命中、开屏绑定命中 splash 家族但绝不命中激励/发奖端点，以及 `#!name/#!desc/#!author/#!version/#!date` 元数据齐全且 `#!icon` 是 https 链接。参数 schema 由 `src/args/*.json` 单源生成，`node tools/gen-args.js --check` 保证插件 `[Argument]`、`SWITCH_LABELS` 与 README 表无漂移。

**绑定矩阵门禁**：Loon 对同一请求/响应只执行配置顺序里第一条 `enable` 为真的脚本。lint 用真实 URL 样本（soda 26 响应 + 3 请求，douyin 13 响应 + 3 请求）把每条绑定都匹配一遍，确保没有死绑定；同一 URL 上重叠的绑定必须是「同脚本 + 同参数」的等效冗余，或在 `SHADOW_ALLOWED_PAIRS` 允许清单里（清理类抢只读观测、域名拦截抢开屏拦截），否则直接报错。

**脚本安全门禁**：`src/*/*.js` 与部署的 `*.min.js` 必须调用 `$done()` 释放 Loon 的 JS 资源；禁止 `$httpClient`、`fetch()`、`XMLHttpRequest`、`WebSocket`、`sendBeacon`、`Function(`、`eval(`、`require(`；`$notification.post` 只允许出现在 `status.js` / `daily-reminder.js`；禁止 `$persistentStore.remove(`（官方语义是清空**全部**脚本数据，不接受 key 参数，删单项只能用 `write(undefined, key)`）。门禁保证插件脚本不会把抓到的响应数据外发，也不会执行动态代码。同时校验部署目录里没有未被任何 `[Script]` 绑定的孤儿 `.min.js`（删除绑定后必须同步删脚本）。

对单 ads 插件，lint 还会检查 `[General]`/`[Rule]`/`[Host]` 的顺序、General 白名单、DoH 必须使用 IP、Rule 只能 REJECT、默认注释的归因/统计组没有被误启用、共享主域保护名单、旧的三份 ads 文件确实删除，以及生成物与 `src/ads/domains.json` 逐字节一致。`DOMAIN-WILDCARD` 通配层还有独立门禁：插件头 Build ≥1008、30 条模式集合永久锁定、每条 glob 必须是 `DOMAIN-WILDCARD,<glob>,REJECT`（规则行不允许任何参数）、不命中保护名单，并用正/负样本锁定 `*` 跨点语义（`ads.*` 命中 `ads.a.b.com`，不命中 `example.com`/`adsl.example.com`；`advert.*` 不命中 `advertise.example.com`）。

`tests/fixtures/` 里放的是**真实抓包样本**（2026-10-20 HAR）：`douyin_treasure_page.json`（抖音福利页原始响应）、`soda_incentive_done.json`（汽水发奖请求/响应），用于防止“按想象改字段”。

## 断言分布

| 测试 | 断言数 | 覆盖 |
|---|---:|---|
| `test_sanitize2.js` | 19 | 通用字段清洗、包络保留、非目标端点不误伤 |
| `test_prune.js` | 13 | `incentive/config` 的 `advert_sources` / `feed_advert_config` / `preload` |
| `test_taskinfos.js` | 1 | `task_infos` 广告任务裁剪（保留签到/听歌/逛商城） |
| `test_ads_surfaces.js` | 33 | 开屏、广告位、DSP、兜底、卡片、增长入口、upsell |
| `test_soda_upsell_v2.js` | 56 | soda `upsell_map`：真实 93 弹窗样本删除广告/商城实体、奖励弹窗保留、排序/冷启动/频控同步、只带 `upsell_map` 的响应也能命中 |
| `test_treasure_prune2.js` | 15 | 福利任务、banner、弹窗、金币挂件、`commerce_ad_task` / `ad_snap` |
| `test_settings.js` | 85 | TTKitchen 设置层、BDADSDK 形态、可选 `i`/`is` 主机、AGGRESSIVE/DRY_RUN/INJECT_MISSING |
| `test_feed_flags.js` | 17 | `is_advertisement` / `ad_flag` / `adItem` / `card.is_ad` / promoted / sponsored / commercial |
| `test_feed_expand.js` | 16 | 扩展 feed 端点、`search-block` 仅 `banner_list` 场景 |
| `test_reward_observe.js` | 101 | 激励链路只读观测：计数、任务摘要、进度字段、发奖字段、upsell 入口变量、隐私过滤、大响应放行 |
| `test_block_domains.js` | 44 | 广告域名拦截脚本：开关关闭不拦、`rewardSafe` 放行、非广告域名不拦、返回 200 + JSON `{}`；7 条必中 / 4 条必不中样本锁定 Pangle 分片 glob |
| `test_douyin_upsell.js` | 46 | 真实 93 弹窗样本：广告/商城弹窗被删、奖励与兜底弹窗保留、variables 不动、排序/冷启动引用同步清理、频控表只删同名项 |
| `test_splash_ad.js` | 22 | 开屏广告请求拦截（soda/douyin 共享源双家族）：splash/ 与 vN/(ack/)splash/ 全家族被拦、返回 JSON `{}`、inspire / inspire_preload / 发奖回调绝不拦、开关关闭放行 |
| `test_soda_douyin_entry.js` | 17 | 【听抖音】入口：设置层 anchor_luna_to_douyin* 置 0、不动其它设置、保奖励模式下也能生效、与清广告配置互不干扰、`settingsClean+hideDouyinEntry` 同开一次跑完 |
| `test_douyin_activity.js` | 19 | polaris 活动配置（真实样本 181 个活动）：音乐节/抖音运营活动 canshow 置 false、其它活动不动、开关关闭原样放行 |
| `test_soda_kill_reward.js` | 12 | 断激励广告：显式 killRewardAds 才清激励素材（保奖励模式下也能清）、只开 cleanAds 时素材保持原样、广告位配置照常清理 |
| `test_soda_task_titles.js` | 7 | 只读日志带任务标题：默认不打文案、开关打开后带 title、view.title 形态也能取到 |
| `test_douyin_treasure.js` | 38 | 抖音福利页精简：只留攒时长模块、其余分区全部移除、`migrate_first_ad` 关闭、广告预拉取只留保留任务引用、开关关闭原样放行、参数对象/数组/字符串三种形态都识别、**真实抓包样本**回归 |
| `test_douyin_clean.js` | 44 | 抖音广告配置/商业化弹窗/演出清理：广告源与素材清空、`ads/retrieve` 的 `ad_launch*` / `ads_blocks` / `ads_info` 清理、商城与广告弹窗删除、排序/冷启动/频控同名项同步清理、音乐节列表清空 |
| `test_soda_task_page_v2.js` | 31 | `treasure/task/page/v2` 结构化任务判别：只摘激励广告任务、保留签到/翻卡/攒时长、预拉取只留保留任务引用、真实样本回归 |
| `test_unified_args.js` | 27 | 聚合插件开关：`rewardSafe` 优先放行非开屏端点、开屏仍清理、无参数时行为不变、设置层保护、`hideDouyinTab` 只删抖音条目且独立于 `cleanAds` |
| `test_status.js` | 46 | Generic 状态脚本：汽水/抖音打卡摘要、广告统计、开关看板与冲突提醒、脚本抢占提示、Loon 环境诊断（`$loon`/`$script`/`$environment`/`$config`/`$utils.ungzip`，含缺失与拼写兼容）、通知 attach openUrl、`statusNotify=silent` 不弹通知 |
| `test_welfare_stamp.js` | 10 | 打卡副作用：胜出脚本写 `soda-/douyin-welfare-seen`、`dailyReminder=off` 不写、cron 读取后抑制或触发通知、treasure→reminder 端到端 |
| `test_store_scope.js` | 12 | 存储作用域：删一个键不能动别的键（`welfare-seen` / `ad-stats` 必须存活），禁止 `$persistentStore.remove()`，删除走 `write(undefined,key)` |
| `test_encoding_guard.js` | 30 | 编码诊断：六个解析 body 的脚本在 `content-encoding: br` 时输出 `ce=br`，`gzip`/`identity`/无头不加噪声，头名大小写与 `gzip, br` 逗号列表，正常 JSON 不被诊断干扰 |
| `test_args_schema.js` | 37 | 参数 schema 单源：两族开关类型/默认值锁定、共享开关跨家族一致、`[Argument]` / `SWITCH_LABELS` / README 表与 `src/args` 逐字节一致、每个声明参数都被绑定引用、坏 schema 被验证器拒绝 |

合计 **798** 条断言；源码与压缩版各一遍，共 **1596** 条。

## 抖音插件（douyin.plugin）

`plugins/douyin/douyin.plugin` 依据 2026-10 三份真实 HAR 取证实现，测试集中在 `test_douyin_treasure.js`、`test_douyin_clean.js` 与 lint：

- 福利页精简：只保留 `duration_task_section` / `luna_rewards_ads`（攒时长 听歌不中断），其余分区整体删除；
- `config.migrate_first_ad` 关闭；`config.ad_api_preload.task_ids` 只留保留任务引用的 id，一条不剩时 `preload` 关闭；
- 激励广告配置清理：`advert_sources` / `feed_advert_config` / `vids` / `preload` 与 `ad_infos_map` / `ad_infos`；
- 商业化弹窗清理：删 `*ads*` 弹窗与 `browse_mall_popup_acc_amount`（商城），同步清理排序、冷启动引用与同名频控项，保留领奖与兜底弹窗；
- 演出清理：`growth/music_festival/performance_details` 的 `detail_list` 清空（汽水音乐节）；
- 开屏请求拦截：`blockSplashAd` 与汽水共用 `src/common/splash-ad.js`，只拦 `api/ad/...splash/` 家族，不碰激励与发奖（`test_splash_ad.js` + lint hit/miss 锁定）。

## 聚合插件（soda.plugin）

`plugins/soda/soda.plugin` 是汽水音乐唯一部署插件，用 Loon `[Argument]` 开关控制脚本，测试集中在 `test_unified_args.js`、`test_block_domains.js` 与 lint：

- `rewardSafe=true` 时，`sanitize` 对非开屏端点直接放行；开屏品牌广告仍清理；
- `rewardSafe=false` + `cleanAds=true` 时，去广告脚本正常清理；v2 `commerce/v2/upsell` 的 `upsell_map` 只删广告/商城弹窗，排序/冷启动/频控引用同步（`test_soda_upsell_v2.js`，真实 93 弹窗样本）；
- `settings` 在 `rewardSafe=true` 时直接放行；
- `hideDouyinTab=true` 时只删除带“抖音”的列表项，其它任务（签到/听歌/看广告任务）保留；该开关有独立 `enable=` 绑定，`cleanAds=false` 时同样生效；
- 没有 `$argument` 时行为保持不变（脚本可独立运行）；
- 域名拦截脚本：`blockAdDomains=false` 或 `rewardSafe=true` 时一律放行，其它域名不受影响；
- lint 验证 14 个参数的默认值（含 `statusNotify` 的 select 候选）、40 条脚本绑定都带 `enable={...}`、同 URL 重叠绑定不会非预期抢占、通用按钮绑定透传全部开关（含 `statusNotify`）、上报 Rewrite 必须使用 `reject_dict(200)`、插件没有静态 `[Rule]` 域名。

## 只读观测与状态自检

`reward-observe.js` 与 `status.js` 都只读，不修改响应；测试集中在 `test_reward_observe.js`、`test_status.js` 与 lint：

- 激励/任务/入口端点必须命中；`splash`、`commerce/upsells`（v1）、`commerce/v2/upsell_sort_decision`、`feed` 不应被观测；
- `commerce/v2/upsell` 只输出奖励入口变量和场景数，不输出弹窗文案、会员到期时间或 token；
- 观测脚本永远返回 `$done({})`，不写 `body`；
- 日志过滤 `access_token` / `device_id` / `cookie` 等敏感键与值；
- 非 JSON、空体、超过 256KB 的响应只记录状态，不解析；
- `status.js` 通过 `$notification` 输出打卡摘要，attach openUrl 分别使用 `qishui://` / `snssdk1128://`；`statusNotify=silent` 时跳过通知，只保留日志与 `$done` 结果页；
- 结果页/通知的「开关状态」摘要由 generic 绑定透传的全部开关生成；冲突组合（`killRewardAds`、`rewardSafe+cleanAds`、`rewardSafe+settingsClean`、`rewardSafe+blockAdDomains`、`treasureMinimal+killRewardAds`）逐条提示；
- `cleanAds` / `treasureMinimal` / `hideDouyinTab` 与 `debugLog` 同开时，状态看板提示该端点的只读日志会被首条命中的清理/隐藏脚本抢占；
- 「运行环境」行汇总 `$loon`、`$script.name/startTime`、`$environment.params.nodeInfo`（兼容 `$envirnoment`）与 `$config.getConfig().running_model`；任一全局对象缺失时整行省略，测试同时覆盖完整环境、仅拼写兼容、无环境三种形态。「Loon 能力」行固定显示 `$utils.ungzip` 是否可用（988+），983–987 会明确标 ❌ 而不是静默失效。

## 注意

- 测试文件里的 URL 是构造的，字段名来自 20.5.0 二进制取证；真实响应可能有额外包装。
- `settings.js` 的响应形态是兼容式实现，测试覆盖扁平字典、`{settings:{...}}`、`{data:{...}}`、`{key,value}` 数组、JSON 字符串和 BDADSDK `{settings,ctx_infos,settings_time}`。
- 压缩版测试会通过 `SODA_SCRIPT_SET=dist` 加载 `.min.js`；`AGGRESSIVE` / `DRY_RUN` / `INJECT_MISSING` 的开关测试同时兼容源码和压缩写法。
- 真机验证仍需观察 Loon 日志前缀 `[soda]` / `[soda-settings]` / `[soda-reward]`，并确认 MITM 未被证书固定拦截。
