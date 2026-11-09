# 文档索引

本页按 **Loon 配置段落 → 使用场景 → 验证方式** 组织文档，避免在多个页面之间来回找。

> **CI 政策**：本仓库**没有** GitHub Actions / CI，远端不跑任何检查；`.github/` 已在 `.gitignore` 中禁止提交。所有质量门禁（build / lint / 54 套件测试 / 各审计 `--check`）都在**本地** `npm run check` 执行——发布前自行跑绿即可，不要依赖远端。

## 先读

| 文档 | 用途 |
|---|---|
| [项目 README](../README.md) | 插件列表与一键导入（徽章按钮） |
| [Loon 原生优先](loon-native-first.md) | 为什么优先 `[Host]`/`[Rule]`，脚本与 MITM 的边界 |
| [Loon 全功能清单](loon-feature-checklist.md) | 以 Loon 官方能力为索引的仓库落地清单 |
| [高级功能矩阵](advanced-features.md) | Mac 高级功能逐项结论、STUN/网关/插件版本兼容与回滚 |

官方参考：

- 插件与参数：https://nsloon.app/docs/Plugin/
- 新版 Script：https://nsloon.app/docs/Script/script_v2
- 新版 Rewrite：https://nsloon.app/docs/Rewrite/rewrite_v2
- MitM：https://nsloon.app/docs/MitM/
- Scheme：https://nsloon.app/docs/Scheme/

## 去广告策略与审计

| 文档 | 用途 |
|---|---|
| [按广告类型分类的去除策略](ad-type-strategy.md) | DNS、Host、路径 Rewrite、脚本裁剪的选型 |
| [三份外部去广告方案研判](ad-eradication-review.md) | 外部「七维根除」架构的逐条判定：已做到 / 做不到 / 写错了 / 漏了什么 |
| [规则有效率](rule-effectiveness.md) | “写了”不等于“生效”：前提、MITM、正则面审计 |
| [旁路审计](bypass-audit.md) | “拦了”不等于“拦住”：DNS/HTTPDNS/DoH 旁路与红线 |
| [Loon 能力覆盖](loon-coverage.md) | 已用/可用未用/不适用能力盘点 |
| [App 插件覆盖率](app-coverage.md) | App 级覆盖矩阵（生成物） |
| [仓库规模](repo-metrics.md) | 插件、规则、脚本与文档规模（生成物） |

## 运行时与真机

| 文档 | 用途 |
|---|---|
| [真机验证清单](device-checklist.md) | 重装/更新后按单走的分段验证 |
| [测试套件说明](../tests/README.md) | Node 回归套件、断言分布、lint 与配置门禁 |

## 插件入口

本仓库只分发独立插件（无主配置、无分流规则、无节点/订阅、无证书私钥），完整导入表见根 README。

| 文件 | 用途 |
|---|---|
| [plugins/ads/README.md](../plugins/ads/README.md) | 全局广告底座 |
| [plugins/soda/README.md](../plugins/soda/README.md) | 汽水音乐唯一插件 |
| [plugins/douyin/README.md](../plugins/douyin/README.md) | 抖音唯一插件 |

## 生成物

以下文件由构建/审计器生成，不要手改：

- `plugins/*/*.plugin`、`plugins/*/scripts/*.min.js`
- `plugins/*/README.md`（`src/apps/*.json` 对应的 App 插件）
- `docs/app-coverage.md`、`docs/repo-metrics.md`

改源后执行 `npm run build`；提交前执行 `npm run check`。

## 图标

`#!icon` 不手抄 URL。身份只记在 `src/icons.json`（bundleId / trackId / seller），
`tools/refresh-icons.py` 现场向 iTunes Lookup（钉 `country=CN`）取 `artworkUrl100`
并统一改写成 Apple 官方 CDN `is1-ssl.mzstatic.com` 的 `512x512bb.jpg`：

- `npm run icons`：离线报告当前差异；`npm run icons:write` 只写 `src/apps/*.json` 的
  `"icon"` 行与手写插件的 `#!icon=` 行，生成物交给 `npm run build`。
- `npm run check:icons`：在线取一遍并 HEAD 校验，漂移即红——artwork 路径里的
  `<hash>` 段随构建产物重分配，旧串会被回收（知乎踩过 404）。
- 例外表也住在 `src/icons.json` 的 `_exceptions`，lint 的图标门禁只认这张表。
