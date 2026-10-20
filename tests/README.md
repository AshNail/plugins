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

`run-all.py` 默认对源码和压缩版各跑一遍；`SODA_SCRIPT_SET=src|dist` 由 `tests/load-script.js` 读取。`lint-plugins.py` 检查五个插件的 section、域名、Rewrite/Script 行数、正则编译、`script-path` 是否指向存在的 `.min.js`、源码是否存在、压缩脚本能否通过 `node --check`，并确认压缩脚本确实比源码小且行数不超过 5 行。它还会验证保奖励插件不会匹配 `incentive` / `ads` / `task` / `feed` 等奖励链路端点，只读观测插件只匹配激励链路端点，以及统一开关版没有静态域名规则、每个脚本都带 `enable={开关}`。

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
| `test_unified_args.js` | 14 | 统一开关版：`rewardSafe` 优先放行非开屏端点、开屏仍清理、无参数时独立插件行为不变、设置层保护 |

合计 **290** 条断言；源码与压缩版各一遍，共 **580** 条。

## 保奖励插件

`SodaClean-Reward.plugin` 不新增脚本断言，它的正确性由 `lint-plugins.py` 的接线检查覆盖：

- 正样本：`splash/brand/retrieve` 必须命中 Script。
- 负样本：`incentive/config`、`incentive/retrieve`、`ads/config`、`ads/retrieve`、`treasure/task/view`、`treasure/entrance/config`、`growth/activity_entrance`、`feed/*`、`advert/fallback/done/info`、`treasure/task/fallback|flip_card|guide|browse_mall/do_action`、`commerce/upsells`、`commerce/v2/upsell` 必须不被任何 Script 匹配。
- `[Rule]` 为空：不拦任何域名（包括 App Store 评分弹窗 `praisewindow.ugsdk.cn`），更不拦激励广告 SDK 域名。

## 统一开关版

`SodaClean-Unified.plugin` 用 Loon `[Argument]` 开关控制脚本，测试集中在 `test_unified_args.js` 与 lint：

- `rewardSafe=true` 时，`sanitize` 对非开屏端点直接放行；开屏品牌广告仍清理；
- `rewardSafe=false` + `cleanAds=true` 时，去广告脚本正常清理；
- `settings` 在 `rewardSafe=true` 时直接放行；
- 没有 `$argument` 时，独立主插件/设置插件的行为保持不变；
- lint 验证五个开关的默认值、31 条脚本都带 `enable={...}`、统一版没有静态 `[Rule]` 域名。

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
