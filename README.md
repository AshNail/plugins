[![一键导入 Loon 全功能配置](https://img.shields.io/badge/Loon-一键导入全功能配置-blue?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?sub=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fconfigs%2Floon.conf)

# AshNail Loon Plugins

以 **Loon 原生能力优先** 的个人插件与全功能配置库：能用 `[Host]` / `[Rule]` 解决的不用脚本；需要脚本时只做响应裁剪与按路径拦截，不伪造发奖、不接管登录/支付/风控。

- 全功能配置：`configs/loon.conf`
- 单插件：`plugins/<name>/<name>.plugin`
- 文档入口：[docs/INDEX.md](docs/INDEX.md)
- 真机检查表：[docs/device-checklist.md](docs/device-checklist.md)

## 快速开始

1. 全功能配置：点击顶部徽章导入 `configs/loon.conf`，按注释替换节点/订阅后再启用。
2. 单个 App：进入对应插件的 README，点击 `一键导入 x.plugin`。
3. 首次使用或更新后：按 [device-checklist](docs/device-checklist.md) 做一轮冒烟验证。

版本要求：脚本与插件语法以 **Loon 3.5.1(983)+** 为基线；`ads.plugin` 的 `DOMAIN-WILDCARD` 层要求 **3.5.2(996)+**。具体以各插件文件头 `#!loon_version` 为准。

## 项目结构

| 目录 | 职责 |
|---|---|
| `configs/` | 全功能 Loon 主配置，包含 `[General]` / `[Host]` / `[Rule]` / `[Rewrite]` / `[Script]` / `[MITM]` / `[Plugin]` |
| `examples/` | 最小配置与分流/Host/ASN 示例，供对照和门禁校验 |
| `plugins/` | 可导入产物：`.plugin`、压缩脚本 `scripts/*.min.js`、每个插件的 README |
| `src/` | 单一真源：`src/apps/*.json`（App 插件定义）、`src/args/*.json`（开关 schema）、`src/ads/domains.json`、`src/common/`、`src/<family>/` |
| `tools/` | 构建器与审计器：参数生成、压缩、覆盖率/有效性/红线/分流门禁 |
| `tests/` | Node `vm` 回归套件、真实 HAR fixtures、插件结构 lint |
| `docs/` | 架构、策略、审计、真机检查、路由/Host/ASN 手册 |
| `types/` | Loon 运行时全局声明（TypeScript 检查用） |

## Loon 段落映射

| Loon 段落 | 本仓库位置 | 用途 |
|---|---|---|
| `[General]` | `configs/loon.conf`、`plugins/ads/ads.plugin` | DNS、DoH、IPv6、传输层参数 |
| `[Host]` | `plugins/*/*.plugin` | 广告/遥测 DNS 黑洞，零证书、零脚本 |
| `[Rule]` | `configs/loon.conf`、插件 | 域名/端口/IP 分流与 REJECT |
| `[Rewrite]` | `configs/loon.conf`、插件 | 请求/响应改写，`reject_dict` 等原生 Action |
| `[Script]` | `plugins/*/*.plugin` | 新版 `script("...")`，按 `enable`/条件绑定 |
| `[MitM]` | `plugins/*/*.plugin`、主配置 | 仅对需要解密的目标域声明；插件默认零证书 |
| `[Plugin]` | `configs/loon.conf` | 插件清单与启用顺序 |

> Loon 段落名大小写不敏感。官方文档写作 `[MitM]`，本仓库历史插件统一写作 `[MITM]`，两者等价；脚本/规则内容不受影响。

官方参考：

- 插件与新版 Script：https://nsloon.app/docs/Plugin/
- 新版 Script 语法：https://nsloon.app/docs/Script/script_v2
- 新版 Rewrite 语法：https://nsloon.app/docs/Rewrite/rewrite_v2
- 官方转换器：https://nsloon.app/script-converter 、https://nsloon.app/rewrite-converter

## 插件目录

### 全局层

| 插件 | 作用 |
|---|---|
| [ads](plugins/ads/README.md) | DNS/HTTPDNS/DoH 广告与防绕过底座；零证书、零脚本 |
| [banks](plugins/banks/README.md) | 六款银行 App 的遥测/自有广告瘦身聚合层 |

### App 唯一插件

| 插件 | 作用 |
|---|---|
| [soda](plugins/soda/README.md) | 汽水音乐：默认去广告 + 保奖励，路径级拦截 |
| [douyin](plugins/douyin/README.md) | 抖音：默认去广告 + 保奖励，福利任务保留 |
| [qidian](plugins/qidian/README.md) | 起点读书：穿山甲/优量汇 + 自有广告统计 + 阅读热源上报 |
| [jd](plugins/jd/README.md) | 京东：自建广告交易/点击监测域 |
| [meituan](plugins/meituan/README.md) | 美团/点评：第三方变现与自建广告端点 |
| [xianyu](plugins/xianyu/README.md) | 闲鱼：同域 mtop 广告的能力边界与可选增强 |
| [wechat](plugins/wechat/README.md) | 微信：广点通/优量汇素材与广告位主机 |
| [instagram](plugins/instagram/README.md) | Instagram：像素、VAST 与遥测瘦身 |
| [x](plugins/x/README.md) | X：广告像素、嵌入与广告后台域 |
| [mijia](plugins/mijia/README.md) | 米家：小米统一广告平台层 |
| [mba-dashi](plugins/mba-dashi/README.md) | MBA 大师：穿山甲/优量汇广告位 |
| [ruankao-tong](plugins/ruankao-tong/README.md) | 软考通：穿山甲/优量汇广告位 |
| [zhihuifangdong](plugins/zhihuifangdong/README.md) | 智慧房东：多广告网络聚合 |
| [bubei-danci](plugins/bubei-danci/README.md) | 不背单词：无广告联盟，只裁跟踪 |

> `soda` 与 `douyin` 是共享 `src/common/` 的家族插件；其余 App 插件由 `src/apps/*.json` 生成。

## 源与产物

- **只改 `src/`**：`plugins/*/*.plugin`、`plugins/*/scripts/*.min.js`、App 插件 README、`docs/app-coverage.md`、`docs/repo-metrics.md` 都由构建器生成。
- 共享脚本在 `src/common/`，按 `src/common/families.json` 注入 `src/soda` / `src/douyin`；不要直接改生成副本。
- 开关以 `src/args/*.json` 为单一真源，生成 `[Argument]`、README 表和状态摘要。
- 广告域清单以 `src/ads/domains.json` 为单一真源，`plugins/ads/ads.plugin` 由构建器生成。

## 构建与验证

```bash
npm ci
python3 -m pip install -r requirements-dev.txt
npm run build
npm run check
```

`npm run check` 依次执行：参数同步、脚本压缩、广告/App 构建、README 生成、TypeScript、oxlint、ruff、插件结构 lint、Loon token/配置/分流/覆盖率/有效性审计、App 覆盖率与 Node 回归套件。

常用单项：

```bash
npm run test:src       # 源码脚本回归
npm run test:dist      # 压缩脚本回归
npm run lint           # 插件结构与 Loon 语法面
npm run check:config   # 主配置 / Host / Rule / MITM / 分流示例
npm run coverage       # Loon 能力覆盖
npm run effective      # 规则有效性审计
```

当前基线：54 个测试套件 / 1760 条断言；详细断言分布见 [tests/README.md](tests/README.md)。

## 设计边界

- 不内置 CA、订阅、节点或代理凭据；`configs/loon.conf` 可直接公开。
- 不伪造签到、领取、播放完成或发奖；需要设备签名的请求不在插件层代做。
- 支付、登录、风控、证书固定域默认不碰；需要 MITM 的增强层必须显式启用。
- 去广告优先 DNS/`[Host]`；同域广告用路径级 Rewrite，并保留激励/发奖路径。
- 任何“已拦截”声明都要有规则、样本或审计工具支撑，见 [rule-effectiveness](docs/rule-effectiveness.md) 与 [bypass-audit](docs/bypass-audit.md)。

## 文档

完整索引见 [docs/INDEX.md](docs/INDEX.md)。建议阅读顺序：

1. [Loon 原生优先](docs/loon-native-first.md)
2. [Loon 全功能清单](docs/loon-feature-checklist.md)
3. [最大化配置](docs/loon-max-config.md)
4. [分流/Host/ASN](docs/loon-routing-host-asn.md)
5. [规则有效性](docs/rule-effectiveness.md) / [旁路审计](docs/bypass-audit.md)
6. [真机验证清单](docs/device-checklist.md)
