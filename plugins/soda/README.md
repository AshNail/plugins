# 汽水音乐 · Loon 聚合插件（soda）

> 所属：Loon 插件仓库 · 插件族 `soda`（[仓库总览](../../README.md)）
> 部署目录：`plugins/soda/`；源码目录：`src/soda/`
> 目标：汽水音乐 iOS 20.5.0（`com.luna.music`）
> 类型：Loon 插件（聚合开关 / 字段级响应改写 / 诊断脚本）
> 取证：Ghidra 全量分析 + ARM64 `ADRP+ADD` 字符串引用扫描（详见配套逆向报告）

**版本要求**：本插件使用 **Loon 3.5.1(983) 起的新版 Script 语法**
（`script("...", {${开关名}})` + `with enable=${开关名}`）。
旧版语法的 `argument=[{开关名}]` 在 Loon 3.5.x 上不会把开关值送进脚本——
真机日志显示脚本被触发但拿不到开关，表现为“插件装了却没效果”（2026-10-20 实测）。
**gzip 响应体解析依赖 `$utils.ungzip`（Loon 3.5.1(988) 起提供）**：983–987 仍可安装，
但压缩响应的端点会跳过清理，只记录状态；完整去广告效果请升级到 988+。状态看板会直接显示当前 build 是否具备该能力。

**v2.2.0 当前架构（一个 App 一个插件）**：Soda 只部署 `plugins/soda/soda.plugin` 一个文件。保奖励、去广告脚本、**广告域名拦截**、设置层、只读日志、隐藏【听抖音】全部通过 Loon `[Argument]` 开关控制：`rewardSafe`、`cleanAds`、`blockAdDomains`、`settingsClean`、`debugLog`、`splashClean`、`hideDouyinTab`。默认 `rewardSafe=true`，只清开屏品牌广告。旧的 `SodaClean` / `SodaClean-Reward` / `SodaClean-Reward-Debug` / `SodaClean-Settings` 独立插件已合并进本插件，不再单独安装。

> 以下 v1.x / 0.x 段落保留为历史设计记录；当前安装和使用只看 `soda.plugin`。

**v1.5.2 历史变更**：部署脚本改为 terser 实际压缩版 `plugins/soda/scripts/*.min.js`（去空白/注释、混淆局部与顶层变量名），可读源码保留在 `src/soda/`，由 `tools/build.js` 生成。插件行为与 v1.5.1 一致。

**v1.5.1 新增**：补充 `search-block` / `search-categories` / `card` / `growth/activity_entrance` / `advert/fallback/done/info` 五个端点；信息流 `fastReject` 识别 `banner_list`，修复“只有 banner 广告时脚本不解析”的漏洞；福利任务正则加入 `commerce_ad` / `ad_snap`；设置层新增 `splash_ad_config` / `reward_ad_config` / `adn_group_config` / `commerce_*_ad_config` / DSP / mannor 等广告专用键，并可选接入 `is.snssdk.com`（BDADSDK 设置）与 `i.snssdk.com`（Unisus 设置）。主插件 v1.5.2，设置插件 v0.1.2。

**历史：保奖励模式（独立插件 v0.2.3，已合并）**：`SodaClean-Reward.plugin` 只清开屏品牌广告，**保留**激励广告、奖励任务、发奖链路，并**刻意不碰 upsell**（可能承载 `UpsellStyleRewardAdsDefault` / `reward_btn_text` 等激励入口）。适合“完整看完广告后正常领奖”；**不拦任何域名**（包括 App Store 评分弹窗 `praisewindow.ugsdk.cn`），信息流/DSP/商业弹窗可能仍会出现。与主插件、设置插件二选一，不能同时启用。

**历史：激励链路观测（只读 v0.2.2，已合并为 `debugLog`）**：`SodaClean-Reward-Debug.plugin` 只写 `[soda-reward]` 日志，不修改响应；观察 22 个激励/任务/入口端点绑定（v2.6.1 起含 `task/page`），用来判断广告源、`reward_ads` 任务、发奖接口、`fallback/flip_card/guide/browse_mall` 动作，以及 `upsell` 的奖励入口变量到底卡在哪一层。可与保奖励插件同时启用，排障后停用。

**历史：统一开关版（实验 v0.1.0 → v2.1.0）**：`SodaClean-Unified.plugin` 是当前 `soda.plugin` 的前身。v2.1.0 起域名拦截也做成了开关（`blockAdDomains`，MITM + `http-request` 脚本），`[Rule]` 只作为不依赖 MITM 的手动严格模式保留。

**v1.5 已包含**：信息流 `is_advertisement` / `is_ad_item` / `ad_flag` / `adItem` 与 `card.is_ad` 嵌套判定；信息流端点扩展 `playlist/search` / `discover/mix`；福利任务/ banner 增加 `ad_reward` 变体；福利页 `banner_list` 广告项裁剪；新增**设置层实验插件** `SodaClean-Settings.plugin`，通过 `conf.qishui.com/service/settings/v3/` 清空 `commerce_ad_config` / `feed_reward_ad_config` / `reward_ad_fallback_config` / `splash_ad_early_load_config` 等 TTKitchen 配置。

**v1.4 已包含**：开屏 `ad_launch_list` / `ad_launch`、信息流 `ads_blocks` / `ads_info` / `is_ad`、广告位配置 `ad_unit_configs` / `splash_config` / `feed_ads_config` / `reward_config`、DSP 上报 `reject_dict(200)`、金币挂件 `widgetAdReward` 广告态。字段地址与描述符见《汽水音乐_20.5.0_开屏与信息流广告_字段取证与净化方案.md》。

---

## 0. 边界：Loon 能做什么、不能做什么

Loon 工作在**网络层**。

| ✅ 能做 | ❌ 不能做 |
|---|---|
| 拦截广告 SDK 域名、归因回传 | 修改 App 本地 UI 控件 |
| 字段级改写配置接口响应 | 模拟点击、手势、自动跳页 |
| 阻断开屏、激励视频、DSP 广告请求 | 绕过服务端发奖校验 |
| 记录真实响应体，辅助迭代规则 | Hook 方法 / 改二进制 |

### 关于「自动获取激励」

- 激励视频的奖励以「广告实际播放完成」为结算条件；屏蔽广告后再触发领奖属于广告欺诈（ad fraud）。
- 服务端有三道校验：幂等键（`task_token`、`global_task_id`、`fallback_done_req_id`）、发奖校验（`luna/commerce/validate_reward`、`luna/advert/fallback/done/info`）、频控（`freqCtrlTool`）。
- Loon 也无法重放带签名的请求或伪造 SDK 回调。

所以本插件**不做**「伪造广告完成领奖励」。它做的是：**广告不再出现**、**入口/弹窗不再下发**、**无效请求不出去**。

---

## 1. 取证：响应模型与线上键名

二进制里 `STNetProto` 的 Swift 类成员符号直接给出了响应字段：

| 响应模型 | Swift 属性 | 线上 JSON 键（snake_case） |
|---|---|---|
| `GetIncentiveAdvertConfigResponse` | `statusCode` `statusInfo` `advertSources` `feedAdvertConfig` `expireTime` `preload` | `status_code` `status_info` `advert_sources` `feed_advert_config` `expire_time` `preload` |
| `IncentiveRetrieveResponse` | `statusCode` `statusInfo` `adInfosMap` `expireTime` | `status_code` `status_info` `ad_infos_map` `expire_time` |
| `IncentiveDoneResponseInfo` | `statusCode` `statusInfo` `rewardDetails` `rewardTips` | `status_code` `status_info` `reward_details` `reward_tips` |

判断依据：每个属性对应的 snake_case 串在二进制中**恰好出现一次**（解码映射键），camelCase 出现 2–3 次（属性反射 + 符号）。

开屏、信息流、广告位的字段来自二进制中的字段描述符（0x1147cb…–0x1147cf… 的绝对字符串指针数组）：

| 端点 | 真实字段 | 说明 |
|---|---|---|
| `luna/advert/splash/brand/retrieve` | `ad_launch_list` / `ad_launch` | 开屏品牌广告对象；`SplashAdSourceBrand.lastSelectedAdLaunch` 佐证 |
| `luna/ads/config` | `ad_unit_configs` `splash_config` `feed_ads_config` `reward_config` | 广告位 / 开屏 / 信息流 / 激励四类配置 |
| `luna/ads/retrieve`、`luna/ads/dsp/retrieve` | `ad_launch` `ad_launch_list` `ads_blocks` `ads_info` | 通用广告拉取 |
| 信息流（`luna/feed/*`、`luna/playlist/feed/media` 等） | `ads_blocks` `ads_info` `is_ad` | 信息流广告块与广告条目标记 |
| `luna/commerce/upsells`（v1） | `card` `upsell_unique_name` `countdown` | 会员升级 / 挽回弹窗（旧版） |
| `luna/commerce/v2/upsell` | `upsell_map` / `sort_control_unique_names` / `cold_launch_timing` / `freq_ctrl_cfg`（2026-10-20 真 HAR，snake_case）；`sceneUpsellsMap` / `upellsVariables` / `popupConfig` 为二进制 Swift 属性名，线上键名待确认 | 商业化弹窗（`upsell_map` 实体）按名字精确清理；金币挂件配置在 `candidates[].fixed_entrance.coin_widget_data`（奖励入口） |
| `luna/treasure/entrance/config` | `main_icon` `main_tab`（`TreasureEntranceConfigResponse`） | 福利入口；`coin_widget_data` 的直接宿主是 upsell 的 `FixedEntrance` |

### 1.1 设置层：TTKitchen 下发（v1.5 新增，v1.5.1 扩展）

除了 `api.qishui.com` 的业务接口，App 还会从**另一个域名**拉取全局设置：

| 项 | 值 |
|---|---|
| 端点 | `https://conf.qishui.com/service/settings/v3/` |
| 字符串地址 | `0x10ebe7100` |
| 代码引用 | `0x10692d6ec`（ADRP）/ `0x10692d6f0`（ADD） |
| 调用方 | `TTKitchenSyncer` → `TTNetworkManager requestForJSONWithResponse:`（GET，JSON） |
| 合并方式 | 响应字典合并进 `TTKitchenManager` |

广告相关设置键（`STABSettingsService` 注册表 + 字段描述符 + 代码引用）：

| 设置键 | 地址 | 含义 | 默认处理 |
|---|---|---|---|
| `commerce_ad_config` | `0x10e7c6d90` | 商业化广告配置 | `{}` |
| `commerce_ad_feed_config` | `0x10e7c6ec0` | 信息流广告配置 | `{}` |
| `reward_ad_fallback_config` | `0x10e7c6ff0` | 兜底广告配置 | `{}` |
| `feed_reward_ad_config` | `0x10e7f46d0` | 信息流激励广告配置 | `{}` |
| `splash_ad_early_load_config` | `0x10e7f0100` | 开屏广告提前加载配置 | `{}` |
| `ad_webview_sdk_config` | `0x10e7c6e00` | 广告 WebView SDK 配置 | `{}` |
| `splash_ad_config` | `0x10e7c6280` | 开屏广告主配置 | `{}` |
| `reward_ad_config` | `0x10e7c62a0` | 激励广告主配置 | `{}` |
| `commerce_libra_ad_config` | `0x10e7c6200` | 商业化 LibRA 广告配置 | `{}` |
| `commerce_common_ad_config` | `0x10e7c6220` | 商业化通用广告配置 | `{}` |
| `adn_group_config` | `0x10e7c65c0` | 广告网络分组配置 | `[]` |
| `splash_dsp_config` | `0x10e7c6570` | 开屏 DSP 配置 | `{}` |
| `preload_dsp_config` | `0x10e7c6600` | DSP 预加载配置 | `{}` |
| `splash_mannor_config` | `0x10e7c6550` | 开屏 Mannor 配置 | `{}` |
| `ad_ignore_player_status_config` | `0x10e7c6f00` | 广告忽略播放器状态配置 | `{}` |
| `feed_ad_config` | `0x10e78a282` | 信息流广告配置（扁平变体） | `{}` |
| `ad_reward_config` | `0x10e7a6388` | 广告奖励配置 | `{}` |
| `incentive_advert_config` | `0x10ec8d5b0` | 激励广告配置 | `{}` |
| `feed_reward_ad_entrance` | `0x10e7ced30` | 信息流激励入口 | `{}` |
| `enable_client_ads_strategy` | `0x10e7597a4` | 客户端广告策略开关 | `false` |
| `preload_feed_ads` | `0x10ed43e4c` | 信息流广告预加载 | `false` |
| `timor_should_enable_ad` | `0x10e7fa9d0` | 是否启用广告 | 仅 `AGGRESSIVE=true` 时 `false` |
| `switch_show_all_ad` | `0x10e7c61e0` | 全局广告展示开关 | 仅 `AGGRESSIVE=true` 时 `false` |
| `kBasicModeDisableRewardAdEnabled` | `0x10e7f49c0` | 基础模式是否禁止激励广告 | `true` |
| `ad_reward_position_exp` | `0x10e7f0860` | 激励广告入口展示 | 仅 `AGGRESSIVE=true` 时 `0` |

> `ads_config_expire_time_ms`（`0x10e7c62c0`）是广告配置过期时间，**不**清空：把它改成 0 会缩短缓存、引发更多请求。脚本只清配置，不动过期时间。
>
> `conf.qishui.com` 已在聚合插件 `soda.plugin` 的 `[MITM]` 里；设置层由 `settingsClean` 开关控制（见 3.7 / 3.8）。插件还预留了 `is.snssdk.com`（BDADSDK.SettingsManager）与 `i.snssdk.com`（Unisus）两个可选设置端点，默认注释。

广告/归因域名：

| 域名 | 用途 | 证据 |
|---|---|---|
| `ad.zijieapi.com` | 激励视频/Pangle 广告请求、激励完成上报、负反馈 | `https://ad.zijieapi.com/api/ad/v1`、`/api/incentive/marketing/done` |
| `lianmengapi.snssdk.com` | 穿山甲联盟 API | 二进制字符串 |
| `ads?-normal*.zijieapi.com`（分片族） | 广告素材/投放 CDN；Pangle 按服务端下发在 `ads3/ads5 × normal/-hl/-lf/-lq/-xh` 之间切换 | HAR 里只见过 `ads5-normal-hl`；同族的其余 9 个分片来自本仓库 `ads.plugin` 的公开广告清单 |
| `zlink.ugsdk.cn` | 归因/转化回传 | `https://zlink.ugsdk.cn/ad/impression/asa/token` |
| `praisewindow.ugsdk.cn` | App Store 评分弹窗（非广告） | `AppStoreStarAdapter`、`/zebra/praise/click`、`为汽水音乐评分` |

> 设置层还有两个**不默认拦截**的端点：`is.snssdk.com/service/settings/v3/`（`BDADSDK.SettingsManager`，广告 SDK 设置）和 `i.snssdk.com/service/settings/v3/`（`Unisus` 通用设置）。它们可能被证书固定，默认只在实验插件里以注释形式提供。

---

## 2. 为什么配置端点默认不用 `reject-dict`

| 方案 | 返回 | 风险 |
|---|---|---|
| `reject-dict` | `{}` | 丢失 `status_code`，App 解码失败 → 重试 / 走默认值 / 弹错误 |
| 本插件 | 原包络 + 广告容器清空 | App 认为「本次没有广告」，流程正常结束 |

> 纯上报端点（`splash/brand/report`、`ads/report/dsp/show`）没有业务包络，已改用 Rewrite v2 的 `reject_dict(200)`（JSON `{}` + `application/json`）；配置类端点仍走脚本保留包络。注意 `reject(200)` 的空 Body 是 `text/plain`，需要 JSON 时应使用 `reject_dict`。

改写后的激励配置长这样（真实结构）：

```json
{
  "status_code": 0,
  "status_info": "",
  "advert_sources": [],
  "feed_advert_config": {},
  "expire_time": 1700000000,
  "preload": false
}
```

---

## 3. 精准改写器（`src/soda/sanitize.js`）

### 3.1 工作方式

1. 按 URL 匹配规则（只处理广告/弹窗/入口配置端点）；
2. 递归遍历 JSON，按**归一化键名**匹配（`advert_sources` 与 `advertSources` 等价）；
3. 容器字段清空（数组 → `[]`，对象 → `{}`），布尔开关 `true → false`；
4. 其余字段（含 `status_code`）原样保留；
5. 任何异常 → 原样放行。

### 3.2 规则表

| 端点 | 处理 |
|---|---|
| `luna/advert/incentive/config` | `advert_sources → []`、`feed_advert_config → {}`、`preload → false` |
| `luna/advert/incentive/retrieve` | `ad_infos_map → {}` |
| `luna/advert/splash/brand/retrieve` | `ad_launch_list` / `ad_launch` / `splash_active_data` / `jump_btn_info → []` |
| `luna/ads/config` | `ad_unit_configs` / `splash_config` / `feed_ads_config` / `reward_config` / `search_banner` / `feed_widget` / `commerce_libra_ad_config` / `commerce_common_ad_config` / `adn_group_config` / `splash_dsp_config` / `preload_dsp_config` / `splash_mannor_config` / `ad_ignore_player_status_config` → 空容器（数组 `[]`，对象 `{}`） |
| `luna/ads/{retrieve,dsp/retrieve}`、`luna/advert/fallback/done/info` | `ad_launch` / `ad_launch_list` / `ads_blocks` / `ads_info` / `ad_infos` / 上述广告配置 → 空容器（数组 `[]`，对象 `{}`） |
| 信息流（`luna/feed/*`、`luna/v2/feed/*`、`luna/playlist/detail`、`luna/playlist/search`、`luna/search/track`、`luna/search-block`、`luna/search-categories`、`luna/card`、`luna/discover/mix`、`luna/media/assistant/related`、`luna/me/discover`、`luna/featured-content/list` 等） | 清 `ads_blocks` / `ads_info` / `ad_info` / `video_end_ad` / `feed_ads` / `feed_reward_ad_entrance`；`is_ad` / `is_advertisement` / `is_ad_item` / `ad_flag` / `adItem` 为 true 的条目整条丢；`banner_list` 里的广告项裁掉 |
| `luna/commerce/{upsells,v2/upsell,v2/upsell_sort_decision}` | v1：`card` / `upsells` / `upsell_unique_name` / `items` / `popups` / `list → []`；v2：`upsell_map` 里广告/商城命名的弹窗实体逐个删除，同步清理 `freq_ctrl_cfg.freq_ctrl_map` 同名项、`sort_control_unique_names` 与 `cold_launch_timing.upsell_item_unique_names`（含只登记无实体的广告弹窗）；奖励/发奖/兜底弹窗与 `variables` / `libra_params_map` 不动。`sceneUpsellsMap → candidates → fixedEntrance.coinWidgetData` 仍不处理（奖励入口，非广告实体） |
| `luna/treasure/entrance/config`、`luna/growth/activity_entrance` | 摘 `labels`；若响应内出现 `coin_widget_state_list`，按 `widgetAdReward` 等广告态过滤；清 `reward_ad_banner` / `ads_banner` / `ad_snap` / `popup_show_ad` 等；`banner_list` 只裁广告项（含 `ad_reward`） |
| `luna/treasure/task/view` | 只摘 `task_infos` / `tasks` / `taskList` / `list` / `data` 里匹配 `ad_reward` / `reward_ads` / `incentive` / `watch_video` / `commerce_ad` / `ad_snap` / 看视频 / 看广告 的任务；同样裁广告 banner/popup |

> `treasure/*` 两条默认开启：**只过滤广告任务，签到/听歌/分享/逛商城/翻牌全部保留**。

### 3.3 DRY_RUN（首次上线建议）

```js
const DRY_RUN = true;   // 只打日志，不改响应
```

跑一轮后看日志确认改了什么，再切回 `false`。

### 3.4 日志示例

```
[soda] incentive-config | 3 change(s) | 31B smaller
  $.advert_sources : [{"rit":1},{"rit":2}] -> []
  $.feed_advert_config : {"enable":true} -> {}
  $.preload : true -> false
```

Loon → 日志，搜索 `[soda]`。

### 3.5 只摘广告任务，保留合法福利

`treasure` 的两个端点是"任务中心"，里面不止广告任务。二进制里的任务类型：

| 任务 | 入口/证据 | 是否需要看广告 |
|---|---|---|
| 每日签到 | `sign_in`、`听歌15分钟去签到` | ❌ |
| 听歌赚金币 | `听歌赚金币功能开关`、`listen_duration` | ❌ |
| 每日登录 | `每日登录 领双重福利` | ❌ |
| 分享 | `share_cnt`、`分享单曲` | ❌ |
| 邀请好友 | `enable_invite`、`invite_share_module` | ❌ |
| 逛商城 | `luna/treasure/task/browse_mall/do_action` | ❌ |
| 翻牌 | `luna/treasure/task/flip_card/do_action` | ❌ |
| 引导任务 | `luna/treasure/task/guide/do_action` | ❌ |
| **看视频领福利** | **`luna/treasure/task/reward_ads/do_action`** | ✅ |

脚本只摘最后一条，其余全部保留。日志会显示：

```
[soda] treasure-task-view | 1 change(s) | 87B smaller
  $.task_infos : dropped 2/5 ad item(s)
```

> 实际字段名是 `task_infos`（此前写成 `tasks` 是猜测值）。如果某个版本的字段名不同，把日志里的实际 `task_key` 发我，改一行正则即可。

### 3.6 开屏 / 信息流 / 广告位

| 类型 | 关键字段 | 处理 |
|---|---|---|
| 开屏品牌 | `ad_launch_list` | 清空；`splash_active_data` / `jump_btn_info` 一并清 |
| 开屏 / 通用广告 | `ad_launch` / `ad_launch_list` | 清空；配置里的 `splash_config` 也清 |
| 信息流 | `ads_blocks` / `ads_info` / `is_ad` | 清 `ads_blocks`、`ads_info`；`is_ad=true` 的条目整条丢 |
| 广告位配置 | `ad_unit_configs` / `feed_ads_config` / `reward_config` | 清空，阻止 SDK 注册广告位 |
| 会员弹窗 | `card` / `upsell_unique_name` | 清空 |
| DSP 上报 | `luna/ads/report/dsp/show` | Rewrite `reject_dict(200)`，不走上游 |

`feed-ads` 规则先做字符串预检（`fastReject`）：响应里没有 `ads_blocks` / `ads_info` / `is_ad` / `banner_list` / `feed_reward_ad_entrance` 等标记就直接放行，不对大 feed 响应做 `JSON.parse`。v1.5.1 把 `banner_list` 加入预检，修复“只有 banner 广告时脚本不解析”的漏网。

**保守策略**：`isAdItem` 只在以下情况丢整条：

1. 显式 `is_ad` / `is_advert` / `is_advertisement` / `is_ad_item` / `ad_flag` / `adItem` 为 true；
2. 只有 `ad_info` / `ad_data`，且没有 `video` / `track` / `song` / `media` 等媒体字段；
3. 外层没有媒体字段，但 `card` / `ad_info` / `ads_info` 等嵌套对象里带 `is_ad=true`。

正常内容即使带 `ad_info`，只要还有媒体字段就保留，只清广告字段。`ads_info` 单独出现时也保留条目，只清空 `ads_info`，避免误删 featured 卡片。

### 3.7 设置层（实验，v1.5 新增）

`src/soda/settings.js` 处理 `conf.qishui.com/service/settings/v3/` 的 JSON：

| 设置键 | 默认处理 |
|---|---|
| `commerce_ad_config` | `{}` |
| `commerce_ad_feed_config` | `{}` |
| `reward_ad_fallback_config` | `{}` |
| `feed_reward_ad_config` | `{}` |
| `splash_ad_early_load_config` | `{}` |
| `ad_webview_sdk_config` | `{}` |
| `splash_ad_config` / `reward_ad_config` / `feed_ad_config` / `ad_reward_config` / `incentive_advert_config` / `feed_reward_ad_entrance` | `{}` |
| `commerce_libra_ad_config` / `commerce_common_ad_config` / `splash_dsp_config` / `preload_dsp_config` / `splash_mannor_config` / `ad_ignore_player_status_config` | `{}` |
| `adn_group_config` | `[]` |
| `enable_client_ads_strategy` / `preload_feed_ads` | `false` |
| `timor_should_enable_ad` | 仅 `AGGRESSIVE=true` 时置 `false` |
| `switch_show_all_ad` | 仅 `AGGRESSIVE=true` 时置 `false` |
| `kBasicModeDisableRewardAdEnabled` | `true` |
| `ad_reward_position_exp` | 仅 `AGGRESSIVE=true` 时置 `0` |

三个开关：

```js
const ENABLED = true;          // false = 完全放行
const DRY_RUN = false;         // true = 只打日志
const AGGRESSIVE = false;      // true = 关全局广告开关 + 隐藏播放器激励入口
const INJECT_MISSING = false;  // true = 响应缺失时补空配置
```

脚本兼容五种响应形态：扁平字典、`{settings:{...}}`、`{data:{...}}`、`{key,value}` 数组、整个响应是 JSON 字符串。非 JSON / 解析失败一律原样放行。

**可选 SDK 设置端点**：`is.snssdk.com/service/settings/v3/` 的调用方是 `BDADSDK.SettingsManager`（Pangle 广告 SDK 设置），`i.snssdk.com/service/settings/v3/` 的调用方是 `Unisus` 通用设置。两者在 v1.x 设置插件里以注释形式给出；当前聚合插件默认只声明 `conf.qishui.com`，需要更上游关闭广告时再手动加 `[Script]` / `[MITM]`。它们比 `conf.qishui.com` 更容易触发证书固定，默认不碰。

> ⚠️ 设置层是**实验功能**，由 `settingsClean` 开关控制。`conf.qishui.com` 若证书固定，MITM 会失败；关闭 `settingsClean` 或停用插件即可回滚，保奖励模式不受影响。

### 3.8 聚合单插件与 Loon 限制

`soda.plugin` 是 Soda 唯一部署插件，使用 Loon `[Argument]` 的 `switch` / `select` 控件，把脚本启停和按钮行为做成参数：

<!-- >>> GENERATED ARG-TABLE from src/args/soda.json -- do not edit (npm run build:args) -->
| 开关/参数 | 默认 | 作用 |
|---|---|---|
| `rewardSafe` | 开 | 保奖励优先；`sanitize` 对非开屏端点直接放行，`settings` 直接放行，域名拦截脚本也放行 |
| `cleanAds` | 关 | 广告位、信息流、福利页广告任务等清理脚本（**不含激励素材**） |
| `killRewardAds` | 关 | 清空激励广告素材与预拉取 + 兜底发奖凭证；开了领奖会变 `amount=-1` |
| `blockAdDomains` | 关 | `block-domains.js`：`http-request` 拦截 `ad.zijieapi.com`、`lianmengapi.snssdk.com`、`ads?-normal*.zijieapi.com` 等广告/归因域名 |
| `settingsClean` | 关 | `conf.qishui.com` 设置层脚本 |
| `skipUpdateCheck` | 关 | `luna/check-update` 响应的 `has_update` → `false`，静音「发现新版本」提示；只动这一个键、解析失败原样放行（取证依据 `STNetProto.CheckUpdateRequest`／`CheckUpdateResponseInfo`／`has_update` 字符串簇 + 真机日志） |
| `hideDouyinEntry` | 关 | 关掉设置层 `anchor_luna_to_douyin` / `_mv` → 汽水里的【听抖音】入口不再出现（服务端配置驱动，不动广告配置，可与保奖励同开） |
| `blockSplashAd` | 开 | 拦掉穿山甲开屏广告请求（`splash/` 与 `vN/(ack/)splash/` 全家族），**不碰激励广告**（`ad.zijieapi.com/api/ad/v1/inspire` 与发奖回调照常） |
| `debugLog` | 关 | 只读观测脚本（记录响应，不修改内容） |
| `logTaskTitles` | 关 | 只读日志里额外打印任务标题（`听抖音`/`签到得金币`…），用来定位福利页入口；默认关闭，避免把文案写进日志 |
| `splashClean` | 开 | 开屏品牌广告清理 |
| `hideDouyinTab` | 关 | 福利页带“抖音”的 tab/任务条目过滤（**只按标题字段匹配**，不扫正文；独立绑定，不需要 `cleanAds`） |
| `dailyReminder` | 关 | 每天 cron 时间检查：当天没打开福利页就发 Loon 通知（只提醒不代领） |
| `reminderCron` | `30 20 * * *` | 提醒时间，五段 cron（分 时 日 月 周），默认每天 20:30 |
| `statusNotify` | `notification` | 状态自检按钮的通知模式：`notification` 弹通知并带 `openUrl`，`silent` 只写日志和结果页（Loon `[Argument]` `select` 类型）；结果页汇总当前开关并提示冲突组合，同时输出 `$loon` / 脚本名与执行时间 / 节点 / 运行模式（`$config.getConfig()`） |
<!-- <<< GENERATED ARG-TABLE -->

关键限制：

- **`[Rule]` 不能按开关启停**。Loon 的插件参数只能传给 Script / Rewrite；域名规则仍是静态配置。
  所以“域名拦截”改用 `http-request` 脚本实现（`blockAdDomains` 开关）：
  - 开关关闭 → 脚本不执行，流量零影响；
  - 开关打开 → 返回 200 空响应，广告 SDK 拿不到广告；
  - `rewardSafe=true` → 脚本内部直接放行，激励广告照常播放。
  - HTTP/3 不再是漏洞：v2.8.0 起 `[Rule]` 常开 QUIC 强制回退（见下），这些域只会走 TCP+TLS。
  - 仍依赖 MITM：所以它不能替代 `ads.plugin` 的 DNS 层，两者互补。
- **静态传输层（常开，无开关）**：`[Rule]` 对这 17 个广告域名做 `AND,((DOMAIN-SUFFIX,…),(PROTOCOL,QUIC)),REJECT`，
  把 HTTP/3 逼回 TCP；`[MITM]` 另写 `h2 = true`（未文档化键，零成本冗余，见下）。
  这两项不提供开关——关掉等于让所有脚本看不见流量。回滚方式：删掉对应行。
- **`[MITM]` 也不能按开关启停**。插件声明 `api.qishui.com, conf.qishui.com` 与 5 个广告域名；即使 `blockAdDomains` 关闭，这些域名也会被解密。如果开启后激励广告播不了（证书固定），把 `[MITM]` 里那 5 个广告域名注释掉即可。
- **开关冲突保护**：`rewardSafe=true` 时脚本优先保护非开屏端点；但仍建议不要同时打开 `rewardSafe` 与 `cleanAds` / `settingsClean`。

---

## 4. 分层设计

| 层 | 内容 | 默认 | MITM |
|---|---|---|---|
| **L0** | 传输层：17 条 QUIC 回退（8 个 `[MITM]` 条目，含 Pangle 10 个分片）+ `h2` | ✅ 常开（无开关） | 是（前置条件） |
| **L1** | `ad.zijieapi.com`、`lianmengapi.snssdk.com`、`ads?-normal*.zijieapi.com`（Pangle 分片族）、`zlink.ugsdk.cn`、`praisewindow.ugsdk.cn`（App Store 评分）→ 拦截 | ⬜（`blockAdDomains` 开关） | 是（脚本） |
| **L2** | 字段级裁剪（见 3.2） | ✅ 部分（`cleanAds` 开关） | 是 |
| **L2.5** | 设置层：`conf.qishui.com/service/settings/v3/`；可选 `is.snssdk.com` / `i.snssdk.com` | ⬜（`settingsClean` 开关） | 是 |
| **L3** | 埋点 `mon/log/applog.zijieapi.com`、`log.qishui.com`、风控 `timon` | ⬜ | 否 |

L0 常开：它不拦任何业务流量，只决定“脚本能不能看见流量”。关掉它，L1/L2/L2.5 会随机失效。
L1 默认关闭：广告域名被拦后，激励广告就播不了，保奖励模式必须放行。
L3 默认关闭：拦 `timon` / `gurd` 可能影响登录与风控校验。

> 跨插件分层：L1 的 5 条里，`ad.zijieapi.com` / `lianmengapi.snssdk.com` /
> `ads?-normal*.zijieapi.com`（Pangle 分片族）三条同时也在 `ads.plugin` 的
> `[Host]` + `DOMAIN-WILDCARD` 家族层被拦截；
> `zlink.ugsdk.cn` / `praisewindow.ugsdk.cn` 是 App 内运营端点（口令/弹窗），只由本插件
> 的开关覆盖，不进全局 DNS 插件。两者互补：DNS 层在解析阶段拦，MITM 层按开关做
> App 内精准控制；刷奖励关掉 `ads.plugin` 时，本层 L1 仍然可用。

---

## 5. Loon 规范落地：Rule / Rewrite / Script / MITM

插件按 Loon 的四段式组织：

| 段 | 作用 | 需要 MITM |
|---|---|---|
| `[Rule]` | 传输层：8 个 MITM 域 `AND+PROTOCOL,QUIC` → `REJECT`（常开） | ❌ |
| `[Rewrite]` | URL 级重写：上报端点 `reject_dict(200)`（开关） | ✅ |
| `[Script]` | 字段级响应改写 + 广告域名拦截脚本（保留包络） | ✅ |
| `[MITM]` | 声明 `api.qishui.com`、`conf.qishui.com` 与 5 个广告域名（域名拦截开关需要）+ `h2 = true`（未文档化键，保留作冗余） | ✅ |

> Loon 的 HTTPS Rewrite 必须先经 MITM 解密，才能看到路径并匹配。所以 `[Rewrite]` 不是"无 MITM"方案；
> 真正的无 MITM 方案是 `ads.plugin` 的 DNS 层。`[Rule]` 在插件里也不能写死业务域名的 REJECT——
> 那会直接掐断激励广告，所以域名拦截保留为脚本开关。

### 5.1 历史模式（A/B/C/D/E，已合并）

> 当前只部署 `soda.plugin` 一个聚合插件；以下 A-E 是 v1.x 的设计记录，不再需要分别安装。实际使用看 3.8 的七个开关。

**A. 精准模式（默认，推荐）**

```
[Rule] + [Rewrite] + [Script] + [MITM]
```

- 保留 `status_code` / `status_info` / `expire_time`
- 只清 `advert_sources` / `ad_infos_map` / `feed_advert_config`
- 福利页只摘 `reward_ads`，保留签到/听歌/分享/逛商城/翻牌

**B. 轻量模式（仍要 MITM，不跑脚本）**

```
[Rule] + [Rewrite] + [MITM]
```

操作：注释掉整个 `[Script]`，保留 `[MITM]`，取消 `[Rewrite]` 里"轻量模式"段的注释。

代价：返回 `{}` / `[]`，可能触发解码失败或重试。好处是不执行 JS，开销更低。

**C. 纯域名模式（无 MITM）**

```
[Rule]
```

只拦广告 SDK 域名，不做 URL / 字段级处理。注释掉整个 `[Rewrite]`、`[Script]`、`[MITM]`。

**D. 配置层模式（实验，独立插件）**

```
主插件 A + SodaClean-Settings.plugin
```

`SodaClean-Settings.plugin` 只做一件事：MITM `conf.qishui.com`，用 `src/soda/settings.js` 清空 TTKitchen 下发的广告配置。与主插件可同时安装，`[Rule]` 重复域名会自动去重。

**E. 保奖励模式（独立插件，Reward Safe）**

```
只用 SodaClean-Reward.plugin
```

适合“我要完整看完激励视频，正常拿奖励”：

- 不拦 `ad.zijieapi.com` / `lianmengapi.snssdk.com` / `ads?-normal*.zijieapi.com`，激励广告能加载；
- 不跑 `incentive/config` / `incentive/retrieve` / `ads/config` / `ads/retrieve` 脚本，广告源、广告位与 `reward_config` 保持原样；
- 不跑 `treasure/task/view` / `treasure/entrance` / `growth/activity_entrance` 脚本，奖励任务与入口保留；
- 不碰 `incentive/done` / `ads/reward/receive|settle` / `commerce/validate_reward`；
- **不跑 upsell 脚本**：二进制里有 `UpsellStyleRewardAdsDefault` / `UpsellStyleRewardAdsExposureReward` / `reward_btn_text` / `reward_ads_cold_start_style`，upsell 可能承载“看广告得奖励”入口，清掉会减少奖励机会；
- 只清开屏品牌广告；
- **`[Rule]` 为空**：连 `praisewindow.ugsdk.cn` 也不拦。它是 App Store 评分弹窗（`AppStoreStarAdapter` / `/zebra/praise/click`），不是激励广告域名；为不误伤“去评分/引导”类非广告任务，保奖励模式不拦任何域名。

代价：信息流、DSP 与商业弹窗可能仍会出现。**不要与主插件或设置插件同时启用**；主插件的 `[Rule]` 与脚本会再次把激励链路清掉。如果 MITM 被证书固定拦截（App 断网/广告 SDK 初始化失败），停用 `[Rewrite]`、`[Script]`、`[MITM]` 三段即可（`[Rule]` 本来就是空的）；奖励按 App 原始流程走。

> 合规边界：保奖励模式只保证“广告正常播放后，奖励链路不被插件破坏”。它不跳过广告、不伪造回调、不提供屏蔽广告后领奖。

### 5.2 为什么 `[Rewrite]` 只放少量纯上报端点

纯上报端点是 fire-and-forget，没有业务包络需要保留，适合在 Rewrite 阶段直接回包：

```
luna/advert/splash/brand/report
luna/ads/report/dsp/show
```

两条都用原生 `reject_dict(200)`：返回 JSON `{}` 且带 `application/json`，SDK 按 JSON 解码不会报错。官方的 `reject(200)` 返回空 Body（`text/plain`），`reject(200, "{}")` 也只是普通文本——需要 JSON Content-Type 时必须用 `reject_dict` / `reject_array`。

配置类端点不能直接 `reject_dict`：会丢掉 `status_code`，App 可能重试或走默认值——所以交给 `[Script]` 保留包络、只清广告容器。

### 5.3 语法说明

本插件使用 Loon 3.5.1(983)+ 的新版 Rewrite 语法：

```
request if ${splashClean} == true && ${url} ~= /^https?:\/\/api\.qishui\.com\/luna\/advert\/splash\/brand\/report/ then reject_dict(200)
request if ${cleanAds} == true && ${url} ~= /^https?:\/\/api\.qishui\.com\/luna\/ads\/report\/dsp\/show/ then reject_dict(200)
```

注意不是 Surge 的 `url reject`。`reject_dict(status)` 的状态码范围是 100–599；HTTPS 命中需要该域名在 `[MITM]` 中。

### 5.4 请求侧减负：开屏广告请求拦截（默认开）

`blockSplashAd` 使用 `http-request` 脚本（与 douyin 共用 `src/common/splash-ad.js`，家族差异只有日志前缀），在请求发出前返回 200 + JSON `{}`，走穿山甲（CSJ）开屏素材获取与登记端点的请求不会真正出网。绑定覆盖：

```
/api/ad/splash/                    # luna/aweme/v14/v15、stock/realtime 等
/api/ad/vN/splash/                 # 版本化库存
/api/ad/vN/ack/splash/             # ack 上报
```

激励广告（`ad.zijieapi.com/api/ad/v1/inspire/**`）与发奖回调（`api/incentive/marketing/done`）不在匹配范围内，保奖励模式不受影响。如果开启后激励广告播不了（证书固定），把 `[MITM]` 里的广告域名注释掉即可。

### 5.5 激励链路观测（只读）

在 `soda.plugin` 里打开 `debugLog` 开关；脚本不拦域名、不改写、不返回 body，只把关键结构写进 Loon 日志，前缀 `[soda-reward]`。

它观察 20 个端点：`incentive/config`、`incentive/retrieve`、`incentive/done`、`ads/config`、`ads/retrieve`、`ads/dsp/retrieve`、`ads/reward/receive`、`ads/reward/settle`、`commerce/validate_reward`、`treasure/task/view`、`treasure/entrance/config`、`treasure/task/reward_ads/do_action`、`treasure/task/fallback/do_action`、`treasure/task/flip_card/do_action`、`treasure/task/guide/do_action`、`treasure/task/browse_mall/do_action`、`growth/activity_entrance`、`growth/activity/finish`、`advert/fallback/done/info`、`commerce/v2/upsell`。

`commerce/v2/upsell` 只打印奖励入口资格变量（`enable_ads`、`enable_coin`、`ads_today_task_full`、`ads_days_obtained`、`max_release_days`、`reward_tasks_count`、`has_play_entitlement`、`can_show_cold_launch_popup_coin`、`coin_new_user_first_launch_opt`），以及 `sceneUpsellsMap` / `scene_upsells_map` 的场景名、数量、`fixedEntrance` / `coinWidgetData` 出现次数；不打印弹窗标题、正文、图片、跳转链接或会员到期时间。`/v2/upsell_sort_decision` 刻意不观测，避免和入口响应混淆。

日志会给出：

- `status` / `statusInfo`：服务端状态码与简短错误信息（长 token 会脱敏）；
- `counts`：`advert_sources` / `ad_infos_map` / `ad_unit_configs` / `reward_config` / `task_infos` 等数组或对象的条目数；
- `preload`：激励配置是否要求预加载；
- `progress`：`PlayEntitlements.reward_finished_task_info` 的 `days_obtained` / `full_day` / `all_full` / `tasks_finished` / `task_to_full_day`，用来看“今天是否已看满”；
- `tasks`：`task_key` / `reward_type` / `reward_amount` / `reward_max_amount` / `valid_duration` / `can_show` / `stats.total_times` / `stats.completed_times` / `stats.last_rewarded_time` / `ad_snap` 是否存在（最多 12 条，不含完整文案）；
- `reward`：`reward_details` / `reward_tips` / `is_valid` / `transaction_success` / `play_entitlements` / `max_release_days` / `reward_advance_release_days` 等发奖字段的摘要；
- `upsell`：奖励入口资格变量与 `scene_upsells_map` 场景数；用于判断“奖励入口为什么不出现”，不修改任何弹窗。

隐私与开销：只打印结构、计数和白名单字段，不打印 token / cookie / `device_id` / 用户 ID / 素材 URL；超过 256KB 的响应只记录长度，不解析。

使用注意：

- 可与 `rewardSafe` 同时启用；这是推荐的排障组合；
- **不要**同时开 `cleanAds` / `settingsClean`：清理脚本会先改掉激励字段，日志看到的是“已清空”的假象；
- 排障完成后关闭 `debugLog`，避免长期打印日志。

### 5.6 20.5.0 奖励字段补全（Swift 元数据）

本轮从 `__swift5_types` 类型描述符和 field descriptor 还原了奖励模型的真实字段，补齐了只看字符串时容易混淆的归属：

| 模型 / 字段 | 作用 | 保奖励处理 |
|---|---|---|
| `Incentive.available` / `expireTime` / `cooldownEndTime` / `maxReleaseDays` | 激励是否可用、过期/冷却、最多提前释放天数 | 保留，不改 |
| `IncentiveRewardType`：`default` / `qualityAndEffect` / `coin`；`IncentiveQuestsType`：`main` / `sideQualityAndEffect` | 金币、音质/音效权益、主/侧任务 | 保留，不改 |
| `PlayEntitlements.rewardFinishedTaskInfo`：`daysObtained` / `fullDay` / `allFull` / `tasksFinished` / `taskToFullDay` | 今日/累计是否看满 | 只读观测 |
| `AdUnitConfig.rewardAdvanceReleaseDays` + `RewardReceiveScene.advanceReleaseTimeReceive` | 看广告提前释放未来奖励 | 保留，不改 |
| `RewardAdActionSheetScene.rewardRetry` / `rewardLoadFailed` / `rewardExpired` | 官方重试、加载失败、过期处理 | 保留，不改 |
| `UpsellVariable.enable_ads` / `ads_today_task_full` / `ads_days_obtained` / `max_release_days` / `reward_tasks_count` | 入口资格与今日进度 | 不修改 upsell |

关键纠正：`incentive/done` 的**响应**只有 `status_code` / `status_info` / `reward_details` / `reward_tips`；`is_valid` 属于 `ads/reward/settle` 的 `RewardOfferResponseInfo`，`compensate` / `launch_duration` / `quests_type` 属于 `IncentiveDoneRequest`（请求字段）。不要把请求字段当成响应字段，也不要用它们绕过发奖校验。

> 这些字段只用于判断“入口是否下发、今天是否看满、奖励是否到账”。不要改 `task_token` / `transaction_id` / `sign` / `valid_duration`，也不要在未看完广告时调用发奖接口。

---

## 6. 安装

部署目录是 `plugins/soda/`：**一个** `soda.plugin` + `scripts/*.min.js`。推送前先运行 `npm run build` 生成压缩脚本；`src/`、`tests/` 可以保留在仓库里，不需要单独上传。

1. 把仓库推到 `AshNail/plugins`（`main` 分支，**无需开启 GitHub Pages**）；
2. 插件位于 `plugins/soda/`，Loon 以插件 URL 为基准解析同目录 `scripts/*.min.js`；
3. 只导入这一个插件：

[![一键导入 soda.plugin](https://img.shields.io/badge/Loon-导入汽水音乐-blue?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fsoda%2Fsoda.plugin)

```text
loon://import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fsoda%2Fsoda.plugin
```

5. Loon → 设置 → MITM → 生成证书 → 安装并信任；
6. `soda.plugin` 的 `[MITM]` 已声明 `api.qishui.com` + `conf.qishui.com` + 5 个广告域名。`settingsClean` / `blockAdDomains` 关闭时，这些域名仍会被解密，但脚本直接放行。

聚合插件的开关：

| 开关 | 默认 | 作用 |
|---|---|---|
| `rewardSafe` | 开 | 保奖励优先；非开屏端点直接放行，域名拦截也放行 |
| `cleanAds` | 关 | 去广告脚本：广告位、信息流、福利页广告任务（**不动激励素材**） |
| `killRewardAds` | 关 | 断掉激励广告素材与预拉取（= 广告完全不发，领奖会变 `amount=-1`） |
| `blockAdDomains` | 关 | 广告/归因域名拦截（MITM + `http-request` 脚本；QUIC 已由静态层强制回退，不再漏 HTTP/3） |
| `settingsClean` | 关 | 设置层净化；不要与 `rewardSafe` 同开 |
| `debugLog` | 关 | 只读日志，可与保奖励同开 |
| `splashClean` | 开 | 清理开屏品牌广告 |
| `hideDouyinTab` | 关 | 隐藏福利页【听抖音】tab/任务条目 |

推荐组合：

- **正常领奖励（默认）**：`rewardSafe=开`，其余默认；只清开屏品牌广告。
- **排障**：在保奖励基础上打开 `debugLog`，日志搜 `[soda-reward]`。
- **去广告**：`rewardSafe=关`、`cleanAds=开`、`splashClean=开`。
- **强力去广告**：再加 `blockAdDomains=开`；若激励广告因此播不了，把 `[MITM]` 里 5 个广告域名注释掉。
- **隐藏听抖音**：`hideDouyinTab=开`（独立生效，不需要 `cleanAds`；`rewardSafe` 同开时只删抖音条目，不做广告裁剪）。
- **强力域名拦截**：关闭 `rewardSafe` 后开 `blockAdDomains` 即可；HTTP/3 已由 `[Rule]` 的 QUIC 回退覆盖，不需要再手改静态规则。

> Loon 的 `[Rule]` 不能按开关关闭，所以域名拦截改用脚本实现（`blockAdDomains`）：开关关闭时零影响，`rewardSafe=true` 时自动放行。
> 唯一需要静态层兜的是传输协议：v2.8.0 起 8 个 MITM 域常开 QUIC 回退，脚本才能稳定看见流量。

> 【听抖音】默认保留。它属于福利页的正常任务条目，`hideDouyinTab` 打开后只删除带“抖音”字样的列表项，不动签到 / 听歌 / 分享 / 金币 / 逛商城 / 翻牌 / 引导。字段定位以你提供的珠宝页 HAR 为准。

> 插件里的 `script-path=scripts/...` 是相对路径，所以 `.plugin` 和 `scripts/` 必须保持同级；不要只发单个 `.plugin` 文件。导入用 raw 直链即可，无需 Pages。

> ⚠️ 若 MITM 后 App 断网，说明 TTNet 启用了证书固定。此时把 `[Rewrite]`、`[Script]` 与 `[MITM]` 整段注释，退回 C（纯域名拦截仍然有效）。实验插件同理，停用即可回滚。

---

## 7. 验证

| 检查项 | 方法 |
|---|---|
| 广告是否消失 | 开屏、金币任务、听歌页激励卡片 |
| 改写是否命中 | Loon 日志搜 `[soda]` |
| 设置层是否命中 | Loon 日志搜 `[soda-settings]`，应出现 `change(s)` 或 `no ad setting change` |
| SDK 设置层是否命中（可选） | 启用 `is.snssdk.com` 后搜 `[soda-settings]`；若断网/广告 SDK 初始化失败，停用该行 |
| 包络是否保留 | 日志里 `status_code` 不应缺失 |
| App 是否异常 | 福利页、播放页、会员页各走一遍 |
| 保奖励模式是否生效 | 只装 `soda.plugin`；默认 `rewardSafe=true`，奖励任务应保留，开屏品牌广告应消失，信息流/DSP/商业弹窗可能仍在 |
| 去广告脚本是否生效 | `rewardSafe=关`、`cleanAds=开`；开屏/信息流/福利页广告任务应减少 |
| 域名拦截是否生效 | `blockAdDomains=开`；Loon 日志搜 `[soda-domains] blocked`；若某次仍无日志，先看 Loon 规则日志里 QUIC 回退是否命中 |
| 【听抖音】是否消失 | `hideDouyinTab=开`；福利页不再出现“听抖音”条目，签到/听歌/分享仍在 |
| 奖励是否正常到账 | 完整看完激励视频，确认金币/畅听/翻牌等奖励到账；不要跳过广告或伪造回调 |
| 激励链路是否下发 | 打开 `debugLog`，日志搜 `[soda-reward]`；看 `counts.sources` / `counts.adInfosMap` / `tasks` / `reward` 是否为空 |

本地回归：`npm run check`（build + lint + coverage + 源码/压缩版测试）。单独跑：`python3 tests/run-all.py`（26 套 / 798 条断言，源码与压缩版各一遍，共 1596 条）；`python3 tests/lint-plugins.py` 检查 1 个聚合插件。

建议顺序（严格去广告）：**先确认保奖励模式 → 关闭 rewardSafe → 开 cleanAds → 最后开 blockAdDomains**，每一步观察一天。

保奖励模式不要开 `cleanAds` / `settingsClean`；只保留 `splashClean`，需要排障时再开 `debugLog`。

---

## 8. 已知副作用

| 现象 | 原因 |
|---|---|
| 福利页提示「广告加载失败」 | 广告域名被 REJECT |
| 可能出现「视频加载失败，先送你60分钟」 | App 自身补偿分支（`0x10ebf1d00` ← `0x106a395b4`） |
| 金币/福利入口里少一项 | 只摘了 `reward_ads` 广告任务；签到、听歌、分享不受影响 |
| 会员页/商城入口异常 | `upsells` 裁剪过度，注释该条恢复 |
| 冷启仍闪一次开屏 | 本地已缓存的开屏素材（`SplashAdCacheManager`）可能先展示；网络层只能阻止新拉取 |
| 信息流广告残留 | 广告条目是 `video + ad_info` 时，默认保守策略只清 `ad_info`，不丢整条；按 3.6 改成看到 `ad_info` 就丢 |
| SDK 日志「注册广告位失败」 | `ad_unit_configs` 被清空，属预期，不影响播放 |
| 金币挂件只剩签到/累积/可领取 | `coin_widget_state_list` 里的 `widgetAdReward` 广告态被摘掉，属预期 |
| 金币挂件仍显示广告态 | 福利页 `coin_widget_state_list` 广告态已由 `treasure-entrance` 摘除；upsell 的 `fixedEntrance.coinWidgetData` 是入口配置，尚无真机广告态字段样本，暂不裁剪 |
| 广告配置有本地缓存 | 首次启用后旧配置可能仍生效；清 App 缓存/重装，或等 `expires_at` 过期 |
| 打开设置层后 App 设置加载失败/断网 | `conf.qishui.com` 证书固定；关闭 `settingsClean` 回滚 |
| 启用 `is.snssdk.com` 后广告 SDK 初始化失败/崩溃 | BDADSDK 设置被清空或证书固定；注释该 Script/MITM 行，只保留 `conf.qishui.com` |
| 设置层日志 `no ad setting change` | 响应里没有广告配置键，或字段名变了；打开 `diag.js` 看结构 |
| 信息流广告整条消失但正常内容也少了 | 该条目命中了 `card.is_ad` 嵌套判定；把 `sanitize.js` 的 `hasNestedAdFlag` 收紧或关掉 |
| MITM 后无法联网 | 证书固定，退回 L1 |

---

## 9. 继续扩展

1. 打开 `diag.js`（插件里已注释），跑一轮拿到**其他端点**的真实结构；
2. 在 `sanitize.js` 的 `RULES` 里加一条：
   ```js
   { id: "xxx", match: /\/luna\/xxx\//, kill: ["someList"], falsy: ["show"] }
   ```
3. 先 `DRY_RUN=true` 验证键名命中，再切 `false`；
4. 版本升级后回归：接口路径与字段可能变；
5. 开屏 / 信息流仍有残留时，先看 Loon 日志里的 rule id：
   - `splash-brand` 没命中 → 检查 URL 是否带前导 `/`、MITM 是否生效；
   - `feed-ads` 显示 `no ad marker` → 该响应确实没有广告字段；
   - `feed-ads` 命中了但广告还在 → 把 `isAdItem` 改成看到 `ad_info` 就丢，或把 `card.is_ad` 判定扩展到更多嵌套键；
   - 搜索页/卡片页残留 → 已覆盖 `search-block` / `search-categories` / `card`，若仍有新端点，按 9.2 加规则并同步插件 `[Script]` 正则；
   - 兜底广告残留 → 检查 `advert/fallback/done/info` 是否被 MITM，或响应字段是否不在 `ads` 规则的 `kill` 列表里。
6. 设置层没命中时，先把 `soda.plugin` 里设置层的诊断行取消注释，确认响应结构：
   - 日志里出现 `[soda-diag]` 但没有广告键 → 服务端没下发，考虑 `INJECT_MISSING=true`；
   - 出现 `commerce_ad_config` 但脚本没改 → 检查是否被包在 JSON 字符串里；
   - `conf.qishui.com` 完全没请求 → 试开 `is.snssdk.com`（BDADSDK）或 `i.snssdk.com`（Unisus）的可选行；
   - App 断网 → 证书固定，停用实验插件。
7. 想验证“广告加载失败”是否触发补偿分支，先只开 L1，观察是否出现「先送你60分钟」；这是 App 自身行为，不是插件伪造。

---

## 10. 文件结构

```
loon-plugins/
├── README.md                       # 仓库总览（多插件族）
├── plugins/
│   └── soda/                       # 汽水音乐插件族（部署目录）
│       ├── README.md               # 本文件
│       ├── soda.plugin             # 唯一部署插件（聚合开关版 v2.8.7）
│       └── scripts/                # 压缩后的部署脚本
│           ├── sanitize.min.js
│           ├── settings.min.js
│           ├── reward-observe.min.js
│           ├── splash-ad.min.js
│           ├── status.min.js
│           ├── block-domains.min.js   # ← 与 douyin 同源（src/common 生成）
│           ├── daily-reminder.min.js  # ← 与 douyin 同源（src/common 生成）
│           └── welfare-stamp.min.js   # ← 与 douyin 同源（src/common 生成）
├── src/
│   ├── common/                     # soda/douyin 共享脚本单一来源 + families.json
│   └── soda/                       # 可读源码（共享脚本为生成物）
│       ├── sanitize.js
│       ├── settings.js
│       ├── reward-observe.js
│       ├── splash-ad.js            # ← src/common 生成，勿手改
│       ├── status.js               # ← src/common 生成，勿手改
│       ├── block-domains.js        # ← src/common 生成，勿手改
│       ├── daily-reminder.js       # ← src/common 生成，勿手改
│       └── welfare-stamp.js        # ← src/common 生成，勿手改
├── tools/
│   └── build.js                    # src/common 家族展开 + src -> plugins 压缩构建
├── tests/                          # 脚本层回归测试（26 套 / 798 条断言 × 2 = 1596）
├── package.json
├── package-lock.json
├── .github/workflows/check.yml     # CI：build + lint + 测试
├── .nojekyll                       # 防御性保留：若日后启用 Pages，避免 Jekyll 处理 .plugin / scripts
└── .gitignore
```

> `.plugin` 里的脚本路径指向同级的 `scripts/*.min.js`；`src/` 只用于阅读和改代码，不参与 Loon 加载。

---

## 10.5 2026-10-21 抓包新增取证（soda.plugin v2.4.0）

### 1. 响应体是 gzip 的 → 脚本要自己解压

`/luna/advert/incentive/done`、`conf.qishui.com/service/settings/v3/` 的回包都是
`content-encoding: gzip`（真机日志里有 `zip decompress error:-3`）。
Loon 偶尔把**未解压的压缩串**交给脚本，`JSON.parse` 直接失败 → 脚本静默放行 → 看起来“插件没效果”。
v2.4.0 起 `readBody()` 会识别 gzip 魔数并用 `$utils.ungzip`（Build ≥ 988）解压，
也能直接吃 `Uint8Array`；每个被处理的响应都带 `X-Soda-Plugin` 诊断头。

**只支持 gzip，br 解不了。** 这是 Loon 的硬边界，不是实现偷懒：

- 脚本 API 的完整清单里，能解压的只有 `$utils.ungzip`（gzip）。没有 brotli / zstd /
  inflate 的入口，也没有 `decompress(data, algo)` 这种通用方法。
- **br 没有魔数**。RFC 7932 定义的是纯 stream format，不含 checksum、也不含原始长度，
  所以脚本连「这段字节是不是 br」都判断不出来——只能看 `content-encoding` 响应头。
  这点和 gzip 不同：`1f 8b` 两个字节就能认。
- Loon 官方复写文档全文没出现过 `gzip` / `brotli` / `Content-Encoding` 任何一次。
  唯一沾边的一句是「修改响应 Body 后，Loon 会根据传输协议处理 Content-Length、
  Transfer-Encoding 和 Content-Encoding 等相关 Header」——那是**写出**时对齐头，
  不是**读入**时解压。自家真机日志里 gzip 都出现过 `zip decompress error:-3`，
  更不能指望它默默把 br 解好。

v2.8.1 起 `readBody()` 旁边多了 `ceTag()`：遇到解不了的编码，诊断标记变成
`soda-sanitize;skip=not-json;ce=br`。在这之前「接口换成 br 了」和「接口本来就不是
JSON」都只写 `skip=not-json`，排查方向会完全错。`gzip` / `identity` / 没有该头时
不加这段，标记保持干净。

> 真遇到 `ce=br` 怎么修：**不要**删 `Accept-Encoding`（upsell 在 gzip 下已 183–191 KB，
> 去压缩会膨胀 5~10 倍）。只对那一个端点把请求头设成 `Accept-Encoding: gzip`，
> 压缩照旧，只是不许服务端选 br。

### 2. `killRewardAds` 开着会让领奖变成 amount = -1

2026-10-21 10:38–10:41 汽水侧三次 `advert/incentive/done`：

```text
10:40:03  → {"reward_details":{"0":{"reward_type":0,"amount":1800,"claim_status":1}}}       ✅
10:38:46  → {"reward_details":{"0":{"reward_type":0,"amount":-1,"expire_time":1792684812}}}  ⚠️
10:41:21  → {"reward_details":{"0":{"reward_type":0,"amount":-1,"expire_time":1792771215}}}  ⚠️
```

`amount = -1` + `expire_time` = 这笔奖励**没发**（广告素材被清空 → 广告没播 → 领不到）。
**要领奖就别开 `killRewardAds`**（它会把 `incentive/config` 的 `preload`/`vids` 和
`incentive/retrieve` 的素材表一起清掉）。`cleanAds` 也会影响发放路径，同样要慎开。

### 2.1 观测器现在认识“新版福利页”的任务对象

抖音/汽水新版福利页的任务对象是 `{"id":"600585","key":"soda_music_sign_in","view":{...},"stats":{...}}`
（没有 `task_key`），旧版观测器认不出来。v2.5.0 起 `key + id` 且带 `view/stats/rewards` 的对象
也会被当作任务摘要，`logTaskTitles=开` 时连标题一起打出来 —— 这样一次抓包就能定位
【听抖音】到底是哪个字段下发的。

### 3. 抖音侧仍是设备风控（与插件无关）

```text
treasure/task/flip_card/do_action → {"status_code":1000043,"status_info":{"status_msg":"设备异常，领取失败"}}
sign_in_done                      → {"err_no":210021,"err_tips":"设备异常，领取失败"}
```

同一场里 4 次翻卡有 3 次成功、1 次被风控拦；设备分 13.9 + 新加坡环境，插件改不了。

---

## 10.6 2026-10-29 真机日志：luna 主机搬家（soda.plugin v2.8.6）

Loon 引擎日志 113 MB / 1,538,207 行，覆盖 2026-10-29 10:39 → 2026-10-30 09:37（约 23 小时），
汽水音乐 Luna 21.4.0（`version_code=100214010`，iPhone18,4，SG 环境）。

### 1. 旧绑定为什么大面积失效

日志里按主机统计 `Search rule by host:`（每条 = 一次请求）：

```text
beta-luna.douyin.com/luna/*   784 条
api.qishui.com/luna/*           3 条（commerce/ecommerce/order_list，非广告端点）
（两主机另有 99 条非 luna 请求）
```

旧版 34 条 `^https?://api.qishui.com/luna…` api 单主机 luna 绑定在 beta-luna 的
784 条 luna 请求上命中 **0**；整个旧插件只靠两条 beta-only 的 task/page 绑定命中 **1** 条。
v2.8.6 把 34 条前缀统一改成 `^https?://(?:api.qishui.com|beta-luna.douyin.com)/luna`，
同一份日志回放命中 **149/787**（信息流 105、upsell 38+3、激励 2+2、task/page 1、入口 1，含重叠）。
剩下 638 条 luna 请求是 `me/`、`media-stats/`、`comments/`、`action/`、`check-update/` 等非广告面，
**故意不绑**——绑了只是白白多跑脚本。

### 2. 同宿主跨插件竞争（已知边界）

`beta-luna.douyin.com` 同时服务汽水和抖音。日志里 787 条 luna 请求中有 43 条
同时命中抖音插件的响应绑定；Loon 对同一响应只跑**第一条命中的**响应脚本，
所以两个插件都开清理时，跑哪条取决于绑定顺序——可能拿汽水脚本处理抖音响应，反之亦然。
**同时安装两个插件时，清理开关只在一个插件里开**（soda.plugin 的 [Script] 段头也写了这句）。
没有可靠 UA 条件可写，故不做未经验证的自动分流。

### 3. 顺带核实的全局面

- 28,547 次 `Host Map IP:127.0.0.1`，涉及 13 个主机；
  其中 17,073 次 `dns.alidns.com` + 11,239 次 `doh.pub` = 28,312 次（99.2%）是
  `ads.plugin` 的 DoH 防泄漏规则把系统自己的加密 DNS 打进黑洞（见 ads README 的说明）。
- 9,389 次 `NGQUIC-CLOSE host=127.0.0.1`（6,576@443 + 2,813@853）——
  被黑洞的 DoH/DoT 走 QUIC 时的必然结果，属于预期噪声。
- 110 次 `DOMAIN-KEYWORD,httpdns,REJECT-DROP` 命中；13 个被黑洞主机对
  137 个受保护主域（103 手写 + 34 由 App 红线派生）**0 命中**。
- 抖音开屏素材域 12 次 `ads5-normal-hl.zijieapi.com` + 2 次 `ad.zijieapi.com` 被黑洞，
  与 `splash-ad` 的请求拦截互补（一个挡 DNS，一个挡请求）。

---

## 10.7 2026-10-30 版本检查静音 `skipUpdateCheck` + 开屏请求拦截默认开（v2.8.7）

### 1. 取证链（20.5.0 主二进制，按地址序的字符串簇）

`luna/check-update` 与它的请求/响应模型在同一簇里，形态一目了然：

```text
luna/check-update                ← 端点
STNetProto.CheckUpdateRequest    ← 请求模型（Swift）
_TtC10STNetProto18CheckUpdateRequest
（嵌套类型名表）CheckUpdateRequest / Scene / Params / CodingKeys /
                 CheckUpdateResponseInfo / CheckMediaResult
（响应侧同簇字段）media_result / shark_expired_at / has_update
```

真机佐证（§10.6）：`check-update/` 在 2026-10-29 的 23 小时日志里属于 638 条非广告
luna 请求——端点真实在跑，由 `api.qishui.com` + `beta-luna.douyin.com` 双主机承载。

**四个同形键，全部不是版本检查，已排除绑定**：

| 字符串 | 实际归属 |
|---|---|
| `check_update_info` | gecko bytesync 通道 |
| `check_update_result` | 贴纸/特效平台（`/effect/api/panel/*` 同簇） |
| `force_update` | `BDPSensitiveWordsService` 敏感词库资源 |
| `force_update_ts_ms` | 听歌房（ListenTogether）同步协议字段 |

### 2. 设计与边界

- `check-update` 是**只读查询**，不参与任何支付/权益/结算。脚本只把响应里的
  `has_update` 置 false（「要不要提示更新」的判定分支），包络与其它字段零接触。
- `CheckUpdateResponseInfo` 的完整 Codable 键表静态未挖全，所以走防御式形态：
  非 JSON / 解析失败 / 无 `has_update` 键 → **一个字节不动，原样放行**；
  最坏情况 = 「发现新版本」提示还在。诊断标记 `X-Soda-Plugin: soda-check-update;…`
  每个 pass-through 分支都带 `skip=` 与（必要时）`ce=`。
- 不用 `reject_dict(200)`：丢包络会让 App 解码失败重试（§2 的结论）。
- `skipUpdateCheck` 默认**关**，先当实验开关；等 `debugLog` 抓到一次真实响应后
  再考虑收紧字段路径。

### 3. 默认态调整

- `blockSplashAd`（拦穿山甲开屏请求家族）双家族一起默认开：与 `splashClean`
  构成开屏双层（请求侧 + 响应侧），脚本对激励广告与发奖回调零接触。
  抖音插件同开关同开源自 schema 强制的「共享开关跨家族语义一致」规则。
- `rewardSafe` / `splashClean` 老默认不变；`skipUpdateCheck` 新开关默认关。

### 4. 门禁联动

- lint：soda 绑定面 38 → **39**；新增 `enable=${skipUpdateCheck}` 计数 1 与
  `luna-check-update`（双主机正反样本）两个命中样本；`luna host parity` 37 条
  生效 luna 绑定全双主机。
- schema 套件：`skipUpdateCheck` 进 `SWITCH_LABELS` 钉死清单；两家族
  `blockSplashAd:true` / 汽水 `skipUpdateCheck:false` 进「关键默认值」钉死清单。
- 新测试 `tests/test_check_update.js`（23 断言 × src/dist 双跑）：置 false 的
  深层命中与包络保留、同形键不误伤、not-json/no-key/gzip 三条放行路径、
  过期压缩头清理、`ENABLED`/`DRY_RUN` 常量存在性。

---

## 11. 版本更新记录

### v2.8.7（2026-10-30）版本检查静音 + 开屏请求拦截默认开

- **新增 `skipUpdateCheck`（默认关，实验）**：`luna/check-update` 响应的
  `has_update` → `false`，静音「发现新版本」提示。只动这一个键、解析失败原样
  放行（取证：`STNetProto.CheckUpdateRequest` / `CheckUpdateResponseInfo` /
  `has_update` 字符串簇 + §10.6 真机日志；四个同形键已排除，见 §10.7）。
- **`blockSplashAd` 默认值 `false → true`（soda + douyin 双家族）**：
  开屏请求拦截 + 开屏品牌清理构成开屏双层默认开；与激励广告/发奖零接触。
- **lint**：绑定面 38→39、`skipUpdateCheck` enable 计数、`luna-check-update`
  样本；schema 套件钉死新默认值（跨家族一致性按旧规则跑通）。
- **新测试** `tests/test_check_update.js`（23 断言，src/dist 双跑）。

### v2.8.6（2026-10-30）luna 主机搬家：响应绑定从单主机改成双主机

- **根因**：2026-10-29 的 23 小时真机日志里，Luna 21.4.0 把 luna 流量全部发到
  `beta-luna.douyin.com`（784 条），`api.qishui.com` 只有 3 条非广告请求；
  旧版 34 条 api 单主机绑定在这 784 条上命中 0 条，整个旧插件只靠 1 条 task/page 命中——
  插件看起来“完全没效果”。
- **修复**：34 条绑定前缀统一扩成 `(?:api.qishui.com|beta-luna.douyin.com)`，
  并删掉两条因此变得重复的 beta-only task/page 绑定（[Script] 40 → 38 条）。
  同一份日志回放，广告相关面从 1/787 提升到 149/787。
- **新增 lint 门禁 `luna host parity`**：任何生效 luna 绑定少写一个真实主机，
  或 [MITM] hostname 缺一个，`npm run check` 直接报错——单主机绑定 = 静默失效，不许再进仓库。
- **已知边界**：`beta-luna.douyin.com` 同时服务抖音，两个插件都开清理时同一响应只会跑
  第一条命中的脚本；同时安装时清理开关只在一个插件里开。

### v2.8.5（2026-10-27）插件元数据补齐 `#!openUrl`

- **`#!openUrl` 落地**：Loon 插件详情页的「打开链接」现在直达本 README
  （`https://github.com/AshNail/plugins/blob/main/plugins/soda/README.md`），
  装完插件不用回仓库找使用说明。lint 同步要求三插件必须带 https 的 `#!openUrl`。

### v2.8.4（2026-10-27）修掉一处「每量一次广告就清空全部存储」

- **`$persistentStore.remove(key)` 不是「删这个键」**：官方 Script API 5.3 写明它**不接受参数**，
  语义是「清空通过脚本存储 API 保存的全部数据」。原来量完一次广告时长就调它，
  于是 `soda-welfare-seen`（当日打卡）、`soda-ad-stats`（广告统计）、每日提醒的已读标记
  一起被抹掉——而且没有任何报错，只表现为「状态页说今天还没打卡」。
  改成 `write(undefined, AD_START_KEY)`（官方 5.1 的唯一正确写法），只删开始时间这一个键。
- **状态页新增「全局直连」告警**：`running_model = 0` 时 Loon 不执行规则、不进 MITM、不跑脚本，
  插件等于没装。以前只显示「运行模式 直连」四个字，现在会点名并给出处置建议。
  `running_model` 是字符串 `"0"` 也能识别（`Number()` 归一）。
- **新增 `tests/test_store_scope.js`**（12 断言 × 2 套件）：带 `$persistentStore` 桩跑一遍
  「广告结束」链路，断言**别的键必须还在**——只断言「目标键没了」是抓不到这个 bug 的。
- **lint 新增 `SAFE_STORE_WIPE_RX`**：源码或产物里再出现 `$persistentStore.remove(` 直接报错，
  报错信息指向 Script API 5.3。守卫在剥掉注释后的文本上匹配，避免把自己写进注释的解释判违规。

### v2.8.3（2026-10-27）压缩从「事后诊断」变成「事前统一」

- **`[Rewrite]` 把压缩协商降到 gzip（常开，无开关）**：脚本层只有 `$utils.ungzip`，
  br / zstd / deflate 没有解码器，收到就是乱码 → 落进「不是 JSON」分支 → 表现为
  「这个端点本来就没广告」。v2.8.1 的 `ce=br` 只能事后定位，这一版直接在 `[Rewrite]`
  里 `request.header.set("Accept-Encoding","gzip")`，服务端不会再回 br。
  这里是**降级不是免压缩**：upsell 类响应 gzip 后已有 183~191 KB，去压缩会膨胀 5~10 倍（E2）。
- **回写 body 时清掉过期的压缩头**：`markHeaders(reason, bodyChanged)` 在带回新 body 时
  删掉原响应头的 `content-encoding` / `content-length`。它们指向的是压缩前的旧 body：
  留着会让客户端拿明文按 gzip 解（JSON 解析失败）或按旧长度截断。只加诊断头的分支不动它们。
- **`blockAdDomains` 回包对齐 `reject_dict(200)`**：从 `200 + 空 text/plain` 改成
  `200 + application/json + {}`。官方写明「`reject(200,"{}")` 返回普通文本，需要 JSON
  Content-Type 时用 `reject_dict`」，空 text/plain 会让按 JSON 解析的广告 SDK 走重试。
- **`debug=${debugLog}`**：每条 `[Script]` 都挂上官方 `with debug` 属性，打开「只读日志」时
  同时打开 Loon 原生脚本调试输出（命中哪条、耗时、异常），不用再靠 `console.log` 猜。
- **lint 新增三道守卫**：`Accept-Encoding` 只允许 `set(...,"gzip")`（删压缩/改 identity 直接报错）；
  降级规则必须覆盖 `[MITM]` 的每一个域名（漏一个＝那个域名静默失效）；状态看板补「压缩→gzip」。

### v2.8.2（2026-10-27）广告拦截从「单分片」升级为「全族」

- **`[MITM]` 用通配代替枚举**：`ads5-normal-hl.zijieapi.com` → `ads?-normal*.zijieapi.com`。
  官方文档写明 `[MITM] hostname` 支持 `*` / `?`，这条同时覆盖 `ads3/ads5 × normal/-hl/-lf/-lq/-xh`。
  之前只要服务端把分片从 ads5 换到 ads3，`blockAdDomains` 就整个静默失效——解密名单里没有它。
- **QUIC 回退补到 17 条**：`[Rule]` 的 `DOMAIN-SUFFIX` 不吃通配，只能逐个列 10 个分片。
  两边各用自己最强的写法，覆盖关系由 lint 的 `mitm_covers()` 按 glob 校验。
  清单取自本仓库 `ads.plugin` 的公开广告数据，不是猜的。
- **`BLOCKED_HOSTS` 支持 glob**：`?` 一个字符、`*` 任意字符，脚本里预编译成正则。
  `[Script]` 正则同步改成 `ads[0-9]-normal[a-z0-9-]*\.zijieapi\.com`。
  lint 从「字面集合相等」改为「正反 URL 样本双向命中」，因为名单里出现 glob 后集合比对没有意义。
- **状态看板**：`静态层：QUIC 回退 17 域`。
- **通知剪贴板**：点状态自检通知除了打开 App，还会把完整诊断复制到剪贴板（`attach.clipboard`），
  报障时直接粘贴即可。

### v2.8.1（2026-10-27）编码诊断：把「解不了」和「不是 JSON」分开

- **`readBody()` 旁边新增 `ceTag()`**：读 `content-encoding`，非 gzip 时给诊断标记加上 `;ce=br`
  这样的尾巴。之前 br / zstd / deflate 的响应体都会以乱码落进 `skip=not-json`，和
  「接口换了形状」长得一模一样，排查方向会完全错。
- **`skip=json-parse` 分支同样带上 `ce=`**：压缩体偶尔能凑巧以 `{` 开头，这时失败发生在
  `JSON.parse` 而不是头部判断，两条路都得有线索。
- **`gzip` / `identity` / 无该头不加 `ce=`**：正常路径的标记保持干净，不给抓包添噪声。
- **两个观察器补上同一线索**：`reward-observe.js` 的 `non-JSON` / `JSON parse failed` 日志加 `ce=`；
  `douyin/observe.js` 原来在非 JSON 时**完全静默**，现在会打一行 `len=… ce=… url`。
- 背景（写进 §10.5）：Loon 脚本层只有 `$utils.ungzip`，br 没有魔数、官方复写文档对压缩
  一字未提，所以「br 解不了」是硬边界；真遇到 `ce=br` 的修法是只对该端点把
  `Accept-Encoding` **设为** `gzip`（不是删掉，删掉会让 183–191 KB 的 upsell 膨胀 5~10 倍）。
- **lint 新增 `check_encoding_guard()`**：6 个解析 body 的脚本必须同时有 `readBody()` 与
  `ceTag()`，且 `skip=not-json` / `skip=json-parse` / `non-JSON len=` / `JSON parse failed len=`
  四条分支都不许漏 `ceTag()`；`ceTag()` 必须把 gzip 当正常值，防止把正常响应也打上 `ce=`。
- **新增 `test_encoding_guard.js`（22 断言）**：六脚本 × br/gzip/无头三态、头名大小写、
  `gzip, br` 逗号列表、以及「正常 JSON 仍走完清理且不被诊断干扰」。
- 回归：48 套件 / 1442 断言全绿；lint 0 error。

### v2.8.0（2026-10-27）静态传输层常开：QUIC 回退 + h2

- **`[Rule]` 新增 8 条 `AND,((DOMAIN-SUFFIX,…),(PROTOCOL,QUIC)),REJECT`**：只针对 `[MITM]` 里的精确域，
  把 HTTP/3 逼回 TCP+TLS。这是所有脚本的前置条件——MITM 只处理 TCP，QUIC 流量脚本完全看不见。
  不做全局 `PROTOCOL,QUIC,REJECT`（会伤视频/通话）。
- **`[MITM]` 新增 `h2 = true`**（后经复核：官方 MitM 文档只列 `hostname`/`ca-p12`/`ca-passphrase`，
  没有 `h2`；HTTP/2 解密是官方产品页宣称的默认能力。保留该行属零成本冗余，不当能力点宣称）。
- **删除注释里的 `[Rule]` 严格模式**：静态全域 REJECT 会直接掐断激励广告，且已被 `blockAdDomains`
  + QUIC 回退覆盖，不再保留“手动取消注释”的分叉。
- **评估后放弃“请求免压缩”**：`request.header.del("Accept-Encoding")` 本身可行，但自家 HAR 显示
  `commerce/v2/upsell` 在 gzip 下已有 183–191 KB，去压缩会让单次传输膨胀 5~10 倍；为省一次
  `$utils.ungzip` 换这个代价是负收益。lint 反向锁死，防止后续又加回来。
- 这一层**没有开关**：关掉等于让上面所有脚本失效。回滚方式 = 删对应行。
- 状态看板新增「静态层：QUIC 回退 8 域 · h2（常开）」，条数由 `families.json` 提供、lint 对账插件真实规则数。
- lint 新增三组守卫：静态层完整性（QUIC 集合 / 全局 QUIC 禁令 / 免压缩反向锁 / h2）、
  跨层短路矩阵（`[Rule]` 整域拒绝、`[Rewrite]` 终止型复写 vs 脚本，用真实 URL 样本交叉验证）、
  `SWITCH_LABELS` 与 `[Argument]` 双向一致。
- 回归：46 套件 / 1398 断言全绿；lint 0 error。

### v2.7.1（2026-10-27）状态看板加入 Loon 环境诊断

- `status.js` 在结果页新增「运行环境」行：`$loon`（设备/系统/Loon 版本）、`$script.name` 与 `startTime`、`$environment.params.nodeInfo`（兼容文档里的 `$envirnoment` 拼写）、`$config.getConfig()` 的 `running_model`（直连/分流/全局代理）。
- 新增「Loon 能力」行：检测 `$utils.ungzip` 是否存在，988+ 显示 ✅，983–987 显示 ❌ 并标注门槛，避免把“版本旧”误判成“脚本失效”。
- 所有全局对象都走 `typeof` 守卫：旧 build、generic 非节点场景或测试环境缺失时整行省略，不影响打卡/统计/开关摘要，也不新增任何网络请求。
- 排障收益：一眼区分“插件没生效”是 Loon 版本旧、运行模式不对，还是脚本根本没被执行。
- 文档补充 gzip 门槛：`$utils.ungzip` 自 Loon 3.5.1(988) 提供；983–987 可安装，但 gzip 响应端点只记录状态、不清理。
- 回归：`test_status.js` 31 → 40 条（含完整环境、`$envirnoment` 拼写、无全局对象，以及 ungzip 可用/不可用）；全量 46 套件 / 1398 断言。

### v2.7.0（2026-10-27）修复同 URL 响应脚本遮蔽（首条命中）

- Loon 对同一响应只执行配置顺序里第一条条件为真的 Response Script。旧绑定让实际行为与开关不一致：
  - `settingsClean + hideDouyinEntry` 同开时，第二条被第一条遮蔽 → 隐藏入口失效。现在两条绑定传同一组三参数，settings 脚本一次处理两件事。
  - `hideDouyinTab` 原先没有独立绑定，只有开 `cleanAds` 才会顺带生效。新增独立绑定（排在清理之后、只读日志之前），`sanitize.js` 补 `cleanAds=false` 时只做 `douyinOnly` 的分支。
  - `dailyReminder` 的独立打卡绑定会被 `cleanAds`/`debugLog`/`hideDouyinTab` 胜出的脚本遮蔽，导致提醒误报。现在 `sanitize` 与 `reward-observe` 在命中 `task/page` 时内置写入 `soda-welfare-seen`；独立 `welfare-stamp` 只作全关兜底，并覆盖 `beta-luna` 与 `api.qishui` 两个域名。
- 状态看板新增遮蔽提示：`cleanAds+debugLog`、`hideDouyinTab+debugLog`。
- lint 新增绑定矩阵：用真实 URL 样本覆盖每条 request/response 绑定；同 URL 多绑定只允许“同脚本同参数”或显式白名单组合，新增遮蔽直接失败。
- 回归：新增 `test_welfare_stamp.js` 10 条；`test_unified_args` 27 条、`test_soda_douyin_entry` 17 条、`test_status` 31 条；全量 46 套件 / 1376 断言。

### v2.6.9（2026-10-27）状态自检升级为开关看板

- Generic 按钮现在透传全部开关（`rewardSafe` / `cleanAds` / `killRewardAds` / `blockAdDomains` / `blockSplashAd` / `settingsClean` / `hideDouyin*` / `debugLog` / `dailyReminder` / `reminderCron` 等），结果页与通知新增「开关状态」摘要。
- 冲突组合给出显式提醒：`killRewardAds`、`rewardSafe+cleanAds`、`rewardSafe+settingsClean`、`rewardSafe+blockAdDomains`；`dailyReminder` 打开时带出 cron 时间。
- lint 锁定 generic 绑定必须透传全部声明开关，防止后续新增开关只进插件、不进状态页。
- 回归：`test_status.js` 29 条断言（含默认组合无冲突、冲突逐条命中、通知正文带警告）；全量 44 套件 / 1336 断言。

### v2.6.8（2026-10-27）splash-ad 共享源统一（行为不变）

- `splash-ad.js` 从 `src/soda/` 迁入 `src/common/` 单一来源，与 douyin 共用；家族差异只有日志前缀（`[soda-splash]` / `[douyin-splash]`）。
- douyin 0.7.6 新增 `blockSplashAd` 绑定后，两家族的开屏拦截逻辑、URL 家族判断与响应形态完全一致。
- lint 新增开屏绑定边界锁：每个家族必须有且仅有一条 splash 绑定，3 个开屏样本命中、`inspire` / `inspire_preload` / `marketing/done` 绝不命中。
- 回归：`test_splash_ad.js` 双家族 22 条断言（含 JSON Content-Type 与激励预拉取放行）；全量 44 套件 / 1302 断言。

### v2.6.7（2026-10-27）原生 reject_dict + select 参数 + 开屏全家族覆盖

- 上报 Rewrite 从 `reject(200)` 换成 Loon Rewrite v2 原生 `reject_dict(200)`：开屏品牌上报与 DSP 展示上报现在返回 JSON `{}` + `application/json`，不再是无 Content-Type 的空 Body；对 fire-and-forget 上报更友好，仍然零出网。
- 新增 `[Argument]` `statusNotify = select,"notification","silent"`：Generic 状态自检按钮可选弹通知（带 `openUrl` 一键跳 App）或静默模式；`status.js` 同时兼容对象/字符串参数与缺省值。
- 开屏请求脚本绑定补齐 `/api/ad/vN/splash/` 与 `/api/ad/vN/ack/splash/`（此前只匹配 `/api/ad/(v1/)?splash/`），与 `splash-ad.js` 内部家族判断和 IPA 取证一致；激励广告与发奖回调仍不在匹配范围。
- lint 锁定：上报 Rewrite 必须使用 `reject_dict(200)`、`statusNotify` select 候选值、generic 按钮必须透传 `statusNotify`，并新增 `v2/ack/splash` 命中样本。

### v2.6.6（2026-10-27）upsell v2 弹窗精确清理

- `commerce/v2/upsell` 的 `upsell_map` 实装：真实 93 弹窗样本中删除 18 个广告/商城弹窗（`*_ads_*`、`reward_ad_cold_launch_popup`、`browse_mall_popup_acc_amount` 等），奖励/发奖/兜底弹窗全部保留。
- 同步清理三处调度引用：`freq_ctrl_cfg.freq_ctrl_map` 只删与已删弹窗同名的 3 项（共享 `background_voice_prompt` 与非弹窗 `widget_ad` 保留）；`sort_control_unique_names` 14→6；`cold_launch_timing.upsell_item_unique_names` 23→20，含只登记无实体的 `cold_launch_popup_ads_text`。
- `fastReject` 新增 `upsell_map` 标记，只带该字段的响应也能进入 JSON 处理；`variables` / `libra_params_map` / `status_code` 原样保留。
- 说明：`sceneUpsellsMap → candidates → fixedEntrance.coinWidgetData` 属于奖励入口，不作为广告实体删除。

### v2.6.5（2026-10-27）task/page 预拉取精确收紧

- `task/page` 页面级广告开关收紧：`config.migrate_first_ad` 置 false。
- `config.ad_api_preload.task_ids` 不再原样保留：只留“仍在页面里的任务”引用的 id（`task.id` / `ad_snap.task_id` / `base_ad_diversion.id`），被摘掉的广告任务与页面快照里不存在的 id 丢弃；一条不剩时同步关闭 `preload`。保留任务（签到/翻卡/红包雨/开宝箱等）的广告预拉取不受影响。
- 真实样本回归：9 个预拉取 id 收紧为 4 个（保留任务的 600607/600585/600625/600662），`music_incentive_ad` 的 600572 与 4 个已不存在 id 被清掉。

### v2.6.4（2026-10-27）广告源/retrieve 补齐 + 大响应预检

- `luna/ads/retrieve` 纳入 `cleanAds`：补齐 `ad_launch` / `ad_launch_list` / `ads_blocks` / `ads_info` 及广告位配置字段，不再只处理 `ads/config` 与 `ads/dsp/retrieve`。
- `sanitize` 的 `fastReject` 改为从每条规则的 kill/falsy/prune 键自动生成（兼容 camelCase/snake_case），修复手写正则漏键导致 upsell 等响应被提前放行的问题；新增规则不会再漏同步。
- 无广告标记的大响应直接返回 `X-Soda-Plugin: soda-sanitize;noop=no-marker`，避免无谓 `JSON.parse`。

### v2.6.3（2026-10-26）传感器误触 / 商业推广 / 上报阻断

- 开屏与广告位清理补 `shake_info` / `twist_info` / `motion_info` / `interaction_info` / `splash_cache`，覆盖摇一摇、扭转、前倾等传感器误触广告。
- 信息流广告条目识别扩展 `is_promoted` / `is_sponsored` / `is_commercial` 与 `promoted` / `sponsored`。
- 新增 `luna/ads/report/dsp/show` 请求阻断（`reject(200)`，`cleanAds` 控制），减少已清理广告的无用上报。
- 新增 `status.js` Generic 状态脚本与通知 attach openUrl；设置层同步关闭摇一摇/扭一扭传感器、开屏预加载与缓存开关。

### v2.6.2（2026-10-26）共享脚本单一来源整合（行为不变）

- **同功能不分散**：`block-domains.js` / `daily-reminder.js` / `welfare-stamp.js`
  这三个脚本此前在 `src/soda/` 与 `src/douyin/` 各存一份逐字复制（只差日志前缀、
  存储键前缀、通知文案和 `rewardSafe` 默认值）。现在统一为单一来源
  `src/common/*.js` + 家族参数 `src/common/families.json`，`tools/build.js`
  按家族展开到 `src/{soda,douyin}/`（生成物，勿手改）再压缩——
  源码一处改动，两个家族同步生效。
- **编译产物逐字节等价**：生成后 `plugins/*/scripts/` 里 6 个对应 `.min.js`
  与重构前完全一致（`git diff` 零差异），没有行为变化；`blockAdDomains` 等
  开关语义不变（soda 的保奖励兜底默认开，douyin 因没有保奖励概念默认关，
  该差异已写进 families.json 并由测试断言锁定）。
- **名单四处一致性锁**：lint 新增两项守卫——① 按 families.json 重新展开
  共享脚本并与 `src/<family>/` 生成物逐字节比对；② 把 `BLOCKED_HOSTS`
  与插件的 `[Script]` 正则、注释 `[Rule]`、`[MITM]` 四处名单强校验。
  手改生成物会报 stale，直接生效。
- **分层说明写入插件头注释**：5 个被拦域名中 3 个（`ad.zijieapi.com` /
  `lianmengapi.snssdk.com` / `ads5-normal-hl.zijieapi.com`）同时被
  `ads.plugin` 的 `[Host]` DNS 层拦截；`zlink/praisewindow.ugsdk.cn` 是
  App 内运营端点，只由本开关覆盖。

### v2.6.1（2026-10-23）task/page 结构化判别 + 真样本回归

- **新通道**：`luna/treasure/task/page/v[0-9]`（beta-luna.douyin.com 与 api.qishui.com 双绑定，
  `enable=${cleanAds}` 默认惰性）接入 sanitize——cleanAds 此前对该端点 `skip=no-rule`，
  v2 sections 形态的广告任务完全无人处理。
- **结构化判别**（修复整条 stringify 匹配的误删）：v1 时代 `p.match.test(safeString(item))`
  会把带 `extra.ad_task_id` / `ad_snap` 的**正常任务**（签到 / 翻卡）误判成广告条目删掉。
  对 `tasks` / `taskInfos` 容器改用三分量判别：
  1) `item.key` ∈ 显式广告任务键名单（`music_incentive_ad`）；
  2) `item.type` 命中 incentive_ad 家族（`polaris_incentive_ad_v3` 等）；
  3) 任务标题（`view.title.plain_text`）命中广告词。
  领奖/发奖字段零接触；`luna_rewards_ads`（攒时长）在保留名单。
- **证据**：HAR 393 真机样本（`tests/fixtures/soda_task_page_v2.json`，tokens 已脱敏）——
  8 个金币任务中只摘 `music_incentive_ad`，资产金额 256/55/3 与签到 7 档奖励原样保留；
  新套件 `test_soda_task_page_v2.js` 27 断言（含反误删哨兵、push_permission 存活
  哨兵与三通道分发验证）。
- **观察面补绑**：`reward-observe` 此前只绑 api.qishui.com 的 20 个端点，真机页面来自
  beta-luna.douyin.com 的 task/page 从未被观测——补 RULES `task-page` 条目 +
  beta-luna / api.qishui 双绑定（`enable=${debugLog}`），并新增 [15]/[16] 断言：
  393 样本出 ≥10 任务摘要；`logTaskTitles=开` 时签到/看广告/攒时长标题随日志带出
  （C 步采集链路就此就绪）。
- **内部整理（行为不变）**：`settings.js` / `sanitize.js` 各删除一份重复的
  pargs/pflag 工具块声明（复制两份，Terser 也会白编译）；`reward-observe` 观测 tag
  端点计数 20→22。
- **观察脚本健壮性**：`douyin/observe.js` 主流程原直读 `$response.body`（Loon 交接
  gzip 原串时静默失效），改走 `readBody`；treasure/observe 页面正则放宽
  `page/v2` → `page/v[0-9]+`。
- 版本联动：lint 期望 scripts 35→39、`cleanAds` enable 计数 7→9、`debugLog` 20→22。

### v2.6.0（2026-10-22）每日提醒打卡 + 开屏家族兜底

- 新增 `dailyReminder`（默认关）与 `reminderCron`（默认 `30 20 * * *`）：当天没打开福利页
  → 到点发 Loon 通知；已打卡 → 免打扰。新版 Script 语法：
  `cron <表达式> then script(...) with enable=${dailyReminder}`（Loon 3.5.1(983)+）。
- 新增 `scripts/welfare-stamp.min.js`：命中 `/luna/treasure/task/page` 即落当天福利卡，
  **不读不改响应体**；打卡域 `beta-luna.douyin.com`（`[MITM]` 新增）。
- 广告统计键改为插件隔离名 `soda-ad-stats`（Loon 的 `$persistentStore` 全局共享，避免与他米互踩）。
- 开屏端点家族升级（IPA 全量端点核对后）：`api/ad/splash/**` 与
  `api/ad/v[0-9]/(ack/)?splash/**`（v2+ 路径漂移兜底）；激励 `api/ad/v1/inspire`、
  `api/incentive/marketing/done` 保持**不可拦**。

### v2.5.0（2026-10-21）

- `key + id` 且带 `view/stats/rewards` 的新版任务对象识别（旧版观测器认不出无 `task_key` 的）。

---

## 12. 免责声明

仅供个人设备上的网络流量管理与广告过滤研究。请遵守当地法律与 App 用户协议；不要用于批量刷取奖励、绕过付费或商业分发。使用风险自负。
