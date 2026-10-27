# 抖音 · douyin（Loon 聚合插件）

> 所属：Loon 插件仓库 · 插件族 `douyin`（[仓库总览](../../README.md)）
> 部署目录：`plugins/douyin/`；源码目录：`src/douyin/`
> 目标接口：抖音内嵌的音乐/福利模块 `beta-luna.douyin.com/luna/*`
> 取证：2026-10-20 三份真实 Loon HAR（`381_1792495728793.har`、`382_1792495842588.har`、`383_1792495850343.har`）

**架构**：一个 App 一个插件。抖音只部署 `plugins/douyin/douyin.plugin`，所有功能用 Loon `[Argument]` 开关控制。

**版本要求**：Loon 3.5.1(983)+（新版 `script(...,{args})` 语法）。gzip 响应清理依赖 `$utils.ungzip`（988+）；983–987 可安装，但压缩响应端点只记录状态、不清理。

**图标**：`#!icon` 用抖音官方 App 图标（App Store CDN，512×512）；
若要换成字节自家 CDN 的网页版 favicon（32×32，清晰度较低）：
`https://lf1-cdn-tos.bytegoofy.com/goofy/ies/douyin_web/public/favicon.png`。

<!-- >>> GENERATED ARG-TABLE from src/args/douyin.json -- do not edit (npm run build:args) -->
| 开关/参数 | 默认 | 作用 |
|---|---|---|
| `treasureMinimal` | 开 | 福利页只保留【攒时长 听歌不中断】 |
| `cleanFeedAds` | 关 | 清掉信息流/广告位广告容器（**不影响激励奖励**） |
| `killRewardAds` | 关 | 断掉激励广告素材与预拉取（= 广告完全不发，奖励也没了） |
| `cleanUpsell` | 关 | 删商业化弹窗、逛商城弹窗、汽水音乐节（演出）列表 |
| `cleanActivity` | 关 | 把 polaris 活动配置里的汽水音乐节（演出）与抖音运营活动（选游戏/选作者/开学季/创作者抽奖）置为不展示 |
| `blockAdDomains` | 关 | 广告/归因域名拦截（MITM + `http-request` 脚本） |
| `blockSplashAd` | 关 | 拦掉穿山甲开屏广告请求（`splash/` 与 `vN/(ack/)splash/` 全家族），**不碰激励广告**与发奖回调 |
| `debugLog` | 关 | 只读日志，前缀 `[douyin-reward]`（含穿山甲广告配置、领奖回调、广告耗时实测） |
| `dailyReminder` | 关 | 每天 cron 时间检查：当天没打开福利页就发 Loon 通知（只提醒不代领） |
| `reminderCron` | `30 20 * * *` | 提醒时间，五段 cron（分 时 日 月 周），默认每天 20:30 |
| `statusNotify` | `notification` | 状态自检按钮通知模式：`notification` 弹通知并带 `openUrl`；`silent` 只写日志和结果页（Loon `[Argument]` `select`）；结果页汇总当前开关、提示冲突组合，并输出 Loon 环境（`$loon` / 脚本 / 节点 / 运行模式） |
<!-- <<< GENERATED ARG-TABLE -->

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

`treasureMinimal=true` 时：只保留 `duration_task_section`（只留 `luna_rewards_ads`），其余分区整体删除；`config.migrate_first_ad` 置 false，`config.ad_api_preload.task_ids` 只留保留下来的任务自己引用的 id（被删任务与页面里不存在的 id 不再预拉取），一条不剩时 `preload` 一并关闭。

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

合规可行的只有两种：要么**广告完全不看**（本插件 `cleanFeedAds` / `killRewardAds` / `blockAdDomains` 走的路，此时也不能领对应奖励），
要么**完整看完**再领。本插件的原则是：前者可以，后者不造假。

### 3.4 开屏广告请求拦截（`blockSplashAd`，默认关）

开屏广告和激励广告都走穿山甲（CSJ），但路径分开。`blockSplashAd` 在 `http-request` 阶段只拦开屏素材获取与登记：

```text
/api/ad/splash/                 # luna/aweme v14/v15、stock/realtime
/api/ad/vN/splash/              # 版本化库存
/api/ad/vN/ack/splash/          # ack 上报
```

命中后返回 200 + JSON `{}`，请求不会真正出网；`ad.zijieapi.com/api/ad/v1/inspire/**`（激励）与 `api/incentive/marketing/done`（发奖回调）不在匹配范围。与汽水共用 `src/common/splash-ad.js`（家族差异只有日志前缀），lint 对两家族做 3 hit / 3 miss 边界锁定。

需要 `ad.zijieapi.com` / `ads?-normal*.zijieapi.com`（Pangle 分片族）在 `[MITM]`（本插件已声明）。如果开启后抖音启动异常，先改回关即可。

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

[![一键导入 douyin.plugin](https://img.shields.io/badge/Loon-导入抖音-black?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fdouyin%2Fdouyin.plugin)

```text
loon://import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fdouyin%2Fdouyin.plugin
```

直链地址（无需开启 Pages）：

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
| 开屏广告是否还在 | `blockSplashAd` 打开后冷启，日志应出现 `[douyin-splash] blocked`；激励广告仍能正常加载 |
| 状态看板 | 点「插件状态自检」：结果页含「开关状态」摘要与「运行环境」行（Loon 版本/脚本/节点/运行模式）；`treasureMinimal` 与 `killRewardAds` 同开时出现冲突提醒 |
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

**③ 编码边界：只认 gzip，br 解不了（v0.8.1 起能看出来）**

Loon 的脚本层只有 `$utils.ungzip`（gzip，Build 988+），没有 brotli / zstd 解码器，
也没有通用的 `decompress(data, algo)` 入口；官方复写文档全文对压缩没有任何承诺。
更麻烦的是 **br 没有魔数**（RFC 7932 是纯 stream format，不带 checksum 与原始长度），
所以脚本连“这段字节是不是 br”都判断不出来——只能读 `content-encoding` 响应头。
gzip 不一样，`1f 8b` 两个字节就能认，这也是 `readBody()` 只嗅 gzip 的原因。

v0.8.1 起解不了的编码会写进标记，把“编码不支持”和“接口换了形状”分开：

```text
X-Soda-Plugin: douyin-clean;skip=not-json;ce=br   ← 是 br 压缩体，不是非 JSON
X-Soda-Plugin: douyin-clean;skip=not-json         ← 真的不是 JSON
```

`gzip` / `identity` / 没有该头时不加 `ce=`，标记保持干净。真遇到 `ce=br` 的修法：
**不要删** `Accept-Encoding`（upsell gzip 后已 183–191 KB，去压缩会膨胀 5~10 倍），
只对那一个端点把请求头设成 `Accept-Encoding: gzip`——压缩照旧，只是禁止服务端选 br。

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

本地回归：`npm run check`（build + lint + coverage + 源码/压缩版测试；26 套 / 798 条断言 × 2 = 1596）。

---

## 7. 版本更新记录

### v0.8.5（2026-10-27）插件元数据补齐 `#!openUrl`

- **`#!openUrl` 落地**：插件详情页「打开链接」直达本 README
  （`https://github.com/AshNail/plugins/blob/main/plugins/douyin/README.md`）。lint 同步校验。

### v0.8.4（2026-10-27）修掉一处「每量一次广告就清空全部存储」

- **`$persistentStore.remove(key)` 不是「删这个键」**：官方 Script API 5.3 写明它不接受参数，
  语义是清空全部脚本数据。原来领奖回调里调它清开始时间，把 `douyin-welfare-seen`、
  `douyin-ad-stats` 一起抹了，且无任何报错。改成 `write(undefined, AD_START_KEY)`。
- **状态页新增「全局直连」告警**：`running_model = 0` 时插件完全不生效，结果页会点名。
- **新增 `tests/test_store_scope.js`** 与 lint `SAFE_STORE_WIPE_RX`，与汽水共用同一套守卫。

### v0.8.3（2026-10-27）压缩从「事后诊断」变成「事前统一」

- **`[Rewrite]` 把压缩协商降到 gzip（常开）**：脚本层只有 `$utils.ungzip`，br/zstd 解不开，
  乱码会落进「不是 JSON」分支，看起来和「接口没广告」一样。这里直接改请求头，服务端不再回 br。
  降级不是免压缩（gzip 比 br 只大 10~20%，免压缩会膨胀 5~10 倍，见 E2）。
- **回写 body 时清掉 `content-encoding` / `content-length`**：新 body 是明文，旧头指向压缩体，
  留着会让客户端按 gzip 解明文或按旧长度截断。
- **`blockAdDomains` 回包改为 `200 + application/json + {}`**，与 `reject_dict(200)` 同形状，
  避免 SDK 走「解析失败→重试」。
- **`debug=${debugLog}`**：14 条 `[Script]` 全部挂上官方 `with debug`，与「只读日志」开关联动。
- **lint 守卫**：`Accept-Encoding` 只允许 gzip 降级写法；降级规则必须覆盖 `[MITM]` 全部域名。

### v0.8.2（2026-10-27）广告拦截从「单分片」升级为「全族」

- **`[MITM]` 用通配代替枚举**：`ads5-normal-hl.zijieapi.com` → `ads?-normal*.zijieapi.com`。
  官方文档写明 `[MITM] hostname` 支持 `*` / `?`，一条覆盖 `ads3/ads5 × normal/-hl/-lf/-lq/-xh`。
  分片由服务端下发，以前只在名单里放 ads5，服务端换到 ads3 就整个静默失效。
- **QUIC 回退补到 16 条**：`[Rule]` 的 `DOMAIN-SUFFIX` 不吃通配，逐个列 10 个分片；
  与 `[MITM]` 的覆盖关系由 lint 的 `mitm_covers()` 按 glob 校验。
- **`BLOCKED_HOSTS` 支持 glob**：`?` 一个字符、`*` 任意字符，脚本内预编译成正则；
  `[Script]` 正则同步改成 `ads[0-9]-normal[a-z0-9-]*\.zijieapi\.com`。
  lint 改成「正反 URL 样本双向命中」（名单含 glob 后字面集合比对失去意义）。
- **状态看板**：`静态层：QUIC 回退 16 域`。

### v0.8.1（2026-10-27）编码诊断：把「解不了」和「不是 JSON」分开

- **`readBody()` 旁边新增 `ceTag()`**：读 `content-encoding`，非 gzip 时给诊断标记加上 `;ce=br`。
  之前 br / zstd / deflate 的响应体都会以乱码落进 `skip=not-json`，和「接口换了形状」
  长得一模一样；`skip=json-parse` 分支同样带上，覆盖「压缩体凑巧以 `{` 开头」的少数情况。
- **`gzip` / `identity` / 无该头不加 `ce=`**：正常路径标记保持干净。
- **`observe.js` 在非 JSON 时不再静默**：原来直接 `$done({})`，接口换形状、返回 HTML
  错误页、或换成 br 编码三种情况全都看不出来；现在打一行 `non-JSON len=… ce=… url`。
  `reward-observe.js` 的 `non-JSON` / `JSON parse failed` 日志同步加 `ce=`。
- 背景（写进 §5.2）：Loon 脚本层只有 `$utils.ungzip`，br 没有魔数、官方复写文档对压缩
  一字未提，「br 解不了」是硬边界。真遇到 `ce=br` 的修法是只对该端点把 `Accept-Encoding`
  **设为** `gzip`（不是删掉，删掉会让 183–191 KB 的 upsell 膨胀 5~10 倍）。
- **lint 新增 `check_encoding_guard()`**：6 个解析 body 的脚本必须同时有 `readBody()` 与
  `ceTag()`，四条「解析失败」分支都不许漏 `ceTag()`。
- **新增 `test_encoding_guard.js`（22 断言）**：六脚本 × br/gzip/无头三态、头名大小写、
  `gzip, br` 逗号列表、正常 JSON 不受干扰。
- 回归：48 套件 / 1442 断言全绿；lint 0 error。

### v0.8.0（2026-10-27）静态传输层常开：QUIC 回退 + h2

- **`[Rule]` 新增 7 条 `AND,((DOMAIN-SUFFIX,…),(PROTOCOL,QUIC)),REJECT`**：只针对 `[MITM]` 里的精确域，
  把 HTTP/3 逼回 TCP+TLS。MITM 只处理 TCP，QUIC 流量脚本完全看不见——这是所有脚本的前置条件。
  不做全局 `PROTOCOL,QUIC,REJECT`（会伤视频/通话）。
- **`[MITM]` 新增 `h2 = true`**（后经复核：官方 MitM 文档只列 `hostname`/`ca-p12`/`ca-passphrase`，
  没有 `h2`；HTTP/2 解密是官方产品页宣称的默认能力。保留该行属零成本冗余，不当能力点宣称）。
- **删除注释里的 `[Rule]` 严格模式**：静态全域 REJECT 会直接掐断攒时长（看广告结算），
  且已被 `blockAdDomains` + QUIC 回退覆盖。
- **评估后放弃“请求免压缩”**：HAR 里 `commerce/v2/upsell` 在 gzip 下已有 183–191 KB，
  去压缩会让单次传输膨胀 5~10 倍，换一次 `ungzip` 不划算。lint 反向锁死。
- 这一层**没有开关**：关掉等于让上面所有脚本失效。回滚方式 = 删对应行。
- 状态看板新增「静态层：QUIC 回退 7 域 · h2（常开）」。
- lint 新增静态层完整性、跨层短路矩阵、`SWITCH_LABELS` 双向一致三组守卫。
- 回归：46 套件 / 1398 断言全绿；lint 0 error。

### v0.7.9（2026-10-27）状态看板加入 Loon 环境诊断

- 与汽水共用 `status.js`：结果页新增「运行环境」行，汇总 `$loon`、`$script.name/startTime`、`$environment.params.nodeInfo`（兼容 `$envirnoment` 拼写）与 `$config.getConfig().running_model`；「Loon 能力」行检测 `$utils.ungzip`（988+）是否可用。
- 缺失全局对象时整行省略，不弹错、不发请求；通知正文同样带上，方便截图回传。
- 文档补充 gzip 门槛：`$utils.ungzip` 自 Loon 3.5.1(988) 提供；983–987 可安装，但 gzip 响应只记录状态。
- 回归：`test_status.js` 31 → 40 条；全量 46 套件 / 1398 断言。

### v0.7.8（2026-10-27）修复福利页打卡被精简脚本遮蔽

- Loon 对同一响应只执行配置顺序里第一条条件为真的 Response Script。`treasureMinimal` 默认开启且排在 `welfare-stamp` 之前，导致打卡脚本永远轮不到、`dailyReminder` 每天误报。
- 打卡逻辑内置进 `treasure.js` 与 `observe.js`：命中 `treasure/task/page/vN` 且 `dailyReminder=true` 时写入 `douyin-welfare-seen`；独立 `welfare-stamp` 绑定只在两者都关时兜底。
- 状态看板新增 `treasureMinimal+debugLog` 遮蔽提示；lint 新增绑定矩阵，同 URL 多绑定只允许同脚本同参数或显式白名单组合。
- 回归：新增 `test_welfare_stamp.js` 10 条；全量 46 套件 / 1376 断言。

### v0.7.7（2026-10-27）状态自检升级为开关看板

- Generic 按钮透传全部开关，结果页与通知新增「开关状态」摘要（`treasureMinimal` / `cleanFeedAds` / `killRewardAds` / `cleanUpsell` / `cleanActivity` / `blockAdDomains` / `blockSplashAd` / `debugLog` / `dailyReminder` / cron）。
- 冲突组合显式提醒：`killRewardAds` 与 `treasureMinimal+killRewardAds`（福利页只剩攒时长，但激励已断）；与汽水共用 `status.js`。
- lint 锁定 generic 绑定必须透传全部声明开关。
- 回归：`test_status.js` 29 条断言；全量 44 套件 / 1336 断言。

### v0.7.6（2026-10-27）开屏广告请求拦截 + 共享源统一

- 新增 `[Argument]` `blockSplashAd`（默认关）与 `http-request` 绑定：只拦穿山甲开屏 `api/ad/splash/`、`api/ad/vN/splash/`、`api/ad/vN/(ack/)splash/` 家族，返回 200 + JSON `{}`；`inspire`、`inspire_preload` 与 `marketing/done` 不在匹配范围，激励与发奖不受影响。
- `splash-ad.js` 从 `src/soda/` 迁入 `src/common/` 单一来源（家族差异只有日志前缀 `[douyin-splash]` / `[soda-splash]`），与 block-domains / daily-reminder / welfare-stamp / status 同层管理。
- lint 新增开屏绑定边界锁：每个家族必须有且仅有一条 splash 绑定，3 个开屏样本全部命中，`inspire` / `inspire_preload` / `marketing/done` 三个样本全部不命中。
- 回归：`test_splash_ad.js` 双家族 22 条断言；全量 44 套件 / 1302 断言。

### v0.7.5（2026-10-27）原生 reject_dict + select 参数

- DSP 展示上报 Rewrite 从 `reject(200)` 换成 Loon Rewrite v2 原生 `reject_dict(200)`：返回 JSON `{}` + `application/json`，避免 SDK 对空 Body / `text/plain` 的解码差异，仍然不产生真实出网。
- 新增 `[Argument]` `statusNotify = select,"notification","silent"`：Generic 状态自检按钮可选弹通知（带 `openUrl` 跳抖音）或静默模式；`status.js` 与汽水插件共用同一份实现。
- lint 锁定 `statusNotify` select 候选值与 generic 按钮参数透传，并继续校验上报 Rewrite 必须使用 `reject_dict(200)`。

### v0.7.4（2026-10-27）福利页预拉取已删任务停止预热 + upsell 频控同步

- **福利页**：`config.migrate_first_ad` 置 false；`config.ad_api_preload.task_ids` 改为按保留任务引用过滤（`task.id` / `ad_snap.task_id` / `base_ad_diversion.id`），被裁掉的任务和页面里不存在的 id 不再预拉取，一条不剩时 `preload` 关闭；保留任务若仍引用预拉取 id 则不受影响。
- **商业化弹窗**：删除广告/商城弹窗后，同步删除 `freq_ctrl_cfg.freq_ctrl_map` 里与已删弹窗同名的频控项（真实样本 82→79）；`background_voice_prompt` 这类被普通弹窗共享的键、以及 `widget_ad` 等非 upsell 实体的键保持原样。
- 回归：`test_douyin_treasure.js` 38 条、`test_douyin_upsell.js` 46 条、`test_douyin_clean.js` 44 条。

### v0.7.3（2026-10-27）ads/retrieve 补齐 + 大响应预检

- `cleanFeedAds` 绑定的信息流清理从 `ads/(config|dsp/retrieve)` 扩到 `ads/(config|retrieve|dsp/retrieve)`；`clean.js` 新增 `ad_launch` / `ad_launch_list` / `ad_launches` / `ads_blocks` / `ads_info` / `ad_unit_configs` / `splash_config` / `feed_ads_config` / `reward_config` 等字段清理。
- 广告配置响应在 `JSON.parse` 前先做广告标记预检，无标记的大响应直接放行并写 `X-Soda-Plugin: douyin-clean;noop=no-marker`。
- 只读观测绑定同步覆盖 `ads/retrieve`。

### v0.7.2（2026-10-26）传感器误触 / 商业推广 / 上报阻断

- 广告配置清理补 `shake_info` / `twist_info` / `motion_info` / `interaction_info` / `splash_cache`、DSP/广告位配置字段，并把 `preload` / `enable_ads` / `enable_ad` 置 false。
- 信息流广告条目识别扩展 `is_promoted` / `is_sponsored` / `is_commercial`。
- 新增 `luna/ads/report/dsp/show` 请求阻断（`reject(200)`，`cleanFeedAds` 控制）。
- 新增 `status.js` Generic 状态脚本与通知 attach openUrl。

### v0.7.1（2026-10-26）共享脚本单一来源整合（行为不变）

- **同功能不分散**：`block-domains.js` / `daily-reminder.js` / `welfare-stamp.js`
  三个脚本此前与 `src/soda/` 各存一份逐字复制（只差日志前缀、存储键前缀、
  通知文案与 `rewardSafe` 默认值）。现统一为单一来源 `src/common/*.js` +
  家族参数 `src/common/families.json`，`tools/build.js` 按家族展开到
  `src/douyin/`（生成物，勿手改）再压缩；源码一处改动，两个家族同步生效。
- **编译产物逐字节等价**：生成后 `plugins/douyin/scripts/` 里 3 个对应
  `.min.js` 与重构前完全一致（`git diff` 零差异），无行为变化。
  douyin 无 rewardSafe 概念 → `families.json` `rewardSafeDefault=false`
  已由测试断言锁定（`blockAdDomains=开` 且未显式传 rewardSafe 时照旧拦截）。
- **名单四处一致性锁**：lint 新增两项守卫——① 按 families.json 重新展开
  共享脚本并与 `src/<family>/` 生成物逐字节比对；② 把 `BLOCKED_HOSTS`
  与插件的 `[Script]` 正则、`[MITM]` 两处名单强校验（注释里的静态严格模式已删除）。
- **分层说明写入插件头注释**：被拦的 5 个域名中 3 个同时被 `ads.plugin`
  DNS 层拦截；`zlink/praisewindow.ugsdk.cn` 为 App 内运营端点，仅本开关覆盖。

### v0.7.0（2026-10-22）每日提醒打卡

- 新增 `dailyReminder` / `reminderCron` 与 `scripts/welfare-stamp.min.js`：
  打卡 `beta-luna.douyin.com/luna/treasure/task/page`（`[MITM]` 新增该域），
  当天未打卡到点通知；统计键 `douyin-ad-stats`。
- **内部整理（2026-10-23 同批）**：
  1. `observe.js` 主流程改走 `readBody`——原先直读 `$response.body`，Loon 交接
     gzip 原串时观察者会静默失效（readBody 明写了兼容三种形态但没被调用）；
  2. 页面兼容范围 `task/page/v2` → `task/page/v[0-9]+`（treasure.js / observe.js /
     两处插件绑定同步），为下一版页号漂移兜底；
  3. clean.js / treasure.js 各删除一份重复的工具块声明（pargs/pflag 复制两次），
     `[soda]` 误用 tag 修正为家族各自前缀。
- 边界不变：`marketing/done` 等领奖请求仍为**观测只读**；抖音侧奖励受服务端设备风控
  （1000043/210021），插件不可绕过也不尝试绕过。

---

## 8. 免责声明

仅供个人设备上的网络流量管理与广告过滤研究。请遵守当地法律与 App 用户协议；不要用于批量刷取奖励、绕过付费或商业分发。使用风险自负。
