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
npm run lint        # 插件结构、正则、脚本引用、压缩脚本语法
```

`run-all.py` 默认对源码和压缩版各跑一遍；`SODA_SCRIPT_SET=src|dist`（或 `SCRIPT_SET`）由 `tests/load-script.js` 读取，`loadScript(name, family)` 可以加载不同插件族。`lint-plugins.py` 检查每个 App 唯一部署插件（`soda.plugin`、`douyin.plugin`）的 section、域名、Rewrite/Script 行数、正则编译、`script-path` 是否指向存在的 `.min.js`、源码是否存在、压缩脚本能否通过 `node --check`，并确认压缩脚本确实比源码小且行数不超过 5 行。它还会验证：插件没有启用的静态 `[Rule]` 域名、每条脚本都带 `enable=${开关}`、开关默认值正确、`[MITM]` 覆盖 API/设置/广告域名、关键端点能被脚本正则命中，以及 `#!name/#!desc/#!author/#!version/#!homepage/#!icon` 元数据齐全且 `#!icon` 是 https 链接。

`tests/fixtures/` 里放的是**真实抓包样本**（2026-10-20 HAR）：`douyin_treasure_page.json`（抖音福利页原始响应）、`soda_incentive_done.json`（汽水发奖请求/响应），用于防止“按想象改字段”。

## 断言分布

| 测试 | 断言数 | 覆盖 |
|---|---:|---|
| `test_sanitize2.js` | 19 | 通用字段清洗、包络保留、非目标端点不误伤 |
| `test_prune.js` | 13 | `incentive/config` 的 `advert_sources` / `feed_advert_config` / `preload` |
| `test_taskinfos.js` | 1 | `task_infos` 广告任务裁剪（保留签到/听歌/逛商城） |
| `test_request.js` | 12 | 请求侧 `preload=false`，不动 `ad_unit_configs` / `advert_duration` |
| `test_ads_surfaces.js` | 33 | 开屏、广告位、DSP、兜底、卡片、增长入口、upsell |
| `test_treasure_prune2.js` | 15 | 福利任务、banner、弹窗、金币挂件、`commerce_ad_task` / `ad_snap` |
| `test_settings.js` | 66 | TTKitchen 设置层、BDADSDK 形态、可选 `i`/`is` 主机、AGGRESSIVE/DRY_RUN/INJECT_MISSING |
| `test_feed_flags.js` | 10 | `is_advertisement` / `ad_flag` / `adItem` / `card.is_ad` |
| `test_feed_expand.js` | 16 | 扩展 feed 端点、`search-block` 仅 `banner_list` 场景 |
| `test_reward_observe.js` | 91 | 激励链路只读观测：计数、任务摘要、进度字段、发奖字段、upsell 入口变量、隐私过滤、大响应放行 |
| `test_block_domains.js` | 7 | 广告域名拦截脚本：开关关闭不拦、`rewardSafe` 放行、非广告域名不拦、返回 200 空响应 |
| `test_douyin_upsell.js` | 39 | 真实 93 弹窗样本：广告/商城弹窗被删、奖励与兜底弹窗保留、variables 不动、排序与冷启动引用同步清理 |
| `test_soda_splash_ad.js` | 8 | 开屏广告请求拦截：开屏路径被拦、激励广告与发奖回调绝不拦、开关关闭放行 |
| `test_soda_douyin_entry.js` | 13 | 【听抖音】入口：设置层 anchor_luna_to_douyin* 置 0、不动其它设置、保奖励模式下也能生效、与清广告配置互不干扰 |
| `test_douyin_activity.js` | 19 | polaris 活动配置（真实样本 181 个活动）：音乐节/抖音运营活动 canshow 置 false、其它活动不动、开关关闭原样放行 |
| `test_soda_task_titles.js` | 7 | 只读日志带任务标题：默认不打文案、开关打开后带 title、view.title 形态也能取到 |
| `test_douyin_treasure.js` | 32 | 抖音福利页精简：只留攒时长模块、其余分区全部移除、广告预拉取 id 清空、开关关闭原样放行、参数对象/数组/字符串三种形态都识别、**真实抓包样本**回归 |
| `test_douyin_clean.js` | 20 | 抖音广告配置/商业化弹窗/演出清理：广告源与素材清空、商城与广告弹窗删除、排序与冷启动引用同步清理、音乐节列表清空 |
| `test_unified_args.js` | 19 | 聚合插件开关：`rewardSafe` 优先放行非开屏端点、开屏仍清理、无参数时行为不变、设置层保护、`hideDouyinTab` 只删抖音条目 |

合计 **344** 条断言；源码与压缩版各一遍，共 **688** 条。

## 抖音插件（douyin.plugin）

`plugins/douyin/douyin.plugin` 依据 2026-10 三份真实 HAR 取证实现，测试集中在 `test_douyin_treasure.js`、`test_douyin_clean.js` 与 lint：

- 福利页精简：只保留 `duration_task_section` / `luna_rewards_ads`（攒时长 听歌不中断），其余分区整体删除；
- 被删任务的广告预拉取 id（`config.ad_api_preload.task_ids`）清空；
- 激励广告配置清理：`advert_sources` / `feed_advert_config` / `vids` / `preload` 与 `ad_infos_map` / `ad_infos`；
- 商业化弹窗清理：删 `*ads*` 弹窗与 `browse_mall_popup_acc_amount`（商城），同步清理排序与冷启动引用，保留领奖与兜底弹窗；
- 演出清理：`growth/music_festival/performance_details` 的 `detail_list` 清空（汽水音乐节）。

## 聚合插件（soda.plugin）

`plugins/soda/soda.plugin` 是汽水音乐唯一部署插件，用 Loon `[Argument]` 开关控制脚本，测试集中在 `test_unified_args.js`、`test_block_domains.js` 与 lint：

- `rewardSafe=true` 时，`sanitize` 对非开屏端点直接放行；开屏品牌广告仍清理；
- `rewardSafe=false` + `cleanAds=true` 时，去广告脚本正常清理；
- `settings` 在 `rewardSafe=true` 时直接放行；
- `hideDouyinTab=true` 时只删除带“抖音”的列表项，其它任务（签到/听歌/看广告任务）保留；
- 没有 `$argument` 时行为保持不变（脚本可独立运行）；
- 域名拦截脚本：`blockAdDomains=false` 或 `rewardSafe=true` 时一律放行，其它域名不受影响；
- lint 验证 7 个开关的默认值、32 条脚本都带 `enable={...}`、插件没有静态 `[Rule]` 域名。

## 只读观测插件

`SodaClean-Reward-Debug.plugin` 不新增字段裁剪，测试集中在 `test_reward_observe.js` 与 lint：

- 20 个激励/任务/入口端点必须命中；`splash`、`commerce/upsells`（v1）、`commerce/v2/upsell_sort_decision`、`feed` 不应被观测；
- `commerce/v2/upsell` 只输出奖励入口变量和场景数，不输出弹窗文案、会员到期时间或 token；
- 脚本永远返回 `$done({})`，不写 `body`；
- 日志过滤 `access_token` / `device_id` / `cookie` 等敏感键与值；
- 非 JSON、空体、超过 256KB 的响应只记录状态，不解析。

## 注意

- 测试文件里的 URL 是构造的，字段名来自 20.5.0 二进制取证；真实响应可能有额外包装。
- `settings.js` 的响应形态是兼容式实现，测试覆盖扁平字典、`{settings:{...}}`、`{data:{...}}`、`{key,value}` 数组、JSON 字符串和 BDADSDK `{settings,ctx_infos,settings_time}`。
- 压缩版测试会通过 `SODA_SCRIPT_SET=dist` 加载 `.min.js`；`AGGRESSIVE` / `DRY_RUN` / `INJECT_MISSING` 的开关测试同时兼容源码和压缩写法。
- 真机验证仍需观察 Loon 日志前缀 `[soda]` / `[soda-settings]` / `[soda-reward]`，并确认 MITM 未被证书固定拦截。
