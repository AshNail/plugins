# 抖音 · douyin（Loon 聚合插件）

> 所属：Loon 插件仓库 · 插件族 `douyin`（[仓库总览](../../README.md)）
> 部署目录：`plugins/douyin/`；源码目录：`src/douyin/`
> 目标接口：抖音内嵌的音乐/福利模块 `beta-luna.douyin.com/luna/*`
> 取证：2026-10-20 三份真实 Loon HAR（`381_1792495728793.har`、`382_1792495842588.har`、`383_1792495850343.har`）

**架构**：一个 App 一个插件。抖音只部署 `plugins/douyin/douyin.plugin`，所有功能用 Loon `[Argument]` 开关控制。

**图标**：`#!icon` 用抖音官方 App 图标（App Store CDN，512×512）；
若要换成字节自家 CDN 的网页版 favicon（32×32，清晰度较低）：
`https://lf1-cdn-tos.bytegoofy.com/goofy/ies/douyin_web/public/favicon.png`。

| 开关 | 默认 | 作用 |
|---|---|---|
| `treasureMinimal` | 开 | 福利页只保留【攒时长 听歌不中断】 |
| `cleanFeedAds` | 关 | 清掉信息流/广告位广告容器（**不影响激励奖励**） |
| `killRewardAds` | 关 | 断掉激励广告素材与预拉取（= 广告完全不发，奖励也没了） |
| `cleanUpsell` | 关 | 删商业化弹窗、逛商城弹窗、汽水音乐节（演出）列表 |
| `blockAdDomains` | 关 | 广告/归因域名拦截（MITM + `http-request` 脚本） |
| `cleanActivity` | 关 | 把 polaris 活动配置里的汽水音乐节（演出）与抖音运营活动（选游戏/选作者/开学季/创作者抽奖）置为不展示 |
| `debugLog` | 关 | 只读日志，前缀 `[douyin-reward]`（含穿山甲广告配置、领奖回调、广告耗时实测） |

> v0.2.0 起原来的 `cleanAds` 拆成 `cleanFeedAds` / `killRewardAds`：
> 原实现会连 `incentive/config`（`preload=true` + `vids[]` 预拉取列表）和 `incentive/retrieve`（素材表）一起清掉，
> 而那正是“下一次广告秒开”的关键，清掉后每次广告都要现下载，反而更慢 —— 而【攒时长】本来就靠看广告结算。
> 所以现在默认两个开关都关：**要看广告、要奖励，就别开这两个**。

---

## 1. 福利页结构（`/luna/treasure/task/page/v2`）

响应外层固定是 `status_code` / `status_info`，业务数据在 `data`：

```text
data.sections[]                       页面分区
  key = asset_section                 我的资产（余额 / 提现）
  key = duration_task_section         攒时长 听歌不中断
      task_group.tasks[0].key = luna_rewards_ads
  key = gold_task_section             做任务 赚金币
      soda_music_sign_in        签到得金币
      luna_treasure_shop        逛街赚金币（= 福利页【商城】）
      music_incentive_ad        看广告赚金币
      luna_treasure_draw_duration 连续刷视频赚金币
      luna_incentive_push_permission 每天提醒我来赚金币
      luna_treasure_flip_card   翻卡赢金币
      luna_treasure_red_packet_rain 红包雨
  key = widget_task_section           开宝箱得金币（music_ug_treasure）
data.config.ad_api_preload.task_ids   需要预拉取广告的 task_id（9 个）
data.feedback_schema                  领奖反馈弹窗
data.namespace = luna_incentive
```

`treasureMinimal=true` 时：只保留 `duration_task_section`（只留 `luna_rewards_ads`），其余分区整体删除，并把 `config.ad_api_preload.task_ids` 清空（被删任务的广告不再预拉取）。

### 【攒时长 听歌不中断】本质就是看广告

按钮 schema：

```text
sslocal://luckydog/activity_task
  ?luckydog_task_type=luna_watch_ads_settle_vip
  &luckydog_global_task_id=20261020:656865033715820:1:30:1
  &luckydog_task_token=***
  &extra={"creator_id":"210036","ad_type":"ads_get_duration","from_page":"coin_task_list"}
```

`ad_type=ads_get_duration` + `luna_watch_ads_settle_vip` 说明：**看一次广告结算一段 VIP 时长**。所以：

- `cleanAds=true` 或 `blockAdDomains=true` → 这个模块拿不到时长；
- 想“又去广告又想攒时长”在链路层是矛盾的（除非广告服务端自己下发兜底时长，那是 App 的补偿逻辑，不是插件能造出来的）。

---

## 2. 【签到得金币】点不动：不是插件的问题

抓包链路：

```text
POST https://aweme.snssdk.com/aweme/ug/common/luckyapi/v1/common/sign_in/sign_in_done/
→ 200 {"err_no":210021,"err_tips":"设备异常，领取失败","data":null}
```

`sign_in_detail` 里写明要先听够时长才发奖：

```text
button_data.desc = "已听30秒  领{{sign_in_amount}}金币"
settings.treasure.sign_in.listen_duration_seconds = 30
```

两个独立原因：

1. **服务端设备风控**：请求参数里 `lucky_device_score=13.9329`（luckydog 设备分），设备地区是新加坡
   （`geo_region=sg`、`language=en-SG`、`tz_name=Asia/Singapore`）。抖音金币/签到是大陆玩法，
   设备分过低 + 非大陆环境 → `err_no 210021 设备异常`，服务端直接拒发，客户端表现为“点了没反应”。
2. **前置条件**：即使风控通过，也要先听满 30 秒才允许领取。

插件侧没有拦这个接口（`aweme.snssdk.com` 不在 `[MITM]`、也不在 `[Rule]`），所以和本插件无关。
可行的只有：换大陆网络环境 + 正常抖音账号 + 不要改包改设备指纹。

---

## 3. 广告时长在哪里，能不能改短

### 3.1 实测时间线（`381_1792495728793.har`，t=0 是 `incentive/config` 到达时刻）

```text
 0.0s  /luna/advert/incentive/config      736 B   广告源 + preload=true + vids[33] + advert_duration=30
 1.0s  /luna/advert/incentive/retrieve   4106 B   素材表（5 条 creative，launch_duration=30）
12.0s  /luna/treasure/task/listen_music/do_action          其它任务
34.0s  /luna/treasure/task/flip_card/do_action             翻卡
42.0s  /luna/treasure/task/box/do_action                   开宝箱
49.0s  p6-luna.douyinpic.com/...e78a3d8e....mp4  206      ← 广告素材真正开始下载（点了“去完成”之后）
74.0s  p6-luna.douyinpic.com/...{5 个 mp4}  206            ← 预拉取批次启动（为下一次广告预热）
76.0s  /luna/advert/incentive/done          191 B         ← 发奖成功
```

读出来的三件事：

1. **广告本体确实是 30 秒**：素材下载 49s → 发奖 76s，正好 30s（= `launch_duration`）。
2. **第一次点广告前有一段下载空转**（49s 才开始拉 mp4），预拉取批次要到 74s 才起来。
   `incentive/config` 里的 `preload=true` + `vids[]` 就是给这件事用的 —— **别清它**（v0.2.0 已把开关拆开）。
3. **只有看广告这一段是硬成本**，其余等待（翻卡、开宝箱、红包雨、签到、商城、演出）都已从福利页移除。

### 3.2 有效时长是**广告平台签发**的，客户端改不了（2026-10-20 20:25:47 实证）

抖音侧的激励广告走的是**穿山甲（CSJ）广告 SDK**：

```text
GET  ad.zijieapi.com/api/ad/v1/inspire/            32 KB   广告平台下发的广告配置
GET  ad.zijieapi.com/api/ad/v1/inspire_preload/    74 KB   预拉取
GET  *.qrstuvwxyzab.com/.../video/...             206     广告视频本体（range 请求）
POST ad.zijieapi.com/api/incentive/marketing/done         领奖回调（带 time_token）
```

领奖时提交的 `post_done_extra` 里带一个 **JWT 形态的 time_token**，解开是：

```json
{"iat":1792499149,"nbf":1792499178,
 "payload_b64":"eyJlZmZlY3RpdmVfaW5zcGlyZV90aW1lIjozMH0"}
                └─ base64 → {"effective_inspire_time":30}
```

也就是说：**“有效观看 30 秒”这个事实是广告平台自己在服务端记录并签进 token 的**
（iat/nbf 是签发与生效时间），客户端的 `launch_duration` 只是播放器的展示时长。
改它既骗不过平台，也换不来奖励。

> 顺带一个重要发现：同一份抓包里，抖音这边的领奖被广告平台**直接拒了**：
> `POST /api/incentive/marketing/done → {"code":403,"msg":"设备异常，领取失败"}`
> 和【签到得金币】的 `err_no 210021 设备异常` 是同一套设备风控。
> 而**汽水**那边同一时刻是成功的：
> `api.qishui.com/luna/advert/incentive/done → {"reward_details":{"0":{"amount":1800,"claim_status":1}},"status_code":0}`
> 也就是说抖音侧的奖励这次根本没发出去，和广告时长无关。

### 3.3 改短时长的技术结论

实测到的时长字段（都在客户端下发，**不等于发奖条件**）：

| 位置 | 字段 | 实测值 |
|---|---|---|
| `/luna/advert/incentive/config` | `feed_advert_config.advert_duration` | 30 |
| `/luna/advert/incentive/config` | `preload` / `vids[]` | true / 33 个预拉取 id |
| `/luna/advert/incentive/retrieve` | `ad_infos_map.default.ad_infos[].launch_duration` | 30 |
| 同上 | `.interaction_info` | `{"interaction_type":"4","interact_behavior":2}` |
| 同上 | `.component.countdown` | `{}`（倒计时组件可配） |
| `/luna/advert/incentive/config` | `advert_sources[].freq_ctrl` | `day_max_cnt 9999 / min_interval_sec 0` |
| `conf.qishui.com` 设置 | `treasure.sign_in.listen_duration_seconds` | 30（签到听歌时长） |
| `conf.qishui.com` 设置 | `commerce_ad_config...reward_ad_config.ad_load_timeout` | 8（秒） |

发奖链路（服务端校验）：

```text
广告播放完 → /luna/advert/fallback/done/info
              post_done_extra = {req_id, time_token, nonce, marketing_coin_data}
          → /luna/advert/incentive/done
              reward_details = {"0": {reward_type:0, amount:1800, claim_status:1}}
```

结论：

- 客户端时长（`launch_duration` / `advert_duration`）可以改，但**改了也拿不到奖励**：
  服务端用 `time_token` / `nonce` / `req_id` 这类一次性凭证 + `valid_duration` 校验真实观看时长；
  真机验证方法：开 `debugLog`，对比 `incentive/retrieve` 里的 `launch_duration` 与 `incentive/done` 的到达时间，
  以及 `fallback/done/info` 的 `post_done_extra` 是否带出 `time_token`；
- 更重要的是，**少看广告再领奖属于广告欺诈**（ad fraud），本仓库不做，也不建议做：
  它违反 App 协议与广告主投放约定，账号会被风控（你这次的 `210021 设备异常` 就是风控长相）。

> 换算一下性价比：攒时长模块是 **1 次广告 = 1 天畅听**（`assets[].amount=1, amount_type=day`，
> 副标题“再看3次提前解锁下一天”），30 秒换一天不中断，这已经是最划算的路径。
> 签到则是**纯听歌 30 秒**、不看广告（但目前被服务端设备风控挡着，见 §2）。

合规可行的只有两种：要么**广告完全不看**（本插件 `cleanAds` / `blockAdDomains` 走的路，此时也不能领该广告对应的奖励），
要么**完整看完**再领。本插件的原则是：前者可以，后者不造假。

---

## 4. 商城 / 演出去哪了

| 页面元素 | 数据来源 | 处理方式 |
|---|---|---|
| 福利页【商城】（逛街赚金币） | `gold_task_section` / `luna_treasure_shop` | `treasureMinimal` 直接删掉该分区 |
| 商城弹窗（逛商城赚金币） | `/luna/commerce/v2/upsell` → `upsell_map.browse_mall_popup_acc_amount` | `cleanUpsell` 删除该弹窗 |
| 【演出】汽水音乐节 | `/luna/growth/music_festival/performance_details` → `detail_list[]`（`title=汽水音乐节`、`performance_stop_name=常州站`） | `cleanUpsell` 清空 `detail_list` |
| 其它商业化弹窗（开屏/预览/冷启动/回放…） | `upsell_map` 里 `*ads*` / `*_ad` / `ad_*` 命名的 unique_name | `cleanUpsell` 一并删除，并同步清理 `sort_control_unique_names` 与 `cold_launch_timing.upsell_item_unique_names` |

注意：演出（音乐节）并不在福利页 `sections` 里，所以只开 `treasureMinimal` 不会自动去掉它，要开 `cleanUpsell`。

---

## 5. 安装

```text
loon://import?plugin=https%3A%2F%2Fashnail.github.io%2Fplugins%2Fplugins%2Fdouyin%2Fdouyin.plugin
```

Pages 未开启时：

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/douyin/douyin.plugin
```

步骤：

1. Loon → 插件 → URL 导入上面的地址；
2. Loon → 设置 → MITM → 生成证书 → 安装并信任；
3. 插件默认只开 `treasureMinimal`（福利页精简），其余按需打开；
4. 如果抖音提示网络异常，说明 `beta-luna.douyin.com` 有证书固定，停用 `[Script]` / `[MITM]` 即可回滚。

---

## 6. 验证

| 检查项 | 方法 |
|---|---|
| 福利页是否只剩攒时长 | 打开福利页，只应看到【攒时长 听歌不中断】；我的资产/签到/商城/看广告/翻卡/红包雨/开宝箱都消失 |
| 攒时长是否仍可点 | 按钮应能进入看广告结算流程（`ad_type=ads_get_duration`） |
| 广告是否还在 | `killRewardAds` 打开后，日志搜 `[douyin-clean]`，`advert_sources` / `ad_infos_map` 应为空；`cleanFeedAds` 只影响信息流广告 |
| 弹窗/演出是否消失 | `cleanUpsell` 打开后，`upsell_map` 里不应再有 `*ads*` 与 `browse_mall_popup_acc_amount`；音乐节列表为空 |
| 链路取证 | `debugLog` 打开后，日志搜 `[douyin-reward]` |

### 5.1 清理规则用**真实 93 弹窗**校验过

`tests/fixtures/douyin_upsell.json` 是 2026-10-20 真机抓到的原始 `commerce/v2/upsell`（182,993 B / 93 个弹窗）。
`test_douyin_upsell.js` 直接拿它跑清理，断言：

- 广告类 + 商城弹窗 **18 个**被删（含 `browse_mall_popup_acc_amount` 逛商城、`ad_incentive_backup_card` 激励兜底卡）；
- 奖励相关弹窗**全部保留**：`reward_video_load_fail_compensate` / `_retry`（广告加载失败的官方补偿）、
  `reward_task_dialog_active` / `_passive`、`feed_listen_music_reward_popup`、
  `feed_treasure_box_reward_popup`、`treasure_guide_reward_acc_popup`、`task_page_svip_popup`、`coin_widget`（金币挂件入口）；
- `variables`（45 条入口资格变量）与 `libra_params_map` **一个字节都不动**；
- `sort_control_unique_names` / `cold_launch_timing.upsell_item_unique_names` 同步清理，
  包括**只出现在列表、upsell_map 里没有实体**的广告弹窗（如 `cold_launch_popup_ads_text`）——
  不清它，冷启动照样弹广告。

## 5.2 2026-10-21 抓包的两个新结论

**① 响应体是 gzip 的（关键）**

```text
/luna/treasure/task/page/v2      content-encoding: gzip   16–21 KB
/luna/commerce/v2/upsell          content-encoding: gzip   183–191 KB
```

真机日志同时出现 `zip decompress error:-3`（同一连接上的 beta-luna.douyin.com）。
说明 **Loon 偶尔把未解压的压缩串交给脚本** → `JSON.parse` 失败 → 脚本静默放行 → 看起来“插件没效果”。
v0.5.0 起 `readBody()` 会自己识别 gzip 魔数并用 `$utils.ungzip` 解压（Build ≥ 988）。

**② 每个被处理的响应都带诊断头**

```text
X-Soda-Plugin: douyin-treasure;pruned=3        成功精简
X-Soda-Plugin: douyin-treasure;skip=json-parse 拿到压缩体/非 JSON
X-Soda-Plugin: douyin-treasure;skip=switch-off 开关是关的
X-Soda-Plugin: douyin-clean;changed=2          upsell 清理生效
```

抓包里直接看这个头，就能判断“脚本跑了没有、跑到哪一步”。

## 5.3 【演出】的真正开关在 polaris 活动配置里

2026-10-21 抓包发现，`polaris.zijieapi.com/luckycat/activity/settings/get_dynamic_settings/`
（28 KB，`data.activity_info` 181 个活动）里有：

```text
activity_info.music_festival        = 汽水音乐节（= 福利页【演出】）
activity_info.music_festival_v2     = 同上 v2
activity_info.douyin_select_*       = 抖音运营活动（选游戏 / 选作者 / 开学季 / 创作者抽奖）
```

每个条目的形状是 `{"activity_common": {"canshow": false, "forbid_reason": 2, ...}}`。
所以【演出】和这些运营活动**不用删数据，把 `canshow` 置 false 就够了**：
新开关 `cleanActivity` 就是干这个的（默认关；只动 `music_festival*` 与 `douyin_select_*`，
签到/翻卡/红包雨等用户自己的活动一个都不碰）。
`growth/music_festival/performance_details` 的演出列表仍由 `cleanUpsell` 清空。

## 6.1 版本要求（必读）

本插件用 **Loon 3.5.1(983) 起的新版 Script 语法**：

```ini
response if ${url} ~= /^https?:\/\/beta-luna\.douyin\.com\/luna\/treasure\/task\/page\/v2/
  then script("scripts/treasure.min.js", {${treasureMinimal}})
  with enable=${treasureMinimal}, requires_body=true, timeout=10, tag="福利页精简"
```

**为什么不用旧语法**：旧版的 `argument=[{开关名}]` + `enable={开关名}` 在 Loon 3.5.x 上
**不会把开关值送进脚本**——真机日志里 `scripts/treasure.min.js` 被正常触发了，
但 `$argument` 里没有开关值，于是脚本走了“放行”分支，表现为**插件装了却完全没效果**
（2026-10-20 的实测：福利页响应仍是 4 个分区，一条没删）。
换成新版语法后开关以布尔值透传，脚本里另外做了对象/数组/字符串三种形态的兼容解析，
取不到时按插件声明的默认值兜底（`treasureMinimal` 默认开）。

## 6.2 真实样本回归

`tests/fixtures/douyin_treasure_page.json` 是 2026-10-20 真机抓到的**福利页原始响应**，
`test_douyin_treasure.js` 直接拿它跑精简，确保裁剪规则是按真实字段写的，而不是按想象。

本地回归：`npm run check`（build + lint + 源码/压缩版测试）。

---

## 7. 免责声明

仅供个人设备上的网络流量管理与广告过滤研究。请遵守当地法律与 App 用户协议；不要用于批量刷取奖励、绕过付费或商业分发。使用风险自负。
