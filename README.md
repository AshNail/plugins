# Loon 插件仓库

> 仓库名：`loon-plugins`  
> GitHub：`https://github.com/AshNail/plugins`

个人 Loon 插件集合，按 **插件族（family）** 组织。每个插件族自包含：`.plugin` 文件与压缩后的 `scripts/` 放在同一目录，方便 Loon 通过相对路径加载脚本。

当前插件族：**汽水音乐（Soda）**。详细逆向说明、字段取证和使用边界见 [`plugins/soda/README.md`](plugins/soda/README.md)。

---

## 插件列表

| 插件 | 版本 | 用途 | 兼容性 |
|---|---:|---|---|
| `soda.plugin` | 2.1.0 | 汽水音乐唯一插件：保奖励 / 去广告脚本 / 广告域名拦截 / 设置层 / 只读日志 / 隐藏【听抖音】，全部用 `[Argument]` 开关控制 | 一个 App 只装这一个；域名拦截走 MITM+脚本，HTTP/3 可能漏过 |

> 一个 App 只保留一个 `.plugin`。旧的 `SodaClean` / `SodaClean-Reward` / `SodaClean-Reward-Debug` / `SodaClean-Settings` 独立插件已合并进 `soda.plugin`，不再单独部署；历史版本可在 git 历史中找回。

> 保奖励模式只保证“完整看完广告后正常领奖”，不提供跳过广告、伪造回调、重复领奖或未看完就发奖。

---

## 仓库结构

```text
.
├── plugins/
│   └── soda/
│       ├── README.md                  # 汽水音乐详细说明
│       ├── soda.plugin                # 唯一部署插件（聚合开关版）
│       └── scripts/
│           ├── sanitize.min.js
│           ├── settings.min.js
│           ├── request.min.js
│           ├── reward-observe.min.js
│           ├── block-domains.min.js
│           └── diag.min.js
├── src/
│   └── soda/                          # 可读源码（不要直接部署）
│       ├── sanitize.js
│       ├── settings.js
│       ├── request.js
│       ├── reward-observe.js
│       ├── block-domains.js
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
| `src/soda/sanitize.js` | 21,574 B | `plugins/soda/scripts/sanitize.min.js` | 9,708 B |
| `src/soda/settings.js` | 15,367 B | `plugins/soda/scripts/settings.min.js` | 5,606 B |
| `src/soda/reward-observe.js` | 16,472 B | `plugins/soda/scripts/reward-observe.min.js` | 9,632 B |
| `src/soda/block-domains.js` | 2,652 B | `plugins/soda/scripts/block-domains.min.js` | 820 B |
| `src/soda/request.js` | 3,401 B | `plugins/soda/scripts/request.min.js` | 1,195 B |
| `src/soda/diag.js` | 2,996 B | `plugins/soda/scripts/diag.min.js` | 1,320 B |

合计 **62,462 B → 28,281 B（约 -54.7%）**。每个 `.min.js` 只有 2 行：一行来源标记 + 一行压缩代码（源码为 72–575 行）；构建和 lint 都会检查“压缩后必须比源码小、行数不超过 5 行”。Loon 只加载 `plugins/soda/scripts/*.min.js`；原始代码仍在 `src/soda/`。

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

`soda.plugin` 的 `[Argument]` 开关：

| 开关 | 默认 | 作用 |
|---|---|---|
| `rewardSafe` | 开 | 保奖励优先；非开屏端点直接放行，域名拦截也自动放行 |
| `cleanAds` | 关 | 去广告脚本：广告配置、信息流、福利页广告任务 |
| `blockAdDomains` | 关 | 广告/归因域名拦截（MITM + `http-request` 脚本，HTTP/3 可能漏过） |
| `settingsClean` | 关 | 设置层净化；不要与 `rewardSafe` 同开 |
| `debugLog` | 关 | 只读日志，可与保奖励同开 |
| `splashClean` | 开 | 清理开屏品牌广告 |
| `hideDouyinTab` | 关 | 隐藏福利页【听抖音】tab/任务条目 |

推荐用法：

- **正常领奖励（默认）**：`rewardSafe=开`，其余保持默认；只清开屏品牌广告。
- **排障**：在保奖励基础上打开 `debugLog`，日志搜 `[soda-reward]`。
- **去广告**：`rewardSafe=关`、`cleanAds=开`、`splashClean=开`。
- **强力去广告**：再加 `blockAdDomains=开`（需要 `[MITM]` 里的 5 个广告域名；若激励广告因此播不了，注释掉那 5 个域名即可）。
- **隐藏听抖音**：`hideDouyinTab=开`（可与 `rewardSafe` 同开，只删带“抖音”的条目）。
- **100% 域名拦截**（不依赖 MITM、能挡 HTTP/3）：关闭 `rewardSafe`，手动取消 `soda.plugin` 里 `[Rule]` 段的 5 行 `DOMAIN` 注释；严格模式会阻断激励广告，不能领奖励。

安装注意：

- 一个 App 只装 `soda.plugin`；旧的 `SodaClean` / `SodaClean-Reward` / `-Debug` / `-Settings` 不要再装，已合并进本插件。
- 只装单个 `.plugin` 文件不够，必须同时能访问同级的 `scripts/`；更新时把 `plugins/soda/scripts/` 一起覆盖。
- Loon 的 `[Rule]` **不能按开关关闭**，所以域名拦截用脚本实现（`blockAdDomains`）；它依赖 MITM，HTTP/3(QUIC) 请求可能漏过。
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

当前测试规模：12 套脚本、302 条断言；源码与压缩版各跑一遍，共 **24 个套件 / 604 条断言**。

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
