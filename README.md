# Loon 插件仓库

> 仓库名：`loon-plugins`  
> GitHub：`https://github.com/3kaiu/loon-plugins`

个人 Loon 插件集合，按 **插件族（family）** 组织。每个插件族自包含：`.plugin` 文件与压缩后的 `scripts/` 放在同一目录，方便 Loon 通过相对路径加载脚本。

当前插件族：**汽水音乐（Soda）**。详细逆向说明、字段取证和使用边界见 [`plugins/soda/README.md`](plugins/soda/README.md)。

---

## 插件列表

| 插件 | 版本 | 用途 | 兼容性 |
|---|---:|---|---|
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
| `src/soda/sanitize.js` | 18,084 B | `plugins/soda/scripts/sanitize.min.js` | 8,508 B |
| `src/soda/settings.js` | 14,987 B | `plugins/soda/scripts/settings.min.js` | 5,446 B |
| `src/soda/reward-observe.js` | 16,472 B | `plugins/soda/scripts/reward-observe.min.js` | 9,632 B |
| `src/soda/request.js` | 3,401 B | `plugins/soda/scripts/request.min.js` | 1,195 B |
| `src/soda/diag.js` | 2,996 B | `plugins/soda/scripts/diag.min.js` | 1,320 B |

合计 **55,940 B → 26,101 B（约 -53.3%）**。每个 `.min.js` 只有 2 行：一行来源标记 + 一行压缩代码（源码为 95–479 行）；构建和 lint 都会检查“压缩后必须比源码小、行数不超过 5 行”。Loon 只加载 `plugins/soda/scripts/*.min.js`；原始代码仍在 `src/soda/`。

---

## 安装

把仓库推到 `https://github.com/3kaiu/loon-plugins` 后，`Settings → Pages → Deploy from a branch`，Branch 选 `main`，Folder 选 `/ (root)`。不需要 `index.html`，根地址 404 是正常的，直接访问插件文件即可。

保奖励模式（推荐先装这个）：

```text
https://3kaiu.github.io/loon-plugins/plugins/soda/SodaClean-Reward.plugin
```

Loon 导入链接：

```text
loon://import?plugin=https%3A%2F%2F3kaiu.github.io%2Floon-plugins%2Fplugins%2Fsoda%2FSodaClean-Reward.plugin
```

其他插件把文件名替换即可：

| 插件 | 文件 |
|---|---|
| 主插件 | `plugins/soda/SodaClean.plugin` |
| 保奖励 | `plugins/soda/SodaClean-Reward.plugin` |
| 只读观测 | `plugins/soda/SodaClean-Reward-Debug.plugin` |
| 设置层实验 | `plugins/soda/SodaClean-Settings.plugin` |

安装注意：

- 只装单个 `.plugin` 文件不够，必须同时能访问同级的 `scripts/`；
- 保奖励插件不要与主插件/设置插件混用；主插件 + 设置插件可以组合，但设置插件是实验性的；
- 保奖励模式只 MITM `api.qishui.com`；设置插件需要单独 MITM `conf.qishui.com`；
- 如果 MITM 后 App 断网，先停用 `[Rewrite]` / `[Script]` / `[MITM]`，退回域名拦截或原版流程。

首次发布（如果还没有 git 仓库）：

```bash
git init
git add .
git commit -m "Loon plugins: SodaClean"
git branch -M main
git remote add origin https://github.com/3kaiu/loon-plugins.git
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

当前测试规模：10 套脚本、276 条断言；源码与压缩版各跑一遍，共 **20 个套件 / 552 条断言**。

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
