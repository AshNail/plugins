# 文档索引

本页按 **Loon 配置段落 → 使用场景 → 验证方式** 组织文档，避免在多个页面之间来回找。

## 先读

| 文档 | 用途 |
|---|---|
| [项目 README](../README.md) | 项目结构、Loon 段落映射、插件目录、构建与验证入口 |
| [Loon 原生优先](loon-native-first.md) | 为什么优先 `[Host]`/`[Rule]`，脚本与 MITM 的边界 |
| [Loon 全功能清单](loon-feature-checklist.md) | 以 Loon 官方能力为索引的仓库落地清单 |
| [最大化配置](loon-max-config.md) | `configs/loon.conf` 的基线围栏与插件外能力台账 |
| [分流 / Host / ASN](loon-routing-host-asn.md) | 规则顺序、Host Map、ASN 与代理组配方 |

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
| [旁路审计](bypass-audit.md) | “拦了”不等于“拦住”：DNS/HTTPDNS/DoH 旁路与红线 |
| [Loon 能力覆盖](loon-coverage.md) | 已用/可用未用/不适用能力盘点 |
| [App 插件覆盖率](app-coverage.md) | App 级覆盖矩阵（生成物） |
| [仓库规模](repo-metrics.md) | 插件、规则、脚本与文档规模（生成物） |

## 运行时与真机

| 文档 | 用途 |
|---|---|
| [真机验证清单](device-checklist.md) | 重装/更新后按单走的分段验证 |
| [多端支持矩阵](platform-support.md) | iOS / iPadOS / macOS / tvOS 的插件声明、推荐子集与已知问题 |
| [听抖音字段工具包](listen-douyin-field-kit.md) | 【听抖音】入口字段定位与回传流程 |
| [测试套件说明](../tests/README.md) | Node 回归套件、断言分布、lint 与配置门禁 |

## 配置与产物

| 文件 | 用途 |
|---|---|
| [configs/loon.conf](../configs/loon.conf) | 全功能主配置；公开、无节点/CA/凭据 |
| [examples/loon.conf](../examples/loon.conf) | 最小公开配置基线 |
| [examples/loon-routing.conf](../examples/loon-routing.conf) | 分流/Host/ASN 顺序示例 |
| [plugins/ads/README.md](../plugins/ads/README.md) | 全局广告底座 |
| [plugins/soda/README.md](../plugins/soda/README.md) | 汽水音乐唯一插件 |
| [plugins/douyin/README.md](../plugins/douyin/README.md) | 抖音唯一插件 |

## 生成物

以下文件由构建/审计器生成，不要手改：

- `plugins/*/*.plugin`、`plugins/*/scripts/*.min.js`
- `plugins/*/README.md`（`src/apps/*.json` 对应的 App 插件）
- `docs/app-coverage.md`、`docs/repo-metrics.md`

改源后执行 `npm run build`；提交前执行 `npm run check`。
