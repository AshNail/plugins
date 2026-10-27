# Loon 原生优先：能力盘点、差距分析与探索路线

> **一句话结论**：本仓库把「能开关的」做到了极致，但 Loon 有近一半能力**天生不能开关**——它们只能用构建期/发行期手段启用。缺的不是功能，是**开关模型**。
>
> 依据：`docs/loon-feature-checklist.md`（官方文档逐页核对）、两份外部去广告指南、iRingo / Biliverse / DualSubs 三个线上插件工程的实际产物、本仓库 46 套件 / 1398 断言现状。
> 适用门槛：soda/douyin 3.5.1(983)+（gzip 清理 988+）、ads 3.5.3(1008)+。
> 证据标注：**【文档】**= Loon 官方手册明示；**【实证】**= 第三方线上 Loon 插件正在使用；**【待证】**= 假设，需真机。

> **落地状态（2026-10-27 · soda v2.8.0 / douyin v0.8.0）**
> 本文的结论已按「常开的进静态层、要改主意的才进开关」落地，不再用发行变体：
>
> | 项 | 状态 | 落点 |
> |---|---|---|
> | E1 QUIC 强制回退 | ✅ 常开 | soda 8 条 / douyin 7 条 `AND,((DOMAIN-SUFFIX,…),(PROTOCOL,QUIC)),REJECT` |
> | E2 请求免压缩 | ❌ 实测后放弃 | 自家 HAR：upsell gzip 后 183–191 KB，去压缩会膨胀 5~10 倍 |
> | E8a `h2` | ✅ 常开 | `[MITM] h2 = true` |
> | E5 跨层命中矩阵 | ✅ 进 lint | 真实 URL 交叉验证 + 允许清单，可拦截注入的短路配置 |
> | E6 参数 schema | ◐ 只做标签单源 | `SWITCH_LABELS` 与 `[Argument]` 双向对账，未上全量生成器 |
> | E7 lite/strict 变体 | ❌ 取消 | 静态层本来就是常开，不需要靠“装哪个版本”来开关 |
> | E3 `body.mock` / E4 `jq` | ⏸ 未做 | 缺端点取证；原生 JSON 动作对 gzip 响应的行为未确认，贸然迁移会让 988 以下用户静默失效 |

---

## 0. 五条判断

1. **增量不在「更多域名」，在「原生响应层」。** ads 已有 1200 条 `[Host]` 映射（744 个精确主机）、30 条 `DOMAIN-WILDCARD`，DNS 覆盖接近饱和。`[Rewrite]` 全仓仍然只用 `reject_dict(200)` 一个动作；本轮补的是 `[Rule]` 的 `AND+PROTOCOL,QUIC`，`header.*` / `body.mock` / `json.jq` / `reject_array` / `reject_img` 仍未使用（其中 `header.del` 经实测后主动放弃，见 E2）。
2. **MITM 的真实边界是传输层，不是规则层。** 脚本只能看见 TCP+TLS。两个绕过面：HTTPDNS（已有 `[Host]` + `REJECT-DROP` + `[IP Rewrite]` 三重）与 QUIC/HTTP/3（**目前零配置**）。
3. **三个站点证明的范式是「一份源码 → 多端产物 + 参数 schema + 原生降级版」。** 本仓库第 1 项已做到（`families.json`），第 2、3 项缺失。
4. **当前最大风险是一致性，不是功能不足。** soda 39 条 `response if`、37 处 `requires_body`；同一批开关名在 5 个地方手写（`[Argument]`、`[Script]`、`status.js` 的 `SWITCH_LABELS`、README、lint 矩阵）。
5. **边界不动。** 不做激励欺诈；外部资源依赖（`mock_file`、第三方网关）继续拒绝。但**内联 `body.mock`** 不引入任何外部依赖，不在禁令范围内。

---

## 1. 外部资料综述

### 1.1 两份指南：合并后的「形态 × 层」表

两文合计 18 种形态，去重后 10 类。关键不是清单长度，而是**每一类只有一个层真正有效**——打错层的典型症状写在最后一列。

| 形态 | 下发/呈现载体 | 唯一有效的层 | 打错层的症状 |
|---|---|---|---|
| 开屏（在线） | 启动接口 JSON | 响应体裁剪 + 请求拦截 | 空白等待 → 1.5~3s 超时降级 |
| 开屏（离线缓存） | 本地沙盒 | **设置层**关预载 + 素材 CDN | 断网照样出广告 |
| 摇一摇 / 扭一扭 | 设置阈值 + 广告元数据 | **设置层**置零 + 元数据删除 | 只阻断跳转 → 卡在倒计时 |
| 信息流穿插 | Feed JSON 混排 | 字段级裁剪（保留包络） | 整包 reject → 白屏 / 重试 |
| 弹窗 / Upsell | 商业化配置字典 | 字典 + 排序数组**双清** | 只删字典 → 唤起时 NPE |
| 贴片 / 音频插播 | 播放器预配置 | 字段置空 + 状态解绑 | 拦截 → 黑屏等广告超时 |
| 搜索 / 推荐词 | `search-block` | 结构化过滤 | 同信息流 |
| WebView / H5 联盟 | 联盟 JS + 素材 CDN | `[Host]` 127.0.0.1（网络层主场） | 拦接口没用，广告是前端拉的 |
| 激励视频 | `time_token` + 设备签名 | 只做**开关分流**，不伪造 | 伪造 = IVT，封号 / `amount=-1` |
| HTTPDNS / 上报 | 单 IPv4 / 埋点 | `REJECT-DROP` + `REJECT-DICT` | 200 空包 → 秒级重试风暴 |

三条可复用的方法论：

- **「保留包络」原则**：凡是客户端会解析结构体再渲染的接口，删字段不删响应。整包 reject 只适用于 fire-and-forget 的上报端点。
- **「双事实源」陷阱**：凡是「字典 + 排序数组」「开关 + 名单」成对下发的配置，必须同步清理，否则触发客户端空指针。
- **「二次伤害」意识**：广告拦截的代价常常不是漏广告，而是重试风暴、耗电、白屏。`REJECT-DROP` 与 `REJECT-DICT` 就是为二次伤害准备的两个反向工具。

### 1.2 三个站点：六条共同范式

三者同属一个生态（同文档骨架、同 Telegram、同 BoxJs 体系），但产物形态恰好覆盖了 Loon 插件的三个层次。

| 范式 | 证据（实际产物） | 本仓库 |
|---|---|---|
| **① 参数 schema 单一来源** | `arguments-builder.full.config.ts` 一份 TS 配置 → 同时生成 Surge/Loon/QX/Stash/Shadowrocket 的 `[Argument]` + `d.ts` + `boxjs.settings.json` | 手写，5 处重复 |
| **② 原生假响应，而非脚本造包** | `response.body.mock("text","AAAAAAA=",200,true)` + `response.header.set("grpc-status","0")` 直接伪造 gRPC 空响应 | 只有 `reject_dict(200)` |
| **③ 原生结构化裁剪** | `response-body-json-jq 'del(.data.payment)'`；`mock-response-body data-type=text ...` | 全部走 JS |
| **④ HTTP/2 显式开启** | `[Mitm]` 段 `h2 = true` | 未开 |
| **⑤ 降级发行版** | `loon.rewrite.handlebars` → 零脚本纯 Rewrite 版（同一功能的第二条产品线） | 无 |
| **⑥ 文档骨架固定** | 简介 / 使用方式 / 功能列表 / 安装链接 / 默认设置 / 更新日志 / 相关链接 | 部分（缺更新日志与默认设置表） |

**最有价值的一条是 ⑤**：它不是「多写一个模板」，而是承认**静态能力无法运行时开关**，于是用「发行变体」把它补回来。这一点直接命中本仓库的结构性缺口（见第 3 节）。

### 1.3 一条明确不采纳

Biliverse 的 Rewrite 版把 JSON 接口整体重定向到第三方网关 `app.nanocat.cloud` 由边缘侧改写。效果确实好、零脚本、全平台一致，但**响应数据出境到第三方**，与「自包含、不外发」的仓库纪律冲突。列入不采纳。

---

## 2. 能力矩阵：Loon 全栈 × 本仓库

图例：✅ 在用 / 🟡 半成品（注释里、可选组里）/ ❌ 未用。

| 段 | 能力 | 生效阶段 | 本仓库 |
|---|---|---|---|
| `[Host]` | 精确域 + `*.` 通配 → 127.0.0.1 | DNS | ✅ 1286 条（约 700 根域） |
| `[Rule]` | `DOMAIN` / `-SUFFIX` / `-KEYWORD` / `-WILDCARD` | 规则 | ✅ 30 条通配 |
| `[Rule]` | `IP-CIDR` / `IP-CIDR6` / `USER-AGENT` / `URL-REGEX` | 规则 | ✅ 可选组 |
| `[Rule]` | `PROTOCOL,QUIC` | 规则 | ✅ 常开，soda 8 / douyin 7 域 |
| `[Rule]` | `AND` / `OR` / `NOT` 逻辑组合 | 规则 | ✅ `AND,((DOMAIN-SUFFIX,…),(PROTOCOL,QUIC))` |
| `[Rule]` | `REJECT` / `-DROP` / `-DICT` | 规则 | ✅ |
| `[Rule]` | `REJECT-IMG` / `REJECT-ARRAY` | 规则 | ❌ |
| `[Rewrite]` | `reject` 族五种 | 复写（规则匹配前）**【文档】** | ✅ 仅 `reject_dict` ×3 |
| `[Rewrite]` | `header-add` / `header-del` / `header-replace` | 复写 | ❌ 评估后放弃（E2） |
| `[Rewrite]` | URL 重写 / 302 / 307 | 复写 | ❌ |
| `[Rewrite]` v2 | `response.body.mock(...)` / `response.header.set(...)` | 复写 | ❌ **实证可用** |
| `[Rewrite]` | `response-body-json-jq` / `mock-response-body` | 复写 | ❌ |
| `[Script]` | `http-request` / `http-response` | 脚本 | ✅ 57 条绑定（soda 43 / douyin 14） |
| `[Script]` | `cron` / `generic` | 脚本 | ✅ 提醒 + 状态看板 |
| `[Script]` | `network-changed` | 脚本 | ❌ |
| `[Script]` | `$done()` 无参 = 断开连接 **【文档】** | 脚本 | ❌（未用中断语义） |
| `[MITM]` | `hostname = %APPEND% ...` | 解密 | ✅ |
| `[MITM]` | `h2 = true` **【实证】** | 解密 | ✅ 常开 |
| `[IP Rewrite]` | 单 IPv4 `drop` | TUN（最早） | 🟡 16 条全注释 |
| `[General]` | `dns/doh/doh3-server` | 解析 | ✅ ads |
| `[Argument]` | `switch` / `input` / `select` | 配置 | ✅ |
| 通知 | `$notification.post` + `openUrl` | 输出 | ✅ |
| 元数据 | `#!openUrl` **【实证】** | 安装页 | ❌ |

**统计口径**（v2.8.0 后）：脚本层 100%，DNS 层 95%，**传输层 100%**（QUIC 回退 + h2），原生响应层 ~7%（仍是 1/14 个动作；`body.mock` / `json.jq` / `header.*` 均未用）。

---

## 3. 核心发现：开关模型的断层

### 3.1 三层开关模型

Loon 的能力按「能否在运行时改变」分成三层。本仓库只建设了第一层。

| 层 | 机制 | 生效时机 | 能覆盖的能力 | 本仓库 |
|---|---|---|---|---|
| **L1 运行时** | `[Argument]` + `enable=${x}` + 脚本内分支 | 每次请求 | 字段级裁剪、日志、cron、通知 | ✅ 做到极致 |
| **L2 构建时** | 数据源 `disabled` 标志 / 生成器条件 / 注释块 | 打包时 | 静态规则分组、名单批量启停 | 🟡 仅 ads 的 `domains.json` |
| **L3 发行时** | 变体插件（lite / strict） | 用户选装 | **QUIC 拒绝、静态 REJECT、`[IP Rewrite]`、`h2`、纯 Rewrite 版** | ❌ 完全缺失 |

### 3.2 代价：静态层全部躺在注释里

仓库里曾有三处「写好了但永远不生效」的静态能力，它们不是没做，是**没有启用通道**：

| 位置 | 内容 | 现状（v2.8.0 / v0.8.0 后） |
|---|---|---|
| `soda.plugin` / `douyin.plugin` 的 `[Rule]` 段 | 5 行 `DOMAIN,...,REJECT` 严格模式 | **已删除**：被 `blockAdDomains` + QUIC 回退取代，不再提供“手改注释”的分叉 |
| `ads.plugin` 的 `[IP Rewrite]` 段 | 16 条 HTTPDNS 单 IPv4 `drop` | 仍注释：这些 IP 可能与其他业务共用，属于“用户该自己决定”的可选项 |
| `ads.plugin` 的 `PROTOCOL,STUN` | WebRTC 防泄漏 | 仍注释：会打断部分 App 的语音/视频，同上 |

**这就是「全部开关化」原则的隐性代价**：`[Rule]`/`[Rewrite]`/`[MITM]`/`[IP Rewrite]` 都是静态配置，一旦坚持「一切进 `[Argument]`」，等价于**永久放弃静态层**。

但复查时要把“静态层”再拆一刀：

- **前置条件型**（QUIC 回退、h2）：关掉它，所有脚本都失效。**必须常开，不该有开关**——本次落地就是这一刀。
- **策略选择型**（`[IP Rewrite]` 网段、STUN 阻断、整域 REJECT）：关掉只是少一个效果，代价明确。**继续留在注释/开关里**，让用户自己决定。

---

## 4. 八个探索项（按杠杆排序）

### E1 传输层：QUIC 强制回退（杠杆最高）

- **现状**：`blockSplashAd`、`blockAdDomains`、全部 sanitize 脚本都依赖 MITM。如果目标域走 HTTP/3，脚本完全看不见——`device-checklist.md` 的 F 节已经在怀疑这一点，但没有解法。
- **做法**：对**仅有的 8 个 MITM 目标域**加逻辑规则，把 QUIC 打掉，逼客户端回退 TCP+TLS：
  ```ini
  AND,((DOMAIN-SUFFIX,api.qishui.com),(PROTOCOL,QUIC)),REJECT
  AND,((DOMAIN-SUFFIX,beta-luna.douyin.com),(PROTOCOL,QUIC)),REJECT
  ```
  只限定精确域名，不要用 `PROTOCOL,QUIC,REJECT` 全局规则（会伤视频/通话）。
  落地时**没有加 `pre-matching`**：逻辑规则里参数位置没有官方示例，默认匹配即可；
  域名能否被识别取决于 Loon 的 Fake IP / DNS 关联——如果 App 自己走 HTTPDNS 直连 IP，
  这条规则不会命中（`ads.plugin` 的 HTTPDNS 拦截可以补上这个前提）。
- **收益**：把「可能拦不住」变成「一定拦得住」，是所有脚本型功能的前置条件。
- **风险**：若 App 对这几个域强依赖 H3，回退会慢 100~300ms（首包）；极少数实现不回退 → 接口挂。**必须逐域灰度**。
- **验证**：开规则前后各冷启 3 次，看 Loon 日志中目标 URL 是否出现在「脚本命中」列表（而不是无记录）；同时观察 App 首屏耗时。
- **结论**：**P0，已常开落地**（soda 8 域 / douyin 7 域）。它天生不该有开关——关掉等于让所有脚本看不见流量。这也直接推翻了 E7：「变体」不是必需，直接开就行。

### E2 压缩层：`header-del Accept-Encoding` —— **实测后放弃**

- **原设想**：请求侧删掉压缩协商，让响应以明文回来，从而解除 988 门槛、省一次 `ungzip`。
- **为什么放弃**：自家 HAR 就写着答案——`/luna/commerce/v2/upsell` 在 `content-encoding: gzip` 下是 **183–191 KB**，
  `/luna/treasure/task/page/v2` 是 **16–21 KB**。JSON 的 gzip 比通常 5~10 倍，去压缩等于把这些响应放大一个数量级。
  为了省一次原生 `ungzip`（微秒级）去换每屏几十 KB 到 1 MB 的流量，是负收益。
- **唯一真实收益**：983–987（无 `$utils.ungzip`）能真正清理。但这批用户占比极低，且脚本已有“跳过并打标”的兜底。
- **保留的可能性**：若将来出现“响应体很小、且 Loon gzip 交接有 bug”的端点，可以**只针对该端点**加一条，
  并用 `tests/lint-plugins.py` 的 `Accept-Encoding` 反向断言改名放行。现在默认锁死。
- **结论**：**不做**。lint 反向锁死：插件 `[Rewrite]` 里出现 `Accept-Encoding` 直接报错。

### E3 响应层：内联 `body.mock`

- **现状**：`reject_dict(200)` 只能回 `{}`。凡是需要**特定信封**的接口（例如 `{"code":0,"data":{"closeType":"close_win"}}` 这种「告诉客户端没有弹窗」的响应），现在只能写脚本。
- **做法**：v2 复写直接造包，不落盘、不外链：
  ```ini
  response if ${url} ~= /^https:\/\/api\.qishui\.com\/luna\/commerce\/v2\/upsell/ then response.body.mock("json", "{\"code\":0,\"data\":{}}", 200) | response.header.set("Content-Type","application/json")
  ```
  第三方已在这种写法上跑生产**【实证】**；`mock_file`（外链文件）继续禁用，但 `body.mock` 是**内联字符串**，不违反自包含。
- **收益**：把「开关常开、逻辑恒定」的端点从 JS 迁到原生，省一次 JSC 启动 + 整包 parse。
- **风险**：**必须先有 HAR 证明该端点不承载奖励语义**；一旦误伤领奖链路，回滚需要发版。
- **验证**：对候选端点做 A/B：原生 mock vs 现脚本，比对 App 表现与发奖结果。
- **结论**：**P1，本轮未落地**。道理上成立，但当前没有“响应恒为固定信封”的端点能拿出 HAR 证据；误伤领奖链路的回滚要发版，不划算。等真机抓到候选再迁。

### E4 响应层：`json-jq` 承接「纯删除」

- **现状**：`sanitize.js` 1008 行、`settings.js` 629 行，其中相当一部分是「遍历数组删若干 key」。
- **做法**：官方/实证支持 `response-body-json-jq 'del(...)'`**【实证】**。把**无开关分支、无统计副作用**的纯删除迁到 jq：
  ```ini
  ^https:\/\/api\.qishui\.com\/luna\/search-block response-body-json-jq 'del(.data[] | select(.block_type=="advert"))'
  ```
- **收益**：减少 JS 面积 = 减少回归面；jq 在代理核内执行，无 JS 引擎开销。
- **风险**：jq 表达式可读性差、无日志、无法做「保留包络」之外的判断；复杂条件仍应留 JS。
- **验证**：同一份 HAR fixture 分别跑 JS 与 jq，diff 输出应完全一致（可复用现有 `tests/fixtures`）。
- **结论**：**P2，本轮未落地**。原生 `response.json.*` 对 gzip 响应体的行为未确认：脚本自己 `ungzip`，原生动作未必会；若它不解 gzip，迁移后会在 988 以下静默失效。先保留 JS，等拿到“Loon 对 gzip 响应执行 json 动作”的实证再谈减负。

### E5 判定层：跨层命中矩阵（治理项，零运行时风险）

- **现状**：lint 已经锁了「脚本 vs 脚本」首条命中，但**没有锁「Rewrite vs Script」「Rule vs Script」**。`soda.plugin` 的 `[Rewrite]` 与 `[Script]` 存在同域绑定（`splash/brand/report` 与 `splash/brand/retrieve` 同前缀），一旦有人把 Rewrite 正则放宽，脚本会静默失效——这正是历史上「settings 双绑定」那类 bug 的同构版本。
- **做法**：给 lint 增加一层矩阵：对每个 URL 样本，列出所有可能命中的 `[Rule]` / `[Rewrite]` / `[Script]`，标出「跨层短路」；允许清单显式登记「故意短路」。
- **收益**：把「注释里写清楚」升级为「CI 挡住」。
- **风险**：无（纯静态检查）。
- **结论**：**P0**，与 E1 无关，可立即做。

### E6 参数层：schema 单一来源

- **现状**：一个开关要改 5 处。`SWITCH_LABELS` 是纯手工镜像，已经出现过「加了开关忘了加标签」的情况（状态看板显示不全但不报错）。
- **做法**：`src/args/<family>.json` 定义为唯一事实源 → 生成 ① `[Argument]` 段 ② `[Script]` 的 `{${...}}` 绑定 ③ `status.js` 的标签数组 ④ README 开关表 ⑤ lint 绑定矩阵。第三方用 TS + handlebars 做到了六端生成**【实证】**，本仓库只需单端，成本更低。
- **收益**：消灭「参数遗漏」这一整类 bug；新增开关从 5 处编辑降到 1 处。
- **风险**：生成器本身要有测试（对现有产物做 golden diff，必须逐字节一致才算迁移成功）。
- **验证**：`npm run build` 后 `git diff` 为空。
- **结论**：**P0**（重构，不动运行时）。

### E7 发行层：lite / strict 变体 —— **已取消**

- **原做法**：给静态能力单独发一个 `-strict` 变体，靠“装哪个版本”来开关。
- **为什么取消**：变体是「静态能力不能运行时开关」的补丁；但本轮真正需要的静态能力（QUIC 回退 / h2）**本来就不该由用户关**——它们是所有脚本的前置条件，不是可选项。给不可选项做变体，等于把“默认正确”拆成“默认可能错”。
- **保留的纪律**：真要给用户选择的（`blockAdDomains`、`blockSplashAd`、`cleanAds`）仍然是 `[Argument]` 开关；`ads.plugin` 的归因/统计组仍是 `domains.json` 的 `disabled` 构建期开关。
- **结论**：**不做**。发行物继续只有三个插件，减少一倍维护面。

### E8 观测层：`h2` 与原生层计数

- **现状**：状态看板能看到 Loon 版本、节点、运行模式、gzip 能力，但看不到「这次请求走的什么协议」「原生层有几条在生效」。
- **做法**：① `[MITM]` 加 `h2 = true`（第三方实证**【实证】**），让 HTTP/2 与 gRPC 端点进入可见范围；② 状态看板增加一行「原生层：Rule N / Rewrite M / 脚本 K」——由构建器把计数写进 `families.json` 常量，脚本只读不算。
- **收益**：把「看不见的层」变成可观测数字；`h2` 是 gRPC 类接口（抖音主站大量使用）被 MITM 的前提。
- **风险**：`h2 = true` 在极老 build 上可能不识别（需按 build 守卫，或只在 ≥1008 变体启用）。
- **结论**：**P2，部分落地**：`h2 = true` 已进两插件 `[MITM]`；计数没有走“构建器写常量”，而是 `families.json.quicCount` + lint 对账真实规则数（更简单，且漂移会直接报错）。

---

## 5. 决策树：什么时候用原生，什么时候用脚本

```text
这个改动能不能用一条原生表达式写完？
├─ 能，且是 [Rewrite] 能表达的（改头 / 拦包 / 假包 / 删固定 key）
│   ├─ 需要用户开关？ ── 是 ──> 条件 Rewrite（${开关} == true && …）★ 仍比脚本轻
│   └─ 不需要 ───────────────> 静态 Rewrite（常开）
├─ 能，但只能落在 [Rule] / [MITM] / [IP Rewrite]（不吃 [Argument]）
│   ├─ 关掉它会让其它功能全部失效？ ── 是 ──> 静态常开，不做开关 ★ 本次做法
│   └─ 用户真的会想关？ ─────────────> 换脚本实现（或让用户改主配置）
└─ 不能
    ├─ 需要读状态 / 写状态 / 发通知？ ── 是 ──> 脚本
    ├─ 需要按字段语义决定「删还是留」？ ── 是 ──> 脚本
    └─ 只是「整包丢弃 / 固定假包 / 删固定字段」 ──> 原生（reject 族 / body.mock / jq）
```

五条判据，按顺序问：

1. **静态可表达？** 能 → 原生。省一次 JSC 启动，少一个失败面。
2. **这段配置能不能吃 `[Argument]`？** Loon v2 的 `[Rewrite]` 能（`${开关} == true`）；`[Rule]` / `[MITM]` / `[IP Rewrite]` **不能**。只有“不能 + 又必须可关”才退回脚本。
3. **关掉它会不会让其它功能全部失效？** 会 → 它是前置条件，必须常开，别做成开关（QUIC 回退、h2 都属于这档）。
4. **需要跨请求状态？** （打卡、统计、去重）需要 → 脚本。
5. **需要「保留包络」的字段判断？** 需要 → 脚本；纯删固定 key → jq。

> 旧版本文写的是“需要开关就只能脚本”，这句在 v2 Rewrite 上是错的：`[Argument]` 在 Rewrite 条件里可用（官方 Plugin 文档的 `response if ${enabled} == true …` 就是例子）。本次没有因此迁移现有脚本，是因为现有开关绑定的都是响应体字段逻辑，不是“拦/不拦”这种一句话判断。

---

## 6. 路线图（2026-10-27 更新）

### 已完成（本次落地）

| 项 | 动作 | 验收 |
|---|---|---|
| E1 | soda 8 / douyin 7 条 `AND+PROTOCOL,QUIC` 回退，常开 | lint 锁定集合；真机 F 段观察回退耗时 |
| E8a | `[MITM] h2 = true` | lint 锁定；状态看板不再显示“未知协议” |
| E8b | 状态看板「静态层：QUIC 回退 N 域」 | `families.json.quicCount` + lint 对账 + `test_status` 4 条断言 |
| E5 | lint 跨层命中矩阵 | 注入 `DOMAIN,api.qishui.com,REJECT` / 终止型 Rewrite 均能报错 |
| E6 | `SWITCH_LABELS` ↔ `[Argument]` 双向对账 | 16 开关 / 16 标签，漂移即失败 |
| 清理 | 删除两插件注释里的 `[Rule]` 严格模式 | 常量面 -10 行，不再有“手改配置”的分叉 |

### 待真机（不改代码，只观察）

| 项 | 观察点 | 回滚 |
|---|---|---|
| E1 | 冷启 3 次首屏耗时；Loon 规则日志命中 QUIC 回退 | 删该域一行 |
| E2 | `/luna/*` 响应是否还有 `Content-Encoding` | 删对应 rewrite 行 |
| E8a | 若报网络错误，先删 `h2 = true` 复测 | 删一行 |
| §8 层序 | 同域放 Rewrite reject 与 Rule REJECT-DICT，看日志谁命中 | 实验后删除 |

### 明确不做（见第 7 节）

`body.mock` / `json.jq` 的批量迁移、请求免压缩（E2）、`-strict` 变体、全局 QUIC 拒绝、第三方改写网关。

---

## 7. 不采纳清单（增量）

| 项 | 理由 |
|---|---|
| `mock_file` / 远程 mock 文件 | 外部依赖，断网即失效；与自包含冲突 |
| 第三方改写网关（`*.nanocat.cloud` 类） | 响应数据出境，违背边界 |
| 全局 `PROTOCOL,QUIC,REJECT` | 伤视频/通话；只允许按域 + `AND` 组合 |
| 用 `302` 把广告请求重定向到本地服务 | 需要额外进程；`body.mock` 已能覆盖同一场景且零依赖 |
| 把 `[Argument]` 开关写进 `[Rule]` / `[MITM]` / `[IP Rewrite]` | 语法上不成立（这几段不支持变量）；但 `[Rewrite]` **支持** `${开关}`，所以“需要开关”不再是退回脚本的理由 |
| `-strict` 变体 | 静态层（QUIC / h2）是前置条件，不是可选项；给它做变体等于把正确拆成可能错 |
| 静态层开关（`quicFallback=true/false` 之类） | 关掉后所有脚本静默失效，属于“看起来能配、实际只会配错”的开关 |
| 手改注释启用严格模式 | 用户改不了 raw 插件；已用 `blockAdDomains` + QUIC 回退覆盖同一场景 |
| 引入 BoxJs 作为配置面板 | 多一个外部依赖；现有 `[Argument]` + 状态看板已覆盖单 App 场景 |

---

## 8. 附：层序的一个待确认点

外部指南画的层序是「DNS → `[IP Rewrite]` → `[Rule]` → `[Rewrite]` → `[Script]`」，但 Loon 官方 rewrite 文档明确写「**复写的处理会在规则匹配之前**」**【文档】**。

两者不一定矛盾：官方说的「规则匹配」很可能指**策略选择**（DIRECT/PROXY），而带 `pre-matching` 的规则在更早的解析阶段生效，属于另一趟匹配。但在真机确认前，**不要把关键逻辑建立在层序假设上**。

建议做一次 5 分钟对照实验：对同一个 URL 同时放一条 `[Rewrite] ... reject_dict(200)` 和一条 `[Rule] ... REJECT-DICT`，看 Loon 日志里命中哪一条、返回的 `Content-Type` 是哪一个。

**本次落地后的姿态**：E5 的跨层矩阵按“两层都可能先命中”的保守假设写——只要同一 URL 上同时存在静态整域拒绝与脚本、或终止型复写与脚本，就报错，不依赖谁先谁后。这样实验结论无论偏向哪一边，lint 都不会漏。实验本身仍未做，`[待证]` 状态保留。
