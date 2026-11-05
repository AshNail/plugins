# 文档索引

本页按 **Loon 配置段落 → 使用场景 → 验证方式** 组织文档，避免在多个页面之间来回找。

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
| [规则有效率](rule-effectiveness.md) | “写了”不等于“生效”：前提、MITM、正则面审计 |
| [起点官网 Web 资源](qidian-web-resources.md) | 首页实际字节、第三方推广/统计与可选拦截清单 |
| [TG@Nzmgs 上游研究](nzmgs-upstream.md) | QX 脚本源的可移植域、明确排除项与验证边界 |
| [网易云与镜像源研究](netease-mirror-sources.md) | 网易云模块、可莉 GitHub 镜像与 Jsforbaby 合规边界 |
| [可莉迁移对照](kelee-migration.md) | 可莉插件规则到自研原生实现的逐条迁移记录 |
| [可莉清单](fkikelee-inventory.md) | 上游可莉规则清单与裁剪口径 |
| [旁路审计](bypass-audit.md) | “拦了”不等于“拦住”：DNS/HTTPDNS/DoH 旁路与红线 |
| [Loon 能力覆盖](loon-coverage.md) | 已用/可用未用/不适用能力盘点 |
| [App 插件覆盖率](app-coverage.md) | App 级覆盖矩阵（生成物） |
| [仓库规模](repo-metrics.md) | 插件、规则、脚本与文档规模（生成物） |

## 运行时与真机

| 文档 | 用途 |
|---|---|
| [真机验证清单](device-checklist.md) | 重装/更新后按单走的分段验证 |
| [听抖音字段工具包](listen-douyin-field-kit.md) | 【听抖音】入口字段定位与回传流程 |
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
