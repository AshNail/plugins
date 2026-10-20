# 汽水音乐 · Loon 净化插件（SodaClean）

> 所属：Loon 插件仓库 · 插件族 `soda`（[仓库总览](../../README.md)）
> 部署目录：`plugins/soda/`；源码目录：`src/soda/`
> 目标：汽水音乐 iOS 20.5.0（`com.luna.music`）
> 类型：Loon 插件（域名拦截 + 字段级响应改写 + 诊断脚本）
> 取证：Ghidra 全量分析 + ARM64 `ADRP+ADD` 字符串引用扫描（详见配套逆向报告）

**v1.5.2 本次变更**：部署脚本改为 terser 实际压缩版 `plugins/soda/scripts/*.min.js`（去空白/注释、混淆局部与顶层变量名），可读源码保留在 `src/soda/`，由 `tools/build.js` 生成。插件行为与 v1.5.1 一致。

**v1.5.1 新增**：补充 `search-block` / `search-categories` / `card` / `growth/activity_entrance` / `advert/fallback/done/info` 五个端点；信息流 `fastReject` 识别 `banner_list`，修复“只有 banner 广告时脚本不解析”的漏洞；福利任务正则加入 `commerce_ad` / `ad_snap`；设置层新增 `splash_ad_config` / `reward_ad_config` / `adn_group_config` / `commerce_*_ad_config` / DSP / mannor 等广告专用键，并可选接入 `is.snssdk.com`（BDADSDK 设置）与 `i.snssdk.com`（Unisus 设置）。主插件 v1.5.2，设置插件 v0.1.2。

**保奖励模式（独立插件 v0.2.3）**：`SodaClean-Reward.plugin` 只清开屏品牌广告，**保留**激励广告、奖励任务、发奖链路，并**刻意不碰 upsell**（可能承载 `UpsellStyleRewardAdsDefault` / `reward_btn_text` 等激励入口）。适合“完整看完广告后正常领奖”；**不拦任何域名**（包括 App Store 评分弹窗 `praisewindow.ugsdk.cn`），信息流/DSP/商业弹窗可能仍会出现。与主插件、设置插件二选一，不能同时启用。

**激励链路观测（只读 v0.2.2）**：`SodaClean-Reward-Debug.plugin` 只写 `[soda-reward]` 日志，不修改响应；观察 20 个激励/任务/入口端点，用来判断广告源、`reward_ads` 任务、发奖接口、`fallback/flip_card/guide/browse_mall` 动作，以及 `upsell` 的奖励入口变量到底卡在哪一层。可与保奖励插件同时启用，排障后停用。

**v1.5 已包含**：信息流 `is_advertisement` / `is_ad_item` / `ad_flag` / `adItem` 与 `card.is_ad` 嵌套判定；信息流端点扩展 `playlist/search` / `discover/mix`；福利任务/ banner 增加 `ad_reward` 变体；福利页 `banner_list` 广告项裁剪；新增**设置层实验插件** `SodaClean-Settings.plugin`，通过 `conf.qishui.com/service/settings/v3/` 清空 `commerce_ad_config` / `feed_reward_ad_config` / `reward_ad_fallback_config` / `splash_ad_early_load_config` 等 TTKitchen 配置。

**v1.4 已包含**：开屏 `ad_launch_list` / `ad_launch`、信息流 `ads_blocks` / `ads_info` / `is_ad`、广告位配置 `ad_unit_configs` / `splash_config` / `feed_ads_config` / `reward_config`、DSP 上报 `reject-200`、金币挂件 `widgetAdReward` 广告态。字段地址与描述符见《汽水音乐_20.5.0_开屏与信息流广告_字段取证与净化方案.md》。

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
| `luna/commerce/v2/upsell` | `sceneUpsellsMap` / `upellsVariables` / `sortControlUniqueNames` / `popupConfig` 等（Swift 属性名；线上键大小写待真实响应确认） | 奖励入口 / 商业化弹窗；金币挂件配置在 `candidates[].fixed_entrance.coin_widget_data` |
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
> `conf.qishui.com` 不在主插件的 `[MITM]` 里。要用设置层，需要装独立的 `SodaClean-Settings.plugin`（见 3.7）。该插件还预留了 `is.snssdk.com`（BDADSDK.SettingsManager）与 `i.snssdk.com`（Unisus）两个可选设置端点，默认注释。

广告/归因域名：

| 域名 | 用途 | 证据 |
|---|---|---|
| `ad.zijieapi.com` | 激励视频/Pangle 广告请求、激励完成上报、负反馈 | `https://ad.zijieapi.com/api/ad/v1`、`/api/incentive/marketing/done` |
| `lianmengapi.snssdk.com` | 穿山甲联盟 API | 二进制字符串 |
| `ads5-normal-hl.zijieapi.com` | 广告素材/投放 CDN | `ads5-normal-hl.zijieapi.com` 字符串 |
| `zlink.ugsdk.cn` | 归因/转化回传 | `https://zlink.ugsdk.cn/ad/impression/asa/token` |
| `praisewindow.ugsdk.cn` | App Store 评分弹窗（非广告） | `AppStoreStarAdapter`、`/zebra/praise/click`、`为汽水音乐评分` |

> 设置层还有两个**不默认拦截**的端点：`is.snssdk.com/service/settings/v3/`（`BDADSDK.SettingsManager`，广告 SDK 设置）和 `i.snssdk.com/service/settings/v3/`（`Unisus` 通用设置）。它们可能被证书固定，默认只在实验插件里以注释形式提供。

---

## 2. 为什么默认不用 `reject-dict`

| 方案 | 返回 | 风险 |
|---|---|---|
| `reject-dict` | `{}` | 丢失 `status_code`，App 解码失败 → 重试 / 走默认值 / 弹错误 |
| 本插件 | 原包络 + 广告容器清空 | App 认为「本次没有广告」，流程正常结束 |

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
| `luna/commerce/{upsells,v2/upsell,v2/upsell_sort_decision}` | v1：`card` / `upsells` / `upsell_unique_name` / `items` / `popups` / `list → []`；v2 目前尚未覆盖 `sceneUpsellsMap` → `candidates` → `fixedEntrance.coinWidgetData`（已知缺口，见报告 14.11） |
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
| DSP 上报 | `luna/ads/report/dsp/show` | Rewrite `reject-200`，不走上游 |

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

**可选 SDK 设置端点**：`is.snssdk.com/service/settings/v3/` 的调用方是 `BDADSDK.SettingsManager`（Pangle 广告 SDK 设置），`i.snssdk.com/service/settings/v3/` 的调用方是 `Unisus` 通用设置。两者已在 `SodaClean-Settings.plugin` 的 `[Script]` / `[MITM]` 里以注释形式给出；确认 `conf.qishui.com` 不命中或想更上游关闭广告时再启用。它们比 `conf.qishui.com` 更容易触发证书固定，默认不碰。

> ⚠️ 这是**实验插件**，单独安装 `SodaClean-Settings.plugin`。`conf.qishui.com` 若证书固定，MITM 会失败；停用插件即可回滚，主插件不受影响。

---

## 4. 分层设计

| 层 | 内容 | 默认 | MITM |
|---|---|---|---|
| **L1** | `ad.zijieapi.com`、`lianmengapi.snssdk.com`、`ads5-normal-hl.zijieapi.com`、`zlink.ugsdk.cn`、`praisewindow.ugsdk.cn`（App Store 评分）→ `REJECT` | ✅ | 否 |
| **L2** | 字段级裁剪（见 3.2） | ✅ 部分 | 是 |
| **L2.5** | 设置层：`conf.qishui.com/service/settings/v3/`（独立实验插件）；可选 `is.snssdk.com` / `i.snssdk.com` | ⬜ | 是 |
| **L3** | 埋点 `mon/log/applog.zijieapi.com`、`log.qishui.com`、风控 `timon` | ⬜ | 否 |

L3 默认关闭：拦 `timon` / `gurd` 可能影响登录与风控校验。

---

## 5. Loon 规范落地：Rule / Rewrite / Script / MITM

插件按 Loon 的四段式组织：

| 段 | 作用 | 需要 MITM |
|---|---|---|
| `[Rule]` | 域名级拦截（广告 SDK、归因回传） | ❌ |
| `[Rewrite]` | URL 级重写（纯上报 `reject-200`；轻量模式 `reject-dict`） | ✅ |
| `[Script]` | 字段级响应改写（保留包络） | ✅ |
| `[MITM]` | 声明 `api.qishui.com`；实验插件声明 `conf.qishui.com`，可选 `is.snssdk.com` / `i.snssdk.com` | ✅ |

> Loon 的 HTTPS Rewrite 必须先经 MITM 解密，才能看到路径并匹配。所以 `[Rewrite]` 不是"无 MITM"方案；真正的无 MITM 方案只有 `[Rule]` 域名拦截。

### 5.1 五种模式（A/B/C/D/E）

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

- 不拦 `ad.zijieapi.com` / `lianmengapi.snssdk.com` / `ads5-normal-hl.zijieapi.com`，激励广告能加载；
- 不跑 `incentive/config` / `incentive/retrieve` / `ads/config` / `ads/retrieve` 脚本，广告源、广告位与 `reward_config` 保持原样；
- 不跑 `treasure/task/view` / `treasure/entrance` / `growth/activity_entrance` 脚本，奖励任务与入口保留；
- 不碰 `incentive/done` / `ads/reward/receive|settle` / `commerce/validate_reward`；
- **不跑 upsell 脚本**：二进制里有 `UpsellStyleRewardAdsDefault` / `UpsellStyleRewardAdsExposureReward` / `reward_btn_text` / `reward_ads_cold_start_style`，upsell 可能承载“看广告得奖励”入口，清掉会减少奖励机会；
- 只清开屏品牌广告；
- **`[Rule]` 为空**：连 `praisewindow.ugsdk.cn` 也不拦。它是 App Store 评分弹窗（`AppStoreStarAdapter` / `/zebra/praise/click`），不是激励广告域名；为不误伤“去评分/引导”类非广告任务，保奖励模式不拦任何域名。

代价：信息流、DSP 与商业弹窗可能仍会出现。**不要与主插件或设置插件同时启用**；主插件的 `[Rule]` 与脚本会再次把激励链路清掉。如果 MITM 被证书固定拦截（App 断网/广告 SDK 初始化失败），停用 `[Rewrite]`、`[Script]`、`[MITM]` 三段即可（`[Rule]` 本来就是空的）；奖励按 App 原始流程走。

> 合规边界：保奖励模式只保证“广告正常播放后，奖励链路不被插件破坏”。它不跳过广告、不伪造回调、不提供屏蔽广告后领奖。

### 5.2 为什么 `[Rewrite]` 只放少量纯上报端点

`reject-200` 适合"响应无人解析"的 fire-and-forget 上报，例如：

```
luna/advert/splash/brand/report
luna/ads/report/dsp/show
```

配置类端点如果直接 `reject-dict`，会丢掉 `status_code`，App 可能重试或走默认值——所以交给 `[Script]` 保留包络。

### 5.3 语法说明

本插件使用 Loon 旧版 Rewrite 语法，全版本兼容：

```
^https?:\/\/api\.qishui\.com\/luna\/advert\/splash\/brand\/report reject-200
```

注意不是 Surge 的 `url reject`。Loon 3.5.1+ 也可以写成新语法：

```
request if ${url} ~= /^https:\/\/api\.qishui\.com\/luna\/advert\/splash\/brand\/report/ then reject(200)
```

### 5.4 可选：请求侧减负

`src/soda/request.js` 只做一件事：把 `incentive/config` 与 `ads/config` 请求里的 `preload` 关掉，避免 App 主动预加载广告素材。

在 `[Script]` 里取消这一行注释即可：

```
http-request ^https?:\/\/api\.qishui\.com\/luna\/(?:advert\/incentive\/config|ads\/config) script-path=scripts/request.min.js, requires-body=true, timeout=10
```

明确只改 `preload`，不碰 `advert_duration` / `advert_sources` / 发奖字段。

### 5.5 激励链路观测（只读）

`SodaClean-Reward-Debug.plugin` 不拦域名、不改写、不返回 body，只把关键结构写进 Loon 日志，前缀 `[soda-reward]`。

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

- 可与 `SodaClean-Reward.plugin` 同时启用；
- **不要**与 `SodaClean.plugin` 同时启用：主插件会先清掉激励字段，日志看到的是“已清空”的假象；
- **不要**与 `SodaClean-Settings.plugin` 同时启用：设置层会清奖励配置；
- 排障完成后停用，避免长期打印日志。

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

部署目录是 `plugins/soda/`：四个 `.plugin` + `scripts/*.min.js`。推送前先运行 `npm run build` 生成压缩脚本；`src/`、`tests/` 可以保留在仓库里，不需要单独上传。

1. 把 `plugins/soda/` 和仓库根目录的 `.nojekyll` 推到 GitHub；
2. GitHub → Settings → Pages → Source 选 `Deploy from a branch`，Branch 选 `main`，Folder 选 `/ (root)`；
3. 站点根为 `https://ashnail.github.io/plugins`，插件位于 `.../plugins/soda/`；
4. 主插件：

```
loon://import?plugin=https%3A%2F%2Fashnail.github.io%2Fplugins%2Fplugins%2Fsoda%2FSodaClean.plugin
```

5. 实验插件（可选，需单独 MITM `conf.qishui.com`）：

```
loon://import?plugin=https%3A%2F%2Fashnail.github.io%2Fplugins%2Fplugins%2Fsoda%2FSodaClean-Settings.plugin
```

6. 保奖励插件（想正常拿激励奖励时用，**不要同时启用主插件/设置插件**）：

```
loon://import?plugin=https%3A%2F%2Fashnail.github.io%2Fplugins%2Fplugins%2Fsoda%2FSodaClean-Reward.plugin
```

7. 激励链路观测插件（只读，排障时与保奖励插件一起装）：

```
loon://import?plugin=https%3A%2F%2Fashnail.github.io%2Fplugins%2Fplugins%2Fsoda%2FSodaClean-Reward-Debug.plugin
```

8. Loon → 设置 → MITM → 生成证书 → 安装并信任；
9. 主插件/保奖励插件 `[MITM]` 已声明 `api.qishui.com`；实验插件声明 `conf.qishui.com`。要试广告 SDK 设置层，再取消实验插件里 `is.snssdk.com` / `i.snssdk.com` 两行注释，并同步 `[MITM]`。

> 插件里的 `script-path=scripts/...` 是相对路径，所以 `.plugin` 和 `scripts/` 必须保持同级；不要只发单个 `.plugin` 文件。GitHub Pages 根地址没有 `index.html`，会 404，直接访问插件文件即可。

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
| 保奖励模式是否生效 | 只装 `SodaClean-Reward.plugin`；奖励任务应保留，开屏品牌广告应消失，信息流/DSP/商业弹窗可能仍在 |
| 奖励是否正常到账 | 完整看完激励视频，确认金币/畅听/翻牌等奖励到账；不要跳过广告或伪造回调 |
| 激励链路是否下发 | 装 `SodaClean-Reward-Debug.plugin`，日志搜 `[soda-reward]`；看 `counts.sources` / `counts.adInfosMap` / `tasks` / `reward` 是否为空 |

本地回归：`npm run check`（build + lint + 源码/压缩版测试）。单独跑：`python3 tests/run-all.py`（10 套 / 276 条断言，源码与压缩版各一遍，共 552 条）；`python3 tests/lint-plugins.py` 检查 4 个插件。

建议顺序（主插件）：**L1 → incentive/config → splash → retrieve → upsell → treasure → 设置层实验**，每加一条观察一天。

保奖励模式不要按这个顺序加：**只开 splash 脚本 + 观测插件**；不要开 upsell / incentive / ads / treasure 脚本，否则会减少或切断激励入口。

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
| 金币挂件仍显示广告态 | 主插件 v1.5.2 的 `upsell` 规则未覆盖 v2 `sceneUpsellsMap` → `candidates` → `fixedEntrance.coinWidgetData`；待后续补定向裁剪 |
| 广告配置有本地缓存 | 首次启用后旧配置可能仍生效；清 App 缓存/重装，或等 `expires_at` 过期 |
| 设置层插件装上后 App 设置加载失败/断网 | `conf.qishui.com` 证书固定；停用 `SodaClean-Settings.plugin` 回滚 |
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
6. 设置层没命中时，先把 `SodaClean-Settings.plugin` 的诊断行取消注释，确认响应结构：
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
│       ├── SodaClean.plugin        # 主插件（API 字段级，去广告优先）
│       ├── SodaClean-Reward.plugin # 保奖励插件（激励链路优先）
│       ├── SodaClean-Reward-Debug.plugin # 只读观测（[soda-reward] 日志）
│       ├── SodaClean-Settings.plugin # 实验插件（TTKitchen 设置层）
│       └── scripts/                # 压缩后的部署脚本
│           ├── sanitize.min.js
│           ├── settings.min.js
│           ├── request.min.js
│           ├── reward-observe.min.js
│           └── diag.min.js
├── src/
│   └── soda/                       # 可读源码（构建输入）
│       ├── sanitize.js
│       ├── settings.js
│       ├── request.js
│       ├── reward-observe.js
│       └── diag.js
├── tools/
│   └── build.js                    # src -> plugins 压缩构建
├── tests/                          # 脚本层回归测试（10 套 / 276 条断言 × 2）
├── package.json
├── package-lock.json
├── .github/workflows/check.yml     # CI：build + lint + 测试
├── .nojekyll                       # GitHub Pages 原样提供 .plugin / scripts
└── .gitignore
```

> `.plugin` 里的脚本路径指向同级的 `scripts/*.min.js`；`src/` 只用于阅读和改代码，不参与 Loon 加载。

---

## 11. 免责声明

仅供个人设备上的网络流量管理与广告过滤研究。请遵守当地法律与 App 用户协议；不要用于批量刷取奖励、绕过付费或商业分发。使用风险自负。
