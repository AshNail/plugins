# Loon 插件仓库

> 仓库 [`AshNail/plugins`](https://github.com/AshNail/plugins) · soda/douyin 要求 **Loon 3.5.1(983)+**（gzip 响应解析需 **988+**）；`ads.plugin` 与全部 App 插件门槛统一降到 **App Store 正式版 3.5.2(996)**——`DOMAIN-WILDCARD` 仅 TestFlight 3.5.3(1008) 才有，改为默认注释层，绝不再用 TF 版本卡住真实用户 · **无需 GitHub Pages**（Loon 以插件 URL 为基准解析同级 `scripts/`）

个人 Loon 插件集合，按「一个 App 一个插件」组织：汽水音乐（soda）、抖音（douyin）、广告平台拦截器（ads），以及 12 个按 App 取证落地的去广告插件（微信、美团、闲鱼、起点读书、银行合集×6 App、米家、智慧房东、X、Instagram、不背单词、软考通、MBA大师）。逆向说明、字段取证、使用边界都在各插件目录的 README 里。

## 一键导入

在 **iPhone / iPad 用 Safari** 打开本页，点按钮跳进 Loon；GitHub App / 微信内置浏览器可能拦截跳转，用 Safari 或复制备用链接。

<!-- Loon 官方通用链接（Universal Link，AASA: /openloon/*）；loon:// custom scheme 在网页上不可靠 -->

| 插件 | 版本 | 一句话用途 | 按钮 |
|---|---:|---|---|
| 汽水音乐 `soda.plugin` | 2.8.5 | 保奖励 + 去广告 + 广告域名拦截 + 开屏请求拦截 + 设置层 + 隐藏【听抖音】+ 每日提醒 + 状态自检看板（含 Loon 环境诊断），全部开关控制 | [![导入 soda](https://img.shields.io/badge/Loon-导入汽水音乐-blue?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fsoda%2Fsoda.plugin) |
| 抖音 `douyin.plugin` | 0.8.5 | 福利页精简 + 信息流广告清理 + 商业化弹窗清理 + 开屏请求拦截 + 状态自检看板（含 Loon 环境诊断，2026-10 真实 HAR 取证） | [![导入 douyin](https://img.shields.io/badge/Loon-导入抖音-black?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fdouyin%2Fdouyin.plugin) |
| 广告平台拦截器 `ads.plugin` | 2.7.0 | DNS 层全平台拦截 + HTTPDNS 防绕过(REJECT-DROP) + 公共 DoH/DoT 防泄漏；DOMAIN-WILDCARD 广告子域通配 + 数字分片家族层 `[0-9]`（需 TF 3.5.3，默认注释、可取消）+ IP Rewrite(Build 1007+, 默认注释)；**App Store 3.5.2 即可全量导入生效**，零证书、零 MITM/脚本 | [![导入 ads](https://img.shields.io/badge/Loon-导入广告拦截器-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fads%2Fads.plugin) |

### App 专属去广告插件（零证书默认态，`[Host]`/`[Rule]`；3 个非固定 App 另带默认注释的可选 MITM 增强层）

每个插件的证据、置信分级（A/B/C）与「能力天花板」如实写在各自 README；与 `ads.plugin` 的域重叠是有意设计（按 App 开关是分组语义）。
美团/闲鱼/起点读书未做证书固定，插件文末附**整段默认注释**的 `[MITM]` + `URL-REGEX` 路径级规则（同域广告接口黑洞会伤功能，只有解密后按路径拦才可能净化）；装不装证书、启不启用完全自愿，银行/微信/米家/X/Instagram 因证书固定或 mmtls 红线**不提供**本层。

| 插件 | 覆盖对象 | 天花板一句话 |
|---|---|---|
| [wechat](plugins/wechat/README.md) | 微信进程内 GDT/优量汇 + 8 个朋友圈/视频号素材主机 | 素材空白化、条目不可移除（mmtls 内联） |
| [meituan](plugins/meituan/README.md) | iOS 官方 SDK 目录实证 ADN（Sigmob/ToBid/美数）+ impdsp/mads + 遥测；+可选 MITM 层（开屏/启动配置路径 + p[0-9] 广告素材路径） | 自建广告与业务同域同 CDN，≈25-35% 可切；路径层需装证书 |
| [xianyu](plugins/xianyu/README.md) | iyes.youku.com + AMDC + Tunion/afpapi；+可选 MITM 层（mtop splash.ads / ad.expose 路径） | 广告 100% 内嵌 mtop 网关，DNS 层≈0-5%；路径层需装证书 |
| [qidian](plugins/qidian/README.md) | 起点读书 first-party 广告域 + 遥测；+可选 MITM 层（magev6 argus 6 条广告接口，REJECT-DICT） | 推荐位与内容同域（magev6）黑洞不可分；路径层需装证书 |
| [banks](plugins/banks/README.md) | 招商/银联 6 银行 App 广告端点 | 银行 App 无第三方 ADN，广告≈全内联 |
| [mijia](plugins/mijia/README.md) | 小米系统广告域（ad.xiaomi.com 族） | 只影响米家 App 内推广位 |
| [zhihuifangdong](plugins/zhihuifangdong/README.md) | 五家聚合 SDK（穿山甲/优量汇/快手/百度/倍孜） | 开屏/插屏可断；ttlock 设备链路红线 |
| [x](plugins/x/README.md) | Twitter/X 像素与广告控制台域 | App 内信息流广告内联，DNS 层≈像素 only |
| [instagram](plugins/instagram/README.md) | FAN/pixel/an 族 | 同上，信息流广告不可分 |
| [ruankao-tong](plugins/ruankao-tong/README.md) | 广点通（官方协议唯一自证 SDK） | 激励任务依赖，慎用 |
| [bubei-danci](plugins/bubei-danci/README.md) | 跟踪端点瘦身（官方目录无广告 SDK） | 诚实低收益 |
| [mba-dashi](plugins/mba-dashi/README.md) | 百度统计族（默认关） | 官方协议无广告 SDK |

导入链接统一格式：`https://raw.githubusercontent.com/AshNail/plugins/main/plugins/<slug>/<slug>.plugin`（各插件 README 内有按钮）。

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
| 全仓库 | [`docs/app-coverage.md`](docs/app-coverage.md) | **App 覆盖率审计**：拿 14 家上游黑名单反查 12 个 App 插件的品牌域缺口（A≥3 源/B=2 源），品牌根域白名单防 typosquat 误报；候选≠必拦，逐条定级后才进源（生成物） |

---

## 开发者速查

```bash
npm ci
npm run build       # src/common 家族展开 → src/{soda,douyin}/*.js → plugins/*/scripts/*.min.js
npm run build:ads   # src/ads/domains.json → plugins/ads/ads.plugin
npm run build:apps  # src/apps/*.json + _sdk.json → plugins/<slug>/<slug>.plugin（12 个 App 插件）
npm run build:app-readmes  # src/apps/*.json → plugins/<slug>/README.md
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
src/apps/    _sdk.json + <slug>.json                # App 插件数据源（SDK 组引用 ads，域名不复制）
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
