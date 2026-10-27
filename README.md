# Loon 插件仓库

> 仓库 [`AshNail/plugins`](https://github.com/AshNail/plugins) · soda/douyin 要求 **Loon 3.5.1(983)+**（gzip 响应解析需 **988+**）；`ads.plugin` 因 `DOMAIN-WILDCARD` 要求 **3.5.3(1008)+** · **无需 GitHub Pages**（Loon 以插件 URL 为基准解析同级 `scripts/`）

个人 Loon 插件集合，按「一个 App 一个插件」组织：汽水音乐（soda）、抖音（douyin）、广告平台拦截器（ads）。逆向说明、字段取证、使用边界都在各插件目录的 README 里。

## 一键导入

在 **iPhone / iPad 用 Safari** 打开本页，点按钮跳进 Loon；GitHub App / 微信内置浏览器可能拦截跳转，用 Safari 或复制备用链接。

<!-- Loon 官方通用链接（Universal Link，AASA: /openloon/*）；loon:// custom scheme 在网页上不可靠 -->

| 插件 | 版本 | 一句话用途 | 按钮 |
|---|---:|---|---|
| 汽水音乐 `soda.plugin` | 2.8.5 | 保奖励 + 去广告 + 广告域名拦截 + 开屏请求拦截 + 设置层 + 隐藏【听抖音】+ 每日提醒 + 状态自检看板（含 Loon 环境诊断），全部开关控制 | [![导入 soda](https://img.shields.io/badge/Loon-导入汽水音乐-blue?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fsoda%2Fsoda.plugin) |
| 抖音 `douyin.plugin` | 0.8.5 | 福利页精简 + 信息流广告清理 + 商业化弹窗清理 + 开屏请求拦截 + 状态自检看板（含 Loon 环境诊断，2026-10 真实 HAR 取证） | [![导入 douyin](https://img.shields.io/badge/Loon-导入抖音-black?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fdouyin%2Fdouyin.plugin) |
| 广告平台拦截器 `ads.plugin` | 2.6.0 | DNS 层全平台拦截 + DOMAIN-WILDCARD 广告子域通配 + 数字分片家族层 `[0-9]`(1008+) + HTTPDNS 防绕过(REJECT-DROP) + IP Rewrite(Build 1007+) + 公共 DoH/DoT 防泄漏；**零证书、零 MITM/脚本** | [![导入 ads](https://img.shields.io/badge/Loon-导入广告拦截器-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fads%2Fads.plugin) |

<details>
<summary>备用链接（网页按钮没反应时手动复制）</summary>

```text
# raw 直链（插件页 → + → URL 导入）
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/soda/soda.plugin
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/douyin/douyin.plugin
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/ads/ads.plugin

# loon:// scheme（复制到 Safari 地址栏打开）
loon://import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fsoda%2Fsoda.plugin
loon://import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fdouyin%2Fdouyin.plugin
loon://import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fads%2Fads.plugin
```

</details>

## 冲突与使用要点

- **⚠️ `ads.plugin` 与激励广告互斥**：它在 DNS 阶段拦掉穿山甲/优量汇/快手联盟，soda/douyin 的奖励任务会失败。**刷奖励时禁用 `ads.plugin`**，或只开 soda/douyin。
- **soda/douyin 的传输层常开、无开关**：`[Rule]` 对 `[MITM]` 域强制 QUIC→TCP 回退、`[MITM]` 开 `h2`。它们不拦业务流量，只保证脚本能看见流量；若某个版本因此连不上，删掉插件里对应那一行即可回滚。
- **一个 App 只装一个插件**；旧的 `SodaClean` 系列与 `ads-httpdns/ads-measurement/ads-strict` 已全部并入现插件，不要再装。
- soda/douyin 需要 **MITM**：导入后 Loon → 设置 → MITM → 生成证书 → 安装并信任；`ads.plugin` 不需要证书。
- 装完**完全退出并重开 App**；如果 MITM 后断网，先停用插件里的 `[Rewrite]/[Script]/[MITM]` 回滚，再看插件 README 的排查表。
- 本仓库保奖励只保证「完整看完广告后正常领奖」，不做跳广告/伪造回调/自动领取（`x-argus` 等设备级签名无法伪造，详见 douyin README）。

## 详细文档

| 插件 | 文档 | 内容 |
|---|---|---|
| soda | [`plugins/soda/README.md`](plugins/soda/README.md) | 全开关表、推荐用法、gzip 响应体兼容、耗时统计、部署细节 |
| douyin | [`plugins/douyin/README.md`](plugins/douyin/README.md) | 全开关表、HAR 取证证据、【听抖音】字段包、证书固定风险 |
| ads | [`plugins/ads/README.md`](plugins/ads/README.md) | 拦截分层、可选网关 IP 组、主配置加固片段、来源清单、FAQ |
| 全仓库 | [`docs/ad-type-strategy.md`](docs/ad-type-strategy.md) | **按广告类型分类的去除策略**：19 类广告 × 6 族，每类的线上特征、可用层与规则思路、覆盖档位、局限、**为什么提不了档**，附六种可复制写法 |
| 全仓库 | [`docs/loon-feature-checklist.md`](docs/loon-feature-checklist.md) | Loon 全功能清单：官方文档 30 页逐页核对（通用链接/General 全键/规则与 REJECT 变体/策略组/脚本五型/IP Rewrite）、真机取证队列、不采纳清单 |
| 全仓库 | [`docs/loon-coverage.md`](docs/loon-coverage.md) | Loon 能力覆盖与利用率（按功能轴，生成物） |
| 全仓库 | [`docs/rule-effectiveness.md`](docs/rule-effectiveness.md) | **规则有效率审计**：写了 ≠ 生效。逐条判定规则的生效前提（连接层 / 仅明文 / 需解密），存疑规则必须登记 waiver 与真机证伪方法（生成物） |
| 全仓库 | [`docs/bypass-audit.md`](docs/bypass-audit.md) | **旁路审计**：拦了 ≠ 拦住。枚举 17 条「广告请求绕开整个插件」的路径，四态封死判定 + 为什么停在这 + 真机证伪方法（生成物） |

---

## 开发者速查

```bash
npm ci
npm run build       # src/common 家族展开 → src/{soda,douyin}/*.js → plugins/*/scripts/*.min.js
npm run build:ads   # src/ads/domains.json → plugins/ads/ads.plugin
npm run audit:ads   # 上游清单覆盖率/缺口审计（只读）
npm run lint        # 结构/正则/脚本引用/安全边界/孤儿脚本/压缩语法/ads 数据一致性 + 四处名单一致
npm run check       # build + build:ads + lint + coverage + 全部测试（源码+压缩版）
npm run coverage    # Loon 能力覆盖/利用率报表（111 条能力，探测真实用法）
npm test            # 仅测试；26 套件 ×2 = 52 套件 / 1596 断言
```

仓库结构：

```text
plugins/<family>/<name>.plugin + scripts/*.min.js   # 部署物（相对路径可被 Loon 加载）
src/<family>/*.js                                   # 可读源码（common 三件为生成物，勿手改）
src/common/  block-domains / daily-reminder / welfare-stamp / splash-ad / status + families.json   # soda/douyin 单一来源
src/ads/     domains.json + protected-roots.json    # ads 单插件数据源
tests/ tools/{gen-args.js,build.js,build-ads.py,audit.py,ads-audit.py,check-remote.py,publish.py,loon-coverage.py,ad-surface-audit.py,rule-effectiveness.py,bypass-audit.py}
.github/workflows/check.yml                         # CI：push 自动跑 npm run check
```

约定：

- 改脚本只改 `src/`；`src/common/` 是共享脚本唯一写点，品牌差异进 `families.json`；
- `plugins/` 是生成物/部署目录：`npm run build` / `npm run build:ads` 生成，不手改（lint 会报 stale）；
- `.plugin` 与 `scripts/` 必须同级（脚本引用是相对路径），提交 `src/` 与 `plugins/` 同时入库；
- 发布直接 `git push`（raw 直链即生效）；核对远端一致性用 `python3 tools/check-remote.py`，自动对齐可用 `tools/publish.py --with-source --yes`；
- 更新行为后 bump `#!version=`，重新导入/刷新远程插件即生效。

新增插件族：`src/<family>/xxx.js` → `plugins/<family>/Xxx.plugin`（新版 `script("scripts/xxx.min.js", {...})` 相对路径）→ `npm run build` → 补测试与 README；要共享脚本就在 `families.json` 加参数。`ads` 例外：无 JS 源码，只改 `src/ads/domains.json` 后 `npm run build:ads`。

## 边界

只做网络层广告过滤与激励链路保活，不做广告欺诈：不缩短广告时长、不伪造 SDK 完成回调、不重复领取、不在未看完广告时调用发奖接口、不绕过服务端风控。`ads.plugin` 会同时拦掉激励广告——「去广告」与「保奖励」的固有权衡，不是 bug。
