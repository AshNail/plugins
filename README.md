# Loon 插件仓库

> 仓库名：`loon-plugins`  
> GitHub：`https://github.com/AshNail/plugins`

个人 Loon 插件集合，按 **插件族（family）** 组织。每个插件族自包含：`.plugin` 文件与压缩后的 `scripts/` 放在同一目录，方便 Loon 通过相对路径加载脚本。

当前插件族：**汽水音乐（Soda）**。详细逆向说明、字段取证和使用边界见 [`plugins/soda/README.md`](plugins/soda/README.md)。

---

## 插件列表

| 插件 | 版本 | 用途 | 兼容性 |
|---|---:|---|---|
| `SodaClean-Unified.plugin` | 0.1.0 | 单插件多开关：默认保奖励；可选去广告脚本、设置层、只读日志；不含域名拦截 | 实验：推荐先试；完整域名拦截仍需主插件 |
| `SodaClean.plugin` | 1.5.2 | 去广告优先：域名拦截 + 字段级响应裁剪，摘除广告任务/广告位/信息流广告 | 不要与保奖励插件同时启用；设置插件可选搭配（实验） |
| `SodaClean-Reward.plugin` | 0.2.3 | 保奖励优先：只清开屏品牌广告，保留激励广告、奖励任务、发奖链路；不拦任何域名 | 不要与主插件/设置插件同时启用；可与只读观测插件搭配 |
| `SodaClean-Reward-Debug.plugin` | 0.2.2 | 只读观测：记录 20 个激励/任务/入口端点，不修改响应 | 与保奖励插件搭配排障 |
| `SodaClean-Settings.plugin` | 0.1.2 | 实验：通过 TTKitchen 设置层清广告配置 | 可与主插件搭配；不要与保奖励插件同时启用 |

> 保奖励模式只保证“完整看完广告后正常领奖”，不提供跳过广告、伪造回调、重复领奖或未看完就发奖。

---

## 仓库结构

```text
.
├── plugins/
│   └── soda/
│       ├── README.md                  # 汽水音乐详细说明
│       ├── SodaClean-Unified.plugin
│       ├── SodaClean.plugin
│       ├── SodaClean-Reward.plugin
│       ├── SodaClean-Reward-Debug.plugin
│       ├── SodaClean-Settings.plugin
│       └── scripts/
│           ├── sanitize.min.js
│           ├── settings.min.js
│           ├── request.min.js
│           ├── reward-observe.min.js
│           └── diag.min.js
├── src/
│   └── soda/                          # 可读源码（不要直接部署）
│       ├── sanitize.js
│       ├── settings.js
│       ├── request.js
│       ├── reward-observe.js
│       └── diag.js
├── tests/                             # 脚本层回归测试
├── tools/build.js                     # 源码 -> 压缩脚本
├── .github/workflows/check.yml        # CI：build + lint + 源码/压缩版测试
├── package.json
├── package-lock.json
├── .nojekyll
└── .gitignore
```

约定：

- **`src/` 是源码**，修改脚本只改这里；
- **`plugins/` 是部署目录**，`*.min.js` 由 `tools/build.js` 用 terser 实际压缩生成，不是只改后缀；
- `.plugin` 里的 `script-path=scripts/xxx.min.js` 是相对路径，所以 `.plugin` 和 `scripts/` 必须保持同级；
- 构建脚本会自动发现 `src/<family>/` 下的所有 `.js`，并输出到 `plugins/<family>/scripts/`；
- 压缩会去掉注释和空白、缩短局部/顶层变量名；`AGGRESSIVE` / `DRY_RUN` 等开关名保留，便于排查。

当前 Soda 脚本压缩结果：

| 源码 | 源码大小 | 压缩版 | 压缩后 |
|---|---:|---|---:|
| `src/soda/sanitize.js` | 18,639 B | `plugins/soda/scripts/sanitize.min.js` | 8,720 B |
| `src/soda/settings.js` | 15,367 B | `plugins/soda/scripts/settings.min.js` | 5,606 B |
| `src/soda/reward-observe.js` | 16,472 B | `plugins/soda/scripts/reward-observe.min.js` | 9,632 B |
| `src/soda/request.js` | 3,401 B | `plugins/soda/scripts/request.min.js` | 1,195 B |
| `src/soda/diag.js` | 2,996 B | `plugins/soda/scripts/diag.min.js` | 1,320 B |

合计 **56,875 B → 26,473 B（约 -53.5%）**。每个 `.min.js` 只有 2 行：一行来源标记 + 一行压缩代码（源码为 95–493 行）；构建和 lint 都会检查“压缩后必须比源码小、行数不超过 5 行”。Loon 只加载 `plugins/soda/scripts/*.min.js`；原始代码仍在 `src/soda/`。

---

## 安装

把仓库推到 `https://github.com/AshNail/plugins` 后，`Settings → Pages → Deploy from a branch`，Branch 选 `main`，Folder 选 `/ (root)`。不需要 `index.html`，根地址 404 是正常的，直接访问插件文件即可。

统一开关版（推荐先试这个，默认保奖励）：

```text
https://ashnail.github.io/plugins/plugins/soda/SodaClean-Unified.plugin
```

Loon 导入链接：

```text
loon://import?plugin=https%3A%2F%2Fashnail.github.io%2Fplugins%2Fplugins%2Fsoda%2FSodaClean-Unified.plugin
```

稳定保奖励版（不想用实验开关时）：

```text
https://ashnail.github.io/plugins/plugins/soda/SodaClean-Reward.plugin
```

其他插件把文件名替换即可：

| 插件 | 文件 |
|---|---|
| 统一开关版 | `plugins/soda/SodaClean-Unified.plugin` |
| 主插件（完整域名拦截） | `plugins/soda/SodaClean.plugin` |
| 保奖励稳定版 | `plugins/soda/SodaClean-Reward.plugin` |
| 只读观测 | `plugins/soda/SodaClean-Reward-Debug.plugin` |
| 设置层实验 | `plugins/soda/SodaClean-Settings.plugin` |

统一开关版的 `[Argument]`：

| 开关 | 默认 | 作用 |
|---|---|---|
| `rewardSafe` | 开 | 保奖励优先；非开屏端点直接放行 |
| `cleanAds` | 关 | 去广告脚本：广告配置、信息流、福利页广告任务 |
| `settingsClean` | 关 | 设置层净化；不要与 `rewardSafe` 同开 |
| `debugLog` | 关 | 只读日志，可与保奖励同开 |
| `splashClean` | 开 | 清理开屏品牌广告 |

安装注意：

- 只装单个 `.plugin` 文件不够，必须同时能访问同级的 `scripts/`；
- 统一版**不包含域名拦截**：Loon 的 `[Rule]` 不能按开关关闭。需要完整去广告域名拦截时用主插件，但主插件不能和保奖励同开；
- 统一版默认 `rewardSafe=true`；如果同时打开 `cleanAds`，脚本会保护非开屏端点，但仍建议只开一种模式；
- 保奖励/统一版只 MITM `api.qishui.com`；设置层需要 `conf.qishui.com`；
- 如果 MITM 后 App 断网，先停用 `[Rewrite]` / `[Script]` / `[MITM]`，退回原版流程。

首次发布（如果还没有 git 仓库）：

```bash
git init
git add .
git commit -m "Loon plugins: SodaClean"
git branch -M main
git remote add origin https://github.com/AshNail/plugins.git
git push -u origin main
```

---

## 构建与检查

```bash
npm ci
npm run build       # src/soda/*.js -> plugins/soda/scripts/*.min.js
npm run lint        # 插件结构、正则、脚本引用、压缩脚本语法
npm run check       # build + lint + 源码/压缩版测试
```

单独跑测试：

```bash
npm run test:src    # 只测源码
npm run test:dist   # 只测压缩版
npm test            # 源码 + 压缩版都跑
```

当前测试规模：11 套脚本、290 条断言；源码与压缩版各跑一遍，共 **22 个套件 / 580 条断言**。

---

## 新增插件族

以后加新 App 的插件，不需要改构建脚本：

1. 新建 `src/<family>/<name>.js`；
2. 新建 `plugins/<family>/<Name>.plugin`，脚本行写 `script-path=scripts/<name>.min.js`；
3. 运行 `npm run build`，自动生成 `plugins/<family>/scripts/<name>.min.js`；
4. 在 `tests/` 加对应测试，并更新本 README 的插件表。

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

仅供个人设备上的网络管理与广告过滤研究，请遵守当地法律和 App 用户协议。
