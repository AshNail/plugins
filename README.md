# Loon 插件仓库

> 仓库名：`loon-plugins`  
> GitHub：`https://github.com/AshNail/plugins`

个人 Loon 插件集合，按 **插件族（family）** 组织。每个插件族自包含：`.plugin` 文件与压缩后的 `scripts/` 放在同一目录，方便 Loon 通过相对路径加载脚本。

当前插件族：**汽水音乐（soda）**、**抖音（douyin）**、**广告平台拦截器（ads）**。详细逆向说明、字段取证和使用边界见 [`plugins/soda/README.md`](plugins/soda/README.md)、[`plugins/douyin/README.md`](plugins/douyin/README.md) 与 [`plugins/ads/README.md`](plugins/ads/README.md)。

> **广告平台拦截器是单插件底层依赖**：`ads.plugin` 在 DNS 阶段把广告平台域映射到 `127.0.0.1`，并用 `[Rule]`/`[General]` 处理 HTTPDNS 与公共 DoH/DoT。零证书、不依赖 MITM/脚本。它会同时拦掉激励广告，**和 soda/douyin 的保奖励模式冲突**；刷奖励时请禁用。详见 [`plugins/ads/README.md`](plugins/ads/README.md)。

---

## 插件列表

| 插件 | 版本 | 用途 | 兼容性 |
|---|---:|---|---|
| `soda.plugin` | 2.6.2 | 汽水音乐唯一插件：保奖励 / 去广告脚本 / 广告域名拦截 / 设置层 / 只读日志 / 隐藏【听抖音】 / 每日提醒打卡，全部用 `[Argument]` 开关控制 | 一个 App 只装这一个；域名拦截走 MITM+脚本，HTTP/3 可能漏过 |
| `douyin.plugin` | 0.7.1 | 抖音唯一插件：福利页精简（只留【攒时长 听歌不中断】）、信息流广告清理、激励广告开关、商业化弹窗/商城/演出清理、域名拦截、只读日志、每日提醒打卡 | 依据 2026-10 真实 HAR 取证；MITM 抖音 API 域名有证书固定风险 |
| `ads.plugin` | 2.1.2 | 单插件 All-in-One：广告平台 DNS 拦截 + HTTPDNS/私有 DoH 防绕过 + 公共 DoH/DoT 防泄漏；归因/统计组默认注释 | **零证书、零 MITM/脚本**；会断激励广告，刷奖励时禁用；公共 DoH 拦截可能影响浏览器安全 DNS |

> 一个 App 只保留一个 `.plugin`。旧的 `SodaClean` / `SodaClean-Reward` / `SodaClean-Reward-Debug` / `SodaClean-Settings` 独立插件已合并进 `soda.plugin`，不再单独部署；历史版本可在 git 历史中找回。
>
> `ads` 已合并为**一个** `ads.plugin`：核心广告、HTTPDNS、公共 DoH、可选归因/统计都在同一文件里；旧的 `ads-httpdns.plugin` / `ads-measurement.plugin` / `ads-strict.plugin` 已删除，不要再安装。归因/统计默认注释，按需在 `src/ads/domains.json` 开启。
>
> **公共脚本单一来源（同功能不分散）**：soda / douyin 两个插件的 `block-domains`（广告域名拦截）、`daily-reminder`（每日提醒）、`welfare-stamp`（打卡）共用 `src/common/*.js` 一份源码，品牌差异（日志前缀 / 文案 / 开关默认值）集中在 `src/common/families.json`，构建时按家族展开——不要直接改 `src/<family>/` 里的这三个生成文件。`lint` 会校验 families.json 展开一致，并锁定拦截名单与插件 `[Script]` / `[Rule]` / `[MITM]` 四处一致。
>
> **「广告域名拦截」的分层**：5 个被拦域名中 `ad.zijieapi.com` / `lianmengapi.snssdk.com` / `ads5-normal-hl.zijieapi.com` 已同时被 `ads.plugin` 的 `[Host]` DNS 层拦截；App 插件的同份名单是 **MITM 兜底层**（挡 HTTP/3 之外的已解密流量，且在 `ads.plugin` 刷奖励关闭时仍单独可用）。`zlink.ugsdk.cn` / `praisewindow.ugsdk.cn` 是 App 内运营端点（口令/弹窗），只由 App 插件开关覆盖，不进全局 DNS 插件。

### 版本要求（重要）

`soda` / `douyin` 两个 App 插件都用 **Loon 3.5.1(983) 起支持的新版 Script 语法**：

```ini
response if ${url} ~= /^https?:\/\/api\.qishui\.com\/luna\/treasure\/task\/view/
  then script("scripts/sanitize.min.js", {${rewardSafe}, ${cleanAds}})
  with enable=${cleanAds}, requires_body=true, timeout=10, tag="..."
```

原因（2026-10-20 真机日志实证）：旧版语法里的 `argument=[{开关名}]` + `enable={开关名}`
**不会把开关值送进脚本**——脚本被正常触发，但拿到的 `$argument` 里没有开关，
于是所有按开关分支的逻辑都走了“放行”，表现为“插件装了但没效果”。
换新版语法后，开关以布尔值透传（`$argument.<参数名>`），脚本里也做了
对象/数组/字符串三种形态的兼容解析，取不到时按插件声明的默认值兜底。

`ads` 单插件使用 `[General]` + `[Rule]` + `[Host]`，不依赖 Script/MITM；仓库统一按 Loon 3.5.1(983)+ 标注，早期版本可能只支持其中一部分 `[General]` 键。

### 响应体是 gzip 时的兼容（2026-10-21 真机发现）

抖音/汽水的这些接口回包**全是 `content-encoding: gzip`**：

```text
beta-luna.douyin.com/luna/treasure/task/page/v2      16–21 KB
beta-luna.douyin.com/luna/commerce/v2/upsell        183–191 KB
api.qishui.com/luna/advert/incentive/done              191 B
conf.qishui.com/service/settings/v3/               175 KB
```

Loon 偶尔会把**未解压的压缩串**交给脚本（真机日志里同时有 `zip decompress error:-3`），
这时 `JSON.parse` 直接失败 → 脚本静默放行 → 表现为“插件装了没效果”。
v2.4.0 / v0.5.0 起脚本会自己处理：

- `readBody()`：识别 gzip 魔数（`1f 8b`）→ 用 `$utils.ungzip`（Build ≥ 988）解压 → UTF-8 解码；
- 也能直接吃 `Uint8Array`（`binary_body_mode=true`）；
- 每个被处理的响应都带 **`X-Soda-Plugin`** 诊断头，例如
  `X-Soda-Plugin: douyin-treasure;pruned=3` / `;skip=json-parse`，
  下次抓包一眼就能看出脚本跑到哪一步、为什么没生效。

### 广告耗时统计（debugLog 打开即可）

```
[soda-reward] 发奖结果 amount=1800 claim=1 | 广告请求->发奖 30 秒 | 今日广告 3 次 / 共 90 秒
[douyin-reward] 广告平台领奖回调
  marketing/done -> code=0 msg=
  广告请求->发奖 实际耗时: 31 秒
  今日广告: 2 次 / 共 62 秒
```

统计存在 Loon 本地（`$persistentStore`），按天累计，方便对照“今天为了拿时长/金币
一共看了几个广告、花了几分钟”。领取面板构建端实测零死时（素材播放到尾帧即出现按钮、
点击到发奖响应 315–420ms），日志里若出现 >35s，多出部分是加载/等待，值得排查。

```
[douyin-reward] 广告平台领奖回调
  marketing/done -> code=0 msg=
  广告请求->发奖 实际耗时: 31 秒        ← 30 秒是广告本体；>35 说明多出来的是加载/等待
[soda-reward] 发奖结果 amount=1800 claim=1 | 广告请求->发奖 30 秒
```

`amount=-1` 表示这笔奖励**没发出来**（广告没播或被风控）——这通常是
`killRewardAds` / `cleanAds` 开着导致的（广告素材被清空 → 广告没播 → 领不到）。
**要领奖就别开这两个开关。**

### 插件图标（`#!icon`）

| 插件 | 图标来源 | URL |
|---|---|---|
| `soda.plugin` | 汽水音乐官方 logo（字节静态 CDN，256×256 PNG） | `https://lf3-static.bytednsdoc.com/obj/eden-cn/zvtheh7pfpenuhog/cyber_logo/music.png` |
| `douyin.plugin` | 抖音官方 App 图标（App Store CDN，512×512） | `https://is1-ssl.mzstatic.com/image/thumb/Purple221/v4/56/0d/e6/560de620-6e7e-4679-43e4-689a52d71e4c/AppIcon-0-0-1x_U007emarketing-0-0-0-7-0-0-85-220.png/512x512bb.jpg` |
| `ads.plugin` | AdGuard 官方 logo（CDN） | `https://cdn.adguard.com/public/Adguard/Common/logo.png` |

> 抖音若要改用字节自家 CDN 的网页版 favicon（32×32，清晰度较低）：
> `https://lf1-cdn-tos.bytegoofy.com/goofy/ies/douyin_web/public/favicon.png`
> （`s3.bytecdn.cn` 上的 `favicon_v2_7145ff0.ico` 在部分网络不可达，不建议用）

> 保奖励模式只保证“完整看完广告后正常领奖”，不提供跳过广告、伪造回调、重复领奖或未看完就发奖。

---

## 仓库结构

```text
.
├── plugins/
│   ├── soda/
│   │   ├── README.md                  # 汽水音乐详细说明
│   │   ├── soda.plugin                # 唯一部署插件（聚合开关版）
│   │   └── scripts/
│   │       ├── sanitize.min.js
│   │       ├── settings.min.js
│   │       ├── reward-observe.min.js
│   │       ├── splash-ad.min.js
│   │       ├── block-domains.min.js   # ← 与 douyin 同源（src/common 生成）
│   │       ├── daily-reminder.min.js  # ← 与 douyin 同源（src/common 生成）
│   │       └── welfare-stamp.min.js   # ← 与 douyin 同源（src/common 生成）
│   ├── douyin/
│   │   ├── README.md                  # 抖音详细说明
│   │   ├── douyin.plugin              # 唯一部署插件（聚合开关版）
│   │   └── scripts/
│   │       ├── treasure.min.js
│   │       ├── clean.min.js
│   │       ├── observe.min.js
│   │       ├── block-domains.min.js   # ← 与 soda 同源（src/common 生成）
│   │       ├── daily-reminder.min.js  # ← 与 soda 同源（src/common 生成）
│   │       └── welfare-stamp.min.js   # ← 与 soda 同源（src/common 生成）
│   └── ads/
│       ├── README.md                  # 广告平台拦截器单插件说明
│       └── ads.plugin                 # 唯一部署文件：General + Rule + Host，零证书
├── src/
│   ├── common/                        # soda/douyin 共享脚本单一来源
│   │   ├── block-domains.js           #   广告域名拦截（5 域名单唯一写点）
│   │   ├── daily-reminder.js          #   每日领取提醒
│   │   ├── welfare-stamp.js           #   福利页打卡
│   │   └── families.json              #   家族参数（tag/文案/开关默认值）
│   ├── soda/                          # 可读源码（block-domains 等三个为生成物）
│   │   ├── sanitize.js
│   │   ├── settings.js
│   │   ├── reward-observe.js
│   │   ├── splash-ad.js
│   │   ├── block-domains.js           # ← src/common 生成，勿手改
│   │   ├── daily-reminder.js          # ← src/common 生成，勿手改
│   │   └── welfare-stamp.js           # ← src/common 生成，勿手改
│   ├── douyin/                        # 可读源码（block-domains 等三个为生成物）
│   │   ├── treasure.js
│   │   ├── clean.js
│   │   ├── observe.js
│   │   ├── block-domains.js           # ← src/common 生成，勿手改
│   │   ├── daily-reminder.js          # ← src/common 生成，勿手改
│   │   └── welfare-stamp.js           # ← src/common 生成，勿手改
│   └── ads/                           # 广告平台拦截器数据源
│       ├── domains.json               # 分组 + 域名（唯一数据源）
│       └── protected-roots.json       # 共享主域保护名单
├── tests/                             # 脚本层回归测试
├── tools/build.js                     # 源码 -> 压缩脚本（含共享层家族展开）
├── tools/build-ads.py                 # src/ads/domains.json -> plugins/ads/ads.plugin
├── tools/ads-audit.py                 # 上游清单覆盖率/缺口审计
├── .github/workflows/check.yml        # CI：build + lint + 源码/压缩版测试
├── package.json
├── package-lock.json
├── .nojekyll
└── .gitignore
```

约定：

- **`src/` 是源码**，修改脚本只改这里；其中 `src/common/` 是 soda/douyin 共享脚本的**单一来源**（`block-domains.js` / `daily-reminder.js` / `welfare-stamp.js`），品牌差异写在 `src/common/families.json`；`src/<family>/` 里同名文件是构建生成物，勿手改；
- **`plugins/` 是部署目录**，`*.min.js` 由 `tools/build.js` 用 terser 实际压缩生成，不是只改后缀；
- `.plugin` 里的 `script-path=scripts/xxx.min.js` 是相对路径，所以 `.plugin` 和 `scripts/` 必须保持同级；
- 构建脚本先按 `families.json` 把共享脚本展开到 `src/<family>/`，再自动发现 `src/<family>/` 下的所有 `.js`，输出到 `plugins/<family>/scripts/`；`src/common/` 本身不输出插件；
- `lint` 会做两件共享层守卫：① 按家族重新展开 `src/common/*.js` 并与 `src/<family>/` 生成物逐字节比对；② 把 `block-domains.js` 的 `BLOCKED_HOSTS` 与插件 `[Script]` 正则、注释 `[Rule]`、`[MITM]` 四处名单强校验一致；
- 压缩会去掉注释和空白、缩短局部/顶层变量名；`AGGRESSIVE` / `DRY_RUN` 等开关名保留，便于排查。
- **`ads` 单插件是数据驱动**：只改 `src/ads/domains.json` 和 `src/ads/protected-roots.json`，运行 `npm run build:ads` 生成 `plugins/ads/ads.plugin`；不要手改生成物，`npm run lint` 会逐字节比对并报 stale。

当前脚本压缩结果（soda / douyin，含共享层同名脚本展开）：

| 源码 | 源码大小 | 压缩版 | 压缩后 |
|---|---:|---|---:|
| `src/soda/sanitize.js` | 30,586 B | `plugins/soda/scripts/sanitize.min.js` | 13,660 B |
| `src/soda/settings.js` | 21,063 B | `plugins/soda/scripts/settings.min.js` | 7,886 B |
| `src/soda/reward-observe.js` | 24,545 B | `plugins/soda/scripts/reward-observe.min.js` | 13,315 B |
| `src/soda/splash-ad.js` | 3,502 B | `plugins/soda/scripts/splash-ad.min.js` | 1,202 B |
| `src/common/block-domains.js` → `src/{soda,douyin}/` | 4,728 / 4,735 B | `plugins/*/scripts/block-domains.min.js` | 1,451 / 1,461 B |
| `src/common/daily-reminder.js` → `src/{soda,douyin}/` | 2,814 / 2,816 B | `plugins/*/scripts/daily-reminder.min.js` | 1,353 / 1,359 B |
| `src/common/welfare-stamp.js` → `src/{soda,douyin}/` | 1,577 / 1,583 B | `plugins/*/scripts/welfare-stamp.min.js` | 618 / 628 B |
| `src/douyin/treasure.js` | 8,548 B | `plugins/douyin/scripts/treasure.min.js` | 3,706 B |
| `src/douyin/clean.js` | 14,345 B | `plugins/douyin/scripts/clean.min.js` | 5,688 B |
| `src/douyin/observe.js` | 16,238 B | `plugins/douyin/scripts/observe.min.js` | 8,155 B |

合计 **137,080 B → 60,482 B（约 -55.9%）**；三个共享脚本源码只存一份（`src/common/`），家族差异由 `families.json` 注入。每个 `.min.js` 只有 2 行：一行来源标记 + 一行压缩代码（源码为 39–610 行）；构建和 lint 都会检查「压缩后必须比源码小、行数不超过 5 行」。Loon 只加载 `plugins/<family>/scripts/*.min.js`；原始代码仍在 `src/`。

---

## 安装

把仓库推到 `https://github.com/AshNail/plugins` 后，`Settings → Pages → Deploy from a branch`，Branch 选 `main`，Folder 选 `/ (root)`。不需要 `index.html`，根地址 404 是正常的，直接访问插件文件即可。

汽水音乐唯一插件（一个 App 只装这一个）：

```text
https://ashnail.github.io/plugins/plugins/soda/soda.plugin
```

Loon 导入链接：

```text
loon://import?plugin=https%3A%2F%2Fashnail.github.io%2Fplugins%2Fplugins%2Fsoda%2Fsoda.plugin
```

如果 GitHub Pages 还没开启，先用 raw 地址：

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/soda/soda.plugin
```

抖音插件（另一个 App，同样只装一个）：

```text
https://ashnail.github.io/plugins/plugins/douyin/douyin.plugin
loon://import?plugin=https%3A%2F%2Fashnail.github.io%2Fplugins%2Fplugins%2Fdouyin%2Fdouyin.plugin
```

广告平台拦截器（单插件，不需要其他 ads 文件）：

```text
https://ashnail.github.io/plugins/plugins/ads/ads.plugin
```

Loon 导入：

```text
loon://import?plugin=https%3A%2F%2Fashnail.github.io%2Fplugins%2Fplugins%2Fads%2Fads.plugin
```

> **冲突提醒**：`ads.plugin` 会在 DNS 阶段拦掉穿山甲/优量汇/快手联盟，soda/douyin 的激励广告和奖励任务会失败。刷奖励时禁用 `ads.plugin`，或不要把两者同时启用。完整风险表、HTTPDNS 与 DNS 防泄漏主配置片段见 [`plugins/ads/README.md`](plugins/ads/README.md)。

`soda.plugin` 的 `[Argument]` 开关：

| 开关 | 默认 | 作用 |
|---|---|---|
| `rewardSafe` | 开 | 保奖励优先；非开屏端点直接放行，域名拦截也自动放行 |
| `cleanAds` | 关 | 去广告脚本：广告位、信息流、福利页广告任务（**不动激励素材**，不影响领奖） |
| `killRewardAds` | 关 | 断掉激励广告素材与预拉取（= 广告完全不发，领奖会变 `amount=-1`） |
| `blockAdDomains` | 关 | 广告/归因域名拦截（MITM + `http-request` 脚本，HTTP/3 可能漏过） |
| `settingsClean` | 关 | 设置层净化；不要与 `rewardSafe` 同开 |
| `debugLog` | 关 | 只读日志，可与保奖励同开 |
| `logTaskTitles` | 关 | 只读日志里额外打印任务标题（定位【听抖音】等入口用） |
| `splashClean` | 开 | 清理开屏品牌广告 |
| `hideDouyinTab` | 关 | 隐藏福利页【听抖音】tab/任务条目（按标题匹配，保守） |
| `hideDouyinEntry` | 关 | 关掉设置层的 `anchor_luna_to_douyin*` → 汽水里的【听抖音】入口不再出现（可与保奖励同开） |
| `blockSplashAd` | 关 | 拦掉穿山甲开屏广告请求（`ads5-*.zijieapi.com/api/ad/splash/`），不影响激励广告 |
| `dailyReminder` | 关 | 每日领取提醒：`reminderCron`（默认每天 20:30）定时检查，当天没打开福利页就发 Loon 通知；打开过则免打扰 |
| `reminderCron` | `30 20 * * *` | 提醒时间（五段 cron，分 时 日 月 周） |

推荐用法：

- **正常领奖励（默认）**：`rewardSafe=开`，其余保持默认；只清开屏品牌广告。
- **排障**：在保奖励基础上打开 `debugLog`，日志搜 `[soda-reward]`。
- **去广告**：`rewardSafe=关`、`cleanAds=开`、`splashClean=开`。
- **强力去广告**：再加 `blockAdDomains=开`（需要 `[MITM]` 里的 5 个广告域名；若激励广告因此播不了，注释掉那 5 个域名即可）。
- **隐藏听抖音**：`hideDouyinTab=开`（可与 `rewardSafe` 同开，只删带“抖音”的条目）。
- **每日提醒**：`dailyReminder=开`，`reminderCron` 自定义时间。ON 状态下打开福利页会打当天卡（`/luna/treasure/task/page` 命中即写存储，`.welfare-stamp` 脚本不读不改响应体）；到点未打卡才发通知。
- **100% 域名拦截**（不依赖 MITM、能挡 HTTP/3）：关闭 `rewardSafe`，手动取消 `soda.plugin` 里 `[Rule]` 段的 5 行 `DOMAIN` 注释；严格模式会阻断激励广告，不能领奖励。

`douyin.plugin` 的 `[Argument]` 开关：

| 开关 | 默认 | 作用 |
|---|---|---|
| `treasureMinimal` | 开 | 福利页只保留【攒时长 听歌不中断】 |
| `cleanFeedAds` | 关 | 清掉信息流/广告位广告容器（**不影响激励奖励**） |
| `killRewardAds` | 关 | 断掉激励广告素材与预拉取（= 广告完全不发，奖励也没了） |
| `cleanUpsell` | 关 | 删商业化弹窗、逛商城弹窗、汽水音乐节（演出）列表 |
| `blockAdDomains` | 关 | 广告域名拦截（MITM + `http-request` 脚本） |
| `cleanActivity` | 关 | 把 polaris 活动配置里的汽水音乐节（演出）与抖音运营活动置为不展示 |
| `debugLog` | 关 | 只读日志，前缀 `[douyin-reward]`（含穿山甲广告配置、领奖回调、广告耗时实测） |
| `dailyReminder` | 关 | 每日领取提醒：`reminderCron`（默认每天 20:30）定时检查，当天没打开福利页就发 Loon 通知；打开过则免打扰 |
| `reminderCron` | `30 20 * * *` | 提醒时间（五段 cron，分 时 日 月 周） |

> 激励广告 30 秒是硬成本（服务端按 `valid_duration` 校验真实观看时长），本仓库不做“改短时长照常领奖”；
> 也**不做“自动领取 / 自动看广告”**——原因在请求结构和证据层（2026-10-22 复核）：
> `luna/advert/incentive/done` 请求带 59 个头，其中 `x-argus` / `x-gorgon` / `x-ladon` / `x-medusa`
> 是 App 内安全 SDK 逐请求生成的设备级签名，`bd-ticket-guard-*` 是证书绑定凭证，脚本无法生成；
> `time_token` 只有真实完播才由穿山甲签发；`x-luna-is-background-req` 头会如实标注“App 是否在前台”，
> 后台代领天然可识别。cron 只能发通知/HTTP，驱动不了 App 内的播放与点击——自动化领取在 MITM 层没有实现面。
> 能省的是**等待里的空转**：v0.2.0 起 `cleanAds` 拆成 `cleanFeedAds` / `killRewardAds`，
> 默认两者都关，`incentive/config` 的 `preload=true` + `vids[]` 预拉取列表会完整保留，
> 第一次广告也能秒开。

安装注意：

- 一个 App 只装 `soda.plugin`；旧的 `SodaClean` / `SodaClean-Reward` / `-Debug` / `-Settings` 不要再装，已合并进本插件。
- 只装单个 `.plugin` 文件不够，必须同时能访问同级的 `scripts/`；更新时把 `plugins/soda/scripts/` 一起覆盖。
- App 插件里的 `[Argument]` **不能条件控制 `[Rule]`**，所以 soda 的域名拦截用脚本实现（`blockAdDomains`）；它依赖 MITM，HTTP/3(QUIC) 请求可能漏过。
- `[MITM]` 是静态配置：本插件声明 `api.qishui.com` + `conf.qishui.com` + 5 个广告域名。即使 `blockAdDomains` 关闭，这些域名也会被解密；如果激励广告因此播不了（证书固定），注释掉那 5 个广告域名即可。
- 如果 MITM 后 App 断网，先停用 `[Rewrite]` / `[Script]` / `[MITM]`，退回原版流程。

首次发布（如果还没有 git 仓库）：

```bash
git init
git add .
git commit -m "Loon plugins: soda"
git branch -M main
git remote add origin https://github.com/AshNail/plugins.git
git push -u origin main
```

---

## 部署到 GitHub（必看：脚本漏传 = 插件完全无效）

插件里的 `script-path=scripts/xxx.min.js` 是**相对路径**，Loon 会在插件同目录找脚本。
少传一个 `.min.js`，对应功能就**静默失效**（插件照常加载、界面照常显示，就是没效果）。

要上传的文件一共 **15 个**（其余文件不用传；`daily-reminder` / `welfare-stamp` 是每日提醒功能的配对脚本，不要漏）：

```text
plugins/soda/soda.plugin
plugins/soda/scripts/sanitize.min.js
plugins/soda/scripts/settings.min.js
plugins/soda/scripts/reward-observe.min.js
plugins/soda/scripts/splash-ad.min.js
plugins/soda/scripts/block-domains.min.js
plugins/soda/scripts/daily-reminder.min.js
plugins/soda/scripts/welfare-stamp.min.js
plugins/douyin/douyin.plugin
plugins/douyin/scripts/treasure.min.js
plugins/douyin/scripts/clean.min.js
plugins/douyin/scripts/observe.min.js
plugins/douyin/scripts/block-domains.min.js
plugins/douyin/scripts/daily-reminder.min.js
plugins/douyin/scripts/welfare-stamp.min.js
```

广告插件只需额外上传一个文件（没有 scripts）：

```text
plugins/ads/ads.plugin
```

旧的 `plugins/ads/ads-httpdns.plugin`、`ads-measurement.plugin`、`ads-strict.plugin` 不要上传；它们已合并进 `ads.plugin`。

上传完跑一次核对（会逐个文件比字节数和 SHA，并打印远端/本地版本号）：

```bash
python3 tools/check-remote.py
```

输出 `✓ 远端与本地完全一致` 才算传完；不一致的项会逐行列出来，照着传即可。

想知道"到底要传哪些、删哪些"，直接问工具：

```bash
python3 tools/check-remote.py --list
```

输出分四段：**A 必须覆盖/新增**（Loon 生效所需）、**B 已一致不用动**、
**C 建议从远端删除**（本地已移除的无用文件）、**D 可选同步源码与文档**。

### 一键发布（不想手动拖拽就用这个）

```bash
# 1) 用有写权限的账号登录
gh auth login --hostname github.com --git-protocol https

# 2) 先看计划
python3 tools/publish.py --with-source --dry-run

# 3) 确认后执行（覆盖变更文件 + 删除废弃文件 + 结束自动核对）
python3 tools/publish.py --with-source --yes
```

`publish.py` 以本地为准对齐远端：只动 `plugins/` 里插件真正引用的脚本 + 插件本身，
远端多余的自动删掉；`--with-source`（推荐）可连 `src/`、`docs/` 与 README 一起同步。
需要 PAT 时用 `export GH_TOKEN=ghp_xxx`。

> 特别注意：v2.4.0 / v0.5.0 起脚本会**自己解 gzip 响应体**。抖音/汽水的接口回包全是
> `content-encoding: gzip`，旧版脚本拿到压缩串会 `JSON.parse` 失败 → 表现为“清理模块全都没生效”。
> 所以**必须整体覆盖 scripts/ 目录**，只换 `.plugin` 没用。

重装/更新后的自检照单走：`docs/device-checklist.md`
（发布 → Loon 导入 → 冒烟 → 【听抖音】字段抓取 → 领奖复测 → 提醒验证 → QUIC 判读 → 回传清单）。
字段定位与 v2.6.1 升级预案：`docs/listen-douyin-field-kit.md`（含日志粘贴解析器 `tools/parse-task-titles.py`）。

## 构建与检查

```bash
npm ci
npm run build       # src/common 家族展开 -> src/{soda,douyin}/*.js -> plugins/*/scripts/*.min.js
npm run build:ads   # src/ads/domains.json -> plugins/ads/ads.plugin
npm run audit:ads   # 拉取上游清单，输出覆盖率/缺口（只读）
npm run lint        # 插件结构、正则、脚本引用、压缩脚本语法、ads 数据一致性
npm run check       # build + build:ads + lint + 源码/压缩版测试
```

单独跑测试：

```bash
npm run test:src    # 只测源码
npm run test:dist   # 只测压缩版
npm test            # 源码 + 压缩版都跑
```

当前测试规模：20 套脚本、510 条断言；源码与压缩版各跑一遍，共 **40 个套件 / 1020 条断言**。

---

## 新增插件族

以后加新 App 的插件，不需要改构建脚本：

1. 新建 `src/<family>/<name>.js`；
2. 新建 `plugins/<family>/<Name>.plugin`，脚本行写 `script-path=scripts/<name>.min.js`；
3. 运行 `npm run build`，自动生成 `plugins/<family>/scripts/<name>.min.js`；
4. 在 `tests/` 加对应测试，并更新本 README 的插件表。

如果新家族用到共享脚本（广告域名拦截 / 每日提醒 / 打卡），在 `src/common/families.json` 里为它加一组参数（`logTag` / `appName` / `notifyBody` / `rewardSafeDefault`），并同步给 lint 的对应家族校验补好 `[MITM]` 名单；构建会自动把 `src/common/*.js` 展开到该家族。

`ads` 是例外：它没有 JS 源码，数据源是 `src/ads/domains.json`，用 `npm run build:ads` 生成单插件 `plugins/ads/ads.plugin`（`[General]` + `[Rule]` + `[Host]`）；新增广告平台域时不要改生成物。

示例：

```text
src/example/clean.js
plugins/example/Example.plugin      # script-path=scripts/clean.min.js
plugins/example/scripts/clean.min.js
```

发布时保持 `plugins/<family>/` 整个目录完整；Loon 会按插件 URL 的相对位置取脚本。

---

## 更新与版本

- 改行为或脚本后，同步修改 `.plugin` 的 `#!version=`；
- 运行 `npm run build` 重新生成压缩脚本；
- 提交时同时提交 `src/` 和 `plugins/`（压缩脚本需要入库，GitHub Pages 才能直接提供）；
- Loon 重新导入插件或刷新远程插件即可获取新版本。

---

## 边界

本项目只做网络层广告过滤与激励链路保活，不做广告欺诈：

- 不缩短广告时长；
- 不伪造 SDK 完成回调；
- 不重复领取奖励；
- 不在未看完广告时调用发奖接口；
- 不绕过 `validate_reward` / `valid_duration` / 服务端风控。

`ads` 单插件只做网络层广告域/DNS 拦截，不修改 App 数据、不伪造发奖；它会同时拦掉激励广告，这是“去广告”与“保奖励”的固有权衡，不是 bug。

仅供个人设备上的网络管理与广告过滤研究，请遵守当地法律和 App 用户协议。